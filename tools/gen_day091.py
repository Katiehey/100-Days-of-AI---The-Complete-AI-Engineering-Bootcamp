#!/usr/bin/env python3
"""Day 091 generator — Backtesting Fundamentals."""
import json, pathlib

ROOT  = pathlib.Path(__file__).parent.parent
DAY   = "091"
SLUG  = "backtester"
TITLE = "Backtesting Fundamentals"
DIR   = ROOT / "07_finance" / f"day_{DAY}"

# ══════════════════════════════════════════════════════════════════════════════
# Deliverable
# ══════════════════════════════════════════════════════════════════════════════

DELIVERABLE = '''\
"""
Day 091 — Backtesting Fundamentals
====================================
Event-driven backtest engine for daily OHLCV strategies.

Public API
----------
    compute_returns(df)                           -> pd.Series
    compute_equity(returns, initial=1.0)          -> pd.Series
    max_drawdown(equity)                          -> float  (≤ 0)
    sharpe_ratio(returns, periods_per_year=252)   -> float
    run_backtest(df, signals)                     -> dict

run_backtest return keys
    total_return, annualized_return, sharpe_ratio,
    max_drawdown, win_rate, n_trades,
    equity (pd.Series), strategy_returns (pd.Series),
    market_returns (pd.Series)
"""
import pandas as pd


# ── returns ───────────────────────────────────────────────────────────────────

def compute_returns(df):
    """Daily percentage returns from df["Close"].

    Returns pd.Series with the same index as df.
    First value is NaN (no prior close to compare against).
    """
    return df["Close"].pct_change()


def compute_equity(returns, initial=1.0):
    """Compound a daily-returns Series into an equity curve.

    NaN values are treated as zero-return days.
    Starts at `initial` (default 1.0 — track growth of $1).

    Returns pd.Series with the same index as returns.
    """
    return (1 + returns.fillna(0)).cumprod() * initial


# ── risk metrics ──────────────────────────────────────────────────────────────

def max_drawdown(equity):
    """Maximum peak-to-trough drawdown of an equity curve.

    Returns a float ≤ 0, e.g. -0.25 means the curve fell 25% from its peak.
    A value of 0.0 means the equity never fell below its starting point.
    """
    peak = equity.cummax()
    dd   = (equity - peak) / peak
    return float(dd.min())


def sharpe_ratio(returns, periods_per_year=252):
    """Annualised Sharpe ratio (risk-free rate = 0).

    Drops NaN before computing. Returns 0.0 if std is zero or no data.
    """
    clean = returns.dropna()
    if len(clean) == 0 or clean.std() == 0:
        return 0.0
    return float(clean.mean() / clean.std() * (periods_per_year ** 0.5))


# ── backtest engine ───────────────────────────────────────────────────────────

def run_backtest(df, signals):
    """Run a vectorised daily backtest.

    Args:
        df      : OHLCV DataFrame (needs "Close" column)
        signals : pd.Series aligned to df.index; values {-1, 0, 1}
                  — 1 = long, 0 = flat, -1 = short

    Returns dict with scalar metrics and three Series:
        total_return      (float) — cumulative strategy return
        annualized_return (float) — CAGR over the backtest period
        sharpe_ratio      (float) — annualised Sharpe (rfr=0)
        max_drawdown      (float) — peak-to-trough, ≤ 0
        win_rate          (float) — fraction of days with positive return
        n_trades          (int)   — number of position changes
        equity            (pd.Series) — equity curve starting at 1.0
        strategy_returns  (pd.Series) — daily strategy P&L
        market_returns    (pd.Series) — daily buy-and-hold P&L
    """
    market_returns = compute_returns(df)

    # shift(1): enter at next day's open — eliminates look-ahead bias
    positions        = signals.shift(1).fillna(0)
    strategy_returns = positions * market_returns

    equity  = compute_equity(strategy_returns)
    clean   = strategy_returns.dropna()
    n_days  = len(clean)
    win_rate = float((clean > 0).sum() / max(n_days, 1))

    # count position transitions (entries + exits + reversals)
    pos_diff = positions.diff().fillna(0)
    n_trades = int((pos_diff != 0).sum())

    total_ret = float(equity.iloc[-1] - 1.0)
    base      = 1.0 + total_ret
    ann_ret   = float(base ** (252.0 / max(n_days, 1)) - 1) if base > 0 else -1.0

    return {
        "total_return":      total_ret,
        "annualized_return": ann_ret,
        "sharpe_ratio":      sharpe_ratio(strategy_returns),
        "max_drawdown":      max_drawdown(equity),
        "win_rate":          win_rate,
        "n_trades":          n_trades,
        "equity":            equity,
        "strategy_returns":  strategy_returns,
        "market_returns":    market_returns,
    }
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
import pandas as pd, math

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
"""

_P_INDICATORS = """\
def sma(s, w=20):  return s.rolling(window=w).mean()
def ema(s, w=20):  return s.ewm(span=w, adjust=False).mean()
def rsi(s, w=14):
    import warnings
    d = s.diff()
    g = d.clip(lower=0).rolling(w).mean()
    l = (-d.clip(upper=0)).rolling(w).mean()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        rs = g / l
    return 100 - (100 / (1 + rs))
def macd(s, fast=12, slow=26, sig=9):
    ml = ema(s, fast) - ema(s, slow)
    sl = ema(ml, sig)
    return pd.DataFrame({"macd": ml, "signal": sl, "histogram": ml - sl})
def bollinger_bands(s, w=20, ns=2.0):
    mid = sma(s, w); std = s.rolling(w).std()
    return pd.DataFrame({"upper": mid+ns*std, "middle": mid, "lower": mid-ns*std})
def add_indicators(df, sw=20, ew=20, rw=14, mf=12, ms=26, mg=9, bw=20, bs=2.0):
    df = df.copy(); c = df["Close"]
    df[f"sma_{sw}"] = sma(c, sw); df[f"ema_{ew}"] = ema(c, ew)
    df[f"rsi_{rw}"] = rsi(c, rw)
    m = macd(c, mf, ms, mg)
    df["macd"] = m["macd"]; df["macd_signal"] = m["signal"]; df["macd_hist"] = m["histogram"]
    bb = bollinger_bands(c, bw, bs)
    df["bb_upper"] = bb["upper"]; df["bb_middle"] = bb["middle"]; df["bb_lower"] = bb["lower"]
    return df
"""

_P_RETURNS = """\
def compute_returns(df):
    return df["Close"].pct_change()

def compute_equity(returns, initial=1.0):
    return (1 + returns.fillna(0)).cumprod() * initial
"""

_P_DRAWDOWN = """\
def max_drawdown(equity):
    peak = equity.cummax()
    return float(((equity - peak) / peak).min())
"""

_P_SHARPE = """\
def sharpe_ratio(returns, periods_per_year=252):
    clean = returns.dropna()
    if len(clean) == 0 or clean.std() == 0:
        return 0.0
    return float(clean.mean() / clean.std() * (periods_per_year ** 0.5))
"""

_P_BACKTEST = """\
def run_backtest(df, signals):
    market_returns   = compute_returns(df)
    positions        = signals.shift(1).fillna(0)
    strategy_returns = positions * market_returns
    equity  = compute_equity(strategy_returns)
    clean   = strategy_returns.dropna()
    n_days  = len(clean)
    win_rate = float((clean > 0).sum() / max(n_days, 1))
    pos_diff = positions.diff().fillna(0)
    n_trades = int((pos_diff != 0).sum())
    total_ret = float(equity.iloc[-1] - 1.0)
    base = 1.0 + total_ret
    ann_ret = float(base ** (252.0 / max(n_days, 1)) - 1) if base > 0 else -1.0
    return {
        "total_return":      total_ret,
        "annualized_return": ann_ret,
        "sharpe_ratio":      sharpe_ratio(strategy_returns),
        "max_drawdown":      max_drawdown(equity),
        "win_rate":          win_rate,
        "n_trades":          n_trades,
        "equity":            equity,
        "strategy_returns":  strategy_returns,
        "market_returns":    market_returns,
    }
"""

# ══════════════════════════════════════════════════════════════════════════════
# Exercise notebooks
# ══════════════════════════════════════════════════════════════════════════════

_EX1 = _nb([
    _md("# Exercise 1 — compute_returns and compute_equity\n\n"
        "Every backtest starts with a clean return series and an equity curve. "
        "`compute_returns` converts prices to daily percentage changes. "
        "`compute_equity` compounds those changes into a dollar curve that shows "
        "how $1 invested at the start would have grown (or shrunk)."),
    _code(_P_BASE + """\

def compute_returns(df):
    \"\"\"Daily percentage returns from df["Close"].

    Returns pd.Series — same length as df.  First value is NaN.
    \"\"\"
    # TODO: return df["Close"].pct_change()
    return pd.Series([float("nan")] * len(df), index=df.index)


def compute_equity(returns, initial=1.0):
    \"\"\"Compound daily returns into an equity curve starting at `initial`.

    Treat NaN values as 0-return days (fillna(0) before compounding).
    Formula: (1 + returns.fillna(0)).cumprod() * initial
    \"\"\"
    # TODO: return (1 + returns.fillna(0)).cumprod() * initial
    return pd.Series([initial] * len(returns), index=returns.index)
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — compute_returns returns a Series of the same length
try:
    df = _synthetic()
    r  = compute_returns(df)
    assert isinstance(r, pd.Series) and len(r) == len(df)
    checks += 1; print("✅ 1 compute_returns returns same-length Series")
except Exception as e:
    print("❌ 1:", e)

# 2 — first value is NaN (no previous close)
try:
    df = _synthetic()
    r  = compute_returns(df)
    assert pd.isna(r.iloc[0]), "first return should be NaN"
    assert not pd.isna(r.iloc[1]), "second return should not be NaN"
    checks += 1; print("✅ 2 first return is NaN, second is not")
except Exception as e:
    print("❌ 2:", e)

# 3 — constant prices produce zero returns
try:
    df2 = _synthetic(); df2["Close"] = 50.0
    r   = compute_returns(df2)
    assert r.iloc[1:].abs().max() < 1e-9, f"expected zeros, got max {r.iloc[1:].abs().max()}"
    checks += 1; print("✅ 3 constant prices → zero returns")
except Exception as e:
    print("❌ 3:", e)

# 4 — compute_equity starts at `initial`
try:
    df = _synthetic()
    r  = compute_returns(df)
    eq = compute_equity(r, initial=1.0)
    assert isinstance(eq, pd.Series) and len(eq) == len(r)
    assert abs(eq.iloc[0] - 1.0) < 1e-9, f"equity[0] should be 1.0, got {eq.iloc[0]}"
    checks += 1; print("✅ 4 equity curve starts at initial=1.0")
except Exception as e:
    print("❌ 4:", e)

# 5 — all-positive returns → equity strictly greater than initial
try:
    pos_ret = pd.Series([0.01] * 30)
    eq = compute_equity(pos_ret, initial=1.0)
    assert (eq > 1.0).all(), f"expected all > 1.0, min={eq.min():.4f}"
    assert eq.iloc[-1] > eq.iloc[0], "equity should grow"
    checks += 1; print("✅ 5 all-positive returns → equity grows above initial")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX2 = _nb([
    _md("# Exercise 2 — max_drawdown\n\n"
        "Drawdown measures how far a portfolio fell from its peak. Maximum "
        "drawdown is the worst peak-to-trough decline over the entire history — "
        "the single number every investor asks about before allocating capital. "
        "A drawdown of -0.30 means the strategy fell 30% from its prior high."),
    _code(_P_BASE + _P_RETURNS + """\

def max_drawdown(equity):
    \"\"\"Maximum peak-to-trough drawdown.

    Returns a float ≤ 0.
    A return of 0.0 means equity never fell below its starting point.
    -0.25 means the worst decline was 25% from the prior peak.

    Steps:
      1. peak     = equity.cummax()          — running maximum up to each point
      2. drawdown = (equity - peak) / peak   — fractional distance below peak
      3. return   float(drawdown.min())      — deepest trough
    \"\"\"
    # TODO: implement the 3 steps above
    return 0.0
"""),
    _md("### Checks"),
    _code("""\
import warnings
checks = 0

# 1 — returns a float
try:
    df = _synthetic()
    eq = compute_equity(compute_returns(df))
    dd = max_drawdown(eq)
    assert isinstance(dd, float), f"expected float, got {type(dd)}"
    checks += 1; print("✅ 1 max_drawdown returns a float")
except Exception as e:
    print("❌ 1:", e)

# 2 — drawdown is always ≤ 0
try:
    df = _synthetic()
    eq = compute_equity(compute_returns(df))
    dd = max_drawdown(eq)
    assert dd <= 1e-9, f"drawdown should be ≤ 0, got {dd}"
    checks += 1; print("✅ 2 max_drawdown is ≤ 0")
except Exception as e:
    print("❌ 2:", e)

# 3 — monotonically rising equity → drawdown ≈ 0
try:
    rising = pd.Series([1.0 + 0.01 * i for i in range(100)])
    dd = max_drawdown(rising)
    assert abs(dd) < 1e-9, f"monotone rise: expected 0, got {dd}"
    checks += 1; print("✅ 3 monotonically rising equity → drawdown ≈ 0")
except Exception as e:
    print("❌ 3:", e)

# 4 — known 50 % drawdown: 1 → 2 → 1
try:
    dates = pd.date_range("2023-01-01", periods=5, freq="B")
    test_eq = pd.Series([1.0, 1.5, 2.0, 1.5, 1.0], index=dates)
    dd = max_drawdown(test_eq)
    assert abs(dd - (-0.5)) < 1e-9, f"expected -0.5, got {dd}"
    checks += 1; print("✅ 4 equity 1→2→1 gives max_drawdown = -0.5")
except Exception as e:
    print("❌ 4:", e)

# 5 — deeper trough dominates a shallower one
try:
    dates = pd.date_range("2023-01-01", periods=7, freq="B")
    eq = pd.Series([1.0, 0.9, 1.1, 0.7, 0.8, 1.2, 1.3], index=dates)
    # Peak before index 3 = 1.1 → trough 0.7 → dd = (0.7-1.1)/1.1 ≈ -0.364
    dd = max_drawdown(eq)
    assert dd < -0.35, f"expected dd < -0.35, got {dd}"
    checks += 1; print("✅ 5 deepest trough dominates shallower ones")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX3 = _nb([
    _md("# Exercise 3 — sharpe_ratio\n\n"
        "The Sharpe ratio is the gold standard for risk-adjusted performance. "
        "It divides average daily return by daily volatility, then annualises "
        "by multiplying by √252. A Sharpe above 1.0 is considered good; above "
        "2.0 is excellent. A Sharpe of 0 means the strategy earned nothing "
        "after accounting for risk."),
    _code(_P_BASE + _P_RETURNS + _P_DRAWDOWN + """\

def sharpe_ratio(returns, periods_per_year=252):
    \"\"\"Annualised Sharpe ratio (risk-free rate = 0).

    Steps:
      1. clean = returns.dropna()
      2. if len(clean) == 0 or clean.std() == 0: return 0.0
      3. return float(clean.mean() / clean.std() * (periods_per_year ** 0.5))

    Dropping NaN before computing prevents the first-row NaN from distorting
    the mean and std.
    \"\"\"
    # TODO: implement the 3 steps above
    return 0.0
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — returns a float
try:
    df = _synthetic()
    r  = compute_returns(df)
    sr = sharpe_ratio(r)
    assert isinstance(sr, float), f"expected float, got {type(sr)}"
    checks += 1; print("✅ 1 sharpe_ratio returns a float")
except Exception as e:
    print("❌ 1:", e)

# 2 — all-zero returns → Sharpe = 0
try:
    zero = pd.Series([0.0] * 30)
    assert sharpe_ratio(zero) == 0.0, f"expected 0.0, got {sharpe_ratio(zero)}"
    checks += 1; print("✅ 2 all-zero returns → Sharpe = 0.0")
except Exception as e:
    print("❌ 2:", e)

# 3 — empty returns → Sharpe = 0
try:
    empty = pd.Series([], dtype=float)
    assert sharpe_ratio(empty) == 0.0, f"expected 0.0, got {sharpe_ratio(empty)}"
    checks += 1; print("✅ 3 empty returns → Sharpe = 0.0")
except Exception as e:
    print("❌ 3:", e)

# 4 — positive mean, nonzero std → positive Sharpe
try:
    good = pd.Series([0.001, 0.002, -0.0005, 0.003, 0.001] * 10)
    sr   = sharpe_ratio(good)
    assert sr > 0, f"expected positive Sharpe, got {sr}"
    checks += 1; print("✅ 4 positive mean returns → positive Sharpe")
except Exception as e:
    print("❌ 4:", e)

# 5 — higher returns / lower vol → higher Sharpe
try:
    r_good  = pd.Series([0.002] * 50 + [-0.001] * 10)
    r_noisy = pd.Series([0.002] * 50 + [-0.005] * 10)
    sr_good  = sharpe_ratio(r_good)
    sr_noisy = sharpe_ratio(r_noisy)
    assert sr_good > sr_noisy, f"lower vol should give higher Sharpe: {sr_good:.3f} vs {sr_noisy:.3f}"
    checks += 1; print("✅ 5 less volatile returns → higher Sharpe")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX4 = _nb([
    _md("# Exercise 4 — run_backtest\n\n"
        "`run_backtest` is the engine that powers every trading experiment in "
        "Section 7. It takes an OHLCV DataFrame and a signal Series, applies a "
        "one-day lag to prevent look-ahead bias, and returns a dict of metrics "
        "plus the equity curve. The one-day lag is the most important detail: "
        "you see the signal at the end of today, and trade at the start of tomorrow."),
    _code(_P_BASE + _P_RETURNS + _P_DRAWDOWN + _P_SHARPE + """\

REQUIRED_KEYS = {
    "total_return", "annualized_return", "sharpe_ratio", "max_drawdown",
    "win_rate", "n_trades", "equity", "strategy_returns", "market_returns",
}

def run_backtest(df, signals):
    \"\"\"Vectorised daily backtest with look-ahead prevention.

    Args:
        df      : OHLCV DataFrame (needs "Close")
        signals : pd.Series aligned to df.index; values in {-1, 0, 1}

    Critical: apply signals.shift(1).fillna(0) before multiplying by returns.
    This means the signal you see at end of day t enters your portfolio on
    day t+1 — no peeking at tomorrow's price.

    Returns a dict with keys: total_return, annualized_return, sharpe_ratio,
    max_drawdown, win_rate, n_trades, equity, strategy_returns, market_returns.
    \"\"\"
    # TODO:
    # 1. market_returns   = compute_returns(df)
    # 2. positions        = signals.shift(1).fillna(0)
    # 3. strategy_returns = positions * market_returns
    # 4. equity           = compute_equity(strategy_returns)
    # 5. clean            = strategy_returns.dropna(); n_days = len(clean)
    # 6. win_rate         = float((clean > 0).sum() / max(n_days, 1))
    # 7. n_trades         = int((positions.diff().fillna(0) != 0).sum())
    # 8. total_ret        = float(equity.iloc[-1] - 1.0)
    # 9. base = 1 + total_ret; ann_ret = base**(252/max(n_days,1))-1 if base>0 else -1.0
    # 10. return dict with all REQUIRED_KEYS
    n  = len(df)
    eq = pd.Series([1.0] * n, index=df.index)
    mr = compute_returns(df)
    return {
        "total_return":      0.0,
        "annualized_return": 0.0,
        "sharpe_ratio":      0.0,
        "max_drawdown":      0.0,
        "win_rate":          0.0,
        "n_trades":          0,
        "equity":            eq,
        "strategy_returns":  pd.Series([0.0] * n, index=df.index),
        "market_returns":    mr,
    }
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — returns dict with all required keys
try:
    df      = _synthetic()
    signals = pd.Series(1, index=df.index)
    result  = run_backtest(df, signals)
    assert isinstance(result, dict)
    missing = REQUIRED_KEYS - result.keys()
    assert not missing, f"missing keys: {missing}"
    checks += 1; print("✅ 1 run_backtest returns dict with all required keys")
except Exception as e:
    print("❌ 1:", e)

# 2 — equity[-1] == 1 + total_return
try:
    df      = _synthetic()
    signals = pd.Series(1, index=df.index)
    r       = run_backtest(df, signals)
    diff    = abs(r["equity"].iloc[-1] - (1 + r["total_return"]))
    assert diff < 1e-9, f"equity[-1] != 1+total_return: diff={diff}"
    checks += 1; print("✅ 2 equity[-1] == 1 + total_return")
except Exception as e:
    print("❌ 2:", e)

# 3 — always-long: strategy ≈ buy-and-hold (same market returns)
try:
    df      = _synthetic()
    signals = pd.Series(1, index=df.index)
    r       = run_backtest(df, signals)
    # positions = signals.shift(1) = [0, 1, 1, ..., 1]
    # strategy_returns differs from market_returns only on day 0 (position=0)
    sr = r["strategy_returns"].iloc[2:]
    mr = r["market_returns"].iloc[2:]
    diff = (sr - mr).abs().max()
    assert diff < 1e-9, f"always-long should match buy-and-hold after day 1, diff={diff}"
    checks += 1; print("✅ 3 always-long matches buy-and-hold (after warmup day)")
except Exception as e:
    print("❌ 3:", e)

# 4 — look-ahead bias: first strategy_return is NaN or 0 even when signal[0]=1
try:
    df      = _synthetic()
    signals = pd.Series(0, index=df.index)
    signals.iloc[0] = 1   # first day: buy signal
    r = run_backtest(df, signals)
    sr0 = r["strategy_returns"].iloc[0]
    assert pd.isna(sr0) or abs(sr0) < 1e-12, \
        f"look-ahead bias: strategy_returns[0] should be 0/NaN, got {sr0}"
    # Signal from day 0 should be applied on day 1
    sr1 = r["strategy_returns"].iloc[1]
    mr1 = r["market_returns"].iloc[1]
    assert abs(sr1 - mr1) < 1e-12, \
        f"signal[0]=1 should give strategy_returns[1]=market_returns[1]"
    checks += 1; print("✅ 4 signals are shifted by 1: no look-ahead bias")
except Exception as e:
    print("❌ 4:", e)

# 5 — flat signals → n_trades ≤ 1 (only the initial entry if any)
try:
    df = _synthetic()
    flat = pd.Series(0, index=df.index)   # never trade
    r   = run_backtest(df, flat)
    assert r["n_trades"] == 0, f"flat signal → 0 trades, got {r['n_trades']}"
    always_long = pd.Series(1, index=df.index)
    r2 = run_backtest(df, always_long)
    assert r2["n_trades"] == 1, f"always-long → 1 entry trade, got {r2['n_trades']}"
    checks += 1; print("✅ 5 n_trades: flat=0, always-long=1")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX5 = _nb([
    _md("# Exercise 5 — Full Pipeline: Indicators → Signal → Backtest\n\n"
        "This exercise connects the full Day 89–91 stack: synthetic OHLCV → "
        "`add_indicators` → RSI-based signal → `run_backtest` → metrics. "
        "The signal rule: go long (1) when RSI < 40 (oversold), go flat (0) "
        "when RSI > 60 (overbought), otherwise hold the previous position."),
    _code(_P_BASE + _P_INDICATORS + _P_RETURNS + _P_DRAWDOWN + _P_SHARPE + _P_BACKTEST + """\

# ── Exercise: build and run a complete RSI mean-reversion strategy ────────────

def make_rsi_signal(enriched, oversold=40, overbought=60):
    \"\"\"RSI mean-reversion signal.

    Rules:
      - Long (1) when RSI < oversold
      - Flat (0) when RSI > overbought
      - Otherwise: hold the previous position (forward-fill)

    Args:
        enriched   : DataFrame with "rsi_14" column (output of add_indicators)
        oversold   : RSI level to go long (default 40)
        overbought : RSI level to go flat (default 60)

    Returns:
        pd.Series of {0, 1} aligned to enriched.index
    \"\"\"
    # TODO:
    # 1. signal = pd.Series(float("nan"), index=enriched.index)
    # 2. signal[enriched["rsi_14"] < oversold]  = 1.0
    # 3. signal[enriched["rsi_14"] > overbought] = 0.0
    # 4. signal = signal.ffill().fillna(0.0)  — carry forward; default flat
    # 5. return signal
    return pd.Series(0.0, index=enriched.index)
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — make_rsi_signal returns a Series aligned to df
try:
    df       = _synthetic()
    enriched = add_indicators(df)
    sig      = make_rsi_signal(enriched)
    assert isinstance(sig, pd.Series) and len(sig) == len(enriched)
    checks += 1; print("✅ 1 make_rsi_signal returns same-length Series")
except Exception as e:
    print("❌ 1:", e)

# 2 — signal values are only 0 or 1
try:
    df       = _synthetic()
    enriched = add_indicators(df)
    sig      = make_rsi_signal(enriched)
    valid    = set(sig.unique()) - {0.0, 1.0, 0, 1}
    assert not valid, f"unexpected signal values: {valid}"
    checks += 1; print("✅ 2 signal values are only 0 and 1")
except Exception as e:
    print("❌ 2:", e)

# 3 — when RSI < 40, signal should be 1
try:
    df       = _synthetic()
    enriched = add_indicators(df)
    sig      = make_rsi_signal(enriched, oversold=40, overbought=60)
    oversold_mask = enriched["rsi_14"] < 40
    if oversold_mask.any():
        assert (sig[oversold_mask] == 1.0).all(), "oversold RSI should give signal=1"
    checks += 1; print("✅ 3 RSI < 40 → signal = 1")
except Exception as e:
    print("❌ 3:", e)

# 4 — run_backtest accepts the signal and returns valid metrics
try:
    df       = _synthetic()
    enriched = add_indicators(df)
    sig      = make_rsi_signal(enriched)
    result   = run_backtest(df, sig)
    assert isinstance(result["total_return"], float)
    assert isinstance(result["equity"], pd.Series)
    assert len(result["equity"]) == len(df)
    checks += 1; print("✅ 4 run_backtest runs on RSI signal without error")
except Exception as e:
    print("❌ 4:", e)

# 5 — print metrics summary
try:
    df       = _synthetic()
    enriched = add_indicators(df)
    sig      = make_rsi_signal(enriched)
    r        = run_backtest(df, sig)
    print(f"\\n  RSI strategy metrics:")
    print(f"    Total return    : {r['total_return']:.2%}")
    print(f"    Annualised ret  : {r['annualized_return']:.2%}")
    print(f"    Sharpe ratio    : {r['sharpe_ratio']:.3f}")
    print(f"    Max drawdown    : {r['max_drawdown']:.2%}")
    print(f"    Win rate        : {r['win_rate']:.2%}")
    print(f"    Trades          : {r['n_trades']}")
    checks += 1; print("✅ 5 metrics printed successfully")
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
day: "091"
lesson: 1
title: "What Is Backtesting?"
slides:
  - type: title
    heading: "Backtesting Fundamentals"
    subheading: "Simulate a trading strategy on historical data"
    narration: >
      Day 91. You have market data from Day 89 and technical indicators from Day
      90. Today you learn backtesting: the process of testing a trading strategy
      on historical price data to estimate how it would have performed. This is
      the core loop of quantitative trading. By the end of today you will have a
      working backtester that takes any signal Series and returns a full set of
      performance metrics — total return, Sharpe ratio, drawdown, win rate, and
      the number of trades. Every strategy in Days 92 through 96 runs through
      this engine.

  - type: concept
    label: "What backtesting is"
    heading: "Backtesting: Simulated Trading on Historical Data"
    body: >
      A backtest replays history using strategy rules — before you risk real money.
    bullets:
      - "Generate signals from indicators (1=long, 0=flat, -1=short)"
      - "Apply signals to historical prices to compute daily P&L"
      - "Aggregate P&L into an equity curve and risk metrics"
      - "Judge the strategy by its risk-adjusted return, not raw return"
      - "Backtest is a necessary condition, not a sufficient one"
    narration: >
      Backtesting answers the question: if I had followed this rule over the
      past year, what would my returns have been? The answer is never a
      guarantee about the future — markets change, and a rule that worked in
      2020 may fail in 2024. But a strategy that cannot survive a historical
      backtest is almost certainly not worth live trading. Today's backtester
      is the evaluation tool for every strategy you build in this section.

  - type: concept
    label: "Look-ahead bias"
    heading: "Look-Ahead Bias: The Cardinal Sin of Backtesting"
    body: >
      Your signal at day t can only use information available at the end of day t.
    bullets:
      - "Forbidden: using tomorrow's close to generate today's signal"
      - "Common mistake: not shifting signals before computing returns"
      - "Fix: positions = signals.shift(1) — enter trade on day t+1"
      - "Effect of cheating: backtest shows stellar returns; live trading loses money"
      - "shift(1) is one line; forgetting it corrupts the entire analysis"
    narration: >
      Look-ahead bias is why backtests often look better than live trading.
      When you generate a signal using today's indicator and apply it to
      today's return, you are assuming you can trade at today's closing price
      after seeing today's indicator — impossible in reality. Shifting the
      signal by one day says: I see the indicator at market close, I place the
      order for tomorrow's open. This is the correct causal structure. Every
      function in today's backtester enforces this with signals.shift(1).

  - type: concept
    label: "Backtest workflow"
    heading: "The Five-Step Backtest Loop"
    body: >
      Fetch → Enrich → Signal → Backtest → Evaluate.
    bullets:
      - "Step 1: fetch OHLCV data (market_data.py, Day 89)"
      - "Step 2: add indicators (indicators.py, Day 90)"
      - "Step 3: generate signals — rules over indicator values"
      - "Step 4: run_backtest(df, signals) → metrics dict"
      - "Step 5: compare metrics against a benchmark (buy-and-hold)"
    narration: >
      This five-step loop is what you will run dozens of times across Days
      91 through 96. Each iteration tests a different signal rule or
      parameter. The benchmark is always buy-and-hold: if your strategy
      cannot beat the market with less risk over the backtest period, there
      is no reason to run it. The Sharpe ratio captures this: it measures
      return per unit of risk, so a strategy that doubles the return but
      triples the volatility looks worse than buy-and-hold.

  - type: exercise
    heading: "Exercise 1 — compute_returns and compute_equity"
    prompt: >
      Implement compute_returns(df) using df["Close"].pct_change().
      Implement compute_equity(returns, initial=1.0) using
      (1 + returns.fillna(0)).cumprod() * initial.
    hint: >
      Both are one-liners. The fillna(0) in compute_equity converts the
      first NaN return into a zero-return day so the equity curve starts at
      exactly initial.
    narration: >
      Two one-liners. The entire complexity of this exercise is understanding
      what the output looks like: pct_change gives you the daily gains and
      losses; cumprod turns them into a dollar value. After you pass the
      checks, look at the equity curve for the synthetic data — it should
      oscillate up and down following the sine-wave price pattern.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "Backtesting: simulate strategy on history before risking real money"
      - "Look-ahead bias: signals must be shifted by 1 before computing returns"
      - "Five-step loop: fetch → enrich → signal → backtest → evaluate"
      - "compute_returns: pct_change on Close prices"
      - "compute_equity: (1+returns.fillna(0)).cumprod() * initial"
    narration: >
      The first two building blocks are in place. Next: risk metrics —
      drawdown and Sharpe ratio. These are what distinguish a good strategy
      from a lucky one.
""",

    """\
day: "091"
lesson: 2
title: "Returns and Equity Curves"
slides:
  - type: title
    heading: "Returns and Equity Curves"
    subheading: "From price to compounded growth"
    narration: >
      Every backtest starts with the same two transforms: daily returns from
      prices, and an equity curve from daily returns. This lesson digs into
      both — what they measure, where the edge cases are, and why compounding
      matters more than most people realise.

  - type: concept
    label: "Percentage returns"
    heading: "Daily Percentage Returns"
    body: >
      r_t = (Close_t - Close_{t-1}) / Close_{t-1}
    bullets:
      - "pandas: df['Close'].pct_change() — identical formula, handles NaN at t=0"
      - "Positive return: price went up; negative: price went down"
      - "Typically small numbers: 0.01 = 1%, -0.02 = -2%"
      - "Log returns: log(Close_t / Close_{t-1}) — better for long horizons"
      - "We use simple returns (pct_change) — standard for daily strategy P&L"
    narration: >
      Percentage returns are symmetric in ratio terms but not in dollar terms.
      A 50% gain followed by a 50% loss brings you to 75% of where you started,
      not back to even. This asymmetry is why drawdown recovery takes longer
      than the drawdown itself: falling 50% requires a 100% gain to recover.
      Log returns avoid this asymmetry but are harder to interpret day-to-day.
      For strategy P&L accounting at daily granularity, simple returns are the
      standard.

  - type: concept
    label: "Equity curve"
    heading: "The Equity Curve: Compounding Returns"
    body: >
      equity_t = initial × ∏(1 + r_i) for i = 1 … t
    bullets:
      - "pandas: (1 + returns.fillna(0)).cumprod() * initial"
      - "Starts at initial (typically 1.0 — 'track growth of $1')"
      - "equity > initial: strategy is profitable at that point"
      - "equity < initial: strategy is in drawdown"
      - "Shape tells you more than the final value alone"
    narration: >
      The equity curve is the single most informative chart in quantitative
      trading. You can immediately see: when did the strategy make money, when
      did it lose, how deep were the drawdowns, and how long did it take to
      recover. A strategy that ends at 1.20 (20% gain) but dipped to 0.60
      along the way is very different from one that steadily climbed to 1.20
      with no drawdown deeper than 5%. Same final number, completely different
      risk profile.

  - type: code
    label: "Returns and equity"
    heading: "Computing Returns and Equity in Practice"
    body: >
      Two lines that power every backtest.
    code: |
      market_returns = df["Close"].pct_change()    # NaN at position 0

      # Strategy: positions shifted by 1 to prevent look-ahead
      positions        = signals.shift(1).fillna(0)
      strategy_returns = positions * market_returns  # 0 on day 0 (NaN*0=NaN)

      # Equity curve: fillna(0) converts day-0 NaN → zero-return day
      equity = (1 + strategy_returns.fillna(0)).cumprod()

      # Total return
      total_return = float(equity.iloc[-1] - 1.0)
    narration: >
      Notice that `positions * market_returns` at day 0 gives NaN times zero,
      which is NaN. The fillna in compute_equity then converts that NaN to 0,
      so the equity starts at exactly 1.0. This is the correct behavior: on
      day 0 there is no previous position to carry forward, so you earn nothing.
      The first actual trade happens on day 1 when the shifted signal from day 0
      enters the position.

  - type: exercise
    heading: "Exercise 1 — compute_returns and compute_equity"
    prompt: >
      If not already done, implement compute_returns and compute_equity. After
      passing the checks, examine the equity curve for the synthetic data:
      print equity.min(), equity.max(), equity.iloc[-1].
    hint: >
      compute_equity check 4: the curve starts at 1.0 because fillna(0) makes
      the first return 0, and (1+0) = 1.0.
    narration: >
      Two one-liners. After implementing them, look at the equity curve for
      the always-long synthetic strategy. The sine-wave prices produce a
      sinusoidal equity curve — it rises, falls, and roughly returns to where
      it started after 252 trading days. This is the expected behavior for a
      perfect sine wave.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "Daily returns: pct_change on Close — first value NaN"
      - "Strategy returns: positions * market_returns (after shift(1))"
      - "Equity curve: (1+returns.fillna(0)).cumprod() — starts at 1.0"
      - "equity[-1] - 1.0 = total return"
      - "Next: measuring risk — drawdown and Sharpe ratio"
    narration: >
      Returns and equity give you the profit picture. Drawdown and Sharpe
      give you the risk picture. Both are required to evaluate a strategy.
      Next lesson: max_drawdown.
""",

    """\
day: "091"
lesson: 3
title: "Drawdown"
slides:
  - type: title
    heading: "Maximum Drawdown"
    subheading: "The worst peak-to-trough decline"
    narration: >
      Drawdown is the metric every allocator asks for: if I had invested at
      the worst possible moment, how much would I have lost before recovery?
      Maximum drawdown is the answer. It is a measure of pain — how deep the
      hole gets — and of recovery difficulty. A 50% drawdown requires a 100%
      gain to recover. Understanding drawdown changes how you evaluate a
      strategy.

  - type: concept
    label: "Drawdown formula"
    heading: "Computing Drawdown, Step by Step"
    body: >
      DD_t = (Equity_t − Peak_t) / Peak_t    where Peak_t = max(Equity_0 … Equity_t)
    bullets:
      - "peak = equity.cummax()  — running maximum up to each point in time"
      - "drawdown = (equity - peak) / peak  — fractional distance below peak"
      - "max_drawdown = drawdown.min()  — the most negative value (worst trough)"
      - "Result is always ≤ 0: negative means loss, 0 means never below peak"
      - "-0.30 means the strategy fell 30% from its prior high at worst"
    narration: >
      The cummax function is the key insight: at every point in time, the
      peak is the highest value the equity curve has ever reached up to that
      point. When the equity falls below the peak, the drawdown is negative.
      When it reaches a new all-time high, the drawdown is zero. The minimum
      of this drawdown series across the entire history is the maximum drawdown.
      Note that we call it maximum drawdown even though the value is negative —
      maximum refers to the magnitude (the worst drop), not the sign.

  - type: code
    label: "max_drawdown"
    heading: "Three Lines of pandas"
    body: >
      cummax is the key function.
    code: |
      def max_drawdown(equity):
          peak     = equity.cummax()
          drawdown = (equity - peak) / peak
          return float(drawdown.min())

      # Example: equity goes 1.0 → 1.5 → 2.0 → 1.0
      # peak:     1.0    1.5    2.0    2.0
      # dd:       0.0    0.0    0.0   -0.5
      # max_dd = -0.5  (fell 50% from the peak of 2.0)

      # Recovery: to go from 2.0 back to 2.0 from 1.0 requires +100%
      # This is the drawdown recovery asymmetry
    narration: >
      In the example: the peak at position 3 is still 2.0 (the all-time high
      from position 2). The current equity is 1.0. The drawdown is
      (1.0 - 2.0) / 2.0 = -0.5. To recover from -0.5, the strategy needs to
      earn 100% from the trough — a much bigger gain than the loss. This
      asymmetry is fundamental to risk management: avoiding large drawdowns is
      more important than chasing large returns.

  - type: exercise
    heading: "Exercise 2 — Implement max_drawdown"
    prompt: >
      Implement max_drawdown(equity) using cummax, then (equity-peak)/peak,
      then float(dd.min()). Check 4 uses a known equity curve 1→2→1 and
      expects max_drawdown = -0.5 exactly.
    hint: >
      Check 3 (monotonically rising) expects abs(dd) < 1e-9. If you get a
      small negative number like -1e-16, that is floating-point noise and
      should pass the assertion. Check 5 uses a curve with two drawdowns
      of different depths — verify that your function returns the deeper one.
    narration: >
      Three lines. After implementing, test it on the synthetic backtest:
      compute_equity on the always-long strategy, then max_drawdown. With the
      sine-wave data, expect a drawdown of roughly -30% (since prices swing
      30% above and below 100).

  - type: summary
    heading: "What You Learned"
    bullets:
      - "peak = equity.cummax() — running maximum"
      - "drawdown = (equity - peak) / peak — fractional decline from peak"
      - "max_drawdown = drawdown.min() — worst trough, always ≤ 0"
      - "A -0.5 drawdown needs a +100% gain to recover"
      - "Next: Sharpe ratio — risk-adjusted return"
    narration: >
      Drawdown tells you about the downside risk. Sharpe ratio tells you
      about the return per unit of risk. Together they give you a complete
      picture. Next lesson: Sharpe ratio.
""",

    """\
day: "091"
lesson: 4
title: "Sharpe Ratio"
slides:
  - type: title
    heading: "Sharpe Ratio"
    subheading: "Return per unit of risk — the gold standard metric"
    narration: >
      The Sharpe ratio, developed by William Sharpe in 1966, is the most
      widely cited performance metric in finance. It answers: how much return
      did the strategy generate per unit of volatility? A strategy that earns
      10% with 5% annual volatility has the same Sharpe as one that earns 20%
      with 10% volatility. Both are better than one that earns 15% with 15%
      volatility. The Sharpe ratio lets you compare strategies with different
      return and risk levels on a common scale.

  - type: concept
    label: "Sharpe formula"
    heading: "The Sharpe Formula"
    body: >
      Sharpe = (mean_daily_return / std_daily_return) × √252
    bullets:
      - "Numerator: average daily return (the reward)"
      - "Denominator: daily standard deviation (the risk)"
      - "√252: annualise — there are ~252 trading days per year"
      - "Risk-free rate: set to 0 for simplicity (standard in crypto/alternatives)"
      - "Sharpe > 1: acceptable; > 2: excellent; > 3: exceptional"
    narration: >
      The square root of 252 is approximately 15.87. Multiplying by this
      factor converts daily Sharpe to annual Sharpe, assuming returns are
      independent and identically distributed — a simplification, but the
      industry standard. The risk-free rate is the return you could earn with
      no risk (e.g., short-term government bonds). Setting it to 0 is
      conservative: it makes strategies look slightly worse than they are,
      which is the right direction for filtering.

  - type: code
    label: "Sharpe implementation"
    heading: "Sharpe Ratio in Four Lines"
    body: >
      Guard against zero standard deviation before dividing.
    code: |
      def sharpe_ratio(returns, periods_per_year=252):
          clean = returns.dropna()
          if len(clean) == 0 or clean.std() == 0:
              return 0.0
          return float(clean.mean() / clean.std() * (periods_per_year ** 0.5))

      # Zero std happens when:
      #   — all returns are identical (constant positive return)
      #   — returns are all zero (flat, no trading)
      # Convention: return 0.0 in both cases (undefined → no signal)

      # Interpretation:
      # Sharpe = 0:   earns nothing risk-adjusted
      # Sharpe = 1:   earns 1 std of return per year of risk
      # Sharpe = 2:   top-quartile hedge fund
    narration: >
      The guard for zero standard deviation is important in two cases. If
      positions are always zero, strategy returns are always zero, and std is
      zero. If positions are always 1 and prices are perfectly constant, same
      result. In both cases, returning 0.0 is the correct convention — there
      is no risk-adjusted signal. In practice, real price data almost never
      has zero standard deviation, so the guard is a safety net, not a common
      path.

  - type: exercise
    heading: "Exercise 3 — Implement sharpe_ratio"
    prompt: >
      Implement sharpe_ratio(returns, periods_per_year=252). Drop NaN first.
      Return 0.0 if empty or std is zero. Otherwise return
      mean / std * sqrt(periods_per_year).
    hint: >
      Check 5 tests that lower-volatility returns give a higher Sharpe.
      Both series have the same mean return; only the variance differs.
      If your Sharpe values are equal, check that you are using std (ddof=1)
      not var.
    narration: >
      Four lines including the guard. After implementing, run sharpe_ratio
      on the always-long synthetic strategy. The sine-wave data produces
      a Sharpe close to zero because the strategy ends roughly where it
      started — the mean daily return over a full sine cycle is near zero.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "Sharpe = (mean / std) × √periods — risk-adjusted return"
      - "Drop NaN before computing — the first return is always NaN"
      - "Zero std → return 0.0 (undefined; no signal)"
      - "Sharpe > 1 is acceptable; > 2 is excellent"
      - "Next: run_backtest — the full engine combining all metrics"
    narration: >
      Sharpe is complete. You now have all four primitives: compute_returns,
      compute_equity, max_drawdown, and sharpe_ratio. The final step is
      run_backtest, which assembles them into a single function that takes
      any signal Series and returns the full metric suite.
""",

    """\
day: "091"
lesson: 5
title: "run_backtest — The Full Engine"
slides:
  - type: title
    heading: "run_backtest"
    subheading: "One call to evaluate any strategy"
    narration: >
      The final lesson assembles everything. run_backtest is a single function
      that takes an OHLCV DataFrame and a signal Series, applies the one-day
      lag, computes all five metrics, and returns a dict with both scalars and
      the equity curve. Every subsequent day in Section 7 calls this function
      to evaluate strategies. Writing a new strategy becomes: generate signals,
      call run_backtest, read the metrics.

  - type: concept
    label: "run_backtest internals"
    heading: "What run_backtest Does, Step by Step"
    body: >
      Signal → Positions → Strategy Returns → Metrics.
    bullets:
      - "market_returns = compute_returns(df)  — buy-and-hold baseline"
      - "positions = signals.shift(1).fillna(0)  — look-ahead prevention"
      - "strategy_returns = positions * market_returns  — daily P&L"
      - "equity = compute_equity(strategy_returns)"
      - "metrics: total_return, annualized_return, sharpe_ratio, max_drawdown"
      - "counters: win_rate, n_trades"
    narration: >
      The step that matters most is the shift. By applying signals.shift(1)
      before multiplying by returns, you ensure that the signal observed at
      the end of day t is applied to the return of day t+1. This is the
      correct causal structure: you see the signal today, you trade tomorrow.
      Without the shift, the strategy uses today's indicator to trade at
      today's close — impossible in practice and the source of most backtest
      inflation.

  - type: code
    label: "run_backtest"
    heading: "The Full Implementation"
    body: >
      Twelve lines; the shift on line 3 is the most important.
    code: |
      def run_backtest(df, signals):
          market_returns   = compute_returns(df)
          positions        = signals.shift(1).fillna(0)   # ← look-ahead fix
          strategy_returns = positions * market_returns

          equity   = compute_equity(strategy_returns)
          clean    = strategy_returns.dropna()
          n_days   = len(clean)
          win_rate = float((clean > 0).sum() / max(n_days, 1))
          n_trades = int((positions.diff().fillna(0) != 0).sum())

          total_ret = float(equity.iloc[-1] - 1.0)
          base      = 1.0 + total_ret
          ann_ret   = float(base ** (252.0 / max(n_days, 1)) - 1) if base > 0 else -1.0

          return {
              "total_return":      total_ret,
              "annualized_return": ann_ret,
              "sharpe_ratio":      sharpe_ratio(strategy_returns),
              "max_drawdown":      max_drawdown(equity),
              "win_rate":          win_rate,
              "n_trades":          n_trades,
              "equity":            equity,
              "strategy_returns":  strategy_returns,
              "market_returns":    market_returns,
          }
    narration: >
      n_trades counts every time the position changes: entering long, exiting,
      entering short, reversing. For an always-long strategy, positions go
      from 0 to 1 on day 1 and stay at 1 — one trade. For a strategy that
      alternates between long and flat every day, n_trades would be close to
      252. High n_trades does not mean bad — it depends on how much each trade
      earns. But high n_trades with low Sharpe means you are churning for
      nothing.

  - type: exercise
    heading: "Exercise 4 — Implement run_backtest"
    prompt: >
      Implement run_backtest(df, signals) following the steps in the TODO.
      The look-ahead test (check 4) verifies that signals.shift(1) is applied:
      strategy_returns[0] must be NaN or 0 even when signals[0] = 1.
    hint: >
      For n_trades: positions.diff().fillna(0) != 0 counts position changes.
      The first element of diff is NaN → fillna(0) makes it zero (no trade
      on day 0 since positions start at 0). For check 5: flat signal (all
      zeros) → n_trades = 0; always-long → positions go 0→1 on day 1 →
      n_trades = 1.
    narration: >
      Twelve lines. After implementing, run Exercise 5 which connects the
      full pipeline: add_indicators from Day 90, an RSI signal function, and
      run_backtest. That full pipeline — data + indicators + signal +
      backtest — is the template for Days 92 through 96.

  - type: summary
    heading: "Day 91 Complete"
    bullets:
      - "compute_returns: df['Close'].pct_change()"
      - "compute_equity: (1+returns.fillna(0)).cumprod() * initial"
      - "max_drawdown: (equity - equity.cummax()) / equity.cummax()"
      - "sharpe_ratio: mean/std × √252, dropping NaN"
      - "run_backtest: positions=signals.shift(1); returns metrics + equity"
      - "Look-ahead bias prevented by shift(1) — the most important line"
    narration: >
      The backtester is complete. You now have the three-layer foundation of
      Section 7: market data (Day 89), indicators (Day 90), and a backtest
      engine (Day 91). Tomorrow, Day 92, you build actual trading strategies:
      SMA crossover, RSI mean-reversion, and a combined signal — all tested
      through this engine. The quality of your backtester determines the
      quality of every strategy you evaluate.
""",
]

# ══════════════════════════════════════════════════════════════════════════════
# Project + solution
# ══════════════════════════════════════════════════════════════════════════════

_FULL_P = _P_BASE + _P_INDICATORS + _P_RETURNS + _P_DRAWDOWN + _P_SHARPE + _P_BACKTEST

PROJECT_NB = _nb([
    _md(f"# Day {DAY} Project — Strategy Comparison Dashboard\n\n"
        "Compare three strategies on one year of synthetic OHLCV data:\n"
        "1. **Buy-and-hold** — always long\n"
        "2. **SMA crossover** — long when Close > SMA(20), flat otherwise\n"
        "3. **RSI mean-reversion** — long when RSI < 40, flat when RSI > 60\n\n"
        "Print a side-by-side metrics table."),
    _code(_FULL_P),
    _code("""\
df       = _synthetic(n=252)
enriched = add_indicators(df)

# Strategy 1: buy-and-hold
sig_bah = pd.Series(1, index=df.index)

# Strategy 2: SMA crossover
sig_sma = (enriched["Close"] > enriched["sma_20"]).astype(int)

# Strategy 3: RSI mean-reversion
sig_rsi = pd.Series(float("nan"), index=enriched.index)
sig_rsi[enriched["rsi_14"] < 40]  = 1.0
sig_rsi[enriched["rsi_14"] > 60]  = 0.0
sig_rsi = sig_rsi.ffill().fillna(0.0)
"""),
    _code("""\
r_bah = run_backtest(df, sig_bah)
r_sma = run_backtest(df, sig_sma)
r_rsi = run_backtest(df, sig_rsi)

print(f"{'Metric':<20} {'Buy-Hold':>10} {'SMA-20':>10} {'RSI-MR':>10}")
print("-" * 52)
for key, fmt in [
    ("total_return",      ".2%"),
    ("annualized_return", ".2%"),
    ("sharpe_ratio",      ".3f"),
    ("max_drawdown",      ".2%"),
    ("win_rate",          ".2%"),
    ("n_trades",          "d"),
]:
    v1 = r_bah[key]; v2 = r_sma[key]; v3 = r_rsi[key]
    if fmt == "d":
        print(f"{key:<20} {v1:>10d} {v2:>10d} {v3:>10d}")
    else:
        print(f"{key:<20} {v1:>{10}{fmt}} {v2:>{10}{fmt}} {v3:>{10}{fmt}}")
"""),
])

SOLUTION_NB = _nb([
    _md(f"# Day {DAY} Solution — Strategy Comparison Dashboard"),
    _code(_FULL_P),
    _code("""\
df       = _synthetic(n=252)
enriched = add_indicators(df)

sig_bah = pd.Series(1, index=df.index)
sig_sma = (enriched["Close"] > enriched["sma_20"]).astype(int)
sig_rsi = pd.Series(float("nan"), index=enriched.index)
sig_rsi[enriched["rsi_14"] < 40]  = 1.0
sig_rsi[enriched["rsi_14"] > 60]  = 0.0
sig_rsi = sig_rsi.ffill().fillna(0.0)

r_bah = run_backtest(df, sig_bah)
r_sma = run_backtest(df, sig_sma)
r_rsi = run_backtest(df, sig_rsi)

# Correctness assertions
for r in [r_bah, r_sma, r_rsi]:
    assert isinstance(r["equity"], pd.Series) and len(r["equity"]) == len(df)
    assert abs(r["equity"].iloc[-1] - (1 + r["total_return"])) < 1e-9
    assert r["max_drawdown"] <= 1e-9
    assert 0.0 <= r["win_rate"] <= 1.0
    assert r["n_trades"] >= 0

# look-ahead: always-long positions[0] = 0
positions_bah = sig_bah.shift(1).fillna(0)
assert positions_bah.iloc[0] == 0, "look-ahead: position[0] should be 0"

print(f"{'Metric':<20} {'Buy-Hold':>10} {'SMA-20':>10} {'RSI-MR':>10}")
print("-" * 52)
for key, fmt in [
    ("total_return",      ".2%"),
    ("annualized_return", ".2%"),
    ("sharpe_ratio",      ".3f"),
    ("max_drawdown",      ".2%"),
    ("win_rate",          ".2%"),
    ("n_trades",          "d"),
]:
    v1 = r_bah[key]; v2 = r_sma[key]; v3 = r_rsi[key]
    if fmt == "d":
        print(f"{key:<20} {v1:>10d} {v2:>10d} {v3:>10d}")
    else:
        print(f"{key:<20} {v1:>{10}{fmt}} {v2:>{10}{fmt}} {v3:>{10}{fmt}}")
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

# compute_returns
r = mod.compute_returns(df)
assert isinstance(r, pd.Series) and len(r) == n
assert pd.isna(r.iloc[0]), "first return must be NaN"
const_df = df.copy(); const_df["Close"] = 50.0
assert mod.compute_returns(const_df).iloc[1:].abs().max() < 1e-9

# compute_equity
eq = mod.compute_equity(r, initial=1.0)
assert isinstance(eq, pd.Series) and len(eq) == n
assert abs(eq.iloc[0] - 1.0) < 1e-9, f"equity starts at 1.0, got {{eq.iloc[0]}}"
pos_ret = pd.Series([0.01] * 10)
assert (mod.compute_equity(pos_ret) > 1.0).all()

# max_drawdown
rising = pd.Series([1.0 + 0.01 * i for i in range(50)], index=dates[:50])
dd = mod.max_drawdown(rising)
assert isinstance(dd, float) and dd <= 1e-9, f"monotone rise dd should be ≈0, got {{dd}}"
dates5 = pd.date_range("2023-01-01", periods=5, freq="B")
eq50 = pd.Series([1.0, 1.5, 2.0, 1.5, 1.0], index=dates5)
assert abs(mod.max_drawdown(eq50) - (-0.5)) < 1e-9, "expected -0.5 drawdown"

# sharpe_ratio
assert mod.sharpe_ratio(pd.Series([0.0] * 30)) == 0.0
assert mod.sharpe_ratio(pd.Series([], dtype=float)) == 0.0
good = pd.Series([0.002, 0.001, -0.0005] * 20)
assert mod.sharpe_ratio(good) > 0

# run_backtest — keys
REQUIRED = {{"total_return","annualized_return","sharpe_ratio","max_drawdown",
              "win_rate","n_trades","equity","strategy_returns","market_returns"}}
al = pd.Series(1, index=df.index)
result = mod.run_backtest(df, al)
assert isinstance(result, dict) and REQUIRED.issubset(result.keys())
assert isinstance(result["equity"], pd.Series)
assert abs(result["equity"].iloc[-1] - (1 + result["total_return"])) < 1e-9

# look-ahead bias test
la_sig = pd.Series(0, index=df.index)
la_sig.iloc[0] = 1
la_r = mod.run_backtest(df, la_sig)
sr0 = la_r["strategy_returns"].iloc[0]
assert pd.isna(sr0) or abs(sr0) < 1e-12, f"look-ahead: strategy_returns[0] should be 0/NaN, got {{sr0}}"
sr1 = la_r["strategy_returns"].iloc[1]
mr1 = la_r["market_returns"].iloc[1]
assert abs(sr1 - mr1) < 1e-12, f"signal[0]=1 → strategy_returns[1]=market_returns[1]"

# n_trades
flat_r = mod.run_backtest(df, pd.Series(0, index=df.index))
assert flat_r["n_trades"] == 0, f"flat → 0 trades, got {{flat_r['n_trades']}}"
al_r   = mod.run_backtest(df, pd.Series(1, index=df.index))
assert al_r["n_trades"] == 1, f"always-long → 1 trade, got {{al_r['n_trades']}}"

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
