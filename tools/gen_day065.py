#!/usr/bin/env python3
"""gen_day065.py — generate Day 065: Capstone Build II notebooks."""
from pathlib import Path
import json

ROOT    = Path(__file__).parent.parent
DAY     = "065"
SECTION = "04_real_apps"
OUT     = ROOT / SECTION / f"day_{DAY}"

(OUT / "exercises").mkdir(parents=True, exist_ok=True)
(OUT / "lessons").mkdir(parents=True, exist_ok=True)
(OUT / "project" / "solution").mkdir(parents=True, exist_ok=True)

# ── deliverable sources ────────────────────────────────────────────────────────
_SHIPPED_APP_SRC = '''\
"""shipped_app.py — Day 065: Capstone Build II — shippable AI Writing Assistant.

All Day 064 features + monitoring middleware + /metrics endpoint.

Setup:
  pip install fastapi "uvicorn[standard]" ollama
  ollama pull llama3.2

Run:  uvicorn shipped_app:app --reload
Docs: http://localhost:8000/docs
Test: pytest test_shipped_app.py -v
"""
import os
import re
import secrets
import time
from datetime import datetime

import ollama
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

APP_VER = "1.1.0"
MODEL   = os.environ.get("MODEL", "llama3.2")

# ── plan configuration ────────────────────────────────────────────────────────

DAILY_LIMITS = {"free": 5, "pro": 500, "enterprise": float("inf")}

FEATURE_MATRIX = {
    "free": {"basic_generate", "view_history"},
    "pro":  {"basic_generate", "view_history", "improve_text", "export"},
}

TEMPLATES = {
    "email":      "Write a {tone} email to {recipient} about {topic}.",
    "tweet":      "Write a {tone} tweet about {topic} in under 280 characters.",
    "summary":    "Write a concise {length}-sentence summary of: {content}",
    "blog_intro": "Write an engaging blog intro about {topic} for a {audience} audience.",
}


def check_feature_access(plan: str, feature: str) -> bool:
    return feature in FEATURE_MATRIX.get(plan, set())


def check_rate_limit(usage_count: int, plan: str) -> tuple[bool, str]:
    limit = DAILY_LIMITS.get(plan, 0)
    if usage_count >= limit:
        return False, (
            f"Daily limit reached for {plan!r} plan "
            f"({usage_count}/{int(limit)}). Upgrade to pro for 500/day."
        )
    return True, ""


def render_template(template_str: str, **vars) -> str:
    required = set(re.findall(r\'\\{(\\w+)\\}\', template_str))
    missing  = required - set(vars.keys())
    if missing:
        raise ValueError(f"Missing template variables: {missing}")
    result = template_str
    for key, value in vars.items():
        result = result.replace(f"{{{key}}}", str(value))
    return result


# ── storage ───────────────────────────────────────────────────────────────────

class ContentStore:
    def __init__(self):
        self._store: dict = {}

    def add(self, user_id: str, prompt: str, content: str) -> str:
        cid = secrets.token_urlsafe(8)
        self._store[cid] = {
            "content_id": cid, "user_id": user_id,
            "prompt": prompt, "content": content,
            "created_at": datetime.utcnow().isoformat() + "Z",
        }
        return cid

    def get(self, content_id: str) -> dict | None:
        return self._store.get(content_id)

    def list_user(self, user_id: str) -> list[dict]:
        return [v for v in self._store.values() if v["user_id"] == user_id]

    def count(self, user_id: str) -> int:
        return sum(1 for v in self._store.values() if v["user_id"] == user_id)


# ── metrics ───────────────────────────────────────────────────────────────────

class MetricsCollector:
    def __init__(self):
        self._requests  = 0
        self._errors    = 0
        self._latencies: list[float] = []

    def record(self, status_code: int, duration_ms: float) -> None:
        self._requests += 1
        if status_code >= 400:
            self._errors += 1
        self._latencies.append(duration_ms)

    def summary(self) -> dict:
        avg  = (sum(self._latencies) / len(self._latencies)
                if self._latencies else 0.0)
        rate = self._errors / self._requests if self._requests else 0.0
        return {
            "requests":       self._requests,
            "errors":         self._errors,
            "avg_latency_ms": round(avg, 1),
            "error_rate":     round(rate, 3),
        }


# ── FastAPI app ───────────────────────────────────────────────────────────────

def build_api(process_fn=None, initial_plan: str = "free",
              initial_usage: int = 0) -> FastAPI:
    app       = FastAPI(title="AI Writing Assistant", version=APP_VER)
    store     = ContentStore()
    collector = MetricsCollector()
    state     = {"plan": initial_plan, "usage": initial_usage}

    @app.middleware("http")
    async def metrics_middleware(request, call_next):
        start    = time.monotonic()
        response = await call_next(request)
        duration = (time.monotonic() - start) * 1000
        collector.record(response.status_code, duration)
        return response

    class _GenReq(BaseModel):
        prompt:  str = Field(min_length=1)
        user_id: str = Field(min_length=1)

    class _TplReq(BaseModel):
        template: str = Field(min_length=1)
        vars:     dict = {}
        user_id:  str  = Field(min_length=1)

    class _ImpReq(BaseModel):
        text:    str = Field(min_length=1)
        user_id: str = Field(min_length=1)

    @app.get("/health")
    def health():
        return {"status": "ok",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "version": APP_VER}

    @app.get("/plan")
    def get_plan():
        lim = DAILY_LIMITS.get(state["plan"], 0)
        return {"plan": state["plan"], "usage_today": state["usage"],
                "limit": lim if lim != float("inf") else -1}

    @app.get("/metrics")
    def get_metrics():
        return collector.summary()

    @app.get("/templates")
    def list_templates():
        return {"templates": list(TEMPLATES.keys())}

    @app.post("/generate")
    def generate(req: _GenReq):
        ok, reason = check_rate_limit(state["usage"], state["plan"])
        if not ok:
            raise HTTPException(429, reason)
        answer = (process_fn(req.prompt) if process_fn
                  else ollama.chat(model=MODEL,
                                   messages=[{"role": "user",
                                              "content": req.prompt}])
                  ["message"]["content"])
        state["usage"] += 1
        cid = store.add(req.user_id, req.prompt, answer)
        return {"content_id": cid, "content": answer, "user_id": req.user_id}

    @app.post("/generate/template")
    def gen_template(req: _TplReq):
        ok, reason = check_rate_limit(state["usage"], state["plan"])
        if not ok:
            raise HTTPException(429, reason)
        tmpl = TEMPLATES.get(req.template)
        if tmpl is None:
            raise HTTPException(400, f"Unknown template: {req.template!r}")
        try:
            prompt = render_template(tmpl, **req.vars)
        except ValueError as e:
            raise HTTPException(400, str(e))
        answer = (process_fn(prompt) if process_fn
                  else ollama.chat(model=MODEL,
                                   messages=[{"role": "user",
                                              "content": prompt}])
                  ["message"]["content"])
        state["usage"] += 1
        cid = store.add(req.user_id, prompt, answer)
        return {"content_id": cid, "content": answer,
                "template": req.template, "user_id": req.user_id}

    @app.post("/improve")
    def improve(req: _ImpReq):
        if not check_feature_access(state["plan"], "improve_text"):
            raise HTTPException(403, "improve_text requires pro plan. "
                                     "Upgrade at /checkout")
        ok, reason = check_rate_limit(state["usage"], state["plan"])
        if not ok:
            raise HTTPException(429, reason)
        prompt = f"Improve this text for clarity and style:\\n\\n{req.text}"
        answer = (process_fn(prompt) if process_fn
                  else ollama.chat(model=MODEL,
                                   messages=[{"role": "user",
                                              "content": prompt}])
                  ["message"]["content"])
        state["usage"] += 1
        cid = store.add(req.user_id, prompt, answer)
        return {"content_id": cid, "original": req.text,
                "improved": answer, "user_id": req.user_id}

    @app.get("/history/{user_id}")
    def history(user_id: str):
        items = store.list_user(user_id)
        return {"user_id": user_id, "count": len(items), "items": items}

    @app.get("/content/{content_id}")
    def get_content(content_id: str):
        item = store.get(content_id)
        if item is None:
            raise HTTPException(404, f"Content {content_id!r} not found")
        return item

    return app


app = build_api()

if __name__ == "__main__":
    import uvicorn
    PORT = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=PORT)
'''

_TEST_SRC = '''\
"""test_shipped_app.py — pytest test suite for shipped_app.

Run:
  pytest test_shipped_app.py -v
  pytest test_shipped_app.py -v -k generate
"""
import pytest
from starlette.testclient import TestClient
from shipped_app import build_api


@pytest.fixture
def client():
    return TestClient(build_api(plan="free", process_fn=str.upper),
                      raise_server_exceptions=False)


@pytest.fixture
def pro_client():
    return TestClient(build_api(plan="pro", process_fn=str.upper),
                      raise_server_exceptions=False)


@pytest.fixture
def at_limit_client():
    return TestClient(
        build_api(plan="free", process_fn=str.upper, initial_usage=5),
        raise_server_exceptions=False,
    )


# ── infrastructure ─────────────────────────────────────────────────────────────

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "ok"
    assert "timestamp" in d and "version" in d


def test_plan(client):
    r = client.get("/plan")
    assert r.status_code == 200
    d = r.json()
    assert d["plan"] == "free"
    assert d["usage_today"] == 0
    assert d["limit"] == 5


def test_templates(client):
    r = client.get("/templates")
    assert r.status_code == 200
    assert isinstance(r.json()["templates"], list)
    assert len(r.json()["templates"]) > 0


def test_metrics(client):
    r = client.get("/metrics")
    assert r.status_code == 200
    d = r.json()
    for key in ("requests", "errors", "avg_latency_ms", "error_rate"):
        assert key in d, f"Missing key: {key}"


# ── generation ─────────────────────────────────────────────────────────────────

def test_generate_ok(client):
    r = client.post("/generate", json={"prompt": "hello", "user_id": "u1"})
    assert r.status_code == 200
    d = r.json()
    assert "content_id" in d
    assert d["content"] == "HELLO"
    assert d["user_id"] == "u1"


@pytest.mark.parametrize("body,expected", [
    ({"prompt": "", "user_id": "u1"}, 422),    # empty prompt
    ({"prompt": "hi"}, 422),                   # missing user_id
    ({}, 422),                                  # empty body
])
def test_generate_validation(client, body, expected):
    r = client.post("/generate", json=body)
    assert r.status_code == expected, f"got {r.status_code}: {r.text[:120]}"


def test_generate_rate_limit(at_limit_client):
    r = at_limit_client.post("/generate",
                             json={"prompt": "hi", "user_id": "u1"})
    assert r.status_code == 429


def test_generate_usage_increments(client):
    client.post("/generate", json={"prompt": "a", "user_id": "u1"})
    client.post("/generate", json={"prompt": "b", "user_id": "u1"})
    r = client.get("/plan")
    assert r.json()["usage_today"] == 2


# ── history ────────────────────────────────────────────────────────────────────

def test_history_empty(client):
    r = client.get("/history/nobody")
    assert r.status_code == 200
    assert r.json()["count"] == 0


def test_history_after_generate(client):
    client.post("/generate", json={"prompt": "x", "user_id": "alice"})
    client.post("/generate", json={"prompt": "y", "user_id": "alice"})
    client.post("/generate", json={"prompt": "z", "user_id": "bob"})
    r = client.get("/history/alice")
    assert r.json()["count"] == 2
    assert all(i["user_id"] == "alice" for i in r.json()["items"])


def test_content_get(client):
    rg  = client.post("/generate", json={"prompt": "hi", "user_id": "u"})
    cid = rg.json()["content_id"]
    rc  = client.get(f"/content/{cid}")
    assert rc.status_code == 200
    assert rc.json()["content_id"] == cid


def test_content_not_found(client):
    assert client.get("/content/does_not_exist").status_code == 404


# ── feature gating ─────────────────────────────────────────────────────────────

def test_improve_requires_pro(client):
    r = client.post("/improve", json={"text": "hello", "user_id": "u1"})
    assert r.status_code == 403


def test_improve_works_for_pro(pro_client):
    r = pro_client.post("/improve", json={"text": "hello", "user_id": "u1"})
    assert r.status_code == 200
    assert "improved" in r.json()


# ── state isolation ────────────────────────────────────────────────────────────

def test_isolation_between_clients():
    c1 = TestClient(build_api(plan="free", process_fn=str.upper),
                    raise_server_exceptions=False)
    c2 = TestClient(build_api(plan="free", process_fn=str.upper),
                    raise_server_exceptions=False)
    c1.post("/generate", json={"prompt": "a", "user_id": "u"})
    assert c2.get("/history/u").json()["count"] == 0
'''

_RENDER_YAML = """\
services:
  - type: web
    name: writing-assistant
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn shipped_app:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: MODEL
        value: llama3.2
      - key: STRIPE_SECRET_KEY
        sync: false
      - key: STRIPE_WEBHOOK_SECRET
        sync: false
      - key: PORT
        generateValue: false
"""

_ENV_EXAMPLE = """\
# Copy to .env and fill in values before running locally.
# Never commit .env to git.
MODEL=llama3.2
PORT=8000
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
"""

_REQUIREMENTS = "fastapi\nhttpx\nollama\nuvicorn[standard]\n"
_PROCFILE     = "web: uvicorn shipped_app:app --host 0.0.0.0 --port $PORT\n"

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
# EXERCISE 1 — add_metrics_middleware
# ══════════════════════════════════════════════════════════════════════════════
_EX1_GIVEN = """\
import time
from fastapi import FastAPI
from starlette.testclient import TestClient

class MetricsCollector:
    \"\"\"Records HTTP request metrics (from Day 061).\"\"\"
    def __init__(self):
        self._requests  = 0
        self._errors    = 0
        self._latencies: list[float] = []

    def record(self, status_code: int, duration_ms: float) -> None:
        self._requests += 1
        if status_code >= 400:
            self._errors += 1
        self._latencies.append(duration_ms)

    def summary(self) -> dict:
        avg  = sum(self._latencies)/len(self._latencies) if self._latencies else 0.0
        rate = self._errors/self._requests if self._requests else 0.0
        return {
            "requests":       self._requests,
            "errors":         self._errors,
            "avg_latency_ms": round(avg, 1),
            "error_rate":     round(rate, 3),
        }

    def reset(self):
        self._requests = 0; self._errors = 0; self._latencies.clear()
"""

_EX1_STUB = """\
def add_metrics_middleware(app: FastAPI,
                           collector: MetricsCollector) -> FastAPI:
    \"\"\"Add HTTP middleware and /metrics endpoint to an existing FastAPI app.

    The middleware:
    - Captures start time before each request (time.monotonic())
    - Calls next handler (await call_next(request))
    - Computes duration_ms = (time.monotonic() - start) * 1000
    - Records via collector.record(response.status_code, duration_ms)

    The /metrics endpoint:
    - GET /metrics → collector.summary()

    Returns the same app (mutates it).
    \"\"\"
    # TODO: add @app.middleware('http') + GET /metrics route
    raise NotImplementedError
"""

_EX1_SOLUTION = """\
def add_metrics_middleware(app: FastAPI,
                           collector: MetricsCollector) -> FastAPI:
    @app.middleware("http")
    async def _middleware(request, call_next):
        start    = time.monotonic()
        response = await call_next(request)
        duration = (time.monotonic() - start) * 1000
        collector.record(response.status_code, duration)
        return response

    @app.get("/metrics")
    def _metrics():
        return collector.summary()

    return app
"""

_EX1_CHECKS = """\
score, total = 0, 5
try:
    from fastapi import FastAPI
    from starlette.testclient import TestClient
    from starlette.responses import JSONResponse

    # build a minimal app to instrument
    base_app  = FastAPI()
    collector = MetricsCollector()

    @base_app.get("/ping")
    def ping(): return {"pong": True}

    @base_app.get("/boom")
    def boom(): return JSONResponse({"err": "oops"}, status_code=500)

    add_metrics_middleware(base_app, collector)
    c = TestClient(base_app, raise_server_exceptions=False)

    # /metrics endpoint exists
    r = c.get("/metrics")
    assert r.status_code == 200
    score += 1; print("\\u2705 GET /metrics endpoint exists and returns 200")

    # make 2 successful requests
    c.get("/ping"); c.get("/ping")
    m = c.get("/metrics").json()
    # middleware records /metrics too, so requests >= 2 (exact count depends on order)
    assert m["requests"] >= 2
    score += 1; print("\\u2705 requests counter increments on each call")

    # trigger an error
    c.get("/boom")
    m2 = c.get("/metrics").json()
    assert m2["errors"] >= 1
    score += 1; print("\\u2705 errors counter increments on 5xx responses")

    # avg_latency_ms is a float >= 0
    assert isinstance(m2["avg_latency_ms"], (int, float)) and m2["avg_latency_ms"] >= 0
    score += 1; print("\\u2705 avg_latency_ms is a non-negative number")

    # error_rate between 0 and 1
    assert 0.0 <= m2["error_rate"] <= 1.0
    score += 1; print("\\u2705 error_rate is between 0.0 and 1.0")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX1 = nb([
    md("# Day 065 — Exercise 1: Metrics Middleware\n\n"
       "Day 061 introduced `MetricsCollector` and `@app.middleware('http')`. "
       "Today we combine them into a reusable function: `add_metrics_middleware` "
       "takes any existing FastAPI app and instruments it — adding the middleware "
       "and a `/metrics` endpoint — then returns the same app.\n\n"
       "This is the **decorator pattern**: enhance an object without modifying "
       "its original definition."),
    code(_EX1_GIVEN),
    md("## Task\n\n"
       "Implement `add_metrics_middleware(app, collector) -> FastAPI`:\n\n"
       "1. Add `@app.middleware('http')` that times each request and calls "
       "`collector.record(status_code, duration_ms)`\n"
       "2. Add `GET /metrics` → `collector.summary()`\n"
       "3. Return the same `app` object\n\n"
       "Timing: `start = time.monotonic()` → `await call_next(request)` → "
       "`duration = (time.monotonic() - start) * 1000`"),
    md("## Your Implementation"),
    code(_EX1_STUB),
    code(_EX1_SOLUTION),
    md("## Automated checks"),
    code(_EX1_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX1_SOLUTION + "```\n\n"
       "**Why mutate and return?** Returning `app` allows chaining: "
       "`add_monitoring(add_cors(FastAPI(), origins), collector)`. "
       "It also makes testing natural: `app = add_metrics_middleware(build_base(), c)`. "
       "Mutating is safe here because FastAPI registers middleware at definition time.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_01.ipynb", EX1)

# ══════════════════════════════════════════════════════════════════════════════
# EXERCISE 2 — run_test_battery
# ══════════════════════════════════════════════════════════════════════════════
_EX2_GIVEN = """\
from fastapi import FastAPI
from pydantic import BaseModel, Field
from starlette.testclient import TestClient

# A minimal test app to run the battery against
def build_test_app():
    app = FastAPI()
    class _R(BaseModel):
        prompt: str = Field(min_length=1)
    @app.get("/health")
    def h(): return {"status": "ok"}
    @app.post("/echo")
    def echo(req: _R): return {"echo": req.prompt}
    return app
"""

_EX2_STUB = """\
def run_test_battery(client, cases: list[dict]) -> dict:
    \"\"\"Run a list of API test cases and return a summary.

    Each case dict:
        name:            str — human-readable test name
        method:          str — 'GET' or 'POST'
        path:            str — URL path
        json:            dict | None — request body (optional)
        expected_status: int — expected HTTP status code

    Returns:
        {
          'passed':  int,
          'failed':  int,
          'total':   int,
          'results': list[{name, expected, got, passed: bool}],
        }

    Never raises — catch all exceptions and mark as failed.
    \"\"\"
    # TODO: iterate cases, call client.request(method, path, json=...),
    #       compare status_code, collect results
    raise NotImplementedError
"""

_EX2_SOLUTION = """\
def run_test_battery(client, cases: list[dict]) -> dict:
    results = []
    for case in cases:
        name     = case["name"]
        method   = case["method"]
        path     = case["path"]
        body     = case.get("json")
        expected = case["expected_status"]
        try:
            r   = client.request(method, path, json=body)
            got = r.status_code
        except Exception as e:
            got = -1
            name = f"{name} [ERROR: {e}]"
        passed = (got == expected)
        results.append({"name": name, "expected": expected,
                        "got": got, "passed": passed})
    passed_n = sum(1 for r in results if r["passed"])
    return {"passed": passed_n, "failed": len(results) - passed_n,
            "total": len(results), "results": results}
"""

_EX2_CHECKS = """\
score, total = 0, 5
try:
    app = build_test_app()
    c   = TestClient(app, raise_server_exceptions=False)

    cases = [
        {"name": "health ok",      "method": "GET",  "path": "/health",
         "json": None,             "expected_status": 200},
        {"name": "echo ok",        "method": "POST", "path": "/echo",
         "json": {"prompt": "hi"}, "expected_status": 200},
        {"name": "echo empty",     "method": "POST", "path": "/echo",
         "json": {"prompt": ""},   "expected_status": 422},
        {"name": "not found",      "method": "GET",  "path": "/missing",
         "json": None,             "expected_status": 404},
        {"name": "intentional fail","method": "GET",  "path": "/health",
         "json": None,             "expected_status": 999},   # wrong expected
    ]

    result = run_test_battery(c, cases)

    # has required keys
    for k in ("passed", "failed", "total", "results"):
        assert k in result, f"Missing key: {k}"
    score += 1; print("\\u2705 result has all required keys")

    # total = len(cases)
    assert result["total"] == len(cases)
    score += 1; print("\\u2705 total == len(cases)")

    # first 4 should pass, last one fails (expected=999)
    assert result["passed"] == 4
    assert result["failed"] == 1
    score += 1; print("\\u2705 passed=4, failed=1 (correct pass/fail split)")

    # results list has one entry per case
    assert len(result["results"]) == len(cases)
    score += 1; print("\\u2705 results list has one entry per case")

    # each result has name, expected, got, passed
    for r in result["results"]:
        assert all(k in r for k in ("name", "expected", "got", "passed"))
    score += 1; print("\\u2705 each result entry has name/expected/got/passed")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX2 = nb([
    md("# Day 065 — Exercise 2: Test Battery Runner\n\n"
       "Day 062 taught `pytest` and `@pytest.mark.parametrize`. For a product "
       "launch you also want a **programmatic test runner** — one you can call "
       "from a notebook, a CI script, or a health-check endpoint.\n\n"
       "`run_test_battery` takes a list of test-case dicts and a TestClient, "
       "runs every case, and returns a structured summary — never raising, "
       "always collecting all results."),
    code(_EX2_GIVEN),
    md("## Task\n\n"
       "Implement `run_test_battery(client, cases) -> dict`:\n\n"
       "- Iterate `cases`: each has `name`, `method`, `path`, `json` (optional), "
       "`expected_status`\n"
       "- Call `client.request(method, path, json=body)` — handle exceptions\n"
       "- Compare `r.status_code == expected_status` → `passed: bool`\n"
       "- Return `{passed, failed, total, results: [{name, expected, got, passed}]}`"),
    md("## Your Implementation"),
    code(_EX2_STUB),
    code(_EX2_SOLUTION),
    md("## Automated checks"),
    code(_EX2_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX2_SOLUTION + "```\n\n"
       "**Never raise in a test runner**: wrapping in try/except means a "
       "network error or unexpected exception marks the test failed but lets "
       "all other tests run. One crash shouldn't blank out 20 results. "
       "`got = -1` for exceptions makes it visually obvious in the results dict.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_02.ipynb", EX2)

# ══════════════════════════════════════════════════════════════════════════════
# EXERCISE 3 — check_readiness
# ══════════════════════════════════════════════════════════════════════════════
_EX3_STUB = """\
def check_readiness(client) -> dict:
    \"\"\"Run pre-deploy readiness checks against a TestClient.

    Checks performed:
        health_ok        GET /health → 200 with status='ok'
        templates_exist  GET /templates → 200 with non-empty 'templates' list
        validation_works POST /generate with empty prompt → 422
        rate_limit_works POST /generate with valid body → 200 (not 429)

    Returns:
        {
          'ready':  bool,          # True only if ALL checks pass
          'checks': list[{name: str, passed: bool, detail: str}],
        }
    \"\"\"
    # TODO: run each check, collect {name, passed, detail}, compute ready
    raise NotImplementedError
"""

_EX3_SOLUTION = """\
def check_readiness(client) -> dict:
    checks = []

    def run(name, fn):
        try:
            passed, detail = fn()
        except Exception as e:
            passed, detail = False, str(e)
        checks.append({"name": name, "passed": passed, "detail": detail})

    def _health():
        r = client.get("/health")
        ok = r.status_code == 200 and r.json().get("status") == "ok"
        return ok, f"status={r.status_code}"

    def _templates():
        r = client.get("/templates")
        if r.status_code != 200:
            return False, f"status={r.status_code}"
        tmpl = r.json().get("templates", [])
        ok = isinstance(tmpl, list) and len(tmpl) > 0
        return ok, f"{len(tmpl)} templates found"

    def _validation():
        r = client.post("/generate", json={"prompt": "", "user_id": "x"})
        ok = r.status_code == 422
        return ok, f"status={r.status_code} (want 422)"

    def _generate():
        r = client.post("/generate", json={"prompt": "hi", "user_id": "x"})
        ok = r.status_code == 200
        return ok, f"status={r.status_code} (want 200)"

    run("health_ok", _health)
    run("templates_exist", _templates)
    run("validation_works", _validation)
    run("rate_limit_works", _generate)

    return {"ready": all(c["passed"] for c in checks), "checks": checks}
"""

_EX3_GIVEN_IMPORTS = """\
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from starlette.testclient import TestClient

# Pre-built apps for checks
def _full_app():
    \"\"\"Complete writing-assistant-style app.\"\"\"
    app = FastAPI()
    class _R(BaseModel):
        prompt:  str = Field(min_length=1)
        user_id: str = Field(min_length=1)
    @app.get("/health")
    def h(): return {"status": "ok"}
    @app.get("/templates")
    def t(): return {"templates": ["email", "tweet"]}
    @app.post("/generate")
    def g(req: _R): return {"content_id": "cid", "content": req.prompt.upper(),
                             "user_id": req.user_id}
    return app

def _bare_app():
    \"\"\"Minimal app — only health, no generate/templates.\"\"\"
    app = FastAPI()
    @app.get("/health")
    def h(): return {"status": "ok"}
    return app
"""

_EX3_CHECKS = """\
score, total = 0, 5
try:
    # Full app → ready
    full_client = TestClient(_full_app(), raise_server_exceptions=False)
    r_full = check_readiness(full_client)
    assert isinstance(r_full, dict) and "ready" in r_full and "checks" in r_full
    score += 1; print("\\u2705 returns dict with 'ready' and 'checks' keys")

    assert r_full["ready"] is True, f"expected ready=True: {r_full['checks']}"
    score += 1; print("\\u2705 full app → ready=True")

    assert isinstance(r_full["checks"], list) and len(r_full["checks"]) >= 3
    score += 1; print("\\u2705 checks list has at least 3 entries")

    each_ok = all(isinstance(c, dict) and
                  all(k in c for k in ("name", "passed", "detail"))
                  for c in r_full["checks"])
    assert each_ok, "each check must have name, passed, detail"
    score += 1; print("\\u2705 each check has name, passed, detail")

    # Bare app → not ready
    bare_client = TestClient(_bare_app(), raise_server_exceptions=False)
    r_bare = check_readiness(bare_client)
    assert r_bare["ready"] is False, f"expected ready=False: {r_bare['checks']}"
    score += 1; print("\\u2705 bare app (missing routes) → ready=False")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX3 = nb([
    md("# Day 065 — Exercise 3: Readiness Checker\n\n"
       "Before deploying, run a **readiness check**: a structured set of "
       "assertions that verify the app behaves correctly. If any check fails, "
       "abort the deploy. This is the principle behind Kubernetes "
       "readinessProbes and Render's health checks — automated gates that "
       "prevent a broken build reaching production.\n\n"
       "Our readiness checker verifies four properties:\n\n"
       "| Check | Verifies |\n"
       "|-------|----------|\n"
       "| `health_ok` | `/health` returns 200 with `status='ok'` |\n"
       "| `templates_exist` | `/templates` returns a non-empty list |\n"
       "| `validation_works` | Empty prompt → 422 (Pydantic validation active) |\n"
       "| `rate_limit_works` | Valid prompt → 200 (app actually works) |"),
    code(_EX3_GIVEN_IMPORTS),
    md("## Task\n\n"
       "Implement `check_readiness(client) -> dict`:\n\n"
       "- Run each check in a try/except (exception = failed)\n"
       "- Collect `{name, passed: bool, detail: str}` per check\n"
       "- `ready = all(c['passed'] for c in checks)`\n"
       "- Return `{ready: bool, checks: list[...]}`"),
    md("## Your Implementation"),
    code(_EX3_STUB),
    code(_EX3_SOLUTION),
    md("## Automated checks"),
    code(_EX3_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX3_SOLUTION + "```\n\n"
       "**The inner `run` helper** eliminates the try/except repetition — "
       "write each check as a plain function that returns `(passed, detail)`, "
       "then wrap it once. `all(c['passed'] for c in checks)` short-circuits "
       "on the first failure — but here we collect all checks first so the "
       "report shows everything that failed, not just the first.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_03.ipynb", EX3)

# ══════════════════════════════════════════════════════════════════════════════
# EXERCISE 4 — write_deploy_files
# ══════════════════════════════════════════════════════════════════════════════
_RENDER_YAML_TMPL = """\
services:
  - type: web
    name: {app_name}
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn {module}:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: MODEL
        value: llama3.2
      - key: STRIPE_SECRET_KEY
        sync: false
      - key: STRIPE_WEBHOOK_SECRET
        sync: false
"""

_ENV_EXAMPLE_TMPL = """\
# Copy to .env and fill in values. Never commit .env to git.
MODEL=llama3.2
PORT=8000
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
"""

_EX4_GIVEN = f"""\
from pathlib import Path

_RENDER_YAML_TMPL = {repr(_RENDER_YAML_TMPL)}

_ENV_EXAMPLE = {repr(_ENV_EXAMPLE_TMPL)}
"""

_EX4_STUB = """\
def write_deploy_files(directory: str, app_name: str = "my-app",
                       module: str = "app",
                       packages: list[str] | None = None) -> list[str]:
    \"\"\"Write deployment configuration files to directory.

    Files created:
        requirements.txt  — one package per line (packages arg, or defaults)
        Procfile          — web: uvicorn {module}:app --host 0.0.0.0 --port $PORT
        render.yaml       — Render service definition (use _RENDER_YAML_TMPL)
        .env.example      — environment variable template (use _ENV_EXAMPLE)

    packages default: ['fastapi', 'uvicorn[standard]', 'ollama', 'httpx']
    Returns list of filenames written.
    \"\"\"
    # TODO: build each file content, write to directory, return list of names
    raise NotImplementedError
"""

_EX4_SOLUTION = """\
def write_deploy_files(directory: str, app_name: str = "my-app",
                       module: str = "app",
                       packages: list[str] | None = None) -> list[str]:
    base = Path(directory)
    base.mkdir(parents=True, exist_ok=True)
    pkgs = packages or ["fastapi", "uvicorn[standard]", "ollama", "httpx"]

    files = {
        "requirements.txt": "\\n".join(pkgs) + "\\n",
        "Procfile":         f"web: uvicorn {module}:app --host 0.0.0.0 --port $PORT\\n",
        "render.yaml":      _RENDER_YAML_TMPL.format(app_name=app_name, module=module),
        ".env.example":     _ENV_EXAMPLE,
    }
    for fname, content in files.items():
        (base / fname).write_text(content, encoding="utf-8")
    return list(files.keys())
"""

_EX4_CHECKS = """\
score, total = 0, 6
try:
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        created = write_deploy_files(tmpdir, app_name="test-app", module="app")

        # returns a list of at least 4 filenames
        assert isinstance(created, list) and len(created) >= 4
        score += 1; print("\\u2705 returns list of at least 4 filenames")

        # all files exist
        for f in created:
            assert (Path(tmpdir) / f).exists(), f"{f} missing"
        score += 1; print("\\u2705 all listed files exist on disk")

        # requirements.txt has fastapi
        req = (Path(tmpdir) / "requirements.txt").read_text()
        assert "fastapi" in req.lower()
        score += 1; print("\\u2705 requirements.txt contains fastapi")

        # Procfile references $PORT and uvicorn
        proc = (Path(tmpdir) / "Procfile").read_text()
        assert "uvicorn" in proc and "$PORT" in proc
        score += 1; print("\\u2705 Procfile has uvicorn and $PORT")

        # render.yaml references the app_name
        render = (Path(tmpdir) / "render.yaml").read_text()
        assert "test-app" in render
        score += 1; print("\\u2705 render.yaml contains app_name")

        # .env.example has MODEL=
        env_ex = (Path(tmpdir) / ".env.example").read_text()
        assert "MODEL=" in env_ex
        score += 1; print("\\u2705 .env.example contains MODEL=")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX4 = nb([
    md("# Day 065 — Exercise 4: Write Deploy Files\n\n"
       "A deployable app needs four files that most developers write manually "
       "and get slightly wrong each time. Generate them programmatically from "
       "a single function call — consistent, repeatable, and easy to add to a "
       "project generator.\n\n"
       "| File | Purpose |\n"
       "|------|---------|\n"
       "| `requirements.txt` | Package list for `pip install -r` |\n"
       "| `Procfile` | Start command for Render/Railway/Heroku |\n"
       "| `render.yaml` | Render service definition (IaC) |\n"
       "| `.env.example` | Documents every required environment variable |"),
    code(_EX4_GIVEN),
    md("## Task\n\n"
       "Implement `write_deploy_files(directory, app_name, module, packages) -> list[str]`:\n\n"
       "- Default packages: `['fastapi', 'uvicorn[standard]', 'ollama', 'httpx']`\n"
       "- `requirements.txt`: `'\\n'.join(packages) + '\\n'`\n"
       "- `Procfile`: `f'web: uvicorn {module}:app --host 0.0.0.0 --port $PORT\\n'`\n"
       "- `render.yaml`: fill `_RENDER_YAML_TMPL` with `app_name` and `module`\n"
       "- `.env.example`: write `_ENV_EXAMPLE` verbatim\n"
       "- Return list of filenames created"),
    md("## Your Implementation"),
    code(_EX4_STUB),
    code(_EX4_SOLUTION),
    md("## Automated checks"),
    code(_EX4_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX4_SOLUTION + "```\n\n"
       "**Why `.env.example` not `.env`?** `.env` is in `.gitignore` because it "
       "contains real secrets. `.env.example` is committed — it documents what "
       "variables are required without exposing values. New team members copy it "
       "to `.env` and fill in their own credentials.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_04.ipynb", EX4)

# ══════════════════════════════════════════════════════════════════════════════
# EXERCISE 5 — run_integration_test (end-to-end)
# ══════════════════════════════════════════════════════════════════════════════
_EX5_GIVEN = """\
import re, secrets, time
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from starlette.testclient import TestClient

# ── same components as shipped_app (local copies for this exercise) ────────────
DAILY_LIMITS = {"free": 5, "pro": 500}
TEMPLATES    = {"email": "Write a {tone} email about {topic}."}

def check_rate_limit(usage_count, plan):
    limit = DAILY_LIMITS.get(plan, 0)
    if usage_count >= limit: return False, "limit"
    return True, ""

class ContentStore:
    def __init__(self): self._store = {}
    def add(self, uid, p, c):
        cid = secrets.token_urlsafe(8)
        self._store[cid] = {"content_id": cid, "user_id": uid,
                             "prompt": p, "content": c}
        return cid
    def get(self, cid): return self._store.get(cid)
    def list_user(self, uid): return [v for v in self._store.values() if v["user_id"]==uid]

class MetricsCollector:
    def __init__(self): self._req=0; self._err=0; self._lat=[]
    def record(self, sc, ms): self._req+=1; (self._err.__class__.__add__) ; \
        self._err += (1 if sc>=400 else 0); self._lat.append(ms)
    def summary(self): avg=sum(self._lat)/len(self._lat) if self._lat else 0.0; \
        return {"requests":self._req,"errors":self._err,
                "avg_latency_ms":round(avg,1),"error_rate":round(self._err/self._req if self._req else 0,3)}

def build_app_under_test(plan="free", process_fn=None, initial_usage=0):
    app=FastAPI(); store=ContentStore(); collector=MetricsCollector()
    state={"plan":plan,"usage":initial_usage}
    class _G(BaseModel): prompt:str=Field(min_length=1); user_id:str=Field(min_length=1)
    @app.middleware("http")
    async def mw(req, call_next):
        s=time.monotonic(); r=await call_next(req)
        collector.record(r.status_code,(time.monotonic()-s)*1000); return r
    @app.get("/health")
    def h(): return {"status":"ok","version":"1.1.0"}
    @app.get("/plan")
    def p(): lim=DAILY_LIMITS.get(state["plan"],0); return {"plan":state["plan"],"usage_today":state["usage"],"limit":lim}
    @app.get("/metrics")
    def m(): return collector.summary()
    @app.get("/templates")
    def t(): return {"templates":list(TEMPLATES.keys())}
    @app.post("/generate")
    def g(req:_G):
        ok,reason=check_rate_limit(state["usage"],state["plan"])
        if not ok: raise HTTPException(429,reason)
        ans=process_fn(req.prompt) if process_fn else req.prompt.upper()
        state["usage"]+=1; cid=store.add(req.user_id,req.prompt,ans)
        return {"content_id":cid,"content":ans,"user_id":req.user_id}
    @app.get("/history/{user_id}")
    def hst(user_id:str): items=store.list_user(user_id); return {"user_id":user_id,"count":len(items),"items":items}
    @app.get("/content/{content_id}")
    def gc(content_id:str):
        item=store.get(content_id)
        if item is None: raise HTTPException(404)
        return item
    return app
"""

_EX5_STUB = """\
def run_integration_test(app_factory) -> dict:
    \"\"\"End-to-end smoke test of a writing-assistant-style app.

    app_factory: zero-arg callable → FastAPI app
                 (should use process_fn=str.upper internally)

    Tests performed:
        1. GET /health           → 200 with status='ok'
        2. GET /templates        → 200 with non-empty templates list
        3. POST /generate (ok)   → 200 with content_id
        4. GET /history/{user}   → count=1 after one generate
        5. GET /content/{cid}    → 200, item matches generate response
        6. POST /generate (empty)→ 422 (validation)
        7. Rate-limit test       → build new app with initial_usage=5,
                                   POST /generate → 429
        8. GET /metrics          → 200 with 'requests' key

    Returns:
        {passed: int, failed: int, total: int, failures: list[str]}

    Never raises — all failures collected.
    \"\"\"
    # TODO: create client, run each test, collect failures, return summary
    raise NotImplementedError
"""

_EX5_SOLUTION = """\
def run_integration_test(app_factory) -> dict:
    failures = []
    total    = 8

    def check(name, cond, detail=""):
        if not cond:
            failures.append(f"{name}: {detail}" if detail else name)

    app = app_factory()
    c   = TestClient(app, raise_server_exceptions=False)

    # 1. health
    try:
        r = c.get("/health")
        check("health_ok", r.status_code == 200 and
              r.json().get("status") == "ok", f"got {r.status_code}")
    except Exception as e:
        failures.append(f"health_ok ERROR: {e}")

    # 2. templates
    try:
        r = c.get("/templates")
        check("templates_exist",
              r.status_code == 200 and len(r.json().get("templates", [])) > 0)
    except Exception as e:
        failures.append(f"templates_exist ERROR: {e}")

    # 3. generate ok
    cid = None
    try:
        r = c.post("/generate", json={"prompt": "hello", "user_id": "u_test"})
        check("generate_200", r.status_code == 200, f"got {r.status_code}")
        cid = r.json().get("content_id") if r.status_code == 200 else None
    except Exception as e:
        failures.append(f"generate_200 ERROR: {e}")

    # 4. history
    try:
        r = c.get("/history/u_test")
        check("history_count", r.status_code == 200 and
              r.json().get("count", 0) == 1)
    except Exception as e:
        failures.append(f"history_count ERROR: {e}")

    # 5. content get
    try:
        if cid:
            r = c.get(f"/content/{cid}")
            check("content_get", r.status_code == 200)
        else:
            failures.append("content_get SKIP: no cid from generate")
    except Exception as e:
        failures.append(f"content_get ERROR: {e}")

    # 6. validation
    try:
        r = c.post("/generate", json={"prompt": "", "user_id": "u"})
        check("validation_422", r.status_code == 422, f"got {r.status_code}")
    except Exception as e:
        failures.append(f"validation_422 ERROR: {e}")

    # 7. rate limit (separate at-limit app)
    try:
        at_limit = TestClient(
            build_app_under_test(plan="free", process_fn=str.upper,
                                 initial_usage=5),
            raise_server_exceptions=False,
        )
        r = at_limit.post("/generate", json={"prompt": "x", "user_id": "u"})
        check("rate_limit_429", r.status_code == 429, f"got {r.status_code}")
    except Exception as e:
        failures.append(f"rate_limit_429 ERROR: {e}")

    # 8. metrics
    try:
        r = c.get("/metrics")
        check("metrics_ok",
              r.status_code == 200 and "requests" in r.json())
    except Exception as e:
        failures.append(f"metrics_ok ERROR: {e}")

    passed = total - len(failures)
    return {"passed": passed, "failed": len(failures),
            "total": total, "failures": failures}
"""

_EX5_CHECKS = """\
score, total = 0, 4
try:
    def _factory():
        return build_app_under_test(plan="free", process_fn=str.upper)

    result = run_integration_test(_factory)

    # has required keys
    assert all(k in result for k in ("passed","failed","total","failures"))
    score += 1; print("\\u2705 result has passed/failed/total/failures keys")

    # total == 8
    assert result["total"] == 8, f"expected total=8, got {result['total']}"
    score += 1; print("\\u2705 total == 8 tests")

    # all 8 tests pass for a correct app
    assert result["passed"] == 8, (
        f"Expected 8 passed, got {result['passed']}. "
        f"Failures: {result['failures']}"
    )
    score += 1; print("\\u2705 all 8 tests pass for a correct app")

    # failures is a list
    assert isinstance(result["failures"], list)
    score += 1; print("\\u2705 failures is a list")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX5 = nb([
    md("# Day 065 — Exercise 5: End-to-End Integration Test\n\n"
       "An **integration test** exercises the whole system as a user would. "
       "It's the last gate before deploy: if this passes, the app is shippable.\n\n"
       "`run_integration_test` takes an app factory, builds the app, and runs "
       "8 checks covering every major behaviour:\n\n"
       "| # | Test | Checks |\n"
       "|---|------|--------|\n"
       "| 1 | health | 200 + status='ok' |\n"
       "| 2 | templates | non-empty list |\n"
       "| 3 | generate | 200 + content_id |\n"
       "| 4 | history | count=1 after generate |\n"
       "| 5 | content get | item found by id |\n"
       "| 6 | validation | empty prompt → 422 |\n"
       "| 7 | rate limit | at-limit → 429 |\n"
       "| 8 | metrics | /metrics with requests key |"),
    code(_EX5_GIVEN),
    md("## Task\n\n"
       "Implement `run_integration_test(app_factory) -> dict`:\n\n"
       "- Call `app_factory()` to get the FastAPI app\n"
       "- Wrap in `TestClient(app, raise_server_exceptions=False)`\n"
       "- Run all 8 checks; collect failures without raising\n"
       "- For the rate-limit check (7), create a fresh at-limit app via "
       "`build_app_under_test(initial_usage=5)`\n"
       "- Return `{passed, failed, total, failures: list[str]}`"),
    md("## Your Implementation"),
    code(_EX5_STUB),
    code(_EX5_SOLUTION),
    md("## Automated checks"),
    code(_EX5_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX5_SOLUTION + "```\n\n"
       "**The `check(name, cond)` helper** is the same pattern as `assert_response` "
       "from Day 062 — single-line test with a named failure. Wrapping each check "
       "in `try/except` means an exception in test 3 doesn't prevent tests 4-8 "
       "from running. `failures: list[str]` is more informative than `failed: int` "
       "— you see exactly which tests failed, not just how many.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_05.ipynb", EX5)

# ══════════════════════════════════════════════════════════════════════════════
# PROJECT NOTEBOOK
# ══════════════════════════════════════════════════════════════════════════════
PROJECT = nb([
    md("# Day 065 — Project: Capstone Build II\n\n"
       "Complete and ship the AI Writing Assistant MVP."),
    md("## Deliverables\n\n"
       "| File | Description |\n"
       "|------|-------------|\n"
       "| `shipped_app.py` | Full FastAPI app — monitoring + all routes |\n"
       "| `test_shipped_app.py` | pytest suite — 16 tests |\n"
       "| `requirements.txt` | Package list |\n"
       "| `Procfile` | Render/Railway start command |\n"
       "| `render.yaml` | Render IaC definition |\n"
       "| `.env.example` | Required environment variables |\n\n"
       "## Run\n\n"
       "```bash\n"
       "# Test\n"
       "pytest test_shipped_app.py -v\n\n"
       "# Run locally\n"
       "uvicorn shipped_app:app --reload\n"
       "# → http://localhost:8000/docs\n\n"
       "# Deploy (Render)\n"
       "git push && # Render auto-deploys on push\n"
       "```\n\n"
       "## Section 4 Skills Demonstrated\n\n"
       "| Skill | From Day |\n"
       "|-------|----------|\n"
       "| FastAPI routes + Pydantic | 52 |\n"
       "| In-memory storage | 54/064 |\n"
       "| Health endpoint + deploy config | 57 |\n"
       "| Streaming & WebSockets | 58 |\n"
       "| Monitoring middleware | 61 |\n"
       "| pytest test suite | 62 |\n"
       "| Feature gating + rate limiting | 63 |\n"
       "| MVP scoping + templates | 064 |\n"
       "| Integration tests + readiness | 065 |"),
])
save(OUT / "project" / "project.ipynb", PROJECT)

# ══════════════════════════════════════════════════════════════════════════════
# SOLUTION NOTEBOOK
# ══════════════════════════════════════════════════════════════════════════════
_SOL_CELL1 = (
    f"_SHIPPED_SRC  = {repr(_SHIPPED_APP_SRC)}\n"
    f"_TEST_SRC     = {repr(_TEST_SRC)}\n"
    f"_RENDER_YAML  = {repr(_RENDER_YAML)}\n"
    f"_ENV_EXAMPLE  = {repr(_ENV_EXAMPLE)}\n"
    f"_REQUIREMENTS = {repr(_REQUIREMENTS)}\n"
    f"_PROCFILE     = {repr(_PROCFILE)}\n"
    "from pathlib import Path\n"
    "Path('shipped_app.py').write_text(_SHIPPED_SRC)\n"
    "Path('test_shipped_app.py').write_text(_TEST_SRC)\n"
    "Path('render.yaml').write_text(_RENDER_YAML)\n"
    "Path('.env.example').write_text(_ENV_EXAMPLE)\n"
    "Path('requirements.txt').write_text(_REQUIREMENTS)\n"
    "Path('Procfile').write_text(_PROCFILE)\n"
    "print('All deliverable files written.')"
)

_SOL_CELL2 = """\
# inline integration test — no Ollama needed
import re, secrets, time
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from starlette.testclient import TestClient

DAILY_LIMITS = {"free": 5, "pro": 500}
TEMPLATES    = {"email": "Write a {tone} email about {topic}.",
                "tweet": "Write a {tone} tweet about {topic}."}

def check_rate_limit(u, p):
    lim = DAILY_LIMITS.get(p, 0)
    return (False, "limit") if u >= lim else (True, "")

class ContentStore:
    def __init__(self): self._s = {}
    def add(self, uid, p, c):
        cid = secrets.token_urlsafe(8)
        self._s[cid] = {"content_id":cid,"user_id":uid,"prompt":p,"content":c}
        return cid
    def get(self, cid): return self._s.get(cid)
    def list_user(self, uid): return [v for v in self._s.values() if v["user_id"]==uid]

class MetricsCollector:
    def __init__(self): self._req=0; self._err=0; self._lat=[]
    def record(self, sc, ms): self._req+=1; self._err+=(1 if sc>=400 else 0); self._lat.append(ms)
    def summary(self): avg=sum(self._lat)/len(self._lat) if self._lat else 0.0; \
        return {"requests":self._req,"errors":self._err,
                "avg_latency_ms":round(avg,1),"error_rate":round(self._err/self._req if self._req else 0,3)}

def build_core(plan="free", process_fn=None, initial_usage=0):
    app=FastAPI(); store=ContentStore(); collector=MetricsCollector()
    state={"plan":plan,"usage":initial_usage}
    class _G(BaseModel): prompt:str=Field(min_length=1); user_id:str=Field(min_length=1)
    @app.middleware("http")
    async def mw(req,call_next):
        s=time.monotonic(); r=await call_next(req)
        collector.record(r.status_code,(time.monotonic()-s)*1000); return r
    @app.get("/health")
    def h(): return {"status":"ok","version":"1.1.0"}
    @app.get("/plan")
    def p(): lim=DAILY_LIMITS.get(state["plan"],0); return {"plan":state["plan"],"usage_today":state["usage"],"limit":lim}
    @app.get("/metrics")
    def m(): return collector.summary()
    @app.get("/templates")
    def t(): return {"templates":list(TEMPLATES.keys())}
    @app.post("/generate")
    def g(req:_G):
        ok,reason=check_rate_limit(state["usage"],state["plan"])
        if not ok: raise HTTPException(429,reason)
        ans=process_fn(req.prompt) if process_fn else req.prompt.upper()
        state["usage"]+=1; cid=store.add(req.user_id,req.prompt,ans)
        return {"content_id":cid,"content":ans,"user_id":req.user_id}
    @app.get("/history/{user_id}")
    def hist(user_id:str): items=store.list_user(user_id); return {"user_id":user_id,"count":len(items),"items":items}
    @app.get("/content/{cid}")
    def gc(cid:str):
        item=store.get(cid)
        if item is None: raise HTTPException(404)
        return item
    return app

# — run integration tests —
c = TestClient(build_core(plan="free", process_fn=str.upper), raise_server_exceptions=False)

assert c.get("/health").json()["status"] == "ok"; print("\\u2705 /health")
assert c.get("/plan").json()["plan"] == "free"; print("\\u2705 /plan")
assert c.get("/metrics").status_code == 200; print("\\u2705 /metrics")
assert len(c.get("/templates").json()["templates"]) > 0; print("\\u2705 /templates")

r = c.post("/generate", json={"prompt":"hi","user_id":"u1"})
assert r.status_code == 200 and r.json()["content"] == "HI"
cid = r.json()["content_id"]; print("\\u2705 /generate 200")

assert c.get("/history/u1").json()["count"] == 1; print("\\u2705 /history")
assert c.get(f"/content/{cid}").status_code == 200; print("\\u2705 /content/{id}")
assert c.get("/content/bad").status_code == 404; print("\\u2705 /content/bad 404")

assert c.post("/generate", json={"prompt":"","user_id":"u"}).status_code == 422
print("\\u2705 empty prompt 422")

c2 = TestClient(build_core(plan="free", process_fn=str.upper, initial_usage=5), raise_server_exceptions=False)
assert c2.post("/generate", json={"prompt":"x","user_id":"u"}).status_code == 429
print("\\u2705 rate limit 429")

m = c.get("/metrics").json()
assert m["requests"] >= 5 and "error_rate" in m; print("\\u2705 metrics correct")

print("\\nSection 4 capstone complete! \\U0001f389 shipped_app.py is ready to deploy.")
"""

SOLUTION = nb([
    md("# Day 065 — Solution: Capstone Build II"),
    code(_SOL_CELL1),
    code(_SOL_CELL2),
])
save(OUT / "project" / "solution" / "solution.ipynb", SOLUTION)
(OUT / "project" / "solution" / "shipped_app.py").write_text(_SHIPPED_APP_SRC)
(OUT / "project" / "solution" / "test_shipped_app.py").write_text(_TEST_SRC)
(OUT / "project" / "solution" / "render.yaml").write_text(_RENDER_YAML)
(OUT / "project" / "solution" / ".env.example").write_text(_ENV_EXAMPLE)
(OUT / "project" / "solution" / "requirements.txt").write_text(_REQUIREMENTS)
(OUT / "project" / "solution" / "Procfile").write_text(_PROCFILE)

print(f"Day {DAY} notebooks written to {OUT}")
print("  exercises/  exercise_01 – exercise_05")
print("  project/    project.ipynb")
print("  project/solution/  solution.ipynb + shipped_app.py + test_shipped_app.py")
print("                     + render.yaml + .env.example + requirements.txt + Procfile")
