#!/usr/bin/env python3
"""gen_day061.py — generate Day 061: Monitoring & Logging notebooks."""
from pathlib import Path
import json

ROOT    = Path(__file__).parent.parent
DAY     = "061"
SECTION = "04_real_apps"
OUT     = ROOT / SECTION / f"day_{DAY}"

(OUT / "exercises").mkdir(parents=True, exist_ok=True)
(OUT / "lessons").mkdir(parents=True, exist_ok=True)
(OUT / "project" / "solution").mkdir(parents=True, exist_ok=True)

# ── deliverable source ─────────────────────────────────────────────────────────
_MONITORED_API_SRC = '''\
"""monitored_api.py — Day 061: monitoring and logging for AI apps.

Run:  uvicorn monitored_api:app --reload
Docs: http://localhost:8000/docs
"""
import json
import logging
import os
import time
from datetime import datetime

import ollama
from fastapi import FastAPI, Request
from pydantic import BaseModel, Field

MODEL   = os.environ.get("MODEL", "llama3.2")
APP_VER = "1.0.0"
LOG_LVL = os.environ.get("LOG_LEVEL", "INFO")


class JsonFormatter(logging.Formatter):
    """Emit one JSON object per log record."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level":     record.levelname,
            "logger":    record.name,
            "message":   record.getMessage(),
        }
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry)


def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Return a named logger with a JsonFormatter on stdout."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    if not logger.handlers:
        h = logging.StreamHandler()
        h.setFormatter(JsonFormatter())
        logger.addHandler(h)
    logger.propagate = False
    return logger


class MetricsCollector:
    """Thread-safe request metrics accumulator."""

    def __init__(self):
        self._requests = 0
        self._errors   = 0
        self._latencies: list[float] = []

    def record(self, status_code: int, duration_ms: float) -> None:
        self._requests += 1
        if status_code >= 400:
            self._errors += 1
        self._latencies.append(duration_ms)

    def summary(self) -> dict:
        avg        = sum(self._latencies) / len(self._latencies) if self._latencies else 0.0
        error_rate = self._errors / self._requests if self._requests else 0.0
        return {
            "requests":       self._requests,
            "errors":         self._errors,
            "avg_latency_ms": round(avg, 1),
            "error_rate":     round(error_rate, 3),
        }

    def reset(self) -> None:
        self._requests = 0
        self._errors   = 0
        self._latencies.clear()


class AskRequest(BaseModel):
    prompt: str = Field(min_length=1)


def build_api(process_fn=None) -> FastAPI:
    """Build the monitored API.

    process_fn: optional callable(prompt: str) -> str for testing.
    """
    app       = FastAPI(title="Monitored API", version=APP_VER)
    collector = MetricsCollector()
    logger    = setup_logger("monitored_api", LOG_LVL)

    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        start    = time.monotonic()
        response = await call_next(request)
        duration = (time.monotonic() - start) * 1000
        collector.record(response.status_code, duration)
        entry = {"method": request.method, "path": request.url.path,
                 "status": response.status_code, "duration_ms": round(duration, 1)}
        logger.info(json.dumps(entry))
        return response

    @app.get("/health")
    def health():
        return {"status": "ok",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "version": APP_VER}

    @app.get("/metrics")
    def metrics():
        return collector.summary()

    @app.post("/ask")
    def ask(req: AskRequest):
        if process_fn is not None:
            answer = process_fn(req.prompt)
        else:
            resp   = ollama.chat(
                model=MODEL,
                messages=[{"role": "user", "content": req.prompt}],
            )
            answer = resp["message"]["content"]
        return {"answer": answer}

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
# EXERCISE 1 — setup_logger
# ══════════════════════════════════════════════════════════════════════════════
_EX1_GIVEN = """\
# --- helper for capturing log records in tests ---
import logging

class _ListHandler(logging.Handler):
    \"\"\"Stores LogRecord objects in a list for inspection.\"\"\"
    def __init__(self):
        super().__init__()
        self.records = []
    def emit(self, record):
        self.records.append(record)
"""

_EX1_IMPORTS = """\
import sys
"""

_EX1_STUB = """\
def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    \"\"\"Return a configured logger.

    - getLogger(name) — named logger (singleton per name)
    - setLevel to the numeric value of level (e.g. 'WARNING' -> logging.WARNING)
    - Add a StreamHandler(sys.stdout) with a basic Formatter IF no handlers exist
    - Set logger.propagate = False so root logger doesn't duplicate output
    - Return the logger
    \"\"\"
    # TODO: configure and return the logger
    raise NotImplementedError
"""

_EX1_SOLUTION = """\
def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    if not logger.handlers:
        h = logging.StreamHandler(sys.stdout)
        h.setFormatter(logging.Formatter(
            "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
        ))
        logger.addHandler(h)
    logger.propagate = False
    return logger
"""

_EX1_CHECKS = """\
score, total = 0, 5
try:
    # create logger at WARNING level
    logger = setup_logger("day061_ex1", "WARNING")

    # wire in our capturing handler
    h = _ListHandler()
    logger.handlers.clear()
    logger.addHandler(h)
    logger.propagate = False

    # check level
    assert logger.level == logging.WARNING, (
        f"Expected WARNING ({logging.WARNING}), got {logger.level}")
    score += 1; print("\\u2705 logger.level is WARNING")

    # DEBUG below WARNING — should not log
    logger.debug("ignored")
    assert len(h.records) == 0, "DEBUG should be filtered by WARNING level"
    score += 1; print("\\u2705 DEBUG below WARNING is filtered")

    # INFO below WARNING — should not log
    logger.info("also ignored")
    assert len(h.records) == 0, "INFO should be filtered by WARNING level"
    score += 1; print("\\u2705 INFO below WARNING is filtered")

    # WARNING logs
    logger.warning("first warning")
    assert len(h.records) == 1
    assert h.records[0].levelname == "WARNING"
    assert "first warning" in h.records[0].getMessage()
    score += 1; print("\\u2705 WARNING level emits a log record")

    # ERROR logs too
    logger.error("something broke")
    assert len(h.records) == 2
    assert h.records[1].levelname == "ERROR"
    score += 1; print("\\u2705 ERROR level emits a log record")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX1 = nb([
    md("# Day 061 — Exercise 1: setup_logger\n\n"
       "Python's `logging` module is the standard way to emit diagnostic output "
       "from application code. Unlike `print()`, logging has:\n\n"
       "- **Levels** — DEBUG < INFO < WARNING < ERROR < CRITICAL; "
       "messages below the logger's level are silently dropped\n"
       "- **Handlers** — where output goes (stdout, file, network)\n"
       "- **Formatters** — how output looks\n"
       "- **Named loggers** — `logging.getLogger(name)` returns a singleton; "
       "calling it again with the same name returns the same object"),
    code(_EX1_GIVEN),
    code(_EX1_IMPORTS),
    md("## Task\n\n"
       "Implement `setup_logger(name, level='INFO') -> logging.Logger`:\n\n"
       "1. `logging.getLogger(name)` — get (or create) the named logger\n"
       "2. `logger.setLevel(getattr(logging, level.upper()))` — set numeric level\n"
       "3. If `not logger.handlers`: add a `StreamHandler(sys.stdout)` with a Formatter\n"
       "4. `logger.propagate = False` — prevent double-output via the root logger\n"
       "5. Return the logger\n\n"
       "The `if not logger.handlers` guard prevents adding a second handler if the "
       "function is called more than once with the same name."),
    md("## Your Implementation"),
    code(_EX1_STUB),
    code(_EX1_SOLUTION),
    md("## Automated checks"),
    code(_EX1_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX1_SOLUTION + "```\n\n"
       "**Why `propagate = False`?** By default, log records bubble up to the root "
       "logger. If the root logger also has a handler (e.g. from `logging.basicConfig`), "
       "every message appears twice. Setting `propagate = False` stops the bubble-up.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_01.ipynb", EX1)

# ══════════════════════════════════════════════════════════════════════════════
# EXERCISE 2 — JsonFormatter
# ══════════════════════════════════════════════════════════════════════════════
_EX2_IMPORTS = """\
import json
import logging
from datetime import datetime
"""

_EX2_STUB = """\
class JsonFormatter(logging.Formatter):
    \"\"\"Emit one JSON object per log record.

    Each call to format(record) returns a string like:
    {\"timestamp\": \"2026-01-01T12:00:00\", \"level\": \"INFO\",
     \"logger\": \"myapp\", \"message\": \"Hello world\"}

    If the record has exc_info (an exception), also include:
    {\"exc\": \"<formatted traceback string>\"}

    Use datetime.fromtimestamp(record.created).isoformat() for the timestamp.
    Use record.getMessage() for the message (handles % formatting).
    Use self.formatException(record.exc_info) for the traceback string.
    \"\"\"

    def format(self, record: logging.LogRecord) -> str:
        # TODO: build entry dict, add exc key if record.exc_info, return json.dumps(entry)
        raise NotImplementedError
"""

_EX2_SOLUTION = """\
class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level":     record.levelname,
            "logger":    record.name,
            "message":   record.getMessage(),
        }
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry)
"""

_EX2_CHECKS = """\
score, total = 0, 5
try:
    formatter = JsonFormatter()

    # helper: make a real LogRecord
    def make_record(msg, level=logging.INFO, name="test"):
        r = logging.LogRecord(
            name=name, level=level, pathname="", lineno=0,
            msg=msg, args=(), exc_info=None,
        )
        return r

    # output is valid JSON
    rec1 = make_record("hello world")
    output = formatter.format(rec1)
    data = json.loads(output)
    score += 1; print("\\u2705 format() returns valid JSON")

    # required fields present
    for field in ("timestamp", "level", "logger", "message"):
        assert field in data, f"Missing field: {field}"
    score += 1; print("\\u2705 output has timestamp, level, logger, message")

    # level name is correct
    assert data["level"] == "INFO", f"Expected 'INFO', got {data['level']!r}"
    score += 1; print("\\u2705 level field contains levelname string")

    # message is correct
    assert data["message"] == "hello world", f"Got {data['message']!r}"
    score += 1; print("\\u2705 message field contains the log message")

    # exception adds 'exc' key
    try:
        raise ValueError("oops")
    except ValueError:
        import sys
        exc_info = sys.exc_info()
    rec2 = logging.LogRecord(
        name="test", level=logging.ERROR, pathname="", lineno=0,
        msg="error occurred", args=(), exc_info=exc_info,
    )
    data2 = json.loads(formatter.format(rec2))
    assert "exc" in data2, f"Expected 'exc' key for exception record"
    assert "ValueError" in data2["exc"]
    score += 1; print("\\u2705 exception record includes 'exc' traceback field")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX2 = nb([
    md("# Day 061 — Exercise 2: JsonFormatter\n\n"
       "Plain-text log lines like `2026-01-01 12:00:00 | app | INFO | Request received` "
       "are human-readable but hard to query in production. Tools like Datadog, Loki, "
       "and CloudWatch work much better with **structured logs** — one JSON object per "
       "line, where each field can be indexed and filtered.\n\n"
       "A custom `logging.Formatter` subclass controls what each log record looks like. "
       "Override `format(record) -> str` to return any string you want."),
    code(_EX2_IMPORTS),
    md("## Task\n\n"
       "Implement `JsonFormatter(logging.Formatter)` with a `format` method that returns:\n\n"
       "```json\n"
       "{\"timestamp\": \"2026-01-01T12:00:00\", \"level\": \"INFO\",\n"
       " \"logger\": \"myapp\", \"message\": \"Hello world\"}\n"
       "```\n\n"
       "Field sources:\n"
       "- `timestamp`: `datetime.fromtimestamp(record.created).isoformat()`\n"
       "- `level`: `record.levelname`\n"
       "- `logger`: `record.name`\n"
       "- `message`: `record.getMessage()` (handles `%s` formatting args)\n"
       "- `exc` (only if `record.exc_info`): `self.formatException(record.exc_info)`"),
    md("## Your Implementation"),
    code(_EX2_STUB),
    code(_EX2_SOLUTION),
    md("## Automated checks"),
    code(_EX2_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX2_SOLUTION + "```\n\n"
       "**Why `record.getMessage()` not `record.msg`?** `record.msg` is the raw format "
       "string (e.g. `'user %s logged in'`). `getMessage()` applies the args: "
       "`'user alice logged in'`. Always use `getMessage()` in formatters.\n\n"
       "**Why `self.formatException(record.exc_info)` not `traceback.format_exc()`?** "
       "`formatException` uses the exc_info stored in the record — safe across threads "
       "and callbacks. `traceback.format_exc()` reads the current thread's exception "
       "state, which may differ.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_02.ipynb", EX2)

# ══════════════════════════════════════════════════════════════════════════════
# EXERCISE 3 — MetricsCollector
# ══════════════════════════════════════════════════════════════════════════════
_EX3_IMPORTS = """\
# no extra imports needed
"""

_EX3_STUB = """\
class MetricsCollector:
    \"\"\"Accumulate per-request metrics.

    record(status_code, duration_ms) — add one request observation.
        status_code >= 400 counts as an error.
    summary() -> dict — return aggregate stats:
        {\"requests\": int, \"errors\": int,
         \"avg_latency_ms\": float (1 dp), \"error_rate\": float (3 dp)}
        error_rate = errors / requests (0.0 if no requests)
        avg_latency_ms = 0.0 if no requests
    reset() — clear all counters and samples.
    \"\"\"

    def __init__(self):
        # TODO: init counters and latency list
        raise NotImplementedError

    def record(self, status_code: int, duration_ms: float) -> None:
        raise NotImplementedError

    def summary(self) -> dict:
        raise NotImplementedError

    def reset(self) -> None:
        raise NotImplementedError
"""

_EX3_SOLUTION = """\
class MetricsCollector:
    def __init__(self):
        self._requests = 0
        self._errors   = 0
        self._latencies: list = []

    def record(self, status_code: int, duration_ms: float) -> None:
        self._requests += 1
        if status_code >= 400:
            self._errors += 1
        self._latencies.append(duration_ms)

    def summary(self) -> dict:
        avg        = sum(self._latencies) / len(self._latencies) if self._latencies else 0.0
        error_rate = self._errors / self._requests if self._requests else 0.0
        return {
            "requests":       self._requests,
            "errors":         self._errors,
            "avg_latency_ms": round(avg, 1),
            "error_rate":     round(error_rate, 3),
        }

    def reset(self) -> None:
        self._requests = 0
        self._errors   = 0
        self._latencies.clear()
"""

_EX3_CHECKS = """\
score, total = 0, 6
try:
    mc = MetricsCollector()

    # empty summary
    s0 = mc.summary()
    assert s0["requests"] == 0 and s0["errors"] == 0
    assert s0["avg_latency_ms"] == 0.0 and s0["error_rate"] == 0.0
    score += 1; print("\\u2705 empty collector returns zero summary")

    # record a 200
    mc.record(200, 50.0)
    s1 = mc.summary()
    assert s1["requests"] == 1 and s1["errors"] == 0
    assert s1["error_rate"] == 0.0
    score += 1; print("\\u2705 200 response: requests=1, errors=0")

    # record a 404 (error)
    mc.record(404, 10.0)
    s2 = mc.summary()
    assert s2["requests"] == 2 and s2["errors"] == 1
    score += 1; print("\\u2705 404 counts as an error")

    # record a 500 (also error)
    mc.record(500, 30.0)
    s3 = mc.summary()
    assert s3["errors"] == 2 and s3["requests"] == 3
    score += 1; print("\\u2705 500 counts as an error")

    # avg_latency_ms (50 + 10 + 30) / 3 = 30.0
    assert s3["avg_latency_ms"] == 30.0, (
        f"Expected 30.0, got {s3['avg_latency_ms']}")
    score += 1; print("\\u2705 avg_latency_ms is correct")

    # error_rate = 2/3 ≈ 0.667
    assert abs(s3["error_rate"] - 0.667) < 0.001, (
        f"Expected ~0.667, got {s3['error_rate']}")
    # reset
    mc.reset()
    assert mc.summary()["requests"] == 0
    score += 1; print("\\u2705 reset() clears all counters")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX3 = nb([
    md("# Day 061 — Exercise 3: MetricsCollector\n\n"
       "Logging tells you WHAT happened. Metrics tell you HOW OFTEN and HOW FAST. "
       "The key counters for an AI API are:\n\n"
       "- **request count** — total traffic\n"
       "- **error count** — 4xx/5xx responses\n"
       "- **error rate** — fraction of requests that failed\n"
       "- **average latency** — how long requests take on average\n\n"
       "A single in-memory accumulator is sufficient for one server instance. "
       "For multi-instance deployments, metrics would be pushed to a central "
       "store (Prometheus, Datadog) — the same interface, different backend."),
    code(_EX3_IMPORTS),
    md("## Task\n\n"
       "Implement `MetricsCollector`:\n\n"
       "| Method | Behaviour |\n"
       "|--------|-----------|\n"
       "| `record(status_code, duration_ms)` | Increment requests; if `status_code >= 400` also increment errors; append duration_ms |\n"
       "| `summary() -> dict` | `{requests, errors, avg_latency_ms (1dp), error_rate (3dp)}` |\n"
       "| `reset()` | Clear all counters and latency list |\n\n"
       "`error_rate = errors / requests` (or `0.0` when no requests)."),
    md("## Your Implementation"),
    code(_EX3_STUB),
    code(_EX3_SOLUTION),
    md("## Automated checks"),
    code(_EX3_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX3_SOLUTION + "```\n\n"
       "**Latency list instead of a running sum?** A list lets you compute percentiles "
       "(p50, p95, p99) later. A running sum only gives you the mean. In production "
       "you'd use a histogram or reservoir sampling to keep memory bounded — but for "
       "a single-server AI app, a plain list is fine.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_03.ipynb", EX3)

# ══════════════════════════════════════════════════════════════════════════════
# EXERCISE 4 — build_logged_api
# ══════════════════════════════════════════════════════════════════════════════
_EX4_GIVEN = """\
# --- Provided: MetricsCollector (from Exercise 3) ---
import time

class MetricsCollector:
    def __init__(self):
        self._requests = 0
        self._errors   = 0
        self._latencies: list = []

    def record(self, status_code: int, duration_ms: float) -> None:
        self._requests += 1
        if status_code >= 400:
            self._errors += 1
        self._latencies.append(duration_ms)

    def summary(self) -> dict:
        avg        = sum(self._latencies) / len(self._latencies) if self._latencies else 0.0
        error_rate = self._errors / self._requests if self._requests else 0.0
        return {
            "requests":       self._requests,
            "errors":         self._errors,
            "avg_latency_ms": round(avg, 1),
            "error_rate":     round(error_rate, 3),
        }

    def reset(self) -> None:
        self._requests = 0
        self._errors   = 0
        self._latencies.clear()
"""

_EX4_IMPORTS = """\
from fastapi import FastAPI, Request
from pydantic import BaseModel, Field
from starlette.testclient import TestClient
"""

_EX4_STUB = """\
def build_logged_api(process_fn=None) -> FastAPI:
    \"\"\"FastAPI app with a metrics-recording middleware.

    POST /ask   {\"prompt\": str (min_length=1)} → {\"answer\": str}
    GET /health                                → {\"status\": \"ok\"}
    GET /metrics                               → MetricsCollector.summary()

    Middleware (registered with @app.middleware('http')):
        - Measure duration with time.monotonic()
        - After route runs: collector.record(response.status_code, duration_ms)

    process_fn: optional callable(prompt: str) -> str for testing.
    \"\"\"
    # TODO: create app + collector, add middleware, add routes, return app
    raise NotImplementedError
"""

_EX4_SOLUTION = """\
def build_logged_api(process_fn=None) -> FastAPI:
    app       = FastAPI()
    collector = MetricsCollector()

    @app.middleware("http")
    async def _metrics(request: Request, call_next):
        start    = time.monotonic()
        response = await call_next(request)
        duration = (time.monotonic() - start) * 1000
        collector.record(response.status_code, duration)
        return response

    class _AskReq(BaseModel):
        prompt: str = Field(min_length=1)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/metrics")
    def metrics():
        return collector.summary()

    @app.post("/ask")
    def ask(req: _AskReq):
        answer = process_fn(req.prompt) if process_fn else req.prompt.upper()
        return {"answer": answer}

    return app
"""

_EX4_CHECKS = """\
score, total = 0, 6
try:
    app    = build_logged_api(process_fn=str.upper)
    client = TestClient(app, raise_server_exceptions=False)

    # /health works
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"
    score += 1; print("\\u2705 GET /health returns 200 ok")

    # /ask returns answer
    r2 = client.post("/ask", json={"prompt": "hello"})
    assert r2.status_code == 200 and r2.json()["answer"] == "HELLO"
    score += 1; print("\\u2705 POST /ask returns processed answer")

    # empty prompt → 422
    r3 = client.post("/ask", json={"prompt": ""})
    assert r3.status_code == 422
    score += 1; print("\\u2705 empty prompt \\u2192 422")

    # metrics recorded (3 requests so far; /metrics itself is 4th but not yet counted)
    rm = client.get("/metrics")
    assert rm.status_code == 200
    m = rm.json()
    assert m["requests"] == 3, f"Expected 3 requests, got {m['requests']}"
    score += 1; print("\\u2705 /metrics shows 3 requests recorded")

    # errors >= 1 (the 422)
    assert m["errors"] >= 1, f"Expected errors >= 1, got {m['errors']}"
    score += 1; print("\\u2705 /metrics shows at least 1 error (the 422)")

    # avg_latency_ms is a non-negative number
    assert isinstance(m["avg_latency_ms"], (int, float)) and m["avg_latency_ms"] >= 0
    assert 0 <= m["error_rate"] <= 1
    score += 1; print("\\u2705 /metrics has valid avg_latency_ms and error_rate")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX4 = nb([
    md("# Day 061 — Exercise 4: Logged API\n\n"
       "Wire `MetricsCollector` into a FastAPI app using `@app.middleware('http')`. "
       "Middleware runs **around every request** — before and after the route handler. "
       "This is the right place to measure latency and record status codes, because "
       "middleware sees both the request AND the final response.\n\n"
       "```\n"
       "Client → [middleware: start timer]\n"
       "       → [route handler: build response]\n"
       "       → [middleware: record status + duration]\n"
       "       → Client\n"
       "```"),
    code(_EX4_GIVEN),
    code(_EX4_IMPORTS),
    md("## Task\n\n"
       "Implement `build_logged_api(process_fn=None) -> FastAPI`:\n\n"
       "```\n"
       "POST /ask   {\"prompt\": \"...\"}  → {\"answer\": str}  (422 if prompt empty)\n"
       "GET /health                    → {\"status\": \"ok\"}\n"
       "GET /metrics                   → collector.summary()\n"
       "```\n\n"
       "**Middleware** (`@app.middleware('http')`):\n"
       "```python\n"
       "async def _metrics(request: Request, call_next):\n"
       "    start    = time.monotonic()\n"
       "    response = await call_next(request)   # run the route\n"
       "    duration = (time.monotonic() - start) * 1000\n"
       "    collector.record(response.status_code, duration)\n"
       "    return response\n"
       "```"),
    md("## Your Implementation"),
    code(_EX4_STUB),
    code(_EX4_SOLUTION),
    md("## Automated checks"),
    code(_EX4_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX4_SOLUTION + "```\n\n"
       "**Why does `/metrics` show 3 requests, not 4?** The middleware records AFTER "
       "`call_next` returns. When GET /metrics runs, the route handler calls "
       "`collector.summary()` — which sees the 3 previous requests. The middleware "
       "then records the /metrics request itself, but the response is already built. "
       "This off-by-one is expected and consistent.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_04.ipynb", EX4)

# ══════════════════════════════════════════════════════════════════════════════
# EXERCISE 5 — make_health_report
# ══════════════════════════════════════════════════════════════════════════════
_EX5_IMPORTS = """\
from typing import Callable
"""

_EX5_STUB = """\
def make_health_report(services: dict[str, Callable[[], bool]]) -> dict:
    \"\"\"Run each service check and return an aggregated health report.

    services: {name: check_fn} where check_fn() returns True (healthy) / False (unhealthy).
              check_fn() may also raise — treat a raised exception as False.

    Returns:
    {
        \"status\": \"ok\" | \"degraded\" | \"down\",
        \"services\": {name: bool, ...},
    }

    Status rules:
        \"ok\"       — all checks pass
        \"degraded\" — at least one passes and at least one fails
        \"down\"     — all checks fail (or no checks provided → \"ok\")
    \"\"\"
    # TODO: run checks, collect results, compute status, return dict
    raise NotImplementedError
"""

_EX5_SOLUTION = """\
def make_health_report(services: dict[str, Callable[[], bool]]) -> dict:
    results = {}
    for name, fn in services.items():
        try:
            results[name] = bool(fn())
        except Exception:
            results[name] = False

    if not results:
        status = "ok"
    elif all(results.values()):
        status = "ok"
    elif not any(results.values()):
        status = "down"
    else:
        status = "degraded"

    return {"status": status, "services": results}
"""

_EX5_CHECKS = """\
score, total = 0, 6
try:
    # all ok
    r1 = make_health_report({"db": lambda: True, "cache": lambda: True})
    assert r1["status"] == "ok", f"Expected 'ok', got {r1['status']!r}"
    assert r1["services"] == {"db": True, "cache": True}
    score += 1; print("\\u2705 all passing checks → status='ok'")

    # all failing
    r2 = make_health_report({"db": lambda: False, "cache": lambda: False})
    assert r2["status"] == "down", f"Expected 'down', got {r2['status']!r}"
    score += 1; print("\\u2705 all failing checks → status='down'")

    # mixed → degraded
    r3 = make_health_report({"db": lambda: True, "cache": lambda: False})
    assert r3["status"] == "degraded", f"Expected 'degraded', got {r3['status']!r}"
    assert r3["services"]["db"] is True
    assert r3["services"]["cache"] is False
    score += 1; print("\\u2705 mixed checks → status='degraded'")

    # exception in check counts as False
    def bad_check():
        raise RuntimeError("connection refused")

    r4 = make_health_report({"db": lambda: True, "cache": bad_check})
    assert r4["services"]["cache"] is False
    assert r4["status"] == "degraded"
    score += 1; print("\\u2705 exception in check_fn treated as False")

    # empty services → ok
    r5 = make_health_report({})
    assert r5["status"] == "ok"
    score += 1; print("\\u2705 empty services dict → status='ok'")

    # single failing → down
    r6 = make_health_report({"only": lambda: False})
    assert r6["status"] == "down"
    score += 1; print("\\u2705 single failing check → status='down'")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX5 = nb([
    md("# Day 061 — Exercise 5: Health Report\n\n"
       "A **health endpoint** is the first thing load balancers, Kubernetes, and "
       "on-call engineers check when something goes wrong. A good health endpoint "
       "doesn't just return `{\"status\": \"ok\"}` — it checks each dependency "
       "(database, cache, model server) and reports which ones are healthy.\n\n"
       "Three status values:\n\n"
       "| Status | Meaning |\n"
       "|--------|--------|\n"
       "| `ok` | All dependencies healthy |\n"
       "| `degraded` | Some healthy, some not — service partially functional |\n"
       "| `down` | All dependencies unhealthy — service not functional |\n\n"
       "`degraded` is important: it lets the load balancer keep sending traffic "
       "(some requests can still succeed) while alerting the team to investigate."),
    code(_EX5_IMPORTS),
    md("## Task\n\n"
       "Implement `make_health_report(services: dict[str, Callable[[], bool]]) -> dict`:\n\n"
       "- Call each `check_fn()` — wrap in try/except, treat raised exceptions as `False`\n"
       "- `status = 'ok'` if all pass, `'down'` if all fail, `'degraded'` if mixed\n"
       "- Return `{'status': ..., 'services': {name: bool, ...}}`\n"
       "- Empty `services` dict → `'ok'`"),
    md("## Your Implementation"),
    code(_EX5_STUB),
    code(_EX5_SOLUTION),
    md("## Automated checks"),
    code(_EX5_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX5_SOLUTION + "```\n\n"
       "**Why wrap in try/except?** A check_fn that tries to connect to a database "
       "or ping a service can always raise (network timeout, DNS failure, auth error). "
       "A crashed check_fn doesn't mean the health endpoint itself should 500 — it "
       "means that specific dependency is down. Catch broadly and report `False`.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_05.ipynb", EX5)

# ══════════════════════════════════════════════════════════════════════════════
# PROJECT NOTEBOOK
# ══════════════════════════════════════════════════════════════════════════════
PROJECT = nb([
    md("# Day 061 — Project: Monitoring & Logging\n\n"
       "Build `monitored_api.py` — a FastAPI server that logs every request as "
       "structured JSON, tracks metrics, and exposes health and metrics endpoints."),
    md("## Deliverable\n\n"
       "`monitored_api.py` in `project/solution/` — a FastAPI app with:\n\n"
       "| Endpoint | Method | Description |\n"
       "|----------|--------|-------------|\n"
       "| `/health` | GET | Health check |\n"
       "| `/metrics` | GET | Request count, errors, avg latency, error rate |\n"
       "| `/ask` | POST | Ollama Q&A (JSON-logged) |\n\n"
       "**Features:**\n"
       "- `JsonFormatter` — every log line is a parseable JSON object\n"
       "- `MetricsCollector` middleware — records status + duration for every request\n"
       "- `LOG_LEVEL` env var — controls verbosity without code changes\n\n"
       "## How to run\n\n"
       "```bash\n"
       "LOG_LEVEL=DEBUG uvicorn monitored_api:app --reload\n"
       "# Watch structured JSON logs appear per request:\n"
       "curl -X POST http://localhost:8000/ask \\\\\n"
       "     -H 'Content-Type: application/json' \\\\\n"
       "     -d '{\"prompt\": \"What is observability?\"}'\n"
       "# Check metrics:\n"
       "curl http://localhost:8000/metrics\n"
       "```\n\n"
       "## Concepts used\n\n"
       "- `logging.getLogger`, `setLevel`, `StreamHandler` — stdlib logging setup\n"
       "- `JsonFormatter` — one JSON object per log line\n"
       "- `MetricsCollector` — request count, errors, latency\n"
       "- `@app.middleware('http')` — intercept every request/response\n"
       "- `time.monotonic()` for latency measurement"),
])
save(OUT / "project" / "project.ipynb", PROJECT)

# ══════════════════════════════════════════════════════════════════════════════
# SOLUTION NOTEBOOK
# ══════════════════════════════════════════════════════════════════════════════
_SOL_CELL1 = (
    f"_MONITORED_API_SRC = {repr(_MONITORED_API_SRC)}\n"
    "from pathlib import Path\n"
    "Path('monitored_api.py').write_text(_MONITORED_API_SRC)\n"
    "print('monitored_api.py written.')"
)

_SOL_CELL2 = """\
# inline test — no Ollama needed
import json, logging, time
from datetime import datetime
from fastapi import FastAPI, Request
from pydantic import BaseModel, Field
from starlette.testclient import TestClient

# --- JsonFormatter ---
class JsonFormatter(logging.Formatter):
    def format(self, record):
        entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level":     record.levelname,
            "logger":    record.name,
            "message":   record.getMessage(),
        }
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry)

# --- MetricsCollector ---
class MetricsCollector:
    def __init__(self):
        self._requests = 0; self._errors = 0; self._latencies = []
    def record(self, status_code, duration_ms):
        self._requests += 1
        if status_code >= 400: self._errors += 1
        self._latencies.append(duration_ms)
    def summary(self):
        avg = sum(self._latencies) / len(self._latencies) if self._latencies else 0.0
        rate = self._errors / self._requests if self._requests else 0.0
        return {"requests": self._requests, "errors": self._errors,
                "avg_latency_ms": round(avg, 1), "error_rate": round(rate, 3)}
    def reset(self):
        self._requests = 0; self._errors = 0; self._latencies.clear()

# --- build_api ---
def build_api(process_fn=None):
    app = FastAPI(); collector = MetricsCollector()

    @app.middleware("http")
    async def _m(request: Request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        collector.record(response.status_code, (time.monotonic() - start) * 1000)
        return response

    class _AskReq(BaseModel):
        prompt: str = Field(min_length=1)

    @app.get("/health")
    def health():
        return {"status": "ok", "version": "1.0.0"}

    @app.get("/metrics")
    def metrics():
        return collector.summary()

    @app.post("/ask")
    def ask(req: _AskReq):
        answer = process_fn(req.prompt) if process_fn else req.prompt.upper()
        return {"answer": answer}

    return app

# --- tests ---
app    = build_api(process_fn=lambda p: f"Answer: {p}")
client = TestClient(app, raise_server_exceptions=False)

r = client.get("/health")
assert r.status_code == 200 and r.json()["status"] == "ok"
print("\\u2705 /health works")

r2 = client.post("/ask", json={"prompt": "hello"})
assert r2.status_code == 200 and "Answer" in r2.json()["answer"]
print("\\u2705 POST /ask returns answer")

r3 = client.post("/ask", json={"prompt": ""})
assert r3.status_code == 422
print("\\u2705 empty prompt \\u2192 422")

rm = client.get("/metrics")
m = rm.json()
assert m["requests"] == 3
assert m["errors"] == 1
assert m["avg_latency_ms"] >= 0
print("\\u2705 /metrics reports correct counts")

# JsonFormatter check
fmt = JsonFormatter()
rec = logging.LogRecord(name="test", level=logging.INFO, pathname="",
                        lineno=0, msg="solution check", args=(), exc_info=None)
data = json.loads(fmt.format(rec))
assert data["level"] == "INFO" and data["message"] == "solution check"
print("\\u2705 JsonFormatter produces valid JSON")

# make_health_report check (inline)
def make_health_report(services):
    results = {}
    for name, fn in services.items():
        try: results[name] = bool(fn())
        except Exception: results[name] = False
    if not results: status = "ok"
    elif all(results.values()): status = "ok"
    elif not any(results.values()): status = "down"
    else: status = "degraded"
    return {"status": status, "services": results}

assert make_health_report({"db": lambda: True})["status"] == "ok"
assert make_health_report({"db": lambda: False})["status"] == "down"
assert make_health_report({"db": lambda: True, "cache": lambda: False})["status"] == "degraded"
print("\\u2705 make_health_report status logic correct")

print("\\nDay 061 \\u2014 Monitoring & Logging complete! \\U0001f389")
"""

SOLUTION = nb([
    md("# Day 061 — Solution: Monitoring & Logging"),
    code(_SOL_CELL1),
    code(_SOL_CELL2),
])
save(OUT / "project" / "solution" / "solution.ipynb", SOLUTION)
(OUT / "project" / "solution" / "monitored_api.py").write_text(_MONITORED_API_SRC)

print(f"Day {DAY} notebooks written to {OUT}")
print("  exercises/  exercise_01 – exercise_05")
print("  project/    project.ipynb")
print("  project/solution/  solution.ipynb + monitored_api.py")
