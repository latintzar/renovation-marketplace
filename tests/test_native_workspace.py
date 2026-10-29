"""Real original route/domain functions over local SQL storage and cookie authority."""
from pathlib import Path
import stat, sys
import pytest
from fastapi.testclient import TestClient
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'apps/scope/product/backend'), str(ROOT / 'packages/core/src'), str(ROOT / 'packages/payments/src')]
from local_mode.server import create_app
from payments.finance import compute_quote_financials

@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv('SUPABASE_URL', 'http://local.marketplace.invalid')
    monkeypatch.setenv('SUPABASE_SERVICE_ROLE_KEY', 'local-internal-transport-only')
    return create_app(tmp_path / 'private', prefix='/app')

def session(client):
    return client.get('/app/api/local/session').json()

def quote(client):
    return client.get('/app/v1/canvas/sample-quote').json()

def info(client):
    user = session(client)['user']
    return client.get('/app/v1/contractor/by-auth-user/' + user['id']).json()

def test_original_route_functions_and_quote_financials(app):
    with TestClient(app) as client:
        actor = info(client)
        data = quote(client)
        assert data['amount_total_cents'] == 819000 and data['scope'] == data['quote_data']
        scopes = client.get('/app/v1/quotes', params={'contractor_id': actor['contractor_id']}).json()
        assert scopes['quotes'] == scopes['scopes'] and len(scopes['scopes']) == 2
        changed = {**data['scope'], 'title': 'Saved private quote', 'materials_upfront': 1900}
        assert client.post('/app/v1/quote/update', json={'token': 'sample-quote', 'scope_data': changed, 'contractor_id': actor['contractor_id']}).status_code == 200
        saved = quote(client)
        assert saved['scope']['title'] == 'Saved private quote' and saved['amount_total_cents'] == compute_quote_financials(changed).amount_total_cents
        assert client.post('/app/v1/quote/update', json={'token': 'sample-project', 'quote_data': changed, 'contractor_id': actor['contractor_id']}).status_code == 409

def test_messages_proof_and_cross_visitor_isolation(app):
    with TestClient(app) as a, TestClient(app) as b:
        actor = info(a)
        other = info(b)
        assert actor['contractor_id'] != other['contractor_id']
        response = a.post('/app/v1/messages/send', json={'quote_token': 'sample-project', 'sender_role': 'homeowner', 'sender_id': 'forged', 'body': 'Please check the first-fix photos.'})
        assert response.status_code == 200
        row = response.json()['message']
        assert row['sender_role'] == 'contractor' and row['sender_id'] == actor['contractor_id']
        assert len(a.get('/app/v1/messages/sample-project').json()) == 1 and b.get('/app/v1/messages/sample-project').json() == []
        assert b.get('/app/v1/quotes', params={'contractor_id': actor['contractor_id']}).json()['quotes'] == []
        assert b.post('/app/v1/quote/update', json={'token': 'sample-quote', 'scope_data': quote(b)['scope'], 'contractor_id': actor['contractor_id']}).status_code == 403
        assert a.post('/app/v1/projects/sample-project/milestones/1/proof', json={'photos': [], 'note': 'Waterproofing ready for inspection.'}).status_code == 200
        assert a.get('/app/v1/canvas/sample-project').json()['milestones'][1]['status'] == 'proof_submitted'
        assert b.get('/app/v1/canvas/sample-project').json()['milestones'][1]['status'] == 'pending'

def test_sql_state_survives_application_restart(app):
    with TestClient(app) as client:
        actor = info(client)
        changed = {**quote(client)['scope'], 'title': 'Restart persistence'}
        assert client.post('/app/v1/quote/update', json={'token': 'sample-quote', 'quote_data': changed, 'contractor_id': actor['contractor_id']}).status_code == 200
        cookies = client.cookies
    with TestClient(create_app(app.state.store.state, prefix='/app')) as restarted:
        restarted.cookies.update(cookies)
        assert quote(restarted)['scope']['title'] == 'Restart persistence'
    assert stat.S_IMODE(app.state.store.state.stat().st_mode) == 448 and stat.S_IMODE(app.state.store.path.stat().st_mode) == 384

def test_provider_payments_csrf_body_cap_and_private_routes(app):
    with TestClient(app) as client:
        session(client)
        for path in ['/v1/chat', '/v1/projects/sample-project/milestones/0/release', '/v1/payment/create-checkout', '/api/profile-import', '/v1/projects/example.id.png/milestones/0/release']:
            assert client.post('/app' + path, json={}).status_code == 503
        assert client.post('/app/v1/messages/send', json={}, headers={'Origin': 'https://foreign.example'}).status_code == 403
        assert client.post('/app/v1/messages/send', json={}, headers={'Sec-Fetch-Site': 'cross-site'}).status_code == 403
        assert client.post('/app/v1/messages/send', content=b'x' * 32769).status_code == 413
        assert client.get('/v1/canvas/sample-quote').status_code == 404
        assert client.get('/app/rest/v1/quotes').status_code == 404

def test_secure_cookie_is_private_and_scoped(app):
    secure = create_app(app.state.store.state, prefix='/apps/renovation-marketplace', public_origin='https://preview.example.test')
    with TestClient(secure, base_url='https://preview.example.test') as client:
        response = client.get('/apps/renovation-marketplace/api/local/session')
        cookie = response.headers['set-cookie']
        assert all((value in cookie for value in ['HttpOnly', 'Secure', 'SameSite=lax', 'Path=/apps/renovation-marketplace/']))
        assert 'renovation_workspace_session' not in response.text

def test_homeowner_entry_uses_native_project_party(app):
    with TestClient(app) as client:
        session(client)
        client.get('/app/my-projects?local_role=homeowner')
        user = session(client)['user']
        response = client.post('/app/v1/messages/send', json={'quote_token': 'sample-project', 'sender_role': 'contractor', 'sender_id': 'forged', 'body': 'I will review the work this afternoon.'})
        assert response.status_code == 200 and response.json()['message']['sender_role'] == 'homeowner' and (response.json()['message']['sender_id'] == user['id'])
        assert client.post('/app/v1/projects/sample-project/milestones/1/proof', json={'note': 'forged'}).status_code == 403

def test_native_legacy_forms_are_scoped_and_persisted(app):
    with TestClient(app) as client:
        actor = info(client)
        proof = {'quote_token': 'sample-project', 'milestone_index': 1, 'photos': [], 'note': 'Native form proof', 'contractor_auth_id': actor['contractor_id']}
        assert client.post('/app/v1/milestone/submit-proof', json=proof).status_code == 200
        assert any((row['note'] == 'Native form proof' for row in client.get('/app/v1/milestone-updates/sample-project').json()))
        assert client.post('/app/v1/milestone/submit-proof', json={**proof, 'milestone_index': -1}).status_code == 400
        assert client.post('/app/v1/milestone/submit-proof', json={**proof, 'contractor_auth_id': 'another-contractor'}).status_code == 403
        variation = {'quote_token': 'sample-project', 'title': 'Additional work', 'amount_cents': 20000, 'reason': 'unforeseen_work', 'contractor_auth_id': actor['contractor_id']}
        assert client.post('/app/v1/variation/create', json=variation).status_code == 200
        assert client.get('/app/v1/variation-orders/sample-project').json()[0]['title'] == 'Additional work'


def test_sql_limits_apply_to_each_connection(app):
    with app.state.store.connect() as connection:
        assert connection.execute('PRAGMA max_page_count').fetchone()[0] == 32768


def test_unknown_page_writes_and_optional_pdf_fail_closed(app):
    with TestClient(app) as client:
        assert client.post('/app/dashboard', json={}).status_code == 405
        assert client.get('/app/v1/documents/sample-project/agreement?format=pdf').status_code == 503
        response = client.get('/app/v1/documents/unknown/agreement')
        assert response.status_code == 404
        assert response.json()['detail']['ok'] is False

def test_original_connected_quote_writes_require_contractor_authority():
    from fastapi import FastAPI
    from core import CurrentUser, require_contractor
    from routes.canvas import router
    connected = FastAPI()
    connected.include_router(router)
    from core.errors import AppError
    from fastapi.responses import JSONResponse
    @connected.exception_handler(AppError)
    async def domain_error(_request, error):
        return JSONResponse({'detail': error.to_detail()}, status_code=error.status)
    body = {'token': 'sample-quote', 'scope_data': {}, 'contractor_id': 'submitted-other-contractor'}
    with TestClient(connected) as client:
        assert client.post('/quote/update', json=body).status_code == 401
        assert client.post('/quote/finalize', json=body).status_code == 401
    connected.dependency_overrides[require_contractor] = lambda: CurrentUser(id='verified-auth', email='contractor@example.invalid', role='contractor', contractor_id='verified-contractor')
    with TestClient(connected) as client:
        assert client.post('/quote/update', json=body).status_code == 403
        assert client.post('/quote/finalize', json=body).status_code == 403
