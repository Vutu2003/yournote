"""Evidence/scope contracts on neutral learning materials; no paid model calls."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.config import settings
from src.store import close_client
from src.indexing import save_and_ingest_document
from backend.tests.test_documents_phase04 import TinyEmbeddings
from backend.services import core_adapter
from backend.schemas.api import ComparisonRequest,ReportRequest,GraphRequest,ExportRequest
from pydantic import TypeAdapter,ValidationError
from src.errors import LLMServiceError
from evaluation.phase05_fixture import create_fixture,CRITERIA,GOAL


def fake_research(prompt):
    step=prompt.split('RESEARCH_STEP=',1)[1].split('\n',1)[0]
    data=json.loads(prompt.split('DATA (JSON):\n',1)[1])
    def statement(passage): return {'text':passage['text'],'evidence':[{'source_marker':passage['source_marker'],'quote':passage['text']}]}
    if step=='compare_source':
        rows=[]
        for criterion in data['criteria']:
            keyword={'c1':'MSE','c2':'scal','c3':'LAB-A','c4':'TUITION'}[criterion['id']]
            passage=next((p for p in data['passages'] if keyword in p['text']),None)
            if not passage and criterion['id']=='c2': passage=next((p for p in data['passages'] if 'chuẩn hóa' in p['text']),None)
            rows.append({'criterion_id':criterion['id'],'status':'supported' if passage else 'not_found','statement':statement(passage) if passage else None,'limitation':'' if passage else 'Chưa tìm thấy trong các đoạn đã xét.'})
        return json.dumps({'criteria':rows},ensure_ascii=False)
    if step=='compare_synthesis':
        findings=[]
        for cid,kind in [('c1','agreement'),('c2','different_conditions'),('c3','direct_conflict')]:
            supported=[next(c for c in source['criteria'] if c['criterion_id']==cid)['statement'] for source in data['sources']]
            supported=[s for s in supported if s]
            if len(supported)>1:
                findings.append({'criterion_id':cid,'kind':kind,'statement':{'text':'Đối chiếu có bằng chứng ở cả hai nguồn.','evidence':[s['evidence'][0] for s in supported]}})
        return json.dumps({'findings':findings,'conclusion':[data['sources'][0]['criteria'][0]['statement']]},ensure_ascii=False)
    if step=='report_source': return json.dumps({'facts':[statement(data['passages'][0])],'limitations':[]},ensure_ascii=False)
    if step=='report_synthesis': return json.dumps({'title':'Đề cương ôn tập','sections':[{'title':'Các ý chính','statements':[r['facts'][0] for r in data['sources']]}],'conclusion':[data['sources'][0]['facts'][0]]},ensure_ascii=False)
    if step=='graph_source':
        passage=next(p for p in data['passages'] if 'MSE' in p['text'])
        defined=statement(passage)
        return json.dumps({'nodes':[{'id':'a','label':'MSE','meaning_key':'mean_squared_error','aliases':['MSE'],'definition':defined},
            {'id':'b','label':'error' if 'error' in passage['text'] else 'sai số','meaning_key':'prediction_error','aliases':[],'definition':defined}],
            'edges':[{'source':'a','target':'b','relation':'measures','statement':defined}],'limitations':[]},ensure_ascii=False)
    raise AssertionError(step)


class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.root=Path(self.enterContext(tempfile.TemporaryDirectory(prefix='research-test-')))
        self.enterContext(patch.object(settings,'storage_dir',self.root/'qdrant'))
        self.enterContext(patch.object(settings,'data_dir',self.root/'data'))
        self.enterContext(patch('src.store.get_embeddings',return_value=TinyEmbeddings()))
        self.addCleanup(close_client)
        self.sources=[save_and_ingest_document(path.read_bytes(),path.name) for path in create_fixture(self.root/'fixtures')]
        self.names=[s['filename'] for s in self.sources]
        self.prompts=[]
        def inference(prompt): self.prompts.append(prompt);return fake_research(prompt)
        self.enterContext(patch('src.research.invoke_llm',side_effect=inference))

    def test_comparison_balances_sources_and_separates_missing_conditions_and_conflicts(self):
        result=core_adapter.comparison(ComparisonRequest(filenames=self.names,goal=GOAL,criteria=CRITERIA))
        self.assertEqual(len(self.prompts),4)
        self.assertEqual([s.filename for s in result.sources],self.names)
        self.assertTrue(all([row.filename for row in criterion.sources]==self.names for criterion in result.criteria))
        self.assertTrue(all(row.status=='not_found' for row in result.criteria[3].sources))
        self.assertEqual({f.kind for f in result.findings},{'agreement','different_conditions','direct_conflict'})
        self.assertTrue(all(c.document_version for c in result.citations))
        exported=core_adapter.markdown(TypeAdapter(ExportRequest).validate_python({'feature':'comparison','result':result.model_dump()}))
        self.assertIn('Chi phí học phần',exported);self.assertIn('Chưa tìm thấy',exported);self.assertIn('version',exported)

    def test_report_modes_keep_every_source_and_roundtrip_export(self):
        for mode in ['study_guide','explanation','synthesis']:
            result=core_adapter.report(ReportRequest(filenames=self.names,goal='Lập đề cương khái niệm',mode=mode))
            self.assertEqual(result.mode,mode)
            self.assertEqual({c.filename for c in result.citations},set(self.names))
            text=core_adapter.markdown(TypeAdapter(ExportRequest).validate_python({'feature':'report','result':result.model_dump()}))
            self.assertIn('Đề cương',text);self.assertIn('Giới hạn',text)

    def test_one_source_comparison_and_too_many_sources_rejected(self):
        with self.assertRaises(ValidationError): ComparisonRequest(filenames=[self.names[0]],goal=GOAL,criteria=CRITERIA)
        with self.assertRaises(ValidationError): ReportRequest(filenames=[f'd{i}.md' for i in range(7)],goal=GOAL)

    def test_wrong_quote_marker_or_schema_never_returns_valid_artifact(self):
        for payload in ['not json',json.dumps({'criteria':[]}),json.dumps({'criteria':[{'criterion_id':'c1','status':'supported','statement':{'text':'A claim','evidence':[{'source_marker':'S999','quote':'An invented literal excerpt.'}]},'limitation':''}]}),json.dumps({'criteria':[{'criterion_id':'c1','status':'supported','statement':{'text':'A claim','evidence':[{'source_marker':'S1','quote':'An invented literal excerpt.'}]},'limitation':''}]})]:
            with self.subTest(payload=payload),patch('src.research.invoke_llm',return_value=payload):
                with self.assertRaises(LLMServiceError): core_adapter.comparison(ComparisonRequest(filenames=self.names[:2],goal=GOAL,criteria=['One criterion']))

    def test_wholly_missing_criterion_is_explicit_and_does_not_invent_a_synthesis(self):
        def missing(prompt):
            data=json.loads(prompt.split('DATA (JSON):\n')[1]);return json.dumps({'criteria':[{'criterion_id':row['id'],'status':'not_found','statement':None,'limitation':'Chưa tìm thấy trong các đoạn đã xét.'} for row in data['criteria']]})
        with patch('src.research.invoke_llm',side_effect=missing) as calls:
            result=core_adapter.comparison(ComparisonRequest(filenames=self.names[:2],goal='Tuition',criteria=['Học phí']))
        self.assertEqual(calls.call_count,2);self.assertEqual(result.conclusion,[]);self.assertEqual(result.findings,[]);self.assertEqual(result.citations,[])

    def test_unselected_source_never_enters_any_model_pass(self):
        result=core_adapter.report(ReportRequest(filenames=[self.names[0]],goal='Study'))
        self.assertEqual({c.filename for c in result.citations},{self.names[0]})
        self.assertTrue(all(self.names[1] not in p and self.names[2] not in p for p in self.prompts))

    def test_graph_pipeline_preserves_scope_roundtrips_and_exports(self):
        result=core_adapter.graph(GraphRequest(filenames=self.names,goal='MSE and prediction error'))
        self.assertEqual(len(self.prompts),3)
        self.assertGreaterEqual(len(result.edges),1)
        self.assertEqual({s.filename for s in result.sources},set(self.names))
        self.assertEqual({c.filename for c in result.citations},set(self.names))
        from backend.schemas.notebooks import WorkspaceState
        state=WorkspaceState(schema_version=3,document_filenames=self.names,graph_artifacts=[{'id':'graph-one','title':'Learning','createdAt':1,'sourceFilenames':self.names,'pages':[],'topic':None,'result':result.model_dump()}])
        restored=WorkspaceState.model_validate_json(state.model_dump_json())
        self.assertEqual(restored.graph_artifacts[0].result,result)
        self.assertEqual(restored.mindmap_artifacts,[])
        for version in (1,2):
            old=WorkspaceState.model_validate({'schema_version':version,'document_filenames':self.names})
            self.assertEqual(old.graph_artifacts,[]);self.assertEqual(old.comparison_artifacts,[])
        text=core_adapter.markdown(TypeAdapter(ExportRequest).validate_python({'feature':'graph','result':result.model_dump()}))
        self.assertIn('MSE',text);self.assertIn('version',text)

    def test_cancel_between_source_passes_and_failure_do_not_continue(self):
        from src.llm import llm_task
        from src.providers.contracts import ExecutionContext,ModelSelection,CancellationToken
        token=CancellationToken();calls=[]
        def cancelled(prompt):
            calls.append(prompt);token.cancel();return fake_research(prompt)
        with patch('src.research.invoke_llm',side_effect=cancelled),llm_task(ExecutionContext(ModelSelection('gemini','fake')),cancellation=token):
            with self.assertRaises(LLMServiceError): core_adapter.report(ReportRequest(filenames=self.names,goal='Study'))
        self.assertEqual(len(calls),1)
        def failed(prompt):
            calls.append(prompt)
            if len(calls)>1: raise LLMServiceError(502,'Temporary provider failure')
            return fake_research(prompt)
        calls.clear()
        with patch('src.research.invoke_llm',side_effect=failed):
            with self.assertRaises(LLMServiceError): core_adapter.comparison(ComparisonRequest(filenames=self.names,goal=GOAL,criteria=CRITERIA))
        self.assertEqual(len(calls),2)

    def test_bad_evidence_is_rejected_on_reload_and_export(self):
        from backend.schemas.api import GraphResponse
        result=core_adapter.graph(GraphRequest(filenames=self.names,goal='MSE and prediction error')).model_dump()
        result['edges'][0]['statement']['evidence'][0]['source_marker']='S999'
        with self.assertRaises(ValidationError): GraphResponse.model_validate(result)
        with self.assertRaises(ValidationError): TypeAdapter(ExportRequest).validate_python({'feature':'graph','result':result})

    def test_task_pipeline_model_metadata_cancel_error_and_notebook_isolation(self):
        import time
        from threading import Event
        from uuid import uuid4
        from backend.schemas.tasks import TaskRequest
        from backend.schemas.notebooks import NotebookCreate,NotebookUpdate
        from backend.services import notebooks
        from backend.services.generation import TaskRegistry
        from backend.tests.test_generation_tasks import FakeConnections
        from src.providers.contracts import LLMResult,Completion,ProviderCapabilities
        from src.llm import invoke_llm as real_invoke
        calls=[];mode=['complete'];entered=Event()
        class Provider:
            capabilities=ProviderCapabilities(streaming=True)
            def generate(provider,request,context,*,credential,cancellation):
                return next(provider.stream(request,context,credential=credential,cancellation=cancellation)).result
            def stream(provider,request,context,*,credential,cancellation):
                calls.append(context)
                if mode[0]=='cancel' and len(calls)==2:
                    entered.set()
                    while not cancellation.wait(.01):pass
                    cancellation.raise_if_cancelled()
                if mode[0]=='error' and len(calls)==2:raise LLMServiceError(502,'Temporary failure')
                yield Completion(LLMResult(text=fake_research(request.prompt),provider='chatgpt',model='resolved-alpha'))
        registry=TaskRegistry();self.addCleanup(registry.close)
        notebook=notebooks.create_notebook(NotebookCreate(title='Research task fixture'))
        notebook.state.document_filenames=self.names;notebook.state.selected=self.names
        notebooks.update_notebook(notebook.id,NotebookUpdate(title=notebook.title,icon=notebook.icon,state=notebook.state))
        other=notebooks.create_notebook(NotebookCreate(title='Unrelated notebook'))
        def collect(job):
            events=[];end=time.monotonic()+8
            while time.monotonic()<end:
                event=job.read()
                if event:
                    events.append(event)
                    if event['type'] in ('completed','error','cancelled'):return events
            self.fail('No terminal event')
        with patch('src.research.invoke_llm',side_effect=real_invoke),patch('src.llm.get_provider',return_value=Provider()),patch('backend.services.chatgpt_auth.get_manager',return_value=FakeConnections()):
            for feature in ('comparison','report','graph'):
                calls.clear();body={'id':str(uuid4()),'notebook_id':notebook.id,'feature':feature,'model':{'provider':'chatgpt','model':'alpha','connection_id':'fake'},'input':{'filenames':self.names,'goal':GOAL,**({'criteria':CRITERIA} if feature=='comparison' else {})}}
                parsed=TypeAdapter(TaskRequest).validate_python(body);job=registry.start('owner',parsed)
                parsed.model.model='beta';parsed.input.filenames=[]
                events=collect(job);self.assertEqual(events[-1]['type'],'completed',events[-1])
                self.assertNotIn('delta',[e['type'] for e in events])
                exported=core_adapter.markdown(TypeAdapter(ExportRequest).validate_python({'feature':feature,'result':events[-1]['result']}))
                self.assertIn('resolved-alpha',exported)
                metadata=events[-1]['result']['generation'];self.assertEqual(metadata['calls'],3 if feature=='graph' else 4)
                self.assertEqual(metadata['source_filenames'],self.names);self.assertEqual(metadata['requested_model'],'alpha')
                self.assertTrue(all(c.selection.model=='alpha' for c in calls));self.assertIsNone(metadata['usage'])
                registry.release(job)
            for failure in ('cancel','error'):
                mode[0]=failure;calls.clear();entered.clear();body['id']=str(uuid4());body['feature']='report';body['input'].pop('criteria',None)
                job=registry.start('owner',TypeAdapter(TaskRequest).validate_python(body))
                if failure=='cancel':
                    self.assertTrue(entered.wait(5));registry.cancel('owner',job.request.id)
                events=collect(job);self.assertEqual(events[-1]['type'],'cancelled' if failure=='cancel' else 'error')
                self.assertEqual(len(calls),2);self.assertNotIn('completed',[e['type'] for e in events]);registry.release(job)
        for identifier in (notebook.id,other.id):
            state=notebooks.get_notebook(identifier).state
            self.assertEqual(state.comparison_artifacts,[]);self.assertEqual(state.report_artifacts,[]);self.assertEqual(state.graph_artifacts,[])

    def test_partial_coverage_balanced_retrieval_and_bounds_before_model_calls(self):
        from src import research
        from src.rag import fetch_all_chunks,retrieve
        from src.llm import llm_task
        from src.providers.contracts import ExecutionContext,ModelSelection
        def expanded(*,filters):
            chunks=fetch_all_chunks(filters=filters)
            return chunks*2 if filters['filename']==self.names[0] else chunks
        with patch.object(research,'fetch_all_chunks',side_effect=expanded),patch.object(research,'retrieve',wraps=retrieve) as retrieval:
            result=core_adapter.report(ReportRequest(filenames=self.names[:2],goal='Study'))
        self.assertEqual(result.sources[0].coverage,'selected_excerpt');self.assertEqual(result.sources[1].coverage,'complete')
        self.assertEqual(retrieval.call_count,1);self.assertEqual(retrieval.call_args.kwargs['filters']['filename'],self.names[0])
        self.prompts.clear()
        with llm_task(ExecutionContext(ModelSelection('gemini','fake')),max_calls=2):
            with self.assertRaises(LLMServiceError):core_adapter.report(ReportRequest(filenames=self.names[:2],goal='Study'))
        self.assertEqual(self.prompts,[])
        chunks=fetch_all_chunks(filters={'filename':self.names[0]})
        chunks[0]=chunks[0].model_copy(update={'text':'x'*60001})
        with patch.object(research,'fetch_all_chunks',return_value=chunks):
            with self.assertRaises(LLMServiceError):core_adapter.report(ReportRequest(filenames=[self.names[0]],goal='Study'))
        self.assertEqual(self.prompts,[])

    def test_workspace_addition_and_whole_store_rollback_preserve_old_data(self):
        from backend.services import notebooks
        from backend.schemas.notebooks import NotebookCreate,NotebookUpdate
        from src.data_guard import data_guard
        from src.migration import backup,verify_backup,rollback
        result=core_adapter.graph(GraphRequest(filenames=self.names,goal='MSE'))
        book=notebooks.create_notebook(NotebookCreate(title='Legacy compatible'))
        book.state.schema_version=2;book.state.document_filenames=self.names;book.state.selected=self.names
        book.state.notes=[{'id':'note-old','title':'My previous note','content':'Keep this text','createdAt':1,'updatedAt':1}]
        # Validate public serialized input as the real update API does.
        update=NotebookUpdate.model_validate({'title':book.title,'icon':book.icon,'state':book.state.model_dump(warnings=False)})
        old=notebooks.update_notebook(book.id,update)
        close_client()
        with data_guard(offline=True):backup(self.root/'phase05-backup')
        self.assertTrue(verify_backup(self.root/'phase05-backup'))
        state=old.state.model_dump();state['schema_version']=3;state['graph_artifacts']=[{'id':'new-graph','title':'MSE','createdAt':2,'sourceFilenames':self.names,'pages':[],'topic':None,'result':result.model_dump()}]
        notebooks.update_notebook(book.id,NotebookUpdate.model_validate({'title':book.title,'icon':book.icon,'state':state}))
        self.assertEqual(len(notebooks.get_notebook(book.id).state.graph_artifacts),1)
        restored=rollback(self.root/'phase05-backup');self.assertTrue(restored['restored'])
        recovered=notebooks.get_notebook(book.id)
        self.assertEqual(recovered.state,old.state);self.assertEqual(recovered.state.notes[0].content,'Keep this text')
        from src.store import list_documents
        self.assertEqual(len(list_documents()),3)
