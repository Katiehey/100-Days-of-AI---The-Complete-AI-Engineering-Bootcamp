#!/usr/bin/env python3
"""gen_day062.py — generate Day 062: Testing Web Apps notebooks."""
from pathlib import Path
import json

ROOT    = Path(__file__).parent.parent
DAY     = "062"
SECTION = "04_real_apps"
OUT     = ROOT / SECTION / f"day_{DAY}"

(OUT / "exercises").mkdir(parents=True, exist_ok=True)
(OUT / "lessons").mkdir(parents=True, exist_ok=True)
(OUT / "project" / "solution").mkdir(parents=True, exist_ok=True)

# ── deliverable source ─────────────────────────────────────────────────────────
_TEST_APP_SRC = '''\
"""test_app.py — Day 062: pytest test suite for a simple CRUD API.

Run:  pytest test_app.py -v
      pytest test_app.py -v -k "delete"   # filter by name
      pytest test_app.py --tb=short        # compact tracebacks
"""
import pytest
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from starlette.testclient import TestClient


# ── app under test ─────────────────────────────────────────────────────────────
class Item(BaseModel):
    name:  str   = Field(min_length=1)
    price: float = Field(gt=0)


def build_app() -> FastAPI:
    """Simple item CRUD API — the subject under test."""
    app  = FastAPI()
    _db  = {}
    _nxt = {"id": 1}

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/items")
    def list_items():
        return {"items": list(_db.values())}

    @app.post("/items", status_code=201)
    def create_item(item: Item):
        iid         = _nxt["id"]
        _nxt["id"] += 1
        _db[iid]    = {"id": iid, **item.model_dump()}
        return _db[iid]

    @app.get("/items/{item_id}")
    def get_item(item_id: int):
        if item_id not in _db:
            raise HTTPException(status_code=404, detail="Not found")
        return _db[item_id]

    @app.delete("/items/{item_id}", status_code=204)
    def delete_item(item_id: int):
        if item_id not in _db:
            raise HTTPException(status_code=404, detail="Not found")
        del _db[item_id]

    return app


# ── pytest fixture ─────────────────────────────────────────────────────────────
@pytest.fixture
def client():
    """Fresh TestClient (and fresh app state) for every test."""
    return TestClient(build_app())


# ── health tests ───────────────────────────────────────────────────────────────
def test_health_returns_200(client):
    r = client.get("/health")
    assert r.status_code == 200


def test_health_status_is_ok(client):
    r = client.get("/health")
    assert r.json()["status"] == "ok"


# ── list tests ─────────────────────────────────────────────────────────────────
def test_list_items_empty_on_start(client):
    r = client.get("/items")
    assert r.status_code == 200
    assert r.json()["items"] == []


# ── create tests ───────────────────────────────────────────────────────────────
def test_create_item_returns_201(client):
    r = client.post("/items", json={"name": "Widget", "price": 9.99})
    assert r.status_code == 201


def test_create_item_has_id(client):
    r = client.post("/items", json={"name": "Widget", "price": 9.99})
    assert "id" in r.json()


def test_create_item_preserves_fields(client):
    r = client.post("/items", json={"name": "Widget", "price": 9.99})
    data = r.json()
    assert data["name"]  == "Widget"
    assert data["price"] == 9.99


@pytest.mark.parametrize("name,price,expected_status", [
    ("Widget", 9.99,  201),   # valid
    ("",       9.99,  422),   # empty name
    ("Widget", 0.0,   422),   # price must be > 0
    ("Widget", -1.0,  422),   # negative price
])
def test_create_item_validation(client, name, price, expected_status):
    r = client.post("/items", json={"name": name, "price": price})
    assert r.status_code == expected_status, (
        f"name={name!r}, price={price}: expected {expected_status}, got {r.status_code}")


# ── get tests ──────────────────────────────────────────────────────────────────
def test_get_item_after_create(client):
    created = client.post("/items", json={"name": "Gadget", "price": 14.99}).json()
    r = client.get(f"/items/{created['id']}")
    assert r.status_code == 200
    assert r.json()["name"] == "Gadget"


def test_get_item_not_found(client):
    r = client.get("/items/999")
    assert r.status_code == 404


# ── delete tests ───────────────────────────────────────────────────────────────
def test_delete_item_returns_204(client):
    created = client.post("/items", json={"name": "Thing", "price": 1.0}).json()
    r = client.delete(f"/items/{created['id']}")
    assert r.status_code == 204


def test_deleted_item_is_gone(client):
    created = client.post("/items", json={"name": "Thing", "price": 1.0}).json()
    client.delete(f"/items/{created['id']}")
    r = client.get(f"/items/{created['id']}")
    assert r.status_code == 404


def test_delete_item_not_found(client):
    r = client.delete("/items/999")
    assert r.status_code == 404
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
# EXERCISE 1 — assert_response
# ══════════════════════════════════════════════════════════════════════════════
_EX1_GIVEN = """\
# --- minimal app for testing ---
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from starlette.testclient import TestClient

def _build_echo_app():
    app = FastAPI()
    class _Body(BaseModel):
        text: str = Field(min_length=1)
    @app.get("/health")
    def health():
        return {"status": "ok"}
    @app.post("/echo")
    def echo(body: _Body):
        return {"echo": body.text}
    return app

_client = TestClient(_build_echo_app(), raise_server_exceptions=False)
"""

_EX1_IMPORTS = """\
# no extra imports needed
"""

_EX1_STUB = """\
def assert_response(response, expected_status: int, required_keys: tuple = ()) -> dict:
    \"\"\"Assert response status and that all required_keys appear in JSON body.

    Returns the parsed JSON dict on success.
    Raises AssertionError with a clear message on:
    - wrong status code (include response.text[:200] in the message)
    - any required key missing from the response body

    Hint: f\"{expected_status}, got {response.status_code}: {response.text[:200]}\"
    \"\"\"
    # TODO: assert status, parse JSON, assert each required key, return dict
    raise NotImplementedError
"""

_EX1_SOLUTION = """\
def assert_response(response, expected_status: int, required_keys: tuple = ()) -> dict:
    assert response.status_code == expected_status, (
        f"Expected {expected_status}, got {response.status_code}: {response.text[:200]}")
    data = response.json()
    for key in required_keys:
        assert key in data, f"Missing key {key!r} in response: {data}"
    return data
"""

_EX1_CHECKS = """\
score, total = 0, 5
try:
    # 1. returns dict on correct status
    r = _client.get("/health")
    data = assert_response(r, 200, ("status",))
    assert isinstance(data, dict) and data.get("status") == "ok"
    score += 1; print("\\u2705 returns parsed JSON dict on correct status + key")

    # 2. correct status, no required_keys
    r2 = _client.post("/echo", json={"text": "hello"})
    d2 = assert_response(r2, 200)
    assert d2["echo"] == "hello"
    score += 1; print("\\u2705 works with no required_keys")

    # 3. wrong status → AssertionError with message containing the actual code
    r3 = _client.get("/health")
    try:
        assert_response(r3, 404)
        assert False, "Should have raised AssertionError"
    except AssertionError as e:
        assert "200" in str(e) or "404" in str(e), f"Error message missing status codes: {e}"
    score += 1; print("\\u2705 wrong status raises AssertionError with status info")

    # 4. missing key → AssertionError
    r4 = _client.get("/health")
    try:
        assert_response(r4, 200, ("missing_key",))
        assert False, "Should have raised AssertionError"
    except AssertionError as e:
        assert "missing_key" in str(e), f"Error message should name missing key: {e}"
    score += 1; print("\\u2705 missing required key raises AssertionError naming the key")

    # 5. 422 assertion (empty text)
    r5 = _client.post("/echo", json={"text": ""})
    assert_response(r5, 422)
    score += 1; print("\\u2705 correctly asserts 422 validation error")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX1 = nb([
    md("# Day 062 — Exercise 1: assert_response\n\n"
       "Repeating the same assertion boilerplate in every API test gets tedious "
       "and produces unhelpful failure messages. A reusable helper encapsulates the "
       "pattern and produces informative errors when tests fail.\n\n"
       "Without a helper:\n"
       "```python\n"
       "assert r.status_code == 200  # ❌ only shows 'False', not actual code\n"
       "```\n\n"
       "With `assert_response`:\n"
       "```python\n"
       "data = assert_response(r, 200, ('status', 'version'))\n"
       "# ❌ Expected 200, got 500: {\"detail\": \"Internal Server Error\"}\n"
       "```"),
    code(_EX1_GIVEN),
    code(_EX1_IMPORTS),
    md("## Task\n\n"
       "Implement `assert_response(response, expected_status, required_keys=()) -> dict`:\n\n"
       "1. `assert response.status_code == expected_status` — include actual status + "
       "`response.text[:200]` in the failure message\n"
       "2. `data = response.json()` — parse the body\n"
       "3. For each key in `required_keys`: assert it's in `data`, name the missing key\n"
       "4. Return `data`"),
    md("## Your Implementation"),
    code(_EX1_STUB),
    code(_EX1_SOLUTION),
    md("## Automated checks"),
    code(_EX1_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX1_SOLUTION + "```\n\n"
       "**Why `response.text[:200]`?** A bare `assert r.status_code == 200` prints "
       "nothing useful when it fails. Including the first 200 chars of the response "
       "body shows you the actual error — e.g. `{\"detail\": \"Internal Server Error\"}` "
       "— so you know where to look without re-running with extra print statements.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_01.ipynb", EX1)

# ══════════════════════════════════════════════════════════════════════════════
# EXERCISE 2 — parametrize_api
# ══════════════════════════════════════════════════════════════════════════════
_EX2_GIVEN = """\
from fastapi import FastAPI
from pydantic import BaseModel, Field
from starlette.testclient import TestClient

def _build_classify_app():
    app = FastAPI()
    class _Body(BaseModel):
        score: float = Field(ge=0.0, le=1.0)
    @app.post("/classify")
    def classify(body: _Body):
        label = "high" if body.score >= 0.7 else "medium" if body.score >= 0.3 else "low"
        return {"label": label}
    return app

_client = TestClient(_build_classify_app(), raise_server_exceptions=False)
"""

_EX2_IMPORTS = """\
from typing import Any
"""

_EX2_STUB = """\
def parametrize_api(client, cases: list[dict]) -> dict:
    \"\"\"Run multiple API test cases and collect results.

    Each case is a dict with:
        method          str  — 'GET', 'POST', etc.
        path            str  — e.g. '/classify'
        json            dict|None — request body (optional)
        expected_status int  — expected HTTP status code
        label           str  — human-readable name for the case

    Returns:
        {\"passed\": int, \"failed\": int, \"failures\": [str, ...]}

    On status mismatch: append f\"{label}: expected {es}, got {actual}\" to failures.
    Do NOT raise — collect all results and return.
    \"\"\"
    # TODO: iterate cases, call client.request, check status, collect pass/fail
    raise NotImplementedError
"""

_EX2_SOLUTION = """\
def parametrize_api(client, cases: list[dict]) -> dict:
    passed, failed, failures = 0, 0, []
    for case in cases:
        label = case.get("label", f"{case['method']} {case['path']}")
        try:
            r = client.request(case["method"], case["path"],
                               json=case.get("json"))
            assert r.status_code == case["expected_status"], (
                f"{label}: expected {case['expected_status']}, got {r.status_code}")
            passed += 1
        except AssertionError as e:
            failed += 1
            failures.append(str(e))
    return {"passed": passed, "failed": failed, "failures": failures}
"""

_EX2_CHECKS = """\
score, total = 0, 4
try:
    cases = [
        {"method": "POST", "path": "/classify", "json": {"score": 0.9},
         "expected_status": 200, "label": "high score"},
        {"method": "POST", "path": "/classify", "json": {"score": 0.5},
         "expected_status": 200, "label": "medium score"},
        {"method": "POST", "path": "/classify", "json": {"score": 0.1},
         "expected_status": 200, "label": "low score"},
        {"method": "POST", "path": "/classify", "json": {"score": 2.0},
         "expected_status": 422, "label": "out of range"},
    ]

    result = parametrize_api(_client, cases)
    assert isinstance(result, dict)
    assert "passed" in result and "failed" in result and "failures" in result
    score += 1; print("\\u2705 returns dict with passed/failed/failures")

    # all 4 cases pass
    assert result["passed"] == 4, f"Expected 4 passed, got {result['passed']}"
    assert result["failed"] == 0
    score += 1; print("\\u2705 all 4 valid cases pass")

    # wrong expected_status → failure is collected (not raised)
    wrong = [{"method": "POST", "path": "/classify", "json": {"score": 0.5},
              "expected_status": 404, "label": "deliberate wrong status"}]
    r2 = parametrize_api(_client, wrong)
    assert r2["failed"] == 1 and r2["passed"] == 0
    assert len(r2["failures"]) == 1
    score += 1; print("\\u2705 wrong expected_status is collected as a failure (not raised)")

    # label appears in failure message
    assert "deliberate wrong status" in r2["failures"][0], (
        f"Label missing from failure: {r2['failures'][0]!r}")
    score += 1; print("\\u2705 label appears in failure message")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX2 = nb([
    md("# Day 062 — Exercise 2: parametrize_api\n\n"
       "Testing many input variations copy-paste style is painful:\n\n"
       "```python\n"
       "assert_response(client.post('/classify', json={'score': 0.9}), 200)\n"
       "assert_response(client.post('/classify', json={'score': 0.5}), 200)\n"
       "assert_response(client.post('/classify', json={'score': 2.0}), 422)\n"
       "# ...10 more lines\n"
       "```\n\n"
       "pytest solves this with `@pytest.mark.parametrize`. In notebooks, a "
       "`parametrize_api` helper achieves the same goal: one function, a list of "
       "cases, all results collected without crashing on the first failure."),
    code(_EX2_GIVEN),
    code(_EX2_IMPORTS),
    md("## Task\n\n"
       "Implement `parametrize_api(client, cases) -> dict`:\n\n"
       "Each `case` has `method`, `path`, `json` (optional), `expected_status`, `label`.\n\n"
       "For each case:\n"
       "- `client.request(method, path, json=json_body)`\n"
       "- If `status_code != expected_status`: append `f\"{label}: expected {es}, got {actual}\"` to failures\n"
       "- Collect all results — do NOT raise on failure\n\n"
       "Return `{\"passed\": N, \"failed\": N, \"failures\": [...]}`"),
    md("## Your Implementation"),
    code(_EX2_STUB),
    code(_EX2_SOLUTION),
    md("## Automated checks"),
    code(_EX2_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX2_SOLUTION + "```\n\n"
       "**Why collect failures instead of raising?** Raising on the first failure "
       "means you only know about ONE broken case at a time. Collecting lets you see "
       "ALL failures in one run — e.g. 'cases 3, 7, and 11 fail' tells you much more "
       "about the regression than 'case 3 fails' followed by three re-runs.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_02.ipynb", EX2)

# ══════════════════════════════════════════════════════════════════════════════
# EXERCISE 3 — run_test_suite
# ══════════════════════════════════════════════════════════════════════════════
_EX3_IMPORTS = """\
from typing import Callable
"""

_EX3_STUB = """\
def run_test_suite(tests: list[Callable]) -> dict:
    \"\"\"Run a list of zero-argument test functions and collect results.

    A test function PASSES if it completes without raising.
    A test function FAILS  if it raises AssertionError.
    A test function ERRORS if it raises any other exception.

    Returns:
        {\"passed\": int, \"failed\": int, \"errors\": int,
         \"failures\": [str, ...]}

    failures list contains:
        \"FAIL  test_name: <AssertionError message>\"
        \"ERROR test_name: <exception type and message>\"
    \"\"\"
    # TODO: iterate tests, call each, collect pass/fail/error
    raise NotImplementedError
"""

_EX3_SOLUTION = """\
def run_test_suite(tests: list[Callable]) -> dict:
    passed = failed = errors = 0
    failures = []
    for fn in tests:
        name = fn.__name__
        try:
            fn()
            passed += 1
        except AssertionError as e:
            failed += 1
            failures.append(f"FAIL  {name}: {e}")
        except Exception as e:
            errors += 1
            failures.append(f"ERROR {name}: {type(e).__name__}: {e}")
    return {"passed": passed, "failed": failed, "errors": errors,
            "failures": failures}
"""

_EX3_CHECKS = """\
score, total = 0, 5
try:
    # passing test
    def test_passes():
        assert 1 + 1 == 2

    # failing test (AssertionError)
    def test_fails():
        assert 1 + 1 == 3, "math is wrong"

    # error test (non-AssertionError)
    def test_errors():
        raise ValueError("unexpected crash")

    r = run_test_suite([test_passes, test_fails, test_errors])
    assert isinstance(r, dict)
    assert "passed" in r and "failed" in r and "errors" in r and "failures" in r
    score += 1; print("\\u2705 returns dict with passed/failed/errors/failures")

    assert r["passed"] == 1, f"Expected 1 passed, got {r['passed']}"
    score += 1; print("\\u2705 passing test counted correctly")

    assert r["failed"] == 1, f"Expected 1 failed, got {r['failed']}"
    score += 1; print("\\u2705 failing test (AssertionError) counted correctly")

    assert r["errors"] == 1, f"Expected 1 error, got {r['errors']}"
    score += 1; print("\\u2705 erroring test (non-AssertionError) counted correctly")

    # failure messages contain function name + error detail
    assert any("test_fails" in f for f in r["failures"]), (
        f"test_fails not in failures: {r['failures']}")
    assert any("test_errors" in f for f in r["failures"]), (
        f"test_errors not in failures: {r['failures']}")
    score += 1; print("\\u2705 failures list contains function names")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX3 = nb([
    md("# Day 062 — Exercise 3: run_test_suite\n\n"
       "pytest is fundamentally a test discovery and execution engine: it finds "
       "`test_*` functions, runs them, catches `AssertionError` as a test failure, "
       "and counts results. This exercise builds a mini version of that engine.\n\n"
       "Understanding the difference between **FAIL** (expected behaviour that "
       "doesn't match) and **ERROR** (unexpected crash in the test itself) is "
       "important — they indicate different kinds of problems."),
    code(_EX3_IMPORTS),
    md("## Task\n\n"
       "Implement `run_test_suite(tests: list[Callable]) -> dict`:\n\n"
       "For each `fn` in `tests` (called with no arguments):\n"
       "- **No exception** → `passed += 1`\n"
       "- **AssertionError** → `failed += 1`, append `f\"FAIL  {fn.__name__}: {e}\"` to failures\n"
       "- **Other exception** → `errors += 1`, append `f\"ERROR {fn.__name__}: {type(e).__name__}: {e}\"`\n\n"
       "Return `{\"passed\": N, \"failed\": N, \"errors\": N, \"failures\": [...]}`"),
    md("## Your Implementation"),
    code(_EX3_STUB),
    code(_EX3_SOLUTION),
    md("## Automated checks"),
    code(_EX3_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX3_SOLUTION + "```\n\n"
       "**FAIL vs ERROR** — two separate counters matter because they mean different "
       "things. FAIL: your assertion is wrong or your code has a bug. ERROR: the test "
       "itself crashed before it could even assert (missing import, network timeout, "
       "wrong fixture setup). Mixing them hides information.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_03.ipynb", EX3)

# ══════════════════════════════════════════════════════════════════════════════
# EXERCISE 4 — Regression test: write a test that catches a bug
# ══════════════════════════════════════════════════════════════════════════════
_EX4_GIVEN = """\
from fastapi import FastAPI
from starlette.testclient import TestClient

def _build_broken_api():
    \"\"\"Buggy API: /multiply returns the SUM, not the product.\"\"\"
    app = FastAPI()
    @app.get("/multiply")
    def multiply(a: int, b: int):
        return {"result": a + b}    # BUG: should be a * b
    return app

def _build_fixed_api():
    \"\"\"Fixed API: /multiply returns the product.\"\"\"
    app = FastAPI()
    @app.get("/multiply")
    def multiply(a: int, b: int):
        return {"result": a * b}
    return app
"""

_EX4_IMPORTS = """\
# no extra imports needed
"""

_EX4_STUB = """\
def test_multiply_correct(client) -> None:
    \"\"\"Test that GET /multiply?a=3&b=4 returns {result: 12}.

    Use client.get('/multiply', params={'a': 3, 'b': 4}).
    Assert status is 200.
    Assert result == 12 (include actual value in assertion message).
    This test should FAIL against the broken API and PASS against the fixed one.
    \"\"\"
    # TODO: make the request, assert 200, assert result == 12
    raise NotImplementedError
"""

_EX4_SOLUTION = """\
def test_multiply_correct(client) -> None:
    r = client.get("/multiply", params={"a": 3, "b": 4})
    assert r.status_code == 200
    data = r.json()
    assert data["result"] == 12, (
        f"Expected 12 (3*4), got {data['result']} (may be 3+4=7 if the bug is present)")
"""

_EX4_CHECKS = """\
score, total = 0, 4
try:
    # test raises AssertionError against the broken API (catches the bug)
    broken = TestClient(_build_broken_api(), raise_server_exceptions=False)
    try:
        test_multiply_correct(broken)
        print("\\u274c test_multiply_correct did NOT catch the bug")
    except AssertionError:
        score += 1; print("\\u2705 test_multiply_correct FAILS against the buggy API")
    except NotImplementedError:
        print("\\u274c function raises NotImplementedError — implement it first")

    # test passes against the fixed API
    fixed = TestClient(_build_fixed_api(), raise_server_exceptions=False)
    try:
        test_multiply_correct(fixed)
        score += 1; print("\\u2705 test_multiply_correct PASSES against the fixed API")
    except Exception as e:
        print(f"\\u274c test_multiply_correct raised on fixed API: {e}")

    # test asserts status 200
    try:
        class _FakeResp:
            status_code = 503
            def json(self): return {"result": 12}
        class _FakeClient:
            def get(self, *a, **kw): return _FakeResp()
        test_multiply_correct(_FakeClient())
        print("\\u274c should have raised on 503")
    except AssertionError:
        score += 1; print("\\u2705 test checks status_code (caught 503)")
    except NotImplementedError:
        print("\\u274c not implemented")
    except Exception:
        score += 1; print("\\u2705 test rejects 503 (some exception raised)")

    # test asserts result == 12 specifically
    broken_12 = TestClient(_build_broken_api(), raise_server_exceptions=False)
    # a=6, b=6 → broken returns 12 (6+6), fixed returns 36 (6*6)
    # So if we test a=3, b=4 → broken returns 7 which != 12 ✓
    try:
        test_multiply_correct(broken)  # a=3,b=4 → broken returns 7
        print("\\u274c bug not caught for 3*4=12")
    except AssertionError as e:
        assert "12" in str(e) or "7" in str(e) or "result" in str(e).lower(), (
            f"Assertion message should reference 12 or 7: {e!r}")
        score += 1; print("\\u2705 assertion message references expected/actual values")
    except NotImplementedError:
        print("\\u274c not implemented")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX4 = nb([
    md("# Day 062 — Exercise 4: Regression Test\n\n"
       "A **regression test** documents a bug so it can never silently come back. "
       "The workflow:\n\n"
       "1. Discover a bug\n"
       "2. Write a test that FAILS (proving the bug exists)\n"
       "3. Fix the bug\n"
       "4. Confirm the test now PASSES\n"
       "5. The test lives in the suite forever — it will catch any future regression\n\n"
       "The bug here: `GET /multiply?a=3&b=4` returns `7` (the sum) instead of `12` (the product). "
       "Your test must catch this specific mistake."),
    code(_EX4_GIVEN),
    code(_EX4_IMPORTS),
    md("## Task\n\n"
       "Implement `test_multiply_correct(client) -> None`:\n\n"
       "- `GET /multiply` with query params `a=3, b=4`\n"
       "- Assert `status_code == 200`\n"
       "- Assert `result == 12` — include the actual value in the failure message\n\n"
       "The test should **FAIL** against `_build_broken_api()` (returns 7) and "
       "**PASS** against `_build_fixed_api()` (returns 12)."),
    md("## Your Implementation"),
    code(_EX4_STUB),
    code(_EX4_SOLUTION),
    md("## Automated checks"),
    code(_EX4_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX4_SOLUTION + "```\n\n"
       "**Include actual values in assertion messages.** `assert result == 12` prints "
       "only `AssertionError`. `assert result == 12, f'Expected 12, got {result}'` "
       "immediately tells you the actual value — crucial when tests run in CI at 2am "
       "and you're reading a log, not a debugger.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_04.ipynb", EX4)

# ══════════════════════════════════════════════════════════════════════════════
# EXERCISE 5 — Full test suite for a CRUD API
# ══════════════════════════════════════════════════════════════════════════════
_EX5_GIVEN = """\
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from starlette.testclient import TestClient

def build_item_api() -> FastAPI:
    \"\"\"Provided: simple CRUD API.

    GET /items                    → {\"items\": [...]}
    POST /items {name, price}     → 201 {id, name, price}
    GET /items/{id}               → {id, name, price} | 404
    DELETE /items/{id}            → 204 | 404
    \"\"\"
    app = FastAPI()
    _db: dict = {}
    _nxt = {"id": 1}

    class _Item(BaseModel):
        name:  str   = Field(min_length=1)
        price: float = Field(gt=0)

    @app.get("/items")
    def list_items():
        return {"items": list(_db.values())}

    @app.post("/items", status_code=201)
    def create(item: _Item):
        iid = _nxt["id"]; _nxt["id"] += 1
        _db[iid] = {"id": iid, **item.model_dump()}
        return _db[iid]

    @app.get("/items/{iid}")
    def get(iid: int):
        if iid not in _db: raise HTTPException(404, "Not found")
        return _db[iid]

    @app.delete("/items/{iid}", status_code=204)
    def delete(iid: int):
        if iid not in _db: raise HTTPException(404, "Not found")
        del _db[iid]

    return app

def _fresh():
    \"\"\"Return a fresh TestClient for each test (isolated state).\"\"\"
    return TestClient(build_item_api(), raise_server_exceptions=False)
"""

_EX5_IMPORTS = """\
# no extra imports needed
"""

_EX5_STUB = """\
def test_list_empty(client) -> None:
    \"\"\"GET /items on a fresh app returns an empty list.\"\"\"
    # TODO: GET /items, assert 200, assert items == []
    raise NotImplementedError

def test_create_item(client) -> None:
    \"\"\"POST /items with valid data returns 201 with id, name, price.\"\"\"
    # TODO: POST /items, assert 201, check id/name/price in response
    raise NotImplementedError

def test_get_not_found(client) -> None:
    \"\"\"GET /items/999 on a fresh app returns 404.\"\"\"
    # TODO: GET /items/999, assert 404
    raise NotImplementedError

def test_create_then_delete(client) -> None:
    \"\"\"Create an item, delete it, confirm it's gone (404 on GET).\"\"\"
    # TODO: POST to create, DELETE by id, GET to confirm 404
    raise NotImplementedError
"""

_EX5_SOLUTION = """\
def test_list_empty(client) -> None:
    r = client.get("/items")
    assert r.status_code == 200
    assert r.json()["items"] == []

def test_create_item(client) -> None:
    r = client.post("/items", json={"name": "Widget", "price": 9.99})
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Widget"
    assert data["price"] == 9.99
    assert "id" in data

def test_get_not_found(client) -> None:
    r = client.get("/items/999")
    assert r.status_code == 404

def test_create_then_delete(client) -> None:
    created = client.post("/items", json={"name": "Thing", "price": 1.0}).json()
    r_del = client.delete(f"/items/{created['id']}")
    assert r_del.status_code == 204
    r_get = client.get(f"/items/{created['id']}")
    assert r_get.status_code == 404
"""

_EX5_CHECKS = """\
score, total = 0, 4
try:
    test_list_empty(_fresh())
    score += 1; print("\\u2705 test_list_empty passes")
except NotImplementedError:
    print("\\u274c test_list_empty not implemented")
except Exception as e:
    print(f"\\u274c test_list_empty: {e}")

try:
    test_create_item(_fresh())
    score += 1; print("\\u2705 test_create_item passes")
except NotImplementedError:
    print("\\u274c test_create_item not implemented")
except Exception as e:
    print(f"\\u274c test_create_item: {e}")

try:
    test_get_not_found(_fresh())
    score += 1; print("\\u2705 test_get_not_found passes")
except NotImplementedError:
    print("\\u274c test_get_not_found not implemented")
except Exception as e:
    print(f"\\u274c test_get_not_found: {e}")

try:
    test_create_then_delete(_fresh())
    score += 1; print("\\u2705 test_create_then_delete passes")
except NotImplementedError:
    print("\\u274c test_create_then_delete not implemented")
except Exception as e:
    print(f"\\u274c test_create_then_delete: {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX5 = nb([
    md("# Day 062 — Exercise 5: Full Test Suite\n\n"
       "A **test suite** covers the core paths through an API: the happy path "
       "(things that should work), validation errors (things that should be rejected), "
       "and state transitions (create → read → delete).\n\n"
       "Good test isolation means each test gets a **fresh app instance** — no shared "
       "state between tests. In pytest, a `@pytest.fixture` on the `client` does this "
       "automatically. Here, `_fresh()` returns a new client for each test call."),
    code(_EX5_GIVEN),
    code(_EX5_IMPORTS),
    md("## Task\n\n"
       "Implement four test functions for `build_item_api()`. Each takes a `client` argument.\n\n"
       "| Test | What to check |\n"
       "|------|---------------|\n"
       "| `test_list_empty` | GET /items → 200, `items == []` |\n"
       "| `test_create_item` | POST /items → 201, response has `id`, `name`, `price` |\n"
       "| `test_get_not_found` | GET /items/999 → 404 |\n"
       "| `test_create_then_delete` | POST → DELETE (204) → GET → 404 |"),
    md("## Your Implementation"),
    code(_EX5_STUB),
    code(_EX5_SOLUTION),
    md("## Automated checks"),
    code(_EX5_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX5_SOLUTION + "```\n\n"
       "**Why a fresh client per test?** Without isolation, test order matters — "
       "`test_list_empty` would fail if `test_create_item` ran first and left an item "
       "in the store. pytest fixtures solve this automatically. Here, `_fresh()` is "
       "the manual equivalent.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_05.ipynb", EX5)

# ══════════════════════════════════════════════════════════════════════════════
# PROJECT NOTEBOOK
# ══════════════════════════════════════════════════════════════════════════════
PROJECT = nb([
    md("# Day 062 — Project: Testing Web Apps\n\n"
       "Build `test_app.py` — a real pytest test suite for a CRUD API. "
       "When complete, run it with `pytest test_app.py -v` and see all tests pass."),
    md("## Deliverable\n\n"
       "`test_app.py` in `project/solution/` — a pytest test suite with:\n\n"
       "| Feature | Detail |\n"
       "|---------|--------|\n"
       "| `@pytest.fixture` | Fresh TestClient for every test — no shared state |\n"
       "| `@pytest.mark.parametrize` | Test many input combinations in one test |\n"
       "| Happy path tests | 200/201/204 for valid requests |\n"
       "| Validation tests | 422 for invalid payloads |\n"
       "| Not found tests | 404 for missing resources |\n"
       "| State transition | Create → GET → DELETE → 404 |\n\n"
       "## How to run\n\n"
       "```bash\n"
       "cd 04_real_apps/day_062/project/solution/\n"
       "pytest test_app.py -v          # run all tests, verbose\n"
       "pytest test_app.py -k delete   # run only delete tests\n"
       "pytest test_app.py --tb=short  # compact tracebacks\n"
       "```\n\n"
       "## Concepts used\n\n"
       "- `@pytest.fixture` — shared setup (TestClient) reset per test\n"
       "- `@pytest.mark.parametrize` — table-driven testing\n"
       "- `assert r.status_code == N` — clear status assertions\n"
       "- State transition tests — POST → DELETE → 404\n"
       "- Test isolation — `build_app()` called fresh in the fixture"),
])
save(OUT / "project" / "project.ipynb", PROJECT)

# ══════════════════════════════════════════════════════════════════════════════
# SOLUTION NOTEBOOK
# ══════════════════════════════════════════════════════════════════════════════
_SOL_CELL1 = (
    f"_TEST_APP_SRC = {repr(_TEST_APP_SRC)}\n"
    "from pathlib import Path\n"
    "Path('test_app.py').write_text(_TEST_APP_SRC)\n"
    "print('test_app.py written.')"
)

_SOL_CELL2 = """\
# inline verification — demonstrates all patterns without running pytest subprocess
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from starlette.testclient import TestClient

class Item(BaseModel):
    name:  str   = Field(min_length=1)
    price: float = Field(gt=0)

def build_app():
    app = FastAPI(); _db = {}; _nxt = {"id": 1}
    @app.get("/health")
    def health(): return {"status": "ok"}
    @app.get("/items")
    def list_items(): return {"items": list(_db.values())}
    @app.post("/items", status_code=201)
    def create(item: Item):
        iid = _nxt["id"]; _nxt["id"] += 1
        _db[iid] = {"id": iid, **item.model_dump()}; return _db[iid]
    @app.get("/items/{item_id}")
    def get(item_id: int):
        if item_id not in _db: raise HTTPException(404)
        return _db[item_id]
    @app.delete("/items/{item_id}", status_code=204)
    def delete(item_id: int):
        if item_id not in _db: raise HTTPException(404)
        del _db[item_id]
    return app

def fresh(): return TestClient(build_app(), raise_server_exceptions=False)

# health
c = fresh()
assert c.get("/health").json()["status"] == "ok"
print("\\u2705 /health")

# list empty
c = fresh()
assert c.get("/items").json()["items"] == []
print("\\u2705 list empty")

# create
c = fresh()
r = c.post("/items", json={"name": "Widget", "price": 9.99})
assert r.status_code == 201 and r.json()["name"] == "Widget" and "id" in r.json()
print("\\u2705 create item 201")

# validation
c = fresh()
assert c.post("/items", json={"name": "", "price": 9.99}).status_code == 422
assert c.post("/items", json={"name": "X", "price": 0}).status_code == 422
assert c.post("/items", json={"name": "X", "price": -1}).status_code == 422
print("\\u2705 validation 422 cases")

# get
c = fresh()
created = c.post("/items", json={"name": "G", "price": 1.0}).json()
assert c.get(f"/items/{created['id']}").json()["name"] == "G"
assert c.get("/items/999").status_code == 404
print("\\u2705 get item / 404")

# delete
c = fresh()
created = c.post("/items", json={"name": "T", "price": 1.0}).json()
assert c.delete(f"/items/{created['id']}").status_code == 204
assert c.get(f"/items/{created['id']}").status_code == 404
assert c.delete("/items/999").status_code == 404
print("\\u2705 delete item / 404")

# parametrize-style: multiple validation cases
cases = [("Widget", 9.99, 201), ("", 9.99, 422), ("X", 0.0, 422), ("X", -1, 422)]
c = fresh()
for name, price, expected in cases:
    actual = c.post("/items", json={"name": name, "price": price}).status_code
    assert actual == expected, f"name={name!r}, price={price}: expected {expected}, got {actual}"
print("\\u2705 parametrized validation cases")

print("\\nDay 062 \\u2014 Testing Web Apps complete! \\U0001f389")
"""

SOLUTION = nb([
    md("# Day 062 — Solution: Testing Web Apps"),
    code(_SOL_CELL1),
    code(_SOL_CELL2),
])
save(OUT / "project" / "solution" / "solution.ipynb", SOLUTION)
(OUT / "project" / "solution" / "test_app.py").write_text(_TEST_APP_SRC)

print(f"Day {DAY} notebooks written to {OUT}")
print("  exercises/  exercise_01 – exercise_05")
print("  project/    project.ipynb")
print("  project/solution/  solution.ipynb + test_app.py")
