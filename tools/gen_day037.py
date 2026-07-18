#!/usr/bin/env python3
"""Generate all Day 037 notebooks: exercises 1-5, project, solution."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAY_DIR = ROOT / "03_data_analysis" / "day_037"

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
# Implementations (module-level — no f-string conflicts)
# ---------------------------------------------------------------------------

DROP_OR_FILL_NULLS_IMPL = """\
import pandas as pd

def drop_or_fill_nulls(df: pd.DataFrame, strategy: str = 'mean') -> pd.DataFrame:
    result   = df.copy()
    if strategy == 'drop':
        return result.dropna().reset_index(drop=True)
    num_cols = result.select_dtypes(include='number').columns
    if strategy == 'zero':
        result[num_cols] = result[num_cols].fillna(0)
    elif strategy == 'mean':
        for col in num_cols:
            result[col] = result[col].fillna(result[col].mean())
    elif strategy == 'median':
        for col in num_cols:
            result[col] = result[col].fillna(result[col].median())
    else:
        raise ValueError(
            f"Unknown strategy {strategy!r}. "
            "Use 'drop', 'zero', 'mean', or 'median'."
        )
    return result"""

COERCE_NUMERIC_IMPL = """\
import pandas as pd

def coerce_numeric_columns(df: pd.DataFrame, columns: list) -> pd.DataFrame:
    result = df.copy()
    for col in columns:
        result[col] = pd.to_numeric(result[col], errors='coerce')
    return result"""

CLEAN_STRING_COLUMN_IMPL = """\
import pandas as pd

def clean_string_column(df: pd.DataFrame, col: str) -> pd.DataFrame:
    result = df.copy()
    result[col] = result[col].str.strip().str.lower()
    return result"""

DEDUPLICATE_IMPL = """\
import pandas as pd

def deduplicate(df: pd.DataFrame, subset: list | None = None) -> pd.DataFrame:
    return df.drop_duplicates(subset=subset).reset_index(drop=True)"""

CLEAN_DATAFRAME_IMPL = """\
import pandas as pd

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    for col in result.select_dtypes(include='object').columns:
        result[col] = result[col].str.strip()
    for col in result.select_dtypes(include='number').columns:
        result[col] = result[col].fillna(result[col].median())
    return result.drop_duplicates().reset_index(drop=True)"""

# Ordered subsets used in exercise setup cells
_BEFORE_COERCE  = DROP_OR_FILL_NULLS_IMPL
_BEFORE_STRING  = "\n\n\n".join([DROP_OR_FILL_NULLS_IMPL, COERCE_NUMERIC_IMPL])
_BEFORE_DEDUP   = "\n\n\n".join([DROP_OR_FILL_NULLS_IMPL, COERCE_NUMERIC_IMPL,
                                  CLEAN_STRING_COLUMN_IMPL])
ALL_IMPLS = "\n\n\n".join([DROP_OR_FILL_NULLS_IMPL, COERCE_NUMERIC_IMPL,
                            CLEAN_STRING_COLUMN_IMPL, DEDUPLICATE_IMPL])


# ---------------------------------------------------------------------------
# Exercise 01 — drop_or_fill_nulls
# ---------------------------------------------------------------------------

def ex01():
    global _cid; _cid = 0
    return [
        md(
            "# Day 037 — Exercise 1: drop_or_fill_nulls\n\n"
            "**What you'll build:** `drop_or_fill_nulls(df, strategy) -> pd.DataFrame` — "
            "handle NaN values in numeric columns using one of four strategies: "
            "`'drop'` (remove rows), `'zero'` (replace with 0), "
            "`'mean'` (column mean), `'median'` (column median).\n\n"
            "**Why it matters:** Missing values crash every downstream operation — "
            "groupby, ML models, arithmetic. Choosing the right fill strategy is the "
            "first engineering decision in any cleaning pipeline."
        ),
        code(
            "import warnings\n"
            "warnings.filterwarnings('ignore')\n"
            "import pandas as pd\n"
            "\n"
            "# NULL_DF: rows 1 and 2 have nulls in different columns\n"
            "NULL_DF = pd.DataFrame({\n"
            "    'a':     [1.0, 2.0, None, 4.0],\n"
            "    'b':     [10.0, None, 30.0, 40.0],\n"
            "    'label': ['x', 'y', 'z', 'w'],\n"
            "})"
        ),
        md("## Your Implementation"),
        code(
            "def drop_or_fill_nulls(df: pd.DataFrame, strategy: str = 'mean') -> pd.DataFrame:\n"
            '    """\n'
            "    Handle NaN values in numeric columns.\n\n"
            "    Strategies:\n"
            "        'drop'   — remove any row that has at least one NaN; reset index\n"
            "        'zero'   — replace NaN with 0 in all numeric columns\n"
            "        'mean'   — replace NaN with the column mean\n"
            "        'median' — replace NaN with the column median\n"
            "    Non-numeric columns are not touched. Original df is not mutated.\n"
            '    """\n'
            "    result = df.copy()\n"
            "    # TODO: if strategy == 'drop': return result.dropna().reset_index(drop=True)\n"
            "    # TODO: num_cols = result.select_dtypes(include='number').columns\n"
            "    # TODO: if strategy == 'zero':   result[num_cols] = result[num_cols].fillna(0)\n"
            "    # TODO: elif strategy == 'mean': for col in num_cols: fill with col mean\n"
            "    # TODO: elif strategy == 'median': for col in num_cols: fill with col median\n"
            "    # TODO: else: raise ValueError(f'Unknown strategy ...')\n"
            "    # TODO: return result\n"
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
            "        assert 'drop_or_fill_nulls' in globals()\n"
            "        result = drop_or_fill_nulls(NULL_DF, 'drop')\n"
            "        assert isinstance(result, pd.DataFrame), \\\n"
            "            f'expected DataFrame, got {type(result).__name__}'\n"
            "        passed += 1; print('\\u2705 Check 1: returns a DataFrame')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: strategy='drop' removes rows with any null\n"
            "    try:\n"
            "        result = drop_or_fill_nulls(NULL_DF, 'drop')\n"
            "        assert len(result) == 2, f'expected 2 rows, got {len(result)}'\n"
            "        assert result.isnull().sum().sum() == 0, 'nulls still present after drop'\n"
            "        assert list(result.index) == [0, 1], f'index not reset: {list(result.index)}'\n"
            "        passed += 1; print('\\u2705 Check 2: strategy=drop removes null rows and resets index')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: strategy='zero' fills numeric nulls with 0\n"
            "    try:\n"
            "        result = drop_or_fill_nulls(NULL_DF, 'zero')\n"
            "        assert result.shape == NULL_DF.shape, \\\n"
            "            f'shape changed: {result.shape}'\n"
            "        assert result[['a', 'b']].isnull().sum().sum() == 0, \\\n"
            "            'numeric nulls not filled'\n"
            "        assert result.at[1, 'b'] == 0.0, \\\n"
            "            f'b[1] should be 0.0, got {result.at[1, \"b\"]}'\n"
            "        assert result.at[2, 'a'] == 0.0, \\\n"
            "            f'a[2] should be 0.0, got {result.at[2, \"a\"]}'\n"
            "        passed += 1; print('\\u2705 Check 3: strategy=zero fills nulls with 0')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: strategy='mean' fills with column mean\n"
            "    try:\n"
            "        result = drop_or_fill_nulls(NULL_DF, 'mean')\n"
            "        assert result.shape == NULL_DF.shape\n"
            "        assert result[['a', 'b']].isnull().sum().sum() == 0\n"
            "        expected_a = (1 + 2 + 4) / 3\n"
            "        actual_a   = float(result.at[2, 'a'])\n"
            "        assert abs(actual_a - expected_a) < 0.001, \\\n"
            "            f'a[2] should be ~{expected_a:.3f}, got {actual_a:.3f}'\n"
            "        passed += 1; print(f'\\u2705 Check 4: strategy=mean fills a[2] with ~{expected_a:.3f}')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: original DataFrame is NOT mutated\n"
            "    try:\n"
            "        _ = drop_or_fill_nulls(NULL_DF, 'zero')\n"
            "        assert NULL_DF.isnull().sum().sum() == 2, \\\n"
            "            'original DataFrame was mutated (use df.copy()!)'\n"
            "        passed += 1; print('\\u2705 Check 5: original DataFrame not mutated')\n"
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
            + DROP_OR_FILL_NULLS_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 02 — coerce_numeric_columns
# ---------------------------------------------------------------------------

def ex02():
    global _cid; _cid = 100
    return [
        md(
            "# Day 037 — Exercise 2: coerce_numeric_columns\n\n"
            "**What you'll build:** `coerce_numeric_columns(df, columns) -> pd.DataFrame` — "
            "convert listed columns to numeric using `pd.to_numeric(errors='coerce')`, "
            "turning non-numeric strings into NaN.\n\n"
            "**Why it matters:** Real CSVs often store numbers as strings, or have typos "
            "like `'abc'` in a price field. `errors='coerce'` converts what it can and "
            "makes bad values NaN — a safe, auditable conversion that you can then fill "
            "with your null strategy."
        ),
        code(
            "import warnings\n"
            "warnings.filterwarnings('ignore')\n"
            "import io\n"
            "import pandas as pd\n"
            "\n"
            + _BEFORE_COERCE + "\n\n\n"
            "# COERCE_DF: 'abc' and 'def' are bad values that will become NaN\n"
            "COERCE_CSV = (\n"
            "    'item,price,quantity\\n'\n"
            "    'pen,5,10\\n'\n"
            "    'book,abc,5\\n'\n"
            "    'laptop,999,def\\n'\n"
            "    'cup,12.5,20'\n"
            ")\n"
            "COERCE_DF = pd.read_csv(io.StringIO(COERCE_CSV))\n"
            "# price dtype is 'object' because 'abc' prevented numeric inference"
        ),
        md("## Your Implementation"),
        code(
            "def coerce_numeric_columns(df: pd.DataFrame, columns: list) -> pd.DataFrame:\n"
            '    """\n'
            "    Convert the listed columns to numeric dtype.\n\n"
            "    Values that cannot be converted become NaN (errors='coerce').\n"
            "    Original df is not mutated.\n"
            '    """\n'
            "    result = df.copy()\n"
            "    # TODO: for col in columns:\n"
            "    #     result[col] = pd.to_numeric(result[col], errors='coerce')\n"
            "    # TODO: return result\n"
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
            "        assert 'coerce_numeric_columns' in globals()\n"
            "        result = coerce_numeric_columns(COERCE_DF, ['price'])\n"
            "        assert isinstance(result, pd.DataFrame), \\\n"
            "            f'expected DataFrame, got {type(result).__name__}'\n"
            "        passed += 1; print('\\u2705 Check 1: returns a DataFrame')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: non-numeric 'abc' becomes NaN in price\n"
            "    try:\n"
            "        result = coerce_numeric_columns(COERCE_DF, ['price', 'quantity'])\n"
            "        import math\n"
            "        assert math.isnan(float(result.at[1, 'price'])), \\\n"
            "            f\"price[1] should be NaN (was 'abc'), got {result.at[1, 'price']}\"\n"
            "        passed += 1; print(\"\\u2705 Check 2: 'abc' becomes NaN in price column\")\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: valid numbers are converted to float\n"
            "    try:\n"
            "        result = coerce_numeric_columns(COERCE_DF, ['price', 'quantity'])\n"
            "        assert float(result.at[0, 'price']) == 5.0, \\\n"
            "            f\"price[0] should be 5.0, got {result.at[0, 'price']}\"\n"
            "        assert float(result.at[2, 'price']) == 999.0, \\\n"
            "            f\"price[2] should be 999.0, got {result.at[2, 'price']}\"\n"
            "        passed += 1; print('\\u2705 Check 3: valid numbers converted to float correctly')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: coerced columns are now numeric dtype\n"
            "    try:\n"
            "        result = coerce_numeric_columns(COERCE_DF, ['price', 'quantity'])\n"
            "        assert pd.api.types.is_numeric_dtype(result['price']), \\\n"
            "            f\"price dtype still {result['price'].dtype}\"\n"
            "        assert pd.api.types.is_numeric_dtype(result['quantity']), \\\n"
            "            f\"quantity dtype still {result['quantity'].dtype}\"\n"
            "        passed += 1; print('\\u2705 Check 4: coerced columns are numeric dtype')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: original DataFrame not mutated\n"
            "    try:\n"
            "        _ = coerce_numeric_columns(COERCE_DF, ['price', 'quantity'])\n"
            "        assert COERCE_DF['price'].dtype == object, \\\n"
            "            f'original price dtype changed to {COERCE_DF[\"price\"].dtype}'\n"
            "        assert COERCE_DF.at[1, 'price'] == 'abc', \\\n"
            "            f\"original price[1] changed from 'abc' to {COERCE_DF.at[1, 'price']}\"\n"
            "        passed += 1; print('\\u2705 Check 5: original DataFrame not mutated')\n"
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
            + COERCE_NUMERIC_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 03 — clean_string_column
# ---------------------------------------------------------------------------

def ex03():
    global _cid; _cid = 200
    return [
        md(
            "# Day 037 — Exercise 3: clean_string_column\n\n"
            "**What you'll build:** `clean_string_column(df, col) -> pd.DataFrame` — "
            "strip leading/trailing whitespace and lowercase a single string column "
            "using pandas' vectorised `.str` accessor.\n\n"
            "**Why it matters:** `'  Widget '` and `'widget'` look the same to humans "
            "but are different strings to Python — groupby, merge, and dedup will treat "
            "them as distinct values. Normalising case and whitespace is the fix."
        ),
        code(
            "import warnings\n"
            "warnings.filterwarnings('ignore')\n"
            "import io\n"
            "import pandas as pd\n"
            "\n"
            + _BEFORE_STRING + "\n\n\n"
            "STRING_CSV = (\n"
            "    'name,city\\n'\n"
            "    '  Alice  ,New York\\n'\n"
            "    ' bob, London \\n'\n"
            "    'CAROL,PARIS'\n"
            ")\n"
            "STRING_DF = pd.read_csv(io.StringIO(STRING_CSV))"
        ),
        md("## Your Implementation"),
        code(
            "def clean_string_column(df: pd.DataFrame, col: str) -> pd.DataFrame:\n"
            '    """\n'
            "    Strip whitespace and lowercase one string column.\n\n"
            "    Uses the vectorised .str accessor — NaN values are preserved (not\n"
            "    converted to the string 'nan'). Original df is not mutated.\n"
            '    """\n'
            "    result = df.copy()\n"
            "    # TODO: result[col] = result[col].str.strip().str.lower()\n"
            "    # TODO: return result\n"
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
            "        assert 'clean_string_column' in globals()\n"
            "        result = clean_string_column(STRING_DF, 'name')\n"
            "        assert isinstance(result, pd.DataFrame), \\\n"
            "            f'expected DataFrame, got {type(result).__name__}'\n"
            "        passed += 1; print('\\u2705 Check 1: returns a DataFrame')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: whitespace stripped from target column\n"
            "    try:\n"
            "        result = clean_string_column(STRING_DF, 'name')\n"
            "        names = result['name'].tolist()\n"
            "        for n in names:\n"
            "            assert not n.startswith(' ') and not n.endswith(' '), \\\n"
            "                f'name {n!r} still has leading/trailing whitespace'\n"
            "        passed += 1; print('\\u2705 Check 2: whitespace stripped from name column')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: values are lowercased\n"
            "    try:\n"
            "        result = clean_string_column(STRING_DF, 'name')\n"
            "        assert result['name'].tolist() == ['alice', 'bob', 'carol'], \\\n"
            "            f\"expected ['alice','bob','carol'], got {result['name'].tolist()}\"\n"
            "        passed += 1; print(\"\\u2705 Check 3: name column is ['alice', 'bob', 'carol']\")\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: other columns NOT changed\n"
            "    try:\n"
            "        result = clean_string_column(STRING_DF, 'name')\n"
            "        assert result['city'].tolist() == STRING_DF['city'].tolist(), \\\n"
            "            f'city column was changed: {result[\"city\"].tolist()}'\n"
            "        passed += 1; print('\\u2705 Check 4: city column unchanged')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: original DataFrame not mutated\n"
            "    try:\n"
            "        _ = clean_string_column(STRING_DF, 'name')\n"
            "        assert STRING_DF.at[0, 'name'] == '  Alice  ', \\\n"
            "            f\"original name[0] changed from '  Alice  ' to {STRING_DF.at[0, 'name']!r}\"\n"
            "        passed += 1; print('\\u2705 Check 5: original DataFrame not mutated')\n"
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
            + CLEAN_STRING_COLUMN_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 04 — deduplicate
# ---------------------------------------------------------------------------

def ex04():
    global _cid; _cid = 300
    return [
        md(
            "# Day 037 — Exercise 4: deduplicate\n\n"
            "**What you'll build:** `deduplicate(df, subset=None) -> pd.DataFrame` — "
            "remove duplicate rows with `df.drop_duplicates()` and reset the index. "
            "The optional `subset` list restricts which columns define a duplicate.\n\n"
            "**Why it matters:** Double-processing an API response, re-running an ETL "
            "job, or concatenating overlapping exports all produce duplicates. "
            "`drop_duplicates` keeps the first occurrence by default — an auditable, "
            "deterministic choice."
        ),
        code(
            "import warnings\n"
            "warnings.filterwarnings('ignore')\n"
            "import io\n"
            "import pandas as pd\n"
            "\n"
            + _BEFORE_DEDUP + "\n\n\n"
            "# DUPE_DF: Widget(25) appears at rows 0 and 2; Gadget(150) at rows 1 and 4\n"
            "DUPE_CSV = (\n"
            "    'product,price\\n'\n"
            "    'Widget,25\\n'\n"
            "    'Gadget,150\\n'\n"
            "    'Widget,25\\n'\n"
            "    'Doohickey,8\\n'\n"
            "    'Gadget,150'\n"
            ")\n"
            "DUPE_DF = pd.read_csv(io.StringIO(DUPE_CSV))"
        ),
        md("## Your Implementation"),
        code(
            "def deduplicate(df: pd.DataFrame, subset: list | None = None) -> pd.DataFrame:\n"
            '    """\n'
            "    Remove duplicate rows and reset the index.\n\n"
            "    Args:\n"
            "        df     — source DataFrame\n"
            "        subset — column name list to compare (None = all columns)\n"
            "    Returns:\n"
            "        Deduplicated DataFrame with index reset to 0, 1, 2, ...\n"
            '    """\n'
            "    # TODO: return df.drop_duplicates(subset=subset).reset_index(drop=True)\n"
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
            "        assert 'deduplicate' in globals()\n"
            "        result = deduplicate(DUPE_DF)\n"
            "        assert isinstance(result, pd.DataFrame), \\\n"
            "            f'expected DataFrame, got {type(result).__name__}'\n"
            "        passed += 1; print('\\u2705 Check 1: returns a DataFrame')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: duplicate rows removed (5 → 3)\n"
            "    try:\n"
            "        result = deduplicate(DUPE_DF)\n"
            "        assert len(result) == 3, f'expected 3 rows, got {len(result)}'\n"
            "        products = set(result['product'])\n"
            "        assert products == {'Widget', 'Gadget', 'Doohickey'}, \\\n"
            "            f'unexpected products: {products}'\n"
            "        passed += 1; print('\\u2705 Check 2: 5 rows → 3 unique rows')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: index is reset (0, 1, 2)\n"
            "    try:\n"
            "        result = deduplicate(DUPE_DF)\n"
            "        assert list(result.index) == [0, 1, 2], \\\n"
            "            f'index not reset: {list(result.index)}'\n"
            "        passed += 1; print('\\u2705 Check 3: index reset to 0, 1, 2')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: subset parameter limits which columns define equality\n"
            "    try:\n"
            "        mixed = pd.DataFrame({\n"
            "            'product': ['Widget', 'Widget', 'Gadget'],\n"
            "            'price':   [25, 30, 150],\n"
            "        })\n"
            "        result_all = deduplicate(mixed)\n"
            "        result_sub = deduplicate(mixed, subset=['product'])\n"
            "        assert len(result_all) == 3, \\\n"
            "            f'all-columns dedup: expected 3 rows, got {len(result_all)}'\n"
            "        assert len(result_sub) == 2, \\\n"
            "            f'subset dedup: expected 2 rows, got {len(result_sub)}'\n"
            "        passed += 1; print('\\u2705 Check 4: subset parameter works correctly')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: original DataFrame not mutated\n"
            "    try:\n"
            "        _ = deduplicate(DUPE_DF)\n"
            "        assert len(DUPE_DF) == 5, \\\n"
            "            f'original changed: expected 5 rows, got {len(DUPE_DF)}'\n"
            "        passed += 1; print('\\u2705 Check 5: original DataFrame not mutated')\n"
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
            + DEDUPLICATE_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 05 — clean_dataframe (pipeline)
# ---------------------------------------------------------------------------

def ex05():
    global _cid; _cid = 400
    return [
        md(
            "# Day 037 — Exercise 5: clean_dataframe\n\n"
            "**What you'll build:** `clean_dataframe(df) -> pd.DataFrame` — a single-call "
            "cleaning pipeline that: (1) strips whitespace from all string columns, "
            "(2) fills numeric NaN with each column's median, "
            "(3) drops duplicate rows and resets the index.\n\n"
            "**Why it matters:** Real pipelines need a reliable entry point that "
            "normalises any raw DataFrame before analysis. Composing the three techniques "
            "into one function gives downstream code a clean guarantee."
        ),
        md("## Provided: All Four Cleaning Helpers"),
        code(ALL_IMPLS),
        code(
            "import warnings\n"
            "warnings.filterwarnings('ignore')\n"
            "import pandas as pd\n"
            "\n"
            "# MESSY_DF: whitespace in product, one null price, two duplicate rows\n"
            "MESSY_DF = pd.DataFrame({\n"
            "    'product': ['  Widget  ', ' Gadget', 'Widget ', '  Widget  ', 'Doohickey'],\n"
            "    'price':   [25.0, 150.0, 25.0, 25.0, None],\n"
            "    'qty':     [10.0, 5.0, 10.0, 10.0, 50.0],\n"
            "})"
        ),
        md("## Your Implementation"),
        code(
            "def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:\n"
            '    """\n'
            "    Strip → fill nulls → deduplicate.\n\n"
            "    1. For every object (string) column: strip leading/trailing whitespace.\n"
            "    2. For every numeric column: fill NaN with the column median.\n"
            "    3. Drop duplicate rows and reset the index.\n"
            "    Original df is not mutated.\n"
            '    """\n'
            "    result = df.copy()\n"
            "    # TODO: for col in result.select_dtypes(include='object').columns:\n"
            "    #     result[col] = result[col].str.strip()\n"
            "    # TODO: for col in result.select_dtypes(include='number').columns:\n"
            "    #     result[col] = result[col].fillna(result[col].median())\n"
            "    # TODO: return result.drop_duplicates().reset_index(drop=True)\n"
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
            "        assert 'clean_dataframe' in globals()\n"
            "        result = clean_dataframe(MESSY_DF)\n"
            "        assert isinstance(result, pd.DataFrame), \\\n"
            "            f'expected DataFrame, got {type(result).__name__}'\n"
            "        passed += 1; print('\\u2705 Check 1: returns a DataFrame')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: no numeric nulls remain\n"
            "    try:\n"
            "        result = clean_dataframe(MESSY_DF)\n"
            "        num_nulls = result.select_dtypes(include='number').isnull().sum().sum()\n"
            "        assert num_nulls == 0, f'{num_nulls} numeric nulls still present'\n"
            "        passed += 1; print('\\u2705 Check 2: no numeric nulls after cleaning')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: string columns have no leading/trailing whitespace\n"
            "    try:\n"
            "        result = clean_dataframe(MESSY_DF)\n"
            "        str_cols = result.select_dtypes(include='object').columns\n"
            "        for col in str_cols:\n"
            "            vals = result[col].dropna()\n"
            "            has_ws = vals.str.startswith(' ') | vals.str.endswith(' ')\n"
            "            assert not has_ws.any(), \\\n"
            "                f'column {col!r} still has whitespace: {vals[has_ws].tolist()}'\n"
            "        passed += 1; print('\\u2705 Check 3: string columns stripped of whitespace')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: no duplicate rows and index is reset\n"
            "    try:\n"
            "        result = clean_dataframe(MESSY_DF)\n"
            "        assert not result.duplicated().any(), \\\n"
            "            'duplicate rows still present'\n"
            "        assert list(result.index) == list(range(len(result))), \\\n"
            "            f'index not reset: {list(result.index)}'\n"
            "        passed += 1; print(f'\\u2705 Check 4: no duplicates, index reset ({len(result)} rows)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: original DataFrame not mutated\n"
            "    try:\n"
            "        _ = clean_dataframe(MESSY_DF)\n"
            "        assert '  Widget  ' in MESSY_DF['product'].values, \\\n"
            "            'original product column was mutated (spaces removed)'\n"
            "        assert MESSY_DF['price'].isnull().sum() == 1, \\\n"
            "            'original price column was mutated (null filled)'\n"
            "        passed += 1; print('\\u2705 Check 5: original DataFrame not mutated')\n"
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
            + CLEAN_DATAFRAME_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Project notebook
# ---------------------------------------------------------------------------

def project_nb():
    global _cid; _cid = 500
    all_code = ALL_IMPLS + "\n\n\n" + CLEAN_DATAFRAME_IMPL
    return [
        md(
            "# Day 037 Project: Clean a Messy Sales Dataset\n\n"
            "## What You're Building\n\n"
            "A full cleaning pipeline applied to a realistic messy dataset: "
            "bad numeric values, whitespace in strings, missing quantities, and "
            "duplicate rows — all fixed in a reproducible sequence of steps.\n\n"
            "**Deliverable:** You run every cell top-to-bottom. "
            "The final cell's checks pass. You have a `cleaned` DataFrame "
            "with no nulls, no extra whitespace, and no duplicates.\n\n"
            "## Project Requirements\n\n"
            "1. Load `MESSY_CSV` (provided) with `pd.read_csv(io.StringIO(...))`\n"
            "2. Call `coerce_numeric_columns` to fix the bad `price` value\n"
            "3. Call `clean_string_column` on `product` and `region`\n"
            "4. Call `drop_or_fill_nulls` with `strategy='median'` to fill missing `quantity`\n"
            "5. Call `deduplicate` to remove duplicate rows\n"
            "6. Store the result as `cleaned` and verify with `_run_project_checks()`"
        ),
        code(
            "import warnings\n"
            "warnings.filterwarnings('ignore')\n"
            "import io\n"
            "import pandas as pd\n"
            "\n"
            + all_code + "\n\n\n"
            "MESSY_CSV = (\n"
            "    'order_id,product,price,quantity,region\\n'\n"
            "    '1, Widget ,25.0,10, North\\n'\n"
            "    '2, Gadget ,bad_price,,South\\n'\n"
            "    '3,Widget,25.0,20,North\\n'\n"
            "    '4, Widget ,25.0,20, North\\n'\n"
            "    '5,Doohickey,8.0,50,EAST\\n'\n"
            "    '5,Doohickey,8.0,50,EAST\\n'\n"
            "    '6,Thingamajig,200.0,8,West'\n"
            ")\n"
            "raw = pd.read_csv(io.StringIO(MESSY_CSV))\n"
            "print(f'Raw shape: {raw.shape}')\n"
            "print(raw.to_string())"
        ),
        md("## Your Cleaning Pipeline"),
        code(
            "# Step 1: Fix the bad price value ('bad_price' -> NaN)\n"
            "# TODO: df = coerce_numeric_columns(raw, ['price'])\n"
            "\n"
            "# Step 2: Strip and lowercase product and region\n"
            "# TODO: df = clean_string_column(df, 'product')\n"
            "# TODO: df = clean_string_column(df, 'region')\n"
            "\n"
            "# Step 3: Fill missing quantity (and coerced NaN price) with median\n"
            "# TODO: df = drop_or_fill_nulls(df, strategy='median')\n"
            "\n"
            "# Step 4: Remove duplicate rows\n"
            "# TODO: cleaned = deduplicate(df)\n"
            "\n"
            "# Step 5: Inspect the result\n"
            "# TODO: print(cleaned.to_string())"
        ),
        md("## Project Checks"),
        code(
            "def _run_project_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: cleaned is defined\n"
            "    try:\n"
            "        assert 'cleaned' in globals(), \\\n"
            "            \"'cleaned' not defined — complete all steps and store result as 'cleaned'\"\n"
            "        assert isinstance(cleaned, pd.DataFrame)\n"
            "        passed += 1; print('\\u2705 Check 1: cleaned DataFrame defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: no nulls in cleaned\n"
            "    try:\n"
            "        null_total = cleaned.isnull().sum().sum()\n"
            "        assert null_total == 0, \\\n"
            "            f'{null_total} null values remain in cleaned'\n"
            "        passed += 1; print('\\u2705 Check 2: no null values')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: no leading/trailing whitespace in string columns\n"
            "    try:\n"
            "        str_cols = cleaned.select_dtypes(include='object').columns\n"
            "        for col in str_cols:\n"
            "            vals = cleaned[col].dropna()\n"
            "            has_ws = vals.str.startswith(' ') | vals.str.endswith(' ')\n"
            "            assert not has_ws.any(), \\\n"
            "                f'column {col!r} still has whitespace'\n"
            "        passed += 1; print('\\u2705 Check 3: no whitespace in string columns')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: no duplicate rows\n"
            "    try:\n"
            "        assert not cleaned.duplicated().any(), \\\n"
            "            'duplicate rows still present'\n"
            "        passed += 1; print(f'\\u2705 Check 4: no duplicate rows ({len(cleaned)} rows remain)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: fewer rows than raw (cleaning removed rows)\n"
            "    try:\n"
            "        assert len(cleaned) < len(raw), \\\n"
            "            f'cleaned has same row count as raw ({len(raw)}) — dedup did not run'\n"
            "        assert len(cleaned) > 0, 'cleaned is empty'\n"
            "        passed += 1; print(f'\\u2705 Check 5: {len(raw)} raw rows → {len(cleaned)} clean rows')\n"
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
            "- Add a `clean_dataframe` call at the end and compare its output to your step-by-step result\n"
            "- Handle the inconsistent casing in `region` — 'EAST' vs 'East' — using "
            "`clean_string_column`; what effect does it have on `deduplicate`?\n"
            "- Try `strategy='mean'` vs `strategy='median'` for the null fill — "
            "which gives a more realistic replacement for `quantity`?\n"
            "- Export `cleaned` to CSV with `cleaned.to_csv('cleaned_sales.csv', index=False)`\n"
            "- On Day 38 you will run a full EDA on this dataset — save `cleaned` for then"
        ),
    ]


# ---------------------------------------------------------------------------
# Solution notebook
# ---------------------------------------------------------------------------

def solution_nb():
    global _cid; _cid = 600
    all_code = ALL_IMPLS + "\n\n\n" + CLEAN_DATAFRAME_IMPL
    return [
        md(
            "# Day 037 Solution — Data Cleaning\n\n"
            "Full cleaning pipeline: type coercion → string normalisation → "
            "null handling → deduplication. All data defined inline for headless execution."
        ),
        code(
            "import warnings\n"
            "warnings.filterwarnings('ignore')\n"
            "import io\n"
            "import pandas as pd\n"
            "\n"
            + all_code
        ),
        md("## Step 1 — Load the Messy Dataset"),
        code(
            "MESSY_CSV = (\n"
            "    'order_id,product,price,quantity,region\\n'\n"
            "    '1, Widget ,25.0,10, North\\n'\n"
            "    '2, Gadget ,bad_price,,South\\n'\n"
            "    '3,Widget,25.0,20,North\\n'\n"
            "    '4, Widget ,25.0,20, North\\n'\n"
            "    '5,Doohickey,8.0,50,EAST\\n'\n"
            "    '5,Doohickey,8.0,50,EAST\\n'\n"
            "    '6,Thingamajig,200.0,8,West'\n"
            ")\n"
            "raw = pd.read_csv(io.StringIO(MESSY_CSV))\n"
            "print(f'Raw shape: {raw.shape}')\n"
            "print(f'Null counts:\\n{raw.isnull().sum()}')\n"
            "print(f'\\nraw dtypes:\\n{raw.dtypes}')\n"
            "\n"
            "assert raw.shape == (7, 5)\n"
            "assert raw.isnull().sum().sum() > 0"
        ),
        md("## Step 2 — Coerce Numeric Columns"),
        code(
            "df = coerce_numeric_columns(raw, ['price'])\n"
            "print(f'price dtype after coerce: {df[\"price\"].dtype}')\n"
            "print(f'Nulls in price: {df[\"price\"].isnull().sum()}')\n"
            "\n"
            "assert pd.api.types.is_numeric_dtype(df['price'])\n"
            "assert df['price'].isnull().sum() == 1"
        ),
        md("## Step 3 — Clean String Columns"),
        code(
            "df = clean_string_column(df, 'product')\n"
            "df = clean_string_column(df, 'region')\n"
            "print('Products:', df['product'].unique().tolist())\n"
            "print('Regions :', df['region'].unique().tolist())\n"
            "\n"
            "assert 'widget' in df['product'].values\n"
            "assert not any(v.startswith(' ') for v in df['product'].dropna())\n"
            "assert 'north' in df['region'].values"
        ),
        md("## Step 4 — Fill Null Values"),
        code(
            "df = drop_or_fill_nulls(df, strategy='median')\n"
            "null_count = df.isnull().sum().sum()\n"
            "print(f'Nulls after fill: {null_count}')\n"
            "print(df[['product', 'price', 'quantity', 'region']].to_string())\n"
            "\n"
            "assert null_count == 0"
        ),
        md("## Step 5 — Deduplicate"),
        code(
            "cleaned = deduplicate(df)\n"
            "print(f'\\nShape after dedup: {cleaned.shape}')\n"
            "print(cleaned.to_string())\n"
            "\n"
            "assert len(cleaned) < len(raw)\n"
            "assert not cleaned.duplicated().any()\n"
            "assert list(cleaned.index) == list(range(len(cleaned)))"
        ),
        md("## Step 6 — One-Call Pipeline (clean_dataframe)"),
        code(
            "# Same dataset, same result in one call\n"
            "raw2 = pd.read_csv(io.StringIO(MESSY_CSV))\n"
            "raw2 = coerce_numeric_columns(raw2, ['price'])\n"
            "auto_cleaned = clean_dataframe(raw2)\n"
            "print(f'clean_dataframe result shape: {auto_cleaned.shape}')\n"
            "print(f'Nulls: {auto_cleaned.isnull().sum().sum()}')\n"
            "print(f'Dupes: {auto_cleaned.duplicated().sum()}')\n"
            "\n"
            "assert auto_cleaned.isnull().sum().sum() == 0\n"
            "assert not auto_cleaned.duplicated().any()\n"
            "\n"
            "print('\\nData Cleaning complete!')"
        ),
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Generating Day 037 notebooks...")
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
