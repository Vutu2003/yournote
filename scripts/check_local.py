"""Run isolated regression/build/lint; never runs a real-model benchmark."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import time

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--ui',action='store_true');args=parser.parse_args()
    report={'date':datetime.now(timezone.utc).isoformat(),'real_model_calls':0,'steps':[]};out=ROOT/'reports/phase06';out.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(prefix='yournote-checks-') as directory:
        env={**os.environ,'RAG_STORAGE_DIR':directory+'/storage/qdrant','RAG_DATA_DIR':directory+'/data','RAG_CHATGPT_RUNTIME_DIR':directory+'/runtime','GEMINI_API_KEY':'','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','YOURNOTE_TEST_RESULT':directory+'/tests.json','PATH':str(ROOT/'.tools/node/bin')+os.pathsep+os.environ.get('PATH','')}
        code='''import json,os,unittest
class Recorded(unittest.TextTestResult):
 def startTest(self,test):super().startTest(test);self.events=getattr(self,'events',[])
 def addSuccess(self,test):super().addSuccess(test);self.events.append({'id':test.id(),'status':'passed'})
 def addError(self,test,err):super().addError(test,err);self.events.append({'id':test.id(),'status':'error'})
 def addFailure(self,test,err):super().addFailure(test,err);self.events.append({'id':test.id(),'status':'failed'})
 def addSkip(self,test,reason):super().addSkip(test,reason);self.events.append({'id':test.id(),'status':'skipped'})
suite=unittest.defaultTestLoader.discover('backend/tests');result=unittest.TextTestRunner(verbosity=1,resultclass=Recorded).run(suite)
open(os.environ['YOURNOTE_TEST_RESULT'],'w').write(json.dumps({'run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'cases':getattr(result,'events',[])}))
raise SystemExit(not result.wasSuccessful())
'''
        commands=[('backend_tests',[sys.executable,'-c',code]),('frontend_build',['npm','--prefix','frontend','run','build']),('frontend_lint',['npm','--prefix','frontend','run','lint'])]
        if args.ui:commands.extend([('prepare_ui',[sys.executable,'evaluation/prepare_research_ui.py']),('ui_studio',['node','evaluation/phase06/ui.mjs']),('ui_reading',['node','evaluation/phase06/ui_reading.mjs']),('ui_models',['node','evaluation/phase06/ui_models.mjs'])])
        for name,command in commands:
            start=time.monotonic();result=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True,timeout=300)
            row={'name':name,'exit_code':result.returncode,'seconds':time.monotonic()-start}
            if name=='backend_tests' and Path(env['YOURNOTE_TEST_RESULT']).exists():row['result']=json.loads(Path(env['YOURNOTE_TEST_RESULT']).read_text())
            if name=='frontend_lint':row['warnings']=(result.stdout+result.stderr).count('warning ')
            if name.startswith('ui_'):row['pass_lines']=[line for line in result.stdout.splitlines() if line.startswith('PASS ')]
            report['steps'].append(row);(out/'checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
            print(json.dumps({key:value for key,value in row.items() if key not in ('result','pass_lines')}),flush=True)
            if result.returncode:return 1
    return 0

if __name__=='__main__':raise SystemExit(main())
