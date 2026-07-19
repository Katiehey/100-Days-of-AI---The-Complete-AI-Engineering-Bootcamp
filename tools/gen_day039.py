#!/usr/bin/env python3
"""Generate all Day 039 notebooks: exercises 1-5, project, solution."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAY_DIR = ROOT / "03_data_analysis" / "day_039"

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
# Shared setup
# ---------------------------------------------------------------------------

SETUP_CODE = """\
import warnings
warnings.filterwarnings('ignore')
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

PRODUCTS = ['Widget', 'Gadget', 'Doohickey', 'Thingamajig']
REVENUES = [625.0, 1800.0, 680.0, 1000.0]"""

RETAIL_CSV_CODE = """\
import io
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
# Implementations
# ---------------------------------------------------------------------------

BAR_CHART_IMPL = """\
import matplotlib.pyplot as plt

def bar_chart(ax, labels, values, title='', xlabel='', ylabel=''):
    ax.bar(labels, values)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.tick_params(axis='x', rotation=45)
    return ax"""

LINE_CHART_IMPL = """\
import matplotlib.pyplot as plt

def line_chart(ax, x, y, title='', xlabel='', ylabel='', label=None):
    ax.plot(x, y, marker='o', label=label)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if label:
        ax.legend()
    return ax"""

SCATTER_CHART_IMPL = """\
import matplotlib.pyplot as plt

def scatter_chart(ax, x, y, title='', xlabel='', ylabel=''):
    ax.scatter(x, y)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    return ax"""

HISTOGRAM_IMPL = """\
import matplotlib.pyplot as plt

def histogram(ax, data, bins=10, title='', xlabel=''):
    ax.hist(data, bins=bins, edgecolor='white')
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel('Count')
    return ax"""

MULTI_CHART_IMPL = """\
import os
import matplotlib.pyplot as plt

def multi_chart_figure(df, out_path='dashboard.png'):
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    # Top-left: bar chart — revenue by product
    totals = df.groupby('product')['revenue'].sum().sort_values(ascending=False)
    bar_chart(axes[0, 0], totals.index.tolist(), totals.values.tolist(),
              'Revenue by Product', 'Product', 'Revenue ($)')

    # Top-right: line chart — cumulative revenue
    df_s = df.sort_values('order_id').reset_index(drop=True)
    line_chart(axes[0, 1], list(range(1, len(df_s) + 1)),
               df_s['revenue'].cumsum().tolist(),
               'Cumulative Revenue', 'Order #', 'Revenue ($)',
               label='cumulative')

    # Bottom-left: scatter — price vs revenue
    scatter_chart(axes[1, 0], df['price'].tolist(), df['revenue'].tolist(),
                  'Price vs Revenue', 'Price ($)', 'Revenue ($)')

    # Bottom-right: histogram — revenue distribution
    histogram(axes[1, 1], df['revenue'].tolist(), bins=8,
              title='Revenue Distribution', xlabel='Revenue ($)')

    fig.suptitle('Sales Dashboard', fontsize=16)
    plt.tight_layout()
    fig.savefig(out_path, bbox_inches='tight', dpi=100)
    plt.close(fig)
    return out_path"""

ALL_IMPLS = "\n\n\n".join([
    BAR_CHART_IMPL,
    LINE_CHART_IMPL,
    SCATTER_CHART_IMPL,
    HISTOGRAM_IMPL,
])


# ---------------------------------------------------------------------------
# Exercise 01 — bar_chart
# ---------------------------------------------------------------------------

def ex01():
    global _cid; _cid = 0
    return [
        md(
            "# Day 039 — Exercise 1: bar_chart\n\n"
            "**What you'll build:** `bar_chart(ax, labels, values, title, xlabel, ylabel) -> ax` — "
            "draw a vertical bar chart on a given Axes object with proper title and axis labels.\n\n"
            "**Why it matters:** Bar charts are the single most common chart in data reporting. "
            "Wrapping them in a function with a consistent signature means every chart in your "
            "dashboard is created the same way — testable, composable, and swappable."
        ),
        code(SETUP_CODE),
        md("## Your Implementation"),
        code(
            "def bar_chart(ax, labels, values, title='', xlabel='', ylabel=''):\n"
            '    """\n'
            "    Draw a vertical bar chart on ax.\n\n"
            "    Args:\n"
            "        ax     — matplotlib Axes to draw on\n"
            "        labels — list of category labels (x-axis)\n"
            "        values — list of numeric values (bar heights)\n"
            "        title  — chart title\n"
            "        xlabel — x-axis label\n"
            "        ylabel — y-axis label\n"
            "    Returns:\n"
            "        ax     — the modified Axes (for chaining)\n"
            '    """\n'
            "    # TODO: ax.bar(labels, values)\n"
            "    # TODO: set title, xlabel, ylabel on ax\n"
            "    # TODO: ax.tick_params(axis='x', rotation=45)  — prevent label overlap\n"
            "    # TODO: return ax\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: defined and callable without crashing\n"
            "    try:\n"
            "        assert 'bar_chart' in globals()\n"
            "        _fig, _ax = plt.subplots()\n"
            "        bar_chart(_ax, ['A', 'B'], [1, 2])\n"
            "        plt.close(_fig)\n"
            "        passed += 1; print('\\u2705 Check 1: bar_chart is defined and callable')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        plt.close('all')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: correct number of bars\n"
            "    try:\n"
            "        _fig, _ax = plt.subplots()\n"
            "        bar_chart(_ax, ['A', 'B', 'C'], [10, 20, 15])\n"
            "        assert len(_ax.patches) == 3, \\\n"
            "            f'expected 3 bars, got {len(_ax.patches)}'\n"
            "        plt.close(_fig)\n"
            "        passed += 1; print('\\u2705 Check 2: 3 bars rendered for 3 labels')\n"
            "    except Exception as e:\n"
            "        plt.close('all'); print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: title is set\n"
            "    try:\n"
            "        _fig, _ax = plt.subplots()\n"
            "        bar_chart(_ax, PRODUCTS, REVENUES, title='Revenue')\n"
            "        assert _ax.get_title() == 'Revenue', \\\n"
            "            f'title={_ax.get_title()!r}, expected \"Revenue\"'\n"
            "        plt.close(_fig)\n"
            "        passed += 1; print('\\u2705 Check 3: title is set correctly')\n"
            "    except Exception as e:\n"
            "        plt.close('all'); print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: xlabel and ylabel are set\n"
            "    try:\n"
            "        _fig, _ax = plt.subplots()\n"
            "        bar_chart(_ax, PRODUCTS, REVENUES,\n"
            "                  title='T', xlabel='Product', ylabel='Revenue ($)')\n"
            "        assert _ax.get_xlabel() == 'Product', \\\n"
            "            f'xlabel={_ax.get_xlabel()!r}'\n"
            "        assert _ax.get_ylabel() == 'Revenue ($)', \\\n"
            "            f'ylabel={_ax.get_ylabel()!r}'\n"
            "        plt.close(_fig)\n"
            "        passed += 1; print('\\u2705 Check 4: xlabel=\"Product\", ylabel=\"Revenue ($)\"')\n"
            "    except Exception as e:\n"
            "        plt.close('all'); print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: figure saves to a valid PNG\n"
            "    _tmp = '/tmp/day039_ex01.png'\n"
            "    try:\n"
            "        _fig, _ax = plt.subplots()\n"
            "        bar_chart(_ax, PRODUCTS, REVENUES,\n"
            "                  title='Revenue by Product', xlabel='Product', ylabel='Revenue ($)')\n"
            "        _fig.savefig(_tmp, bbox_inches='tight', dpi=72)\n"
            "        plt.close(_fig)\n"
            "        assert os.path.exists(_tmp) and os.path.getsize(_tmp) > 1000, \\\n"
            "            f'saved file missing or too small'\n"
            "        with open(_tmp, 'rb') as f:\n"
            "            assert f.read(4) == b'\\x89PNG', 'not a valid PNG'\n"
            "        os.remove(_tmp)\n"
            "        passed += 1; print('\\u2705 Check 5: figure saves as a valid PNG')\n"
            "    except Exception as e:\n"
            "        plt.close('all')\n"
            "        if os.path.exists(_tmp): os.remove(_tmp)\n"
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
            + BAR_CHART_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 02 — line_chart
# ---------------------------------------------------------------------------

def ex02():
    global _cid; _cid = 100
    return [
        md(
            "# Day 039 — Exercise 2: line_chart\n\n"
            "**What you'll build:** `line_chart(ax, x, y, title, xlabel, ylabel, label=None) -> ax` — "
            "draw a line chart with markers on a given Axes object. "
            "When `label` is provided, add a legend.\n\n"
            "**Why it matters:** Line charts show trends over time or sequence. "
            "The optional `label` parameter enables multi-series charts — call `line_chart` "
            "twice on the same ax with different labels to overlay two series."
        ),
        code(SETUP_CODE + "\n\n" + BAR_CHART_IMPL),
        md("## Your Implementation"),
        code(
            "def line_chart(ax, x, y, title='', xlabel='', ylabel='', label=None):\n"
            '    """\n'
            "    Draw a line chart with circular markers on ax.\n\n"
            "    Args:\n"
            "        ax     — matplotlib Axes to draw on\n"
            "        x      — list of x-axis values\n"
            "        y      — list of y-axis values\n"
            "        title  — chart title\n"
            "        xlabel — x-axis label\n"
            "        ylabel — y-axis label\n"
            "        label  — series legend label (None = no legend)\n"
            "    Returns:\n"
            "        ax     — the modified Axes\n"
            '    """\n'
            "    # TODO: ax.plot(x, y, marker='o', label=label)\n"
            "    # TODO: set title, xlabel, ylabel\n"
            "    # TODO: if label: ax.legend()\n"
            "    # TODO: return ax\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "    _X = [1, 2, 3, 4, 5]\n"
            "    _Y = [100, 150, 120, 180, 200]\n"
            "\n"
            "    # Check 1: defined and callable without crashing\n"
            "    try:\n"
            "        assert 'line_chart' in globals()\n"
            "        _fig, _ax = plt.subplots()\n"
            "        line_chart(_ax, _X, _Y)\n"
            "        plt.close(_fig)\n"
            "        passed += 1; print('\\u2705 Check 1: line_chart is defined and callable')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        plt.close('all')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: at least one line rendered\n"
            "    try:\n"
            "        _fig, _ax = plt.subplots()\n"
            "        line_chart(_ax, _X, _Y, title='Trend')\n"
            "        _lines = _ax.get_lines()\n"
            "        assert len(_lines) >= 1, \\\n"
            "            f'expected at least 1 line, got {len(_lines)}'\n"
            "        plt.close(_fig)\n"
            "        passed += 1; print(f'\\u2705 Check 2: {len(_lines)} line(s) rendered')\n"
            "    except Exception as e:\n"
            "        plt.close('all'); print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: title, xlabel, ylabel set\n"
            "    try:\n"
            "        _fig, _ax = plt.subplots()\n"
            "        line_chart(_ax, _X, _Y, title='Monthly', xlabel='Month', ylabel='Revenue')\n"
            "        assert _ax.get_title()  == 'Monthly',  f'title={_ax.get_title()!r}'\n"
            "        assert _ax.get_xlabel() == 'Month',    f'xlabel={_ax.get_xlabel()!r}'\n"
            "        assert _ax.get_ylabel() == 'Revenue',  f'ylabel={_ax.get_ylabel()!r}'\n"
            "        plt.close(_fig)\n"
            "        passed += 1; print('\\u2705 Check 3: title, xlabel, ylabel all set')\n"
            "    except Exception as e:\n"
            "        plt.close('all'); print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: legend present when label given, absent when label=None\n"
            "    try:\n"
            "        _fig, _ax = plt.subplots()\n"
            "        line_chart(_ax, _X, _Y, label=None)\n"
            "        assert _ax.get_legend() is None, \\\n"
            "            'legend should be None when label=None'\n"
            "        plt.close(_fig)\n"
            "\n"
            "        _fig, _ax = plt.subplots()\n"
            "        line_chart(_ax, _X, _Y, label='Revenue')\n"
            "        assert _ax.get_legend() is not None, \\\n"
            "            'legend should appear when label is provided'\n"
            "        plt.close(_fig)\n"
            "        passed += 1; print('\\u2705 Check 4: legend absent w/o label, present with label')\n"
            "    except Exception as e:\n"
            "        plt.close('all'); print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: figure saves to a valid PNG\n"
            "    _tmp = '/tmp/day039_ex02.png'\n"
            "    try:\n"
            "        _fig, _ax = plt.subplots()\n"
            "        line_chart(_ax, _X, _Y, title='Trend', xlabel='Month',\n"
            "                   ylabel='Revenue', label='sales')\n"
            "        _fig.savefig(_tmp, bbox_inches='tight', dpi=72)\n"
            "        plt.close(_fig)\n"
            "        assert os.path.exists(_tmp) and os.path.getsize(_tmp) > 1000\n"
            "        with open(_tmp, 'rb') as f:\n"
            "            assert f.read(4) == b'\\x89PNG'\n"
            "        os.remove(_tmp)\n"
            "        passed += 1; print('\\u2705 Check 5: figure saves as a valid PNG')\n"
            "    except Exception as e:\n"
            "        plt.close('all')\n"
            "        if os.path.exists(_tmp): os.remove(_tmp)\n"
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
            + LINE_CHART_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 03 — scatter_chart
# ---------------------------------------------------------------------------

def ex03():
    global _cid; _cid = 200
    return [
        md(
            "# Day 039 — Exercise 3: scatter_chart\n\n"
            "**What you'll build:** `scatter_chart(ax, x, y, title, xlabel, ylabel) -> ax` — "
            "draw a scatter plot on a given Axes object.\n\n"
            "**Why it matters:** Scatter plots reveal the relationship between two numeric variables. "
            "When you built `correlation_summary` on Day 38, you found which columns co-vary. "
            "A scatter plot shows *how* they co-vary — linear, curved, or not at all."
        ),
        code(SETUP_CODE + "\n\n" + BAR_CHART_IMPL + "\n\n\n" + LINE_CHART_IMPL),
        md("## Your Implementation"),
        code(
            "def scatter_chart(ax, x, y, title='', xlabel='', ylabel=''):\n"
            '    """\n'
            "    Draw a scatter plot on ax.\n\n"
            "    Args:\n"
            "        ax     — matplotlib Axes to draw on\n"
            "        x      — list of x-axis values\n"
            "        y      — list of y-axis values\n"
            "        title  — chart title\n"
            "        xlabel — x-axis label\n"
            "        ylabel — y-axis label\n"
            "    Returns:\n"
            "        ax     — the modified Axes\n"
            '    """\n'
            "    # TODO: ax.scatter(x, y)\n"
            "    # TODO: set title, xlabel, ylabel\n"
            "    # TODO: return ax\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "    _X = [25.0, 150.0, 8.0, 200.0, 25.0, 150.0]\n"
            "    _Y = [250.0, 450.0, 400.0, 200.0, 125.0, 1050.0]\n"
            "\n"
            "    # Check 1: defined and callable without crashing\n"
            "    try:\n"
            "        assert 'scatter_chart' in globals()\n"
            "        _fig, _ax = plt.subplots()\n"
            "        scatter_chart(_ax, _X, _Y)\n"
            "        plt.close(_fig)\n"
            "        passed += 1; print('\\u2705 Check 1: scatter_chart is defined and callable')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        plt.close('all')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: scatter collection is present\n"
            "    try:\n"
            "        _fig, _ax = plt.subplots()\n"
            "        scatter_chart(_ax, _X, _Y)\n"
            "        assert len(_ax.collections) >= 1, \\\n"
            "            f'expected scatter collection, got {len(_ax.collections)} collections'\n"
            "        plt.close(_fig)\n"
            "        passed += 1; print('\\u2705 Check 2: scatter collection rendered')\n"
            "    except Exception as e:\n"
            "        plt.close('all'); print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: correct number of points\n"
            "    try:\n"
            "        _fig, _ax = plt.subplots()\n"
            "        scatter_chart(_ax, _X, _Y)\n"
            "        _n_pts = _ax.collections[0].get_offsets().shape[0]\n"
            "        assert _n_pts == len(_X), \\\n"
            "            f'expected {len(_X)} points, got {_n_pts}'\n"
            "        plt.close(_fig)\n"
            "        passed += 1; print(f'\\u2705 Check 3: {_n_pts} points rendered ({len(_X)} expected)')\n"
            "    except Exception as e:\n"
            "        plt.close('all'); print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: title, xlabel, ylabel set\n"
            "    try:\n"
            "        _fig, _ax = plt.subplots()\n"
            "        scatter_chart(_ax, _X, _Y,\n"
            "                      title='Price vs Revenue', xlabel='Price', ylabel='Revenue')\n"
            "        assert _ax.get_title()  == 'Price vs Revenue'\n"
            "        assert _ax.get_xlabel() == 'Price'\n"
            "        assert _ax.get_ylabel() == 'Revenue'\n"
            "        plt.close(_fig)\n"
            "        passed += 1; print('\\u2705 Check 4: title, xlabel, ylabel all set')\n"
            "    except Exception as e:\n"
            "        plt.close('all'); print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: figure saves to a valid PNG\n"
            "    _tmp = '/tmp/day039_ex03.png'\n"
            "    try:\n"
            "        _fig, _ax = plt.subplots()\n"
            "        scatter_chart(_ax, _X, _Y,\n"
            "                      title='Price vs Revenue', xlabel='Price ($)', ylabel='Revenue ($)')\n"
            "        _fig.savefig(_tmp, bbox_inches='tight', dpi=72)\n"
            "        plt.close(_fig)\n"
            "        assert os.path.exists(_tmp) and os.path.getsize(_tmp) > 1000\n"
            "        with open(_tmp, 'rb') as f:\n"
            "            assert f.read(4) == b'\\x89PNG'\n"
            "        os.remove(_tmp)\n"
            "        passed += 1; print('\\u2705 Check 5: figure saves as a valid PNG')\n"
            "    except Exception as e:\n"
            "        plt.close('all')\n"
            "        if os.path.exists(_tmp): os.remove(_tmp)\n"
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
            + SCATTER_CHART_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 04 — histogram
# ---------------------------------------------------------------------------

def ex04():
    global _cid; _cid = 300
    return [
        md(
            "# Day 039 — Exercise 4: histogram\n\n"
            "**What you'll build:** `histogram(ax, data, bins=10, title='', xlabel='') -> ax` — "
            "draw a histogram with consistent styling (white bar edges) "
            "and a 'Count' y-axis label.\n\n"
            "**Why it matters:** Histograms reveal the shape of a numeric distribution — "
            "is it symmetric, skewed, bimodal? On Day 38 you computed the five-number summary; "
            "a histogram makes the distribution visible in a way numbers alone cannot."
        ),
        code(
            SETUP_CODE + "\n\n"
            + BAR_CHART_IMPL + "\n\n\n"
            + LINE_CHART_IMPL + "\n\n\n"
            + SCATTER_CHART_IMPL
        ),
        md("## Your Implementation"),
        code(
            "def histogram(ax, data, bins=10, title='', xlabel=''):\n"
            '    """\n'
            "    Draw a histogram on ax.\n\n"
            "    Args:\n"
            "        ax    — matplotlib Axes to draw on\n"
            "        data  — list or Series of numeric values\n"
            "        bins  — number of bins (default 10)\n"
            "        title — chart title\n"
            "        xlabel— x-axis label\n"
            "    Returns:\n"
            "        ax    — the modified Axes\n"
            '    """\n'
            "    # TODO: ax.hist(data, bins=bins, edgecolor='white')\n"
            "    # TODO: ax.set_title(title)\n"
            "    # TODO: ax.set_xlabel(xlabel)\n"
            "    # TODO: ax.set_ylabel('Count')  — always 'Count' for histograms\n"
            "    # TODO: return ax\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "    _DATA = [100.0, 125.0, 150.0, 250.0, 400.0, 450.0, 680.0, 1000.0, 1050.0, 1800.0]\n"
            "\n"
            "    # Check 1: defined and callable without crashing\n"
            "    try:\n"
            "        assert 'histogram' in globals()\n"
            "        _fig, _ax = plt.subplots()\n"
            "        histogram(_ax, _DATA)\n"
            "        plt.close(_fig)\n"
            "        passed += 1; print('\\u2705 Check 1: histogram is defined and callable')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        plt.close('all')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: histogram bars (patches) are rendered\n"
            "    try:\n"
            "        _fig, _ax = plt.subplots()\n"
            "        histogram(_ax, _DATA, bins=5)\n"
            "        assert len(_ax.patches) > 0, 'no histogram bars rendered'\n"
            "        plt.close(_fig)\n"
            "        passed += 1; print(f'\\u2705 Check 2: {len(_ax.patches)} bar(s) rendered')\n"
            "    except Exception as e:\n"
            "        plt.close('all'); print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: bins parameter respected — more bins = more bars\n"
            "    try:\n"
            "        _fig4, _ax4 = plt.subplots()\n"
            "        histogram(_ax4, _DATA, bins=4)\n"
            "        _cnt4 = len(_ax4.patches)\n"
            "        plt.close(_fig4)\n"
            "\n"
            "        _fig8, _ax8 = plt.subplots()\n"
            "        histogram(_ax8, _DATA, bins=8)\n"
            "        _cnt8 = len(_ax8.patches)\n"
            "        plt.close(_fig8)\n"
            "\n"
            "        assert _cnt8 >= _cnt4, \\\n"
            "            f'bins=8 should give >= bars than bins=4 ({_cnt8} vs {_cnt4})'\n"
            "        passed += 1; print(f'\\u2705 Check 3: bins=4 gives {_cnt4} bars, bins=8 gives {_cnt8}')\n"
            "    except Exception as e:\n"
            "        plt.close('all'); print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: ylabel is 'Count', title and xlabel are set\n"
            "    try:\n"
            "        _fig, _ax = plt.subplots()\n"
            "        histogram(_ax, _DATA, bins=5,\n"
            "                  title='Revenue Dist', xlabel='Revenue ($)')\n"
            "        assert _ax.get_ylabel() == 'Count', \\\n"
            "            f'ylabel={_ax.get_ylabel()!r}, expected \"Count\"'\n"
            "        assert _ax.get_title() == 'Revenue Dist'\n"
            "        assert _ax.get_xlabel() == 'Revenue ($)'\n"
            "        plt.close(_fig)\n"
            "        passed += 1; print('\\u2705 Check 4: ylabel=\"Count\", title and xlabel set')\n"
            "    except Exception as e:\n"
            "        plt.close('all'); print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: figure saves to a valid PNG\n"
            "    _tmp = '/tmp/day039_ex04.png'\n"
            "    try:\n"
            "        _fig, _ax = plt.subplots()\n"
            "        histogram(_ax, _DATA, bins=5,\n"
            "                  title='Revenue Distribution', xlabel='Revenue ($)')\n"
            "        _fig.savefig(_tmp, bbox_inches='tight', dpi=72)\n"
            "        plt.close(_fig)\n"
            "        assert os.path.exists(_tmp) and os.path.getsize(_tmp) > 1000\n"
            "        with open(_tmp, 'rb') as f:\n"
            "            assert f.read(4) == b'\\x89PNG'\n"
            "        os.remove(_tmp)\n"
            "        passed += 1; print('\\u2705 Check 5: figure saves as a valid PNG')\n"
            "    except Exception as e:\n"
            "        plt.close('all')\n"
            "        if os.path.exists(_tmp): os.remove(_tmp)\n"
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
            + HISTOGRAM_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 05 — multi_chart_figure
# ---------------------------------------------------------------------------

def ex05():
    global _cid; _cid = 400
    return [
        md(
            "# Day 039 — Exercise 5: multi_chart_figure\n\n"
            "**What you'll build:** `multi_chart_figure(df, out_path) -> out_path` — "
            "compose a 2×2 subplot dashboard using all four chart functions, save it as a PNG, "
            "close the figure, and return the saved path.\n\n"
            "**Why it matters:** Dashboards are the deliverable — they combine multiple "
            "perspectives (ranking, trend, correlation, distribution) into one page. "
            "plt.subplots(2, 2) creates a grid of Axes; you fill each cell, "
            "call tight_layout to prevent overlap, then save and close."
        ),
        md("## Provided: All Four Chart Functions"),
        code(ALL_IMPLS),
        code(SETUP_CODE + "\n\n" + RETAIL_CSV_CODE),
        md("## Your Implementation"),
        code(
            "def multi_chart_figure(df, out_path='dashboard.png'):\n"
            '    """\n'
            "    Create a 2×2 subplot dashboard and save it to out_path.\n\n"
            "    Layout:\n"
            "        [0,0] bar_chart   — revenue by product (groupby + sum)\n"
            "        [0,1] line_chart  — cumulative revenue (sort by order_id, cumsum)\n"
            "        [1,0] scatter_chart — price vs revenue\n"
            "        [1,1] histogram   — revenue distribution (bins=8)\n\n"
            "    Args:\n"
            "        df       — DataFrame with columns: order_id, product, price, revenue\n"
            "        out_path — file path to save the PNG\n"
            "    Returns:\n"
            "        out_path — the path the figure was saved to\n"
            '    """\n'
            "    # TODO: fig, axes = plt.subplots(2, 2, figsize=(12, 10))\n"
            "    # TODO: fill axes[0, 0] with bar_chart (revenue by product)\n"
            "    # TODO: fill axes[0, 1] with line_chart (cumulative revenue)\n"
            "    # TODO: fill axes[1, 0] with scatter_chart (price vs revenue)\n"
            "    # TODO: fill axes[1, 1] with histogram (revenue distribution, bins=8)\n"
            "    # TODO: fig.suptitle('Sales Dashboard', fontsize=16)\n"
            "    # TODO: plt.tight_layout()\n"
            "    # TODO: fig.savefig(out_path, bbox_inches='tight', dpi=100)\n"
            "    # TODO: plt.close(fig)  — important: prevents figure accumulation\n"
            "    # TODO: return out_path\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "    _tmp = '/tmp/day039_ex05.png'\n"
            "\n"
            "    # Check 1: defined and callable without crashing\n"
            "    try:\n"
            "        assert 'multi_chart_figure' in globals()\n"
            "        plt.close('all')\n"
            "        multi_chart_figure(SALES_DF, _tmp)\n"
            "        passed += 1; print('\\u2705 Check 1: multi_chart_figure is defined and callable')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        plt.close('all')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: output file is created\n"
            "    try:\n"
            "        assert os.path.exists(_tmp), \\\n"
            "            f'no file created at {_tmp} — did you call fig.savefig(out_path)?'\n"
            "        passed += 1; print(f'\\u2705 Check 2: output file created at {_tmp}')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 3: file is a valid PNG\n"
            "    try:\n"
            "        with open(_tmp, 'rb') as f:\n"
            "            _magic = f.read(4)\n"
            "        assert _magic == b'\\x89PNG', \\\n"
            "            f'not a valid PNG (magic bytes={_magic!r})'\n"
            "        passed += 1; print('\\u2705 Check 3: file is a valid PNG')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: file size implies multi-panel content (> 10 KB)\n"
            "    try:\n"
            "        _sz = os.path.getsize(_tmp)\n"
            "        assert _sz > 10000, \\\n"
            "            f'file too small ({_sz} bytes) — expected a 2x2 dashboard > 10 KB'\n"
            "        passed += 1; print(f'\\u2705 Check 4: file size {_sz:,} bytes (multi-panel confirmed)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: no lingering figures (plt.close called inside function)\n"
            "    try:\n"
            "        plt.close('all')\n"
            "        multi_chart_figure(SALES_DF, _tmp)  # call again on clean state\n"
            "        _open = plt.get_fignums()\n"
            "        assert len(_open) == 0, \\\n"
            "            f'{len(_open)} figure(s) still open — call plt.close(fig) inside the function'\n"
            "        passed += 1; print('\\u2705 Check 5: no lingering figures (plt.close called inside)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "    finally:\n"
            "        plt.close('all')\n"
            "        if os.path.exists(_tmp): os.remove(_tmp)\n"
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
            + MULTI_CHART_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Project notebook
# ---------------------------------------------------------------------------

def project_nb():
    global _cid; _cid = 500
    all_code = ALL_IMPLS + "\n\n\n" + MULTI_CHART_IMPL
    return [
        md(
            "# Day 039 Project: Chart Dashboard\n\n"
            "## What You're Building\n\n"
            "A four-panel chart dashboard saved to `chart_dashboard.png` — "
            "bar, line, scatter, and histogram panels, each showing a different "
            "perspective on the retail sales dataset.\n\n"
            "**Deliverable:** You run every cell top-to-bottom. The final checks pass. "
            "A file named `chart_dashboard.png` exists in the current directory.\n\n"
            "## Project Requirements\n\n"
            "1. Load `RETAIL_CSV` (provided) into a DataFrame with a `revenue` column\n"
            "2. Build your bar chart: top products by revenue\n"
            "3. Build your line chart: cumulative revenue over orders\n"
            "4. Build your scatter chart: price vs revenue\n"
            "5. Build your histogram: distribution of revenue values\n"
            "6. Compose all four into a 2×2 dashboard and save as `chart_dashboard.png`\n"
            "7. Verify with `_run_project_checks()`"
        ),
        code(
            "import warnings\n"
            "warnings.filterwarnings('ignore')\n"
            "import os\n"
            "import io\n"
            "import matplotlib\n"
            "matplotlib.use('Agg')\n"
            "import matplotlib.pyplot as plt\n"
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
            "print(f'Loaded {len(df)} rows × {len(df.columns)} columns')"
        ),
        md("## Your Dashboard"),
        code(
            "# TODO: Build your chart dashboard\n"
            "# Option A — call multi_chart_figure directly:\n"
            "# out = multi_chart_figure(df, 'chart_dashboard.png')\n"
            "# print(f'Saved to {out}')\n"
            "\n"
            "# Option B — build it manually for more control:\n"
            "# fig, axes = plt.subplots(2, 2, figsize=(12, 10))\n"
            "# bar_chart(axes[0, 0], ...)\n"
            "# line_chart(axes[0, 1], ...)\n"
            "# scatter_chart(axes[1, 0], ...)\n"
            "# histogram(axes[1, 1], ...)\n"
            "# fig.suptitle('Sales Dashboard', fontsize=16)\n"
            "# plt.tight_layout()\n"
            "# fig.savefig('chart_dashboard.png', bbox_inches='tight', dpi=100)\n"
            "# plt.close(fig)"
        ),
        md("## Project Checks"),
        code(
            "def _run_project_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "    _out = 'chart_dashboard.png'\n"
            "\n"
            "    # Check 1: df has revenue column\n"
            "    try:\n"
            "        assert 'df' in globals() and 'revenue' in df.columns, \\\n"
            "            \"'revenue' column missing\"\n"
            "        passed += 1; print(f'\\u2705 Check 1: df loaded with revenue ({len(df)} rows)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "\n"
            "    # Check 2: chart_dashboard.png exists\n"
            "    try:\n"
            "        assert os.path.exists(_out), \\\n"
            "            f'{_out!r} not found — did you call fig.savefig({_out!r})?'\n"
            "        passed += 1; print(f'\\u2705 Check 2: {_out} exists')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 3: valid PNG\n"
            "    try:\n"
            "        with open(_out, 'rb') as f:\n"
            "            _magic = f.read(4)\n"
            "        assert _magic == b'\\x89PNG'\n"
            "        passed += 1; print('\\u2705 Check 3: valid PNG file')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: file size > 10 KB (multi-panel content)\n"
            "    try:\n"
            "        _sz = os.path.getsize(_out)\n"
            "        assert _sz > 10000, \\\n"
            "            f'file too small ({_sz} bytes) — multi-panel should exceed 10 KB'\n"
            "        passed += 1; print(f'\\u2705 Check 4: file size {_sz:,} bytes')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: no open figures (all closed)\n"
            "    try:\n"
            "        _open = plt.get_fignums()\n"
            "        assert len(_open) == 0, \\\n"
            "            f'{len(_open)} figure(s) still open — call plt.close() after savefig'\n"
            "        passed += 1; print('\\u2705 Check 5: no lingering open figures')\n"
            "    except Exception as e:\n"
            "        plt.close('all')\n"
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
            "- Add colour: pass a `color=` or `cmap=` argument to bar/scatter\n"
            "- Sort the bar chart by revenue descending before plotting\n"
            "- Add a second line series to the line chart (e.g. separate Widget and Gadget revenue "
            "over time) by calling `line_chart` twice on the same ax with different labels\n"
            "- Annotate the scatter plot: `ax.annotate('Gadget', xy=(150, 1050), ...)` "
            "to label the highest-revenue point\n"
            "- Try `plt.style.use('seaborn-v0_8')` at the top for a cleaner look\n"
            "- On Day 40 you will ask an LLM to narrate these charts — keep `df` handy"
        ),
    ]


# ---------------------------------------------------------------------------
# Solution notebook
# ---------------------------------------------------------------------------

def solution_nb():
    global _cid; _cid = 600
    all_code = ALL_IMPLS + "\n\n\n" + MULTI_CHART_IMPL
    return [
        md(
            "# Day 039 Solution — Chart Dashboard\n\n"
            "bar_chart, line_chart, scatter_chart, histogram, and multi_chart_figure. "
            "All data defined inline. Saves `chart_dashboard.png`."
        ),
        code(
            "import warnings\n"
            "warnings.filterwarnings('ignore')\n"
            "import os\n"
            "import io\n"
            "import matplotlib\n"
            "matplotlib.use('Agg')\n"
            "import matplotlib.pyplot as plt\n"
            "import pandas as pd\n"
            "\n"
            + all_code
        ),
        md("## Step 1 — Load Data"),
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
            "print(df[['product', 'price', 'quantity', 'revenue']].to_string(index=False))\n"
            "\n"
            "assert df.shape == (12, 7)\n"
            "assert 'revenue' in df.columns"
        ),
        md("## Step 2 — Individual Charts"),
        code(
            "# Bar chart — revenue by product\n"
            "_fig, _ax = plt.subplots(figsize=(7, 4))\n"
            "totals = df.groupby('product')['revenue'].sum().sort_values(ascending=False)\n"
            "bar_chart(_ax, totals.index.tolist(), totals.values.tolist(),\n"
            "          'Revenue by Product', 'Product', 'Revenue ($)')\n"
            "_fig.savefig('/tmp/day039_bar.png', bbox_inches='tight', dpi=72)\n"
            "plt.close(_fig)\n"
            "print('bar_chart: saved')\n"
            "\n"
            "# Line chart — cumulative revenue\n"
            "_fig, _ax = plt.subplots(figsize=(7, 4))\n"
            "df_s = df.sort_values('order_id').reset_index(drop=True)\n"
            "line_chart(_ax, list(range(1, len(df_s) + 1)),\n"
            "           df_s['revenue'].cumsum().tolist(),\n"
            "           'Cumulative Revenue', 'Order #', 'Revenue ($)', label='cumulative')\n"
            "_fig.savefig('/tmp/day039_line.png', bbox_inches='tight', dpi=72)\n"
            "plt.close(_fig)\n"
            "print('line_chart: saved')\n"
            "\n"
            "# Scatter chart — price vs revenue\n"
            "_fig, _ax = plt.subplots(figsize=(7, 4))\n"
            "scatter_chart(_ax, df['price'].tolist(), df['revenue'].tolist(),\n"
            "              'Price vs Revenue', 'Price ($)', 'Revenue ($)')\n"
            "_fig.savefig('/tmp/day039_scatter.png', bbox_inches='tight', dpi=72)\n"
            "plt.close(_fig)\n"
            "print('scatter_chart: saved')\n"
            "\n"
            "# Histogram — revenue distribution\n"
            "_fig, _ax = plt.subplots(figsize=(7, 4))\n"
            "histogram(_ax, df['revenue'].tolist(), bins=8,\n"
            "          title='Revenue Distribution', xlabel='Revenue ($)')\n"
            "_fig.savefig('/tmp/day039_hist.png', bbox_inches='tight', dpi=72)\n"
            "plt.close(_fig)\n"
            "print('histogram: saved')\n"
            "\n"
            "assert len(plt.get_fignums()) == 0, 'all figures should be closed'"
        ),
        md("## Step 3 — Dashboard (2×2)"),
        code(
            "out = multi_chart_figure(df, 'chart_dashboard.png')\n"
            "print(f'Dashboard saved to: {out}')\n"
            "\n"
            "assert os.path.exists('chart_dashboard.png')\n"
            "sz = os.path.getsize('chart_dashboard.png')\n"
            "assert sz > 10000, f'file too small: {sz} bytes'\n"
            "with open('chart_dashboard.png', 'rb') as f:\n"
            "    assert f.read(4) == b'\\x89PNG'\n"
            "assert len(plt.get_fignums()) == 0\n"
            "print(f'Dashboard verified: {sz:,} bytes, valid PNG, no open figures')"
        ),
        md("## Step 4 — Individual Chart Verification"),
        code(
            "# Verify each chart type's properties independently\n"
            "_fig, _ax = plt.subplots()\n"
            "bar_chart(_ax, ['A', 'B', 'C'], [10, 20, 15], 'Test', 'X', 'Y')\n"
            "assert len(_ax.patches) == 3\n"
            "assert _ax.get_title() == 'Test'\n"
            "plt.close(_fig)\n"
            "print('bar_chart: 3 bars, title correct')\n"
            "\n"
            "_fig, _ax = plt.subplots()\n"
            "line_chart(_ax, [1, 2, 3], [10, 20, 15], label='s')\n"
            "assert len(_ax.get_lines()) >= 1\n"
            "assert _ax.get_legend() is not None\n"
            "plt.close(_fig)\n"
            "print('line_chart: line + legend correct')\n"
            "\n"
            "_fig, _ax = plt.subplots()\n"
            "scatter_chart(_ax, [1, 2, 3], [4, 5, 6])\n"
            "assert len(_ax.collections) >= 1\n"
            "assert _ax.collections[0].get_offsets().shape[0] == 3\n"
            "plt.close(_fig)\n"
            "print('scatter_chart: 3 points correct')\n"
            "\n"
            "_fig, _ax = plt.subplots()\n"
            "histogram(_ax, [1, 2, 3, 4, 5, 6, 7, 8], bins=4)\n"
            "assert len(_ax.patches) > 0\n"
            "assert _ax.get_ylabel() == 'Count'\n"
            "plt.close(_fig)\n"
            "print('histogram: bars + Count label correct')\n"
            "\n"
            "print('\\nAll charts verified!')"
        ),
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Generating Day 039 notebooks...")
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
