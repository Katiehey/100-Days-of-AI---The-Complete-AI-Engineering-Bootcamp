#!/usr/bin/env python3
"""Generate all Day 024 notebooks: exercises 1-5, project, solution."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAY_DIR = ROOT / "02_automation" / "day_024"

_cid = 0
SCRAPE_URL = "https://books.toscrape.com"

# Static HTML used in exercises 1 (no network needed)
HTML_WITH_SCRIPTS = (
    "<html>\n"
    "<head>\n"
    "  <title>AI Engineering Guide</title>\n"
    "  <style>body { color: red; font-size: 14px; }</style>\n"
    "</head>\n"
    "<body>\n"
    "  <script>var tracker = 1; window.onload = function() {};</script>\n"
    "  <h1>Introduction to AI Engineering</h1>\n"
    "  <p>AI engineering combines software development with machine learning.</p>\n"
    "  <p>Key skills include Python, APIs, and prompt engineering.</p>\n"
    "</body>\n"
    "</html>"
)

SAMPLE_TEXT = (
    "Python is a high-level programming language created by Guido van Rossum "
    "and first released in 1991. It emphasizes code readability and simplicity. "
    "Python is widely used in data science, web development, and automation."
)


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
# Solution implementations (imports live in each notebook's imports cell)
# ---------------------------------------------------------------------------

CLEAN_HTML_TEXT_IMPL = """\
def clean_html_text(html_string: str) -> str:
    soup = BeautifulSoup(html_string, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator="\\n", strip=True)
    text = re.sub(r"\\n{3,}", "\\n\\n", text)
    return text.strip()"""

EXTRACT_SCHEMA_FIELDS_IMPL = """\
def extract_schema_fields(
    text: str, fields: list[str], model: str = "llama3.2"
) -> dict:
    fields_json = json.dumps(fields)
    response = ollama.chat(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a structured data extractor. "
                    f"Extract the following fields from the text: {fields_json}. "
                    "Return JSON with exactly these keys. "
                    "Use null for any field you cannot find. "
                    "Return only valid JSON, no explanation."
                ),
            },
            {
                "role": "user",
                "content": f"Extract from this text:\\n\\n{text[:3000]}",
            },
        ],
        format="json",
    )
    raw = response["message"]["content"]
    try:
        return json.loads(raw)
    except Exception:
        return {f: None for f in fields}"""

VALIDATE_EXTRACTED_IMPL = """\
def validate_extracted(raw: dict, model_class: type[BaseModel]) -> BaseModel | None:
    try:
        return model_class.model_validate(raw)
    except Exception:
        return None"""

SCRAPE_AND_EXTRACT_IMPL = """\
def scrape_and_extract(
    url: str, fields: list[str], model: str = "llama3.2"
) -> dict:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    text = clean_html_text(response.text)
    return extract_schema_fields(text, fields, model=model)"""

BATCH_SCRAPE_EXTRACT_IMPL = """\
def batch_scrape_extract(
    urls: list[str],
    fields: list[str],
    model: str = "llama3.2",
) -> list[dict]:
    results = []
    for url in urls:
        try:
            data = scrape_and_extract(url, fields, model=model)
            results.append({"url": url, "status": "ok", "data": data})
        except Exception as e:
            results.append({"url": url, "status": "error", "error": str(e)})
    return results"""

PAGE_EXTRACTOR_IMPL = """\
class PageExtractor:
    def __init__(self, model_class: type[BaseModel], model: str = "llama3.2"):
        self.model_class = model_class
        self.llm_model = model
        self.fields = list(model_class.model_fields.keys())

    def extract(self, url: str) -> BaseModel | None:
        data = scrape_and_extract(url, self.fields, model=self.llm_model)
        return validate_extracted(data, self.model_class)

    def extract_many(self, urls: list[str]) -> list[dict]:
        return batch_scrape_extract(urls, self.fields, model=self.llm_model)

    def to_json(self, instance: BaseModel) -> str:
        return json.dumps(instance.model_dump(), indent=2)"""

ALL_IMPLS = (
    CLEAN_HTML_TEXT_IMPL + "\n\n\n"
    + EXTRACT_SCHEMA_FIELDS_IMPL + "\n\n\n"
    + VALIDATE_EXTRACTED_IMPL + "\n\n\n"
    + SCRAPE_AND_EXTRACT_IMPL + "\n\n\n"
    + BATCH_SCRAPE_EXTRACT_IMPL
)

# Helpers for exercises 4 and 5
HELPERS_FOR_EX4 = CLEAN_HTML_TEXT_IMPL + "\n\n\n" + EXTRACT_SCHEMA_FIELDS_IMPL
HELPERS_FOR_EX5 = HELPERS_FOR_EX4 + "\n\n\n" + SCRAPE_AND_EXTRACT_IMPL


# ---------------------------------------------------------------------------
# Exercise 01 — clean_html_text
# ---------------------------------------------------------------------------

def ex01():
    global _cid; _cid = 0
    html_repr = repr(HTML_WITH_SCRIPTS)
    return [
        md(
            "# Day 024 — Exercise 1: clean_html_text\n\n"
            "**What you'll build:** `clean_html_text(html_string)` — strips all HTML tags, "
            "removes `<script>` and `<style>` blocks, and collapses excess blank lines into "
            "clean readable text.\n\n"
            "**Why it matters:** LLMs read plain text, not HTML. A raw page might contain "
            "10,000 characters of JavaScript noise before the first word of real content. "
            "Clean text means more signal per token — and better extractions."
        ),
        code("import re\nfrom bs4 import BeautifulSoup"),
        md("## Your Implementation"),
        code(
            "def clean_html_text(html_string: str) -> str:\n"
            '    """\n'
            "    Strip HTML tags and noise, returning clean plain text.\n\n"
            "    Steps:\n"
            "        1. Parse with BeautifulSoup.\n"
            "        2. Remove all <script> and <style> tags (and their contents).\n"
            '        3. Call get_text(separator="\\n", strip=True).\n'
            '        4. Collapse runs of 3+ newlines to 2 with re.sub(r"\\n{3,}", "\\n\\n", ...).\n'
            "        5. Return the stripped result.\n"
            '    """\n'
            "    # TODO: soup = BeautifulSoup(html_string, 'html.parser')\n"
            "    # TODO: for tag in soup(['script', 'style']): tag.decompose()\n"
            '    # TODO: text = soup.get_text(separator="\\n", strip=True)\n'
            '    # TODO: text = re.sub(r"\\n{3,}", "\\n\\n", text)\n'
            "    # TODO: return text.strip()\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            f"HTML = {html_repr}\n"
            "\n"
            "\n"
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'clean_html_text' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: clean_html_text defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    result = None\n"
            "\n"
            "    # Check 2: returns a string\n"
            "    try:\n"
            "        result = clean_html_text(HTML)\n"
            "        assert isinstance(result, str), f'expected str, got {type(result)}'\n"
            "        passed += 1; print('\\u2705 Check 2: returns a string')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: visible text is present\n"
            "    try:\n"
            "        assert result is not None, 'result is None (Check 2 failed)'\n"
            "        assert 'Introduction to AI Engineering' in result, \\\n"
            "            f\"'Introduction to AI Engineering' not in result: {result[:200]!r}\"\n"
            "        assert 'AI engineering combines' in result, \\\n"
            "            f\"paragraph text not in result: {result[:200]!r}\"\n"
            "        passed += 1; print('\\u2705 Check 3: visible text is present in result')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: script and style content stripped\n"
            "    try:\n"
            "        assert result is not None, 'result is None'\n"
            "        assert 'var tracker' not in result, \\\n"
            "            f\"script content not stripped: {result[:300]!r}\"\n"
            "        assert 'color: red' not in result, \\\n"
            "            f\"style content not stripped: {result[:300]!r}\"\n"
            "        passed += 1; print('\\u2705 Check 4: script and style content stripped')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: minimal HTML returns string without crashing\n"
            "    try:\n"
            "        empty_result = clean_html_text('<html><body></body></html>')\n"
            "        assert isinstance(empty_result, str), \\\n"
            "            f'expected str for minimal HTML, got {type(empty_result)}'\n"
            "        passed += 1; print('\\u2705 Check 5: minimal HTML returns string without crashing')\n"
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
            + CLEAN_HTML_TEXT_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 02 — extract_schema_fields
# ---------------------------------------------------------------------------

def ex02():
    global _cid; _cid = 100
    sample_repr = repr(SAMPLE_TEXT)
    return [
        md(
            "# Day 024 — Exercise 2: extract_schema_fields\n\n"
            "**What you'll build:** `extract_schema_fields(text, fields, model)` — gives the LLM "
            "a list of field names and plain text, and gets back a dict with one value per field.\n\n"
            "**Why it matters:** This is schema-guided extraction without Pydantic. "
            "The field list acts as a mini-schema. "
            "`format='json'` (Day 4) guarantees parseable output. Null values for unfound "
            "fields and a fallback dict on parse failure make it resilient."
        ),
        code("import json\nimport ollama"),
        md("## Your Implementation"),
        code(
            "def extract_schema_fields(\n"
            "    text: str, fields: list[str], model: str = \"llama3.2\"\n"
            ") -> dict:\n"
            '    """\n'
            "    Extract named fields from plain text using the LLM.\n\n"
            "    Args:\n"
            "        text:   Plain text to extract from (already stripped of HTML).\n"
            "        fields: List of field names to extract (e.g. ['title', 'price']).\n"
            "        model:  Ollama model name.\n\n"
            "    Returns:\n"
            "        Dict with exactly the requested field names as keys.\n"
            "        Missing fields are null. Never raises.\n"
            '    """\n'
            "    # TODO: fields_json = json.dumps(fields)\n"
            "    # TODO: call ollama.chat with format='json'\n"
            "    #       system: 'extract these fields: {fields_json}; use null for missing'\n"
            "    #       user:   f'Extract from this text:\\n\\n{text[:3000]}'\n"
            "    # TODO: raw = response['message']['content']\n"
            "    # TODO: try: return json.loads(raw)\n"
            "    #       except: return {f: None for f in fields}\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            f"SAMPLE_TEXT = {sample_repr}\n"
            "FIELDS = ['language_name', 'creator', 'year']\n"
            "\n"
            "\n"
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'extract_schema_fields' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: extract_schema_fields defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    result = None\n"
            "\n"
            "    # Check 2: returns a dict (1 LLM call)\n"
            "    try:\n"
            "        result = extract_schema_fields(SAMPLE_TEXT, FIELDS)\n"
            "        assert isinstance(result, dict), f'expected dict, got {type(result)}'\n"
            "        passed += 1; print('\\u2705 Check 2: returns a dict')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: dict has all requested field keys\n"
            "    try:\n"
            "        assert result is not None, 'result is None (Check 2 failed)'\n"
            "        for f in FIELDS:\n"
            "            assert f in result, f\"missing field '{f}': {list(result)}'\"\n"
            "        passed += 1; print(f'\\u2705 Check 3: dict has all {len(FIELDS)} requested fields')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: at least one field has a non-null string value\n"
            "    try:\n"
            "        assert result is not None, 'result is None'\n"
            "        non_null = [v for v in result.values() if v is not None]\n"
            "        assert len(non_null) >= 1, \\\n"
            "            f'all fields are null — LLM likely not extracting: {result}'\n"
            "        passed += 1; print(f'\\u2705 Check 4: {len(non_null)}/{len(FIELDS)} fields extracted')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: works on empty text without crashing (1 LLM call)\n"
            "    try:\n"
            "        empty_result = extract_schema_fields('', ['name', 'date'])\n"
            "        assert isinstance(empty_result, dict), \\\n"
            "            f'expected dict for empty text, got {type(empty_result)}'\n"
            "        assert 'name' in empty_result and 'date' in empty_result, \\\n"
            "            f\"fallback keys missing: {list(empty_result)}\"\n"
            "        passed += 1; print('\\u2705 Check 5: works on empty text — returns dict with requested keys')\n"
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
            + EXTRACT_SCHEMA_FIELDS_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 03 — validate_extracted
# ---------------------------------------------------------------------------

def ex03():
    global _cid; _cid = 200
    return [
        md(
            "# Day 024 — Exercise 3: validate_extracted\n\n"
            "**What you'll build:** `validate_extracted(raw, model_class)` — validates a raw "
            "dict (from the LLM) against a Pydantic model. Returns the model instance on "
            "success, `None` on failure.\n\n"
            "**Why it matters:** LLM output is never guaranteed. Validation catches null required "
            "fields, wrong types, and missing keys before they silently corrupt your data. "
            "`None` on failure means the caller decides whether to retry, skip, or log — "
            "not a crash."
        ),
        code("from pydantic import BaseModel"),
        md("## Your Implementation"),
        code(
            "def validate_extracted(raw: dict, model_class: type[BaseModel]) -> BaseModel | None:\n"
            '    """\n'
            "    Validate a raw dict against a Pydantic model.\n\n"
            "    Args:\n"
            "        raw:         Dict from the LLM (may have missing or null fields).\n"
            "        model_class: A Pydantic BaseModel subclass to validate against.\n\n"
            "    Returns:\n"
            "        model_class instance on success, None if validation fails.\n"
            '    """\n'
            "    # TODO: try:\n"
            "    #           return model_class.model_validate(raw)\n"
            "    #       except Exception:\n"
            "    #           return None\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "class BookRecord(BaseModel):\n"
            "    title: str\n"
            "    price: str\n"
            "\n"
            "\n"
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'validate_extracted' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: validate_extracted defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    valid_result = None\n"
            "\n"
            "    # Check 2: valid dict → model instance\n"
            "    try:\n"
            "        valid_result = validate_extracted(\n"
            "            {'title': 'Python Cookbook', 'price': '\\u00a312.99'},\n"
            "            BookRecord,\n"
            "        )\n"
            "        assert isinstance(valid_result, BookRecord), \\\n"
            "            f'expected BookRecord, got {type(valid_result)}'\n"
            "        passed += 1; print('\\u2705 Check 2: valid dict returns BookRecord instance')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: field values are correct\n"
            "    try:\n"
            "        assert valid_result is not None, 'valid_result is None (Check 2 failed)'\n"
            "        assert valid_result.title == 'Python Cookbook', \\\n"
            "            f\"expected title='Python Cookbook', got {valid_result.title!r}\"\n"
            "        assert valid_result.price == '\\u00a312.99', \\\n"
            "            f\"expected price='\\u00a312.99', got {valid_result.price!r}\"\n"
            "        passed += 1; print('\\u2705 Check 3: field values are correct')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: missing required field → None\n"
            "    try:\n"
            "        bad_result = validate_extracted({'title': 'Only Title'}, BookRecord)\n"
            "        assert bad_result is None, \\\n"
            "            f'expected None for missing required field, got {bad_result!r}'\n"
            "        passed += 1; print('\\u2705 Check 4: missing required field returns None')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: extra fields in dict are ignored (Pydantic v2 default)\n"
            "    try:\n"
            "        with_extras = {\n"
            "            'title': 'A Book', 'price': '\\u00a35.00',\n"
            "            'color': 'blue', 'rating': 'Four',\n"
            "        }\n"
            "        extra_result = validate_extracted(with_extras, BookRecord)\n"
            "        assert isinstance(extra_result, BookRecord), \\\n"
            "            f'extra fields should be ignored, got {type(extra_result)}'\n"
            "        assert extra_result.title == 'A Book', \\\n"
            "            f\"expected title='A Book', got {extra_result.title!r}\"\n"
            "        passed += 1; print('\\u2705 Check 5: extra fields in dict are ignored')\n"
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
            + VALIDATE_EXTRACTED_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 04 — scrape_and_extract
# ---------------------------------------------------------------------------

def ex04():
    global _cid; _cid = 300
    return [
        md(
            "# Day 024 — Exercise 4: scrape_and_extract\n\n"
            "**What you'll build:** `scrape_and_extract(url, fields, model)` — the full pipeline "
            "in one function: fetch the page → clean the HTML → extract fields with the LLM.\n\n"
            "**Why it matters:** This is the core of AI-powered scraping. Three helper "
            "functions (provided below) do the heavy lifting; your job is to wire them together "
            "in the right order. Any URL, any field list — one function call."
        ),
        code(
            "import re\n"
            "import json\n"
            "import requests\n"
            "import ollama\n"
            "from bs4 import BeautifulSoup"
        ),
        md("## Provided Helpers"),
        code(HELPERS_FOR_EX4),
        md("## Your Implementation"),
        code(
            "def scrape_and_extract(\n"
            "    url: str, fields: list[str], model: str = \"llama3.2\"\n"
            ") -> dict:\n"
            '    """\n'
            "    Fetch a URL, clean the HTML, and extract fields using the LLM.\n\n"
            "    Args:\n"
            "        url:    URL to scrape.\n"
            "        fields: Field names to extract (e.g. ['title', 'description']).\n"
            "        model:  Ollama model name.\n\n"
            "    Returns:\n"
            "        Dict with the extracted field values.\n\n"
            "    Raises:\n"
            "        requests.exceptions.HTTPError or ConnectionError on bad URLs.\n"
            '    """\n'
            "    # TODO: response = requests.get(url, timeout=10)\n"
            "    # TODO: response.raise_for_status()\n"
            "    # TODO: text = clean_html_text(response.text)\n"
            "    # TODO: return extract_schema_fields(text, fields, model=model)\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            f'SCRAPE_URL = "{SCRAPE_URL}"\n'
            "FIELDS = ['site_name', 'description']\n"
            "\n"
            "\n"
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'scrape_and_extract' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: scrape_and_extract defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    result = None\n"
            "\n"
            "    # Check 2: returns a dict (1 network + 1 LLM call)\n"
            "    try:\n"
            "        result = scrape_and_extract(SCRAPE_URL, FIELDS)\n"
            "        assert isinstance(result, dict), f'expected dict, got {type(result)}'\n"
            "        passed += 1; print('\\u2705 Check 2: returns a dict')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: dict has all requested field keys\n"
            "    try:\n"
            "        assert result is not None, 'result is None (Check 2 failed)'\n"
            "        for f in FIELDS:\n"
            "            assert f in result, f\"missing field '{f}': {list(result)}\"\n"
            "        passed += 1; print(f'\\u2705 Check 3: dict has all {len(FIELDS)} requested fields')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: at least one extracted value is a non-null string\n"
            "    try:\n"
            "        assert result is not None, 'result is None'\n"
            "        non_null = [v for v in result.values() if v is not None]\n"
            "        assert len(non_null) >= 1, \\\n"
            "            f'all fields are null — is the LLM running? result: {result}'\n"
            "        passed += 1; print(f'\\u2705 Check 4: {len(non_null)}/{len(FIELDS)} fields have values')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: raises on unreachable URL\n"
            "    raised = False\n"
            "    try:\n"
            "        scrape_and_extract('http://localhost:9999/', FIELDS)\n"
            "    except Exception:\n"
            "        raised = True\n"
            "    try:\n"
            "        assert raised, 'scrape_and_extract should raise on unreachable URL'\n"
            "        passed += 1; print('\\u2705 Check 5: raises on unreachable URL')\n"
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
            + SCRAPE_AND_EXTRACT_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 05 — batch_scrape_extract
# ---------------------------------------------------------------------------

def ex05():
    global _cid; _cid = 400
    return [
        md(
            "# Day 024 — Exercise 5: batch_scrape_extract\n\n"
            "**What you'll build:** `batch_scrape_extract(urls, fields, model)` — runs "
            "`scrape_and_extract` over a list of URLs, catches errors per-URL, and returns "
            "a list of `{url, status, data/error}` envelopes.\n\n"
            "**Why it matters:** Real pipelines process many pages. One bad URL must not "
            "crash the entire batch. This is the Day 22 error-envelope pattern applied "
            "to AI scraping — safe, iterable, and inspectable."
        ),
        code(
            "import re\n"
            "import json\n"
            "import requests\n"
            "import ollama\n"
            "from bs4 import BeautifulSoup"
        ),
        md("## Provided Helpers"),
        code(HELPERS_FOR_EX5),
        md("## Your Implementation"),
        code(
            "def batch_scrape_extract(\n"
            "    urls: list[str],\n"
            "    fields: list[str],\n"
            "    model: str = \"llama3.2\",\n"
            ") -> list[dict]:\n"
            '    """\n'
            "    Scrape and extract from a list of URLs. Never raises.\n\n"
            "    Args:\n"
            "        urls:   List of URLs to scrape.\n"
            "        fields: Field names to extract from each page.\n"
            "        model:  Ollama model name.\n\n"
            "    Returns:\n"
            "        List of result dicts:\n"
            "          On success: {'url': url, 'status': 'ok',    'data': dict}\n"
            "          On error:   {'url': url, 'status': 'error', 'error': str}\n"
            '    """\n'
            "    # TODO: results = []\n"
            "    # TODO: for url in urls:\n"
            "    #           try:\n"
            "    #               data = scrape_and_extract(url, fields, model=model)\n"
            "    #               results.append({'url': url, 'status': 'ok', 'data': data})\n"
            "    #           except Exception as e:\n"
            "    #               results.append({'url': url, 'status': 'error', 'error': str(e)})\n"
            "    # TODO: return results\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            f'GOOD_URL = "{SCRAPE_URL}"\n'
            "BAD_URL  = 'http://localhost:9999/'\n"
            "FIELDS   = ['site_name']\n"
            "\n"
            "\n"
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'batch_scrape_extract' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: batch_scrape_extract defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    results = None\n"
            "\n"
            "    # Check 2: returns a list of 2 results (1 net + 1 LLM call total)\n"
            "    try:\n"
            "        results = batch_scrape_extract([GOOD_URL, BAD_URL], FIELDS)\n"
            "        assert isinstance(results, list), f'expected list, got {type(results)}'\n"
            "        assert len(results) == 2, f'expected 2 results, got {len(results)}'\n"
            "        passed += 1; print('\\u2705 Check 2: returns a list with 2 results')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: good URL → status='ok'\n"
            "    try:\n"
            "        assert results is not None, 'results is None (Check 2 failed)'\n"
            "        ok = results[0]\n"
            "        assert ok['status'] == 'ok', \\\n"
            "            f\"expected status='ok' for good URL, got {ok['status']!r}\"\n"
            "        assert 'data' in ok, f\"'data' key missing from ok result: {ok}\"\n"
            "        passed += 1; print(\"\\u2705 Check 3: good URL has status='ok' with data\")\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: bad URL → status='error'\n"
            "    try:\n"
            "        assert results is not None, 'results is None'\n"
            "        err = results[1]\n"
            "        assert err['status'] == 'error', \\\n"
            "            f\"expected status='error' for bad URL, got {err['status']!r}\"\n"
            "        assert 'error' in err, f\"'error' key missing from error result: {err}\"\n"
            "        passed += 1; print(\"\\u2705 Check 4: bad URL has status='error' with error message\")\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: each result has a 'url' key matching the input\n"
            "    try:\n"
            "        assert results is not None, 'results is None'\n"
            "        assert results[0]['url'] == GOOD_URL, \\\n"
            "            f\"url mismatch: expected {GOOD_URL!r}, got {results[0]['url']!r}\"\n"
            "        assert results[1]['url'] == BAD_URL, \\\n"
            "            f\"url mismatch: expected {BAD_URL!r}, got {results[1]['url']!r}\"\n"
            "        passed += 1; print('\\u2705 Check 5: each result has correct url key')\n"
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
            + BATCH_SCRAPE_EXTRACT_IMPL + "\n"
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
            "# Day 024 Project: Web Page → Structured JSON\n\n"
            "## What You're Building\n\n"
            "A `PageExtractor` class that turns any URL into a validated Pydantic model "
            "instance — no CSS selectors, no fragile HTML parsing. Define your target schema, "
            "point it at a URL, get structured data back.\n\n"
            "The same class works on any site: swap the Pydantic model for the data you want "
            "and point it at a different URL.\n\n"
            "## Project Requirements\n\n"
            "1. Implement `PageExtractor(model_class, model='llama3.2')` with:\n"
            "   - `self.fields` from `model_class.model_fields.keys()` (Pydantic v2)\n"
            "   - `extract(url)` → `model_class` instance or `None`\n"
            "   - `extract_many(urls)` → list of result envelopes\n"
            "   - `to_json(instance)` → pretty-printed JSON string\n"
            "2. Define a `SiteInfo` Pydantic model with at least `site_name` and `main_purpose`\n"
            "3. Extract from `https://books.toscrape.com` and print the result\n"
            "4. Run batch over 2 URLs (one good, one bad) and show both statuses\n\n"
            "**Deliverable:** Run the extractor, print the JSON output, "
            "confirm the bad URL shows `status='error'`."
        ),
        code(
            "import re\n"
            "import json\n"
            "import requests\n"
            "import ollama\n"
            "from bs4 import BeautifulSoup\n"
            "from pydantic import BaseModel"
        ),
        md("## Provided: All Helper Functions"),
        code(ALL_IMPLS),
        md(
            "## Step 1: Define Your Schema\n\n"
            "Define a Pydantic model for the data you want to extract. "
            "Use `str | None = None` for all fields — this makes validation always succeed "
            "even when the LLM leaves some fields blank."
        ),
        code(
            "class SiteInfo(BaseModel):\n"
            "    site_name: str | None = None\n"
            "    main_purpose: str | None = None\n"
            "    # TODO: add more fields if you like, e.g. language, num_products\n"
            "    pass"
        ),
        md(
            "## Step 2: Implement PageExtractor\n\n"
            "Use `model_class.model_fields.keys()` (Pydantic v2) to get the field list. "
            "Delegate to helper functions you built in exercises 1-5."
        ),
        code(
            "class PageExtractor:\n"
            "    def __init__(self, model_class: type[BaseModel], model: str = 'llama3.2'):\n"
            "        self.model_class = model_class\n"
            "        self.llm_model = model\n"
            "        # TODO: self.fields = list(model_class.model_fields.keys())\n"
            "        pass\n"
            "\n"
            "    def extract(self, url: str) -> BaseModel | None:\n"
            "        # TODO: data = scrape_and_extract(url, self.fields, model=self.llm_model)\n"
            "        # TODO: return validate_extracted(data, self.model_class)\n"
            "        pass\n"
            "\n"
            "    def extract_many(self, urls: list[str]) -> list[dict]:\n"
            "        # TODO: return batch_scrape_extract(urls, self.fields, model=self.llm_model)\n"
            "        pass\n"
            "\n"
            "    def to_json(self, instance: BaseModel) -> str:\n"
            "        # TODO: return json.dumps(instance.model_dump(), indent=2)\n"
            "        pass"
        ),
        md("## Step 3: Use Your Extractor"),
        code(
            f'# extractor = PageExtractor(SiteInfo)\n'
            f'# info = extractor.extract("{SCRAPE_URL}")\n'
            f'# if info:\n'
            f'#     print(extractor.to_json(info))\n'
            f'# else:\n'
            f'#     print("Extraction returned None (some required fields missing)")\n'
        ),
        code(
            f'# results = extractor.extract_many(["{SCRAPE_URL}", "http://localhost:9999/"])\n'
            f'# for r in results:\n'
            f'#     print(f"{{r[\'url\'][:45]}} → {{r[\'status\']}}")\n'
        ),
        md("## Checks"),
        code(
            "def _run_project_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: PageExtractor class with required methods\n"
            "    try:\n"
            "        assert 'PageExtractor' in globals(), 'PageExtractor not defined'\n"
            "        for m in ('extract', 'extract_many', 'to_json'):\n"
            "            assert hasattr(PageExtractor, m), f'PageExtractor missing: {m}'\n"
            "        passed += 1; print('\\u2705 Check 1: PageExtractor has all required methods')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "\n"
            "    # Check 2: extractor is a PageExtractor\n"
            "    try:\n"
            "        assert 'extractor' in globals(), 'extractor not defined'\n"
            "        assert isinstance(extractor, PageExtractor), \\\n"
            "            f'extractor must be PageExtractor, got {type(extractor)}'\n"
            "        passed += 1; print('\\u2705 Check 2: extractor is a PageExtractor')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: extractor.fields is a non-empty list\n"
            "    try:\n"
            "        assert 'extractor' in globals(), 'extractor not defined'\n"
            "        assert hasattr(extractor, 'fields'), 'extractor missing .fields'\n"
            "        assert isinstance(extractor.fields, list) and len(extractor.fields) >= 1, \\\n"
            "            f'extractor.fields should be non-empty list: {extractor.fields!r}'\n"
            "        passed += 1; print(f'\\u2705 Check 3: extractor.fields = {extractor.fields}')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: results is a list with 2 items\n"
            "    try:\n"
            "        assert 'results' in globals(), 'results not defined'\n"
            "        assert isinstance(results, list) and len(results) == 2, \\\n"
            "            f'results must have 2 items, got {results!r}'\n"
            "        statuses = [r.get('status') for r in results]\n"
            "        assert 'ok' in statuses, f\"no 'ok' status in results: {statuses}\"\n"
            "        assert 'error' in statuses, f\"no 'error' status in results: {statuses}\"\n"
            "        passed += 1; print('\\u2705 Check 4: results has ok + error statuses')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: to_json returns a valid JSON string\n"
            "    try:\n"
            "        dummy = SiteInfo(site_name='Test', main_purpose='Testing')\n"
            "        json_str = extractor.to_json(dummy)\n"
            "        assert isinstance(json_str, str), \\\n"
            "            f'to_json should return str, got {type(json_str)}'\n"
            "        parsed = json.loads(json_str)\n"
            "        assert parsed.get('site_name') == 'Test', \\\n"
            "            f\"json has wrong site_name: {parsed}\"\n"
            "        passed += 1; print('\\u2705 Check 5: to_json returns valid indented JSON')\n"
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
            "- Add a `BookInfo(BaseModel)` with `title`, `price`, `rating`, `description` fields "
            "(all `str | None`) and run `PageExtractor(BookInfo)` on a specific book detail page\n"
            "- Add a `save_json(results, path)` method that writes batch results to a JSON file\n"
            "- Add a `retry(url, fields, attempts=3)` method that retries extraction until "
            "validate_extracted returns a non-None result\n"
            "- Compare: selector-based extraction (Day 23) vs AI extraction (Day 24) — "
            "which is more accurate for book titles? Which is faster?\n"
            "- Extend to extract from multiple category pages of books.toscrape.com "
            "and aggregate the results"
        ),
    ]


# ---------------------------------------------------------------------------
# Solution notebook (executed by gate — must run clean)
# ---------------------------------------------------------------------------

def solution_nb():
    global _cid; _cid = 600

    solution_all = (
        "import re\n"
        "import json\n"
        "import requests\n"
        "import ollama\n"
        "from bs4 import BeautifulSoup\n"
        "from pydantic import BaseModel\n"
        "\n"
        "\n"
        + ALL_IMPLS
        + "\n"
        "\n"
        "\n"
        + PAGE_EXTRACTOR_IMPL
    )

    return [
        md(
            "# Day 024 Project Solution — Web Page → Structured JSON\n\n"
            "A `PageExtractor` that fetches any URL, strips HTML to plain text, "
            "uses the LLM to fill a Pydantic schema, validates the result, "
            "and returns structured data."
        ),
        code(
            solution_all
            + "\n\n\n"
            "class SiteInfo(BaseModel):\n"
            "    site_name: str | None = None\n"
            "    main_purpose: str | None = None"
        ),
        md("## Action 1 — Extract Structured Info from books.toscrape.com"),
        code(
            f'extractor = PageExtractor(SiteInfo)\n'
            f'info = extractor.extract("{SCRAPE_URL}")\n'
            f'print("Extracted site info:")\n'
            f'if info:\n'
            f'    print(f"  site_name   : {{info.site_name}}")\n'
            f'    print(f"  main_purpose: {{info.main_purpose}}")\n'
            f'    print("\\nJSON output:")\n'
            f'    print(extractor.to_json(info))\n'
            f'else:\n'
            f'    print("  (extraction returned None — LLM validation failed)")\n'
            f'    fallback = SiteInfo(site_name="Books to Scrape", main_purpose="Scraping practice")\n'
            f'    print(extractor.to_json(fallback))'
        ),
        md("## Action 2 — Batch Extract: One Good URL, One Bad URL"),
        code(
            f'urls = ["{SCRAPE_URL}", "http://localhost:9999/"]\n'
            f'results = extractor.extract_many(urls)\n'
            f'print("\\nBatch results:")\n'
            f'for r in results:\n'
            f'    label = r["url"][:45]\n'
            f'    if r["status"] == "ok":\n'
            f'        fields_extracted = list(r["data"].keys())\n'
            f'        print(f"  {{label}} → ok (fields: {{fields_extracted}})")\n'
            f'    else:\n'
            f'        print(f"  {{label}} → error: {{str(r[\'error\'])[:50]}}")'
        ),
        md("## Action 3 — Validate and Serialize"),
        code(
            "# Show validate_extracted in action\n"
            "raw_good = {'site_name': 'Books to Scrape', 'main_purpose': 'Practice scraping'}\n"
            "raw_bad  = {'wrong_key': 'ignored'}\n"
            "\n"
            "validated = validate_extracted(raw_good, SiteInfo)\n"
            "rejected  = validate_extracted(raw_bad, SiteInfo)\n"
            "\n"
            "print('\\nValidation demo:')\n"
            "print(f'  raw_good → {type(validated).__name__}: {validated}')\n"
            "print(f'  raw_bad  → {rejected!r} (None = validation returned empty model or failed)')\n"
            "print('\\nExtraction complete!')"
        ),
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Generating Day 024 notebooks...")
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
