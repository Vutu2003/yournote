"""Consistent offline data backup/verify/restore. Never includes OAuth/keyring/.env.

Restore previews by default. Stop all services and explicitly confirm to restore.
"""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['backup','verify','restore']);parser.add_argument('--backup',type=Path,required=True);parser.add_argument('--confirm-restore',choices=['RESTORE']);args=parser.parse_args()
    from src.migration import backup,verify_backup,rollback
    from src.data_guard import data_guard
    if args.action=='backup':
        with data_guard(offline=True):manifest=backup(args.backup)
        result={'action':'backup','verified_files':len(verify_backup(args.backup)['sha256']),'credentials_included':False}
    elif args.action=='verify':result={'action':'verify','verified_files':len(verify_backup(args.backup)['sha256'])}
    else:
        manifest=verify_backup(args.backup)
        if args.confirm_restore!='RESTORE':
            result={'action':'restore_preview','verified_files':len(manifest['sha256']),'replaces':['notebooks.sqlite','documents.sqlite','data','qdrant'],'requires_stopped_services':True,'next_step':'Repeat with --confirm-restore RESTORE; existing changes since the snapshot will be replaced.'}
        else:result=rollback(args.backup)
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
