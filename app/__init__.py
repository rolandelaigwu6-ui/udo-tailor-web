import os
import click
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.middleware.proxy_fix import ProxyFix
from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)


def create_app(config_name=None, config_overrides=None):
    app = Flask(__name__, instance_relative_config=True)

    if config_name == 'testing':
        from config import TestConfig
        app.config.from_object(TestConfig)
    else:
        from config import Config
        app.config.from_object(Config)

    if config_overrides:
        app.config.update(config_overrides)
    from config import normalize_database_url
    app.config['SQLALCHEMY_DATABASE_URI'] = normalize_database_url(app.config['SQLALCHEMY_DATABASE_URI'])
    if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgresql'):
        options = dict(app.config.get('SQLALCHEMY_ENGINE_OPTIONS', {}))
        for key, value in {'pool_size': 2, 'max_overflow': 2, 'pool_recycle': 300}.items():
            options.setdefault(key, value)
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = options
    if not app.config.get('TESTING'):
        key = app.config.get('SECRET_KEY') or ''
        if len(key) < 32 or key in {'dev-secret-change-me-in-production', 'change-me-to-a-long-random-string'}:
            raise RuntimeError('Set SECRET_KEY to a random value of at least 32 characters.')
        username = app.config.get('ADMIN_USERNAME') or ''
        password = app.config.get('ADMIN_PASSWORD') or ''
        if not username.strip() or len(username) > 80 or len(password) < 12 or password.lower() in {'changeme', 'change-me-to-a-long-random-password'}:
            raise RuntimeError('Set ADMIN_USERNAME (1–80 characters) and a strong ADMIN_PASSWORD (at least 12 characters).')

    backend = app.config.get('STORAGE_BACKEND')
    if backend not in {'local', 'supabase'}:
        raise RuntimeError('STORAGE_BACKEND must be local or supabase.')
    if backend == 'supabase':
        from urllib.parse import urlsplit
        import re
        url = urlsplit(app.config.get('SUPABASE_URL', ''))
        if (url.scheme != 'https' or not url.hostname or url.username or url.password
                or url.path not in {'', '/'} or url.query or url.fragment
                or not app.config.get('SUPABASE_SERVICE_ROLE_KEY')
                or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,62}', app.config.get('SUPABASE_STORAGE_BUCKET', ''))):
            raise RuntimeError('Configure a valid HTTPS SUPABASE_URL, server-only SUPABASE_SERVICE_ROLE_KEY, and SUPABASE_STORAGE_BUCKET.')
    if app.config.get('REQUIRE_EXTERNAL_STORAGE') and (backend != 'supabase' or
            not app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgresql')):
        raise RuntimeError('Free hosting requires PostgreSQL and Supabase image storage to preserve your data.')

    if app.config.get('TRUST_PROXY_HEADERS'):
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=0, x_port=0, x_prefix=0)

    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    from app.models import Admin, Clothing, ClothingImage, SiteSettings, Visitor, ClothingActivity, Achievement, ClientShowcase  # noqa
    from app import seeds

    from app.migrations import schema_is_current, upgrade_database
    from app.utils import image_url, http_url, phone_digits, cleanup_pending_uploads
    app.jinja_env.filters.update(image_url=image_url, http_url=http_url, phone_digits=phone_digits)
    app.teardown_request(cleanup_pending_uploads)

    with app.app_context():
        if app.config.get('TESTING'):
            db.create_all()
        app.config['SCHEMA_READY'] = app.config.get('TESTING') or schema_is_current()
        if app.config['SCHEMA_READY']:
            seeds.seed_admin(app)
            seeds.seed_settings()
        else:
            app.logger.warning('Database requires migration: run flask --app run.py init-db.')

    @app.before_request
    def require_schema():
        if not app.config['SCHEMA_READY'] and request.endpoint != 'static':
            return 'The catalogue is temporarily unavailable.', 503

    from app.routes.public import public_bp
    from app.routes.admin import admin_bp
    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')

    @app.route('/healthz')
    def health():
        try:
            db.session.execute(text('SELECT 1'))
        except SQLAlchemyError:
            db.session.rollback()
            return {'status': 'unavailable'}, 503
        return {'status': 'ok'}

    @app.cli.command('init-db')
    def init_db():
        upgrade_database()
        app.config['SCHEMA_READY'] = True
        seeds.seed_admin(app)
        seeds.seed_settings()
        print('Database initialized and migrated.')

    @app.cli.command('init-storage')
    def init_storage():
        if app.config['STORAGE_BACKEND'] == 'supabase':
            from app.storage import initialize_bucket
            initialize_bucket()
            click.echo('Catalogue image storage initialized.')

    @app.cli.command('seed-demo')
    def seed_demo():
        if not schema_is_current():
            raise RuntimeError('Run init-db before seed-demo.')
        seeds.seed_demo_data()
        print('Demo data seeded.')

    @app.cli.command('reset-admin-password')
    @click.option('--username', help='Existing admin username; defaults to ADMIN_USERNAME.')
    @click.option('--rename-to-configured', is_flag=True, help='Also rename this admin to ADMIN_USERNAME.')
    def reset_admin_password(username, rename_to_configured):
        from werkzeug.security import generate_password_hash
        if not schema_is_current():
            raise click.ClickException('Run init-db first.')
        admin = Admin.query.filter_by(username=username or app.config['ADMIN_USERNAME']).first()
        if admin is None:
            raise click.ClickException('Admin not found. Environment credentials only initialize new accounts; use --username with the existing username.')
        password = click.prompt('New password', hide_input=True, confirmation_prompt=True)
        if len(password) < 12 or password.lower() == 'changeme':
            raise click.ClickException('Use a password of at least 12 characters.')
        if rename_to_configured:
            conflict = Admin.query.filter(Admin.username == app.config['ADMIN_USERNAME'], Admin.id != admin.id).first()
            if conflict:
                raise click.ClickException('Configured username already belongs to another admin.')
            admin.username = app.config['ADMIN_USERNAME']
        admin.password_hash = generate_password_hash(password)
        db.session.commit()
        click.echo('Admin password updated. Rotate SECRET_KEY to invalidate existing sessions.')

    @app.context_processor
    def inject_settings():
        settings = SiteSettings.query.first()
        if settings is None:
            settings = SiteSettings()
            db.session.add(settings)
            db.session.commit()
        from app.models import Clothing
        cats = [c[0] for c in db.session.query(Clothing.category).distinct().all() if c[0]]
        return dict(site_settings=settings, nav_categories=cats)

    @app.errorhandler(404)
    def not_found(e):
        if not app.config['SCHEMA_READY']:
            return 'Not found', 404
        return render_template('errors/404.html'), 404

    @app.errorhandler(403)
    def forbidden(e):
        if not app.config['SCHEMA_READY']:
            return 'Forbidden', 403
        return render_template('errors/403.html'), 403

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        if not app.config['SCHEMA_READY']:
            return 'Database is not initialized.', 500
        return render_template('errors/500.html'), 500

    @app.errorhandler(413)
    def too_large(e):
        return 'File too large', 413

    return app
