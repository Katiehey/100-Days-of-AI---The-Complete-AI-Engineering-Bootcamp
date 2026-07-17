#!/usr/bin/env python3
"""Generate all Day 022 notebooks: exercises 1-5, project, solution."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAY_DIR = ROOT / "02_automation" / "day_022"

_cid = 0

JPH_BASE = "https://jsonplaceholder.typicode.com"


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
# Solution implementations (rely on each notebook's imports cell)
# ---------------------------------------------------------------------------

GET_JSON_IMPL = """\
def get_json(url: str, params: dict | None = None, headers: dict | None = None):
    response = requests.get(url, params=params, headers=headers, timeout=10)
    response.raise_for_status()
    return response.json()"""

BUILD_HEADERS_IMPL = """\
def build_headers(api_key: str, extra: dict | None = None) -> dict:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if extra:
        headers.update(extra)
    return headers"""

PAGINATE_COLLECT_IMPL = """\
def paginate_collect(url: str, page_size: int = 10, max_pages: int = 3) -> list[dict]:
    all_results = []
    for page in range(1, max_pages + 1):
        params = {"_page": page, "_limit": page_size}
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        if not data:
            break
        all_results.extend(data)
    return all_results"""

SAFE_GET_IMPL = """\
def safe_get(url: str, headers: dict | None = None, timeout: int = 10) -> dict:
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        return {"status": r.status_code, "data": r.json(), "error": None}
    except requests.exceptions.HTTPError as e:
        return {"status": e.response.status_code, "data": None, "error": str(e)}
    except Exception as e:
        return {"status": None, "data": None, "error": str(e)}"""

AI_ANALYZE_RESULTS_IMPL = """\
def ai_analyze_results(records: list[dict], question: str, model: str = "llama3.2") -> str:
    summary = json.dumps(records[:5], indent=2)
    response = ollama.chat(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are an API data analyst. Answer questions about the provided JSON data concisely.",
            },
            {
                "role": "user",
                "content": f"Data (first 5 records):\\n{summary}\\n\\nQuestion: {question}",
            },
        ],
    )
    return response["message"]["content"]"""

POSTS_API_IMPL = """\
class PostsAPI:
    BASE = "https://jsonplaceholder.typicode.com"

    def __init__(self, api_key: str = "demo"):
        self.session = requests.Session()
        self.session.headers.update(build_headers(api_key))

    def get_posts(self, user_id: int | None = None, limit: int = 10) -> list[dict]:
        params = {"_limit": limit}
        if user_id is not None:
            params["userId"] = user_id
        r = self.session.get(f"{self.BASE}/posts", params=params, timeout=10)
        r.raise_for_status()
        return r.json()

    def get_pages(self, page_size: int = 5, max_pages: int = 3) -> list[dict]:
        return paginate_collect(f"{self.BASE}/posts", page_size=page_size, max_pages=max_pages)

    def ai_summary(self, question: str, limit: int = 5) -> str:
        posts = self.get_posts(limit=limit)
        return ai_analyze_results(posts, question)

    def safe_fetch(self, endpoint: str) -> dict:
        return safe_get(f"{self.BASE}/{endpoint}")\
"""

ALL_IMPLS = (
    GET_JSON_IMPL + "\n\n\n"
    + BUILD_HEADERS_IMPL + "\n\n\n"
    + PAGINATE_COLLECT_IMPL + "\n\n\n"
    + SAFE_GET_IMPL + "\n\n\n"
    + AI_ANALYZE_RESULTS_IMPL
)


# ---------------------------------------------------------------------------
# Exercise 01 — get_json
# ---------------------------------------------------------------------------

def ex01():
    global _cid; _cid = 0
    return [
        md(
            "# Day 022 — Exercise 1: get_json\n\n"
            "**What you'll build:** `get_json(url, params, headers)` — makes a GET request "
            "and returns parsed JSON. Raises on HTTP errors.\n\n"
            "**Why it matters:** GET is the foundation of every read-only API interaction. "
            "Passing `params` as a dict lets `requests` URL-encode them correctly "
            "(no manual string formatting). `raise_for_status()` catches 4xx/5xx "
            "before bad responses silently corrupt your data."
        ),
        code("import requests"),
        md("## Your Implementation"),
        code(
            "def get_json(url: str, params: dict | None = None, headers: dict | None = None):\n"
            '    """\n'
            "    Make a GET request and return the parsed JSON body.\n\n"
            "    Args:\n"
            "        url:     Full URL to request.\n"
            "        params:  Query parameters as a dict (e.g. {'_limit': 3}).\n"
            "        headers: Extra request headers as a dict.\n\n"
            "    Returns:\n"
            "        Parsed JSON — list or dict depending on the endpoint.\n\n"
            "    Raises:\n"
            "        requests.exceptions.HTTPError on 4xx/5xx responses.\n"
            "        requests.exceptions.ConnectionError if the host is unreachable.\n"
            '    """\n'
            "    # TODO: response = requests.get(url, params=params, headers=headers, timeout=10)\n"
            "    # TODO: response.raise_for_status()\n"
            "    # TODO: return response.json()\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            f'JPH = "{JPH_BASE}"\n'
            "\n"
            "\n"
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'get_json' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: get_json defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    result = None\n"
            "\n"
            "    # Check 2: returns a list (1 GET call)\n"
            "    try:\n"
            "        result = get_json(JPH + '/posts', params={'_limit': 3})\n"
            "        assert isinstance(result, list), \\\n"
            "            f'expected list, got {type(result)}'\n"
            "        passed += 1; print('\\u2705 Check 2: returns a list')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: params filter respected (3 items)\n"
            "    try:\n"
            "        assert result is not None, 'result is None (Check 2 failed)'\n"
            "        assert len(result) == 3, f'expected 3 items, got {len(result)}'\n"
            "        passed += 1; print('\\u2705 Check 3: _limit=3 returns exactly 3 items')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: items are dicts with expected keys\n"
            "    try:\n"
            "        assert result is not None and len(result) > 0, 'empty result'\n"
            "        for item in result:\n"
            "            assert isinstance(item, dict), f'item is not a dict: {item}'\n"
            "            assert 'id' in item and 'title' in item, \\\n"
            "                f\"missing 'id' or 'title': {list(item)}\"\n"
            "        passed += 1; print(\"\\u2705 Check 4: each item is a dict with 'id' and 'title'\")\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: raises on connection error\n"
            "    raised = False\n"
            "    try:\n"
            "        get_json('http://localhost:9999/')\n"
            "    except Exception:\n"
            "        raised = True\n"
            "    try:\n"
            "        assert raised, 'get_json should raise on an unreachable URL'\n"
            "        passed += 1; print('\\u2705 Check 5: raises on connection error')\n"
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
            + GET_JSON_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 02 — build_headers
# ---------------------------------------------------------------------------

def ex02():
    global _cid; _cid = 100
    return [
        md(
            "# Day 022 — Exercise 2: build_headers\n\n"
            "**What you'll build:** `build_headers(api_key, extra)` — a pure function that "
            "constructs the auth headers dict for API requests.\n\n"
            "**Why it matters:** Centralising header construction means you change the auth "
            "scheme in one place. Bearer tokens (used by most modern APIs) and X-API-Key "
            "headers (common in REST APIs) are just dict entries — knowing the pattern "
            "lets you authenticate with any API."
        ),
        code("# No external imports needed — pure function"),
        md("## Your Implementation"),
        code(
            "def build_headers(api_key: str, extra: dict | None = None) -> dict:\n"
            '    """\n'
            "    Build authentication headers for API requests.\n\n"
            "    Args:\n"
            "        api_key: The API key or token string.\n"
            "        extra:   Optional additional headers to merge in.\n\n"
            "    Returns:\n"
            "        dict with at least:\n"
            "            Authorization: Bearer <api_key>\n"
            "            Content-Type:  application/json\n"
            "        Extra headers are merged in if provided.\n"
            '    """\n'
            "    # TODO: headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}\n"
            "    # TODO: if extra: headers.update(extra)\n"
            "    # TODO: return headers\n"
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
            "        assert 'build_headers' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: build_headers defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    h = None\n"
            "\n"
            "    # Check 2: returns a dict\n"
            "    try:\n"
            "        h = build_headers('my_secret_key')\n"
            "        assert isinstance(h, dict), f'expected dict, got {type(h)}'\n"
            "        passed += 1; print('\\u2705 Check 2: returns a dict')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: Authorization starts with Bearer\n"
            "    try:\n"
            "        assert h is not None, 'h is None'\n"
            "        auth = h.get('Authorization', '')\n"
            "        assert auth.startswith('Bearer '), \\\n"
            "            f\"Authorization must start with 'Bearer ', got {auth!r}\"\n"
            "        assert 'my_secret_key' in auth, \\\n"
            "            f'api_key should appear in Authorization, got {auth!r}'\n"
            "        passed += 1; print('\\u2705 Check 3: Authorization header has Bearer token')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: Content-Type is application/json\n"
            "    try:\n"
            "        assert h is not None, 'h is None'\n"
            "        ct = h.get('Content-Type', '')\n"
            "        assert ct == 'application/json', \\\n"
            "            f\"expected 'application/json', got {ct!r}\"\n"
            "        passed += 1; print(\"\\u2705 Check 4: Content-Type is application/json\")\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: extra headers merged\n"
            "    try:\n"
            "        h2 = build_headers('key', extra={'X-Custom': 'value', 'Accept': 'text/plain'})\n"
            "        assert h2.get('X-Custom') == 'value', \\\n"
            "            f\"extra 'X-Custom' not merged: {h2}\"\n"
            "        assert h2.get('Accept') == 'text/plain', \\\n"
            "            f\"extra 'Accept' not merged: {h2}\"\n"
            "        assert 'Authorization' in h2, 'Authorization should still be present'\n"
            "        passed += 1; print('\\u2705 Check 5: extra headers merged correctly')\n"
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
            + BUILD_HEADERS_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 03 — paginate_collect
# ---------------------------------------------------------------------------

def ex03():
    global _cid; _cid = 200
    return [
        md(
            "# Day 022 — Exercise 3: paginate_collect\n\n"
            "**What you'll build:** `paginate_collect(url, page_size, max_pages)` — collects "
            "paginated results by looping over offset/limit pages until data runs out "
            "or max_pages is reached.\n\n"
            "**Why it matters:** Almost every API limits how many records it returns per "
            "call. Without pagination logic you silently miss data. This function is the "
            "core of any bulk data collection workflow."
        ),
        code("import requests"),
        md("## Your Implementation"),
        code(
            "def paginate_collect(url: str, page_size: int = 10, max_pages: int = 3) -> list[dict]:\n"
            '    """\n'
            "    Collect paginated results using _page / _limit query parameters.\n\n"
            "    Args:\n"
            "        url:       API endpoint URL.\n"
            "        page_size: Number of items to request per page.\n"
            "        max_pages: Maximum number of pages to fetch.\n\n"
            "    Returns:\n"
            "        Flat list of all collected items (list[dict]).\n"
            "        Stops early if a page returns an empty list.\n"
            '    """\n'
            "    # TODO: all_results = []\n"
            "    # TODO: for page in range(1, max_pages + 1):\n"
            "    #           params = {'_page': page, '_limit': page_size}\n"
            "    #           r = requests.get(url, params=params, timeout=10)\n"
            "    #           r.raise_for_status()\n"
            "    #           data = r.json()\n"
            "    #           if not data: break\n"
            "    #           all_results.extend(data)\n"
            "    # TODO: return all_results\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            f'JPH = "{JPH_BASE}"\n'
            "\n"
            "\n"
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'paginate_collect' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: paginate_collect defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    pages = None\n"
            "\n"
            "    # Check 2: returns a list (fetches 1 page of 5)\n"
            "    try:\n"
            "        pages = paginate_collect(JPH + '/posts', page_size=5, max_pages=1)\n"
            "        assert isinstance(pages, list), \\\n"
            "            f'expected list, got {type(pages)}'\n"
            "        passed += 1; print('\\u2705 Check 2: returns a list')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: one page gives page_size items\n"
            "    try:\n"
            "        assert pages is not None, 'pages is None (Check 2 failed)'\n"
            "        assert len(pages) == 5, \\\n"
            "            f'expected 5 items for max_pages=1 page_size=5, got {len(pages)}'\n"
            "        passed += 1; print('\\u2705 Check 3: one page returns page_size items')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: items are dicts\n"
            "    try:\n"
            "        assert pages is not None and len(pages) > 0, 'pages is empty'\n"
            "        assert all(isinstance(item, dict) for item in pages), \\\n"
            "            'not all items are dicts'\n"
            "        passed += 1; print('\\u2705 Check 4: all items are dicts')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: 2 pages × 5 = 10 items\n"
            "    try:\n"
            "        two_pages = paginate_collect(JPH + '/posts', page_size=5, max_pages=2)\n"
            "        assert len(two_pages) == 10, \\\n"
            "            f'expected 10 for 2 pages x 5, got {len(two_pages)}'\n"
            "        passed += 1; print('\\u2705 Check 5: 2 pages × page_size=5 gives 10 items')\n"
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
            + PAGINATE_COLLECT_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 04 — safe_get
# ---------------------------------------------------------------------------

def ex04():
    global _cid; _cid = 300
    return [
        md(
            "# Day 022 — Exercise 4: safe_get\n\n"
            "**What you'll build:** `safe_get(url, headers, timeout)` — a GET wrapper that "
            "**never raises**. Returns `{status, data, error}` whether the request "
            "succeeds or fails.\n\n"
            "**Why it matters:** In automation pipelines you cannot let one bad API "
            "response crash the whole run. `safe_get` lets the caller inspect the result "
            "dict and decide what to do — retry, skip, or alert — without try/except "
            "scattered across the codebase."
        ),
        code("import requests"),
        md("## Your Implementation"),
        code(
            "def safe_get(url: str, headers: dict | None = None, timeout: int = 10) -> dict:\n"
            '    """\n'
            "    Safe GET that never raises. Returns a result dict instead.\n\n"
            "    Args:\n"
            "        url:     URL to request.\n"
            "        headers: Optional request headers.\n"
            "        timeout: Request timeout in seconds.\n\n"
            "    Returns:\n"
            "        On success:    {'status': 200, 'data': <parsed JSON>, 'error': None}\n"
            "        On HTTP error: {'status': <code>, 'data': None, 'error': str(e)}\n"
            "        On any other:  {'status': None,  'data': None, 'error': str(e)}\n"
            '    """\n'
            "    # TODO: try:\n"
            "    #           r = requests.get(url, headers=headers, timeout=timeout)\n"
            "    #           r.raise_for_status()\n"
            "    #           return {'status': r.status_code, 'data': r.json(), 'error': None}\n"
            "    #       except requests.exceptions.HTTPError as e:\n"
            "    #           return {'status': e.response.status_code, 'data': None, 'error': str(e)}\n"
            "    #       except Exception as e:\n"
            "    #           return {'status': None, 'data': None, 'error': str(e)}\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            f'JPH = "{JPH_BASE}"\n'
            "\n"
            "\n"
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'safe_get' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: safe_get defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    ok_result = None\n"
            "\n"
            "    # Check 2: returns a dict with required keys (1 GET call)\n"
            "    try:\n"
            "        ok_result = safe_get(JPH + '/posts/1')\n"
            "        assert isinstance(ok_result, dict), \\\n"
            "            f'expected dict, got {type(ok_result)}'\n"
            "        for key in ('status', 'data', 'error'):\n"
            "            assert key in ok_result, f\"missing key '{key}': {ok_result}\"\n"
            "        passed += 1; print('\\u2705 Check 2: returns dict with status/data/error keys')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: success case values\n"
            "    try:\n"
            "        assert ok_result is not None, 'ok_result is None'\n"
            "        assert ok_result['status'] == 200, \\\n"
            "            f\"expected status=200, got {ok_result['status']}\"\n"
            "        assert ok_result['data'] is not None, 'data should not be None on success'\n"
            "        assert ok_result['error'] is None, \\\n"
            "            f\"error should be None on success, got {ok_result['error']!r}\"\n"
            "        passed += 1; print('\\u2705 Check 3: success: status=200, data set, error=None')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: connection error → status=None, error is a string\n"
            "    try:\n"
            "        err_result = safe_get('http://localhost:9999/')\n"
            "        assert err_result['status'] is None, \\\n"
            "            f\"expected status=None on connection error, got {err_result['status']}\"\n"
            "        assert isinstance(err_result['error'], str) and err_result['error'], \\\n"
            "            'error should be a non-empty string'\n"
            "        passed += 1; print('\\u2705 Check 4: connection error returns status=None with error string')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: success data is non-empty\n"
            "    try:\n"
            "        assert ok_result is not None and ok_result['data'] is not None, \\\n"
            "            'data is None (Check 3 failed)'\n"
            "        assert len(ok_result['data']) > 0, 'data should be non-empty'\n"
            "        passed += 1; print('\\u2705 Check 5: success data is non-empty')\n"
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
            + SAFE_GET_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 05 — ai_analyze_results
# ---------------------------------------------------------------------------

def ex05():
    global _cid; _cid = 400
    return [
        md(
            "# Day 022 — Exercise 5: ai_analyze_results\n\n"
            "**What you'll build:** `ai_analyze_results(records, question, model)` — passes "
            "a list of API records (as JSON) to the LLM and returns a natural-language "
            "answer to any question about them.\n\n"
            "**Why it matters:** Raw API data is structured but dense. An LLM can answer "
            "plain-English questions about it instantly — turning any API response "
            "into an intelligent assistant with a few lines of code."
        ),
        code("import ollama\nimport json"),
        md("## Your Implementation"),
        code(
            "def ai_analyze_results(records: list[dict], question: str, model: str = \"llama3.2\") -> str:\n"
            '    """\n'
            "    Ask the LLM a question about a list of API records.\n\n"
            "    Args:\n"
            "        records:  List of dicts from an API response.\n"
            "        question: Plain-English question to answer about the data.\n"
            "        model:    Ollama model name.\n\n"
            "    Returns:\n"
            "        LLM answer as a string.\n"
            "        Works on an empty records list (returns a string, never raises).\n"
            '    """\n'
            "    # TODO: summary = json.dumps(records[:5], indent=2)  # cap at 5 records\n"
            "    # TODO: call ollama.chat with system='data analyst' and\n"
            "    #       user=f'Data:\\n{summary}\\n\\nQuestion: {question}'\n"
            "    # TODO: return response['message']['content']\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "SAMPLE_RECORDS = [\n"
            "    {'id': 1, 'userId': 1, 'title': 'Introduction to Python', 'body': 'Python is easy to learn.'},\n"
            "    {'id': 2, 'userId': 1, 'title': 'Machine Learning Basics', 'body': 'ML uses data to find patterns.'},\n"
            "    {'id': 3, 'userId': 2, 'title': 'Web Development Tips', 'body': 'Use frameworks to save time.'},\n"
            "]\n"
            "\n"
            "\n"
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'ai_analyze_results' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: ai_analyze_results defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    result = None\n"
            "\n"
            "    # Check 2: returns a string (1 LLM call)\n"
            "    try:\n"
            "        result = ai_analyze_results(SAMPLE_RECORDS, 'How many records are there?')\n"
            "        assert isinstance(result, str), \\\n"
            "            f'expected str, got {type(result)}'\n"
            "        passed += 1; print('\\u2705 Check 2: returns a string')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: result is non-empty\n"
            "    try:\n"
            "        assert result is not None, 'result is None (Check 2 failed)'\n"
            "        assert len(result) > 0, 'result string is empty'\n"
            "        passed += 1; print('\\u2705 Check 3: result is non-empty')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: result is a meaningful length (> 10 chars)\n"
            "    try:\n"
            "        assert result is not None, 'result is None'\n"
            "        assert len(result) > 10, \\\n"
            "            f'result too short ({len(result)} chars): {result!r}'\n"
            "        passed += 1; print(f'\\u2705 Check 4: result has {len(result)} chars')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: works on empty records (no crash; 1 LLM call)\n"
            "    try:\n"
            "        empty_result = ai_analyze_results([], 'How many records?')\n"
            "        assert isinstance(empty_result, str), \\\n"
            "            f'expected str for empty records, got {type(empty_result)}'\n"
            "        passed += 1; print('\\u2705 Check 5: works on empty records list')\n"
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
            + AI_ANALYZE_RESULTS_IMPL + "\n"
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
            "# Day 022 Project: REST API Client\n\n"
            "## What You're Building\n\n"
            "A `PostsAPI` class that wraps [JSONPlaceholder](https://jsonplaceholder.typicode.com) "
            "— a free, always-available fake REST API used by millions of developers for testing. "
            "The same patterns you apply here work for any real API: GitHub, Stripe, Notion, Spotify.\n\n"
            "## Project Requirements\n\n"
            "1. Implement `PostsAPI` with a `requests.Session` and auth headers\n"
            "2. `get_posts(user_id, limit)` — fetch posts, optionally filtered by user\n"
            "3. `get_pages(page_size, max_pages)` — collect paginated results\n"
            "4. `ai_summary(question)` — fetch posts and ask the LLM about them\n"
            "5. `safe_fetch(endpoint)` — fetch any endpoint safely (no raise)\n\n"
            "**You run it, it prints post titles, user stats, and an AI summary. "
            "That's the deliverable.**"
        ),
        code(
            "import requests\n"
            "import json\n"
            "import ollama"
        ),
        md("## Provided: All Helper Functions"),
        code(ALL_IMPLS),
        md(
            "## Your Implementation\n\n"
            "Implement `PostsAPI` using the helper functions above. "
            "Use `requests.Session()` for connection reuse and persistent auth headers."
        ),
        code(
            f'JPH_BASE = "{JPH_BASE}"\n'
            "\n"
            "\n"
            "class PostsAPI:\n"
            "    BASE = JPH_BASE\n"
            "\n"
            "    def __init__(self, api_key: str = 'demo'):\n"
            "        # TODO: self.session = requests.Session()\n"
            "        # TODO: self.session.headers.update(build_headers(api_key))\n"
            "        pass\n"
            "\n"
            "    def get_posts(self, user_id: int | None = None, limit: int = 10) -> list[dict]:\n"
            "        # TODO: build params dict {'_limit': limit} + optionally {'userId': user_id}\n"
            "        # TODO: self.session.get(url, params=params, timeout=10).raise_for_status()\n"
            "        # TODO: return response.json()\n"
            "        pass\n"
            "\n"
            "    def get_pages(self, page_size: int = 5, max_pages: int = 3) -> list[dict]:\n"
            "        # TODO: return paginate_collect(f'{self.BASE}/posts', page_size, max_pages)\n"
            "        pass\n"
            "\n"
            "    def ai_summary(self, question: str, limit: int = 5) -> str:\n"
            "        # TODO: posts = self.get_posts(limit=limit)\n"
            "        # TODO: return ai_analyze_results(posts, question)\n"
            "        pass\n"
            "\n"
            "    def safe_fetch(self, endpoint: str) -> dict:\n"
            "        # TODO: return safe_get(f'{self.BASE}/{endpoint}')\n"
            "        pass"
        ),
        md("## Use Your Client"),
        code(
            "# 1. Create the client\n"
            "# client = PostsAPI()\n"
            "\n"
            "# 2. Fetch 5 posts and print their titles\n"
            "# posts = client.get_posts(limit=5)\n"
            "# for p in posts:\n"
            "#     print(f\"  [{p['id']}] {p['title']}\")\n"
        ),
        code(
            "# 3. Filter to user 1's posts\n"
            "# user_posts = client.get_posts(user_id=1, limit=3)\n"
            "# print(f'User 1 has {len(user_posts)} posts (limited to 3)')\n"
        ),
        code(
            "# 4. Collect 2 pages of 5\n"
            "# pages = client.get_pages(page_size=5, max_pages=2)\n"
            "# print(f'Paginated: {len(pages)} total posts')\n"
        ),
        code(
            "# 5. AI summary\n"
            "# summary = client.ai_summary('What topics or themes appear in these posts?')\n"
            "# print('AI Summary:')\n"
            "# print(summary)\n"
        ),
        md("## Checks"),
        code(
            "def _run_project_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: PostsAPI class defined with required methods\n"
            "    try:\n"
            "        assert 'PostsAPI' in globals(), 'PostsAPI not defined'\n"
            "        for method in ('get_posts', 'get_pages', 'ai_summary', 'safe_fetch'):\n"
            "            assert hasattr(PostsAPI, method), f'PostsAPI missing method: {method}'\n"
            "        passed += 1; print('\\u2705 Check 1: PostsAPI class has all required methods')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "\n"
            "    # Check 2: client is a PostsAPI instance\n"
            "    try:\n"
            "        assert 'client' in globals(), 'client not defined'\n"
            "        assert isinstance(client, PostsAPI), \\\n"
            "            f'client should be PostsAPI, got {type(client)}'\n"
            "        passed += 1; print('\\u2705 Check 2: client is a PostsAPI instance')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: posts is a list with dicts containing 'id' and 'title'\n"
            "    try:\n"
            "        assert 'posts' in globals(), 'posts not defined'\n"
            "        assert isinstance(posts, list) and len(posts) >= 1, \\\n"
            "            f'posts should be non-empty list, got {posts!r}'\n"
            "        assert 'id' in posts[0] and 'title' in posts[0], \\\n"
            "            f\"posts items missing 'id'/'title': {list(posts[0])}\"\n"
            "        passed += 1; print(f'\\u2705 Check 3: posts has {len(posts)} items with id/title')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: pages has more items than a single page\n"
            "    try:\n"
            "        assert 'pages' in globals(), 'pages not defined'\n"
            "        assert isinstance(pages, list), f'pages must be list, got {type(pages)}'\n"
            "        assert len(pages) >= 6, \\\n"
            "            f'pages should have >= 6 items (at least 2 pages), got {len(pages)}'\n"
            "        passed += 1; print(f'\\u2705 Check 4: pages has {len(pages)} items (multiple pages)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: summary is a non-empty string\n"
            "    try:\n"
            "        assert 'summary' in globals(), 'summary not defined'\n"
            "        assert isinstance(summary, str) and len(summary) > 10, \\\n"
            "            f'summary should be non-empty string, got {summary!r}'\n"
            "        passed += 1; print(f'\\u2705 Check 5: summary is a {len(summary)}-char string')\n"
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
            "- Add `get_comments(post_id)` that fetches `/posts/{id}/comments` using the session\n"
            "- Add retry logic inside `get_posts`: if the response status is 429, wait and retry\n"
            "- Replace `PostsAPI.BASE` with a real public API you care about "
            "(e.g. Open Library, REST Countries, PokeAPI)\n"
            "- Use `safe_fetch` to gracefully handle a non-existent endpoint "
            "and log the error to a file\n"
            "- Extend `ai_summary` to accept a `user_id` filter and summarise "
            "only that user's posts"
        ),
    ]


# ---------------------------------------------------------------------------
# Solution notebook (executed by gate — must run clean)
# ---------------------------------------------------------------------------

def solution_nb():
    global _cid; _cid = 600

    solution_imports_and_impls = (
        "import requests\n"
        "import json\n"
        "import ollama\n"
        "\n"
        "\n"
        + ALL_IMPLS
        + "\n"
        "\n"
        "\n"
        + POSTS_API_IMPL
    )

    return [
        md(
            "# Day 022 Project Solution — REST API Client\n\n"
            "A `PostsAPI` client wrapping JSONPlaceholder with auth headers, "
            "pagination, safe error handling, and AI analysis."
        ),
        code(solution_imports_and_impls),
        md("## Action 1 — Fetch 5 Posts and Print Titles"),
        code(
            "client = PostsAPI(api_key='demo')\n"
            "posts = client.get_posts(limit=5)\n"
            "print(f'Fetched {len(posts)} posts:')\n"
            "for p in posts:\n"
            "    print(f\"  [{p['id']}] {p['title']}\")"
        ),
        md("## Action 2 — Filter by User and Paginate"),
        code(
            "user_posts = client.get_posts(user_id=1, limit=3)\n"
            "print(f'\\nUser 1 posts (limited to 3): {len(user_posts)}')\n"
            "for p in user_posts:\n"
            "    print(f\"  userId={p['userId']} | {p['title'][:50]}\")\n"
            "\n"
            "pages = client.get_pages(page_size=5, max_pages=2)\n"
            "print(f'\\nPaginated (2 pages x 5): {len(pages)} total items')"
        ),
        md("## Action 3 — AI Summary"),
        code(
            "summary = client.ai_summary(\n"
            "    'What topics or themes appear across these posts? Give a one-paragraph overview.',\n"
            "    limit=5,\n"
            ")\n"
            "print('\\nAI Summary:')\n"
            "print(summary)"
        ),
        md("## Safe Fetch Demo"),
        code(
            "good = client.safe_fetch('posts/1')\n"
            "bad  = client.safe_fetch('nonexistent/endpoint')\n"
            "print(f'\\nSafe fetch /posts/1  -> status={good[\"status\"]}, error={good[\"error\"]}')\n"
            "print(f'Safe fetch /nonexist -> status={bad[\"status\"]},  error={str(bad[\"error\"])[:40]!r}')\n"
            "print('\\nDemo complete!')"
        ),
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Generating Day 022 notebooks...")
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
