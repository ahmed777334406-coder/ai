from app.database import get_db
from app.models import User, UserRole
from app.security import hash_password

HEADER = {"X-SmartFind-Request":"1"}
ITEM = {"status":"FOUND", "title":"蓝色钱包 Blue wallet", "description":"Blue wallet found at the campus library", "category":"Wallets", "color":"Blue", "private_identifiers":"secret mark"}


def start(client):
    result = client.post('/api/v1/auth/session')
    assert result.status_code == 200
    return result


def test_cookie_is_http_only_persistent_and_stable(client):
    first = start(client)
    cookie = first.headers['set-cookie'].lower()
    assert 'httponly' in cookie and 'samesite=lax' in cookie and 'max-age=2592000' in cookie
    assert 'access_token' not in first.json()
    assert start(client).json()['id'] == first.json()['id']
    assert client.get('/api/v1/auth/me').json()['id'] == first.json()['id']


def test_cookie_visitor_isolation_and_filters(client):
    owner = start(client).json()['id']
    found = client.post('/api/v1/listings', json=ITEM).json()
    assert client.get('/api/v1/listings/mine').json()[0]['id'] == found['id']
    assert client.get('/api/v1/listings?category=Wallets&color=Blue').json()['total'] == 1
    assert client.get('/api/v1/listings?color=Red').json()['total'] == 0
    owner_cookie = client.cookies.get('smartfind_visitor')
    client.cookies.clear()
    assert start(client).json()['id'] != owner
    assert client.get('/api/v1/listings/mine').json() == []
    assert client.patch(f"/api/v1/listings/{found['id']}", json={'title':'Stolen update'}).status_code == 403
    assert client.delete(f"/api/v1/listings/{found['id']}").status_code == 403
    claim = client.post('/api/v1/claims', json={'listing_id':found['id'], 'verification_details':'My private ownership evidence'} )
    assert claim.status_code == 201
    claim_id = claim.json()['id']
    assert len(client.get('/api/v1/claims').json()) == 1
    client.cookies.clear()
    client.cookies.set('smartfind_visitor', owner_cookie)
    assert client.get('/api/v1/claims').json() == []
    assert client.get(f'/api/v1/claims/{claim_id}').status_code == 403
    assert client.get('/api/v1/admin/dashboard').status_code == 403


def test_csrf_and_tampered_sessions(client):
    start(client)
    assert client.post('/api/v1/listings', headers={'X-SmartFind-Request':''}, json=ITEM).status_code == 403
    assert client.post('/api/v1/listings', headers={'Origin':'https://evil.invalid'}, json=ITEM).status_code == 403
    client.cookies.clear()
    client.cookies.set('smartfind_visitor', 'tampered')
    assert client.get('/api/v1/auth/me').status_code == 401
    assert start(client).status_code == 200


def test_production_cookie_flags(client):
    from unittest.mock import patch
    with patch('app.api.routes.auth.settings.environment', 'production'):
        assert 'Secure' in start(client).headers['set-cookie']


def test_admin_login_requires_individually_provisioned_admin(client):
    start(client)
    db = next(client.app.dependency_overrides[get_db]())
    admin = User(email='reviewer@example.edu', full_name='Reviewer', password_hash=hash_password('UniqueReviewerPassword!'), role=UserRole.ADMIN)
    db.add(admin); db.commit(); db.close()
    response = client.post('/api/v1/auth/login', json={'email':'reviewer@example.edu','password':'UniqueReviewerPassword!'})
    assert response.status_code == 200
    headers={'Authorization':'Bearer '+response.json()['access_token']}
    assert client.get('/api/v1/admin/dashboard',headers=headers).status_code == 200


def test_cookie_logout_revokes_session(client):
    start(client)
    token=client.cookies.get('smartfind_visitor')
    assert client.post('/api/v1/auth/logout').status_code == 200
    client.cookies.set('smartfind_visitor', token, domain='testserver.local', path='/')
    assert client.get('/api/v1/auth/me').status_code == 401
    start(client)
    assert client.cookies.get('smartfind_visitor') != token
