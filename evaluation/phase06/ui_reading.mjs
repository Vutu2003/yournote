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
const out='/tmp/phase06-reading-ui'; await mkdir(out,{recursive:true});
const profile=await mkdtemp('/tmp/phase03-ui-chrome-');
const clone=value=>structuredClone(value); const now=Date.now();
const initialVersion='a'.repeat(64);
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
const blank=()=>({schema_version:2,document_filenames:docs.map(d=>d.filename),source_names:{[docs[2].filename]:'Ghi chú môn học'},selected:[docs[2].filename],read_documents:[],notes:[],page:'',active_tool:'summary',chat:[{question:'Câu hỏi cũ',answer:'Nội dung đã xác nhận [S1]',citations:[citation]}],summary_artifacts:[],quiz_artifacts:[],flashcard_artifacts:[],mindmap_artifacts:[]});
const notebooks=new Map(['a','b'].map(id=>[id,{id,title:'Fixture '+id.toUpperCase(),icon:'📓',created_at:new Date(now).toISOString(),updated_at:new Date(now).toISOString(),source_count:4,chat_count:1,state:blank()}]));
let uploadCount=0;
let taskMode='complete'; let delaySave=0; let modelList=['alpha','beta',...Array.from({length:6},(_,i)=>'extra-'+i)]; let granted=true;
const jobs=[]; const cancellations=[]; const errors=[]; const requests=[];
const json=(res,data,status=200)=>{res.writeHead(status,{'Content-Type':'application/json','Access-Control-Allow-Origin':'*','Access-Control-Allow-Methods':'GET,POST,PUT,OPTIONS','Access-Control-Allow-Headers':'Content-Type, X-YourNote-Local, X-YourNote-CSRF'});res.end(JSON.stringify(data));};
const frame=value=>'data: '+JSON.stringify(value)+'\n\n';
function result(job) {
 const body=job.body;const sources=body.sources||body.input;
 const cited={...citation,filename:sources.filenames[0],document_version:sources.document_versions?.[sources.filenames[0]]||initialVersion};
 const generation={provider:body.model.provider,requested_model:body.model.model,model:'actual-'+body.model.model,actual_models:['actual-'+body.model.model],created_at:new Date().toISOString(),status:'completed',request_id:body.id,notebook_id:body.notebook_id,source_versions:clone(sources.document_versions||{}),source_filenames:clone(sources.filenames),pages:sources.pages||[],calls:1,duration_seconds:.2,usage:{input_tokens:5,output_tokens:5,total_tokens:10}};
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
 if(path.endsWith('/citations/resolve')){
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


 async function readSource(name){
   if(await exists('.reading-workspace')){await evaluate(`Array.from(document.querySelectorAll('.workspace-header-actions button')).find(e=>e.textContent.includes('Về sổ')).click()`);await until(async()=>!await exists('.reading-workspace'),'notebook mode');}
   await delay(180);
   await evaluate(`(()=>{const e=Array.from(document.querySelectorAll('.source-item')).find(e=>e.querySelector('.source-name').textContent===${JSON.stringify(name)});e.querySelector('.source-menu-trigger').click()})()`);
   await until(()=>exists('.source-menu-popup'),'source menu');await click('.source-menu-popup button:first-child');
   await until(()=>exists('#notebook-pdf-panel'),'reader');
   if(name.endsWith('.pdf'))await until(()=>exists('.pdf-page canvas'),'PDF rendered');else await until(()=>exists('.text-source-block'),'text rendered');
 }
 async function back(){if(await exists('.reading-workspace')){await evaluate(`Array.from(document.querySelectorAll('.workspace-header-actions button')).find(e=>e.textContent.includes('Về sổ')).click()`);await until(async()=>!await exists('.reading-workspace'),'back to notebook');}}
 await evaluate(`document.querySelector('.conversation .inline-citation').click()`);
 await until(()=>exists('.text-source-block.is-cited'),'citation anchor');
 assert.equal(await evaluate(`document.querySelector('.text-source-block.is-cited').dataset.anchor`),'b000002');
 await input('input[aria-label="Đến đoạn văn"]','3');await evaluate(`document.querySelector('input[aria-label="Đến đoạn văn"]').dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}))`);await until(()=>evaluate(`document.activeElement?.dataset.anchor==='b000003'`),'paragraph navigation');
 assert.equal(await evaluate(`window.documentAttack`),undefined);
 assert.equal(await evaluate(`document.querySelector('.text-reader-body img, .text-reader-body script')===null`),true);
 assert.equal(await evaluate(`document.querySelector('.text-reader-body').textContent.includes('<script>')`),true);
 const reading=await send('Hỏi theo nguồn văn bản');assert.equal(reading.body.feature,'reading');assert.equal(reading.body.input.document_version,initialVersion);
 assert.equal(reading.body.sources.document_versions[docs[2].filename],initialVersion);await saved('a',s=>s.chat.length===2,'reading autosave');
 console.log('PASS typed paragraph citation, escaped HTML/script, selected version snapshot and reading chat');
 for(const name of ['Bài giảng.pdf','Giáo trình.docx','Đề cương.txt']){await readSource(name);assert.equal(await evaluate(`window.documentAttack`),undefined);}
 await back();
 // Replacement is explicit, keeps aliases and read state, and preserves old citation targets.
 await evaluate(`Array.from(document.querySelectorAll('.source-item')).find(e=>e.textContent.includes('Ghi chú môn học')).querySelector('.source-menu-trigger').click()`);
 await until(()=>exists('.source-menu-popup'),'replace menu');await evaluate(`Array.from(document.querySelectorAll('.source-menu-popup button')).find(e=>e.textContent.includes('Cập nhật nội dung')).click()`);
 const files=await mkdtemp('/tmp/phase04-upload-');await mkdir(join(files,'a'));await mkdir(join(files,'b'));
 await writeFile(join(files,'a','same.md'),'# Topic\n\nVersion 1');await writeFile(join(files,'b','same.md'),'# Topic\n\nVersion 2');
 async function setFile(path){const {root}=await command('DOM.getDocument',{},session);const {nodeId}=await command('DOM.querySelector',{nodeId:root.nodeId,selector:'#pdf-upload'},session);await command('DOM.setFileInputFiles',{nodeId,files:[path]},session);await until(()=>exists('.upload-area .selected-file'),'file selected');}
 await setFile(join(files,'b','same.md'));await click('.upload-area .button.primary');await until(()=>Promise.resolve(docs[2].document_version==='b'.repeat(64)),'replacement accepted');await until(()=>evaluate(`document.querySelector('.upload-area').textContent.includes('Đã cập nhật')`),'replacement notice');
 await until(()=>Promise.resolve(notebooks.get('a').state.source_names[docs[2].filename]==='Ghi chú môn học'),'alias retained');
 await evaluate(`document.querySelector('.conversation .inline-citation').click()`);await until(()=>exists('.source-version-banner'),'old version banner');
 assert.equal(await evaluate(`document.querySelector('.text-reader-body').textContent.includes('42')`),true);
 const oldCount=jobs.length;await input('#chat-question','Hỏi bản cũ');await click('button[aria-label="Gửi câu hỏi"]');await until(()=>evaluate(`document.querySelector('.chat-composer').textContent.includes('Đang xem phiên bản cũ')`),'old reading generation blocked');assert.equal(jobs.length,oldCount);
 await click('.source-version-banner button');await until(async()=>!await exists('.source-version-banner'),'current source');await until(()=>evaluate(`document.querySelector('.text-reader-body').textContent.includes('99')`),'current version body');
 await back();
 for(const part of ['a','b']){await setFile(join(files,part,'same.md'));await click('.upload-area .button.primary');await until(()=>Promise.resolve(uploadCount>=(part==='a'?1:2)),'upload');await until(()=>evaluate(`!document.querySelector('.upload-area .selected-file')`),'upload reset');}
 assert.equal(await evaluate(`Array.from(document.querySelectorAll('.source-name')).filter(e=>e.textContent==='same.md').length`),2);
 assert.notEqual(docs.at(-1).filename,docs.at(-2).filename);
 await rm(files,{recursive:true,force:true});console.log('PASS PDF/DOCX/TXT viewers, explicit update, historical citation, old-version generation guard, same-name uploads');
 let layouts=0;
 for(const width of [360,768,1280,1920]){
  await command('Emulation.setDeviceMetricsOverride',{width,height:1000,deviceScaleFactor:1,mobile:width<500},session);await delay(180);
  for(const theme of ['dark','light']){
   await evaluate(`document.documentElement.dataset.theme=${JSON.stringify(theme)}`);
   for(const name of ['Ghi chú môn học','Bài giảng.pdf']){
    await readSource(name);await delay(220);
    const layout=await evaluate(`(()=>{const r=document.querySelector('#notebook-pdf-panel');return {page:document.documentElement.scrollWidth<=innerWidth,reader:r.scrollWidth<=r.clientWidth+1}})()`);
    assert(Object.values(layout).every(Boolean),JSON.stringify({width,theme,name,layout}));
    const shot=await command('Page.captureScreenshot',{format:'png'},session);await writeFile(join(out,`${width}-${theme}-${name.endsWith('.pdf')?'pdf':'text'}.png`),Buffer.from(shot.data,'base64'));layouts++;
   }
  }
 }
 await back();
 notebooks.get('a').state.document_filenames=[...docs.map(d=>d.filename),...Array.from({length:64-docs.length},(_,i)=>'unavailable-'+i+'.pdf')];
 await command('Page.reload',{},session);await open('a');
 assert.equal(await evaluate(`document.querySelector('#pdf-upload').disabled`),true);
 await evaluate(`Array.from(document.querySelectorAll('.source-item')).find(e=>e.textContent.includes('Ghi chú môn học')).querySelector('.source-menu-trigger').click()`);
 await until(()=>exists('.source-menu-popup'),'source menu at capacity');await evaluate(`Array.from(document.querySelectorAll('.source-menu-popup button')).find(e=>e.textContent.includes('Cập nhật nội dung')).click()`);
 await until(()=>evaluate(`!document.querySelector('#pdf-upload').disabled`),'existing source update allowed at capacity');
 await evaluate(`Array.from(document.querySelectorAll('.upload-area button')).find(e=>e.textContent.includes('Hủy cập nhật')).click()`);
 await until(()=>evaluate(`document.querySelector('#pdf-upload').disabled`),'new upload still blocked at capacity');
 assert.deepEqual(errors,[]);console.log(`PASS ${layouts} mobile/desktop dark/light text/PDF layouts; no JS errors`);
}catch(error){console.log(await evaluate(`({preference:localStorage.getItem('yournote.model.preference.v1'),popover:document.querySelector('.model-popover')?.textContent,settings:document.querySelector('.viewer-overlay:not([hidden])')?.textContent,trigger:document.querySelector('.model-trigger')?.outerHTML})`));throw error;}finally{clearTimeout(watchdog);chrome.kill();server.close();await delay(150);await rm(profile,{recursive:true,force:true});}
