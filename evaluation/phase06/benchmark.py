"""Preview by default. Live inference requires explicit --live and plan digest.

No private corpus, implicit model fallback, infinite repairs, or auto-run in tests.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from evaluation.phase06.bundle import ROOT,load_fixture


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def plan(models,subset='all',baseline_subset=False,max_calls=0,effort=None):
    fixture,policy=load_fixture()
    ids=[case['id'] for case in fixture['cases']] if subset=='all' else policy['controlled_subset'] if subset=='controlled8' else subset.split(',')
    if not ids or len(ids)!=len(set(ids)) or not set(ids)<={case['id'] for case in fixture['cases']}:raise ValueError('Unknown or duplicate case IDs.')
    if not models or len(models)!=len(set(models)):raise ValueError('Select explicit, unique model IDs.')
    jobs=[{'case_id':id,'model':model,'retriever':'hybrid'} for model in models for id in ids]
    if baseline_subset:jobs.extend({'case_id':id,'model':model,'retriever':'vector'} for model in models for id in ids if id in policy['controlled_subset'])
    body={'fixture_sha256':policy['fixture_sha256'],'policy_sha256':digest(policy),'models':models,'jobs':jobs,'max_model_calls':max_calls,'planned_model_calls':len(jobs),'fits_budget':len(jobs)<=max_calls,
        'effort':effort,'k':policy['k'],'same_prompt_and_contextual_query':True,'uses_chatgpt_plan':True,'automatic_retries':0}
    return {**body,'plan_sha256':digest(body)}


def retrieval(case,mapping,mode,k):
    from evaluation.phase06.bundle import case_scope,case_history,evidence_metrics
    from src.conversation import contextual_query
    from src.rag import retrieve,retrieve_vector,format_citations
    from src.grounding import verify_citation
    query=contextual_query(case['question'],case_history(case,mapping));start=time.perf_counter()
    chunks=(retrieve if mode=='hybrid' else retrieve_vector)(query,k=k,filters=case_scope(case,mapping))
    elapsed=(time.perf_counter()-start)*1000
    citations=format_citations(chunks)
    for citation in citations:verify_citation(citation)
    return chunks,{**evidence_metrics(case,chunks,mapping),'duration_ms':elapsed,'locator_checks':len(citations),'invalid_marker_or_locator':0}


def summarize_retrieval(rows):
    answerable=[row for row in rows if row['evidence_hit'] is not None]
    return {'cases':len(rows),'answerable_cases':len(answerable),'evidence_hit':statistics.mean(row['evidence_hit'] for row in answerable) if answerable else None,
        'macro_evidence_recall':statistics.mean(row['evidence_recall'] for row in answerable) if answerable else None,'scope_leaks':sum(row['scope_leaks'] for row in rows),
        'invalid_marker_or_locator':sum(row['invalid_marker_or_locator'] for row in rows),'warm_median_ms':statistics.median(row['duration_ms'] for row in rows),'warm_p95_ms':sorted(row['duration_ms'] for row in rows)[max(0,__import__('math').ceil(.95*len(rows))-1)]}


def run_retrieval(output):
    from evaluation.phase06.bundle import isolated_index
    fixture,policy=load_fixture();rows=[];start=time.perf_counter()
    with isolated_index() as mapping:
        cold=time.perf_counter()-start
        for mode in ('vector','hybrid'):
            for case in fixture['cases']:
                timings=[]
                for _ in range(policy['retrieval_repetitions']):chunks,metrics=retrieval(case,mapping,mode,policy['k']);timings.append(metrics['duration_ms'])
                rows.append({'case_id':case['id'],'group':case['group'],'retriever':mode,**metrics,'duration_ms':statistics.median(timings),'returned_chunk_ids':[chunk.metadata.chunk_id for chunk in chunks]})
    result={'date':datetime.now(timezone.utc).isoformat(),'fixture_sha256':policy['fixture_sha256'],'policy_sha256':digest(policy),'model_calls':0,'embedding':'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2','k':policy['k'],'cold_embedding_and_index_seconds':cold,
        'repetitions':policy['retrieval_repetitions'],'baseline_definition':policy['baseline'],'summary':{mode:summarize_retrieval([row for row in rows if row['retriever']==mode]) for mode in ('vector','hybrid')},'rows':rows}
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result['summary'],ensure_ascii=False))


def run_live(proposal,output,effort=None):
    if output.exists():raise ValueError('Output already exists; select a new path, do not overwrite results.')
    if not proposal['fits_budget']:raise ValueError('Planned calls exceed the explicit budget.')
    from backend.services.chatgpt_auth import get_manager,shutdown
    from evaluation.phase06.bundle import isolated_index,case_history
    from src.llm import llm_task
    from src.providers.contracts import CancellationToken,CredentialRef,ExecutionContext,ModelSelection,GenerationParameters
    from src.rag import answer_from_chunks
    from src.errors import LLMServiceError
    from src.grounding import verify_citation
    fixture,policy=load_fixture();cases={case['id']:case for case in fixture['cases']};manager=get_manager()
    status=manager.status('phase06-benchmark');connection=status['active_connection_id']
    profile=next((profile for profile in status['profiles'] if profile['id']==connection),None)
    if not profile or not profile['plan_enabled']:raise ValueError('No authorized plan connection; no fallback.')
    catalog={model['slug']:model for model in manager.catalog(connection)['models']}
    for model in proposal['models']:
        if model not in catalog:raise ValueError('Requested model is not granted; no fallback.')
        if effort and effort not in catalog[model].get('supported_reasoning_levels',[]):raise ValueError('Selected effort is not supported.')
    result={'schema_version':1,'date':datetime.now(timezone.utc).isoformat(),'synthetic_material_only':True,'plan':proposal,'effort':effort,'rows':[],
        'manual_review':'Not assessed yet; automatic integrity is not semantic answer quality.','history':'Seeded completed synthetic turns; same history in both arms; not live multi-turn session latency.'}
    def save():output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    try:
        with isolated_index() as mapping:
            context_cache={}
            for job in proposal['jobs']:
                case=cases[job['case_id']];key=(case['id'],job['retriever']);records=[];token=CancellationToken();start=time.perf_counter();row={**job,'group':case['group'],'question':case['question'],'status':'error'}
                try:
                    if key not in context_cache:context_cache[key]=retrieval(case,mapping,job['retriever'],proposal['k'])
                    chunks,metrics=context_cache[key];row.update(retrieval=metrics,context=[{'text':c.text,'metadata':c.metadata.model_dump(exclude={'source'},exclude_none=True)} for c in chunks])
                    context=ExecutionContext(ModelSelection('chatgpt',job['model']),CredentialRef(connection),parameters=GenerationParameters(reasoning_effort=effort))
                    with manager.bind_task(connection,token) as resolver,llm_task(context,credential_resolver=resolver,cancellation=token,on_result=records.append,max_calls=1):
                        answer=answer_from_chunks(case['question'],chunks,history=case_history(case,mapping));resolver(context.credential_ref)
                    for citation in answer.citations:verify_citation(citation)
                    row.update(status='completed',answer=answer.answer,citations=[c.model_dump(exclude_none=True) for c in answer.citations])
                except Exception as exc:
                    row.update(error_type=type(exc).__name__,error_code=exc.code.value if isinstance(exc,LLMServiceError) else 'benchmark_error')
                row.update(duration_seconds=time.perf_counter()-start,calls=len(records),actual_models=[record.model for record in records if record.model],usage=[{key:getattr(record.usage,key,None) for key in ('input_tokens','output_tokens','total_tokens')} if record.usage else None for record in records])
                row['review_sha256']=digest({key:row.get(key) for key in ('case_id','model','retriever','status','answer','citations','context')})
                result['rows'].append(row);save();print(json.dumps({'case':case['id'],'model':job['model'],'retriever':job['retriever'],'status':row['status'],'calls':row['calls'],'seconds':round(row['duration_seconds'],2)}),flush=True)
                if row['status']!='completed':break  # Stop on any error, never repeat quota/auth/model failure.
    finally:shutdown()
    return 0 if len(result['rows'])==len(proposal['jobs']) and all(row['status']=='completed' for row in result['rows']) else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--models',nargs='+',default=['gpt-6.1-terra']);parser.add_argument('--subset',default='all');parser.add_argument('--baseline-subset',action='store_true');parser.add_argument('--max-calls',type=int,default=0);parser.add_argument('--live',action='store_true');parser.add_argument('--confirm-plan-sha');parser.add_argument('--effort');parser.add_argument('--retrieval-only',action='store_true');parser.add_argument('--output',type=Path,default=Path('reports/phase06/answers.json'));args=parser.parse_args()
    if not 0<=args.max_calls<=120:parser.error('max-calls must be 0..120')
    if args.retrieval_only:
        if args.live:parser.error('retrieval-only cannot use --live')
        import torch;torch.set_num_threads(2)
        run_retrieval(args.output);return 0
    proposal=plan(args.models,args.subset,args.baseline_subset,args.max_calls,args.effort)
    if not args.live:print(json.dumps(proposal,ensure_ascii=False,indent=2));return 0
    if args.confirm_plan_sha!=proposal['plan_sha256']:parser.error('Preview this exact plan and pass its plan_sha256 before --live.')
    import torch;torch.set_num_threads(2)
    return run_live(proposal,args.output,args.effort)

if __name__=='__main__':raise SystemExit(main())
