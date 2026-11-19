"""One process owns embedded Qdrant; only index work holds this shared lock."""
from functools import wraps
from threading import RLock

core_lock = RLock()


def index_operation(function):
    @wraps(function)
    def locked(*args, **kwargs):
        with core_lock:
            return function(*args, **kwargs)
    return locked
