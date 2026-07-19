#!/usr/bin/env python3
"""Generate all Day 040 notebooks: exercises 1-5, project, solution."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAY_DIR = ROOT / "03_data_analysis" / "day_040"

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
# Shared data + EDA helpers (from Days 36-38, reproduced for self-containment)
# ---------------------------------------------------------------------------

BASE_IMPORTS = """\
import warnings
warnings.filterwarnings('ignore')
import json
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

# EDA helpers — needed as setup for several exercises
DISTRIBUTION_SUMMARY_IMPL = """\
def distribution_summary(df, col):
    s = df[col]
    if pd.api.types.is_numeric_dtype(s):
        return {
            'count': int(s.count()), 'mean': round(float(s.mean()), 4),
            'std': round(float(s.std()), 4), 'min': float(s.min()),
            'q25': float(s.quantile(0.25)), 'median': float(s.quantile(0.50)),
            'q75': float(s.quantile(0.75)), 'max': float(s.max()),
            'null_count': int(s.isnull().sum()),
        }
    counts = s.value_counts()
    return {
        'count': int(s.count()), 'unique': int(s.nunique()),
        'top': str(counts.index[0]) if len(counts) else None,
        'top_freq': int(counts.iloc[0]) if len(counts) else 0,
        'null_count': int(s.isnull().sum()),
    }"""

TOP_GROUPS_IMPL = """\
def top_groups(df, group_col, value_col, n=5):
    return (
        df.groupby(group_col)[value_col]
        .agg(total='sum', mean='mean', count='count')
        .reset_index()
        .nlargest(n, 'total')
        .reset_index(drop=True)
    )"""

CORRELATION_SUMMARY_IMPL = """\
def correlation_summary(df, target_col):
    corr = df.select_dtypes(include='number').corr()[target_col].drop(target_col)
    result = pd.DataFrame({'feature': corr.index.tolist(), 'correlation': corr.values})
    result['_abs'] = result['correlation'].abs()
    result = result.sort_values('_abs', ascending=False).drop(columns='_abs')
    return result.reset_index(drop=True)"""

EDA_REPORT_IMPL = """\
def eda_report(df):
    num_cols = df.select_dtypes(include='number').columns.tolist()
    cat_cols = df.select_dtypes(include='object').columns.tolist()
    return {
        'shape':           df.shape,
        'null_counts':     df.isnull().sum().to_dict(),
        'numeric_summary': df[num_cols].describe().round(2).to_dict() if num_cols else {},
        'category_counts': {col: df[col].value_counts().to_dict() for col in cat_cols},
        'correlations':    df[num_cols].corr().round(4).to_dict() if len(num_cols) > 1 else {},
    }"""

ALL_EDA_HELPERS = "\n\n\n".join([
    DISTRIBUTION_SUMMARY_IMPL,
    TOP_GROUPS_IMPL,
    CORRELATION_SUMMARY_IMPL,
    EDA_REPORT_IMPL,
])

# ---------------------------------------------------------------------------
# Day 040 implementations
# ---------------------------------------------------------------------------

SUMMARIZE_COLUMN_IMPL = """\
import json
import ollama

def summarize_column(col_name: str, stats: dict,
                     model: str = 'llama3.2') -> str:
    prompt = (
        f"You are a concise data analyst. Describe the column '{col_name}' "
        f"in 1-2 clear sentences for a non-technical reader.\\n\\n"
        f"Statistics:\\n{json.dumps(stats, indent=2)}"
    )
    resp = ollama.chat(model=model,
                       messages=[{"role": "user", "content": prompt}])
    return resp["message"]["content"].strip()"""

NARRATE_TOP_GROUPS_IMPL = """\
import json
import ollama

def narrate_top_groups(groups_df, group_col: str, value_col: str,
                       model: str = 'llama3.2') -> str:
    records = groups_df.to_dict(orient='records')
    prompt = (
        f"You are a concise data analyst. Write 2-3 sentences about which "
        f"'{group_col}' groups have the highest '{value_col}' and what stands out.\\n\\n"
        f"Top groups by {value_col}:\\n{json.dumps(records, indent=2)}"
    )
    resp = ollama.chat(model=model,
                       messages=[{"role": "user", "content": prompt}])
    return resp["message"]["content"].strip()"""

NARRATE_CORRELATIONS_IMPL = """\
import json
import ollama

def narrate_correlations(corr_df, target_col: str,
                         model: str = 'llama3.2') -> str:
    records = corr_df.to_dict(orient='records')
    prompt = (
        f"You are a concise data analyst. Write 2-3 sentences explaining which "
        f"features correlate most with '{target_col}' and what this likely means.\\n\\n"
        f"Correlations with '{target_col}':\\n{json.dumps(records, indent=2)}"
    )
    resp = ollama.chat(model=model,
                       messages=[{"role": "user", "content": prompt}])
    return resp["message"]["content"].strip()"""

NARRATE_EDA_IMPL = """\
import json
import ollama

def narrate_eda_report(report: dict, title: str = 'Dataset',
                       model: str = 'llama3.2') -> str:
    shape = report['shape']
    nulls = sum(report['null_counts'].values())
    summary = {
        'dataset':             title,
        'rows':                shape[0],
        'columns':             shape[1],
        'total_nulls':         nulls,
        'numeric_columns':     list(report['numeric_summary'].keys()),
        'categorical_columns': list(report['category_counts'].keys()),
        'numeric_stats':       report['numeric_summary'],
        'top_categories':      {
            col: dict(list(counts.items())[:5])
            for col, counts in report['category_counts'].items()
        },
    }
    prompt = (
        "You are a data analyst. Write a 3-5 sentence executive summary of this "
        "dataset for a business audience. Highlight key patterns, data quality, "
        "and notable findings.\\n\\n"
        f"EDA Report:\\n{json.dumps(summary, indent=2, default=str)}"
    )
    resp = ollama.chat(model=model,
                       messages=[{"role": "user", "content": prompt}])
    return resp["message"]["content"].strip()"""

GENERATE_DATA_STORY_IMPL = """\
import ollama
import pandas as pd

def generate_data_story(df: pd.DataFrame, title: str = 'Dataset',
                        model: str = 'llama3.2') -> str:
    report = eda_report(df)
    return narrate_eda_report(report, title=title, model=model)"""

ALL_NARRATE_IMPLS = "\n\n\n".join([
    SUMMARIZE_COLUMN_IMPL,
    NARRATE_TOP_GROUPS_IMPL,
    NARRATE_CORRELATIONS_IMPL,
    NARRATE_EDA_IMPL,
])


# ---------------------------------------------------------------------------
# Exercise 01 — summarize_column
# ---------------------------------------------------------------------------

def ex01():
    global _cid; _cid = 0
    setup = BASE_IMPORTS + "\n\n\n" + DISTRIBUTION_SUMMARY_IMPL + "\n\n\n" + RETAIL_CSV_CODE
    return [
        md(
            "# Day 040 — Exercise 1: summarize_column\n\n"
            "**What you'll build:** `summarize_column(col_name, stats, model) -> str` — "
            "take a column name and its `distribution_summary` stats dict, build a "
            "prompt, call Ollama, and return a 1-2 sentence description in plain English.\n\n"
            "**Why it matters:** Numbers alone don't communicate. "
            "A stats dict tells you mean=298.69 and std=453.04 — "
            "an LLM turns that into 'Revenue varies widely, from as low as $100 to a "
            "peak of $1,050, with most orders in the $125-$450 range.' "
            "That sentence is what a stakeholder reads."
        ),
        code(setup),
        md("## Your Implementation"),
        code(
            "def summarize_column(col_name: str, stats: dict,\n"
            "                     model: str = 'llama3.2') -> str:\n"
            '    """\n'
            "    Describe one column in plain English using an LLM.\n\n"
            "    Args:\n"
            "        col_name — column name to describe (included in prompt)\n"
            "        stats    — dict from distribution_summary (numeric or categorical)\n"
            "        model    — Ollama model to use\n"
            "    Returns:\n"
            "        str      — 1-2 sentence plain-English description\n"
            '    """\n'
            "    # TODO: build a prompt string that includes col_name and\n"
            "    #       json.dumps(stats, indent=2)\n"
            "    # TODO: resp = ollama.chat(model=model,\n"
            "    #             messages=[{'role': 'user', 'content': prompt}])\n"
            "    # TODO: return resp['message']['content'].strip()\n"
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
            "        assert 'summarize_column' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: summarize_column is defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: returns a string (makes a real Ollama call)\n"
            "    try:\n"
            "        _stats = distribution_summary(SALES_DF, 'revenue')\n"
            "        _result = summarize_column('revenue', _stats)\n"
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
            "        passed += 1; print('\\u2705 Check 3: response is non-empty')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: response is a meaningful length (> 30 chars)\n"
            "    try:\n"
            "        _n = len(_result.strip())\n"
            "        assert _n > 30, \\\n"
            "            f'response too short ({_n} chars) — expected a meaningful sentence'\n"
            "        passed += 1; print(f'\\u2705 Check 4: response is {_n} chars')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: also works for a categorical column\n"
            "    try:\n"
            "        _cat_stats = distribution_summary(SALES_DF, 'product')\n"
            "        _cat_result = summarize_column('product', _cat_stats)\n"
            "        assert isinstance(_cat_result, str) and len(_cat_result.strip()) > 0\n"
            "        passed += 1; print('\\u2705 Check 5: works for categorical column (product)')\n"
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
            + SUMMARIZE_COLUMN_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 02 — narrate_top_groups
# ---------------------------------------------------------------------------

def ex02():
    global _cid; _cid = 100
    setup = (
        BASE_IMPORTS + "\n\n\n"
        + DISTRIBUTION_SUMMARY_IMPL + "\n\n\n"
        + TOP_GROUPS_IMPL + "\n\n\n"
        + RETAIL_CSV_CODE + "\n\n\n"
        + SUMMARIZE_COLUMN_IMPL
    )
    return [
        md(
            "# Day 040 — Exercise 2: narrate_top_groups\n\n"
            "**What you'll build:** `narrate_top_groups(groups_df, group_col, value_col, model) -> str` — "
            "take a `top_groups` DataFrame, convert it to a list of dicts with "
            "`df.to_dict(orient='records')`, build a prompt, and return a 2-3 sentence "
            "narrative about the rankings.\n\n"
            "**Why it matters:** A table of product revenue totals requires the reader "
            "to do the comparison themselves. A sentence that says 'Gadget dominates at "
            "\\$1,800 — nearly double the next product' does the analysis for them. "
            "The `orient='records'` format gives the LLM a clean, row-by-row JSON structure."
        ),
        code(setup),
        md("## Your Implementation"),
        code(
            "def narrate_top_groups(groups_df, group_col: str, value_col: str,\n"
            "                       model: str = 'llama3.2') -> str:\n"
            '    """\n'
            "    Narrate a top_groups DataFrame as a plain-English ranking summary.\n\n"
            "    Args:\n"
            "        groups_df  — DataFrame from top_groups() with total/mean/count cols\n"
            "        group_col  — name of the grouping column (e.g. 'product')\n"
            "        value_col  — name of the value column (e.g. 'revenue')\n"
            "        model      — Ollama model to use\n"
            "    Returns:\n"
            "        str        — 2-3 sentence narrative about the rankings\n"
            '    """\n'
            "    # TODO: records = groups_df.to_dict(orient='records')\n"
            "    # TODO: build a prompt mentioning group_col and value_col,\n"
            "    #       include json.dumps(records, indent=2)\n"
            "    # TODO: call ollama.chat and return stripped content\n"
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
            "        assert 'narrate_top_groups' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: narrate_top_groups is defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: returns a string (Ollama call)\n"
            "    try:\n"
            "        _top = top_groups(SALES_DF, 'product', 'revenue', n=4)\n"
            "        _result = narrate_top_groups(_top, 'product', 'revenue')\n"
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
            "        passed += 1; print('\\u2705 Check 3: response is non-empty')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: response is substantial (> 50 chars for 2-3 sentences)\n"
            "    try:\n"
            "        _n = len(_result.strip())\n"
            "        assert _n > 50, \\\n"
            "            f'response too short ({_n} chars) — expected 2-3 sentences'\n"
            "        passed += 1; print(f'\\u2705 Check 4: response is {_n} chars')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: also works for a different grouping (region)\n"
            "    try:\n"
            "        _top_r = top_groups(SALES_DF, 'region', 'revenue', n=4)\n"
            "        _r_result = narrate_top_groups(_top_r, 'region', 'revenue')\n"
            "        assert isinstance(_r_result, str) and len(_r_result.strip()) > 0\n"
            "        passed += 1; print('\\u2705 Check 5: also works for region grouping')\n"
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
            + NARRATE_TOP_GROUPS_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 03 — narrate_correlations
# ---------------------------------------------------------------------------

def ex03():
    global _cid; _cid = 200
    setup = (
        BASE_IMPORTS + "\n\n\n"
        + DISTRIBUTION_SUMMARY_IMPL + "\n\n\n"
        + TOP_GROUPS_IMPL + "\n\n\n"
        + CORRELATION_SUMMARY_IMPL + "\n\n\n"
        + RETAIL_CSV_CODE + "\n\n\n"
        + SUMMARIZE_COLUMN_IMPL + "\n\n\n"
        + NARRATE_TOP_GROUPS_IMPL
    )
    return [
        md(
            "# Day 040 — Exercise 3: narrate_correlations\n\n"
            "**What you'll build:** `narrate_correlations(corr_df, target_col, model) -> str` — "
            "take a `correlation_summary` DataFrame (feature, correlation columns), "
            "convert to records, and return a 2-3 sentence explanation of which features "
            "co-vary with the target and why that might matter.\n\n"
            "**Why it matters:** On Day 38 you computed correlation numbers. "
            "Now you give those numbers to the LLM and it explains them in business terms: "
            "'Quantity is strongly correlated with revenue (r=0.86), suggesting that "
            "driving order volume is more impactful than increasing unit price.' "
            "That inference cannot come from the number alone."
        ),
        code(setup),
        md("## Your Implementation"),
        code(
            "def narrate_correlations(corr_df, target_col: str,\n"
            "                         model: str = 'llama3.2') -> str:\n"
            '    """\n'
            "    Explain a correlation_summary DataFrame in plain English.\n\n"
            "    Args:\n"
            "        corr_df    — DataFrame with columns ['feature', 'correlation']\n"
            "        target_col — the column correlations were computed against\n"
            "        model      — Ollama model to use\n"
            "    Returns:\n"
            "        str        — 2-3 sentence explanation\n"
            '    """\n'
            "    # TODO: records = corr_df.to_dict(orient='records')\n"
            "    # TODO: build prompt mentioning target_col,\n"
            "    #       include json.dumps(records, indent=2)\n"
            "    # TODO: call ollama.chat and return stripped content\n"
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
            "        assert 'narrate_correlations' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: narrate_correlations is defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: returns a string (Ollama call)\n"
            "    try:\n"
            "        _corr = correlation_summary(SALES_DF, 'revenue')\n"
            "        _result = narrate_correlations(_corr, 'revenue')\n"
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
            "        passed += 1; print('\\u2705 Check 3: response is non-empty')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: response is substantial (> 50 chars)\n"
            "    try:\n"
            "        _n = len(_result.strip())\n"
            "        assert _n > 50, f'response too short ({_n} chars)'\n"
            "        passed += 1; print(f'\\u2705 Check 4: response is {_n} chars')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: also works targeting a different numeric column (price)\n"
            "    try:\n"
            "        _corr2 = correlation_summary(SALES_DF, 'price')\n"
            "        _result2 = narrate_correlations(_corr2, 'price')\n"
            "        assert isinstance(_result2, str) and len(_result2.strip()) > 0\n"
            "        passed += 1; print('\\u2705 Check 5: also works with price as target')\n"
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
            + NARRATE_CORRELATIONS_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 04 — narrate_eda_report
# ---------------------------------------------------------------------------

def ex04():
    global _cid; _cid = 300
    setup = (
        BASE_IMPORTS + "\n\n\n"
        + ALL_EDA_HELPERS + "\n\n\n"
        + RETAIL_CSV_CODE + "\n\n\n"
        + SUMMARIZE_COLUMN_IMPL + "\n\n\n"
        + NARRATE_TOP_GROUPS_IMPL + "\n\n\n"
        + NARRATE_CORRELATIONS_IMPL
    )
    return [
        md(
            "# Day 040 — Exercise 4: narrate_eda_report\n\n"
            "**What you'll build:** `narrate_eda_report(report, title, model) -> str` — "
            "take a full `eda_report` dict, extract the key facts into a compact summary, "
            "build a prompt, and return a 3-5 sentence executive summary.\n\n"
            "**Why it matters:** A full EDA report dict has hundreds of numbers. "
            "You cannot dump the entire thing into a prompt — the LLM will lose focus. "
            "The skill is knowing what to include: shape, null count, column names, "
            "and the top category counts. That compact context gives the LLM enough "
            "to write a meaningful executive summary for a business reader."
        ),
        code(setup),
        md("## Your Implementation"),
        code(
            "def narrate_eda_report(report: dict, title: str = 'Dataset',\n"
            "                       model: str = 'llama3.2') -> str:\n"
            '    """\n'
            "    Generate an executive summary from a full eda_report dict.\n\n"
            "    Args:\n"
            "        report — dict from eda_report() with shape/null_counts/etc.\n"
            "        title  — human-readable dataset name for the prompt\n"
            "        model  — Ollama model to use\n"
            "    Returns:\n"
            "        str    — 3-5 sentence executive summary\n"
            '    """\n'
            "    shape = report['shape']\n"
            "    nulls = sum(report['null_counts'].values())\n"
            "    # TODO: build a compact summary dict (rows, columns, nulls,\n"
            "    #       list of numeric/categorical columns, numeric_stats,\n"
            "    #       top 5 entries per category)\n"
            "    # TODO: build prompt asking for a 3-5 sentence executive summary\n"
            "    # TODO: call ollama.chat and return stripped content\n"
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
            "        assert 'narrate_eda_report' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: narrate_eda_report is defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: returns a string (Ollama call)\n"
            "    try:\n"
            "        _report = eda_report(SALES_DF)\n"
            "        _result = narrate_eda_report(_report, title='Retail Sales')\n"
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
            "        passed += 1; print('\\u2705 Check 3: response is non-empty')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: response is longer than a single-column summary (> 100 chars)\n"
            "    try:\n"
            "        _n = len(_result.strip())\n"
            "        assert _n > 100, \\\n"
            "            f'response too short ({_n} chars) — executive summary should be > 100 chars'\n"
            "        passed += 1; print(f'\\u2705 Check 4: response is {_n} chars (full EDA summary)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: title parameter is accepted (no TypeError)\n"
            "    try:\n"
            "        _result2 = narrate_eda_report(_report, title='Q4 Sales Report',\n"
            "                                      model='llama3.2')\n"
            "        assert isinstance(_result2, str) and len(_result2.strip()) > 0\n"
            "        passed += 1; print('\\u2705 Check 5: title and model parameters accepted')\n"
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
            + NARRATE_EDA_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 05 — generate_data_story
# ---------------------------------------------------------------------------

def ex05():
    global _cid; _cid = 400
    return [
        md(
            "# Day 040 — Exercise 5: generate_data_story\n\n"
            "**What you'll build:** `generate_data_story(df, title, model) -> str` — "
            "the end-to-end pipeline: run `eda_report(df)`, pass the result to "
            "`narrate_eda_report`, and return the narrative. "
            "One function, DataFrame in, story out.\n\n"
            "**Why it matters:** This is the pattern you will use in Day 50's "
            "Insight Engine capstone: upload a CSV, get a narrative back. "
            "The two-line implementation is deliberately minimal — "
            "the value is in composing functions you already trust."
        ),
        md("## Provided: All EDA Helpers + Narration Functions"),
        code(
            BASE_IMPORTS + "\n\n\n"
            + ALL_EDA_HELPERS
        ),
        code(ALL_NARRATE_IMPLS),
        code(RETAIL_CSV_CODE),
        md("## Your Implementation"),
        code(
            "def generate_data_story(df, title: str = 'Dataset',\n"
            "                        model: str = 'llama3.2') -> str:\n"
            '    """\n'
            "    End-to-end: DataFrame → EDA → plain-English narrative.\n\n"
            "    Args:\n"
            "        df    — any pandas DataFrame\n"
            "        title — human-readable dataset name\n"
            "        model — Ollama model to use\n"
            "    Returns:\n"
            "        str   — executive narrative from the LLM\n"
            '    """\n'
            "    # TODO: report = eda_report(df)\n"
            "    # TODO: return narrate_eda_report(report, title=title, model=model)\n"
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
            "        assert 'generate_data_story' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: generate_data_story is defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: returns a string (Ollama call)\n"
            "    try:\n"
            "        _result = generate_data_story(SALES_DF, title='Retail Sales')\n"
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
            "        passed += 1; print('\\u2705 Check 3: response is non-empty')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: response is a full summary (> 100 chars)\n"
            "    try:\n"
            "        _n = len(_result.strip())\n"
            "        assert _n > 100, f'response too short ({_n} chars)'\n"
            "        passed += 1; print(f'\\u2705 Check 4: response is {_n} chars')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: works on a minimal DataFrame with different structure\n"
            "    try:\n"
            "        import pandas as pd\n"
            "        _mini = pd.DataFrame({'x': [1, 2, 3], 'label': ['a', 'b', 'c']})\n"
            "        _mini_result = generate_data_story(_mini, title='Mini Dataset')\n"
            "        assert isinstance(_mini_result, str) and len(_mini_result.strip()) > 0\n"
            "        passed += 1; print('\\u2705 Check 5: works on any DataFrame structure')\n"
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
            + GENERATE_DATA_STORY_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Project notebook
# ---------------------------------------------------------------------------

def project_nb():
    global _cid; _cid = 500
    all_narrate = ALL_NARRATE_IMPLS + "\n\n\n" + GENERATE_DATA_STORY_IMPL
    return [
        md(
            "# Day 040 Project: Auto-Generated Data Story\n\n"
            "## What You're Building\n\n"
            "A full automated data story pipeline: load a CSV, run EDA, "
            "narrate individual columns and groups, then generate an executive "
            "summary — all driven by Ollama.\n\n"
            "**Deliverable:** You run every cell top-to-bottom. The final checks pass. "
            "You have a printed narrative that a non-technical stakeholder could read.\n\n"
            "## Project Requirements\n\n"
            "1. Load `RETAIL_CSV` into a DataFrame with a `revenue` column\n"
            "2. Narrate the `revenue` column using `summarize_column`\n"
            "3. Narrate the top products using `narrate_top_groups`\n"
            "4. Narrate the correlations with `revenue` using `narrate_correlations`\n"
            "5. Generate a full executive summary using `generate_data_story`\n"
            "6. Verify with `_run_project_checks()`"
        ),
        code(
            BASE_IMPORTS + "\n\n\n"
            + ALL_EDA_HELPERS + "\n\n\n"
            + all_narrate + "\n\n\n"
            + RETAIL_CSV_CODE + "\n\n"
            + "print(f'Loaded {SALES_DF.shape[0]} rows')"
        ),
        md("## Your Data Story"),
        code(
            "# Step 1: Narrate the revenue column\n"
            "# TODO: rev_stats  = distribution_summary(SALES_DF, 'revenue')\n"
            "# TODO: rev_narr   = summarize_column('revenue', rev_stats)\n"
            "# TODO: print('Revenue column:\\n', rev_narr)\n"
            "\n"
            "# Step 2: Narrate top products by revenue\n"
            "# TODO: top3       = top_groups(SALES_DF, 'product', 'revenue', n=4)\n"
            "# TODO: group_narr = narrate_top_groups(top3, 'product', 'revenue')\n"
            "# TODO: print('\\nProduct rankings:\\n', group_narr)\n"
            "\n"
            "# Step 3: Narrate correlations with revenue\n"
            "# TODO: corr       = correlation_summary(SALES_DF, 'revenue')\n"
            "# TODO: corr_narr  = narrate_correlations(corr, 'revenue')\n"
            "# TODO: print('\\nCorrelations:\\n', corr_narr)\n"
            "\n"
            "# Step 4: Full executive summary\n"
            "# TODO: story = generate_data_story(SALES_DF, title='Retail Sales Q4')\n"
            "# TODO: print('\\n=== Executive Summary ===\\n', story)"
        ),
        md("## Project Checks"),
        code(
            "def _run_project_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: SALES_DF has revenue column\n"
            "    try:\n"
            "        assert 'SALES_DF' in globals() and 'revenue' in SALES_DF.columns\n"
            "        passed += 1; print(f'\\u2705 Check 1: SALES_DF loaded ({len(SALES_DF)} rows)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "\n"
            "    # Check 2: rev_narr is a non-empty string\n"
            "    try:\n"
            "        assert 'rev_narr' in globals(), 'rev_narr not defined'\n"
            "        assert isinstance(rev_narr, str) and len(rev_narr.strip()) > 0\n"
            "        passed += 1; print(f'\\u2705 Check 2: rev_narr is {len(rev_narr)} chars')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: group_narr is a non-empty string\n"
            "    try:\n"
            "        assert 'group_narr' in globals(), 'group_narr not defined'\n"
            "        assert isinstance(group_narr, str) and len(group_narr.strip()) > 0\n"
            "        passed += 1; print(f'\\u2705 Check 3: group_narr is {len(group_narr)} chars')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: corr_narr is a non-empty string\n"
            "    try:\n"
            "        assert 'corr_narr' in globals(), 'corr_narr not defined'\n"
            "        assert isinstance(corr_narr, str) and len(corr_narr.strip()) > 0\n"
            "        passed += 1; print(f'\\u2705 Check 4: corr_narr is {len(corr_narr)} chars')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: story is a substantial executive summary (> 100 chars)\n"
            "    try:\n"
            "        assert 'story' in globals(), 'story not defined'\n"
            "        assert isinstance(story, str) and len(story.strip()) > 100, \\\n"
            "            f'story too short ({len(story)} chars)'\n"
            "        passed += 1; print(f'\\u2705 Check 5: story is {len(story)} chars (executive summary)')\n"
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
            "- Loop `summarize_column` over every column in `SALES_DF` and print each summary\n"
            "- Ask the LLM to suggest one business action based on the data story\n"
            "- Pass a system prompt to `ollama.chat` to set the analyst's persona "
            "(e.g. 'You are a CFO summarising sales data for the board')\n"
            "- Try a different model (`model='mistral'` if installed) and compare the summaries\n"
            "- On Day 50 you will build the Insight Engine capstone — "
            "upload any CSV and get an auto-generated story back via a web UI"
        ),
    ]


# ---------------------------------------------------------------------------
# Solution notebook
# ---------------------------------------------------------------------------

def solution_nb():
    global _cid; _cid = 600
    all_narrate = ALL_NARRATE_IMPLS + "\n\n\n" + GENERATE_DATA_STORY_IMPL
    return [
        md(
            "# Day 040 Solution — AI-Assisted Analysis\n\n"
            "summarize_column, narrate_top_groups, narrate_correlations, "
            "narrate_eda_report, generate_data_story. "
            "All data and EDA helpers defined inline."
        ),
        code(
            BASE_IMPORTS + "\n\n\n"
            + ALL_EDA_HELPERS + "\n\n\n"
            + all_narrate
        ),
        md("## Step 1 — Load Data"),
        code(
            RETAIL_CSV_CODE + "\n\n"
            "print(f'Shape: {SALES_DF.shape}')\n"
            "print(SALES_DF[['product', 'price', 'quantity', 'revenue']].head())\n"
            "\n"
            "assert SALES_DF.shape == (12, 7)\n"
            "assert 'revenue' in SALES_DF.columns"
        ),
        md("## Step 2 — Narrate Revenue Column"),
        code(
            "rev_stats = distribution_summary(SALES_DF, 'revenue')\n"
            "print('Revenue stats:', json.dumps(rev_stats, indent=2))\n"
            "\n"
            "rev_narr = summarize_column('revenue', rev_stats)\n"
            "print('\\nNarration:')\n"
            "print(rev_narr)\n"
            "\n"
            "assert isinstance(rev_narr, str) and len(rev_narr.strip()) > 0\n"
            "print(f'\\n[{len(rev_narr)} chars]')"
        ),
        md("## Step 3 — Narrate Top Products"),
        code(
            "top4 = top_groups(SALES_DF, 'product', 'revenue', n=4)\n"
            "print('Top products:')\n"
            "print(top4.to_string(index=False))\n"
            "\n"
            "group_narr = narrate_top_groups(top4, 'product', 'revenue')\n"
            "print('\\nNarration:')\n"
            "print(group_narr)\n"
            "\n"
            "assert isinstance(group_narr, str) and len(group_narr.strip()) > 0"
        ),
        md("## Step 4 — Narrate Correlations"),
        code(
            "corr = correlation_summary(SALES_DF, 'revenue')\n"
            "print('Correlations with revenue:')\n"
            "print(corr.to_string(index=False))\n"
            "\n"
            "corr_narr = narrate_correlations(corr, 'revenue')\n"
            "print('\\nNarration:')\n"
            "print(corr_narr)\n"
            "\n"
            "assert isinstance(corr_narr, str) and len(corr_narr.strip()) > 0"
        ),
        md("## Step 5 — Full Data Story"),
        code(
            "story = generate_data_story(SALES_DF, title='Retail Sales Dataset')\n"
            "print('=== Executive Summary ===')\n"
            "print(story)\n"
            "\n"
            "assert isinstance(story, str) and len(story.strip()) > 100\n"
            "print(f'\\n[{len(story)} chars — data story complete]')"
        ),
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Generating Day 040 notebooks...")
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
