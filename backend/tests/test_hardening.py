from datetime import datetime, timezone
from unittest.mock import patch
from sqlalchemy.exc import OperationalError
from app.models import EmbeddingVector
from app.config import Settings
from test_api import register


def test_logout_revokes_token_and_requires_authentication(client):
    token = register(client)
    headers = {"Authorization": f"Bearer {token}"}
    assert client.post('/api/v1/auth/logout').status_code == 401
    assert client.post('/api/v1/auth/logout', headers=headers).status_code == 200
    assert client.get('/api/v1/auth/me', headers=headers).status_code == 401
    assert client.post('/api/v1/listings', headers=headers, json={}).status_code == 401
    login = client.post('/api/v1/auth/login', json={"email":"student@example.edu", "password":"SecurePass123!"})
    assert login.status_code == 401


def test_profile_updates_persist_and_cannot_change_role(client):
    token = register(client)
    headers = {"Authorization": f"Bearer {token}"}
    updated = client.patch('/api/v1/auth/me', headers=headers, json={"full_name":"Fictional Student", "preferred_language":"zh", "role":"ADMIN"})
    assert updated.status_code == 200
    profile = client.get('/api/v1/auth/me', headers=headers).json()
    assert profile['full_name'] == 'Fictional Student'
    assert profile['preferred_language'] == 'zh'
    assert profile['role'] == 'STUDENT'
    assert client.patch('/api/v1/auth/me', headers=headers, json={"full_name":None}).status_code == 422
    assert client.patch('/api/v1/auth/me', headers=headers, json={"full_name":"   "}).status_code == 422


def test_readiness_returns_service_unavailable_when_database_fails(client):
    with patch('app.main.engine.connect', side_effect=OperationalError('SELECT 1', {}, Exception('offline'))):
        response = client.get('/health/ready')
    assert response.status_code == 503
    assert response.json()['status'] == 'not_ready'
    assert 'offline' not in response.text


def test_railway_postgres_urls_use_installed_driver():
    config = Settings(database_url='postgresql://user:password@database:5432/smartfind', _env_file=None)
    assert config.database_url == 'postgresql+psycopg://user:password@database:5432/smartfind'


def test_pgvector_results_convert_to_plain_lists():
    import numpy as np
    result = EmbeddingVector(3).process_result_value(np.array([0.1, 0.2, 0.3]), None)
    assert isinstance(result, list) and len(result) == 3


def test_public_listings_do_not_disclose_student_names(client):
    token = register(client)
    created = client.post('/api/v1/listings', headers={"Authorization":f"Bearer {token}"}, json={"status":"LOST", "title":"Black backpack", "description":"Black backpack lost near the library", "category":"Bags"})
    assert created.status_code == 201
    assert 'Test Student' not in client.get('/api/v1/listings').text


def test_rejected_claim_reopens_item_and_notifies_student(client):
    from app.models import User, UserRole
    from app.database import get_db
    from app.security import hash_password, create_access_token
    owner = register(client, 'claim-owner@example.edu')
    finder = register(client, 'claim-finder@example.edu')
    found = client.post('/api/v1/listings', headers={'Authorization':f'Bearer {finder}'}, json={'status':'FOUND','title':'Fictional wallet','description':'Blue wallet found in the cafeteria','category':'Wallets'}).json()
    claim = client.post('/api/v1/claims', headers={'Authorization':f'Bearer {owner}'}, json={'listing_id':found['id'],'verification_details':'Fictional identifying details for verification.'}).json()
    with next(client.app.dependency_overrides[get_db]()) as db:
        admin=User(email='private-reviewer@example.edu',full_name='Test Reviewer',password_hash=hash_password('PrivateTestPassword!'),role=UserRole.ADMIN)
        db.add(admin);db.commit();db.refresh(admin)
        token=create_access_token(admin.id,admin.role.value)
    response=client.patch(f"/api/v1/admin/claims/{claim['id']}", headers={'Authorization':f'Bearer {token}'},json={'status':'REJECTED','admin_note':'Identifying details do not match.'})
    assert response.status_code == 200
    assert client.get(f"/api/v1/listings/{found['id']}").json()['state']=='OPEN'
    notifications=client.get('/api/v1/notifications',headers={'Authorization':f'Bearer {owner}'}).json()
    assert any(n['kind']=='CLAIM_REJECTED' for n in notifications)
    assert client.patch(f"/api/v1/admin/claims/{claim['id']}",headers={'Authorization':f'Bearer {token}'},json={'status':'APPROVED'}).status_code==409


def test_listing_patch_rejects_invalid_required_fields(client):
    token=register(client)
    headers={'Authorization':f'Bearer {token}'}
    item=client.post('/api/v1/listings',headers=headers,json={'status':'LOST','title':'Fictional key ring','description':'A silver key ring lost near the library','category':'Keys'}).json()
    for change in ({'title':None},{'description':''},{'category':'  '},{'title':'x'*181}):
        assert client.patch(f"/api/v1/listings/{item['id']}",headers=headers,json=change).status_code==422


def test_login_rate_limit_is_enforced(client):
    for _ in range(12):
        assert client.post('/api/v1/auth/login',json={'email':'missing@example.edu','password':'incorrect'}).status_code==401
    assert client.post('/api/v1/auth/login',json={'email':'missing@example.edu','password':'incorrect'}).status_code==429
