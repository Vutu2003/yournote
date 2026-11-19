"""Prepare synthetic UI fixtures without model calls or touching the user store."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.tests.test_research_phase05 import ResearchTests,GOAL,CRITERIA
from backend.services import core_adapter
from backend.schemas.api import ComparisonRequest,ReportRequest,GraphRequest

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='/tmp/phase05-ui-results.json');parser.add_argument('--live-graph',type=Path);args=parser.parse_args()
    case=ResearchTests();case.setUp()
    try:
        results={'comparison':core_adapter.comparison(ComparisonRequest(filenames=case.names,goal=GOAL,criteria=CRITERIA)).model_dump(),
            'report':core_adapter.report(ReportRequest(filenames=case.names,goal='Ôn tập các khái niệm chính')).model_dump(),
            'graph':core_adapter.graph(GraphRequest(filenames=case.names,goal='MSE và sai số dự đoán')).model_dump()}
        if args.live_graph:
            saved=json.loads(args.live_graph.read_text())
            if saved.get('synthetic_material_only') is not True:raise ValueError('UI fixture must use synthetic material only')
            results['graph']=next(row['result'] for row in saved['rows'] if row['feature']=='graph' and row['status']=='completed')
        import tempfile,shutil
        from evaluation.phase05_fixture import create_fixture
        with tempfile.TemporaryDirectory() as folder:
            paths=create_fixture(folder);shutil.copyfile(next(path for path in paths if path.suffix=='.pdf'),'/tmp/phase05-ui.pdf')
        Path(args.output).write_text(json.dumps(results,ensure_ascii=False),encoding='utf-8')
        print('Prepared isolated synthetic UI fixtures; model calls: 0.')
    finally:case.doCleanups()
