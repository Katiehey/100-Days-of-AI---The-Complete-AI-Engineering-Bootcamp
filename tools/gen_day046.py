#!/usr/bin/env python3
"""Generate all Day 046 notebooks: exercises 1-5, project, solution."""
import json
from pathlib import Path

ROOT    = Path(__file__).resolve().parent.parent
DAY_DIR = ROOT / "03_data_analysis" / "day_046"

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
# Shared data-generation helper (Provided cells only, not student-written)
# ---------------------------------------------------------------------------

MAKE_SAMPLE_TS = """\
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

def make_sample_ts(n_days: int = 90, seed: int = 42) -> pd.DataFrame:
    \"\"\"Return a reproducible daily time-series DataFrame for exercises.\"\"\"
    rng   = np.random.default_rng(seed)
    dates = pd.date_range('2024-01-01', periods=n_days, freq='D')
    vals  = 1000.0 + (rng.standard_normal(n_days).cumsum() * 50)
    return pd.DataFrame({'date': dates.strftime('%Y-%m-%d'),
                         'value': vals.round(2)})"""

# ---------------------------------------------------------------------------
# Implementations (student writes these)
# ---------------------------------------------------------------------------

PARSE_TS_IMPL = """\
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

def parse_time_series(df: pd.DataFrame, date_col: str) -> pd.DataFrame:
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    df = df.dropna(subset=[date_col])
    df = df.set_index(date_col).sort_index()
    return df

def date_features(df: pd.DataFrame) -> pd.DataFrame:
    idx = df.index
    return pd.DataFrame({
        'year':        idx.year,
        'month':       idx.month,
        'day':         idx.day,
        'day_of_week': idx.dayofweek,
        'quarter':     idx.quarter,
    }, index=idx)"""

RESAMPLE_IMPL = """\
def resample_series(series: pd.Series, freq: str, agg: str = 'sum') -> pd.Series:
    return series.resample(freq).agg(agg)

def multi_freq_summary(series: pd.Series) -> dict:
    return {
        'daily':  resample_series(series, 'D'),
        'weekly': resample_series(series, 'W'),
    }"""

ROLLING_IMPL = """\
def rolling_mean(series: pd.Series, window: int, min_periods: int = 1) -> pd.Series:
    return series.rolling(window=window, min_periods=min_periods).mean()

def rolling_stats(series: pd.Series, window: int) -> pd.DataFrame:
    r = series.rolling(window=window, min_periods=1)
    return pd.DataFrame({
        'mean': r.mean(),
        'std':  r.std(),
        'min':  r.min(),
        'max':  r.max(),
    })"""

CHANGES_IMPL = """\
def period_changes(series: pd.Series) -> pd.DataFrame:
    return pd.DataFrame({
        'value':      series,
        'change':     series.diff(),
        'pct_change': series.pct_change() * 100,
        'cumulative': series.cumsum(),
    })"""

TREND_ANALYZER_IMPL = """\
class TrendAnalyzer:
    def __init__(self):
        self._series = None

    def load(self, df: pd.DataFrame, date_col: str, value_col: str) -> 'TrendAnalyzer':
        self._series = parse_time_series(df, date_col)[value_col].dropna()
        return self

    def summary(self) -> dict:
        s = self._series
        if s is None or len(s) == 0:
            return {}
        first, last = float(s.iloc[0]), float(s.iloc[-1])
        total_pct   = (last - first) / abs(first) * 100 if first != 0 else 0.0
        direction   = 'up' if total_pct > 1 else ('down' if total_pct < -1 else 'flat')
        return {
            'n_periods':        len(s),
            'start_date':       str(s.index[0].date()),
            'end_date':         str(s.index[-1].date()),
            'first_value':      round(first, 2),
            'last_value':       round(last, 2),
            'total_pct_change': round(total_pct, 2),
            'trend_direction':  direction,
            'weekly_avg':       resample_series(s, 'W', 'mean'),
            'rolling_mean_7d':  rolling_stats(s, 7)['mean'],
            'daily_changes':    period_changes(s),
        }"""

# Cumulative provided snippets for later exercises
_BEFORE_RESAMPLE = "\n\n\n".join([MAKE_SAMPLE_TS, PARSE_TS_IMPL])
_BEFORE_ROLLING  = "\n\n\n".join([MAKE_SAMPLE_TS, PARSE_TS_IMPL, RESAMPLE_IMPL])
_BEFORE_CHANGES  = "\n\n\n".join([MAKE_SAMPLE_TS, PARSE_TS_IMPL, RESAMPLE_IMPL, ROLLING_IMPL])
ALL_IMPLS        = "\n\n\n".join([
    MAKE_SAMPLE_TS, PARSE_TS_IMPL, RESAMPLE_IMPL, ROLLING_IMPL, CHANGES_IMPL,
])


# ---------------------------------------------------------------------------
# Exercise 01 — DatetimeIndex: parse_time_series + date_features
# ---------------------------------------------------------------------------

def ex01():
    global _cid; _cid = 0
    return [
        md(
            "# Day 046 — Exercise 1: DatetimeIndex\n\n"
            "**What you'll build:** `parse_time_series(df, date_col) -> pd.DataFrame` — "
            "convert a string date column to a DatetimeIndex, drop bad rows, sort chronologically. "
            "And `date_features(df) -> pd.DataFrame` — extract year, month, day, day_of_week, and "
            "quarter from a DatetimeIndex'd DataFrame.\n\n"
            "**Why it matters:** Every time-series operation (resample, rolling, diff) "
            "requires a sorted DatetimeIndex. Without it pandas has no idea what 'weekly average' "
            "or 'rolling 7-day window' means — it's just a table with a string column."
        ),
        md("## Provided: Sample Data Generator"),
        code(MAKE_SAMPLE_TS),
        md("## Your Implementation"),
        code(
            "import pandas as pd\n"
            "import warnings\n"
            "warnings.filterwarnings('ignore')\n"
            "\n"
            "def parse_time_series(df: pd.DataFrame, date_col: str) -> pd.DataFrame:\n"
            '    """\n'
            "    Convert date_col to DatetimeIndex, drop NaT rows, sort chronologically.\n\n"
            "    Args:\n"
            "        df: raw DataFrame with a string date column\n"
            "        date_col: column name containing date strings\n"
            "    Returns:\n"
            "        DataFrame with DatetimeIndex, sorted ascending\n"
            '    """\n'
            "    # TODO: df = df.copy()\n"
            "    # TODO: df[date_col] = pd.to_datetime(df[date_col], errors='coerce')\n"
            "    # TODO: df = df.dropna(subset=[date_col])\n"
            "    # TODO: df = df.set_index(date_col).sort_index()\n"
            "    # TODO: return df\n"
            "    pass\n"
            "\n"
            "\n"
            "def date_features(df: pd.DataFrame) -> pd.DataFrame:\n"
            '    """\n'
            "    Extract calendar features from a DatetimeIndex'd DataFrame.\n\n"
            "    Returns DataFrame with columns: year, month, day, day_of_week, quarter.\n"
            '    """\n'
            "    # TODO: idx = df.index\n"
            "    # TODO: return pd.DataFrame({\n"
            "    #     'year': idx.year, 'month': idx.month, 'day': idx.day,\n"
            "    #     'day_of_week': idx.dayofweek, 'quarter': idx.quarter,\n"
            "    # }, index=idx)\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: parse_time_series returns a DatetimeIndex\n"
            "    try:\n"
            "        assert 'parse_time_series' in globals()\n"
            "        df_raw = make_sample_ts(30)\n"
            "        df_ts  = parse_time_series(df_raw, 'date')\n"
            "        assert isinstance(df_ts, pd.DataFrame), \\\n"
            "            f'expected DataFrame, got {type(df_ts).__name__}'\n"
            "        assert isinstance(df_ts.index, pd.DatetimeIndex), \\\n"
            "            f'index should be DatetimeIndex, got {type(df_ts.index).__name__}'\n"
            "        passed += 1; print('\\u2705 Check 1: parse_time_series returns DatetimeIndex')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: index is sorted chronologically\n"
            "    try:\n"
            "        assert df_ts.index.is_monotonic_increasing, \\\n"
            "            'index should be sorted ascending (chronological)'\n"
            "        passed += 1; print('\\u2705 Check 2: index sorted chronologically')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: date_features defined, returns DataFrame\n"
            "    try:\n"
            "        assert 'date_features' in globals()\n"
            "        feats = date_features(df_ts)\n"
            "        assert isinstance(feats, pd.DataFrame), \\\n"
            "            f'expected DataFrame, got {type(feats).__name__}'\n"
            "        passed += 1; print('\\u2705 Check 3: date_features returns DataFrame')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 4: all expected columns present\n"
            "    try:\n"
            "        for col in ('year', 'month', 'day', 'day_of_week', 'quarter'):\n"
            "            assert col in feats.columns, f'missing column: {col}'\n"
            "        passed += 1; print('\\u2705 Check 4: has year, month, day, day_of_week, quarter')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: values correct for 2024-01-01 (Monday = 0, month=1, quarter=1)\n"
            "    try:\n"
            "        row = feats.iloc[0]\n"
            "        assert int(row['year'])        == 2024, f'year:        {row[\"year\"]}'\n"
            "        assert int(row['month'])       == 1,    f'month:       {row[\"month\"]}'\n"
            "        assert int(row['day'])         == 1,    f'day:         {row[\"day\"]}'\n"
            "        assert int(row['day_of_week']) == 0,    f'day_of_week: {row[\"day_of_week\"]} (Mon=0)'\n"
            "        assert int(row['quarter'])     == 1,    f'quarter:     {row[\"quarter\"]}'\n"
            "        passed += 1; print('\\u2705 Check 5: 2024-01-01 → Monday, Q1 — values correct')\n"
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
            + PARSE_TS_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 02 — Resampling: resample_series + multi_freq_summary
# ---------------------------------------------------------------------------

def ex02():
    global _cid; _cid = 100
    return [
        md(
            "# Day 046 — Exercise 2: Resampling\n\n"
            "**What you'll build:** `resample_series(series, freq, agg='sum') -> pd.Series` — "
            "aggregate a datetime-indexed Series at a new time frequency (daily, weekly, monthly). "
            "And `multi_freq_summary(series) -> dict` — return a dict of the series summarised "
            "at daily and weekly frequencies.\n\n"
            "**Why it matters:** Raw data often arrives daily but insights live at the weekly or "
            "monthly level. Resampling is how you move between them — it's the time-series "
            "equivalent of `groupby`."
        ),
        md("## Provided: Setup + parse_time_series"),
        code(_BEFORE_RESAMPLE),
        md("## Your Implementation"),
        code(
            "def resample_series(series: pd.Series, freq: str,\n"
            "                    agg: str = 'sum') -> pd.Series:\n"
            '    """\n'
            "    Resample a datetime-indexed Series to a new frequency.\n\n"
            "    Args:\n"
            "        series: pd.Series with DatetimeIndex\n"
            "        freq:   resample rule — 'D' daily, 'W' weekly, 'ME' month-end\n"
            "        agg:    aggregation — 'sum', 'mean', 'min', 'max', 'count'\n"
            "    Returns:\n"
            "        Resampled pd.Series\n"
            '    """\n'
            "    # TODO: return series.resample(freq).agg(agg)\n"
            "    pass\n"
            "\n"
            "\n"
            "def multi_freq_summary(series: pd.Series) -> dict:\n"
            '    """\n'
            "    Return dict with keys 'daily' and 'weekly', each a resampled sum Series.\n"
            '    """\n'
            "    # TODO: return {\n"
            "    #     'daily':  resample_series(series, 'D'),\n"
            "    #     'weekly': resample_series(series, 'W'),\n"
            "    # }\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    df_raw = make_sample_ts(28)\n"
            "    df_ts  = parse_time_series(df_raw, 'date')\n"
            "    series = df_ts['value']\n"
            "\n"
            "    # Check 1: resample_series defined, returns pd.Series\n"
            "    try:\n"
            "        assert 'resample_series' in globals()\n"
            "        daily = resample_series(series, 'D')\n"
            "        assert isinstance(daily, pd.Series), \\\n"
            "            f'expected Series, got {type(daily).__name__}'\n"
            "        passed += 1; print('\\u2705 Check 1: resample_series returns pd.Series')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: daily resample — same length as input (no gaps in test data)\n"
            "    try:\n"
            "        assert len(daily) == 28, \\\n"
            "            f'daily resample of 28-day series should have 28 rows, got {len(daily)}'\n"
            "        passed += 1; print(f'\\u2705 Check 2: daily resample has {len(daily)} rows')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: weekly resample has fewer rows than daily\n"
            "    try:\n"
            "        weekly = resample_series(series, 'W')\n"
            "        assert isinstance(weekly, pd.Series)\n"
            "        assert len(weekly) < len(daily), \\\n"
            "            f'weekly ({len(weekly)}) should be shorter than daily ({len(daily)})'\n"
            "        passed += 1; print(f'\\u2705 Check 3: weekly has {len(weekly)} rows < {len(daily)} daily')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: multi_freq_summary defined, returns dict\n"
            "    try:\n"
            "        assert 'multi_freq_summary' in globals()\n"
            "        summary = multi_freq_summary(series)\n"
            "        assert isinstance(summary, dict), \\\n"
            "            f'expected dict, got {type(summary).__name__}'\n"
            "        passed += 1; print('\\u2705 Check 4: multi_freq_summary returns dict')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 5: dict has 'daily' and 'weekly' keys, both pd.Series\n"
            "    try:\n"
            "        for key in ('daily', 'weekly'):\n"
            "            assert key in summary, f'missing key: {key!r}'\n"
            "            assert isinstance(summary[key], pd.Series), \\\n"
            "                f'summary[{key!r}] should be Series'\n"
            "        passed += 1; print(\"\\u2705 Check 5: dict has 'daily' and 'weekly' Series\")\n"
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
            + RESAMPLE_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 03 — Rolling Windows: rolling_mean + rolling_stats
# ---------------------------------------------------------------------------

def ex03():
    global _cid; _cid = 200
    return [
        md(
            "# Day 046 — Exercise 3: Rolling Windows\n\n"
            "**What you'll build:** `rolling_mean(series, window, min_periods=1) -> pd.Series` "
            "— smooth a noisy series with a moving average. And "
            "`rolling_stats(series, window) -> pd.DataFrame` — compute rolling mean, std, min, "
            "and max in one DataFrame.\n\n"
            "**Why it matters:** Raw time series is noisy. A 7-day rolling mean strips that noise "
            "and shows the underlying trend. Rolling std reveals volatility spikes. Together they "
            "are the most-used tools for pattern detection in time series."
        ),
        md("## Provided: Setup + parse_time_series + resample_series"),
        code(_BEFORE_ROLLING),
        md("## Your Implementation"),
        code(
            "def rolling_mean(series: pd.Series, window: int,\n"
            "                 min_periods: int = 1) -> pd.Series:\n"
            '    """\n'
            "    Compute rolling mean with min_periods=1 so the first values aren't NaN.\n\n"
            "    Args:\n"
            "        series:      datetime-indexed Series\n"
            "        window:      look-back window (number of periods)\n"
            "        min_periods: minimum observations needed (default 1 — no leading NaN)\n"
            "    Returns:\n"
            "        pd.Series of rolling means, same length as input\n"
            '    """\n'
            "    # TODO: return series.rolling(window=window, min_periods=min_periods).mean()\n"
            "    pass\n"
            "\n"
            "\n"
            "def rolling_stats(series: pd.Series, window: int) -> pd.DataFrame:\n"
            '    """\n'
            "    Compute rolling mean, std, min, max in one DataFrame.\n\n"
            "    Uses min_periods=1 so no leading NaN rows.\n"
            "    Returns DataFrame with columns: mean, std, min, max.\n"
            '    """\n'
            "    # TODO: r = series.rolling(window=window, min_periods=1)\n"
            "    # TODO: return pd.DataFrame({\n"
            "    #     'mean': r.mean(), 'std': r.std(),\n"
            "    #     'min':  r.min(),  'max': r.max(),\n"
            "    # })\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    df_raw = make_sample_ts(30)\n"
            "    series = parse_time_series(df_raw, 'date')['value']\n"
            "\n"
            "    # Check 1: rolling_mean returns same-length Series\n"
            "    try:\n"
            "        assert 'rolling_mean' in globals()\n"
            "        rm = rolling_mean(series, window=7)\n"
            "        assert isinstance(rm, pd.Series), \\\n"
            "            f'expected Series, got {type(rm).__name__}'\n"
            "        assert len(rm) == len(series), \\\n"
            "            f'rolling_mean must preserve length: {len(rm)} vs {len(series)}'\n"
            "        passed += 1; print('\\u2705 Check 1: rolling_mean returns same-length Series')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: no NaN in first value (min_periods=1)\n"
            "    try:\n"
            "        assert not pd.isna(rm.iloc[0]), \\\n"
            "            'first rolling_mean value should not be NaN (min_periods=1)'\n"
            "        passed += 1; print('\\u2705 Check 2: no leading NaN — min_periods=1 working')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: rolling_stats returns DataFrame with correct shape\n"
            "    try:\n"
            "        assert 'rolling_stats' in globals()\n"
            "        rs = rolling_stats(series, window=7)\n"
            "        assert isinstance(rs, pd.DataFrame), \\\n"
            "            f'expected DataFrame, got {type(rs).__name__}'\n"
            "        assert len(rs) == len(series), \\\n"
            "            f'rolling_stats must preserve length'\n"
            "        passed += 1; print('\\u2705 Check 3: rolling_stats returns same-length DataFrame')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 4: has mean, std, min, max columns\n"
            "    try:\n"
            "        for col in ('mean', 'std', 'min', 'max'):\n"
            "            assert col in rs.columns, f'missing column: {col}'\n"
            "        passed += 1; print('\\u2705 Check 4: rolling_stats has mean, std, min, max')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: rolling_stats mean == rolling_mean for same window\n"
            "    try:\n"
            "        rm2 = rolling_mean(series, window=7)\n"
            "        diff = (rs['mean'] - rm2).abs().max()\n"
            "        assert diff < 1e-9, f'rolling_stats mean != rolling_mean (max diff={diff})'\n"
            "        passed += 1; print('\\u2705 Check 5: rolling_stats[mean] == rolling_mean')\n"
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
            + ROLLING_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 04 — Change Analysis: period_changes
# ---------------------------------------------------------------------------

def ex04():
    global _cid; _cid = 300
    return [
        md(
            "# Day 046 — Exercise 4: Change Analysis\n\n"
            "**What you'll build:** `period_changes(series) -> pd.DataFrame` — "
            "compute absolute change (`diff()`), percentage change (`pct_change()`), "
            "and cumulative sum (`cumsum()`) alongside the original values, all in one DataFrame.\n\n"
            "**Why it matters:** Absolute values answer 'what is it?'. Change metrics answer "
            "'is it getting better or worse?'. Percentage change normalises across different scales. "
            "Cumulative sum tracks total throughput over time."
        ),
        md("## Provided: Setup + parse_time_series + rolling functions"),
        code(_BEFORE_CHANGES),
        md("## Your Implementation"),
        code(
            "def period_changes(series: pd.Series) -> pd.DataFrame:\n"
            '    """\n'
            "    Return a DataFrame with value, change, pct_change, and cumulative columns.\n\n"
            "    Columns:\n"
            "        value:      original values\n"
            "        change:     series.diff()  — absolute change vs previous period (NaN for first row)\n"
            "        pct_change: series.pct_change() * 100  — % change (NaN for first row)\n"
            "        cumulative: series.cumsum()  — running total\n"
            '    """\n'
            "    # TODO: return pd.DataFrame({\n"
            "    #     'value':      series,\n"
            "    #     'change':     series.diff(),\n"
            "    #     'pct_change': series.pct_change() * 100,\n"
            "    #     'cumulative': series.cumsum(),\n"
            "    # })\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    df_raw = make_sample_ts(20)\n"
            "    series = parse_time_series(df_raw, 'date')['value']\n"
            "\n"
            "    # Check 1: period_changes defined, returns DataFrame\n"
            "    try:\n"
            "        assert 'period_changes' in globals()\n"
            "        pc = period_changes(series)\n"
            "        assert isinstance(pc, pd.DataFrame), \\\n"
            "            f'expected DataFrame, got {type(pc).__name__}'\n"
            "        passed += 1; print('\\u2705 Check 1: period_changes returns DataFrame')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: has all four columns\n"
            "    try:\n"
            "        for col in ('value', 'change', 'pct_change', 'cumulative'):\n"
            "            assert col in pc.columns, f'missing column: {col}'\n"
            "        passed += 1; print('\\u2705 Check 2: has value, change, pct_change, cumulative')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: first row change is NaN (no previous period)\n"
            "    try:\n"
            "        assert pd.isna(pc['change'].iloc[0]), \\\n"
            "            f'first change should be NaN, got {pc[\"change\"].iloc[0]}'\n"
            "        assert pd.isna(pc['pct_change'].iloc[0]), \\\n"
            "            f'first pct_change should be NaN, got {pc[\"pct_change\"].iloc[0]}'\n"
            "        passed += 1; print('\\u2705 Check 3: first row change and pct_change are NaN')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: value column matches original series\n"
            "    try:\n"
            "        assert (pc['value'] == series).all(), \\\n"
            "            'value column should equal the input series'\n"
            "        passed += 1; print('\\u2705 Check 4: value column matches original series')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: cumulative is correct (cumsum)\n"
            "    try:\n"
            "        expected_cumsum = series.cumsum()\n"
            "        diff = (pc['cumulative'] - expected_cumsum).abs().max()\n"
            "        assert diff < 1e-9, f'cumulative != series.cumsum() (max diff={diff:.2e})'\n"
            "        passed += 1; print('\\u2705 Check 5: cumulative == series.cumsum()')\n"
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
            + CHANGES_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 05 — TrendAnalyzer class
# ---------------------------------------------------------------------------

def ex05():
    global _cid; _cid = 400
    return [
        md(
            "# Day 046 — Exercise 5: TrendAnalyzer\n\n"
            "**What you'll build:** The `TrendAnalyzer` class — `load(df, date_col, value_col)` "
            "(fluent, returns self) and `summary() -> dict` — combining parse, resample, rolling, "
            "and change analysis into one callable object.\n\n"
            "**Why it matters:** The four functions you built in Exercises 1-4 are useful "
            "individually, but an analyst needs them composed. `TrendAnalyzer` is that composition — "
            "one `.load(...).summary()` call gives you everything: period count, start/end date, "
            "total change, trend direction, and pre-computed rolling stats."
        ),
        md("## Provided: All Helper Functions"),
        code(ALL_IMPLS),
        md("## Your Implementation"),
        code(
            "class TrendAnalyzer:\n"
            '    """\n'
            "    Compose time-series analysis into one callable object.\n\n"
            "    Usage:\n"
            "        ta = TrendAnalyzer()\n"
            "        ta.load(df, 'date', 'value')\n"
            "        report = ta.summary()\n"
            '    """\n'
            "\n"
            "    def __init__(self):\n"
            "        # TODO: self._series = None\n"
            "        pass\n"
            "\n"
            "    def load(self, df: pd.DataFrame, date_col: str,\n"
            "             value_col: str) -> 'TrendAnalyzer':\n"
            '        """\n'
            "        Parse the DataFrame, store the value column as self._series.\n"
            "        Returns self for fluent chaining: ta.load(...).summary()\n"
            '        """\n'
            "        # TODO: self._series = parse_time_series(df, date_col)[value_col].dropna()\n"
            "        # TODO: return self\n"
            "        pass\n"
            "\n"
            "    def summary(self) -> dict:\n"
            '        """\n'
            "        Return analysis dict with keys:\n"
            "            n_periods, start_date, end_date,\n"
            "            first_value, last_value,\n"
            "            total_pct_change, trend_direction,\n"
            "            weekly_avg, rolling_mean_7d, daily_changes\n"
            '        """\n'
            "        # TODO: s = self._series\n"
            "        # TODO: if s is None or len(s) == 0: return {}\n"
            "        # TODO: first, last = float(s.iloc[0]), float(s.iloc[-1])\n"
            "        # TODO: total_pct = (last - first) / abs(first) * 100 if first != 0 else 0.0\n"
            "        # TODO: direction = 'up' if total_pct > 1 else ('down' if total_pct < -1 else 'flat')\n"
            "        # TODO: return {\n"
            "        #     'n_periods': len(s),\n"
            "        #     'start_date': str(s.index[0].date()),\n"
            "        #     'end_date': str(s.index[-1].date()),\n"
            "        #     'first_value': round(first, 2),\n"
            "        #     'last_value': round(last, 2),\n"
            "        #     'total_pct_change': round(total_pct, 2),\n"
            "        #     'trend_direction': direction,\n"
            "        #     'weekly_avg': resample_series(s, 'W', 'mean'),\n"
            "        #     'rolling_mean_7d': rolling_stats(s, 7)['mean'],\n"
            "        #     'daily_changes': period_changes(s),\n"
            "        # }\n"
            "        pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: class defined with load and summary methods\n"
            "    try:\n"
            "        assert 'TrendAnalyzer' in globals()\n"
            "        for m in ('load', 'summary'):\n"
            "            assert hasattr(TrendAnalyzer, m), f'missing method: {m}'\n"
            "        passed += 1; print('\\u2705 Check 1: TrendAnalyzer has load and summary')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: load() returns self (fluent)\n"
            "    try:\n"
            "        ta  = TrendAnalyzer()\n"
            "        ret = ta.load(make_sample_ts(60), 'date', 'value')\n"
            "        assert ret is ta, f'load() must return self, got {type(ret).__name__}'\n"
            "        passed += 1; print('\\u2705 Check 2: load() returns self (fluent chaining)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 3: summary() returns dict with required keys\n"
            "    try:\n"
            "        report = ta.summary()\n"
            "        assert isinstance(report, dict), \\\n"
            "            f'summary() should return dict, got {type(report).__name__}'\n"
            "        required = ('n_periods', 'start_date', 'end_date',\n"
            "                    'first_value', 'last_value', 'total_pct_change',\n"
            "                    'trend_direction')\n"
            "        for k in required:\n"
            "            assert k in report, f'summary missing key: {k!r}'\n"
            "        passed += 1; print('\\u2705 Check 3: summary() returns dict with all required keys')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 4: n_periods is correct\n"
            "    try:\n"
            "        assert report['n_periods'] == 60, \\\n"
            "            f'n_periods should be 60, got {report[\"n_periods\"]}'\n"
            "        assert report['start_date'] == '2024-01-01', \\\n"
            "            f'start_date should be 2024-01-01, got {report[\"start_date\"]}'\n"
            "        passed += 1; print(f'\\u2705 Check 4: n_periods=60, start_date=2024-01-01')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: trend_direction is one of 'up', 'down', 'flat'\n"
            "    try:\n"
            "        assert report['trend_direction'] in ('up', 'down', 'flat'), \\\n"
            "            f'trend_direction must be up/down/flat, got {report[\"trend_direction\"]!r}'\n"
            "        pct = report['total_pct_change']\n"
            "        assert isinstance(pct, float), \\\n"
            "            f'total_pct_change should be float, got {type(pct).__name__}'\n"
            "        passed += 1; print(f'\\u2705 Check 5: trend_direction={report[\"trend_direction\"]!r}, '\n"
            "                           f'total_pct_change={pct:.2f}%')\n"
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
            + TREND_ANALYZER_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Project notebook
# ---------------------------------------------------------------------------

def project_nb():
    global _cid; _cid = 500
    all_code = ALL_IMPLS + "\n\n\n" + TREND_ANALYZER_IMPL
    return [
        md(
            "# Day 046 Project: Trend Analysis Report\n\n"
            "## What You're Building\n\n"
            "A `TrendAnalyzer` pipeline that takes a daily time series, produces a full "
            "summary report, and saves a matplotlib chart showing the raw values and their "
            "7-day rolling mean.\n\n"
            "## Project Requirements\n\n"
            "1. Generate or load a time series with at least 60 data points\n"
            "2. Create a `TrendAnalyzer`, call `.load(df, 'date', 'value')`\n"
            "3. Call `.summary()` and store the result as `report`\n"
            "4. Print: n_periods, trend_direction, total_pct_change, start_date, end_date\n"
            "5. Save a chart with the raw series + 7-day rolling mean to `trend_chart.png`\n"
            "6. Run `_run_project_checks()` to verify\n\n"
            "You run it, it prints a trend summary and saves a chart. That is the deliverable."
        ),
        md("## Provided: All Implementations"),
        code(all_code),
        md("## Your Pipeline"),
        code(
            "import matplotlib\n"
            "matplotlib.use('Agg')\n"
            "import matplotlib.pyplot as plt\n"
            "\n"
            "# TODO: generate or load data\n"
            "# df = make_sample_ts(n_days=90, seed=7)\n"
            "\n"
            "# TODO: create and load the analyzer\n"
            "# ta = TrendAnalyzer()\n"
            "# ta.load(df, 'date', 'value')\n"
            "# report = ta.summary()\n"
            "\n"
            "# TODO: print report\n"
            "# print(f\"Periods: {report['n_periods']}\")\n"
            "# print(f\"Range:   {report['start_date']} → {report['end_date']}\")\n"
            "# print(f\"Trend:   {report['trend_direction']}  ({report['total_pct_change']:+.2f}%)\")\n"
            "\n"
            "# TODO: save chart\n"
            "# fig, ax = plt.subplots(figsize=(12, 4))\n"
            "# report['rolling_mean_7d'].plot(ax=ax, label='7-day rolling mean', linewidth=2)\n"
            "# ax.set_title('Trend Analysis')\n"
            "# ax.legend()\n"
            "# fig.savefig('trend_chart.png', bbox_inches='tight', dpi=100)\n"
            "# plt.close('all')\n"
            "# print('Chart saved: trend_chart.png')"
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
            "        assert 'report' in globals(), 'report not defined — call ta.summary()'\n"
            "        assert isinstance(report, dict)\n"
            "        passed += 1; print('\\u2705 Check 1: report is a dict')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: required keys present\n"
            "    try:\n"
            "        for k in ('n_periods', 'trend_direction', 'total_pct_change',\n"
            "                  'start_date', 'end_date', 'rolling_mean_7d'):\n"
            "            assert k in report, f'missing key: {k!r}'\n"
            "        passed += 1; print('\\u2705 Check 2: report has all required keys')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: at least 60 periods\n"
            "    try:\n"
            "        n = report['n_periods']\n"
            "        assert n >= 60, f'need >= 60 periods, got {n}'\n"
            "        passed += 1; print(f'\\u2705 Check 3: {n} periods (>= 60)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: trend_direction is valid\n"
            "    try:\n"
            "        d = report['trend_direction']\n"
            "        assert d in ('up', 'down', 'flat'), \\\n"
            "            f'trend_direction must be up/down/flat, got {d!r}'\n"
            "        passed += 1; print(f'\\u2705 Check 4: trend_direction={d!r}')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: chart file saved\n"
            "    try:\n"
            "        assert os.path.exists('trend_chart.png'), \\\n"
            "            'trend_chart.png not found — save with fig.savefig()'\n"
            "        assert os.path.getsize('trend_chart.png') > 1000, \\\n"
            "            'trend_chart.png looks empty'\n"
            "        passed += 1; print('\\u2705 Check 5: trend_chart.png saved')\n"
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
            "- Try a monthly resample: `resample_series(report['rolling_mean_7d'], 'ME', 'mean')`\n"
            "- Use `date_features()` to plot average value by day of week (bar chart)\n"
            "- Add a second subplot showing daily `pct_change` to spot volatility spikes\n"
            "- Load a real CSV from Day 45's pipeline and run `TrendAnalyzer` on it\n"
            "- Use `ollama.chat` (Day 40 pattern) to narrate the trend summary in plain English"
        ),
    ]


# ---------------------------------------------------------------------------
# Solution notebook
# ---------------------------------------------------------------------------

def solution_nb():
    global _cid; _cid = 600
    all_code = ALL_IMPLS + "\n\n\n" + TREND_ANALYZER_IMPL
    return [
        md(
            "# Day 046 Solution — Time Series Basics\n\n"
            "Demonstrates: DatetimeIndex, resampling, rolling windows, change analysis, "
            "TrendAnalyzer class, and a saved matplotlib chart.\n"
            "All data is generated in-cell — no external files required."
        ),
        code(
            "import matplotlib\n"
            "matplotlib.use('Agg')\n"
            "import matplotlib.pyplot as plt\n"
        ),
        code(all_code),
        md("## Step 1 — Build a DatetimeIndex"),
        code(
            "df_raw = make_sample_ts(n_days=90, seed=42)\n"
            "df_ts  = parse_time_series(df_raw, 'date')\n"
            "series = df_ts['value']\n"
            "\n"
            "print(f'Shape:      {df_ts.shape}')\n"
            "print(f'Index type: {type(df_ts.index).__name__}')\n"
            "print(f'Date range: {series.index[0].date()} → {series.index[-1].date()}')\n"
            "\n"
            "feats = date_features(df_ts)\n"
            "print(f'\\nFirst row features:')\n"
            "print(feats.iloc[0].to_dict())\n"
            "\n"
            "assert isinstance(df_ts.index, pd.DatetimeIndex)\n"
            "assert df_ts.index.is_monotonic_increasing\n"
            "assert list(feats.columns) == ['year', 'month', 'day', 'day_of_week', 'quarter']"
        ),
        md("## Step 2 — Resample at Multiple Frequencies"),
        code(
            "summary = multi_freq_summary(series)\n"
            "print(f'Daily  rows: {len(summary[\"daily\"])}')\n"
            "print(f'Weekly rows: {len(summary[\"weekly\"])}')\n"
            "\n"
            "monthly = resample_series(series, 'ME', 'mean')\n"
            "print(f'Monthly rows: {len(monthly)}')\n"
            "print(monthly.round(2))\n"
            "\n"
            "assert len(summary['daily'])  == 90\n"
            "assert len(summary['weekly'])  < 90"
        ),
        md("## Step 3 — Rolling Windows"),
        code(
            "rm7 = rolling_mean(series, window=7)\n"
            "rs7 = rolling_stats(series, window=7)\n"
            "\n"
            "print(f'First rolling mean (w=7): {rm7.iloc[0]:.2f}  (single point, min_periods=1)')\n"
            "print(f'7th rolling mean  (w=7):  {rm7.iloc[6]:.2f}  (full 7-day window)')\n"
            "print(f'\\nRolling stats (last 5 rows):')\n"
            "print(rs7.tail().round(2))\n"
            "\n"
            "assert len(rm7) == len(series)\n"
            "assert not rm7.isna().any()"
        ),
        md("## Step 4 — Change Analysis"),
        code(
            "changes = period_changes(series)\n"
            "print('First 5 rows of period_changes:')\n"
            "print(changes.head().round(2))\n"
            "\n"
            "print(f'\\nAverage daily change: {changes[\"change\"].mean():.2f}')\n"
            "print(f'Max single-day gain:  {changes[\"change\"].max():.2f}')\n"
            "print(f'Max single-day loss:  {changes[\"change\"].min():.2f}')\n"
            "\n"
            "assert pd.isna(changes['change'].iloc[0])\n"
            "assert not pd.isna(changes['change'].iloc[1])"
        ),
        md("## Step 5 — TrendAnalyzer Full Report"),
        code(
            "ta     = TrendAnalyzer()\n"
            "report = ta.load(df_raw, 'date', 'value').summary()\n"
            "\n"
            "print('=== Trend Report ===')\n"
            "print(f\"Periods:       {report['n_periods']}\")\n"
            "print(f\"Range:         {report['start_date']} -> {report['end_date']}\")\n"
            "print(f\"First/Last:    {report['first_value']:.2f} -> {report['last_value']:.2f}\")\n"
            "print(f\"Total change:  {report['total_pct_change']:+.2f}%\")\n"
            "print(f\"Direction:     {report['trend_direction']}\")\n"
            "\n"
            "assert report['n_periods']    == 90\n"
            "assert report['start_date']   == '2024-01-01'\n"
            "assert report['trend_direction'] in ('up', 'down', 'flat')"
        ),
        md("## Step 6 — Save Trend Chart"),
        code(
            "fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 6), sharex=True)\n"
            "\n"
            "# Raw + 7-day rolling mean\n"
            "series.plot(ax=ax1, alpha=0.4, label='Daily value', color='steelblue')\n"
            "report['rolling_mean_7d'].plot(ax=ax1, label='7-day rolling mean',\n"
            "                               color='navy', linewidth=2)\n"
            "ax1.set_title('Daily Values with 7-Day Rolling Mean')\n"
            "ax1.set_ylabel('Value')\n"
            "ax1.legend()\n"
            "\n"
            "# Daily % change\n"
            "report['daily_changes']['pct_change'].plot(ax=ax2, color='darkorange', alpha=0.7)\n"
            "ax2.axhline(0, color='black', linewidth=0.8, linestyle='--')\n"
            "ax2.set_title('Daily % Change')\n"
            "ax2.set_ylabel('% Change')\n"
            "ax2.set_xlabel('Date')\n"
            "\n"
            "plt.tight_layout()\n"
            "fig.savefig('trend_chart.png', bbox_inches='tight', dpi=100)\n"
            "plt.close('all')\n"
            "print('Chart saved: trend_chart.png')\n"
            "\n"
            "import os\n"
            "assert os.path.exists('trend_chart.png') and os.path.getsize('trend_chart.png') > 1000\n"
            "\n"
            "print('\\nTime Series Basics complete!')"
        ),
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Generating Day 046 notebooks...")
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
