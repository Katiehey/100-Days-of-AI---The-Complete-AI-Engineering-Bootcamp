#!/usr/bin/env python3
"""Generate all Day 030 notebooks: exercises 1-5, project, solution."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAY_DIR = ROOT / "02_automation" / "day_030"

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

RUN_STEP_IMPL = """\
import time


def run_step(name: str, fn) -> dict:
    start = time.time()
    try:
        result = fn()
        return {
            "name":       name,
            "status":     "ok",
            "result":     result,
            "error":      None,
            "duration_s": round(time.time() - start, 3),
        }
    except Exception as e:
        return {
            "name":       name,
            "status":     "error",
            "result":     None,
            "error":      str(e),
            "duration_s": round(time.time() - start, 3),
        }"""

CHAIN_STEPS_IMPL = """\
def chain_steps(steps: list, stop_on_error: bool = True) -> list:
    results = []
    failed  = False
    for name, fn in steps:
        if failed and stop_on_error:
            results.append({
                "name":       name,
                "status":     "skipped",
                "result":     None,
                "error":      None,
                "duration_s": 0.0,
            })
        else:
            step_result = run_step(name, fn)
            results.append(step_result)
            if step_result["status"] == "error":
                failed = True
    return results"""

SUMMARIZE_RUN_IMPL = """\
def summarize_run(step_results: list) -> dict:
    statuses = [s["status"] for s in step_results]
    return {
        "total":            len(step_results),
        "passed":           statuses.count("ok"),
        "failed":           statuses.count("error"),
        "skipped":          statuses.count("skipped"),
        "total_duration_s": round(
            sum(s.get("duration_s", 0.0) for s in step_results), 3
        ),
        "all_ok":           all(s == "ok" for s in statuses),
    }"""

AI_PIPELINE_SUMMARY_IMPL = """\
def ai_pipeline_summary(step_results: list, model: str = "llama3.2") -> str:
    summary = summarize_run(step_results)
    lines = []
    for s in step_results:
        if s["status"] == "ok":
            lines.append(f"  \\u2713 {s['name']} ({s['duration_s']:.3f}s)")
        elif s["status"] == "error":
            lines.append(f"  \\u2717 {s['name']}: {s['error']}")
        else:
            lines.append(f"  - {s['name']}: skipped")
    run_text = (
        f"{summary['passed']}/{summary['total']} steps passed, "
        f"{summary['total_duration_s']}s total\\n"
        + "\\n".join(lines)
    )
    response = ollama.chat(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a pipeline monitor. "
                    "Summarise a workflow run in 2\\u20133 sentences. Be concise."
                ),
            },
            {
                "role": "user",
                "content": f"{run_text}\\n\\nSummarise the run:",
            },
        ],
    )
    return response["message"]["content"]"""

PIPELINE_IMPL = """\
class Pipeline:
    def __init__(
        self,
        name: str = "pipeline",
        stop_on_error: bool = True,
        model: str = "llama3.2",
    ):
        self.name          = name
        self.stop_on_error = stop_on_error
        self.model         = model
        self._steps: list  = []

    def add_step(self, name: str, fn) -> "Pipeline":
        self._steps.append((name, fn))
        return self

    def run(self) -> dict:
        step_results = chain_steps(self._steps, stop_on_error=self.stop_on_error)
        summary      = summarize_run(step_results)
        report       = ai_pipeline_summary(step_results, model=self.model)
        return {
            "name":    self.name,
            "steps":   step_results,
            "summary": summary,
            "report":  report,
        }"""

ALL_IMPLS = "\n\n\n".join([
    RUN_STEP_IMPL,
    CHAIN_STEPS_IMPL,
    SUMMARIZE_RUN_IMPL,
    AI_PIPELINE_SUMMARY_IMPL,
])


# ---------------------------------------------------------------------------
# Exercise 01 — run_step
# ---------------------------------------------------------------------------

def ex01():
    global _cid; _cid = 0
    return [
        md(
            "# Day 030 — Exercise 1: run_step\n\n"
            "**What you'll build:** `run_step(name, fn) -> dict` — calls `fn()` safely, "
            "measures elapsed time, and returns a standard step result dict with five keys: "
            "`name`, `status` ('ok' or 'error'), `result`, `error`, `duration_s`.\n\n"
            "**Why it matters:** run_step is the foundation of the pipeline. By wrapping "
            "every callable in the same try/except, the pipeline runner never has to handle "
            "exceptions itself — it always gets back a predictable dict it can examine."
        ),
        code("import time"),
        md("## Your Implementation"),
        code(
            "def run_step(name: str, fn) -> dict:\n"
            '    """\n'
            "    Call fn() safely; return a standard step result dict.\n\n"
            "    Args:\n"
            "        name: Human-readable label for the step.\n"
            "        fn:   Zero-arg callable to execute.\n\n"
            "    Returns:\n"
            "        Dict with keys: name, status ('ok'|'error'), result, error, duration_s.\n"
            "        Never raises — all exceptions are captured in the error field.\n"
            '    """\n'
            "    # TODO: start = time.time()\n"
            "    # TODO: try: result = fn() → return ok dict\n"
            "    # TODO: except Exception as e: → return error dict with str(e)\n"
            "    # Both branches return same 5 keys; duration_s = round(time.time()-start, 3)\n"
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
            "        assert 'run_step' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: run_step defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    ok_result = None\n"
            "\n"
            "    # Check 2: successful fn → status='ok', result correct\n"
            "    try:\n"
            "        ok_result = run_step('compute', lambda: 2 + 2)\n"
            "        assert isinstance(ok_result, dict), \\\n"
            "            f'expected dict, got {type(ok_result)}'\n"
            "        assert ok_result.get('status') == 'ok', \\\n"
            "            f\"status should be 'ok', got {ok_result.get('status')!r}\"\n"
            "        assert ok_result.get('result') == 4, \\\n"
            "            f\"result should be 4, got {ok_result.get('result')!r}\"\n"
            "        passed += 1; print('\\u2705 Check 2: ok step returns correct result')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: ok step has error=None and all five keys\n"
            "    try:\n"
            "        assert ok_result is not None\n"
            "        for k in ('name', 'status', 'result', 'error', 'duration_s'):\n"
            "            assert k in ok_result, f'missing key: {k}'\n"
            "        assert ok_result['error'] is None, \\\n"
            "            f\"error should be None on ok step, got {ok_result['error']!r}\"\n"
            "        assert ok_result['name'] == 'compute', \\\n"
            "            f\"name wrong: {ok_result['name']!r}\"\n"
            "        passed += 1; print('\\u2705 Check 3: all five keys present; error=None on ok')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: failing fn → status='error', error=str(exception)\n"
            "    try:\n"
            "        def _raise():\n"
            "            raise ValueError('bad input')\n"
            "        err_result = run_step('validate', _raise)\n"
            "        assert err_result.get('status') == 'error', \\\n"
            "            f\"status should be 'error', got {err_result.get('status')!r}\"\n"
            "        assert err_result.get('error') == 'bad input', \\\n"
            "            f\"error should be 'bad input', got {err_result.get('error')!r}\"\n"
            "        assert err_result.get('result') is None, \\\n"
            "            f\"result should be None on error, got {err_result.get('result')!r}\"\n"
            "        passed += 1; print('\\u2705 Check 4: failing fn → status=error, error=str(e)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: run_step never raises — exception is captured, not re-raised\n"
            "    try:\n"
            "        r = run_step('bomb', lambda: 1 / 0)\n"
            "        assert isinstance(r, dict), \\\n"
            "            'run_step should return dict, not raise'\n"
            "        assert r['status'] == 'error'\n"
            "        assert isinstance(r.get('duration_s'), float)\n"
            "        passed += 1; print('\\u2705 Check 5: run_step never raises; duration_s is float')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: run_step raised unexpectedly: {e}')\n"
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
            + RUN_STEP_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 02 — chain_steps
# ---------------------------------------------------------------------------

def ex02():
    global _cid; _cid = 100
    return [
        md(
            "# Day 030 — Exercise 2: chain_steps\n\n"
            "**What you'll build:** `chain_steps(steps, stop_on_error=True) -> list` — "
            "runs a list of `(name, fn)` tuples in sequence using `run_step`. When a step "
            "fails and `stop_on_error=True`, remaining steps get status='skipped' without "
            "calling their `fn`. The returned list always has exactly `len(steps)` records.\n\n"
            "**Why it matters:** Downstream steps often depend on upstream output. "
            "Skipping rather than running them prevents corrupt state when the data "
            "they would have received is missing or broken."
        ),
        code("import time"),
        md("## Provided: run_step"),
        code(RUN_STEP_IMPL),
        md("## Your Implementation"),
        code(
            "def chain_steps(steps: list, stop_on_error: bool = True) -> list:\n"
            '    """\n'
            "    Run a list of (name, fn) tuples; skip tail on error if stop_on_error.\n\n"
            "    Args:\n"
            "        steps:         List of (name, fn) tuples.\n"
            "        stop_on_error: If True, skip remaining steps after first failure.\n\n"
            "    Returns:\n"
            "        List of step result dicts — always len(steps) records.\n"
            "        Skipped steps have status='skipped', result=None, error=None, duration_s=0.0.\n"
            '    """\n'
            "    # TODO: results = []; failed = False\n"
            "    # TODO: for name, fn in steps:\n"
            "    #     if failed and stop_on_error: append skipped record\n"
            "    #     else: step_result = run_step(name, fn); append it\n"
            "    #           if step_result['status'] == 'error': failed = True\n"
            "    # TODO: return results\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    def _ok(val):\n"
            "        def fn(): return val\n"
            "        return fn\n"
            "    def _fail():\n"
            "        raise RuntimeError('step failed')\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'chain_steps' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: chain_steps defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    # Check 2: all steps pass → list of 3 ok records\n"
            "    try:\n"
            "        steps = [('a', _ok(1)), ('b', _ok(2)), ('c', _ok(3))]\n"
            "        results = chain_steps(steps)\n"
            "        assert isinstance(results, list), \\\n"
            "            f'expected list, got {type(results)}'\n"
            "        assert len(results) == 3, \\\n"
            "            f'expected 3 records, got {len(results)}'\n"
            "        assert all(r['status'] == 'ok' for r in results), \\\n"
            "            f'all should be ok: {[r[\"status\"] for r in results]}'\n"
            "        passed += 1; print('\\u2705 Check 2: all-ok → 3 ok records')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: step_b fails → step_c is skipped (stop_on_error=True)\n"
            "    try:\n"
            "        steps = [('step_a', _ok('good')), ('step_b', _fail), ('step_c', _ok('done'))]\n"
            "        results = chain_steps(steps, stop_on_error=True)\n"
            "        assert len(results) == 3, \\\n"
            "            f'expected 3 records, got {len(results)}'\n"
            "        assert results[0]['status'] == 'ok', \\\n"
            "            f\"step_a should be 'ok': {results[0]['status']!r}\"\n"
            "        assert results[1]['status'] == 'error', \\\n"
            "            f\"step_b should be 'error': {results[1]['status']!r}\"\n"
            "        assert results[2]['status'] == 'skipped', \\\n"
            "            f\"step_c should be 'skipped': {results[2]['status']!r}\"\n"
            "        passed += 1; print('\\u2705 Check 3: fail → remaining steps skipped')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: stop_on_error=False → all steps run even after failure\n"
            "    try:\n"
            "        steps = [('step_a', _ok('good')), ('step_b', _fail), ('step_c', _ok('done'))]\n"
            "        results = chain_steps(steps, stop_on_error=False)\n"
            "        assert results[1]['status'] == 'error', \\\n"
            "            f\"step_b should still be 'error': {results[1]['status']!r}\"\n"
            "        assert results[2]['status'] == 'ok', \\\n"
            "            f\"step_c should run and be 'ok': {results[2]['status']!r}\"\n"
            "        passed += 1; print('\\u2705 Check 4: stop_on_error=False → all steps run')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: skipped record has correct sentinel values\n"
            "    try:\n"
            "        steps = [('a', _fail), ('b', _ok(1))]\n"
            "        results = chain_steps(steps)\n"
            "        skipped = results[1]\n"
            "        assert skipped['status']     == 'skipped',  f\"status: {skipped['status']!r}\"\n"
            "        assert skipped['result']     is None,       f\"result: {skipped['result']!r}\"\n"
            "        assert skipped['error']      is None,       f\"error: {skipped['error']!r}\"\n"
            "        assert skipped['duration_s'] == 0.0,        f\"duration_s: {skipped['duration_s']}\"\n"
            "        assert skipped['name']       == 'b',        f\"name: {skipped['name']!r}\"\n"
            "        passed += 1; print('\\u2705 Check 5: skipped sentinel values correct')\n"
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
            + CHAIN_STEPS_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 03 — summarize_run
# ---------------------------------------------------------------------------

def ex03():
    global _cid; _cid = 200
    return [
        md(
            "# Day 030 — Exercise 3: summarize_run\n\n"
            "**What you'll build:** `summarize_run(step_results) -> dict` — "
            "aggregates a list of step result dicts into a summary with six keys: "
            "`total`, `passed`, `failed`, `skipped`, `total_duration_s`, `all_ok`.\n\n"
            "**Why it matters:** The step list tells you what each step did. "
            "The summary tells you what the pipeline did overall. It is the "
            "single dict you log, alert on, or return as the pipeline's outcome."
        ),
        md("## Your Implementation"),
        code(
            "def summarize_run(step_results: list) -> dict:\n"
            '    """\n'
            "    Aggregate a list of step result dicts into a run summary.\n\n"
            "    Args:\n"
            "        step_results: List of step result dicts from chain_steps.\n\n"
            "    Returns:\n"
            "        Dict with six keys:\n"
            "          total            — len(step_results)\n"
            "          passed           — count of status=='ok'\n"
            "          failed           — count of status=='error'\n"
            "          skipped          — count of status=='skipped'\n"
            "          total_duration_s — round(sum of duration_s, 3)\n"
            "          all_ok           — True iff every status is 'ok'\n"
            '    """\n'
            "    # TODO: statuses = [s['status'] for s in step_results]\n"
            "    # TODO: return dict with total, passed, failed, skipped,\n"
            "    #        total_duration_s, all_ok\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    def _sr(name, status, dur=0.1):\n"
            "        return {'name': name, 'status': status, 'result': None,\n"
            "                'error': None, 'duration_s': dur}\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'summarize_run' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: summarize_run defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    # Check 2: all-ok → all_ok=True, passed=total\n"
            "    try:\n"
            "        records = [_sr('a', 'ok', 0.1), _sr('b', 'ok', 0.2), _sr('c', 'ok', 0.3)]\n"
            "        s = summarize_run(records)\n"
            "        assert isinstance(s, dict), f'expected dict, got {type(s)}'\n"
            "        assert s.get('total')  == 3,    f\"total wrong: {s.get('total')}\"\n"
            "        assert s.get('passed') == 3,    f\"passed wrong: {s.get('passed')}\"\n"
            "        assert s.get('all_ok') is True, f\"all_ok wrong: {s.get('all_ok')}\"\n"
            "        passed += 1; print('\\u2705 Check 2: all-ok → all_ok=True, passed=3')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: mixed → correct counts\n"
            "    try:\n"
            "        records = [\n"
            "            _sr('a', 'ok',      0.1),\n"
            "            _sr('b', 'ok',      0.2),\n"
            "            _sr('c', 'error',   0.05),\n"
            "            _sr('d', 'skipped', 0.0),\n"
            "        ]\n"
            "        s = summarize_run(records)\n"
            "        assert s.get('total')   == 4, f\"total: {s.get('total')}\"\n"
            "        assert s.get('passed')  == 2, f\"passed: {s.get('passed')}\"\n"
            "        assert s.get('failed')  == 1, f\"failed: {s.get('failed')}\"\n"
            "        assert s.get('skipped') == 1, f\"skipped: {s.get('skipped')}\"\n"
            "        passed += 1; print('\\u2705 Check 3: mixed → correct counts (2/1/1)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: total_duration_s is correct sum (rounded)\n"
            "    try:\n"
            "        records = [_sr('a', 'ok', 0.1), _sr('b', 'ok', 0.25), _sr('c', 'skipped', 0.0)]\n"
            "        s = summarize_run(records)\n"
            "        assert isinstance(s.get('total_duration_s'), float), \\\n"
            "            f'total_duration_s should be float: {s.get(\"total_duration_s\")!r}'\n"
            "        assert abs(s['total_duration_s'] - 0.35) < 0.01, \\\n"
            "            f'total_duration_s wrong: {s[\"total_duration_s\"]}'\n"
            "        passed += 1; print(f'\\u2705 Check 4: total_duration_s={s[\"total_duration_s\"]}s correct')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: all_ok=False when any step is not 'ok'\n"
            "    try:\n"
            "        # Failure makes all_ok False\n"
            "        r1 = summarize_run([_sr('a', 'ok'), _sr('b', 'error')])\n"
            "        assert r1['all_ok'] is False, f'should be False with error: {r1[\"all_ok\"]}'\n"
            "        # Skipped also makes all_ok False\n"
            "        r2 = summarize_run([_sr('a', 'ok'), _sr('b', 'skipped')])\n"
            "        assert r2['all_ok'] is False, f'should be False with skipped: {r2[\"all_ok\"]}'\n"
            "        passed += 1; print('\\u2705 Check 5: all_ok=False with error or skipped step')\n"
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
            + SUMMARIZE_RUN_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 04 — ai_pipeline_summary
# ---------------------------------------------------------------------------

def ex04():
    global _cid; _cid = 300
    return [
        md(
            "# Day 030 — Exercise 4: ai_pipeline_summary\n\n"
            "**What you'll build:** `ai_pipeline_summary(step_results, model='llama3.2') -> str` — "
            "formats step results as a checkmark/cross text block and asks Ollama to summarise "
            "the pipeline run in 2–3 sentences.\n\n"
            "**Why it matters:** A pipeline monitor that shows raw JSON is hard to read. "
            "A natural-language summary — 'The pipeline completed successfully in 0.3s' or "
            "'Step process_content failed with a KeyError; downstream steps were skipped' — "
            "is immediately actionable for a human operator."
        ),
        code("import ollama"),
        md("## Provided: run_step, chain_steps, summarize_run"),
        code(RUN_STEP_IMPL + "\n\n\n" + CHAIN_STEPS_IMPL + "\n\n\n" + SUMMARIZE_RUN_IMPL),
        md("## Your Implementation"),
        code(
            "def ai_pipeline_summary(\n"
            "    step_results: list,\n"
            "    model: str = 'llama3.2',\n"
            ") -> str:\n"
            '    """\n'
            "    Return a 2–3 sentence natural-language summary of a pipeline run.\n\n"
            "    Args:\n"
            "        step_results: List of step result dicts from chain_steps.\n"
            "        model:        Ollama model name.\n\n"
            "    Returns:\n"
            "        A concise string describing what happened in the pipeline.\n"
            '    """\n'
            "    # TODO: summary = summarize_run(step_results)\n"
            "    # TODO: for each step: '  \\u2713 name (dur)' or '  \\u2717 name: error' or '  - name: skipped'\n"
            "    # TODO: run_text = f'{passed}/{total} steps passed, {dur}s total\\n' + '\\n'.join(lines)\n"
            "    # TODO: ollama.chat with system 'Summarise run in 2-3 sentences'\n"
            "    # TODO: return response['message']['content']\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    def _sr(name, status, dur=0.05, error=None):\n"
            "        return {'name': name, 'status': status, 'result': None,\n"
            "                'error': error, 'duration_s': dur}\n"
            "\n"
            "    ALL_OK   = [_sr('fetch', 'ok', 0.1), _sr('process', 'ok', 0.2), _sr('report', 'ok', 0.05)]\n"
            "    WITH_ERR = [_sr('fetch', 'ok', 0.1), _sr('process', 'error', 0.02, 'KeyError: rows'),\n"
            "                _sr('report', 'skipped', 0.0)]\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'ai_pipeline_summary' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: ai_pipeline_summary defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    ok_report = None\n"
            "\n"
            "    # Check 2: returns a string for all-ok input\n"
            "    try:\n"
            "        ok_report = ai_pipeline_summary(ALL_OK)\n"
            "        assert isinstance(ok_report, str), \\\n"
            "            f'expected str, got {type(ok_report)}'\n"
            "        passed += 1; print('\\u2705 Check 2: returns a string')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: non-empty summary\n"
            "    try:\n"
            "        assert ok_report is not None\n"
            "        assert len(ok_report.strip()) > 10, \\\n"
            "            f'summary too short: {ok_report!r}'\n"
            "        passed += 1; print(f'\\u2705 Check 3: summary is {len(ok_report)} chars')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: works with failed/skipped steps\n"
            "    try:\n"
            "        err_report = ai_pipeline_summary(WITH_ERR)\n"
            "        assert isinstance(err_report, str) and len(err_report) > 10\n"
            "        passed += 1; print('\\u2705 Check 4: works with error/skipped steps')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: single-step pipeline also works\n"
            "    try:\n"
            "        one = [_sr('solo', 'ok', 0.01)]\n"
            "        report = ai_pipeline_summary(one)\n"
            "        assert isinstance(report, str) and len(report) > 5\n"
            "        passed += 1; print('\\u2705 Check 5: single-step pipeline summary works')\n"
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
            + AI_PIPELINE_SUMMARY_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 05 — Pipeline class
# ---------------------------------------------------------------------------

def ex05():
    global _cid; _cid = 400
    return [
        md(
            "# Day 030 — Exercise 5: Pipeline class\n\n"
            "**What you'll build:** The `Pipeline` class — `add_step(name, fn)` registers steps, "
            "`run()` executes them with `chain_steps`, summarises with `summarize_run`, generates "
            "an AI report with `ai_pipeline_summary`, and returns a result dict with four keys: "
            "`name`, `steps`, `summary`, `report`.\n\n"
            "**Why it matters:** The class encapsulates the step registry and orchestration logic "
            "behind a clean API. Adding a new automation step is one `add_step` call — no "
            "changes to the runner, no changes to the summary logic."
        ),
        code("import ollama\nimport time"),
        md("## Provided: All Helper Functions"),
        code(ALL_IMPLS),
        md("## Your Implementation"),
        code(
            "class Pipeline:\n"
            "    def __init__(\n"
            "        self,\n"
            "        name: str = 'pipeline',\n"
            "        stop_on_error: bool = True,\n"
            "        model: str = 'llama3.2',\n"
            "    ):\n"
            "        # TODO: store name, stop_on_error, model\n"
            "        # TODO: self._steps = []\n"
            "        pass\n"
            "\n"
            "    def add_step(self, name: str, fn) -> 'Pipeline':\n"
            "        # TODO: append (name, fn) to self._steps\n"
            "        # TODO: return self  (enables fluent chaining)\n"
            "        pass\n"
            "\n"
            "    def run(self) -> dict:\n"
            "        # TODO: step_results = chain_steps(self._steps, stop_on_error=self.stop_on_error)\n"
            "        # TODO: summary = summarize_run(step_results)\n"
            "        # TODO: report  = ai_pipeline_summary(step_results, model=self.model)\n"
            "        # TODO: return {'name': self.name, 'steps': step_results,\n"
            "        #               'summary': summary, 'report': report}\n"
            "        pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: class and methods defined\n"
            "    try:\n"
            "        assert 'Pipeline' in globals()\n"
            "        for m in ('add_step', 'run'):\n"
            "            assert hasattr(Pipeline, m), f'Pipeline missing method: {m}'\n"
            "        passed += 1; print('\\u2705 Check 1: Pipeline class with add_step and run')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    p = None\n"
            "\n"
            "    # Check 2: add_step returns self (fluent chaining)\n"
            "    try:\n"
            "        p = Pipeline(name='test_pipe')\n"
            "        ret = p.add_step('step_a', lambda: 1)\n"
            "        assert ret is p, \\\n"
            "            f'add_step should return self, got {type(ret)}'\n"
            "        passed += 1; print('\\u2705 Check 2: add_step returns self')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: _steps contains the registered steps\n"
            "    try:\n"
            "        assert p is not None\n"
            "        p.add_step('step_b', lambda: 2)\n"
            "        assert hasattr(p, '_steps'), 'Pipeline missing _steps attribute'\n"
            "        assert len(p._steps) == 2, \\\n"
            "            f'expected 2 steps, got {len(p._steps)}'\n"
            "        passed += 1; print('\\u2705 Check 3: _steps has 2 entries after 2 add_step calls')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: run() returns dict with all four keys\n"
            "    try:\n"
            "        result = p.run()\n"
            "        assert isinstance(result, dict), \\\n"
            "            f'run() should return dict, got {type(result)}'\n"
            "        for k in ('name', 'steps', 'summary', 'report'):\n"
            "            assert k in result, f\"result missing key: '{k}'\"\n"
            "        passed += 1; print('\\u2705 Check 4: run() returns dict with name/steps/summary/report')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: summary.all_ok=True and name is preserved\n"
            "    try:\n"
            "        result = Pipeline(name='my_pipe').add_step('only', lambda: 42).run()\n"
            "        assert result['name'] == 'my_pipe', \\\n"
            "            f\"name wrong: {result['name']!r}\"\n"
            "        assert result['summary']['all_ok'] is True, \\\n"
            "            f\"all_ok wrong: {result['summary']['all_ok']}\"\n"
            "        assert len(result['steps']) == 1\n"
            "        assert isinstance(result['report'], str) and len(result['report']) > 5\n"
            "        passed += 1; print('\\u2705 Check 5: summary.all_ok=True; name and report correct')\n"
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
            + PIPELINE_IMPL + "\n"
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
            "# Day 030 Project: Multi-Step Automation Pipeline\n\n"
            "## What You're Building\n\n"
            "A `Pipeline` that orchestrates a realistic multi-step automation flow:\n"
            "1. **Fetch** — load or simulate source data\n"
            "2. **Process** — transform the data\n"
            "3. **Summarize** — generate an AI narrative of the data\n"
            "4. **Report** — write a simple text report\n\n"
            "The pipeline uses `chain_steps` to run steps in order, stops on the "
            "first failure, and produces a complete run record with an AI-generated "
            "summary via `ai_pipeline_summary`.\n\n"
            "## Project Requirements\n\n"
            "1. Build a `Pipeline` with at least 3 named steps\n"
            "2. Call `pipeline.run()` and store the result as `result`\n"
            "3. The pipeline should complete with `summary['all_ok'] == True`\n"
            "4. Verify with `_run_project_checks()`"
        ),
        code("import ollama\nimport time"),
        md("## Provided: All Helper Functions"),
        code("import ollama\nimport time\n\n\n" + ALL_IMPLS + "\n\n\n" + PIPELINE_IMPL),
        md(
            "## Your Pipeline\n\n"
            "Design a multi-step automation flow. Each step should be a zero-arg "
            "callable that returns its output. Use closures (inner functions or lambdas) "
            "to capture any data you need to pass between steps."
        ),
        code(
            "# Example multi-step pipeline — customise with your own steps\n"
            "\n"
            "# Step 1: Fetch data (simulate loading from a source)\n"
            "def fetch_data():\n"
            "    # Simulate fetching articles or records\n"
            "    return [\n"
            "        {'title': 'AI in 2026',     'words': 850},\n"
            "        {'title': 'Python tips',    'words': 420},\n"
            "        {'title': 'Automation now', 'words': 610},\n"
            "    ]\n"
            "\n"
            "# Step 2: Process data (filter, transform)\n"
            "_raw_data = None   # will be set by fetch_data\n"
            "def process_data():\n"
            "    # In a real pipeline, earlier results would be shared via a context dict\n"
            "    data = fetch_data()\n"
            "    return [r for r in data if r['words'] >= 500]\n"
            "\n"
            "# Step 3: Generate AI summary of the processed data\n"
            "def ai_summarize():\n"
            "    processed = process_data()\n"
            "    prompt = 'Summarise these articles in one sentence: ' + str(processed)\n"
            "    resp = ollama.chat(\n"
            "        model='llama3.2',\n"
            "        messages=[{'role': 'user', 'content': prompt}],\n"
            "    )\n"
            "    return resp['message']['content']\n"
            "\n"
            "# Build and run the pipeline\n"
            "pipeline = Pipeline(name='article_pipeline')\n"
            "pipeline.add_step('fetch',     fetch_data)\n"
            "pipeline.add_step('process',   process_data)\n"
            "pipeline.add_step('summarize', ai_summarize)\n"
            "\n"
            "result = pipeline.run()\n"
            "print(f\"Pipeline: {result['name']}\")\n"
            "print(f\"Outcome:  {result['summary']['passed']}/{result['summary']['total']} steps passed\")\n"
            "print(f\"All OK:   {result['summary']['all_ok']}\")\n"
            "print(f\"\\nAI Report:\\n{result['report']}\")"
        ),
        md("## Checks"),
        code(
            "def _run_project_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: Pipeline class exists with required methods\n"
            "    try:\n"
            "        assert 'Pipeline' in globals()\n"
            "        for m in ('add_step', 'run'):\n"
            "            assert hasattr(Pipeline, m), f'missing method: {m}'\n"
            "        passed += 1; print('\\u2705 Check 1: Pipeline class ready')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "\n"
            "    # Check 2: result dict exists with required keys\n"
            "    try:\n"
            "        assert 'result' in globals(), 'result not defined — call pipeline.run()'\n"
            "        for k in ('name', 'steps', 'summary', 'report'):\n"
            "            assert k in result, f\"result missing key: '{k}'\"\n"
            "        passed += 1; print('\\u2705 Check 2: result has all required keys')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: pipeline has at least 3 steps\n"
            "    try:\n"
            "        assert 'result' in globals()\n"
            "        assert len(result['steps']) >= 3, \\\n"
            "            f'pipeline should have >=3 steps, got {len(result[\"steps\"])}'\n"
            "        passed += 1; print(f'\\u2705 Check 3: {len(result[\"steps\"])} steps recorded')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: all steps passed\n"
            "    try:\n"
            "        assert 'result' in globals()\n"
            "        s = result['summary']\n"
            "        assert s['all_ok'] is True, \\\n"
            "            f\"all_ok is {s['all_ok']} — {s['failed']} step(s) failed\"\n"
            "        passed += 1; print('\\u2705 Check 4: all_ok=True — pipeline completed cleanly')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: AI report is a non-empty string\n"
            "    try:\n"
            "        assert 'result' in globals()\n"
            "        assert isinstance(result['report'], str) and len(result['report']) > 10, \\\n"
            "            f\"report should be a non-empty string: {result['report']!r}\"\n"
            "        passed += 1; print(f'\\u2705 Check 5: report is {len(result[\"report\"])} chars')\n"
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
            "- Add a `context: dict` to Pipeline that steps can read and write, "
            "so downstream steps can consume upstream results without re-running earlier steps\n"
            "- Add `dry_run()` — print what would happen without calling any fn\n"
            "- Add a `stop_on_error=False` pipeline with independent steps "
            "(e.g., send Slack notification AND write log file — run both even if one fails)\n"
            "- Wire in a real automation step from earlier days: "
            "scrape a URL (Day 23), parse the text (Day 9), "
            "generate a summary (Day 7), and write an XLSX report (Day 28)\n"
            "- Add a `timeout_s` parameter to run_step using `threading.Timer` "
            "to cancel steps that hang"
        ),
    ]


# ---------------------------------------------------------------------------
# Solution notebook (executed by gate)
# ---------------------------------------------------------------------------

def solution_nb():
    global _cid; _cid = 600

    imports = "import ollama\nimport time"

    all_code = imports + "\n\n\n" + ALL_IMPLS + "\n\n\n" + PIPELINE_IMPL

    return [
        md(
            "# Day 030 Project Solution — Workflow Orchestration\n\n"
            "A `Pipeline` that chains multiple automation steps, captures success and failure, "
            "and generates an AI-powered run report."
        ),
        code(all_code),
        md("## Action 1 — Run a Successful Three-Step Pipeline"),
        code(
            "p = Pipeline(name='daily_digest', stop_on_error=True)\n"
            "p.add_step('fetch_articles',   lambda: {'articles': 12, 'sources': 3})\n"
            "p.add_step('process_content',  lambda: 'Processed 12 articles into 8 summaries')\n"
            "p.add_step('generate_report',  lambda: '/tmp/day030_report.txt')\n"
            "\n"
            "result = p.run()\n"
            "print(f\"Pipeline : {result['name']}\")\n"
            "print(f\"Total    : {result['summary']['total']} steps\")\n"
            "print(f\"Passed   : {result['summary']['passed']}\")\n"
            "print(f\"All OK   : {result['summary']['all_ok']}\")\n"
            "print(f\"Duration : {result['summary']['total_duration_s']}s\")"
        ),
        md("## Action 2 — Demonstrate Stop-on-Error with a Failing Step"),
        code(
            "def _fail_step():\n"
            "    raise ValueError('simulated network error')\n"
            "\n"
            "p2 = Pipeline(name='with_failure', stop_on_error=True)\n"
            "p2.add_step('prepare',   lambda: 'ready')\n"
            "p2.add_step('fetch_remote', _fail_step)\n"
            "p2.add_step('post_process', lambda: 'this is skipped')\n"
            "\n"
            "result2 = p2.run()\n"
            "for s in result2['steps']:\n"
            "    print(f\"  {s['status']:8} {s['name']}\"\n"
            "          + (f\" — {s['error']}\" if s['error'] else ''))\n"
            "print(f\"\\nFailed : {result2['summary']['failed']}\")\n"
            "print(f\"Skipped: {result2['summary']['skipped']}\")\n"
            "print(f\"All OK : {result2['summary']['all_ok']}\")"
        ),
        md("## Action 3 — AI Run Report and Verify"),
        code(
            "# Re-use the successful pipeline result from Action 1\n"
            "print('AI Run Report:')\n"
            "print(result['report'])\n"
            "\n"
            "# Confirm structure\n"
            "assert result['summary']['all_ok'] is True\n"
            "assert len(result['steps']) == 3\n"
            "assert isinstance(result['report'], str) and len(result['report']) > 10\n"
            "\n"
            "print('\\nOrchestration complete!')"
        ),
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Generating Day 030 notebooks...")
    ex_dir = DAY_DIR / "exercises"
    proj_dir = DAY_DIR / "project"
    sol_dir = proj_dir / "solution"
    for d in (ex_dir, proj_dir, sol_dir):
        d.mkdir(parents=True, exist_ok=True)

    write_nb(ex_dir / "exercise_01.ipynb", ex01())
    write_nb(ex_dir / "exercise_02.ipynb", ex02())
    write_nb(ex_dir / "exercise_03.ipynb", ex03())
    write_nb(ex_dir / "exercise_04.ipynb", ex04())
    write_nb(ex_dir / "exercise_05.ipynb", ex05())
    write_nb(proj_dir / "project.ipynb", project_nb())
    write_nb(sol_dir / "solution.ipynb", solution_nb())
    print("Done.")


if __name__ == "__main__":
    main()
