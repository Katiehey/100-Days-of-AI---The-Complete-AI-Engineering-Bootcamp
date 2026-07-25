#!/usr/bin/env python3
"""gen_day060.py — generate Day 060: Caching & Performance notebooks."""
from pathlib import Path
import json

ROOT    = Path(__file__).parent.parent
DAY     = "060"
SECTION = "04_real_apps"
OUT     = ROOT / SECTION / f"day_{DAY}"

(OUT / "exercises").mkdir(parents=True, exist_ok=True)
(OUT / "lessons").mkdir(parents=True, exist_ok=True)
(OUT / "project" / "solution").mkdir(parents=True, exist_ok=True)

# ── deliverable source ─────────────────────────────────────────────────────────
_CACHING_API_SRC = '''\
"""caching_api.py — Day 060: response caching for AI apps.

Run:  uvicorn caching_api:app --reload
Docs: http://localhost:8000/docs
"""
import os
import time
from datetime import datetime

import ollama
from fastapi import FastAPI
from pydantic import BaseModel, Field

MODEL     = os.environ.get("MODEL", "llama3.2")
CACHE_TTL = float(os.environ.get("CACHE_TTL_SECONDS", "300"))
APP_VER   = "1.0.0"


class SimpleCache:
    """In-memory key-value cache with per-entry TTL."""

    def __init__(self):
        self._store: dict = {}   # key -> (value, expires_at)

    def set(self, key: str, value, ttl: float = 60.0) -> None:
        self._store[key] = (value, time.monotonic() + ttl)

    def get(self, key: str):
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return value

    def has(self, key: str) -> bool:
        return self.get(key) is not None

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> int:
        n = len(self._store)
        self._store.clear()
        return n

    def __len__(self) -> int:
        now = time.monotonic()
        return sum(1 for _, exp in self._store.values() if now <= exp)


class AskRequest(BaseModel):
    prompt: str = Field(min_length=1)


def build_api(process_fn=None) -> FastAPI:
    """Build the caching API.

    process_fn: optional callable(prompt: str) -> str for testing.
    """
    app   = FastAPI(title="Caching API", version=APP_VER)
    cache = SimpleCache()
    stats = {"hits": 0, "misses": 0}

    @app.get("/health")
    def health():
        return {"status": "ok",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "version": APP_VER}

    @app.post("/ask")
    def ask(req: AskRequest):
        cached = cache.get(req.prompt)
        if cached is not None:
            stats["hits"] += 1
            return {"answer": cached, "cache_hit": True}

        stats["misses"] += 1
        if process_fn is not None:
            answer = process_fn(req.prompt)
        else:
            resp = ollama.chat(
                model=MODEL,
                messages=[{"role": "user", "content": req.prompt}],
            )
            answer = resp["message"]["content"]
        cache.set(req.prompt, answer, ttl=CACHE_TTL)
        return {"answer": answer, "cache_hit": False}

    @app.get("/cache/stats")
    def cache_stats():
        return {"hits": stats["hits"], "misses": stats["misses"],
                "size": len(cache)}

    @app.delete("/cache")
    def clear_cache():
        n = cache.clear()
        stats["hits"] = 0
        stats["misses"] = 0
        return {"cleared": n}

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
# EXERCISE 1 — SimpleCache
# ══════════════════════════════════════════════════════════════════════════════
_EX1_IMPORTS = """\
import time
from typing import Any
"""

_EX1_STUB = """\
class SimpleCache:
    \"\"\"In-memory key-value cache with per-entry TTL.

    set(key, value, ttl)  — store value; expires after ttl seconds
    get(key) -> Any|None  — return value if not expired, else None
    has(key) -> bool      — True if key exists and is not expired
    delete(key)           — remove key (no-op if missing)
    clear() -> int        — remove all entries, return count removed
    __len__() -> int      — count of non-expired entries
    \"\"\"

    def __init__(self):
        # TODO: init _store dict: key -> (value, expires_at)
        raise NotImplementedError

    def set(self, key: str, value: Any, ttl: float = 60.0) -> None:
        raise NotImplementedError

    def get(self, key: str) -> Any:
        raise NotImplementedError

    def has(self, key: str) -> bool:
        raise NotImplementedError

    def delete(self, key: str) -> None:
        raise NotImplementedError

    def clear(self) -> int:
        raise NotImplementedError

    def __len__(self) -> int:
        raise NotImplementedError
"""

_EX1_SOLUTION = """\
class SimpleCache:
    def __init__(self):
        self._store: dict = {}

    def set(self, key: str, value: Any, ttl: float = 60.0) -> None:
        self._store[key] = (value, time.monotonic() + ttl)

    def get(self, key: str) -> Any:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return value

    def has(self, key: str) -> bool:
        return self.get(key) is not None

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> int:
        n = len(self._store)
        self._store.clear()
        return n

    def __len__(self) -> int:
        now = time.monotonic()
        return sum(1 for _, exp in self._store.values() if now <= exp)
"""

_EX1_CHECKS = """\
score, total = 0, 6
try:
    c = SimpleCache()

    # set and get
    c.set("k1", "hello", ttl=10.0)
    assert c.get("k1") == "hello", f"Expected 'hello', got {c.get('k1')}"
    score += 1; print("\\u2705 set/get stores and retrieves value")

    # has
    assert c.has("k1") is True
    assert c.has("nope") is False
    score += 1; print("\\u2705 has() returns True/False correctly")

    # expired entry
    c.set("k2", "short", ttl=0.01)
    time.sleep(0.05)
    assert c.get("k2") is None, f"Expired entry should be None, got {c.get('k2')}"
    score += 1; print("\\u2705 expired entry returns None")

    # delete
    c.set("k3", "val", ttl=10.0)
    c.delete("k3")
    assert c.get("k3") is None
    c.delete("no_such_key")   # should not raise
    score += 1; print("\\u2705 delete removes entry (no-op for missing)")

    # __len__ counts non-expired
    c2 = SimpleCache()
    c2.set("a", 1, ttl=10.0)
    c2.set("b", 2, ttl=0.01)
    time.sleep(0.05)
    assert len(c2) == 1, f"Expected 1 non-expired entry, got {len(c2)}"
    score += 1; print("\\u2705 __len__ counts only non-expired entries")

    # clear
    c3 = SimpleCache()
    c3.set("x", 1, ttl=10.0)
    c3.set("y", 2, ttl=10.0)
    removed = c3.clear()
    assert removed == 2, f"Expected clear() to return 2, got {removed}"
    assert len(c3) == 0
    score += 1; print("\\u2705 clear() removes all entries and returns count")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX1 = nb([
    md("# Day 060 — Exercise 1: SimpleCache\n\n"
       "The simplest caching strategy is an **in-memory dict** where each entry "
       "has a **time-to-live (TTL)**. After TTL seconds the entry expires and the "
       "next `get` returns `None`, forcing a fresh fetch.\n\n"
       "Key design: `_store[key] = (value, expires_at)` where `expires_at` is "
       "`time.monotonic() + ttl`. Use `time.monotonic()` — it never goes backwards "
       "and is unaffected by system clock changes."),
    code(_EX1_IMPORTS),
    md("## Task\n\n"
       "Implement `SimpleCache`:\n\n"
       "| Method | Behaviour |\n"
       "|--------|-----------|\n"
       "| `set(key, value, ttl=60)` | Store `(value, now + ttl)` |\n"
       "| `get(key) -> Any\\|None` | Return value if not expired; evict and return `None` if expired |\n"
       "| `has(key) -> bool` | `True` if key exists and is not expired |\n"
       "| `delete(key)` | Remove key (no-op if missing) |\n"
       "| `clear() -> int` | Remove all entries, return count |\n"
       "| `__len__() -> int` | Count of non-expired entries |"),
    md("## Your Implementation"),
    code(_EX1_STUB),
    code(_EX1_SOLUTION),
    md("## Automated checks"),
    code(_EX1_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX1_SOLUTION + "```\n\n"
       "**Why `time.monotonic()`?** Unlike `time.time()`, the monotonic clock never "
       "goes backwards — NTP corrections can adjust `time.time()` by seconds, which "
       "would cause entries to expire prematurely or never. `monotonic` is purely "
       "for measuring elapsed time.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_01.ipynb", EX1)

# ══════════════════════════════════════════════════════════════════════════════
# EXERCISE 2 — cache_aside
# ══════════════════════════════════════════════════════════════════════════════
_EX2_GIVEN = """\
# --- Provided: SimpleCache (from Exercise 1) ---
import time
from typing import Any

class SimpleCache:
    def __init__(self):
        self._store: dict = {}

    def set(self, key: str, value: Any, ttl: float = 60.0) -> None:
        self._store[key] = (value, time.monotonic() + ttl)

    def get(self, key: str) -> Any:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return value

    def has(self, key: str) -> bool:
        return self.get(key) is not None

    def clear(self) -> int:
        n = len(self._store)
        self._store.clear()
        return n

    def __len__(self) -> int:
        now = time.monotonic()
        return sum(1 for _, exp in self._store.values() if now <= exp)
"""

_EX2_IMPORTS = """\
from typing import Any, Callable
"""

_EX2_STUB = """\
def cache_aside(key: str, cache: SimpleCache, fn: Callable[[], Any],
                ttl: float = 60.0) -> Any:
    \"\"\"Cache-aside pattern: check cache first, call fn() on miss.

    1. If cache.has(key): return cache.get(key)
    2. Else: call fn(), store result with ttl, return result
    fn is called with no arguments.
    \"\"\"
    # TODO: check cache.has(key), call fn() on miss, cache the result
    raise NotImplementedError
"""

_EX2_SOLUTION = """\
def cache_aside(key, cache, fn, ttl=60.0):
    if cache.has(key):
        return cache.get(key)
    value = fn()
    cache.set(key, value, ttl)
    return value
"""

_EX2_CHECKS = """\
score, total = 0, 4
try:
    call_log = {"n": 0}

    def expensive():
        call_log["n"] += 1
        return f"result_{call_log['n']}"

    cache = SimpleCache()

    # first call — miss, fn invoked
    r1 = cache_aside("k", cache, expensive, ttl=10.0)
    assert r1 == "result_1", f"Got {r1}"
    assert call_log["n"] == 1
    score += 1; print("\\u2705 first call invokes fn and returns result")

    # second call — hit, fn NOT invoked again
    r2 = cache_aside("k", cache, expensive, ttl=10.0)
    assert r2 == "result_1", f"Got {r2}"
    assert call_log["n"] == 1, f"fn called {call_log['n']} times, expected 1"
    score += 1; print("\\u2705 second call returns cached result (fn not called)")

    # after TTL expires — miss again
    cache2 = SimpleCache()
    r3 = cache_aside("k2", cache2, expensive, ttl=0.02)
    assert call_log["n"] == 2
    time.sleep(0.06)
    r4 = cache_aside("k2", cache2, expensive, ttl=0.02)
    assert call_log["n"] == 3, f"fn should have been called again after TTL, got {call_log['n']}"
    score += 1; print("\\u2705 after TTL expiry, fn is called again")

    # different keys are cached independently
    cache3 = SimpleCache()
    cache_aside("a", cache3, lambda: "aa", ttl=10.0)
    cache_aside("b", cache3, lambda: "bb", ttl=10.0)
    assert cache3.get("a") == "aa" and cache3.get("b") == "bb"
    score += 1; print("\\u2705 different keys cached independently")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX2 = nb([
    md("# Day 060 — Exercise 2: Cache-Aside Pattern\n\n"
       "**Cache-aside** (also called *lazy loading*) is the most common caching pattern:\n\n"
       "1. Check the cache — if found, return it (**cache hit**)\n"
       "2. If not found (**cache miss**): call the slow function, store the result, return it\n\n"
       "The cache is *populated on demand* — only entries that are actually requested "
       "get cached. This avoids pre-loading data that may never be used."),
    code(_EX2_GIVEN),
    code(_EX2_IMPORTS),
    md("## Task\n\n"
       "Implement `cache_aside(key, cache, fn, ttl=60.0) -> Any`:\n\n"
       "- If `cache.has(key)`: return `cache.get(key)`\n"
       "- Otherwise: `value = fn()`, then `cache.set(key, value, ttl)`, return `value`\n"
       "- `fn` is a zero-argument callable (`lambda: expensive_call()`)"),
    md("## Your Implementation"),
    code(_EX2_STUB),
    code(_EX2_SOLUTION),
    md("## Automated checks"),
    code(_EX2_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX2_SOLUTION + "```\n\n"
       "**Why `has()` instead of `get() is not None`?** If `fn()` could return `None` "
       "legitimately, `get() is not None` would treat a cached `None` as a miss and "
       "re-call `fn()`. Using `has()` correctly distinguishes 'key present' from 'key absent'.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_02.ipynb", EX2)

# ══════════════════════════════════════════════════════════════════════════════
# EXERCISE 3 — build_cached_api
# ══════════════════════════════════════════════════════════════════════════════
_EX3_GIVEN = _EX2_GIVEN  # reuse SimpleCache

_EX3_IMPORTS = """\
from fastapi import FastAPI
from pydantic import BaseModel, Field
from starlette.testclient import TestClient
"""

_EX3_STUB = """\
def build_cached_api(process_fn=None) -> FastAPI:
    \"\"\"FastAPI with response caching.

    POST /ask    {\"prompt\": \"...\"}  → {\"answer\": str, \"cache_hit\": bool}
    GET /cache/stats               → {\"hits\": int, \"misses\": int, \"size\": int}
    DELETE /cache                  → {\"cleared\": int}

    process_fn: optional callable(prompt: str) -> str for testing.
    Returns 422 when prompt is empty.
    \"\"\"
    # TODO: create SimpleCache, stats dict, POST /ask, GET /cache/stats, DELETE /cache
    raise NotImplementedError
"""

_EX3_SOLUTION = """\
def build_cached_api(process_fn=None) -> FastAPI:
    app   = FastAPI()
    cache = SimpleCache()
    stats = {"hits": 0, "misses": 0}

    class _AskReq(BaseModel):
        prompt: str = Field(min_length=1)

    @app.post("/ask")
    def ask(req: _AskReq):
        cached = cache.get(req.prompt)
        if cached is not None:
            stats["hits"] += 1
            return {"answer": cached, "cache_hit": True}
        stats["misses"] += 1
        answer = process_fn(req.prompt) if process_fn else req.prompt.upper()
        cache.set(req.prompt, answer, ttl=60.0)
        return {"answer": answer, "cache_hit": False}

    @app.get("/cache/stats")
    def cache_stats():
        return {"hits": stats["hits"], "misses": stats["misses"], "size": len(cache)}

    @app.delete("/cache")
    def clear_cache():
        n = cache.clear()
        stats["hits"] = 0
        stats["misses"] = 0
        return {"cleared": n}

    return app
"""

_EX3_CHECKS = """\
score, total = 0, 6
try:
    app    = build_cached_api(process_fn=str.upper)
    client = TestClient(app, raise_server_exceptions=False)

    # first ask — miss
    r1 = client.post("/ask", json={"prompt": "hello"})
    assert r1.status_code == 200, f"Got {r1.status_code}"
    b1 = r1.json()
    assert b1["cache_hit"] is False, f"Expected cache_hit=False: {b1}"
    assert b1["answer"] == "HELLO"
    score += 1; print("\\u2705 first POST /ask returns correct answer, cache_hit=False")

    # second ask — hit
    r2 = client.post("/ask", json={"prompt": "hello"})
    b2 = r2.json()
    assert b2["cache_hit"] is True, f"Expected cache_hit=True: {b2}"
    assert b2["answer"] == "HELLO"
    score += 1; print("\\u2705 repeated prompt returns cache_hit=True")

    # different prompt — separate cache entry
    r3 = client.post("/ask", json={"prompt": "world"})
    assert r3.json()["cache_hit"] is False
    score += 1; print("\\u2705 different prompt is a separate cache entry")

    # stats
    rs = client.get("/cache/stats")
    s = rs.json()
    assert s["hits"] == 1, f"Expected 1 hit, got {s['hits']}"
    assert s["misses"] == 2, f"Expected 2 misses, got {s['misses']}"
    assert s["size"] == 2, f"Expected size 2, got {s['size']}"
    score += 1; print("\\u2705 /cache/stats reports correct hits/misses/size")

    # clear cache
    rd = client.delete("/cache")
    assert rd.json()["cleared"] == 2, f"Expected cleared=2, got {rd.json()}"
    rs2 = client.get("/cache/stats")
    assert rs2.json()["size"] == 0
    score += 1; print("\\u2705 DELETE /cache clears all entries")

    # empty prompt → 422
    r4 = client.post("/ask", json={"prompt": ""})
    assert r4.status_code == 422
    score += 1; print("\\u2705 empty prompt → 422")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX3 = nb([
    md("# Day 060 — Exercise 3: Cached API\n\n"
       "Wire `SimpleCache` and `cache_aside` into a FastAPI app. The `POST /ask` "
       "endpoint checks the cache before calling the (slow) process function. "
       "The `cache_hit` flag in the response tells the client whether a fresh "
       "answer was generated or a cached one was returned.\n\n"
       "`GET /cache/stats` gives operational visibility — essential for tuning "
       "your TTL. A low hit rate means TTL is too short or prompts vary too much."),
    code(_EX3_GIVEN),
    code(_EX3_IMPORTS),
    md("## Task\n\n"
       "Implement `build_cached_api(process_fn=None)` with:\n\n"
       "```\n"
       "POST /ask    {\"prompt\": \"...\"}  → {\"answer\": str, \"cache_hit\": bool}\n"
       "GET /cache/stats               → {\"hits\": int, \"misses\": int, \"size\": int}\n"
       "DELETE /cache                  → {\"cleared\": int}\n"
       "```\n\n"
       "- Cache by `prompt` string; use `cache.get(prompt)` / `cache.set(prompt, answer)`\n"
       "- Track `hits` and `misses` in a dict\n"
       "- `DELETE /cache` resets both the cache and the hit/miss counters"),
    md("## Your Implementation"),
    code(_EX3_STUB),
    code(_EX3_SOLUTION),
    md("## Automated checks"),
    code(_EX3_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX3_SOLUTION + "```\n\n"
       "**Cache key choice:** using the raw `prompt` string as the key means two "
       "semantically identical prompts with different whitespace are treated as misses. "
       "In production you might normalise the key: `prompt.strip().lower()`. For "
       "Ollama responses, case and whitespace in the prompt usually DO produce "
       "different answers, so the raw string is a reasonable default.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_03.ipynb", EX3)

# ══════════════════════════════════════════════════════════════════════════════
# EXERCISE 4 — lru_memoize
# ══════════════════════════════════════════════════════════════════════════════
_EX4_IMPORTS = """\
import functools
from typing import Any, Callable
"""

_EX4_STUB = """\
def lru_memoize(fn: Callable, maxsize: int = 128) -> Callable:
    \"\"\"Return a memoized version of fn using functools.lru_cache.

    fn must accept only hashable arguments (str, int, tuple, etc.).
    Repeated calls with the same arguments return the cached result
    without calling fn again.

    The returned callable exposes cache_info() from lru_cache.
    \"\"\"
    # TODO: wrap fn in functools.lru_cache(maxsize=maxsize) and return the wrapper
    raise NotImplementedError
"""

_EX4_SOLUTION = """\
def lru_memoize(fn, maxsize=128):
    @functools.lru_cache(maxsize=maxsize)
    def wrapper(*args):
        return fn(*args)
    return wrapper
"""

_EX4_CHECKS = """\
score, total = 0, 4
try:
    call_count = {"n": 0}

    def slow_fn(x):
        call_count["n"] += 1
        return x * 2

    memoized = lru_memoize(slow_fn, maxsize=4)

    # first call — fn invoked
    assert memoized(5) == 10
    assert call_count["n"] == 1
    score += 1; print("\\u2705 first call invokes fn")

    # same arg — cached, fn NOT called
    assert memoized(5) == 10
    assert call_count["n"] == 1, f"fn called {call_count['n']} times, expected 1"
    score += 1; print("\\u2705 same args return cached result (fn not called again)")

    # different args — separate cache entry
    assert memoized(7) == 14
    assert call_count["n"] == 2
    score += 1; print("\\u2705 different args are cached separately")

    # cache_info() available
    info = memoized.cache_info()
    assert info.hits >= 1, f"Expected hits >= 1, got {info.hits}"
    assert info.misses >= 2, f"Expected misses >= 2, got {info.misses}"
    score += 1; print(f"\\u2705 cache_info() available: {info}")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX4 = nb([
    md("# Day 060 — Exercise 4: LRU Memoize\n\n"
       "`functools.lru_cache` is Python's built-in memoization decorator — it caches "
       "the return value of a function keyed by its arguments. **LRU** = Least Recently "
       "Used: when the cache is full (`maxsize`), the entry that was accessed least "
       "recently is evicted.\n\n"
       "Unlike `SimpleCache`, `lru_cache` has no TTL — entries live until evicted by "
       "size pressure or explicitly cleared with `fn.cache_clear()`. Use it for "
       "pure functions whose output never changes for the same input."),
    code(_EX4_IMPORTS),
    md("## Task\n\n"
       "Implement `lru_memoize(fn, maxsize=128) -> Callable`:\n\n"
       "- Wrap `fn` in `@functools.lru_cache(maxsize=maxsize)`\n"
       "- The wrapper accepts `*args` and delegates to `fn`\n"
       "- Return the wrapper — it exposes `.cache_info()` from `lru_cache`"),
    md("## Your Implementation"),
    code(_EX4_STUB),
    code(_EX4_SOLUTION),
    md("## Automated checks"),
    code(_EX4_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX4_SOLUTION + "```\n\n"
       "**Why a wrapper?** You cannot apply `lru_cache` directly to an arbitrary "
       "function reference — you need to define a new function inside `lru_memoize` "
       "and decorate it. The inner `wrapper` captures `fn` via closure. The "
       "`cache_info()` method comes from `lru_cache` and reports hits, misses, "
       "max size, and current size.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_04.ipynb", EX4)

# ══════════════════════════════════════════════════════════════════════════════
# EXERCISE 5 — build_etag_api
# ══════════════════════════════════════════════════════════════════════════════
_EX5_IMPORTS = """\
import hashlib
import json as _json
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from starlette.testclient import TestClient
"""

_EX5_STUB = """\
def build_etag_api() -> FastAPI:
    \"\"\"FastAPI app with HTTP ETag-based caching on GET /data.

    GET /data  (no If-None-Match header)
        → 200 JSON + 'ETag: \"<md5hash>\"' + 'Cache-Control: max-age=60'

    GET /data  (If-None-Match matches current ETag)
        → 304 Not Modified (empty body)

    GET /data  (If-None-Match does NOT match)
        → 200 JSON + ETag + Cache-Control

    The ETag is the MD5 hex digest of the JSON-encoded data, wrapped in quotes.
    \"\"\"
    # TODO: build app, compute etag from data, check if-none-match header
    raise NotImplementedError
"""

_EX5_SOLUTION = """\
def build_etag_api() -> FastAPI:
    app   = FastAPI()
    _data = {"message": "Hello from the cached API!", "version": 1}

    def _etag(data) -> str:
        raw = _json.dumps(data, sort_keys=True)
        return '"' + hashlib.md5(raw.encode()).hexdigest() + '"'

    @app.get("/data")
    def get_data(request: Request):
        etag = _etag(_data)
        if_none_match = request.headers.get("if-none-match", "")
        if if_none_match == etag:
            return Response(status_code=304)
        return JSONResponse(
            content=_data,
            headers={"ETag": etag, "Cache-Control": "max-age=60"},
        )

    return app
"""

_EX5_CHECKS = """\
score, total = 0, 5
try:
    app    = build_etag_api()
    client = TestClient(app, raise_server_exceptions=False)

    # first request → 200
    r1 = client.get("/data")
    assert r1.status_code == 200, f"Expected 200, got {r1.status_code}"
    score += 1; print("\\u2705 GET /data returns 200")

    # has ETag header
    assert "etag" in r1.headers, f"Missing ETag header: {dict(r1.headers)}"
    etag = r1.headers["etag"]
    assert etag.startswith('"') and etag.endswith('"'), f"ETag must be quoted: {etag}"
    score += 1; print("\\u2705 response has quoted ETag header")

    # has Cache-Control header
    cc = r1.headers.get("cache-control", "")
    assert "max-age" in cc, f"Expected max-age in Cache-Control, got {cc!r}"
    score += 1; print("\\u2705 response has Cache-Control: max-age header")

    # matching ETag → 304
    r2 = client.get("/data", headers={"if-none-match": etag})
    assert r2.status_code == 304, f"Expected 304, got {r2.status_code}"
    assert len(r2.content) == 0, "304 response must have empty body"
    score += 1; print("\\u2705 matching If-None-Match → 304 empty body")

    # wrong ETag → 200
    r3 = client.get("/data", headers={"if-none-match": '"wrong-etag"'})
    assert r3.status_code == 200, f"Expected 200, got {r3.status_code}"
    score += 1; print("\\u2705 non-matching If-None-Match → 200")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX5 = nb([
    md("# Day 060 — Exercise 5: HTTP ETag Caching\n\n"
       "**ETags** are HTTP-level caching: the server includes an `ETag` header "
       "identifying the current version of the resource. The browser stores it and "
       "sends it back as `If-None-Match` on the next request. If the data hasn't "
       "changed, the server returns `304 Not Modified` (no body) — saving bandwidth.\n\n"
       "This is different from in-process caching: ETags let the **client** avoid "
       "re-downloading data it already has."),
    code(_EX5_IMPORTS),
    md("## Task\n\n"
       "Implement `build_etag_api()` — return a FastAPI app with:\n\n"
       "```\n"
       "GET /data  → 200 JSON body + ETag + Cache-Control\n"
       "GET /data  (If-None-Match == current ETag) → 304 empty body\n"
       "GET /data  (If-None-Match != current ETag) → 200 JSON body\n"
       "```\n\n"
       "ETag format: `'\"' + hashlib.md5(json_bytes).hexdigest() + '\"'` (quoted string)\n\n"
       "Use `request.headers.get('if-none-match', '')` to read the client's ETag.\n"
       "Return `Response(status_code=304)` for the not-modified case."),
    md("## Your Implementation"),
    code(_EX5_STUB),
    code(_EX5_SOLUTION),
    md("## Automated checks"),
    code(_EX5_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX5_SOLUTION + "```\n\n"
       "**Why quote the ETag?** The HTTP spec requires ETag values to be "
       "double-quoted strings: `\\\"abc123\\\"`, not `abc123`. Browsers and proxies "
       "reject unquoted ETags. The MD5 of the JSON body is a stable hash — "
       "any change to the data produces a different ETag, triggering a fresh "
       "200 response.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_05.ipynb", EX5)

# ══════════════════════════════════════════════════════════════════════════════
# PROJECT NOTEBOOK
# ══════════════════════════════════════════════════════════════════════════════
PROJECT = nb([
    md("# Day 060 — Project: Caching & Performance\n\n"
       "Build `caching_api.py` — a FastAPI server that caches Ollama responses "
       "to eliminate redundant model calls and measure cache effectiveness."),
    md("## Deliverable\n\n"
       "`caching_api.py` in `project/solution/` — a FastAPI app with:\n\n"
       "| Endpoint | Method | Description |\n"
       "|----------|--------|-------------|\n"
       "| `/health` | GET | Health check |\n"
       "| `/ask` | POST | Cached Ollama Q&A (`cache_hit` flag in response) |\n"
       "| `/cache/stats` | GET | Hits, misses, current cache size |\n"
       "| `/cache` | DELETE | Clear cache and reset stats |\n\n"
       "## How to run\n\n"
       "```bash\n"
       "CACHE_TTL_SECONDS=300 uvicorn caching_api:app --reload\n"
       "# Ask the same question twice:\n"
       "curl -X POST http://localhost:8000/ask \\\\\n"
       "     -H 'Content-Type: application/json' \\\\\n"
       "     -d '{\"prompt\": \"What is Python?\"}'\n"
       "# Second call is instant (cache_hit: true):\n"
       "curl -X POST http://localhost:8000/ask \\\\\n"
       "     -H 'Content-Type: application/json' \\\\\n"
       "     -d '{\"prompt\": \"What is Python?\"}'\n"
       "```\n\n"
       "## Concepts used\n\n"
       "- `SimpleCache` with TTL — in-memory key-value store\n"
       "- Cache-aside pattern — check cache, call fn on miss\n"
       "- `cache_hit` flag — transparency about caching behaviour\n"
       "- Stats endpoint — operational visibility into cache effectiveness\n"
       "- `CACHE_TTL_SECONDS` env var — TTL configurable without code changes"),
])
save(OUT / "project" / "project.ipynb", PROJECT)

# ══════════════════════════════════════════════════════════════════════════════
# SOLUTION NOTEBOOK
# ══════════════════════════════════════════════════════════════════════════════
_FULL_SOL_CELL1 = (
    f"_CACHING_API_SRC = {repr(_CACHING_API_SRC)}\n"
    "from pathlib import Path\n"
    "Path('caching_api.py').write_text(_CACHING_API_SRC)\n"
    "print('caching_api.py written.')"
)

_FULL_SOL_CELL2 = """\
from fastapi import FastAPI
from pydantic import BaseModel, Field
from starlette.testclient import TestClient

# ── inline test app (no Ollama) ───────────────────────────────────────────────
call_count = {"n": 0}

def fake_process(prompt: str) -> str:
    call_count["n"] += 1
    return f"Answer to: {prompt}"

import time

class _SC:
    def __init__(self):
        self._s: dict = {}
    def set(self, k, v, ttl=60.0):
        self._s[k] = (v, time.monotonic() + ttl)
    def get(self, k):
        e = self._s.get(k)
        if not e: return None
        v, exp = e
        if time.monotonic() > exp:
            del self._s[k]; return None
        return v
    def has(self, k): return self.get(k) is not None
    def clear(self):
        n = len(self._s); self._s.clear(); return n
    def __len__(self):
        now = time.monotonic()
        return sum(1 for _, exp in self._s.values() if now <= exp)

cache = _SC()
stats = {"hits": 0, "misses": 0}

class _AskReq(BaseModel):
    prompt: str = Field(min_length=1)

test_app = FastAPI()

@test_app.get("/health")
def _health():
    from datetime import datetime
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": "1.0.0"}

@test_app.post("/ask")
def _ask(req: _AskReq):
    cached = cache.get(req.prompt)
    if cached is not None:
        stats["hits"] += 1
        return {"answer": cached, "cache_hit": True}
    stats["misses"] += 1
    answer = fake_process(req.prompt)
    cache.set(req.prompt, answer, ttl=60.0)
    return {"answer": answer, "cache_hit": False}

@test_app.get("/cache/stats")
def _stats():
    return {"hits": stats["hits"], "misses": stats["misses"], "size": len(cache)}

@test_app.delete("/cache")
def _clear():
    n = cache.clear(); stats["hits"] = 0; stats["misses"] = 0
    return {"cleared": n}

client = TestClient(test_app, raise_server_exceptions=False)

# /health
r = client.get("/health")
assert r.status_code == 200 and r.json()["status"] == "ok"
print("\\u2705 /health works")

# first ask → miss
r1 = client.post("/ask", json={"prompt": "What is caching?"})
assert r1.status_code == 200
b1 = r1.json()
assert b1["cache_hit"] is False and "Answer to:" in b1["answer"]
assert call_count["n"] == 1
print("\\u2705 first POST /ask calls process_fn (miss)")

# same prompt → hit
r2 = client.post("/ask", json={"prompt": "What is caching?"})
b2 = r2.json()
assert b2["cache_hit"] is True and call_count["n"] == 1
print("\\u2705 repeated prompt returns cache_hit=True (fn not called again)")

# stats
rs = client.get("/cache/stats")
s = rs.json()
assert s["hits"] == 1 and s["misses"] == 1 and s["size"] == 1
print("\\u2705 /cache/stats reports correct hits/misses/size")

# DELETE /cache
rd = client.delete("/cache")
assert rd.json()["cleared"] == 1
assert client.get("/cache/stats").json()["size"] == 0
print("\\u2705 DELETE /cache clears everything")

# empty prompt → 422
r3 = client.post("/ask", json={"prompt": ""})
assert r3.status_code == 422
print("\\u2705 empty prompt \\u2192 422")

print("\\nDay 060 \\u2014 Caching & Performance complete! \\U0001f389")
"""

SOLUTION = nb([
    md("# Day 060 — Solution: Caching & Performance"),
    code(_FULL_SOL_CELL1),
    code(_FULL_SOL_CELL2),
])
save(OUT / "project" / "solution" / "solution.ipynb", SOLUTION)
(OUT / "project" / "solution" / "caching_api.py").write_text(_CACHING_API_SRC)

print(f"Day {DAY} notebooks written to {OUT}")
print("  exercises/  exercise_01 – exercise_05")
print("  project/    project.ipynb")
print("  project/solution/  solution.ipynb + caching_api.py")
