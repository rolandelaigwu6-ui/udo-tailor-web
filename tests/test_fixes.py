import io
from html.parser import HTMLParser
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from app import create_app, db, limiter
from app.migrations import schema_is_current, upgrade_database
from app.models import Clothing, ClothingActivity, ClothingImage, Visitor, Achievement, ClientShowcase, SiteSettings


def png(name='image.png'):
    stream = io.BytesIO()
    Image.new('RGB', (4, 4), 'blue').save(stream, 'PNG')
    stream.seek(0)
    return stream, name


def design(client, **values):
    data = {'name': 'Test design', 'availability': 'Available', **values}
    assert client.post('/admin/clothes/new', data=data).status_code == 302
    with client.application.app_context():
        item = Clothing.query.filter_by(name=data['name']).first()
        return item.id, item.slug


@pytest.mark.parametrize('path', ['/', '/collections', '/new-designs', '/about', '/contact', '/missing'])
def test_public_pages(client, path):
    assert client.get(path).status_code == (404 if path == '/missing' else 200)


@pytest.mark.parametrize('path,method', [
    ('/admin/clothes', 'get'), ('/admin/settings', 'get'), ('/admin/activity', 'get'),
    ('/admin/about', 'get'), ('/admin/achievements/new', 'post'),
    ('/admin/showcase', 'get'), ('/admin/clothes/new', 'post'),
    ('/admin/clothes/1/delete', 'post'), ('/admin/clothes/1/edit', 'post'),
    ('/admin/clothes/1/image/1/delete', 'post'), ('/admin/clothes/1/image/1/primary', 'post'),
    ('/admin/showcase/1/delete', 'post'), ('/admin/showcase/1/edit', 'post'),
    ('/admin/achievements/1/delete', 'post'), ('/admin/clothes/1/activity', 'get'),
])
def test_admin_routes_require_authentication(client, path, method):
    assert getattr(client, method)(path).status_code == 302
    with client.application.app_context():
        assert Clothing.query.count() == 0


def test_delete_design_with_activity_and_upload(auth_client):
    cid, slug = design(auth_client, images=png())
    auth_client.get('/clothes/' + slug)
    auth_client.post(f'/like/{cid}')
    auth_client.post(f'/interest/{cid}', json={'answer': 'yes'})
    with auth_client.application.app_context():
        image = db.session.get(Clothing, cid).primary_image
        image_path = Path(auth_client.application.config['UPLOAD_FOLDER']) / Path(image.image_url).name
        assert image_path.exists()
    assert auth_client.post(f'/admin/clothes/{cid}/delete').status_code == 302
    with auth_client.application.app_context():
        assert db.session.get(Clothing, cid) is None
        assert ClothingActivity.query.count() == 0
        assert ClothingImage.query.count() == 0
    assert not image_path.exists()


def test_custom_upload_directory_and_traversal(auth_client):
    cid, _ = design(auth_client, images=png())
    with auth_client.application.test_request_context():
        url = db.session.get(Clothing, cid).primary_image.url
    assert url.startswith('/uploads/')
    response = auth_client.get(url)
    assert response.status_code == 200
    assert response.mimetype == 'image/png'
    assert auth_client.get('/uploads/../config.py').status_code == 404


@pytest.mark.parametrize('files', [
    lambda: (io.BytesIO(b'not an image'), 'fake.png'),
    lambda: png('wrong.jpg'),
    lambda: (io.BytesIO(b'bad'), 'bad.html'),
    lambda: [png(), (io.BytesIO(b'bad'), 'second.png')],
])
def test_invalid_uploads_are_visible_and_atomic(auth_client, files):
    response = auth_client.post('/admin/clothes/new', data={
        'name': 'Invalid upload', 'availability': 'Available', 'images': files()})
    assert response.status_code == 200
    assert b'alert-danger' in response.data
    with auth_client.application.app_context():
        assert Clothing.query.count() == 0
    assert not list(Path(auth_client.application.config['UPLOAD_FOLDER']).iterdir())


def test_upload_size_limit(auth_client):
    auth_client.application.config['MAX_CONTENT_LENGTH'] = 128
    assert auth_client.post('/admin/clothes/new', data={'images': png()}).status_code == 413


def test_image_actions_and_edit_form(auth_client):
    cid, _ = design(auth_client, images=[png(), png()])
    with auth_client.application.app_context():
        images = db.session.get(Clothing, cid).images
        first, second = [i.id for i in images]
    class FormParser(HTMLParser):
        depth = 0
        def handle_starttag(self, tag, attrs):
            if tag == 'form':
                assert self.depth == 0, 'Nested form'
                self.depth += 1
        def handle_endtag(self, tag):
            if tag == 'form':
                self.depth -= 1
    parser = FormParser()
    parser.feed(auth_client.get(f'/admin/clothes/{cid}/edit').text)
    assert parser.depth == 0
    assert auth_client.post(f'/admin/clothes/{cid}/edit', data={'name': 'Updated design', 'availability': 'Available'}).status_code == 302
    assert auth_client.post(f'/admin/clothes/{cid}/image/{second}/primary').status_code == 302
    with auth_client.application.app_context():
        assert db.session.get(Clothing, cid).primary_image.id == second
    assert auth_client.post(f'/admin/clothes/{cid}/image/{second}/delete').status_code == 302
    with auth_client.application.app_context():
        assert db.session.get(Clothing, cid).primary_image.id == first
    assert auth_client.post(f'/admin/clothes/{cid}/image/9999/primary').status_code == 404
    with auth_client.application.app_context():
        assert db.session.get(Clothing, cid).primary_image.is_primary


@pytest.mark.parametrize('payload', [[], 'text', None, {'name': 12}, {'name': 'x' * 121},
                                     {'email': 'invalid'}, {'email': ['x']}, {'email': 'x' * 121}])
def test_invalid_identity(client, payload):
    response = client.post('/visitor/identify', data=__import__('json').dumps(payload), content_type='application/json')
    assert response.status_code == 400
    with client.application.app_context():
        assert Visitor.query.count() == 0


def test_voluntary_identity_and_email_privacy(auth_client):
    cid, slug = design(auth_client)
    assert auth_client.post('/visitor/identify', json={}).status_code == 200
    assert auth_client.post('/visitor/identify', json={'name': 'Visitor', 'email': 'private@example.com'}).status_code == 200
    auth_client.post(f'/like/{cid}')
    for path in ['/', '/collections', '/about', '/contact', '/clothes/' + slug]:
        assert b'private@example.com' not in auth_client.get(path).data
    assert b'private@example.com' in auth_client.get('/admin/activity').data
    with auth_client.application.app_context():
        assert Visitor.query.count() == 1
        activity = ClothingActivity.query.filter_by(activity_type='LIKE').one()
        assert activity.visitor.email == 'private@example.com'


@pytest.mark.parametrize('email', ['@', 'a@', 'x', 12, ['x'], 'a' * 121 + '@example.com'])
def test_newsletter_validation(client, email):
    assert client.post('/newsletter/subscribe', json={'email': email}).status_code == 400


def test_newsletter_subscription(client):
    assert client.post('/newsletter/subscribe', json={'email': 'reader@example.com'}).status_code == 200
    assert client.post('/newsletter/subscribe', json={'email': 'reader@example.com'}).status_code == 200
    with client.application.app_context():
        assert Visitor.query.count() == 1
        assert Visitor.query.one().newsletter_subscribed


def test_analytics_consistent_and_interest_once_per_session(auth_client):
    cid, slug = design(auth_client)
    auth_client.get('/clothes/' + slug)
    for _ in range(2):
        auth_client.post(f'/like/{cid}')
        auth_client.post(f'/interest/{cid}', json={'answer': 'yes'})
    auth_client.post(f'/interest/{cid}', json={'answer': 'no'})
    for event in ['VIEW', 'LIKE', 'INTERESTED', 'NOT_INTERESTED', 'unknown']:
        assert auth_client.post(f'/track/{cid}/{event}').status_code == 400
    assert auth_client.post(f'/track/{cid}/WHATSAPP_CLICK').status_code == 200
    assert auth_client.post(f'/track/{cid}/PHONE_CLICK').status_code == 200
    with auth_client.application.app_context():
        item = db.session.get(Clothing, cid)
        assert (item.likes, item.interested_count, item.not_interested_count, item.view_count) == (1, 1, 0, 1)
        assert ClothingActivity.query.count() == 5
    assert auth_client.get(f'/admin/clothes/{cid}/activity').status_code == 200
    assert auth_client.get('/admin/').status_code == 200


@pytest.mark.parametrize('payload', [[], {'answer': 1}, {'answer': 'maybe'}, {'answer': ['yes']}])
def test_invalid_interest(auth_client, payload):
    cid, _ = design(auth_client)
    assert auth_client.post(f'/interest/{cid}', json=payload).status_code == 400


def test_achievement_order_validation(auth_client):
    for order in ['abc', '-1', '2147483648']:
        response = auth_client.post('/admin/achievements/new', data={'title': 'Award', 'display_order': order})
        assert response.status_code == 200
        assert b'alert-danger' in response.data
    with auth_client.application.app_context():
        assert Achievement.query.count() == 0
    assert auth_client.post('/admin/achievements/new', data={'title': 'Award', 'display_order': '2'}).status_code == 302


@pytest.mark.parametrize('field,value', [('instagram', 'javascript:alert(1)'), ('facebook', 'ftp://example.com'),
                                         ('tiktok', 'data:text/html,bad'), ('email', 'invalid')])
def test_settings_validation(auth_client, field, value):
    response = auth_client.post('/admin/settings', data={field: value})
    assert response.status_code == 200
    assert b'alert-danger' in response.data


def test_replaced_and_deleted_images_are_cleaned(auth_client):
    for _ in range(2):
        assert auth_client.post('/admin/settings', data={'brand_name': 'Brand', 'logo': png()}).status_code == 302
    assert len(list(Path(auth_client.application.config['UPLOAD_FOLDER']).iterdir())) == 1
    assert auth_client.post('/admin/settings', data={'brand_name': 'Keep logo'}).status_code == 302
    assert len(list(Path(auth_client.application.config['UPLOAD_FOLDER']).iterdir())) == 1
    assert auth_client.post('/admin/achievements/new', data={'title': 'Award', 'image': png()}).status_code == 302
    with auth_client.application.app_context():
        aid = Achievement.query.one().id
    auth_client.post(f'/admin/achievements/{aid}/delete')
    assert len(list(Path(auth_client.application.config['UPLOAD_FOLDER']).iterdir())) == 1
    assert auth_client.post('/admin/showcase/new', data={'design_name': 'Client design', 'image': png()}).status_code == 302
    with auth_client.application.app_context():
        iid = ClientShowcase.query.one().id
    assert b'Client design' not in auth_client.get('/about').data
    auth_client.post(f'/admin/showcase/{iid}/edit', data={'design_name': 'Client design', 'permission_confirmed': 'y', 'image': png()})
    assert b'Client design' in auth_client.get('/about').data
    assert len(list(Path(auth_client.application.config['UPLOAD_FOLDER']).iterdir())) == 2
    auth_client.post(f'/admin/showcase/{iid}/delete')
    assert len(list(Path(auth_client.application.config['UPLOAD_FOLDER']).iterdir())) == 1


def test_commit_failure_removes_new_uploads(auth_client, monkeypatch):
    def fail():
        raise SQLAlchemyError('Simulated database failure')
    monkeypatch.setattr(db.session, 'commit', fail)
    with pytest.raises(SQLAlchemyError):
        auth_client.post('/admin/clothes/new', data={'name': 'Fail', 'availability': 'Available', 'images': png()})
    assert not list(Path(auth_client.application.config['UPLOAD_FOLDER']).iterdir())
    with auth_client.application.app_context():
        assert Clothing.query.count() == 0


def test_failed_delete_preserves_image(auth_client, monkeypatch):
    cid, _ = design(auth_client, images=png())
    def fail():
        raise SQLAlchemyError('Simulated database failure')
    monkeypatch.setattr(db.session, 'commit', fail)
    with pytest.raises(SQLAlchemyError):
        auth_client.post(f'/admin/clothes/{cid}/delete')
    assert len(list(Path(auth_client.application.config['UPLOAD_FOLDER']).iterdir())) == 1
    with auth_client.application.app_context():
        assert db.session.get(Clothing, cid) is not None


def test_csrf_enabled(app):
    import re
    app.config['WTF_CSRF_ENABLED'] = True
    client = app.test_client()
    assert client.post('/visitor/identify', json={}).status_code == 400
    html = client.get('/').text
    token = re.search(r'name="csrf-token" content="([^"]+)"', html).group(1)
    assert client.post('/visitor/identify', json={}, headers={'X-CSRFToken': token}).status_code == 200
    assert client.post('/admin/login', data={'username': 'admin', 'password': 'secret'}).status_code == 400
    assert client.post('/admin/login', data={'username': 'admin', 'password': 'secret', 'csrf_token': token}).status_code == 302


def test_login_rate_limit(client, app):
    with app.app_context():
        limiter.reset()
    for _ in range(10):
        assert client.post('/admin/login', data={'username': 'admin', 'password': 'wrong'}).status_code == 200
    assert client.post('/admin/login', data={'username': 'admin', 'password': 'wrong'}).status_code == 429


def test_categories_and_pagination(auth_client):
    with auth_client.application.app_context():
        for i in range(26):
            db.session.add(Clothing(name=f'Paged {i:02}', slug=f'paged-{i}', category='Women'))
        db.session.commit()
    response = auth_client.get('/collections?category=Women')
    assert b'Next' in response.data
    assert b'Page 1 of 2' in response.data
    assert b'Page 2 of 2' in auth_client.get('/collections?category=Women&page=2').data
    assert b"Men's Statement Wear" not in auth_client.get('/').data
    assert b"Women's Traditional Wear" in auth_client.get('/').data
    assert b'Next' in auth_client.get('/admin/clothes').data
    assert auth_client.get('/collections?page=999').status_code == 404
    assert auth_client.get('/collections?q=' + 'a' * 201).status_code == 400


def production_config(tmp_path):
    return {'SECRET_KEY': 'test-production-key-with-more-than-32-characters',
            'ADMIN_USERNAME': 'tailor', 'ADMIN_PASSWORD': 'long-test-password-123',
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///' + str(tmp_path / 'production.db'),
            'UPLOAD_FOLDER': str(tmp_path / 'uploads'), 'SESSION_COOKIE_SECURE': False,
            'RATELIMIT_ENABLED': False}


@pytest.mark.parametrize('bad', [{'SECRET_KEY': None}, {'SECRET_KEY': 'dev-secret-change-me-in-production'},
                                 {'ADMIN_PASSWORD': 'changeme'}, {'ADMIN_USERNAME': ''}])
def test_production_requires_secrets(tmp_path, bad):
    with pytest.raises(RuntimeError):
        create_app(config_overrides={**production_config(tmp_path), **bad})


def test_migrations_initialization_restart_and_password_reset(tmp_path):
    config = production_config(tmp_path)
    app = create_app(config_overrides=config)
    assert app.test_client().get('/').status_code == 503
    result = app.test_cli_runner().invoke(args=['init-db'])
    assert result.exit_code == 0, result.output
    with app.app_context():
        assert schema_is_current()
        assert Clothing.query.count() == 0
        assert len(inspect(db.engine).get_table_names()) == 9
        from alembic.autogenerate import compare_metadata
        from alembic.migration import MigrationContext
        with db.engine.connect() as connection:
            assert compare_metadata(MigrationContext.configure(connection), db.metadata) == []
    result = app.test_cli_runner().invoke(args=['init-db'])
    assert result.exit_code == 0, result.output
    restarted = create_app(config_overrides=config)
    assert restarted.test_client().get('/').status_code == 200
    with restarted.app_context():
        assert Clothing.query.count() == 0
    result = restarted.test_cli_runner().invoke(args=['reset-admin-password'], input='another-long-password\nanother-long-password\n')
    assert result.exit_code == 0, result.output
    with restarted.app_context():
        from app.models import Admin
        assert Admin.query.one().check_password('another-long-password')


def test_adopt_legacy_database_preserves_data(app):
    with app.app_context():
        db.session.add(Clothing(name='Legacy', slug='legacy'))
        db.session.commit()
        db.session.execute(text('ALTER TABLE clothing DROP COLUMN featured'))
        db.session.execute(text('ALTER TABLE clothing ADD COLUMN featured BOOLEAN DEFAULT 0'))
        db.session.execute(text('UPDATE clothing SET featured = NULL'))
        db.session.execute(text('ALTER TABLE site_settings DROP COLUMN designer_name'))
        db.session.execute(text('ALTER TABLE visitors DROP COLUMN newsletter_subscribed'))
        db.session.commit()
        upgrade_database()
        assert schema_is_current()
        item = Clothing.query.filter_by(slug='legacy').one()
        assert item.name == 'Legacy'
        assert item.featured is False
        assert not next(c for c in inspect(db.engine).get_columns('clothing') if c['name'] == 'featured')['nullable']
        assert 'designer_name' in {c['name'] for c in inspect(db.engine).get_columns('site_settings')}


def test_secure_cookie_configuration(app):
    app.config['SESSION_COOKIE_SECURE'] = True
    response = app.test_client().post('/visitor/identify', json={})
    cookie = response.headers['Set-Cookie']
    assert 'Secure' in cookie and 'HttpOnly' in cookie and 'SameSite=Lax' in cookie


def test_existing_unsafe_social_links_are_not_rendered(auth_client):
    with auth_client.application.app_context():
        SiteSettings.query.first().instagram = 'javascript:alert(1)'
        db.session.commit()
    assert b'javascript:alert(1)' not in auth_client.get('/').data


def test_profile_image_replacement(auth_client):
    for _ in range(2):
        assert auth_client.post('/admin/about', data={'designer_name': 'Tailor', 'designer_image': png()}).status_code == 302
    assert len(list(Path(auth_client.application.config['UPLOAD_FOLDER']).iterdir())) == 1
    assert auth_client.post('/admin/about', data={'designer_name': 'Tailor'}).status_code == 302
    assert len(list(Path(auth_client.application.config['UPLOAD_FOLDER']).iterdir())) == 1


def test_shared_image_is_preserved(auth_client):
    cid, _ = design(auth_client, images=png())
    with auth_client.application.app_context():
        image_url = db.session.get(Clothing, cid).primary_image.image_url
        db.session.add(Achievement(title='Shared image', image_url=image_url))
        db.session.commit()
    assert auth_client.post(f'/admin/clothes/{cid}/delete').status_code == 302
    assert len(list(Path(auth_client.application.config['UPLOAD_FOLDER']).iterdir())) == 1


@pytest.mark.parametrize('price', ['sNaN', 'NaN', 'Infinity', '-Infinity', '-1', '10000000000'])
def test_nonfinite_or_out_of_range_prices_are_rejected(auth_client, price):
    response = auth_client.post('/admin/clothes/new', data={
        'name': 'Invalid price', 'availability': 'Available', 'price': price})
    assert response.status_code == 200
    assert b'alert-danger' in response.data
    with auth_client.application.app_context():
        assert Clothing.query.count() == 0


def test_maximum_supported_price(auth_client):
    cid, _ = design(auth_client, price='9999999999.99')
    with auth_client.application.app_context():
        from decimal import Decimal
        assert db.session.get(Clothing, cid).price == Decimal('9999999999.99')


def test_health_check(client, app, monkeypatch):
    assert client.get('/healthz').get_json() == {'status': 'ok'}
    def unavailable(*args, **kwargs):
        raise SQLAlchemyError('Database unavailable')
    monkeypatch.setattr(db.session, 'execute', unavailable)
    response = client.get('/healthz')
    assert response.status_code == 503
    assert response.get_json() == {'status': 'unavailable'}


@pytest.mark.parametrize('trust_proxy', [False, True])
def test_proxy_headers_are_opt_in_and_use_trusted_last_hop(tmp_path, trust_proxy):
    from flask import request
    app = create_app('testing', {
        'TRUST_PROXY_HEADERS': trust_proxy,
        'UPLOAD_FOLDER': str(tmp_path / 'uploads'),
    })
    @app.get('/test-proxy')
    def proxy_details():
        return {'address': request.remote_addr, 'secure': request.is_secure, 'host': request.host}
    response = app.test_client().get('/test-proxy', headers={
        'X-Forwarded-For': '192.0.2.1, 198.51.100.2',
        'X-Forwarded-Proto': 'https',
        'X-Forwarded-Host': 'untrusted.example',
    })
    assert response.json == {
        'address': '198.51.100.2' if trust_proxy else '127.0.0.1',
        'secure': trust_proxy,
        'host': 'localhost',
    }


def test_proxy_clients_get_separate_login_limits(tmp_path):
    app = create_app('testing', {
        'TRUST_PROXY_HEADERS': True,
        'UPLOAD_FOLDER': str(tmp_path / 'uploads'),
    })
    client = app.test_client()
    first_headers = {'X-Forwarded-For': 'spoofed, 198.51.100.1'}
    for _ in range(10):
        assert client.post('/admin/login', data={'username': 'missing', 'password': 'wrong'}, headers=first_headers).status_code == 200
    assert client.post('/admin/login', data={'username': 'missing', 'password': 'wrong'}, headers=first_headers).status_code == 429
    assert client.post('/admin/login', data={'username': 'missing', 'password': 'wrong'}, headers={'X-Forwarded-For': 'spoofed, 198.51.100.2'}).status_code == 200


def test_recover_admin_after_environment_username_change(tmp_path):
    from app.models import Admin
    config = production_config(tmp_path)
    app = create_app(config_overrides=config)
    assert app.test_cli_runner().invoke(args=['init-db']).exit_code == 0
    changed = create_app(config_overrides={**config, 'ADMIN_USERNAME': 'renamed-tailor'})
    result = changed.test_cli_runner().invoke(
        args=['reset-admin-password', '--username', 'tailor', '--rename-to-configured'],
        input='recovered-password-123\nrecovered-password-123\n',
    )
    assert result.exit_code == 0, result.output
    with changed.app_context():
        admin = Admin.query.one()
        assert admin.username == 'renamed-tailor'
        assert admin.check_password('recovered-password-123')
