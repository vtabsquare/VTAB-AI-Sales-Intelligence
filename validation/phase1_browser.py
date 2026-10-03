"""Isolated Phase 1 browser acceptance. Requires Playwright's headless shell."""
import json,os,signal,subprocess,tempfile,time,urllib.request,socket
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1]
checks=[]
def check(name):checks.append(name)
def port():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
with tempfile.TemporaryDirectory(prefix='vtab-phase1-browser-') as tmp:
    backend_port,frontend_port=port(),port()
    env={**os.environ,'DATABASE_URL':'sqlite:///'+str(Path(tmp)/'browser.db'),'INITIALIZE_SCHEMA':'false','SCHEDULER_ENABLED':'false','DEMO_MODE':'true','DEMO_AUTH':'true','APP_ENV':'test','LOGIN_EMAIL':'demo@vtabsquare.local','LOGIN_PASSWORD':'browser-test-only','JWT_SECRET':'browser-test-only-signing-key','AI_PROVIDER':'local','OPENAI_API_KEY':'','SERPER_API_KEY':'','MICROSOFT_CLIENT_SECRET':''}
    subprocess.run(['alembic','upgrade','head'],cwd=ROOT/'backend',env=env,check=True)
    subprocess.run([os.sys.executable,'-m','app.seed'],cwd=ROOT/'backend',env=env,check=True)
    log=open(Path(tmp)/'servers.log','w')
    backend=subprocess.Popen([os.sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(backend_port)],cwd=ROOT/'backend',env=env,stdout=log,stderr=log,start_new_session=True)
    frontend=subprocess.Popen(['npm','start','--','--hostname','127.0.0.1','--port',str(frontend_port)],cwd=ROOT/'frontend',env={**os.environ,'API_BASE_URL':f'http://127.0.0.1:{backend_port}'},stdout=log,stderr=log,start_new_session=True)
    base=f'http://localhost:{frontend_port}'
    try:
        for url in [f'http://127.0.0.1:{backend_port}/api/health',base+'/login']:
            for _ in range(80):
                try:urllib.request.urlopen(url);break
                except Exception:time.sleep(.25)
            else:raise RuntimeError('Server did not start.')
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
            page=browser.new_page(viewport={'width':1280,'height':720})
            errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
            page.on('response',lambda r:print('HTTP ERROR',r.status,r.url,r.text()[:500]) if r.status>=400 else None)
            page.goto(base+'/knowledge');expect(page).to_have_url(__import__('re').compile('/login'));check('Unauthenticated knowledge access redirects')
            page.locator('input[type=email]').fill('demo@vtabsquare.local');page.locator('input[type=password]').fill('browser-test-only');page.get_by_role('button',name='Continue securely').click()
            expect(page.get_by_role('heading',name='Verify development demo')).to_be_visible();check('Development OTP is labeled and required')
            page.get_by_placeholder('000000').fill('123456');page.get_by_role('button',name='Verify & enter').click();expect(page).to_have_url(base+'/knowledge');check('Password and OTP establish authenticated session')
            page.goto(base+'/knowledge');expect(page.get_by_role('heading',name='VTAB Knowledge Base')).to_be_visible()
            page.get_by_label('Document title').fill('Browser reviewed Power BI capability');page.get_by_label('Evidence text').fill('Power BI dashboard modernization and Microsoft Fabric implementation. Browser fixture only.')
            page.get_by_role('button',name='Save for review').click();expect(page.get_by_role('heading',name='Browser reviewed Power BI capability')).to_be_visible();check('Knowledge save and review UI')
            page.get_by_role('button',name='Approve factual evidence').click();expect(page.get_by_role('status').filter(has_text='Knowledge approved')).to_be_visible();check('Human knowledge approval')
            page.get_by_label('Requirement',exact=True).fill('dashboard');page.get_by_role('button',name='Find matching knowledge').click();expect(page.get_by_role('heading',name='Browser reviewed Power BI capability')).to_have_count(2);check('Approved retrieval evidence')
            page.goto(base+'/discovery');page.get_by_role('button',name='Run Discovery Now').click();expect(page.get_by_role('status').filter(has_text='synthetic opportunity')).to_be_visible();check('Demo discovery displays synthetic mode')
            page.get_by_label('Country / region').fill('Ireland');page.get_by_label('IANA time zone').fill('Europe/Dublin');page.get_by_role('button',name='Save country').click();expect(page.get_by_role('status').filter(has_text='targeting saved')).to_be_visible();check('Country configuration persists')
            page.goto(base+'/opportunities');expect(page.locator('.vtab-opportunity-row')).to_have_count(3);page.get_by_label('Country',exact=True).select_option('Ireland');expect(page.locator('.vtab-opportunity-row')).to_have_count(1);check('Country filtering')
            page.locator('.vtab-opportunity-row').press('Enter');expect(page.get_by_role('heading',name='Agent workflow and scoring evidence')).to_be_visible();check('Keyboard opportunity review')
            page.get_by_role('button',name='Run / resume to approval').click();expect(page.get_by_text('Workflow: WAITING_APPROVAL',exact=False)).to_be_visible(timeout=20000);expect(page.locator('.score-dimensions > div')).to_have_count(7);check('Supervisor workflow and seven score dimensions')
            page.get_by_role('button',name='Run / resume to approval').click();expect(page.get_by_text('Workflow: WAITING_APPROVAL',exact=False)).to_be_visible();check('Completed workflow remains idempotent')
            page.get_by_role('button',name='Close review').click()
            with page.expect_download() as download:page.get_by_role('button',name='Export filtered CSV').click()
            assert download.value.suggested_filename=='vtab-opportunities.csv';check('Filtered CSV export')
            page.goto(base+'/approval');expect(page.get_by_text('Example Ireland Analytics Ltd',exact=False).first).to_be_visible();check('Draft appears in human approval queue')
            for width,height in [(1280,720),(768,480),(390,844)]:
                page.set_viewport_size({'width':width,'height':height})
                for route in ['/knowledge','/discovery','/opportunities']:
                    page.goto(base+route);page.wait_for_timeout(150)
                    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth+1'),(route,width)
                    check(f'No horizontal overflow {route} at {width}x{height}')
            page.get_by_role('button',name='Sign out').click();expect(page).to_have_url(__import__('re').compile('/login'));check('Logout revokes session')
            assert not errors,errors;check('No browser JavaScript errors')
            browser.close()
        result={'checks_passed':len(checks),'checks':checks,'errors':[],'database':'isolated SQLite','external_calls':'none','demo_mode':True}
        (ROOT/'validation/phase1-browser-results.json').write_text(json.dumps(result,indent=2))
        print(json.dumps(result))
    finally:
        for process in (frontend,backend):
            if process.poll() is None: os.killpg(process.pid,signal.SIGTERM)
            process.wait(timeout=10)
