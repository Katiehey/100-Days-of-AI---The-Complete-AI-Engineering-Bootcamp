#!/usr/bin/env python3
"""Generate all Day 036 notebooks: exercises 1-5, project, solution."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAY_DIR = ROOT / "03_data_analysis" / "day_036"

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

SUMMARIZE_DATAFRAME_IMPL = """\
import warnings
warnings.filterwarnings('ignore')
import pandas as pd

def summarize_dataframe(df: pd.DataFrame) -> dict:
    numeric_cols = df.select_dtypes(include='number').columns.tolist()
    null_count   = int(df.isnull().sum().sum())
    return {
        'rows':         df.shape[0],
        'cols':         df.shape[1],
        'columns':      df.columns.tolist(),
        'numeric_cols': numeric_cols,
        'null_count':   null_count,
    }"""

LOAD_CSV_IMPL = """\
import io
import pandas as pd

def load_csv(csv_text: str) -> pd.DataFrame:
    return pd.read_csv(io.StringIO(csv_text))"""

FILTER_BY_THRESHOLD_IMPL = """\
import pandas as pd

def filter_by_threshold(df: pd.DataFrame, column: str, threshold: float) -> pd.DataFrame:
    mask = df[column] >= threshold
    return df[mask].reset_index(drop=True)"""

ADD_CATEGORY_COLUMN_IMPL = """\
import pandas as pd

def add_category_column(df: pd.DataFrame, price_col: str) -> pd.DataFrame:
    def categorize(price):
        if price < 20:
            return 'budget'
        elif price < 100:
            return 'standard'
        else:
            return 'premium'
    result = df.copy()
    result['category'] = result[price_col].apply(categorize)
    return result"""

GROUP_SUMMARY_IMPL = """\
import pandas as pd

def group_summary(df: pd.DataFrame, group_col: str, value_col: str) -> pd.DataFrame:
    summary = (
        df.groupby(group_col)[value_col]
        .agg(total='sum', count='count')
        .reset_index()
        .sort_values('total', ascending=False)
        .reset_index(drop=True)
    )
    return summary"""

ALL_IMPLS = "\n\n\n".join([
    SUMMARIZE_DATAFRAME_IMPL,
    LOAD_CSV_IMPL,
    FILTER_BY_THRESHOLD_IMPL,
    ADD_CATEGORY_COLUMN_IMPL,
])


# ---------------------------------------------------------------------------
# Exercise 01 — summarize_dataframe
# ---------------------------------------------------------------------------

def ex01():
    global _cid; _cid = 0
    return [
        md(
            "# Day 036 — Exercise 1: summarize_dataframe\n\n"
            "**What you'll build:** `summarize_dataframe(df) -> dict` — inspect a DataFrame "
            "and return key facts: row count, column count, column names, numeric column names, "
            "and total null count.\n\n"
            "**Why it matters:** The first thing you do with any new dataset is get oriented. "
            "This function captures the most useful signals from `.shape`, `.dtypes`, and "
            "`.isnull()` in one structured dict you can log, test, or display."
        ),
        code(
            "import warnings\n"
            "warnings.filterwarnings('ignore')\n"
            "import pandas as pd\n"
            "\n"
            "# Sample DataFrames for checks\n"
            "SIMPLE_DF = pd.DataFrame({\n"
            "    'name':  ['Alice', 'Bob', 'Carol'],\n"
            "    'age':   [25, 30, 35],\n"
            "    'score': [90.5, 85.0, 92.3],\n"
            "})\n"
            "\n"
            "NULLS_DF = pd.DataFrame({\n"
            "    'x': [1, None, 3],\n"
            "    'y': ['a', 'b', None],\n"
            "})"
        ),
        md("## Your Implementation"),
        code(
            "def summarize_dataframe(df: pd.DataFrame) -> dict:\n"
            '    """\n'
            "    Summarise a DataFrame's structure.\n\n"
            "    Returns:\n"
            "        dict with keys:\n"
            "          'rows'         — int, number of rows\n"
            "          'cols'         — int, number of columns\n"
            "          'columns'      — list[str], all column names\n"
            "          'numeric_cols' — list[str], numeric column names\n"
            "          'null_count'   — int, total null/NaN cells\n"
            '    """\n'
            "    # TODO: numeric_cols = df.select_dtypes(include='number').columns.tolist()\n"
            "    # TODO: null_count   = int(df.isnull().sum().sum())\n"
            "    # TODO: return {\n"
            "    #     'rows': df.shape[0], 'cols': df.shape[1],\n"
            "    #     'columns': df.columns.tolist(),\n"
            "    #     'numeric_cols': numeric_cols, 'null_count': null_count,\n"
            "    # }\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: defined, returns dict with all keys\n"
            "    try:\n"
            "        assert 'summarize_dataframe' in globals()\n"
            "        result = summarize_dataframe(SIMPLE_DF)\n"
            "        assert isinstance(result, dict), f'expected dict, got {type(result).__name__}'\n"
            "        for k in ('rows', 'cols', 'columns', 'numeric_cols', 'null_count'):\n"
            "            assert k in result, f'missing key: {k}'\n"
            "        passed += 1; print('\\u2705 Check 1: returns dict with all 5 keys')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: correct row and col counts\n"
            "    try:\n"
            "        r = summarize_dataframe(SIMPLE_DF)\n"
            "        assert r['rows'] == 3, f\"rows={r['rows']}, expected 3\"\n"
            "        assert r['cols'] == 3, f\"cols={r['cols']}, expected 3\"\n"
            "        passed += 1; print('\\u2705 Check 2: rows=3, cols=3')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: correct column names list\n"
            "    try:\n"
            "        r = summarize_dataframe(SIMPLE_DF)\n"
            "        assert r['columns'] == ['name', 'age', 'score'], \\\n"
            "            f\"columns={r['columns']}\"\n"
            "        passed += 1; print(\"\\u2705 Check 3: columns=['name', 'age', 'score']\")\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: correct numeric_cols\n"
            "    try:\n"
            "        r = summarize_dataframe(SIMPLE_DF)\n"
            "        assert set(r['numeric_cols']) == {'age', 'score'}, \\\n"
            "            f\"numeric_cols={r['numeric_cols']}, expected ['age', 'score']\"\n"
            "        passed += 1; print(\"\\u2705 Check 4: numeric_cols=['age', 'score']\")\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: null_count correct on NULLS_DF\n"
            "    try:\n"
            "        r = summarize_dataframe(NULLS_DF)\n"
            "        assert r['null_count'] == 2, \\\n"
            "            f\"null_count={r['null_count']}, expected 2\"\n"
            "        passed += 1; print('\\u2705 Check 5: null_count=2 on NULLS_DF')\n"
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
            + SUMMARIZE_DATAFRAME_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 02 — load_csv
# ---------------------------------------------------------------------------

def ex02():
    global _cid; _cid = 100
    SAMPLE_CSV = (
        "product,price,quantity\n"
        "apple,1.5,100\n"
        "banana,0.75,200\n"
        "cherry,3.0,50\n"
        "date,5.0,30"
    )
    return [
        md(
            "# Day 036 — Exercise 2: load_csv\n\n"
            "**What you'll build:** `load_csv(csv_text: str) -> pd.DataFrame` — parse a raw CSV "
            "string into a DataFrame using `io.StringIO` as an in-memory file buffer.\n\n"
            "**Why it matters:** Real data arrives as files, API responses, and string blobs. "
            "`io.StringIO` lets `pd.read_csv` consume a string without touching the filesystem — "
            "essential for tests, pipelines, and reproducible notebooks."
        ),
        code(
            "import warnings\n"
            "warnings.filterwarnings('ignore')\n"
            "import io\n"
            "import pandas as pd\n"
            "\n"
            "SAMPLE_CSV = '''" + SAMPLE_CSV + "'''"
        ),
        md("## Your Implementation"),
        code(
            "def load_csv(csv_text: str) -> pd.DataFrame:\n"
            '    """\n'
            "    Parse a CSV string into a DataFrame.\n\n"
            "    Args:\n"
            "        csv_text: raw CSV content as a string (with header row)\n"
            "    Returns:\n"
            "        pd.DataFrame with column names taken from the first row\n"
            '    """\n'
            "    # TODO: return pd.read_csv(io.StringIO(csv_text))\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: defined, returns a DataFrame\n"
            "    try:\n"
            "        assert 'load_csv' in globals()\n"
            "        result = load_csv(SAMPLE_CSV)\n"
            "        assert isinstance(result, pd.DataFrame), \\\n"
            "            f'expected DataFrame, got {type(result).__name__}'\n"
            "        passed += 1; print('\\u2705 Check 1: load_csv returns a DataFrame')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: correct shape\n"
            "    try:\n"
            "        df = load_csv(SAMPLE_CSV)\n"
            "        assert df.shape == (4, 3), f'shape={df.shape}, expected (4, 3)'\n"
            "        passed += 1; print('\\u2705 Check 2: shape=(4, 3)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: correct column names\n"
            "    try:\n"
            "        df = load_csv(SAMPLE_CSV)\n"
            "        assert list(df.columns) == ['product', 'price', 'quantity'], \\\n"
            "            f'columns={list(df.columns)}'\n"
            "        passed += 1; print(\"\\u2705 Check 3: columns=['product', 'price', 'quantity']\")\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: first row values are correct\n"
            "    try:\n"
            "        df = load_csv(SAMPLE_CSV)\n"
            "        assert df.iloc[0]['product'] == 'apple', \\\n"
            "            f\"first product={df.iloc[0]['product']!r}, expected 'apple'\"\n"
            "        assert df.iloc[0]['price'] == 1.5, \\\n"
            "            f\"first price={df.iloc[0]['price']}, expected 1.5\"\n"
            "        passed += 1; print(\"\\u2705 Check 4: first row is apple, price=1.5\")\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: price and quantity are numeric\n"
            "    try:\n"
            "        df = load_csv(SAMPLE_CSV)\n"
            "        assert pd.api.types.is_numeric_dtype(df['price']), \\\n"
            "            f\"price dtype={df['price'].dtype}, expected numeric\"\n"
            "        assert pd.api.types.is_numeric_dtype(df['quantity']), \\\n"
            "            f\"quantity dtype={df['quantity'].dtype}, expected numeric\"\n"
            "        passed += 1; print('\\u2705 Check 5: price and quantity are numeric dtypes')\n"
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
            + LOAD_CSV_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 03 — filter_by_threshold
# ---------------------------------------------------------------------------

def ex03():
    global _cid; _cid = 200
    return [
        md(
            "# Day 036 — Exercise 3: filter_by_threshold\n\n"
            "**What you'll build:** `filter_by_threshold(df, column, threshold) -> pd.DataFrame` — "
            "return only rows where `df[column] >= threshold`, with the index reset to start from 0.\n\n"
            "**Why it matters:** Boolean filtering is the most common DataFrame operation. "
            "The pattern `df[mask]` with `.reset_index(drop=True)` gives you a clean sub-table "
            "you can pass to the next pipeline stage."
        ),
        code(
            "import warnings\n"
            "warnings.filterwarnings('ignore')\n"
            "import io\n"
            "import pandas as pd\n"
            "\n"
            + LOAD_CSV_IMPL + "\n\n\n"
            "SALES_CSV = (\n"
            "    'product,price,qty\\n'\n"
            "    'apple,1.5,100\\n'\n"
            "    'banana,0.75,200\\n'\n"
            "    'cherry,3.0,50\\n'\n"
            "    'orange,2.0,75\\n'\n"
            "    'grape,4.5,40'\n"
            ")\n"
            "SALES_DF = load_csv(SALES_CSV)"
        ),
        md("## Your Implementation"),
        code(
            "def filter_by_threshold(df: pd.DataFrame, column: str,\n"
            "                        threshold: float) -> pd.DataFrame:\n"
            '    """\n'
            "    Return rows where df[column] >= threshold.\n\n"
            "    Args:\n"
            "        df        — source DataFrame\n"
            "        column    — column name to filter on\n"
            "        threshold — minimum value (inclusive)\n"
            "    Returns:\n"
            "        Filtered DataFrame with index reset to 0, 1, 2, ...\n"
            '    """\n'
            "    # TODO: mask = df[column] >= threshold\n"
            "    # TODO: return df[mask].reset_index(drop=True)\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: defined, returns DataFrame\n"
            "    try:\n"
            "        assert 'filter_by_threshold' in globals()\n"
            "        result = filter_by_threshold(SALES_DF, 'price', 2.0)\n"
            "        assert isinstance(result, pd.DataFrame), \\\n"
            "            f'expected DataFrame, got {type(result).__name__}'\n"
            "        passed += 1; print('\\u2705 Check 1: returns a DataFrame')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: correct row count (price >= 2.0: cherry 3.0, orange 2.0, grape 4.5)\n"
            "    try:\n"
            "        result = filter_by_threshold(SALES_DF, 'price', 2.0)\n"
            "        assert len(result) == 3, f'expected 3 rows, got {len(result)}'\n"
            "        passed += 1; print('\\u2705 Check 2: price >= 2.0 gives 3 rows')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: all returned rows satisfy the filter\n"
            "    try:\n"
            "        result = filter_by_threshold(SALES_DF, 'price', 2.0)\n"
            "        assert (result['price'] >= 2.0).all(), \\\n"
            "            f'some rows have price < 2.0: {result[\"price\"].tolist()}'\n"
            "        passed += 1; print('\\u2705 Check 3: all returned prices >= 2.0')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: index is reset (starts at 0)\n"
            "    try:\n"
            "        result = filter_by_threshold(SALES_DF, 'price', 2.0)\n"
            "        assert list(result.index) == list(range(len(result))), \\\n"
            "            f'index not reset: {list(result.index)}'\n"
            "        passed += 1; print('\\u2705 Check 4: index is reset to 0, 1, 2, ...')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: threshold=0 keeps all rows; threshold=999 keeps none\n"
            "    try:\n"
            "        all_rows  = filter_by_threshold(SALES_DF, 'price', 0)\n"
            "        no_rows   = filter_by_threshold(SALES_DF, 'price', 999)\n"
            "        assert len(all_rows) == len(SALES_DF), \\\n"
            "            f'threshold=0 should keep all {len(SALES_DF)} rows, got {len(all_rows)}'\n"
            "        assert len(no_rows)  == 0, \\\n"
            "            f'threshold=999 should keep 0 rows, got {len(no_rows)}'\n"
            "        passed += 1; print('\\u2705 Check 5: edge cases — threshold 0 keeps all, 999 keeps none')\n"
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
            + FILTER_BY_THRESHOLD_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 04 — add_category_column
# ---------------------------------------------------------------------------

def ex04():
    global _cid; _cid = 300
    return [
        md(
            "# Day 036 — Exercise 4: add_category_column\n\n"
            "**What you'll build:** `add_category_column(df, price_col) -> pd.DataFrame` — "
            "add a `'category'` column by applying a price bucketing rule to an existing price "
            "column: `'budget'` (< 20), `'standard'` (20–99), `'premium'` (>= 100).\n\n"
            "**Why it matters:** `.apply()` with a lambda or helper function is the pandas "
            "pattern for row-level transforms. Using `df.copy()` protects the original from "
            "mutation — a critical habit in multi-stage pipelines."
        ),
        code(
            "import warnings\n"
            "warnings.filterwarnings('ignore')\n"
            "import io\n"
            "import pandas as pd\n"
            "\n"
            + LOAD_CSV_IMPL + "\n\n\n"
            "PRICE_CSV = (\n"
            "    'item,price\\n'\n"
            "    'pen,5\\n'\n"
            "    'notebook,35\\n'\n"
            "    'laptop,999\\n'\n"
            "    'cup,12\\n'\n"
            "    'phone,599\\n'\n"
            "    'stapler,18\\n'\n"
            "    'monitor,250'\n"
            ")\n"
            "PRICE_DF = load_csv(PRICE_CSV)"
        ),
        md("## Your Implementation"),
        code(
            "def add_category_column(df: pd.DataFrame, price_col: str) -> pd.DataFrame:\n"
            '    """\n'
            "    Add a \'category\' column based on price thresholds.\n\n"
            "    Buckets:\n"
            "        price < 20   -> \'budget\'\n"
            "        price < 100  -> \'standard\'\n"
            "        price >= 100 -> \'premium\'\n\n"
            "    Args:\n"
            "        df        — source DataFrame (not mutated)\n"
            "        price_col — name of the price column\n"
            "    Returns:\n"
            "        New DataFrame with an added \'category\' column\n"
            '    """\n'
            "    def categorize(price):\n"
            "        # TODO: return 'budget' / 'standard' / 'premium'\n"
            "        pass\n"
            "\n"
            "    # TODO: result = df.copy()\n"
            "    # TODO: result['category'] = result[price_col].apply(categorize)\n"
            "    # TODO: return result\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: defined, returns DataFrame with 'category' column\n"
            "    try:\n"
            "        assert 'add_category_column' in globals()\n"
            "        result = add_category_column(PRICE_DF, 'price')\n"
            "        assert isinstance(result, pd.DataFrame), \\\n"
            "            f'expected DataFrame, got {type(result).__name__}'\n"
            "        assert 'category' in result.columns, \\\n"
            "            f\"'category' column missing; columns={list(result.columns)}\"\n"
            "        passed += 1; print(\"\\u2705 Check 1: returns DataFrame with 'category' column\")\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: correct bucket assignments\n"
            "    try:\n"
            "        result = add_category_column(PRICE_DF, 'price')\n"
            "        cats = dict(zip(result['item'], result['category']))\n"
            "        assert cats['pen']     == 'budget',   f\"pen -> {cats['pen']!r}\"\n"
            "        assert cats['notebook']== 'standard', f\"notebook -> {cats['notebook']!r}\"\n"
            "        assert cats['laptop']  == 'premium',  f\"laptop -> {cats['laptop']!r}\"\n"
            "        passed += 1; print(\"\\u2705 Check 2: pen=budget, notebook=standard, laptop=premium\")\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: boundary values (price=20 -> standard, price=100 -> premium)\n"
            "    try:\n"
            "        boundary_df = pd.DataFrame({'item': ['a', 'b', 'c'], 'price': [19, 20, 100]})\n"
            "        res = add_category_column(boundary_df, 'price')\n"
            "        cats = dict(zip(res['item'], res['category']))\n"
            "        assert cats['a'] == 'budget',   f\"price=19 -> {cats['a']!r}\"\n"
            "        assert cats['b'] == 'standard', f\"price=20 -> {cats['b']!r}\"\n"
            "        assert cats['c'] == 'premium',  f\"price=100 -> {cats['c']!r}\"\n"
            "        passed += 1; print(\"\\u2705 Check 3: boundaries (19=budget, 20=standard, 100=premium)\")\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: original DataFrame is NOT mutated\n"
            "    try:\n"
            "        orig_cols = list(PRICE_DF.columns)\n"
            "        _ = add_category_column(PRICE_DF, 'price')\n"
            "        assert list(PRICE_DF.columns) == orig_cols, \\\n"
            "            f'original df was mutated: columns={list(PRICE_DF.columns)}'\n"
            "        assert 'category' not in PRICE_DF.columns, \\\n"
            "            'original df has category column — use df.copy()!'\n"
            "        passed += 1; print('\\u2705 Check 4: original DataFrame is not mutated')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: no NaN values in category column\n"
            "    try:\n"
            "        result = add_category_column(PRICE_DF, 'price')\n"
            "        null_cats = result['category'].isnull().sum()\n"
            "        assert null_cats == 0, f'{null_cats} NaN values in category column'\n"
            "        valid = {'budget', 'standard', 'premium'}\n"
            "        bad   = set(result['category'].unique()) - valid\n"
            "        assert not bad, f'unexpected category values: {bad}'\n"
            "        passed += 1; print('\\u2705 Check 5: no NaN, all categories are budget/standard/premium')\n"
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
            + ADD_CATEGORY_COLUMN_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 05 — group_summary
# ---------------------------------------------------------------------------

def ex05():
    global _cid; _cid = 400
    return [
        md(
            "# Day 036 — Exercise 5: group_summary\n\n"
            "**What you'll build:** `group_summary(df, group_col, value_col) -> pd.DataFrame` — "
            "group rows by `group_col`, aggregate `value_col` to produce `total` (sum) and "
            "`count`, sort by `total` descending.\n\n"
            "**Why it matters:** GroupBy is the workhorse of data analysis. "
            "The split-apply-combine pattern — `groupby().agg().reset_index().sort_values()` — "
            "appears in almost every EDA pipeline you will ever write."
        ),
        code(
            "import warnings\n"
            "warnings.filterwarnings('ignore')\n"
            "import io\n"
            "import pandas as pd\n"
            "\n"
            + LOAD_CSV_IMPL + "\n\n\n"
            "ORDERS_CSV = (\n"
            "    'region,product,sales\\n'\n"
            "    'North,Widget,100\\n'\n"
            "    'South,Widget,150\\n'\n"
            "    'North,Gadget,200\\n'\n"
            "    'South,Gadget,50\\n'\n"
            "    'North,Widget,75\\n'\n"
            "    'East,Gadget,300\\n'\n"
            "    'East,Widget,60'\n"
            ")\n"
            "ORDERS_DF = load_csv(ORDERS_CSV)"
        ),
        md("## Your Implementation"),
        code(
            "def group_summary(df: pd.DataFrame, group_col: str,\n"
            "                  value_col: str) -> pd.DataFrame:\n"
            '    """\n'
            "    Aggregate value_col by group_col.\n\n"
            "    Returns a DataFrame with columns:\n"
            "        group_col  — unique group values\n"
            "        'total'    — sum of value_col per group\n"
            "        'count'    — number of rows per group\n"
            "    Sorted by 'total' descending, index reset to 0, 1, 2, ...\n"
            '    """\n'
            "    # TODO: summary = (\n"
            "    #     df.groupby(group_col)[value_col]\n"
            "    #     .agg(total='sum', count='count')\n"
            "    #     .reset_index()\n"
            "    #     .sort_values('total', ascending=False)\n"
            "    #     .reset_index(drop=True)\n"
            "    # )\n"
            "    # TODO: return summary\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: defined, returns DataFrame\n"
            "    try:\n"
            "        assert 'group_summary' in globals()\n"
            "        result = group_summary(ORDERS_DF, 'product', 'sales')\n"
            "        assert isinstance(result, pd.DataFrame), \\\n"
            "            f'expected DataFrame, got {type(result).__name__}'\n"
            "        passed += 1; print('\\u2705 Check 1: returns a DataFrame')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: correct shape — 2 products, 3 columns\n"
            "    try:\n"
            "        result = group_summary(ORDERS_DF, 'product', 'sales')\n"
            "        assert result.shape == (2, 3), \\\n"
            "            f'shape={result.shape}, expected (2, 3)'\n"
            "        passed += 1; print('\\u2705 Check 2: shape=(2, 3)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: columns include 'total' and 'count'\n"
            "    try:\n"
            "        result = group_summary(ORDERS_DF, 'product', 'sales')\n"
            "        assert 'total' in result.columns, f\"missing 'total' column\"\n"
            "        assert 'count' in result.columns, f\"missing 'count' column\"\n"
            "        passed += 1; print(\"\\u2705 Check 3: columns include 'total' and 'count'\")\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: correct totals\n"
            "    # Widget: 100+150+75+60=385; Gadget: 200+50+300=550\n"
            "    try:\n"
            "        result = group_summary(ORDERS_DF, 'product', 'sales')\n"
            "        totals = dict(zip(result['product'], result['total']))\n"
            "        assert totals['Widget'] == 385, f\"Widget total={totals['Widget']}, expected 385\"\n"
            "        assert totals['Gadget'] == 550, f\"Gadget total={totals['Gadget']}, expected 550\"\n"
            "        passed += 1; print('\\u2705 Check 4: Widget=385, Gadget=550')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: sorted descending by total (Gadget 550 first)\n"
            "    try:\n"
            "        result = group_summary(ORDERS_DF, 'product', 'sales')\n"
            "        assert result.iloc[0]['product'] == 'Gadget', \\\n"
            "            f\"first row should be Gadget (total=550), got {result.iloc[0]['product']!r}\"\n"
            "        assert list(result.index) == list(range(len(result))), \\\n"
            "            f'index not reset: {list(result.index)}'\n"
            "        passed += 1; print('\\u2705 Check 5: sorted by total desc, index reset')\n"
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
            + GROUP_SUMMARY_IMPL + "\n"
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
            "# Day 036 Project: Sales Dataset Analysis\n\n"
            "## What You're Building\n\n"
            "A structured analysis of a sales dataset using all five pandas skills from today:\n"
            "inspect, load, filter, transform, and aggregate.\n\n"
            "**Deliverable:** You run every cell top-to-bottom. The final cell's checks pass. "
            "You have a `report` dict with `total_revenue`, `top_product`, `avg_order_value`, "
            "and `category_breakdown`.\n\n"
            "## Project Requirements\n\n"
            "1. Load `SALES_CSV` (provided below) into a DataFrame using `load_csv`\n"
            "2. Call `summarize_dataframe` to inspect it\n"
            "3. Add a `'category'` column using `add_category_column`\n"
            "4. Filter to high-value orders (`revenue >= 500`) using `filter_by_threshold`\n"
            "5. Build a `group_summary` of `revenue` by `product`\n"
            "6. Assemble a `report` dict and verify with `_run_project_checks()`"
        ),
        code(
            "import warnings\n"
            "warnings.filterwarnings('ignore')\n"
            "import io\n"
            "import pandas as pd\n"
            "\n"
            + ALL_IMPLS + "\n\n\n"
            + GROUP_SUMMARY_IMPL + "\n\n\n"
            "SALES_CSV = (\n"
            "    'order_id,product,unit_price,quantity\\n'\n"
            "    '1,Widget,25,10\\n'\n"
            "    '2,Gadget,150,3\\n'\n"
            "    '3,Widget,25,20\\n'\n"
            "    '4,Doohickey,8,50\\n'\n"
            "    '5,Gadget,150,5\\n'\n"
            "    '6,Thingamajig,200,2\\n'\n"
            "    '7,Widget,25,4\\n'\n"
            "    '8,Doohickey,8,15\\n'\n"
            "    '9,Thingamajig,200,8\\n'\n"
            "    '10,Gadget,150,1'\n"
            ")"
        ),
        md("## Your Analysis"),
        code(
            "# Step 1: Load and inspect\n"
            "df = load_csv(SALES_CSV)\n"
            "# TODO: info = summarize_dataframe(df)\n"
            "# print(info)\n"
            "\n"
            "# Step 2: Add a revenue column\n"
            "# TODO: df['revenue'] = df['unit_price'] * df['quantity']\n"
            "\n"
            "# Step 3: Add price category\n"
            "# TODO: df = add_category_column(df, 'unit_price')\n"
            "\n"
            "# Step 4: Filter to high-value orders (revenue >= 500)\n"
            "# TODO: high_value = filter_by_threshold(df, 'revenue', 500)\n"
            "\n"
            "# Step 5: Group summary by product\n"
            "# TODO: product_summary = group_summary(df, 'product', 'revenue')\n"
            "\n"
            "# Step 6: Assemble report\n"
            "# TODO: report = {\n"
            "#     'total_revenue':    df['revenue'].sum(),\n"
            "#     'top_product':      product_summary.iloc[0]['product'],\n"
            "#     'avg_order_value':  round(df['revenue'].mean(), 2),\n"
            "#     'category_breakdown': group_summary(df, 'category', 'revenue'),\n"
            "# }\n"
            "# print(report)"
        ),
        md("## Project Checks"),
        code(
            "def _run_project_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: df has revenue column\n"
            "    try:\n"
            "        assert 'df' in globals()\n"
            "        assert 'revenue' in df.columns, \\\n"
            "            \"'revenue' column missing — add: df['revenue'] = df['unit_price'] * df['quantity']\"\n"
            "        passed += 1; print('\\u2705 Check 1: df has revenue column')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "\n"
            "    # Check 2: df has category column\n"
            "    try:\n"
            "        assert 'category' in df.columns, \\\n"
            "            \"'category' column missing — call add_category_column(df, 'unit_price')\"\n"
            "        valid = {'budget', 'standard', 'premium'}\n"
            "        bad = set(df['category'].unique()) - valid\n"
            "        assert not bad, f'unexpected category values: {bad}'\n"
            "        passed += 1; print('\\u2705 Check 2: df has valid category column')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: high_value is defined and correct\n"
            "    try:\n"
            "        assert 'high_value' in globals(), \\\n"
            "            'high_value not defined — call filter_by_threshold(df, revenue, 500)'\n"
            "        assert (high_value['revenue'] >= 500).all(), \\\n"
            "            'some high_value rows have revenue < 500'\n"
            "        assert len(high_value) > 0, 'high_value is empty'\n"
            "        passed += 1; print(f'\\u2705 Check 3: {len(high_value)} high-value orders (revenue >= 500)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: report is defined with correct keys\n"
            "    try:\n"
            "        assert 'report' in globals(), 'report not defined'\n"
            "        for k in ('total_revenue', 'top_product', 'avg_order_value', 'category_breakdown'):\n"
            "            assert k in report, f'report missing key: {k}'\n"
            "        passed += 1; print('\\u2705 Check 4: report has all 4 keys')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: report values are plausible\n"
            "    try:\n"
            "        assert report['total_revenue'] > 0, 'total_revenue should be > 0'\n"
            "        assert isinstance(report['top_product'], str), \\\n"
            "            f\"top_product should be a str, got {type(report['top_product']).__name__}\"\n"
            "        assert report['avg_order_value'] > 0, 'avg_order_value should be > 0'\n"
            "        assert isinstance(report['category_breakdown'], pd.DataFrame), \\\n"
            "            'category_breakdown should be a DataFrame'\n"
            "        passed += 1; print(f\"\\u2705 Check 5: total_revenue={report['total_revenue']}, \"\n"
            "                           f\"top_product={report['top_product']!r}\")\n"
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
            "- Add a `month` column by repeating months across orders and group by month\n"
            "- Use `.loc[]` to update specific rows — try raising prices of 'budget' items by 10%\n"
            "- Use `df.describe()` to get the full statistics table and print it\n"
            "- Export the report to CSV with `product_summary.to_csv('report.csv', index=False)`\n"
            "- On Day 39 you will visualize this data — save `df` for then"
        ),
    ]


# ---------------------------------------------------------------------------
# Solution notebook
# ---------------------------------------------------------------------------

def solution_nb():
    global _cid; _cid = 600
    return [
        md(
            "# Day 036 Solution — Pandas Fundamentals\n\n"
            "End-to-end analysis: load a sales dataset, inspect it, "
            "add computed columns, filter, and aggregate."
        ),
        code(
            "import warnings\n"
            "warnings.filterwarnings('ignore')\n"
            "import io\n"
            "import pandas as pd\n"
            "\n"
            + ALL_IMPLS + "\n\n\n"
            + GROUP_SUMMARY_IMPL
        ),
        md("## Step 1 — Load & Inspect"),
        code(
            "SALES_CSV = (\n"
            "    'order_id,product,unit_price,quantity\\n'\n"
            "    '1,Widget,25,10\\n'\n"
            "    '2,Gadget,150,3\\n'\n"
            "    '3,Widget,25,20\\n'\n"
            "    '4,Doohickey,8,50\\n'\n"
            "    '5,Gadget,150,5\\n'\n"
            "    '6,Thingamajig,200,2\\n'\n"
            "    '7,Widget,25,4\\n'\n"
            "    '8,Doohickey,8,15\\n'\n"
            "    '9,Thingamajig,200,8\\n'\n"
            "    '10,Gadget,150,1'\n"
            ")\n"
            "\n"
            "df = load_csv(SALES_CSV)\n"
            "info = summarize_dataframe(df)\n"
            "print('Shape:', df.shape)\n"
            "print('Columns:', info['columns'])\n"
            "print('Numeric cols:', info['numeric_cols'])\n"
            "print('Null count:', info['null_count'])\n"
            "print(df.head())\n"
            "\n"
            "assert df.shape == (10, 4)\n"
            "assert info['null_count'] == 0"
        ),
        md("## Step 2 — Add Revenue Column"),
        code(
            "df['revenue'] = df['unit_price'] * df['quantity']\n"
            "print(df[['product', 'unit_price', 'quantity', 'revenue']].to_string(index=False))\n"
            "\n"
            "assert 'revenue' in df.columns\n"
            "assert df['revenue'].sum() == (\n"
            "    25*10 + 150*3 + 25*20 + 8*50 + 150*5 + 200*2 + 25*4 + 8*15 + 200*8 + 150*1\n"
            ")"
        ),
        md("## Step 3 — Add Price Category"),
        code(
            "df = add_category_column(df, 'unit_price')\n"
            "print(df[['product', 'unit_price', 'category']].drop_duplicates().to_string(index=False))\n"
            "\n"
            "assert 'category' in df.columns\n"
            "# Doohickey 8 -> budget, Widget 25 -> standard,\n"
            "# Gadget 150 -> premium, Thingamajig 200 -> premium\n"
            "cats = dict(zip(df['product'], df['category']))\n"
            "assert cats['Doohickey']    == 'budget'\n"
            "assert cats['Widget']       == 'standard'\n"
            "assert cats['Gadget']       == 'premium'\n"
            "assert cats['Thingamajig']  == 'premium'"
        ),
        md("## Step 4 — Filter High-Value Orders"),
        code(
            "high_value = filter_by_threshold(df, 'revenue', 500)\n"
            "print(f'{len(high_value)} orders with revenue >= 500:')\n"
            "print(high_value[['order_id', 'product', 'revenue']].to_string(index=False))\n"
            "\n"
            "assert (high_value['revenue'] >= 500).all()\n"
            "assert len(high_value) > 0"
        ),
        md("## Step 5 — Group Summary by Product"),
        code(
            "product_summary = group_summary(df, 'product', 'revenue')\n"
            "print('Revenue by product (sorted):')\n"
            "print(product_summary.to_string(index=False))\n"
            "\n"
            "assert list(product_summary.columns) == ['product', 'total', 'count']\n"
            "assert product_summary.iloc[0]['total'] >= product_summary.iloc[1]['total']"
        ),
        md("## Step 6 — Assemble Report"),
        code(
            "report = {\n"
            "    'total_revenue':     df['revenue'].sum(),\n"
            "    'top_product':       product_summary.iloc[0]['product'],\n"
            "    'avg_order_value':   round(df['revenue'].mean(), 2),\n"
            "    'category_breakdown': group_summary(df, 'category', 'revenue'),\n"
            "}\n"
            "\n"
            "print(f\"Total revenue    : {report['total_revenue']}\")\n"
            "print(f\"Top product      : {report['top_product']}\")\n"
            "print(f\"Avg order value  : {report['avg_order_value']}\")\n"
            "print('Category breakdown:')\n"
            "print(report['category_breakdown'].to_string(index=False))\n"
            "\n"
            "assert report['total_revenue'] > 0\n"
            "assert isinstance(report['top_product'], str)\n"
            "assert report['avg_order_value'] > 0\n"
            "\n"
            "print('\\nPandas Fundamentals complete!')"
        ),
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Generating Day 036 notebooks...")
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
