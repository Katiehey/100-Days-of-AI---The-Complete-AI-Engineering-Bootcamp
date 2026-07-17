#!/usr/bin/env python3
"""Generate all Day 027 notebooks: exercises 1-5, project, solution."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAY_DIR = ROOT / "02_automation" / "day_027"

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

BUILD_JOB_IMPL = """\
def build_job(
    name: str,
    fn,
    interval_minutes: int,
    enabled: bool = True,
) -> dict:
    if interval_minutes <= 0:
        raise ValueError(f"interval_minutes must be > 0, got {interval_minutes}")
    return {
        "name": name,
        "fn_name": fn.__name__,
        "interval_minutes": interval_minutes,
        "enabled": enabled,
    }"""

IS_DUE_IMPL = """\
def is_due(
    last_run_iso: str | None,
    interval_minutes: int,
    now: datetime | None = None,
) -> bool:
    if last_run_iso is None:
        return True
    if now is None:
        now = datetime.now()
    last_run = datetime.fromisoformat(last_run_iso)
    elapsed_seconds = (now - last_run).total_seconds()
    return elapsed_seconds >= interval_minutes * 60"""

LOG_FNS_IMPL = """\
def save_run_log(path: str, records: list[dict]) -> None:
    Path(path).write_text(json.dumps(records, indent=2), encoding="utf-8")


def load_run_log(path: str) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8"))"""

RECORD_RUN_IMPL = """\
def record_run(
    log: list[dict],
    name: str,
    result: str,
    status: str = "ok",
) -> list[dict]:
    new_record = {
        "name": name,
        "ran_at": datetime.now().isoformat(),
        "result": result,
        "status": status,
    }
    return log + [new_record]"""

AI_BRIEFING_IMPL = """\
def ai_daily_briefing(topics: list[str], model: str = "llama3.2") -> str:
    topics_str = "\\n".join(f"- {t}" for t in topics)
    response = ollama.chat(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a professional daily briefing assistant. "
                    "Write a concise, structured briefing covering the given topics. "
                    "Use clear section headers (## Topic). Keep it under 300 words."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Generate a daily briefing covering these topics:\\n{topics_str}\\n\\n"
                    "Today's briefing:"
                ),
            },
        ],
    )
    return response["message"]["content"]"""

SCHEDULER_IMPL = """\
class DailyBriefingScheduler:
    def __init__(self, log_path: str = "/tmp/day027_run_log.json"):
        self.log_path = log_path
        self.jobs: list[dict] = []

    def add_job(self, name: str, fn, interval_minutes: int) -> None:
        self.jobs.append(build_job(name, fn, interval_minutes))

    def _last_run(self, name: str) -> str | None:
        log = load_run_log(self.log_path)
        runs = [r for r in log if r["name"] == name]
        return runs[-1]["ran_at"] if runs else None

    def due_jobs(self, now: datetime | None = None) -> list[str]:
        return [
            j["name"]
            for j in self.jobs
            if j["enabled"] and is_due(self._last_run(j["name"]), j["interval_minutes"], now)
        ]

    def save_briefing(self, content: str, output_dir: str) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        path = str(Path(output_dir) / f"briefing_{today}.txt")
        Path(path).write_text(content, encoding="utf-8")
        return path

    def run(
        self,
        topics: list[str],
        output_dir: str,
        model: str = "llama3.2",
        now: datetime | None = None,
    ) -> dict:
        due = self.due_jobs(now)
        content = ai_daily_briefing(topics, model=model)
        path = self.save_briefing(content, output_dir)
        log = load_run_log(self.log_path)
        for name in due:
            log = record_run(log, name, f"briefing saved to {path}")
        save_run_log(self.log_path, log)
        return {"content": content, "path": path, "ran_jobs": due}\
"""

ALL_IMPLS = "\n\n\n".join([
    BUILD_JOB_IMPL, IS_DUE_IMPL, LOG_FNS_IMPL, RECORD_RUN_IMPL, AI_BRIEFING_IMPL,
])


# ---------------------------------------------------------------------------
# Exercise 01 — build_job
# ---------------------------------------------------------------------------

def ex01():
    global _cid; _cid = 0
    return [
        md(
            "# Day 027 — Exercise 1: build_job\n\n"
            "**What you'll build:** `build_job(name, fn, interval_minutes, enabled=True)` — "
            "creates a serialisable job configuration dict.\n\n"
            "**Why it matters:** Schedulers need to know *what* to run, *how often*, and "
            "*whether* it is active. Encoding this as a plain dict (not a class with "
            "a live callable reference) makes the config JSON-serialisable — you can save "
            "it to a file, send it over a network, or reload it across process restarts. "
            "`fn.__name__` records which function to call without holding a non-picklable "
            "reference to the function object."
        ),
        code("from datetime import datetime"),
        md("## Your Implementation"),
        code(
            "def build_job(\n"
            "    name: str,\n"
            "    fn,\n"
            "    interval_minutes: int,\n"
            "    enabled: bool = True,\n"
            ") -> dict:\n"
            '    """\n'
            "    Build a serialisable job configuration dict.\n\n"
            "    Args:\n"
            "        name:             Human-readable job name.\n"
            "        fn:               The callable this job will invoke.\n"
            "        interval_minutes: How often the job should run (must be > 0).\n"
            "        enabled:          Whether the job is active (default True).\n\n"
            "    Returns:\n"
            "        dict with keys: name, fn_name, interval_minutes, enabled.\n\n"
            "    Raises:\n"
            "        ValueError: if interval_minutes <= 0.\n"
            '    """\n'
            "    # TODO: if interval_minutes <= 0: raise ValueError(...)\n"
            "    # TODO: return {'name': name, 'fn_name': fn.__name__,\n"
            "    #               'interval_minutes': interval_minutes, 'enabled': enabled}\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _sample_task():\n"
            "    pass\n"
            "\n"
            "\n"
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'build_job' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: build_job defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    job = None\n"
            "\n"
            "    # Check 2: returns a dict\n"
            "    try:\n"
            "        job = build_job('briefing', _sample_task, 60)\n"
            "        assert isinstance(job, dict), f'expected dict, got {type(job)}'\n"
            "        passed += 1; print('\\u2705 Check 2: returns a dict')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: name and fn_name correct\n"
            "    try:\n"
            "        assert job is not None, 'job is None (Check 2 failed)'\n"
            "        assert job['name'] == 'briefing', f\"name wrong: {job['name']!r}\"\n"
            "        assert job['fn_name'] == '_sample_task', \\\n"
            "            f\"fn_name should be '_sample_task', got {job['fn_name']!r}\"\n"
            "        passed += 1; print(f\"\\u2705 Check 3: name={job['name']!r} fn_name={job['fn_name']!r}\")\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: interval_minutes and enabled defaults\n"
            "    try:\n"
            "        assert job is not None, 'job is None'\n"
            "        assert job['interval_minutes'] == 60, \\\n"
            "            f\"interval_minutes wrong: {job['interval_minutes']!r}\"\n"
            "        assert job['enabled'] is True, \\\n"
            "            f\"enabled should default to True, got {job['enabled']!r}\"\n"
            "        passed += 1; print('\\u2705 Check 4: interval_minutes=60, enabled=True')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: raises ValueError on invalid interval\n"
            "    try:\n"
            "        raised = False\n"
            "        try:\n"
            "            build_job('bad', _sample_task, 0)\n"
            "        except ValueError:\n"
            "            raised = True\n"
            "        assert raised, 'should raise ValueError for interval_minutes=0'\n"
            "        passed += 1; print('\\u2705 Check 5: raises ValueError for interval_minutes <= 0')\n"
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
            + BUILD_JOB_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 02 — is_due
# ---------------------------------------------------------------------------

def ex02():
    global _cid; _cid = 100
    return [
        md(
            "# Day 027 — Exercise 2: is_due\n\n"
            "**What you'll build:** `is_due(last_run_iso, interval_minutes, now=None) -> bool` — "
            "the core of interval-based scheduling. Returns True if enough time has elapsed "
            "since the last run (or if the job has never run).\n\n"
            "**Why it matters:** This is the heart of idempotent scheduling. Before running "
            "any job, a well-behaved scheduler asks 'is it time yet?' rather than blindly "
            "executing. Storing `last_run` as an ISO string makes it JSON-serialisable — "
            "the scheduler can persist it across restarts. The `now` parameter makes "
            "the function testable without depending on the real clock."
        ),
        code("from datetime import datetime"),
        md("## Your Implementation"),
        code(
            "def is_due(\n"
            "    last_run_iso: str | None,\n"
            "    interval_minutes: int,\n"
            "    now: datetime | None = None,\n"
            ") -> bool:\n"
            '    """\n'
            "    Check whether a job is due to run.\n\n"
            "    Args:\n"
            "        last_run_iso:     ISO-format datetime string of last run, or None\n"
            "                          if the job has never run.\n"
            "        interval_minutes: How often the job should run, in minutes.\n"
            "        now:              Current datetime (defaults to datetime.now()).\n\n"
            "    Returns:\n"
            "        True if never ran, or if elapsed time >= interval_minutes * 60.\n"
            '    """\n'
            "    # TODO: if last_run_iso is None: return True\n"
            "    # TODO: if now is None: now = datetime.now()\n"
            "    # TODO: last_run = datetime.fromisoformat(last_run_iso)\n"
            "    # TODO: elapsed_seconds = (now - last_run).total_seconds()\n"
            "    # TODO: return elapsed_seconds >= interval_minutes * 60\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Fixed reference time for deterministic tests\n"
            "    NOW = datetime(2026, 7, 17, 9, 0, 0)\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'is_due' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: is_due defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    # Check 2: None last_run → always True (never ran)\n"
            "    try:\n"
            "        result = is_due(None, 60, now=NOW)\n"
            "        assert result is True, f'expected True for None last_run, got {result}'\n"
            "        passed += 1; print('\\u2705 Check 2: None last_run → True (never ran)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: elapsed < interval → False (not yet due)\n"
            "    try:\n"
            "        last_30_min_ago = datetime(2026, 7, 17, 8, 30, 0).isoformat()\n"
            "        result = is_due(last_30_min_ago, 60, now=NOW)\n"
            "        assert result is False, \\\n"
            "            f'30 min ago with 60-min interval should be False, got {result}'\n"
            "        passed += 1; print('\\u2705 Check 3: 30 min elapsed < 60 min interval → False')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: elapsed >= interval → True (overdue)\n"
            "    try:\n"
            "        last_2h_ago = datetime(2026, 7, 17, 7, 0, 0).isoformat()\n"
            "        result = is_due(last_2h_ago, 60, now=NOW)\n"
            "        assert result is True, \\\n"
            "            f'2 hours ago with 60-min interval should be True, got {result}'\n"
            "        passed += 1; print('\\u2705 Check 4: 120 min elapsed >= 60 min interval → True')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: exactly at interval boundary → True\n"
            "    try:\n"
            "        last_exactly_1h = datetime(2026, 7, 17, 8, 0, 0).isoformat()\n"
            "        result = is_due(last_exactly_1h, 60, now=NOW)\n"
            "        assert result is True, \\\n"
            "            f'exactly 60 min ago with 60-min interval should be True, got {result}'\n"
            "        passed += 1; print('\\u2705 Check 5: exactly at interval boundary → True')\n"
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
            + IS_DUE_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 03 — save_run_log / load_run_log
# ---------------------------------------------------------------------------

def ex03():
    global _cid; _cid = 200
    return [
        md(
            "# Day 027 — Exercise 3: save_run_log / load_run_log\n\n"
            "**What you'll build:** `save_run_log(path, records)` and "
            "`load_run_log(path)` — JSON-based persistence for the job run history.\n\n"
            "**Why it matters:** A scheduler that does not persist its run history "
            "re-runs every job on every restart — breaking idempotency. Saving to a "
            "JSON file is the simplest durable store: human-readable, no database "
            "needed, and loadable across process restarts. "
            "`load_run_log` returns `[]` for missing files so first-time use works "
            "without creating an empty file manually."
        ),
        code("import json\nfrom pathlib import Path"),
        md("## Your Implementation"),
        code(
            "def save_run_log(path: str, records: list[dict]) -> None:\n"
            '    """\n'
            "    Write the run log to a JSON file.\n\n"
            "    Args:\n"
            "        path:    File path to write (creates or overwrites).\n"
            "        records: List of run record dicts.\n"
            '    """\n'
            "    # TODO: Path(path).write_text(json.dumps(records, indent=2), encoding='utf-8')\n"
            "    pass\n"
            "\n"
            "\n"
            "def load_run_log(path: str) -> list[dict]:\n"
            '    """\n'
            "    Load the run log from a JSON file.\n\n"
            "    Args:\n"
            "        path: File path to read.\n\n"
            "    Returns:\n"
            "        List of run record dicts. Empty list if file does not exist.\n"
            '    """\n'
            "    # TODO: p = Path(path)\n"
            "    # TODO: if not p.exists(): return []\n"
            "    # TODO: return json.loads(p.read_text(encoding='utf-8'))\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "import tempfile, os\n"
            "\n"
            "\n"
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    tmp = tempfile.mktemp(suffix='.json')\n"
            "    RECORDS = [\n"
            "        {'name': 'briefing', 'ran_at': '2026-07-17T08:00:00', 'result': 'ok', 'status': 'ok'},\n"
            "        {'name': 'briefing', 'ran_at': '2026-07-17T09:00:00', 'result': 'ok', 'status': 'ok'},\n"
            "    ]\n"
            "\n"
            "    # Check 1: both functions defined\n"
            "    try:\n"
            "        assert 'save_run_log' in globals(), 'save_run_log not defined'\n"
            "        assert 'load_run_log' in globals(), 'load_run_log not defined'\n"
            "        passed += 1; print('\\u2705 Check 1: save_run_log and load_run_log defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    # Check 2: load_run_log returns [] for missing file\n"
            "    try:\n"
            "        missing = tempfile.mktemp(suffix='.json')\n"
            "        result = load_run_log(missing)\n"
            "        assert result == [], f'expected [] for missing file, got {result}'\n"
            "        passed += 1; print('\\u2705 Check 2: missing file → []')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: round-trip save then load\n"
            "    loaded = None\n"
            "    try:\n"
            "        save_run_log(tmp, RECORDS)\n"
            "        loaded = load_run_log(tmp)\n"
            "        assert loaded == RECORDS, f'round-trip failed: {loaded}'\n"
            "        passed += 1; print(f'\\u2705 Check 3: round-trip: {len(loaded)} records')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: save overwrites (not appends)\n"
            "    try:\n"
            "        single = [{'name': 'x', 'ran_at': '2026-07-17T10:00:00', 'result': 'y', 'status': 'ok'}]\n"
            "        save_run_log(tmp, single)\n"
            "        reloaded = load_run_log(tmp)\n"
            "        assert len(reloaded) == 1, \\\n"
            "            f'expected 1 record after overwrite, got {len(reloaded)}'\n"
            "        passed += 1; print('\\u2705 Check 4: save overwrites (not appends)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: empty list round-trips\n"
            "    try:\n"
            "        save_run_log(tmp, [])\n"
            "        empty = load_run_log(tmp)\n"
            "        assert empty == [], f'expected [] for empty save, got {empty}'\n"
            "        passed += 1; print('\\u2705 Check 5: empty list round-trips correctly')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "\n"
            "    try:\n"
            "        os.unlink(tmp)\n"
            "    except Exception:\n"
            "        pass\n"
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
            + LOG_FNS_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 04 — record_run
# ---------------------------------------------------------------------------

def ex04():
    global _cid; _cid = 300
    return [
        md(
            "# Day 027 — Exercise 4: record_run\n\n"
            "**What you'll build:** `record_run(log, name, result, status='ok')` — "
            "appends a new run record to the log and returns the new list.\n\n"
            "**Why it matters:** `record_run` is a *pure* function — it never mutates "
            "its input. This makes it safe to call in any order and easy to test "
            "(no side effects). The caller decides when to persist the returned list "
            "with `save_run_log`. The ISO timestamp lets `is_due` (Exercise 2) calculate "
            "elapsed time when the job is checked again."
        ),
        code("from datetime import datetime"),
        md("## Your Implementation"),
        code(
            "def record_run(\n"
            "    log: list[dict],\n"
            "    name: str,\n"
            "    result: str,\n"
            "    status: str = 'ok',\n"
            ") -> list[dict]:\n"
            '    """\n'
            "    Append a new run record to the log (pure — returns new list).\n\n"
            "    Args:\n"
            "        log:    Existing list of run records.\n"
            "        name:   Job name.\n"
            "        result: Human-readable result string.\n"
            "        status: 'ok' or 'error'.\n\n"
            "    Returns:\n"
            "        New list with one extra record appended. Original log unchanged.\n"
            '    """\n'
            "    # Record schema: {name, ran_at (ISO), result, status}\n"
            "    # TODO: new_record = {'name': name, 'ran_at': datetime.now().isoformat(),\n"
            "    #                     'result': result, 'status': status}\n"
            "    # TODO: return log + [new_record]\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    EXISTING = [\n"
            "        {'name': 'briefing', 'ran_at': '2026-07-17T08:00:00',\n"
            "         'result': 'done', 'status': 'ok'},\n"
            "    ]\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'record_run' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: record_run defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    new_log = None\n"
            "\n"
            "    # Check 2: returns a list with one more item\n"
            "    try:\n"
            "        new_log = record_run(EXISTING, 'briefing', 'saved to /tmp/b.txt')\n"
            "        assert isinstance(new_log, list), f'expected list, got {type(new_log)}'\n"
            "        assert len(new_log) == 2, f'expected 2 items, got {len(new_log)}'\n"
            "        passed += 1; print(f'\\u2705 Check 2: returned list has {len(new_log)} items')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: new record has correct name and result\n"
            "    try:\n"
            "        assert new_log is not None, 'new_log is None (Check 2 failed)'\n"
            "        rec = new_log[-1]\n"
            "        assert rec['name'] == 'briefing', f\"name wrong: {rec['name']!r}\"\n"
            "        assert rec['result'] == 'saved to /tmp/b.txt', \\\n"
            "            f\"result wrong: {rec['result']!r}\"\n"
            "        passed += 1; print(f\"\\u2705 Check 3: name and result correct\")\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: new record has ran_at (ISO) and default status='ok'\n"
            "    try:\n"
            "        assert new_log is not None, 'new_log is None'\n"
            "        rec = new_log[-1]\n"
            "        assert 'ran_at' in rec, f\"'ran_at' missing from record: {rec}\"\n"
            "        datetime.fromisoformat(rec['ran_at'])  # must be valid ISO\n"
            "        assert rec['status'] == 'ok', f\"status should default to 'ok': {rec['status']!r}\"\n"
            "        passed += 1; print(f\"\\u2705 Check 4: ran_at is valid ISO, status='ok'\")\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: original log is not mutated (pure function)\n"
            "    try:\n"
            "        assert len(EXISTING) == 1, \\\n"
            "            f'original log was mutated — expected 1 item, got {len(EXISTING)}'\n"
            "        passed += 1; print('\\u2705 Check 5: original log not mutated (pure function)')\n"
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
            + RECORD_RUN_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 05 — ai_daily_briefing
# ---------------------------------------------------------------------------

def ex05():
    global _cid; _cid = 400
    return [
        md(
            "# Day 027 — Exercise 5: ai_daily_briefing\n\n"
            "**What you'll build:** `ai_daily_briefing(topics, model='llama3.2') -> str` — "
            "the AI step of the pipeline. Takes a list of topic strings and returns a "
            "structured briefing draft.\n\n"
            "**Why it matters:** This is the payload that makes the scheduler valuable. "
            "The system prompt establishes the briefing persona and format constraint "
            "(section headers, under 300 words). The topics list is the human-in-the-loop "
            "control: the scheduler runs automatically, but the owner chooses which "
            "topics matter."
        ),
        code("import ollama"),
        md("## Your Implementation"),
        code(
            "def ai_daily_briefing(topics: list[str], model: str = 'llama3.2') -> str:\n"
            '    """\n'
            "    Generate a structured daily briefing from a list of topics.\n\n"
            "    Args:\n"
            "        topics: List of topic strings to cover in the briefing.\n"
            "        model:  Ollama model name.\n\n"
            "    Returns:\n"
            "        Briefing text with section headers, under 300 words.\n"
            '    """\n'
            "    # TODO: topics_str = \"\\n\".join(f\"- {t}\" for t in topics)\n"
            "    # TODO: system: 'professional briefing assistant; headers; < 300 words'\n"
            "    # TODO: user: list the topics and ask for today's briefing\n"
            "    # TODO: return response['message']['content']\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    TOPICS = ['AI Engineering progress', 'Project status']\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'ai_daily_briefing' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: ai_daily_briefing defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    result = None\n"
            "\n"
            "    # Check 2: returns a string (1 LLM call)\n"
            "    try:\n"
            "        result = ai_daily_briefing(TOPICS)\n"
            "        assert isinstance(result, str), f'expected str, got {type(result)}'\n"
            "        passed += 1; print('\\u2705 Check 2: returns a string')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: result is non-empty\n"
            "    try:\n"
            "        assert result is not None, 'result is None (Check 2 failed)'\n"
            "        assert len(result.strip()) > 20, \\\n"
            "            f'briefing too short ({len(result)} chars): {result!r}'\n"
            "        passed += 1; print(f'\\u2705 Check 3: briefing is {len(result)} chars')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: single-topic briefing also works\n"
            "    try:\n"
            "        single = ai_daily_briefing(['Learning update'])\n"
            "        assert isinstance(single, str) and len(single) > 10\n"
            "        passed += 1; print('\\u2705 Check 4: works with single topic')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: result differs from a second call topic (LLM is not static)\n"
            "    try:\n"
            "        assert result is not None, 'result is None'\n"
            "        # Topics are in the prompt → result should reference them\n"
            "        # We just verify the function accepts the list form\n"
            "        multi = ai_daily_briefing(['Goal 1', 'Goal 2', 'Goal 3'])\n"
            "        assert isinstance(multi, str) and len(multi) > 10\n"
            "        passed += 1; print('\\u2705 Check 5: works with 3-topic list')\n"
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
            + AI_BRIEFING_IMPL + "\n"
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
            "# Day 027 Project: DailyBriefingScheduler\n\n"
            "## What You're Building\n\n"
            "A `DailyBriefingScheduler` class that:\n"
            "1. Holds a list of job configs (added via `add_job`)\n"
            "2. Checks which jobs are due using `is_due` + a persisted run log\n"
            "3. Generates an AI briefing for due jobs\n"
            "4. Saves the briefing to a file and updates the run log\n\n"
            "This extends Day 1's AI Briefing Generator with automated scheduling "
            "and idempotency.\n\n"
            "## Project Requirements\n\n"
            "1. Implement `DailyBriefingScheduler` with:\n"
            "   - `add_job(name, fn, interval_minutes)` — add a job config\n"
            "   - `due_jobs(now=None) -> list[str]` — names of due jobs\n"
            "   - `save_briefing(content, output_dir) -> str` — write to dated file\n"
            "   - `run(topics, output_dir, model, now) -> dict` — full pipeline\n"
            "2. Run `scheduler.run(TOPICS, '/tmp')` and store as `result`\n"
            "3. Verify with `_run_project_checks()`"
        ),
        code(
            "import json, os, tempfile\n"
            "from datetime import datetime\n"
            "from pathlib import Path\n"
            "import ollama"
        ),
        md("## Provided: All Helper Functions"),
        code(ALL_IMPLS),
        md(
            "## Your Implementation\n\n"
            "Implement `DailyBriefingScheduler` by wiring the helper functions."
        ),
        code(
            "class DailyBriefingScheduler:\n"
            "    def __init__(self, log_path: str = '/tmp/day027_run_log.json'):\n"
            "        self.log_path = log_path\n"
            "        self.jobs: list[dict] = []\n"
            "\n"
            "    def add_job(self, name: str, fn, interval_minutes: int) -> None:\n"
            "        # TODO: self.jobs.append(build_job(name, fn, interval_minutes))\n"
            "        pass\n"
            "\n"
            "    def _last_run(self, name: str) -> str | None:\n"
            "        # TODO: load_run_log; filter by name; return last ran_at or None\n"
            "        pass\n"
            "\n"
            "    def due_jobs(self, now: datetime | None = None) -> list[str]:\n"
            "        # TODO: [j['name'] for j in self.jobs if j['enabled'] and\n"
            "        #        is_due(self._last_run(j['name']), j['interval_minutes'], now)]\n"
            "        pass\n"
            "\n"
            "    def save_briefing(self, content: str, output_dir: str) -> str:\n"
            "        # TODO: today = datetime.now().strftime('%Y-%m-%d')\n"
            "        # TODO: path = str(Path(output_dir) / f'briefing_{today}.txt')\n"
            "        # TODO: Path(path).write_text(content, encoding='utf-8')\n"
            "        # TODO: return path\n"
            "        pass\n"
            "\n"
            "    def run(\n"
            "        self, topics: list[str], output_dir: str,\n"
            "        model: str = 'llama3.2', now: datetime | None = None,\n"
            "    ) -> dict:\n"
            "        # TODO: due = self.due_jobs(now)\n"
            "        # TODO: content = ai_daily_briefing(topics, model=model)\n"
            "        # TODO: path = self.save_briefing(content, output_dir)\n"
            "        # TODO: log = load_run_log(self.log_path)\n"
            "        # TODO: for name in due: log = record_run(log, name, f'saved to {path}')\n"
            "        # TODO: save_run_log(self.log_path, log)\n"
            "        # TODO: return {'content': content, 'path': path, 'ran_jobs': due}\n"
            "        pass"
        ),
        md("## Topics and Run"),
        code(
            "TOPICS = [\n"
            "    'AI Engineering learning progress',\n"
            "    'Project status update',\n"
            "    'Today\\'s priorities',\n"
            "]\n"
        ),
        code(
            "# def my_briefing_task(): pass  # placeholder callable\n"
            "# scheduler = DailyBriefingScheduler()\n"
            "# scheduler.add_job('daily_briefing', my_briefing_task, interval_minutes=1440)\n"
            "# result = scheduler.run(TOPICS, '/tmp')\n"
            "# print(f\"Briefing saved to: {result['path']}\")\n"
            "# print(f\"Ran jobs: {result['ran_jobs']}\")"
        ),
        md(
            "## Plug into APScheduler (Optional Extension)\n\n"
            "Once `DailyBriefingScheduler.run` works, you can wrap it in APScheduler "
            "to run automatically:\n\n"
            "```python\n"
            "from apscheduler.schedulers.blocking import BlockingScheduler\n\n"
            "aps = BlockingScheduler()\n\n"
            "@aps.scheduled_job('cron', hour=7, minute=30)\n"
            "def morning_briefing():\n"
            "    result = scheduler.run(TOPICS, '/tmp')\n"
            "    print(f\"Briefing saved: {result['path']}\")\n\n"
            "# aps.start()  # blocks until stopped; run in a terminal, not a notebook\n"
            "```\n\n"
            "Or interval-based:\n\n"
            "```python\n"
            "@aps.scheduled_job('interval', hours=1)\n"
            "def hourly_check():\n"
            "    ...\n"
            "```\n"
        ),
        md("## Checks"),
        code(
            "def _run_project_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: DailyBriefingScheduler has all required methods\n"
            "    try:\n"
            "        assert 'DailyBriefingScheduler' in globals()\n"
            "        for m in ('add_job', 'due_jobs', 'save_briefing', 'run'):\n"
            "            assert hasattr(DailyBriefingScheduler, m), \\\n"
            "                f'DailyBriefingScheduler missing: {m}'\n"
            "        passed += 1; print('\\u2705 Check 1: all methods present')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "\n"
            "    # Check 2: scheduler is an instance\n"
            "    try:\n"
            "        assert 'scheduler' in globals()\n"
            "        assert isinstance(scheduler, DailyBriefingScheduler)\n"
            "        passed += 1; print('\\u2705 Check 2: scheduler is DailyBriefingScheduler')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: result dict has required keys\n"
            "    try:\n"
            "        assert 'result' in globals()\n"
            "        for k in ('content', 'path', 'ran_jobs'):\n"
            "            assert k in result, f\"result missing '{k}': {list(result)}\"\n"
            "        passed += 1; print('\\u2705 Check 3: result has content/path/ran_jobs')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: briefing file exists\n"
            "    try:\n"
            "        assert 'result' in globals()\n"
            "        path = result.get('path', '')\n"
            "        assert os.path.exists(path), f'briefing file not found: {path}'\n"
            "        size = os.path.getsize(path)\n"
            "        assert size > 20, f'briefing file too small ({size} bytes)'\n"
            "        passed += 1; print(f'\\u2705 Check 4: briefing file exists ({size} bytes)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: briefing content is non-empty string\n"
            "    try:\n"
            "        assert 'result' in globals()\n"
            "        content = result.get('content', '')\n"
            "        assert isinstance(content, str) and len(content) > 20, \\\n"
            "            f'content should be non-empty str: {content!r}'\n"
            "        passed += 1; print(f'\\u2705 Check 5: briefing is {len(content)} chars')\n"
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
            "- Add a `disable_job(name)` method that sets `enabled=False` for a named job\n"
            "- Add a `status()` method that returns a dict of `{job_name: last_ran, is_due}` "
            "for all jobs\n"
            "- Persist jobs to a JSON config file (separate from the run log) so the "
            "scheduler reloads its job list on restart\n"
            "- Add an `error_handler(fn)` callback: if `ai_daily_briefing` raises, call "
            "the handler and record `status='error'` in the run log\n"
            "- Wire it to APScheduler's cron trigger: fire at 07:30 every weekday\n"
            "- Add an `only_weekdays` flag to `build_job` and check it in `due_jobs`"
        ),
    ]


# ---------------------------------------------------------------------------
# Solution notebook (executed by gate)
# ---------------------------------------------------------------------------

def solution_nb():
    global _cid; _cid = 600

    imports = (
        "import json, os, tempfile\n"
        "from datetime import datetime\n"
        "from pathlib import Path\n"
        "import ollama"
    )

    all_fns = imports + "\n\n\n" + ALL_IMPLS + "\n\n\n" + SCHEDULER_IMPL

    return [
        md(
            "# Day 027 Project Solution — DailyBriefingScheduler\n\n"
            "A `DailyBriefingScheduler` that generates AI briefings on an interval "
            "schedule with idempotent run tracking."
        ),
        code(all_fns),
        md("## Action 1 — Set Up Scheduler and Jobs"),
        code(
            "def _briefing_fn(): pass  # placeholder callable for job config\n"
            "\n"
            "scheduler = DailyBriefingScheduler(\n"
            "    log_path=os.path.join(tempfile.gettempdir(), 'day027_run_log.json'),\n"
            ")\n"
            "scheduler.add_job('daily_briefing', _briefing_fn, interval_minutes=1440)\n"
            "print(f'Jobs registered: {[j[\"name\"] for j in scheduler.jobs]}')\n"
            "print(f'Due jobs (never ran before): {scheduler.due_jobs()}')"
        ),
        md("## Action 2 — Run the Briefing Pipeline"),
        code(
            "TOPICS = [\n"
            "    'AI Engineering learning progress',\n"
            "    'Project status update',\n"
            "]\n"
            "\n"
            "result = scheduler.run(TOPICS, tempfile.gettempdir())\n"
            "print(f\"Briefing saved: {result['path']}\")\n"
            "print(f\"Jobs that ran:  {result['ran_jobs']}\")"
        ),
        md("## Action 3 — Verify Output and Run Log"),
        code(
            "# Preview the briefing\n"
            "print('Briefing preview (first 200 chars):')\n"
            "print(result['content'][:200])\n"
            "\n"
            "# Verify run log was updated\n"
            "log = load_run_log(scheduler.log_path)\n"
            "print(f'\\nRun log has {len(log)} record(s)')\n"
            "if log:\n"
            "    last = log[-1]\n"
            "    print(f\"Last entry: name={last['name']!r} status={last['status']!r}\")\n"
            "\n"
            "# Idempotency check: run again — same job should NOT be due\n"
            "still_due = scheduler.due_jobs()\n"
            "print(f'\\nDue jobs after first run: {still_due} (should be [])')\n"
            "print('\\nScheduling complete!')"
        ),
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Generating Day 027 notebooks...")
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
