import os
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

load_dotenv(os.path.join(BASE_DIR, '.env'))


def normalize_database_url(value):
    if value.startswith(('postgres://', 'postgresql://', 'postgresql+psycopg://')):
        from sqlalchemy.engine import make_url
        value = value.replace('postgres://', 'postgresql+psycopg://', 1).replace('postgresql://', 'postgresql+psycopg://', 1)
        url = make_url(value)
        if 'sslmode' not in url.query:
            url = url.update_query_dict({'sslmode': 'require'})
        return url.render_as_string(hide_password=False)
    return value


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'tailor.db')
    SQLALCHEMY_DATABASE_URI = normalize_database_url(SQLALCHEMY_DATABASE_URI)
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True}
    REQUIRE_EXTERNAL_STORAGE = os.environ.get('REQUIRE_EXTERNAL_STORAGE', '0') == '1'
    STORAGE_BACKEND = os.environ.get('STORAGE_BACKEND', 'local')
    SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
    SUPABASE_SERVICE_ROLE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')
    SUPABASE_STORAGE_BUCKET = os.environ.get('SUPABASE_STORAGE_BUCKET', 'tailor-images')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or os.path.join(BASE_DIR, 'app', 'static', 'uploads')
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    WTF_CSRF_ENABLED = True
    TRUST_PROXY_HEADERS = os.environ.get('TRUST_PROXY_HEADERS', '0') == '1'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', '1') == '1'
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URI = os.environ.get('RATELIMIT_STORAGE_URI', 'memory://')
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')


class TestConfig(Config):
    REQUIRE_EXTERNAL_STORAGE = False
    STORAGE_BACKEND = 'local'
    SUPABASE_URL = ''
    SUPABASE_SERVICE_ROLE_KEY = ''
    TESTING = True
    TRUST_PROXY_HEADERS = False
    SECRET_KEY = "testing-only-secret-not-for-deployment"
    ADMIN_USERNAME = "admin"
    ADMIN_PASSWORD = "testing-only-password"
    SESSION_COOKIE_SECURE = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'instance', 'test_uploads')
