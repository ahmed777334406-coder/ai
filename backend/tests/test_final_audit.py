from unittest.mock import patch
from app.models import Listing, ListingState
from app.database import get_db

ITEM = {"status":"FOUND","title":"Blue wallet","description":"Blue wallet silver clasp library","category":"Wallets"}

def start(client):
    client.cookies.clear()
    assert client.post('/api/v1/auth/session').status_code == 200

def test_search_excludes_unrelated_recovered_and_moderated(client):
    start(client)
    item=client.post('/api/v1/listings',json=ITEM).json()
    assert client.post('/api/v1/ai/search',json={'query':'Blue wallet'}).json()['results']
    assert client.post('/api/v1/ai/search',json={'query':'zzzzqqq'}).json()['results']==[]
    for state in [ListingState.RECOVERED,ListingState.UNDER_REVIEW,ListingState.CLOSED]:
        db=next(client.app.dependency_overrides[get_db]())
        db.get(Listing,item['id']).state=state;db.commit();db.close()
        result=client.post('/api/v1/ai/assistant',json={'query':'Blue wallet'}).json()
        assert result['retrieved_records']==[]
        assert result['answer_provider']=='database_only_no_results'

def test_same_owner_reports_never_match(client):
    start(client)
    client.post('/api/v1/listings',json=ITEM)
    lost=client.post('/api/v1/listings',json={**ITEM,'status':'LOST'}).json()
    assert client.post(f"/api/v1/ai/match/{lost['id']}").json()['matches']==[]
    assert client.get('/api/v1/matches').json()==[]

def test_whitespace_report_rejected(client):
    start(client)
    assert client.post('/api/v1/listings',json={**ITEM,'title':'   '}).status_code==422

def test_gemini_error_fallback_is_honest(client):
    start(client)
    with patch('app.services.gemini.gemini_service._get_client',return_value=None):
        result=client.post('/api/v1/ai/analyze',json={'query':'黑色耳机'}).json()
        assert result['provider']=='rule_fallback' and not result['gemini_live']
        assert result['analysis']['category']=='Electronics'

def test_reused_session_is_not_cacheable(client):
    start(client)
    assert client.post('/api/v1/auth/session').headers['cache-control']=='no-store'

def test_retry_key_is_idempotent_and_scoped_to_visitor(client):
    start(client)
    payload={**ITEM,'client_request_id':'isolated-test-request-1234'}
    first=client.post('/api/v1/listings',json=payload)
    retry=client.post('/api/v1/listings',json=payload)
    assert first.status_code==201 and retry.status_code==201
    assert first.json()['id']==retry.json()['id']
    assert len(client.get('/api/v1/listings/mine').json())==1
    start(client)
    other=client.post('/api/v1/listings',json=payload)
    assert other.json()['id']!=first.json()['id']
