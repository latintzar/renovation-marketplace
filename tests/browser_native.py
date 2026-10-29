"""Exercise the normal app against its real local backend; paid services stay held."""
import json,os
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright
BASE=os.environ.get('NATIVE_TEST_URL','http://127.0.0.1:18260/app/').rstrip('/')+'/'
HOST=urlsplit(BASE).hostname
checks={};errors=[];foreign=[]
with sync_playwright() as p:
 launch={'headless':True}
 executable=os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH')
 if executable:launch['executable_path']=executable
 browser=p.chromium.launch(**launch)
 try:
  for width in (1600,390):
   context=browser.new_context(viewport={'width':width,'height':1000 if width==1600 else 844});page=context.new_page()
   page.on('pageerror',lambda error:errors.append(str(error)))
   def route(request):
    url=urlsplit(request.request.url)
    if url.hostname==HOST or url.scheme in {'data','blob'}:return request.continue_()
    foreign.append(url.hostname);return request.abort()
   context.route('**/*',route)
   page.goto(BASE,wait_until='domcontentloaded');page.get_by_role('heading',name='My jobs',exact=True).wait_for()
   if page.get_by_role('button',name='Decline',exact=True).is_visible():page.get_by_role('button',name='Decline',exact=True).click()
   page.goto(BASE+'quote/first?editToken=sample-quote',wait_until='domcontentloaded');page.get_by_role('button',name='Edit',exact=True).click()
   title='Native saved quote '+str(width)
   page.locator('input[placeholder="Job title…"]:visible').fill(title)
   with page.expect_response('**/v1/quote/update') as saved:page.get_by_role('button',name='Save',exact=True).click()
   assert saved.value.status==200
   page.reload(wait_until='domcontentloaded');page.get_by_text(title,exact=True).filter(visible=True).first.wait_for();checks['saved_quote_reload_'+str(width)]=True
   page.goto(BASE+'dashboard',wait_until='domcontentloaded');page.get_by_role('button',name='Submit proof',exact=True).click()
   note='Native phase evidence '+str(width);page.get_by_placeholder("Describe what you've completed…",exact=True).fill(note)
   with page.expect_response('**/v1/milestone/submit-proof') as submitted:page.get_by_role('button',name='Send to homeowner',exact=True).click()
   assert submitted.value.status==200
   assert any(row['note']==note for row in context.request.get(BASE+'v1/milestone-updates/sample-project').json());checks['phase_proof_persisted_'+str(width)]=True
   page.goto(BASE+'dashboard',wait_until='domcontentloaded');page.get_by_role('button',name='+ Change',exact=True).click()
   page.get_by_placeholder('e.g. Additional debris removal').fill('Extra floor protection');page.get_by_placeholder('200',exact=True).fill('200')
   with page.expect_response('**/v1/variation/create') as change:page.get_by_role('button',name='Send to homeowner',exact=True).click()
   assert change.value.status==200 and change.value.request.post_data_json['amount_cents']==20000;checks['variation_euros_'+str(width)]=True
   page.goto(BASE+'job-chat/sample-project',wait_until='domcontentloaded');text='Native project message '+str(width);page.get_by_placeholder('Type a message…',exact=True).fill(text)
   with page.expect_response('**/v1/messages/send') as sent:page.get_by_role('button',name='Send message',exact=True).click()
   assert sent.value.status==200
   page.reload(wait_until='domcontentloaded');page.get_by_text(text,exact=True).filter(visible=True).first.wait_for();checks['project_message_reload_'+str(width)]=True
   second=browser.new_context();assert second.request.get(BASE+'v1/messages/sample-project').json()==[];second.close();checks['visitor_isolation_'+str(width)]=True
   assert context.request.post(BASE+'v1/projects/sample-project/milestones/0/release',data={}).status==503;checks['payment_service_held_'+str(width)]=True
   assert context.request.post(BASE+'v1/chat',data={}).status==503;checks['model_service_held_'+str(width)]=True
   page.goto(BASE+'my-projects?local_role=homeowner',wait_until='domcontentloaded');page.get_by_role('heading',name='My projects',exact=True).wait_for()
   page.goto(BASE+'project/sample-project',wait_until='domcontentloaded');page.get_by_role('button',name='Review phase 1',exact=True).click();page.get_by_text('Under review',exact=True).wait_for();page.keyboard.press('Escape')
   page.goto(BASE+'project/sample-project',wait_until='domcontentloaded');page.get_by_role('button',name='View agreement',exact=True).click();page.get_by_text('Construction Agreement',exact=True).wait_for();page.get_by_text('CONTRATO',exact=False).first.wait_for();checks['homeowner_review_agreement_'+str(width)]=True
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1');checks['viewport_'+str(width)]=True
   context.request.delete(BASE+'api/local/session');context.close()
 finally:browser.close()
print(json.dumps({'checks':checks,'page_errors':errors,'foreign_requests':foreign},indent=2))
assert all(checks.values()) and not errors and not foreign
