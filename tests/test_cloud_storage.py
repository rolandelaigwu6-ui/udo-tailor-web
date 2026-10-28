import io
import json
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app import create_app, db
from app.models import Clothing, Achievement
from app.storage import initialize_bucket
from test_fixes import png, design


@pytest.fixture
def cloud(app, monkeypatch):
    app.config.update(STORAGE_BACKEND='supabase', SUPABASE_URL='https://example.supabase.co',
                      SUPABASE_SERVICE_ROLE_KEY='test-server-key-not-real', SUPABASE_STORAGE_BUCKET='tailor-images')
    calls = []
    def request(req, timeout):
        calls.append(req)
        return io.BytesIO(b'{}')
    monkeypatch.setattr('app.storage.urlopen', request)
    return calls


def test_cloud_upload_and_delete(auth_client, cloud):
    cid, slug = design(auth_client, images=png())
    assert cloud[0].get_method() == 'POST'
    assert cloud[0].full_url.startswith('https://example.supabase.co/storage/v1/object/tailor-images/')
    assert cloud[0].get_header('Authorization') == 'Bearer test-server-key-not-real'
    assert cloud[0].get_header('Content-type') == 'image/png'
    assert cloud[0].data.startswith(b'\x89PNG')
    assert not list(Path(auth_client.application.config['UPLOAD_FOLDER']).iterdir())
    response = auth_client.get('/clothes/' + slug)
    assert b'/storage/v1/object/public/tailor-images/' in response.data
    assert b'test-server-key-not-real' not in response.data
    with auth_client.application.app_context():
        path = db.session.get(Clothing, cid).primary_image.image_url
        assert path.startswith('supabase/')
    assert auth_client.post(f'/admin/clothes/{cid}/delete').status_code == 302
    assert cloud[-1].get_method() == 'DELETE'
    assert json.loads(cloud[-1].data) == {'prefixes': [path.removeprefix('supabase/')]}


def test_failed_database_commit_cleans_cloud_upload(auth_client, cloud, monkeypatch):
    def fail():
        raise SQLAlchemyError('Failure')
    monkeypatch.setattr(db.session, 'commit', fail)
    with pytest.raises(SQLAlchemyError):
        auth_client.post('/admin/clothes/new', data={'name': 'Fail', 'availability': 'Available', 'images': png()})
    assert [request.get_method() for request in cloud] == ['POST', 'DELETE']
    with auth_client.application.app_context():
        assert Clothing.query.count() == 0


def test_storage_failure_is_visible_without_leaking_secrets(auth_client, cloud, monkeypatch, caplog):
    def fail(*args, **kwargs):
        raise URLError('test-server-key-not-real')
    monkeypatch.setattr('app.storage.urlopen', fail)
    response = auth_client.post('/admin/clothes/new', data={'name': 'Fail', 'availability': 'Available', 'images': png()})
    assert response.status_code == 502
    assert b'test-server-key-not-real' not in response.data
    assert 'test-server-key-not-real' not in caplog.text
    with auth_client.application.app_context():
        assert Clothing.query.count() == 0


def test_shared_cloud_image_is_preserved(auth_client, cloud):
    cid, _ = design(auth_client, images=png())
    with auth_client.application.app_context():
        path = db.session.get(Clothing, cid).primary_image.image_url
        db.session.add(Achievement(title='Shared', image_url=path))
        db.session.commit()
    auth_client.post(f'/admin/clothes/{cid}/delete')
    assert len(cloud) == 1


def test_initialize_new_bucket(app, cloud, monkeypatch):
    calls = []
    def request(req, timeout):
        calls.append(req)
        if req.get_method() == 'GET':
            raise HTTPError(req.full_url, 404, 'Not found', {}, None)
        return io.BytesIO(b'{}')
    monkeypatch.setattr('app.storage.urlopen', request)
    result = app.test_cli_runner().invoke(args=['init-storage'])
    assert result.exit_code == 0, result.output
    assert [request.get_method() for request in calls] == ['GET', 'POST']
    data = json.loads(calls[-1].data)
    assert data['public'] is True
    assert data['id'] == 'tailor-images'
    assert data['file_size_limit'] == app.config['MAX_CONTENT_LENGTH']


def test_existing_private_bucket_is_not_made_public(app, cloud, monkeypatch):
    calls = []
    def request(req, timeout):
        calls.append(req)
        return io.BytesIO(b'{"public":false}')
    monkeypatch.setattr('app.storage.urlopen', request)
    with app.app_context(), pytest.raises(RuntimeError, match='dedicated catalogue-image bucket'):
        initialize_bucket()
    assert len(calls) == 1


def test_existing_public_bucket_is_reused(app, cloud, monkeypatch):
    monkeypatch.setattr('app.storage.urlopen', lambda *args, **kwargs: io.BytesIO(b'{"public":true}'))
    assert app.test_cli_runner().invoke(args=['init-storage']).exit_code == 0


@pytest.mark.parametrize('overrides', [
    {'STORAGE_BACKEND': 'unknown'},
    {'STORAGE_BACKEND': 'supabase'},
    {'STORAGE_BACKEND': 'supabase', 'SUPABASE_URL': 'http://example.supabase.co', 'SUPABASE_SERVICE_ROLE_KEY': 'test'},
    {'REQUIRE_EXTERNAL_STORAGE': True},
])
def test_bad_storage_configuration_fails_early(tmp_path, overrides):
    with pytest.raises(RuntimeError):
        create_app('testing', {'UPLOAD_FOLDER': str(tmp_path / 'uploads'), **overrides})


@pytest.mark.parametrize('scheme', ['postgres://', 'postgresql://', 'postgresql+psycopg://'])
def test_postgresql_url_normalization_and_ssl(scheme):
    from config import normalize_database_url
    from sqlalchemy.engine import make_url
    result = make_url(normalize_database_url(scheme + 'postgres:encoded%40password@pooler.example:5432/postgres'))
    assert result.drivername == 'postgresql+psycopg'
    assert result.password == 'encoded@password'
    assert result.query['sslmode'] == 'require'


def test_storage_gateway_missing_bucket_response(app, cloud, monkeypatch):
    calls = []
    def request(req, timeout):
        calls.append(req)
        if req.get_method() == 'GET':
            raise HTTPError(req.full_url, 400, 'Error', {}, io.BytesIO(b'{"statusCode":"404"}'))
        return io.BytesIO(b'{}')
    monkeypatch.setattr('app.storage.urlopen', request)
    assert app.test_cli_runner().invoke(args=['init-storage']).exit_code == 0
    assert [request.get_method() for request in calls] == ['GET', 'POST']


def test_storage_auth_failure_does_not_create_bucket(app, cloud, monkeypatch):
    calls = []
    def request(req, timeout):
        calls.append(req)
        raise HTTPError(req.full_url, 403, 'Denied', {}, None)
    monkeypatch.setattr('app.storage.urlopen', request)
    with app.app_context(), pytest.raises(RuntimeError, match='Could not initialize'):
        initialize_bucket()
    assert len(calls) == 1
