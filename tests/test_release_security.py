"""Release hardening regressions using in-process HTTP and fake transports."""
from dataclasses import dataclass
from types import SimpleNamespace,ModuleType
import sys
import httpx,pytest
from fastapi import FastAPI,HTTPException
from core import CurrentUser,require_auth
from payments import resolve_sandbox
from project_access import is_project_homeowner,project_party
from routes import messages,notifications,milestones,projects

HOME=CurrentUser(id='homeowner-auth',email='homeowner@example.invalid',role='homeowner')
CONTRACTOR=CurrentUser(id='contractor-auth',email='contractor@example.invalid',role='contractor',contractor_id='contractor-record')
OTHER=CurrentUser(id='other-auth',email='other@example.invalid',role='homeowner')
QUOTE={'token':'sample-project','contractor_id':'contractor-record','homeowner_auth_id':'homeowner-auth','homeowner_email':'homeowner@example.invalid','payment_status':'paid','milestones':[{'title':'Preparation','amount_cents':140000,'status':'proof_submitted'}]}

class FakeDatabase:
 def __init__(self):self.calls=[]
 async def __aenter__(self):return self
 async def __aexit__(self,*args):pass
 async def get(self,url,**kw):
  self.calls.append(('get',url,kw))
  return httpx.Response(200,json=[QUOTE] if url.endswith('/quotes') else [])
 async def post(self,url,**kw):
  self.calls.append(('post',url,kw));return httpx.Response(201,json=[{'id':'sample-message',**kw['json']}])
 async def patch(self,url,**kw):self.calls.append(('patch',url,kw));return httpx.Response(200,json=[])

@pytest.fixture
def rig(monkeypatch):
 db=FakeDatabase();app=FastAPI();who={'caller':HOME}
 app.dependency_overrides[require_auth]=lambda:who['caller']
 app.dependency_overrides[resolve_sandbox]=lambda:SimpleNamespace(is_sandbox=True,suppress_whatsapp=True)
 for module in [messages,notifications]:
  monkeypatch.setattr(module,'http_client',lambda **kwargs:db)
  monkeypatch.setattr(module,'sb_url',lambda:'https://sample-database.invalid/rest/v1')
  monkeypatch.setattr(module,'sb_headers',lambda:{})
 async def quote(_):return {**QUOTE,'milestones':[dict(x) for x in QUOTE['milestones']]}
 monkeypatch.setattr(projects,'get_quote',quote);monkeypatch.setattr(milestones,'get_quote',quote)
 legacy=ModuleType('routes.milestone')
 async def no_recipient(_):return {'phone':''}
 async def no_send(*args,**kwargs):raise AssertionError('Notification transport must stay unused')
 legacy._get_contractor=no_recipient;legacy._send_whatsapp=no_send
 monkeypatch.setitem(sys.modules,'routes.milestone',legacy)
 for module in [messages,notifications,milestones]:app.include_router(module.router,prefix='/v1')
 return app,db,who

@pytest.mark.asyncio
async def test_outsider_cannot_read_or_write_project_chat(rig):
 app,db,who=rig;who['caller']=OTHER
 async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='https://local.test') as client:
  read=await client.get('/v1/messages/sample-project')
  write=await client.post('/v1/messages/send',json={'quote_token':'sample-project','sender_role':'contractor','sender_id':'contractor-record','body':'Spoofed participant'})
 assert read.status_code==403 and write.status_code==403
 assert not [x for x in db.calls if x[0]=='post']

@pytest.mark.asyncio
async def test_verified_sender_overrides_client_identity(rig):
 app,db,who=rig
 async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='https://local.test') as client:
  response=await client.post('/v1/messages/send',json={'quote_token':'sample-project','sender_role':'contractor','sender_id':'someone-else','body':'Sample project discussion'})
 assert response.status_code==200
 row=response.json()['message'];assert row['sender_role']=='homeowner' and row['sender_id']==HOME.id

@pytest.mark.asyncio
async def test_notification_mark_read_is_qualified_by_current_owner(rig):
 app,db,who=rig;who['caller']=CONTRACTOR
 async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='https://local.test') as client:
  response=await client.post('/v1/notifications/mark-read',json={'ids':['foreign-or-own-id']})
 assert response.status_code==200
 writes=[x for x in db.calls if x[0]=='patch'];assert writes and all(x[2]['params']['user_id']=='eq.contractor-record' for x in writes)

def test_empty_emails_never_establish_project_ownership():
 caller=CurrentUser(id='outsider',email='',role='homeowner')
 quote={**QUOTE,'homeowner_auth_id':None,'homeowner_email':''}
 assert not is_project_homeowner(caller,quote)
 with pytest.raises(HTTPException) as error:project_party(caller,quote)
 assert error.value.status_code==403

@pytest.mark.asyncio
@pytest.mark.parametrize('action,caller',[('proof',CONTRACTOR),('release',HOME)])
async def test_negative_milestone_index_is_rejected_before_effects(rig,monkeypatch,action,caller):
 app,db,who=rig;who['caller']=caller
 def forbidden(*args,**kwargs):raise AssertionError('Payment transport must stay unused')
 monkeypatch.setattr(milestones,'get_stripe_client',forbidden)
 async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='https://local.test') as client:
  response=await client.post('/v1/projects/sample-project/milestones/-1/'+action,json={} if action=='proof' else None)
 assert response.status_code==400
 assert not [x for x in db.calls if x[0] in ('post','patch')]
