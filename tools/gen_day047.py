#!/usr/bin/env python3
"""Generate all Day 047 notebooks: exercises 1-5, project, solution."""
import json
from pathlib import Path

ROOT    = Path(__file__).resolve().parent.parent
DAY_DIR = ROOT / "03_data_analysis" / "day_047"

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
            "language_info": {"name": "python", "version": "3.10.0"},
        },
        "cells": cells,
    }


def write_nb(path: Path, cells: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(nb(cells), indent=1), encoding="utf-8")
    print(f"  wrote {path.relative_to(ROOT)}")


# ---------------------------------------------------------------------------
# Shared data-generation helper (Provided cells only)
# ---------------------------------------------------------------------------

MAKE_SAMPLE_DATA = """\
import pandas as pd
import numpy as np
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

def make_sample_data(n: int = 100, seed: int = 42) -> pd.DataFrame:
    \"\"\"Return a reproducible multi-column dataset for statistics exercises.\"\"\"
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        'normal_col': rng.standard_normal(n).round(3),
        'skewed_col': rng.exponential(2, n).round(3),
        'score_a':    (50 + rng.standard_normal(n) * 10).round(1),
        'score_b':    (70 + rng.standard_normal(n) * 10).round(1),
    })"""

# ---------------------------------------------------------------------------
# Implementations
# ---------------------------------------------------------------------------

DESCRIBE_DIST_IMPL = """\
def describe_distribution(series: pd.Series) -> dict:
    s   = series.dropna()
    q25 = float(s.quantile(0.25))
    q75 = float(s.quantile(0.75))
    return {
        'count':    int(len(s)),
        'mean':     round(float(s.mean()), 4),
        'median':   round(float(s.median()), 4),
        'std':      round(float(s.std(ddof=1)), 4),
        'sem':      round(float(s.sem()), 4),
        'min':      round(float(s.min()), 4),
        'max':      round(float(s.max()), 4),
        'q25':      round(q25, 4),
        'q75':      round(q75, 4),
        'iqr':      round(q75 - q25, 4),
        'skewness': round(float(s.skew()), 4),
        'kurtosis': round(float(s.kurt()), 4),
    }"""

NORMALITY_IMPL = """\
def test_normality(series: pd.Series, alpha: float = 0.05) -> dict:
    s      = series.dropna()
    stat, p = stats.shapiro(s)
    return {
        'n':          len(s),
        'statistic':  round(float(stat), 4),
        'p_value':    round(float(p), 6),
        'is_normal':  bool(p > alpha),
        'alpha':      alpha,
    }"""

CORR_IMPL = """\
def correlation_with_pvalue(x: pd.Series, y: pd.Series,
                             method: str = 'pearson') -> dict:
    mask  = x.notna() & y.notna()
    x_c, y_c = x[mask], y[mask]
    if method == 'pearson':
        r, p = stats.pearsonr(x_c, y_c)
    elif method == 'spearman':
        r, p = stats.spearmanr(x_c, y_c)
    else:
        raise ValueError(f"method must be 'pearson' or 'spearman', got {method!r}")
    return {
        'method':         method,
        'n':              len(x_c),
        'r':              round(float(r), 4),
        'p_value':        round(float(p), 6),
        'is_significant': bool(p < 0.05),
    }"""

GROUPS_IMPL = """\
def compare_groups(a: pd.Series, b: pd.Series,
                   alpha: float = 0.05) -> dict:
    a_c, b_c  = a.dropna(), b.dropna()
    t, p       = stats.ttest_ind(a_c, b_c)
    n_a, n_b   = len(a_c), len(b_c)
    std_a      = float(a_c.std(ddof=1))
    std_b      = float(b_c.std(ddof=1))
    pooled_var = ((n_a - 1) * std_a**2 + (n_b - 1) * std_b**2) / (n_a + n_b - 2)
    pooled     = np.sqrt(pooled_var) if pooled_var > 0 else 0.0
    d          = (float(a_c.mean()) - float(b_c.mean())) / pooled if pooled > 0 else 0.0
    sig        = bool(p < alpha)
    return {
        'n_a':            n_a,
        'n_b':            n_b,
        'mean_a':         round(float(a_c.mean()), 4),
        'mean_b':         round(float(b_c.mean()), 4),
        'statistic':      round(float(t), 4),
        'p_value':        round(float(p), 6),
        'is_significant': sig,
        'cohens_d':       round(d, 4),
        'conclusion':     'different' if sig else 'not_different',
    }"""

STATS_REPORT_IMPL = """\
class StatsReport:
    def __init__(self):
        self._df      = None
        self._columns = None

    def load(self, df: pd.DataFrame,
             columns: list | None = None) -> 'StatsReport':
        self._df      = df.copy()
        num_cols      = df.select_dtypes(include='number').columns.tolist()
        self._columns = columns if columns is not None else num_cols
        return self

    def report(self) -> dict:
        result = {}
        for col in self._columns:
            if col not in self._df.columns:
                continue
            s = self._df[col].dropna()
            if len(s) < 3:
                continue
            result[col] = {
                'distribution': describe_distribution(s),
                'normality':    test_normality(s),
            }
        return result"""

# Cumulative provided snippets
_BEFORE_NORMALITY = "\n\n\n".join([MAKE_SAMPLE_DATA, DESCRIBE_DIST_IMPL])
_BEFORE_CORR      = "\n\n\n".join([MAKE_SAMPLE_DATA, DESCRIBE_DIST_IMPL, NORMALITY_IMPL])
_BEFORE_GROUPS    = "\n\n\n".join([MAKE_SAMPLE_DATA, DESCRIBE_DIST_IMPL, NORMALITY_IMPL, CORR_IMPL])
ALL_IMPLS         = "\n\n\n".join([
    MAKE_SAMPLE_DATA, DESCRIBE_DIST_IMPL, NORMALITY_IMPL, CORR_IMPL, GROUPS_IMPL,
])


# ---------------------------------------------------------------------------
# Exercise 01 — describe_distribution
# ---------------------------------------------------------------------------

def ex01():
    global _cid; _cid = 0
    return [
        md(
            "# Day 047 — Exercise 1: describe_distribution\n\n"
            "**What you'll build:** `describe_distribution(series) -> dict` — "
            "extend pandas' `describe()` with skewness, kurtosis, standard error of the mean "
            "(SEM), and interquartile range (IQR), all in one dict.\n\n"
            "**Why it matters:** `df.describe()` gives mean and std — but not shape. "
            "Skewness tells you if the distribution leans left or right. Kurtosis tells you "
            "how heavy the tails are. SEM tells you how uncertain the sample mean is. "
            "Together they give you a complete picture of a variable's distribution."
        ),
        md("## Provided: Sample Data Generator"),
        code(MAKE_SAMPLE_DATA),
        md("## Your Implementation"),
        code(
            "def describe_distribution(series: pd.Series) -> dict:\n"
            '    """\n'
            "    Extended descriptive statistics beyond df.describe().\n\n"
            "    Args:\n"
            "        series: numeric pd.Series (NaN values are dropped)\n"
            "    Returns:\n"
            "        dict with keys: count, mean, median, std, sem, min, max,\n"
            "                        q25, q75, iqr, skewness, kurtosis\n"
            '    """\n'
            "    s   = series.dropna()\n"
            "    q25 = float(s.quantile(0.25))\n"
            "    q75 = float(s.quantile(0.75))\n"
            "    # TODO: return {\n"
            "    #     'count':    int(len(s)),\n"
            "    #     'mean':     round(float(s.mean()), 4),\n"
            "    #     'median':   round(float(s.median()), 4),\n"
            "    #     'std':      round(float(s.std(ddof=1)), 4),\n"
            "    #     'sem':      round(float(s.sem()), 4),\n"
            "    #     'min':      round(float(s.min()), 4),\n"
            "    #     'max':      round(float(s.max()), 4),\n"
            "    #     'q25':      round(q25, 4),\n"
            "    #     'q75':      round(q75, 4),\n"
            "    #     'iqr':      round(q75 - q25, 4),\n"
            "    #     'skewness': round(float(s.skew()), 4),\n"
            "    #     'kurtosis': round(float(s.kurt()), 4),\n"
            "    # }\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    df = make_sample_data(100)\n"
            "\n"
            "    # Check 1: defined, returns dict\n"
            "    try:\n"
            "        assert 'describe_distribution' in globals()\n"
            "        result = describe_distribution(df['normal_col'])\n"
            "        assert isinstance(result, dict), \\\n"
            "            f'expected dict, got {type(result).__name__}'\n"
            "        passed += 1; print('\\u2705 Check 1: describe_distribution returns dict')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: all required keys present\n"
            "    try:\n"
            "        required = ('count', 'mean', 'median', 'std', 'sem',\n"
            "                    'min', 'max', 'q25', 'q75', 'iqr', 'skewness', 'kurtosis')\n"
            "        for k in required:\n"
            "            assert k in result, f'missing key: {k!r}'\n"
            "        passed += 1; print('\\u2705 Check 2: all 12 keys present')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: count == 100\n"
            "    try:\n"
            "        assert result['count'] == 100, \\\n"
            "            f'count should be 100, got {result[\"count\"]}'\n"
            "        passed += 1; print('\\u2705 Check 3: count == 100')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: IQR == q75 - q25\n"
            "    try:\n"
            "        expected_iqr = round(result['q75'] - result['q25'], 4)\n"
            "        assert abs(result['iqr'] - expected_iqr) < 1e-4, \\\n"
            "            f'iqr should be q75-q25={expected_iqr:.4f}, got {result[\"iqr\"]}'\n"
            "        passed += 1; print('\\u2705 Check 4: iqr == q75 - q25')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: skewed_col has positive skewness (exponential distribution)\n"
            "    try:\n"
            "        r_skew = describe_distribution(df['skewed_col'])\n"
            "        assert r_skew['skewness'] > 0, \\\n"
            "            f'exponential column should be right-skewed (> 0), got {r_skew[\"skewness\"]}'\n"
            "        passed += 1; print(f'\\u2705 Check 5: skewed_col skewness={r_skew[\"skewness\"]:.4f} > 0 (right-skewed)')\n"
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
            + DESCRIBE_DIST_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 02 — test_normality
# ---------------------------------------------------------------------------

def ex02():
    global _cid; _cid = 100
    return [
        md(
            "# Day 047 — Exercise 2: test_normality\n\n"
            "**What you'll build:** `test_normality(series, alpha=0.05) -> dict` — "
            "run the Shapiro-Wilk normality test (`scipy.stats.shapiro`) and return the "
            "statistic, p-value, and a boolean `is_normal` (True if p > alpha).\n\n"
            "**Why it matters:** Many statistical methods assume normally distributed data. "
            "A normality test lets you check that assumption before relying on it. "
            "Knowing your data is right-skewed changes how you summarise it "
            "(median > mean) and which downstream operations are appropriate."
        ),
        md("## Provided: Setup + describe_distribution"),
        code(_BEFORE_NORMALITY),
        md("## Your Implementation"),
        code(
            "def test_normality(series: pd.Series, alpha: float = 0.05) -> dict:\n"
            '    """\n'
            "    Shapiro-Wilk normality test (best for n <= 5000).\n\n"
            "    Args:\n"
            "        series: numeric pd.Series (NaN values are dropped)\n"
            "        alpha:  significance level (default 0.05)\n"
            "    Returns:\n"
            "        dict with keys: n, statistic, p_value, is_normal, alpha\n"
            "        is_normal is True when p_value > alpha.\n"
            '    """\n'
            "    s       = series.dropna()\n"
            "    # TODO: stat, p = stats.shapiro(s)\n"
            "    # TODO: return {\n"
            "    #     'n':          len(s),\n"
            "    #     'statistic':  round(float(stat), 4),\n"
            "    #     'p_value':    round(float(p), 6),\n"
            "    #     'is_normal':  bool(p > alpha),\n"
            "    #     'alpha':      alpha,\n"
            "    # }\n"
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
            "        assert 'test_normality' in globals()\n"
            "        rng = np.random.default_rng(0)\n"
            "        normal_data = pd.Series(rng.standard_normal(200))\n"
            "        result = test_normality(normal_data)\n"
            "        assert isinstance(result, dict), \\\n"
            "            f'expected dict, got {type(result).__name__}'\n"
            "        passed += 1; print('\\u2705 Check 1: test_normality returns dict')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: all required keys\n"
            "    try:\n"
            "        for k in ('n', 'statistic', 'p_value', 'is_normal', 'alpha'):\n"
            "            assert k in result, f'missing key: {k!r}'\n"
            "        passed += 1; print('\\u2705 Check 2: all required keys present')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: is_normal is bool\n"
            "    try:\n"
            "        assert isinstance(result['is_normal'], bool), \\\n"
            "            f'is_normal must be bool, got {type(result[\"is_normal\"]).__name__}'\n"
            "        passed += 1; print('\\u2705 Check 3: is_normal is bool')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: normal data (seed=0, n=200) → is_normal=True\n"
            "    try:\n"
            "        assert result['is_normal'] is True, \\\n"
            "            f'standard_normal(200,seed=0) should pass normality test, p={result[\"p_value\"]}'\n"
            "        passed += 1; print(f'\\u2705 Check 4: normal data passes test (p={result[\"p_value\"]})')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: exponential data (seed=0, n=100) → is_normal=False\n"
            "    try:\n"
            "        expo_data = pd.Series(np.random.default_rng(0).exponential(2, 100))\n"
            "        r_expo = test_normality(expo_data)\n"
            "        assert r_expo['is_normal'] is False, \\\n"
            "            f'exponential data should fail normality test, p={r_expo[\"p_value\"]}'\n"
            "        passed += 1; print(f'\\u2705 Check 5: skewed data fails test (p={r_expo[\"p_value\"]:.2e})')\n"
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
            + NORMALITY_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 03 — correlation_with_pvalue
# ---------------------------------------------------------------------------

def ex03():
    global _cid; _cid = 200
    return [
        md(
            "# Day 047 — Exercise 3: correlation_with_pvalue\n\n"
            "**What you'll build:** `correlation_with_pvalue(x, y, method='pearson') -> dict` — "
            "compute the Pearson or Spearman correlation coefficient together with its "
            "p-value, so you know both the strength and the statistical reliability of "
            "the relationship.\n\n"
            "**Why it matters:** `df.corr()` gives you r but not a p-value, so you can't "
            "tell if a correlation of 0.3 is real or just noise. Adding the p-value answers "
            "'is this relationship real?' — not just 'how strong is it?'."
        ),
        md("## Provided: Setup + describe_distribution + test_normality"),
        code(_BEFORE_CORR),
        md("## Your Implementation"),
        code(
            "def correlation_with_pvalue(x: pd.Series, y: pd.Series,\n"
            "                             method: str = 'pearson') -> dict:\n"
            '    """\n'
            "    Pearson or Spearman correlation with p-value.\n\n"
            "    Args:\n"
            "        x, y:   numeric pd.Series (NaN pairs are dropped together)\n"
            "        method: 'pearson' (linear) or 'spearman' (rank-based)\n"
            "    Returns:\n"
            "        dict with keys: method, n, r, p_value, is_significant\n"
            "        is_significant is True when p_value < 0.05.\n"
            '    """\n'
            "    mask  = x.notna() & y.notna()\n"
            "    x_c, y_c = x[mask], y[mask]\n"
            "    # TODO: if method == 'pearson':\n"
            "    #     r, p = stats.pearsonr(x_c, y_c)\n"
            "    # elif method == 'spearman':\n"
            "    #     r, p = stats.spearmanr(x_c, y_c)\n"
            "    # else:\n"
            "    #     raise ValueError(f\"method must be 'pearson' or 'spearman', got {method!r}\")\n"
            "    # TODO: return {\n"
            "    #     'method':         method,\n"
            "    #     'n':              len(x_c),\n"
            "    #     'r':              round(float(r), 4),\n"
            "    #     'p_value':        round(float(p), 6),\n"
            "    #     'is_significant': bool(p < 0.05),\n"
            "    # }\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    x = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])\n"
            "    y = x * 2 + 3   # perfectly correlated\n"
            "\n"
            "    # Check 1: defined, returns dict\n"
            "    try:\n"
            "        assert 'correlation_with_pvalue' in globals()\n"
            "        result = correlation_with_pvalue(x, y)\n"
            "        assert isinstance(result, dict), \\\n"
            "            f'expected dict, got {type(result).__name__}'\n"
            "        passed += 1; print('\\u2705 Check 1: correlation_with_pvalue returns dict')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: all required keys\n"
            "    try:\n"
            "        for k in ('method', 'n', 'r', 'p_value', 'is_significant'):\n"
            "            assert k in result, f'missing key: {k!r}'\n"
            "        passed += 1; print('\\u2705 Check 2: all required keys present')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: r is in [-1, 1]\n"
            "    try:\n"
            "        r = result['r']\n"
            "        assert -1.0 <= r <= 1.0, f'r must be in [-1, 1], got {r}'\n"
            "        passed += 1; print(f'\\u2705 Check 3: r={r:.4f} is in [-1, 1]')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: perfect positive correlation → r≈1.0 and is_significant=True\n"
            "    try:\n"
            "        assert abs(result['r'] - 1.0) < 1e-4, \\\n"
            "            f'y=2x+3 should give r≈1.0, got {result[\"r\"]}'\n"
            "        assert result['is_significant'] is True, \\\n"
            "            f'perfect correlation should be significant'\n"
            "        passed += 1; print(f'\\u2705 Check 4: perfect correlation r=1.0, is_significant=True')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: Spearman on same data also gives r≈1.0\n"
            "    try:\n"
            "        r_sp = correlation_with_pvalue(x, y, method='spearman')\n"
            "        assert abs(r_sp['r'] - 1.0) < 1e-4, \\\n"
            "            f'Spearman of y=2x+3 should also be ≈1.0, got {r_sp[\"r\"]}'\n"
            "        assert r_sp['method'] == 'spearman'\n"
            "        passed += 1; print(f'\\u2705 Check 5: Spearman r={r_sp[\"r\"]:.4f}')\n"
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
            + CORR_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 04 — compare_groups
# ---------------------------------------------------------------------------

def ex04():
    global _cid; _cid = 300
    return [
        md(
            "# Day 047 — Exercise 4: compare_groups\n\n"
            "**What you'll build:** `compare_groups(a, b, alpha=0.05) -> dict` — "
            "independent-samples t-test (`scipy.stats.ttest_ind`) plus Cohen's d effect size, "
            "returning whether the groups are statistically different and how large the "
            "difference is.\n\n"
            "**Why it matters:** Knowing two group means differ is one thing; knowing "
            "*how much* they differ (effect size) is another. Cohen's d tells you if "
            "the difference is negligible (|d| < 0.2), small (0.2–0.5), medium (0.5–0.8), "
            "or large (> 0.8) — independent of sample size."
        ),
        md("## Provided: Setup + all prior functions"),
        code(_BEFORE_GROUPS),
        md("## Your Implementation"),
        code(
            "def compare_groups(a: pd.Series, b: pd.Series,\n"
            "                   alpha: float = 0.05) -> dict:\n"
            '    """\n'
            "    Independent-samples t-test + Cohen's d effect size.\n\n"
            "    Args:\n"
            "        a, b:  two numeric pd.Series to compare (NaN values are dropped)\n"
            "        alpha: significance level (default 0.05)\n"
            "    Returns:\n"
            "        dict with keys: n_a, n_b, mean_a, mean_b, statistic, p_value,\n"
            "                        is_significant, cohens_d, conclusion\n"
            "        conclusion: 'different' if p_value < alpha, else 'not_different'\n"
            "        cohens_d: (mean_a - mean_b) / pooled_std (signed)\n"
            '    """\n'
            "    a_c, b_c = a.dropna(), b.dropna()\n"
            "    # TODO: t, p = stats.ttest_ind(a_c, b_c)\n"
            "    # TODO: n_a, n_b = len(a_c), len(b_c)\n"
            "    # TODO: std_a = float(a_c.std(ddof=1))\n"
            "    # TODO: std_b = float(b_c.std(ddof=1))\n"
            "    # TODO: pooled_var = ((n_a - 1) * std_a**2 + (n_b - 1) * std_b**2) / (n_a + n_b - 2)\n"
            "    # TODO: pooled = np.sqrt(pooled_var) if pooled_var > 0 else 0.0\n"
            "    # TODO: d = (float(a_c.mean()) - float(b_c.mean())) / pooled if pooled > 0 else 0.0\n"
            "    # TODO: sig = bool(p < alpha)\n"
            "    # TODO: return {\n"
            "    #     'n_a': n_a, 'n_b': n_b,\n"
            "    #     'mean_a': round(float(a_c.mean()), 4),\n"
            "    #     'mean_b': round(float(b_c.mean()), 4),\n"
            "    #     'statistic':      round(float(t), 4),\n"
            "    #     'p_value':        round(float(p), 6),\n"
            "    #     'is_significant': sig,\n"
            "    #     'cohens_d':       round(d, 4),\n"
            "    #     'conclusion':     'different' if sig else 'not_different',\n"
            "    # }\n"
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
            "        assert 'compare_groups' in globals()\n"
            "        a = pd.Series([4.9, 5.1, 5.0, 5.05, 4.95])\n"
            "        b = pd.Series([5.0, 4.95, 5.05, 5.0, 5.02])\n"
            "        result = compare_groups(a, b)\n"
            "        assert isinstance(result, dict), \\\n"
            "            f'expected dict, got {type(result).__name__}'\n"
            "        passed += 1; print('\\u2705 Check 1: compare_groups returns dict')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: all required keys\n"
            "    try:\n"
            "        for k in ('n_a', 'n_b', 'mean_a', 'mean_b', 'statistic',\n"
            "                  'p_value', 'is_significant', 'cohens_d', 'conclusion'):\n"
            "            assert k in result, f'missing key: {k!r}'\n"
            "        passed += 1; print('\\u2705 Check 2: all required keys present')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: conclusion is 'different' or 'not_different'\n"
            "    try:\n"
            "        assert result['conclusion'] in ('different', 'not_different'), \\\n"
            "            f'conclusion must be different/not_different, got {result[\"conclusion\"]!r}'\n"
            "        passed += 1; print(f'\\u2705 Check 3: conclusion={result[\"conclusion\"]!r}')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: similar groups → not_different\n"
            "    try:\n"
            "        assert result['conclusion'] == 'not_different', \\\n"
            "            f'groups with mean≈5.0 should be not_different (p={result[\"p_value\"]}), got {result[\"conclusion\"]!r}'\n"
            "        passed += 1; print(f'\\u2705 Check 4: similar groups → not_different (p={result[\"p_value\"]:.4f})')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: very different groups → different\n"
            "    try:\n"
            "        df = make_sample_data(100)\n"
            "        r5 = compare_groups(df['score_a'], df['score_b'])\n"
            "        assert r5['conclusion'] == 'different', \\\n"
            "            f'score_a (mean≈50) vs score_b (mean≈70) should be different, p={r5[\"p_value\"]}'\n"
            "        assert abs(r5['cohens_d']) > 1.0, \\\n"
            "            f'large effect expected (|d|>1), got {r5[\"cohens_d\"]}'\n"
            "        passed += 1; print(f'\\u2705 Check 5: different groups → different (d={r5[\"cohens_d\"]:.2f})')\n"
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
            + GROUPS_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 05 — StatsReport class
# ---------------------------------------------------------------------------

def ex05():
    global _cid; _cid = 400
    return [
        md(
            "# Day 047 — Exercise 5: StatsReport\n\n"
            "**What you'll build:** The `StatsReport` class — "
            "`load(df, columns=None) -> StatsReport` (fluent builder) and "
            "`report() -> dict` — run `describe_distribution` + `test_normality` on "
            "every numeric column and return the results as a nested dict.\n\n"
            "**Why it matters:** When you get a new dataset, the first thing you always do "
            "is characterise every column. `StatsReport` automates that: one `.load(df).report()` "
            "call gives you the full statistical picture of an entire DataFrame."
        ),
        md("## Provided: All Helper Functions"),
        code(ALL_IMPLS),
        md("## Your Implementation"),
        code(
            "class StatsReport:\n"
            '    """\n'
            "    Automated per-column statistical report.\n\n"
            "    Usage:\n"
            "        sr = StatsReport()\n"
            "        report = sr.load(df).report()\n"
            '    """\n'
            "\n"
            "    def __init__(self):\n"
            "        # TODO: self._df      = None\n"
            "        # TODO: self._columns = None\n"
            "        pass\n"
            "\n"
            "    def load(self, df: pd.DataFrame,\n"
            "             columns: list | None = None) -> 'StatsReport':\n"
            '        """\n'
            "        Store df and the columns to analyse.\n"
            "        If columns is None, use all numeric columns.\n"
            "        Returns self for fluent chaining.\n"
            '        """\n'
            "        # TODO: self._df      = df.copy()\n"
            "        # TODO: num_cols      = df.select_dtypes(include='number').columns.tolist()\n"
            "        # TODO: self._columns = columns if columns is not None else num_cols\n"
            "        # TODO: return self\n"
            "        pass\n"
            "\n"
            "    def report(self) -> dict:\n"
            '        """\n'
            "        Return {col: {'distribution': {...}, 'normality': {...}}} for each column.\n"
            "        Skip columns not in df or with fewer than 3 non-null values.\n"
            '        """\n'
            "        # TODO: result = {}\n"
            "        # TODO: for col in self._columns:\n"
            "        #     if col not in self._df.columns: continue\n"
            "        #     s = self._df[col].dropna()\n"
            "        #     if len(s) < 3: continue\n"
            "        #     result[col] = {\n"
            "        #         'distribution': describe_distribution(s),\n"
            "        #         'normality':    test_normality(s),\n"
            "        #     }\n"
            "        # TODO: return result\n"
            "        pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    df = make_sample_data(100)\n"
            "\n"
            "    # Check 1: class defined with load and report methods\n"
            "    try:\n"
            "        assert 'StatsReport' in globals()\n"
            "        for m in ('load', 'report'):\n"
            "            assert hasattr(StatsReport, m), f'missing method: {m}'\n"
            "        passed += 1; print('\\u2705 Check 1: StatsReport has load and report')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: load() returns self (fluent)\n"
            "    try:\n"
            "        sr  = StatsReport()\n"
            "        ret = sr.load(df)\n"
            "        assert ret is sr, f'load() must return self, got {type(ret).__name__}'\n"
            "        passed += 1; print('\\u2705 Check 2: load() returns self (fluent chaining)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 3: report() returns non-empty dict\n"
            "    try:\n"
            "        rep = sr.report()\n"
            "        assert isinstance(rep, dict), \\\n"
            "            f'report() should return dict, got {type(rep).__name__}'\n"
            "        assert len(rep) > 0, 'report() returned empty dict'\n"
            "        passed += 1; print(f'\\u2705 Check 3: report() returns dict with {len(rep)} entries')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 4: report keys are column names from the DataFrame\n"
            "    try:\n"
            "        for col in rep:\n"
            "            assert col in df.columns, f'unexpected column in report: {col!r}'\n"
            "        assert len(rep) == 4, f'expected 4 numeric columns, got {len(rep)}'\n"
            "        passed += 1; print(f'\\u2705 Check 4: 4 numeric columns reported')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: each entry has distribution and normality sub-dicts\n"
            "    try:\n"
            "        col = list(rep.keys())[0]\n"
            "        entry = rep[col]\n"
            "        assert 'distribution' in entry, f'missing distribution key'\n"
            "        assert 'normality'    in entry, f'missing normality key'\n"
            "        dist = entry['distribution']\n"
            "        norm = entry['normality']\n"
            "        assert 'count'    in dist, 'distribution missing count'\n"
            "        assert 'skewness' in dist, 'distribution missing skewness'\n"
            "        assert 'is_normal' in norm, 'normality missing is_normal'\n"
            "        passed += 1; print(f'\\u2705 Check 5: each entry has distribution + normality sub-dicts')\n"
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
            + STATS_REPORT_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Project notebook
# ---------------------------------------------------------------------------

def project_nb():
    global _cid; _cid = 500
    all_code = ALL_IMPLS + "\n\n\n" + STATS_REPORT_IMPL
    return [
        md(
            "# Day 047 Project: Stats Report\n\n"
            "## What You're Building\n\n"
            "A full statistical analysis of a multi-column dataset using `StatsReport`, "
            "`correlation_with_pvalue`, and `compare_groups`. The report is saved as a "
            "matplotlib figure with distribution plots and annotated group comparison.\n\n"
            "## Project Requirements\n\n"
            "1. Generate a dataset with at least 100 rows using `make_sample_data()`\n"
            "2. Run `StatsReport().load(df).report()` and store as `report`\n"
            "3. Print the skewness and is_normal flag for every column\n"
            "4. Run `compare_groups(df['score_a'], df['score_b'])` and store as `comparison`\n"
            "5. Run `correlation_with_pvalue` between at least one pair of columns\n"
            "6. Save a figure with at least 2 subplots (e.g. histograms, box plot)\n"
            "7. Run `_run_project_checks()` to verify\n\n"
            "You run it, it prints a stats summary and saves a chart. That is the deliverable."
        ),
        md("## Provided: All Implementations"),
        code(all_code),
        md("## Your Pipeline"),
        code(
            "import matplotlib\n"
            "matplotlib.use('Agg')\n"
            "import matplotlib.pyplot as plt\n"
            "\n"
            "df = make_sample_data(n=100, seed=42)\n"
            "\n"
            "# TODO: create and run StatsReport\n"
            "# report = StatsReport().load(df).report()\n"
            "# for col, entry in report.items():\n"
            "#     d = entry['distribution']\n"
            "#     n = entry['normality']\n"
            "#     print(f\"{col}: skew={d['skewness']:.2f} is_normal={n['is_normal']}\")\n"
            "\n"
            "# TODO: compare the two score groups\n"
            "# comparison = compare_groups(df['score_a'], df['score_b'])\n"
            "# print(comparison)\n"
            "\n"
            "# TODO: compute at least one correlation\n"
            "# corr_result = correlation_with_pvalue(df['score_a'], df['score_b'])\n"
            "# print(corr_result)\n"
            "\n"
            "# TODO: save a 2-subplot figure to 'stats_report.png'\n"
            "# fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))\n"
            "# ax1.hist(df['normal_col'], bins=20, edgecolor='white')\n"
            "# ax1.set_title('Normal Column')\n"
            "# ax2.hist(df['skewed_col'], bins=20, edgecolor='white', color='orange')\n"
            "# ax2.set_title('Skewed Column')\n"
            "# fig.savefig('stats_report.png', bbox_inches='tight', dpi=100)\n"
            "# plt.close('all')\n"
            "# print('Chart saved: stats_report.png')"
        ),
        md("## Checks"),
        code(
            "import os\n"
            "\n"
            "def _run_project_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: report defined as dict\n"
            "    try:\n"
            "        assert 'report' in globals(), 'report not defined — run StatsReport'\n"
            "        assert isinstance(report, dict) and len(report) > 0\n"
            "        passed += 1; print('\\u2705 Check 1: report is a non-empty dict')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: report has distribution and normality for each col\n"
            "    try:\n"
            "        for col, entry in report.items():\n"
            "            assert 'distribution' in entry\n"
            "            assert 'normality' in entry\n"
            "        passed += 1; print('\\u2705 Check 2: each column has distribution + normality')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: comparison defined as dict\n"
            "    try:\n"
            "        assert 'comparison' in globals(), 'comparison not defined — run compare_groups'\n"
            "        assert isinstance(comparison, dict)\n"
            "        assert 'conclusion' in comparison\n"
            "        passed += 1; print(f'\\u2705 Check 3: comparison conclusion={comparison[\"conclusion\"]!r}')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: corr_result defined\n"
            "    try:\n"
            "        assert 'corr_result' in globals(), 'corr_result not defined — run correlation_with_pvalue'\n"
            "        assert isinstance(corr_result, dict)\n"
            "        assert 'r' in corr_result\n"
            "        passed += 1; print(f'\\u2705 Check 4: corr_result r={corr_result[\"r\"]}')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: chart file saved\n"
            "    try:\n"
            "        assert os.path.exists('stats_report.png'), \\\n"
            "            'stats_report.png not found — save with fig.savefig()'\n"
            "        assert os.path.getsize('stats_report.png') > 1000, \\\n"
            "            'stats_report.png looks empty'\n"
            "        passed += 1; print('\\u2705 Check 5: stats_report.png saved')\n"
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
            "- Test normality before using correlation: if either variable is non-normal, "
            "use Spearman instead of Pearson\n"
            "- Create a full correlation matrix heatmap with `ax.imshow()` using `df.corr()`\n"
            "- Add a third group column and use `compare_groups` on all pairs\n"
            "- Use `ollama.chat` (Day 40 pattern) to narrate the `StatsReport` output in plain English\n"
            "- Export the report as a JSON file with `json.dumps(report, default=str, indent=2)`"
        ),
    ]


# ---------------------------------------------------------------------------
# Solution notebook
# ---------------------------------------------------------------------------

def solution_nb():
    global _cid; _cid = 600
    all_code = ALL_IMPLS + "\n\n\n" + STATS_REPORT_IMPL
    return [
        md(
            "# Day 047 Solution — Statistics for AI Engineers\n\n"
            "Demonstrates: extended descriptive stats, normality testing, correlation "
            "with p-values, group comparison (t-test + Cohen's d), StatsReport class, "
            "and a saved matplotlib figure.\n"
            "All data generated in-cell — no external files required."
        ),
        code(
            "import matplotlib\n"
            "matplotlib.use('Agg')\n"
            "import matplotlib.pyplot as plt\n"
        ),
        code(all_code),
        md("## Step 1 — Descriptive Statistics"),
        code(
            "df = make_sample_data(n=100, seed=42)\n"
            "\n"
            "for col in df.columns:\n"
            "    d = describe_distribution(df[col])\n"
            "    print(f'{col}:')\n"
            "    print(f'  mean={d[\"mean\"]:.3f}  median={d[\"median\"]:.3f}  std={d[\"std\"]:.3f}')\n"
            "    print(f'  IQR={d[\"iqr\"]:.3f}  skew={d[\"skewness\"]:.3f}  kurt={d[\"kurtosis\"]:.3f}')\n"
            "    print(f'  SEM={d[\"sem\"]:.4f}')\n"
            "\n"
            "d_norm = describe_distribution(df['normal_col'])\n"
            "d_skew = describe_distribution(df['skewed_col'])\n"
            "assert d_norm['count'] == 100\n"
            "assert d_skew['skewness'] > 0, 'exponential column should be right-skewed'"
        ),
        md("## Step 2 — Normality Testing"),
        code(
            "for col in df.columns:\n"
            "    n = test_normality(df[col])\n"
            "    status = 'normal' if n['is_normal'] else 'NOT normal'\n"
            "    print(f'{col}: {status}  (W={n[\"statistic\"]:.4f}, p={n[\"p_value\"]:.4f})')\n"
            "\n"
            "assert test_normality(df['normal_col'])['is_normal']  in (True, False)  # may vary\n"
            "assert test_normality(df['skewed_col'])['is_normal'] is False"
        ),
        md("## Step 3 — Correlation with p-value"),
        code(
            "# Create a correlated pair: score_c ≈ 0.7 * score_a + noise\n"
            "rng2   = np.random.default_rng(99)\n"
            "score_c = df['score_a'] * 0.7 + pd.Series(rng2.standard_normal(100) * 8)\n"
            "\n"
            "r_pearson = correlation_with_pvalue(df['score_a'], score_c)\n"
            "r_spearman = correlation_with_pvalue(df['score_a'], score_c, method='spearman')\n"
            "r_indep   = correlation_with_pvalue(df['score_a'], df['score_b'])\n"
            "\n"
            "print(f'score_a vs score_c  (Pearson):  r={r_pearson[\"r\"]:.3f}  p={r_pearson[\"p_value\"]:.4f}  sig={r_pearson[\"is_significant\"]}')\n"
            "print(f'score_a vs score_c  (Spearman): r={r_spearman[\"r\"]:.3f}  p={r_spearman[\"p_value\"]:.4f}  sig={r_spearman[\"is_significant\"]}')\n"
            "print(f'score_a vs score_b  (Pearson):  r={r_indep[\"r\"]:.3f}  p={r_indep[\"p_value\"]:.4f}  sig={r_indep[\"is_significant\"]}')\n"
            "\n"
            "assert r_pearson['is_significant'] is True,  'correlated pair should be significant'\n"
            "assert abs(r_pearson['r']) > 0.4,            'correlation should be moderate+'"
        ),
        md("## Step 4 — Group Comparison"),
        code(
            "comparison = compare_groups(df['score_a'], df['score_b'])\n"
            "\n"
            "print('=== Group Comparison ===')\n"
            "print(f'Group A: n={comparison[\"n_a\"]}  mean={comparison[\"mean_a\"]:.2f}')\n"
            "print(f'Group B: n={comparison[\"n_b\"]}  mean={comparison[\"mean_b\"]:.2f}')\n"
            "print(f'  t = {comparison[\"statistic\"]:.3f}   p = {comparison[\"p_value\"]:.2e}')\n"
            "print(f\"  Cohen's d = {comparison['cohens_d']:.3f}  → conclusion: {comparison['conclusion']}\")\n"
            "\n"
            "assert comparison['conclusion'] == 'different'\n"
            "assert abs(comparison['cohens_d']) > 1.0"
        ),
        md("## Step 5 — StatsReport"),
        code(
            "report = StatsReport().load(df).report()\n"
            "\n"
            "print('=== Stats Report ===')\n"
            "for col, entry in report.items():\n"
            "    d = entry['distribution']\n"
            "    n = entry['normality']\n"
            "    norm_str = 'normal' if n['is_normal'] else 'NOT normal'\n"
            "    print(f'{col}: mean={d[\"mean\"]:.2f} skew={d[\"skewness\"]:.2f} [{norm_str}]')\n"
            "\n"
            "assert len(report) == 4\n"
            "assert all('distribution' in v and 'normality' in v for v in report.values())"
        ),
        md("## Step 6 — Save Visualisation"),
        code(
            "fig, axes = plt.subplots(1, 3, figsize=(13, 4))\n"
            "\n"
            "# Histogram: normal column\n"
            "axes[0].hist(df['normal_col'], bins=20, edgecolor='white', color='steelblue')\n"
            "axes[0].axvline(df['normal_col'].mean(), color='red', linestyle='--', label='mean')\n"
            "axes[0].set_title('normal_col')\n"
            "axes[0].set_xlabel('value')\n"
            "axes[0].legend()\n"
            "\n"
            "# Histogram: skewed column\n"
            "axes[1].hist(df['skewed_col'], bins=20, edgecolor='white', color='orange')\n"
            "axes[1].axvline(df['skewed_col'].mean(),   color='red',  linestyle='--', label='mean')\n"
            "axes[1].axvline(df['skewed_col'].median(), color='blue', linestyle='--', label='median')\n"
            "axes[1].set_title('skewed_col (right-skewed)')\n"
            "axes[1].set_xlabel('value')\n"
            "axes[1].legend()\n"
            "\n"
            "# Box plot: score_a vs score_b\n"
            "axes[2].boxplot([df['score_a'].values, df['score_b'].values],\n"
            "                labels=['Score A', 'Score B'],\n"
            "                patch_artist=True,\n"
            "                boxprops=dict(facecolor='lightblue'))\n"
            "axes[2].set_title(f\"Group Comparison (d={comparison['cohens_d']:.2f})\")\n"
            "axes[2].set_ylabel('score')\n"
            "\n"
            "plt.tight_layout()\n"
            "fig.savefig('stats_report.png', bbox_inches='tight', dpi=100)\n"
            "plt.close('all')\n"
            "print('Chart saved: stats_report.png')\n"
            "\n"
            "import os\n"
            "assert os.path.exists('stats_report.png') and os.path.getsize('stats_report.png') > 1000\n"
            "\n"
            "print('\\nStatistics for AI Engineers complete!')"
        ),
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Generating Day 047 notebooks...")
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
