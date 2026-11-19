"""Cross-process guard: live API processes versus offline backup/migration."""
from contextlib import contextmanager
import fcntl
from src.config import settings


@contextmanager
def data_guard(*,offline=False):
    parent=settings.storage_dir.resolve().parent
    parent.mkdir(parents=True,exist_ok=True)
    if not offline and (parent/'.phase04-incomplete').exists():
        raise RuntimeError('An offline data migration/restore is incomplete. Finish migration or rollback before starting the backend.')
    with (parent/'.phase04-data.lock').open('a+b') as handle:
        try:
            fcntl.flock(handle, (fcntl.LOCK_EX if offline else fcntl.LOCK_SH) | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Stop the backend before document migration/rollback; the data store is in use.') from None
        try: yield
        finally: fcntl.flock(handle,fcntl.LOCK_UN)
