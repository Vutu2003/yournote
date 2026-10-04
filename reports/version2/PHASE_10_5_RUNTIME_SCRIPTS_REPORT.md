# Phase 10.5 — Runtime Scripts Report

## Result

**PASS** — 2026-10-04. Local React/FastAPI startup, duplicate prevention, status, safe shutdown and restart passed. All test services are stopped. No generation endpoint, Gemini call, Qdrant operation, commit or push occurred. Phase 11 was not started.

## Scripts

- `scripts/start_all.sh`: starts FastAPI and Vite, checks readiness, prints URLs/log locations.
- `scripts/stop_all.sh`: stops verified frontend/backend sessions, frontend first; repeated stop succeeds.
- `scripts/status.sh`: reports RUNNING, STOPPED or UNHEALTHY without starting services.
- `scripts/runtime.py`: shared standard-library implementation for process ownership, locking and health checks.

Scripts resolve the root from their own location, use `.venv/bin/python`, prefer project-local Node/npm, bind to `127.0.0.1`, and install nothing. FastAPI explicitly uses **one worker**, without reload. Vite uses `--strictPort` to prevent silently changing ports.

PID ownership includes boot ID, process start time, executable, command and working directory. Dedicated process sessions allow stopping npm's frontend children. Recorded child identities also verify an orphaned session after its npm leader exits. A lock serializes runtime operations. Shutdown sends SIGTERM, waits up to eight seconds, and uses SIGKILL only for remaining verified process generations; no broad kill commands are used.

Existing `dev_backend.sh` / `dev_frontend.sh` remain unchanged for development. Legacy `start.sh` / `stop.sh` remain unchanged for the Gradio fallback.

## Startup Test

PASS: backend health and frontend returned HTTP 200. Both PID/log files were created; exactly one backend serving process ran, without a reload supervisor or Gradio. Startup completed in under one second in the initial observed run. Readiness is bounded to 20 seconds per component using local Python HTTP probes without ambient proxies.

Additional checks passed for launch from `/tmp`, project paths containing spaces, occupied-port refusal, concurrent-operation refusal, and rollback of a newly started backend when the frontend failed. Unmanaged listeners/processes were left untouched.

## Duplicate Start Test

PASS: repeated start reported existing backend/frontend PIDs and preserved the exact PID values. No duplicate backend or frontend instance was launched.

## Stop Test

PASS: frontend session and backend stopped, PID/ownership files were removed, and ports 5173/8000 had no listeners. A second stop printed **Research Notebook is not running.** and succeeded.

An unrelated test process survived shutdown. A live unrelated PID with a synthetic ownership record was rejected without signalling it. Dead/malformed records were cleaned safely. Verified frontend children were also stopped after terminating their own npm leader in a temporary fixture.

## Restart Test

PASS: completed start → health → stop → start → health → stop cycles. Restart produced fresh healthy PIDs. Final status/shutdown checks passed; no test service or PID file remains.

## Runtime URLs

- Frontend: `http://127.0.0.1:5173`
- API health: `http://127.0.0.1:8000/api/health`
- API docs: `http://127.0.0.1:8000/docs`

## Logs / PID Files

Ignored `.run/` contains `backend.log`, `frontend.log`, PID files while running, companion `.owner` process-identity records, and `runtime.lock`. Directory/file permissions are private (`0700` / `0600` for newly created entries). Identity records contain no credentials or environment values. Logs remain available after stop and are replaced on the next launch.

## Files Changed

Added the three executable shell scripts and shared `scripts/runtime.py`; added `.run/` to `.gitignore`; created this small report only. No README update was needed. Test harnesses and fixtures stayed under `/tmp`.

## Core Integrity

All **76 baseline files** retained their SHA-256 hashes, including application/backend/frontend source, existing scripts, PDFs, `.env`, package files and original Qdrant storage files. Required Git diffs for `src/`, `backend/`, `frontend/src/`, `app.py` and `requirements.txt` exactly match the pre-task snapshot: existing Phase 10 changes were preserved, with zero application/core changes from Phase 10.5.

`bash -n` passed for all new shell scripts; Python compilation and `git diff --check` passed. Git confirms `.run/` logs/PIDs are ignored.

## Recommended Commands

```bash
./scripts/start_all.sh
./scripts/status.sh
./scripts/stop_all.sh
```

Development: continue using `./scripts/dev_backend.sh` and `./scripts/dev_frontend.sh` in separate terminals. Their foreground processes remain controlled by those terminals; normal runtime scripts do not adopt or stop unmanaged development processes.

Next: **Phase 11 — Final Full-System Regression and Freeze**, not started here.
