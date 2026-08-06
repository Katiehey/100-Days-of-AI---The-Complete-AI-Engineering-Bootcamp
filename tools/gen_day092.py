#!/usr/bin/env python3
"""Day 092 generator — Building a Strategy."""
import json, pathlib

ROOT  = pathlib.Path(__file__).parent.parent
DAY   = "092"
SLUG  = "strategy"
TITLE = "Building a Strategy"
DIR   = ROOT / "07_finance" / f"day_{DAY}"

# ══════════════════════════════════════════════════════════════════════════════
# Deliverable
# ══════════════════════════════════════════════════════════════════════════════

DELIVERABLE = '''\
"""
Day 092 — Building a Strategy
================================
Three production-ready signal generators plus a combined filter.

All functions accept a raw OHLCV DataFrame and return a pd.Series of
{0, 1} values (0 = flat, 1 = long) aligned to df.index with no NaN.

Public API
----------
    sma_crossover(df, fast=20, slow=50)              -> pd.Series {0,1}
    rsi_mean_reversion(df, window=14, oversold=30,
                       overbought=70)                -> pd.Series {0,1}
    macd_cross(df, fast=12, slow=26, signal=9)       -> pd.Series {0,1}
    combined_signal(df, fast=20, slow=50,
                    macd_fast=12, macd_slow=26,
                    macd_sig=9)                      -> pd.Series {0,1}
"""
import warnings
import pandas as pd


# ── private helpers ───────────────────────────────────────────────────────────

def _sma(series, window):
    return series.rolling(window).mean()

def _ema(series, window):
    return series.ewm(span=window, adjust=False).mean()

def _rsi(series, window):
    delta = series.diff()
    gain  = delta.clip(lower=0).rolling(window).mean()
    loss  = (-delta.clip(upper=0)).rolling(window).mean()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        rs = gain / loss
    return 100 - (100 / (1 + rs))


# ── signal generators ─────────────────────────────────────────────────────────

def sma_crossover(df, fast=20, slow=50):
    """Trend-following: long when the fast SMA is above the slow SMA.

    Args:
        df   : OHLCV DataFrame (needs "Close")
        fast : fast SMA window (default 20)
        slow : slow SMA window (default 50)

    Returns:
        pd.Series of {0, 1}; 1 = fast_sma > slow_sma; 0 otherwise.
        First slow-1 values are 0 (insufficient data for slow SMA).
    """
    close    = df["Close"]
    fast_sma = _sma(close, fast)
    slow_sma = _sma(close, slow)
    return (fast_sma > slow_sma).fillna(False).astype(int)


def rsi_mean_reversion(df, window=14, oversold=30, overbought=70):
    """Mean-reversion: long when RSI < oversold, flat when RSI > overbought.

    Holds the previous position between the two thresholds (forward-fill).
    Defaults to flat (0) before the first RSI value is available.

    Args:
        df         : OHLCV DataFrame (needs "Close")
        window     : RSI look-back period (default 14)
        oversold   : RSI level to go long (default 30)
        overbought : RSI level to go flat (default 70)

    Returns:
        pd.Series of {0, 1}; no NaN.
    """
    rsi_s  = _rsi(df["Close"], window)
    signal = pd.Series(float("nan"), index=df.index)
    signal[rsi_s < oversold]   = 1.0
    signal[rsi_s > overbought] = 0.0
    return signal.ffill().fillna(0).astype(int)


def macd_cross(df, fast=12, slow=26, signal=9):
    """Momentum crossover: long when the MACD line is above the signal line.

    MACD line  = EMA(fast) − EMA(slow)
    Signal line = EMA(MACD line, signal)
    Position   = 1 when MACD line > signal line; 0 otherwise.

    No NaN values because EMA starts from the first observation.

    Args:
        df     : OHLCV DataFrame (needs "Close")
        fast   : fast EMA window (default 12)
        slow   : slow EMA window (default 26)
        signal : signal EMA window (default 9)

    Returns:
        pd.Series of {0, 1}; no NaN.
    """
    close       = df["Close"]
    macd_line   = _ema(close, fast) - _ema(close, slow)
    signal_line = _ema(macd_line, signal)
    return (macd_line > signal_line).astype(int)


def combined_signal(df, fast=20, slow=50, macd_fast=12, macd_slow=26, macd_sig=9):
    """Combined trend + momentum filter: long only when both agree.

    Requires:
      - SMA crossover: fast SMA > slow SMA  (uptrend confirmed)
      - MACD cross   : MACD line > signal line  (momentum positive)

    More conservative than either signal alone — fewer but higher-quality entries.

    Returns:
        pd.Series of {0, 1}; no NaN.
    """
    sma_sig  = sma_crossover(df, fast, slow)
    macd_sig = macd_cross(df, macd_fast, macd_slow, macd_sig)
    return ((sma_sig == 1) & (macd_sig == 1)).astype(int)
'''

# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _nb(cells):
    return {
        "nbformat": 4, "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3 (ipykernel)",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.10.0"},
        },
        "cells": cells,
    }

def _code(src, outputs=None):
    return {
        "cell_type": "code", "execution_count": None, "metadata": {},
        "outputs": outputs or [],
        "source": src.splitlines(keepends=True),
    }

def _md(src):
    return {"cell_type": "markdown", "metadata": {},
            "source": src.splitlines(keepends=True)}

# ── preludes ──────────────────────────────────────────────────────────────────

_P_BASE = """\
import pandas as pd, math, warnings

def _synthetic(n=252):
    prices = [100.0 * (1 + 0.3 * math.sin(i * 2 * math.pi / n)) for i in range(n)]
    dates  = pd.date_range("2023-01-01", periods=n, freq="B")
    close  = pd.Series(prices, index=dates)
    return pd.DataFrame({
        "Open":   close.shift(1).fillna(close.iloc[0]),
        "High":   close * 1.01,
        "Low":    close * 0.99,
        "Close":  close,
        "Volume": pd.Series([1_000_000 + i * 1_000 for i in range(n)], index=dates),
    })

def _sma(s, w):  return s.rolling(w).mean()
def _ema(s, w):  return s.ewm(span=w, adjust=False).mean()
def _rsi(s, w):
    d = s.diff()
    g = d.clip(lower=0).rolling(w).mean()
    l = (-d.clip(upper=0)).rolling(w).mean()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        rs = g / l
    return 100 - (100 / (1 + rs))
"""

_P_SMA_CROSS = """\
def sma_crossover(df, fast=20, slow=50):
    close = df["Close"]
    return (_sma(close, fast) > _sma(close, slow)).fillna(False).astype(int)
"""

_P_RSI_MR = """\
def rsi_mean_reversion(df, window=14, oversold=30, overbought=70):
    rsi_s  = _rsi(df["Close"], window)
    signal = pd.Series(float("nan"), index=df.index)
    signal[rsi_s < oversold]   = 1.0
    signal[rsi_s > overbought] = 0.0
    return signal.ffill().fillna(0).astype(int)
"""

_P_MACD_CROSS = """\
def macd_cross(df, fast=12, slow=26, signal=9):
    close       = df["Close"]
    macd_line   = _ema(close, fast) - _ema(close, slow)
    signal_line = _ema(macd_line, signal)
    return (macd_line > signal_line).astype(int)
"""

_P_COMBINED = """\
def combined_signal(df, fast=20, slow=50, macd_fast=12, macd_slow=26, macd_sig=9):
    sma_sig  = sma_crossover(df, fast, slow)
    macd_sig = macd_cross(df, macd_fast, macd_slow, macd_sig)
    return ((sma_sig == 1) & (macd_sig == 1)).astype(int)
"""

_P_BACKTEST = """\
def _compute_returns(df):  return df["Close"].pct_change()
def _compute_equity(r):    return (1 + r.fillna(0)).cumprod()
def _max_dd(eq):
    peak = eq.cummax()
    return float(((eq - peak) / peak).min())
def _sharpe(r):
    c = r.dropna()
    if len(c) == 0 or c.std() == 0: return 0.0
    return float(c.mean() / c.std() * (252 ** 0.5))
def run_backtest(df, signals, label="strategy"):
    mr  = _compute_returns(df)
    pos = signals.shift(1).fillna(0)
    sr  = pos * mr
    eq  = _compute_equity(sr)
    c   = sr.dropna(); n = len(c)
    tr  = float(eq.iloc[-1] - 1.0)
    base = 1.0 + tr
    ar  = float(base ** (252.0 / max(n, 1)) - 1) if base > 0 else -1.0
    pos_diff = pos.diff().fillna(0)
    return {
        "label":             label,
        "total_return":      tr,
        "annualized_return": ar,
        "sharpe_ratio":      _sharpe(sr),
        "max_drawdown":      _max_dd(eq),
        "win_rate":          float((c > 0).sum() / max(n, 1)),
        "n_trades":          int((pos_diff != 0).sum()),
        "equity":            eq,
    }
"""

# ══════════════════════════════════════════════════════════════════════════════
# Exercises
# ══════════════════════════════════════════════════════════════════════════════

_EX1 = _nb([
    _md("# Exercise 1 — SMA Crossover\n\n"
        "The SMA crossover is the oldest systematic trading rule. When the "
        "fast moving average rises above the slow moving average, prices are "
        "trending up — go long. When the fast falls below the slow, the trend "
        "has reversed — go flat. Simple, interpretable, and effective enough "
        "to still be widely used."),
    _code(_P_BASE + """\

def sma_crossover(df, fast=20, slow=50):
    \"\"\"Long (1) when fast SMA > slow SMA; flat (0) otherwise.

    Steps:
      1. close    = df["Close"]
      2. fast_sma = _sma(close, fast)
      3. slow_sma = _sma(close, slow)
      4. return (fast_sma > slow_sma).fillna(False).astype(int)

    Args:
        df   : OHLCV DataFrame
        fast : fast SMA window (default 20)
        slow : slow SMA window (default 50)
    \"\"\"
    # TODO: implement the 4 steps above
    return pd.Series(0, index=df.index)
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — returns same-length Series
try:
    df  = _synthetic()
    sig = sma_crossover(df)
    assert isinstance(sig, pd.Series) and len(sig) == len(df)
    checks += 1; print("✅ 1 sma_crossover returns same-length Series")
except Exception as e:
    print("❌ 1:", e)

# 2 — no NaN
try:
    sig = sma_crossover(_synthetic())
    assert not sig.isna().any(), "signal has NaN values"
    checks += 1; print("✅ 2 no NaN values")
except Exception as e:
    print("❌ 2:", e)

# 3 — values are only 0 and 1
try:
    sig = sma_crossover(_synthetic())
    assert set(sig.unique()).issubset({0, 1}), f"unexpected values: {set(sig.unique())}"
    checks += 1; print("✅ 3 signal values are only 0 and 1")
except Exception as e:
    print("❌ 3:", e)

# 4 — produces both 0s and 1s on sine-wave data
try:
    sig = sma_crossover(_synthetic(), fast=10, slow=20)
    assert (sig == 1).any(), "no 1s found — fast never exceeded slow"
    assert (sig == 0).any(), "no 0s found — always long?"
    checks += 1; print("✅ 4 both 0s and 1s present")
except Exception as e:
    print("❌ 4:", e)

# 5 — signal is 1 exactly when fast SMA > slow SMA
try:
    df      = _synthetic()
    close   = df["Close"]
    fast20  = close.rolling(20).mean()
    slow50  = close.rolling(50).mean()
    expected = (fast20 > slow50).fillna(False).astype(int)
    sig      = sma_crossover(df, 20, 50)
    assert (sig == expected).all(), "signal does not match fast_sma > slow_sma"
    checks += 1; print("✅ 5 signal matches fast_sma > slow_sma exactly")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX2 = _nb([
    _md("# Exercise 2 — RSI Mean Reversion\n\n"
        "RSI mean reversion bets that an oversold market will bounce back. "
        "When RSI falls below 30 (too much selling), go long. When it rises "
        "above 70 (too much buying), go flat. Between the thresholds, hold "
        "the previous position — avoiding whipsaw from small RSI fluctuations."),
    _code(_P_BASE + _P_SMA_CROSS + """\

def rsi_mean_reversion(df, window=14, oversold=30, overbought=70):
    \"\"\"Long when RSI < oversold; flat when RSI > overbought; hold otherwise.

    Steps:
      1. rsi_s  = _rsi(df["Close"], window)
      2. signal = pd.Series(float("nan"), index=df.index)
      3. signal[rsi_s < oversold]   = 1.0
      4. signal[rsi_s > overbought] = 0.0
      5. return signal.ffill().fillna(0).astype(int)

    The ffill() carries the last explicit 0 or 1 through the neutral zone.
    The final fillna(0) handles the warmup period (before first RSI value).
    \"\"\"
    # TODO: implement the 5 steps above
    return pd.Series(0, index=df.index)
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — returns same-length Series, no NaN, values in {0,1}
try:
    df  = _synthetic()
    sig = rsi_mean_reversion(df)
    assert isinstance(sig, pd.Series) and len(sig) == len(df)
    assert not sig.isna().any()
    assert set(sig.unique()).issubset({0, 1})
    checks += 1; print("✅ 1 valid Series: same length, no NaN, values in {0,1}")
except Exception as e:
    print("❌ 1:", e)

# 2 — with loose thresholds, produces both 0s and 1s
try:
    sig = rsi_mean_reversion(_synthetic(), window=14, oversold=40, overbought=60)
    assert (sig == 1).any(), "no 1s with oversold=40"
    assert (sig == 0).any(), "no 0s with overbought=60"
    checks += 1; print("✅ 2 produces both 0s and 1s with loose thresholds")
except Exception as e:
    print("❌ 2:", e)

# 3 — when RSI is forced below oversold, signal = 1
try:
    df    = _synthetic()
    close = df["Close"]
    # Compute RSI to find an oversold bar
    d = close.diff()
    g = d.clip(lower=0).rolling(14).mean()
    l = (-d.clip(upper=0)).rolling(14).mean()
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        rs = g / l
    rsi_s = 100 - (100 / (1 + rs))
    oversold_mask = rsi_s < 30
    if oversold_mask.any():
        sig = rsi_mean_reversion(df, window=14, oversold=30, overbought=70)
        assert (sig[oversold_mask] == 1).all(), "oversold bars should give signal=1"
    checks += 1; print("✅ 3 RSI < oversold → signal = 1")
except Exception as e:
    print("❌ 3:", e)

# 4 — when RSI > overbought, signal = 0
try:
    df    = _synthetic()
    close = df["Close"]
    d = close.diff()
    g = d.clip(lower=0).rolling(14).mean()
    l = (-d.clip(upper=0)).rolling(14).mean()
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        rs = g / l
    rsi_s = 100 - (100 / (1 + rs))
    overbought_mask = rsi_s > 70
    if overbought_mask.any():
        sig = rsi_mean_reversion(df, window=14, oversold=30, overbought=70)
        assert (sig[overbought_mask] == 0).all(), "overbought bars should give signal=0"
    checks += 1; print("✅ 4 RSI > overbought → signal = 0")
except Exception as e:
    print("❌ 4:", e)

# 5 — default period: signal is 0 for first window rows
try:
    df  = _synthetic()
    sig = rsi_mean_reversion(df, window=14)
    # Before first RSI value, signal should be 0 (from fillna(0))
    assert sig.iloc[0] == 0, f"expected 0 before first RSI, got {sig.iloc[0]}"
    checks += 1; print("✅ 5 warmup period (before first RSI) gives signal=0")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX3 = _nb([
    _md("# Exercise 3 — MACD Cross\n\n"
        "The MACD crossover is a momentum signal. The MACD line "
        "(fast EMA − slow EMA) measures how quickly price is accelerating. "
        "The signal line smooths the MACD. When MACD crosses above its signal "
        "line, momentum is building upward — go long. When it crosses below, "
        "momentum has turned negative — go flat."),
    _code(_P_BASE + _P_SMA_CROSS + _P_RSI_MR + """\

def macd_cross(df, fast=12, slow=26, signal=9):
    \"\"\"Long (1) when the MACD line is above the signal line; flat (0) otherwise.

    Steps:
      1. close       = df["Close"]
      2. macd_line   = _ema(close, fast) - _ema(close, slow)
      3. signal_line = _ema(macd_line, signal)
      4. return (macd_line > signal_line).astype(int)

    No NaN values — EMA starts from the first observation.
    \"\"\"
    # TODO: implement the 4 steps above
    return pd.Series(0, index=df.index)
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — returns same-length Series, no NaN, values in {0,1}
try:
    df  = _synthetic()
    sig = macd_cross(df)
    assert isinstance(sig, pd.Series) and len(sig) == len(df)
    assert not sig.isna().any()
    assert set(sig.unique()).issubset({0, 1})
    checks += 1; print("✅ 1 valid Series: same length, no NaN, values in {0,1}")
except Exception as e:
    print("❌ 1:", e)

# 2 — produces both 0s and 1s on sine-wave data
try:
    sig = macd_cross(_synthetic())
    assert (sig == 1).any(), "no 1s — MACD never crossed above signal"
    assert (sig == 0).any(), "no 0s — MACD always above signal?"
    checks += 1; print("✅ 2 produces both 0s and 1s")
except Exception as e:
    print("❌ 2:", e)

# 3 — signal matches macd_line > signal_line
try:
    df          = _synthetic()
    close       = df["Close"]
    macd_line   = _ema(close, 12) - _ema(close, 26)
    signal_line = _ema(macd_line, 9)
    expected    = (macd_line > signal_line).astype(int)
    sig         = macd_cross(df, 12, 26, 9)
    assert (sig == expected).all(), "signal doesn't match macd > signal"
    checks += 1; print("✅ 3 signal matches macd_line > signal_line exactly")
except Exception as e:
    print("❌ 3:", e)

# 4 — for a monotonically rising series, MACD > signal most of the time
try:
    dates   = pd.date_range("2023-01-01", periods=100, freq="B")
    rising  = pd.DataFrame({"Close": [float(i) for i in range(1, 101)]}, index=dates)
    sig     = macd_cross(rising, fast=5, slow=20, signal=3)
    # After warmup (last 50 rows), signal should be 1 (fast ema above slow)
    tail_sig = sig.iloc[-50:]
    assert (tail_sig == 1).all(), f"rising prices: expected all 1s in tail, got {tail_sig.value_counts().to_dict()}"
    checks += 1; print("✅ 4 monotonically rising prices → MACD signal = 1 at tail")
except Exception as e:
    print("❌ 4:", e)

# 5 — for a monotonically falling series, MACD < signal at tail
try:
    dates    = pd.date_range("2023-01-01", periods=100, freq="B")
    falling  = pd.DataFrame({"Close": [float(100 - i) for i in range(100)]}, index=dates)
    sig      = macd_cross(falling, fast=5, slow=20, signal=3)
    tail_sig = sig.iloc[-50:]
    assert (tail_sig == 0).all(), f"falling prices: expected all 0s in tail, got {tail_sig.value_counts().to_dict()}"
    checks += 1; print("✅ 5 monotonically falling prices → MACD signal = 0 at tail")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX4 = _nb([
    _md("# Exercise 4 — Combined Signal\n\n"
        "`combined_signal` is the integration function. It requires both the "
        "SMA crossover (trend confirmation) AND the MACD cross (momentum "
        "confirmation) to be positive before going long. Requiring two "
        "independent signals to agree reduces false entries at the cost of "
        "entering later in the trend. This is the classical 'signal confluence' "
        "approach used in systematic strategies."),
    _code(_P_BASE + _P_SMA_CROSS + _P_RSI_MR + _P_MACD_CROSS + """\

def combined_signal(df, fast=20, slow=50, macd_fast=12, macd_slow=26, macd_sig=9):
    \"\"\"Long only when SMA crossover AND MACD cross both agree.

    Steps:
      1. sma_sig  = sma_crossover(df, fast, slow)
      2. macd_sig = macd_cross(df, macd_fast, macd_slow, macd_sig)
      3. return ((sma_sig == 1) & (macd_sig == 1)).astype(int)

    More conservative than either signal alone.
    \"\"\"
    # TODO: implement the 3 steps above
    return pd.Series(0, index=df.index)
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — returns same-length Series, no NaN, values in {0,1}
try:
    df  = _synthetic()
    sig = combined_signal(df)
    assert isinstance(sig, pd.Series) and len(sig) == len(df)
    assert not sig.isna().any()
    assert set(sig.unique()).issubset({0, 1})
    checks += 1; print("✅ 1 valid Series: same length, no NaN, values in {0,1}")
except Exception as e:
    print("❌ 1:", e)

# 2 — combined is more conservative: sum(combined) <= sum(sma_cross) and sum(macd_cross)
try:
    df       = _synthetic()
    sma_sig  = sma_crossover(df, 20, 50)
    macd_sig = macd_cross(df)
    comb_sig = combined_signal(df)
    assert comb_sig.sum() <= sma_sig.sum(), \
        f"combined ({comb_sig.sum()}) should have ≤ 1s than SMA ({sma_sig.sum()})"
    assert comb_sig.sum() <= macd_sig.sum(), \
        f"combined ({comb_sig.sum()}) should have ≤ 1s than MACD ({macd_sig.sum()})"
    checks += 1; print("✅ 2 combined is more conservative (fewer or equal 1s)")
except Exception as e:
    print("❌ 2:", e)

# 3 — combined = 1 only when both sma and macd are 1
try:
    df       = _synthetic()
    sma_sig  = sma_crossover(df, 20, 50)
    macd_sig = macd_cross(df)
    comb_sig = combined_signal(df)
    expected = ((sma_sig == 1) & (macd_sig == 1)).astype(int)
    assert (comb_sig == expected).all(), "combined != sma AND macd"
    checks += 1; print("✅ 3 combined = sma_cross AND macd_cross")
except Exception as e:
    print("❌ 3:", e)

# 4 — combined = 0 when either signal is 0
try:
    df       = _synthetic()
    sma_sig  = sma_crossover(df, 20, 50)
    macd_sig = macd_cross(df)
    comb_sig = combined_signal(df)
    # Wherever either is 0, combined must be 0
    either_zero = (sma_sig == 0) | (macd_sig == 0)
    assert (comb_sig[either_zero] == 0).all()
    checks += 1; print("✅ 4 combined = 0 whenever either component is 0")
except Exception as e:
    print("❌ 4:", e)

# 5 — combined = 1 only where both are 1
try:
    df       = _synthetic()
    sma_sig  = sma_crossover(df, 20, 50)
    macd_sig = macd_cross(df)
    comb_sig = combined_signal(df)
    both_one = (sma_sig == 1) & (macd_sig == 1)
    assert (comb_sig[both_one] == 1).all()
    checks += 1; print("✅ 5 combined = 1 only where both signals are 1")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX5 = _nb([
    _md("# Exercise 5 — Strategy Backtest Comparison\n\n"
        "Run all four strategies through the backtester and compare their metrics. "
        "The goal is not to find the 'best' strategy on synthetic data — sine-wave "
        "prices are not real. The goal is to practise reading the metrics table and "
        "understanding the trade-offs between trend-following, mean-reversion, "
        "momentum, and combined strategies."),
    _code(_P_BASE + _P_SMA_CROSS + _P_RSI_MR + _P_MACD_CROSS + _P_COMBINED + _P_BACKTEST),
    _md("### Build signals and run backtests"),
    _code("""\
df = _synthetic(n=252)

sig_sma  = sma_crossover(df)
sig_rsi  = rsi_mean_reversion(df, oversold=35, overbought=65)
sig_macd = macd_cross(df)
sig_comb = combined_signal(df)
sig_bah  = pd.Series(1, index=df.index)   # benchmark: buy-and-hold

r_sma  = run_backtest(df, sig_sma,  "SMA-cross")
r_rsi  = run_backtest(df, sig_rsi,  "RSI-MR")
r_macd = run_backtest(df, sig_macd, "MACD-cross")
r_comb = run_backtest(df, sig_comb, "Combined")
r_bah  = run_backtest(df, sig_bah,  "Buy-Hold")
"""),
    _md("### Print metrics table"),
    _code("""\
checks = 0

# 1 — all results have required keys
try:
    REQUIRED = {"total_return","annualized_return","sharpe_ratio","max_drawdown","win_rate","n_trades","equity"}
    for r in [r_sma, r_rsi, r_macd, r_comb, r_bah]:
        assert REQUIRED.issubset(r.keys()), f"missing keys in {r.get('label')}"
    checks += 1; print("✅ 1 all backtest results have required keys")
except Exception as e:
    print("❌ 1:", e)

# 2 — equity[-1] == 1 + total_return for all
try:
    for r in [r_sma, r_rsi, r_macd, r_comb, r_bah]:
        diff = abs(r["equity"].iloc[-1] - (1 + r["total_return"]))
        assert diff < 1e-9, f"equity/total_return mismatch for {r['label']}"
    checks += 1; print("✅ 2 equity[-1] == 1 + total_return for all strategies")
except Exception as e:
    print("❌ 2:", e)

# 3 — combined has fewer or equal trades than SMA crossover
try:
    assert r_comb["n_trades"] <= r_sma["n_trades"] + 1, \
        f"combined ({r_comb['n_trades']}) has more trades than SMA ({r_sma['n_trades']})"
    checks += 1; print("✅ 3 combined strategy has fewer or equal trades")
except Exception as e:
    print("❌ 3:", e)

# 4 — max_drawdown is negative for all strategies
try:
    for r in [r_sma, r_rsi, r_macd, r_comb, r_bah]:
        assert r["max_drawdown"] <= 1e-9, \
            f"{r['label']}: drawdown should be ≤ 0, got {r['max_drawdown']}"
    checks += 1; print("✅ 4 all max_drawdown values are ≤ 0")
except Exception as e:
    print("❌ 4:", e)

# 5 — print comparison table
try:
    results = [r_bah, r_sma, r_rsi, r_macd, r_comb]
    print(f"\\n{'Metric':<20}", end="")
    for r in results: print(f" {r['label']:>10}", end="")
    print("\\n" + "-" * 72)
    for key, fmt in [
        ("total_return",      ".2%"),
        ("sharpe_ratio",      ".3f"),
        ("max_drawdown",      ".2%"),
        ("win_rate",          ".2%"),
        ("n_trades",          "d"),
    ]:
        print(f"{key:<20}", end="")
        for r in results:
            v = r[key]
            if fmt == "d":
                print(f" {v:>10d}", end="")
            else:
                print(f" {v:>{10}{fmt}}", end="")
        print()
    checks += 1; print("\\n✅ 5 comparison table printed")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

EXERCISES = [_EX1, _EX2, _EX3, _EX4, _EX5]

# ══════════════════════════════════════════════════════════════════════════════
# YAML lessons
# ══════════════════════════════════════════════════════════════════════════════

LESSONS = [
    """\
day: "092"
lesson: 1
title: "What Makes a Trading Strategy?"
slides:
  - type: title
    heading: "Building a Strategy"
    subheading: "Turn indicator rules into actionable signals"
    narration: >
      Day 92. You have a backtester from Day 91 and indicators from Day 90.
      Today you write the strategies: the rules that convert indicator values
      into buy and sell decisions. You will build three strategies — SMA
      crossover, RSI mean reversion, and MACD crossover — then combine them
      into a single filtered signal. Each strategy represents a different market
      hypothesis: trend-following, mean-reversion, and momentum. By the end of
      today, you can generate and backtest any rule-based signal in a few lines.

  - type: concept
    label: "Signal anatomy"
    heading: "Anatomy of a Signal"
    body: >
      A signal is a rule applied to indicators that produces a position: 1 (long),
      0 (flat), or -1 (short).
    bullets:
      - "If (indicator condition) then position = 1, else position = 0"
      - "Signal must use only past information — no future data"
      - "Entry rule: when to go from 0 to 1"
      - "Exit rule: when to go from 1 to 0"
      - "Hold rule: what to do between entry and exit (usually: hold)"
    narration: >
      The signal is the bridge between indicators and the backtest engine.
      indicators.py computes SMA, EMA, RSI, MACD, Bollinger Bands. The backtest
      engine takes a signal Series and computes returns. strategy.py sits in
      the middle: it reads indicators from df and writes a signal Series.
      Every strategy you write this week follows the same pattern: compute an
      indicator, apply a threshold rule, return a 0/1 Series.

  - type: concept
    label: "Three strategy types"
    heading: "Three Market Hypotheses"
    body: >
      Different strategies bet on different market behaviors.
    bullets:
      - "Trend-following: markets that go up continue going up (momentum)"
      - "Mean-reversion: markets that fall too far bounce back"
      - "Momentum crossover: strength of trend measured by EMA divergence"
      - "Combined: require multiple hypotheses to agree → fewer but better entries"
      - "No single type works in all markets — diversification applies to strategies too"
    narration: >
      Trend-following works well in trending markets and fails in choppy ones.
      Mean-reversion works in range-bound markets and fails in strong trends.
      This is why professional quant funds run many strategies simultaneously:
      they are betting on different market regimes. When one regime fails,
      another succeeds. Today you build three complementary strategies that
      represent these three different market hypotheses.

  - type: exercise
    heading: "Exercise 1 — SMA Crossover"
    prompt: >
      Implement sma_crossover(df, fast=20, slow=50) that returns 1 when
      the fast SMA is above the slow SMA, 0 otherwise. No NaN values.
      Use _sma(series, window) = series.rolling(window).mean().
    hint: >
      (fast_sma > slow_sma) returns a boolean Series. .fillna(False) converts
      the first slow-1 NaN values to False. .astype(int) converts True/False
      to 1/0.
    narration: >
      One line after the two SMA computations. The fillna(False) is important:
      before the first slow SMA value is available, the comparison would
      produce NaN, which .astype(int) would convert to 0 anyway — but
      explicitly filling is safer and makes the intent clear. Check 5 verifies
      that your output matches the expected boolean comparison exactly.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "A signal is a rule on indicators producing {-1, 0, 1}"
      - "Three types: trend-following, mean-reversion, momentum"
      - "Combined signals require multiple hypotheses to agree"
      - "sma_crossover: 1 when fast_sma > slow_sma, 0 otherwise"
      - "Next: RSI mean reversion and MACD crossover"
    narration: >
      The SMA crossover is the foundation. Next you will build RSI mean
      reversion — a completely different market hypothesis — and then MACD
      crossover, which combines two EMAs. All three will be fed into the
      backtester in Exercise 5.
""",

    """\
day: "092"
lesson: 2
title: "SMA Crossover — Trend-Following"
slides:
  - type: title
    heading: "SMA Crossover"
    subheading: "The oldest trend-following rule"
    narration: >
      The SMA crossover has been used in markets since long before computers.
      The idea is simple: if short-term average prices are above long-term
      average prices, the market is in an uptrend. Go long. When the short-term
      average falls below the long-term, the trend has reversed. Go flat or
      short. Despite its simplicity, some version of this rule appears in almost
      every major systematic trading fund.

  - type: concept
    label: "Fast vs slow SMA"
    heading: "Fast and Slow SMAs: Two Views of the Trend"
    body: >
      The crossover captures the gap between short-term and long-term momentum.
    bullets:
      - "Fast SMA (20): tracks last month's average — short-term trend"
      - "Slow SMA (50): tracks last quarter's average — long-term trend"
      - "fast > slow: short-term strength above long-term mean → uptrend"
      - "fast < slow: short-term weakness below long-term mean → downtrend"
      - "The crossover event (from below to above) is the entry trigger"
    narration: >
      The 20/50 crossover is sometimes called the golden cross when the faster
      SMA crosses above the slower SMA, and the death cross when it crosses
      below. Professional traders use the 50/200 crossover for longer-term
      signals. The shorter the windows, the more trades are generated — but
      also more false signals. Longer windows give fewer, cleaner signals but
      react slowly to trend changes.

  - type: code
    label: "sma_crossover"
    heading: "Implementation: Four Lines"
    body: >
      The comparison produces a boolean; astype(int) converts to signal.
    code: |
      def sma_crossover(df, fast=20, slow=50):
          close    = df["Close"]
          fast_sma = close.rolling(fast).mean()
          slow_sma = close.rolling(slow).mean()
          return (fast_sma > slow_sma).fillna(False).astype(int)

      # fillna(False): before enough data for slow SMA, output 0
      # astype(int):   True → 1, False → 0; no NaN in output
    narration: >
      The output has no NaN because fillna(False) handles the warmup period.
      For the first slow-1 bars, both SMAs may be NaN. The comparison of
      NaN with NaN produces NaN. fillna(False) replaces those NaN with False,
      which then becomes 0. After the slow SMA has enough data, all values are
      True or False — no NaN at all.

  - type: concept
    label: "Trade-offs"
    heading: "Trend-Following Trade-Offs"
    body: >
      No strategy is free — SMA crossover has known failure modes.
    bullets:
      - "Works well in trending markets; loses money in choppy, range-bound markets"
      - "Lags price: enters after the trend starts, exits after it ends"
      - "Whipsaw: generates many trades when price oscillates near the crossover"
      - "Longer windows: fewer trades, less whipsaw, more lag"
      - "Adding filters (RSI, MACD) reduces whipsaw at the cost of fewer entries"
    narration: >
      Whipsaw is the biggest problem with SMA crossover: when price oscillates
      around the crossover level, the strategy generates many small losing trades.
      Each individual loss is small, but many small losses add up. The combined
      signal you will build in Exercise 4 adds MACD confirmation to reduce
      whipsaw: only enter when both the trend AND the momentum agree.

  - type: exercise
    heading: "Exercise 1 — SMA Crossover (continued)"
    prompt: >
      Complete your sma_crossover implementation from the previous exercise.
      After passing all checks, compare the number of 1s (long positions) in
      sma_crossover(df, 10, 20) vs sma_crossover(df, 20, 50) on the synthetic
      data. Which generates more long signals?
    hint: >
      sig.sum() gives the count of 1s. The shorter-window crossover (10/20)
      reacts faster and will likely generate more position changes.
    narration: >
      The check 5 verification — that your output matches the reference formula
      exactly — is the most important. It rules out off-by-one errors in the
      window calculation and ensures you are computing the comparison in the
      correct direction.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "SMA crossover: fast_sma > slow_sma → long; otherwise flat"
      - "Works best in trending markets; fails in choppy markets"
      - "Shorter windows: more trades, more whipsaw"
      - "Longer windows: fewer trades, more lag"
      - "Filters like MACD confirmation reduce whipsaw"
    narration: >
      SMA crossover is done. Next: RSI mean reversion — the opposite market
      hypothesis. Where SMA crossover says 'follow the trend,' RSI says
      'bet on the reversal when prices have moved too far too fast.'
""",

    """\
day: "092"
lesson: 3
title: "RSI Mean Reversion"
slides:
  - type: title
    heading: "RSI Mean Reversion"
    subheading: "Buy when the market is oversold; sell when overbought"
    narration: >
      RSI mean reversion is the classic contrarian strategy. When prices have
      fallen so fast that RSI drops below 30, the selling is likely overdone —
      buy, expecting a bounce. When prices have risen so fast that RSI exceeds
      70, the buying is likely exhausted — exit, expecting a pullback. Between
      those thresholds, hold whatever position you had. This is the 'neutral
      zone' that prevents constant entry and exit on small RSI fluctuations.

  - type: concept
    label: "Hold logic"
    heading: "The Hold Zone: Forward-Fill Between Thresholds"
    body: >
      The signal only changes at the thresholds; between them, it holds.
    bullets:
      - "RSI < 30: set signal = 1 (go long)"
      - "RSI > 70: set signal = 0 (go flat)"
      - "30 ≤ RSI ≤ 70: signal = NaN → ffill from previous explicit value"
      - "ffill propagates the last 0 or 1 through the neutral zone"
      - "fillna(0): before first RSI value, default to flat"
    narration: >
      The forward-fill pattern is the key difference between RSI mean reversion
      and a simple threshold filter. Without forward-fill, you would set signal
      to 0 everywhere between thresholds — meaning you exit as soon as RSI
      recovers above 30, even if the position is still profitable. With
      forward-fill, you stay long until RSI hits the overbought level at 70.
      This turns the strategy from a very short-hold scalper into a medium-term
      position holder — a more realistic market behavior.

  - type: code
    label: "rsi_mean_reversion"
    heading: "RSI Mean Reversion: Five Steps"
    body: >
      Set, fill, default.
    code: |
      def rsi_mean_reversion(df, window=14, oversold=30, overbought=70):
          rsi_s  = _rsi(df["Close"], window)    # computed RSI series
          signal = pd.Series(float("nan"), index=df.index)
          signal[rsi_s < oversold]   = 1.0      # explicitly set to long
          signal[rsi_s > overbought] = 0.0      # explicitly set to flat
          return signal.ffill().fillna(0).astype(int)

      # ffill():    carries 0 or 1 forward through the neutral zone
      # fillna(0):  warmup bars before first RSI get 0 (flat)
    narration: >
      The series starts as all-NaN. You then stamp 1.0 at every oversold bar
      and 0.0 at every overbought bar. Everything in between stays NaN. The
      forward-fill propagates the most recent explicit value through the neutral
      zone. The final fillna(0) handles the warmup period where no RSI has been
      computed yet — before enough data exists for a rolling window.

  - type: exercise
    heading: "Exercise 2 — RSI Mean Reversion"
    prompt: >
      Implement rsi_mean_reversion(df, window=14, oversold=30, overbought=70)
      following the five steps. Check 2 uses looser thresholds (40/60) to
      ensure the sine-wave data produces both 0s and 1s. Check 5 verifies
      that the warmup period (before first RSI) gives 0.
    hint: >
      If you get no 1s with default thresholds (30/70), that is correct —
      the synthetic sine wave may not drop below RSI 30. Use oversold=40,
      overbought=60 for the test. The implementation is the same; only the
      thresholds change.
    narration: >
      Pay attention to the order of operations: first stamp the explicit
      values, then forward-fill, then fill remaining NaN with 0.
      If you do fillna(0) before ffill, you will get wrong behavior — the
      warmup 0s will block the forward-fill from propagating.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "RSI mean reversion: buy oversold, sell overbought, hold in between"
      - "Forward-fill carries the last explicit signal through the neutral zone"
      - "Default (warmup period): flat (0) — never trade without enough data"
      - "Works in range-bound markets; fails in strong trends"
      - "Next: MACD crossover — momentum without the threshold complexity"
    narration: >
      RSI mean reversion is done. Next: MACD crossover — a cleaner momentum
      signal that does not need forward-fill because the MACD comparison
      is defined at every bar from the start.
""",

    """\
day: "092"
lesson: 4
title: "MACD Crossover"
slides:
  - type: title
    heading: "MACD Crossover"
    subheading: "Momentum signal from the gap between two EMAs"
    narration: >
      The MACD crossover is a momentum-based signal that avoids the complexity
      of threshold tuning. Long when the MACD line is above the signal line;
      flat when below. No neutral zone, no forward-fill — just a continuous
      {0,1} signal. This makes it easy to combine with other signals: wherever
      the MACD says 'long' and the SMA crossover also says 'long,' you have
      two independent confirmations.

  - type: concept
    label: "MACD as a signal"
    heading: "From Indicator to Signal: One Comparison"
    body: >
      MACD line > signal line → long; MACD line < signal line → flat.
    bullets:
      - "MACD line   = EMA(12) − EMA(26)  — how far fast is above slow"
      - "Signal line = EMA(MACD, 9)       — smoothed MACD"
      - "When MACD > signal: upward momentum is accelerating"
      - "When MACD < signal: upward momentum is fading"
      - "No warmup NaN — EMA starts from the first price"
    narration: >
      The MACD crossover is a signal about a signal: it measures whether the
      gap between two EMAs is growing or shrinking. When the MACD line crosses
      above the signal line, it means the fast EMA has recently gained speed
      relative to the slow EMA — momentum is building. Unlike RSI, there is no
      threshold to tune and no neutral zone to configure. The comparison is
      binary and clean.

  - type: code
    label: "macd_cross"
    heading: "MACD Crossover: Four Lines"
    body: >
      Three computations and one comparison.
    code: |
      def macd_cross(df, fast=12, slow=26, signal=9):
          close       = df["Close"]
          macd_line   = _ema(close, fast) - _ema(close, slow)
          signal_line = _ema(macd_line, signal)
          return (macd_line > signal_line).astype(int)

      # No fillna needed — EMA has no NaN, so macd_line has no NaN,
      # so signal_line has no NaN, so the comparison has no NaN.
    narration: >
      Because EMA starts from the very first observation rather than
      requiring a full window before producing output, every row has a
      defined macd_line and signal_line. The comparison produces a boolean
      Series with no NaN values. astype(int) converts it to {0, 1}. This
      is simpler than RSI because there is no warmup NaN to handle.

  - type: concept
    label: "Combined signal"
    heading: "Combined Signal: Confidence Through Confluence"
    body: >
      Require two independent signals to agree before entering a trade.
    bullets:
      - "SMA crossover: uptrend confirmed (fast SMA > slow SMA)"
      - "MACD cross:    momentum positive (MACD > signal)"
      - "Combined: 1 only when BOTH are 1"
      - "Fewer entries, but higher confidence per entry"
      - "combined.sum() ≤ min(sma.sum(), macd.sum()) — stricter than either"
    narration: >
      Signal confluence is one of the most reliable risk filters in systematic
      trading. When two independent indicators built on different formulas and
      different time horizons both say 'buy,' the probability that the signal
      is a false positive is lower than when only one says it. The cost is
      that you enter later in the trend and miss some moves entirely. Whether
      the trade-off is worth it depends on the market and the transaction costs.

  - type: exercise
    heading: "Exercises 3 and 4 — MACD Cross and Combined Signal"
    prompt: >
      Implement macd_cross(df, fast=12, slow=26, signal=9) in Exercise 3.
      Then implement combined_signal(df, ...) in Exercise 4 by calling
      sma_crossover and macd_cross and taking their logical AND.
    hint: >
      Check 2 of Exercise 4: combined.sum() must be ≤ both sma.sum() and
      macd.sum(). Check 3 verifies that combined == (sma==1 & macd==1)
      exactly. If check 3 fails, make sure you are using astype(int) at
      the end rather than returning a boolean Series.
    narration: >
      Two exercises for one lesson. MACD cross is straightforward. Combined
      signal is one line after the two calls. The value of these exercises
      is not the implementation — it is understanding what the output looks
      like: combined has fewer 1s than either component because it requires
      both to agree simultaneously.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "MACD cross: macd_line > signal_line → 1; no NaN"
      - "Signal confluence: AND of two independent signals"
      - "Combined signal is more conservative: fewer but higher-quality entries"
      - "Three strategy types built: trend (SMA), mean-reversion (RSI), momentum (MACD)"
      - "Next: backtest all three and read the comparison table"
    narration: >
      All three strategies and the combined signal are done. Exercise 5 runs
      all of them through the backtester and prints a comparison table. You
      will see how different market hypotheses produce different metric profiles:
      trend strategies have high Sharpe but few trades; mean-reversion strategies
      have lower Sharpe but more trades. Neither is universally better.
""",

    """\
day: "092"
lesson: 5
title: "Evaluating and Comparing Strategies"
slides:
  - type: title
    heading: "Comparing Strategies"
    subheading: "Read the metrics table — not just total return"
    narration: >
      The final lesson covers how to evaluate and compare strategies. Running
      a backtest is easy. Interpreting it correctly is the skill. Total return
      is the least useful metric in isolation — a strategy that earns 50% with
      a 60% drawdown is worse than one that earns 30% with a 10% drawdown.
      This lesson teaches you to read the full metrics table and understand
      what each number means for strategy quality.

  - type: concept
    label: "Reading metrics"
    heading: "How to Read a Backtest Metrics Table"
    body: >
      Every metric answers a different question.
    bullets:
      - "total_return: how much did it make? (least useful alone)"
      - "sharpe_ratio: how much return per unit of risk? (most useful)"
      - "max_drawdown: what is the worst case? (survival question)"
      - "win_rate: fraction of trading days with positive P&L"
      - "n_trades: how often does it trade? (proxy for transaction costs)"
    narration: >
      The Sharpe ratio is the single most important number. A Sharpe of 2.0
      with 15% return beats a Sharpe of 0.5 with 30% return — the second
      strategy is taking four times as much risk to earn twice as much. Max
      drawdown is the second most important: if the drawdown exceeds your
      psychological tolerance or risk limits, the strategy is undriveable
      regardless of Sharpe. Win rate and n_trades matter for implementation:
      a strategy that trades 200 times per year at 0.1% transaction cost is
      losing 20% to costs before making any profit.

  - type: concept
    label: "Strategy trade-offs"
    heading: "Expected Trade-Off Profile by Strategy Type"
    body: >
      Different strategies have different metric fingerprints.
    bullets:
      - "Trend-following (SMA): high Sharpe in trending markets, few trades"
      - "Mean-reversion (RSI): more trades, often lower Sharpe, low drawdown"
      - "Momentum (MACD): intermediate — more responsive than SMA, less noise than RSI"
      - "Combined: lowest n_trades, highest quality per trade — but misses many moves"
      - "Buy-and-hold: highest drawdown, zero complexity — the benchmark"
    narration: >
      On the synthetic sine-wave data, these profiles will not be as clean as
      in real markets — the sine wave is too regular. But the structural
      relationships still hold: combined has fewer trades than SMA or MACD,
      RSI mean-reversion has more trades, buy-and-hold has the largest drawdown
      because it is always exposed. Learning to read these patterns on synthetic
      data prepares you for interpreting real market results where the noise is
      much higher.

  - type: code
    label: "Comparison table"
    heading: "Printing a Side-by-Side Comparison"
    body: >
      Run all strategies; print one row per metric.
    code: |
      strategies = [
          ("Buy-Hold", pd.Series(1, index=df.index)),
          ("SMA-cross", sma_crossover(df)),
          ("RSI-MR",    rsi_mean_reversion(df, oversold=35, overbought=65)),
          ("MACD",      macd_cross(df)),
          ("Combined",  combined_signal(df)),
      ]
      results = [run_backtest(df, sig, label) for label, sig in strategies]

      # Print table
      for key in ["total_return","sharpe_ratio","max_drawdown","n_trades"]:
          row = f"{key:<20}"
          for r in results:
              v = r[key]
              row += f" {v:>10.2%}" if isinstance(v, float) else f" {v:>10d}"
          print(row)
    narration: >
      The comparison table is what you would show a potential investor or
      manager. It makes the trade-offs visible at a glance. A strategy with
      great Sharpe but 200 trades per year has hidden costs that may eliminate
      the edge. A strategy with poor Sharpe but very low drawdown might still
      be useful as part of a diversified portfolio. No single row of the table
      tells the full story.

  - type: exercise
    heading: "Exercise 5 — Full Strategy Comparison"
    prompt: >
      Using the prelude implementations of all four strategies plus run_backtest,
      run all five strategies (including buy-and-hold) and print the comparison
      table. The 5 checks verify: correct keys, equity consistency, combined is
      conservative, all drawdowns ≤ 0, and the table prints successfully.
    hint: >
      Check 3 allows combined to have n_trades up to sma_trades + 1 because
      the initial position transition (0→1) can differ. If it fails, check that
      combined_signal returns the logical AND of sma_crossover and macd_cross.
    narration: >
      This exercise is the payoff for three days of work. Day 89 fetched
      data. Day 90 computed indicators. Day 91 built the backtest engine.
      Day 92 built the strategies. All four layers running together in one
      notebook is the Section 7 stack in miniature.

  - type: summary
    heading: "Day 92 Complete"
    bullets:
      - "sma_crossover: trend-following via fast/slow SMA comparison"
      - "rsi_mean_reversion: contrarian via RSI thresholds + forward-fill"
      - "macd_cross: momentum via MACD line vs signal line comparison"
      - "combined_signal: confluence filter requiring trend AND momentum"
      - "Metrics: Sharpe > total_return; drawdown > win_rate in importance"
    narration: >
      Four strategies built and tested. Day 93 adds a fifth signal source:
      AI-driven news sentiment. Instead of computing signals from price data,
      you will call an LLM to analyze news headlines and produce a sentiment
      score that feeds into the backtest as a signal. This is the point where
      AI engineering intersects with quantitative trading.
""",
]

# ══════════════════════════════════════════════════════════════════════════════
# Project + solution
# ══════════════════════════════════════════════════════════════════════════════

_FULL_P = _P_BASE + _P_SMA_CROSS + _P_RSI_MR + _P_MACD_CROSS + _P_COMBINED + _P_BACKTEST

PROJECT_NB = _nb([
    _md(f"# Day {DAY} Project — Strategy Lab\n\n"
        "Run all four strategies plus buy-and-hold on 252 days of synthetic "
        "OHLCV data. Print the comparison table and identify which strategy "
        "has the highest Sharpe ratio."),
    _code(_FULL_P),
    _code("""\
df = _synthetic(n=252)

strategies = [
    ("Buy-Hold", pd.Series(1, index=df.index)),
    ("SMA-cross", sma_crossover(df)),
    ("RSI-MR",    rsi_mean_reversion(df, oversold=35, overbought=65)),
    ("MACD",      macd_cross(df)),
    ("Combined",  combined_signal(df)),
]
results = [run_backtest(df, sig, label) for label, sig in strategies]
"""),
    _code("""\
labels = [r["label"] for r in results]
print(f"{'Metric':<22}", " ".join(f"{l:>10}" for l in labels))
print("-" * (22 + 11 * len(labels)))
for key, fmt in [
    ("total_return",      ".2%"),
    ("annualized_return", ".2%"),
    ("sharpe_ratio",      ".3f"),
    ("max_drawdown",      ".2%"),
    ("win_rate",          ".2%"),
    ("n_trades",          "d"),
]:
    vals = []
    for r in results:
        v = r[key]
        vals.append(f"{v:>{10}{fmt}}" if fmt != "d" else f"{v:>10d}")
    print(f"{key:<22}", " ".join(vals))

best = max(results, key=lambda r: r["sharpe_ratio"])
print(f"\\nBest Sharpe: {best['label']} ({best['sharpe_ratio']:.3f})")
"""),
])

SOLUTION_NB = _nb([
    _md(f"# Day {DAY} Solution — Strategy Lab"),
    _code(_FULL_P),
    _code("""\
df = _synthetic(n=252)

strategies = [
    ("Buy-Hold", pd.Series(1, index=df.index)),
    ("SMA-cross", sma_crossover(df)),
    ("RSI-MR",    rsi_mean_reversion(df, oversold=35, overbought=65)),
    ("MACD",      macd_cross(df)),
    ("Combined",  combined_signal(df)),
]
results = [run_backtest(df, sig, label) for label, sig in strategies]

# Assertions
REQUIRED = {"label","total_return","annualized_return","sharpe_ratio",
            "max_drawdown","win_rate","n_trades","equity"}
for r in results:
    assert REQUIRED.issubset(r.keys())
    assert r["max_drawdown"] <= 1e-9
    assert abs(r["equity"].iloc[-1] - (1 + r["total_return"])) < 1e-9

comb = next(r for r in results if r["label"] == "Combined")
sma  = next(r for r in results if r["label"] == "SMA-cross")
macd = next(r for r in results if r["label"] == "MACD")
assert comb["n_trades"] <= max(sma["n_trades"], macd["n_trades"]) + 1

labels = [r["label"] for r in results]
print(f"{'Metric':<22}", " ".join(f"{l:>10}" for l in labels))
print("-" * (22 + 11 * len(labels)))
for key, fmt in [
    ("total_return",      ".2%"),
    ("sharpe_ratio",      ".3f"),
    ("max_drawdown",      ".2%"),
    ("n_trades",          "d"),
]:
    vals = []
    for r in results:
        v = r[key]
        vals.append(f"{v:>{10}{fmt}}" if fmt != "d" else f"{v:>10d}")
    print(f"{key:<22}", " ".join(vals))

best = max(results, key=lambda r: r["sharpe_ratio"])
print(f"\\nBest Sharpe: {best['label']} ({best['sharpe_ratio']:.3f})")
print("\\nSolution smoke-test passed.")
"""),
])

# ══════════════════════════════════════════════════════════════════════════════
# Gate
# ══════════════════════════════════════════════════════════════════════════════

GATE_PY = f"""\
import importlib.util, sys, math, warnings
import pandas as pd

spec = importlib.util.spec_from_file_location(
    "{SLUG}", r"{DIR / (SLUG + '.py')}"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

n      = 252
prices = [100.0 * (1 + 0.3 * math.sin(i * 2 * math.pi / 252)) for i in range(n)]
dates  = pd.date_range("2023-01-01", periods=n, freq="B")
close  = pd.Series(prices, index=dates)
df = pd.DataFrame({{
    "Open":   close.shift(1).fillna(close.iloc[0]),
    "High":   close * 1.01,
    "Low":    close * 0.99,
    "Close":  close,
    "Volume": pd.Series([1_000_000 + i * 1_000 for i in range(n)], index=dates),
}})

def _check(sig, name):
    assert isinstance(sig, pd.Series) and len(sig) == n, f"{{name}}: wrong type/length"
    assert not sig.isna().any(),                          f"{{name}}: NaN found"
    assert set(sig.unique()).issubset({{0, 1}}),           f"{{name}}: values not in {{0,1}}"

# sma_crossover
sma_sig = mod.sma_crossover(df, 10, 20)
_check(sma_sig, "sma_crossover")
assert (sma_sig == 1).any() and (sma_sig == 0).any(), "sma_crossover: must have both 0s and 1s"
fast20 = close.rolling(10).mean(); slow50 = close.rolling(20).mean()
expected = (fast20 > slow50).fillna(False).astype(int)
assert (sma_sig == expected).all(), "sma_crossover: mismatch with reference"

# rsi_mean_reversion — use loose thresholds to ensure both 0s and 1s
rsi_sig = mod.rsi_mean_reversion(df, window=14, oversold=40, overbought=60)
_check(rsi_sig, "rsi_mean_reversion")
assert (rsi_sig == 1).any() and (rsi_sig == 0).any(), "rsi_mean_reversion: must have both 0s and 1s"
assert rsi_sig.iloc[0] == 0, "rsi_mean_reversion: warmup should give 0"

# macd_cross
macd_sig = mod.macd_cross(df, 12, 26, 9)
_check(macd_sig, "macd_cross")
assert (macd_sig == 1).any() and (macd_sig == 0).any(), "macd_cross: must have both 0s and 1s"
# monotone rising → macd > signal at tail
rising_d = pd.date_range("2023-01-01", periods=80, freq="B")
rising   = pd.DataFrame({{"Close": [float(i) for i in range(1, 81)]}}, index=rising_d)
rising["Open"] = rising["Close"]; rising["High"] = rising["Close"]
rising["Low"]  = rising["Close"]; rising["Volume"] = 1_000_000
rsig = mod.macd_cross(rising, fast=5, slow=20, signal=3)
assert (rsig.iloc[-30:] == 1).all(), "macd_cross: rising prices should give signal=1 at tail"

# combined_signal
comb_sig = mod.combined_signal(df, 10, 20, 12, 26, 9)
_check(comb_sig, "combined_signal")
assert comb_sig.sum() <= sma_sig.sum(), "combined: not more conservative than SMA"
assert comb_sig.sum() <= macd_sig.sum(), "combined: not more conservative than MACD"
# combined = sma AND macd
expected_comb = ((sma_sig == 1) & (macd_sig == 1)).astype(int)
assert (comb_sig == expected_comb).all(), "combined: does not equal sma AND macd"

print("Gate: all inline checks passed")
"""

# ══════════════════════════════════════════════════════════════════════════════
# main
# ══════════════════════════════════════════════════════════════════════════════

def main():
    import subprocess, sys, re

    (DIR / "exercises").mkdir(parents=True, exist_ok=True)
    (DIR / "lessons").mkdir(parents=True, exist_ok=True)
    (DIR / "project" / "solution").mkdir(parents=True, exist_ok=True)

    (DIR / f"{SLUG}.py").write_text(DELIVERABLE, encoding="utf-8")
    (DIR / "project" / "solution" / f"{SLUG}.py").write_text(DELIVERABLE, encoding="utf-8")

    for i, nb in enumerate(EXERCISES, 1):
        (DIR / "exercises" / f"exercise_{i:02d}.ipynb").write_text(
            json.dumps(nb, indent=1), encoding="utf-8")

    for i, yaml_text in enumerate(LESSONS, 1):
        (DIR / "lessons" / f"day_{DAY}_lesson_{i:02d}.yaml").write_text(
            yaml_text, encoding="utf-8")

    (DIR / "project" / "project.ipynb").write_text(
        json.dumps(PROJECT_NB, indent=1), encoding="utf-8")
    (DIR / "project" / "solution" / "solution.ipynb").write_text(
        json.dumps(SOLUTION_NB, indent=1), encoding="utf-8")

    print(f"[gen_day{DAY}] files written — running gate …")

    result = subprocess.run(
        ["conda", "run", "-n", "ai-course", "--no-capture-output",
         "python", "-c", GATE_PY],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print("GATE FAILED (inline)\n", result.stdout, result.stderr)
        sys.exit(1)
    print(result.stdout.strip())

    nb_paths = (
        [DIR / "exercises" / f"exercise_{i:02d}.ipynb" for i in range(1, 6)]
        + [DIR / "project" / "solution" / "solution.ipynb"]
    )
    nbclient_script = "import nbformat, nbclient\n"
    for p in nb_paths:
        nbclient_script += (
            f"nb = nbformat.read(r'{p}', as_version=4)\n"
            f"nbclient.NotebookClient(nb, timeout=60, kernel_name='python3',"
            f" resources={{'metadata': {{'path': r'{p.parent}'}}}}).execute()\n"
            f"errs = [c for c in nb.cells if any(o.get('output_type')=='error'"
            f" for o in c.get('outputs',[]))]\n"
            f"assert not errs, 'Notebook {p.name} had errors'\n"
            f"print('  OK {p.name}')\n"
        )
    result2 = subprocess.run(
        ["conda", "run", "-n", "ai-course", "--no-capture-output",
         "python", "-c", nbclient_script],
        capture_output=True, text=True,
    )
    if result2.returncode != 0:
        print("GATE FAILED (nbclient)\n", result2.stdout, result2.stderr)
        sys.exit(1)
    print(result2.stdout.strip())

    src = DELIVERABLE + "\n".join(
        json.dumps(nb) for nb in EXERCISES + [PROJECT_NB, SOLUTION_NB]
    )
    for pattern in ["openai", "anthropic", r"\beval\b"]:
        if re.search(pattern, src):
            print(f"GATE FAILED: banned pattern '{pattern}' found")
            sys.exit(1)
    print("Gate: adversarial grep clean")
    print(f"\n[gen_day{DAY}] gate-green ✓")


if __name__ == "__main__":
    main()
