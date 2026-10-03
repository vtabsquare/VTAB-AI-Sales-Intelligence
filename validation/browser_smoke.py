"""Starts both processes in one isolated run; never uses production SQL/Graph."""
import os,sys,time,subprocess,json,urllib.request,tempfile,re
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
results=[];errors=[];network=[]
def record(name,fn):
 try:fn();results.append({'test':name,'status':'PASS'});print('PASS '+name,flush=True)
 except Exception as e:results.append({'test':name,'status':'FAIL','reason':str(e)[:700]});raise

def wait(url):
 for _ in range(100):
  try:
   with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(url,timeout=1):return
  except Exception:time.sleep(.15)
 raise RuntimeError('Server did not start')
if __name__=='__main__':
 log=Path(tempfile.gettempdir())/'vtab-browser-server.log';handle=log.open('w')
 tempdir=tempfile.TemporaryDirectory(prefix='vtab-browser-')
 env={**os.environ,'VTAB_VALIDATION_DB':str(Path(tempdir.name)/'test.db'),'NEXT_TELEMETRY_DISABLED':'1','API_BASE_URL':'http://127.0.0.1:8001'}
 backend=subprocess.Popen([sys.executable,str(ROOT/'validation/serve_fixture.py')],cwd=ROOT,env=env,stdout=handle,stderr=handle)
 frontend=subprocess.Popen(['node','node_modules/next/dist/bin/next','start','--hostname','127.0.0.1','--port','3000'],cwd=ROOT/'frontend',env=env,stdout=handle,stderr=handle)
 try:
  wait('http://127.0.0.1:8001/api/health');wait('http://127.0.0.1:3000/login')
  with sync_playwright() as p:
   browser=p.chromium.launch(headless=True,args=['--no-sandbox'],executable_path=os.environ.get('VTAB_CHROMIUM_EXECUTABLE'));context=browser.new_context();page=context.new_page()
   page.on('pageerror',lambda e:errors.append(str(e)))
   page.on('console',lambda m:errors.append(m.text) if m.type=='error' and 'Failed to load resource' not in m.text else None)
   page.on('response',lambda r:network.append({'url':r.url.split('3000')[-1],'status':r.status}) if '/backend-api/' in r.url else None)
   def goto(path):page.goto('http://127.0.0.1:3000'+path);page.wait_for_load_state('networkidle');assert page.locator('h1').count()>0
   def protected():goto('/templates');assert '/login' in page.url
   record('Unauthenticated protected route redirect',protected)
   goto('/login?next=/templates');page.locator('input[type=email]').fill('qa@example.com');page.locator('input[type=password]').fill('wrong');page.get_by_role('button',name='Continue securely').click();page.get_by_text('Invalid email or password.',exact=True).wait_for()
   record('Password rejection',lambda:None)
   page.locator('input[type=password]').fill('test-only-password');page.get_by_role('button',name='Continue securely').click();page.locator('.otp-input').wait_for();page.locator('.otp-input').fill('123456');page.locator('form button[type=submit]').click();page.wait_for_url('http://127.0.0.1:3000/templates');page.wait_for_load_state('networkidle')
   def cookies():
    rows=context.cookies();cookie=next(x for x in rows if x['name']=='vtab_session');assert cookie['httpOnly'],'Cookie must be HttpOnly';assert cookie['sameSite']=='Lax','Cookie must use SameSite Lax';assert not any(x['name']=='vtab_auth_token' for x in rows),'Legacy compatibility cookie must be removed';assert page.evaluate('localStorage.getItem("vtab_token")') is None,'LocalStorage must not contain a bearer token'
   record('Login OTP proxy HttpOnly cookie and return URL',cookies)
   for route in ['/','/discovery','/opportunities','/approval','/outreach','/workflow','/responses','/response-center','/pipeline','/agents','/templates','/portfolio','/resources','/job-monitor','/schedulers','/security','/admin']:
    record('Page '+route,lambda route=route:goto(route))
   record('Refresh preserves session',lambda:goto('/'))
   def navigation_layout(width,height):
    page.set_viewport_size({'width':width,'height':height});goto('/admin')
    nav=page.locator('.premium-nav');nav.evaluate('(e)=>e.scrollTop=e.scrollHeight')
    assert nav.evaluate('(e)=>e.scrollTop>0 || e.scrollHeight<=e.clientHeight'), 'Navigation cannot scroll'
    admin=page.get_by_role('link',name='Admin',exact=True);admin.scroll_into_view_if_needed()
    box=admin.bounding_box();assert box and box['y']>=0 and box['y']+box['height']<=height,'Admin inaccessible'
    signout=page.get_by_role('button',name='Sign out',exact=True);signout.scroll_into_view_if_needed()
    box=signout.bounding_box();assert box and box['y']>=0 and box['y']+box['height']<=height,'Sign out inaccessible'
    assert page.locator('.operating-status').inner_text().startswith('DEMO MODE'), 'Backend demo mode not shown'
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 2'), 'Page overflows horizontally'
   for width,height in [(1280,720),(1024,600),(960,480),(768,650),(390,844)]:
    record(f'Navigation, mode and admin layout {width}x{height}',lambda w=width,h=height:navigation_layout(w,h))
   page.set_viewport_size({'width':390,'height':844})
   for route in ['/','/discovery','/opportunities','/approval','/outreach','/workflow','/responses','/response-center','/pipeline','/agents','/templates','/portfolio','/resources','/job-monitor','/schedulers','/security','/admin']:
    def mobile_route(route=route):
     goto(route)
     assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 2'), 'Page overflows horizontally'
    record('Mobile page '+route,mobile_route)
   page.set_viewport_size({'width':1280,'height':720});goto('/admin')
   page.route('**/backend-api/integrations/microsoft/status',lambda route:route.fulfill(status=503,content_type='application/json',body='{"detail":"Status temporarily unavailable"}'))
   page.get_by_role('button',name='Refresh mode',exact=True).click();page.get_by_text('MODE UNKNOWN',exact=True).wait_for()
   record('Unavailable mode is shown as unknown, never live',lambda:None)
   page.unroute('**/backend-api/integrations/microsoft/status');page.get_by_role('button',name='Refresh mode',exact=True).click();page.locator('.operating-status.demo').wait_for()

   # Existing form actions, not just route rendering.
   goto('/templates');page.locator('input[placeholder="Template name"]').fill('Browser QA template');page.locator('input[placeholder*="relevant subject"]').fill('QA Subject');page.once('dialog',lambda d:d.accept());page.get_by_role('button',name='Save template',exact=True).click();page.get_by_role('button',name='Browser QA template').wait_for()
   record('Templates save and list',lambda:None)
   page.get_by_role('button',name='Browser QA template').click();assert page.locator('textarea.html-editor').count()==1
   page.get_by_role('button',name='HTML',exact=True).click();assert page.locator('textarea.html-editor').count()==1
   page.get_by_role('button',name='Preview',exact=True).click();assert page.locator('iframe.email-preview').get_attribute('sandbox')==''
   page.get_by_role('button',name='Generate with AI').click();page.wait_for_load_state('networkidle');record('Template tabs preview and local generation',lambda:None)
   goto('/portfolio');page.locator('input[placeholder*="Microsoft Fabric"]').fill('Browser QA Service');page.locator('textarea').fill('QA capability');page.locator('input[placeholder*="fabric, onelake"]').fill('qa,analytics');page.get_by_role('button',name='Add capability').click();page.get_by_text('Browser QA Service',exact=True).wait_for();record('Portfolio add',lambda:None)
   goto('/resources');inputs=page.locator('.nx-card input');inputs.nth(0).fill('QA Resource');inputs.nth(1).fill('https://example.com/qa');page.get_by_role('button',name='Link resource').click();page.get_by_text('QA Resource',exact=True).wait_for();record('Resources add',lambda:None)
   goto('/discovery');inputs=page.locator('.nx-card input');inputs.nth(0).fill('QA RSS');inputs.nth(1).fill('https://example.com/qa-feed');page.get_by_role('button',name='Add connector').click();page.get_by_text('QA RSS',exact=True).wait_for();page.get_by_role('button',name='Run Discovery Now').click();page.get_by_text('New opportunities',exact=True).wait_for();record('Discovery source add and run',lambda:None)
   goto('/opportunities');page.get_by_text('QA Power BI Fabric tender RFP',exact=True).click()
   for action in ['qualify','research','find contact','generate outreach']:
    page.get_by_role('button',name=action,exact=True).click();page.wait_for_load_state('networkidle')
   record('Opportunity review qualification research contact and draft actions',lambda:None)
   goto('/approval');page.on('dialog',lambda d:d.accept('Reviewed official procurement notice reference QA') if d.type=='prompt' and 'Describe the official source' in d.message else d.accept(d.default_value) if d.type=='prompt' else d.accept());page.get_by_role('button',name='Edit draft',exact=True).click();page.wait_for_load_state('networkidle');page.get_by_role('button',name='Approve',exact=True).click();page.get_by_text('Approval queue is clear',exact=True).wait_for();record('Approval edit and approve without sending',lambda:None)
   goto('/outreach');page.get_by_role('button',name='Enter Manually').click();page.locator('input[placeholder="e.g. John Smith"]').fill('QA Buyer');page.locator('input[placeholder="e.g. Head of Data"]').fill('QA Role');page.locator('input[placeholder="name@company.com"]').fill('reply@example.com');page.get_by_role('button',name='Save Recipient',exact=True).click();page.get_by_role('button',name='Test Verify',exact=True).wait_for();page.get_by_role('button',name='Test Verify',exact=True).click();page.get_by_role('button',name='Confirm Test Verification',exact=True).click();page.get_by_role('button',name='Send Approved Outreach').wait_for();page.get_by_role('button',name='Send Approved Outreach').click();page.get_by_role('button',name='Confirm & Send',exact=True).click();page.wait_for_load_state('networkidle');record('Manual recipient test verification final confirmation simulated send',lambda:None)
   goto('/responses');page.get_by_role('button',name='Sync Microsoft 365').click();page.get_by_text('Buyer',exact=True).wait_for();page.get_by_text('Buyer',exact=True).click();assert page.get_by_text('COMPLETE MESSAGE',exact=True).count()==1;page.get_by_role('button',name='Close',exact=True).click()
   for label in ['Customer Replies','Procurement','Automated','Bounces','Internal','Marketing','Needs Review','All']:page.get_by_role('button',name=label,exact=True).click()
   page.get_by_role('button',name='Reprocess Intelligence',exact=True).click();page.wait_for_load_state('networkidle');page.get_by_role('button',name='Approve Follow-up',exact=True).click();page.get_by_role('button',name='Prepare follow-up draft',exact=True).wait_for();page.get_by_role('button',name='Prepare follow-up draft',exact=True).click();page.wait_for_load_state('networkidle');record('Inbox sync reply detail filters reprocess follow-up approve and draft',lambda:None)
   goto('/approval');page.get_by_role('button',name='Reject',exact=True).click();page.get_by_text('Approval queue is clear',exact=True).wait_for();record('Follow-up draft rejection',lambda:None)
   goto('/opportunities');page.get_by_text('QA Power BI Fabric tender RFP',exact=True).click();page.get_by_role('button',name='generate outreach',exact=True).click();page.wait_for_load_state('networkidle');goto('/approval');page.get_by_role('button',name='Approve',exact=True).click();page.get_by_text('Approval queue is clear',exact=True).wait_for();goto('/outreach');page.locator('.recipient-edit-button').click();page.locator('input[placeholder="name@company.com"]').fill('reviewed@example.com');page.get_by_role('button',name='Save Recipient',exact=True).click();page.get_by_role('button',name='Confirm recipient evidence',exact=True).wait_for();page.get_by_role('button',name='Confirm recipient evidence',exact=True).click();page.get_by_role('button',name='Send Approved Outreach').wait_for();record('Human recipient evidence review enables only separately confirmed sending',lambda:None)
   goto('/schedulers');page.get_by_label('Name',exact=True).fill('Browser Reprocess Job');page.get_by_label('Action',exact=True).select_option('REPROCESS');page.get_by_label('Frequency',exact=True).select_option('60');page.get_by_role('button',name='Create schedule').click();page.get_by_text('Browser Reprocess Job',exact=True).wait_for();page.get_by_role('button',name='Run now',exact=True).click();page.wait_for_load_state('networkidle');goto('/job-monitor');page.get_by_role('button',name=re.compile(r'Refresh$')).click();page.get_by_text('Browser Reprocess Job',exact=True).wait_for();record('Scheduler create manual run and job history refresh',lambda:None)
   goto('/pipeline');page.get_by_role('button',name=re.compile(r'Refresh$')).click();page.wait_for_load_state('networkidle');goto('/agents');page.locator('input[placeholder="Search agent or status..."]').fill('Qualification');assert page.locator('.vtab-agent-run').count()>0;record('Pipeline refresh and agent log filter',lambda:None)
   goto('/admin');page.get_by_role('button',name='Test Microsoft Connection',exact=True).click();page.get_by_text('Connected to sales@qa.example.',exact=True).wait_for();page.get_by_role('button',name='Refresh Status',exact=True).click();record('Integration connection test and refresh using mocked Graph',lambda:None)
   goto('/workflow');page.locator('.wf-shortcut').filter(has_text='Email Templates').click();page.wait_for_url('http://127.0.0.1:3000/templates');record('Workflow shortcut navigation',lambda:None)
   # Every list page rejects malformed successful JSON and exposes server failures.
   cases=[('/templates','/platform/templates'),('/portfolio','/platform/services'),('/resources','/platform/resources'),('/schedulers','/platform/schedules'),('/job-monitor','/platform/schedule-history/all?limit=300'),('/discovery','/platform/sources'),('/opportunities','/opportunities'),('/agents','/agent-runs'),('/outreach','/outreach/send-center'),('/approval','/outreach/approval-queue'),('/responses','/responses')]
   for route,api in cases:
    pattern='**/backend-api'+api
    page.route(pattern,lambda r:r.fulfill(status=200,content_type='application/json',body='{"detail":"wrong list shape"}'))
    goto(route);page.get_by_role('alert').first.wait_for();page.unroute(pattern);record('Malformed response resilience '+route,lambda:None)
   pattern='**/backend-api/platform/templates';page.route(pattern,lambda r:r.fulfill(status=500,content_type='application/json',body='{"detail":"QA server failure"}'));goto('/templates');page.get_by_role('alert').first.wait_for();page.unroute(pattern);record('Backend error is visible without React crash',lambda:None)
   goto('/');page.reload();page.wait_for_load_state('networkidle');assert '/login' not in page.url;record('Actual browser refresh keeps session',lambda:None)
   rejected=context.request.post('http://127.0.0.1:3000/backend-api/platform/templates',headers={'Origin':'https://evil.example'},data={});assert rejected.status==403;record('Proxy cross-origin mutation rejected',lambda:None)
   backend.terminate();frontend.terminate();backend.wait(timeout=10);frontend.wait(timeout=10)
   backend=subprocess.Popen([sys.executable,str(ROOT/'validation/serve_fixture.py')],cwd=ROOT,env=env,stdout=handle,stderr=handle)
   frontend=subprocess.Popen(['node','node_modules/next/dist/bin/next','start','--hostname','127.0.0.1','--port','3000'],cwd=ROOT/'frontend',env=env,stdout=handle,stderr=handle)
   wait('http://127.0.0.1:8001/api/health');wait('http://127.0.0.1:3000/login');goto('/');assert '/login' not in page.url;record('Backend and frontend clean restart preserve durable session',lambda:None)
   saved=next(c for c in context.cookies() if c['name']=='vtab_session');page.get_by_role('button',name='Sign out').click();page.wait_for_url('http://127.0.0.1:3000/login');assert not any(c['name']=='vtab_session' for c in context.cookies());context.add_cookies([saved]);goto('/templates');assert '/login' in page.url;goto('/login');record('Logout revokes session stale cookie redirects and login stays reachable',lambda:None)
   record('No browser runtime/console exceptions',lambda: (_ for _ in ()).throw(AssertionError(errors)) if errors else None)
   browser.close()
 except Exception as e:
  results.append({'test':'Browser run completion','status':'FAIL','reason':str(e)[:1200]});print('BROWSER FAILURE:',str(e)[:1200],flush=True)
 finally:
  backend.terminate();frontend.terminate();backend.wait(timeout=10);frontend.wait(timeout=10);handle.close()
  (ROOT/'validation/browser-results.json').write_text(json.dumps({'results':results,'browser_errors':errors,'network':network},indent=2))
  print(json.dumps({'results':results,'browser_errors':errors},indent=2),flush=True)
  if any(x['status']=='FAIL' for x in results):sys.exit(1)
