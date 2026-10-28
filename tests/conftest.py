import pytest
from app import create_app, db


@pytest.fixture
def app(tmp_path):
    app = create_app('testing', {
        'UPLOAD_FOLDER': str(tmp_path / 'uploads'),
        'ADMIN_PASSWORD': 'secret',
    })
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client):
    response = client.post('/admin/login', data={'username': 'admin', 'password': 'secret'})
    assert response.status_code == 302
    return client
