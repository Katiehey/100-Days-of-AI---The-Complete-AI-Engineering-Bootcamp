#!/usr/bin/env python3
"""Generate all Day 031 notebooks: exercises 1-5, project, solution."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAY_DIR = ROOT / "02_automation" / "day_031"

_cid = 0


def cid():
    global _cid
    _cid += 1
    return f"c{_cid:04d}"


def md(source: str) -> dict:
    return {"cell_type": "markdown", "id": cid(), "metadata": {}, "source": source}


def code(source: str) -> dict:
    return {
        "cell_type": "code",
        "id": cid(),
        "metadata": {},
        "outputs": [],
        "execution_count": None,
        "source": source,
    }


def nb(cells: list) -> dict:
    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "display_name": "ai-course",
                "language": "python",
                "name": "ai-course",
            },
            "language_info": {"name": "python", "version": "3.11.0"},
        },
        "cells": cells,
    }


def write_nb(path: Path, cells: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(nb(cells), indent=1), encoding="utf-8")
    print(f"  wrote {path.relative_to(ROOT)}")


# ---------------------------------------------------------------------------
# Implementations
# ---------------------------------------------------------------------------

RETRY_IMPL = """\
import time


def retry(fn, max_attempts: int = 3, base_delay: float = 1.0, backoff: float = 2.0):
    last_error = None
    for attempt in range(max_attempts):
        try:
            return fn()
        except Exception as e:
            last_error = e
            if attempt < max_attempts - 1:
                time.sleep(base_delay * (backoff ** attempt))
    raise last_error"""

DLQ_IMPL = """\
from datetime import datetime


class DeadLetterQueue:
    def __init__(self):
        self._items: list = []

    def add(self, item, error: str, context: dict | None = None) -> None:
        self._items.append({
            "item":     item,
            "error":    error,
            "context":  context or {},
            "added_at": datetime.now().isoformat(),
        })

    def drain(self) -> list:
        items, self._items = self._items, []
        return items

    def peek(self) -> list:
        return list(self._items)

    def size(self) -> int:
        return len(self._items)"""

RESILIENT_STEP_IMPL = """\
def resilient_step(
    name: str,
    fn,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    backoff: float = 2.0,
) -> dict:
    start      = time.time()
    last_error = None
    for attempt in range(max_attempts):
        try:
            result = fn()
            return {
                "name":       name,
                "status":     "ok",
                "result":     result,
                "error":      None,
                "duration_s": round(time.time() - start, 3),
                "attempts":   attempt + 1,
            }
        except Exception as e:
            last_error = e
            if attempt < max_attempts - 1:
                time.sleep(base_delay * (backoff ** attempt))
    return {
        "name":       name,
        "status":     "error",
        "result":     None,
        "error":      str(last_error),
        "duration_s": round(time.time() - start, 3),
        "attempts":   max_attempts,
    }"""

PROCESS_BATCH_IMPL = """\
def process_batch_with_dlq(
    items: list,
    process_fn,
    dlq: DeadLetterQueue,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    backoff: float = 2.0,
) -> list:
    results = []
    for item in items:
        r = resilient_step(
            str(item),
            lambda i=item: process_fn(i),
            max_attempts=max_attempts,
            base_delay=base_delay,
            backoff=backoff,
        )
        if r["status"] == "error":
            dlq.add(item, r["error"])
        results.append(r)
    return results"""

AI_REPORT_IMPL = """\
def ai_resilience_report(
    batch_results: list,
    dlq_items: list,
    model: str = "llama3.2",
) -> str:
    total        = len(batch_results)
    passed       = sum(1 for r in batch_results if r["status"] == "ok")
    avg_attempts = (
        round(sum(r.get("attempts", 1) for r in batch_results) / total, 2)
        if total else 0.0
    )
    lines = [
        f"Batch run: {passed}/{total} items succeeded, "
        f"{len(dlq_items)} failed to DLQ.",
        f"Average attempts per item: {avg_attempts}.",
    ]
    for entry in dlq_items[:3]:
        lines.append(f"  DLQ: {entry['item']} \\u2014 {entry['error']}")

    response = ollama.chat(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a reliability engineer. "
                    "Summarise a batch processing run in 2\\u20133 sentences. "
                    "Focus on the failure rate and recommend one concrete action."
                ),
            },
            {
                "role": "user",
                "content": "\\n".join(lines) + "\\n\\nSummarise and recommend:",
            },
        ],
    )
    return response["message"]["content"]"""

ALL_IMPLS = "\n\n\n".join([
    RETRY_IMPL,
    DLQ_IMPL,
    RESILIENT_STEP_IMPL,
    PROCESS_BATCH_IMPL,
])


# ---------------------------------------------------------------------------
# Exercise 01 — retry
# ---------------------------------------------------------------------------

def ex01():
    global _cid; _cid = 0
    return [
        md(
            "# Day 031 — Exercise 1: retry\n\n"
            "**What you'll build:** `retry(fn, max_attempts=3, base_delay=1.0, backoff=2.0)` — "
            "calls `fn()` up to `max_attempts` times; on each failure sleeps "
            "`base_delay * (backoff ** attempt)` seconds before the next try; "
            "raises the LAST exception if all attempts fail.\n\n"
            "**Why it matters:** Network calls, API requests, and file I/O fail intermittently. "
            "A retry loop turns transient failures into automatic recovery. "
            "Exponential backoff prevents hammering a struggling service with immediate retries."
        ),
        code("import time"),
        md("## Your Implementation"),
        code(
            "def retry(\n"
            "    fn,\n"
            "    max_attempts: int = 3,\n"
            "    base_delay: float = 1.0,\n"
            "    backoff: float = 2.0,\n"
            "):\n"
            '    """\n'
            "    Call fn() up to max_attempts times with exponential backoff.\n\n"
            "    Args:\n"
            "        fn:           Zero-arg callable to retry.\n"
            "        max_attempts: Maximum number of attempts (default 3).\n"
            "        base_delay:   Seconds to wait after first failure (default 1.0).\n"
            "        backoff:      Multiplier applied each subsequent retry (default 2.0).\n\n"
            "    Returns:\n"
            "        Return value of fn() if any attempt succeeds.\n\n"
            "    Raises:\n"
            "        The exception from the LAST failed attempt.\n"
            '    """\n'
            "    # TODO: last_error = None\n"
            "    # TODO: for attempt in range(max_attempts):\n"
            "    #     try: return fn()\n"
            "    #     except Exception as e:\n"
            "    #         last_error = e\n"
            "    #         if attempt < max_attempts - 1: time.sleep(base_delay * (backoff ** attempt))\n"
            "    # TODO: raise last_error\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'retry' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: retry defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    # Check 2: succeeds on first try → correct return value\n"
            "    try:\n"
            "        result = retry(lambda: 42, max_attempts=3, base_delay=0.0)\n"
            "        assert result == 42, f'expected 42, got {result!r}'\n"
            "        passed += 1; print('\\u2705 Check 2: immediate success returns correct value')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: fn fails twice then succeeds → returns correct result\n"
            "    try:\n"
            "        _n = [0]\n"
            "        def _flaky():\n"
            "            _n[0] += 1\n"
            "            if _n[0] < 3:\n"
            "                raise ValueError(f'attempt {_n[0]} failed')\n"
            "            return 'success'\n"
            "        result = retry(_flaky, max_attempts=3, base_delay=0.0)\n"
            "        assert result == 'success', f'expected success, got {result!r}'\n"
            "        assert _n[0] == 3, f'fn should be called 3 times, got {_n[0]}'\n"
            "        passed += 1; print('\\u2705 Check 3: retries until success on 3rd attempt')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: always fails → raises LAST exception (not first)\n"
            "    try:\n"
            "        _m = [0]\n"
            "        def _always_fail():\n"
            "            _m[0] += 1\n"
            "            raise RuntimeError(f'error #{_m[0]}')\n"
            "        raised = False\n"
            "        try:\n"
            "            retry(_always_fail, max_attempts=3, base_delay=0.0)\n"
            "        except RuntimeError as e:\n"
            "            raised = True\n"
            "            assert 'error #3' in str(e), \\\n"
            "                f'should raise LAST error (#3), got: {e}'\n"
            "        assert raised, 'retry should have raised RuntimeError'\n"
            "        passed += 1; print('\\u2705 Check 4: raises the LAST exception after all retries')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: fn called exactly max_attempts times when always failing\n"
            "    try:\n"
            "        _k = [0]\n"
            "        def _count_calls():\n"
            "            _k[0] += 1\n"
            "            raise ValueError('always fails')\n"
            "        try:\n"
            "            retry(_count_calls, max_attempts=4, base_delay=0.0)\n"
            "        except ValueError:\n"
            "            pass\n"
            "        assert _k[0] == 4, f'expected 4 calls (max_attempts=4), got {_k[0]}'\n"
            "        passed += 1; print(f'\\u2705 Check 5: fn called exactly max_attempts times')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\\U0001f389 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "\n"
            "_run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + RETRY_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 02 — DeadLetterQueue
# ---------------------------------------------------------------------------

def ex02():
    global _cid; _cid = 100
    return [
        md(
            "# Day 031 — Exercise 2: DeadLetterQueue\n\n"
            "**What you'll build:** `DeadLetterQueue` — a container for failed items "
            "that exhausted all retries. `add(item, error)` stores the failed item with "
            "an error message and timestamp. `drain()` returns all stored items and resets "
            "the queue to empty. `peek()` returns items without draining. `size()` returns "
            "the current count.\n\n"
            "**Why it matters:** When retries are exhausted, the item must go somewhere. "
            "Silently discarding it loses data. Crashing the batch stops processing. "
            "The DLQ routes failures to a holding area for later inspection, replay, or alert."
        ),
        code("from datetime import datetime"),
        md("## Your Implementation"),
        code(
            "class DeadLetterQueue:\n"
            '    """\n'
            "    Container for items that failed all retry attempts.\n\n"
            "    Each record has: item (original value), error (str), context (dict),\n"
            "    added_at (ISO timestamp).\n"
            '    """\n'
            "\n"
            "    def __init__(self):\n"
            "        # TODO: self._items = []\n"
            "        pass\n"
            "\n"
            "    def add(self, item, error: str, context: dict | None = None) -> None:\n"
            "        # TODO: append dict with item, error, context (or {}), added_at (ISO str)\n"
            "        pass\n"
            "\n"
            "    def drain(self) -> list:\n"
            "        # TODO: atomic swap: items, self._items = self._items, []; return items\n"
            "        pass\n"
            "\n"
            "    def peek(self) -> list:\n"
            "        # TODO: return list(self._items) — copy, not reference\n"
            "        pass\n"
            "\n"
            "    def size(self) -> int:\n"
            "        # TODO: return len(self._items)\n"
            "        pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: class defined with required methods\n"
            "    try:\n"
            "        assert 'DeadLetterQueue' in globals()\n"
            "        for m in ('add', 'drain', 'peek', 'size'):\n"
            "            assert hasattr(DeadLetterQueue, m), f'missing method: {m}'\n"
            "        passed += 1; print('\\u2705 Check 1: DeadLetterQueue with add/drain/peek/size')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    dlq = DeadLetterQueue()\n"
            "\n"
            "    # Check 2: add increases size; record has required keys\n"
            "    try:\n"
            "        dlq.add('url_1', 'ConnectionTimeout')\n"
            "        dlq.add(42,      'ValueError: bad id')\n"
            "        assert dlq.size() == 2, f'size should be 2, got {dlq.size()}'\n"
            "        passed += 1; print('\\u2705 Check 2: add increases size to 2')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: record has correct keys and values\n"
            "    try:\n"
            "        items = dlq.peek()\n"
            "        rec = items[0]\n"
            "        for k in ('item', 'error', 'context', 'added_at'):\n"
            "            assert k in rec, f'record missing key: {k}'\n"
            "        assert rec['item']  == 'url_1',             f\"item wrong: {rec['item']!r}\"\n"
            "        assert rec['error'] == 'ConnectionTimeout', f\"error wrong: {rec['error']!r}\"\n"
            "        assert isinstance(rec['added_at'], str) and rec['added_at'], \\\n"
            "            f'added_at should be non-empty str: {rec[\"added_at\"]!r}'\n"
            "        passed += 1; print('\\u2705 Check 3: record has correct keys and values')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: peek does NOT empty the queue\n"
            "    try:\n"
            "        before = dlq.size()\n"
            "        _ = dlq.peek()\n"
            "        after = dlq.size()\n"
            "        assert before == after, \\\n"
            "            f'peek should not change size: before={before}, after={after}'\n"
            "        passed += 1; print('\\u2705 Check 4: peek is non-destructive')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: drain returns all items and empties the queue\n"
            "    try:\n"
            "        drained = dlq.drain()\n"
            "        assert len(drained) == 2, f'should drain 2 items, got {len(drained)}'\n"
            "        assert dlq.size() == 0, f'queue should be empty after drain, got {dlq.size()}'\n"
            "        # Drain again → empty list\n"
            "        again = dlq.drain()\n"
            "        assert again == [], f'second drain should return [], got {again}'\n"
            "        passed += 1; print('\\u2705 Check 5: drain returns all items and empties queue')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\\U0001f389 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "\n"
            "_run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + DLQ_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 03 — resilient_step
# ---------------------------------------------------------------------------

def ex03():
    global _cid; _cid = 200
    return [
        md(
            "# Day 031 — Exercise 3: resilient_step\n\n"
            "**What you'll build:** `resilient_step(name, fn, max_attempts=3, base_delay=1.0, backoff=2.0) -> dict` — "
            "combines retry logic with the Day 30 step result schema. Tries `fn()` up to "
            "`max_attempts` times; returns an ok dict on first success or an error dict "
            "after all failures. Adds an `attempts` key (int) to the schema.\n\n"
            "**Why it matters:** resilient_step is a drop-in upgrade over run_step (Day 30). "
            "Any step in a pipeline can be hardened by switching from run_step to resilient_step "
            "without changing the caller — same schema, extra resilience."
        ),
        code("import time"),
        md("## Provided: RETRY_IMPL is used internally — implement the loop directly"),
        md("## Your Implementation"),
        code(
            "def resilient_step(\n"
            "    name: str,\n"
            "    fn,\n"
            "    max_attempts: int = 3,\n"
            "    base_delay: float = 1.0,\n"
            "    backoff: float = 2.0,\n"
            ") -> dict:\n"
            '    """\n'
            "    Run fn() with retry; return a step result dict.\n\n"
            "    Returns dict with keys: name, status ('ok'|'error'), result, error,\n"
            "    duration_s, attempts (int — how many tries were needed).\n"
            "    Never raises.\n"
            '    """\n'
            "    # TODO: start = time.time(); last_error = None\n"
            "    # TODO: for attempt in range(max_attempts):\n"
            "    #     try: result = fn(); return ok-dict (attempts=attempt+1)\n"
            "    #     except Exception as e:\n"
            "    #         last_error = e\n"
            "    #         if attempt < max_attempts - 1: time.sleep(base_delay*(backoff**attempt))\n"
            "    # TODO: return error-dict (attempts=max_attempts)\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'resilient_step' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: resilient_step defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    # Check 2: immediate success → status=ok, attempts=1, all 6 keys\n"
            "    try:\n"
            "        r = resilient_step('compute', lambda: 7 * 6, max_attempts=3, base_delay=0.0)\n"
            "        for k in ('name', 'status', 'result', 'error', 'duration_s', 'attempts'):\n"
            "            assert k in r, f'missing key: {k}'\n"
            "        assert r['status']   == 'ok', f\"status: {r['status']!r}\"\n"
            "        assert r['result']   == 42,   f\"result: {r['result']!r}\"\n"
            "        assert r['attempts'] == 1,    f\"attempts: {r['attempts']}\"\n"
            "        passed += 1; print('\\u2705 Check 2: immediate success → status=ok, attempts=1')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: fn fails once then succeeds → attempts=2\n"
            "    try:\n"
            "        _n = [0]\n"
            "        def _flaky2():\n"
            "            _n[0] += 1\n"
            "            if _n[0] < 2:\n"
            "                raise RuntimeError('transient')\n"
            "            return 'ok'\n"
            "        r = resilient_step('fetch', _flaky2, max_attempts=3, base_delay=0.0)\n"
            "        assert r['status']   == 'ok',  f\"status: {r['status']!r}\"\n"
            "        assert r['attempts'] == 2,     f\"attempts should be 2, got {r['attempts']}\"\n"
            "        passed += 1; print('\\u2705 Check 3: 1 failure then success → attempts=2')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: always fails → status=error, attempts=max_attempts\n"
            "    try:\n"
            "        def _fail(): raise ValueError('permanent')\n"
            "        r = resilient_step('bad', _fail, max_attempts=3, base_delay=0.0)\n"
            "        assert r['status']   == 'error',    f\"status: {r['status']!r}\"\n"
            "        assert r['result']   is None,       f\"result should be None: {r['result']!r}\"\n"
            "        assert r['attempts'] == 3,          f\"attempts: {r['attempts']}\"\n"
            "        assert 'permanent'   in r['error'], f\"error: {r['error']!r}\"\n"
            "        passed += 1; print('\\u2705 Check 4: all-fail → status=error, attempts=max_attempts')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: resilient_step never raises\n"
            "    try:\n"
            "        r = resilient_step('bomb', lambda: 1/0, max_attempts=2, base_delay=0.0)\n"
            "        assert isinstance(r, dict), 'should return dict, not raise'\n"
            "        assert r['status'] == 'error'\n"
            "        passed += 1; print('\\u2705 Check 5: never raises — error captured in dict')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: resilient_step raised unexpectedly: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\\U0001f389 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "\n"
            "_run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + RESILIENT_STEP_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 04 — process_batch_with_dlq
# ---------------------------------------------------------------------------

def ex04():
    global _cid; _cid = 300
    return [
        md(
            "# Day 031 — Exercise 4: process_batch_with_dlq\n\n"
            "**What you'll build:** `process_batch_with_dlq(items, process_fn, dlq, "
            "max_attempts=3, base_delay=1.0, backoff=2.0) -> list` — "
            "applies `resilient_step` to every item; routes permanently failed items to "
            "the DLQ; returns a list of step result dicts (one per item).\n\n"
            "**Why it matters:** This is the core of a hardened batch processor. "
            "It processes every item regardless of failures, retries transient errors, "
            "and never loses a permanently failed item to the dead-letter queue."
        ),
        code("import time\nfrom datetime import datetime"),
        md("## Provided: DeadLetterQueue + resilient_step"),
        code(DLQ_IMPL + "\n\n\n" + RESILIENT_STEP_IMPL),
        md("## Your Implementation"),
        code(
            "def process_batch_with_dlq(\n"
            "    items: list,\n"
            "    process_fn,\n"
            "    dlq: DeadLetterQueue,\n"
            "    max_attempts: int = 3,\n"
            "    base_delay: float = 1.0,\n"
            "    backoff: float = 2.0,\n"
            ") -> list:\n"
            '    """\n'
            "    Process every item with resilient_step; route failures to DLQ.\n\n"
            "    Args:\n"
            "        items:      Input values to process.\n"
            "        process_fn: fn(item) -> any — the work to do per item.\n"
            "        dlq:        DeadLetterQueue instance for failed items.\n\n"
            "    Returns:\n"
            "        List of step result dicts, one per item (always len(items)).\n"
            '    """\n'
            "    # CRITICAL: use 'lambda i=item: process_fn(i)' NOT 'lambda: process_fn(item)'\n"
            "    # TODO: results = []\n"
            "    # TODO: for item in items:\n"
            "    #     r = resilient_step(str(item), lambda i=item: process_fn(i), ...)\n"
            "    #     if r['status'] == 'error': dlq.add(item, r['error'])\n"
            "    #     results.append(r)\n"
            "    # TODO: return results\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'process_batch_with_dlq' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: process_batch_with_dlq defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    # Check 2: all items succeed → results list length correct; DLQ empty\n"
            "    try:\n"
            "        dlq = DeadLetterQueue()\n"
            "        items = [1, 2, 3]\n"
            "        results = process_batch_with_dlq(items, lambda n: n * 10, dlq, base_delay=0.0)\n"
            "        assert isinstance(results, list), f'expected list, got {type(results)}'\n"
            "        assert len(results) == 3, f'expected 3 results, got {len(results)}'\n"
            "        assert all(r['status'] == 'ok' for r in results), \\\n"
            "            f'all should be ok: {[r[\"status\"] for r in results]}'\n"
            "        assert dlq.size() == 0, f'DLQ should be empty, size={dlq.size()}'\n"
            "        passed += 1; print('\\u2705 Check 2: all-ok → 3 results, DLQ empty')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: some items fail → DLQ has correct count\n"
            "    try:\n"
            "        dlq2 = DeadLetterQueue()\n"
            "        items2 = [1, 2, 3, 4, 5]\n"
            "        def _proc(n):\n"
            "            if n % 2 == 0:\n"
            "                raise ValueError(f'even: {n}')\n"
            "            return n * 10\n"
            "        results2 = process_batch_with_dlq(items2, _proc, dlq2, base_delay=0.0)\n"
            "        assert len(results2) == 5, f'expected 5 results, got {len(results2)}'\n"
            "        assert dlq2.size() == 2, f'expected 2 DLQ items, got {dlq2.size()}'\n"
            "        passed += 1; print(f'\\u2705 Check 3: 2 failures → DLQ size=2')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: DLQ items have correct item values and non-empty error\n"
            "    try:\n"
            "        dlq3 = DeadLetterQueue()\n"
            "        items3 = ['good', 'bad', 'good2']\n"
            "        def _proc3(s):\n"
            "            if s == 'bad':\n"
            "                raise RuntimeError('bad item')\n"
            "            return s.upper()\n"
            "        process_batch_with_dlq(items3, _proc3, dlq3, base_delay=0.0)\n"
            "        dlq_items = dlq3.drain()\n"
            "        assert len(dlq_items) == 1, f'expected 1 DLQ item, got {len(dlq_items)}'\n"
            "        assert dlq_items[0]['item'] == 'bad', \\\n"
            "            f\"DLQ item should be 'bad': {dlq_items[0]['item']!r}\"\n"
            "        assert dlq_items[0]['error'], 'DLQ error should be non-empty'\n"
            "        passed += 1; print('\\u2705 Check 4: DLQ item has correct item and error')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: lambda capture — each result name matches its item\n"
            "    try:\n"
            "        dlq4 = DeadLetterQueue()\n"
            "        items4 = ['alpha', 'beta', 'gamma']\n"
            "        results4 = process_batch_with_dlq(\n"
            "            items4, lambda s: s.upper(), dlq4, base_delay=0.0\n"
            "        )\n"
            "        for item, r in zip(items4, results4):\n"
            "            assert r['name'] == str(item), \\\n"
            "                f\"name mismatch: expected {item!r}, got {r['name']!r} (lambda capture bug?)\"\n"
            "            assert r['result'] == item.upper(), \\\n"
            "                f\"result mismatch for {item}: {r['result']!r}\"\n"
            "        passed += 1; print('\\u2705 Check 5: lambda capture correct — names match items')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\\U0001f389 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "\n"
            "_run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + PROCESS_BATCH_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 05 — ai_resilience_report
# ---------------------------------------------------------------------------

def ex05():
    global _cid; _cid = 400
    return [
        md(
            "# Day 031 — Exercise 5: ai_resilience_report\n\n"
            "**What you'll build:** `ai_resilience_report(batch_results, dlq_items, model='llama3.2') -> str` — "
            "formats batch run statistics and DLQ contents into a text block, "
            "then asks Ollama to produce a 2–3 sentence incident report with a recommended action.\n\n"
            "**Why it matters:** A list of step result dicts is useful for machines. "
            "An incident report is useful for engineers. ai_resilience_report bridges "
            "the gap: it translates failure statistics into actionable natural language."
        ),
        code("import ollama\nimport time\nfrom datetime import datetime"),
        md("## Provided: All Helper Functions"),
        code(ALL_IMPLS),
        md("## Your Implementation"),
        code(
            "def ai_resilience_report(\n"
            "    batch_results: list,\n"
            "    dlq_items: list,\n"
            "    model: str = 'llama3.2',\n"
            ") -> str:\n"
            '    """\n'
            "    Return a 2–3 sentence incident report with recommended action.\n\n"
            "    Args:\n"
            "        batch_results: List of step result dicts from process_batch_with_dlq.\n"
            "        dlq_items:     List of DLQ records (each has item, error, added_at).\n"
            "        model:         Ollama model name.\n\n"
            "    Returns:\n"
            "        Concise natural-language report as a string.\n"
            '    """\n'
            "    # TODO: total=len(batch_results); passed=sum(status=='ok')\n"
            "    # TODO: avg_attempts = round(sum(r.get('attempts',1) for r in batch_results)/total, 2) if total else 0.0\n"
            "    # TODO: lines = [f'Batch run: {passed}/{total} items succeeded, {len(dlq_items)} failed to DLQ.',\n"
            "    #                 f'Average attempts per item: {avg_attempts}.']\n"
            "    # TODO: for entry in dlq_items[:3]: lines.append(f'  DLQ: {entry[\"item\"]} \\u2014 {entry[\"error\"]}')\n"
            "    # TODO: ollama.chat with reliability-engineer system prompt\n"
            "    # TODO: return response['message']['content']\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    def _sr(name, status, attempts=1):\n"
            "        return {'name': name, 'status': status, 'result': None,\n"
            "                'error': None if status == 'ok' else 'err', 'duration_s': 0.1, 'attempts': attempts}\n"
            "\n"
            "    ALL_OK = [_sr('a', 'ok'), _sr('b', 'ok'), _sr('c', 'ok', 2)]\n"
            "    EMPTY_DLQ = []\n"
            "\n"
            "    MIXED = [_sr('a', 'ok'), _sr('b', 'error', 3), _sr('c', 'ok'), _sr('d', 'error', 3)]\n"
            "    FULL_DLQ = [\n"
            "        {'item': 'url_1', 'error': 'ConnectionTimeout', 'added_at': '2026-01-01T00:00:00'},\n"
            "        {'item': 'url_2', 'error': 'ReadTimeout',       'added_at': '2026-01-01T00:00:01'},\n"
            "    ]\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'ai_resilience_report' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: ai_resilience_report defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    ok_report = None\n"
            "\n"
            "    # Check 2: returns a string for all-ok input\n"
            "    try:\n"
            "        ok_report = ai_resilience_report(ALL_OK, EMPTY_DLQ)\n"
            "        assert isinstance(ok_report, str), \\\n"
            "            f'expected str, got {type(ok_report)}'\n"
            "        passed += 1; print('\\u2705 Check 2: returns a string for all-ok input')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: non-empty report\n"
            "    try:\n"
            "        assert ok_report is not None\n"
            "        assert len(ok_report.strip()) > 10, \\\n"
            "            f'report too short: {ok_report!r}'\n"
            "        passed += 1; print(f'\\u2705 Check 3: report is {len(ok_report)} chars')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: works with mixed (failures + DLQ items)\n"
            "    try:\n"
            "        err_report = ai_resilience_report(MIXED, FULL_DLQ)\n"
            "        assert isinstance(err_report, str) and len(err_report) > 10\n"
            "        passed += 1; print('\\u2705 Check 4: works with mixed batch + DLQ items')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: empty batch does not crash\n"
            "    try:\n"
            "        empty_report = ai_resilience_report([], [])\n"
            "        assert isinstance(empty_report, str) and len(empty_report) > 5\n"
            "        passed += 1; print('\\u2705 Check 5: empty batch returns a string without error')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\\U0001f389 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "\n"
            "_run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + AI_REPORT_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Project notebook (student template — NOT executed by gate)
# ---------------------------------------------------------------------------

def project_nb():
    global _cid; _cid = 500
    return [
        md(
            "# Day 031 Project: Hardened Batch Processor\n\n"
            "## What You're Building\n\n"
            "A resilient batch processor that:\n"
            "1. Applies `resilient_step` to every input item (retrying transient failures)\n"
            "2. Routes permanently failed items to a `DeadLetterQueue`\n"
            "3. Generates an AI-powered incident report via `ai_resilience_report`\n\n"
            "Think of this as a hardened version of the Day 30 pipeline: instead of a "
            "single pipeline that stops on failure, you have a batch that processes every "
            "item and preserves the audit trail.\n\n"
            "## Project Requirements\n\n"
            "1. Define a `process_item(item)` function that might fail transiently\n"
            "2. Process at least 5 items using `process_batch_with_dlq`\n"
            "3. Store the result as `result` (the list of step result dicts)\n"
            "4. Drain the DLQ into `dlq_items`\n"
            "5. Generate a report with `ai_resilience_report` stored as `report`\n"
            "6. Verify with `_run_project_checks()`"
        ),
        code("import ollama\nimport time\nfrom datetime import datetime"),
        md("## Provided: All Helper Functions"),
        code("import ollama\nimport time\nfrom datetime import datetime\n\n\n" + ALL_IMPLS + "\n\n\n" + AI_REPORT_IMPL),
        md(
            "## Your Batch Processor\n\n"
            "Design a process_item function and a batch to process. "
            "To test resilience, you can make the function fail for certain inputs "
            "or simulate transient failures with a counter."
        ),
        code(
            "# Example: process a list of URLs or IDs — some will fail\n"
            "# Your process_item can be anything: fetch data, transform a record, call an API\n"
            "\n"
            "_attempt_count = {}  # tracks per-item attempt count for simulated transience\n"
            "\n"
            "def process_item(item):\n"
            "    # Simulate: some items need 2 attempts, some always fail\n"
            "    _attempt_count[item] = _attempt_count.get(item, 0) + 1\n"
            "    if str(item).startswith('fail_'):\n"
            "        raise ValueError(f'permanently invalid: {item}')\n"
            "    if str(item).startswith('retry_') and _attempt_count[item] < 2:\n"
            "        raise ConnectionError(f'transient error, attempt {_attempt_count[item]}')\n"
            "    return f'processed: {item}'\n"
            "\n"
            "# Create your batch\n"
            "items = [\n"
            "    'item_1', 'item_2', 'retry_3', 'fail_4', 'item_5',\n"
            "    'retry_6', 'item_7', 'fail_8',\n"
            "]\n"
            "\n"
            "dlq = DeadLetterQueue()\n"
            "\n"
            "result = process_batch_with_dlq(\n"
            "    items, process_item, dlq,\n"
            "    max_attempts=3, base_delay=0.0,  # base_delay=0.0 for fast execution\n"
            ")\n"
            "\n"
            "dlq_items = dlq.drain()\n"
            "\n"
            "print(f'Processed {len(result)} items')\n"
            "print(f'Succeeded: {sum(1 for r in result if r[\"status\"]==\"ok\")}')\n"
            "print(f'Failed:    {len(dlq_items)} items in DLQ')\n"
            "for r in result:\n"
            "    print(f'  {r[\"status\"]:7} {r[\"name\"]:15} attempts={r[\"attempts\"]}')"
        ),
        code(
            "report = ai_resilience_report(result, dlq_items)\n"
            "print('\\nAI Incident Report:')\n"
            "print(report)"
        ),
        md("## Checks"),
        code(
            "def _run_project_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: result is a list\n"
            "    try:\n"
            "        assert 'result' in globals(), 'result not defined'\n"
            "        assert isinstance(result, list), f'result should be list, got {type(result)}'\n"
            "        passed += 1; print(f'\\u2705 Check 1: result is a list of {len(result)} records')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "\n"
            "    # Check 2: at least 5 items processed\n"
            "    try:\n"
            "        assert len(result) >= 5, f'expected >=5 items, got {len(result)}'\n"
            "        passed += 1; print(f'\\u2705 Check 2: {len(result)} items processed')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: dlq_items is a list\n"
            "    try:\n"
            "        assert 'dlq_items' in globals(), 'dlq_items not defined'\n"
            "        assert isinstance(dlq_items, list), f'dlq_items should be list'\n"
            "        passed += 1; print(f'\\u2705 Check 3: dlq_items is list with {len(dlq_items)} entries')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: all results have attempts key\n"
            "    try:\n"
            "        for r in result:\n"
            "            assert 'attempts' in r, f\"result missing 'attempts' key: {list(r)}\"\n"
            "        passed += 1; print('\\u2705 Check 4: all results have attempts key')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: report is a non-empty string\n"
            "    try:\n"
            "        assert 'report' in globals(), 'report not defined'\n"
            "        assert isinstance(report, str) and len(report) > 10, \\\n"
            "            f'report should be non-empty str: {report!r}'\n"
            "        passed += 1; print(f'\\u2705 Check 5: report is {len(report)} chars')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\\U0001f389 Project complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "\n"
            "_run_project_checks()"
        ),
        md(
            "## Bonus Challenges\n\n"
            "- Add jitter to the retry backoff: `time.sleep(base_delay * (backoff**attempt) + random.uniform(0, 0.5))`\n"
            "- Persist the DLQ to disk as JSON after each batch run so failures survive restarts\n"
            "- Implement a `replay_dlq(dlq_json_path, process_fn)` function that "
            "re-processes items from a saved DLQ file\n"
            "- Add an `exception_filter` parameter to process_batch_with_dlq that only retries "
            "specific exception types (e.g., `ConnectionError`) and immediately routes others to DLQ\n"
            "- Wire Day 30's `Pipeline` with Day 31's `resilient_step` — replace `chain_steps` "
            "with a `resilient_chain_steps` variant"
        ),
    ]


# ---------------------------------------------------------------------------
# Solution notebook (executed by gate)
# ---------------------------------------------------------------------------

def solution_nb():
    global _cid; _cid = 600

    imports = "import ollama\nimport time\nfrom datetime import datetime"
    all_code = imports + "\n\n\n" + ALL_IMPLS + "\n\n\n" + AI_REPORT_IMPL

    return [
        md(
            "# Day 031 Project Solution — Resilient Batch Processor\n\n"
            "A hardened batch processor with retry, dead-letter queue, and AI incident reporting."
        ),
        code(all_code),
        md("## Action 1 — Process Batch with Simulated Transient and Permanent Failures"),
        code(
            "_attempt_tracker = {}\n"
            "\n"
            "def process_item(item):\n"
            "    _attempt_tracker[item] = _attempt_tracker.get(item, 0) + 1\n"
            "    if str(item).startswith('fail'):\n"
            "        raise ValueError(f'invalid item: {item}')\n"
            "    if str(item).startswith('retry') and _attempt_tracker[item] < 2:\n"
            "        raise ConnectionError(f'transient on attempt {_attempt_tracker[item]}')\n"
            "    return f'ok:{item}'\n"
            "\n"
            "items = ['item_1', 'retry_2', 'item_3', 'fail_4', 'retry_5', 'item_6']\n"
            "dlq   = DeadLetterQueue()\n"
            "\n"
            "result = process_batch_with_dlq(\n"
            "    items, process_item, dlq, max_attempts=3, base_delay=0.0\n"
            ")\n"
            "\n"
            "print('Batch results:')\n"
            "for r in result:\n"
            "    print(f\"  {r['status']:7} {r['name']:12} attempts={r['attempts']}\")\n"
            "\n"
            "print(f'\\nSucceeded: {sum(1 for r in result if r[\"status\"]==\"ok\")}/{len(result)}')\n"
            "print(f'DLQ size:  {dlq.size()}')"
        ),
        md("## Action 2 — Inspect DLQ"),
        code(
            "dlq_items = dlq.drain()\n"
            "print(f'DLQ items ({len(dlq_items)}):')\n"
            "for entry in dlq_items:\n"
            "    print(f\"  item={entry['item']!r:15} error={entry['error']!r}\")\n"
            "\n"
            "assert dlq.size() == 0, 'DLQ should be empty after drain'\n"
            "print('DLQ drained successfully')"
        ),
        md("## Action 3 — AI Incident Report"),
        code(
            "report = ai_resilience_report(result, dlq_items)\n"
            "print('Incident Report:')\n"
            "print(report)\n"
            "\n"
            "assert isinstance(report, str) and len(report) > 10\n"
            "assert any(r['attempts'] >= 1 for r in result)\n"
            "\n"
            "print('\\nResilience complete!')"
        ),
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Generating Day 031 notebooks...")
    ex_dir  = DAY_DIR / "exercises"
    proj_dir = DAY_DIR / "project"
    sol_dir  = proj_dir / "solution"
    for d in (ex_dir, proj_dir, sol_dir):
        d.mkdir(parents=True, exist_ok=True)

    write_nb(ex_dir  / "exercise_01.ipynb", ex01())
    write_nb(ex_dir  / "exercise_02.ipynb", ex02())
    write_nb(ex_dir  / "exercise_03.ipynb", ex03())
    write_nb(ex_dir  / "exercise_04.ipynb", ex04())
    write_nb(ex_dir  / "exercise_05.ipynb", ex05())
    write_nb(proj_dir / "project.ipynb",    project_nb())
    write_nb(sol_dir  / "solution.ipynb",   solution_nb())
    print("Done.")


if __name__ == "__main__":
    main()
