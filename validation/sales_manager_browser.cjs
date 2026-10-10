/* Isolated acceptance: production frontend + real API + disposable SQLite. No live credentials. */
const {chromium}=require(process.env.VTAB_PLAYWRIGHT_MODULE||'playwright');
const {spawn,spawnSync}=require('node:child_process');
const {mkdtempSync,writeFileSync,rmSync}=require('node:fs');
const {tmpdir}=require('node:os');
const path=require('node:path');
const net=require('node:net');
const assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
const python=process.env.VTAB_TEST_PYTHON||'python';
const tmp=mkdtempSync(path.join(tmpdir(),'vtab-sales-browser-'));
const checks=[];
const delay=ms=>new Promise(r=>setTimeout(r,ms));
const port=()=>new Promise(resolve=>{const server=net.createServer();server.listen(0,'127.0.0.1',()=>{const p=server.address().port;server.close(()=>resolve(p))})});
const env={...process.env,DATABASE_URL:'sqlite:///'+path.join(tmp,'acceptance.db'),INITIALIZE_SCHEMA:'false',SCHEDULER_ENABLED:'false',DEMO_MODE:'true',DEMO_AUTH:'true',APP_ENV:'test',LOGIN_EMAIL:'demo@vtabsquare.local',LOGIN_PASSWORD:'browser-fixture-only',JWT_SECRET:'browser-fixture-only-signing-key',AI_PROVIDER:'local',OPENAI_API_KEY:'',SERPER_API_KEY:'',MICROSOFT_CLIENT_SECRET:'',MICROSOFT_CLIENT_ID:'',MICROSOFT_TENANT_ID:'',MICROSOFT_SENDER_EMAIL:'',GOOGLE_CLIENT_ID:'',GOOGLE_CLIENT_SECRET:'',GOOGLE_REFRESH_TOKEN:'',GOOGLE_DRIVE_FOLDER_IDS:'',GITHUB_READ_TOKEN:''};
function runPython(args){const r=spawnSync(python,args,{cwd:path.join(root,'backend'),env,encoding:'utf8'});assert.equal(r.status,0,r.stderr);return r.stdout}
async function ready(url){for(let i=0;i<120;i++){try{if((await fetch(url)).ok)return}catch{}await delay(250)}throw Error('Server did not start: '+url)}
async function visible(locator){await locator.waitFor({state:'visible',timeout:20000})}
(async()=>{
 let backend,frontend,browser,page;
 try{
  runPython(['-m','alembic','upgrade','head']);runPython(['-m','app.seed']);
  runPython(['-c',`
from app.models.db import SessionLocal
from app.models import entities,platform,intelligence,sales_followup,sales_agent
from app.models.entities import Company,Opportunity,Contact,OutreachDraft,Communication
from app.models.sales_followup import InboundResponse
from app.services.response_intelligence import _apply_intelligence
with SessionLocal() as db:
 c=Company(name='Browser Fixture Buyer',country='Ireland');db.add(c);db.flush()
 o=Opportunity(company_id=c.id,title='Power BI browser fixture requirement',source_name='FIXTURE',source_url='https://example.invalid/browser-fixture',country='Ireland',description='Power BI support',pipeline_status='CONTACTED');db.add(o);db.flush()
 contact=Contact(company_id=c.id,full_name='Buyer',title='IT Manager',email='buyer@example.com',email_verification_status='TEST_VERIFIED');db.add(contact);db.flush()
 d=OutreachDraft(opportunity_id=o.id,contact_id=contact.id,subject='Browser EOI fixture',body_text='Fixture EOI',status='SENT');db.add(d)
 db.add(Communication(opportunity_id=o.id,direction='OUTBOUND',subject=d.subject,body=d.body_text,status='SIMULATED_SENT'));db.commit()
 r=InboundResponse(graph_message_id='browser-fixture-reply',sender_email=contact.email,subject='Re: Browser EOI fixture',body_text='Interested. Please share more information about Power BI and AI agents.');db.add(r);db.flush();_apply_intelligence(db,r);db.commit()
`]);
  const bp=await port(),fp=await port(),base='http://localhost:'+fp;
  backend=spawn(python,['-m','uvicorn','app.main:app','--host','127.0.0.1','--port',String(bp)],{cwd:path.join(root,'backend'),env,stdio:'ignore',detached:true});
  frontend=spawn('npm',['start','--','--hostname','127.0.0.1','--port',String(fp)],{cwd:path.join(root,'frontend'),env:{...env,API_BASE_URL:'http://127.0.0.1:'+bp},stdio:'ignore',detached:true});
  await Promise.all([ready('http://127.0.0.1:'+bp+'/api/health'),ready(base+'/login')]);
  browser=await chromium.launch({headless:true,executablePath:process.env.VTAB_CHROMIUM_PATH||chromium.executablePath(),args:['--no-sandbox','--disable-dev-shm-usage']});
  page=await browser.newPage({viewport:{width:1280,height:720}});const errors=[];
  page.on('pageerror',e=>errors.push(String(e)));
  await page.goto(base+'/sales-manager');assert.match(page.url(),/\/login/);checks.push('Sales Manager requires login');
  await page.locator('input[type=email]').fill(env.LOGIN_EMAIL);await page.locator('input[type=password]').fill(env.LOGIN_PASSWORD);
  await page.getByRole('button',{name:'Continue securely'}).click();await visible(page.getByPlaceholder('000000'));
  await page.getByPlaceholder('000000').fill('123456');await page.getByRole('button',{name:'Verify & enter'}).click();
  await visible(page.getByRole('heading',{name:'Sales Manager',exact:true}));await visible(page.getByText('DEMO · All sends simulated',{exact:true}));
  const cookies=await page.context().cookies();assert(cookies.find(c=>c.name==='vtab_session')?.httpOnly);checks.push('OTP login and HttpOnly session');
  await page.getByLabel('Enable sales agent',{exact:true}).check();await page.getByRole('button',{name:'Save automation policy'}).click();
  await visible(page.getByRole('button',{name:'Run saved policy now'}));await page.getByRole('button',{name:'Run saved policy now'}).click();
  await visible(page.getByText('Writer: LOCAL_STARTER',{exact:false}));checks.push('Sales cycle creates reviewed local response draft');
  await page.getByLabel('Response for owner review').fill('Reviewed capability response for this fixture buyer. Please confirm your timeline.');
  assert(await page.getByRole('button',{name:'Approve for next cycle'}).isDisabled());checks.push('Unsaved response cannot be approved');
  await page.getByRole('button',{name:'Save edited response'}).click();
  await page.waitForFunction(()=>!Array.from(document.querySelectorAll('button')).find(b=>b.textContent==='Approve for next cycle')?.disabled);
  await page.getByRole('button',{name:'Approve for next cycle'}).click();
  await visible(page.getByText('The reviewed version is approved for delivery in the next enabled cycle.',{exact:true}));
  await page.getByRole('button',{name:'Run saved policy now'}).click();
  await visible(page.getByText('No pending responses.',{exact:false}));checks.push('Approved edited response sent in demo cycle');
  await page.getByRole('button',{name:/Browser Fixture Buyer/}).click();await visible(page.getByRole('heading',{name:'Conversation & decision history'}));
  assert(await page.getByText('Reviewed capability response for this fixture buyer. Please confirm your timeline.',{exact:true}).count()>0);
  assert(await page.getByText('Delivery: SIMULATED_SENT',{exact:true}).count()>0);checks.push('Casebook contains incoming reply, approval and simulated outbound');
  await page.getByLabel('Lead status').selectOption('PROPOSAL');await page.getByLabel('Owner notes').fill('Fixture proposal scope review');
  await page.getByRole('button',{name:'Update casebook'}).click();await visible(page.getByText('Casebook updated.',{exact:true}));checks.push('Owner case status and notes persist');
  await page.getByLabel('Company source name').fill('Fixture repository');await page.getByLabel('Source type',{exact:true}).selectOption('GITHUB_REPOSITORY');
  await page.getByLabel('Source URL',{exact:true}).fill('https://github.com/vtabsquare/VTAB-AI-Sales-Intelligence');await page.getByRole('button',{name:'Add company source'}).click();
  await visible(page.getByText('Source saved.',{exact:false}));checks.push('Company repository source saved');
  await page.getByRole('button',{name:'Sync configured materials'}).click();await visible(page.getByText('Company-source network imports require live mode.',{exact:false}).first());checks.push('Demo source imports skip external accounts');
  for(const viewport of [{width:1280,height:720},{width:768,height:480},{width:390,height:844}]){
   await page.setViewportSize(viewport);await page.goto(base+'/sales-manager');await visible(page.getByRole('heading',{name:'Sales Manager',exact:true}));
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+2));
   const nav=page.locator('.premium-nav');await nav.evaluate(e=>e.scrollTop=e.scrollHeight);
   assert(await nav.evaluate(e=>e.scrollTop>0||e.scrollHeight<=e.clientHeight));checks.push('Responsive Sales Manager and scrolling navigation '+viewport.width+'x'+viewport.height);
  }
  await page.setViewportSize({width:1280,height:720});await page.goto(base+'/schedulers');await page.getByLabel('Name',{exact:true}).fill('Fixture periodic sales cycle');
  await page.getByLabel('Action',{exact:true}).selectOption('SALES_CYCLE');await page.getByLabel('Frequency',{exact:true}).selectOption('5');await page.getByRole('button',{name:'+ Create schedule'}).click();
  await visible(page.getByRole('heading',{name:'Fixture periodic sales cycle'}));checks.push('Five-minute complete sales cycle schedule');
  await page.getByRole('button',{name:'Sign out',exact:true}).click();await page.waitForURL(/\/login/);checks.push('Logout');
  assert.deepEqual(errors,[]);checks.push('No browser JavaScript errors');
  const result={checks_passed:checks.length,checks,database:'disposable SQLite with Alembic migrations',mode:'demo',external_sends:0};
  writeFileSync(path.join(__dirname,'sales-manager-browser-results.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
 }catch(e){
  if(page){writeFileSync("/tmp/vtab-sales-browser-failure.html",await page.content());console.error("Visible form controls",await page.locator("label").allTextContents());await page.screenshot({path:"/tmp/vtab-sales-browser-failure.png",fullPage:true})}throw e;
 }finally{
  if(browser)await browser.close();for(const p of [frontend,backend])if(p){try{process.kill(-p.pid,'SIGTERM')}catch{}}rmSync(tmp,{recursive:true,force:true});
 }
})().catch(e=>{console.error(e);process.exitCode=1});
