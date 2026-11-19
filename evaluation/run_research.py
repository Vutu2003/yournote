"""Phase05 bounded live smoke on invented learning materials, never user corpus.

Run with the live backend stopped (embedded Qdrant has one owner).
Requires an already authorized plan connection and explicit model; no fallback/retry.
"""
import argparse
import json
from pathlib import Path
import socket
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--model',required=True);args=parser.parse_args()
    with socket.socket() as probe:
        if probe.connect_ex(('127.0.0.1',8000))==0: raise RuntimeError('Stop the live backend before running isolated model evaluation.')
    import torch
    torch.set_num_threads(2)
    from src.config import settings
    from src.store import close_client
    from src.indexing import save_and_ingest_document
    from backend.services.chatgpt_auth import get_manager,shutdown
    from backend.services.generation import TaskRegistry
    from backend.services import notebooks,core_adapter
    from backend.schemas.notebooks import NotebookCreate,NotebookUpdate
    from backend.schemas.tasks import TaskRequest
    from backend.schemas.api import ExportRequest
    from pydantic import TypeAdapter
    from evaluation.phase05_fixture import create_fixture,GOAL,CRITERIA
    manager=get_manager();status=manager.status('phase05-evaluation');connection=status['active_connection_id']
    profile=next((p for p in status['profiles'] if p['id']==connection),None)
    if not profile or not profile['plan_enabled']: raise RuntimeError('No already authorized plan connection.')
    if args.model not in {m['slug'] for m in manager.catalog(connection)['models']}:
        raise RuntimeError('Requested model is unavailable. No alternative was selected.')
    output=Path('reports/phase05');output.mkdir(exist_ok=True,parents=True)
    proof={'synthetic_material_only':True,'requested_model':args.model,'max_planned_model_calls':7,'prior_attempt':{'completed_comparison_calls':4,'export_failed_before_proof_write':True,'reason':'Fixed generation metadata passed into strict core export schema; mock regression added before rerun'},'automatic_repairs':0,'rows':[]}
    registry=TaskRegistry()
    try:
        with TemporaryDirectory(prefix='phase05-live-') as directory,patch.object(settings,'storage_dir',Path(directory)/'qdrant'),patch.object(settings,'data_dir',Path(directory)/'data'):
            sources=[save_and_ingest_document(path.read_bytes(),path.name) for path in create_fixture(Path(directory)/'fixtures')]
            names=[source['filename'] for source in sources]
            notebook=notebooks.create_notebook(NotebookCreate(title='Synthetic Phase05 smoke'))
            notebook.state.document_filenames=names;notebook.state.selected=names
            notebooks.update_notebook(notebook.id,NotebookUpdate(title=notebook.title,icon=notebook.icon,state=notebook.state))
            for feature in ('comparison','graph'):
                goal=GOAL if feature=='comparison' else 'Liên kết MSE, sai số dự đoán, hồi quy tuyến tính, gradient descent và chuẩn hóa đặc trưng; chỉ quan hệ được nêu rõ trong nguồn.'
                body={'id':str(uuid4()),'notebook_id':notebook.id,'feature':feature,'model':{'provider':'chatgpt','model':args.model,'connection_id':connection},
                      'input':{'filenames':names,'goal':goal,**({'criteria':CRITERIA} if feature=='comparison' else {})}}
                job=registry.start('phase05-live',TypeAdapter(TaskRequest).validate_python(body));row={'feature':feature,'progress':[]}
                while True:
                    event=job.read()
                    if not event: continue
                    if event['type']=='progress': row['progress'].append(event)
                    if event['type'] in ('completed','error','cancelled'):
                        row['status']=event['type']
                        if event['type']=='completed':
                            row['result']=event['result']
                            (output/'live-smoke-in-progress.json').write_text(json.dumps({**proof,'current':row},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
                            export=core_adapter.markdown(TypeAdapter(ExportRequest).validate_python({'feature':feature,'result':event['result']}))
                            (output/f'live-{feature}.md').write_text(export,encoding='utf-8')
                            from backend.schemas.notebooks import WorkspaceState
                            state=notebooks.get_notebook(notebook.id).state
                            dumped=state.model_dump()
                            dumped[f'{feature}_artifacts']=[{'id':feature,'title':feature,'createdAt':1,'sourceFilenames':names,'pages':[],'topic':goal,'result':event['result']}]
                            state=WorkspaceState.model_validate(dumped)
                            notebooks.update_notebook(notebook.id,NotebookUpdate(title=notebook.title,icon=notebook.icon,state=state))
                            loaded=notebooks.get_notebook(notebook.id).state
                            row['persisted_roundtrip']=getattr(loaded,f'{feature}_artifacts')[0].result.model_dump()==event['result']
                        else: row.update(code=event.get('code'),detail=event.get('detail'))
                        break
                registry.release(job);proof['rows'].append(row)
                (output/'live-smoke.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
                print(json.dumps({'feature':feature,'status':row['status'],'calls':row.get('result',{}).get('generation',{}).get('calls'),'roundtrip':row.get('persisted_roundtrip')}),flush=True)
                if row['status']!='completed': return 1
            close_client()
    finally:
        registry.close();shutdown()
    return 0

if __name__=='__main__':raise SystemExit(main())
