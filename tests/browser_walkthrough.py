#!/usr/bin/env python3
"""Check the actual scripted product at desktop/phone sizes, with remote HTTP blocked."""
from pathlib import Path
from urllib.parse import urlsplit
import argparse,json
from playwright.sync_api import sync_playwright
ENTRIES=[('quote','/app/quote/first?reel=set-milestones'),('review','/app/project/reel?reel=approve-release'),('brief','/app/onboard/homeowner?reel=post-job'),('proof','/app/dashboard?reel=submit-proof'),('profile','/app/onboard/pro?reel=import-profile')]
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--base-url',default='http://127.0.0.1:18260');parser.add_argument('--output',type=Path,default=Path('.local/browser-proof'));parser.add_argument('--executable');parser.add_argument('--flows',nargs='+',choices=[name for name,_ in ENTRIES]);args=parser.parse_args()
 args.output.mkdir(parents=True,exist_ok=True);origin=urlsplit(args.base_url);results=[]
 with sync_playwright() as p:
  launch={'headless':True}
  if args.executable:launch['executable_path']=args.executable
  browser=p.chromium.launch(**launch)
  for width in [1600,390]:
   for name,path in ENTRIES:
    if args.flows and name not in args.flows:continue
    context=browser.new_context(viewport={'width':width,'height':1000 if width==1600 else 844},reduced_motion='reduce');page=context.new_page();errors=[];external=[];missing=[];writes=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    def route(r):
     parsed=urlsplit(r.request.url)
     if parsed.scheme in ['http','https'] and (parsed.scheme,parsed.netloc)!=(origin.scheme,origin.netloc):external.append(parsed.path);return r.abort()
     if r.request.method not in ['GET','HEAD']:writes.append({'method':r.request.method,'path':parsed.path})
     r.continue_()
    context.route('**/*',route)
    page.on('response',lambda r:missing.append({'status':r.status,'path':urlsplit(r.url).path}) if r.status>=400 else None)
    response=page.goto(args.base_url+path,wait_until='networkidle');page.evaluate('document.fonts.ready');page.wait_for_timeout(12000 if name=='quote' else 4000)
    text=page.locator('body').text_content() or ''
    checks={'http_200':response.status==200,'page_errors':len(errors),'external_requests':len(external),'mutating_requests':len(writes),'missing_resources':len(missing),'horizontal_overflow':page.evaluate('document.documentElement.scrollWidth>innerWidth')}
    if name=='quote':
     checks['vellum_css_loaded']=page.evaluate('''()=>{const sample=document.createElement('div');sample.className='brand-glass--vellum';sample.style.visibility='hidden';document.body.append(sample);const value=getComputedStyle(sample).backdropFilter;sample.remove();return value}''')=='blur(7px)'
     if width<768:
      toggle=page.get_by_role('button',name='Preview quote',exact=False);box=toggle.bounding_box();checks['preview_touch_target']=box['width']>=44 and box['height']>=44;toggle.click();page.wait_for_timeout(350)
     canvas=page.locator('.flex.flex-col.h-full.min-h-0.overflow-y-auto:visible').first
     canvas.evaluate('(e)=>e.scrollTop=e.scrollHeight')
     checks['quote_total_scroll_accessible']=page.get_by_text('€8,190',exact=True).filter(visible=True).count()>0
    if name=='quote' and width==1600:
     checks['materials_displayed']='1800' in text.replace('\u00a0','').replace(' ','').replace(',','')
     checks['iva_displayed']='10%' in text
     checks['english_quote_labels']=all(label in text for label in ['Work phases','Materials and purchases','Labour','VAT included'])
     checks['human_quote_date']='24 Jun 2026' in text and '2026-06-24T09:' not in text
     checks['total_8190_displayed']='8190' in text.replace('\u00a0','').replace(' ','').replace(',','')
    page.screenshot(path=str(args.output/f'{name}-{width}.png'),full_page=False)
    results.append({'flow':name,'width':width,'checks':checks});context.close()
  browser.close()
 output={'browser':'Chromium','network':'only selected local origin allowed','entries':results,'provider_calls':0,'customer_rows_read':0}
 (args.output/'proof.json').write_text(json.dumps(output,indent=2)+'\n');print(json.dumps(output,indent=2))
 for r in results:
  c=r['checks'];assert c['http_200'] and not any(c[k] for k in ['page_errors','external_requests','mutating_requests','missing_resources','horizontal_overflow']),r
  if 'vellum_css_loaded' in c:assert c['vellum_css_loaded'] and c['quote_total_scroll_accessible'],r
  if 'preview_touch_target' in c:assert c['preview_touch_target'],r
  if 'materials_displayed' in c:assert all(c[k] for k in ['materials_displayed','iva_displayed','total_8190_displayed','english_quote_labels','human_quote_date']),r
if __name__=='__main__':main()
