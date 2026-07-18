#!/usr/bin/env python3
"""Generate all Day 035 notebooks: exercises 1-5, project, solution."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAY_DIR = ROOT / "02_automation" / "day_035"

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

FETCH_TEXT_IMPL = """\
import requests
from pathlib import Path

def fetch_text(source: str) -> dict:
    src  = str(source)
    text = None
    kind = 'text'

    if src.startswith('http://') or src.startswith('https://'):
        try:
            response = requests.get(src, timeout=10)
            response.raise_for_status()
            text = response.text
            kind = 'url'
        except Exception as e:
            text = '[fetch error: ' + str(e) + ']'
            kind = 'url_error'
    else:
        try:
            p = Path(src)
            if p.exists() and p.is_file():
                text = p.read_text(encoding='utf-8')
                kind = 'file'
        except Exception:
            pass

    if text is None:
        text = src
        kind = 'text'

    return {
        'source':     src,
        'kind':       kind,
        'content':    text,
        'char_count': len(text),
    }"""

EXTRACT_INFO_IMPL = """\
import json
import ollama
from pydantic import BaseModel, Field

class ArticleInfo(BaseModel):
    title:      str       = Field(description='Topic or title in 3-6 words')
    summary:    str       = Field(description='One sentence summary')
    sentiment:  str       = Field(description='positive, negative, or neutral')
    key_points: list[str] = Field(default_factory=list,
                                  description='Up to 3 key points as short phrases')

def extract_info(doc: dict, model: str = 'llama3.2') -> dict:
    schema = ArticleInfo.model_json_schema()
    prompt = (
        'Extract information from the document below. '
        'Return valid JSON matching this schema:\\n'
        + json.dumps(schema, indent=2)
        + '\\n\\nDocument:\\n' + doc['content'][:1500]
    )
    try:
        response = ollama.chat(
            model=model,
            messages=[{'role': 'user', 'content': prompt}],
            format='json',
        )
        info = ArticleInfo.model_validate_json(response['message']['content'])
        return {**doc, 'info': info.model_dump(), 'status': 'ok',    'error': None}
    except Exception as e:
        return {**doc, 'info': None,               'status': 'error', 'error': str(e)}"""

ASYNC_EXTRACT_IMPL = """\
import asyncio
import json
import ollama

async def async_extract(doc: dict, model: str = 'llama3.2') -> dict:
    client = ollama.AsyncClient()
    schema = ArticleInfo.model_json_schema()
    prompt = (
        'Extract information from the document below. '
        'Return valid JSON matching this schema:\\n'
        + json.dumps(schema, indent=2)
        + '\\n\\nDocument:\\n' + doc['content'][:1500]
    )
    try:
        response = await client.chat(
            model=model,
            messages=[{'role': 'user', 'content': prompt}],
            format='json',
        )
        info = ArticleInfo.model_validate_json(response['message']['content'])
        return {**doc, 'info': info.model_dump(), 'status': 'ok',    'error': None}
    except Exception as e:
        return {**doc, 'info': None,               'status': 'error', 'error': str(e)}"""

BATCH_EXTRACT_IMPL = """\
async def batch_extract(docs: list, max_concurrent: int = 3,
                        model: str = 'llama3.2') -> list[dict]:
    if not docs:
        return []
    sem = asyncio.Semaphore(max_concurrent)
    async def _run(doc):
        async with sem:
            return await async_extract(doc, model)
    return list(await asyncio.gather(*[_run(d) for d in docs]))"""

GENERATE_DIGEST_IMPL = """\
import ollama

def generate_digest(results: list, model: str = 'llama3.2') -> str:
    ok     = [r for r in results if r.get('status') == 'ok']
    errors = [r for r in results if r.get('status') == 'error']
    if not ok:
        return 'No articles extracted successfully (' + str(len(errors)) + ' errors).'
    lines = [
        '=== Auto-Analyst Digest ===',
        str(len(results)) + ' sources processed: '
        + str(len(ok)) + ' ok, ' + str(len(errors)) + ' failed.\\n',
    ]
    for i, r in enumerate(ok, 1):
        info      = r.get('info') or {}
        title     = info.get('title',     'Untitled')
        summary   = info.get('summary',   '')
        sentiment = info.get('sentiment', 'unknown')
        kp        = info.get('key_points', [])
        kp_text   = '; '.join(kp[:3]) if kp else ''
        lines.append('[' + str(i) + '] ' + title + '  [' + sentiment + ']')
        lines.append('    ' + summary)
        if kp_text:
            lines.append('    Key points: ' + kp_text)
        lines.append('')
    context  = '\\n'.join(lines)
    prompt   = (
        context + '\\n\\n'
        'Write a 3-4 sentence editorial digest identifying '
        'the main themes, patterns, and key insights across all articles.'
    )
    response = ollama.chat(
        model=model,
        messages=[{'role': 'user', 'content': prompt}],
    )
    return response['message']['content']"""

DIGEST_PIPELINE_IMPL = """\
import asyncio

class DigestPipeline:
    def __init__(self, model: str = 'llama3.2', max_concurrent: int = 3):
        self.model          = model
        self.max_concurrent = max_concurrent
        self._sources: list = []

    def add_source(self, source) -> 'DigestPipeline':
        self._sources.append(source)
        return self

    async def process(self) -> dict:
        docs     = [fetch_text(s) for s in self._sources]
        results  = await batch_extract(docs, self.max_concurrent, self.model)
        digest   = generate_digest(results, self.model)
        ok_count = sum(1 for r in results if r.get('status') == 'ok')
        return {
            'source_count': len(docs),
            'ok_count':     ok_count,
            'results':      results,
            'digest':       digest,
        }

    def run(self) -> dict:
        return asyncio.run(self.process())"""

# Ordered subsets used in exercise setup cells
_BEFORE_ASYNC  = "\n\n\n".join([FETCH_TEXT_IMPL, EXTRACT_INFO_IMPL])
_BEFORE_BATCH  = "\n\n\n".join([FETCH_TEXT_IMPL, EXTRACT_INFO_IMPL, ASYNC_EXTRACT_IMPL])
_BEFORE_DIGEST = "\n\n\n".join([
    FETCH_TEXT_IMPL, EXTRACT_INFO_IMPL, ASYNC_EXTRACT_IMPL, BATCH_EXTRACT_IMPL,
])
ALL_IMPLS = "\n\n\n".join([
    FETCH_TEXT_IMPL, EXTRACT_INFO_IMPL, ASYNC_EXTRACT_IMPL,
    BATCH_EXTRACT_IMPL, GENERATE_DIGEST_IMPL,
])


# ---------------------------------------------------------------------------
# Exercise 01 — fetch_text
# ---------------------------------------------------------------------------

def ex01():
    global _cid; _cid = 0
    return [
        md(
            "# Day 035 — Exercise 1: fetch_text\n\n"
            "**What you'll build:** `fetch_text(source: str) -> dict` — load content from "
            "a URL (`requests.get`), a local file (`Path.read_text`), or a raw text string. "
            "Always returns `{source, kind, content, char_count}`.\n\n"
            "**Why it matters:** A pipeline that accepts only one input type breaks as soon as "
            "sources change. `fetch_text` hides the complexity so every downstream stage "
            "receives the same dict regardless of where the content came from."
        ),
        md("## Your Implementation"),
        code(
            "import requests\n"
            "from pathlib import Path\n"
            "\n"
            "def fetch_text(source: str) -> dict:\n"
            '    """\n'
            "    Fetch text from a URL, file path, or raw string.\n\n"
            "    Returns dict with keys: source, kind, content, char_count.\n"
            "    kind is one of: 'url', 'url_error', 'file', 'text'.\n"
            '    """\n'
            "    src  = str(source)\n"
            "    text = None\n"
            "    kind = 'text'\n"
            "\n"
            "    # TODO: if src starts with 'http://' or 'https://':\n"
            "    #     try: response = requests.get(src, timeout=10)\n"
            "    #          response.raise_for_status()\n"
            "    #          text = response.text; kind = 'url'\n"
            "    #     except Exception as e: text = '[fetch error: ...]'; kind = 'url_error'\n"
            "    # else:\n"
            "    #     try: p = Path(src)\n"
            "    #          if p.exists() and p.is_file(): text = p.read_text(...); kind = 'file'\n"
            "    #     except Exception: pass\n"
            "\n"
            "    # TODO: if text is None: text = src; kind = 'text'\n"
            "\n"
            "    # TODO: return {'source': src, 'kind': kind,\n"
            "    #               'content': text, 'char_count': len(text)}\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: defined, returns dict with correct keys\n"
            "    try:\n"
            "        assert 'fetch_text' in globals()\n"
            "        result = fetch_text('hello world')\n"
            "        assert isinstance(result, dict), f'expected dict, got {type(result).__name__}'\n"
            "        for k in ('source', 'kind', 'content', 'char_count'):\n"
            "            assert k in result, f'missing key: {k}'\n"
            "        passed += 1; print('\\u2705 Check 1: fetch_text returns dict with all 4 keys')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: raw text — content == source, kind == 'text'\n"
            "    try:\n"
            "        doc = fetch_text('Python is great')\n"
            "        assert doc['content'] == 'Python is great', f'content: {doc[\"content\"]!r}'\n"
            "        assert doc['kind']    == 'text',            f'kind: {doc[\"kind\"]!r}'\n"
            "        assert doc['source']  == 'Python is great', f'source: {doc[\"source\"]!r}'\n"
            "        passed += 1; print('\\u2705 Check 2: raw text → content=source, kind=text')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: char_count == len(content)\n"
            "    try:\n"
            "        doc = fetch_text('Hello')\n"
            "        assert doc['char_count'] == 5, \\\n"
            "            f'char_count should be 5, got {doc[\"char_count\"]}'\n"
            "        assert doc['char_count'] == len(doc['content']), \\\n"
            "            'char_count != len(content)'\n"
            "        passed += 1; print('\\u2705 Check 3: char_count == len(content)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: non-existent path treated as raw text\n"
            "    try:\n"
            "        doc = fetch_text('/nonexistent/path/no_file.txt')\n"
            "        assert doc['content'] == '/nonexistent/path/no_file.txt', \\\n"
            "            f'expected path as content, got: {doc[\"content\"]!r}'\n"
            "        assert doc['kind'] in ('text', 'file'), \\\n"
            "            f'kind should be text (file not found), got: {doc[\"kind\"]!r}'\n"
            "        passed += 1; print('\\u2705 Check 4: non-existent path treated as raw text')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: source field preserved exactly\n"
            "    try:\n"
            "        src = 'The quick brown fox'\n"
            "        doc = fetch_text(src)\n"
            "        assert doc['source'] == src, \\\n"
            "            f'source should equal input, got: {doc[\"source\"]!r}'\n"
            "        passed += 1; print('\\u2705 Check 5: source field preserves original input')\n"
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
            + FETCH_TEXT_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 02 — extract_info
# ---------------------------------------------------------------------------

def ex02():
    global _cid; _cid = 100
    return [
        md(
            "# Day 035 — Exercise 2: extract_info\n\n"
            "**What you'll build:** `extract_info(doc, model) -> dict` — use Pydantic + "
            "`format='json'` to extract `ArticleInfo` (title, summary, sentiment, key_points) "
            "from a document dict. Returns an error envelope `{status, info, error}` — never raises.\n\n"
            "**Why it matters:** Schema-guided extraction (Day 4/9 pattern) applied to a pipeline "
            "stage. The error envelope means the batch layer never has to catch exceptions — it just "
            "checks the `status` key."
        ),
        md("## Provided: ArticleInfo Pydantic Model"),
        code(
            "import json\n"
            "import ollama\n"
            "from pydantic import BaseModel, Field\n"
            "\n"
            "class ArticleInfo(BaseModel):\n"
            "    title:      str       = Field(description='Topic or title in 3-6 words')\n"
            "    summary:    str       = Field(description='One sentence summary')\n"
            "    sentiment:  str       = Field(description='positive, negative, or neutral')\n"
            "    key_points: list[str] = Field(default_factory=list,\n"
            "                                  description='Up to 3 key points as short phrases')"
        ),
        md("## Provided: fetch_text (to create test docs)"),
        code(FETCH_TEXT_IMPL),
        md("## Your Implementation"),
        code(
            "def extract_info(doc: dict, model: str = 'llama3.2') -> dict:\n"
            '    """\n'
            "    Extract structured info from a doc dict using ArticleInfo schema.\n\n"
            "    Returns error envelope: always a dict with 'status', 'info', 'error'.\n"
            "    On success:  {**doc, 'info': ArticleInfo.model_dump(), 'status': 'ok',    'error': None}\n"
            "    On failure:  {**doc, 'info': None,                    'status': 'error', 'error': str(e)}\n"
            '    """\n'
            "    schema = ArticleInfo.model_json_schema()\n"
            "    prompt = (\n"
            "        'Extract information from the document below. '\n"
            "        'Return valid JSON matching this schema:\\n'\n"
            "        + json.dumps(schema, indent=2)\n"
            "        + '\\n\\nDocument:\\n' + doc['content'][:1500]\n"
            "    )\n"
            "    # TODO: try:\n"
            "    #     response = ollama.chat(model=model, messages=[...], format='json')\n"
            "    #     info = ArticleInfo.model_validate_json(response['message']['content'])\n"
            "    #     return {**doc, 'info': info.model_dump(), 'status': 'ok', 'error': None}\n"
            "    # TODO: except Exception as e:\n"
            "    #     return {**doc, 'info': None, 'status': 'error', 'error': str(e)}\n"
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
            "        assert 'extract_info' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: extract_info defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Pre-run: call extract_info once for all checks\n"
            "    doc = fetch_text('Python is a popular high-level programming language known '\n"
            "                     'for its clean syntax and large ecosystem.')\n"
            "    result = None\n"
            "    try:\n"
            "        result = extract_info(doc)\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c extract_info raised unexpectedly: {e}')\n"
            "        print('(extract_info should return an error envelope, not raise)')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: returns dict with status, info, error keys\n"
            "    try:\n"
            "        assert isinstance(result, dict), f'expected dict, got {type(result).__name__}'\n"
            "        for k in ('source', 'kind', 'content', 'char_count', 'status', 'info', 'error'):\n"
            "            assert k in result, f'missing key: {k}'\n"
            "        passed += 1; print(f'\\u2705 Check 2: result has all required keys')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: original doc keys preserved\n"
            "    try:\n"
            "        assert result['source']     == doc['source']\n"
            "        assert result['content']    == doc['content']\n"
            "        assert result['char_count'] == doc['char_count']\n"
            "        passed += 1; print('\\u2705 Check 3: original doc fields preserved')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: status is 'ok' or 'error' (never missing)\n"
            "    try:\n"
            "        assert result['status'] in ('ok', 'error'), \\\n"
            "            f\"status must be 'ok' or 'error', got {result['status']!r}\"\n"
            "        passed += 1; print(f\"\\u2705 Check 4: status={result['status']!r}\")\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: if ok, info is a dict with all ArticleInfo fields\n"
            "    try:\n"
            "        if result['status'] == 'ok':\n"
            "            info = result['info']\n"
            "            assert isinstance(info, dict), f'info should be dict, got {type(info).__name__}'\n"
            "            for k in ('title', 'summary', 'sentiment', 'key_points'):\n"
            "                assert k in info, f'info missing field: {k}'\n"
            "            assert isinstance(info['key_points'], list), \\\n"
            "                f'key_points should be list, got {type(info[\"key_points\"]).__name__}'\n"
            "            passed += 1; print(f\"\\u2705 Check 5: info dict has title={info['title']!r}, \"\n"
            "                               f\"sentiment={info['sentiment']!r}\")\n"
            "        else:\n"
            "            assert result['error'] is not None, \\\n"
            "                'status=error but error field is None'\n"
            "            passed += 1; print(f\"\\u2705 Check 5: status=error, error={result['error']!r}\")\n"
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
            + EXTRACT_INFO_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 03 — batch_extract (async)
# ---------------------------------------------------------------------------

def ex03():
    global _cid; _cid = 200
    return [
        md(
            "# Day 035 — Exercise 3: batch_extract\n\n"
            "**What you'll build:** `async def batch_extract(docs, max_concurrent=3, model) -> list[dict]` — "
            "run `async_extract` concurrently on all docs using `asyncio.Semaphore` + `asyncio.gather`.\n\n"
            "**Why it matters:** The concurrency layer. With `max_concurrent=3`, three LLM extractions "
            "run simultaneously — batching 10 documents takes roughly the same wall time as batching 3 "
            "serially. Check cells use top-level `await`."
        ),
        md("## Provided: All Functions up to async_extract"),
        code(_BEFORE_BATCH),
        md("## Your Implementation"),
        code(
            "async def batch_extract(docs: list, max_concurrent: int = 3,\n"
            "                        model: str = 'llama3.2') -> list[dict]:\n"
            '    """\n'
            "    Run async_extract concurrently on all docs with a semaphore.\n\n"
            "    Returns a list of dicts of the same length as docs — each is\n"
            "    the error envelope returned by async_extract.\n"
            '    """\n'
            "    # TODO: if not docs: return []\n"
            "    # TODO: sem = asyncio.Semaphore(max_concurrent)\n"
            "    # TODO: async def _run(doc):\n"
            "    #     async with sem:\n"
            "    #         return await async_extract(doc, model)\n"
            "    # TODO: return list(await asyncio.gather(*[_run(d) for d in docs]))\n"
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
            "    # Check 1: defined and is a coroutine function\n"
            "    try:\n"
            "        assert 'batch_extract' in globals()\n"
            "        assert asyncio.iscoroutinefunction(batch_extract), \\\n"
            "            'batch_extract must be async def'\n"
            "        passed += 1; print('\\u2705 Check 1: batch_extract is async def')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: empty input\n"
            "    try:\n"
            "        result = await batch_extract([])\n"
            "        assert result == [], f'expected [], got {result}'\n"
            "        passed += 1; print('\\u2705 Check 2: batch_extract([]) returns []')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Pre-run 2 docs for checks 3-5\n"
            "    docs = [\n"
            "        fetch_text('Python is a popular programming language for data science and AI.'),\n"
            "        fetch_text('Machine learning uses statistical methods to find patterns in data.'),\n"
            "    ]\n"
            "    results = None\n"
            "    try:\n"
            "        results = await batch_extract(docs)\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c batch_extract call failed: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 3: result length == input length\n"
            "    try:\n"
            "        assert len(results) == 2, f'expected 2 results, got {len(results)}'\n"
            "        passed += 1; print(f'\\u2705 Check 3: 2 docs \\u2192 2 results')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: each result has status key\n"
            "    try:\n"
            "        for r in results:\n"
            "            assert 'status' in r, f'missing status key in result'\n"
            "            assert r['status'] in ('ok', 'error'), \\\n"
            "                f\"invalid status: {r['status']!r}\"\n"
            "        passed += 1; print('\\u2705 Check 4: all results have status key')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: ok results have info dict\n"
            "    try:\n"
            "        ok = [r for r in results if r['status'] == 'ok']\n"
            "        assert ok, 'no successful extractions (is Ollama running?)'\n"
            "        for r in ok:\n"
            "            info = r.get('info', {})\n"
            "            assert isinstance(info, dict), f'info should be dict, got {type(info).__name__}'\n"
            "            for k in ('title', 'summary', 'sentiment'):\n"
            "                assert k in info, f'info missing: {k}'\n"
            "        passed += 1; print(f'\\u2705 Check 5: ok results have info dict '\n"
            "                           f'(title, summary, sentiment) — {len(ok)}/{len(results)} ok')\n"
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
            + BATCH_EXTRACT_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 04 — generate_digest
# ---------------------------------------------------------------------------

def ex04():
    global _cid; _cid = 300
    return [
        md(
            "# Day 035 — Exercise 4: generate_digest\n\n"
            "**What you'll build:** `generate_digest(results, model) -> str` — filter the batch "
            "results to successful ones, format a numbered context block, and call the LLM once "
            "to write a 3-4 sentence editorial digest.\n\n"
            "**Why it matters:** The delivery layer. All the extraction work feeds into one "
            "synthesis call that produces a human-readable output — the digest a user would "
            "actually read each morning."
        ),
        md("## Provided: All Functions up to batch_extract"),
        code(_BEFORE_DIGEST),
        md("## Provided: Sample Results (for checks)"),
        code(
            "SAMPLE_RESULTS = [\n"
            "    {\n"
            "        'source': 'python.txt', 'kind': 'text',\n"
            "        'content': 'Python is a popular language.', 'char_count': 29,\n"
            "        'info': {\n"
            "            'title': 'Python programming language',\n"
            "            'summary': 'Python is widely used in data science and AI.',\n"
            "            'sentiment': 'positive',\n"
            "            'key_points': ['high-level syntax', 'large ecosystem', 'used in AI'],\n"
            "        },\n"
            "        'status': 'ok', 'error': None,\n"
            "    },\n"
            "    {\n"
            "        'source': 'ml.txt', 'kind': 'text',\n"
            "        'content': 'ML uses stats.', 'char_count': 15,\n"
            "        'info': {\n"
            "            'title': 'Machine learning basics',\n"
            "            'summary': 'Machine learning finds patterns in data using statistics.',\n"
            "            'sentiment': 'neutral',\n"
            "            'key_points': ['statistical methods', 'pattern recognition'],\n"
            "        },\n"
            "        'status': 'ok', 'error': None,\n"
            "    },\n"
            "    {\n"
            "        'source': 'bad.txt', 'kind': 'text',\n"
            "        'content': 'bad', 'char_count': 3,\n"
            "        'info': None, 'status': 'error', 'error': 'validation failed',\n"
            "    },\n"
            "]"
        ),
        md("## Your Implementation"),
        code(
            "import ollama\n"
            "\n"
            "def generate_digest(results: list, model: str = 'llama3.2') -> str:\n"
            '    """\n'
            "    Synthesise a digest from batch_extract results.\n\n"
            "    Filter ok results, format a numbered context block, call ollama.chat once,\n"
            "    return the editorial digest string.\n"
            '    """\n'
            "    ok     = [r for r in results if r.get('status') == 'ok']\n"
            "    errors = [r for r in results if r.get('status') == 'error']\n"
            "\n"
            "    # TODO: if not ok: return 'No articles extracted successfully (N errors).'\n"
            "\n"
            "    # TODO: Build lines list:\n"
            "    #   header line: '=== Auto-Analyst Digest ==='\n"
            "    #   count line: 'N sources processed: M ok, K failed.'\n"
            "    #   for i, r in enumerate(ok, 1):\n"
            "    #       info = r.get('info') or {}\n"
            "    #       title, summary, sentiment, kp = info.get(...)\n"
            "    #       lines: '[i] title [sentiment]', '    summary', '    Key points: ...' (if any)\n"
            "    #       append '' for blank line between entries\n"
            "\n"
            "    # TODO: context = '\\n'.join(lines)\n"
            "    # TODO: prompt = context + '\\n\\nWrite a 3-4 sentence editorial digest...'\n"
            "    # TODO: response = ollama.chat(model=model, messages=[...])\n"
            "    # TODO: return response['message']['content']\n"
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
            "        assert 'generate_digest' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: generate_digest defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: empty input returns non-empty string (early return)\n"
            "    try:\n"
            "        r0 = generate_digest([])\n"
            "        assert isinstance(r0, str) and r0.strip(), \\\n"
            "            'generate_digest([]) should return a non-empty string'\n"
            "        passed += 1; print(f'\\u2705 Check 2: generate_digest([]) returns str: {r0!r}')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: all-error input returns without LLM call\n"
            "    try:\n"
            "        err_results = [r for r in SAMPLE_RESULTS if r['status'] == 'error']\n"
            "        r_err = generate_digest(err_results)\n"
            "        assert isinstance(r_err, str) and r_err.strip()\n"
            "        passed += 1; print(f'\\u2705 Check 3: all-error input returns str without LLM call')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: SAMPLE_RESULTS returns non-empty string (1 LLM call)\n"
            "    try:\n"
            "        digest = generate_digest(SAMPLE_RESULTS)\n"
            "        assert isinstance(digest, str), f'expected str, got {type(digest).__name__}'\n"
            "        assert len(digest.strip()) >= 50, \\\n"
            "            f'digest too short: {len(digest)} chars'\n"
            "        passed += 1; print(f'\\u2705 Check 4: returns substantive digest ({len(digest)} chars)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: handles mixed ok/error without crashing\n"
            "    try:\n"
            "        r5 = generate_digest(SAMPLE_RESULTS)\n"
            "        assert isinstance(r5, str) and r5.strip()\n"
            "        passed += 1; print('\\u2705 Check 5: mixed ok/error results handled gracefully')\n"
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
            + GENERATE_DIGEST_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 05 — DigestPipeline
# ---------------------------------------------------------------------------

def ex05():
    global _cid; _cid = 400
    return [
        md(
            "# Day 035 — Exercise 5: DigestPipeline\n\n"
            "**What you'll build:** The `DigestPipeline` class — `add_source(source) -> DigestPipeline` "
            "(fluent builder), `async process() -> dict` (fetch → batch_extract → generate_digest), "
            "`run() -> dict` (asyncio.run wrapper for scripts).\n\n"
            "**Why it matters:** The assembled capstone class. Every pipeline stage is composed here "
            "into a reusable object. `await pipeline.process()` in notebooks; `pipeline.run()` in scripts."
        ),
        md("## Provided: All Helper Functions"),
        code(ALL_IMPLS),
        md("## Your Implementation"),
        code(
            "import asyncio\n"
            "\n"
            "class DigestPipeline:\n"
            '    """\n'
            "    End-to-end Auto-Analyst pipeline:\n"
            "      add_source → process/run → {source_count, ok_count, results, digest}\n"
            '    """\n'
            "\n"
            "    def __init__(self, model: str = 'llama3.2', max_concurrent: int = 3):\n"
            "        # TODO: self.model = model\n"
            "        # TODO: self.max_concurrent = max_concurrent\n"
            "        # TODO: self._sources: list = []\n"
            "        pass\n"
            "\n"
            "    def add_source(self, source) -> 'DigestPipeline':\n"
            "        # TODO: self._sources.append(source)\n"
            "        # TODO: return self\n"
            "        pass\n"
            "\n"
            "    async def process(self) -> dict:\n"
            "        # TODO: docs    = [fetch_text(s) for s in self._sources]\n"
            "        # TODO: results = await batch_extract(docs, self.max_concurrent, self.model)\n"
            "        # TODO: digest  = generate_digest(results, self.model)\n"
            "        # TODO: ok_count = sum(1 for r in results if r.get('status') == 'ok')\n"
            "        # TODO: return {'source_count': len(docs), 'ok_count': ok_count,\n"
            "        #               'results': results, 'digest': digest}\n"
            "        pass\n"
            "\n"
            "    def run(self) -> dict:\n"
            "        # TODO: return asyncio.run(self.process())\n"
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
            "    # Check 1: class defined with correct methods\n"
            "    try:\n"
            "        assert 'DigestPipeline' in globals()\n"
            "        for m in ('add_source', 'process', 'run'):\n"
            "            assert hasattr(DigestPipeline, m), f'missing method: {m}'\n"
            "        assert asyncio.iscoroutinefunction(DigestPipeline.process), \\\n"
            "            'process must be async def'\n"
            "        passed += 1; print('\\u2705 Check 1: DigestPipeline with add_source, process, run')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: __init__ stores model, max_concurrent, _sources\n"
            "    try:\n"
            "        dp = DigestPipeline(model='llama3.2', max_concurrent=2)\n"
            "        assert dp.model          == 'llama3.2', f'model: {dp.model!r}'\n"
            "        assert dp.max_concurrent == 2,          f'max_concurrent: {dp.max_concurrent}'\n"
            "        assert hasattr(dp, '_sources') and isinstance(dp._sources, list), \\\n"
            "            '_sources should be list'\n"
            "        passed += 1; print('\\u2705 Check 2: __init__ stores model, max_concurrent, _sources')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: add_source returns self and appends\n"
            "    try:\n"
            "        dp = DigestPipeline()\n"
            "        ret = dp.add_source('hello world')\n"
            "        assert ret is dp, f'add_source should return self, got {type(ret)}'\n"
            "        assert len(dp._sources) == 1, f'expected 1 source, got {len(dp._sources)}'\n"
            "        dp.add_source('second doc')\n"
            "        assert len(dp._sources) == 2, f'expected 2 sources, got {len(dp._sources)}'\n"
            "        passed += 1; print('\\u2705 Check 3: add_source returns self and appends source')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: process() returns correct dict (1 LLM call via batch_extract)\n"
            "    try:\n"
            "        dp = DigestPipeline(model='llama3.2', max_concurrent=3)\n"
            "        dp.add_source('Python is a versatile high-level programming language.')\n"
            "        output = await dp.process()\n"
            "        assert isinstance(output, dict), f'expected dict, got {type(output).__name__}'\n"
            "        for k in ('source_count', 'ok_count', 'results', 'digest'):\n"
            "            assert k in output, f'missing key: {k}'\n"
            "        assert output['source_count'] == 1, f'source_count: {output[\"source_count\"]}'\n"
            "        assert isinstance(output['results'], list) and len(output['results']) == 1\n"
            "        assert isinstance(output['digest'], str) and output['digest'].strip()\n"
            "        passed += 1; print(f'\\u2705 Check 4: process() returns {{source_count, ok_count, results, digest}}')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: fluent chaining\n"
            "    try:\n"
            "        dp2 = (\n"
            "            DigestPipeline()\n"
            "            .add_source('Artificial intelligence is transforming many industries.')\n"
            "            .add_source('Climate change requires immediate global action.')\n"
            "        )\n"
            "        output2 = await dp2.process()\n"
            "        assert output2['source_count'] == 2, \\\n"
            "            f'source_count should be 2, got {output2[\"source_count\"]}'\n"
            "        assert len(output2['results']) == 2\n"
            "        passed += 1; print('\\u2705 Check 5: fluent chaining, 2-source pipeline works')\n"
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
            + DIGEST_PIPELINE_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Project notebook
# ---------------------------------------------------------------------------

def project_nb():
    global _cid; _cid = 500
    all_code = ALL_IMPLS + "\n\n\n" + DIGEST_PIPELINE_IMPL
    return [
        md(
            "# Day 035 Project: Auto-Analyst — Your Daily Digest Pipeline\n\n"
            "## What You're Building\n\n"
            "A `DigestPipeline` that fetches content from at least 4 sources, "
            "extracts structured information, and produces a consolidated editorial digest.\n\n"
            "## Project Requirements\n\n"
            "1. Create a `DigestPipeline` instance stored as `pipeline`\n"
            "2. Add at least 4 sources (inline text strings, file paths, or URLs)\n"
            "3. Run the full pipeline with `await pipeline.process()`\n"
            "4. Print the digest and at least one per-article summary\n"
            "5. Check the `ok_count` and `source_count` from the result\n"
            "6. Verify with `_run_project_checks()`"
        ),
        md("## Provided: All Implementations"),
        code(all_code),
        md("## Your Pipeline"),
        code(
            "pipeline = (\n"
            "    DigestPipeline(model='llama3.2', max_concurrent=3)\n"
            "    .add_source('Python is a high-level programming language popular in data science.')\n"
            "    .add_source('Machine learning enables computers to learn from data patterns.')\n"
            "    .add_source('Natural language processing lets computers read and generate text.')\n"
            "    .add_source('Cloud computing provides on-demand access to computing resources.')\n"
            ")\n"
            "\n"
            "# TODO: run the pipeline and store the result\n"
            "# output = await pipeline.process()\n"
            "\n"
            "# TODO: print the digest\n"
            "# print('\\n=== DIGEST ===')\n"
            "# print(output['digest'])\n"
            "\n"
            "# TODO: print a summary of each result\n"
            "# for r in output['results']:\n"
            "#     info = r.get('info') or {}\n"
            "#     print(f\"  [{r['status']}] {info.get('title', 'N/A')}\")"
        ),
        md("## Checks"),
        code(
            "async def _run_project_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: pipeline is a DigestPipeline\n"
            "    try:\n"
            "        assert 'pipeline' in globals()\n"
            "        assert isinstance(pipeline, DigestPipeline)\n"
            "        passed += 1; print('\\u2705 Check 1: pipeline is a DigestPipeline')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "\n"
            "    # Check 2: at least 4 sources\n"
            "    try:\n"
            "        assert len(pipeline._sources) >= 4, \\\n"
            "            f'need >= 4 sources, got {len(pipeline._sources)}'\n"
            "        passed += 1; print(f'\\u2705 Check 2: {len(pipeline._sources)} sources registered')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: output is defined\n"
            "    try:\n"
            "        assert 'output' in globals(), \\\n"
            "            'output not defined — run: output = await pipeline.process()'\n"
            "        assert isinstance(output, dict)\n"
            "        for k in ('source_count', 'ok_count', 'results', 'digest'):\n"
            "            assert k in output, f'output missing key: {k}'\n"
            "        passed += 1; print('\\u2705 Check 3: output has source_count, ok_count, results, digest')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: source_count >= 4 and digest is non-empty\n"
            "    try:\n"
            "        assert output['source_count'] >= 4, \\\n"
            "            f'source_count should be >= 4, got {output[\"source_count\"]}'\n"
            "        assert isinstance(output['digest'], str) and output['digest'].strip(), \\\n"
            "            'digest is empty'\n"
            "        passed += 1; print(f'\\u2705 Check 4: {output[\"source_count\"]} sources, digest non-empty')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: at least some ok results\n"
            "    try:\n"
            "        ok = [r for r in output['results'] if r.get('status') == 'ok']\n"
            "        assert ok, 'no successful extractions (is Ollama running?)'\n"
            "        assert output['ok_count'] == len(ok), \\\n"
            "            f'ok_count mismatch: {output[\"ok_count\"]} vs {len(ok)}'\n"
            "        passed += 1; print(f'\\u2705 Check 5: {len(ok)}/{output[\"source_count\"]} extractions ok')\n"
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
            "- Swap inline text for real URLs (news sites, Wikipedia) and run with `fetch_text`\n"
            "- Save `output` to a JSON file with `json.dumps(output, indent=2)`\n"
            "- Add a CLI entry point using `AICli` from Day 34: "
            "`ai-digest --source 'text...' --source 'text...'`\n"
            "- Schedule the pipeline with `APScheduler` from Day 27 for a real daily digest\n"
            "- Add a Slack webhook delivery using Day 29's webhook pattern\n"
            "- Use `SecureConfig` from Day 32 to load model name and max_concurrent from a `.env` file"
        ),
    ]


# ---------------------------------------------------------------------------
# Solution notebook
# ---------------------------------------------------------------------------

def solution_nb():
    global _cid; _cid = 600
    all_code = ALL_IMPLS + "\n\n\n" + DIGEST_PIPELINE_IMPL

    return [
        md(
            "# Day 035 Solution — Auto-Analyst Capstone\n\n"
            "End-to-end pipeline: fetch text → extract structured info "
            "(Pydantic + JSON mode) → batch async → generate digest.\n"
            "All sources are inline text strings for gate compatibility."
        ),
        code(all_code),
        md("## Step 1 — Fetch Text Sources"),
        code(
            "SOURCES = [\n"
            "    'Python is a versatile high-level programming language '\n"
            "    'popular in AI, data science, and web development.',\n"
            "\n"
            "    'Machine learning is a subset of artificial intelligence '\n"
            "    'that enables computers to learn patterns from data.',\n"
            "\n"
            "    'Large language models like GPT and LLaMA are trained '\n"
            "    'on vast amounts of text to generate human-like responses.',\n"
            "]\n"
            "\n"
            "docs = [fetch_text(s) for s in SOURCES]\n"
            "print(f'Loaded {len(docs)} documents:')\n"
            "for d in docs:\n"
            "    print(f'  kind={d[\"kind\"]!r}  chars={d[\"char_count\"]}  '\n"
            "          f'preview={d[\"content\"][:40]!r}...')\n"
            "\n"
            "assert len(docs) == 3\n"
            "assert all(d['kind'] == 'text' for d in docs)"
        ),
        md("## Step 2 — Batch Extract (Async)"),
        code(
            "results = await batch_extract(docs, max_concurrent=3)\n"
            "print(f'\\nExtracted {len(results)} results:')\n"
            "for r in results:\n"
            "    status = r['status']\n"
            "    info   = r.get('info') or {}\n"
            "    title  = info.get('title', 'N/A')\n"
            "    sent   = info.get('sentiment', 'N/A')\n"
            "    print(f'  [{status}] {title!r}  sentiment={sent!r}')\n"
            "\n"
            "assert len(results) == 3\n"
            "assert all('status' in r for r in results)"
        ),
        md("## Step 3 — Generate Digest"),
        code(
            "digest = generate_digest(results)\n"
            "print('\\n' + digest)\n"
            "\n"
            "assert isinstance(digest, str) and len(digest.strip()) >= 50"
        ),
        md("## Step 4 — DigestPipeline Full Run"),
        code(
            "pipeline = (\n"
            "    DigestPipeline(model='llama3.2', max_concurrent=3)\n"
            "    .add_source('Renewable energy sources like solar and wind '\n"
            "                'are becoming increasingly cost-competitive.')\n"
            "    .add_source('Quantum computing promises exponential speedups '\n"
            "                'for certain classes of problems over classical computers.')\n"
            ")\n"
            "\n"
            "output = await pipeline.process()\n"
            "print(f'source_count : {output[\"source_count\"]}')\n"
            "print(f'ok_count     : {output[\"ok_count\"]}')\n"
            "print(f'digest       : {output[\"digest\"][:120]}...')\n"
            "\n"
            "assert output['source_count'] == 2\n"
            "assert isinstance(output['digest'], str) and output['digest'].strip()\n"
            "assert 'results' in output and len(output['results']) == 2\n"
            "\n"
            "print('\\nAuto-Analyst complete!')"
        ),
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Generating Day 035 notebooks...")
    ex_dir   = DAY_DIR / "exercises"
    proj_dir = DAY_DIR / "project"
    sol_dir  = proj_dir / "solution"
    for d in (ex_dir, proj_dir, sol_dir):
        d.mkdir(parents=True, exist_ok=True)

    write_nb(ex_dir   / "exercise_01.ipynb", ex01())
    write_nb(ex_dir   / "exercise_02.ipynb", ex02())
    write_nb(ex_dir   / "exercise_03.ipynb", ex03())
    write_nb(ex_dir   / "exercise_04.ipynb", ex04())
    write_nb(ex_dir   / "exercise_05.ipynb", ex05())
    write_nb(proj_dir / "project.ipynb",     project_nb())
    write_nb(sol_dir  / "solution.ipynb",    solution_nb())
    print("Done.")


if __name__ == "__main__":
    main()
