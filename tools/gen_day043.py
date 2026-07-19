#!/usr/bin/env python3
"""Generate all Day 043 notebooks: exercises 1-5, project, solution."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAY_DIR = ROOT / "03_data_analysis" / "day_043"

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

BASE_IMPORTS = """\
import warnings
warnings.filterwarnings('ignore')
import sqlite3
import re
import ollama"""

SETUP_DB_IMPL = """\
import sqlite3

def setup_db(conn):
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id  INTEGER PRIMARY KEY,
            product   TEXT,
            category  TEXT,
            region    TEXT,
            price     REAL,
            quantity  INTEGER,
            revenue   REAL
        )''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS products (
            product    TEXT PRIMARY KEY,
            category   TEXT,
            unit_price REAL
        )''')
    rows = [
        (1,'Widget','Electronics','North',25.0,10,250.0),
        (2,'Gadget','Electronics','South',150.0,3,450.0),
        (3,'Widget','Electronics','South',25.0,5,125.0),
        (4,'Doohickey','Accessories','East',8.0,50,400.0),
        (5,'Gadget','Electronics','East',150.0,7,1050.0),
        (6,'Widget','Electronics','East',25.0,4,100.0),
        (7,'Doohickey','Accessories','North',8.0,20,160.0),
        (8,'Gadget','Electronics','North',150.0,2,300.0),
        (9,'Widget','Electronics','West',25.0,6,150.0),
        (10,'Doohickey','Accessories','South',8.0,15,120.0),
        (11,'Thingamajig','Accessories','North',200.0,1,200.0),
        (12,'Thingamajig','Accessories','East',200.0,4,800.0),
    ]
    cur.executemany(
        'INSERT OR IGNORE INTO orders VALUES (?,?,?,?,?,?,?)', rows
    )
    products = [
        ('Widget','Electronics',25.0),
        ('Gadget','Electronics',150.0),
        ('Doohickey','Accessories',8.0),
        ('Thingamajig','Accessories',200.0),
    ]
    cur.executemany(
        'INSERT OR IGNORE INTO products VALUES (?,?,?)', products
    )
    conn.commit()"""

RUN_QUERY_IMPL = """\
def run_query(conn, sql, params=()):
    cur = conn.cursor()
    cur.execute(sql, params)
    cols = [col[0] for col in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]"""

# NOTE: uses sqlite_master to return DDL for all tables
GET_DB_SCHEMA_IMPL = """\
def get_db_schema(conn) -> str:
    cur = conn.cursor()
    cur.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    rows = cur.fetchall()
    if not rows:
        return 'No tables found.'
    parts = []
    for name, ddl in rows:
        parts.append(f'Table: {name}')
        parts.append(ddl)
        parts.append('')
    return '\\n'.join(parts).strip()"""

# NOTE: "fenced SQL code block" replaces literal triple-backtick to avoid injection bug
BUILD_SQL_PROMPT_IMPL = """\
def build_sql_prompt(question: str, schema_str: str) -> str:
    return (
        'You are a SQL expert. Write a SQLite SELECT query to answer the question.\\n\\n'
        'Requirements:\\n'
        '- Use only SELECT statements.\\n'
        '- The database schema is provided below.\\n'
        '- Respond with ONLY a fenced SQL code block, no explanation.\\n\\n'
        f'Schema:\\n{schema_str}\\n\\n'
        f'Question: {question}'
    )"""

# NOTE: fence = '`'*3 avoids literal triple-backticks in source (injection bug fix)
EXTRACT_SQL_IMPL = """\
import re

def extract_sql(response: str) -> str:
    fence = '`' * 3
    match = re.search(fence + r'sql\\s*(.*?)' + fence, response, re.DOTALL)
    if match:
        return match.group(1).strip()
    match = re.search(fence + r'\\s*(.*?)' + fence, response, re.DOTALL)
    if match:
        return match.group(1).strip()
    return response.strip()"""

IS_SAFE_SQL_IMPL = """\
import re

def is_safe_sql(sql: str) -> bool:
    normalized = re.sub(r'--[^\\n]*', '', sql)
    normalized = re.sub(r'/\\*.*?\\*/', '', normalized, flags=re.DOTALL)
    normalized = normalized.strip().lower()
    if not normalized.startswith('select'):
        return False
    if ';' in normalized:
        return False
    return True"""

ASK_DB_IMPL = """\
import ollama

def ask_db(conn, question: str, model: str = 'llama3.2') -> str:
    schema = get_db_schema(conn)
    prompt = build_sql_prompt(question, schema)
    resp   = ollama.chat(model=model,
                         messages=[{'role': 'user', 'content': prompt}])
    sql    = extract_sql(resp['message']['content'])
    if not is_safe_sql(sql):
        return f'Unsafe SQL rejected: {sql[:120]}'
    try:
        rows = run_query(conn, sql)
    except Exception as e:
        return f'Query error: {e}'
    if not rows:
        return 'No results found.'
    return str(rows)"""

ALL_IMPLS = "\n\n\n".join([
    SETUP_DB_IMPL,
    RUN_QUERY_IMPL,
    GET_DB_SCHEMA_IMPL,
    BUILD_SQL_PROMPT_IMPL,
    EXTRACT_SQL_IMPL,
    IS_SAFE_SQL_IMPL,
    ASK_DB_IMPL,
])


# ---------------------------------------------------------------------------
# Exercise 01 — get_db_schema
# ---------------------------------------------------------------------------

def ex01():
    global _cid; _cid = 0
    setup = SETUP_DB_IMPL + "\n\n\nconn = sqlite3.connect(':memory:')\nsetup_db(conn)"
    return [
        md(
            "# Day 043 — Exercise 1: get_db_schema\n\n"
            "**What you'll build:** `get_db_schema(conn) -> str` — query "
            "`sqlite_master` to produce a human-readable (and LLM-readable) "
            "description of all tables and their CREATE TABLE statements.\n\n"
            "**Why it matters:** The LLM cannot see inside the database. "
            "You must describe it in the prompt. `sqlite_master` stores the original "
            "DDL for every table — querying it gives you column names, types, and "
            "constraints in a compact form the LLM already understands. "
            "This is the same role `get_df_schema` played in Day 41 for pandas."
        ),
        code(
            "import warnings\nwarnings.filterwarnings('ignore')\nimport sqlite3\n\n\n"
            + setup
        ),
        md("## Your Implementation"),
        code(
            "def get_db_schema(conn) -> str:\n"
            '    """\n'
            "    Return a string describing all tables in the database.\n\n"
            "    Query: SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name\n"
            "    For each table, output 'Table: {name}' then the DDL string.\n"
            "    Join parts with newlines. Return 'No tables found.' if empty.\n"
            '    """\n'
            "    cur = conn.cursor()\n"
            "    # TODO: cur.execute(\"SELECT name, sql FROM sqlite_master\n"
            "    #           WHERE type='table' ORDER BY name\")\n"
            "    # TODO: rows = cur.fetchall()   # list of (name, ddl) tuples\n"
            "    # TODO: build parts list: for each (name, ddl), append 'Table: {name}', ddl, ''\n"
            "    # TODO: return '\\n'.join(parts).strip()\n"
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
            "        assert 'get_db_schema' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: get_db_schema is defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: returns a non-empty string\n"
            "    try:\n"
            "        schema = get_db_schema(conn)\n"
            "        assert isinstance(schema, str), f'expected str, got {type(schema).__name__}'\n"
            "        assert len(schema) > 0, 'schema string is empty'\n"
            "        passed += 1; print('\\u2705 Check 2: returns a non-empty string')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 3: contains 'orders' table name\n"
            "    try:\n"
            "        assert 'orders' in schema.lower(), \\\n"
            "            'schema should mention the orders table'\n"
            "        passed += 1; print('\\u2705 Check 3: schema contains orders table')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: contains 'products' table name\n"
            "    try:\n"
            "        assert 'products' in schema.lower(), \\\n"
            "            'schema should mention the products table'\n"
            "        passed += 1; print('\\u2705 Check 4: schema contains products table')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: contains column name 'revenue'\n"
            "    try:\n"
            "        assert 'revenue' in schema.lower(), \\\n"
            "            'schema should mention revenue column'\n"
            "        passed += 1; print('\\u2705 Check 5: schema contains revenue column')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\\U0001f389 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n\n"
            "_run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + GET_DB_SCHEMA_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 02 — build_sql_prompt
# ---------------------------------------------------------------------------

def ex02():
    global _cid; _cid = 100
    return [
        md(
            "# Day 043 — Exercise 2: build_sql_prompt\n\n"
            "**What you'll build:** `build_sql_prompt(question: str, schema_str: str) -> str` — "
            "construct the prompt that tells the LLM to write a SELECT query.\n\n"
            "**Why it matters:** The prompt is the only interface between your code and "
            "the LLM. It must tell the model its role ('SQL expert'), the constraints "
            "('SELECT only, fenced block'), and supply the schema and question. "
            "A vague prompt produces vague SQL; a precise prompt produces precise SQL."
        ),
        code(
            "import warnings\nwarnings.filterwarnings('ignore')\n"
        ),
        md("## Your Implementation"),
        code(
            "def build_sql_prompt(question: str, schema_str: str) -> str:\n"
            '    """\n'
            "    Build a prompt asking the LLM to write a SQLite SELECT query.\n\n"
            "    The prompt must include:\n"
            "    - Role: 'SQL expert'\n"
            "    - Constraint: SELECT only, respond with a fenced SQL code block\n"
            "    - The schema_str\n"
            "    - The question\n"
            '    """\n'
            "    # TODO: return a multi-line string containing the schema and question\n"
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
            "        assert 'build_sql_prompt' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: build_sql_prompt is defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    SCHEMA = 'Table: orders\\nCREATE TABLE orders (order_id INTEGER, revenue REAL)'\n"
            "    Q = 'What is the total revenue?'\n"
            "\n"
            "    # Check 2: returns a string\n"
            "    try:\n"
            "        prompt = build_sql_prompt(Q, SCHEMA)\n"
            "        assert isinstance(prompt, str), f'expected str, got {type(prompt).__name__}'\n"
            "        assert len(prompt) > 0\n"
            "        passed += 1; print('\\u2705 Check 2: returns a non-empty string')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 3: prompt contains the question\n"
            "    try:\n"
            "        assert Q in prompt, f'question not found in prompt'\n"
            "        passed += 1; print('\\u2705 Check 3: prompt contains the question')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: prompt contains the schema string\n"
            "    try:\n"
            "        assert SCHEMA in prompt, 'schema_str not found in prompt'\n"
            "        passed += 1; print('\\u2705 Check 4: prompt contains schema_str')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: prompt mentions SELECT or SQL\n"
            "    try:\n"
            "        assert 'SELECT' in prompt or 'SQL' in prompt or 'select' in prompt, \\\n"
            "            'prompt should instruct the LLM to write SQL/SELECT'\n"
            "        passed += 1; print('\\u2705 Check 5: prompt mentions SELECT/SQL instruction')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\\U0001f389 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n\n"
            "_run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + BUILD_SQL_PROMPT_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 03 — extract_sql
# ---------------------------------------------------------------------------

def ex03():
    global _cid; _cid = 200
    return [
        md(
            "# Day 043 — Exercise 3: extract_sql\n\n"
            "**What you'll build:** `extract_sql(response: str) -> str` — "
            "parse the SQL query out of the LLM's fenced response.\n\n"
            "**Why it matters:** LLMs wrap code in fenced blocks: "
            "` ```sql ` ... ` ``` `. "
            "You need to extract just the SQL, strip whitespace, and fall back "
            "gracefully if the model returns plain SQL with no fence. "
            "This is the same pattern as Day 41's `extract_code`, applied to SQL."
        ),
        code("import warnings\nwarnings.filterwarnings('ignore')\nimport re\n"),
        md("## Your Implementation"),
        code(
            "def extract_sql(response: str) -> str:\n"
            '    """\n'
            "    Extract the SQL query from a fenced LLM response.\n\n"
            "    Try matching a fenced sql block first (fence + 'sql' + content + fence).\n"
            "    Fall back to any fenced block. Fall back to returning the stripped response.\n\n"
            "    Use fence = '`' * 3 to construct the fence string dynamically.\n"
            "    Use re.DOTALL so '.' matches newlines in multi-line SQL.\n"
            '    """\n'
            "    import re\n"
            "    fence = '`' * 3\n"
            "    # TODO: match = re.search(fence + r'sql\\s*(.*?)' + fence, response, re.DOTALL)\n"
            "    # TODO: if match: return match.group(1).strip()\n"
            "    # TODO: match = re.search(fence + r'\\s*(.*?)' + fence, response, re.DOTALL)\n"
            "    # TODO: if match: return match.group(1).strip()\n"
            "    # TODO: return response.strip()\n"
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
            "        assert 'extract_sql' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: extract_sql is defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    fence = '`' * 3\n"
            "\n"
            "    # Check 2: extracts from sql-tagged fence\n"
            "    try:\n"
            "        sql_text = 'SELECT * FROM orders WHERE revenue > 100'\n"
            "        response = fence + 'sql\\n' + sql_text + '\\n' + fence\n"
            "        result = extract_sql(response)\n"
            "        assert result == sql_text, \\\n"
            "            f'expected {sql_text!r}, got {result!r}'\n"
            "        passed += 1; print('\\u2705 Check 2: extracts from sql-tagged fence')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: extracts from untagged fence\n"
            "    try:\n"
            "        sql_text = 'SELECT COUNT(*) FROM orders'\n"
            "        response = fence + '\\n' + sql_text + '\\n' + fence\n"
            "        result = extract_sql(response)\n"
            "        assert result == sql_text, \\\n"
            "            f'expected {sql_text!r}, got {result!r}'\n"
            "        passed += 1; print('\\u2705 Check 3: extracts from untagged fence')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: falls back to stripped plain text\n"
            "    try:\n"
            "        sql_text = 'SELECT * FROM orders'\n"
            "        result = extract_sql('  ' + sql_text + '  ')\n"
            "        assert result == sql_text, \\\n"
            "            f'fallback failed: expected {sql_text!r}, got {result!r}'\n"
            "        passed += 1; print('\\u2705 Check 4: falls back to stripped plain text')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: handles multi-line SQL in fenced block\n"
            "    try:\n"
            "        multi = 'SELECT product,\\n       SUM(revenue) AS total\\nFROM orders\\nGROUP BY product'\n"
            "        response = fence + 'sql\\n' + multi + '\\n' + fence\n"
            "        result = extract_sql(response)\n"
            "        assert 'GROUP BY' in result, f'multi-line SQL not preserved: {result!r}'\n"
            "        passed += 1; print('\\u2705 Check 5: multi-line SQL extracted correctly')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\\U0001f389 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n\n"
            "_run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + EXTRACT_SQL_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 04 — is_safe_sql
# ---------------------------------------------------------------------------

def ex04():
    global _cid; _cid = 300
    return [
        md(
            "# Day 043 — Exercise 4: is_safe_sql\n\n"
            "**What you'll build:** `is_safe_sql(sql: str) -> bool` — "
            "a guardrail that rejects anything that is not a plain SELECT statement.\n\n"
            "**Why it matters:** The LLM generates the SQL — which means you cannot "
            "trust it the way you trust code you wrote yourself. A prompt injection "
            "attack, a confused model, or a malformed prompt could produce "
            "`DROP TABLE` or `INSERT`. `is_safe_sql` is the gate between the LLM "
            "and your database: only SELECT queries pass through."
        ),
        code("import warnings\nwarnings.filterwarnings('ignore')\nimport re\n"),
        md("## Your Implementation"),
        code(
            "def is_safe_sql(sql: str) -> bool:\n"
            '    """\n'
            "    Return True only if sql is a safe SELECT statement.\n\n"
            "    Steps:\n"
            "    1. Strip SQL line comments (-- ...) and block comments (/* ... */)\n"
            "    2. strip() and lower()\n"
            "    3. Return False if result does not start with 'select'\n"
            "    4. Return False if ';' appears (multi-statement injection)\n"
            "    5. Return True\n"
            '    """\n'
            "    import re\n"
            "    # TODO: normalized = re.sub(r'--[^\\n]*', '', sql)          # strip line comments\n"
            "    # TODO: normalized = re.sub(r'/\\*.*?\\*/', '', normalized,  # strip block comments\n"
            "    # TODO:                     flags=re.DOTALL)\n"
            "    # TODO: normalized = normalized.strip().lower()\n"
            "    # TODO: if not normalized.startswith('select'): return False\n"
            "    # TODO: if ';' in normalized: return False\n"
            "    # TODO: return True\n"
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
            "        assert 'is_safe_sql' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: is_safe_sql is defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: plain SELECT is safe\n"
            "    try:\n"
            "        assert is_safe_sql('SELECT * FROM orders') is True, \\\n"
            "            'SELECT * FROM orders should be safe'\n"
            "        passed += 1; print('\\u2705 Check 2: SELECT * FROM orders is safe')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: INSERT is rejected\n"
            "    try:\n"
            "        assert is_safe_sql(\"INSERT INTO orders VALUES (99,'x','y','z',0,0,0)\") is False, \\\n"
            "            'INSERT should be rejected'\n"
            "        passed += 1; print('\\u2705 Check 3: INSERT is rejected')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: DROP is rejected\n"
            "    try:\n"
            "        assert is_safe_sql('DROP TABLE orders') is False, \\\n"
            "            'DROP TABLE should be rejected'\n"
            "        passed += 1; print('\\u2705 Check 4: DROP TABLE is rejected')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: multi-statement injection rejected\n"
            "    try:\n"
            "        assert is_safe_sql('SELECT * FROM orders; DROP TABLE orders') is False, \\\n"
            "            'semicolon multi-statement should be rejected'\n"
            "        passed += 1; print('\\u2705 Check 5: multi-statement injection rejected')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\\U0001f389 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n\n"
            "_run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + IS_SAFE_SQL_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 05 — ask_db (full pipeline, uses Ollama)
# ---------------------------------------------------------------------------

def ex05():
    global _cid; _cid = 400
    setup = "\n\n\n".join([
        BASE_IMPORTS,
        SETUP_DB_IMPL,
        RUN_QUERY_IMPL,
        GET_DB_SCHEMA_IMPL,
        BUILD_SQL_PROMPT_IMPL,
        EXTRACT_SQL_IMPL,
        IS_SAFE_SQL_IMPL,
    ])
    return [
        md(
            "# Day 043 — Exercise 5: ask_db\n\n"
            "**What you'll build:** `ask_db(conn, question, model='llama3.2') -> str` — "
            "the full natural-language-to-SQL pipeline: schema → prompt → LLM → "
            "extract SQL → validate → execute → return string result.\n\n"
            "**Why it matters:** This is the Day 43 deliverable — a function that "
            "lets anyone query a database in plain English. It composes everything "
            "from today: schema description, prompt construction, SQL extraction, "
            "safety checking, and query execution. "
            "Day 43 is to SQL what Day 41's `ask_df` is to pandas."
        ),
        md("## Provided: All Helper Functions"),
        code(setup),
        code("conn = sqlite3.connect(':memory:')\nsetup_db(conn)"),
        md("## Your Implementation"),
        code(
            "def ask_db(conn, question: str, model: str = 'llama3.2') -> str:\n"
            '    """\n'
            "    Answer a natural-language question by generating and running SQL.\n\n"
            "    Pipeline:\n"
            "    1. get_db_schema(conn)                → schema string\n"
            "    2. build_sql_prompt(question, schema)  → prompt string\n"
            "    3. ollama.chat(model, messages=[...])  → LLM response\n"
            "    4. extract_sql(response content)       → SQL string\n"
            "    5. is_safe_sql(sql) — if False return rejection message\n"
            "    6. run_query(conn, sql)               → list[dict]\n"
            "    7. return str(rows) or 'No results found.'\n"
            "       wrap run_query in try/except and return 'Query error: {e}' on failure\n"
            '    """\n'
            "    import ollama\n"
            "    # TODO: schema = get_db_schema(conn)\n"
            "    # TODO: prompt = build_sql_prompt(question, schema)\n"
            "    # TODO: resp = ollama.chat(model=model,\n"
            "    # TODO:                    messages=[{'role': 'user', 'content': prompt}])\n"
            "    # TODO: sql = extract_sql(resp['message']['content'])\n"
            "    # TODO: if not is_safe_sql(sql): return f'Unsafe SQL rejected: {sql[:120]}'\n"
            "    # TODO: try: rows = run_query(conn, sql)\n"
            "    # TODO: except Exception as e: return f'Query error: {e}'\n"
            "    # TODO: if not rows: return 'No results found.'\n"
            "    # TODO: return str(rows)\n"
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
            "        assert 'ask_db' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: ask_db is defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: returns a string\n"
            "    try:\n"
            "        result = ask_db(conn, 'How many orders are there?')\n"
            "        assert isinstance(result, str), \\\n"
            "            f'expected str, got {type(result).__name__}'\n"
            "        assert len(result) > 0, 'result is empty string'\n"
            "        passed += 1; print(f'\\u2705 Check 2: returns a string ({result[:60]}...)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 3: unsafe SQL is blocked (is_safe_sql used)\n"
            "    try:\n"
            "        # Test that the guardrail works by patching extract_sql\n"
            "        _orig = extract_sql\n"
            "        def _always_drop(resp): return 'DROP TABLE orders'\n"
            "        import builtins; _g = globals()\n"
            "        _g['extract_sql'] = _always_drop\n"
            "        try:\n"
            "            guarded = ask_db(conn, 'drop everything')\n"
            "        finally:\n"
            "            _g['extract_sql'] = _orig\n"
            "        assert 'reject' in guarded.lower() or 'unsafe' in guarded.lower(), \\\n"
            "            f'unsafe SQL should be rejected, got: {guarded}'\n"
            "        passed += 1; print('\\u2705 Check 3: unsafe SQL is rejected')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: handles bad SQL gracefully (returns error string not exception)\n"
            "    try:\n"
            "        _orig = extract_sql\n"
            "        def _bad_select(resp): return 'SELECT nonexistent_col FROM orders'\n"
            "        _g = globals(); _g['extract_sql'] = _bad_select\n"
            "        try:\n"
            "            err = ask_db(conn, 'any question')\n"
            "        finally:\n"
            "            _g['extract_sql'] = _orig\n"
            "        assert isinstance(err, str), 'error path should return string'\n"
            "        passed += 1; print(f'\\u2705 Check 4: bad SQL returns error string ({err[:50]})')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: pipeline produces meaningful result for revenue question\n"
            "    try:\n"
            "        r = ask_db(conn, 'What is the total revenue from all orders?')\n"
            "        assert isinstance(r, str) and len(r) > 0\n"
            "        passed += 1; print(f'\\u2705 Check 5: revenue question answered ({r[:80]})')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\\U0001f389 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n\n"
            "_run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + ASK_DB_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Project notebook
# ---------------------------------------------------------------------------

def project_nb():
    global _cid; _cid = 500
    return [
        md(
            "# Day 043 Project: Chat with a SQL Database\n\n"
            "## What You're Building\n\n"
            "A natural-language query interface for a retail sales database. "
            "The user types a question in English; the system generates SQL, "
            "validates it, runs it, and returns the result.\n\n"
            "**Deliverable:** `ask_db(conn, question)` answers at least 5 "
            "natural-language questions correctly, and `_run_project_checks()` passes.\n\n"
            "## Project Requirements\n\n"
            "1. Set up the database with `setup_db(conn)`\n"
            "2. Call `get_db_schema(conn)` — inspect what the LLM will see\n"
            "3. Ask at least 5 questions with `ask_db`; save results in `answers`\n"
            "4. Verify the guardrail rejects a dangerous SQL string\n"
            "5. Show the schema + one question + SQL + result in a readable format"
        ),
        code(
            "import warnings\nwarnings.filterwarnings('ignore')\n\n\n"
            + ALL_IMPLS
            + "\n\n\nconn = sqlite3.connect(':memory:')\nsetup_db(conn)\nprint('Database ready.')"
        ),
        md("## Step 1 — Inspect the Schema"),
        code(
            "schema = get_db_schema(conn)\n"
            "print(schema)"
        ),
        md("## Step 2 — Ask Natural Language Questions"),
        code(
            "questions = [\n"
            "    'How many orders are there in total?',\n"
            "    'What is the total revenue from all orders?',\n"
            "    'Which product had the highest total revenue?',\n"
            "    'How many orders came from the East region?',\n"
            "    'What is the average revenue per order in the Electronics category?',\n"
            "]\n\n"
            "answers = []\n"
            "for q in questions:\n"
            "    result = ask_db(conn, q)\n"
            "    answers.append({'question': q, 'answer': result})\n"
            "    print(f'Q: {q}')\n"
            "    print(f'A: {result[:120]}')\n"
            "    print()"
        ),
        md("## Step 3 — Show the Full Pipeline for One Question"),
        code(
            "q = 'Which region had the highest total revenue?'\n\n"
            "schema_str = get_db_schema(conn)\n"
            "prompt = build_sql_prompt(q, schema_str)\n"
            "import ollama\n"
            "resp = ollama.chat(model='llama3.2',\n"
            "                   messages=[{'role': 'user', 'content': prompt}])\n"
            "sql_raw = resp['message']['content']\n"
            "sql = extract_sql(sql_raw)\n\n"
            "print('Generated SQL:')\n"
            "print(sql)\n"
            "print()\n"
            "print('Safe?', is_safe_sql(sql))\n"
            "if is_safe_sql(sql):\n"
            "    try:\n"
            "        rows = run_query(conn, sql)\n"
            "        print('Result:', rows)\n"
            "    except Exception as e:\n"
            "        print(f'Query error: {e}')"
        ),
        md("## Project Checks"),
        code(
            "def _run_project_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: schema is non-empty and mentions both tables\n"
            "    try:\n"
            "        s = get_db_schema(conn)\n"
            "        assert isinstance(s, str) and len(s) > 0\n"
            "        assert 'orders' in s.lower() and 'products' in s.lower()\n"
            "        passed += 1; print('\\u2705 Check 1: get_db_schema returns both table names')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "\n"
            "    # Check 2: is_safe_sql correctly allows SELECT\n"
            "    try:\n"
            "        assert is_safe_sql('SELECT * FROM orders') is True\n"
            "        passed += 1; print('\\u2705 Check 2: is_safe_sql allows SELECT')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: is_safe_sql rejects DROP\n"
            "    try:\n"
            "        assert is_safe_sql('DROP TABLE orders') is False\n"
            "        passed += 1; print('\\u2705 Check 3: is_safe_sql rejects DROP')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: answers list has at least 5 entries\n"
            "    try:\n"
            "        assert 'answers' in globals(), 'answers not defined — run Step 2'\n"
            "        assert len(answers) >= 5, \\\n"
            "            f'expected >= 5 answers, got {len(answers)}'\n"
            "        assert all(isinstance(a['answer'], str) for a in answers)\n"
            "        passed += 1; print(f'\\u2705 Check 4: {len(answers)} questions answered')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: ask_db returns a string for a direct count question\n"
            "    try:\n"
            "        r = ask_db(conn, 'How many orders are in the database?')\n"
            "        assert isinstance(r, str) and len(r) > 0\n"
            "        passed += 1; print(f'\\u2705 Check 5: ask_db returns a string ({r[:60]})')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\\U0001f389 Project complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n\n"
            "_run_project_checks()"
        ),
        md(
            "## Bonus Challenges\n\n"
            "- Log the generated SQL alongside the answer so you can audit it\n"
            "- Add a retry loop: if the SQL is unsafe or raises an error, "
            "send the error back to the LLM and ask it to fix the query\n"
            "- Try questions the model struggles with (e.g. 'Show me the running "
            "total of revenue ordered by order_id') and analyse the failure\n"
            "- On Day 44 you will connect to a file-backed SQLite database and "
            "use SQLAlchemy — ask_db will work unchanged on any connection object"
        ),
    ]


# ---------------------------------------------------------------------------
# Solution notebook
# ---------------------------------------------------------------------------

def solution_nb():
    global _cid; _cid = 600
    return [
        md(
            "# Day 043 Solution — Natural Language → SQL\n\n"
            "get_db_schema, build_sql_prompt, extract_sql, is_safe_sql, ask_db. "
            "All data and functions defined inline. Uses in-memory SQLite + Ollama llama3.2."
        ),
        code(
            "import warnings\nwarnings.filterwarnings('ignore')\n\n\n"
            + ALL_IMPLS
        ),
        md("## Step 1 — Create and Populate Database"),
        code(
            "conn = sqlite3.connect(':memory:')\n"
            "setup_db(conn)\n\n"
            "n = conn.execute('SELECT COUNT(*) FROM orders').fetchone()[0]\n"
            "assert n == 12\n"
            "print(f'orders: {n} rows')"
        ),
        md("## Step 2 — get_db_schema"),
        code(
            "schema = get_db_schema(conn)\n"
            "assert isinstance(schema, str) and len(schema) > 0\n"
            "assert 'orders' in schema.lower()\n"
            "assert 'products' in schema.lower()\n"
            "assert 'revenue' in schema.lower()\n"
            "print(schema)"
        ),
        md("## Step 3 — build_sql_prompt"),
        code(
            "q = 'How many orders are there?'\n"
            "prompt = build_sql_prompt(q, schema)\n"
            "assert isinstance(prompt, str)\n"
            "assert q in prompt\n"
            "assert schema in prompt\n"
            "print(f'Prompt length: {len(prompt)} chars')"
        ),
        md("## Step 4 — extract_sql"),
        code(
            "fence = '`' * 3\n"
            "sql_text = 'SELECT COUNT(*) FROM orders'\n"
            "response = fence + 'sql\\n' + sql_text + '\\n' + fence\n"
            "extracted = extract_sql(response)\n"
            "assert extracted == sql_text, f'expected {sql_text!r}, got {extracted!r}'\n"
            "print(f'Extracted: {extracted}')"
        ),
        md("## Step 5 — is_safe_sql"),
        code(
            "assert is_safe_sql('SELECT * FROM orders') is True\n"
            "assert is_safe_sql(\"INSERT INTO orders VALUES (99,'x','y','z',0,0,0)\") is False\n"
            "assert is_safe_sql('DROP TABLE orders') is False\n"
            "assert is_safe_sql('SELECT * FROM orders; DROP TABLE orders') is False\n"
            "print('is_safe_sql: all checks passed')"
        ),
        md("## Step 6 — ask_db (full pipeline, uses Ollama)"),
        code(
            "result = ask_db(conn, 'How many orders are there?')\n"
            "assert isinstance(result, str)\n"
            "assert len(result) > 0\n"
            "print(f'ask_db result: {result}')\n\n"
            "result2 = ask_db(conn, 'What is the total revenue from all orders?')\n"
            "assert isinstance(result2, str)\n"
            "assert len(result2) > 0\n"
            "print(f'ask_db result2: {result2}')\n\n"
            "print('\\nAll solution checks passed.')\n"
            "conn.close()"
        ),
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Generating Day 043 notebooks...")
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
