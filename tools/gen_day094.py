#!/usr/bin/env python3
"""Day 094 generator — Risk Management."""
import json, pathlib

ROOT  = pathlib.Path(__file__).parent.parent
DAY   = "094"
SLUG  = "risk"
TITLE = "Risk Management"
DIR   = ROOT / "07_finance" / f"day_{DAY}"

# ══════════════════════════════════════════════════════════════════════════════
# Deliverable
# ══════════════════════════════════════════════════════════════════════════════

DELIVERABLE = '''\
"""
Day 094 — Risk Management
===========================
Position sizing, stop-loss, and drawdown limits for the trading pipeline.

Public API
----------
    kelly_fraction(win_rate, avg_win, avg_loss)       -> float [0, 1]
    is_stopped_out(entry_price, current_price,
                   stop_pct=0.05)                     -> bool
    apply_stop_loss(signals, prices,
                    stop_pct=0.05)                    -> pd.Series {0,1}
    market_drawdown(prices)                           -> pd.Series (≤ 0)
    apply_drawdown_limit(signals, prices,
                         limit=-0.20)                 -> pd.Series {0,1}

    RiskManager(stop_pct=0.05, drawdown_limit=-0.20)
        .filter(signals, prices)   -> pd.Series {0,1}
        .summary(original,
                 filtered)         -> dict
"""
import pandas as pd


# ── position sizing ───────────────────────────────────────────────────────────

def kelly_fraction(win_rate, avg_win, avg_loss):
    """Optimal fraction of capital to risk per trade (Kelly Criterion).

    Kelly fraction = win_rate − (1 − win_rate) / (avg_win / avg_loss)

    Returns 0.0 for degenerate inputs (avg_loss ≤ 0, win_rate outside (0,1)).
    Clamped to [0.0, 1.0] — never bet more than 100% or a negative amount.

    Args:
        win_rate : float — fraction of trades that are winners (0.0 – 1.0)
        avg_win  : float — average gain on winning trades (positive)
        avg_loss : float — average loss on losing trades (positive magnitude)

    Returns:
        float in [0.0, 1.0]
    """
    if avg_loss <= 0 or win_rate <= 0 or win_rate >= 1:
        return 0.0
    b = avg_win / avg_loss
    return max(0.0, min(1.0, win_rate - (1 - win_rate) / b))


# ── stop-loss ─────────────────────────────────────────────────────────────────

def is_stopped_out(entry_price, current_price, stop_pct=0.05):
    """Check whether the stop-loss level has been breached.

    Returns True if current_price ≤ entry_price × (1 − stop_pct).
    Returns False for non-positive entry_price (defensive guard).

    Args:
        entry_price   : float — price at which the position was entered
        current_price : float — current market price
        stop_pct      : float — loss threshold as a fraction (default 5 %)

    Returns:
        bool — True = exit the position; False = hold
    """
    if entry_price <= 0:
        return False
    return current_price <= entry_price * (1.0 - stop_pct)


def apply_stop_loss(signals, prices, stop_pct=0.05):
    """Apply a trailing stop-loss to a signal Series.

    Iterates bar by bar:
      • On a new long entry (previous signal was 0, current is 1):
        record entry_price = prices[i].
      • If already long and stop-loss is triggered:
        set signal[i] = 0 and clear entry_price.
      • If signal is 0: clear entry_price.

    Returns a modified copy of signals with some 1s replaced by 0s.

    Args:
        signals  : pd.Series of {0, 1} — raw trading signals
        prices   : pd.Series — closing prices aligned to signals.index
        stop_pct : float — stop-loss level (default 5 %)

    Returns:
        pd.Series of {0, 1}
    """
    result      = signals.copy().astype(float)
    entry_price = None

    for i in range(len(result)):
        if result.iloc[i] == 1:
            if entry_price is None:
                entry_price = float(prices.iloc[i])
            elif is_stopped_out(entry_price, float(prices.iloc[i]), stop_pct):
                result.iloc[i] = 0
                entry_price = None
        else:
            entry_price = None

    return result.astype(int)


# ── drawdown limit ────────────────────────────────────────────────────────────

def market_drawdown(prices):
    """Running drawdown of a price series from its rolling peak.

    drawdown[i] = (prices[i] − peak[i]) / peak[i]
    where peak[i] = max(prices[0 … i]).

    Returns a pd.Series of values ≤ 0.

    Args:
        prices : pd.Series — closing prices

    Returns:
        pd.Series — same length; values in (−∞, 0]
    """
    peak = prices.cummax()
    return (prices - peak) / peak


def apply_drawdown_limit(signals, prices, limit=-0.20):
    """Zero out signals whenever the market is in a deep drawdown.

    When the rolling market drawdown (prices vs. its prior peak) is worse
    than `limit`, the position is set to 0.  This is a regime filter:
    stop trading when the market is in a sustained decline.

    Args:
        signals : pd.Series of {0, 1}
        prices  : pd.Series — market price (e.g. df["Close"])
        limit   : float ≤ 0 — drawdown threshold (default -0.20 = -20 %)

    Returns:
        pd.Series of {0, 1} with signals zeroed during deep drawdowns
    """
    dd     = market_drawdown(prices)
    result = signals.copy().astype(int)
    result[dd < limit] = 0
    return result


# ── combined risk manager ─────────────────────────────────────────────────────

class RiskManager:
    """Apply stop-loss and drawdown limit as a single filter step.

    Usage:
        rm      = RiskManager(stop_pct=0.05, drawdown_limit=-0.20)
        safe    = rm.filter(raw_signals, df["Close"])
        metrics = rm.summary(raw_signals, safe)
    """

    def __init__(self, stop_pct=0.05, drawdown_limit=-0.20):
        self.stop_pct       = stop_pct
        self.drawdown_limit = drawdown_limit

    def filter(self, signals, prices):
        """Apply stop-loss then drawdown limit to signals.

        Returns pd.Series of {0, 1} — filtered trading signals.
        """
        s = apply_stop_loss(signals, prices, self.stop_pct)
        s = apply_drawdown_limit(s, prices, self.drawdown_limit)
        return s

    def summary(self, original, filtered):
        """Describe how many bars were filtered by risk controls.

        Returns dict with keys:
            total_long_bars  — bars where original signal was 1
            kept_long_bars   — bars where filtered signal is still 1
            filtered_bars    — bars changed from 1 to 0
            filter_rate      — fraction of original longs removed
        """
        n_orig = int((original == 1).sum())
        n_kept = int((filtered == 1).sum())
        return {
            "total_long_bars": n_orig,
            "kept_long_bars":  n_kept,
            "filtered_bars":   n_orig - n_kept,
            "filter_rate":     float((n_orig - n_kept) / max(n_orig, 1)),
        }
'''

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

_P_KELLY = """\
def kelly_fraction(win_rate, avg_win, avg_loss):
    if avg_loss <= 0 or win_rate <= 0 or win_rate >= 1:
        return 0.0
    b = avg_win / avg_loss
    return max(0.0, min(1.0, win_rate - (1 - win_rate) / b))
"""

_P_STOP_SIMPLE = """\
def is_stopped_out(entry_price, current_price, stop_pct=0.05):
    if entry_price <= 0:
        return False
    return current_price <= entry_price * (1.0 - stop_pct)
"""

_P_STOP_APPLY = """\
def apply_stop_loss(signals, prices, stop_pct=0.05):
    result = signals.copy().astype(float)
    entry_price = None
    for i in range(len(result)):
        if result.iloc[i] == 1:
            if entry_price is None:
                entry_price = float(prices.iloc[i])
            elif is_stopped_out(entry_price, float(prices.iloc[i]), stop_pct):
                result.iloc[i] = 0
                entry_price = None
        else:
            entry_price = None
    return result.astype(int)
"""

_P_DRAWDOWN = """\
def market_drawdown(prices):
    peak = prices.cummax()
    return (prices - peak) / peak

def apply_drawdown_limit(signals, prices, limit=-0.20):
    dd = market_drawdown(prices)
    result = signals.copy().astype(int)
    result[dd < limit] = 0
    return result
"""

_P_RISK_CLASS = """\
class RiskManager:
    def __init__(self, stop_pct=0.05, drawdown_limit=-0.20):
        self.stop_pct = stop_pct
        self.drawdown_limit = drawdown_limit

    def filter(self, signals, prices):
        s = apply_stop_loss(signals, prices, self.stop_pct)
        return apply_drawdown_limit(s, prices, self.drawdown_limit)

    def summary(self, original, filtered):
        n_orig = int((original == 1).sum())
        n_kept = int((filtered == 1).sum())
        return {
            "total_long_bars": n_orig,
            "kept_long_bars":  n_kept,
            "filtered_bars":   n_orig - n_kept,
            "filter_rate":     float((n_orig - n_kept) / max(n_orig, 1)),
        }
"""

_P_BACKTEST = """\
def _compute_returns(df):  return df["Close"].pct_change()
def _compute_equity(r):    return (1 + r.fillna(0)).cumprod()
def _max_dd(eq):
    peak = eq.cummax(); return float(((eq - peak) / peak).min())
def _sharpe(r):
    c = r.dropna()
    if len(c) == 0 or c.std() == 0: return 0.0
    return float(c.mean() / c.std() * (252 ** 0.5))
def run_backtest(df, signals, label=""):
    mr  = _compute_returns(df)
    pos = signals.shift(1).fillna(0)
    sr  = pos * mr; eq = _compute_equity(sr)
    c   = sr.dropna(); n = len(c); tr = float(eq.iloc[-1] - 1.0)
    base = 1.0 + tr
    ar  = float(base ** (252.0 / max(n, 1)) - 1) if base > 0 else -1.0
    return {
        "label":             label,
        "total_return":      tr,
        "annualized_return": ar,
        "sharpe_ratio":      _sharpe(sr),
        "max_drawdown":      _max_dd(eq),
        "win_rate":          float((c > 0).sum() / max(n, 1)),
        "n_trades":          int((pos.diff().fillna(0) != 0).sum()),
        "equity":            eq,
    }
"""

# ══════════════════════════════════════════════════════════════════════════════
# Exercises
# ══════════════════════════════════════════════════════════════════════════════

_EX1 = _nb([
    _md("# Exercise 1 — kelly_fraction and is_stopped_out\n\n"
        "Before placing a trade you make two decisions: how much to bet "
        "(position sizing) and when to exit if wrong (stop-loss trigger). "
        "`kelly_fraction` answers the first question with the Kelly Criterion. "
        "`is_stopped_out` answers the second with a single price comparison."),
    _code(_P_BASE + """\

def kelly_fraction(win_rate, avg_win, avg_loss):
    \"\"\"Kelly Criterion: optimal fraction of capital to risk per trade.

    Formula: f* = win_rate − (1 − win_rate) / (avg_win / avg_loss)

    Returns 0.0 for degenerate inputs (avg_loss ≤ 0, win_rate not in (0,1)).
    Clamp result to [0.0, 1.0].

    Example:
        win_rate=0.6, avg_win=100, avg_loss=100 → 0.6 − 0.4/1 = 0.20
    \"\"\"
    # TODO: implement
    return 0.0


def is_stopped_out(entry_price, current_price, stop_pct=0.05):
    \"\"\"True if current_price ≤ entry_price × (1 − stop_pct).

    Returns False for non-positive entry_price.
    \"\"\"
    # TODO: implement (two lines)
    return False
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — kelly: known example
try:
    k = kelly_fraction(0.6, 100, 100)
    assert abs(k - 0.2) < 1e-9, f"expected 0.2, got {k}"
    checks += 1; print("✅ 1 kelly_fraction(0.6, 100, 100) = 0.20")
except Exception as e:
    print("❌ 1:", e)

# 2 — kelly: different win/loss ratio
try:
    k = kelly_fraction(0.5, 200, 100)   # b=2, f = 0.5 - 0.5/2 = 0.25
    assert abs(k - 0.25) < 1e-9, f"expected 0.25, got {k}"
    checks += 1; print("✅ 2 kelly_fraction(0.5, avg_win=200, avg_loss=100) = 0.25")
except Exception as e:
    print("❌ 2:", e)

# 3 — kelly: edge cases return 0.0
try:
    assert kelly_fraction(0.6, 100, 0)   == 0.0, "avg_loss=0 → 0.0"
    assert kelly_fraction(0.0, 100, 100) == 0.0, "win_rate=0 → 0.0"
    assert kelly_fraction(0.4, 100, 200) == 0.0, "negative kelly → clamped to 0.0"
    checks += 1; print("✅ 3 degenerate inputs return 0.0")
except Exception as e:
    print("❌ 3:", e)

# 4 — is_stopped_out: below stop level → True
try:
    assert is_stopped_out(100.0, 94.0, stop_pct=0.05), "94 ≤ 95 → stopped"
    assert is_stopped_out(100.0, 95.0, stop_pct=0.05), "95 ≤ 95 → stopped (boundary)"
    checks += 1; print("✅ 4 is_stopped_out: price ≤ stop level → True")
except Exception as e:
    print("❌ 4:", e)

# 5 — is_stopped_out: above stop → False; bad entry → False
try:
    assert not is_stopped_out(100.0, 96.0, stop_pct=0.05), "96 > 95 → not stopped"
    assert not is_stopped_out(0.0,   94.0, stop_pct=0.05), "entry=0 → False (guard)"
    assert not is_stopped_out(-1.0,  94.0, stop_pct=0.05), "entry<0 → False"
    checks += 1; print("✅ 5 is_stopped_out: above stop / bad entry → False")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX2 = _nb([
    _md("# Exercise 2 — apply_stop_loss\n\n"
        "`apply_stop_loss` iterates over each bar, tracking the entry price. "
        "When the stop-loss is breached, it converts the signal from 1 to 0 "
        "and clears the entry so the next bar starts fresh. This stateful loop "
        "is the standard approach for stop-loss in a vectorised backtester."),
    _code(_P_BASE + _P_KELLY + _P_STOP_SIMPLE + """\

def apply_stop_loss(signals, prices, stop_pct=0.05):
    \"\"\"Apply stop-loss to a signal Series bar by bar.

    Algorithm:
      entry_price = None
      for i in range(len(result)):
          if result[i] == 1:
              if entry_price is None:       # new entry
                  entry_price = prices[i]
              elif is_stopped_out(entry_price, prices[i], stop_pct):
                  result[i] = 0             # exit position
                  entry_price = None        # clear entry
          else:
              entry_price = None            # position was already flat

    Returns pd.Series of {0, 1}.
    \"\"\"
    # TODO: implement
    result = signals.copy().astype(float)
    # ... loop here ...
    return result.astype(int)
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — returns same-length Series with {0,1} values
try:
    df  = _synthetic()
    sig = pd.Series(1, index=df.index)
    res = apply_stop_loss(sig, df["Close"])
    assert isinstance(res, pd.Series) and len(res) == len(df)
    assert set(res.unique()).issubset({0, 1})
    checks += 1; print("✅ 1 returns same-length Series with values in {0,1}")
except Exception as e:
    print("❌ 1:", e)

# 2 — stop-loss reduces long exposure (fewer or equal 1s)
try:
    df  = _synthetic()
    sig = pd.Series(1, index=df.index)
    res = apply_stop_loss(sig, df["Close"], stop_pct=0.05)
    assert res.sum() <= sig.sum(), "stop-loss should reduce or keep the same 1s"
    checks += 1; print("✅ 2 stop-loss does not increase long exposure")
except Exception as e:
    print("❌ 2:", e)

# 3 — controlled 5-bar test: stop hits at bar 3
try:
    dates = pd.date_range("2023-01-01", periods=5, freq="B")
    prices = pd.Series([100.0, 102.0, 98.0, 93.0, 95.0], index=dates)
    sig    = pd.Series([1, 1, 1, 1, 1], index=dates)
    res    = apply_stop_loss(sig, prices, stop_pct=0.05)
    expected = [1, 1, 1, 0, 1]
    assert res.tolist() == expected, f"expected {expected}, got {res.tolist()}"
    checks += 1; print("✅ 3 stop hits at bar 3 (93 ≤ 100×0.95=95), re-enters bar 4")
except Exception as e:
    print("❌ 3:", e)

# 4 — all-rising prices: no stop ever triggers
try:
    dates   = pd.date_range("2023-01-01", periods=20, freq="B")
    prices  = pd.Series([float(100 + i) for i in range(20)], index=dates)
    sig     = pd.Series(1, index=dates)
    res     = apply_stop_loss(sig, prices, stop_pct=0.05)
    assert (res == 1).all(), "rising prices → no stop-loss, all signals stay 1"
    checks += 1; print("✅ 4 all-rising prices → no stop triggers → all signals stay 1")
except Exception as e:
    print("❌ 4:", e)

# 5 — already-flat signals pass through unchanged
try:
    dates  = pd.date_range("2023-01-01", periods=5, freq="B")
    prices = pd.Series([100.0, 80.0, 60.0, 40.0, 20.0], index=dates)
    sig    = pd.Series([0, 0, 0, 0, 0], index=dates)
    res    = apply_stop_loss(sig, prices, stop_pct=0.05)
    assert (res == 0).all(), "flat signals should be unchanged"
    checks += 1; print("✅ 5 flat signals (all 0) pass through unchanged")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX3 = _nb([
    _md("# Exercise 3 — market_drawdown and apply_drawdown_limit\n\n"
        "`market_drawdown` computes the running distance below the rolling peak — "
        "the same formula as Day 91's `max_drawdown` but applied to a price "
        "series rather than an equity curve, returning a Series rather than a "
        "scalar. `apply_drawdown_limit` uses it as a regime filter: when the "
        "market is in a deep drawdown, all signals go flat."),
    _code(_P_BASE + _P_KELLY + _P_STOP_SIMPLE + _P_STOP_APPLY + """\

def market_drawdown(prices):
    \"\"\"Running drawdown from the rolling peak at each bar.

    drawdown[i] = (prices[i] − peak[i]) / peak[i]
    where peak[i] = max(prices[0 … i])

    Implementation:
        peak = prices.cummax()
        return (prices - peak) / peak

    Returns pd.Series of values ≤ 0.
    \"\"\"
    # TODO: two lines
    return pd.Series(0.0, index=prices.index)


def apply_drawdown_limit(signals, prices, limit=-0.20):
    \"\"\"Zero signals when the market drawdown exceeds `limit`.

    Implementation:
        dd     = market_drawdown(prices)
        result = signals.copy().astype(int)
        result[dd < limit] = 0
        return result

    Args:
        limit : float ≤ 0 — e.g. -0.20 means halt when down 20% from peak
    \"\"\"
    # TODO: three lines
    return signals.copy().astype(int)
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — market_drawdown: monotone rising → all zeros
try:
    dates  = pd.date_range("2023-01-01", periods=10, freq="B")
    rising = pd.Series([float(100 + i) for i in range(10)], index=dates)
    dd     = market_drawdown(rising)
    assert isinstance(dd, pd.Series) and len(dd) == 10
    assert dd.abs().max() < 1e-9, f"rising prices → dd = 0, got max {dd.abs().max()}"
    checks += 1; print("✅ 1 market_drawdown: monotone rising → all zeros")
except Exception as e:
    print("❌ 1:", e)

# 2 — market_drawdown: known 50% drawdown
try:
    dates = pd.date_range("2023-01-01", periods=3, freq="B")
    p     = pd.Series([100.0, 150.0, 75.0], index=dates)
    dd    = market_drawdown(p)
    assert abs(dd.iloc[0]) < 1e-9, f"bar 0: expected 0, got {dd.iloc[0]}"
    assert abs(dd.iloc[1]) < 1e-9, f"bar 1: expected 0, got {dd.iloc[1]}"
    assert abs(dd.iloc[2] - (-0.5)) < 1e-9, f"bar 2: expected -0.5, got {dd.iloc[2]}"
    checks += 1; print("✅ 2 market_drawdown: 100→150→75 gives dd=[0, 0, -0.5]")
except Exception as e:
    print("❌ 2:", e)

# 3 — apply_drawdown_limit: controlled 5-bar test
try:
    dates  = pd.date_range("2023-01-01", periods=5, freq="B")
    prices = pd.Series([100.0, 110.0, 120.0, 90.0, 80.0], index=dates)
    sig    = pd.Series([1, 1, 1, 1, 1], index=dates)
    res    = apply_drawdown_limit(sig, prices, limit=-0.20)
    # bar 3: dd=(90-120)/120=-0.25 < -0.20 → 0
    # bar 4: dd=(80-120)/120=-0.33 < -0.20 → 0
    assert res.tolist() == [1, 1, 1, 0, 0], \
        f"expected [1,1,1,0,0], got {res.tolist()}"
    checks += 1; print("✅ 3 apply_drawdown_limit: bars 3 and 4 zeroed (dd < -20%)")
except Exception as e:
    print("❌ 3:", e)

# 4 — apply_drawdown_limit: tight limit zeroes out most bars on sine-wave
try:
    df  = _synthetic()
    sig = pd.Series(1, index=df.index)
    res = apply_drawdown_limit(sig, df["Close"], limit=-0.10)
    assert res.sum() < sig.sum(), \
        "tight limit should zero some bars on sine-wave data"
    checks += 1; print("✅ 4 tight limit reduces long exposure on sine-wave data")
except Exception as e:
    print("❌ 4:", e)

# 5 — apply_drawdown_limit: very loose limit keeps all bars
try:
    df  = _synthetic()
    sig = pd.Series(1, index=df.index)
    res = apply_drawdown_limit(sig, df["Close"], limit=-1.00)  # -100%: never triggered
    assert (res == 1).all(), "limit=-1.0 should never trigger → all 1s"
    checks += 1; print("✅ 5 limit=-1.0 (never triggers) → all signals unchanged")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX4 = _nb([
    _md("# Exercise 4 — RiskManager\n\n"
        "`RiskManager` combines stop-loss and drawdown limit into a single `filter` "
        "call. It also provides `summary` to report how many bars were filtered. "
        "This is the interface the trading bot (Days 95–96) will use: one object, "
        "one call, before every backtest or live order."),
    _code(_P_BASE + _P_KELLY + _P_STOP_SIMPLE + _P_STOP_APPLY + _P_DRAWDOWN + """\

class RiskManager:
    \"\"\"Combined stop-loss + drawdown-limit filter.

    Constructor args:
        stop_pct       : float — stop-loss threshold (default 5%)
        drawdown_limit : float ≤ 0 — market drawdown halt level (default -20%)

    Methods:
        filter(signals, prices)       -> pd.Series {0,1}
        summary(original, filtered)   -> dict
    \"\"\"

    def __init__(self, stop_pct=0.05, drawdown_limit=-0.20):
        # TODO: store stop_pct and drawdown_limit
        self.stop_pct = stop_pct
        self.drawdown_limit = drawdown_limit

    def filter(self, signals, prices):
        \"\"\"Apply stop-loss then drawdown limit in sequence.

        Steps:
          1. s = apply_stop_loss(signals, prices, self.stop_pct)
          2. return apply_drawdown_limit(s, prices, self.drawdown_limit)
        \"\"\"
        # TODO: two lines
        return signals.copy().astype(int)

    def summary(self, original, filtered):
        \"\"\"Count how many long bars were filtered by risk controls.

        Returns dict with keys:
            total_long_bars, kept_long_bars, filtered_bars, filter_rate
        \"\"\"
        # TODO:
        # n_orig = int((original == 1).sum())
        # n_kept = int((filtered == 1).sum())
        # return {"total_long_bars": n_orig, "kept_long_bars": n_kept,
        #         "filtered_bars": n_orig-n_kept,
        #         "filter_rate": float((n_orig-n_kept)/max(n_orig,1))}
        return {"total_long_bars": 0, "kept_long_bars": 0,
                "filtered_bars": 0, "filter_rate": 0.0}
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — filter returns same-length Series with {0,1}
try:
    df  = _synthetic()
    sig = pd.Series(1, index=df.index)
    rm  = RiskManager()
    res = rm.filter(sig, df["Close"])
    assert isinstance(res, pd.Series) and len(res) == len(df)
    assert set(res.unique()).issubset({0, 1})
    checks += 1; print("✅ 1 filter returns same-length Series with {0,1}")
except Exception as e:
    print("❌ 1:", e)

# 2 — filter is at least as conservative as stop-loss alone
try:
    df  = _synthetic()
    sig = pd.Series(1, index=df.index)
    rm  = RiskManager(stop_pct=0.05, drawdown_limit=-0.20)
    sl  = apply_stop_loss(sig, df["Close"], 0.05)
    res = rm.filter(sig, df["Close"])
    assert res.sum() <= sl.sum(), \
        "combined filter should have ≤ 1s than stop-loss alone"
    checks += 1; print("✅ 2 combined filter is at least as conservative as stop-loss alone")
except Exception as e:
    print("❌ 2:", e)

# 3 — filter: tight limits dramatically reduce exposure
try:
    df    = _synthetic()
    sig   = pd.Series(1, index=df.index)
    rm    = RiskManager(stop_pct=0.02, drawdown_limit=-0.05)
    res   = rm.filter(sig, df["Close"])
    assert res.sum() < sig.sum() * 0.9, \
        "very tight limits should cut at least 10% of exposure"
    checks += 1; print("✅ 3 tight limits significantly reduce long exposure")
except Exception as e:
    print("❌ 3:", e)

# 4 — summary: correct counts
try:
    df   = _synthetic()
    sig  = pd.Series(1, index=df.index)
    rm   = RiskManager()
    res  = rm.filter(sig, df["Close"])
    info = rm.summary(sig, res)
    assert "total_long_bars" in info and "kept_long_bars" in info
    assert "filtered_bars"   in info and "filter_rate"    in info
    assert info["total_long_bars"] == int(sig.sum())
    assert info["kept_long_bars"]  == int(res.sum())
    assert info["filtered_bars"]   == info["total_long_bars"] - info["kept_long_bars"]
    checks += 1; print("✅ 4 summary counts are consistent")
except Exception as e:
    print("❌ 4:", e)

# 5 — summary filter_rate is between 0 and 1
try:
    df   = _synthetic()
    sig  = pd.Series(1, index=df.index)
    rm   = RiskManager()
    res  = rm.filter(sig, df["Close"])
    info = rm.summary(sig, res)
    assert 0.0 <= info["filter_rate"] <= 1.0, \
        f"filter_rate out of [0,1]: {info['filter_rate']}"
    print(f"  Filter rate: {info['filter_rate']:.2%} "
          f"({info['filtered_bars']}/{info['total_long_bars']} bars removed)")
    checks += 1; print("✅ 5 filter_rate is in [0.0, 1.0]")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX5 = _nb([
    _md("# Exercise 5 — Risk-Filtered Backtest Comparison\n\n"
        "Apply `RiskManager` to an always-long strategy and compare it to the "
        "unfiltered version. The risk-filtered strategy should have a lower (less "
        "negative) max drawdown — that is the point of risk management. It may "
        "also have lower total return, but the Sharpe ratio might be higher."),
    _code(_P_BASE + _P_KELLY + _P_STOP_SIMPLE + _P_STOP_APPLY + _P_DRAWDOWN + _P_RISK_CLASS + _P_BACKTEST),
    _md("### Build strategies and run backtests"),
    _code("""\
df = _synthetic(n=252)

# Raw strategy: always long
sig_raw = pd.Series(1, index=df.index)

# Risk-filtered: apply stop-loss + drawdown limit
rm       = RiskManager(stop_pct=0.05, drawdown_limit=-0.20)
sig_risk = rm.filter(sig_raw, df["Close"])

# Summary of filtering
info = rm.summary(sig_raw, sig_risk)
print(f"Bars filtered: {info['filtered_bars']} / {info['total_long_bars']} "
      f"({info['filter_rate']:.2%} filter rate)")

r_raw  = run_backtest(df, sig_raw,  "Always-Long")
r_risk = run_backtest(df, sig_risk, "Risk-Filtered")
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — risk-filtered has lower or equal max drawdown magnitude
try:
    # max_drawdown is negative; less negative = less severe
    assert r_risk["max_drawdown"] >= r_raw["max_drawdown"], \
        f"risk-filtered dd ({r_risk['max_drawdown']:.2%}) should be ≥ raw ({r_raw['max_drawdown']:.2%})"
    checks += 1; print("✅ 1 risk-filtered max drawdown is less severe than unfiltered")
except Exception as e:
    print("❌ 1:", e)

# 2 — risk-filtered has fewer or equal long bars (conservative)
try:
    assert sig_risk.sum() <= sig_raw.sum(), \
        f"filtered {sig_risk.sum()} 1s should be ≤ raw {sig_raw.sum()}"
    checks += 1; print("✅ 2 risk-filtered has fewer long bars than always-long")
except Exception as e:
    print("❌ 2:", e)

# 3 — equity consistency
try:
    for label, r in [("raw", r_raw), ("risk", r_risk)]:
        diff = abs(r["equity"].iloc[-1] - (1 + r["total_return"]))
        assert diff < 1e-9, f"{label}: equity[-1] != 1 + total_return"
    checks += 1; print("✅ 3 equity[-1] == 1 + total_return for both strategies")
except Exception as e:
    print("❌ 3:", e)

# 4 — max_drawdown is ≤ 0 for both
try:
    assert r_raw["max_drawdown"]  <= 1e-9
    assert r_risk["max_drawdown"] <= 1e-9
    checks += 1; print("✅ 4 max_drawdown ≤ 0 for both strategies")
except Exception as e:
    print("❌ 4:", e)

# 5 — print comparison table
try:
    print(f"\\n{'Metric':<22} {'Always-Long':>12} {'Risk-Filtered':>14}")
    print("-" * 50)
    for key, fmt in [("total_return",".2%"),("sharpe_ratio",".3f"),
                     ("max_drawdown",".2%"),("n_trades","d")]:
        v1, v2 = r_raw[key], r_risk[key]
        if fmt == "d":
            print(f"{key:<22} {v1:>12d} {v2:>14d}")
        else:
            print(f"{key:<22} {v1:>{12}{fmt}} {v2:>{14}{fmt}}")
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
day: "094"
lesson: 1
title: "Why Risk Management Matters"
slides:
  - type: title
    heading: "Risk Management"
    subheading: "Position sizing, stop-loss, drawdown limits"
    narration: >
      Day 94. You have a signal layer (Days 92–93) and a backtest engine
      (Day 91). Today you add the control layer: risk management. Risk
      management answers three questions every trade: how much to bet,
      when to exit a losing trade, and when to stop trading entirely. Without
      risk management, a strategy can generate excellent backtest results
      and still blow up in production. With it, losses are bounded and the
      portfolio survives to trade another day. The four functions and one
      class in risk.py are the last layer before the trading bot.

  - type: concept
    label: "Risk vs return"
    heading: "The Risk Management Trinity"
    body: >
      Three controls, one goal: survive long enough to profit.
    bullets:
      - "Position sizing: how much capital to allocate to each trade"
      - "Stop-loss: exit a losing trade before it becomes catastrophic"
      - "Drawdown limit: halt trading when the market is in a bad regime"
      - "All three reduce return; all three prevent ruin"
      - "A strategy that loses 50% needs 100% to recover — avoid deep drawdowns"
    narration: >
      The order matters. Position sizing limits the maximum possible loss per
      trade. Stop-loss limits the actual loss on an individual trade. Drawdown
      limit halts trading when the losses suggest the strategy is no longer
      working — possibly because the market regime has changed. Each control
      operates on a different time horizon: per-trade, per-position, and
      per-portfolio. You need all three because each handles a different type
      of failure.

  - type: concept
    label: "Kelly criterion"
    heading: "The Kelly Criterion: Optimal Bet Size"
    body: >
      f* = win_rate − (1 − win_rate) / (avg_win / avg_loss)
    bullets:
      - "Kelly maximises long-run wealth — in theory"
      - "In practice: use half-Kelly (f*/2) — real win rates are uncertain"
      - "f* > 0 only when the strategy has positive expected value"
      - "f* = 0 for a 50/50 strategy with equal wins and losses"
      - "f* < 0 means the strategy has negative edge — do not trade it"
    narration: >
      The Kelly Criterion was developed by John L. Kelly at Bell Labs in 1956
      as a formula for optimal bet sizing in gambling and investment. A positive
      Kelly fraction means the strategy has mathematical edge. A fraction of
      0.20 means bet 20% of capital on each trade to maximise long-run growth.
      In practice, professional traders use half-Kelly or quarter-Kelly because
      the formula assumes you know the exact win rate and average payoff —
      estimates that are noisy in live trading. The formula is most useful as
      a sanity check: if Kelly is near zero, the strategy barely has edge;
      if it is very high, the inputs may be overfitted.

  - type: exercise
    heading: "Exercise 1 — kelly_fraction and is_stopped_out"
    prompt: >
      Implement kelly_fraction(win_rate, avg_win, avg_loss) using the formula
      above. Return 0.0 for degenerate inputs; clamp to [0.0, 1.0].
      Implement is_stopped_out(entry_price, current_price, stop_pct=0.05)
      returning True if current_price ≤ entry_price × (1 − stop_pct).
    hint: >
      Check 2: kelly_fraction(0.5, 200, 100) — win/loss ratio b = 200/100 = 2;
      f* = 0.5 − 0.5/2 = 0.25. Check 3: kelly_fraction(0.4, 100, 200) —
      f* = 0.4 − 0.6/0.5 = 0.4 − 1.2 = −0.8 → clamped to 0.0.
    narration: >
      Two functions, four lines total. The Kelly formula is a one-liner after
      the edge case guard. is_stopped_out is a comparison after the guard for
      non-positive entry price. After implementing, try kelly_fraction with your
      Day 91 backtest win_rate — plug in the win_rate and average win/loss from
      the metrics dict.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "Three risk controls: position sizing, stop-loss, drawdown limit"
      - "Kelly Criterion: f* = win_rate − (1−win_rate)/(avg_win/avg_loss)"
      - "Kelly > 0 means the strategy has positive expected value"
      - "is_stopped_out: current ≤ entry × (1−stop_pct)"
      - "Next: applying stop-loss to an entire signal Series"
    narration: >
      The building blocks are in place. Next lesson: apply_stop_loss, which
      runs the stop-loss check bar by bar over the entire backtest period.
""",

    """\
day: "094"
lesson: 2
title: "Stop-Loss: Cutting Losses Early"
slides:
  - type: title
    heading: "Stop-Loss"
    subheading: "Limit the damage on any single trade"
    narration: >
      A stop-loss is a pre-committed exit rule: if the trade moves against you
      by more than a fixed percentage, you exit — no hesitation, no hope that
      it will come back. The 5% default means that if you enter at $100 and the
      price falls to $95 or below, you close the position. This limits the
      maximum loss on any trade to 5% before slippage.

  - type: concept
    label: "Why stop-loss"
    heading: "Why Traders Use Stop-Losses"
    body: >
      Human psychology makes cutting losses hard — stop-losses remove the decision.
    bullets:
      - "Loss aversion: people hold losers hoping to break even — and lose more"
      - "Stop-loss forces exit before a small loss becomes a catastrophic one"
      - "Asymmetry: -50% requires +100% to recover; capping at -5% is better"
      - "Frees capital: exit a losing trade → capital available for a better one"
      - "Cost: exits some trades early that would have recovered — acceptable"
    narration: >
      The famous trading rule is: 'cut your losses and let your winners run.'
      A stop-loss is the mechanical implementation of the first half. Without it,
      a trader facing a 10% loss tells themselves 'it will come back' and watches
      it become 30%, then 50%. The stop-loss removes the decision from the human
      at exactly the moment when human psychology is least reliable.

  - type: code
    label: "apply_stop_loss"
    heading: "Bar-by-Bar State Machine"
    body: >
      Track entry price; trigger stop when price falls below the threshold.
    code: |
      def apply_stop_loss(signals, prices, stop_pct=0.05):
          result      = signals.copy().astype(float)
          entry_price = None

          for i in range(len(result)):
              if result.iloc[i] == 1:
                  if entry_price is None:          # new entry
                      entry_price = float(prices.iloc[i])
                  elif is_stopped_out(entry_price,
                                      float(prices.iloc[i]), stop_pct):
                      result.iloc[i] = 0           # exit
                      entry_price = None
              else:
                  entry_price = None               # flat → no active entry

          return result.astype(int)
    narration: >
      The loop is the only state machine in this module. The state is
      entry_price: None means flat, a float means long at that price.
      When a new long signal appears and entry_price is None, we record
      the entry. On subsequent long bars, we check the stop. If it triggers,
      we zero the signal and reset entry_price. If the signal goes flat
      (0), we also reset entry_price — the position is closed.

  - type: concept
    label: "Stop-loss trade-offs"
    heading: "Choosing the Stop-Loss Percentage"
    body: >
      Tighter stops: fewer big losses; more premature exits.
    bullets:
      - "5% stop: exits quickly, many small losses, less catastrophic exposure"
      - "20% stop: few exits, larger individual losses, more room for recovery"
      - "The right level depends on the strategy's typical price volatility"
      - "Rule of thumb: stop ≥ 2 × average daily move (so noise doesn't trigger it)"
      - "Backtesting multiple stop levels helps find the optimal for the strategy"
    narration: >
      A stop-loss that is too tight will trigger on normal market noise —
      every small adverse move exits the position before the trend has a
      chance to develop. A stop-loss that is too wide allows losses large
      enough to seriously damage the portfolio before triggering. The right
      level is typically calibrated to the strategy's Average True Range —
      the average daily price range — so that normal daily fluctuation does
      not trigger the stop.

  - type: exercise
    heading: "Exercise 2 — Implement apply_stop_loss"
    prompt: >
      Implement apply_stop_loss(signals, prices, stop_pct=0.05) using the bar-by-bar
      loop. Check 3 tests a controlled 5-bar sequence: prices go 100→102→98→93→95,
      signal is always-long, stop_pct=0.05. The stop triggers at bar 3 (93 ≤ 95).
    hint: >
      The result starts as signals.copy().astype(float). Use result.iloc[i] to
      read and write (avoids chained assignment). entry_price is None until the
      first long bar. At bar 3: is_stopped_out(100, 93, 0.05) → 93 ≤ 95 → True.
      After the stop, entry_price is reset to None. Bar 4 (signal=1, entry=None)
      records a new entry at price=95.
    narration: >
      The controlled test is the most important check. Trace through it manually
      before implementing: bar 0 enters at 100, bars 1 and 2 are above the stop,
      bar 3 triggers the stop, bar 4 is a fresh entry. If check 3 fails, add a
      print statement inside the loop to trace entry_price and the stop level
      at each bar.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "Stop-loss: exit when price ≤ entry × (1 − stop_pct)"
      - "apply_stop_loss: bar-by-bar state machine with entry_price tracking"
      - "Tighter stop: fewer big losses but more premature exits"
      - "After stop: entry_price is cleared; next long bar starts fresh"
      - "Next: drawdown limit — the portfolio-level regime filter"
    narration: >
      Stop-loss is complete. Next: drawdown limit, which operates at the
      portfolio level rather than the trade level. Where stop-loss exits
      one bad trade, drawdown limit halts all trading when the market is
      in a sustained decline.
""",

    """\
day: "094"
lesson: 3
title: "Drawdown Limits and Regime Filters"
slides:
  - type: title
    heading: "Drawdown Limits"
    subheading: "Stop trading when the market is against you"
    narration: >
      A drawdown limit is a portfolio-level rule: when the market has fallen
      more than a fixed percentage from its recent peak, stop all trading and
      go to cash. The 20% default is a common threshold — a 20% market decline
      typically signals a bear market or serious economic stress. Many systematic
      funds stop trading entirely during such periods, preserving capital until
      conditions improve.

  - type: concept
    label: "Market drawdown"
    heading: "Market Drawdown as a Regime Signal"
    body: >
      Deep drawdowns signal that market conditions have changed.
    bullets:
      - "market_drawdown[i] = (price[i] − peak[i]) / peak[i]"
      - "Always ≤ 0: 0.0 at all-time highs, negative otherwise"
      - "-0.20 threshold: stop trading in a 20%+ market decline"
      - "Why: strategies calibrated on normal markets fail in crises"
      - "Preservation over performance: surviving is more important than profit"
    narration: >
      The 2008–2009 financial crisis saw the S&P 500 fall 57% from peak to
      trough. Many systematic strategies that performed well in normal markets
      continued to generate buy signals during the decline — and lost enormous
      amounts. A simple rule — stop trading when the market is down more than
      20% from its recent peak — would have kept those strategies in cash
      through most of the crisis. The drawdown limit is crude but effective.

  - type: code
    label: "Implementation"
    heading: "market_drawdown and apply_drawdown_limit"
    body: >
      Two functions, four lines total.
    code: |
      def market_drawdown(prices):
          peak = prices.cummax()          # rolling maximum
          return (prices - peak) / peak   # Series ≤ 0

      def apply_drawdown_limit(signals, prices, limit=-0.20):
          dd     = market_drawdown(prices)
          result = signals.copy().astype(int)
          result[dd < limit] = 0          # zero signals in deep drawdown
          return result

      # Unlike apply_stop_loss, no loop needed — vectorised boolean mask
      # cummax() handles the "rolling peak" at each bar
    narration: >
      market_drawdown reuses the same cummax logic from max_drawdown in the
      backtester, but returns a Series instead of a scalar minimum. apply_drawdown_limit
      then uses boolean indexing — a pandas one-liner — to zero all signals where
      the drawdown is worse than the limit. No loop, no state — this is the power
      of vectorised operations for regime filters that depend only on current market
      state rather than trade history.

  - type: concept
    label: "Combined filters"
    heading: "Order of Risk Filters Matters"
    body: >
      Apply stop-loss before drawdown limit for logical consistency.
    bullets:
      - "Stop-loss: trade-level, tracks individual position entry"
      - "Drawdown limit: portfolio-level, tracks aggregate market performance"
      - "Order: stop-loss first, drawdown limit second"
      - "Alternative: drawdown limit first (prevent entries in bad regime)"
      - "RiskManager.filter() applies stop → drawdown in that order"
    narration: >
      The RiskManager applies stop-loss first, then drawdown limit. This means:
      first, trim individual losing trades that have exceeded their exit threshold.
      Then, zero out any remaining signals that are in a bad market regime.
      The result is a doubly-filtered signal: only trades that have not been
      stopped out and are not in a drawdown-limited regime survive.

  - type: exercise
    heading: "Exercise 3 — market_drawdown and apply_drawdown_limit"
    prompt: >
      Implement market_drawdown(prices) as (prices - prices.cummax()) / prices.cummax().
      Implement apply_drawdown_limit(signals, prices, limit=-0.20) using boolean
      indexing. Check 3 uses prices [100, 110, 120, 90, 80] — the drawdown exceeds
      -20% at bars 3 and 4, zeroing those signals.
    hint: >
      Check 5: limit=-1.0 means "trigger only when 100% below peak" which is
      impossible, so all signals stay 1. This verifies that a very loose limit
      does not filter anything. Check 4: limit=-0.10 on the sine-wave data
      should trigger during the price decline phase.
    narration: >
      Two functions, three lines total. The key insight is the comparison:
      dd < limit is True when drawdown is more negative than limit. Since both
      are negative numbers, -0.25 < -0.20 is True (more severe drawdown).
      If you write dd > limit, you will get the opposite behavior.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "market_drawdown: running distance below rolling peak"
      - "apply_drawdown_limit: zero signals where dd < limit"
      - "20% drawdown threshold: typical bear market entry"
      - "Vectorised (no loop): faster and cleaner than stop-loss"
      - "Next: RiskManager — combine both into one class"
    narration: >
      Both functions are complete. Next lesson: the RiskManager class, which
      combines stop-loss and drawdown limit into a single filter call with
      a summary report.
""",

    """\
day: "094"
lesson: 4
title: "RiskManager — The Combined Filter"
slides:
  - type: title
    heading: "RiskManager"
    subheading: "One class, one call, two risk controls"
    narration: >
      RiskManager is the final layer before the trading bot. It wraps
      apply_stop_loss and apply_drawdown_limit into a single filter method.
      The trading bot calls rm.filter(signals, prices) and gets back a
      risk-controlled signal ready for execution. The summary method explains
      how many bars were filtered and by how much — useful for evaluating
      whether risk controls are too tight or too loose.

  - type: code
    label: "RiskManager"
    heading: "Ten Lines"
    body: >
      Two controls in sequence; one summary method.
    code: |
      class RiskManager:
          def __init__(self, stop_pct=0.05, drawdown_limit=-0.20):
              self.stop_pct       = stop_pct
              self.drawdown_limit = drawdown_limit

          def filter(self, signals, prices):
              s = apply_stop_loss(signals, prices, self.stop_pct)
              return apply_drawdown_limit(s, prices, self.drawdown_limit)

          def summary(self, original, filtered):
              n_orig = int((original == 1).sum())
              n_kept = int((filtered  == 1).sum())
              return {
                  "total_long_bars": n_orig,
                  "kept_long_bars":  n_kept,
                  "filtered_bars":   n_orig - n_kept,
                  "filter_rate":     float((n_orig-n_kept)/max(n_orig,1)),
              }
    narration: >
      The design is deliberately simple. filter applies the two controls in
      sequence — stop-loss modifies a copy, drawdown limit modifies that copy
      further. summary compares original and filtered using simple integer
      counts. The filter_rate is the fraction of long bars that were removed.
      A filter_rate of 0.30 means 30% of the raw strategy's long positions
      were eliminated by risk controls.

  - type: concept
    label: "Risk calibration"
    heading: "Calibrating Risk Controls"
    body: >
      Risk parameters should be calibrated, not guessed.
    bullets:
      - "stop_pct: calibrate to 2–3× the strategy's daily volatility"
      - "drawdown_limit: calibrate to the market's historical bear-market depth"
      - "Too tight: filter_rate > 50% → strategy barely trades (poor Sharpe)"
      - "Too loose: filter_rate < 5% → risk controls add little protection"
      - "Target: filter_rate 10–30% — meaningful protection without excess drag"
    narration: >
      Calibrating risk controls is an optimization problem: find the parameters
      that maximize Sharpe ratio after filtering, not before. Too tight, and the
      strategy barely trades — lots of missed opportunities. Too loose, and the
      risk controls do nothing meaningful. In practice, you would backtest the
      strategy over a range of stop_pct and drawdown_limit values, choosing the
      combination that gives the best risk-adjusted return on historical data.

  - type: concept
    label: "Composition pattern"
    heading: "The Filter Composition Pattern"
    body: >
      risk.py extends the pipeline from Days 91–93 without changing them.
    bullets:
      - "Day 91: run_backtest(df, signals) → metrics"
      - "Day 92: signals = sma_crossover(df)"
      - "Day 93: signals = sentiment_to_signal(aggregate_sentiment(scores))"
      - "Day 94: safe_signals = rm.filter(signals, df['Close'])"
      - "Combined: run_backtest(df, rm.filter(signal_series, df['Close']))"
    narration: >
      The composition pattern is the payoff for designing each module to be
      independent. risk.py takes a signal Series and a price Series — it does
      not care where the signals came from. Whether they came from SMA crossover,
      RSI, MACD, sentiment, or a combination — the RiskManager applies the same
      filters. This modularity is what allows you to build the paper-trading
      bot in Days 95–96 by simply composing the existing modules.

  - type: exercise
    heading: "Exercises 4 and 5 — RiskManager"
    prompt: >
      Exercise 4: implement RiskManager. Check 2 verifies that the combined
      filter has fewer or equal 1s than stop-loss alone (drawdown limit is
      additive, not subtractive). Exercise 5: compare always-long vs
      risk-filtered backtest and verify that max_drawdown improves.
    hint: >
      Exercise 5 check 1: r_risk["max_drawdown"] >= r_raw["max_drawdown"].
      Both are negative. Less negative means less severe drawdown.
      If risk-filtered has equal or worse drawdown, check that
      apply_drawdown_limit is also being applied (not just stop-loss).
    narration: >
      The comparison table in check 5 is the key output. Risk-filtered total
      return will likely be lower on the sine-wave data (fewer long positions),
      but max drawdown should be less severe. That is the expected trade-off.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "RiskManager: filter applies stop-loss then drawdown limit"
      - "summary: total_long_bars, kept_long_bars, filtered_bars, filter_rate"
      - "Target filter_rate: 10–30% — meaningful but not excessive"
      - "Calibrate stop_pct to 2–3× daily volatility"
      - "Next: integrate RiskManager into the paper-trading bot (Day 95)"
    narration: >
      Day 94 is nearly done. The final lesson integrates risk management into
      the full Section 7 pipeline for the project, and previews how Days 95–96
      will wrap everything into a running paper-trading bot.
""",

    """\
day: "094"
lesson: 5
title: "The Full Risk Pipeline"
slides:
  - type: title
    heading: "Risk-Adjusted Backtesting"
    subheading: "Filters before execution, not after measurement"
    narration: >
      The final lesson shows the complete risk-adjusted pipeline. The key
      insight is that risk controls must be applied BEFORE run_backtest, not
      after. You do not compute an unfiltered backtest and then 'apply' risk
      rules to the results — you filter the signals before they enter the
      backtester. This ensures the backtest accurately reflects what the
      live system would do.

  - type: concept
    label: "Pipeline order"
    heading: "The Correct Pipeline Order"
    body: >
      Signal → Risk filter → Backtest. Not Signal → Backtest → Risk.
    bullets:
      - "WRONG: run_backtest(df, signals) then 'adjust' the result"
      - "RIGHT: safe = rm.filter(signals, df['Close']); run_backtest(df, safe)"
      - "Risk filtering changes the signal → changes the returns → changes the metrics"
      - "The backtest of the filtered signal is the backtest of the real strategy"
      - "A risk-filtered strategy with Sharpe 1.2 is better than unfiltered 1.5"
    narration: >
      Post-hoc risk adjustment is a form of look-ahead bias in strategy
      evaluation: you backtest the raw strategy, see that it has a 40% drawdown,
      and claim you 'would have' applied a drawdown limit. But you did not
      actually backtest with the limit in place. Correctly implemented, the risk
      filter modifies the signals before the backtester sees them. The backtester
      then measures the actual return of the filtered strategy — lower return,
      lower drawdown, potentially higher Sharpe.

  - type: code
    label: "Complete pipeline"
    heading: "The Full Section 7 Stack"
    body: >
      Six lines from raw data to risk-adjusted metrics.
    code: |
      from market_data  import MarketDataStore, fetch_ohlcv
      from indicators   import add_indicators
      from strategy     import sma_crossover
      from risk         import RiskManager
      from backtester   import run_backtest

      df       = add_indicators(store.load("AAPL"))
      raw_sig  = sma_crossover(df)
      rm       = RiskManager(stop_pct=0.05, drawdown_limit=-0.20)
      safe_sig = rm.filter(raw_sig, df["Close"])
      result   = run_backtest(df, safe_sig)
      print(rm.summary(raw_sig, safe_sig))
    narration: >
      This six-line pipeline is the complete Section 7 stack that Days 89–94
      have been building toward. Market data from Day 89, indicators from Day 90,
      backtester from Day 91, strategy from Day 92, risk from today. On Day 95
      you will add the paper-trading bot that runs this pipeline daily and sends
      alerts. On Day 96, you will add scheduling and logging. The bot itself
      is just a loop around this pipeline.

  - type: concept
    label: "Drawdown vs stop-loss"
    heading: "When to Use Each Control"
    body: >
      Stop-loss and drawdown limit serve different purposes.
    bullets:
      - "Stop-loss: per-trade protection — exits after a specific loss on one position"
      - "Drawdown limit: portfolio protection — halts when the market is in crisis"
      - "Combine both: stop-loss for normal bad trades; drawdown limit for regime change"
      - "Without stop-loss: one bad trade can eat all the Kelly-sized capital"
      - "Without drawdown limit: a 2008-style crisis trades through the collapse"
    narration: >
      Think of it this way: stop-loss protects against individual trade failure.
      Drawdown limit protects against system failure — when the market environment
      makes the strategy's assumptions invalid. A trend-following strategy that
      works in calm markets may generate false signals during a crash, adding
      losses on top of losses. The drawdown limit says: if the environment has
      changed enough to cause a 20% market decline, our signals are no longer
      trustworthy — stop trading.

  - type: exercise
    heading: "Project — Risk-Filtered Strategy Dashboard"
    prompt: >
      The project compares five strategies — always-long, SMA crossover, RSI
      mean reversion, MACD, and combined — each with and without RiskManager.
      Print a table showing how risk filtering changes each strategy's metrics.
      Observe the consistent pattern: lower total return, improved max drawdown,
      sometimes higher Sharpe.
    hint: >
      Use RiskManager(stop_pct=0.05, drawdown_limit=-0.20) for all strategies.
      The solution notebook asserts that risk-filtered max_drawdown ≥ unfiltered
      max_drawdown (less negative) for every strategy.
    narration: >
      The project is the capstone of Day 94 and the section's risk layer.
      After running it, you have a complete picture of what risk management costs
      and what it buys: smaller worst-case losses at the expense of some return.
      That trade-off is the core of risk management. Tomorrow's paper-trading bot
      will apply these controls in a live simulation.

  - type: summary
    heading: "Day 94 Complete"
    bullets:
      - "kelly_fraction: optimal bet size — positive only with edge"
      - "is_stopped_out: single-bar stop-loss check"
      - "apply_stop_loss: bar-by-bar state machine, entry tracking"
      - "market_drawdown + apply_drawdown_limit: regime filter"
      - "RiskManager: filter (stop + drawdown) + summary"
      - "Pipeline order: filter signals BEFORE run_backtest"
    narration: >
      The full Section 7 stack is built. Market data, indicators, strategies,
      backtester, sentiment, risk management — all complete. Days 95 and 96
      assemble these into a paper-trading bot: a program that runs the pipeline
      daily, makes decisions, logs them, and sends alerts. That is the final
      product of Section 7.
""",
]

# ══════════════════════════════════════════════════════════════════════════════
# Project + solution
# ══════════════════════════════════════════════════════════════════════════════

_FULL_P = _P_BASE + _P_KELLY + _P_STOP_SIMPLE + _P_STOP_APPLY + _P_DRAWDOWN + _P_RISK_CLASS + _P_BACKTEST

_STRAT_P = """\
def _sma_cross(df, fast=20, slow=50):
    c = df["Close"]
    return (c.rolling(fast).mean() > c.rolling(slow).mean()).fillna(False).astype(int)

def _rsi_mr(df, window=14, oversold=35, overbought=65):
    import warnings
    d = df["Close"].diff()
    g = d.clip(lower=0).rolling(window).mean()
    l = (-d.clip(upper=0)).rolling(window).mean()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        rs = g / l
    rsi_s = 100 - (100 / (1 + rs))
    sig = pd.Series(float("nan"), index=df.index)
    sig[rsi_s < oversold]   = 1.0
    sig[rsi_s > overbought] = 0.0
    return sig.ffill().fillna(0).astype(int)

def _macd_cross(df, fast=12, slow=26, signal=9):
    c = df["Close"]
    ml = c.ewm(span=fast, adjust=False).mean() - c.ewm(span=slow, adjust=False).mean()
    sl = ml.ewm(span=signal, adjust=False).mean()
    return (ml > sl).astype(int)
"""

PROJECT_NB = _nb([
    _md(f"# Day {DAY} Project — Risk-Filtered Strategy Dashboard\n\n"
        "Compare three strategies — SMA crossover, RSI mean reversion, and MACD — "
        "with and without `RiskManager`. Observe the consistent trade-off: "
        "lower return, better max drawdown, sometimes higher Sharpe."),
    _code(_FULL_P + _STRAT_P),
    _code("""\
df = _synthetic(n=252)
rm = RiskManager(stop_pct=0.05, drawdown_limit=-0.20)

strategies = [
    ("SMA-cross",    _sma_cross(df)),
    ("RSI-MR",       _rsi_mr(df)),
    ("MACD",         _macd_cross(df)),
]

results = []
for label, sig in strategies:
    raw      = run_backtest(df, sig, label)
    filtered = run_backtest(df, rm.filter(sig, df["Close"]), label + "+Risk")
    info     = rm.summary(sig, rm.filter(sig, df["Close"]))
    results.append((label, raw, filtered, info))
"""),
    _code("""\
print(f"{'Strategy':<20} {'Raw Return':>11} {'Risk Return':>11} "
      f"{'Raw MaxDD':>10} {'Risk MaxDD':>10} {'Filter%':>8}")
print("-" * 74)
for label, raw, filt, info in results:
    print(f"{label:<20} "
          f"{raw['total_return']:>11.2%} {filt['total_return']:>11.2%} "
          f"{raw['max_drawdown']:>10.2%} {filt['max_drawdown']:>10.2%} "
          f"{info['filter_rate']:>8.2%}")
"""),
])

SOLUTION_NB = _nb([
    _md(f"# Day {DAY} Solution — Risk-Filtered Strategy Dashboard"),
    _code(_FULL_P + _STRAT_P),
    _code("""\
df = _synthetic(n=252)
rm = RiskManager(stop_pct=0.05, drawdown_limit=-0.20)

strategies = [("SMA-cross", _sma_cross(df)),
              ("RSI-MR",    _rsi_mr(df)),
              ("MACD",      _macd_cross(df))]

results = []
for label, sig in strategies:
    raw_filt = rm.filter(sig, df["Close"])
    raw  = run_backtest(df, sig,      label)
    filt = run_backtest(df, raw_filt, label + "+Risk")
    info = rm.summary(sig, raw_filt)
    results.append((label, raw, filt, info))

# Assertions
for label, raw, filt, info in results:
    assert filt["max_drawdown"] >= raw["max_drawdown"], \
        f"{label}: risk-filtered max_drawdown should be ≥ raw"
    assert abs(filt["equity"].iloc[-1] - (1 + filt["total_return"])) < 1e-9
    assert 0.0 <= info["filter_rate"] <= 1.0

print(f"{'Strategy':<20} {'Raw Return':>11} {'Risk Return':>11} "
      f"{'Raw MaxDD':>10} {'Risk MaxDD':>10} {'Filter%':>8}")
print("-" * 74)
for label, raw, filt, info in results:
    print(f"{label:<20} "
          f"{raw['total_return']:>11.2%} {filt['total_return']:>11.2%} "
          f"{raw['max_drawdown']:>10.2%} {filt['max_drawdown']:>10.2%} "
          f"{info['filter_rate']:>8.2%}")
print("\\nSolution smoke-test passed.")
"""),
])

# ══════════════════════════════════════════════════════════════════════════════
# Gate
# ══════════════════════════════════════════════════════════════════════════════

GATE_PY = f"""\
import importlib.util, sys, math
import pandas as pd

spec = importlib.util.spec_from_file_location(
    "{SLUG}", r"{DIR / (SLUG + '.py')}"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

n      = 252
prices_l = [100.0 * (1 + 0.3 * math.sin(i * 2 * math.pi / 252)) for i in range(n)]
dates  = pd.date_range("2023-01-01", periods=n, freq="B")
close  = pd.Series(prices_l, index=dates)
df = pd.DataFrame({{
    "Open":   close.shift(1).fillna(close.iloc[0]),
    "High":   close * 1.01, "Low":  close * 0.99,
    "Close":  close,
    "Volume": pd.Series([1_000_000 + i * 1_000 for i in range(n)], index=dates),
}})

# kelly_fraction
assert abs(mod.kelly_fraction(0.6, 100, 100) - 0.20) < 1e-9
assert abs(mod.kelly_fraction(0.5, 200, 100) - 0.25) < 1e-9
assert mod.kelly_fraction(0.6, 100, 0)   == 0.0   # avg_loss=0
assert mod.kelly_fraction(0.4, 100, 200) == 0.0   # negative kelly → clamped
assert mod.kelly_fraction(0.0, 100, 100) == 0.0   # win_rate=0

# is_stopped_out
assert     mod.is_stopped_out(100.0, 94.0, 0.05)
assert     mod.is_stopped_out(100.0, 95.0, 0.05)   # boundary: ≤ stop
assert not mod.is_stopped_out(100.0, 96.0, 0.05)
assert not mod.is_stopped_out(0.0,   80.0, 0.05)   # guard: entry≤0

# apply_stop_loss — controlled test
dates5  = pd.date_range("2023-01-01", periods=5, freq="B")
prices5 = pd.Series([100.0, 102.0, 98.0, 93.0, 95.0], index=dates5)
sig5    = pd.Series([1, 1, 1, 1, 1], index=dates5)
sl5     = mod.apply_stop_loss(sig5, prices5, stop_pct=0.05)
assert sl5.tolist() == [1, 1, 1, 0, 1], f"expected [1,1,1,0,1], got {{sl5.tolist()}}"

# apply_stop_loss — rising prices: no stop
rising_d = pd.date_range("2023-01-01", periods=20, freq="B")
rising_p = pd.Series([float(100 + i) for i in range(20)], index=rising_d)
rising_s = pd.Series(1, index=rising_d)
assert (mod.apply_stop_loss(rising_s, rising_p) == 1).all()

# market_drawdown
dd_out = mod.market_drawdown(close)
assert isinstance(dd_out, pd.Series) and len(dd_out) == n
assert (dd_out <= 1e-9).all(), "drawdown must be ≤ 0"
# rising sub-series: dd=0
rising_p2 = pd.Series([float(100+i) for i in range(10)],
                       index=pd.date_range("2023-01-01", periods=10, freq="B"))
assert mod.market_drawdown(rising_p2).abs().max() < 1e-9

# apply_drawdown_limit — controlled test
dates5b  = pd.date_range("2023-01-01", periods=5, freq="B")
prices5b = pd.Series([100.0, 110.0, 120.0, 90.0, 80.0], index=dates5b)
sig5b    = pd.Series([1, 1, 1, 1, 1], index=dates5b)
dl5      = mod.apply_drawdown_limit(sig5b, prices5b, limit=-0.20)
assert dl5.tolist() == [1, 1, 1, 0, 0], f"expected [1,1,1,0,0], got {{dl5.tolist()}}"

# apply_drawdown_limit — limit=-1.0: never triggers
all_sig = pd.Series(1, index=dates)
assert (mod.apply_drawdown_limit(all_sig, close, limit=-1.0) == 1).all()

# RiskManager
rm  = mod.RiskManager(stop_pct=0.05, drawdown_limit=-0.20)
sig = pd.Series(1, index=dates)
res = rm.filter(sig, close)
assert isinstance(res, pd.Series) and len(res) == n
assert set(res.unique()).issubset({{0, 1}})
assert res.sum() <= sig.sum(), "filter should not increase 1s"

sl_only = mod.apply_stop_loss(sig, close, 0.05)
assert res.sum() <= sl_only.sum(), "combined ≤ stop-loss alone"

info = rm.summary(sig, res)
assert {{\"total_long_bars\",\"kept_long_bars\",\"filtered_bars\",\"filter_rate\"}}.issubset(info.keys())
assert info["total_long_bars"] == int(sig.sum())
assert info["kept_long_bars"]  == int(res.sum())
assert info["filtered_bars"]   == info["total_long_bars"] - info["kept_long_bars"]
assert 0.0 <= info["filter_rate"] <= 1.0

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
