"""Run only with the backend stopped. Never includes credentials in backups."""
import argparse
from pathlib import Path
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.migration import migrate,rollback
parser=argparse.ArgumentParser();parser.add_argument('action',choices=['migrate','rollback']);parser.add_argument('--backup',type=Path,required=True)
args=parser.parse_args()
result=migrate(backup_directory=args.backup) if args.action=='migrate' else rollback(args.backup)
print(json.dumps(result,ensure_ascii=False))
