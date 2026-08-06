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
import pandas as pd

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
