#!/usr/bin/env python3
"""Day 090 generator — Analyzing Markets (Technical Indicators)."""
import json, pathlib

ROOT  = pathlib.Path(__file__).parent.parent
DAY   = "090"
SLUG  = "indicators"
TITLE = "Analyzing Markets"
DIR   = ROOT / "07_finance" / f"day_{DAY}"

# ══════════════════════════════════════════════════════════════════════════════
# Deliverable source fragments
# ══════════════════════════════════════════════════════════════════════════════

_FRAG_DOC = '''\
"""
Day 090 — Analyzing Markets
============================
Technical indicator calculator for OHLCV price data.

All functions accept a pd.Series (typically df["Close"]) and return a new
Series or DataFrame.  None mutate the input.  First window-1 values of any
rolling indicator are NaN — this is correct behaviour, not a bug.

Public API
----------
    sma(series, window=20)                          -> pd.Series
    ema(series, window=20)                          -> pd.Series
    rsi(series, window=14)                          -> pd.Series   (0–100)
    macd(series, fast=12, slow=26, signal=9)        -> pd.DataFrame
        columns: macd, signal, histogram
    bollinger_bands(series, window=20, num_std=2.0) -> pd.DataFrame
        columns: upper, middle, lower
    add_indicators(df, sma_w, ema_w, rsi_w,
                   macd_fast, macd_slow, macd_sig,
                   bb_w, bb_std)                    -> pd.DataFrame
"""
'''

_FRAG_IMPORTS = '''\
import pandas as pd
'''

_FRAG_SMA = '''\

# ── SMA ───────────────────────────────────────────────────────────────────────

def sma(series, window=20):
    """Simple Moving Average.

    Args:
        series : pd.Series of prices (typically Close)
        window : look-back period (default 20)

    Returns:
        pd.Series — first window-1 values are NaN
    """
    return series.rolling(window=window).mean()
'''

_FRAG_EMA = '''\

# ── EMA ───────────────────────────────────────────────────────────────────────

def ema(series, window=20):
    """Exponential Moving Average.

    Uses pandas ewm with span=window and adjust=False.
    Alpha = 2 / (window + 1).  No initial NaN — starts from the first value.

    Args:
        series : pd.Series of prices
        window : span parameter (default 20)

    Returns:
        pd.Series
    """
    return series.ewm(span=window, adjust=False).mean()
'''

_FRAG_RSI = '''\

# ── RSI ───────────────────────────────────────────────────────────────────────

def rsi(series, window=14):
    """Relative Strength Index (0–100).

    Uses the simple rolling-mean approximation:
        RS = avg_gain / avg_loss  (over `window` periods)
        RSI = 100 - 100 / (1 + RS)

    First `window` values are NaN.

    Args:
        series : pd.Series of prices
        window : look-back period (default 14)

    Returns:
        pd.Series with values in [0, 100] where not NaN
    """
    delta = series.diff()
    gain  = delta.clip(lower=0).rolling(window=window).mean()
    loss  = (-delta.clip(upper=0)).rolling(window=window).mean()
    rs    = gain / loss
    return 100 - (100 / (1 + rs))
'''

_FRAG_MACD = '''\

# ── MACD ──────────────────────────────────────────────────────────────────────

def macd(series, fast=12, slow=26, signal=9):
    """Moving Average Convergence/Divergence.

    Args:
        series : pd.Series of prices
        fast   : fast EMA window (default 12)
        slow   : slow EMA window (default 26)
        signal : signal EMA window applied to the MACD line (default 9)

    Returns:
        pd.DataFrame with columns:
            macd      — fast_ema - slow_ema
            signal    — EMA of the macd line
            histogram — macd - signal
    """
    fast_ema   = ema(series, fast)
    slow_ema   = ema(series, slow)
    macd_line  = fast_ema - slow_ema
    signal_line = ema(macd_line, signal)
    histogram  = macd_line - signal_line
    return pd.DataFrame({
        "macd":      macd_line,
        "signal":    signal_line,
        "histogram": histogram,
    })
'''

_FRAG_BB = '''\

# ── Bollinger Bands ───────────────────────────────────────────────────────────

def bollinger_bands(series, window=20, num_std=2.0):
    """Bollinger Bands.

    Args:
        series  : pd.Series of prices
        window  : look-back period for SMA and rolling std (default 20)
        num_std : number of standard deviations for the bands (default 2.0)

    Returns:
        pd.DataFrame with columns:
            upper  — middle + num_std * rolling_std
            middle — simple moving average
            lower  — middle - num_std * rolling_std
        First window-1 rows are NaN.
    """
    middle = sma(series, window)
    std    = series.rolling(window=window).std()
    upper  = middle + num_std * std
    lower  = middle - num_std * std
    return pd.DataFrame({
        "upper":  upper,
        "middle": middle,
        "lower":  lower,
    })
'''

_FRAG_ADD = '''\

# ── add_indicators ────────────────────────────────────────────────────────────

def add_indicators(df, sma_w=20, ema_w=20, rsi_w=14,
                   macd_fast=12, macd_slow=26, macd_sig=9,
                   bb_w=20, bb_std=2.0):
    """Add all standard technical indicators to a copy of df.

    Adds 9 new columns (using df["Close"] as the price series):
        sma_{sma_w}   — Simple Moving Average
        ema_{ema_w}   — Exponential Moving Average
        rsi_{rsi_w}   — Relative Strength Index
        macd          — MACD line
        macd_signal   — MACD signal line
        macd_hist     — MACD histogram
        bb_upper      — Bollinger upper band
        bb_middle     — Bollinger middle band (= SMA)
        bb_lower      — Bollinger lower band

    Never mutates the input DataFrame.
    """
    df    = df.copy()
    close = df["Close"]

    df[f"sma_{sma_w}"] = sma(close, sma_w)
    df[f"ema_{ema_w}"] = ema(close, ema_w)
    df[f"rsi_{rsi_w}"] = rsi(close, rsi_w)

    m = macd(close, macd_fast, macd_slow, macd_sig)
    df["macd"]        = m["macd"]
    df["macd_signal"] = m["signal"]
    df["macd_hist"]   = m["histogram"]

    bb = bollinger_bands(close, bb_w, bb_std)
    df["bb_upper"]  = bb["upper"]
    df["bb_middle"] = bb["middle"]
    df["bb_lower"]  = bb["lower"]

    return df
'''

DELIVERABLE = (
    _FRAG_DOC + _FRAG_IMPORTS
    + _FRAG_SMA + _FRAG_EMA + _FRAG_RSI
    + _FRAG_MACD + _FRAG_BB + _FRAG_ADD
)

# ══════════════════════════════════════════════════════════════════════════════
# Notebook helpers
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

# ── shared preludes ───────────────────────────────────────────────────────────

_P_BASE = """\
import pandas as pd, math

def _synthetic(n=50):
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
"""

_P_SMA = """\
def sma(series, window=20):
    return series.rolling(window=window).mean()
"""

_P_EMA = """\
def ema(series, window=20):
    return series.ewm(span=window, adjust=False).mean()
"""

_P_RSI = """\
def rsi(series, window=14):
    delta = series.diff()
    gain  = delta.clip(lower=0).rolling(window=window).mean()
    loss  = (-delta.clip(upper=0)).rolling(window=window).mean()
    rs    = gain / loss
    return 100 - (100 / (1 + rs))
"""

_P_MACD = """\
def macd(series, fast=12, slow=26, signal=9):
    fast_ema    = ema(series, fast)
    slow_ema    = ema(series, slow)
    macd_line   = fast_ema - slow_ema
    signal_line = ema(macd_line, signal)
    return pd.DataFrame({"macd": macd_line, "signal": signal_line,
                          "histogram": macd_line - signal_line})
"""

_P_BB = """\
def bollinger_bands(series, window=20, num_std=2.0):
    middle = sma(series, window)
    std    = series.rolling(window=window).std()
    return pd.DataFrame({"upper": middle + num_std * std,
                          "middle": middle,
                          "lower": middle - num_std * std})
"""

# ══════════════════════════════════════════════════════════════════════════════
# Exercise notebooks
# ══════════════════════════════════════════════════════════════════════════════

_EX1 = _nb([
    _md("# Exercise 1 — SMA and EMA\n\n"
        "Moving averages smooth out price noise and reveal trends. The Simple "
        "Moving Average (SMA) gives equal weight to all prices in the window. "
        "The Exponential Moving Average (EMA) gives more weight to recent prices, "
        "making it more responsive to new information."),
    _code(_P_BASE + """\

# ── Exercise: implement sma and ema ──────────────────────────────────────────

def sma(series, window=20):
    \"\"\"Simple Moving Average.

    Args:
        series : pd.Series of prices
        window : look-back period (default 20)

    Returns:
        pd.Series — first window-1 values are NaN
    \"\"\"
    # TODO: return series.rolling(window=window).mean()
    return pd.Series([float("nan")] * len(series), index=series.index)


def ema(series, window=20):
    \"\"\"Exponential Moving Average.

    Args:
        series : pd.Series of prices
        window : span parameter (default 20); alpha = 2 / (window + 1)

    Returns:
        pd.Series — no NaN (starts from the first value)
    \"\"\"
    # TODO: return series.ewm(span=window, adjust=False).mean()
    return pd.Series([float("nan")] * len(series), index=series.index)
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — sma: first window-1 values are NaN; window-th value is not NaN
try:
    close = _synthetic()["Close"]
    s = sma(close, 10)
    assert isinstance(s, pd.Series) and len(s) == len(close)
    assert s.iloc[:9].isna().all(), "first 9 values should be NaN"
    assert not pd.isna(s.iloc[9]), "index 9 should be the first non-NaN"
    checks += 1; print("✅ 1 sma: first window-1 NaN, then non-NaN")
except Exception as e:
    print("❌ 1:", e)

# 2 — sma: value at window-1 equals mean of first window elements
try:
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    result = sma(s, 3)
    assert abs(result.iloc[2] - 2.0) < 1e-9, f"expected 2.0, got {result.iloc[2]}"
    assert abs(result.iloc[3] - 3.0) < 1e-9, f"expected 3.0, got {result.iloc[3]}"
    assert abs(result.iloc[4] - 4.0) < 1e-9, f"expected 4.0, got {result.iloc[4]}"
    checks += 1; print("✅ 2 sma values are exact rolling means")
except Exception as e:
    print("❌ 2:", e)

# 3 — sma: constant series returns constant (where not NaN)
try:
    const = pd.Series([5.0] * 30)
    s = sma(const, 10)
    non_nan = s.dropna()
    assert len(non_nan) == 21 and (non_nan == 5.0).all()
    checks += 1; print("✅ 3 sma of constant series returns constant")
except Exception as e:
    print("❌ 3:", e)

# 4 — ema: no NaN values; same length as input
try:
    close = _synthetic()["Close"]
    e = ema(close, 20)
    assert isinstance(e, pd.Series) and len(e) == len(close)
    assert not e.isna().any(), "ema should have no NaN values"
    checks += 1; print("✅ 4 ema returns same length Series with no NaN")
except Exception as e:
    print("❌ 4:", e)

# 5 — ema: converges toward a new level after a step change
try:
    # Series: 10 zeros, then 10 tens — ema should end up close to 10
    s = pd.Series([0.0] * 10 + [10.0] * 20)
    e = ema(s, 3)
    assert e.iloc[-1] > 9.0, f"expected ema to converge to ~10, got {e.iloc[-1]:.4f}"
    checks += 1; print("✅ 5 ema converges to new price level after a step change")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX2 = _nb([
    _md("# Exercise 2 — RSI\n\n"
        "The Relative Strength Index (RSI) measures momentum: how fast prices "
        "are moving and in which direction. Values above 70 signal overbought "
        "conditions; below 30 signal oversold. RSI = 100 − 100 / (1 + RS), "
        "where RS = average gain / average loss over the look-back window."),
    _code(_P_BASE + _P_SMA + _P_EMA + """\

# ── Exercise: implement rsi ───────────────────────────────────────────────────

def rsi(series, window=14):
    \"\"\"Relative Strength Index (0–100).

    Steps:
      1. delta = series.diff()                 — daily change
      2. gain  = delta.clip(lower=0)           — keep only positive changes
      3. loss  = -delta.clip(upper=0)          — keep only negative changes (positive)
      4. avg_gain = gain.rolling(window).mean()
      5. avg_loss = loss.rolling(window).mean()
      6. rs     = avg_gain / avg_loss
      7. return 100 - (100 / (1 + rs))

    First `window` values are NaN.
    \"\"\"
    # TODO: implement the 7 steps above
    return pd.Series([float("nan")] * len(series), index=series.index)
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — rsi returns same-length Series
try:
    close = _synthetic()["Close"]
    r = rsi(close, 14)
    assert isinstance(r, pd.Series) and len(r) == len(close)
    checks += 1; print("✅ 1 rsi returns same-length Series")
except Exception as e:
    print("❌ 1:", e)

# 2 — first `window` values are NaN
try:
    close = _synthetic()["Close"]
    r = rsi(close, 14)
    assert r.iloc[:14].isna().all(), "first 14 values should be NaN"
    assert not pd.isna(r.iloc[14]), f"index 14 should be first non-NaN, got {r.iloc[14]}"
    checks += 1; print("✅ 2 first window values are NaN, then non-NaN")
except Exception as e:
    print("❌ 2:", e)

# 3 — all non-NaN RSI values are in [0, 100]
try:
    close = _synthetic()["Close"]
    r = rsi(close, 14)
    non_nan = r.dropna()
    assert (non_nan >= 0).all() and (non_nan <= 100).all(), \\
        f"RSI out of range: min={non_nan.min():.2f}, max={non_nan.max():.2f}"
    checks += 1; print("✅ 3 all non-NaN RSI values are in [0, 100]")
except Exception as e:
    print("❌ 3:", e)

# 4 — all-rising prices -> RSI approaches 100
try:
    import warnings
    rising = pd.Series([float(i) for i in range(30)])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = rsi(rising, 10)
    non_nan = r.dropna()
    assert (non_nan > 90.0).all(), f"expected RSI>90 for all-rising, got {non_nan.tolist()}"
    checks += 1; print("✅ 4 all-rising prices produce RSI > 90")
except Exception as e:
    print("❌ 4:", e)

# 5 — all-falling prices -> RSI approaches 0
try:
    import warnings
    falling = pd.Series([float(30 - i) for i in range(30)])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = rsi(falling, 10)
    non_nan = r.dropna()
    assert (non_nan < 10.0).all(), f"expected RSI<10 for all-falling, got {non_nan.tolist()}"
    checks += 1; print("✅ 5 all-falling prices produce RSI < 10")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX3 = _nb([
    _md("# Exercise 3 — MACD\n\n"
        "MACD (Moving Average Convergence/Divergence) shows the relationship "
        "between two EMAs. The MACD line crosses above the signal line as a "
        "bullish signal; crossing below is bearish. The histogram shows the "
        "gap between the two lines — its direction often signals momentum shifts "
        "before the crossover happens."),
    _code(_P_BASE + _P_SMA + _P_EMA + _P_RSI + """\

# ── Exercise: implement macd ──────────────────────────────────────────────────

def macd(series, fast=12, slow=26, signal=9):
    \"\"\"MACD: Moving Average Convergence/Divergence.

    Args:
        series : pd.Series of prices
        fast   : fast EMA window (default 12)
        slow   : slow EMA window (default 26)
        signal : signal-line EMA applied to the MACD line (default 9)

    Returns:
        pd.DataFrame with columns:
            macd      — ema(series, fast) - ema(series, slow)
            signal    — ema(macd_line, signal)
            histogram — macd_line - signal_line
    \"\"\"
    # TODO:
    # 1. fast_ema  = ema(series, fast)
    # 2. slow_ema  = ema(series, slow)
    # 3. macd_line = fast_ema - slow_ema
    # 4. signal_line = ema(macd_line, signal)
    # 5. histogram = macd_line - signal_line
    # 6. return pd.DataFrame({"macd": macd_line, "signal": signal_line, "histogram": histogram})
    n = len(series)
    return pd.DataFrame({"macd":      [0.0] * n,
                          "signal":    [0.0] * n,
                          "histogram": [0.0] * n},
                         index=series.index)
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — macd returns DataFrame with 3 expected columns
try:
    close = _synthetic()["Close"]
    m = macd(close)
    assert isinstance(m, pd.DataFrame)
    assert "macd" in m.columns and "signal" in m.columns and "histogram" in m.columns
    assert len(m) == len(close)
    checks += 1; print("✅ 1 macd returns DataFrame with macd/signal/histogram columns")
except Exception as e:
    print("❌ 1:", e)

# 2 — histogram = macd - signal for every row
try:
    close = _synthetic()["Close"]
    m = macd(close)
    diff = (m["macd"] - m["signal"] - m["histogram"]).abs().max()
    assert diff < 1e-9, f"histogram != macd - signal, max diff={diff}"
    checks += 1; print("✅ 2 histogram == macd - signal for every row")
except Exception as e:
    print("❌ 2:", e)

# 3 — no NaN values (EMA starts from first observation)
try:
    close = _synthetic()["Close"]
    m = macd(close)
    assert not m.isna().any().any(), f"unexpected NaN in MACD DataFrame"
    checks += 1; print("✅ 3 MACD has no NaN values")
except Exception as e:
    print("❌ 3:", e)

# 4 — macd of a constant series is zero everywhere
try:
    const = pd.Series([50.0] * 50)
    m = macd(const)
    assert m["macd"].abs().max() < 1e-9, f"MACD of constant should be 0, got {m['macd'].abs().max()}"
    checks += 1; print("✅ 4 macd of constant price series is zero")
except Exception as e:
    print("❌ 4:", e)

# 5 — macd line is positive when fast EMA > slow EMA
try:
    # Linearly rising price: fast EMA tracks faster -> fast > slow -> MACD > 0
    rising = pd.Series([float(i) for i in range(1, 51)])
    m = macd(rising, fast=5, slow=20, signal=3)
    # After warmup (say, last 20 rows), MACD should be positive
    last20 = m["macd"].iloc[-20:]
    assert (last20 > 0).all(), f"expected MACD > 0 for rising prices: {last20.tolist()}"
    checks += 1; print("✅ 5 MACD is positive when price has been rising steadily")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX4 = _nb([
    _md("# Exercise 4 — Bollinger Bands\n\n"
        "Bollinger Bands place a volatility envelope around price. The middle "
        "band is the SMA; the upper and lower bands are `num_std` standard "
        "deviations above and below. Prices touching the upper band may be "
        "overbought; touching the lower band may be oversold. Band width "
        "narrows in quiet markets and widens in volatile ones."),
    _code(_P_BASE + _P_SMA + _P_EMA + _P_RSI + _P_MACD + """\

# ── Exercise: implement bollinger_bands ──────────────────────────────────────

def bollinger_bands(series, window=20, num_std=2.0):
    \"\"\"Bollinger Bands.

    Args:
        series  : pd.Series of prices
        window  : SMA and rolling-std look-back (default 20)
        num_std : number of standard deviations for the bands (default 2.0)

    Returns:
        pd.DataFrame with columns:
            upper  — SMA + num_std * rolling_std
            middle — SMA
            lower  — SMA - num_std * rolling_std
        First window-1 rows are NaN.
    \"\"\"
    # TODO:
    # 1. middle = sma(series, window)
    # 2. std    = series.rolling(window=window).std()
    # 3. upper  = middle + num_std * std
    # 4. lower  = middle - num_std * std
    # 5. return pd.DataFrame({"upper": upper, "middle": middle, "lower": lower})
    n = len(series)
    return pd.DataFrame({"upper":  [float("nan")] * n,
                          "middle": [float("nan")] * n,
                          "lower":  [float("nan")] * n},
                         index=series.index)
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — bollinger_bands returns DataFrame with 3 columns
try:
    close = _synthetic()["Close"]
    bb = bollinger_bands(close, 20)
    assert isinstance(bb, pd.DataFrame)
    assert "upper" in bb.columns and "middle" in bb.columns and "lower" in bb.columns
    assert len(bb) == len(close)
    checks += 1; print("✅ 1 bollinger_bands returns DataFrame with upper/middle/lower")
except Exception as e:
    print("❌ 1:", e)

# 2 — first window-1 rows are NaN; row window-1 is not NaN
try:
    close = _synthetic()["Close"]
    bb = bollinger_bands(close, 20)
    assert bb["middle"].iloc[:19].isna().all(), "first 19 should be NaN"
    assert not pd.isna(bb["middle"].iloc[19]), "index 19 should be first non-NaN"
    checks += 1; print("✅ 2 first window-1 rows are NaN")
except Exception as e:
    print("❌ 2:", e)

# 3 — upper > middle > lower for all non-NaN rows
try:
    close = _synthetic()["Close"]
    bb = bollinger_bands(close, 20)
    non_nan = bb.dropna()
    assert (non_nan["upper"] > non_nan["middle"]).all(), "upper <= middle in some rows"
    assert (non_nan["middle"] > non_nan["lower"]).all(), "middle <= lower in some rows"
    checks += 1; print("✅ 3 upper > middle > lower for all non-NaN rows")
except Exception as e:
    print("❌ 3:", e)

# 4 — middle equals SMA of close with window
try:
    close = _synthetic()["Close"]
    bb = bollinger_bands(close, 10)
    s   = sma(close, 10)
    diff = (bb["middle"] - s).dropna().abs().max()
    assert diff < 1e-9, f"middle != sma: max diff={diff}"
    checks += 1; print("✅ 4 middle band equals SMA with same window")
except Exception as e:
    print("❌ 4:", e)

# 5 — wider bands for more volatile price series
try:
    volatile = pd.Series([100.0 + 10.0 * ((-1)**i) for i in range(50)])
    stable   = pd.Series([100.0 + 0.1 * ((-1)**i)  for i in range(50)])
    bb_v = bollinger_bands(volatile, 10)
    bb_s = bollinger_bands(stable,   10)
    width_v = (bb_v["upper"] - bb_v["lower"]).dropna().mean()
    width_s = (bb_s["upper"] - bb_s["lower"]).dropna().mean()
    assert width_v > width_s, f"volatile width ({width_v:.2f}) should > stable ({width_s:.2f})"
    checks += 1; print("✅ 5 bands are wider for more volatile price series")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX5 = _nb([
    _md("# Exercise 5 — add_indicators\n\n"
        "`add_indicators` is the integration function: it takes an OHLCV "
        "DataFrame and returns a copy enriched with all 9 indicator columns. "
        "It is the bridge between market_data.py (Day 89) and the backtester "
        "(Day 91) — every downstream day in Section 7 starts with `df = "
        "add_indicators(store.load(ticker))`."),
    _code(_P_BASE + _P_SMA + _P_EMA + _P_RSI + _P_MACD + _P_BB + """\

# ── Exercise: implement add_indicators ───────────────────────────────────────

def add_indicators(df, sma_w=20, ema_w=20, rsi_w=14,
                   macd_fast=12, macd_slow=26, macd_sig=9,
                   bb_w=20, bb_std=2.0):
    \"\"\"Add all standard indicators to a copy of df.

    Uses df["Close"] as the price series.

    Adds 9 new columns:
        sma_{sma_w}, ema_{ema_w}, rsi_{rsi_w}
        macd, macd_signal, macd_hist
        bb_upper, bb_middle, bb_lower

    Never mutates the input DataFrame.
    \"\"\"
    # TODO:
    # 1. df = df.copy(); close = df["Close"]
    # 2. df[f"sma_{sma_w}"] = sma(close, sma_w)
    # 3. df[f"ema_{ema_w}"] = ema(close, ema_w)
    # 4. df[f"rsi_{rsi_w}"] = rsi(close, rsi_w)
    # 5. m = macd(close, macd_fast, macd_slow, macd_sig)
    #    df["macd"]        = m["macd"]
    #    df["macd_signal"] = m["signal"]
    #    df["macd_hist"]   = m["histogram"]
    # 6. bb = bollinger_bands(close, bb_w, bb_std)
    #    df["bb_upper"]  = bb["upper"]
    #    df["bb_middle"] = bb["middle"]
    #    df["bb_lower"]  = bb["lower"]
    # 7. return df
    return df.copy()
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — add_indicators returns DataFrame with 9 new columns
try:
    df = _synthetic(n=50)
    enriched = add_indicators(df)
    expected_new = {"sma_20", "ema_20", "rsi_14", "macd", "macd_signal",
                    "macd_hist", "bb_upper", "bb_middle", "bb_lower"}
    actual_new = set(enriched.columns) - set(df.columns)
    assert expected_new == actual_new, f"unexpected cols: {actual_new ^ expected_new}"
    checks += 1; print("✅ 1 add_indicators adds exactly the 9 expected columns")
except Exception as e:
    print("❌ 1:", e)

# 2 — does not mutate the input DataFrame
try:
    df = _synthetic(n=50)
    original_cols = list(df.columns)
    _ = add_indicators(df)
    assert list(df.columns) == original_cols, "input DataFrame was mutated!"
    checks += 1; print("✅ 2 add_indicators does not mutate the input DataFrame")
except Exception as e:
    print("❌ 2:", e)

# 3 — same number of rows, 9 more columns
try:
    df = _synthetic(n=50)
    enriched = add_indicators(df)
    assert len(enriched) == len(df), "row count changed"
    assert len(enriched.columns) == len(df.columns) + 9, \\
        f"expected {len(df.columns)+9} cols, got {len(enriched.columns)}"
    checks += 1; print("✅ 3 same rows, exactly 9 more columns")
except Exception as e:
    print("❌ 3:", e)

# 4 — row at index 25 has no NaN in any indicator column
try:
    df = _synthetic(n=50)
    enriched = add_indicators(df)
    indicator_cols = ["sma_20", "ema_20", "rsi_14", "macd", "macd_signal",
                      "macd_hist", "bb_upper", "bb_middle", "bb_lower"]
    row = enriched.iloc[25]
    for col in indicator_cols:
        assert not pd.isna(row[col]), f"{col} is NaN at row 25"
    checks += 1; print("✅ 4 all indicator columns are non-NaN at row 25")
except Exception as e:
    print("❌ 4:", e)

# 5 — bb_upper > bb_middle > bb_lower for all non-NaN rows
try:
    df = _synthetic(n=50)
    enriched = add_indicators(df).dropna(subset=["bb_upper", "bb_lower"])
    assert (enriched["bb_upper"] > enriched["bb_middle"]).all()
    assert (enriched["bb_middle"] > enriched["bb_lower"]).all()
    checks += 1; print("✅ 5 bb_upper > bb_middle > bb_lower for all non-NaN rows")
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
day: "090"
lesson: 1
title: "What Are Technical Indicators?"
slides:
  - type: title
    heading: "Analyzing Markets"
    subheading: "Technical indicators — SMA, EMA, RSI, MACD, Bollinger Bands"
    narration: >
      Day 90. You have market data — a clean OHLCV DataFrame from yesterday's
      pipeline. Today you turn raw prices into actionable signals by computing
      technical indicators. SMA, EMA, RSI, MACD, and Bollinger Bands are the
      five most widely used indicators in systematic trading. By the end of
      today you will be able to compute all five from scratch and combine them
      into an enriched DataFrame that feeds directly into the backtester on
      Day 91.

  - type: concept
    label: "What indicators are"
    heading: "Indicators: Derived Statistics from Price"
    body: >
      Every indicator is a mathematical transform of OHLCV data.
    bullets:
      - "Trend indicators: SMA, EMA — where is price going?"
      - "Momentum indicators: RSI, MACD — how fast is it moving?"
      - "Volatility indicators: Bollinger Bands — how wide is the range?"
      - "All three categories are complementary — use at least one of each"
      - "Indicators lag price — they describe the past, not the future"
    narration: >
      The core insight about technical indicators is that they are backward-
      looking. A 20-day SMA tells you the average price over the last 20 days.
      It says nothing about the next day. Traders use them to identify patterns
      that have been statistically associated with certain price movements —
      not because the indicator predicts the future, but because it signals
      when a particular market condition is present. Understanding this
      limitation is as important as knowing the formula.

  - type: concept
    label: "Look-ahead bias"
    heading: "The Golden Rule: No Look-Ahead Bias"
    body: >
      An indicator computed on day T must use only data up to day T.
    bullets:
      - "Signal at row i uses only rows 0 through i — never row i+1"
      - "Rolling windows enforce this automatically: rolling(20).mean()"
      - "Look-ahead bias inflates backtest returns — they look great but lie"
      - "The most common form: using tomorrow's open to determine today's position"
      - "In Day 91, signals.shift(1) before computing returns — the fix"
    narration: >
      Look-ahead bias is the most dangerous mistake in quantitative finance.
      If your backtest peeks at future prices to generate a signal, the strategy
      will look profitable in simulation but lose money in live trading. Pandas
      rolling operations are your friend: rolling(20).mean() at position i uses
      exactly positions i-19 through i — no peeking ahead. When you shift
      signals by 1 in the backtester, you say: I saw this signal at the end of
      today, so I trade at the start of tomorrow.

  - type: concept
    label: "NaN at the start"
    heading: "First window-1 Values Are NaN — by Design"
    body: >
      Rolling indicators need a full window before they can produce a result.
    bullets:
      - "SMA(20): positions 0–18 are NaN; position 19 is the first value"
      - "RSI(14): positions 0–13 are NaN; position 14 is the first value"
      - "EMA: no NaN — starts from the very first observation"
      - "MACD: no NaN — built from EMA, which has no NaN"
      - "Handle NaN in downstream code: fillna(0) for positions, dropna() for fit"
    narration: >
      When you first run SMA with window 20 on 100 rows of data, you get 19
      NaN values at the start. This is correct — there is not enough data to
      compute a 20-day average for days 1 through 19. Do not fill these with
      zeros or the previous value unless you have a specific reason. In the
      backtester, NaN signals get filled with zero positions — meaning: hold
      nothing during the warmup period. This is the right behaviour.

  - type: exercise
    heading: "Exercise 1 — Implement SMA and EMA"
    prompt: >
      Implement sma(series, window=20) using series.rolling(window).mean().
      Implement ema(series, window=20) using series.ewm(span=window,
      adjust=False).mean(). Neither function mutates the input.
    hint: >
      For SMA: one line. For EMA: one line. The checks test that SMA has
      window-1 leading NaN values and that EMA has none.
    narration: >
      One line each. The value of this exercise is not the implementation —
      it is understanding why the outputs look the way they do. After you
      pass the checks, compare SMA and EMA on the synthetic data: notice how
      EMA tracks price changes faster because recent values get more weight.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "Technical indicators are backward-looking derived statistics"
      - "Three categories: trend (SMA/EMA), momentum (RSI/MACD), volatility (BB)"
      - "Look-ahead bias: signal at t can only use data up to t"
      - "First window-1 values are NaN for rolling indicators"
      - "Next: RSI — measuring momentum"
    narration: >
      You now understand the landscape. The next four lessons drill into
      each indicator: the formula, the intuition, and the implementation.
      SMA and EMA are done. Next: RSI.
""",

    """\
day: "090"
lesson: 2
title: "Moving Averages — SMA and EMA"
slides:
  - type: title
    heading: "Moving Averages"
    subheading: "SMA and EMA — the foundation of trend analysis"
    narration: >
      Moving averages are the most-used tools in technical analysis. They
      smooth price data to reveal the underlying trend without the noise of
      daily fluctuations. The Simple Moving Average treats all days equally.
      The Exponential Moving Average weights recent days more heavily. Both are
      one line of pandas. Understanding when to use each is the skill.

  - type: concept
    label: "SMA"
    heading: "Simple Moving Average"
    body: >
      SMA(n) at time t = average of the last n closing prices.
    bullets:
      - "SMA(20) at day 20 = mean(Close[1..20])"
      - "SMA(20) at day 21 = mean(Close[2..21]) — drops oldest, adds newest"
      - "pandas: series.rolling(window=20).mean()"
      - "Popular windows: 20 (short), 50 (medium), 200 (long-term trend)"
      - "Price above SMA: uptrend. Price below SMA: downtrend."
    narration: >
      The 200-day SMA is watched by professional traders worldwide. When a
      stock's price crosses above its 200-day SMA, it is called the golden
      cross — a bullish signal. When it crosses below, it is called the death
      cross — bearish. These names are dramatic but the concept is simple: is
      the current price above or below its long-run average? That single
      question drives a lot of systematic trading decisions.

  - type: concept
    label: "EMA"
    heading: "Exponential Moving Average"
    body: >
      EMA weights recent prices more heavily using a decay factor.
    bullets:
      - "alpha = 2 / (window + 1)  — the smoothing factor"
      - "EMA[t] = alpha * Price[t] + (1-alpha) * EMA[t-1]"
      - "pandas: series.ewm(span=window, adjust=False).mean()"
      - "EMA(12) reacts faster than SMA(12) — same window, different weights"
      - "No initial NaN — EMA starts from the very first price"
    narration: >
      The exponential decay means that yesterday's price matters more than the
      price from two weeks ago, which matters more than the price from a month
      ago. With a window of 12 and alpha of 2/13, a price move today has
      twice the impact on EMA(12) that the same-sized move from 13 days ago
      has. This makes EMA more responsive but also more susceptible to noise.
      The choice between SMA and EMA depends on whether you want a more stable
      or a more responsive signal.

  - type: code
    label: "SMA vs EMA"
    heading: "Comparing SMA and EMA on Synthetic Data"
    body: >
      See the difference in responsiveness.
    code: |
      close = df["Close"]

      s = sma(close, 20)   # rolling mean, 19 NaN at start
      e = ema(close, 20)   # exponential, no NaN

      # On a price series with a sudden jump:
      # EMA reacts immediately — it updates on every new price
      # SMA catches up after window/2 periods

      # Crossover signal: price above SMA(20) = buy candidate
      signal = (close > s).astype(int)   # 1 above, 0 below, NaN where s is NaN
    narration: >
      A simple moving average crossover — price crossing above or below the
      SMA — is one of the oldest trading signals. It is not particularly
      profitable on its own, but it is a useful building block. In Day 92,
      you will combine multiple signals into a more robust strategy. For now,
      the important pattern is: compute the indicator, then compare the price
      to the indicator. The comparison generates a boolean or integer signal
      that the backtester can act on.

  - type: exercise
    heading: "Exercise 1 — SMA and EMA (continued)"
    prompt: >
      Your SMA and EMA implementations from the previous exercise. If you have
      not done Exercise 1 yet, complete it now before running this lesson's
      checks.
    hint: >
      Check 5 tests EMA convergence on a step function: 10 zeros followed by
      20 tens. With span=3, the EMA should be above 9.0 at the final position.
    narration: >
      Two implementations, two lines of code. The skill is in reading the
      output. After you run the checks, try changing the window: sma(close, 5)
      versus sma(close, 50). The shorter the window, the noisier but faster
      the indicator. The longer the window, the smoother but slower.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "SMA: rolling(window).mean() — equal weighting, window-1 NaN"
      - "EMA: ewm(span=window, adjust=False).mean() — exponential decay, no NaN"
      - "alpha = 2/(window+1) — the decay rate"
      - "EMA responds faster; SMA is more stable"
      - "Next: RSI — measuring momentum, not trend"
    narration: >
      Moving averages tell you the direction of the trend. RSI tells you the
      strength of the momentum. They answer different questions and complement
      each other. Next lesson: RSI.
""",

    """\
day: "090"
lesson: 3
title: "Relative Strength Index — RSI"
slides:
  - type: title
    heading: "RSI — Relative Strength Index"
    subheading: "Measuring momentum: how fast is price moving?"
    narration: >
      RSI is a momentum oscillator — it oscillates between 0 and 100 rather
      than trending with the price. Developed by J. Welles Wilder in 1978, it
      is still one of the most widely used indicators in systematic trading.
      RSI answers: over the last 14 days, have gains dominated losses, or have
      losses dominated gains?

  - type: concept
    label: "RSI formula"
    heading: "The RSI Formula, Step by Step"
    body: >
      RSI = 100 - 100 / (1 + RS)  where RS = avg_gain / avg_loss
    bullets:
      - "delta = series.diff()  — daily change, NaN at position 0"
      - "gain  = delta.clip(lower=0)  — keep only positive changes"
      - "loss  = -delta.clip(upper=0)  — keep only negative changes"
      - "avg_gain = gain.rolling(14).mean()"
      - "avg_loss = loss.rolling(14).mean()"
      - "RS = avg_gain / avg_loss"
    narration: >
      The clip function is the key step. clip(lower=0) keeps any positive
      number and replaces any negative number with zero — so gain is the daily
      gains with losses zeroed out. clip(upper=0) does the reverse. The
      negative sign converts negative losses to positive numbers before the
      rolling average. This is simpler than it sounds: you are just computing
      the average size of up days and the average size of down days over the
      last 14 periods.

  - type: concept
    label: "Interpreting RSI"
    heading: "What RSI Values Tell You"
    body: >
      RSI oscillates between 0 and 100.
    bullets:
      - "RSI > 70: overbought — price has risen fast, reversal possible"
      - "RSI < 30: oversold — price has fallen fast, bounce possible"
      - "RSI = 50: neutral — gains and losses roughly equal"
      - "RSI trending up: momentum is strengthening"
      - "RSI divergence: price makes new high but RSI doesn't — warning sign"
    narration: >
      The 70 and 30 thresholds are not magic numbers — they are conventions.
      In a strong uptrend, RSI can stay above 70 for weeks. In a bear market,
      it can stay below 30 for weeks. RSI is most useful when combined with a
      trend indicator: look for oversold RSI in an uptrend as a buy signal,
      or overbought RSI in a downtrend as a sell signal. Using RSI alone is a
      common beginner mistake.

  - type: code
    label: "RSI implementation"
    heading: "RSI in Six Lines"
    body: >
      Each line corresponds to one step of the formula.
    code: |
      def rsi(series, window=14):
          delta = series.diff()
          gain  = delta.clip(lower=0).rolling(window=window).mean()
          loss  = (-delta.clip(upper=0)).rolling(window=window).mean()
          rs    = gain / loss
          return 100 - (100 / (1 + rs))

      # For a monotonically rising series:
      # loss = 0 -> rs = inf -> RSI = 100 - 0 = 100
      # For a monotonically falling series:
      # gain = 0 -> rs = 0  -> RSI = 100 - 100 = 0
    narration: >
      When the price only rises, loss is always zero. Division by zero
      produces infinity in float arithmetic, not an error. Then 100 divided
      by one plus infinity equals zero, so RSI equals 100. Python handles this
      correctly without any special-casing, though it will emit a RuntimeWarning
      about division by zero. In practice, real prices have both up and down
      days, so this edge case rarely occurs in production.

  - type: exercise
    heading: "Exercise 2 — Implement RSI"
    prompt: >
      Implement rsi(series, window=14) following the six steps: diff, clip
      gains, clip losses, rolling mean both, compute RS, return 100-100/(1+RS).
      The first `window` values should be NaN. Non-NaN values must be in [0, 100].
    hint: >
      loss = -delta.clip(upper=0)  — note the negative sign. clip(upper=0) on
      a negative number gives that negative number; the negative sign makes
      it positive. For the all-rising test, use import warnings and
      catch_warnings to suppress the divide-by-zero RuntimeWarning.
    narration: >
      If you get values outside [0, 100], check the sign on the loss
      calculation. If you get all NaN, check that you are using
      rolling(window=window) not rolling(window). If the first non-NaN is at
      the wrong position, compare the number of NaN values against the window
      size: RSI(14) has 14 NaN values, not 13.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "RSI = 100 - 100/(1+RS) where RS = avg_gain/avg_loss"
      - "clip(lower=0) and clip(upper=0) separate gains from losses"
      - "RSI oscillates between 0 and 100"
      - "RSI > 70 = overbought; RSI < 30 = oversold"
      - "Next: MACD and Bollinger Bands"
    narration: >
      RSI is complete. You now have three indicators: SMA, EMA, and RSI.
      Next lesson: two more — MACD (which combines multiple EMAs) and
      Bollinger Bands (which add a volatility dimension). Then we put them
      all together in add_indicators.
""",

    """\
day: "090"
lesson: 4
title: "MACD and Bollinger Bands"
slides:
  - type: title
    heading: "MACD and Bollinger Bands"
    subheading: "Momentum convergence and volatility envelopes"
    narration: >
      MACD and Bollinger Bands are the two remaining indicators for today.
      MACD combines two EMAs to produce a momentum signal with a crossover
      trigger. Bollinger Bands place a dynamic volatility envelope around
      price. Together with SMA, EMA, and RSI, they give you a complete view
      of a market: trend direction, momentum strength, and current volatility.

  - type: concept
    label: "MACD"
    heading: "MACD: Three Numbers from Two EMAs"
    body: >
      MACD = fast EMA - slow EMA.  Signal = EMA of MACD.  Histogram = MACD - Signal.
    bullets:
      - "MACD line: EMA(12) - EMA(26) — gap between fast and slow averages"
      - "Signal line: EMA(9) applied to the MACD line"
      - "Histogram: MACD - Signal — shows how far apart they are"
      - "MACD crosses above signal: bullish momentum building"
      - "Histogram shrinks toward zero: crossover is approaching"
    narration: >
      MACD was developed by Gerald Appel in the 1970s and remains one of the
      most-used momentum indicators. The key insight is that when the shorter
      EMA pulls away from the longer EMA, momentum is accelerating. When they
      converge, momentum is fading. The signal line smooths the MACD line,
      making the crossovers less noisy. The histogram makes the distance
      between the two lines immediately visible without reading two charts.

  - type: code
    label: "MACD implementation"
    heading: "MACD in Five Lines"
    body: >
      Each output is computed from the previous one.
    code: |
      def macd(series, fast=12, slow=26, signal=9):
          fast_ema    = ema(series, fast)
          slow_ema    = ema(series, slow)
          macd_line   = fast_ema - slow_ema
          signal_line = ema(macd_line, signal)
          histogram   = macd_line - signal_line
          return pd.DataFrame({
              "macd":      macd_line,
              "signal":    signal_line,
              "histogram": histogram,
          })

      # Because EMA has no NaN, MACD also has no NaN
      # histogram always equals macd - signal (by construction)
    narration: >
      EMA starts from the first observation, so MACD has no NaN values. This
      is different from SMA-based indicators like Bollinger Bands. The signal
      line is just another EMA — the same function, applied to a different
      series. This is a good example of composition: you build the signal line
      by reusing the ema function rather than implementing a separate formula.

  - type: concept
    label: "Bollinger Bands"
    heading: "Bollinger Bands: Price Relative to Volatility"
    body: >
      Middle = SMA.  Upper = SMA + 2σ.  Lower = SMA - 2σ.
    bullets:
      - "Middle band: SMA(20) — the trend reference"
      - "Upper band: SMA(20) + 2 * rolling_std(20)"
      - "Lower band: SMA(20) - 2 * rolling_std(20)"
      - "About 95% of prices fall within the bands (normal distribution assumption)"
      - "Band squeeze: bands narrow before a breakout (volatility clustering)"
    narration: >
      The standard deviation measures how much price has varied over the last
      20 days. When the market is calm, the bands are narrow. When the market
      is volatile, they widen. Prices touching the upper band are not
      necessarily a sell signal — in a strong uptrend, prices can walk along
      the upper band for weeks. But when price touches the lower band after a
      period of calm, it often precedes a mean-reversion bounce. The key is
      context: bands combined with RSI give a much richer picture than either
      alone.

  - type: exercise
    heading: "Exercise 4 — Implement bollinger_bands"
    prompt: >
      Implement bollinger_bands(series, window=20, num_std=2.0) returning a
      DataFrame with columns upper, middle, lower. Middle is SMA(window).
      Upper is middle + num_std * rolling std. Lower is middle - num_std.
      First window-1 rows are NaN.
    hint: >
      std = series.rolling(window=window).std().  Note that .std() uses
      ddof=1 (sample standard deviation) by default — this is the standard
      convention for Bollinger Bands and matches most charting platforms.
    narration: >
      Three lines of pandas after computing the middle band. The upper and
      lower bands are symmetric around the middle, so the algebra is simple.
      Check 5 tests that volatile prices produce wider bands than stable
      prices — this is the core property of Bollinger Bands.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "MACD: fast_ema - slow_ema; signal = ema(macd); hist = macd - signal"
      - "MACD has no NaN — built entirely from EMA"
      - "Bollinger Bands: middle ± num_std * rolling_std"
      - "BB bands widen with volatility; squeeze precedes breakout"
      - "Next: add_indicators — combine all five into one DataFrame"
    narration: >
      Four of the five indicators are implemented. The fifth — add_indicators —
      is the integration step. It takes an OHLCV DataFrame, calls all four
      indicator functions on the Close column, and returns an enriched
      DataFrame with nine new columns. That enriched DataFrame is the input
      to the backtester on Day 91.
""",

    """\
day: "090"
lesson: 5
title: "add_indicators — The Full Indicator Table"
slides:
  - type: title
    heading: "add_indicators"
    subheading: "One function to enrich the OHLCV DataFrame"
    narration: >
      The final lesson ties everything together. add_indicators is the bridge
      between the data pipeline (market_data.py from Day 89) and everything
      that follows in Section 7. After today, every analysis, every backtest,
      every strategy signal starts with one line: enriched equals
      add_indicators of the raw OHLCV DataFrame.

  - type: concept
    label: "Nine new columns"
    heading: "What add_indicators Adds"
    body: >
      Nine new columns, all derived from df["Close"].
    bullets:
      - "sma_{w}: Simple Moving Average, window w (default 20)"
      - "ema_{w}: Exponential Moving Average, window w (default 20)"
      - "rsi_{w}: Relative Strength Index, window w (default 14)"
      - "macd: fast EMA - slow EMA (default 12/26)"
      - "macd_signal: EMA of the MACD line (default 9)"
      - "macd_hist: macd - macd_signal"
      - "bb_upper / bb_middle / bb_lower: Bollinger Bands (default 20/2σ)"
    narration: >
      The column names are parameterized: sma_20, ema_20, rsi_14, rather
      than just sma, ema, rsi. This means you can call add_indicators twice
      with different windows and get non-overlapping columns — useful when
      you want both a 10-day and a 50-day SMA side by side. The MACD and
      Bollinger Band column names are fixed because they each produce multiple
      related columns.

  - type: code
    label: "add_indicators"
    heading: "The Full Implementation"
    body: >
      One function, nine assignments.
    code: |
      def add_indicators(df, sma_w=20, ema_w=20, rsi_w=14,
                         macd_fast=12, macd_slow=26, macd_sig=9,
                         bb_w=20, bb_std=2.0):
          df    = df.copy()          # never mutate the input
          close = df["Close"]

          df[f"sma_{sma_w}"] = sma(close, sma_w)
          df[f"ema_{ema_w}"] = ema(close, ema_w)
          df[f"rsi_{rsi_w}"] = rsi(close, rsi_w)

          m = macd(close, macd_fast, macd_slow, macd_sig)
          df["macd"]        = m["macd"]
          df["macd_signal"] = m["signal"]
          df["macd_hist"]   = m["histogram"]

          bb = bollinger_bands(close, bb_w, bb_std)
          df["bb_upper"]  = bb["upper"]
          df["bb_middle"] = bb["middle"]
          df["bb_lower"]  = bb["lower"]

          return df
    narration: >
      Notice that the MACD DataFrame column is named "signal" internally, but
      add_indicators stores it as "macd_signal" in the output. This avoids a
      naming collision with the broader concept of a trading signal in
      subsequent days. When Day 92 generates buy and sell signals, it stores
      them in a column called "signal" — not to be confused with the MACD
      signal line.

  - type: concept
    label: "Usage pattern"
    heading: "The Section 7 Pattern"
    body: >
      Every subsequent day in Section 7 starts with this two-line header.
    bullets:
      - "store = MarketDataStore(db_path, fetch_fn=...)  — from Day 89"
      - "df = add_indicators(store.load('AAPL'))  — enriched DataFrame"
      - "strategy signals = computed from the 9 indicator columns"
      - "backtest runs on the enriched DataFrame"
      - "risk module wraps the backtester output"
    narration: >
      You have now built the first two layers of the Section 7 stack:
      market data from Day 89 and technical indicators from today. Days 91
      and 92 add backtesting and strategy generation. Day 93 adds AI-driven
      signals from news sentiment. Days 94 through 96 wrap everything in risk
      management and a paper-trading bot. Every layer uses the layer below
      it, starting from the OHLCV DataFrame and add_indicators.

  - type: exercise
    heading: "Exercise 5 — Implement add_indicators"
    prompt: >
      Implement add_indicators(df, sma_w, ema_w, rsi_w, macd_fast, macd_slow,
      macd_sig, bb_w, bb_std) that returns a copy of df with 9 new indicator
      columns. Use df["Close"] as the price series. Never mutate the input.
    hint: >
      Start with df = df.copy() and close = df["Close"]. Then six assignment
      lines: sma, ema, rsi (simple), then unpack macd() and bollinger_bands()
      into three columns each.
    narration: >
      This is pure integration: you are connecting the four functions you
      implemented in exercises 1 through 4. If all four pass their checks,
      add_indicators will pass too. The most common mistake is forgetting
      df.copy() and inadvertently mutating the input — check 2 catches this.

  - type: summary
    heading: "Day 90 Complete"
    bullets:
      - "sma(series, window): rolling(window).mean() — trend reference"
      - "ema(series, window): ewm(span, adjust=False) — responsive trend"
      - "rsi(series, window): gain/loss rolling ratio — momentum 0–100"
      - "macd(series, fast, slow, signal): three-column momentum DataFrame"
      - "bollinger_bands(series, window, num_std): three-band volatility envelope"
      - "add_indicators(df): enriches OHLCV with all 9 indicator columns"
    narration: >
      Day 90 is done. You can now transform raw OHLCV data into a rich
      analytical DataFrame with one function call. Tomorrow, Day 91, you will
      feed this enriched DataFrame into a backtester: given a set of signals
      based on these indicators, what would the strategy have returned
      historically? That is the question backtesting answers.
""",
]

# ══════════════════════════════════════════════════════════════════════════════
# Project + solution notebooks
# ══════════════════════════════════════════════════════════════════════════════

_FULL_P = _P_BASE + _P_SMA + _P_EMA + _P_RSI + _P_MACD + _P_BB + """\
def add_indicators(df, sma_w=20, ema_w=20, rsi_w=14,
                   macd_fast=12, macd_slow=26, macd_sig=9,
                   bb_w=20, bb_std=2.0):
    df    = df.copy()
    close = df["Close"]
    df[f"sma_{sma_w}"] = sma(close, sma_w)
    df[f"ema_{ema_w}"] = ema(close, ema_w)
    df[f"rsi_{rsi_w}"] = rsi(close, rsi_w)
    m = macd(close, macd_fast, macd_slow, macd_sig)
    df["macd"]        = m["macd"]
    df["macd_signal"] = m["signal"]
    df["macd_hist"]   = m["histogram"]
    bb = bollinger_bands(close, bb_w, bb_std)
    df["bb_upper"]  = bb["upper"]
    df["bb_middle"] = bb["middle"]
    df["bb_lower"]  = bb["lower"]
    return df
"""

_PROJ_DATA = """\
# Build 252-row synthetic OHLCV (gate-safe; swap for real yfinance data)
df = _synthetic(n=252)
print(f"Raw OHLCV: {df.shape} — {df.index[0].date()} to {df.index[-1].date()}")
"""

_PROJ_ENRICH = """\
enriched = add_indicators(df)
print(f"Enriched:  {enriched.shape}")
print(f"Columns:   {list(enriched.columns)}")
"""

_PROJ_STATS = """\
# Indicator summary for the last 100 rows (past ~5 months)
tail = enriched.tail(100)
print("\\n── RSI (14) stats ──────────────────────────────")
print(tail["rsi_14"].describe().round(2))
print("\\n── MACD stats ──────────────────────────────────")
print(tail[["macd", "macd_signal", "macd_hist"]].describe().round(4))
print("\\n── Bollinger Band width (last 10 rows) ─────────")
width = ((enriched["bb_upper"] - enriched["bb_lower"]) / enriched["bb_middle"]).tail(10)
print(width.round(4))
"""

_PROJ_SIGNAL = """\
# Count simple RSI signals in last 200 rows
recent = enriched.tail(200).copy()
recent["rsi_signal"] = 0
recent.loc[recent["rsi_14"] < 30, "rsi_signal"] = 1   # oversold: buy
recent.loc[recent["rsi_14"] > 70, "rsi_signal"] = -1  # overbought: sell

n_buy  = (recent["rsi_signal"] == 1).sum()
n_sell = (recent["rsi_signal"] == -1).sum()
print(f"\\nRSI signals (last 200 rows): {n_buy} buys, {n_sell} sells")
"""

PROJECT_NB = _nb([
    _md(f"# Day {DAY} Project — Indicator Dashboard\n\n"
        "Build a technical indicator dashboard for one year of synthetic OHLCV "
        "data. Compute all five indicators with `add_indicators`, print summary "
        "statistics, and generate simple RSI-based signals. "
        "Swap `_synthetic` for `fetch_ohlcv` with `fetch_fn=None` to use real "
        "yfinance data."),
    _code(_FULL_P),
    _md("## Step 1 — Load price data"),
    _code(_PROJ_DATA),
    _md("## Step 2 — Enrich with all indicators"),
    _code(_PROJ_ENRICH),
    _md("## Step 3 — Print summary statistics"),
    _code(_PROJ_STATS),
    _md("## Step 4 — Generate RSI signals"),
    _code(_PROJ_SIGNAL),
])

_SOL_ASSERTIONS = """\
df = _synthetic(n=252)
enriched = add_indicators(df)

# Shape checks
assert enriched.shape[1] == df.shape[1] + 9, \\
    f"expected {df.shape[1]+9} cols, got {enriched.shape[1]}"

# No mutation
assert "sma_20" not in df.columns, "input DataFrame was mutated"

# All indicators defined at row 25
indicator_cols = ["sma_20", "ema_20", "rsi_14", "macd", "macd_signal",
                  "macd_hist", "bb_upper", "bb_middle", "bb_lower"]
row25 = enriched.iloc[25]
for col in indicator_cols:
    assert not pd.isna(row25[col]), f"{col} is NaN at row 25"

# Bollinger invariant
non_nan_bb = enriched.dropna(subset=["bb_upper", "bb_lower"])
assert (non_nan_bb["bb_upper"] > non_nan_bb["bb_middle"]).all()
assert (non_nan_bb["bb_middle"] > non_nan_bb["bb_lower"]).all()

print(f"Enriched shape: {enriched.shape}")
print(f"Columns: {list(enriched.columns)}")
"""

_SOL_STATS = """\
tail = enriched.tail(100)
print("\\n── RSI (14) stats ──────────────────────────────")
print(tail["rsi_14"].describe().round(2))
print("\\n── MACD stats ──────────────────────────────────")
print(tail[["macd", "macd_signal", "macd_hist"]].describe().round(4))

recent = enriched.tail(200).copy()
recent["rsi_signal"] = 0
recent.loc[recent["rsi_14"] < 30, "rsi_signal"] = 1
recent.loc[recent["rsi_14"] > 70, "rsi_signal"] = -1
n_buy  = (recent["rsi_signal"] == 1).sum()
n_sell = (recent["rsi_signal"] == -1).sum()
print(f"\\nRSI signals (last 200 rows): {n_buy} buys, {n_sell} sells")
print("\\nSolution smoke-test passed.")
"""

SOLUTION_NB = _nb([
    _md(f"# Day {DAY} Solution — Indicator Dashboard"),
    _code(_FULL_P),
    _code(_SOL_ASSERTIONS),
    _code(_SOL_STATS),
])

# ══════════════════════════════════════════════════════════════════════════════
# Gate inline validation
# ══════════════════════════════════════════════════════════════════════════════

GATE_PY = f"""\
import importlib.util, sys, math, warnings
import pandas as pd

spec = importlib.util.spec_from_file_location(
    "{SLUG}", r"{DIR / (SLUG + '.py')}"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# ── synthetic close series ────────────────────────────────────────────────────
n = 252
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

# sma
s20 = mod.sma(close, 20)
assert isinstance(s20, pd.Series) and len(s20) == n
assert s20.iloc[:19].isna().all() and not pd.isna(s20.iloc[19])
const = pd.Series([5.0] * 30)
assert (mod.sma(const, 10).dropna() == 5.0).all()

# ema
e20 = mod.ema(close, 20)
assert isinstance(e20, pd.Series) and len(e20) == n
assert not e20.isna().any()
assert (mod.ema(const, 10) == 5.0).all()

# rsi
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    r14 = mod.rsi(close, 14)
    assert isinstance(r14, pd.Series) and len(r14) == n
    assert r14.iloc[:14].isna().all() and not pd.isna(r14.iloc[14])
    non_nan = r14.dropna()
    assert (non_nan >= 0).all() and (non_nan <= 100).all()
    rising  = pd.Series([float(i) for i in range(30)])
    assert (mod.rsi(rising, 10).dropna() > 90).all()

# macd
m = mod.macd(close)
assert set(m.columns) == {{"macd", "signal", "histogram"}}
assert not m.isna().any().any()
diff = (m["macd"] - m["signal"] - m["histogram"]).abs().max()
assert diff < 1e-9, f"histogram != macd - signal: {{diff}}"
const_m = mod.macd(const)
assert const_m["macd"].abs().max() < 1e-9

# bollinger_bands
bb = mod.bollinger_bands(close, 20)
assert set(bb.columns) == {{"upper", "middle", "lower"}}
assert bb["middle"].iloc[:19].isna().all() and not pd.isna(bb["middle"].iloc[19])
non_nan_bb = bb.dropna()
assert (non_nan_bb["upper"] > non_nan_bb["middle"]).all()
assert (non_nan_bb["middle"] > non_nan_bb["lower"]).all()

# add_indicators
enriched = mod.add_indicators(df)
assert enriched.shape[1] == df.shape[1] + 9
assert "sma_20" not in df.columns, "input was mutated"
indicator_cols = ["sma_20", "ema_20", "rsi_14", "macd", "macd_signal",
                  "macd_hist", "bb_upper", "bb_middle", "bb_lower"]
row25 = enriched.iloc[25]
for col in indicator_cols:
    assert not pd.isna(row25[col]), f"{{col}} is NaN at row 25"
non_nan_enriched = enriched.dropna(subset=["bb_upper", "bb_lower"])
assert (non_nan_enriched["bb_upper"] > non_nan_enriched["bb_middle"]).all()

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
