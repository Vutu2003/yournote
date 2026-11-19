"""Run real local embedding/Qdrant retrieval on the frozen synthetic fixture only."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import sys
from tempfile import TemporaryDirectory
import time
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def main():
 parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=['baseline','hybrid'],required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
 import torch
 torch.set_num_threads(2)
 from langchain_core.documents import Document
 from src.config import settings
 from src.indexing import index_chunks
 from src.store import ensure_collection, close_client
 from src.rag import retrieve, retrieve_vector
 if args.mode=='baseline': retrieve=retrieve_vector
 fixture=json.loads(Path(__file__).with_name('fixture.json').read_text())
 with TemporaryDirectory(prefix='phase04-eval-') as directory, patch.object(settings,'storage_dir',Path(directory)/'qdrant'), patch.object(settings,'data_dir',Path(directory)/'data'):
  started=time.perf_counter();ensure_collection()
  documents=[Document(page_content=item['text'],metadata={k:v for k,v in item.items() if k!='text'}|{'source':'synthetic-fixture','section':None}) for item in fixture['corpus']]
  index_chunks(documents)
  cold=time.perf_counter()-started
  rows=[]
  for item in fixture['queries']:
   filters={'filenames':item['filenames']}
   if item.get('page'): filters['page']=item['page']
   query=item['question']
   if args.mode=='hybrid' and item.get('history'):
    from src.conversation import contextual_query
    query=contextual_query(query,item['history'])
   times=[]
   for _ in range(3):
    started=time.perf_counter();hits=retrieve(query,k=3,filters=filters);times.append((time.perf_counter()-started)*1000)
   ids=[hit.metadata.chunk_id for hit in hits]
   expected=set(item['expected_chunks'])
   rows.append({'id':item['id'],'kind':item['kind'],'expected':sorted(expected),'returned':ids,
    'hit_at_1':int(bool(expected) and ids[0] in expected) if ids else 0,
    'recall_at_3':len(expected.intersection(ids))/len(expected) if expected else None,
    'scope_leaks':sum(h.metadata.filename not in item['filenames'] or bool(item.get('page') and h.metadata.page!=item['page']) for h in hits),
    'latency_ms':statistics.median(times),'calls':0})
  close_client()
  answerable=[row for row in rows if row['recall_at_3'] is not None]
  result={'mode':args.mode,'fixture_sha256':hashlib.sha256(Path(__file__).with_name('fixture.json').read_bytes()).hexdigest(),
   'rag_code_sha256':hashlib.sha256((Path(__file__).resolve().parents[1]/'src/rag.py').read_bytes()).hexdigest(),
   'embedding_model':settings.embedding_model,'chunks':len(documents),'queries':len(rows),'k':3,'repetitions':3,
   'cold_load_and_index_seconds':cold,'hit_at_1':statistics.mean(r['hit_at_1'] for r in answerable),
   'recall_at_3':statistics.mean(r['recall_at_3'] for r in answerable),'scope_leaks':sum(r['scope_leaks'] for r in rows),
   'median_latency_ms':statistics.median(r['latency_ms'] for r in rows),'llm_calls':0,'rows':rows}
  args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
  print(json.dumps({k:v for k,v in result.items() if k!='rows'},ensure_ascii=False))
if __name__=='__main__': main()
