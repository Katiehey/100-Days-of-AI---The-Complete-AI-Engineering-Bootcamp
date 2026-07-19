#!/usr/bin/env python3
"""Generate all Day 041 notebooks: exercises 1-5, project, solution."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAY_DIR = ROOT / "03_data_analysis" / "day_041"

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
# Shared data
# ---------------------------------------------------------------------------

BASE_IMPORTS = """\
import warnings
warnings.filterwarnings('ignore')
import re
import ollama
import pandas as pd
import io"""

RETAIL_CSV_CODE = """\
RETAIL_CSV = (
    'order_id,product,category,region,price,quantity\\n'
    '1,Widget,Electronics,North,25.0,10\\n'
    '2,Gadget,Electronics,South,150.0,3\\n'
    '3,Widget,Electronics,South,25.0,5\\n'
    '4,Doohickey,Accessories,East,8.0,50\\n'
    '5,Gadget,Electronics,East,150.0,7\\n'
    '6,Widget,Electronics,East,25.0,4\\n'
    '7,Doohickey,Accessories,North,8.0,20\\n'
    '8,Gadget,Electronics,North,150.0,2\\n'
    '9,Widget,Electronics,West,25.0,6\\n'
    '10,Doohickey,Accessories,South,8.0,15\\n'
    '11,Thingamajig,Accessories,North,200.0,1\\n'
    '12,Thingamajig,Accessories,East,200.0,4'
)
SALES_DF = pd.read_csv(io.StringIO(RETAIL_CSV))
SALES_DF['revenue'] = SALES_DF['price'] * SALES_DF['quantity']"""

# ---------------------------------------------------------------------------
# Day 041 implementations
# ---------------------------------------------------------------------------

GET_DF_SCHEMA_IMPL = """\
def get_df_schema(df) -> str:
    lines = [f"Shape: {df.shape[0]} rows x {df.shape[1]} columns"]
    lines.append("\\nColumns and dtypes:")
    for col, dtype in df.dtypes.items():
        lines.append(f"  {col}: {dtype}")
    lines.append(f"\\nSample (first 3 rows):\\n{df.head(3).to_string(index=False)}")
    return "\\n".join(lines)"""

BUILD_QUERY_PROMPT_IMPL = """\
def build_query_prompt(question: str, schema_str: str) -> str:
    return (
        "You are a Python data analyst. Write pandas code to answer the question.\\n\\n"
        "Requirements:\\n"
        "- The DataFrame is already loaded as `df`. `pd` is also in scope.\\n"
        "- Store the final answer in a variable named `result`.\\n"
        "- Respond with ONLY a fenced Python code block, no explanation.\\n\\n"
        f"DataFrame schema:\\n{schema_str}\\n\\n"
        f"Question: {question}"
    )"""

EXTRACT_CODE_IMPL = """\
import re

def extract_code(response: str) -> str:
    fence = '`' * 3
    match = re.search(fence + r'python\\s*(.*?)' + fence, response, re.DOTALL)
    if match:
        return match.group(1).strip()
    match = re.search(fence + r'\\s*(.*?)' + fence, response, re.DOTALL)
    if match:
        return match.group(1).strip()
    return response.strip()"""

RUN_PANDAS_CODE_IMPL = """\
import pandas as pd

def run_pandas_code(code: str, df) -> str:
    namespace = {'df': df, 'pd': pd}
    try:
        exec(code, namespace)
    except Exception as e:
        return f"Code execution error: {e}"
    result = namespace.get('result', 'No result variable found')
    return str(result)"""

ASK_DF_IMPL = """\
import re
import ollama
import pandas as pd

def ask_df(df, question: str, model: str = 'llama3.2') -> str:
    schema  = get_df_schema(df)
    prompt  = build_query_prompt(question, schema)
    resp    = ollama.chat(model=model,
                          messages=[{"role": "user", "content": prompt}])
    code    = extract_code(resp["message"]["content"])
    return run_pandas_code(code, df)"""

ALL_IMPLS = "\n\n\n".join([
    GET_DF_SCHEMA_IMPL,
    BUILD_QUERY_PROMPT_IMPL,
    EXTRACT_CODE_IMPL,
    RUN_PANDAS_CODE_IMPL,
])


# ---------------------------------------------------------------------------
# Exercise 01 — get_df_schema
# ---------------------------------------------------------------------------

def ex01():
    global _cid; _cid = 0
    setup = BASE_IMPORTS + "\n\n\n" + RETAIL_CSV_CODE
    return [
        md(
            "# Day 041 — Exercise 1: get_df_schema\n\n"
            "**What you'll build:** `get_df_schema(df) -> str` — describe a "
            "DataFrame as a readable text block that you can embed in an LLM prompt.\n\n"
            "**Why it matters:** An LLM cannot see your DataFrame directly. "
            "You have to describe it in text: how many rows, what columns exist, "
            "what their types are, and what the data looks like. "
            "`get_df_schema` is the function that produces that description — "
            "it is what the LLM reads before writing pandas code to answer your question."
        ),
        code(setup),
        md("## Your Implementation"),
        code(
            "def get_df_schema(df) -> str:\n"
            '    """\n'
            "    Describe a DataFrame as a readable text block for an LLM prompt.\n\n"
            "    The output must include:\n"
            "    - Shape line: 'Shape: N rows x M columns'\n"
            "    - 'Columns and dtypes:' header\n"
            "    - One line per column: '  col_name: dtype'\n"
            "    - A sample of the first 3 rows via df.head(3).to_string(index=False)\n\n"
            "    Returns:\n"
            "        str — multi-line text block\n"
            '    """\n'
            "    # TODO: build a list of lines\n"
            "    # TODO: add shape line: f'Shape: {df.shape[0]} rows x {df.shape[1]} columns'\n"
            "    # TODO: add 'Columns and dtypes:' header\n"
            "    # TODO: loop over df.dtypes.items() to add each column:dtype line\n"
            "    # TODO: add sample rows via df.head(3).to_string(index=False)\n"
            "    # TODO: return '\\n'.join(lines)\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: function defined\n"
            "    try:\n"
            "        assert 'get_df_schema' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: get_df_schema is defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: returns a string\n"
            "    try:\n"
            "        _schema = get_df_schema(SALES_DF)\n"
            "        assert isinstance(_schema, str), \\\n"
            "            f'expected str, got {type(_schema).__name__}'\n"
            "        passed += 1; print('\\u2705 Check 2: returns a string')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 3: contains shape information\n"
            "    try:\n"
            "        assert '12' in _schema and '7' in _schema, \\\n"
            "            'schema should mention row count (12) and column count (7)'\n"
            "        passed += 1; print('\\u2705 Check 3: schema mentions shape (12 rows, 7 cols)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: contains all column names\n"
            "    try:\n"
            "        for col in SALES_DF.columns:\n"
            "            assert col in _schema, f'missing column: {col}'\n"
            "        passed += 1; print('\\u2705 Check 4: all column names present')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: contains sample row data\n"
            "    try:\n"
            "        assert 'Widget' in _schema or 'Gadget' in _schema, \\\n"
            "            'schema should include sample rows (first 3 rows of data)'\n"
            "        passed += 1; print('\\u2705 Check 5: schema includes sample row data')\n"
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
            + GET_DF_SCHEMA_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 02 — build_query_prompt
# ---------------------------------------------------------------------------

def ex02():
    global _cid; _cid = 100
    setup = BASE_IMPORTS + "\n\n\n" + RETAIL_CSV_CODE + "\n\n\n" + GET_DF_SCHEMA_IMPL
    return [
        md(
            "# Day 041 — Exercise 2: build_query_prompt\n\n"
            "**What you'll build:** `build_query_prompt(question, schema_str) -> str` — "
            "construct the full LLM prompt that includes the schema, the question, "
            "and the rules for how the model must respond.\n\n"
            "**Why it matters:** The prompt is the contract between you and the LLM. "
            "It must tell the model exactly what format to use (a ```python``` block), "
            "what variable to assign the answer to (`result`), and what DataFrame is "
            "available (`df`). A vague prompt produces vague code; a precise prompt "
            "produces code you can exec immediately."
        ),
        code(setup),
        md("## Your Implementation"),
        code(
            "def build_query_prompt(question: str, schema_str: str) -> str:\n"
            '    """\n'
            "    Build a prompt that asks the LLM to write pandas code for a question.\n\n"
            "    The prompt must:\n"
            "    - Tell the model it is a Python data analyst\n"
            "    - State that the DataFrame is loaded as `df` (and `pd` is in scope)\n"
            "    - Require the answer to be stored in a variable called `result`\n"
            "    - Ask for ONLY a ```python ... ``` block, no explanation\n"
            "    - Include schema_str so the model knows the DataFrame layout\n"
            "    - Include the question at the end\n\n"
            "    Returns:\n"
            "        str — the full prompt string\n"
            '    """\n'
            "    # TODO: return a multi-line f-string with all required elements\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: function defined\n"
            "    try:\n"
            "        assert 'build_query_prompt' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: build_query_prompt is defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: returns a string\n"
            "    try:\n"
            "        _schema = get_df_schema(SALES_DF)\n"
            "        _prompt = build_query_prompt('What is the total revenue?', _schema)\n"
            "        assert isinstance(_prompt, str), \\\n"
            "            f'expected str, got {type(_prompt).__name__}'\n"
            "        passed += 1; print('\\u2705 Check 2: returns a string')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 3: contains the question text\n"
            "    try:\n"
            "        assert 'What is the total revenue?' in _prompt, \\\n"
            "            'prompt must include the question text'\n"
            "        passed += 1; print('\\u2705 Check 3: prompt contains the question')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: contains the schema string\n"
            "    try:\n"
            "        assert _schema in _prompt or 'revenue' in _prompt, \\\n"
            "            'prompt must include schema_str'\n"
            "        passed += 1; print('\\u2705 Check 4: prompt contains the schema')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: mentions 'result' variable requirement\n"
            "    try:\n"
            "        assert 'result' in _prompt, \\\n"
            "            \"prompt must mention the 'result' variable requirement\"\n"
            "        passed += 1; print(\"\\u2705 Check 5: prompt mentions 'result' variable\")\n"
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
            + BUILD_QUERY_PROMPT_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 03 — extract_code
# ---------------------------------------------------------------------------

def ex03():
    global _cid; _cid = 200
    setup = BASE_IMPORTS + "\n\n\n" + RETAIL_CSV_CODE
    return [
        md(
            "# Day 041 — Exercise 3: extract_code\n\n"
            "**What you'll build:** `extract_code(response) -> str` — "
            "parse a raw LLM response and return only the Python code, "
            "stripping markdown fences.\n\n"
            "**Why it matters:** LLMs wrap code in markdown fences like "
            "`\\`\\`\\`python ... \\`\\`\\``. You cannot exec that directly — "
            "you need the code inside. `extract_code` uses `re.search` with "
            "`re.DOTALL` to match the content across newlines. "
            "It tries three patterns in order: `\\`\\`\\`python`, plain `\\`\\`\\``, "
            "then falls back to the raw response."
        ),
        code(setup),
        md("## Your Implementation"),
        code(
            "import re\n"
            "\n"
            "def extract_code(response: str) -> str:\n"
            '    """\n'
            "    Extract Python code from an LLM response.\n\n"
            "    Try in order:\n"
            "    1. re.search(r'```python\\\\s*(.*?)```', response, re.DOTALL)\n"
            "    2. re.search(r'```\\\\s*(.*?)```', response, re.DOTALL)\n"
            "    3. Fall back: return response.strip()\n\n"
            "    In all cases, return match.group(1).strip() or response.strip().\n\n"
            "    Returns:\n"
            "        str — the extracted (and stripped) Python code\n"
            '    """\n'
            "    # TODO: try pattern 1: r'```python\\s*(.*?)```' with re.DOTALL\n"
            "    # TODO: if matched, return match.group(1).strip()\n"
            "    # TODO: try pattern 2: r'```\\s*(.*?)```' with re.DOTALL\n"
            "    # TODO: if matched, return match.group(1).strip()\n"
            "    # TODO: fall back: return response.strip()\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: function defined\n"
            "    try:\n"
            "        assert 'extract_code' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: extract_code is defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: extracts from ```python...``` block\n"
            "    try:\n"
            "        _resp = '```python\\nresult = df.shape[0]\\n```'\n"
            "        _code = extract_code(_resp)\n"
            "        assert _code == 'result = df.shape[0]', \\\n"
            "            f'expected \"result = df.shape[0]\", got {repr(_code)}'\n"
            "        passed += 1; print('\\u2705 Check 2: extracts from ```python block')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: extracts from plain ``` block\n"
            "    try:\n"
            "        _resp2 = '```\\nresult = 42\\n```'\n"
            "        _code2 = extract_code(_resp2)\n"
            "        assert _code2 == 'result = 42', \\\n"
            "            f'expected \"result = 42\", got {repr(_code2)}'\n"
            "        passed += 1; print('\\u2705 Check 3: extracts from plain ``` block')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: handles multi-line code blocks correctly\n"
            "    try:\n"
            "        _multi = '```python\\ntotals = df.groupby(\"product\")[\"revenue\"].sum()\\nresult = totals.idxmax()\\n```'\n"
            "        _extracted = extract_code(_multi)\n"
            "        assert 'totals' in _extracted and 'result' in _extracted, \\\n"
            "            'multi-line block not extracted correctly'\n"
            "        passed += 1; print('\\u2705 Check 4: handles multi-line code block')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: falls back to stripped raw text when no fence found\n"
            "    try:\n"
            "        _raw = '  result = df.shape[0]  '\n"
            "        _fallback = extract_code(_raw)\n"
            "        assert _fallback == 'result = df.shape[0]', \\\n"
            "            f'fallback should strip whitespace, got {repr(_fallback)}'\n"
            "        passed += 1; print('\\u2705 Check 5: falls back to stripped raw text')\n"
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
            + EXTRACT_CODE_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 04 — run_pandas_code
# ---------------------------------------------------------------------------

def ex04():
    global _cid; _cid = 300
    setup = (
        BASE_IMPORTS + "\n\n\n"
        + RETAIL_CSV_CODE + "\n\n\n"
        + GET_DF_SCHEMA_IMPL + "\n\n\n"
        + BUILD_QUERY_PROMPT_IMPL + "\n\n\n"
        + EXTRACT_CODE_IMPL
    )
    return [
        md(
            "# Day 041 — Exercise 4: run_pandas_code\n\n"
            "**What you'll build:** `run_pandas_code(code, df) -> str` — "
            "safely exec a string of Python code in a namespace that has "
            "`df` and `pd` available, read the `result` variable, and return it as a string.\n\n"
            "**Why it matters:** `exec()` in a controlled namespace is how you run "
            "LLM-generated code without exposing your full Python environment. "
            "The namespace dict acts as a sandbox: the code can only see `df` and `pd` "
            "(plus Python builtins). Wrapping exec in try/except means a bad code "
            "generation returns an informative error string instead of crashing the pipeline."
        ),
        code(setup),
        md("## Your Implementation"),
        code(
            "import pandas as pd\n"
            "\n"
            "def run_pandas_code(code: str, df) -> str:\n"
            '    """\n'
            "    Execute a pandas code string and return the result as a string.\n\n"
            "    - Create namespace = {'df': df, 'pd': pd}\n"
            "    - exec(code, namespace) wrapped in try/except Exception\n"
            "    - On exception: return f'Code execution error: {e}'\n"
            "    - After exec: result = namespace.get('result', 'No result variable found')\n"
            "    - Return str(result)\n\n"
            "    Returns:\n"
            "        str — str(result) from the exec'd code, or error message\n"
            '    """\n'
            "    # TODO: build namespace dict with df and pd\n"
            "    # TODO: try exec(code, namespace), except Exception as e: return error str\n"
            "    # TODO: get result from namespace, return str(result)\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: function defined\n"
            "    try:\n"
            "        assert 'run_pandas_code' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: run_pandas_code is defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: returns a string\n"
            "    try:\n"
            "        _r = run_pandas_code('result = df.shape[0]', SALES_DF)\n"
            "        assert isinstance(_r, str), \\\n"
            "            f'expected str, got {type(_r).__name__}'\n"
            "        passed += 1; print('\\u2705 Check 2: returns a string')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 3: correctly evaluates row count\n"
            "    try:\n"
            "        assert _r == '12', \\\n"
            "            f'df.shape[0] should be 12, got {repr(_r)}'\n"
            "        passed += 1; print('\\u2705 Check 3: df.shape[0] → \"12\" correct')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: executes pandas aggregation correctly\n"
            "    try:\n"
            "        _rev = run_pandas_code(\"result = df['revenue'].sum()\", SALES_DF)\n"
            "        assert '4105' in _rev, \\\n"
            "            f'revenue sum should contain 4105, got {repr(_rev)}'\n"
            "        passed += 1; print(f'\\u2705 Check 4: revenue sum correct ({_rev})')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: returns error message on bad code (not an exception)\n"
            "    try:\n"
            "        _err = run_pandas_code('result = df[\"nonexistent_col\"].sum()', SALES_DF)\n"
            "        assert 'error' in _err.lower() or 'Error' in _err, \\\n"
            "            f'bad code should return error string, got {repr(_err)}'\n"
            "        passed += 1; print('\\u2705 Check 5: bad code returns error string')\n"
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
            + RUN_PANDAS_CODE_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 05 — ask_df
# ---------------------------------------------------------------------------

def ex05():
    global _cid; _cid = 400
    return [
        md(
            "# Day 041 — Exercise 5: ask_df\n\n"
            "**What you'll build:** `ask_df(df, question, model) -> str` — "
            "the full end-to-end pipeline: get schema, build prompt, call Ollama, "
            "extract code, exec, return result.\n\n"
            "**Why it matters:** Five lines of composition wire together everything "
            "you built in Exercises 1-4. A user types a plain-English question, "
            "the LLM writes the pandas code, and you execute it and return the answer. "
            "That is 'Chat with your CSV' — no query language, no SQL, just English."
        ),
        md("## Provided: All Pipeline Functions"),
        code(
            BASE_IMPORTS + "\n\n\n"
            + ALL_IMPLS
        ),
        code(RETAIL_CSV_CODE),
        md("## Your Implementation"),
        code(
            "import re\n"
            "import ollama\n"
            "import pandas as pd\n"
            "\n"
            "def ask_df(df, question: str, model: str = 'llama3.2') -> str:\n"
            '    """\n'
            "    Answer a plain-English question about a DataFrame using an LLM.\n\n"
            "    Pipeline:\n"
            "    1. schema  = get_df_schema(df)\n"
            "    2. prompt  = build_query_prompt(question, schema)\n"
            "    3. resp    = ollama.chat(model=model, messages=[{user: prompt}])\n"
            "    4. code    = extract_code(resp['message']['content'])\n"
            "    5. return run_pandas_code(code, df)\n\n"
            "    Returns:\n"
            "        str — the answer (result of the exec'd pandas code as a string)\n"
            '    """\n'
            "    # TODO: wire up the 5-step pipeline\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "    _result = None\n"
            "\n"
            "    # Check 1: function defined\n"
            "    try:\n"
            "        assert 'ask_df' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: ask_df is defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: returns a string (Ollama call)\n"
            "    try:\n"
            "        _result = ask_df(SALES_DF, 'What is the total revenue?')\n"
            "        assert isinstance(_result, str), \\\n"
            "            f'expected str, got {type(_result).__name__}'\n"
            "        passed += 1; print('\\u2705 Check 2: returns a string')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 3: response is non-empty\n"
            "    try:\n"
            "        assert len(_result.strip()) > 0, 'response is empty'\n"
            "        passed += 1; print(f'\\u2705 Check 3: response is non-empty')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: total revenue answer contains 4105 (the correct sum)\n"
            "    try:\n"
            "        assert '4105' in _result, \\\n"
            "            f'total revenue should be 4105.0, got {repr(_result)}'\n"
            "        passed += 1; print(f'\\u2705 Check 4: correct revenue total in answer')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: also works for a different question\n"
            "    try:\n"
            "        _result2 = ask_df(SALES_DF,\n"
            "                          'How many rows are in the dataset?')\n"
            "        assert isinstance(_result2, str) and len(_result2.strip()) > 0\n"
            "        passed += 1; print(f'\\u2705 Check 5: works for different question ({repr(_result2[:30])})')\n"
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
            + ASK_DF_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Project notebook
# ---------------------------------------------------------------------------

def project_nb():
    global _cid; _cid = 500
    all_fns = ALL_IMPLS + "\n\n\n" + ASK_DF_IMPL
    return [
        md(
            "# Day 041 Project: Chat with your CSV\n\n"
            "## What You're Building\n\n"
            "A natural-language interface for any CSV: you ask a plain-English question, "
            "the LLM writes the pandas code, you execute it, and get the answer back.\n\n"
            "**Deliverable:** Ask 4 different questions about SALES_DF. "
            "All `_run_project_checks()` pass.\n\n"
            "## Project Requirements\n\n"
            "1. Load `RETAIL_CSV` into `SALES_DF` with a `revenue` column\n"
            "2. Ask: 'What is the total revenue?' → store result in `a1`\n"
            "3. Ask: 'Which product has the highest revenue?' → store result in `a2`\n"
            "4. Ask: 'How many orders are there in each region?' → store result in `a3`\n"
            "5. Ask a question of your own choosing → store result in `a4`"
        ),
        code(
            BASE_IMPORTS + "\n\n\n"
            + all_fns + "\n\n\n"
            + RETAIL_CSV_CODE + "\n\n"
            + "print(f'Loaded {SALES_DF.shape[0]} rows')"
        ),
        md("## Your Questions"),
        code(
            "# Question 1: total revenue\n"
            "# TODO: a1 = ask_df(SALES_DF, 'What is the total revenue?')\n"
            "# TODO: print('Q1:', a1)\n"
            "\n"
            "# Question 2: top product by revenue\n"
            "# TODO: a2 = ask_df(SALES_DF, 'Which product has the highest revenue?')\n"
            "# TODO: print('Q2:', a2)\n"
            "\n"
            "# Question 3: orders per region\n"
            "# TODO: a3 = ask_df(SALES_DF, 'How many orders are there in each region?')\n"
            "# TODO: print('Q3:', a3)\n"
            "\n"
            "# Question 4: your own question\n"
            "# TODO: a4 = ask_df(SALES_DF, 'YOUR QUESTION HERE')\n"
            "# TODO: print('Q4:', a4)"
        ),
        md("## Project Checks"),
        code(
            "def _run_project_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: SALES_DF loaded with revenue\n"
            "    try:\n"
            "        assert 'SALES_DF' in globals() and 'revenue' in SALES_DF.columns\n"
            "        passed += 1; print(f'\\u2705 Check 1: SALES_DF loaded ({len(SALES_DF)} rows)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "\n"
            "    # Check 2: a1 is a non-empty string containing total revenue\n"
            "    try:\n"
            "        assert 'a1' in globals(), 'a1 not defined'\n"
            "        assert isinstance(a1, str) and len(a1.strip()) > 0\n"
            "        assert '4105' in a1, f'a1 should contain 4105, got {repr(a1)}'\n"
            "        passed += 1; print(f'\\u2705 Check 2: a1 correct ({repr(a1[:40])})')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: a2 is a non-empty string mentioning Gadget\n"
            "    try:\n"
            "        assert 'a2' in globals(), 'a2 not defined'\n"
            "        assert isinstance(a2, str) and len(a2.strip()) > 0\n"
            "        assert 'Gadget' in a2 or 'gadget' in a2.lower(), \\\n"
            "            f'a2 should mention Gadget (highest revenue), got {repr(a2)}'\n"
            "        passed += 1; print(f'\\u2705 Check 3: a2 identifies Gadget as top product')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: a3 is a non-empty string\n"
            "    try:\n"
            "        assert 'a3' in globals(), 'a3 not defined'\n"
            "        assert isinstance(a3, str) and len(a3.strip()) > 0\n"
            "        passed += 1; print(f'\\u2705 Check 4: a3 is non-empty ({len(a3)} chars)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: a4 is a non-empty string (user's own question)\n"
            "    try:\n"
            "        assert 'a4' in globals(), 'a4 not defined'\n"
            "        assert isinstance(a4, str) and len(a4.strip()) > 0\n"
            "        passed += 1; print(f'\\u2705 Check 5: a4 answered ({len(a4)} chars)')\n"
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
            "- Loop `ask_df` over a list of 10 questions and print all answers\n"
            "- Add a retry: if the answer contains 'error', call `ask_df` again with "
            "'make sure to assign the result to a variable called result' appended\n"
            "- Display the generated pandas code alongside the answer "
            "(split `ask_df` into schema+prompt+LLM+extract steps and print the code before running it)\n"
            "- On Day 43 you will build the SQL equivalent: ask questions and "
            "get SQL generated and executed against a real database"
        ),
    ]


# ---------------------------------------------------------------------------
# Solution notebook
# ---------------------------------------------------------------------------

def solution_nb():
    global _cid; _cid = 600
    all_fns = ALL_IMPLS + "\n\n\n" + ASK_DF_IMPL
    return [
        md(
            "# Day 041 Solution — Natural Language → Pandas\n\n"
            "get_df_schema, build_query_prompt, extract_code, run_pandas_code, ask_df. "
            "All data and functions defined inline."
        ),
        code(BASE_IMPORTS + "\n\n\n" + all_fns),
        md("## Step 1 — Load Data"),
        code(
            RETAIL_CSV_CODE + "\n\n"
            "print(f'Shape: {SALES_DF.shape}')\n"
            "assert SALES_DF.shape == (12, 7)\n"
            "assert 'revenue' in SALES_DF.columns"
        ),
        md("## Step 2 — Inspect Schema"),
        code(
            "schema = get_df_schema(SALES_DF)\n"
            "print(schema)\n\n"
            "assert '12' in schema\n"
            "assert 'revenue' in schema\n"
            "assert 'Widget' in schema or 'Gadget' in schema"
        ),
        md("## Step 3 — Extract Code (deterministic checks)"),
        code(
            "# Verify extract_code with known inputs\n"
            "_r1 = extract_code('```python\\nresult = 42\\n```')\n"
            "assert _r1 == 'result = 42', repr(_r1)\n"
            "print('extract_code(```python): OK')\n\n"
            "_r2 = extract_code('```\\nresult = 99\\n```')\n"
            "assert _r2 == 'result = 99', repr(_r2)\n"
            "print('extract_code(```): OK')\n\n"
            "_r3 = extract_code('  result = 0  ')\n"
            "assert _r3 == 'result = 0', repr(_r3)\n"
            "print('extract_code(raw): OK')"
        ),
        md("## Step 4 — Run Pandas Code (deterministic checks)"),
        code(
            "_v1 = run_pandas_code('result = df.shape[0]', SALES_DF)\n"
            "assert _v1 == '12', repr(_v1)\n"
            "print(f'row count: {_v1}')\n\n"
            "_v2 = run_pandas_code(\"result = df['revenue'].sum()\", SALES_DF)\n"
            "assert '4105' in _v2, repr(_v2)\n"
            "print(f'total revenue: {_v2}')\n\n"
            "_err = run_pandas_code('result = df[\"bad_col\"].sum()', SALES_DF)\n"
            "assert 'error' in _err.lower()\n"
            "print(f'error handling: {_err}')"
        ),
        md("## Step 5 — Full Q&A Pipeline (Ollama)"),
        code(
            "a1 = ask_df(SALES_DF, 'What is the total revenue?')\n"
            "print('Q1:', a1)\n"
            "assert '4105' in a1\n\n"
            "a2 = ask_df(SALES_DF, 'Which product has the highest revenue?')\n"
            "print('Q2:', a2)\n"
            "assert 'Gadget' in a2 or 'gadget' in a2.lower()\n\n"
            "a3 = ask_df(SALES_DF, 'How many orders are there in each region?')\n"
            "print('Q3:', a3)\n"
            "assert isinstance(a3, str) and len(a3.strip()) > 0\n\n"
            "a4 = ask_df(SALES_DF, 'What is the average price of all orders?')\n"
            "print('Q4:', a4)\n"
            "assert isinstance(a4, str) and len(a4.strip()) > 0\n\n"
            "print('\\nAll Q&A checks passed.')"
        ),
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Generating Day 041 notebooks...")
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
