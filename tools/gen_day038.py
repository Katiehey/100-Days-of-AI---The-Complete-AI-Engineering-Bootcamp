#!/usr/bin/env python3
"""Generate all Day 038 notebooks: exercises 1-5, project, solution."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAY_DIR = ROOT / "03_data_analysis" / "day_038"

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
# Shared setup — sample DataFrame used across all exercises
# ---------------------------------------------------------------------------

SETUP_CODE = """\
import warnings
warnings.filterwarnings('ignore')
import pandas as pd

# SALES_DF: 8 rows, 6 columns
# product:  Widget×4, Gadget×2, Doohickey×2
# revenue   = price × quantity  (pre-computed)
SALES_DF = pd.DataFrame({
    'product':  ['Widget', 'Widget', 'Widget', 'Widget',
                 'Gadget', 'Gadget', 'Doohickey', 'Doohickey'],
    'category': ['Elec', 'Elec', 'Elec', 'Elec',
                 'Elec', 'Elec', 'Access', 'Access'],
    'region':   ['North', 'South', 'East', 'West',
                 'North', 'East', 'North', 'South'],
    'price':    [25.0, 25.0, 25.0, 25.0, 150.0, 150.0, 8.0, 8.0],
    'quantity': [10, 5, 4, 6, 3, 7, 50, 15],
    'revenue':  [250.0, 125.0, 100.0, 150.0, 450.0, 1050.0, 400.0, 120.0],
})"""

# ---------------------------------------------------------------------------
# Implementations
# ---------------------------------------------------------------------------

DISTRIBUTION_SUMMARY_IMPL = """\
import pandas as pd

def distribution_summary(df: pd.DataFrame, col: str) -> dict:
    s = df[col]
    if pd.api.types.is_numeric_dtype(s):
        return {
            'count':      int(s.count()),
            'mean':       round(float(s.mean()), 4),
            'std':        round(float(s.std()), 4),
            'min':        float(s.min()),
            'q25':        float(s.quantile(0.25)),
            'median':     float(s.quantile(0.50)),
            'q75':        float(s.quantile(0.75)),
            'max':        float(s.max()),
            'null_count': int(s.isnull().sum()),
        }
    counts = s.value_counts()
    return {
        'count':      int(s.count()),
        'unique':     int(s.nunique()),
        'top':        str(counts.index[0]) if len(counts) else None,
        'top_freq':   int(counts.iloc[0])  if len(counts) else 0,
        'null_count': int(s.isnull().sum()),
    }"""

TOP_GROUPS_IMPL = """\
import pandas as pd

def top_groups(df: pd.DataFrame, group_col: str, value_col: str,
               n: int = 5) -> pd.DataFrame:
    return (
        df.groupby(group_col)[value_col]
        .agg(total='sum', mean='mean', count='count')
        .reset_index()
        .nlargest(n, 'total')
        .reset_index(drop=True)
    )"""

CORRELATION_SUMMARY_IMPL = """\
import pandas as pd

def correlation_summary(df: pd.DataFrame, target_col: str) -> pd.DataFrame:
    corr   = df.select_dtypes(include='number').corr()[target_col].drop(target_col)
    result = pd.DataFrame({'feature': corr.index.tolist(), 'correlation': corr.values})
    result['_abs'] = result['correlation'].abs()
    result = result.sort_values('_abs', ascending=False).drop(columns='_abs')
    return result.reset_index(drop=True)"""

PIVOT_SUMMARY_IMPL = """\
import pandas as pd

def pivot_summary(df: pd.DataFrame, index: str, columns: str,
                  values: str, aggfunc: str = 'mean') -> pd.DataFrame:
    piv = pd.pivot_table(
        df, values=values, index=index, columns=columns,
        aggfunc=aggfunc, fill_value=0,
    )
    piv.columns.name = None
    return piv.reset_index()"""

EDA_REPORT_IMPL = """\
import pandas as pd

def eda_report(df: pd.DataFrame) -> dict:
    num_cols = df.select_dtypes(include='number').columns.tolist()
    cat_cols = df.select_dtypes(include='object').columns.tolist()
    return {
        'shape':           df.shape,
        'null_counts':     df.isnull().sum().to_dict(),
        'numeric_summary': df[num_cols].describe().round(2).to_dict() if num_cols else {},
        'category_counts': {col: df[col].value_counts().to_dict() for col in cat_cols},
        'correlations':    df[num_cols].corr().round(4).to_dict() if len(num_cols) > 1 else {},
    }"""

ALL_IMPLS = "\n\n\n".join([
    DISTRIBUTION_SUMMARY_IMPL,
    TOP_GROUPS_IMPL,
    CORRELATION_SUMMARY_IMPL,
    PIVOT_SUMMARY_IMPL,
])


# ---------------------------------------------------------------------------
# Exercise 01 — distribution_summary
# ---------------------------------------------------------------------------

def ex01():
    global _cid; _cid = 0
    return [
        md(
            "# Day 038 — Exercise 1: distribution_summary\n\n"
            "**What you'll build:** `distribution_summary(df, col) -> dict` — "
            "return a profile of one column: for numeric columns, compute quantiles "
            "and descriptive stats; for string columns, compute unique count, "
            "top value, and frequency.\n\n"
            "**Why it matters:** The first step of every EDA is asking 'what does this "
            "column look like?' Automating the answer into a structured dict makes it "
            "loggable, testable, and composable into a full report."
        ),
        code(SETUP_CODE),
        md("## Your Implementation"),
        code(
            "def distribution_summary(df: pd.DataFrame, col: str) -> dict:\n"
            '    """\n'
            "    Profile one column.\n\n"
            "    Numeric columns → {count, mean, std, min, q25, median, q75, max, null_count}\n"
            "    String columns  → {count, unique, top, top_freq, null_count}\n"
            '    """\n'
            "    s = df[col]\n"
            "    if pd.api.types.is_numeric_dtype(s):\n"
            "        # TODO: return dict with count, mean, std, min,\n"
            "        #       q25 (quantile 0.25), median (quantile 0.50),\n"
            "        #       q75 (quantile 0.75), max, null_count\n"
            "        pass\n"
            "    # TODO: counts = s.value_counts()\n"
            "    # TODO: return dict with count, unique (nunique()),\n"
            "    #       top (most frequent value), top_freq, null_count\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: defined, returns dict\n"
            "    try:\n"
            "        assert 'distribution_summary' in globals()\n"
            "        result = distribution_summary(SALES_DF, 'revenue')\n"
            "        assert isinstance(result, dict), \\\n"
            "            f'expected dict, got {type(result).__name__}'\n"
            "        passed += 1; print('\\u2705 Check 1: returns a dict')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: numeric column has all required keys\n"
            "    try:\n"
            "        r = distribution_summary(SALES_DF, 'revenue')\n"
            "        for k in ('count', 'mean', 'std', 'min', 'q25', 'median', 'q75', 'max', 'null_count'):\n"
            "            assert k in r, f'numeric result missing key: {k}'\n"
            "        passed += 1; print('\\u2705 Check 2: numeric result has all 9 keys')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: numeric values are correct\n"
            "    # revenue: [250,125,100,150,450,1050,400,120] → count=8, min=100, max=1050\n"
            "    try:\n"
            "        r = distribution_summary(SALES_DF, 'revenue')\n"
            "        assert r['count']      == 8,    f'count={r[\"count\"]}, expected 8'\n"
            "        assert r['min']        == 100.0, f'min={r[\"min\"]}, expected 100'\n"
            "        assert r['max']        == 1050.0, f'max={r[\"max\"]}, expected 1050'\n"
            "        assert r['null_count'] == 0,    f'null_count={r[\"null_count\"]}, expected 0'\n"
            "        passed += 1; print('\\u2705 Check 3: count=8, min=100, max=1050, null_count=0')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: quantile ordering q25 <= median <= q75\n"
            "    try:\n"
            "        r = distribution_summary(SALES_DF, 'revenue')\n"
            "        assert r['q25'] <= r['median'] <= r['q75'], \\\n"
            "            f'quantile order violated: q25={r[\"q25\"]}, median={r[\"median\"]}, q75={r[\"q75\"]}'\n"
            "        passed += 1; print(f'\\u2705 Check 4: q25={r[\"q25\"]:.1f} <= median={r[\"median\"]:.1f} <= q75={r[\"q75\"]:.1f}')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: categorical column returns correct keys + values\n"
            "    # product: Widget×4, Gadget×2, Doohickey×2 → unique=3, top='Widget'\n"
            "    try:\n"
            "        r = distribution_summary(SALES_DF, 'product')\n"
            "        for k in ('count', 'unique', 'top', 'top_freq', 'null_count'):\n"
            "            assert k in r, f'categorical result missing key: {k}'\n"
            "        assert r['count']    == 8,       f'count={r[\"count\"]}'\n"
            "        assert r['unique']   == 3,       f'unique={r[\"unique\"]}, expected 3'\n"
            "        assert r['top']      == 'Widget', f'top={r[\"top\"]!r}, expected Widget'\n"
            "        assert r['top_freq'] == 4,       f'top_freq={r[\"top_freq\"]}, expected 4'\n"
            "        passed += 1; print(\"\\u2705 Check 5: categorical: unique=3, top='Widget', top_freq=4\")\n"
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
            + DISTRIBUTION_SUMMARY_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 02 — top_groups
# ---------------------------------------------------------------------------

def ex02():
    global _cid; _cid = 100
    return [
        md(
            "# Day 038 — Exercise 2: top_groups\n\n"
            "**What you'll build:** `top_groups(df, group_col, value_col, n=5) -> pd.DataFrame` — "
            "group rows by `group_col`, aggregate `value_col` into `total`, `mean`, and `count`, "
            "then return the top `n` groups by total.\n\n"
            "**Why it matters:** 'Which product drives the most revenue?' and 'Which region "
            "has the highest order count?' are the two most common EDA questions. `top_groups` "
            "answers both in one call. The `nlargest` method is cleaner and faster than "
            "`sort_values(...).head(n)`."
        ),
        code(SETUP_CODE),
        md("## Your Implementation"),
        code(
            "def top_groups(df: pd.DataFrame, group_col: str, value_col: str,\n"
            "               n: int = 5) -> pd.DataFrame:\n"
            '    """\n'
            "    Group by group_col and aggregate value_col, returning top n by total.\n\n"
            "    Returns DataFrame with columns: [group_col, 'total', 'mean', 'count']\n"
            "    sorted by 'total' descending, index reset to 0, 1, ..., n-1.\n"
            '    """\n'
            "    # TODO: chain groupby → agg(total='sum', mean='mean', count='count')\n"
            "    #       → reset_index() → nlargest(n, 'total') → reset_index(drop=True)\n"
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
            "        assert 'top_groups' in globals()\n"
            "        result = top_groups(SALES_DF, 'product', 'revenue')\n"
            "        assert isinstance(result, pd.DataFrame), \\\n"
            "            f'expected DataFrame, got {type(result).__name__}'\n"
            "        passed += 1; print('\\u2705 Check 1: returns a DataFrame')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: correct columns\n"
            "    try:\n"
            "        result = top_groups(SALES_DF, 'product', 'revenue')\n"
            "        for col in ('product', 'total', 'mean', 'count'):\n"
            "            assert col in result.columns, f'missing column: {col!r}'\n"
            "        passed += 1; print('\\u2705 Check 2: columns include product, total, mean, count')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: correct totals — Gadget=1500, Doohickey=520, Widget=625\n"
            "    try:\n"
            "        result = top_groups(SALES_DF, 'product', 'revenue')\n"
            "        totals = dict(zip(result['product'], result['total']))\n"
            "        assert totals.get('Gadget')    == 1500.0, f\"Gadget total={totals.get('Gadget')}\"\n"
            "        assert totals.get('Widget')    == 625.0,  f\"Widget total={totals.get('Widget')}\"\n"
            "        assert totals.get('Doohickey') == 520.0,  f\"Doohickey total={totals.get('Doohickey')}\"\n"
            "        passed += 1; print('\\u2705 Check 3: Gadget=1500, Widget=625, Doohickey=520')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: first row is Gadget (highest total)\n"
            "    try:\n"
            "        result = top_groups(SALES_DF, 'product', 'revenue')\n"
            "        assert result.iloc[0]['product'] == 'Gadget', \\\n"
            "            f\"first row should be Gadget, got {result.iloc[0]['product']!r}\"\n"
            "        assert list(result.index) == list(range(len(result))), \\\n"
            "            f'index not reset: {list(result.index)}'\n"
            "        passed += 1; print('\\u2705 Check 4: sorted by total desc, Gadget first')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: n parameter limits the result\n"
            "    try:\n"
            "        top1 = top_groups(SALES_DF, 'product', 'revenue', n=1)\n"
            "        assert len(top1) == 1, f'n=1 should give 1 row, got {len(top1)}'\n"
            "        assert top1.iloc[0]['product'] == 'Gadget'\n"
            "        top2 = top_groups(SALES_DF, 'product', 'revenue', n=2)\n"
            "        assert len(top2) == 2, f'n=2 should give 2 rows, got {len(top2)}'\n"
            "        passed += 1; print('\\u2705 Check 5: n parameter limits rows correctly')\n"
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
            + TOP_GROUPS_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 03 — correlation_summary
# ---------------------------------------------------------------------------

def ex03():
    global _cid; _cid = 200
    return [
        md(
            "# Day 038 — Exercise 3: correlation_summary\n\n"
            "**What you'll build:** `correlation_summary(df, target_col) -> pd.DataFrame` — "
            "compute the Pearson correlation of every numeric column against `target_col`, "
            "return a DataFrame with `feature` and `correlation` columns sorted by "
            "absolute correlation descending.\n\n"
            "**Why it matters:** Correlation reveals which features move together with "
            "your target — the starting point of every feature-selection workflow and the "
            "fastest way to find surprising (or suspicious) relationships in data."
        ),
        code(SETUP_CODE + "\n\n" + DISTRIBUTION_SUMMARY_IMPL + "\n\n" + TOP_GROUPS_IMPL),
        md("## Your Implementation"),
        code(
            "def correlation_summary(df: pd.DataFrame, target_col: str) -> pd.DataFrame:\n"
            '    """\n'
            "    Correlate all numeric columns with target_col.\n\n"
            "    Returns DataFrame with columns ['feature', 'correlation'],\n"
            "    sorted by absolute correlation descending, index reset.\n"
            "    target_col itself is excluded from the results.\n"
            '    """\n'
            "    # TODO: corr = df.select_dtypes(include='number').corr()[target_col].drop(target_col)\n"
            "    # TODO: result = pd.DataFrame({'feature': corr.index.tolist(), 'correlation': corr.values})\n"
            "    # TODO: add a temporary '_abs' column, sort descending, drop '_abs'\n"
            "    # TODO: return result.reset_index(drop=True)\n"
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
            "        assert 'correlation_summary' in globals()\n"
            "        result = correlation_summary(SALES_DF, 'revenue')\n"
            "        assert isinstance(result, pd.DataFrame), \\\n"
            "            f'expected DataFrame, got {type(result).__name__}'\n"
            "        passed += 1; print('\\u2705 Check 1: returns a DataFrame')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: correct columns ['feature', 'correlation']\n"
            "    try:\n"
            "        result = correlation_summary(SALES_DF, 'revenue')\n"
            "        assert list(result.columns) == ['feature', 'correlation'], \\\n"
            "            f'columns={list(result.columns)}, expected [feature, correlation]'\n"
            "        passed += 1; print(\"\\u2705 Check 2: columns=['feature', 'correlation']\")\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: target_col not in features\n"
            "    try:\n"
            "        result = correlation_summary(SALES_DF, 'revenue')\n"
            "        assert 'revenue' not in result['feature'].values, \\\n"
            "            \"'revenue' should not appear in feature column (it's the target)\"\n"
            "        # numeric cols: price, quantity, revenue → after drop(revenue) → price, quantity\n"
            "        assert len(result) == 2, \\\n"
            "            f'expected 2 features (price, quantity), got {len(result)}'\n"
            "        passed += 1; print('\\u2705 Check 3: revenue excluded; 2 features returned')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: all correlation values are in [-1, 1]\n"
            "    try:\n"
            "        result = correlation_summary(SALES_DF, 'revenue')\n"
            "        for _, row in result.iterrows():\n"
            "            c = row['correlation']\n"
            "            assert -1.0 <= c <= 1.0, \\\n"
            "                f'correlation {c} for {row[\"feature\"]!r} out of [-1, 1]'\n"
            "        passed += 1; print('\\u2705 Check 4: all correlations in [-1.0, 1.0]')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: sorted by absolute value descending\n"
            "    try:\n"
            "        result = correlation_summary(SALES_DF, 'revenue')\n"
            "        abs_vals = result['correlation'].abs().tolist()\n"
            "        assert abs_vals == sorted(abs_vals, reverse=True), \\\n"
            "            f'not sorted by abs correlation: {abs_vals}'\n"
            "        passed += 1; print(f'\\u2705 Check 5: sorted by |correlation| desc: {[round(v,3) for v in abs_vals]}')\n"
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
            + CORRELATION_SUMMARY_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 04 — pivot_summary
# ---------------------------------------------------------------------------

def ex04():
    global _cid; _cid = 300
    return [
        md(
            "# Day 038 — Exercise 4: pivot_summary\n\n"
            "**What you'll build:** `pivot_summary(df, index, columns, values, aggfunc='mean') -> pd.DataFrame` — "
            "wrap `pd.pivot_table` to produce a clean cross-tabulation with no NaN values "
            "(`fill_value=0`) and no column axis name artefact.\n\n"
            "**Why it matters:** Pivot tables turn a long-format DataFrame into a readable "
            "matrix — product × region revenue, campaign × channel clicks, user × feature "
            "usage. They are the standard summary a stakeholder wants to see."
        ),
        code(
            SETUP_CODE + "\n\n"
            + DISTRIBUTION_SUMMARY_IMPL + "\n\n"
            + TOP_GROUPS_IMPL + "\n\n"
            + CORRELATION_SUMMARY_IMPL
        ),
        md("## Your Implementation"),
        code(
            "def pivot_summary(df: pd.DataFrame, index: str, columns: str,\n"
            "                  values: str, aggfunc: str = 'mean') -> pd.DataFrame:\n"
            '    """\n'
            "    Create a pivot table and return it as a plain DataFrame.\n\n"
            "    Args:\n"
            "        index   — column whose values become row labels\n"
            "        columns — column whose values become column headers\n"
            "        values  — column to aggregate\n"
            "        aggfunc — aggregation function string ('sum', 'mean', 'count')\n"
            "    fill_value=0 so missing combinations are 0, not NaN.\n"
            '    """\n'
            "    # TODO: piv = pd.pivot_table(df, values=values, index=index,\n"
            "    #                            columns=columns, aggfunc=aggfunc, fill_value=0)\n"
            "    # TODO: piv.columns.name = None  (clear the columns axis name)\n"
            "    # TODO: return piv.reset_index()\n"
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
            "        assert 'pivot_summary' in globals()\n"
            "        result = pivot_summary(SALES_DF, 'product', 'region', 'revenue', 'sum')\n"
            "        assert isinstance(result, pd.DataFrame), \\\n"
            "            f'expected DataFrame, got {type(result).__name__}'\n"
            "        passed += 1; print('\\u2705 Check 1: returns a DataFrame')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: index column present and region columns present\n"
            "    # regions in data: North, South, East, West\n"
            "    try:\n"
            "        result = pivot_summary(SALES_DF, 'product', 'region', 'revenue', 'sum')\n"
            "        assert 'product' in result.columns, \\\n"
            "            f\"'product' column missing; columns={list(result.columns)}\"\n"
            "        for reg in ('North', 'South', 'East', 'West'):\n"
            "            assert reg in result.columns, \\\n"
            "                f'{reg!r} column missing; columns={list(result.columns)}'\n"
            "        passed += 1; print('\\u2705 Check 2: product + all 4 region columns present')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: correct value for Widget-North (price=25, quantity=10 → revenue=250)\n"
            "    try:\n"
            "        result = pivot_summary(SALES_DF, 'product', 'region', 'revenue', 'sum')\n"
            "        widget_row = result[result['product'] == 'Widget'].iloc[0]\n"
            "        assert float(widget_row['North']) == 250.0, \\\n"
            "            f\"Widget-North should be 250, got {widget_row['North']}\"\n"
            "        assert float(widget_row['South']) == 125.0, \\\n"
            "            f\"Widget-South should be 125, got {widget_row['South']}\"\n"
            "        passed += 1; print('\\u2705 Check 3: Widget-North=250, Widget-South=125')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: fill_value=0 — no NaN in result (Gadget has no South/West data)\n"
            "    try:\n"
            "        result = pivot_summary(SALES_DF, 'product', 'region', 'revenue', 'sum')\n"
            "        null_total = result.isnull().sum().sum()\n"
            "        assert null_total == 0, \\\n"
            "            f'{null_total} NaN values — did you use fill_value=0?'\n"
            "        gadget_row  = result[result['product'] == 'Gadget'].iloc[0]\n"
            "        assert float(gadget_row['South']) == 0.0, \\\n"
            "            f'Gadget-South should be 0 (no data), got {gadget_row[\"South\"]}'\n"
            "        passed += 1; print('\\u2705 Check 4: no NaN; Gadget-South=0 (fill_value=0)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: aggfunc='count' gives row counts instead of sums\n"
            "    try:\n"
            "        cnt = pivot_summary(SALES_DF, 'product', 'region', 'revenue', 'count')\n"
            "        widget_row = cnt[cnt['product'] == 'Widget'].iloc[0]\n"
            "        # Widget has 1 row per region (North, South, East, West)\n"
            "        for reg in ('North', 'South', 'East', 'West'):\n"
            "            assert float(widget_row[reg]) == 1.0, \\\n"
            "                f'Widget-{reg} count should be 1, got {widget_row[reg]}'\n"
            "        passed += 1; print('\\u2705 Check 5: aggfunc=count gives per-cell row counts')\n"
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
            + PIVOT_SUMMARY_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 05 — eda_report
# ---------------------------------------------------------------------------

def ex05():
    global _cid; _cid = 400
    return [
        md(
            "# Day 038 — Exercise 5: eda_report\n\n"
            "**What you'll build:** `eda_report(df) -> dict` — a single-call EDA that returns "
            "shape, null counts, numeric describe-style statistics, category value counts, "
            "and a correlation matrix, all in one structured dict.\n\n"
            "**Why it matters:** In practice you need a quick snapshot of any new dataset "
            "in seconds. A report dict is loggable, serialisable to JSON, and can be "
            "diffed between runs to spot data drift."
        ),
        md("## Provided: All Four EDA Helpers"),
        code(ALL_IMPLS),
        code(SETUP_CODE),
        md("## Your Implementation"),
        code(
            "def eda_report(df: pd.DataFrame) -> dict:\n"
            '    """\n'
            "    Run a full EDA on df and return a structured dict.\n\n"
            "    Returns:\n"
            "        shape            — (rows, cols) tuple\n"
            "        null_counts      — {col: null_count} dict\n"
            "        numeric_summary  — {col: {stat: val}} from describe().round(2)\n"
            "        category_counts  — {col: {value: count}} from value_counts()\n"
            "        correlations     — {col: {col: pearson_r}} from corr().round(4)\n"
            '    """\n'
            "    num_cols = df.select_dtypes(include='number').columns.tolist()\n"
            "    cat_cols = df.select_dtypes(include='object').columns.tolist()\n"
            "    # TODO: return dict with shape, null_counts, numeric_summary,\n"
            "    #       category_counts, correlations\n"
            "    # Hint: df[num_cols].describe().round(2).to_dict() for numeric_summary\n"
            "    # Hint: {col: df[col].value_counts().to_dict() for col in cat_cols}\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: defined, returns dict\n"
            "    try:\n"
            "        assert 'eda_report' in globals()\n"
            "        result = eda_report(SALES_DF)\n"
            "        assert isinstance(result, dict), \\\n"
            "            f'expected dict, got {type(result).__name__}'\n"
            "        passed += 1; print('\\u2705 Check 1: returns a dict')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: all 5 top-level keys present\n"
            "    try:\n"
            "        result = eda_report(SALES_DF)\n"
            "        for k in ('shape', 'null_counts', 'numeric_summary',\n"
            "                  'category_counts', 'correlations'):\n"
            "            assert k in result, f'missing key: {k!r}'\n"
            "        passed += 1; print('\\u2705 Check 2: all 5 keys present')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: shape matches df.shape\n"
            "    try:\n"
            "        result = eda_report(SALES_DF)\n"
            "        assert result['shape'] == SALES_DF.shape, \\\n"
            "            f'shape={result[\"shape\"]}, expected {SALES_DF.shape}'\n"
            "        passed += 1; print(f'\\u2705 Check 3: shape={result[\"shape\"]}')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: numeric_summary contains describe stats for numeric cols\n"
            "    try:\n"
            "        result = eda_report(SALES_DF)\n"
            "        ns = result['numeric_summary']\n"
            "        assert isinstance(ns, dict), 'numeric_summary should be a dict'\n"
            "        for col in ('price', 'quantity', 'revenue'):\n"
            "            assert col in ns, f'numeric_summary missing column: {col}'\n"
            "        # describe() returns count, mean, std, min, 25%, 50%, 75%, max\n"
            "        assert 'mean' in ns['revenue'], \\\n"
            "            f'numeric_summary[revenue] missing mean; keys={list(ns[\"revenue\"].keys())}'\n"
            "        passed += 1; print('\\u2705 Check 4: numeric_summary has price/quantity/revenue with stats')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: category_counts has entries for string columns\n"
            "    try:\n"
            "        result = eda_report(SALES_DF)\n"
            "        cc = result['category_counts']\n"
            "        assert isinstance(cc, dict), 'category_counts should be a dict'\n"
            "        for col in ('product', 'category', 'region'):\n"
            "            assert col in cc, f'category_counts missing column: {col}'\n"
            "        assert cc['product']['Widget'] == 4, \\\n"
            "            f'Widget count={cc[\"product\"][\"Widget\"]}, expected 4'\n"
            "        passed += 1; print(\"\\u2705 Check 5: category_counts has product/category/region; Widget=4\")\n"
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
            + EDA_REPORT_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Project notebook
# ---------------------------------------------------------------------------

def project_nb():
    global _cid; _cid = 500
    all_code = ALL_IMPLS + "\n\n\n" + EDA_REPORT_IMPL
    return [
        md(
            "# Day 038 Project: EDA Report on a Retail Dataset\n\n"
            "## What You're Building\n\n"
            "A structured EDA on a retail sales dataset: distribution analysis, "
            "top-group ranking, correlation, pivot table, and a full report dict.\n\n"
            "**Deliverable:** You run every cell top-to-bottom. The final checks pass. "
            "You have a `report` dict and have answered three analysis questions with "
            "printed answers.\n\n"
            "## Project Requirements\n\n"
            "1. Load `RETAIL_CSV` (provided) into a DataFrame\n"
            "2. Call `distribution_summary` on the `revenue` column\n"
            "3. Call `top_groups` for product revenue — find the top 3 products\n"
            "4. Call `correlation_summary` targeting `revenue`\n"
            "5. Call `pivot_summary` for product × region, values=revenue, aggfunc='sum'\n"
            "6. Call `eda_report` and store result as `report`\n"
            "7. Verify with `_run_project_checks()`"
        ),
        code(
            "import warnings\n"
            "warnings.filterwarnings('ignore')\n"
            "import io\n"
            "import pandas as pd\n"
            "\n"
            + all_code + "\n\n\n"
            "RETAIL_CSV = (\n"
            "    'order_id,product,category,region,price,quantity\\n'\n"
            "    '1,Widget,Electronics,North,25.0,10\\n'\n"
            "    '2,Gadget,Electronics,South,150.0,3\\n'\n"
            "    '3,Widget,Electronics,South,25.0,5\\n'\n"
            "    '4,Doohickey,Accessories,East,8.0,50\\n'\n"
            "    '5,Gadget,Electronics,East,150.0,7\\n'\n"
            "    '6,Widget,Electronics,East,25.0,4\\n'\n"
            "    '7,Doohickey,Accessories,North,8.0,20\\n'\n"
            "    '8,Gadget,Electronics,North,150.0,2\\n'\n"
            "    '9,Widget,Electronics,West,25.0,6\\n'\n"
            "    '10,Doohickey,Accessories,South,8.0,15\\n'\n"
            "    '11,Thingamajig,Accessories,North,200.0,1\\n'\n"
            "    '12,Thingamajig,Accessories,East,200.0,4'\n"
            ")\n"
            "df = pd.read_csv(io.StringIO(RETAIL_CSV))\n"
            "df['revenue'] = df['price'] * df['quantity']\n"
            "print(f'Loaded {len(df)} rows × {len(df.columns)} columns')\n"
            "print(df.dtypes)"
        ),
        md("## Your EDA"),
        code(
            "# Step 1: Distribution of revenue\n"
            "# TODO: rev_dist = distribution_summary(df, 'revenue')\n"
            "# TODO: print(rev_dist)\n"
            "\n"
            "# Step 2: Top 3 products by revenue\n"
            "# TODO: top3 = top_groups(df, 'product', 'revenue', n=3)\n"
            "# TODO: print('\\nTop 3 products:')\n"
            "# TODO: print(top3)\n"
            "\n"
            "# Step 3: Correlations with revenue\n"
            "# TODO: corr = correlation_summary(df, 'revenue')\n"
            "# TODO: print('\\nCorrelations with revenue:')\n"
            "# TODO: print(corr)\n"
            "\n"
            "# Step 4: Pivot table — product × region revenue\n"
            "# TODO: piv = pivot_summary(df, 'product', 'region', 'revenue', 'sum')\n"
            "# TODO: print('\\nRevenue pivot (product × region):')\n"
            "# TODO: print(piv)\n"
            "\n"
            "# Step 5: Full EDA report\n"
            "# TODO: report = eda_report(df)\n"
            "# TODO: print(f'\\nShape: {report[\"shape\"]}')"
        ),
        md("## Project Checks"),
        code(
            "def _run_project_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: df has revenue column\n"
            "    try:\n"
            "        assert 'df' in globals() and 'revenue' in df.columns, \\\n"
            "            \"'revenue' column missing — compute df['revenue'] = df['price'] * df['quantity']\"\n"
            "        passed += 1; print(f'\\u2705 Check 1: df loaded with revenue ({len(df)} rows)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "\n"
            "    # Check 2: top3 is defined and Gadget is the top revenue product\n"
            "    try:\n"
            "        assert 'top3' in globals(), 'top3 not defined'\n"
            "        assert len(top3) == 3, f'top3 should have 3 rows, got {len(top3)}'\n"
            "        assert top3.iloc[0]['product'] == 'Gadget', \\\n"
            "            f'top product should be Gadget (total=1800), got {top3.iloc[0][\"product\"]!r}'\n"
            "        passed += 1; print(f'\\u2705 Check 2: top3 correct; top product=Gadget (1800 revenue)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: corr defined with correct structure\n"
            "    try:\n"
            "        assert 'corr' in globals(), 'corr not defined'\n"
            "        assert list(corr.columns) == ['feature', 'correlation'], \\\n"
            "            f'corr columns={list(corr.columns)}'\n"
            "        assert 'revenue' not in corr['feature'].values, \\\n"
            "            'revenue should not appear in feature column'\n"
            "        passed += 1; print('\\u2705 Check 3: corr has feature/correlation columns; revenue excluded')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: piv is a pivot table DataFrame\n"
            "    try:\n"
            "        assert 'piv' in globals(), 'piv not defined'\n"
            "        assert 'product' in piv.columns, \"'product' column missing from pivot\"\n"
            "        assert piv.isnull().sum().sum() == 0, 'pivot has NaN — use fill_value=0'\n"
            "        passed += 1; print('\\u2705 Check 4: pivot table has no NaN')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: report dict has all required keys\n"
            "    try:\n"
            "        assert 'report' in globals(), 'report not defined'\n"
            "        for k in ('shape', 'null_counts', 'numeric_summary', 'category_counts', 'correlations'):\n"
            "            assert k in report, f'report missing key: {k!r}'\n"
            "        assert report['shape'] == df.shape, \\\n"
            "            f'shape mismatch: {report[\"shape\"]} vs {df.shape}'\n"
            "        passed += 1; print(f'\\u2705 Check 5: report complete; shape={report[\"shape\"]}')\n"
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
            "- Loop `distribution_summary` over every column and print a formatted table\n"
            "- Try `aggfunc='count'` in `pivot_summary` to see how many orders per cell\n"
            "- Use `pd.crosstab(df['product'], df['region'])` as a shortcut for counts\n"
            "- Serialise `report` to JSON with `json.dumps(report, default=str, indent=2)` "
            "and save to a file — `default=str` handles tuples and non-JSON-native types\n"
            "- On Day 39 you will visualise this data — keep `df` handy"
        ),
    ]


# ---------------------------------------------------------------------------
# Solution notebook
# ---------------------------------------------------------------------------

def solution_nb():
    global _cid; _cid = 600
    all_code = ALL_IMPLS + "\n\n\n" + EDA_REPORT_IMPL
    return [
        md(
            "# Day 038 Solution — Exploratory Data Analysis\n\n"
            "Distribution profiling, top-group ranking, correlation, "
            "pivot tables, and a full EDA report dict. All data defined inline."
        ),
        code(
            "import warnings\n"
            "warnings.filterwarnings('ignore')\n"
            "import io\n"
            "import pandas as pd\n"
            "\n"
            + all_code
        ),
        md("## Step 1 — Load & Inspect"),
        code(
            "RETAIL_CSV = (\n"
            "    'order_id,product,category,region,price,quantity\\n'\n"
            "    '1,Widget,Electronics,North,25.0,10\\n'\n"
            "    '2,Gadget,Electronics,South,150.0,3\\n'\n"
            "    '3,Widget,Electronics,South,25.0,5\\n'\n"
            "    '4,Doohickey,Accessories,East,8.0,50\\n'\n"
            "    '5,Gadget,Electronics,East,150.0,7\\n'\n"
            "    '6,Widget,Electronics,East,25.0,4\\n'\n"
            "    '7,Doohickey,Accessories,North,8.0,20\\n'\n"
            "    '8,Gadget,Electronics,North,150.0,2\\n'\n"
            "    '9,Widget,Electronics,West,25.0,6\\n'\n"
            "    '10,Doohickey,Accessories,South,8.0,15\\n'\n"
            "    '11,Thingamajig,Accessories,North,200.0,1\\n'\n"
            "    '12,Thingamajig,Accessories,East,200.0,4'\n"
            ")\n"
            "df = pd.read_csv(io.StringIO(RETAIL_CSV))\n"
            "df['revenue'] = df['price'] * df['quantity']\n"
            "print(f'Shape: {df.shape}')\n"
            "print(f'Columns: {df.columns.tolist()}')\n"
            "print(df.head())\n"
            "\n"
            "assert df.shape == (12, 7)\n"
            "assert 'revenue' in df.columns"
        ),
        md("## Step 2 — Distribution Summary"),
        code(
            "# Numeric column\n"
            "rev_dist = distribution_summary(df, 'revenue')\n"
            "print('Revenue distribution:')\n"
            "for k, v in rev_dist.items():\n"
            "    print(f'  {k:12s}: {v}')\n"
            "\n"
            "assert rev_dist['count'] == 12\n"
            "assert rev_dist['null_count'] == 0\n"
            "assert rev_dist['q25'] <= rev_dist['median'] <= rev_dist['q75']\n"
            "\n"
            "# Categorical column\n"
            "prod_dist = distribution_summary(df, 'product')\n"
            "print(f'\\nProduct distribution: unique={prod_dist[\"unique\"]}, top={prod_dist[\"top\"]!r}')\n"
            "\n"
            "assert prod_dist['unique'] == 4\n"
            "assert prod_dist['top'] == 'Widget'  # Widget appears 4 times (most frequent)"
        ),
        md("## Step 3 — Top Groups"),
        code(
            "top3 = top_groups(df, 'product', 'revenue', n=3)\n"
            "print('Top 3 products by revenue:')\n"
            "print(top3.to_string(index=False))\n"
            "\n"
            "assert len(top3) == 3\n"
            "assert top3.iloc[0]['product'] == 'Gadget'  # Gadget total=1800 (top by revenue)\n"
            "assert top3.iloc[0]['total'] == 1800.0\n"
            "\n"
            "# Top regions\n"
            "top_regions = top_groups(df, 'region', 'revenue', n=4)\n"
            "print('\\nRevenue by region:')\n"
            "print(top_regions.to_string(index=False))"
        ),
        md("## Step 4 — Correlation"),
        code(
            "corr = correlation_summary(df, 'revenue')\n"
            "print('Correlations with revenue:')\n"
            "print(corr.to_string(index=False))\n"
            "\n"
            "assert list(corr.columns) == ['feature', 'correlation']\n"
            "assert 'revenue' not in corr['feature'].values\n"
            "abs_vals = corr['correlation'].abs().tolist()\n"
            "assert abs_vals == sorted(abs_vals, reverse=True)"
        ),
        md("## Step 5 — Pivot Table"),
        code(
            "piv = pivot_summary(df, 'product', 'region', 'revenue', 'sum')\n"
            "print('Revenue by product × region:')\n"
            "print(piv.to_string(index=False))\n"
            "\n"
            "assert 'product' in piv.columns\n"
            "assert piv.isnull().sum().sum() == 0\n"
            "\n"
            "# Cross-tabulation shortcut (counts)\n"
            "print('\\nOrder count by product × region:')\n"
            "print(pd.crosstab(df['product'], df['region']))"
        ),
        md("## Step 6 — Full EDA Report"),
        code(
            "report = eda_report(df)\n"
            "print(f'Shape           : {report[\"shape\"]}')\n"
            "print(f'Null counts     : {report[\"null_counts\"]}')\n"
            "print(f'Numeric cols    : {list(report[\"numeric_summary\"].keys())}')\n"
            "print(f'Category cols   : {list(report[\"category_counts\"].keys())}')\n"
            "print(f'Corr matrix cols: {list(report[\"correlations\"].keys())}')\n"
            "\n"
            "assert report['shape'] == df.shape\n"
            "assert 'revenue' in report['numeric_summary']\n"
            "assert 'product' in report['category_counts']\n"
            "\n"
            "print('\\nExploratory Data Analysis complete!')"
        ),
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Generating Day 038 notebooks...")
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
