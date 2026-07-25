#!/usr/bin/env python3
"""gen_day059.py — generate Day 059: Background Jobs & Queues notebooks."""
from pathlib import Path
import json

ROOT    = Path(__file__).parent.parent
DAY     = "059"
SECTION = "04_real_apps"
OUT     = ROOT / SECTION / f"day_{DAY}"

(OUT / "exercises").mkdir(parents=True, exist_ok=True)
(OUT / "lessons").mkdir(parents=True, exist_ok=True)
(OUT / "project" / "solution").mkdir(parents=True, exist_ok=True)

# ── deliverable source ─────────────────────────────────────────────────────────
_BACKGROUND_API_SRC = '''\
"""background_api.py — Day 059: background job processing API.

Run:  uvicorn background_api:app --reload
Docs: http://localhost:8000/docs
"""
import os
import threading
import uuid
from datetime import datetime

import ollama
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

MODEL       = os.environ.get("MODEL", "llama3.2")
APP_VERSION = "1.0.0"


class _JobStore:
    """Thread-safe in-memory job store."""

    def __init__(self):
        self._jobs: dict = {}
        self._lock = threading.Lock()

    def create(self, job_id: str) -> None:
        with self._lock:
            self._jobs[job_id] = {"status": "pending"}

    def set_running(self, job_id: str) -> None:
        with self._lock:
            self._jobs[job_id] = {"status": "running"}

    def set_done(self, job_id: str, result: str) -> None:
        with self._lock:
            self._jobs[job_id] = {"status": "done", "result": result}

    def set_error(self, job_id: str, error: str) -> None:
        with self._lock:
            self._jobs[job_id] = {"status": "error", "error": error}

    def get(self, job_id: str) -> dict | None:
        with self._lock:
            data = self._jobs.get(job_id)
            return dict(data) if data else None


class SummarizeRequest(BaseModel):
    text: str = Field(min_length=1)


def build_api(process_fn=None) -> FastAPI:
    """Build the background job API.

    process_fn: optional callable(text: str) -> str for testing.
                If None, uses ollama.chat to summarize.
    """
    app = FastAPI(title="Background Job API", version=APP_VERSION)
    store = _JobStore()

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": APP_VERSION,
        }

    @app.post("/summarize", status_code=202)
    def submit_summarize(req: SummarizeRequest):
        job_id = uuid.uuid4().hex[:8]
        store.create(job_id)

        def worker():
            store.set_running(job_id)
            try:
                if process_fn is not None:
                    summary = process_fn(req.text)
                else:
                    prompt = "Summarize in one sentence:\\n\\n" + req.text[:3000]
                    resp = ollama.chat(
                        model=MODEL,
                        messages=[{"role": "user", "content": prompt}],
                    )
                    summary = resp["message"]["content"]
                store.set_done(job_id, summary)
            except Exception as exc:
                store.set_error(job_id, str(exc))

        threading.Thread(target=worker, daemon=True).start()
        return {"job_id": job_id, "status": "pending"}

    @app.get("/jobs/{job_id}")
    def get_job(job_id: str):
        job = store.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return job

    return app


app = build_api()

if __name__ == "__main__":
    import uvicorn
    PORT = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=PORT)
'''

# ── notebook helpers ───────────────────────────────────────────────────────────
def nb(cells):
    return {
        "nbformat": 4, "nbformat_minor": 5,
        "metadata": {"kernelspec": {"display_name": "Python 3",
                                    "language": "python",
                                    "name": "python3"}},
        "cells": cells,
    }

def md(src):
    return {"cell_type": "markdown", "metadata": {}, "source": src}

def code(src):
    return {"cell_type": "code", "metadata": {}, "source": src,
            "outputs": [], "execution_count": None}

def save(path, notebook):
    Path(path).write_text(json.dumps(notebook, indent=1))

# ══════════════════════════════════════════════════════════════════════════════
# EXERCISE 1 — build_background_tasks_api (FastAPI BackgroundTasks)
# ══════════════════════════════════════════════════════════════════════════════
_EX1_IMPORTS = """\
import secrets
from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel, Field
from starlette.testclient import TestClient
"""

_EX1_STUB = """\
def build_background_tasks_api(process_fn=None) -> FastAPI:
    \"\"\"Return a FastAPI app using BackgroundTasks for deferred processing.

    Endpoints:
      POST /run   body: {\"text\": \"...\"}  → 202 + {\"job_id\": \"...\", \"status\": \"pending\"}
      GET /jobs/{job_id}               → {\"status\": \"done\", \"result\": \"...\"}
                                         or 404 if unknown

    process_fn: optional callable(text: str) -> str for testing.
                If None, uppercase the text (trivial default).

    Key insight: TestClient runs BackgroundTasks synchronously, so the job
    is already done by the time the POST response is received in tests.
    \"\"\"
    # TODO: create app, _results dict, POST /run with background_tasks param,
    #       GET /jobs/{job_id}
    raise NotImplementedError
"""

_EX1_SOLUTION = """\
def build_background_tasks_api(process_fn=None) -> FastAPI:
    app = FastAPI()
    _results: dict = {}

    class _RunReq(BaseModel):
        text: str = Field(min_length=1)

    @app.post("/run", status_code=202)
    def run_task(req: _RunReq, background_tasks: BackgroundTasks):
        job_id = secrets.token_hex(4)
        _results[job_id] = {"status": "pending"}

        def process():
            try:
                result = process_fn(req.text) if process_fn else req.text.upper()
                _results[job_id] = {"status": "done", "result": result}
            except Exception as e:
                _results[job_id] = {"status": "error", "error": str(e)}

        background_tasks.add_task(process)
        return {"job_id": job_id, "status": "pending"}

    @app.get("/jobs/{job_id}")
    def get_job(job_id: str):
        if job_id not in _results:
            raise HTTPException(404, "Job not found")
        return _results[job_id]

    return app
"""

_EX1_CHECKS = """\
score, total = 0, 5
try:
    app    = build_background_tasks_api(process_fn=str.upper)
    client = TestClient(app, raise_server_exceptions=False)

    # TestClient runs BackgroundTasks synchronously before returning response
    r = client.post("/run", json={"text": "hello"})
    assert r.status_code == 202, f"Expected 202, got {r.status_code}"
    score += 1; print("\\u2705 POST /run returns 202")

    body = r.json()
    assert "job_id" in body, f"Expected job_id in response: {body}"
    score += 1; print("\\u2705 response contains job_id")

    # BackgroundTask already completed (TestClient is sync)
    job_id = body["job_id"]
    r2 = client.get(f"/jobs/{job_id}")
    assert r2.status_code == 200, f"Expected 200, got {r2.status_code}"
    data = r2.json()
    assert data["status"] == "done", f"Expected done, got {data}"
    assert data.get("result") == "HELLO", f"Expected 'HELLO', got {data.get('result')}"
    score += 1; print("\\u2705 job result is available after POST (TestClient sync)")

    # unknown job → 404
    r3 = client.get("/jobs/unknown_id")
    assert r3.status_code == 404, f"Expected 404, got {r3.status_code}"
    score += 1; print("\\u2705 unknown job returns 404")

    # empty text → 422
    r4 = client.post("/run", json={"text": ""})
    assert r4.status_code == 422, f"Expected 422 for empty text, got {r4.status_code}"
    score += 1; print("\\u2705 empty text returns 422")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX1 = nb([
    md("# Day 059 — Exercise 1: FastAPI BackgroundTasks\n\n"
       "FastAPI has a built-in `BackgroundTasks` mechanism: inject it as a route parameter, "
       "call `background_tasks.add_task(fn, *args)`, and FastAPI runs `fn` **after** "
       "the HTTP response is sent — so the client gets an immediate 202 response.\n\n"
       "**Test insight:** `TestClient` runs `BackgroundTasks` synchronously before "
       "returning the response object — so the job is already done by the time you "
       "read `r.json()`. No polling or sleeping needed in tests."),
    code(_EX1_IMPORTS),
    md("## Task\n\n"
       "Implement `build_background_tasks_api(process_fn=None)` — return a FastAPI app with:\n\n"
       "```\n"
       "POST /run   {\"text\": \"...\"}  → 202  {\"job_id\": \"abc123\", \"status\": \"pending\"}\n"
       "GET  /jobs/{job_id}          → 200  {\"status\": \"done\", \"result\": \"...\"}\n"
       "                             → 404  if job_id unknown\n"
       "```\n\n"
       "- Use `background_tasks: BackgroundTasks` as a route parameter (FastAPI injects it)\n"
       "- If `process_fn` is provided: use it instead of the default (uppercase)\n"
       "- Store results in a `dict` keyed by `job_id`\n"
       "- Return 422 automatically when `text` is empty (`Field(min_length=1)`)"),
    md("## Your Implementation"),
    code(_EX1_STUB),
    code(_EX1_SOLUTION),
    md("## Automated checks"),
    code(_EX1_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX1_SOLUTION + "```\n\n"
       "**Why it works:** `background_tasks.add_task(process)` registers `process` to "
       "run after the response is sent. With TestClient, it runs synchronously, so "
       "the result is available immediately. In production, it runs in the same "
       "thread pool as the ASGI server after the response bytes are flushed.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_01.ipynb", EX1)

# ══════════════════════════════════════════════════════════════════════════════
# EXERCISE 2 — JobQueue class
# ══════════════════════════════════════════════════════════════════════════════
_EX2_IMPORTS = """\
import threading
import time
import uuid
from typing import Any, Callable
"""

_EX2_STUB = """\
class JobQueue:
    \"\"\"Thread-safe in-memory job queue.

    submit(fn, *args) -> str
        Run fn(*args) in a background thread. Return job_id.
    status(job_id) -> str
        One of: 'pending', 'running', 'done', 'error', 'not_found'
    result(job_id) -> Any
        Return the result if status is 'done', else None.
    __len__() -> int
        Total number of jobs ever submitted.
    \"\"\"

    def __init__(self):
        # TODO: init _jobs dict and threading.Lock
        raise NotImplementedError

    def submit(self, fn: Callable, *args) -> str:
        raise NotImplementedError

    def status(self, job_id: str) -> str:
        raise NotImplementedError

    def result(self, job_id: str) -> Any:
        raise NotImplementedError

    def __len__(self) -> int:
        raise NotImplementedError
"""

_EX2_SOLUTION = """\
class JobQueue:
    def __init__(self):
        self._jobs: dict = {}
        self._lock = threading.Lock()

    def submit(self, fn: Callable, *args) -> str:
        job_id = uuid.uuid4().hex[:8]
        with self._lock:
            self._jobs[job_id] = {"status": "pending"}

        def worker():
            with self._lock:
                self._jobs[job_id]["status"] = "running"
            try:
                value = fn(*args)
                with self._lock:
                    self._jobs[job_id] = {"status": "done", "result": value}
            except Exception as exc:
                with self._lock:
                    self._jobs[job_id] = {"status": "error", "error": str(exc)}

        threading.Thread(target=worker, daemon=True).start()
        return job_id

    def status(self, job_id: str) -> str:
        with self._lock:
            return self._jobs.get(job_id, {}).get("status", "not_found")

    def result(self, job_id: str) -> Any:
        with self._lock:
            job = self._jobs.get(job_id, {})
            return job.get("result") if job.get("status") == "done" else None

    def __len__(self) -> int:
        with self._lock:
            return len(self._jobs)
"""

_EX2_CHECKS = """\
score, total = 0, 5

def _wait(q, job_id, timeout=2.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if q.status(job_id) not in ("pending", "running"):
            return
        time.sleep(0.01)

try:
    q = JobQueue()

    # submit and wait
    jid = q.submit(lambda: 42)
    _wait(q, jid)
    assert q.status(jid) == "done", f"Expected done, got {q.status(jid)}"
    assert q.result(jid) == 42, f"Expected 42, got {q.result(jid)}"
    score += 1; print("\\u2705 submit runs fn and stores result")

    # result None while not done
    barrier = threading.Event()
    def _slow_fn():
        barrier.wait()
        return "slow_result"
    jid2 = q.submit(_slow_fn)
    time.sleep(0.02)
    assert q.status(jid2) in ("pending", "running"), f"Got {q.status(jid2)}"
    assert q.result(jid2) is None, f"Got {q.result(jid2)}"
    barrier.set()
    _wait(q, jid2)
    assert q.result(jid2) == "slow_result", f"Got {q.result(jid2)}"
    score += 1; print("\\u2705 result() returns None while running")

    # unknown job
    assert q.status("nope") == "not_found", f"Got {q.status('nope')}"
    score += 1; print("\\u2705 unknown job_id → 'not_found'")

    # error job
    def boom(): raise ValueError("oops")
    jid3 = q.submit(boom)
    _wait(q, jid3)
    assert q.status(jid3) == "error", f"Got {q.status(jid3)}"
    score += 1; print("\\u2705 failing fn → status 'error'")

    # __len__
    assert len(q) >= 3, f"Expected at least 3 jobs, got {len(q)}"
    score += 1; print("\\u2705 __len__ counts submitted jobs")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX2 = nb([
    md("# Day 059 — Exercise 2: JobQueue Class\n\n"
       "`BackgroundTasks` is simple but limited: results aren't persistently stored, "
       "and you can't check status later. For real job tracking you need a dedicated "
       "queue that remembers every job's state.\n\n"
       "`threading.Lock` ensures only one thread reads or writes the `_jobs` dict at a time. "
       "Without it, two threads updating the same dict simultaneously can corrupt state."),
    code(_EX2_IMPORTS),
    md("## Task\n\n"
       "Implement `JobQueue` with four behaviours:\n\n"
       "| Method | Behaviour |\n"
       "|--------|-----------|\n"
       "| `submit(fn, *args) -> str` | Launch thread, return `job_id` immediately |\n"
       "| `status(job_id) -> str` | `'pending'/'running'/'done'/'error'/'not_found'` |\n"
       "| `result(job_id) -> Any` | Return result when done, else `None` |\n"
       "| `__len__() -> int` | Total jobs ever submitted |\n\n"
       "Use `threading.Lock()` around every `_jobs` read/write."),
    md("## Your Implementation"),
    code(_EX2_STUB),
    code(_EX2_SOLUTION),
    md("## Automated checks"),
    code(_EX2_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX2_SOLUTION + "```\n\n"
       "**Why `threading.Lock()`?** The `_jobs` dict is accessed from both the main "
       "thread (via `status`/`result`) and background threads (via `worker`). Without "
       "a lock, two threads can interleave dictionary writes and corrupt the state — "
       "a race condition that is hard to reproduce but catastrophic in production.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_02.ipynb", EX2)

# ══════════════════════════════════════════════════════════════════════════════
# EXERCISE 3 — build_worker_api
# ══════════════════════════════════════════════════════════════════════════════
_EX3_GIVEN = """\
# --- Provided: JobQueue (from Exercise 2) ---
import threading
import uuid
from typing import Any, Callable

class JobQueue:
    def __init__(self):
        self._jobs: dict = {}
        self._lock = threading.Lock()

    def submit(self, fn: Callable, *args) -> str:
        job_id = uuid.uuid4().hex[:8]
        with self._lock:
            self._jobs[job_id] = {"status": "pending"}

        def worker():
            with self._lock:
                self._jobs[job_id]["status"] = "running"
            try:
                value = fn(*args)
                with self._lock:
                    self._jobs[job_id] = {"status": "done", "result": value}
            except Exception as exc:
                with self._lock:
                    self._jobs[job_id] = {"status": "error", "error": str(exc)}

        threading.Thread(target=worker, daemon=True).start()
        return job_id

    def status(self, job_id: str) -> str:
        with self._lock:
            return self._jobs.get(job_id, {}).get("status", "not_found")

    def result(self, job_id: str) -> Any:
        with self._lock:
            job = self._jobs.get(job_id, {})
            return job.get("result") if job.get("status") == "done" else None
"""

_EX3_IMPORTS = """\
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from starlette.testclient import TestClient
import time
"""

_EX3_STUB = """\
def build_worker_api(process_fn=None) -> FastAPI:
    \"\"\"FastAPI app backed by a JobQueue.

    Endpoints:
      POST /jobs  {\"payload\": \"...\"}  → 202  {\"job_id\": \"...\", \"status\": \"pending\"}
      GET /jobs/{job_id}             → 200  {\"status\": ..., \"result\": ...}
                                     → 404 if unknown

    process_fn: optional callable(payload: str) -> str for testing.
                If None, uppercase the payload (trivial default).
    \"\"\"
    # TODO: create JobQueue, build app with POST /jobs and GET /jobs/{job_id}
    raise NotImplementedError
"""

_EX3_SOLUTION = """\
def build_worker_api(process_fn=None) -> FastAPI:
    app   = FastAPI()
    queue = JobQueue()

    class _JobReq(BaseModel):
        payload: str = Field(min_length=1)

    @app.post("/jobs", status_code=202)
    def submit(req: _JobReq):
        fn     = process_fn if process_fn is not None else str.upper
        job_id = queue.submit(fn, req.payload)
        return {"job_id": job_id, "status": "pending"}

    @app.get("/jobs/{job_id}")
    def get_job(job_id: str):
        s = queue.status(job_id)
        if s == "not_found":
            raise HTTPException(404, "Job not found")
        result = queue.result(job_id)
        return {"status": s, "result": result}

    return app
"""

_EX3_CHECKS = """\
score, total = 0, 5

def _wait_job(client, job_id, timeout=2.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        r = client.get(f"/jobs/{job_id}")
        if r.json()["status"] not in ("pending", "running"):
            return r.json()
        time.sleep(0.01)
    return client.get(f"/jobs/{job_id}").json()

try:
    app    = build_worker_api(process_fn=str.upper)
    client = TestClient(app, raise_server_exceptions=False)

    r = client.post("/jobs", json={"payload": "hello"})
    assert r.status_code == 202, f"Expected 202, got {r.status_code}"
    score += 1; print("\\u2705 POST /jobs returns 202")

    body = r.json()
    assert "job_id" in body, f"Expected job_id in {body}"
    score += 1; print("\\u2705 response contains job_id")

    job = _wait_job(client, body["job_id"])
    assert job["status"] == "done", f"Expected done, got {job}"
    assert job["result"] == "HELLO", f"Expected HELLO, got {job['result']}"
    score += 1; print("\\u2705 job completes with correct result")

    r2 = client.get("/jobs/no_such_id")
    assert r2.status_code == 404, f"Expected 404, got {r2.status_code}"
    score += 1; print("\\u2705 unknown job_id → 404")

    r3 = client.post("/jobs", json={"payload": ""})
    assert r3.status_code == 422, f"Expected 422 for empty payload, got {r3.status_code}"
    score += 1; print("\\u2705 empty payload → 422")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX3 = nb([
    md("# Day 059 — Exercise 3: Worker API (FastAPI + JobQueue)\n\n"
       "Wire `JobQueue` from Exercise 2 into a FastAPI app. The API accepts jobs "
       "via `POST /jobs`, returns a `job_id` immediately (202 Accepted), and lets "
       "clients poll `GET /jobs/{job_id}` until the status is `done` or `error`.\n\n"
       "This is the standard REST pattern for long-running tasks: accept immediately, "
       "process asynchronously, poll for completion."),
    code(_EX3_GIVEN),
    code(_EX3_IMPORTS),
    md("## Task\n\n"
       "Implement `build_worker_api(process_fn=None)` — return a FastAPI app with:\n\n"
       "```\n"
       "POST /jobs   {\"payload\": \"...\"}  → 202  {\"job_id\": \"...\", \"status\": \"pending\"}\n"
       "GET  /jobs/{job_id}            → 200  {\"status\": ..., \"result\": ...}\n"
       "                               → 404  if unknown\n"
       "```\n\n"
       "Use `JobQueue` (already defined above). Pass `process_fn` (or `str.upper`) "
       "to `queue.submit()` as the worker function."),
    md("## Your Implementation"),
    code(_EX3_STUB),
    code(_EX3_SOLUTION),
    md("## Automated checks"),
    code(_EX3_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX3_SOLUTION + "```\n\n"
       "**Why 202 Accepted?** HTTP 200 means *done*. 202 means *accepted for processing* — "
       "exactly right when the work hasn't finished yet. Clients must poll `GET /jobs/{id}` "
       "to discover completion, which is why the response includes `job_id`.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_03.ipynb", EX3)

# ══════════════════════════════════════════════════════════════════════════════
# EXERCISE 4 — retry_with_backoff
# ══════════════════════════════════════════════════════════════════════════════
_EX4_IMPORTS = """\
import time
from typing import Any, Callable
"""

_EX4_STUB = """\
def retry_with_backoff(fn: Callable, max_retries: int = 3, base_delay: float = 0.001) -> Any:
    \"\"\"Call fn(). On exception, retry up to max_retries times with exponential backoff.

    Delay before retry N: base_delay * (2 ** N) seconds  (0.001, 0.002, 0.004, ...)
    Raises the last exception if all attempts fail.
    fn is called with no arguments.
    \"\"\"
    # TODO: loop up to max_retries+1 times, sleep between failures
    raise NotImplementedError
"""

_EX4_SOLUTION = """\
def retry_with_backoff(fn, max_retries=3, base_delay=0.001):
    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            if attempt < max_retries:
                time.sleep(base_delay * (2 ** attempt))
    raise last_exc
"""

_EX4_CHECKS = """\
score, total = 0, 4
try:
    # succeeds immediately
    result = retry_with_backoff(lambda: 99, max_retries=3, base_delay=0)
    assert result == 99, f"Expected 99, got {result}"
    score += 1; print("\\u2705 succeeds immediately and returns result")

    # fails N times then succeeds
    calls = {"n": 0}
    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ValueError("not yet")
        return "ok"

    result2 = retry_with_backoff(flaky, max_retries=5, base_delay=0)
    assert result2 == "ok", f"Expected 'ok', got {result2}"
    assert calls["n"] == 3, f"Expected 3 calls, got {calls['n']}"
    score += 1; print("\\u2705 retries until success")

    # always fails → raises last exception
    always_fail = lambda: (_ for _ in ()).throw(RuntimeError("always"))
    raised = False
    try:
        retry_with_backoff(always_fail, max_retries=2, base_delay=0)
    except RuntimeError as e:
        raised = True
        assert str(e) == "always", f"Got {e}"
    assert raised, "Should have raised RuntimeError"
    score += 1; print("\\u2705 raises last exception when all retries fail")

    # total call count = max_retries + 1
    n_calls = {"c": 0}
    def count_calls(): n_calls["c"] += 1; raise ValueError()
    try:
        retry_with_backoff(count_calls, max_retries=3, base_delay=0)
    except ValueError:
        pass
    assert n_calls["c"] == 4, f"Expected 4 calls (1 + 3 retries), got {n_calls['c']}"
    score += 1; print("\\u2705 calls fn exactly max_retries + 1 times on total failure")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX4 = nb([
    md("# Day 059 — Exercise 4: Retry with Exponential Backoff\n\n"
       "Background jobs fail for transient reasons: network blips, temporary overload, "
       "a model loading delay. **Exponential backoff** retries with increasing delays "
       "so you don't hammer a struggling service.\n\n"
       "Pattern: attempt 0 → fail → sleep `d`, attempt 1 → fail → sleep `2d`, "
       "attempt 2 → fail → sleep `4d`, …, attempt `max_retries` → raise if still failing."),
    code(_EX4_IMPORTS),
    md("## Task\n\n"
       "Implement `retry_with_backoff(fn, max_retries=3, base_delay=0.001)`:\n\n"
       "- Call `fn()` with no arguments\n"
       "- If it raises, sleep `base_delay * 2**attempt` and retry (up to `max_retries` times)\n"
       "- Return the result of the first successful call\n"
       "- If all attempts fail, re-raise the **last** exception"),
    md("## Your Implementation"),
    code(_EX4_STUB),
    code(_EX4_SOLUTION),
    md("## Automated checks"),
    code(_EX4_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX4_SOLUTION + "```\n\n"
       "**Why `range(max_retries + 1)`?** The first call (attempt 0) is not a retry — "
       "it is the initial attempt. So `max_retries=3` means 1 initial + 3 retries = "
       "4 total calls. `raise last_exc` re-raises the last exception after all "
       "attempts are exhausted.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_04.ipynb", EX4)

# ══════════════════════════════════════════════════════════════════════════════
# EXERCISE 5 — poll_until_done
# ══════════════════════════════════════════════════════════════════════════════
_EX5_IMPORTS = """\
import time
from typing import Callable
"""

_EX5_STUB = """\
def poll_until_done(
    status_fn: Callable[[str], dict],
    job_id: str,
    timeout: float = 5.0,
    interval: float = 0.05,
) -> dict:
    \"\"\"Poll status_fn(job_id) until status is not 'pending' or 'running'.

    status_fn: callable that takes job_id and returns a dict with a 'status' key
    Returns the final status dict (including 'result' if done).
    Raises TimeoutError if the job has not completed within `timeout` seconds.
    \"\"\"
    # TODO: loop until done or timeout, sleep interval between polls
    raise NotImplementedError
"""

_EX5_SOLUTION = """\
def poll_until_done(status_fn, job_id, timeout=5.0, interval=0.05):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = status_fn(job_id)
        if state.get("status") not in ("pending", "running"):
            return state
        time.sleep(interval)
    raise TimeoutError(f"Job {job_id!r} did not complete within {timeout}s")
"""

_EX5_CHECKS = """\
score, total = 0, 4
try:
    # job done immediately
    immediate = lambda jid: {"status": "done", "result": 42}
    result = poll_until_done(immediate, "j1", timeout=1.0, interval=0.001)
    assert result == {"status": "done", "result": 42}, f"Got {result}"
    score += 1; print("\\u2705 returns immediately when job already done")

    # job takes a few polls (pending → running → done)
    _state = {"phase": 0}
    def multi_phase(jid):
        _state["phase"] += 1
        if _state["phase"] == 1: return {"status": "pending"}
        if _state["phase"] == 2: return {"status": "running"}
        return {"status": "done", "result": "ready"}

    result2 = poll_until_done(multi_phase, "j2", timeout=1.0, interval=0.001)
    assert result2["status"] == "done"
    assert result2["result"] == "ready"
    score += 1; print("\\u2705 polls through pending→running→done correctly")

    # error status is returned (not raised)
    error_fn = lambda jid: {"status": "error", "error": "boom"}
    result3 = poll_until_done(error_fn, "j3", timeout=1.0, interval=0.001)
    assert result3["status"] == "error"
    score += 1; print("\\u2705 error status returned without raising")

    # timeout raises TimeoutError
    always_pending = lambda jid: {"status": "pending"}
    timed_out = False
    try:
        poll_until_done(always_pending, "j4", timeout=0.05, interval=0.001)
    except TimeoutError:
        timed_out = True
    assert timed_out, "Should have raised TimeoutError"
    score += 1; print("\\u2705 raises TimeoutError after timeout exceeded")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX5 = nb([
    md("# Day 059 — Exercise 5: Poll Until Done\n\n"
       "When a client submits a background job and gets a `job_id`, it needs a way "
       "to wait for completion. **Polling** repeatedly calls `GET /jobs/{id}` until "
       "the status leaves `pending`/`running`.\n\n"
       "`poll_until_done` abstracts this into a reusable helper that takes a "
       "`status_fn` — any callable that returns a status dict for a job_id. "
       "This makes it testable with mock functions without a real server."),
    code(_EX5_IMPORTS),
    md("## Task\n\n"
       "Implement `poll_until_done(status_fn, job_id, timeout=5.0, interval=0.05)`:\n\n"
       "- Call `status_fn(job_id)` repeatedly\n"
       "- If `status` is `'pending'` or `'running'`, sleep `interval` and try again\n"
       "- If `status` is anything else (`'done'`, `'error'`, etc.), return the dict\n"
       "- If `timeout` seconds elapse without completion, raise `TimeoutError`"),
    md("## Your Implementation"),
    code(_EX5_STUB),
    code(_EX5_SOLUTION),
    md("## Automated checks"),
    code(_EX5_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX5_SOLUTION + "```\n\n"
       "**`time.monotonic()`** is the right clock for measuring elapsed time — "
       "it never goes backwards (unlike `time.time()`, which can jump due to NTP "
       "adjustments). The polling loop returns the dict for any terminal status "
       "(`done`, `error`, `not_found`) — the caller decides what to do with errors.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_05.ipynb", EX5)

# ══════════════════════════════════════════════════════════════════════════════
# PROJECT NOTEBOOK
# ══════════════════════════════════════════════════════════════════════════════
PROJECT = nb([
    md("# Day 059 — Project: Background Job Processing API\n\n"
       "Build `background_api.py` — a FastAPI server that accepts long-running "
       "Ollama summarization requests, processes them in background threads, and "
       "lets clients poll for results."),
    md("## Deliverable\n\n"
       "`background_api.py` in `project/solution/` — a FastAPI app with:\n\n"
       "| Endpoint | Method | Description |\n"
       "|----------|--------|-------------|\n"
       "| `/health` | GET | Health check |\n"
       "| `/summarize` | POST | Submit text → background Ollama summarization |\n"
       "| `/jobs/{job_id}` | GET | Poll status / retrieve result |\n\n"
       "## How to run\n\n"
       "```bash\n"
       "uvicorn background_api:app --reload\n"
       "# Then in another terminal:\n"
       "curl -X POST http://localhost:8000/summarize \\\\\n"
       "     -H 'Content-Type: application/json' \\\\\n"
       "     -d '{\"text\": \"Long document text here...\"}'\n"
       "# Returns: {\"job_id\": \"abc123\", \"status\": \"pending\"}\n"
       "curl http://localhost:8000/jobs/abc123\n"
       "# Returns: {\"status\": \"done\", \"result\": \"One-sentence summary.\"}\n"
       "```\n\n"
       "## Concepts used\n\n"
       "- `_JobStore` — thread-safe status/result store with `threading.Lock`\n"
       "- `threading.Thread(target=worker, daemon=True).start()` — background thread\n"
       "- `daemon=True` — thread exits when main process exits (no zombie threads)\n"
       "- `build_api(process_fn=None)` — dependency injection for testability\n"
       "- `POST /summarize → 202 Accepted` then `GET /jobs/{id}` polling pattern"),
])
save(OUT / "project" / "project.ipynb", PROJECT)

# ══════════════════════════════════════════════════════════════════════════════
# SOLUTION NOTEBOOK
# ══════════════════════════════════════════════════════════════════════════════
_FULL_SOL_CELL1 = (
    f"_BACKGROUND_API_SRC = {repr(_BACKGROUND_API_SRC)}\n"
    "from pathlib import Path\n"
    "Path('background_api.py').write_text(_BACKGROUND_API_SRC)\n"
    "print('background_api.py written.')"
)

_FULL_SOL_CELL2 = """\
import time
import threading
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from starlette.testclient import TestClient

# ── inline test app (no Ollama required) ──────────────────────────────────────
import uuid

class _Store:
    def __init__(self):
        self._jobs: dict = {}
        self._lock = threading.Lock()
    def create(self, jid):
        with self._lock: self._jobs[jid] = {"status": "pending"}
    def done(self, jid, result):
        with self._lock: self._jobs[jid] = {"status": "done", "result": result}
    def error(self, jid, err):
        with self._lock: self._jobs[jid] = {"status": "error", "error": err}
    def get(self, jid):
        with self._lock: return dict(self._jobs.get(jid) or {}) or None

store = _Store()

class _SumReq(BaseModel):
    text: str = Field(min_length=1)

test_app = FastAPI()

@test_app.get("/health")
def _health():
    from datetime import datetime
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": "1.0.0"}

@test_app.post("/summarize", status_code=202)
def _submit(req: _SumReq):
    jid = uuid.uuid4().hex[:8]
    store.create(jid)
    def worker():
        time.sleep(0.01)
        store.done(jid, "Summary: " + req.text[:50])
    threading.Thread(target=worker, daemon=True).start()
    return {"job_id": jid, "status": "pending"}

@test_app.get("/jobs/{job_id}")
def _get(job_id: str):
    job = store.get(job_id)
    if not job: raise HTTPException(404, "Not found")
    return job

client = TestClient(test_app, raise_server_exceptions=False)

# /health
r = client.get("/health")
assert r.status_code == 200 and r.json()["status"] == "ok"
print("\\u2705 /health works")

# POST /summarize → 202 + job_id
r2 = client.post("/summarize", json={"text": "This is a long document."})
assert r2.status_code == 202
body = r2.json()
assert "job_id" in body
print("\\u2705 POST /summarize returns 202 + job_id")

# poll until done
jid = body["job_id"]
deadline = time.monotonic() + 2.0
while time.monotonic() < deadline:
    r3 = client.get(f"/jobs/{jid}")
    if r3.json()["status"] != "pending":
        break
    time.sleep(0.01)
assert r3.json()["status"] == "done"
assert "Summary:" in r3.json()["result"]
print("\\u2705 GET /jobs/{id} returns result when done")

# 404 for unknown
r4 = client.get("/jobs/bad_id")
assert r4.status_code == 404
print("\\u2705 unknown job_id \\u2192 404")

# empty text → 422
r5 = client.post("/summarize", json={"text": ""})
assert r5.status_code == 422
print("\\u2705 empty text \\u2192 422")

print("\\nDay 059 \\u2014 Background Jobs & Queues complete! \\U0001f389")
"""

SOLUTION = nb([
    md("# Day 059 — Solution: Background Job Processing API"),
    code(_FULL_SOL_CELL1),
    code(_FULL_SOL_CELL2),
])
save(OUT / "project" / "solution" / "solution.ipynb", SOLUTION)
(OUT / "project" / "solution" / "background_api.py").write_text(_BACKGROUND_API_SRC)

print(f"Day {DAY} notebooks written to {OUT}")
print("  exercises/  exercise_01 – exercise_05")
print("  project/    project.ipynb")
print("  project/solution/  solution.ipynb + background_api.py")
