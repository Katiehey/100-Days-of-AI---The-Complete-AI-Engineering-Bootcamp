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
