// Local browser QA, isolated synthetic API server/profile, no model calls.
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { createServer } from 'node:http';
import { readFile, writeFile, mkdir, mkdtemp, rm } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { join, resolve, extname } from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';


const project=fileURLToPath(new URL('../..',import.meta.url));
const dist=join(project,'frontend/dist');
const out=process.env.PHASE05_UI_OUTPUT||'/tmp/phase06-ui'; await mkdir(out,{recursive:true});
const profile=await mkdtemp('/tmp/phase03-ui-chrome-');
const clone=value=>structuredClone(value); const now=Date.now();
const initialVersion='a'.repeat(64);
const fixtureResults=JSON.parse(await readFile(process.env.PHASE05_UI_FIXTURE||'/tmp/phase05-ui-results.json','utf8'));
const exported=[];const resolutions=[];
const docs=[
 {filename:'slides.pdf',original_filename:'Bài giảng.pdf',document_id:'doc-pdf',kind:'pdf',document_version:initialVersion,pages:[1,2],page_count:2,chunk_count:2},
 {filename:'textbook--111.docx',original_filename:'Giáo trình.docx',document_id:'doc-docx',kind:'docx',document_version:initialVersion,pages:[],page_count:0,anchor_count:3,chunk_count:3},
 {filename:'notes--222.md',original_filename:'Ôn tập.md',document_id:'doc-md',kind:'markdown',document_version:initialVersion,pages:[],page_count:0,anchor_count:3,chunk_count:3},
 {filename:'outline--333.txt',original_filename:'Đề cương.txt',document_id:'doc-txt',kind:'text',document_version:initialVersion,pages:[],page_count:0,anchor_count:3,chunk_count:3},
];
const blocks=()=>[
 {text:'# Ôn tập',locator:{kind:'paragraph',anchor:'b000001',paragraph:1,heading:['Ôn tập']}},
 {text:'Bằng chứng 42, có trong tài liệu học tập.',locator:{kind:'paragraph',anchor:'b000002',paragraph:2,heading:['Ôn tập']}},
 {text:'<img src=x onerror="window.documentAttack=1"><script>window.documentAttack=1</script>',locator:{kind:'paragraph',anchor:'b000003',paragraph:3,heading:['Ôn tập']}},
];
const citation={source_index:1,source_marker:'S1',filename:docs[2].filename,document_id:'doc-md',document_version:initialVersion,page:null,locator:blocks()[1].locator,source_text:blocks()[1].text};
const oldSummary={scope:'filter',target:null,citations:[citation],summary:'Tóm tắt [S1]',key_points:['Ý chính']};
const blank=()=>({schema_version:2,document_filenames:docs.map(d=>d.filename),source_names:{[docs[2].filename]:'Ghi chú môn học'},selected:docs.slice(0,3).map(d=>d.filename),read_documents:[],notes:[],page:'',active_tool:'summary',chat:[{question:'Câu hỏi cũ',answer:'Nội dung đã xác nhận [S1]',citations:[citation]}],summary_artifacts:[],quiz_artifacts:[],flashcard_artifacts:[],mindmap_artifacts:[]});
const notebooks=new Map(['a','b'].map(id=>[id,{id,title:'Fixture '+id.toUpperCase(),icon:'📓',created_at:new Date(now).toISOString(),updated_at:new Date(now).toISOString(),source_count:4,chat_count:1,state:blank()}]));
let uploadCount=0;let saveFailure=false;
let taskMode='complete'; let delaySave=0; let modelList=['alpha','beta',...Array.from({length:6},(_,i)=>'extra-'+i)]; let granted=true;
const jobs=[]; const cancellations=[]; const errors=[]; const requests=[];
const json=(res,data,status=200)=>{res.writeHead(status,{'Content-Type':'application/json','Access-Control-Allow-Origin':'*','Access-Control-Allow-Methods':'GET,POST,PUT,OPTIONS','Access-Control-Allow-Headers':'Content-Type, X-YourNote-Local, X-YourNote-CSRF'});res.end(JSON.stringify(data));};
const frame=value=>'data: '+JSON.stringify(value)+'\n\n';
function result(job) {
 const body=job.body;const sources=body.sources||body.input;
 const cited={...citation,filename:sources.filenames[0],document_version:sources.document_versions?.[sources.filenames[0]]||initialVersion};
 const generation={provider:body.model.provider,requested_model:body.model.model,model:'actual-'+body.model.model,actual_models:['actual-'+body.model.model],created_at:new Date().toISOString(),status:'completed',request_id:body.id,notebook_id:body.notebook_id,source_versions:clone(sources.document_versions||{}),source_filenames:clone(sources.filenames),pages:sources.pages||[],calls:1,duration_seconds:.2,usage:{input_tokens:5,output_tokens:5,total_tokens:10}};
 if(['quiz','flashcards','mindmap','summary'].includes(body.feature)){
  const base={scope:'filter',target:null,citations:[cited],generation};
  if(body.feature==='summary')return {...base,summary:'Tóm tắt nội dung '+('MSE có bằng chứng. '.repeat(75))+'[S1]',key_points:['Trung bình bình phương sai số [S1]']};
  if(body.feature==='quiz')return {...base,items:[{question:'MSE đo đại lượng gì?',options:['Sai số bình phương trung bình','Nhãn phân loại','Hạn nộp','Học phí'],correct_index:0,explanation:'Theo đoạn nguồn [S1]',source_markers:['S1']}]};
  if(body.feature==='flashcards')return {...base,cards:[{front:'MSE là gì?',back:'Sai số bình phương trung bình.',source_markers:['S1']}]};
  return {...base,root:{label:'Kiến thức ôn tập',description:'Mind Map cũ vẫn là cây.',source_markers:[],children:[{label:'MSE',description:'Sai số bình phương trung bình.',source_markers:['S1'],children:[]}]}};
 }
 if(fixtureResults[body.feature]){
  let value=clone(fixtureResults[body.feature]); const old=value.sources.map(s=>s.filename), replacements=[docs[1],docs[0],docs[2]];
  const map=new Map(old.map((name,i)=>[name,replacements[i]]));
  value.sources=value.sources.map(source=>({...source,filename:map.get(source.filename).filename,document_id:map.get(source.filename).document_id,document_version:initialVersion}));
  value.citations=value.citations.map(c=>({...c,filename:map.get(c.filename).filename,document_id:map.get(c.filename).document_id,document_version:initialVersion,locator:c.page?{kind:'page',page:c.page}:{kind:'paragraph',anchor:'b000002',paragraph:2,heading:[]}}));
  if(value.criteria)for(const criterion of value.criteria)for(const source of criterion.sources)source.filename=map.get(source.filename).filename;
  value.source_notes=value.source_notes.map(note=>({...note,filename:map.get(note.filename).filename}));
  value.goal=body.input.goal;return {...value,generation};
 }
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
 let body={};if(req.method==='POST'||req.method==='PUT'){let raw='';for await(const chunk of req)raw+=chunk;body=req.headers['content-type']?.includes('multipart/form-data')?{multipart:raw}:raw?JSON.parse(raw):{};}
 if(path.startsWith('/api/'))requests.push([req.method,path]);
 if(path==='/api/ai/session')return json(res,{csrf:'fixture-csrf'});
 if(path==='/api/ai/options')return json(res,{server:{provider:'gemini',model:'server-model',configured:true}});
 if(path==='/api/ai/chatgpt')return json(res,{profiles:[{id:'account-a',label:'Student account',state:granted?'connected':'reconnect_required',plan_enabled:granted,identity_connected:granted,catalog_checked:true,inference_checked:true,last_check:null,welcome_pending:false}],active_connection_id:'account-a',storage_mode:'keyring',pending:null,error:null});
 if(path.endsWith('/catalog'))return json(res,{models:modelList.map(slug=>({slug,display_name:'Model '+slug,...(slug==='alpha'?{supported_reasoning_levels:['low','medium','high','xhigh'],default_reasoning_level:'medium'}:{})}))});
 if(path==='/api/ai/tasks'&&req.method==='POST'){
  const job={body:clone(body),res,closed:false,done:false};jobs.push(job);
  res.writeHead(200,{'Content-Type':'text/event-stream','Cache-Control':'no-store'});res.write(frame({type:'started',task_id:body.id,notebook_id:body.notebook_id,feature:body.feature}));
  const progress=frame({type:'progress',stage:'examining',completed_steps:1,total_steps:4,source_count:3,planned_calls:4});res.write(progress.slice(0,27));setTimeout(()=>{if(!job.closed)res.write(progress.slice(27))},20);
  res.on('close',()=>{job.closed=true;});
  if(body.feature==='chat'||body.feature==='reading')setTimeout(()=>{if(!job.closed)res.write(frame({type:'delta',text:'PRIVATE_DRAFT Tiếng Việt [S1]'}));},40);
  if(taskMode==='complete')setTimeout(()=>finish(job),140);
  if(taskMode==='quota')setTimeout(()=>finish(job,'quota'),180);
  if(taskMode==='incomplete')setTimeout(()=>finish(job,'incomplete'),180);
  return;
 }
 if(path.match(/^\/api\/ai\/tasks\/[^/]+\/cancel$/)){cancellations.push(path.split('/')[4]);return json(res,{cancelled:true});}
 if(path.match(/^\/api\/notebooks\/[ab]\/reset$/)){
  assert.equal(body.confirmation,'ĐẶT LẠI');const id=path.split('/')[3];const book=notebooks.get(id);
  book.state={...blank(),document_filenames:[],selected:[],chat:[],notes:[],source_names:{},comparison_artifacts:[],report_artifacts:[],graph_artifacts:[]};return json(res,book);
 }
 if(path==='/api/notebooks'&&req.method==='GET')return json(res,{notebooks:[...notebooks.values()].map(({state,...info})=>info)});
 if(path==='/api/documents')return json(res,{documents:docs});
 const match=path.match(/^\/api\/notebooks\/([ab])$/);
 if(match&&req.method==='GET')return json(res,notebooks.get(match[1]));
 if(match&&req.method==='PUT'){
  if(saveFailure)return json(res,{detail:'Synthetic save failure; original server snapshot kept.'},500);
  if(delaySave)await delay(delaySave);
  const saved={...notebooks.get(match[1]),...body};notebooks.set(match[1],saved);return json(res,saved);
 }
 if(path==='/api/export'){exported.push(body);res.writeHead(200,{'Content-Type':'text/markdown','Content-Disposition':'attachment; filename=fixture.md','Access-Control-Allow-Origin':'*'});return res.end('# Export synthetic result');}
 if(path.endsWith('/citations/resolve')){resolutions.push(clone(body));
  const source=docs.find(d=>d.filename===body.filename);if(!source)return json(res,{detail:'missing'},404);
  return json(res,{document:{...source,document_version:body.document_version||source.document_version,historical:body.document_version!==source.document_version},locator:body.locator||{kind:'page',page:body.page}});
 }
 const read=path.match(/^\/api\/notebooks\/[ab]\/documents\/(doc-[a-z]+)(?:\/(text|original))?$/);
 if(read){const source=docs.find(d=>d.document_id===read[1]);if(!source)return json(res,{detail:'missing'},404);
  const version=url.searchParams.get('version')||source.document_version;const info={...source,document_version:version,historical:version!==source.document_version};
  if(read[2]==='original'){res.writeHead(200,{'Content-Type':'application/octet-stream'});return res.end('original fixture');}
  if(read[2]==='text')return json(res,{...info,blocks:blocks().map(b=>version===initialVersion?b:{...b,text:b.text.replace('42','99')})});
  return json(res,info);
 }
 if(path==='/api/documents/upload'){
  uploadCount++;const original=body.multipart.match(/filename="([^"]+)"/)?.[1]||'same.md';
  const suffix=original.split('.').at(-1);const source={filename:'uploaded-'+uploadCount+'.'+suffix,original_filename:original,document_id:'uploaded-'+uploadCount,kind:suffix==='md'?'markdown':suffix==='txt'?'text':suffix,document_version:String(uploadCount).repeat(64),pages:[],page_count:0,anchor_count:3,chunk_count:3};docs.push(source);
  return json(res,{...source,chunks_indexed:3});
 }
 if(path==='/api/documents/doc-md/versions'){
  const source=docs.find(d=>d.document_id==='doc-md');assert.equal(url.searchParams.get('expected_version'),source.document_version);
  source.document_version='b'.repeat(64);return json(res,{...source,chunks_indexed:3});
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
listeners.set('Fetch.requestPaused',(e,sid)=>{void command('Fetch.continueRequest',{requestId:e.requestId,url:origin+new URL(e.request.url).pathname+new URL(e.request.url).search},sid).catch(error=>errors.push(String(error)));});
listeners.set('Runtime.exceptionThrown',e=>errors.push(e.exceptionDetails.exception?.description||e.exceptionDetails.text));
async function evaluate(expression){const r=await command('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true},session);if(r.exceptionDetails)throw new Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value;}
async function until(fn,label){const end=Date.now()+12000;while(Date.now()<end){if(await fn())return;await delay(50);}throw new Error('Timeout: '+label);}
const exists=selector=>evaluate(`!!document.querySelector(${JSON.stringify(selector)})`);
const click=selector=>evaluate(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});if(!e||e.disabled)throw new Error('Cannot click '+${JSON.stringify(selector)});if(typeof e.click==='function')e.click();else e.dispatchEvent(new MouseEvent('click',{bubbles:true}))})()`);
async function input(selector,value){await evaluate(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});Object.getOwnPropertyDescriptor(e instanceof HTMLTextAreaElement?HTMLTextAreaElement.prototype:HTMLInputElement.prototype,'value').set.call(e,${JSON.stringify(value)});e.dispatchEvent(new Event('input',{bubbles:true}))})()`);}
async function select(selector,value){await until(()=>evaluate(`!!document.querySelector(${JSON.stringify(selector)})&&!document.querySelector(${JSON.stringify(selector)}).disabled`),'select enabled '+selector);await evaluate(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});e.value=${JSON.stringify(value)};e.dispatchEvent(new Event('change',{bubbles:true}))})()`);}
async function open(id){await until(()=>exists('.notebook-open'),'home');await evaluate(`Array.from(document.querySelectorAll('.notebook-open')).find(e=>e.textContent.includes('Fixture ${id.toUpperCase()}')).click()`);await until(()=>evaluate(`document.querySelector('.model-trigger')?.textContent.includes('Model')`),'workspace/catalog');await delay(150);}
async function chooseModel(model){await click('.model-trigger');if(!await exists('.model-options'))await click('.model-current');await until(()=>evaluate(`!!document.querySelector('.model-option:not(:disabled)')`),'model options ready');await click(`.model-option:nth-child(${model==='alpha'?1:2})`);if(await exists('.model-popover'))await evaluate(`document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))`);}
async function send(question){await input('#chat-question',question);await until(()=>evaluate(`!document.querySelector('button[aria-label="Gửi câu hỏi"]').disabled`),'send ready');const count=jobs.length;await click('button[aria-label="Gửi câu hỏi"]');await until(()=>jobs.length>count,'task accepted');return jobs.at(-1);}
async function saved(id,fn,label){await until(()=>Promise.resolve(fn(notebooks.get(id).state)),label);}
const watchdog=setTimeout(()=>{console.error('Browser timeout');chrome.kill();server.close();process.exit(2)},240000);
try{
 await command('Browser.getVersion');const {targetId}=await command('Target.createTarget',{url:'about:blank'});({sessionId:session}=await command('Target.attachToTarget',{targetId,flatten:true}));
 await command('Page.enable',{},session);await command('Runtime.enable',{},session);await command('Fetch.enable',{patterns:[{urlPattern:'http://127.0.0.1:8000/*'}]},session);
 await command('Page.addScriptToEvaluateOnNewDocument',{source:`localStorage.setItem('yournote.model.preference.v1',JSON.stringify({provider:'chatgpt',model:'alpha',connection_id:'account-a'}))`},session);
 await command('Emulation.setDeviceMetricsOverride',{width:1280,height:1000,deviceScaleFactor:1,mobile:false},session);
 await command('Page.navigate',{url:origin},session);await open('a');
 async function tool(feature){await click(`button[aria-controls="studio-${feature}"]`);await until(()=>exists(`#studio-${feature}:not([hidden])`),'tool '+feature);}
 async function generate(feature){await tool(feature);await input(`#${feature}-goal`,'Ôn tập MSE, điều kiện áp dụng và bài tập');if(feature==='comparison')await input('#comparison-criteria','Ý nghĩa MSE\nĐiều kiện chuẩn hóa đặc trưng\nHạn LAB-A\nChi phí học phần');const count=jobs.length;await click(`#studio-${feature} button[type=submit]`);await until(()=>jobs.length>count,'research task');return jobs.at(-1);}
 async function view(feature){await tool(feature);await click(`#studio-${feature} .result-card-actions > button`);await until(()=>exists('.viewer-overlay:not([hidden]) .research-view'),'research viewer');}
 async function closeView(){await click('.viewer-overlay:not([hidden]) .viewer-close');await until(async()=>!await exists('.viewer-overlay:not([hidden])'),'viewer closed');}
 async function back(){await evaluate(`Array.from(document.querySelectorAll('.workspace-header-actions button')).find(e=>e.textContent.includes('Về sổ')).click()`);await until(async()=>!await exists('.reading-workspace'),'back');await delay(150);}
 // New features generate, notes, persisted metadata and reload without inference.
 for(const feature of ['comparison','report','graph']){
  await generate(feature);await saved('a',s=>s[feature+'_artifacts']?.length===1,'saved '+feature);
  assert.equal(notebooks.get('a').state[feature+'_artifacts'][0].result.generation.model,'actual-alpha');
  await view(feature);
  if(feature==='comparison')assert.equal(await evaluate(`document.querySelectorAll('.comparison-source').length`),12);
  if(feature==='graph'){
   await click('.knowledge-node');await until(()=>exists('.knowledge-detail .research-statement'),'node details');
   await evaluate(`document.querySelector('.knowledge-detail button').click()`);
  }else await evaluate(`Array.from(document.querySelectorAll('.research-view button')).find(e=>e.textContent.includes('Lưu')&&e.textContent.includes('ghi chú')).click()`);
  await saved('a',s=>s.notes.length===(feature==='comparison'?1:feature==='report'?2:3),'research note');
  assert(notebooks.get('a').state.notes[0].content.includes('phiên bản '+initialVersion));
  await until(()=>evaluate(`document.querySelector('.user-note-content')?.value.includes('phiên bản')`),'new note editor focused');
  const count=jobs.length;await command('Page.reload',{},session);await open('a');await view(feature);assert.equal(jobs.length,count);
  if(feature==='graph')await click('.knowledge-node');
  await evaluate(`document.querySelector('.research-evidence').open=true`);
  await click('.research-quote button');await until(()=>exists('.text-source-block.is-cited'),'research citation opens anchor');assert.equal(resolutions.at(-1).document_version,initialVersion);await back();
  await view(feature);await click('.viewer-overlay:not([hidden]) .export-control button');await until(()=>Promise.resolve(exported.some(e=>e.feature===feature)),'export '+feature);await closeView();
  await click(`#studio-${feature} .result-card-delete`);await until(()=>exists('.viewer-overlay:not([hidden])'),'confirm delete');await evaluate(`Array.from(document.querySelectorAll('.viewer-overlay:not([hidden]) .viewer-footer button')).find(e=>e.textContent==='Hủy').click()`);
  assert.equal(notebooks.get('a').state[feature+'_artifacts'].length,1);
 }
 console.log('PASS create/view/reload/citations/notes/export/cancel delete for all 3 tools');
 // Graph search/filter, source evidence, pan/zoom, keyboard and mobile list.
 await view('graph');await input('.knowledge-controls input','MSE');assert.equal(await evaluate(`document.querySelectorAll('.knowledge-node:not(.dimmed)').length`),1);
 await input('.knowledge-controls input','');await select('.knowledge-controls select',docs[2].filename);
 await click('.knowledge-edge');await until(()=>exists('.knowledge-detail .research-evidence'),'edge details');await evaluate(`document.querySelector('.knowledge-detail details').open=true`);
 assert.equal(await evaluate(`Array.from(document.querySelectorAll('.knowledge-detail .research-quote button')).every(b=>b.textContent.includes('Ghi chú môn học'))`),true);
 await select('.knowledge-controls select','');const before=await evaluate(`document.querySelector('.knowledge-canvas svg>g').getAttribute('transform')`);
 await click('button[aria-label="Phóng to mạng"]');assert.notEqual(await evaluate(`document.querySelector('.knowledge-canvas svg>g').getAttribute('transform')`),before);
 await evaluate(`document.querySelector('.knowledge-canvas').focus();document.querySelector('.knowledge-canvas').dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}))`);
 assert.equal(await evaluate(`document.querySelector('.knowledge-canvas svg>g').getAttribute('transform').startsWith('translate(-35 0)')`),true);
 await evaluate(`document.querySelector('.knowledge-canvas').dispatchEvent(new KeyboardEvent('keydown',{key:'Home',bubbles:true}));document.querySelector('.knowledge-node').dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}))`);
 assert.equal(await evaluate(`document.querySelector('.knowledge-node').getAttribute('aria-pressed')`),'true');
 await evaluate(`document.querySelector('.knowledge-canvas').scrollIntoView({block:'center'})`);await delay(120);
 const box=await evaluate(`(()=>{const r=document.querySelector('.knowledge-canvas').getBoundingClientRect();return {x:r.x+25,y:r.y+25}})()`);
 const panBefore=await evaluate(`document.querySelector('.knowledge-canvas svg>g').getAttribute('transform')`);
 await command('Input.dispatchMouseEvent',{type:'mousePressed',x:box.x,y:box.y,button:'left',clickCount:1},session);
 await command('Input.dispatchMouseEvent',{type:'mouseMoved',x:box.x+70,y:box.y+35,button:'left',buttons:1},session);
 await command('Input.dispatchMouseEvent',{type:'mouseReleased',x:box.x+70,y:box.y+35,button:'left'},session);
 await until(async()=>await evaluate(`document.querySelector('.knowledge-canvas svg>g').getAttribute('transform')`)!==panBefore,'pointer pan');
 await closeView();
 // Source version changes are visible; old quotes still resolve old version.
 docs[2].document_version='b'.repeat(64);await command('Page.reload',{},session);await open('a');await view('graph');await until(()=>exists('.research-stale'),'stale graph');await closeView();docs[2].document_version=initialVersion;
 // Cancel/error/incomplete, immutable scope/model and deleting old artifact during a new generation.
 for(const feature of ['comparison','report','graph']){
  await tool(feature);taskMode='hold';const old=notebooks.get('a').state[feature+'_artifacts'][0];const pending=await generate(feature);
  await until(()=>evaluate(`document.querySelector('#studio-${feature} .research-progress').textContent.includes('1/4')`),'chunked progress');
  await click(`#studio-${feature} .result-card-delete`);await until(()=>exists('.viewer-overlay:not([hidden])'),'delete old');await click('.viewer-overlay:not([hidden]) .button.danger');await saved('a',s=>s[feature+'_artifacts'].length===0,'old deleted');
  finish(pending);await saved('a',s=>s[feature+'_artifacts'].length===1,'new preserved');assert.notEqual(notebooks.get('a').state[feature+'_artifacts'][0].id,old.id);
  const cancelled=await generate(feature);await click(`#studio-${feature} .research-progress button`);await until(()=>Promise.resolve(cancellations.includes(cancelled.body.id)),'upstream cancel');finish(cancelled);await delay(200);assert.equal(notebooks.get('a').state[feature+'_artifacts'].length,1);
  taskMode='quota';await generate(feature);await until(()=>exists(`#studio-${feature} .error-message`),'error');assert.equal(notebooks.get('a').state[feature+'_artifacts'].length,1);
  taskMode='incomplete';await generate(feature);await until(()=>evaluate(`document.querySelector('#studio-${feature} .error-message')?.textContent.includes('kết thúc')||!!document.querySelector('#studio-${feature} .error-message')`),'incomplete');assert.equal(notebooks.get('a').state[feature+'_artifacts'].length,1);
 }
 taskMode='hold';const pending=await generate('comparison');const captured=clone(pending.body);
 await evaluate(`document.querySelector('.source-item input[type=checkbox]').click()`);await chooseModel('beta');assert.deepEqual(pending.body,captured);
 await click('.back-home');await open('b');await until(()=>Promise.resolve(cancellations.includes(pending.body.id)),'cancel on notebook leave');finish(pending);await delay(200);
 assert.equal(notebooks.get('b').state.comparison_artifacts?.length||0,0);assert.equal(notebooks.get('a').state.comparison_artifacts.length,1);
 console.log('PASS chunked progress, stop/quota/incomplete, delete during generation, scope/model/notebook isolation and stale source banner');
 await click('.back-home');await open('a');await until(async()=>!await exists('.toast'),'transient notices cleared');
 // Regression for all legacy Studio tools, PDF citation, notes/save recovery and reset.
 taskMode='complete';
 const fields={summary:'summary_artifacts',quiz:'quiz_artifacts',flashcards:'flashcard_artifacts',mindmap:'mindmap_artifacts'};
 for(const feature of ['summary','quiz','flashcards','mindmap']){
  await tool(feature);await click(`#studio-${feature} button[type=submit]`);await saved('a',s=>s[fields[feature]].length===1,'legacy generation '+feature);
  await click(`#studio-${feature} .result-card-actions > button`);await until(()=>exists('.viewer-overlay:not([hidden])'),'legacy viewer');
  if(feature==='quiz'){await click('.viewer-overlay:not([hidden]) .quiz-option input');await evaluate(`Array.from(document.querySelectorAll('.viewer-overlay:not([hidden]) button')).find(b=>b.textContent==='Kiểm tra đáp án').click()`);await until(()=>exists('.quiz-feedback'),'quiz answer');}
  if(feature==='flashcards'){await evaluate(`Array.from(document.querySelectorAll('.viewer-overlay:not([hidden]) button')).find(b=>b.textContent==='Hiển thị đáp án').click()`);await until(()=>exists('.flashcard-back'),'flashcard answer');}
  await click('.viewer-overlay:not([hidden]) .export-control button');await until(()=>Promise.resolve(exported.some(e=>e.feature===feature)),'legacy export');await closeView();
  const count=jobs.length;await command('Page.reload',{},session);await open('a');await tool(feature);assert.equal(jobs.length,count);
  await click(`#studio-${feature} .result-card-delete`);await until(()=>exists('.viewer-overlay:not([hidden])'),'legacy confirm');await closeView();assert.equal(notebooks.get('a').state[fields[feature]].length,1);
  await click(`#studio-${feature} .result-card-delete`);await until(()=>exists('.viewer-overlay:not([hidden])'),'legacy delete');await click('.viewer-overlay:not([hidden]) .button.danger');await saved('a',s=>s[fields[feature]].length===0,'legacy deleted');
 }
 assert.equal(notebooks.get('a').state.graph_artifacts.length,1);
 // Notes: failed persistence must leave the local edits available; next edit retries save.
 await tool('notes');await input('.user-note-content','Edited note '+('Nội dung dài có thể đọc được. '.repeat(120)));await saved('a',s=>s.notes[0].content.startsWith('Edited note'),'note save');
 saveFailure=true;await input('.user-note-content','UNSAVED available locally');await until(()=>evaluate(`!!document.querySelector('.save-status.error')`),'save error');assert.equal(await evaluate(`document.querySelector('.user-note-content').value`),'UNSAVED available locally');assert(!notebooks.get('a').state.notes[0].content.startsWith('UNSAVED'));
 saveFailure=false;await input('.user-note-content','Recovered after save failure');await saved('a',s=>s.notes[0].content==='Recovered after save failure','save recovery');
 const priorA=clone(notebooks.get('a').state);await click('.back-home');await open('b');await evaluate(`Array.from(document.querySelectorAll('.workspace-header-actions button')).find(b=>b.getAttribute('aria-label')?.includes('Cài đặt')).click()`);await until(()=>exists('.viewer-overlay:not([hidden]) .settings-form'),'reset settings');await click('.viewer-overlay:not([hidden]) .button.danger');await until(()=>exists('#reset-confirmation'),'reset confirm input');await input('#reset-confirmation','ĐẶT LẠI');await click('.viewer-overlay:not([hidden]) .button.danger');await until(()=>Promise.resolve(notebooks.get('b').state.document_filenames.length===0),'reset b');assert.deepEqual(notebooks.get('a').state,priorA);
 if(await exists('.viewer-overlay:not([hidden])'))await closeView();await click('.back-home');await open('a');await until(async()=>!await exists('.toast'),'notices cleared after regression');
 console.log('PASS all legacy Studio viewers/export/reload/delete, long notes, autosave failure recovery and isolated notebook reset');
 // All new viewers at 360/768/1280/1920, both themes. Graph mobile defaults to a keyboard-operable list.
 let layouts=0;
 for(const width of [360,768,1280,1920]){
  await command('Emulation.setDeviceMetricsOverride',{width,height:1000,deviceScaleFactor:1,mobile:width<500},session);await delay(180);
  for(const theme of ['dark','light']){
   await evaluate(`document.documentElement.dataset.theme=${JSON.stringify(theme)}`);
   for(const feature of ['comparison','report','graph']){
    await view(feature);await delay(180);
    if(feature==='graph'&&width===360){assert.equal(await exists('.knowledge-canvas'),false);await click('.knowledge-items button');await until(()=>exists('.knowledge-detail .research-statement'),'mobile list selection');await evaluate(`Array.from(document.querySelectorAll('.knowledge-list-tabs button')).find(e=>e.textContent==='Quan hệ').click()`);await click('.knowledge-items button');}
    const layout=await evaluate(`(()=>{const r=document.querySelector('.viewer-overlay:not([hidden]) .result-viewer');const v=r.querySelector('.viewer-content');return {page:document.documentElement.scrollWidth<=innerWidth,panel:r.getBoundingClientRect().right<=innerWidth+1,content:v.scrollWidth<=v.clientWidth+1,footer:r.querySelector('.viewer-footer').getBoundingClientRect().bottom<=innerHeight+1}})()`);
    assert(Object.values(layout).every(Boolean),JSON.stringify({width,theme,feature,layout}));
    const shot=await command('Page.captureScreenshot',{format:'png'},session);await writeFile(join(out,`${width}-${theme}-${feature}.png`),Buffer.from(shot.data,'base64'));layouts++;
    await closeView();
   }
  }
 }
 assert.deepEqual(errors,[]);await writeFile(join(out,'proof.json'),JSON.stringify({layouts,features:['comparison','report','graph'],checks:['create','view','reload_no_calls','citations','notes','export','cancel_delete','delete_during_generation','cancel','quota','incomplete','model_scope_snapshot','notebook_isolation','stale_version','search','source_filter','zoom','pointer_pan','legacy_studio_all','long_notes','save_failure_recovery','isolated_reset','keyboard_pan','keyboard_selection','mobile_list'],errors},null,2));
 console.log(`PASS ${layouts} new viewer layouts, themes and keyboard/mobile interactions; no JS errors`);
}catch(error){console.log({errors});console.log(await evaluate(`({text:document.querySelector('.viewer-overlay:not([hidden])')?.textContent||document.querySelector('.research-tool:not([hidden])')?.textContent,body:document.body.textContent.slice(-2000)})`));throw error;}finally{clearTimeout(watchdog);chrome.kill();server.close();await delay(150);await rm(profile,{recursive:true,force:true});}
