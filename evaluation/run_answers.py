"""Bounded real answer comparison, synthetic fixture only, live backend must be stopped.

Uses the already authorized YourNote account/model; never exports credentials.
"""
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import time
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def main():
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument('--model',required=True);args=parser.parse_args()
 import torch
 torch.set_num_threads(2)
 from jinja2 import Environment,FileSystemLoader,StrictUndefined
 from langchain_core.documents import Document
 from src.config import settings
 from src.indexing import index_chunks
 from src.store import ensure_collection,close_client
 from src.rag import answer,retrieve_vector,format_citations
 from src.llm import llm_task,invoke_llm
 from src.providers.contracts import CancellationToken,CredentialRef,ExecutionContext,ModelSelection
 from backend.services.chatgpt_auth import get_manager,shutdown
 fixture=json.loads(Path(__file__).with_name('fixture.json').read_text())
 selected={'exact_assignment','device_exact','semantic_translation','conflict','insufficient','injection','followup','strict_selection'}
 manager=get_manager();status=manager.status('phase04-evaluation')
 connection=status['active_connection_id']
 profile=next((p for p in status['profiles'] if p['id']==connection),None)
 if not profile or not profile['plan_enabled']: raise RuntimeError('No already authorized active connection for real evaluation.')
 # Keep the model the user already verified; do not pick an alternative automatically.
 model=args.model
 if model not in {m['slug'] for m in manager.catalog(connection)['models']}:
  raise RuntimeError('Previously verified model is no longer available; no fallback was selected.')
 baseline=Environment(loader=FileSystemLoader(str(Path(__file__).parent)),undefined=StrictUndefined).get_template('baseline_answer.jinja2')
 rows=[]
 try:
  with TemporaryDirectory(prefix='phase04-answers-') as directory,patch.object(settings,'storage_dir',Path(directory)/'qdrant'),patch.object(settings,'data_dir',Path(directory)/'data'):
   ensure_collection()
   index_chunks([Document(page_content=item['text'],metadata={k:v for k,v in item.items() if k!='text'}|{'source':'synthetic-fixture'}) for item in fixture['corpus']])
   for item in fixture['queries']:
    if item['id'] not in selected: continue
    for mode in ('baseline','hybrid'):
     records=[];token=CancellationToken();started=time.perf_counter()
     row={'id':item['id'],'kind':item['kind'],'mode':mode,'question':item['question'],'expected_chunks':item['expected_chunks']}
     try:
      context=ExecutionContext(ModelSelection('chatgpt',model),CredentialRef(connection))
      with manager.bind_task(connection,token) as resolver,llm_task(context,credential_resolver=resolver,cancellation=token,on_result=records.append,max_calls=1):
       filters={'filenames':item['filenames']}
       if mode=='baseline':
        chunks=retrieve_vector(item['question'],k=3,filters=filters)
        text=invoke_llm(baseline.render(question=item['question'],chunks=chunks))
        citations=format_citations(chunks)
       else:
        result=answer(item['question'],k=3,filters=filters,history=item.get('history',[]))
        text=result.answer;chunks=result.chunks;citations=result.citations
       row.update({'answer':text,'context_chunk_ids':[c.metadata.chunk_id for c in chunks],
                   'citations':[c.model_dump(exclude_none=True) for c in citations],'status':'completed'})
     except Exception as exc:
      row.update(status='error',error_type=type(exc).__name__)
      from src.errors import LLMServiceError
      if isinstance(exc,LLMServiceError): row['error_code']=exc.code.value
     row.update(duration_seconds=time.perf_counter()-started,calls=len(records),
                actual_models=[r.model for r in records if r.model],usage=[r.usage.__dict__ if hasattr(r.usage,'__dict__') else
                  {k:getattr(r.usage,k,None) for k in ('input_tokens','output_tokens','total_tokens')} if r.usage else None for r in records])
     rows.append(row)
     output=Path('reports/phase04/answers.json')
     output.write_text(json.dumps({'fixture_sha256':hashlib.sha256(Path(__file__).with_name('fixture.json').read_bytes()).hexdigest(),
       'requested_model':model,'max_attempts':16,'synthetic_material_only':True,'rows':rows},ensure_ascii=False,indent=2)+'\n')
     print(json.dumps({'case':item['id'],'mode':mode,'status':row['status'],'seconds':round(row['duration_seconds'],2),'calls':row['calls']}),flush=True)
     if row['status']=='error':
      return  # Never repeat requests after quota/auth/permission/model failure.
   close_client()
 finally:
  shutdown()
if __name__=='__main__': main()
