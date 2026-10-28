from app.models import Clothing


def test_homepage(client):
    r = client.get('/')
    assert r.status_code == 200


def test_admin_login_ok(client):
    r = client.post('/admin/login', data={'username': 'admin', 'password': 'secret'}, follow_redirects=True)
    assert r.status_code == 200
    assert b'Dashboard' in r.data


def test_admin_login_bad(client):
    r = client.post('/admin/login', data={'username': 'admin', 'password': 'wrong'}, follow_redirects=True)
    assert b'Invalid' in r.data


def test_unauthorized_admin(client):
    r = client.get('/admin/')
    assert r.status_code in (302, 401, 403)
def test_create_clothing(auth_client):
    data = {
        'name': 'Royal Blue Senator',
        'price': '45000',
        'category': 'Senator',
        'description': 'Nice',
        'material': 'Cashmere',
        'sizes': 'M, L, XL',
        'colors': 'Blue',
        'availability': 'Available',
    }
    r = auth_client.post('/admin/clothes/new', data=data, follow_redirects=True)
    assert r.status_code == 200


def test_public_display_after_create(auth_client, client):
    data = {
        'name': 'Royal Blue Senator',
        'price': '45000',
        'category': 'Senator',
        'description': 'Nice',
        'material': 'Cashmere',
        'sizes': 'M, L, XL',
        'colors': 'Blue',
        'availability': 'Available',
    }
    auth_client.post('/admin/clothes/new', data=data)
    r = client.get('/')
    assert b'Royal Blue Senator' in r.data


def test_clothing_detail(client, auth_client):
    auth_client.post('/admin/clothes/new', data={'name': 'Detail Item', 'price': '1000', 'availability': 'Available'})
    from app.models import Clothing
    with auth_client.application.app_context():
        c = Clothing.query.filter_by(name='Detail Item').first()
        slug = c.slug
    r = client.get(f'/clothes/{slug}')
    assert r.status_code == 200
    assert b'Detail Item' in r.data


def test_like(client, auth_client):
    auth_client.post('/admin/clothes/new', data={'name': 'Like Item', 'price': '1000', 'availability': 'Available'})
    from app.models import Clothing
    with auth_client.application.app_context():
        c = Clothing.query.filter_by(name='Like Item').first()
        cid = c.id
    r = client.post(f'/like/{cid}')
    assert r.status_code == 200
    assert r.get_json()['likes'] == 1
    r2 = client.post(f'/like/{cid}')
    assert r2.get_json()['likes'] == 1


def test_interest_yes(client, auth_client):
    auth_client.post('/admin/clothes/new', data={'name': 'Interest Item', 'price': '1000', 'availability': 'Available'})
    from app.models import Clothing
    with auth_client.application.app_context():
        c = Clothing.query.filter_by(name='Interest Item').first()
        cid = c.id
        slug = c.slug
    r = client.post(f'/interest/{cid}', json={'answer': 'yes'})
    assert r.status_code == 200
    data = r.get_json()
    assert 'redirect' in data
    assert slug in data['redirect']


def test_interest_no(client, auth_client):
    auth_client.post('/admin/clothes/new', data={'name': 'No Item', 'price': '1000', 'availability': 'Available'})
    from app.models import Clothing
    with auth_client.application.app_context():
        c = Clothing.query.filter_by(name='No Item').first()
        cid = c.id
    r = client.post(f'/interest/{cid}', json={'answer': 'no'})
    assert r.status_code == 200
    assert r.get_json().get('ok') is True


def test_search_filter(client, auth_client):
    auth_client.post('/admin/clothes/new', data={'name': 'Blue Shirt', 'category': 'Men', 'price': '1000', 'availability': 'Available'})
    auth_client.post('/admin/clothes/new', data={'name': 'Red Dress', 'category': 'Women', 'price': '2000', 'availability': 'Available'})
    r = client.get('/collections?q=Blue')
    assert b'Blue Shirt' in r.data
    assert b'Red Dress' not in r.data
    r2 = client.get('/collections?category=Women')
    assert b'Red Dress' in r2.data


def test_edit_and_sold(auth_client, client):
    auth_client.post('/admin/clothes/new', data={'name': 'Sold Item', 'price': '1000', 'availability': 'Available'})
    from app.models import Clothing
    with auth_client.application.app_context():
        c = Clothing.query.filter_by(name='Sold Item').first()
        cid = c.id
    auth_client.post(f'/admin/clothes/{cid}/edit', data={'name': 'Sold Item', 'price': '900', 'availability': 'Sold'})
    r = client.get('/collections')
    assert b'SOLD' in r.data


def test_delete(auth_client):
    auth_client.post('/admin/clothes/new', data={'name': 'Del Item', 'price': '1000', 'availability': 'Available'})
    from app.models import Clothing
    with auth_client.application.app_context():
        c = Clothing.query.filter_by(name='Del Item').first()
        cid = c.id
    r = auth_client.post(f'/admin/clothes/{cid}/delete', follow_redirects=True)
    assert r.status_code == 200
    with auth_client.application.app_context():
        assert Clothing.query.filter_by(id=cid).first() is None


def test_settings(auth_client, client):
    data = {
        'brand_name': 'My Brand',
        'phone': '08012345678',
        'whatsapp': '08012345678',
        'bank_name': 'BankX',
        'account_name': 'Fashion Brand',
        'account_number': '1234567890',
        'about': 'About us',
    }
    r = auth_client.post('/admin/settings', data=data, follow_redirects=True)
    assert r.status_code == 200
    r3 = client.get('/')
    assert b'My Brand' in r3.data
