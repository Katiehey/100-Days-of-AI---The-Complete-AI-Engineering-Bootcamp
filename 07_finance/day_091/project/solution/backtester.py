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
