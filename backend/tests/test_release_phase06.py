"""Release gates and benchmark planner; no network/model inference."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from evaluation.phase06.bundle import load_fixture,write_materials,evidence_metrics
from evaluation.phase06.benchmark import plan,digest
from src.document_parser import parse_file


class ReleaseTests(unittest.TestCase):
    def test_frozen_dataset_distribution_gold_and_formats(self):
        fixture,policy=load_fixture()
        self.assertEqual({group:sum(c['group']==group for c in fixture['cases']) for group in ('single','multi','insufficient','followup')},{'single':10,'multi':8,'insufficient':6,'followup':6})
        self.assertEqual(policy['quality_gates']['supported_relevant_answers_min_rate'],.85)
        with tempfile.TemporaryDirectory() as directory:
            paths=write_materials(directory)
            parsed={key:parse_file(path) for key,path in paths.items()}
            self.assertEqual({p.suffix for p in paths.values()},{'.docx','.pdf','.md','.txt'})
            for case in fixture['cases']:
                self.assertTrue(set(case['sources'])<=set(paths))
                for ref in case['expected_evidence']:
                    self.assertIn(ref['source'],case['sources'])
                    self.assertTrue(any(ref['quote'] in block['text'] and (not ref.get('locator') or block['locator']==ref['locator']) for block in parsed[ref['source']]['blocks']),case['id'])
            hashes={key:__import__('hashlib').sha256(path.read_bytes()).hexdigest() for key,path in paths.items()}
            self.assertEqual(hashes,{key:__import__('hashlib').sha256(path.read_bytes()).hexdigest() for key,path in write_materials(directory).items()})

    def test_benchmark_preview_budget_subset_and_effort_are_bound(self):
        full=plan(['alpha'],baseline_subset=True,max_calls=38)
        self.assertEqual(full['planned_model_calls'],38);self.assertTrue(full['fits_budget'])
        self.assertFalse(plan(['alpha','beta'],baseline_subset=True,max_calls=38)['fits_budget'])
        self.assertEqual(plan(['alpha'],subset='controlled8',max_calls=8)['planned_model_calls'],8)
        self.assertNotEqual(full['plan_sha256'],plan(['alpha'],baseline_subset=True,max_calls=38,effort='high')['plan_sha256'])
        for invalid in ('missing','s01,s01'):
            with self.assertRaises(ValueError):plan(['alpha'],subset=invalid)

    def test_benchmark_cli_preview_never_initializes_auth_or_embedding(self):
        code="import sys; from unittest.mock import patch; import evaluation.phase06.benchmark as b; sys.argv=['benchmark','--models','alpha','--max-calls','30']; b.main(); assert not any(n in sys.modules for n in ('src.rag','torch','backend.services.chatgpt_auth'))"
        result=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['planned_model_calls'],30)

    def test_live_missing_confirmation_rejected_before_provider(self):
        result=subprocess.run([sys.executable,'evaluation/phase06/benchmark.py','--live','--max-calls','30'],capture_output=True,text=True,timeout=15)
        self.assertNotEqual(result.returncode,0);self.assertIn('Preview this exact plan',result.stderr)

    def test_runtime_stale_identity_never_stops_an_unrelated_process(self):
        spec=importlib.util.spec_from_file_location('phase06_runtime',Path('scripts/runtime.py'));runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)
        with tempfile.TemporaryDirectory() as directory,patch.object(runtime,'RUN',Path(directory)):
            child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(20)'])
            try:
                current=runtime.process(child.pid)
                record={'pid':child.pid,'boot':runtime.BOOT_ID,'start':current['start'],'exe':str(Path(sys.executable).resolve()),'members':[]}
                (runtime.RUN/'backend.pid').write_text(str(child.pid));(runtime.RUN/'backend.owner').write_text(json.dumps(record))
                runtime.stop()
                self.assertIsNone(child.poll());self.assertFalse((runtime.RUN/'backend.pid').exists())
            finally:child.terminate();child.wait(timeout=5)

    def test_review_digest_changes_when_answer_or_evidence_changes(self):
        old={'answer':'A [S1]','context':['Verified passage']}
        self.assertNotEqual(digest(old),digest({**old,'answer':'B [S1]'}))
        self.assertNotEqual(digest(old),digest({**old,'context':['Different passage']}))

    def test_evidence_metric_compares_real_locator_fields_not_optional_defaults(self):
        from src.schemas import ChunkMetadata,RetrievedChunk
        fixture,_=load_fixture();case=next(c for c in fixture['cases'] if c['id']=='s07')
        quote=case['expected_evidence'][0]['quote']
        mapping={'slides':{'filename':'slides.pdf','document_version':'a'*64}}
        chunk=RetrievedChunk(text=quote,score=0,metadata=ChunkMetadata(source='synthetic',filename='slides.pdf',document_id='slide',document_version='a'*64,chunk_id='slide:1:0',page=1,locator={'kind':'page','page':1}))
        result=evidence_metrics(case,[chunk],mapping)
        self.assertEqual(result['evidence_recall'],1)
        wrong=chunk.model_copy(deep=True);wrong.metadata.locator.page=2
        self.assertEqual(evidence_metrics(case,[wrong],mapping)['evidence_recall'],0)

    def test_empty_answer_subset_is_unknown_not_a_perfect_quality_score(self):
        from evaluation.phase06.review import summarize_answers
        result=summarize_answers([],set())
        self.assertEqual(result['cases'],0);self.assertIsNone(result['pass_rate']);self.assertIsNone(result['p95_seconds'])
        self.assertIsNone(result['reported_tokens']['total_tokens'])
