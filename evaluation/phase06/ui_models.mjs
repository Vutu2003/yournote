import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { readFile, writeFile, mkdir, mkdtemp, rm } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { join, resolve, extname } from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';


const project=fileURLToPath(new URL('../..',import.meta.url));
const dist=join(project,'frontend/dist');
const out='/tmp/phase06-models-ui'; await mkdir(out,{recursive:true});
const profile=await mkdtemp('/tmp/phase03-ui-chrome-');
const clone=value=>structuredClone(value); const now=Date.now();
const citation={source_index:1,source_marker:'S1',filename:'course.pdf',page:1,source_text:'Fixture learning evidence.'};
const oldSummary={scope:'filter',target:null,citations:[citation],summary:'Old summary [S1]',key_points:['Point']};
const blank=()=>({document_filenames:['course.pdf','other.pdf'],source_names:{},selected:['course.pdf'],read_documents:[],notes:[],page:'',active_tool:'summary',chat:[{question:'Old question',answer:'Old answer [S1]',citations:[citation]}],summary_artifacts:[{id:'old-summary',title:'Old summary',createdAt:now,sourceFilenames:['course.pdf'],pages:[],topic:null,result:clone(oldSummary)}],quiz_artifacts:[],flashcard_artifacts:[],mindmap_artifacts:[]});
const notebooks=new Map(['a','b'].map(id=>[id,{id,title:'Fixture '+id.toUpperCase(),icon:'📓',created_at:new Date(now).toISOString(),updated_at:new Date(now).toISOString(),source_count:2,chat_count:1,state:blank()}]));
const originalB=clone(notebooks.get('b'));
const docs=['course.pdf','other.pdf'].map((filename,i)=>({filename,document_id:'doc-'+i,pages:[1,2],page_count:2,chunk_count:2}));
let taskMode='manual'; let delaySave=0; let modelList=['alpha','beta',...Array.from({length:6},(_,i)=>'extra-'+i)]; let granted=true;
const jobs=[]; const cancellations=[]; const errors=[]; const requests=[];
const json=(res,data,status=200)=>{res.writeHead(status,{'Content-Type':'application/json','Access-Control-Allow-Origin':'*','Access-Control-Allow-Methods':'GET,POST,PUT,OPTIONS','Access-Control-Allow-Headers':'Content-Type, X-YourNote-Local, X-YourNote-CSRF'});res.end(JSON.stringify(data));};
const frame=value=>'data: '+JSON.stringify(value)+'\n\n';
function result(job) {
 const body=job.body;const sources=body.sources||body.input;
 const cited={...citation,filename:sources.filenames[0]};
 const generation={provider:body.model.provider,requested_model:body.model.model,model:'actual-'+body.model.model,actual_models:['actual-'+body.model.model],created_at:new Date().toISOString(),status:'completed',request_id:body.id,notebook_id:body.notebook_id,source_filenames:clone(sources.filenames),pages:sources.pages||[],calls:1,duration_seconds:.2,usage:{input_tokens:5,output_tokens:5,total_tokens:10}};
 if(body.feature==='chat'||body.feature==='reading')return {question:body.input.question,answer:'Completed answer '+body.id+' [S1]',citations:[cited],generation,...(body.feature==='reading'?{context:{mode:'reading',scope:body.input.scope,filenames:sources.filenames,selection:null}}:{})};
 return {...clone(oldSummary),summary:'New completed summary '+body.id+' [S1]',citations:[cited],generation};
}
function finish(job,kind='completed') {
 if(job.closed||job.done)return;job.done=true;
 if(kind==='completed')job.res.end(frame({type:'completed',result:result(job)}));
 else if(kind==='quota')job.res.end(frame({type:'error',code:'quota_exceeded',detail:'AI service quota exceeded.',status:429}));
 else job.res.end();
}
const server=createServer(async(req,res)=>{try{
 const url=new URL(req.url,'http://localhost');const path=url.pathname;
 if(req.method==='OPTIONS')return json(res,{},204);
 let body={};if(req.method==='POST'||req.method==='PUT'){let raw='';for await(const chunk of req)raw+=chunk;body=raw?JSON.parse(raw):{};}
 if(path.startsWith('/api/'))requests.push([req.method,path]);
 if(path==='/api/ai/session')return json(res,{csrf:'fixture-csrf'});
 if(path==='/api/ai/options')return json(res,{server:{provider:'gemini',model:'server-model',configured:true}});
 if(path==='/api/ai/chatgpt')return json(res,{profiles:[{id:'account-a',label:'Student account',state:granted?'connected':'reconnect_required',plan_enabled:granted,identity_connected:granted,catalog_checked:true,inference_checked:true,last_check:null,welcome_pending:false}],active_connection_id:'account-a',storage_mode:'keyring',pending:null,error:null});
 if(path.endsWith('/catalog'))return json(res,{models:modelList.map(slug=>({slug,display_name:'Model '+slug,...(slug==='alpha'?{supported_reasoning_levels:['low','medium','high','xhigh'],default_reasoning_level:'medium'}:{})}))});
 if(path==='/api/ai/tasks'&&req.method==='POST'){
  const job={body:clone(body),res,closed:false,done:false};jobs.push(job);
  res.writeHead(200,{'Content-Type':'text/event-stream','Cache-Control':'no-store'});res.write(frame({type:'started',task_id:body.id,notebook_id:body.notebook_id,feature:body.feature}));
  res.write(frame({type:'progress',stage:'preparing',calls:0}));
  res.on('close',()=>{job.closed=true;});
  if(body.feature==='chat'||body.feature==='reading')setTimeout(()=>{if(!job.closed)res.write(frame({type:'delta',text:'PRIVATE_DRAFT Tiếng Việt [S1]'}));},40);
  if(taskMode==='complete')setTimeout(()=>finish(job),140);
  if(taskMode==='quota')setTimeout(()=>finish(job,'quota'),180);
  if(taskMode==='incomplete')setTimeout(()=>finish(job,'incomplete'),180);
  return;
 }
 if(path.match(/^\/api\/ai\/tasks\/[^/]+\/cancel$/)){cancellations.push(path.split('/')[4]);return json(res,{cancelled:true});}
 if(path==='/api/notebooks'&&req.method==='GET')return json(res,{notebooks:[...notebooks.values()].map(({state,...info})=>info)});
 if(path==='/api/documents')return json(res,{documents:docs});
 const match=path.match(/^\/api\/notebooks\/([ab])$/);
 if(match&&req.method==='GET')return json(res,notebooks.get(match[1]));
 if(match&&req.method==='PUT'){
  if(delaySave)await delay(delaySave);
  const saved={...notebooks.get(match[1]),...body};notebooks.set(match[1],saved);return json(res,saved);
 }
 if(path.match(/^\/api\/notebooks\/[ab]\/documents\/doc-[01]$/)){
  const index=Number(path.slice(-1));return json(res,{document_id:'doc-'+index,filename:docs[index].filename,document_version:'a'.repeat(64),page_count:2});
 }
 if(path.endsWith('/pdf')){const pdf=await readFile('/tmp/phase05-ui.pdf');res.writeHead(200,{'Content-Type':'application/pdf','Access-Control-Allow-Origin':'*'});return res.end(pdf);}
 if(path.startsWith('/api/'))throw new Error('Unexpected route '+req.method+' '+path);
 const file=path==='/'?join(dist,'index.html'):resolve(dist,'.'+path);if(!file.startsWith(dist+'/')&&file!==join(dist,'index.html')){res.writeHead(403).end();return;}
 const bytes=await readFile(file);res.writeHead(200,{'Content-Type':({'.html':'text/html','.js':'text/javascript','.css':'text/css','.mjs':'text/javascript'})[extname(file)]||'application/octet-stream'});res.end(bytes);
}catch(error){errors.push(String(error));json(res,{detail:'fixture route error'},500);}});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const origin='http://127.0.0.1:'+server.address().port;
const chrome = spawn('/usr/bin/google-chrome', ['--headless=new', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage', '--disable-background-networking', '--disable-extensions', '--no-first-run', '--no-default-browser-check', '--remote-debugging-pipe', `--user-data-dir=${profile}`], { stdio: ['ignore', 'ignore', 'pipe', 'pipe', 'pipe'] });
let stderr = '';
chrome.stderr.on('data', chunk => { stderr += chunk; });
let sequence = 0;
let buffer = '';
const waiting = new Map();
const listeners = new Map();
function command(method, params = {}, sessionId) {
 return new Promise((resolve, reject) => {
  const id = ++sequence;
  const timer = setTimeout(() => { waiting.delete(id); reject(new Error(`CDP timeout: ${method}`)); }, 10000);
  waiting.set(id, { resolve, reject, timer });
  chrome.stdio[3].write(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }) + '\0');
 });
}
chrome.stdio[4].on('data', chunk => {
 buffer += chunk.toString();
 let index;
 while ((index = buffer.indexOf('\0')) >= 0) {
  const raw = buffer.slice(0, index); buffer = buffer.slice(index + 1);
  if (!raw) continue;
  const msg = JSON.parse(raw);
  if (msg.id) {
   const pending = waiting.get(msg.id);
   if (pending) { waiting.delete(msg.id); clearTimeout(pending.timer); msg.error ? pending.reject(new Error(JSON.stringify(msg.error))) : pending.resolve(msg.result); }
  } else if (msg.method) listeners.get(msg.method)?.(msg.params, msg.sessionId);
 }
});
let session;
listeners.set('Fetch.requestPaused',(e,sid)=>{void command('Fetch.continueRequest',{requestId:e.requestId,url:origin+new URL(e.request.url).pathname},sid).catch(error=>errors.push(String(error)));});
listeners.set('Runtime.exceptionThrown',e=>errors.push(e.exceptionDetails.exception?.description||e.exceptionDetails.text));
async function evaluate(expression){const r=await command('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true},session);if(r.exceptionDetails)throw new Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value;}
async function until(fn,label){const end=Date.now()+12000;while(Date.now()<end){if(await fn())return;await delay(50);}throw new Error('Timeout: '+label);}
const exists=selector=>evaluate(`!!document.querySelector(${JSON.stringify(selector)})`);
const click=selector=>evaluate(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});if(!e||e.disabled)throw new Error('Cannot click '+${JSON.stringify(selector)});e.click()})()`);
async function input(selector,value){await evaluate(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});Object.getOwnPropertyDescriptor(e instanceof HTMLTextAreaElement?HTMLTextAreaElement.prototype:HTMLInputElement.prototype,'value').set.call(e,${JSON.stringify(value)});e.dispatchEvent(new Event('input',{bubbles:true}))})()`);}
async function select(selector,value){await until(()=>evaluate(`!!document.querySelector(${JSON.stringify(selector)})&&!document.querySelector(${JSON.stringify(selector)}).disabled`),'select enabled '+selector);await evaluate(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});e.value=${JSON.stringify(value)};e.dispatchEvent(new Event('change',{bubbles:true}))})()`);}
async function open(id){await until(()=>exists('.notebook-open'),'home');await evaluate(`Array.from(document.querySelectorAll('.notebook-open')).find(e=>e.textContent.includes('Fixture ${id.toUpperCase()}')).click()`);await until(()=>evaluate(`document.querySelector('.model-trigger')?.textContent.includes('Model')`),'workspace/catalog');await delay(150);}
async function chooseModel(model){await click('.model-trigger');if(!await exists('.model-options'))await click('.model-current');await until(()=>evaluate(`!!document.querySelector('.model-option:not(:disabled)')`),'model options ready');await click(`.model-option:nth-child(${model==='alpha'?1:2})`);if(await exists('.model-popover'))await evaluate(`document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))`);}
async function send(question){await input('#chat-question',question);await until(()=>evaluate(`!document.querySelector('button[aria-label="Gửi câu hỏi"]').disabled`),'send ready');const count=jobs.length;await click('button[aria-label="Gửi câu hỏi"]');await until(()=>jobs.length>count,'task accepted');return jobs.at(-1);}
async function saved(id,fn,label){await until(()=>Promise.resolve(fn(notebooks.get(id).state)),label);}
const watchdog=setTimeout(()=>{console.error('Browser timeout');chrome.kill();server.close();process.exit(2)},120000);
try{
 await command('Browser.getVersion');const {targetId}=await command('Target.createTarget',{url:'about:blank'});({sessionId:session}=await command('Target.attachToTarget',{targetId,flatten:true}));
 await command('Page.enable',{},session);await command('Runtime.enable',{},session);await command('Fetch.enable',{patterns:[{urlPattern:'http://127.0.0.1:8000/*'}]},session);
 await command('Page.addScriptToEvaluateOnNewDocument',{source:`if(!localStorage.getItem('yournote.model.preference.v1'))localStorage.setItem('yournote.model.preference.v1',JSON.stringify({provider:'chatgpt',model:'alpha',connection_id:'account-a'}))`},session);
 await command('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false},session);
 await command('Page.navigate',{url:origin},session);await open('a');

 assert.equal(await exists('select[aria-label="Dịch vụ AI"]'),false);
 assert.equal(await exists('select[aria-label="Kết nối ChatGPT"]'),false);
 assert.equal(await exists('a[href="https://chatgpt.com/settings/usage"]'),false);
 assert.equal(await evaluate(`!!document.querySelector('.composer-toolbar .model-trigger')`),true);
 await click('.model-trigger');await until(()=>exists('input[aria-label="Mức suy luận"]'),'effort slider');
 await evaluate(`(()=>{const e=document.querySelector('input[aria-label="Mức suy luận"]');Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(e,'2');e.dispatchEvent(new Event('input',{bubbles:true}))})()`);
 assert.equal(await evaluate(`document.querySelector('.model-effort-value').textContent`),'Cao');
 await evaluate(`document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))`);
 assert.equal(await evaluate(`document.activeElement===document.querySelector('.model-trigger')`),true);
 const first=await send('Reasoning snapshot');assert.equal(first.body.model.reasoning_effort,'high');
 await chooseModel('beta');assert.equal(first.body.model.model,'alpha');
 finish(first);await saved('a',s=>s.chat.length===2,'chat completed');
 assert.equal(await evaluate(`document.querySelector('.model-trigger').textContent.includes('Model beta')`),true);
 await click('.model-trigger');assert.equal(await exists('input[aria-label="Mức suy luận"]'),false);
 await input('input[aria-label="Tìm model"]','unlisted model');assert.equal(await evaluate(`document.querySelector('.model-popover').textContent.includes('Không tìm thấy model')`),true);await input('input[aria-label="Tìm model"]','');
 await click('.model-popover-footer button');await until(()=>exists('select[aria-label="Dịch vụ AI"]'),'quick Settings');
 await until(()=>exists('.ai-usage-card'),'usage loaded');
 assert.equal(await evaluate(`document.querySelector('.ai-usage-card a').href`),'https://chatgpt.com/settings/usage');
 await select('select[aria-label="Dịch vụ AI"]','gemini');await click('.viewer-overlay:not([hidden]) .viewer-close');await until(async()=>!await exists('.viewer-overlay:not([hidden])'),'Settings closed');await until(()=>evaluate(`document.querySelector('.model-trigger')?.textContent.includes('server-model')`),'source preference synchronized');
 await click('button[aria-label="Cài đặt"]');await until(()=>exists('select[aria-label="Dịch vụ AI"]'),'settings');
 await select('select[aria-label="Dịch vụ AI"]','chatgpt');await click('.viewer-overlay:not([hidden]) .viewer-close');await until(async()=>!await exists('.viewer-overlay:not([hidden])'),'Settings closed');await until(()=>evaluate(`document.querySelector('.model-trigger')?.textContent.includes('Chọn model')`),'explicit model choice required');
 await chooseModel('alpha');
 await click('.model-trigger');await click('button[aria-label="Đặt lại mức suy luận"]');
 assert.equal(await evaluate(`JSON.parse(localStorage.getItem('yournote.model.preference.v1')).reasoning_effort`),null);
 await evaluate(`document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))`);
 const count=jobs.length;await click('#studio-summary .generation-form button[type="submit"]');await until(()=>jobs.length>count,'Studio task');
 assert.equal(jobs.at(-1).body.model.model,'alpha');finish(jobs.at(-1));await saved('a',s=>s.summary_artifacts.length===2,'Studio saved');
 console.log('PASS compact picker; capability-aware effort; captured request; quick Settings; provider synchronization; reset; Studio');
 let layouts=0;
 for(const width of [360,768,1280,1920]){
   await command('Emulation.setDeviceMetricsOverride',{width,height:1000,deviceScaleFactor:1,mobile:width<500},session);
   for(const theme of ['dark','light']){
     await evaluate(`document.documentElement.dataset.theme=${JSON.stringify(theme)}`);
     await click('.model-trigger');await delay(240);
     const layout=await evaluate(`(()=>{const m=document.querySelector('.model-popover').getBoundingClientRect(),t=document.querySelector('.model-trigger').getBoundingClientRect(),c=document.querySelector('.composer-surface'),send=document.querySelector('.send-button').getBoundingClientRect();return {page:document.documentElement.scrollWidth<=innerWidth,popup:m.left>=0&&m.right<=innerWidth&&m.top>=0&&m.bottom<=innerHeight,composer:c.scrollWidth<=c.clientWidth+1,buttons:t.right<=send.left}})()`);
     assert(Object.values(layout).every(Boolean),JSON.stringify({width,theme,layout}));
     const shot=await command('Page.captureScreenshot',{format:'png'},session);await writeFile(join(out,`picker-${width}-${theme}.png`),Buffer.from(shot.data,'base64'));
     await click('.model-current');await delay(30);
     const listLayout=await evaluate(`(()=>{const r=document.querySelector('.model-popover').getBoundingClientRect();return r.left>=0&&r.right<=innerWidth&&r.top>=0&&r.bottom<=innerHeight})()`);assert(listLayout);
     await evaluate(`document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))`);
     await click('button[aria-label="Cài đặt"]');await until(()=>exists('.ai-usage-card'),'usage card');
     assert.equal(await evaluate(`document.documentElement.scrollWidth<=innerWidth`),true);
     await evaluate(`document.querySelector('.ai-usage-card').scrollIntoView({block:'center'})`);await delay(240);
     const usage=await command('Page.captureScreenshot',{format:'png'},session);await writeFile(join(out,`settings-${width}-${theme}.png`),Buffer.from(usage.data,'base64'));
     await click('.viewer-overlay:not([hidden]) .viewer-close');await until(async()=>!await exists('.viewer-overlay:not([hidden])'),'Settings closed');layouts++;
   }
 }
 console.log(`PASS ${layouts} responsive/theme layouts: effort popover, model list and Settings quota card`);
 await command('Page.reload',{},session);await open('a');assert.equal(await evaluate(`document.querySelector('.model-trigger').textContent.includes('Model alpha')`),true);
 modelList=[];await click('.model-trigger');await click('.model-current');await click('button[aria-label="Làm mới danh sách model"]');
 await until(()=>evaluate(`document.querySelector('.model-popover').textContent.includes('Lựa chọn cũ')`),'revoked model message');
 assert.equal(await evaluate(`document.querySelector('button[aria-label="Gửi câu hỏi"]').disabled`),true);
 assert.equal(jobs.length,2,'choosing models and Settings never invokes inference');
 assert.deepEqual(errors,[]);console.log('PASS preference reload, revoked model blocked, no automatic AI requests or JS errors');
}catch(error){console.log(await evaluate(`({preference:localStorage.getItem('yournote.model.preference.v1'),popover:document.querySelector('.model-popover')?.textContent,settings:document.querySelector('.viewer-overlay:not([hidden])')?.textContent,trigger:document.querySelector('.model-trigger')?.outerHTML})`));throw error;}finally{clearTimeout(watchdog);chrome.kill();server.close();await delay(150);await rm(profile,{recursive:true,force:true});}
