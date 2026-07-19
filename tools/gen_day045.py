#!/usr/bin/env python3
"""Generate all Day 045 notebooks: exercises 1-5, project, solution."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAY_DIR = ROOT / "03_data_analysis" / "day_045"

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
# Shared CSV source (10 rows: 7 valid, 3 invalid)
# Row 4: empty product  Row 5: amount="twelve"  Row 8: empty amount
# ---------------------------------------------------------------------------

CSV_SOURCE = (
    "date,product,category,amount,region\n"
    "2024-01-15,Laptop,Electronics,999.99,East\n"
    "2024-01-16,Headphones,Electronics,149.99,West\n"
    "2024-01-17,Desk Chair,Furniture,349.00,East\n"
    "2024-01-18,,Furniture,199.00,North\n"
    "2024-01-19,Pen Set,Stationery,twelve,South\n"
    "2024-01-20,Monitor,Electronics,599.99,West\n"
    "2024-01-21,Keyboard,Electronics,79.99,East\n"
    "2024-01-22,Webcam,Electronics,,North\n"
    "2024-01-23,Lamp,Furniture,45.99,South\n"
    "2024-01-24,Notebook,Stationery,8.99,West\n"
)

CSV_SOURCE_REPR = (
    "CSV_SOURCE = (\n"
    "    'date,product,category,amount,region\\n'\n"
    "    '2024-01-15,Laptop,Electronics,999.99,East\\n'\n"
    "    '2024-01-16,Headphones,Electronics,149.99,West\\n'\n"
    "    '2024-01-17,Desk Chair,Furniture,349.00,East\\n'\n"
    "    '2024-01-18,,Furniture,199.00,North\\n'\n"
    "    '2024-01-19,Pen Set,Stationery,twelve,South\\n'\n"
    "    '2024-01-20,Monitor,Electronics,599.99,West\\n'\n"
    "    '2024-01-21,Keyboard,Electronics,79.99,East\\n'\n"
    "    '2024-01-22,Webcam,Electronics,,North\\n'\n"
    "    '2024-01-23,Lamp,Furniture,45.99,South\\n'\n"
    "    '2024-01-24,Notebook,Stationery,8.99,West\\n'\n"
    ")"
)

# ---------------------------------------------------------------------------
# Implementations
# ---------------------------------------------------------------------------

BASE_IMPORTS = """\
import warnings
warnings.filterwarnings('ignore')
import csv
import io
from sqlalchemy import create_engine, String, Float, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
from sqlalchemy.pool import StaticPool"""

MODEL_CODE = """\
class Base(DeclarativeBase):
    pass


class Sale(Base):
    __tablename__ = 'sales'
    id:       Mapped[int]   = mapped_column(primary_key=True)
    date:     Mapped[str]   = mapped_column(String(20))
    product:  Mapped[str]   = mapped_column(String(100))
    category: Mapped[str]   = mapped_column(String(50))
    amount:   Mapped[float] = mapped_column()
    region:   Mapped[str]   = mapped_column(String(50))

    def __repr__(self):
        return f'Sale(id={self.id}, product={self.product!r}, amount={self.amount})'"""

SETUP_ENGINE_IMPL = """\
def setup_engine(url='sqlite:///:memory:'):
    engine = create_engine(
        url,
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine"""

EXTRACT_IMPL = """\
def extract(csv_text: str) -> list:
    reader = csv.DictReader(io.StringIO(csv_text))
    return list(reader)"""

VALIDATE_RECORD_IMPL = """\
def validate_record(record: dict) -> bool:
    required = ['date', 'product', 'amount']
    for field in required:
        if not record.get(field, '').strip():
            return False
    try:
        float(record['amount'])
    except (ValueError, TypeError):
        return False
    return True"""

TRANSFORM_RECORD_IMPL = """\
def transform_record(record: dict) -> dict:
    return {
        'date':     record['date'].strip(),
        'product':  record['product'].strip(),
        'category': record.get('category', '').strip(),
        'amount':   round(float(record['amount']), 2),
        'region':   record.get('region', '').strip().title(),
    }"""

LOAD_IMPL = """\
def load(session, records: list) -> int:
    sales = [Sale(**r) for r in records]
    session.add_all(sales)
    session.commit()
    return len(sales)"""

RUN_PIPELINE_IMPL = """\
def run_pipeline(csv_text: str, session) -> dict:
    raw_records  = extract(csv_text)
    valid        = [r for r in raw_records if validate_record(r)]
    transformed  = [transform_record(r) for r in valid]
    loaded_count = load(session, transformed)
    return {
        'extracted': len(raw_records),
        'loaded':    loaded_count,
        'skipped':   len(raw_records) - loaded_count,
    }"""

ALL_IMPLS = "\n\n\n".join([
    EXTRACT_IMPL,
    VALIDATE_RECORD_IMPL,
    TRANSFORM_RECORD_IMPL,
    LOAD_IMPL,
    RUN_PIPELINE_IMPL,
])


# ---------------------------------------------------------------------------
# Exercise 01 — extract
# ---------------------------------------------------------------------------

def ex01():
    global _cid; _cid = 0
    return [
        md(
            "# Day 045 — Exercise 1: extract\n\n"
            "**What you'll build:** `extract(csv_text: str) -> list[dict]` — "
            "parse a CSV string into a list of dicts using `csv.DictReader` and "
            "`io.StringIO`.\n\n"
            "**Why it matters:** The first step of every ETL pipeline is getting "
            "raw data into a Python-native format. `csv.DictReader` reads each row "
            "as a dict keyed by the CSV header. `io.StringIO` wraps a string as a "
            "file-like object so `DictReader` can read from it without touching the "
            "filesystem. All values remain strings after extraction — type conversion "
            "happens in the Transform step."
        ),
        code(
            BASE_IMPORTS + "\n\n\n"
            + MODEL_CODE + "\n\n\n"
            + SETUP_ENGINE_IMPL + "\n\n\n"
            + CSV_SOURCE_REPR
        ),
        md("## Your Implementation"),
        code(
            "def extract(csv_text: str) -> list:\n"
            '    """\n'
            "    Parse CSV text into a list of dicts.\n\n"
            "    Use csv.DictReader(io.StringIO(csv_text)) to parse the text.\n"
            "    Return list(reader) — each row becomes a dict keyed by column name.\n"
            "    All values are strings at this stage; type conversion happens later.\n"
            '    """\n'
            "    # TODO: reader = csv.DictReader(io.StringIO(csv_text))\n"
            "    # TODO: return list(reader)\n"
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
            "        assert 'extract' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: extract is defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: returns a list\n"
            "    try:\n"
            "        result = extract(CSV_SOURCE)\n"
            "        assert isinstance(result, list), \\\n"
            "            f'expected list, got {type(result).__name__}'\n"
            "        passed += 1; print('\\u2705 Check 2: returns a list')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 3: correct row count (header excluded)\n"
            "    try:\n"
            "        assert len(result) == 10, \\\n"
            "            f'expected 10 rows, got {len(result)}'\n"
            "        passed += 1; print(f'\\u2705 Check 3: 10 rows extracted')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: rows are dicts with correct keys\n"
            "    try:\n"
            "        expected_keys = {'date', 'product', 'category', 'amount', 'region'}\n"
            "        assert all(isinstance(r, dict) for r in result)\n"
            "        assert all(expected_keys <= set(r.keys()) for r in result), \\\n"
            "            f'missing keys in row: {result[0].keys()}'\n"
            "        passed += 1; print(f'\\u2705 Check 4: rows are dicts with correct keys')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: all values are strings (DictReader does NOT convert types)\n"
            "    try:\n"
            "        assert all(isinstance(r['amount'], str) for r in result if r['amount']), \\\n"
            "            'amount values should be strings after extract (no type conversion yet)'\n"
            "        first = result[0]\n"
            "        assert first['product'] == 'Laptop'\n"
            "        assert first['amount'] == '999.99'   # string, not float\n"
            "        passed += 1; print('\\u2705 Check 5: values are strings (as expected from DictReader)')\n"
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
            + EXTRACT_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 02 — validate_record
# ---------------------------------------------------------------------------

def ex02():
    global _cid; _cid = 100
    return [
        md(
            "# Day 045 — Exercise 2: validate_record\n\n"
            "**What you'll build:** `validate_record(record: dict) -> bool` — "
            "check that a raw record has all required fields and that `amount` "
            "is parseable as a float.\n\n"
            "**Why it matters:** Real data is messy. CSV files have missing fields, "
            "typos in numeric columns, and blank rows. `validate_record` is the gate "
            "between raw extracted data and the transform step — only valid records "
            "flow through. It returns `bool` so the caller can count skipped records "
            "without raising exceptions."
        ),
        code(BASE_IMPORTS + "\n\n\n" + MODEL_CODE + "\n\n\n" + SETUP_ENGINE_IMPL),
        md("## Your Implementation"),
        code(
            "def validate_record(record: dict) -> bool:\n"
            '    """\n'
            "    Return True if the record is valid; False otherwise.\n\n"
            "    Required fields (must be present and non-empty after .strip()):\n"
            "      'date', 'product', 'amount'\n\n"
            "    Type check: record['amount'] must be convertible to float.\n"
            "    Use a try/except around float(record['amount']) to catch ValueError.\n"
            '    """\n'
            "    # TODO: required = ['date', 'product', 'amount']\n"
            "    # TODO: for field in required:\n"
            "    # TODO:     if not record.get(field, '').strip():\n"
            "    # TODO:         return False\n"
            "    # TODO: try:\n"
            "    # TODO:     float(record['amount'])\n"
            "    # TODO: except (ValueError, TypeError):\n"
            "    # TODO:     return False\n"
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
            "        assert 'validate_record' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: validate_record is defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    good = {'date': '2024-01-15', 'product': 'Laptop',\n"
            "            'category': 'Electronics', 'amount': '999.99', 'region': 'East'}\n"
            "\n"
            "    # Check 2: valid record returns True\n"
            "    try:\n"
            "        assert validate_record(good) is True, \\\n"
            "            f'expected True for valid record, got {validate_record(good)}'\n"
            "        passed += 1; print('\\u2705 Check 2: valid record → True')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: empty product → False\n"
            "    try:\n"
            "        bad_product = {**good, 'product': ''}\n"
            "        assert validate_record(bad_product) is False, \\\n"
            "            'empty product should return False'\n"
            "        passed += 1; print('\\u2705 Check 3: empty product → False')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: non-numeric amount → False\n"
            "    try:\n"
            "        bad_amount = {**good, 'amount': 'twelve'}\n"
            "        assert validate_record(bad_amount) is False, \\\n"
            "            'non-numeric amount should return False'\n"
            "        passed += 1; print('\\u2705 Check 4: non-numeric amount → False')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: empty amount → False\n"
            "    try:\n"
            "        no_amount = {**good, 'amount': ''}\n"
            "        assert validate_record(no_amount) is False, \\\n"
            "            'empty amount should return False'\n"
            "        passed += 1; print('\\u2705 Check 5: empty amount → False')\n"
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
            + VALIDATE_RECORD_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 03 — transform_record
# ---------------------------------------------------------------------------

def ex03():
    global _cid; _cid = 200
    return [
        md(
            "# Day 045 — Exercise 3: transform_record\n\n"
            "**What you'll build:** `transform_record(record: dict) -> dict` — "
            "clean one valid record: strip whitespace from strings, "
            "coerce `amount` to a rounded float, and title-case `region`.\n\n"
            "**Why it matters:** Raw CSV data is always strings. The transform step "
            "converts values to the types the database expects: `amount` must be a "
            "`float` (not the string `'999.99'`), whitespace must be stripped, and "
            "values should be normalized so that `'east'` and `'East'` don't create "
            "two different groups in a GROUP BY query. `transform_record` is a pure "
            "function: it takes a dict and returns a new dict — never mutates the input."
        ),
        code(BASE_IMPORTS + "\n\n\n" + MODEL_CODE + "\n\n\n" + SETUP_ENGINE_IMPL),
        md("## Your Implementation"),
        code(
            "def transform_record(record: dict) -> dict:\n"
            '    """\n'
            "    Return a new cleaned dict from a validated raw record.\n\n"
            "    Transformations:\n"
            "      date     → record['date'].strip()\n"
            "      product  → record['product'].strip()\n"
            "      category → record.get('category', '').strip()\n"
            "      amount   → round(float(record['amount']), 2)\n"
            "      region   → record.get('region', '').strip().title()\n\n"
            "    Do NOT mutate the input dict — return a fresh dict.\n"
            '    Only call this on records that passed validate_record.\n'
            '    """\n'
            "    # TODO: return {\n"
            "    # TODO:     'date':     record['date'].strip(),\n"
            "    # TODO:     'product':  record['product'].strip(),\n"
            "    # TODO:     'category': record.get('category', '').strip(),\n"
            "    # TODO:     'amount':   round(float(record['amount']), 2),\n"
            "    # TODO:     'region':   record.get('region', '').strip().title(),\n"
            "    # TODO: }\n"
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
            "        assert 'transform_record' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: transform_record is defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    raw = {'date': ' 2024-01-15 ', 'product': ' Laptop ',\n"
            "           'category': ' Electronics ', 'amount': '999.99', 'region': 'east'}\n"
            "\n"
            "    # Check 2: returns a dict\n"
            "    try:\n"
            "        result = transform_record(raw)\n"
            "        assert isinstance(result, dict), \\\n"
            "            f'expected dict, got {type(result).__name__}'\n"
            "        passed += 1; print('\\u2705 Check 2: returns a dict')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 3: amount is float, not string\n"
            "    try:\n"
            "        assert isinstance(result['amount'], float), \\\n"
            "            f'amount should be float, got {type(result[\"amount\"]).__name__}'\n"
            "        assert abs(result['amount'] - 999.99) < 0.001\n"
            "        passed += 1; print(f'\\u2705 Check 3: amount coerced to float ({result[\"amount\"]})')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: strings are stripped\n"
            "    try:\n"
            "        assert result['date'] == '2024-01-15', \\\n"
            "            f'date not stripped: {result[\"date\"]!r}'\n"
            "        assert result['product'] == 'Laptop', \\\n"
            "            f'product not stripped: {result[\"product\"]!r}'\n"
            "        assert result['category'] == 'Electronics', \\\n"
            "            f'category not stripped: {result[\"category\"]!r}'\n"
            "        passed += 1; print('\\u2705 Check 4: strings are stripped')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: region is title-cased\n"
            "    try:\n"
            "        assert result['region'] == 'East', \\\n"
            "            f'region should be title-cased: got {result[\"region\"]!r}'\n"
            "        passed += 1; print(f'\\u2705 Check 5: region title-cased ({result[\"region\"]!r})')\n"
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
            + TRANSFORM_RECORD_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 04 — load
# ---------------------------------------------------------------------------

def ex04():
    global _cid; _cid = 300
    setup = (
        BASE_IMPORTS + "\n\n\n"
        + MODEL_CODE + "\n\n\n"
        + SETUP_ENGINE_IMPL + "\n\n\n"
        + EXTRACT_IMPL + "\n\n\n"
        + VALIDATE_RECORD_IMPL + "\n\n\n"
        + TRANSFORM_RECORD_IMPL + "\n\n\n"
        + CSV_SOURCE_REPR + "\n\n"
        "engine  = setup_engine()\nsession = Session(engine)\n\n"
        "# Pre-transform 3 clean records for use in checks\n"
        "raw     = extract(CSV_SOURCE)\n"
        "ready   = [transform_record(r) for r in raw if validate_record(r)][:3]"
    )
    return [
        md(
            "# Day 045 — Exercise 4: load\n\n"
            "**What you'll build:** `load(session, records: list) -> int` — "
            "bulk-insert a list of clean dicts into the `sales` table "
            "using `session.add_all()` and return the count of rows loaded.\n\n"
            "**Why it matters:** `session.add_all([Sale(**r) for r in records])` "
            "is more efficient than calling `session.add()` in a loop — it stages "
            "all objects in one operation before a single `commit()`. "
            "The function returns `int` (the count loaded) so `run_pipeline` can "
            "calculate how many records were skipped."
        ),
        code(setup),
        md("## Your Implementation"),
        code(
            "def load(session, records: list) -> int:\n"
            '    """\n'
            "    Bulk-insert a list of clean dicts into the sales table.\n\n"
            "    Steps:\n"
            "    1. sales = [Sale(**r) for r in records]  — create ORM objects\n"
            "    2. session.add_all(sales)                — stage all at once\n"
            "    3. session.commit()                      — flush to DB\n"
            "    4. return len(sales)\n"
            '    """\n'
            "    # TODO: sales = [Sale(**r) for r in records]\n"
            "    # TODO: session.add_all(sales)\n"
            "    # TODO: session.commit()\n"
            "    # TODO: return len(sales)\n"
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
            "        assert 'load' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: load is defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: returns an int\n"
            "    try:\n"
            "        count = load(session, ready)\n"
            "        assert isinstance(count, int), \\\n"
            "            f'expected int, got {type(count).__name__}'\n"
            "        passed += 1; print(f'\\u2705 Check 2: returns int ({count})')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 3: returned count matches records passed\n"
            "    try:\n"
            "        assert count == len(ready) == 3, \\\n"
            "            f'expected 3, got {count}'\n"
            "        passed += 1; print(f'\\u2705 Check 3: count == {len(ready)} (records passed)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: rows are in the database\n"
            "    try:\n"
            "        from sqlalchemy import select as sa_select\n"
            "        all_sales = session.execute(sa_select(Sale)).scalars().all()\n"
            "        assert len(all_sales) == 3, \\\n"
            "            f'expected 3 rows in DB, got {len(all_sales)}'\n"
            "        passed += 1; print(f'\\u2705 Check 4: {len(all_sales)} rows in DB')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: amount is stored as float\n"
            "    try:\n"
            "        first = session.execute(sa_select(Sale)).scalars().first()\n"
            "        assert isinstance(first.amount, float), \\\n"
            "            f'amount should be float, got {type(first.amount).__name__}'\n"
            "        passed += 1; print(f'\\u2705 Check 5: amount stored as float ({first.amount})')\n"
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
            + LOAD_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 05 — run_pipeline
# ---------------------------------------------------------------------------

def ex05():
    global _cid; _cid = 400
    setup = (
        BASE_IMPORTS + "\n\n\n"
        + MODEL_CODE + "\n\n\n"
        + SETUP_ENGINE_IMPL + "\n\n\n"
        + EXTRACT_IMPL + "\n\n\n"
        + VALIDATE_RECORD_IMPL + "\n\n\n"
        + TRANSFORM_RECORD_IMPL + "\n\n\n"
        + LOAD_IMPL + "\n\n\n"
        + CSV_SOURCE_REPR + "\n\n"
        "engine  = setup_engine()\nsession = Session(engine)"
    )
    return [
        md(
            "# Day 045 — Exercise 5: run_pipeline\n\n"
            "**What you'll build:** `run_pipeline(csv_text: str, session) -> dict` — "
            "compose the four steps (extract → validate → transform → load) into "
            "a single function that returns a stats dict with keys "
            "`'extracted'`, `'loaded'`, and `'skipped'`.\n\n"
            "**Why it matters:** A pipeline is a composition of pure functions. "
            "Each step has one job: extract returns raw records; validate filters "
            "them; transform cleans them; load persists them. `run_pipeline` "
            "orchestrates the steps and accumulates counts so the caller can "
            "audit what happened without inspecting the database."
        ),
        code(setup),
        md("## Your Implementation"),
        code(
            "def run_pipeline(csv_text: str, session) -> dict:\n"
            '    """\n'
            "    Run the full ETL pipeline: extract → validate → transform → load.\n\n"
            "    Steps:\n"
            "    1. raw_records  = extract(csv_text)\n"
            "    2. valid        = [r for r in raw_records if validate_record(r)]\n"
            "    3. transformed  = [transform_record(r) for r in valid]\n"
            "    4. loaded_count = load(session, transformed)\n"
            "    5. return {'extracted': len(raw_records),\n"
            "               'loaded':    loaded_count,\n"
            "               'skipped':   len(raw_records) - loaded_count}\n"
            '    """\n'
            "    # TODO: raw_records  = extract(csv_text)\n"
            "    # TODO: valid        = [r for r in raw_records if validate_record(r)]\n"
            "    # TODO: transformed  = [transform_record(r) for r in valid]\n"
            "    # TODO: loaded_count = load(session, transformed)\n"
            "    # TODO: return {\n"
            "    # TODO:     'extracted': len(raw_records),\n"
            "    # TODO:     'loaded':    loaded_count,\n"
            "    # TODO:     'skipped':   len(raw_records) - loaded_count,\n"
            "    # TODO: }\n"
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
            "        assert 'run_pipeline' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: run_pipeline is defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: returns a dict with correct keys\n"
            "    try:\n"
            "        stats = run_pipeline(CSV_SOURCE, session)\n"
            "        assert isinstance(stats, dict), \\\n"
            "            f'expected dict, got {type(stats).__name__}'\n"
            "        assert {'extracted', 'loaded', 'skipped'} <= set(stats.keys()), \\\n"
            "            f'missing keys: {set(stats.keys())}'\n"
            "        passed += 1; print(f'\\u2705 Check 2: returns dict {stats}')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 3: extracted == 10 (all CSV rows)\n"
            "    try:\n"
            "        assert stats['extracted'] == 10, \\\n"
            "            f'expected extracted=10, got {stats[\"extracted\"]}'\n"
            "        passed += 1; print(f'\\u2705 Check 3: extracted=10')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: loaded == 7, skipped == 3\n"
            "    try:\n"
            "        assert stats['loaded'] == 7, \\\n"
            "            f'expected loaded=7, got {stats[\"loaded\"]}'\n"
            "        assert stats['skipped'] == 3, \\\n"
            "            f'expected skipped=3, got {stats[\"skipped\"]}'\n"
            "        passed += 1; print(f'\\u2705 Check 4: loaded=7, skipped=3')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: 7 rows in the database\n"
            "    try:\n"
            "        from sqlalchemy import select as sa_select\n"
            "        db_count = len(session.execute(sa_select(Sale)).scalars().all())\n"
            "        assert db_count == 7, \\\n"
            "            f'expected 7 rows in DB, got {db_count}'\n"
            "        passed += 1; print(f'\\u2705 Check 5: {db_count} Sale rows in DB')\n"
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
            + RUN_PIPELINE_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Project notebook
# ---------------------------------------------------------------------------

PROJECT_CSV_REPR = (
    "CSV_SOURCE = (\n"
    "    'date,product,category,amount,region\\n'\n"
    "    '2024-02-01,Laptop Pro,Electronics,1299.99,east\\n'\n"
    "    '2024-02-02,Wireless Mouse,Electronics,39.99,west\\n'\n"
    "    '2024-02-03,Standing Desk,Furniture,549.00,east\\n'\n"
    "    '2024-02-04,Bookshelf,Furniture,229.00,north\\n'\n"
    "    '2024-02-05,Gel Pens 12pk,Stationery,14.99,south\\n'\n"
    "    '2024-02-06,Monitor 27in,Electronics,449.99,west\\n'\n"
    "    '2024-02-07,,Electronics,89.99,east\\n'\n"
    "    '2024-02-08,USB Hub,Electronics,twenty,south\\n'\n"
    "    '2024-02-09,Ergonomic Chair,Furniture,699.00,north\\n'\n"
    "    '2024-02-10,Mechanical Keyboard,Electronics,129.99,east\\n'\n"
    "    '2024-02-11,Sticky Notes,Stationery,6.99,west\\n'\n"
    "    '2024-02-12,Webcam HD,Electronics,199.99,south\\n'\n"
    "    '2024-02-13,Desk Lamp,Furniture,59.99,north\\n'\n"
    "    '2024-02-14,Stapler,Stationery,,\\n'\n"
    "    '2024-02-15,Notebook Set,Stationery,22.99,west\\n'\n"
    ")"
)


def project_nb():
    global _cid; _cid = 500
    proj_setup = (
        BASE_IMPORTS + "\n\n\n"
        + MODEL_CODE + "\n\n\n"
        + SETUP_ENGINE_IMPL + "\n\n\n"
        + ALL_IMPLS + "\n\n\n"
        + PROJECT_CSV_REPR + "\n\n"
        "engine  = setup_engine()\n"
        "session = Session(engine)\n"
        "print('ETL pipeline ready.')"
    )
    return [
        md(
            "# Day 045 Project: Sales ETL Pipeline\n\n"
            "## What You're Building\n\n"
            "A complete ETL pipeline that:\n"
            "1. Extracts raw sales data from a CSV string\n"
            "2. Validates and filters out bad records\n"
            "3. Transforms (cleans/normalizes) valid records\n"
            "4. Loads them into a SQLAlchemy-backed database\n"
            "5. Queries the database to produce a category and region summary\n\n"
            "**Deliverable:** `run_pipeline` succeeds, `stats` shows correct counts, "
            "and `_run_project_checks()` passes all 5 checks.\n\n"
            "## Project Requirements\n\n"
            "1. Run `run_pipeline(CSV_SOURCE, session)` and store the result in `stats`\n"
            "2. Print the pipeline stats\n"
            "3. Query `Sale` rows by category using `select(Sale).where(...)`\n"
            "4. Produce a category summary using `session.execute(text(sql))`\n"
            "5. Produce a region summary"
        ),
        code(proj_setup),
        md("## Step 1 — Run the Pipeline"),
        code(
            "stats = run_pipeline(CSV_SOURCE, session)\n"
            "print(f'Extracted: {stats[\"extracted\"]}')\n"
            "print(f'Loaded:    {stats[\"loaded\"]}')\n"
            "print(f'Skipped:   {stats[\"skipped\"]}')"
        ),
        md("## Step 2 — Browse by Category"),
        code(
            "# Query a specific category using ORM select\n"
            "# electronics = session.execute(\n"
            "#     select(Sale).where(Sale.category == 'Electronics')\n"
            "# ).scalars().all()\n"
            "# print(f'Electronics ({len(electronics)} items):')\n"
            "# for s in electronics:\n"
            "#     print(f'  {s}')"
        ),
        md("## Step 3 — Category Summary (SQL)"),
        code(
            "# Use session.execute(text(sql)) to get a GROUP BY summary\n"
            "# sql = (\n"
            "#     'SELECT category, COUNT(*) as count, '\n"
            "#     'ROUND(SUM(amount), 2) as total '\n"
            "#     'FROM sales GROUP BY category ORDER BY total DESC'\n"
            "# )\n"
            "# rows = session.execute(text(sql)).mappings().all()\n"
            "# print('Category summary:')\n"
            "# for row in rows:\n"
            "#     print(f'  {row[\"category\"]}: {row[\"count\"]} sales, ${row[\"total\"]:.2f}')"
        ),
        md("## Step 4 — Region Summary"),
        code(
            "# TODO: produce a region summary similar to Step 3\n"
            "# SELECT region, COUNT(*) as count, ROUND(SUM(amount), 2) as total\n"
            "# FROM sales GROUP BY region ORDER BY total DESC"
        ),
        md("## Project Checks"),
        code(
            "def _run_project_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: stats dict exists with correct keys\n"
            "    try:\n"
            "        assert 'stats' in globals()\n"
            "        assert {'extracted', 'loaded', 'skipped'} <= set(stats.keys())\n"
            "        passed += 1; print(f'\\u2705 Check 1: stats = {stats}')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "\n"
            "    # Check 2: extracted == 15 (total CSV rows)\n"
            "    try:\n"
            "        assert stats['extracted'] == 15, \\\n"
            "            f'expected 15 extracted, got {stats[\"extracted\"]}'\n"
            "        passed += 1; print('\\u2705 Check 2: extracted=15')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: 3 invalid rows skipped, 12 loaded\n"
            "    try:\n"
            "        assert stats['skipped'] == 3, \\\n"
            "            f'expected skipped=3, got {stats[\"skipped\"]}'\n"
            "        assert stats['loaded'] == 12, \\\n"
            "            f'expected loaded=12, got {stats[\"loaded\"]}'\n"
            "        passed += 1; print('\\u2705 Check 3: skipped=3, loaded=12')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: 12 Sale rows in DB\n"
            "    try:\n"
            "        db_count = len(session.execute(select(Sale)).scalars().all())\n"
            "        assert db_count == 12, \\\n"
            "            f'expected 12 rows in DB, got {db_count}'\n"
            "        passed += 1; print(f'\\u2705 Check 4: {db_count} Sale rows in DB')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: region values are title-cased (not lowercase)\n"
            "    try:\n"
            "        regions = [\n"
            "            s.region for s in\n"
            "            session.execute(select(Sale)).scalars().all()\n"
            "        ]\n"
            "        assert all(r == r.title() for r in regions if r), \\\n"
            "            f'some regions not title-cased: {[r for r in regions if r != r.title()]}'\n"
            "        passed += 1; print(f'\\u2705 Check 5: all regions title-cased ({set(regions)})')\n"
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
            "- Add a `deduplicate(records)` step that drops records with the same "
            "`(date, product)` pair before loading\n"
            "- Make the pipeline idempotent: add `INSERT OR IGNORE` logic so that "
            "running the pipeline twice doesn't double-load records\n"
            "- Add a `report(session)` function that uses `pd.read_sql_query` "
            "with `engine.connect()` to return a DataFrame summary\n"
            "- On Day 46 you will apply time-series analysis to the `date` column "
            "— the ETL pipeline you built today is the data source"
        ),
    ]


# ---------------------------------------------------------------------------
# Solution notebook
# ---------------------------------------------------------------------------

def solution_nb():
    global _cid; _cid = 600
    sol_csv = (
        "CSV_SOURCE = (\n"
        "    'date,product,category,amount,region\\n'\n"
        "    '2024-01-15,Laptop,Electronics,999.99,East\\n'\n"
        "    '2024-01-16,Headphones,Electronics,149.99,West\\n'\n"
        "    '2024-01-17,Desk Chair,Furniture,349.00,East\\n'\n"
        "    '2024-01-18,,Furniture,199.00,North\\n'\n"
        "    '2024-01-19,Pen Set,Stationery,twelve,South\\n'\n"
        "    '2024-01-20,Monitor,Electronics,599.99,West\\n'\n"
        "    '2024-01-21,Keyboard,Electronics,79.99,East\\n'\n"
        "    '2024-01-22,Webcam,Electronics,,North\\n'\n"
        "    '2024-01-23,Lamp,Furniture,45.99,South\\n'\n"
        "    '2024-01-24,Notebook,Stationery,8.99,West\\n'\n"
        ")"
    )
    return [
        md(
            "# Day 045 Solution — Data Pipelines\n\n"
            "extract, validate_record, transform_record, load, run_pipeline. "
            "Self-contained: CSV_SOURCE defined inline, in-memory SQLite via SQLAlchemy."
        ),
        code(
            BASE_IMPORTS + "\n\n\n"
            + MODEL_CODE + "\n\n\n"
            + SETUP_ENGINE_IMPL + "\n\n\n"
            + ALL_IMPLS + "\n\n\n"
            + sol_csv
        ),
        md("## Step 1 — Engine"),
        code(
            "engine  = setup_engine()\n"
            "session = Session(engine)\n"
            "from sqlalchemy import inspect as sa_inspect\n"
            "assert 'sales' in sa_inspect(engine).get_table_names()\n"
            "print('Engine ready, sales table created.')"
        ),
        md("## Step 2 — extract"),
        code(
            "records = extract(CSV_SOURCE)\n"
            "assert len(records) == 10\n"
            "assert all(isinstance(r, dict) for r in records)\n"
            "assert records[0]['amount'] == '999.99'   # string, not float\n"
            "print(f'Extracted {len(records)} records')"
        ),
        md("## Step 3 — validate_record"),
        code(
            "valid_r = {'date':'2024-01-15','product':'Laptop','category':'Electronics','amount':'999.99','region':'East'}\n"
            "assert validate_record(valid_r) is True\n"
            "assert validate_record({**valid_r, 'product': ''}) is False\n"
            "assert validate_record({**valid_r, 'amount': 'twelve'}) is False\n"
            "assert validate_record({**valid_r, 'amount': ''}) is False\n"
            "valid_count = sum(1 for r in records if validate_record(r))\n"
            "assert valid_count == 7, f'expected 7 valid, got {valid_count}'\n"
            "print(f'Valid: {valid_count} / {len(records)}')"
        ),
        md("## Step 4 — transform_record"),
        code(
            "raw_with_spaces = {'date': ' 2024-01-15 ', 'product': ' Laptop ',\n"
            "                   'category': 'Electronics', 'amount': '999.99', 'region': 'east'}\n"
            "t = transform_record(raw_with_spaces)\n"
            "assert isinstance(t['amount'], float)\n"
            "assert t['product'] == 'Laptop'\n"
            "assert t['region'] == 'East'\n"
            "print(f'Transformed: {t}')"
        ),
        md("## Step 5 — load"),
        code(
            "valid_records   = [r for r in records if validate_record(r)]\n"
            "transformed     = [transform_record(r) for r in valid_records]\n"
            "loaded_count    = load(session, transformed)\n"
            "assert loaded_count == 7\n"
            "db_count = len(session.execute(select(Sale)).scalars().all())\n"
            "assert db_count == 7\n"
            "print(f'Loaded {loaded_count} rows into DB')"
        ),
        md("## Step 6 — run_pipeline (fresh session)"),
        code(
            "engine2  = setup_engine()\n"
            "session2 = Session(engine2)\n"
            "stats = run_pipeline(CSV_SOURCE, session2)\n"
            "assert stats['extracted'] == 10\n"
            "assert stats['loaded']    == 7\n"
            "assert stats['skipped']   == 3\n"
            "print(f'Pipeline stats: {stats}')\n\n"
            "# Region check — all title-cased\n"
            "regions = [s.region for s in session2.execute(select(Sale)).scalars().all()]\n"
            "assert all(r == r.title() for r in regions if r)\n"
            "print(f'Regions: {sorted(set(regions))}')\n\n"
            "# Category summary\n"
            "rows = session2.execute(\n"
            "    text('SELECT category, COUNT(*) as c, ROUND(SUM(amount),2) as t '\n"
            "         'FROM sales GROUP BY category ORDER BY t DESC')\n"
            ").mappings().all()\n"
            "for row in rows:\n"
            "    print(f'  {row[\"category\"]}: {row[\"c\"]} sales, ${row[\"t\"]:.2f}')\n\n"
            "session2.close()\n"
            "print('\\nAll solution checks passed.')"
        ),
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Generating Day 045 notebooks...")
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
