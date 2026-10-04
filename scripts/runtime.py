"""Manage only the local React/FastAPI sessions created by these scripts (Linux)."""

import fcntl
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

PROJECT = Path(__file__).resolve().parent.parent
RUN = PROJECT / '.run'
PYTHON = PROJECT / '.venv/bin/python'
BOOT_ID = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
PORTS = {'backend': 8000, 'frontend': 5173}
URLS = {'backend': 'http://127.0.0.1:8000/api/health', 'frontend': 'http://127.0.0.1:5173/'}
# Local probes must not use an ambient HTTP proxy.
HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def process(pid):
    """Read PID identity, including start time to detect reuse; zombies are stopped."""
    try:
        fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
        if fields[0] in {'Z', 'X'}:
            return None
        return {'pid': pid, 'pgid': int(fields[2]), 'sid': int(fields[3]), 'start': fields[19]}
    except (OSError, ValueError, IndexError):
        return None


def group_members(pid):
    members = []
    for entry in Path('/proc').iterdir():
        if entry.name.isdigit():
            item = process(int(entry.name))
            if item and item['pgid'] == pid and item['sid'] == pid:
                members.append(item)
    return members


def forget(name):
    for suffix in ('pid', 'owner'):
        (RUN / f'{name}.{suffix}').unlink(missing_ok=True)


def ownership(name):
    """Validate our record, process generation, executable, command and cwd."""
    pid_path = RUN / f'{name}.pid'
    owner_path = RUN / f'{name}.owner'
    if not pid_path.exists() and not owner_path.exists():
        return None
    try:
        pid = int(pid_path.read_text().strip())
        record = json.loads(owner_path.read_text())
        if pid <= 1 or record['pid'] != pid or record['boot'] != BOOT_ID:
            raise ValueError('stale identity')
        current = process(pid)
        if current:
            cwd = PROJECT if name == 'backend' else PROJECT / 'frontend'
            args = Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')
            command = b' '.join(args).decode(errors='replace').strip()
            expected = ('-m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 1'
                        if name == 'backend' else 'npm run dev --host 127.0.0.1 --port 5173 --strictPort')
            if (current['start'] != record['start'] or current['pgid'] != pid
                    or current['sid'] != pid or Path(f'/proc/{pid}/cwd').resolve() != cwd
                    or os.readlink(f'/proc/{pid}/exe') != record['exe']
                    or expected not in command):
                raise ValueError('process does not match')
        else:
            if not group_members(pid):
                forget(name)
                return None
            # Prove an orphaned session using a child generation recorded while
            # its leader was alive. A group ID alone could come from stale state.
            if not any(process(member['pid']) == member for member in record.get('members', [])):
                raise ValueError('orphaned session cannot be verified')
        return record
    except (OSError, ValueError, KeyError, TypeError):
        print(f'{name.title()}: removed stale/unverified PID record; no process signalled.')
        forget(name)
        return None


def healthy(name):
    try:
        with HTTP.open(URLS[name], timeout=0.5) as response:
            if response.status != 200:
                return False
            return name != 'backend' or json.load(response).get('status') == 'ok'
    except (OSError, ValueError, urllib.error.URLError):
        return False


def listening(port):
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=0.3):
            return True
    except OSError:
        return False


def stop_component(name, record):
    # Revalidate immediately before signalling this dedicated process session.
    if ownership(name) != record:
        return False
    pid = record['pid']
    members = group_members(pid)
    if members:
        try:
            os.killpg(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    deadline = time.monotonic() + 8
    while group_members(pid) and time.monotonic() < deadline:
        time.sleep(0.1)
    remaining = group_members(pid)
    if remaining:
        # Kill only remaining processes whose generation still matches the
        # verified session. Never signal a recycled PID or a broad process name.
        for member in remaining:
            if process(member['pid']) == member:
                try:
                    os.kill(member['pid'], signal.SIGKILL)
                except ProcessLookupError:
                    pass
        deadline = time.monotonic() + 2
        while group_members(pid) and time.monotonic() < deadline:
            time.sleep(0.1)
    if group_members(pid):
        raise RuntimeError(f'{name.title()} did not stop; retained its PID record.')
    forget(name)
    return True


def commands():
    for path in (PYTHON, PROJECT / 'frontend/package.json', PROJECT / 'backend/main.py'):
        if not path.is_file():
            raise RuntimeError(f'Missing required file: {path}')
    env = os.environ.copy()
    local = PROJECT / '.tools/node/bin'
    if (local / 'node').is_file() and os.access(local / 'node', os.X_OK) and (local / 'npm').is_file() and os.access(local / 'npm', os.X_OK):
        env['PATH'] = str(local) + os.pathsep + env.get('PATH', '')
    node = shutil.which('node', path=env.get('PATH'))
    npm = shutil.which('npm', path=env.get('PATH'))
    if not node or not npm:
        raise RuntimeError('Node/npm unavailable. Set up Node before starting; nothing was installed.')
    env['PYTHONUNBUFFERED'] = '1'
    return {
        'backend': ([str(PYTHON), '-m', 'uvicorn', 'backend.main:app', '--host', '127.0.0.1', '--port', '8000', '--workers', '1'], PROJECT, str(PYTHON.resolve())),
        'frontend': ([npm, 'run', 'dev', '--', '--host', '127.0.0.1', '--port', '5173', '--strictPort'], PROJECT / 'frontend', str(Path(node).resolve())),
    }, env


def launch(name, spec, env):
    argv, cwd, executable = spec
    log_path = RUN / f'{name}.log'
    with log_path.open('wb') as log:
        child = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                 stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    current = process(child.pid)
    if current is None:
        raise RuntimeError(f'{name.title()} exited during startup. Log: {log_path}')
    record = {'pid': child.pid, 'start': current['start'], 'boot': BOOT_ID,
              'exe': executable, 'members': group_members(child.pid)}
    # The operation lock prevents readers from observing a partially written pair.
    (RUN / f'{name}.owner').write_text(json.dumps(record))
    (RUN / f'{name}.pid').write_text(f'{child.pid}\n')
    return record, child


def start():
    specs, env = commands()
    existing = {name: ownership(name) for name in PORTS}
    for name, record in existing.items():
        if record and not healthy(name):
            raise RuntimeError(f'{name.title()} PID {record["pid"]} is not healthy. Inspect .run/{name}.log and run stop_all.sh.')
        if not record and listening(PORTS[name]):
            raise RuntimeError(f'Port {PORTS[name]} is occupied by an unmanaged service; left untouched.')
    started = []
    try:
        for name in PORTS:
            if existing[name]:
                print(f'{name.title()} already running on PID {existing[name]["pid"]}.')
                continue
            record, child = launch(name, specs[name], env)
            started.append((name, record, child))
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                if child.poll() is not None:
                    raise RuntimeError(f'{name.title()} exited during startup. Log: .run/{name}.log')
                if healthy(name):
                    break
                time.sleep(0.2)
            else:
                raise RuntimeError(f'{name.title()} did not become ready within 20 seconds. Log: .run/{name}.log')
            if ownership(name) != record:
                raise RuntimeError(f'{name.title()} ownership check failed. Log: .run/{name}.log')
            record['members'] = group_members(record['pid'])
            (RUN / f'{name}.owner').write_text(json.dumps(record))
    except BaseException:
        for name, record, child in reversed(started):
            try:
                stop_component(name, record)
                child.wait(timeout=2)
            except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
                print(f'Cleanup: {error}', file=sys.stderr)
        raise
    print('Research Notebook started\n\nFrontend: http://127.0.0.1:5173\nAPI: http://127.0.0.1:8000\nAPI docs: http://127.0.0.1:8000/docs\nLogs: .run/backend.log, .run/frontend.log')


def stop():
    stopped = False
    failures = []
    for name in ('frontend', 'backend'):
        record = ownership(name)
        if record:
            try:
                stopped = stop_component(name, record) or stopped
                if listening(PORTS[name]):
                    failures.append(f'Port {PORTS[name]} still has a listener; no unverified process was stopped.')
            except (OSError, RuntimeError) as error:
                failures.append(str(error))
    if failures:
        raise RuntimeError(' '.join(failures))
    print('Research Notebook stopped.' if stopped else 'Research Notebook is not running.')


def status():
    print('Research Notebook status')
    for name in PORTS:
        record = ownership(name)
        state = 'RUNNING' if record and healthy(name) else 'UNHEALTHY' if record else 'STOPPED'
        print(f'{name.title()}: {state}' + (f' (PID {record["pid"]})' if record else '') + f'\n  {URLS[name]}')
        if not record and listening(PORTS[name]):
            print(f'  Port {PORTS[name]} occupied by an unmanaged listener; left untouched.')


def main():
    os.umask(0o077)
    RUN.mkdir(mode=0o700, exist_ok=True)
    # One lock serializes start/stop/status, including readiness and cleanup.
    with (RUN / 'runtime.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Another runtime operation is in progress. Try again shortly.')
        {'start': start, 'stop': stop, 'status': status}[sys.argv[1]]()


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
