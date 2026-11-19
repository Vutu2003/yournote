"""Build a local handoff archive from an allowlist; no user data or credentials."""
import hashlib
import json
from pathlib import Path
import tarfile

ROOT=Path(__file__).resolve().parents[1]


def members():
    roots=['README.md','requirements-local.txt','requirements-local.lock','.env.example','backend','src','scripts','docs','frontend/src','frontend/public','frontend/dist','evaluation/phase06','evaluation/phase05_fixture.py','evaluation/prepare_research_ui.py','demo/materials']
    roots.extend('reports/phase06/'+name for name in ['evaluation.md','eligibility.md','answers.json','quality.json','retrieval.json','configuration.json','environment.json','checks.json','benchmark-plan.json','ui-proof.json','clean-runtime.json','clean-install.json','clean-frontend.json','clean-tests.json','backup-proof.json','preservation-proof.json','running-proof.json','functional-matrix.json'])
    frontend=['package.json','package-lock.json','index.html','vite.config.ts','tsconfig.json','tsconfig.app.json','tsconfig.node.json','README.md','eslint.config.js']
    roots.extend('frontend/'+name for name in frontend)
    result={}
    for name in roots:
        path=ROOT/name
        if not path.exists():continue
        for file in path.rglob('*') if path.is_dir() else [path]:
            if file.is_symlink():raise ValueError('Release refuses symlinks.')
            if not file.is_file() or '__pycache__' in file.parts or file.suffix in ('.pyc','.tsbuildinfo'):continue
            relative=file.relative_to(ROOT)
            if any(part in ('data','storage','.run','.git','.venv','node_modules') for part in relative.parts):raise ValueError('Private directory in release allowlist')
            if 'reports' in relative.parts and relative.parts[:2]!=('reports','phase06'):raise ValueError('Private report directory in release')
            if file.name.startswith('.env') and relative!=Path('.env.example'):raise ValueError('Private environment file in release')
            result[str(relative)]=file
    if 'frontend/dist/index.html' not in result:raise ValueError('Build frontend before packaging.')
    return result


def main():
    files=members();destination=ROOT/'releases';destination.mkdir(exist_ok=True)
    archive=destination/'yournote-local-0.6.0.tar.gz'
    def public_info(info):
        info.uid=info.gid=0;info.uname=info.gname='';info.mtime=0
        return info
    with tarfile.open(archive,'w:gz') as output:
        for relative,file in sorted(files.items()):output.add(file,arcname='yournote/'+relative,recursive=False,filter=public_info)
    sha=hashlib.sha256(archive.read_bytes()).hexdigest()
    inventory={'version':'0.6.0-local','private_local_handoff':True,'archive_sha256':sha,'bytes':archive.stat().st_size,'files':{relative:hashlib.sha256(file.read_bytes()).hexdigest() for relative,file in sorted(files.items())},'excluded':['.env','.run','OS keyring','storage','data','node_modules','.venv','.git','reports/slide']}
    (destination/'manifest.json').write_text(json.dumps(inventory,indent=2)+'\n');(destination/'SHA256SUMS').write_text(sha+'  '+archive.name+'\n')
    print(json.dumps({key:inventory[key] for key in ('version','private_local_handoff','bytes','archive_sha256')}))

if __name__=='__main__':main()
