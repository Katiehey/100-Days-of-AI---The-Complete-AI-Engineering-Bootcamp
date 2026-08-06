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
