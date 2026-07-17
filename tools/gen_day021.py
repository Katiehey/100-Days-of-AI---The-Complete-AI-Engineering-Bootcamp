#!/usr/bin/env python3
"""Generate all Day 021 notebooks: exercises 1-5, project, solution."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAY_DIR = ROOT / "02_automation" / "day_021"

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
# Solution implementations (no imports — rely on each notebook's imports cell)
# ---------------------------------------------------------------------------

SCAN_DIRECTORY_IMPL = """\
def scan_directory(directory: str, pattern: str = "*") -> list[dict]:
    result = []
    for item in Path(directory).glob(pattern):
        if item.is_file():
            result.append({
                "name": item.name,
                "path": str(item),
                "size_bytes": item.stat().st_size,
                "extension": item.suffix,
            })
    return result"""

READ_WRITE_CSV_IMPL = """\
def read_csv(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: str, rows: list[dict], fieldnames: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)"""

LOAD_JSON_FILES_IMPL = """\
def load_json_files(directory: str) -> list[dict]:
    results = []
    for p in Path(directory).glob("*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data["_source"] = p.name
                results.append(data)
        except Exception:
            pass
    return results"""

BATCH_PROCESS_FILES_IMPL = """\
def batch_process_files(directory: str, process_fn) -> list[dict]:
    results = []
    for p in sorted(Path(directory).glob("*")):
        if not p.is_file():
            continue
        try:
            content = p.read_text(encoding="utf-8")
            result = process_fn(content)
            results.append({"path": str(p), "status": "ok", "result": result})
        except Exception as e:
            results.append({"path": str(p), "status": "error", "error": str(e)})
    return results"""

AI_TAG_FILE_IMPL = """\
def ai_tag_file(content: str, model: str = "llama3.2") -> dict:
    system = (
        "You are a file categorization assistant. "
        "Given text content, return JSON with exactly these keys: "
        "category (one word: technical, personal, financial, creative, or other), "
        "tags (list of up to 5 keyword strings), "
        "summary (one sentence describing the content). "
        "Return only valid JSON."
    )
    response = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": f"Categorize this content:\\n\\n{content[:2000]}"},
        ],
        format="json",
    )
    raw = response["message"]["content"]
    try:
        data = json.loads(raw)
    except Exception:
        data = {}
    return {
        "category": str(data.get("category", "other")).lower().strip() or "other",
        "tags": list(data.get("tags", [])),
        "summary": str(data.get("summary", "")),
    }"""


# ---------------------------------------------------------------------------
# Exercise 01 — scan_directory
# ---------------------------------------------------------------------------

def ex01():
    global _cid; _cid = 0
    return [
        md(
            "# Day 021 — Exercise 1: scan_directory\n\n"
            "**What you'll build:** `scan_directory(directory, pattern)` — lists files "
            "in a directory as a list of dicts.\n\n"
            "**Why it matters:** Every batch file operation starts by finding the right "
            "files. `pathlib.Path.glob()` lets you filter by pattern (e.g. `*.txt`) "
            "without string concatenation or OS-specific separators."
        ),
        code("from pathlib import Path"),
        md("## Your Implementation"),
        code(
            "def scan_directory(directory: str, pattern: str = \"*\") -> list[dict]:\n"
            '    """\n'
            "    Scan a directory and return file metadata.\n\n"
            "    Args:\n"
            "        directory: Path to the directory to scan (as a string).\n"
            "        pattern:   Glob pattern to filter files, e.g. '*.txt'.\n\n"
            "    Returns:\n"
            "        list[dict] where each dict has:\n"
            "            name       — filename including extension\n"
            "            path       — absolute path as a string\n"
            "            size_bytes — file size in bytes (int)\n"
            "            extension  — extension including dot, e.g. '.txt'\n"
            "        Subdirectories are excluded.\n"
            '    """\n'
            "    # TODO: result = []\n"
            "    # TODO: for item in Path(directory).glob(pattern):\n"
            "    # TODO:     if item.is_file():\n"
            "    # TODO:         result.append({...})\n"
            "    # TODO: return result\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "import tempfile\n"
            "\n"
            "\n"
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: function defined\n"
            "    try:\n"
            "        assert 'scan_directory' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: scan_directory defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    with tempfile.TemporaryDirectory() as tmp:\n"
            "        td = Path(tmp)\n"
            "        (td / 'readme.txt').write_text('Hello world', encoding='utf-8')\n"
            "        (td / 'data.csv').write_text('a,b\\n1,2', encoding='utf-8')\n"
            "        (td / 'notes.txt').write_text('Some notes here', encoding='utf-8')\n"
            "        (td / 'subdir').mkdir()\n"
            "\n"
            "        result = None\n"
            "\n"
            "        # Check 2: returns a list\n"
            "        try:\n"
            "            result = scan_directory(str(td))\n"
            "            assert isinstance(result, list), f'expected list, got {type(result)}'\n"
            "            passed += 1; print('\\u2705 Check 2: returns a list')\n"
            "        except Exception as e:\n"
            "            print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "        # Check 3: each item has required keys\n"
            "        try:\n"
            "            assert result is not None and len(result) > 0, 'no files found'\n"
            "            for item in result:\n"
            "                for key in ('name', 'path', 'size_bytes', 'extension'):\n"
            "                    assert key in item, f\"missing key '{key}': {item}\"\n"
            "            passed += 1; print('\\u2705 Check 3: each item has name/path/size_bytes/extension')\n"
            "        except Exception as e:\n"
            "            print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "        # Check 4: pattern filtering works\n"
            "        try:\n"
            "            txt_files = scan_directory(str(td), '*.txt')\n"
            "            assert all(item['extension'] == '.txt' for item in txt_files), \\\n"
            "                f'non-.txt files in result: {[i[\"extension\"] for i in txt_files]}'\n"
            "            assert len(txt_files) == 2, f'expected 2 .txt files, got {len(txt_files)}'\n"
            "            passed += 1; print('\\u2705 Check 4: *.txt pattern returns only text files')\n"
            "        except Exception as e:\n"
            "            print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "        # Check 5: subdirectories excluded\n"
            "        try:\n"
            "            all_items = scan_directory(str(td))\n"
            "            names = [item['name'] for item in all_items]\n"
            "            assert 'subdir' not in names, \\\n"
            "                f'subdirectory appeared in results: {names}'\n"
            "            passed += 1; print('\\u2705 Check 5: subdirectories excluded from results')\n"
            "        except Exception as e:\n"
            "            print(f'\\u274c Check 5: {e}')\n"
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
            + SCAN_DIRECTORY_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 02 — read_csv / write_csv
# ---------------------------------------------------------------------------

def ex02():
    global _cid; _cid = 100
    return [
        md(
            "# Day 021 — Exercise 2: read_csv / write_csv\n\n"
            "**What you'll build:** `read_csv(path)` and `write_csv(path, rows, fieldnames)` "
            "— CSV round-trip using the stdlib `csv` module.\n\n"
            "**Why it matters:** CSV is the lingua franca of tabular data. Python's "
            "`csv.DictReader` and `csv.DictWriter` give you dict-per-row I/O with correct "
            "quoting and encoding — no pandas required."
        ),
        code("import csv\nfrom pathlib import Path"),
        md("## Your Implementation"),
        code(
            "def read_csv(path: str) -> list[dict]:\n"
            '    """\n'
            "    Read a CSV file and return a list of row dicts.\n\n"
            "    Args:\n"
            "        path: Path to the CSV file.\n\n"
            "    Returns:\n"
            "        list[dict] — one dict per data row; keys are column headers.\n"
            '    """\n'
            "    # TODO: open path with newline='', encoding='utf-8'\n"
            "    # TODO: use csv.DictReader and return list(...)\n"
            "    pass\n"
            "\n"
            "\n"
            "def write_csv(path: str, rows: list[dict], fieldnames: list[str]) -> None:\n"
            '    """\n'
            "    Write a list of dicts to a CSV file.\n\n"
            "    Args:\n"
            "        path:       Destination file path.\n"
            "        rows:       List of dicts to write.\n"
            "        fieldnames: Column names in output order.\n\n"
            "    Notes:\n"
            "        Extra keys in rows that are not in fieldnames are silently ignored.\n"
            '    """\n'
            "    # TODO: open path for writing with newline='', encoding='utf-8'\n"
            "    # TODO: use csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')\n"
            "    # TODO: writer.writeheader() then writer.writerows(rows)\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "import tempfile\n"
            "\n"
            "\n"
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: both functions defined\n"
            "    try:\n"
            "        assert 'read_csv' in globals() and 'write_csv' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: read_csv and write_csv defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    with tempfile.TemporaryDirectory() as tmp:\n"
            "        td = Path(tmp)\n"
            "        test_path = str(td / 'test.csv')\n"
            "        rows = [\n"
            "            {'name': 'Alice', 'score': '95'},\n"
            "            {'name': 'Bob',   'score': '87'},\n"
            "        ]\n"
            "        fieldnames = ['name', 'score']\n"
            "\n"
            "        # Check 2: write_csv creates a file\n"
            "        try:\n"
            "            write_csv(test_path, rows, fieldnames)\n"
            "            assert (td / 'test.csv').exists(), 'write_csv did not create the file'\n"
            "            passed += 1; print('\\u2705 Check 2: write_csv creates the file')\n"
            "        except Exception as e:\n"
            "            print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "        # Check 3: file has correct header row\n"
            "        try:\n"
            "            content = (td / 'test.csv').read_text(encoding='utf-8')\n"
            "            first_line = content.split('\\n')[0].strip()\n"
            "            assert first_line == 'name,score', \\\n"
            "                f'expected header \"name,score\", got {first_line!r}'\n"
            "            passed += 1; print('\\u2705 Check 3: CSV has correct header row')\n"
            "        except Exception as e:\n"
            "            print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "        # Check 4: read_csv returns correct row count\n"
            "        try:\n"
            "            back = read_csv(test_path)\n"
            "            assert isinstance(back, list), f'expected list, got {type(back)}'\n"
            "            assert len(back) == 2, f'expected 2 rows, got {len(back)}'\n"
            "            passed += 1; print('\\u2705 Check 4: read_csv returns correct row count')\n"
            "        except Exception as e:\n"
            "            print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "        # Check 5: field values preserved in round-trip\n"
            "        try:\n"
            "            back2 = read_csv(test_path)\n"
            "            assert back2[0]['name'] == 'Alice', \\\n"
            "                f\"expected 'Alice', got {back2[0]['name']!r}\"\n"
            "            assert back2[1]['score'] == '87', \\\n"
            "                f\"expected '87', got {back2[1]['score']!r}\"\n"
            "            passed += 1; print('\\u2705 Check 5: field values preserved in round-trip')\n"
            "        except Exception as e:\n"
            "            print(f'\\u274c Check 5: {e}')\n"
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
            + READ_WRITE_CSV_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 03 — load_json_files
# ---------------------------------------------------------------------------

def ex03():
    global _cid; _cid = 200
    return [
        md(
            "# Day 021 — Exercise 3: load_json_files\n\n"
            "**What you'll build:** `load_json_files(directory)` — loads every valid `.json` "
            "file in a directory into a list of dicts, adding a `_source` key with the "
            "filename.\n\n"
            "**Why it matters:** AI pipelines often emit one JSON file per document or batch. "
            "Loading them all at once is the first step in any aggregation or post-processing "
            "workflow."
        ),
        code("import json\nfrom pathlib import Path"),
        md("## Your Implementation"),
        code(
            "def load_json_files(directory: str) -> list[dict]:\n"
            '    """\n'
            "    Load all .json files in directory into a list of dicts.\n\n"
            "    Args:\n"
            "        directory: Path to the directory to scan.\n\n"
            "    Returns:\n"
            "        list[dict] — one dict per valid JSON file.\n"
            "        Each dict gets a '_source' key containing the filename (e.g. 'data.json').\n"
            "        Malformed JSON files and non-dict JSON values are silently skipped.\n"
            '    """\n'
            "    # TODO: results = []\n"
            "    # TODO: for p in Path(directory).glob('*.json'):\n"
            "    #           try:\n"
            "    #               data = json.loads(p.read_text(encoding='utf-8'))\n"
            "    #               if isinstance(data, dict):\n"
            "    #                   data['_source'] = p.name\n"
            "    #                   results.append(data)\n"
            "    #           except Exception:\n"
            "    #               pass\n"
            "    # TODO: return results\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "import tempfile\n"
            "\n"
            "\n"
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'load_json_files' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: load_json_files defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    with tempfile.TemporaryDirectory() as tmp:\n"
            "        td = Path(tmp)\n"
            "        (td / 'config.json').write_text(\n"
            "            json.dumps({'app': 'my_app', 'version': '1.0'}), encoding='utf-8')\n"
            "        (td / 'data.json').write_text(\n"
            "            json.dumps({'key': 'value', 'count': 42}), encoding='utf-8')\n"
            "        (td / 'settings.json').write_text(\n"
            "            json.dumps({'theme': 'dark', 'lang': 'en'}), encoding='utf-8')\n"
            "        (td / 'broken.json').write_text('not valid json {{{', encoding='utf-8')\n"
            "        (td / 'readme.txt').write_text('ignored', encoding='utf-8')\n"
            "\n"
            "        results = None\n"
            "\n"
            "        # Check 2: returns a list\n"
            "        try:\n"
            "            results = load_json_files(str(td))\n"
            "            assert isinstance(results, list), f'expected list, got {type(results)}'\n"
            "            passed += 1; print('\\u2705 Check 2: returns a list')\n"
            "        except Exception as e:\n"
            "            print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "        # Check 3: loads exactly 3 valid JSON files\n"
            "        try:\n"
            "            assert results is not None, 'results is None'\n"
            "            assert len(results) == 3, \\\n"
            "                f'expected 3 valid dicts, got {len(results)}'\n"
            "            passed += 1; print('\\u2705 Check 3: loads exactly 3 valid JSON files')\n"
            "        except Exception as e:\n"
            "            print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "        # Check 4: each dict has _source key\n"
            "        try:\n"
            "            assert results is not None and len(results) > 0, 'no results'\n"
            "            for item in results:\n"
            "                assert '_source' in item, f\"missing '_source': {item}\"\n"
            "                assert item['_source'].endswith('.json'), \\\n"
            "                    f\"_source should be filename, got {item['_source']!r}\"\n"
            "            passed += 1; print(\"\\u2705 Check 4: each dict has '_source' filename key\")\n"
            "        except Exception as e:\n"
            "            print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "        # Check 5: skips non-JSON and malformed files\n"
            "        try:\n"
            "            assert results is not None, 'results is None'\n"
            "            sources = [r['_source'] for r in results]\n"
            "            assert 'readme.txt' not in sources, \\\n"
            "                'should not include .txt files'\n"
            "            assert 'broken.json' not in sources, \\\n"
            "                'should skip malformed JSON'\n"
            "            passed += 1; print('\\u2705 Check 5: skips non-JSON and malformed files')\n"
            "        except Exception as e:\n"
            "            print(f'\\u274c Check 5: {e}')\n"
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
            + LOAD_JSON_FILES_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 04 — batch_process_files
# ---------------------------------------------------------------------------

def ex04():
    global _cid; _cid = 300
    return [
        md(
            "# Day 021 — Exercise 4: batch_process_files\n\n"
            "**What you'll build:** `batch_process_files(directory, process_fn)` — applies "
            "a function to every file's text content and collects `{path, status, result}` "
            "dicts. Errors are recorded without stopping the loop.\n\n"
            "**Why it matters:** Real file corpora contain malformed, binary, or unexpected "
            "files. A resilient batch loop never crashes on a single bad file — it records "
            "the error and continues."
        ),
        code("from pathlib import Path"),
        md("## Your Implementation"),
        code(
            "def batch_process_files(directory: str, process_fn) -> list[dict]:\n"
            '    """\n'
            "    Apply process_fn to every file's text content in directory.\n\n"
            "    Args:\n"
            "        directory:  Path to the directory to scan.\n"
            "        process_fn: Callable[[str], Any] — receives file text, returns a result.\n\n"
            "    Returns:\n"
            "        list[dict] — one dict per file:\n"
            "            On success: {'path': str, 'status': 'ok', 'result': <return value>}\n"
            "            On error:   {'path': str, 'status': 'error', 'error': str(exception)}\n"
            "        Subdirectories are skipped. The loop never raises.\n"
            '    """\n'
            "    # TODO: results = []\n"
            "    # TODO: for p in sorted(Path(directory).glob('*')):\n"
            "    #           if not p.is_file(): continue\n"
            "    #           try:\n"
            "    #               content = p.read_text(encoding='utf-8')\n"
            "    #               result = process_fn(content)\n"
            "    #               results.append({'path': str(p), 'status': 'ok', 'result': result})\n"
            "    #           except Exception as e:\n"
            "    #               results.append({'path': str(p), 'status': 'error', 'error': str(e)})\n"
            "    # TODO: return results\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "import tempfile\n"
            "\n"
            "\n"
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'batch_process_files' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: batch_process_files defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    results = None\n"
            "\n"
            "    with tempfile.TemporaryDirectory() as tmp:\n"
            "        td = Path(tmp)\n"
            "        (td / 'a.txt').write_text('Hello world', encoding='utf-8')\n"
            "        (td / 'b.txt').write_text('Goodbye world', encoding='utf-8')\n"
            "        (td / 'binary.dat').write_bytes(b'\\x80\\x90\\xa0')  # invalid utf-8\n"
            "\n"
            "        # Check 2: returns a list\n"
            "        try:\n"
            "            results = batch_process_files(str(td), lambda c: len(c))\n"
            "            assert isinstance(results, list), \\\n"
            "                f'expected list, got {type(results)}'\n"
            "            passed += 1; print('\\u2705 Check 2: returns a list')\n"
            "        except Exception as e:\n"
            "            print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "        # Check 3: each item has path and status keys\n"
            "        try:\n"
            "            assert results is not None and len(results) > 0, 'empty results'\n"
            "            for item in results:\n"
            "                assert 'path' in item, f\"missing 'path': {item}\"\n"
            "                assert 'status' in item, f\"missing 'status': {item}\"\n"
            "            passed += 1; print('\\u2705 Check 3: each item has path and status keys')\n"
            "        except Exception as e:\n"
            "            print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "        # Check 4: successful files have status='ok' and 'result' key\n"
            "        try:\n"
            "            assert results is not None\n"
            "            ok_items = [r for r in results\n"
            "                        if Path(r['path']).suffix == '.txt']\n"
            "            assert len(ok_items) == 2, \\\n"
            "                f'expected 2 text files, got {len(ok_items)}'\n"
            "            for item in ok_items:\n"
            "                assert item['status'] == 'ok', \\\n"
            "                    f\"expected status='ok', got {item['status']!r}\"\n"
            "                assert 'result' in item, \\\n"
            "                    f\"missing 'result' in ok item: {item}\"\n"
            "            passed += 1; print(\"\\u2705 Check 4: text files processed with status='ok'\")\n"
            "        except Exception as e:\n"
            "            print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "        # Check 5: errors recorded without stopping the loop\n"
            "        try:\n"
            "            assert results is not None\n"
            "            statuses = [r['status'] for r in results]\n"
            "            assert 'ok' in statuses, 'no successful items'\n"
            "            assert 'error' in statuses, \\\n"
            "                'binary.dat should produce an error entry'\n"
            "            error_items = [r for r in results if r['status'] == 'error']\n"
            "            for item in error_items:\n"
            "                assert 'error' in item, \\\n"
            "                    f\"missing 'error' key in error item: {item}\"\n"
            "            passed += 1; print('\\u2705 Check 5: errors recorded without stopping loop')\n"
            "        except Exception as e:\n"
            "            print(f'\\u274c Check 5: {e}')\n"
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
            + BATCH_PROCESS_FILES_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 05 — ai_tag_file
# ---------------------------------------------------------------------------

def ex05():
    global _cid; _cid = 400
    return [
        md(
            "# Day 021 — Exercise 5: ai_tag_file\n\n"
            "**What you'll build:** `ai_tag_file(content, model)` — uses a local LLM to "
            "categorize a file's text content, returning `{category, tags, summary}`.\n\n"
            "**Why it matters:** This is the AI layer in the batch pipeline. Once you can "
            "tag one file, you can tag thousands by looping with `batch_process_files`."
        ),
        code("import ollama\nimport json"),
        md("## Your Implementation"),
        code(
            "def ai_tag_file(content: str, model: str = \"llama3.2\") -> dict:\n"
            '    """\n'
            "    Use a local LLM to categorize file content.\n\n"
            "    Args:\n"
            "        content: The text content to categorize.\n"
            "        model:   Ollama model name.\n\n"
            "    Returns:\n"
            "        dict with keys:\n"
            "            category — one word: technical/personal/financial/creative/other\n"
            "            tags     — list of up to 5 keyword strings\n"
            "            summary  — one sentence describing the content\n"
            '    """\n'
            "    # TODO: build a system prompt asking for JSON with category/tags/summary\n"
            "    # TODO: call ollama.chat with format='json'\n"
            "    # TODO: json.loads the response content\n"
            "    # TODO: return {'category': ..., 'tags': ..., 'summary': ...}\n"
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
            "        assert 'ai_tag_file' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: ai_tag_file defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    result = None\n"
            "    SAMPLE = (\n"
            "        'This Python script processes a list of numbers and computes '\n"
            "        'their average, standard deviation, and median values.'\n"
            "    )\n"
            "\n"
            "    # Check 2: returns a dict (1 LLM call)\n"
            "    try:\n"
            "        result = ai_tag_file(SAMPLE)\n"
            "        assert isinstance(result, dict), \\\n"
            "            f'expected dict, got {type(result)}'\n"
            "        passed += 1; print('\\u2705 Check 2: returns a dict')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: has required keys\n"
            "    try:\n"
            "        assert result is not None, 'result is None (Check 2 failed)'\n"
            "        for key in ('category', 'tags', 'summary'):\n"
            "            assert key in result, f\"missing key '{key}': {result}\"\n"
            "        passed += 1; print('\\u2705 Check 3: dict has category/tags/summary keys')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: category is a non-empty string\n"
            "    try:\n"
            "        assert result is not None, 'result is None'\n"
            "        cat = result['category']\n"
            "        assert isinstance(cat, str) and len(cat) > 0, \\\n"
            "            f'category must be non-empty str, got {cat!r}'\n"
            "        passed += 1; print(f'\\u2705 Check 4: category is a string ({cat!r})')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: tags is a list\n"
            "    try:\n"
            "        assert result is not None, 'result is None'\n"
            "        tags = result['tags']\n"
            "        assert isinstance(tags, list), \\\n"
            "            f'tags must be list, got {type(tags)}'\n"
            "        passed += 1; print(f'\\u2705 Check 5: tags is a list ({tags})')\n"
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
            + AI_TAG_FILE_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Project notebook (student template — NOT executed by gate)
# ---------------------------------------------------------------------------

ALL_IMPLS = (
    SCAN_DIRECTORY_IMPL + "\n\n\n"
    + READ_WRITE_CSV_IMPL + "\n\n\n"
    + LOAD_JSON_FILES_IMPL + "\n\n\n"
    + BATCH_PROCESS_FILES_IMPL + "\n\n\n"
    + AI_TAG_FILE_IMPL
)


def project_nb():
    global _cid; _cid = 500
    return [
        md(
            "# Day 021 Project: AI File Organizer\n\n"
            "## What You're Building\n\n"
            "An end-to-end AI pipeline that scans a directory, reads every file, asks a "
            "local LLM to categorize each one, and produces two outputs:\n\n"
            "- `manifest.json` — full metadata for every file (name, path, category, tags, summary)\n"
            "- `report.csv` — a tidy summary table (name, category, summary, size_bytes)\n\n"
            "You also organize the files into category subfolders.\n\n"
            "**You run it, it produces those two files and a sorted folder. That's the deliverable.**"
        ),
        code(
            "import json\n"
            "import csv\n"
            "import shutil\n"
            "import tempfile\n"
            "from pathlib import Path\n"
            "import ollama"
        ),
        md("## Provided: All Helper Functions"),
        code(ALL_IMPLS),
        md(
            "## Your Implementation\n\n"
            "### Step 1: Create your sample corpus\n\n"
            "Define at least **5 diverse text files** as a dict, write them to a temp "
            "directory, then scan it."
        ),
        code(
            "# Create sample corpus — add at least 5 files covering different topics\n"
            "SAMPLE_FILES = {\n"
            "    'python_tutorial.txt': (\n"
            "        'Python is a high-level programming language known for clean syntax. '\n"
            "        'It supports procedural, object-oriented, and functional programming. '\n"
            "        'Python is widely used in data science, web development, and automation.'\n"
            "    ),\n"
            "    'budget_2024.txt': (\n"
            "        'Q1 Budget Summary: Revenue $45,000. Expenses: rent $12,000, '\n"
            "        'salaries $18,000, software subscriptions $2,500, marketing $3,000. '\n"
            "        'Net profit Q1: $9,500.'\n"
            "    ),\n"
            "    'poem_nature.txt': (\n"
            "        'Autumn leaves descend / golden light on still water / silence finds me here. '\n"
            "        'The river speaks low / carrying dreams to the sea / where time dissolves.'\n"
            "    ),\n"
            "    'ml_notes.txt': (\n"
            "        'Neural networks learn by adjusting weights during backpropagation. '\n"
            "        'The transformer architecture uses self-attention to model token relationships. '\n"
            "        'Large language models are pre-trained on vast text corpora.'\n"
            "    ),\n"
            "    'shopping_list.txt': (\n"
            "        'Weekly groceries: milk, eggs, whole wheat bread, cheddar cheese, '\n"
            "        'chicken breast, broccoli, spinach, olive oil, pasta, tomato sauce.'\n"
            "    ),\n"
            "}\n"
            "\n"
            "# Write files to a temp directory\n"
            "SAMPLE_DIR = Path(tempfile.mkdtemp())\n"
            "for fname, content in SAMPLE_FILES.items():\n"
            "    (SAMPLE_DIR / fname).write_text(content, encoding='utf-8')\n"
            "print(f'Created {len(SAMPLE_FILES)} sample files in {SAMPLE_DIR}')"
        ),
        md("### Step 2: Scan the directory"),
        code(
            "# Scan and inspect the files\n"
            "file_list = scan_directory(str(SAMPLE_DIR))\n"
            "print(f'Found {len(file_list)} files:')\n"
            "for f in file_list:\n"
            "    print(f\"  {f['name']} ({f['size_bytes']} bytes)\")"
        ),
        md("### Step 3: AI-tag each file"),
        code(
            "# Tag every file with the LLM\n"
            "results = []\n"
            "for file_info in file_list:\n"
            "    content = Path(file_info['path']).read_text(encoding='utf-8')\n"
            "    tags = ai_tag_file(content)\n"
            "    results.append({**file_info, **tags})\n"
            "    print(f\"  {file_info['name']} -> {tags['category']}: {tags['summary'][:60]}...\")"
        ),
        md("### Step 4: Write manifest.json"),
        code(
            "MANIFEST_PATH = SAMPLE_DIR / 'manifest.json'\n"
            "MANIFEST_PATH.write_text(json.dumps(results, indent=2), encoding='utf-8')\n"
            "print(f'Wrote {MANIFEST_PATH}')"
        ),
        md("### Step 5: Write report.csv"),
        code(
            "REPORT_PATH = SAMPLE_DIR / 'report.csv'\n"
            "write_csv(\n"
            "    str(REPORT_PATH),\n"
            "    results,\n"
            "    fieldnames=['name', 'category', 'summary', 'size_bytes'],\n"
            ")\n"
            "report_rows = read_csv(str(REPORT_PATH))\n"
            "print(f'Wrote {REPORT_PATH} ({len(report_rows)} rows)')"
        ),
        md("### Step 6: Organize files into category folders"),
        code(
            "ORGANIZED_DIR = SAMPLE_DIR / 'organized'\n"
            "ORGANIZED_DIR.mkdir()\n"
            "for item in results:\n"
            "    cat_dir = ORGANIZED_DIR / item['category']\n"
            "    cat_dir.mkdir(exist_ok=True)\n"
            "    shutil.copy(item['path'], cat_dir / item['name'])\n"
            "print('Files organized:')\n"
            "for cat_dir in sorted(ORGANIZED_DIR.iterdir()):\n"
            "    if cat_dir.is_dir():\n"
            "        print(f\"  {cat_dir.name}/: {len(list(cat_dir.iterdir()))} file(s)\")"
        ),
        md("## Checks"),
        code(
            "def _run_project_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: SAMPLE_DIR has >= 3 files\n"
            "    try:\n"
            "        assert 'SAMPLE_DIR' in globals(), 'SAMPLE_DIR not defined'\n"
            "        sample_path = Path(SAMPLE_DIR)\n"
            "        assert sample_path.is_dir(), f'{SAMPLE_DIR} is not a directory'\n"
            "        n_files = len([f for f in sample_path.glob('*') if f.is_file()])\n"
            "        assert n_files >= 3, f'need >= 3 files, found {n_files}'\n"
            "        passed += 1; print(f'\\u2705 Check 1: SAMPLE_DIR has {n_files} files')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: SAMPLE_DIR — {e}')\n"
            "\n"
            "    # Check 2: file_list is populated\n"
            "    try:\n"
            "        assert 'file_list' in globals(), 'file_list not defined'\n"
            "        assert isinstance(file_list, list) and len(file_list) >= 3\n"
            "        for item in file_list:\n"
            "            assert 'name' in item and 'size_bytes' in item\n"
            "        passed += 1; print(f'\\u2705 Check 2: file_list has {len(file_list)} metadata dicts')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: file_list — {e}')\n"
            "\n"
            "    # Check 3: results has category/tags/summary\n"
            "    try:\n"
            "        assert 'results' in globals(), 'results not defined'\n"
            "        assert isinstance(results, list) and len(results) >= 3\n"
            "        for r in results:\n"
            "            for key in ('category', 'tags', 'summary'):\n"
            "                assert key in r, f\"missing '{key}' in: {r}\"\n"
            "        passed += 1; print(f'\\u2705 Check 3: results has {len(results)} tagged items')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: results — {e}')\n"
            "\n"
            "    # Check 4: MANIFEST_PATH exists and is valid JSON\n"
            "    try:\n"
            "        assert 'MANIFEST_PATH' in globals(), 'MANIFEST_PATH not defined'\n"
            "        mp = Path(MANIFEST_PATH)\n"
            "        assert mp.exists(), f'{MANIFEST_PATH} does not exist'\n"
            "        json.loads(mp.read_text(encoding='utf-8'))\n"
            "        passed += 1; print('\\u2705 Check 4: manifest.json exists and is valid JSON')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: MANIFEST_PATH — {e}')\n"
            "\n"
            "    # Check 5: REPORT_PATH exists with data rows\n"
            "    try:\n"
            "        assert 'REPORT_PATH' in globals(), 'REPORT_PATH not defined'\n"
            "        rp = Path(REPORT_PATH)\n"
            "        assert rp.exists(), f'{REPORT_PATH} does not exist'\n"
            "        rows = read_csv(str(rp))\n"
            "        assert len(rows) >= 1, 'report.csv has no data rows'\n"
            "        passed += 1; print(f'\\u2705 Check 5: report.csv exists with {len(rows)} rows')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: REPORT_PATH — {e}')\n"
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
            "- Use `batch_process_files` to collect word counts before tagging — "
            "skip files with fewer than 20 words\n"
            "- Persist results to `manifest.json` incrementally so a crash mid-run "
            "doesn't lose finished work\n"
            "- Add a `--dry-run` mode: print what would be organized without moving files\n"
            "- Try `load_json_files` on the `organized/` subfolders to re-aggregate results\n"
            "- Extend `scan_directory` to recurse with `.rglob()` and add a `depth` counter"
        ),
    ]


# ---------------------------------------------------------------------------
# Solution notebook (executed by gate — must run clean)
# ---------------------------------------------------------------------------

SAMPLE_TEXTS = {
    "python_tutorial.txt": (
        "Python is a high-level, general-purpose programming language. "
        "Created by Guido van Rossum, it was first released in 1991. "
        "Python's clean syntax and extensive standard library make it ideal "
        "for data science, automation, web development, and AI engineering."
    ),
    "budget_q1.txt": (
        "Q1 Financial Report: Total revenue $48,500. "
        "Operating expenses: rent $12,000, payroll $22,000, "
        "cloud services $3,200, marketing $4,100. "
        "Net operating income: $7,200. Cash reserves: $31,000."
    ),
    "haiku_autumn.txt": (
        "Crimson leaves cascade / silence holds the mountain lake / "
        "one last heron flies. "
        "Frost on morning grass / the old pine bends but does not break / "
        "winter teaches patience."
    ),
}

DEMO_QUESTIONS = [
    "What is Python used for?",
    "What were the Q1 expenses?",
    "What images appear in the poems?",
]


def solution_nb():
    global _cid; _cid = 600

    solution_impls = (
        "import json\n"
        "import csv\n"
        "import shutil\n"
        "import tempfile\n"
        "from pathlib import Path\n"
        "import ollama\n"
        "\n"
        "\n"
        + SCAN_DIRECTORY_IMPL + "\n"
        "\n"
        "\n"
        + READ_WRITE_CSV_IMPL + "\n"
        "\n"
        "\n"
        + LOAD_JSON_FILES_IMPL + "\n"
        "\n"
        "\n"
        + BATCH_PROCESS_FILES_IMPL + "\n"
        "\n"
        "\n"
        + AI_TAG_FILE_IMPL
    )

    corpus_lines = "CORPUS = {\n"
    for fname, text in SAMPLE_TEXTS.items():
        corpus_lines += f"    {fname!r}: {text!r},\n"
    corpus_lines += "}\n"

    return [
        md(
            "# Day 021 Project Solution — AI File Organizer\n\n"
            "End-to-end: scan a directory → AI-tag each file → write manifest.json "
            "and report.csv → organize into category subfolders."
        ),
        code(solution_impls),
        md("## Create Sample Corpus"),
        code(
            corpus_lines
            + "\n"
            "WORK_DIR = Path(tempfile.mkdtemp())\n"
            "for fname, content in CORPUS.items():\n"
            "    (WORK_DIR / fname).write_text(content, encoding='utf-8')\n"
            "print(f'Created {len(CORPUS)} sample files.')"
        ),
        md("## Step 1 — Scan"),
        code(
            "file_list = scan_directory(str(WORK_DIR))\n"
            "print(f'Scanned {len(file_list)} files:')\n"
            "for f in file_list:\n"
            "    print(f\"  {f['name']} ({f['size_bytes']} bytes)\")"
        ),
        md("## Step 2 — AI-Tag (scripted: one file per topic)"),
        code(
            "results = []\n"
            "for file_info in file_list:\n"
            "    content = Path(file_info['path']).read_text(encoding='utf-8')\n"
            "    tags = ai_tag_file(content)\n"
            "    row = {**file_info, **tags}\n"
            "    results.append(row)\n"
            "    print(f\"  {file_info['name']} -> [{tags['category']}] {tags['summary'][:55]}...\")"
        ),
        md("## Step 3 — Write manifest.json"),
        code(
            "manifest_path = WORK_DIR / 'manifest.json'\n"
            "manifest_path.write_text(json.dumps(results, indent=2), encoding='utf-8')\n"
            "loaded_back = json.loads(manifest_path.read_text(encoding='utf-8'))\n"
            "print(f'manifest.json: {len(loaded_back)} entries')"
        ),
        md("## Step 4 — Write and verify report.csv"),
        code(
            "report_path = WORK_DIR / 'report.csv'\n"
            "write_csv(\n"
            "    str(report_path),\n"
            "    results,\n"
            "    fieldnames=['name', 'category', 'summary', 'size_bytes'],\n"
            ")\n"
            "report_rows = read_csv(str(report_path))\n"
            "print(f'report.csv: {len(report_rows)} rows')\n"
            "for row in report_rows:\n"
            "    print(f\"  {row['name']} | {row['category']}\")"
        ),
        md("## Step 5 — Organize into category folders"),
        code(
            "organized = WORK_DIR / 'organized'\n"
            "organized.mkdir()\n"
            "for item in results:\n"
            "    cat_dir = organized / item['category']\n"
            "    cat_dir.mkdir(exist_ok=True)\n"
            "    shutil.copy(item['path'], cat_dir / item['name'])\n"
            "categories = sorted(d.name for d in organized.iterdir() if d.is_dir())\n"
            "print(f'Organized into {len(categories)} categories: {categories}')"
        ),
        md("## Summary + Cleanup"),
        code(
            "print('\\n=== AI File Organizer Summary ===')\n"
            "print(f'Files processed : {len(results)}')\n"
            "print(f'Categories found: {sorted(set(r[\"category\"] for r in results))}')\n"
            "print(f'manifest.json   : {manifest_path.name}')\n"
            "print(f'report.csv      : {report_path.name}')\n"
            "shutil.rmtree(WORK_DIR)\n"
            "print('Temp files cleaned up.')\n"
            "print('Demo complete!')"
        ),
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Generating Day 021 notebooks...")
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
