#!/usr/bin/env python3
"""Generate all Day 033 notebooks: exercises 1-5, project, solution."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAY_DIR = ROOT / "02_automation" / "day_033"

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

ASYNC_CHAT_IMPL = """\
import asyncio
import ollama

async def async_chat(prompt: str, model: str = "llama3.2") -> str:
    client = ollama.AsyncClient()
    response = await client.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return response["message"]["content"]"""

GATHER_RESULTS_IMPL = """\
import asyncio

async def gather_results(coros: list) -> list:
    return list(await asyncio.gather(*coros))"""

THROTTLED_GATHER_IMPL = """\
async def throttled_gather(coros: list, max_concurrent: int) -> list:
    sem = asyncio.Semaphore(max_concurrent)
    async def _run(coro):
        async with sem:
            return await coro
    return list(await asyncio.gather(*[_run(c) for c in coros]))"""

PROCESS_BATCH_IMPL = """\
async def process_batch(
    items: list, async_fn, max_concurrent: int = 3
) -> list[dict]:
    sem = asyncio.Semaphore(max_concurrent)
    async def _run(item):
        async with sem:
            try:
                result = await async_fn(item)
                return {"item": item, "status": "ok",
                        "result": result, "error": None}
            except Exception as e:
                return {"item": item, "status": "error",
                        "result": None, "error": str(e)}
    return list(await asyncio.gather(*[_run(i) for i in items]))"""

BATCH_PROCESSOR_IMPL = """\
class BatchProcessor:
    def __init__(self, max_concurrent: int = 3, model: str = "llama3.2"):
        self.max_concurrent = max_concurrent
        self.model          = model

    async def process(self, items: list, prompt_fn) -> list[dict]:
        async def _call(item):
            return await async_chat(prompt_fn(item), self.model)
        return await process_batch(items, _call, self.max_concurrent)

    def run(self, items: list, prompt_fn) -> list[dict]:
        return asyncio.run(self.process(items, prompt_fn))"""

ALL_IMPLS = "\n\n\n".join([
    ASYNC_CHAT_IMPL,
    GATHER_RESULTS_IMPL,
    THROTTLED_GATHER_IMPL,
    PROCESS_BATCH_IMPL,
])


# ---------------------------------------------------------------------------
# Exercise 01 — async_chat
# ---------------------------------------------------------------------------

def ex01():
    global _cid; _cid = 0
    return [
        md(
            "# Day 033 — Exercise 1: async_chat\n\n"
            "**What you'll build:** `async_chat(prompt, model='llama3.2') -> str` — "
            "an async LLM call using `ollama.AsyncClient`. The first `async def` function "
            "you write in the course.\n\n"
            "**Why it matters:** `async_chat` is the atomic unit for all of Day 33. "
            "Every higher-level function (`gather_results`, `throttled_gather`, "
            "`process_batch`, `BatchProcessor`) builds on it. Getting the `await` "
            "placement right here makes the rest straightforward."
        ),
        md("## Your Implementation"),
        code(
            "import asyncio\n"
            "import ollama\n"
            "\n"
            "async def async_chat(prompt: str, model: str = 'llama3.2') -> str:\n"
            '    """\n'
            "    Call ollama asynchronously; return the reply string.\n\n"
            "    Args:\n"
            "        prompt: The user message to send.\n"
            "        model:  The Ollama model name (default 'llama3.2').\n\n"
            "    Returns:\n"
            "        The model's reply as a plain string.\n"
            '    """\n'
            "    # TODO: client = ollama.AsyncClient()\n"
            "    # TODO: response = await client.chat(\n"
            "    #     model=model,\n"
            "    #     messages=[{'role': 'user', 'content': prompt}],\n"
            "    # )\n"
            "    # TODO: return response['message']['content']\n"
            "    pass"
        ),
        md("## Check Your Work\n\n*(Run this cell — top-level `await` works in Jupyter/IPython)*"),
        code(
            "import asyncio\n"
            "import inspect\n"
            "\n"
            "async def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: async_chat is a coroutine function\n"
            "    try:\n"
            "        assert 'async_chat' in globals()\n"
            "        assert asyncio.iscoroutinefunction(async_chat), \\\n"
            "            'async_chat must be async def (is it missing the async keyword?)'\n"
            "        passed += 1; print('\\u2705 Check 1: async_chat is a coroutine function')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    # Check 2: calling it returns a coroutine (does NOT block)\n"
            "    try:\n"
            "        coro = async_chat('hi')\n"
            "        assert asyncio.iscoroutine(coro), \\\n"
            "            f'async_chat() should return a coroutine, got {type(coro)}'\n"
            "        coro.close()  # discard without running\n"
            "        passed += 1; print('\\u2705 Check 2: calling async_chat() returns a coroutine object')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: awaiting it returns a non-empty string\n"
            "    try:\n"
            "        result = await async_chat('Reply with only the word: hello')\n"
            "        assert isinstance(result, str), \\\n"
            "            f'expected str, got {type(result).__name__}: {result!r}'\n"
            "        assert result.strip(), \\\n"
            "            'result is an empty string — did you return response[\"message\"][\"content\"]?'\n"
            "        passed += 1; print(f'\\u2705 Check 3: await async_chat(...) returns non-empty string')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: result is a string (type guard)\n"
            "    try:\n"
            "        assert isinstance(result, str), \\\n"
            "            f'result type is {type(result).__name__}, expected str'\n"
            "        passed += 1; print(f'\\u2705 Check 4: result is str (got: {result.strip()[:40]!r})')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: model kwarg accepted without error\n"
            "    try:\n"
            "        r2 = await async_chat('Say yes.', model='llama3.2')\n"
            "        assert isinstance(r2, str) and r2.strip(), \\\n"
            "            f'explicit model kwarg failed: {r2!r}'\n"
            "        passed += 1; print('\\u2705 Check 5: model kwarg accepted and works')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\\U0001f389 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "\n"
            "await _run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + ASYNC_CHAT_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 02 — gather_results
# ---------------------------------------------------------------------------

def ex02():
    global _cid; _cid = 100
    return [
        md(
            "# Day 033 — Exercise 2: gather_results\n\n"
            "**What you'll build:** `gather_results(coros) -> list` — run a list of "
            "coroutines concurrently with `asyncio.gather` and return results in input order.\n\n"
            "**Why it matters:** `gather_results` is the speedup primitive. Instead of "
            "awaiting ten LLM calls one after another (serial), gather starts them all "
            "at once and collects results when every one is done. The check harness uses "
            "local `asyncio.sleep` coroutines — no LLM calls needed."
        ),
        md("## Your Implementation"),
        code(
            "import asyncio\n"
            "\n"
            "async def gather_results(coros: list) -> list:\n"
            '    """\n'
            "    Run all coroutines concurrently; return results in input order.\n\n"
            "    Args:\n"
            "        coros: List of coroutine objects (not functions — already called).\n\n"
            "    Returns:\n"
            "        List of results, one per coroutine, in the same order as coros.\n"
            '    """\n'
            "    # TODO: return list(await asyncio.gather(*coros))\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "import asyncio\n"
            "import time\n"
            "\n"
            "async def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    async def _slow(x, delay: float = 0.05):\n"
            "        await asyncio.sleep(delay)\n"
            "        return x\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'gather_results' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: gather_results defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    # Check 2: returns a list\n"
            "    try:\n"
            "        result = await gather_results([_slow(1), _slow(2), _slow(3)])\n"
            "        assert isinstance(result, list), \\\n"
            "            f'expected list, got {type(result).__name__}'\n"
            "        assert len(result) == 3, \\\n"
            "            f'expected 3 results, got {len(result)}'\n"
            "        passed += 1; print('\\u2705 Check 2: returns a list of correct length')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: order is preserved (coroutines finish at same time)\n"
            "    try:\n"
            "        result = await gather_results([_slow(30), _slow(10), _slow(20)])\n"
            "        assert result == [30, 10, 20], \\\n"
            "            f'order not preserved: expected [30,10,20], got {result}'\n"
            "        passed += 1; print('\\u2705 Check 3: results in input order (not completion order)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: empty list → []\n"
            "    try:\n"
            "        result = await gather_results([])\n"
            "        assert result == [], \\\n"
            "            f'empty coros: expected [], got {result}'\n"
            "        passed += 1; print('\\u2705 Check 4: empty list → []')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: concurrent — 5 × 0.05s tasks finish faster than 0.20s\n"
            "    try:\n"
            "        start = time.time()\n"
            "        coros = [_slow(i, delay=0.05) for i in range(5)]\n"
            "        await gather_results(coros)\n"
            "        elapsed = time.time() - start\n"
            "        assert elapsed < 0.20, \\\n"
            "            f'5 × 0.05s concurrent should take < 0.20s, took {elapsed:.3f}s — serial?'\n"
            "        passed += 1; print(f'\\u2705 Check 5: concurrent execution ({elapsed:.3f}s < 0.20s)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\\U0001f389 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "\n"
            "await _run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + GATHER_RESULTS_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 03 — throttled_gather
# ---------------------------------------------------------------------------

def ex03():
    global _cid; _cid = 200
    return [
        md(
            "# Day 033 — Exercise 3: throttled_gather\n\n"
            "**What you'll build:** `throttled_gather(coros, max_concurrent) -> list` — "
            "run coroutines concurrently with `asyncio.Semaphore` capping simultaneous "
            "execution to at most `max_concurrent`.\n\n"
            "**Why it matters:** `asyncio.gather` with 1000 coroutines starts 1000 "
            "simultaneous requests. A local Ollama server can only handle a few at a time. "
            "`throttled_gather` prevents server overload while keeping concurrent throughput."
        ),
        md("## Provided: gather_results"),
        code(GATHER_RESULTS_IMPL),
        md("## Your Implementation"),
        code(
            "async def throttled_gather(coros: list, max_concurrent: int) -> list:\n"
            '    """\n'
            "    Run coros concurrently, at most max_concurrent at a time.\n\n"
            "    Args:\n"
            "        coros:          List of coroutine objects.\n"
            "        max_concurrent: Maximum number of coroutines running simultaneously.\n\n"
            "    Returns:\n"
            "        List of results in input order.\n"
            '    """\n'
            "    # TODO: sem = asyncio.Semaphore(max_concurrent)\n"
            "    # TODO: async def _run(coro):\n"
            "    #     async with sem:\n"
            "    #         return await coro\n"
            "    # TODO: return list(await asyncio.gather(*[_run(c) for c in coros]))\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "import asyncio\n"
            "import time\n"
            "\n"
            "async def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    async def _slow(x, delay: float = 0.05):\n"
            "        await asyncio.sleep(delay)\n"
            "        return x\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'throttled_gather' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: throttled_gather defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    # Check 2: returns correct values\n"
            "    try:\n"
            "        result = await throttled_gather([_slow(10), _slow(20), _slow(30)], 2)\n"
            "        assert result == [10, 20, 30], \\\n"
            "            f'expected [10, 20, 30], got {result}'\n"
            "        passed += 1; print('\\u2705 Check 2: correct results returned')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: order preserved\n"
            "    try:\n"
            "        result = await throttled_gather([_slow(99), _slow(1), _slow(50)], 2)\n"
            "        assert result == [99, 1, 50], \\\n"
            "            f'order not preserved: {result}'\n"
            "        passed += 1; print('\\u2705 Check 3: input order preserved')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: max_concurrent=1 is serial — 3×0.05s tasks take ≥ 0.12s\n"
            "    try:\n"
            "        start = time.time()\n"
            "        await throttled_gather([_slow(1), _slow(2), _slow(3)], max_concurrent=1)\n"
            "        elapsed = time.time() - start\n"
            "        assert elapsed >= 0.12, \\\n"
            "            f'max_concurrent=1 should be serial (≥0.12s), took {elapsed:.3f}s'\n"
            "        passed += 1; print(f'\\u2705 Check 4: max_concurrent=1 is serial ({elapsed:.3f}s ≥ 0.12s)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: max_concurrent=4 is concurrent — 4×0.05s tasks take < 0.15s\n"
            "    try:\n"
            "        start = time.time()\n"
            "        await throttled_gather([_slow(i) for i in range(4)], max_concurrent=4)\n"
            "        elapsed = time.time() - start\n"
            "        assert elapsed < 0.15, \\\n"
            "            f'max_concurrent=4 should be concurrent (< 0.15s), took {elapsed:.3f}s'\n"
            "        passed += 1; print(f'\\u2705 Check 5: max_concurrent=4 is concurrent ({elapsed:.3f}s < 0.15s)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\\U0001f389 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "\n"
            "await _run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + THROTTLED_GATHER_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 04 — process_batch
# ---------------------------------------------------------------------------

def ex04():
    global _cid; _cid = 300
    return [
        md(
            "# Day 033 — Exercise 4: process_batch\n\n"
            "**What you'll build:** `process_batch(items, async_fn, max_concurrent=3) -> list[dict]` — "
            "apply an async function to every item with semaphore throttling and per-item "
            "error envelopes.\n\n"
            "**Why it matters:** One failed LLM call should not abort 99 successful ones. "
            "`process_batch` catches exceptions inside each coroutine and packages them as "
            "`{item, status:'error', result:None, error:str}` dicts instead of propagating "
            "them to `asyncio.gather`."
        ),
        md("## Provided: asyncio (already imported) + throttled_gather"),
        code("import asyncio\n\n" + THROTTLED_GATHER_IMPL),
        md("## Your Implementation"),
        code(
            "async def process_batch(\n"
            "    items: list, async_fn, max_concurrent: int = 3\n"
            ") -> list[dict]:\n"
            '    """\n'
            "    Batch-process items with async_fn; wrap each result in an error envelope.\n\n"
            "    Args:\n"
            "        items:          List of items to process.\n"
            "        async_fn:       Async function: async_fn(item) -> result.\n"
            "        max_concurrent: Max simultaneous coroutines (default 3).\n\n"
            "    Returns:\n"
            "        list[dict] — one per item, always len(items) records:\n"
            "        On success: {'item': item, 'status': 'ok', 'result': val, 'error': None}\n"
            "        On error:   {'item': item, 'status': 'error', 'result': None, 'error': str}\n"
            '    """\n'
            "    # TODO: sem = asyncio.Semaphore(max_concurrent)\n"
            "    # TODO: async def _run(item):\n"
            "    #     async with sem:\n"
            "    #         try:\n"
            "    #             result = await async_fn(item)\n"
            "    #             return {'item': item, 'status': 'ok', 'result': result, 'error': None}\n"
            "    #         except Exception as e:\n"
            "    #             return {'item': item, 'status': 'error', 'result': None, 'error': str(e)}\n"
            "    # TODO: return list(await asyncio.gather(*[_run(i) for i in items]))\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "import asyncio\n"
            "\n"
            "async def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Mock async functions for testing (no LLM calls)\n"
            "    async def _good(item):\n"
            "        await asyncio.sleep(0)\n"
            "        return f'done:{item}'\n"
            "\n"
            "    async def _fail_on_bad(item):\n"
            "        await asyncio.sleep(0)\n"
            "        if item == 'bad':\n"
            "            raise ValueError('intentional failure')\n"
            "        return f'ok:{item}'\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'process_batch' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: process_batch defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    # Check 2: result list has correct keys\n"
            "    try:\n"
            "        results = await process_batch(['a', 'b'], _good)\n"
            "        assert isinstance(results, list)\n"
            "        for r in results:\n"
            "            for key in ('item', 'status', 'result', 'error'):\n"
            "                assert key in r, f'missing key {key!r} in {r}'\n"
            "        passed += 1; print('\\u2705 Check 2: result dicts have item, status, result, error')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: successful items have status='ok' and non-None result\n"
            "    try:\n"
            "        results = await process_batch(['x', 'y', 'z'], _good)\n"
            "        for r in results:\n"
            "            assert r['status'] == 'ok', f\"status should be 'ok': {r}\"\n"
            "            assert r['result'] is not None, f'result should not be None: {r}'\n"
            "            assert r['error'] is None, f\"error should be None for ok: {r}\"\n"
            "        passed += 1; print('\\u2705 Check 3: ok items have status=ok, non-None result, error=None')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: failing items have status='error', result=None, error=str\n"
            "    try:\n"
            "        results = await process_batch(['good', 'bad', 'also_good'], _fail_on_bad)\n"
            "        ok_items  = [r for r in results if r['status'] == 'ok']\n"
            "        err_items = [r for r in results if r['status'] == 'error']\n"
            "        assert len(ok_items)  == 2, f'expected 2 ok, got {len(ok_items)}'\n"
            "        assert len(err_items) == 1, f'expected 1 error, got {len(err_items)}'\n"
            "        err = err_items[0]\n"
            "        assert err['item']   == 'bad',  f\"error item should be 'bad': {err}\"\n"
            "        assert err['result'] is None,   f'error result should be None: {err}'\n"
            "        assert isinstance(err['error'], str) and err['error'], \\\n"
            "            f'error should be non-empty str: {err}'\n"
            "        passed += 1; print('\\u2705 Check 4: failing items captured as error envelopes')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: result length always == len(items)\n"
            "    try:\n"
            "        for n in (0, 1, 5):\n"
            "            results = await process_batch(list(range(n)), _good)\n"
            "            assert len(results) == n, \\\n"
            "                f'n={n}: expected {n} results, got {len(results)}'\n"
            "        passed += 1; print('\\u2705 Check 5: result length always equals len(items)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\\U0001f389 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "\n"
            "await _run_checks()"
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
# Exercise 05 — BatchProcessor
# ---------------------------------------------------------------------------

def ex05():
    global _cid; _cid = 400
    return [
        md(
            "# Day 033 — Exercise 5: BatchProcessor\n\n"
            "**What you'll build:** The `BatchProcessor` class — `process(items, prompt_fn)` "
            "(async, for notebooks) and `run(items, prompt_fn)` (sync, for scripts). "
            "`prompt_fn` converts each item to a prompt string; `BatchProcessor` handles "
            "the concurrent LLM calls.\n\n"
            "**Why it matters:** Separating *what to ask* (`prompt_fn`) from *how to batch* "
            "(`BatchProcessor`) makes the class reusable across any batch task — just swap "
            "the `prompt_fn`."
        ),
        md("## Provided: All Helper Functions"),
        code(ALL_IMPLS),
        md("## Your Implementation"),
        code(
            "class BatchProcessor:\n"
            '    """\n'
            "    Async batch processor. Applies prompt_fn to each item, calls async_chat,\n"
            "    and returns error-envelope dicts via process_batch.\n"
            '    """\n'
            "\n"
            "    def __init__(self, max_concurrent: int = 3, model: str = 'llama3.2'):\n"
            "        # TODO: self.max_concurrent = max_concurrent\n"
            "        # TODO: self.model = model\n"
            "        pass\n"
            "\n"
            "    async def process(self, items: list, prompt_fn) -> list[dict]:\n"
            "        # TODO: async def _call(item):\n"
            "        #     return await async_chat(prompt_fn(item), self.model)\n"
            "        # TODO: return await process_batch(items, _call, self.max_concurrent)\n"
            "        pass\n"
            "\n"
            "    def run(self, items: list, prompt_fn) -> list[dict]:\n"
            "        # TODO: return asyncio.run(self.process(items, prompt_fn))\n"
            "        # Note: do NOT call run() from inside Jupyter — use await process() instead\n"
            "        pass"
        ),
        md("## Check Your Work"),
        code(
            "import asyncio\n"
            "\n"
            "async def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: class defined with all 3 methods\n"
            "    try:\n"
            "        assert 'BatchProcessor' in globals()\n"
            "        for m in ('process', 'run'):\n"
            "            assert hasattr(BatchProcessor, m), f'missing method: {m}'\n"
            "        passed += 1; print('\\u2705 Check 1: BatchProcessor with process and run methods')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    # Check 2: __init__ stores max_concurrent and model\n"
            "    try:\n"
            "        bp = BatchProcessor(max_concurrent=5, model='llama3.2')\n"
            "        assert bp.max_concurrent == 5, \\\n"
            "            f'max_concurrent: expected 5, got {bp.max_concurrent}'\n"
            "        assert bp.model == 'llama3.2', \\\n"
            "            f'model: expected llama3.2, got {bp.model!r}'\n"
            "        bp_def = BatchProcessor()\n"
            "        assert bp_def.max_concurrent == 3, \\\n"
            "            f'default max_concurrent: expected 3, got {bp_def.max_concurrent}'\n"
            "        passed += 1; print('\\u2705 Check 2: __init__ stores max_concurrent and model with defaults')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: process is an async method\n"
            "    try:\n"
            "        bp = BatchProcessor()\n"
            "        assert asyncio.iscoroutinefunction(bp.process), \\\n"
            "            'process must be async def'\n"
            "        coro = bp.process([], lambda x: x)\n"
            "        assert asyncio.iscoroutine(coro), \\\n"
            "            f'process() should return a coroutine, got {type(coro)}'\n"
            "        await coro  # run empty batch\n"
            "        passed += 1; print('\\u2705 Check 3: process is an async method')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: await process returns list[dict] with correct structure\n"
            "    try:\n"
            "        bp = BatchProcessor(max_concurrent=2)\n"
            "        items = ['cat', 'dog']\n"
            "        results = await bp.process(\n"
            "            items, lambda x: f\"What animal is a {x}? One word only.\"\n"
            "        )\n"
            "        assert isinstance(results, list), \\\n"
            "            f'expected list, got {type(results).__name__}'\n"
            "        assert len(results) == 2, \\\n"
            "            f'expected 2 results, got {len(results)}'\n"
            "        for r in results:\n"
            "            assert 'item'   in r, f'missing item key: {r}'\n"
            "            assert 'status' in r, f'missing status key: {r}'\n"
            "            assert 'result' in r, f'missing result key: {r}'\n"
            "            assert 'error'  in r, f'missing error key: {r}'\n"
            "        passed += 1; print('\\u2705 Check 4: await process returns list[dict] with correct structure')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "        results = []\n"
            "\n"
            "    # Check 5: successful results have status='ok' and string result\n"
            "    try:\n"
            "        ok_results = [r for r in results if r['status'] == 'ok']\n"
            "        assert len(ok_results) > 0, \\\n"
            "            'no ok results — did the LLM calls succeed?'\n"
            "        for r in ok_results:\n"
            "            assert isinstance(r['result'], str), \\\n"
            "                f\"ok result should be str: {r['result']!r}\"\n"
            "            assert r['error'] is None, \\\n"
            "                f\"ok result error should be None: {r}\"\n"
            "        passed += 1; print(f'\\u2705 Check 5: {len(ok_results)}/2 ok results with string content')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\\U0001f389 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "\n"
            "await _run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + BATCH_PROCESSOR_IMPL + "\n"
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
            "# Day 033 Project: Async Batch Classifier\n\n"
            "## What You're Building\n\n"
            "A `BatchProcessor` that classifies a list of sentences concurrently — "
            "demonstrating that async batch processing is faster than serial for "
            "I/O-bound LLM calls.\n\n"
            "## Project Requirements\n\n"
            "1. Define a list of at least 8 sentences across two or more categories "
            "   (e.g., positive/negative, question/statement, short/long)\n"
            "2. Create a `BatchProcessor` with `max_concurrent=3`\n"
            "3. Use `await bp.process(items, prompt_fn)` to classify all items concurrently\n"
            "4. Print a summary showing how many items were classified in each category\n"
            "5. Time the batch and compare to an estimate of serial time\n"
            "6. Verify with `_run_project_checks()`"
        ),
        md("## Provided: All Helper Functions + BatchProcessor"),
        code(ALL_IMPLS + "\n\n\n" + BATCH_PROCESSOR_IMPL),
        md("## Your Batch Classification"),
        code(
            "import time\n"
            "\n"
            "# At least 8 sentences to classify\n"
            "SENTENCES = [\n"
            "    'I absolutely love this product!',\n"
            "    'This is the worst experience I have ever had.',\n"
            "    'It was okay, nothing special.',\n"
            "    'Fantastic quality, would buy again.',\n"
            "    'Total waste of money.',\n"
            "    'Pretty good, met my expectations.',\n"
            "    'Exceeded all my expectations!',\n"
            "    'Not impressed at all.',\n"
            "]\n"
            "\n"
            "def classify_prompt(sentence: str) -> str:\n"
            "    return (\n"
            "        f\"Classify this review as 'positive', 'negative', or 'neutral'. \"\n"
            "        f\"Reply with one word only.\\n\\nReview: {sentence}\"\n"
            "    )\n"
            "\n"
            "bp = BatchProcessor(max_concurrent=3)\n"
            "\n"
            "# TODO: await bp.process(SENTENCES, classify_prompt) and store as results\n"
            "# TODO: print results and summary\n"
            "# TODO: time the batch and print elapsed seconds\n"
        ),
        md("## Checks"),
        code(
            "async def _run_project_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: bp is a BatchProcessor\n"
            "    try:\n"
            "        assert 'bp' in globals()\n"
            "        assert isinstance(bp, BatchProcessor), \\\n"
            "            f'bp should be BatchProcessor, got {type(bp)}'\n"
            "        passed += 1; print('\\u2705 Check 1: bp is a BatchProcessor')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "\n"
            "    # Check 2: SENTENCES has ≥ 8 items\n"
            "    try:\n"
            "        assert 'SENTENCES' in globals()\n"
            "        assert len(SENTENCES) >= 8, \\\n"
            "            f'need ≥8 sentences, got {len(SENTENCES)}'\n"
            "        passed += 1; print(f'\\u2705 Check 2: {len(SENTENCES)} sentences defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: results defined and has correct length\n"
            "    try:\n"
            "        assert 'results' in globals()\n"
            "        assert len(results) == len(SENTENCES), \\\n"
            "            f'results length {len(results)} != sentences length {len(SENTENCES)}'\n"
            "        passed += 1; print(f'\\u2705 Check 3: {len(results)} results for {len(SENTENCES)} sentences')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: all results are dicts with required keys\n"
            "    try:\n"
            "        for r in results:\n"
            "            for k in ('item', 'status', 'result', 'error'):\n"
            "                assert k in r, f'missing key {k!r}: {r}'\n"
            "        ok = [r for r in results if r['status'] == 'ok']\n"
            "        assert len(ok) > 0, 'no successful classifications'\n"
            "        passed += 1; print(f'\\u2705 Check 4: {len(ok)}/{len(results)} items classified successfully')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: bp.max_concurrent == 3\n"
            "    try:\n"
            "        assert bp.max_concurrent == 3, \\\n"
            "            f'max_concurrent should be 3, got {bp.max_concurrent}'\n"
            "        passed += 1; print('\\u2705 Check 5: max_concurrent=3 set correctly')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\\U0001f389 Project complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "\n"
            "await _run_project_checks()"
        ),
        md(
            "## Bonus Challenges\n\n"
            "- Add timing: measure total batch time and compare to `len(SENTENCES) * estimate_per_call`\n"
            "  to show the speedup factor\n"
            "- Process two different datasets concurrently using `gather_results` of two "
            "  `BatchProcessor.process()` calls at the same time\n"
            "- Add retry logic: after the batch, re-run `process_batch` on the error items "
            "  from the first run (combine with Day 031 retry)\n"
            "- Try `max_concurrent` values of 1, 3, 5 and plot (print) the wall time for each —\n"
            "  at what point does more concurrency stop helping?\n"
            "- Integrate `SecureConfig` (Day 032) to load the model name and max_concurrent "
            "  from a `.env` string instead of hardcoding them"
        ),
    ]


# ---------------------------------------------------------------------------
# Solution notebook (executed by gate)
# ---------------------------------------------------------------------------

def solution_nb():
    global _cid; _cid = 600

    all_code = ALL_IMPLS + "\n\n\n" + BATCH_PROCESSOR_IMPL

    return [
        md(
            "# Day 033 Project Solution — Async Batch Classifier\n\n"
            "Concurrent LLM batch processing with `BatchProcessor`, "
            "`throttled_gather`, and error envelopes."
        ),
        code(all_code),
        md("## Action 1 — Verify async_chat Works"),
        code(
            "# Single async LLM call (baseline)\n"
            "reply = await async_chat('Reply with the single word: hello')\n"
            "print(f'Single call reply: {reply.strip()!r}')\n"
            "assert isinstance(reply, str) and reply.strip()"
        ),
        md("## Action 2 — Concurrent Batch with throttled_gather"),
        code(
            "import time\n"
            "\n"
            "PROMPTS = [\n"
            "    'Name one colour. One word only.',\n"
            "    'Name one country. One word only.',\n"
            "    'Name one fruit. One word only.',\n"
            "    'Name one planet. One word only.',\n"
            "    'Name one animal. One word only.',\n"
            "]\n"
            "\n"
            "start  = time.time()\n"
            "coros  = [async_chat(p) for p in PROMPTS]\n"
            "results = await throttled_gather(coros, max_concurrent=3)\n"
            "elapsed = time.time() - start\n"
            "\n"
            "print(f'Batch of {len(PROMPTS)} items completed in {elapsed:.2f}s')\n"
            "for prompt, reply in zip(PROMPTS, results):\n"
            "    print(f'  {prompt:40} → {reply.strip()}')\n"
            "\n"
            "assert len(results) == len(PROMPTS)"
        ),
        md("## Action 3 — BatchProcessor with Error Envelopes"),
        code(
            "ITEMS = [\n"
            "    'The product is amazing!',\n"
            "    'Terrible, would not recommend.',\n"
            "    'Pretty decent overall.',\n"
            "]\n"
            "\n"
            "bp = BatchProcessor(max_concurrent=3)\n"
            "batch_results = await bp.process(\n"
            "    ITEMS,\n"
            "    lambda x: f\"Classify as positive/negative/neutral. One word.\\n\\n'{x}'\",\n"
            ")\n"
            "\n"
            "ok_count  = sum(1 for r in batch_results if r['status'] == 'ok')\n"
            "err_count = sum(1 for r in batch_results if r['status'] == 'error')\n"
            "\n"
            "print(f'BatchProcessor: {ok_count} ok, {err_count} errors')\n"
            "for r in batch_results:\n"
            "    label = r['result'].strip() if r['status'] == 'ok' else f\"ERROR: {r['error']}\"\n"
            "    print(f'  {r[\"item\"][:35]:35} → {label}')\n"
            "\n"
            "assert len(batch_results) == len(ITEMS)\n"
            "assert ok_count > 0\n"
            "\n"
            "print('\\nBatch complete!')"
        ),
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Generating Day 033 notebooks...")
    ex_dir   = DAY_DIR / "exercises"
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
