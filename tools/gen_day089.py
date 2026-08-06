#!/usr/bin/env python3
"""Day 089 generator — Financial Data."""
import json, pathlib

ROOT  = pathlib.Path(__file__).parent.parent
DAY   = "089"
SLUG  = "market_data"
TITLE = "Financial Data"
DIR   = ROOT / "07_finance" / f"day_{DAY}"

# ══════════════════════════════════════════════════════════════════════════════
# Deliverable source fragments
# ══════════════════════════════════════════════════════════════════════════════

_FRAG_DOC = '''\
"""
Day 089 — Financial Data
=========================
Fetch, validate, normalize, and store OHLCV market data.

OHLCV = Open / High / Low / Close / Volume — the standard candlestick
format returned by market data APIs such as yfinance.

Public API
----------
    OHLCV_COLS                                            — required column names
    fetch_ohlcv(ticker, period, interval, fetch_fn=None)  -> pd.DataFrame
    validate_ohlcv(df)   -> (bool, str)                  — (ok, reason)
    normalize_ohlcv(df)  -> pd.DataFrame                 — tz-naive, 5 cols
    store_ohlcv(df, ticker, db_path)    -> int           — rows stored
    load_ohlcv(ticker,   db_path)       -> pd.DataFrame
    MarketDataStore(db_path, fetch_fn=None)
"""
'''

_FRAG_IMPORTS = '''\
import sqlite3
import pandas as pd
'''

_FRAG_CONSTANTS = '''\

OHLCV_COLS = ["Open", "High", "Low", "Close", "Volume"]
'''

_FRAG_FETCH = '''\

# ── fetch ─────────────────────────────────────────────────────────────────────

def fetch_ohlcv(ticker, period="1y", interval="1d", fetch_fn=None):
    """Fetch OHLCV data for ticker.

    Args
    ----
    ticker   : str  e.g. "AAPL", "BTC-USD"
    period   : str  e.g. "1y", "6mo", "3mo"
    interval : str  e.g. "1d", "1h", "5m"
    fetch_fn : callable(ticker, period, interval) -> pd.DataFrame | None
               If provided, replaces yfinance entirely.
               Gate always injects a deterministic synthetic function.

    Returns
    -------
    pd.DataFrame with columns Open, High, Low, Close, Volume
    """
    if fetch_fn is not None:
        return fetch_fn(ticker, period, interval)
    import yfinance as yf
    df = yf.download(ticker, period=period, interval=interval, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df
'''

_FRAG_VALIDATE = '''\

# ── validate ──────────────────────────────────────────────────────────────────

def validate_ohlcv(df):
    """Return (True, "") if df is a well-formed OHLCV DataFrame.
    Return (False, reason_string) otherwise.  Never raises.
    """
    if not isinstance(df, pd.DataFrame):
        return False, "not a DataFrame"
    missing = [c for c in OHLCV_COLS if c not in df.columns]
    if missing:
        return False, "missing columns: " + ", ".join(missing)
    if len(df) == 0:
        return False, "DataFrame is empty"
    valid_rows = df.dropna(subset=["High", "Low"])
    if len(valid_rows) > 0 and (valid_rows["High"] < valid_rows["Low"]).any():
        return False, "High < Low detected in one or more rows"
    return True, ""
'''

_FRAG_NORMALIZE = '''\

# ── normalize ─────────────────────────────────────────────────────────────────

def normalize_ohlcv(df):
    """Return a copy of df with a tz-naive DatetimeIndex and only OHLCV_COLS."""
    df = df.copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    cols = [c for c in OHLCV_COLS if c in df.columns]
    return df[cols]
'''

_FRAG_STORE = '''\

# ── store / load ──────────────────────────────────────────────────────────────

def store_ohlcv(df, ticker, db_path=":memory:"):
    """Validate, normalize, and persist OHLCV data to SQLite.

    Returns the number of rows stored.
    Raises ValueError if validation fails.

    Note: use a real file path for persistence across calls.
    Each call to sqlite3.connect(":memory:") opens a NEW in-memory
    database, so store + load with ":memory:" will not round-trip.
    """
    ok, reason = validate_ohlcv(df)
    if not ok:
        raise ValueError("Invalid OHLCV data: " + reason)
    df = normalize_ohlcv(df)
    con = sqlite3.connect(db_path)
    try:
        con.execute(
            "CREATE TABLE IF NOT EXISTS ohlcv ("
            "ticker TEXT NOT NULL, date TEXT NOT NULL, "
            "open REAL, high REAL, low REAL, close REAL, volume REAL, "
            "PRIMARY KEY (ticker, date))"
        )
        rows = []
        for date, row in df.iterrows():
            d = str(date.date()) if hasattr(date, "date") else str(date)
            rows.append((
                ticker, d,
                float(row["Open"]),  float(row["High"]),
                float(row["Low"]),   float(row["Close"]),
                float(row["Volume"]),
            ))
        con.executemany("INSERT OR REPLACE INTO ohlcv VALUES (?,?,?,?,?,?,?)", rows)
        con.commit()
        return len(rows)
    finally:
        con.close()


def load_ohlcv(ticker, db_path=":memory:"):
    """Load stored OHLCV data for ticker.

    Returns an empty DataFrame (columns = OHLCV_COLS) if nothing found.
    """
    con = sqlite3.connect(db_path)
    try:
        try:
            rows = con.execute(
                "SELECT date, open, high, low, close, volume "
                "FROM ohlcv WHERE ticker=? ORDER BY date",
                (ticker,),
            ).fetchall()
        except sqlite3.OperationalError:
            return pd.DataFrame(columns=OHLCV_COLS)
        if not rows:
            return pd.DataFrame(columns=OHLCV_COLS)
        df = pd.DataFrame(
            rows, columns=["date", "Open", "High", "Low", "Close", "Volume"]
        )
        df.index = pd.to_datetime(df["date"])
        df.index.name = None
        return df.drop(columns=["date"])
    finally:
        con.close()
'''

_FRAG_CLASS = '''\

# ── MarketDataStore ───────────────────────────────────────────────────────────

class MarketDataStore:
    """Fetch, validate, and persist OHLCV data for multiple tickers.

    Parameters
    ----------
    db_path  : str  SQLite file path.  Use a real file for persistence.
    fetch_fn : callable(ticker, period, interval) -> DataFrame | None
               None -> uses yfinance.  Gate injects a synthetic function.

    Methods
    -------
    fetch(ticker, period, interval)   -> pd.DataFrame  raw fetch, no store
    update(ticker, period, interval)  -> int           fetch + validate + store
    load(ticker)                      -> pd.DataFrame  from SQLite
    tickers()                         -> list[str]     known tickers (sorted)
    """

    def __init__(self, db_path=":memory:", fetch_fn=None):
        self._db       = db_path
        self._fetch_fn = fetch_fn
        self._tickers  = set()

    def fetch(self, ticker, period="1y", interval="1d"):
        """Fetch raw OHLCV without storing."""
        return fetch_ohlcv(
            ticker, period=period, interval=interval,
            fetch_fn=self._fetch_fn,
        )

    def update(self, ticker, period="1y", interval="1d"):
        """Fetch, validate, and store OHLCV. Returns rows stored."""
        df = self.fetch(ticker, period, interval)
        n  = store_ohlcv(df, ticker, self._db)
        self._tickers.add(ticker)
        return n

    def load(self, ticker):
        """Load stored OHLCV for ticker."""
        return load_ohlcv(ticker, self._db)

    def tickers(self):
        """Return sorted list of tickers seen by this store."""
        return sorted(self._tickers)
'''

DELIVERABLE = (
    _FRAG_DOC + _FRAG_IMPORTS + _FRAG_CONSTANTS
    + _FRAG_FETCH + _FRAG_VALIDATE + _FRAG_NORMALIZE
    + _FRAG_STORE + _FRAG_CLASS
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
import pandas as pd, math, sqlite3, tempfile, os

OHLCV_COLS = ["Open", "High", "Low", "Close", "Volume"]

def _synthetic(ticker="TEST", period="1y", interval="1d", n=50):
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

_P_VALIDATE = """\
def validate_ohlcv(df):
    if not isinstance(df, pd.DataFrame): return False, "not a DataFrame"
    missing = [c for c in OHLCV_COLS if c not in df.columns]
    if missing: return False, "missing columns: " + ", ".join(missing)
    if len(df) == 0: return False, "DataFrame is empty"
    valid = df.dropna(subset=["High", "Low"])
    if len(valid) > 0 and (valid["High"] < valid["Low"]).any():
        return False, "High < Low detected"
    return True, ""
"""

_P_NORMALIZE = """\
def normalize_ohlcv(df):
    df = df.copy()
    if not isinstance(df.index, pd.DatetimeIndex): df.index = pd.to_datetime(df.index)
    if df.index.tz is not None: df.index = df.index.tz_localize(None)
    return df[[c for c in OHLCV_COLS if c in df.columns]]
"""

_P_FETCH = """\
def fetch_ohlcv(ticker, period="1y", interval="1d", fetch_fn=None):
    if fetch_fn is not None: return fetch_fn(ticker, period, interval)
    import yfinance as yf
    df = yf.download(ticker, period=period, interval=interval, progress=False)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    return df
"""

_P_STORE = """\
def store_ohlcv(df, ticker, db_path=":memory:"):
    ok, reason = validate_ohlcv(df)
    if not ok: raise ValueError("Invalid OHLCV: " + reason)
    df = normalize_ohlcv(df)
    con = sqlite3.connect(db_path)
    try:
        con.execute("CREATE TABLE IF NOT EXISTS ohlcv (ticker TEXT NOT NULL, date TEXT NOT NULL, open REAL, high REAL, low REAL, close REAL, volume REAL, PRIMARY KEY (ticker, date))")
        rows = []
        for date, row in df.iterrows():
            d = str(date.date()) if hasattr(date, "date") else str(date)
            rows.append((ticker, d, float(row["Open"]), float(row["High"]),
                         float(row["Low"]), float(row["Close"]), float(row["Volume"])))
        con.executemany("INSERT OR REPLACE INTO ohlcv VALUES (?,?,?,?,?,?,?)", rows)
        con.commit(); return len(rows)
    finally: con.close()

def load_ohlcv(ticker, db_path=":memory:"):
    con = sqlite3.connect(db_path)
    try:
        try:
            rows = con.execute(
                "SELECT date, open, high, low, close, volume FROM ohlcv "
                "WHERE ticker=? ORDER BY date", (ticker,)).fetchall()
        except sqlite3.OperationalError:
            return pd.DataFrame(columns=OHLCV_COLS)
        if not rows: return pd.DataFrame(columns=OHLCV_COLS)
        df = pd.DataFrame(rows, columns=["date", "Open", "High", "Low", "Close", "Volume"])
        df.index = pd.to_datetime(df["date"]); df.index.name = None
        return df.drop(columns=["date"])
    finally: con.close()
"""

_P_CLASS = """\
class MarketDataStore:
    def __init__(self, db_path=":memory:", fetch_fn=None):
        self._db = db_path; self._fetch_fn = fetch_fn; self._tickers = set()
    def fetch(self, ticker, period="1y", interval="1d"):
        return fetch_ohlcv(ticker, period=period, interval=interval, fetch_fn=self._fetch_fn)
    def update(self, ticker, period="1y", interval="1d"):
        df = self.fetch(ticker, period, interval)
        n = store_ohlcv(df, ticker, self._db); self._tickers.add(ticker); return n
    def load(self, ticker): return load_ohlcv(ticker, self._db)
    def tickers(self): return sorted(self._tickers)
"""

# ══════════════════════════════════════════════════════════════════════════════
# Exercise notebooks
# ══════════════════════════════════════════════════════════════════════════════

_EX1 = _nb([
    _md("# Exercise 1 — The OHLCV Format\n\n"
        "OHLCV (Open, High, Low, Close, Volume) is the universal format for "
        "price data. Each row is one time period — a day, hour, or minute. "
        "Understanding this structure is the foundation for everything in "
        "Section 7: indicators, backtesting, and trading signals."),
    _code(_P_BASE + """\

# ── Exercise: implement make_ohlcv ────────────────────────────────────────────
# Build a synthetic OHLCV DataFrame following these rules:
#   Index  : pd.DatetimeIndex of n business days starting 2023-01-01
#   Close  : sine-wave starting at 100 with ±30% amplitude
#             100.0 * (1 + 0.3 * sin(i * 2π / n)) for row i
#   Open   : previous row's Close; first row = first Close
#   High   : Close * 1.01  (1% above close)
#   Low    : Close * 0.99  (1% below close)
#   Volume : 1_000_000 + i * 1_000 for row i

def make_ohlcv(n=20):
    \"\"\"Build a synthetic OHLCV DataFrame with n rows.

    Args:
        n: number of trading-day rows

    Returns:
        pd.DataFrame with DatetimeIndex and columns Open, High, Low, Close, Volume
    \"\"\"
    # TODO: compute prices using math.sin, build close Series with DatetimeIndex,
    # then construct the DataFrame with the five rules above.
    dates = pd.date_range("2023-01-01", periods=n, freq="B")
    return pd.DataFrame({
        "Open":   [100.0] * n,
        "High":   [101.0] * n,
        "Low":    [99.0]  * n,
        "Close":  [100.0] * n,
        "Volume": [1_000_000] * n,
    }, index=dates)
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — returns a DataFrame with the 5 required columns
try:
    df = make_ohlcv(30)
    assert isinstance(df, pd.DataFrame)
    assert set(OHLCV_COLS).issubset(set(df.columns)), f"missing: {set(OHLCV_COLS) - set(df.columns)}"
    checks += 1; print("✅ 1 make_ohlcv returns DataFrame with correct columns")
except Exception as e:
    print("❌ 1:", e)

# 2 — index is DatetimeIndex with exactly n rows
try:
    df = make_ohlcv(30)
    assert isinstance(df.index, pd.DatetimeIndex), "index is not DatetimeIndex"
    assert len(df) == 30, f"expected 30 rows, got {len(df)}"
    checks += 1; print("✅ 2 DatetimeIndex with correct length")
except Exception as e:
    print("❌ 2:", e)

# 3 — High >= Close >= Low for every row
try:
    df = make_ohlcv(50)
    assert (df["High"] >= df["Close"]).all(), "High < Close in some rows"
    assert (df["Close"] >= df["Low"]).all(),  "Close < Low in some rows"
    checks += 1; print("✅ 3 High >= Close >= Low for all rows")
except Exception as e:
    print("❌ 3:", e)

# 4 — Volume increases by exactly 1000 per row
try:
    df = make_ohlcv(10)
    vol   = df["Volume"].tolist()
    diffs = [vol[i + 1] - vol[i] for i in range(len(vol) - 1)]
    assert all(abs(d - 1000) < 1e-6 for d in diffs), f"diffs={diffs}"
    checks += 1; print("✅ 4 Volume increases by 1000 per row")
except Exception as e:
    print("❌ 4:", e)

# 5 — Open equals previous Close (lag-1 relationship)
try:
    df = make_ohlcv(30)
    for i in range(1, len(df)):
        diff = abs(df["Open"].iloc[i] - df["Close"].iloc[i - 1])
        assert diff < 1e-9, f"row {i}: Open={df['Open'].iloc[i]}, prev Close={df['Close'].iloc[i-1]}"
    checks += 1; print("✅ 5 Open equals previous Close (lag-1 relationship)")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX2 = _nb([
    _md("# Exercise 2 — validate_ohlcv\n\n"
        "Before trusting any market data, validate it. `validate_ohlcv` checks "
        "four things: it's a DataFrame, it has all five OHLCV columns, it's not "
        "empty, and High is never below Low. It returns `(True, \"\")` on success "
        "or `(False, reason)` on failure — never raises."),
    _code(_P_BASE + """\

# ── Exercise: implement validate_ohlcv ───────────────────────────────────────

def validate_ohlcv(df):
    \"\"\"Validate that df is a well-formed OHLCV DataFrame.

    Checks (in order):
      1. df is a pd.DataFrame
      2. All five OHLCV_COLS are present
      3. df has at least one row
      4. High >= Low for every non-NaN row

    Returns:
        (True, "")  if all checks pass
        (False, reason_string)  on first failure
    Never raises.
    \"\"\"
    # TODO:
    # 1. if not isinstance(df, pd.DataFrame): return False, "not a DataFrame"
    # 2. find missing = [c for c in OHLCV_COLS if c not in df.columns]
    #    if missing: return False, "missing columns: " + ", ".join(missing)
    # 3. if len(df) == 0: return False, "DataFrame is empty"
    # 4. valid = df.dropna(subset=["High", "Low"])
    #    if len(valid) > 0 and (valid["High"] < valid["Low"]).any():
    #        return False, "High < Low detected"
    # 5. return True, ""
    return True, ""
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — valid synthetic data returns (True, "")
try:
    df = _synthetic()
    ok, reason = validate_ohlcv(df)
    assert ok, f"expected ok=True, got reason={reason!r}"
    assert reason == ""
    checks += 1; print("✅ 1 valid OHLCV returns (True, '')")
except Exception as e:
    print("❌ 1:", e)

# 2 — missing column returns (False, reason mentioning the column)
try:
    df_bad = _synthetic().drop(columns=["Volume"])
    ok, reason = validate_ohlcv(df_bad)
    assert not ok, "expected ok=False for missing Volume"
    assert "Volume" in reason, f"reason should mention 'Volume': {reason!r}"
    checks += 1; print("✅ 2 missing column returns (False, reason)")
except Exception as e:
    print("❌ 2:", e)

# 3 — empty DataFrame returns (False, reason)
try:
    df_empty = pd.DataFrame(columns=OHLCV_COLS)
    ok, reason = validate_ohlcv(df_empty)
    assert not ok, "expected ok=False for empty DataFrame"
    checks += 1; print("✅ 3 empty DataFrame returns (False, reason)")
except Exception as e:
    print("❌ 3:", e)

# 4 — High < Low returns (False, reason)
try:
    df_inv = _synthetic().copy()
    df_inv.loc[df_inv.index[5], "High"] = df_inv["Low"].iloc[5] - 1.0
    ok, reason = validate_ohlcv(df_inv)
    assert not ok, "expected ok=False when High < Low"
    assert "High" in reason or "Low" in reason or "detected" in reason
    checks += 1; print("✅ 4 High < Low returns (False, reason)")
except Exception as e:
    print("❌ 4:", e)

# 5 — non-DataFrame returns (False, reason); never raises
try:
    for bad in ["string", 42, None, [1, 2, 3]]:
        ok, reason = validate_ohlcv(bad)
        assert not ok, f"expected ok=False for {type(bad).__name__}"
    checks += 1; print("✅ 5 non-DataFrame inputs return (False, reason), never raise")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX3 = _nb([
    _md("# Exercise 3 — fetch_ohlcv and normalize_ohlcv\n\n"
        "`fetch_ohlcv` is the injectable wrapper around yfinance. Passing "
        "`fetch_fn` replaces the real API call — essential for gate testing. "
        "`normalize_ohlcv` strips any timezone information and keeps only the "
        "five standard columns, returning a clean copy."),
    _code(_P_BASE + _P_VALIDATE + """\

# ── Exercise: implement fetch_ohlcv and normalize_ohlcv ──────────────────────

def fetch_ohlcv(ticker, period="1y", interval="1d", fetch_fn=None):
    \"\"\"Fetch OHLCV data for ticker.

    Args:
        ticker   : stock symbol, e.g. "AAPL"
        period   : data range, e.g. "1y", "6mo"
        interval : bar size, e.g. "1d", "1h"
        fetch_fn : callable(ticker, period, interval) -> DataFrame, or None.
                   None -> calls yfinance.

    Returns:
        pd.DataFrame with columns Open, High, Low, Close, Volume
    \"\"\"
    # TODO:
    # 1. if fetch_fn is not None: return fetch_fn(ticker, period, interval)
    # 2. import yfinance as yf
    # 3. df = yf.download(ticker, period=period, interval=interval, progress=False)
    # 4. handle MultiIndex columns: if isinstance(df.columns, pd.MultiIndex):
    #        df.columns = df.columns.get_level_values(0)
    # 5. return df
    if fetch_fn is not None:
        return fetch_fn(ticker, period, interval)
    return _synthetic(ticker, period, interval)  # stub: removes when yfinance added


def normalize_ohlcv(df):
    \"\"\"Return a copy of df with a tz-naive DatetimeIndex and only OHLCV_COLS.

    Steps:
      1. df = df.copy()
      2. If index is not DatetimeIndex: convert with pd.to_datetime
      3. If index has timezone info: strip it with tz_localize(None)
      4. Keep only columns that appear in OHLCV_COLS (in order)
    \"\"\"
    # TODO: implement the four steps above
    return df.copy()
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — fetch_ohlcv with fetch_fn injection returns the injected result
try:
    df = fetch_ohlcv("TEST", fetch_fn=_synthetic)
    assert isinstance(df, pd.DataFrame)
    assert "Close" in df.columns
    assert len(df) == 50
    checks += 1; print("✅ 1 fetch_fn injection returns injected result")
except Exception as e:
    print("❌ 1:", e)

# 2 — fetch_ohlcv passes ticker/period/interval to fetch_fn correctly
try:
    calls = []
    def _capturing(ticker, period, interval):
        calls.append((ticker, period, interval))
        return _synthetic()
    fetch_ohlcv("AAPL", period="6mo", interval="1d", fetch_fn=_capturing)
    assert calls == [("AAPL", "6mo", "1d")], f"unexpected calls: {calls}"
    checks += 1; print("✅ 2 fetch_fn receives correct ticker, period, interval")
except Exception as e:
    print("❌ 2:", e)

# 3 — normalize_ohlcv strips timezone from DatetimeIndex
try:
    df = _synthetic()
    df_tz = df.copy()
    df_tz.index = df_tz.index.tz_localize("UTC")
    normed = normalize_ohlcv(df_tz)
    assert normed.index.tz is None, f"timezone not stripped: {normed.index.tz}"
    checks += 1; print("✅ 3 normalize_ohlcv strips timezone")
except Exception as e:
    print("❌ 3:", e)

# 4 — normalize_ohlcv keeps only the 5 OHLCV_COLS
try:
    df = _synthetic()
    df["ExtraCol"] = 999
    normed = normalize_ohlcv(df)
    assert list(normed.columns) == OHLCV_COLS, f"columns: {list(normed.columns)}"
    checks += 1; print("✅ 4 normalize_ohlcv keeps only OHLCV_COLS in order")
except Exception as e:
    print("❌ 4:", e)

# 5 — normalize_ohlcv returns a copy (does not mutate input)
try:
    df = _synthetic()
    df_tz = df.copy()
    df_tz.index = df_tz.index.tz_localize("UTC")
    _ = normalize_ohlcv(df_tz)
    assert df_tz.index.tz is not None, "input was mutated!"
    checks += 1; print("✅ 5 normalize_ohlcv does not mutate the input DataFrame")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX4 = _nb([
    _md("# Exercise 4 — store_ohlcv and load_ohlcv\n\n"
        "`store_ohlcv` persists a validated, normalized DataFrame to SQLite. "
        "`load_ohlcv` reads it back. The `db_path` parameter must be a real file "
        "path for round-trip persistence — each `sqlite3.connect(':memory:')` "
        "opens a different in-memory database."),
    _code(_P_BASE + _P_VALIDATE + _P_NORMALIZE + _P_FETCH + """\

# ── Exercise: implement store_ohlcv and load_ohlcv ───────────────────────────

def store_ohlcv(df, ticker, db_path=":memory:"):
    \"\"\"Validate, normalize, and persist OHLCV data to SQLite.

    Table schema: ohlcv(ticker, date, open, high, low, close, volume)
    Primary key : (ticker, date) — INSERT OR REPLACE handles updates.

    Args:
        df      : pd.DataFrame with OHLCV columns
        ticker  : str, e.g. "AAPL"
        db_path : SQLite file path; use a real file for persistence.

    Returns:
        int — number of rows stored

    Raises:
        ValueError if validate_ohlcv(df) fails
    \"\"\"
    # TODO:
    # 1. ok, reason = validate_ohlcv(df); if not ok: raise ValueError(...)
    # 2. df = normalize_ohlcv(df)
    # 3. con = sqlite3.connect(db_path)
    # 4. con.execute("CREATE TABLE IF NOT EXISTS ohlcv (...)")
    # 5. for date, row in df.iterrows(): build rows list
    # 6. con.executemany("INSERT OR REPLACE INTO ohlcv VALUES (?,?,?,?,?,?,?)", rows)
    # 7. con.commit(); con.close(); return len(rows)
    return 0


def load_ohlcv(ticker, db_path=":memory:"):
    \"\"\"Load stored OHLCV data for ticker from SQLite.

    Returns:
        pd.DataFrame with DatetimeIndex and columns Open, High, Low, Close, Volume.
        Empty DataFrame (columns = OHLCV_COLS) if ticker not found.
    \"\"\"
    # TODO:
    # 1. con = sqlite3.connect(db_path)
    # 2. rows = con.execute("SELECT date, open, high, low, close, volume
    #                        FROM ohlcv WHERE ticker=? ORDER BY date", (ticker,)).fetchall()
    # 3. catch sqlite3.OperationalError -> return empty DataFrame
    # 4. if not rows: return empty DataFrame
    # 5. build DataFrame, set index to pd.to_datetime("date" column), drop "date" col
    # 6. return df
    return pd.DataFrame(columns=OHLCV_COLS)
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — store_ohlcv raises ValueError for invalid data
try:
    try:
        store_ohlcv(pd.DataFrame(), "TEST")
        print("❌ 1: should have raised ValueError")
    except ValueError as ve:
        checks += 1; print("✅ 1 store_ohlcv raises ValueError for invalid data")
except Exception as e:
    print("❌ 1:", e)

# 2 — store_ohlcv returns the correct row count
try:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        _db2 = f.name
    try:
        df = _synthetic()
        n = store_ohlcv(df, "TEST", _db2)
        assert n == 50, f"expected 50 rows, got {n}"
        checks += 1; print("✅ 2 store_ohlcv returns correct row count")
    finally:
        os.unlink(_db2)
except Exception as e:
    print("❌ 2:", e)

# 3 — round-trip: stored data loads back correctly
try:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        _db3 = f.name
    try:
        df = _synthetic()
        store_ohlcv(df, "AAPL", _db3)
        loaded = load_ohlcv("AAPL", _db3)
        assert len(loaded) == 50, f"expected 50 rows, got {len(loaded)}"
        assert isinstance(loaded.index, pd.DatetimeIndex)
        assert "Close" in loaded.columns
        assert abs(round(loaded["Close"].iloc[0], 4) - round(df["Close"].iloc[0], 4)) < 1e-4
        checks += 1; print("✅ 3 round-trip: store then load produces matching data")
    finally:
        os.unlink(_db3)
except Exception as e:
    print("❌ 3:", e)

# 4 — multiple tickers stored and loaded independently
try:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        _db4 = f.name
    try:
        df = _synthetic()
        store_ohlcv(df, "AAPL", _db4)
        store_ohlcv(df, "MSFT", _db4)
        aapl = load_ohlcv("AAPL", _db4)
        msft = load_ohlcv("MSFT", _db4)
        assert len(aapl) == 50 and len(msft) == 50
        checks += 1; print("✅ 4 multiple tickers stored and loaded independently")
    finally:
        os.unlink(_db4)
except Exception as e:
    print("❌ 4:", e)

# 5 — load for non-existent ticker returns empty DataFrame
try:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        _db5 = f.name
    try:
        empty = load_ohlcv("NOTEXIST", _db5)
        assert isinstance(empty, pd.DataFrame)
        assert len(empty) == 0
        assert set(empty.columns) == set(OHLCV_COLS)
        checks += 1; print("✅ 5 load for missing ticker returns empty DataFrame")
    finally:
        os.unlink(_db5)
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX5 = _nb([
    _md("# Exercise 5 — MarketDataStore\n\n"
        "`MarketDataStore` ties everything together: it fetches, validates, "
        "stores, and serves OHLCV data for multiple tickers through a clean "
        "four-method interface. The `fetch_fn` injection keeps the gate "
        "deterministic — pass `_synthetic` to avoid live API calls."),
    _code(_P_BASE + _P_VALIDATE + _P_NORMALIZE + _P_FETCH + _P_STORE + """\

# ── Exercise: implement MarketDataStore ──────────────────────────────────────

class MarketDataStore:
    \"\"\"Fetch, validate, and persist OHLCV data for multiple tickers.

    Args:
        db_path  : SQLite file path.
        fetch_fn : callable(ticker, period, interval) -> DataFrame, or None.

    Methods:
        fetch(ticker, period, interval)   -> pd.DataFrame  raw, no store
        update(ticker, period, interval)  -> int           fetch + store
        load(ticker)                      -> pd.DataFrame  from SQLite
        tickers()                         -> list[str]     sorted, seen
    \"\"\"

    def __init__(self, db_path=":memory:", fetch_fn=None):
        # TODO: store db_path, fetch_fn, and a set for seen tickers
        self._db       = db_path
        self._fetch_fn = fetch_fn
        self._tickers  = set()

    def fetch(self, ticker, period="1y", interval="1d"):
        # TODO: call fetch_ohlcv(ticker, period, interval, fetch_fn=self._fetch_fn)
        return fetch_ohlcv(ticker, period=period, interval=interval, fetch_fn=self._fetch_fn)

    def update(self, ticker, period="1y", interval="1d"):
        # TODO: fetch + store_ohlcv(df, ticker, self._db) + add ticker to set + return n
        return 0

    def load(self, ticker):
        # TODO: return load_ohlcv(ticker, self._db)
        return pd.DataFrame(columns=OHLCV_COLS)

    def tickers(self):
        # TODO: return sorted(self._tickers)
        return []
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — update() fetches and stores data, returns row count
try:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        _db1 = f.name
    try:
        store = MarketDataStore(db_path=_db1, fetch_fn=_synthetic)
        n = store.update("AAPL")
        assert n == 50, f"expected 50, got {n}"
        checks += 1; print("✅ 1 update() stores data and returns row count")
    finally:
        os.unlink(_db1)
except Exception as e:
    print("❌ 1:", e)

# 2 — load() returns stored data with DatetimeIndex
try:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        _db2 = f.name
    try:
        store = MarketDataStore(db_path=_db2, fetch_fn=_synthetic)
        store.update("AAPL")
        df = store.load("AAPL")
        assert len(df) == 50
        assert isinstance(df.index, pd.DatetimeIndex)
        assert "Close" in df.columns
        checks += 1; print("✅ 2 load() returns stored data with DatetimeIndex")
    finally:
        os.unlink(_db2)
except Exception as e:
    print("❌ 2:", e)

# 3 — tickers() returns sorted list of updated tickers
try:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        _db3 = f.name
    try:
        store = MarketDataStore(db_path=_db3, fetch_fn=_synthetic)
        store.update("MSFT"); store.update("AAPL"); store.update("GOOG")
        t = store.tickers()
        assert t == sorted(t), f"not sorted: {t}"
        assert "AAPL" in t and "MSFT" in t and "GOOG" in t
        checks += 1; print("✅ 3 tickers() returns sorted list of updated tickers")
    finally:
        os.unlink(_db3)
except Exception as e:
    print("❌ 3:", e)

# 4 — load() for missing ticker returns empty DataFrame
try:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        _db4 = f.name
    try:
        store = MarketDataStore(db_path=_db4, fetch_fn=_synthetic)
        empty = store.load("NOTEXIST")
        assert isinstance(empty, pd.DataFrame) and len(empty) == 0
        checks += 1; print("✅ 4 load() for missing ticker returns empty DataFrame")
    finally:
        os.unlink(_db4)
except Exception as e:
    print("❌ 4:", e)

# 5 — fetch() uses the injected fetch_fn and does NOT store
try:
    calls = []
    def _tracking(ticker, period, interval):
        calls.append(ticker); return _synthetic()
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        _db5 = f.name
    try:
        store = MarketDataStore(db_path=_db5, fetch_fn=_tracking)
        df = store.fetch("AAPL")
        assert "AAPL" in calls
        still_empty = store.load("AAPL")
        assert len(still_empty) == 0, "fetch() should not store data"
        checks += 1; print("✅ 5 fetch() uses fetch_fn and does not persist data")
    finally:
        os.unlink(_db5)
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
day: "089"
lesson: 1
title: "What Is OHLCV?"
slides:
  - type: title
    heading: "Financial Data"
    subheading: "Section 7 begins — OHLCV, yfinance, and market data pipelines"
    narration: >
      Welcome to Section 7: Finance, Trading, and Productizing. Over the next
      twelve days you will build a complete financial data pipeline, implement
      technical indicators, backtest a trading strategy, add AI-driven signals,
      and wrap everything into a paper-trading bot. Today is the foundation:
      understanding market data and building the tools to fetch, validate, and
      store it reliably.

  - type: concept
    label: "OHLCV"
    heading: "The Universal Price Format"
    body: >
      Every candlestick chart you have ever seen is built from OHLCV data.
    bullets:
      - "Open: price at the start of the period"
      - "High: highest price reached during the period"
      - "Low:  lowest price reached during the period"
      - "Close: price at the end of the period"
      - "Volume: number of shares or contracts traded"
    narration: >
      OHLCV stands for Open, High, Low, Close, Volume. These five numbers
      describe everything that happened in a given time period — a day, an hour,
      or a minute. Open and Close tell you where the price started and ended.
      High and Low tell you the range. Volume tells you how many people
      participated. Every major data source — yfinance, Alpaca, Interactive
      Brokers, Binance — returns data in this format, so learning it once
      transfers everywhere.

  - type: concept
    label: "Why it matters"
    heading: "Why Engineers Work With Market Data"
    body: >
      Market data is the raw material for a whole class of AI applications.
    bullets:
      - "Backtesting: test a strategy on historical prices before risking money"
      - "Technical signals: compute RSI, MACD, Bollinger Bands from OHLCV"
      - "AI signals: feed price patterns to an LLM for market commentary"
      - "Paper trading: simulate live trading on real data without real money"
      - "Portfolio analytics: track returns, drawdown, Sharpe ratio"
    narration: >
      You already know all the engineering tools you need for this section.
      Pandas DataFrames, rolling windows from Day 46, SQLite from Day 42, API
      patterns from Day 22, scheduling from Day 27, agent patterns from
      Section 6 — all of these reappear in the next twelve days, applied to
      a new domain. The domain is finance, but the skills are the same.

  - type: code
    label: "OHLCV structure"
    heading: "What an OHLCV DataFrame Looks Like"
    body: >
      A 5-row slice of daily AAPL data.
    code: |
      import pandas as pd

      #            Open    High     Low   Close     Volume
      # 2024-01-02  185.0  188.0  184.5  185.9  84_000_000
      # 2024-01-03  184.0  186.5  182.0  184.3  79_000_000
      # 2024-01-04  183.5  185.0  181.0  182.9  72_000_000

      df.index   # DatetimeIndex — tz-naive, one row per trading day
      df.dtypes  # float64 for OHLC; float64 or int64 for Volume
      df["High"].max()   # highest intraday price over the period
      df["Close"].pct_change()  # daily return series
    narration: >
      The DataFrame index is a DatetimeIndex — dates, not integers. There is no
      Saturday or Sunday: stock markets are closed on weekends, so business-day
      frequency produces the right gaps automatically. The five columns are
      always capitalised exactly this way: Open, High, Low, Close, Volume.
      You will see these exact column names throughout Section 7, so get used
      to them now.

  - type: exercise
    heading: "Exercise 1 — Build a Synthetic OHLCV DataFrame"
    prompt: >
      Implement make_ohlcv(n) that builds a synthetic DataFrame with n rows.
      The index is n business days from 2023-01-01. Close follows a sine wave.
      Open is the previous row's Close. High is Close * 1.01. Low is Close *
      0.99. Volume is 1_000_000 + i * 1_000 for row i.
    hint: >
      Use math.sin with period n. Build close as a pd.Series with a
      DatetimeIndex. Then open = close.shift(1).fillna(close.iloc[0]).
    narration: >
      Rather than hitting the internet in the gate, we build synthetic data by
      hand. A sine wave gives us realistic price variation — prices go up and
      down — without randomness. You will use this same synthetic function as
      the injected fetch_fn for every gate in Section 7.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "OHLCV: Open / High / Low / Close / Volume — the universal price format"
      - "DatetimeIndex with business-day frequency — no weekends"
      - "The five column names are always capitalised exactly this way"
      - "Synthetic data injected via fetch_fn — keeps the gate offline"
      - "Next: validate_ohlcv — never trust incoming data"
    narration: >
      The OHLCV format is the foundation. Every indicator, every backtest,
      every trading signal in Section 7 starts with a DataFrame that looks
      exactly like what you built in Exercise 1. Next lesson: before you do
      anything with that DataFrame, validate it.
""",

    """\
day: "089"
lesson: 2
title: "Validating Market Data"
slides:
  - type: title
    heading: "Validating Market Data"
    subheading: "validate_ohlcv — trust but verify"
    narration: >
      Data quality is the unglamorous part of financial engineering. yfinance
      can return missing columns on certain tickers. Intraday data can have
      inverted High and Low. Gaps in the calendar leave NaN rows. An invalid
      DataFrame fed into a rolling average or a backtest produces wrong numbers
      silently. Today's lesson: write a validator that catches these problems
      before they propagate.

  - type: concept
    label: "What can go wrong"
    heading: "Four Things That Go Wrong With Market Data"
    body: >
      Each is common enough to check explicitly.
    bullets:
      - "Not a DataFrame: someone passed a dict or a list by mistake"
      - "Missing columns: the API returned fewer columns than expected"
      - "Empty DataFrame: the ticker had no data in the requested period"
      - "Inverted prices: High < Low — a data-provider bug, not a market event"
    narration: >
      The inverted High/Low case is subtle. It happens with bad data feeds and
      with adjusted closing prices that have been improperly scaled. If your
      indicator uses High and Low (Bollinger Bands, ATR, stochastic), an
      inversion will produce NaN or nonsense. Catching it at the boundary —
      in validate_ohlcv — means the rest of your code never has to handle it.

  - type: code
    label: "validate_ohlcv"
    heading: "The Validator in Full"
    body: >
      Four checks, (bool, str) return, never raises.
    code: |
      def validate_ohlcv(df):
          if not isinstance(df, pd.DataFrame):
              return False, "not a DataFrame"
          missing = [c for c in OHLCV_COLS if c not in df.columns]
          if missing:
              return False, "missing columns: " + ", ".join(missing)
          if len(df) == 0:
              return False, "DataFrame is empty"
          valid_rows = df.dropna(subset=["High", "Low"])
          if len(valid_rows) > 0 and (valid_rows["High"] < valid_rows["Low"]).any():
              return False, "High < Low detected"
          return True, ""
    narration: >
      Notice the return type: a tuple of boolean and a reason string, never a
      bare boolean and never an exception. This pattern — ok, reason equals
      validate of something — appears throughout Section 6 in the guardrails
      module and throughout Section 7 in the data pipeline. It makes the
      caller decide what to do on failure: log it, raise, skip, or retry.
      The validator's only job is to check and report.

  - type: concept
    label: "Boundary validation"
    heading: "Validate at the Boundary"
    body: >
      Call validate_ohlcv once, at the point where data enters your system.
    bullets:
      - "At the output of fetch_ohlcv — before storing to SQLite"
      - "At the input of store_ohlcv — last chance before persistence"
      - "Never inside indicators or backtesting — trust your own pipeline"
      - "Return (False, reason) from validators — let callers decide on failure"
      - "dropna before checking High < Low — NaN rows are handled separately"
    narration: >
      The boundary-validation principle means you validate data exactly once,
      at the point it enters your system from an external source. Inside your
      own code, once data has passed validation, trust it. Don't add
      isinstance checks inside rolling() calls. Don't re-validate in the
      backtest loop. Validate at the boundary; trust within.

  - type: exercise
    heading: "Exercise 2 — Implement validate_ohlcv"
    prompt: >
      Implement validate_ohlcv(df) that returns (True, "") for valid OHLCV
      data and (False, reason_string) for invalid data. Check: is it a
      DataFrame? Are all 5 OHLCV_COLS present? Is it non-empty? Is High >=
      Low for all non-NaN rows? Never raise.
    hint: >
      Use df.dropna(subset=["High", "Low"]) before the High/Low check so NaN
      rows don't produce false positives. Test each condition in order and
      return immediately on the first failure.
    narration: >
      The checks in this exercise are deliberately simple — each is one line
      of pandas. The real skill is the architecture: checking in the right
      order, returning immediately on failure, and never raising an exception.
      Future days will call validate_ohlcv inside store_ohlcv and inside the
      MarketDataStore, so correctness here pays forward.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "Four things to check: type, columns, length, High >= Low"
      - "(bool, str) return pattern — caller decides what failure means"
      - "dropna before High/Low check — NaN is not an inversion"
      - "Validate once at the boundary; trust your own pipeline"
      - "Next: fetch_ohlcv — the injectable yfinance wrapper"
    narration: >
      Validation is one of those things that pays off silently. When your
      pipeline never crashes on bad data, you don't notice the validator
      working. You only notice it's missing when a NaN propagates through
      fifteen calculations and you spend two hours finding where it came from.
      Next lesson: the fetch wrapper.
""",

    """\
day: "089"
lesson: 3
title: "Fetching and Normalizing"
slides:
  - type: title
    heading: "Fetching and Normalizing"
    subheading: "fetch_ohlcv, normalize_ohlcv, and the inject pattern"
    narration: >
      The inject pattern is the most important architectural decision in
      Section 7. Every function that touches external data accepts a fetch_fn
      parameter. When fetch_fn is None, it calls yfinance. When fetch_fn is
      provided, it calls that instead. The gate always provides a synthetic
      function — so no test ever touches the internet. Today you implement
      this pattern and the normalize function that cleans up timezone
      information.

  - type: concept
    label: "yfinance"
    heading: "yfinance: Free Market Data in One Line"
    body: >
      yfinance wraps Yahoo Finance's API. One function call, a DataFrame back.
    bullets:
      - "pip install yfinance — already installed in ai-course"
      - "yf.download(ticker, period, interval) -> DataFrame"
      - "period: '1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'"
      - "interval: '1m', '5m', '15m', '1h', '1d', '1wk', '1mo'"
      - "Returns tz-aware DatetimeIndex for intraday; tz-naive for daily"
    narration: >
      yfinance is free and covers most use cases — stocks, ETFs, crypto,
      futures, and indices. You do not need an API key. The limitation is rate
      limiting: it's not suitable for high-frequency production use. For
      learning, backtesting, and building prototypes, it's more than enough.
      One gotcha: sometimes it returns a MultiIndex column when you download
      multiple tickers at once. Always handle that case.

  - type: code
    label: "fetch_ohlcv"
    heading: "The Injectable Fetch Wrapper"
    body: >
      One parameter makes the whole pipeline testable.
    code: |
      def fetch_ohlcv(ticker, period="1y", interval="1d", fetch_fn=None):
          if fetch_fn is not None:
              return fetch_fn(ticker, period, interval)
          import yfinance as yf
          df = yf.download(ticker, period=period, interval=interval,
                           progress=False)
          if isinstance(df.columns, pd.MultiIndex):
              df.columns = df.columns.get_level_values(0)
          return df

      # Production: hits the internet
      df = fetch_ohlcv("AAPL", period="1y")

      # Gate-safe: uses synthetic data, zero internet
      df = fetch_ohlcv("AAPL", period="1y", fetch_fn=_synthetic_ohlcv)
    narration: >
      The lazy import — import yfinance inside the else branch — means the
      module loads even if yfinance is not installed. This matters in testing
      environments. The MultiIndex handling catches the case where yfinance
      returns a two-level column when you download multiple tickers in one
      call. For single-ticker downloads it's a no-op; for multi-ticker it
      flattens the column names.

  - type: concept
    label: "normalize_ohlcv"
    heading: "Normalizing: Strip Timezone, Keep 5 Columns"
    body: >
      Normalize immediately after fetch, before validate or store.
    bullets:
      - "df.copy() — never mutate the caller's DataFrame"
      - "Strip tz: df.index.tz_localize(None) if tz-aware"
      - "Keep only OHLCV_COLS: df[[c for c in OHLCV_COLS if c in df.columns]]"
      - "This drops 'Adj Close' and any other extra columns yfinance adds"
      - "After normalize, the DataFrame is uniform regardless of source"
    narration: >
      yfinance sometimes returns a tz-aware DatetimeIndex for daily data —
      timezone UTC — and sometimes tz-naive. Downstream code that expects
      tz-naive will crash on tz-aware. Normalizing strips this inconsistency
      at the boundary. Similarly, yfinance returns 'Adj Close' in addition to
      the five standard columns. Normalize removes it. After normalize, every
      DataFrame in your pipeline has the same shape.

  - type: exercise
    heading: "Exercise 3 — Implement fetch_ohlcv and normalize_ohlcv"
    prompt: >
      Implement fetch_ohlcv(ticker, period, interval, fetch_fn=None) with
      the injection pattern. Implement normalize_ohlcv(df) that strips
      timezone, converts the index to DatetimeIndex if needed, and returns
      only OHLCV_COLS. Both functions return a copy — neither mutates the
      input.
    hint: >
      For normalize: check df.index.tz is not None before tz_localize(None).
      tz_localize(None) on a tz-naive index raises a TypeError.
      For fetch: the lazy yfinance import goes inside the else branch.
    narration: >
      These two functions are the input stage of your data pipeline. Every
      day in Section 7 that needs market data calls fetch_ohlcv with an
      injected function, then normalize_ohlcv, then validate_ohlcv. Writing
      them correctly here means they work correctly everywhere.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "fetch_ohlcv: inject pattern replaces yfinance for gate safety"
      - "Lazy import: import yfinance inside else branch"
      - "MultiIndex columns: flatten with df.columns.get_level_values(0)"
      - "normalize_ohlcv: tz-strip + column filter + copy"
      - "Next: store_ohlcv and load_ohlcv — SQLite persistence"
    narration: >
      The inject pattern is a transferable skill. Anywhere you call an
      external API — yfinance, Stripe, a REST endpoint, a database — wrapping
      it in a function that accepts a mock_fn parameter makes your code
      trivially testable. You already used this pattern in Section 6 with
      llm_fn. In Section 7 it's fetch_fn. The idea is the same.
""",

    """\
day: "089"
lesson: 4
title: "Storing Market Data"
slides:
  - type: title
    heading: "Storing Market Data"
    subheading: "store_ohlcv, load_ohlcv, and SQLite as a data store"
    narration: >
      Fetching data every time is slow and fragile. The market is closed on
      weekends and after hours. If your script fetches on startup and yfinance
      is rate-limited, your whole pipeline fails. Storing data locally in
      SQLite solves all of this: fetch once, query many times. SQLite is
      already in Python's standard library, it needs no server, and it handles
      millions of rows easily for a personal finance project.

  - type: concept
    label: "SQLite for time series"
    heading: "Why SQLite Works for Market Data"
    body: >
      SQLite handles the scale you need and nothing more.
    bullets:
      - "Single file, zero config — perfect for local data science"
      - "PRIMARY KEY (ticker, date) — upsert with INSERT OR REPLACE"
      - "Order by date — time series queries are natural"
      - "Handles 10 years of daily data for 50 tickers in under 50 MB"
      - "Scale up to Postgres/TimescaleDB later — same SQL"
    narration: >
      You already know SQLite from Day 42. The only new pattern here is the
      compound primary key: ticker and date together. This lets you store
      data for hundreds of tickers in one file without confusion. And INSERT
      OR REPLACE means you can re-run your fetch pipeline without getting
      duplicate rows — it updates in place if the row already exists.

  - type: code
    label: "store + load"
    heading: "store_ohlcv and load_ohlcv"
    body: >
      Persist and retrieve one ticker at a time.
    code: |
      import tempfile, os

      # Create a real file — ':memory:' opens a NEW db each call
      with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
          db_path = f.name

      try:
          df = fetch_ohlcv("AAPL", fetch_fn=_synthetic_ohlcv)
          n  = store_ohlcv(df, "AAPL", db_path)   # 252 rows stored
          print(f"Stored {n} rows")

          loaded = load_ohlcv("AAPL", db_path)
          print(loaded.tail(3))
          # DatetimeIndex, columns Open/High/Low/Close/Volume

          empty = load_ohlcv("NOTEXIST", db_path)
          print(len(empty))   # 0
      finally:
          os.unlink(db_path)
    narration: >
      The most common mistake with SQLite and ':memory:' is assuming that two
      calls to sqlite3.connect(':memory:') share the same database. They do
      not. Each call opens a fresh, empty, in-process database. For round-trip
      testing — store then load — you must use a real file path. In exercises
      and tests, use tempfile.NamedTemporaryFile and always clean up in a
      finally block.

  - type: concept
    label: "Pitfalls"
    heading: "SQLite Pitfalls for Market Data"
    body: >
      Three issues to watch for.
    bullets:
      - "':memory:' is per-connection: always use a file for round-trips"
      - "Date storage: store as TEXT 'YYYY-MM-DD', ORDER BY works lexically"
      - "Float precision: float64 -> REAL -> float64 is lossless for prices"
      - "OperationalError on missing table: catch and return empty DataFrame"
      - "timezone in DatetimeIndex: normalize_ohlcv strips it before storing"
    narration: >
      Storing dates as 'YYYY-MM-DD' text works because ISO-8601 dates sort
      lexically in the same order as chronologically. So ORDER BY date gives
      you the rows in time order even though the column type is TEXT, not
      DATE. When you load, pd.to_datetime converts the text back to a proper
      DatetimeIndex. The OperationalError catch handles the case where you
      call load_ohlcv on a database that has never had store_ohlcv called —
      the table doesn't exist yet.

  - type: exercise
    heading: "Exercise 4 — Implement store_ohlcv and load_ohlcv"
    prompt: >
      Implement store_ohlcv(df, ticker, db_path) that validates, normalizes,
      and persists OHLCV data to SQLite. Returns the row count. Raises
      ValueError on invalid data. Implement load_ohlcv(ticker, db_path) that
      reads back the data with a DatetimeIndex, returning an empty DataFrame
      if the ticker is not found.
    hint: >
      Use tempfile.NamedTemporaryFile in your tests — ':memory:' won't
      round-trip. The table schema: ohlcv(ticker, date, open, high, low,
      close, volume) with PRIMARY KEY (ticker, date). Catch
      sqlite3.OperationalError for the missing-table case in load_ohlcv.
    narration: >
      The round-trip test is the most important check: store fifty rows, load
      them back, confirm the count and the index type. If that passes, the
      full pipeline works. If it fails, check whether you're using ':memory:'
      versus a real file path.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "SQLite compound primary key (ticker, date) — no duplicate rows"
      - "INSERT OR REPLACE — idempotent upsert"
      - "':memory:' is per-connection — use a real file for round-trips"
      - "Date as TEXT 'YYYY-MM-DD' — lexical sort equals chronological sort"
      - "Next: MarketDataStore — one class for the full pipeline"
    narration: >
      You now have all the pieces. fetch_ohlcv brings data in. validate_ohlcv
      checks it. normalize_ohlcv standardizes it. store_ohlcv persists it.
      load_ohlcv retrieves it. The last exercise ties all five into one class.
""",

    """\
day: "089"
lesson: 5
title: "The MarketDataStore"
slides:
  - type: title
    heading: "The MarketDataStore"
    subheading: "Integrating the pipeline — and a preview of Section 7"
    narration: >
      The MarketDataStore is the final piece of Day 89. It wraps all five
      functions — fetch, validate, normalize, store, load — into one object
      with a four-method interface. You hand it a database path and an optional
      fetch function; it handles the rest. This is the same class pattern from
      Section 4 and Section 6: bind at construction, delegate in methods.

  - type: concept
    label: "MarketDataStore"
    heading: "Four Methods, One Pipeline"
    body: >
      The class is a thin wrapper — the real work is in the module functions.
    bullets:
      - "fetch(ticker, period, interval) -> DataFrame — raw, no store"
      - "update(ticker, period, interval) -> int — fetch + validate + store"
      - "load(ticker) -> DataFrame — read from SQLite"
      - "tickers() -> list[str] — sorted list of updated tickers"
    narration: >
      Notice the distinction between fetch and update. fetch calls the API
      and returns the DataFrame — it's read-only with respect to the database.
      update calls fetch, then stores the result. This separation lets you
      inspect data before committing it, or fetch for analysis without
      persisting. The tickers() method returns the set of tickers that have
      been updated in this session — not necessarily all tickers in the
      database.

  - type: code
    label: "MarketDataStore usage"
    heading: "Building a Mini Portfolio Data Store"
    body: >
      Fetch and store data for three tickers in four lines.
    code: |
      import tempfile, os

      with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
          db_path = f.name

      store = MarketDataStore(db_path=db_path, fetch_fn=_synthetic_ohlcv)

      for ticker in ["AAPL", "MSFT", "GOOG"]:
          n = store.update(ticker)
          print(f"{ticker}: {n} rows stored")

      print(store.tickers())  # ['AAPL', 'GOOG', 'MSFT']

      aapl = store.load("AAPL")
      print(aapl["Close"].describe())

      os.unlink(db_path)
    narration: >
      This is the shape of every data pipeline in Section 7. You create a
      MarketDataStore once, call update for each ticker at startup, and then
      call load whenever you need the data. Days 90 through 96 will call
      store.load at the top of each exercise to get their input data.

  - type: concept
    label: "Section 7 preview"
    heading: "What the Next 11 Days Look Like"
    body: >
      Each day builds on market_data.py from today.
    bullets:
      - "Day 90: technical indicators — SMA, EMA, RSI, MACD, Bollinger Bands"
      - "Day 91: backtesting — simulate a strategy on historical data"
      - "Day 92: strategy signals — entry/exit rules from indicator combinations"
      - "Day 93: AI signals — LLM-based news sentiment as a trading signal"
      - "Day 94: risk management — position sizing, stop-loss, drawdown"
      - "Days 95–96: a paper-trading bot that runs it all live-ish"
      - "Days 97–100: productizing, landing page, portfolio, final capstone"
    narration: >
      The pipeline you built today — fetch, validate, normalize, store, load —
      is the input stage for every day that follows. In Day 90, you will add
      an indicators function that takes the DataFrame from store.load and
      returns the same DataFrame with additional columns for SMA, RSI, and
      MACD. In Day 91, the backtester will use that enriched DataFrame to
      simulate trades. By Day 96, a full paper-trading agent will be reading
      from the store and making decisions every minute.

  - type: exercise
    heading: "Exercise 5 — Implement MarketDataStore"
    prompt: >
      Implement MarketDataStore with four methods: fetch, update, load, and
      tickers. fetch delegates to fetch_ohlcv with the stored fetch_fn.
      update calls fetch then store_ohlcv. load calls load_ohlcv. tickers
      returns a sorted list of all tickers that update has been called with.
    hint: >
      Store a set() of seen tickers at construction. add() to it in update().
      Use a real file path (not ':memory:') in tests so store and load share
      the same database.
    narration: >
      This is a clean integration exercise. If your five module-level
      functions work correctly, MarketDataStore is just four lines of
      delegation. The only new logic is tracking the set of tickers — and
      sorting it in the tickers() method. If you get stuck, look at how
      ToolRegistry, MediaStudio, or OpsAgent delegated to module-level
      functions in earlier sections.

  - type: summary
    heading: "Day 89 Complete"
    bullets:
      - "OHLCV_COLS: the universal five-column price format"
      - "fetch_ohlcv: injectable yfinance wrapper (gate-safe)"
      - "validate_ohlcv: (bool, str) — four boundary checks"
      - "normalize_ohlcv: tz-strip + column filter + copy"
      - "store_ohlcv / load_ohlcv: SQLite persistence with compound PK"
      - "MarketDataStore: four-method facade over the full pipeline"
    narration: >
      You have the foundation. market_data.py is the module every subsequent
      day in Section 7 depends on. It fetches, validates, normalizes, stores,
      and serves OHLCV data — all in a form that is testable, injectable, and
      offline-safe. Tomorrow: computing technical indicators on top of this data.
""",
]

# ══════════════════════════════════════════════════════════════════════════════
# Project + solution notebooks
# ══════════════════════════════════════════════════════════════════════════════

_FULL_P = _P_BASE + _P_VALIDATE + _P_NORMALIZE + _P_FETCH + _P_STORE + _P_CLASS

_PROJ_SYNTHETIC = """\
# Gate-safe synthetic data — replace fetch_fn=_synthetic with fetch_fn=None
# (or remove the argument) to use real yfinance data.
def _synthetic_ohlcv(ticker="TEST", period="1y", interval="1d"):
    import math
    n = 252
    prices = [100.0 * (1 + 0.3 * math.sin(i * 2 * math.pi / 252)) for i in range(n)]
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

_PROJ_SETUP = """\
import tempfile, os

# Create a persistent SQLite store for this session
_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
DB_PATH = _db_file.name
_db_file.close()

store = MarketDataStore(db_path=DB_PATH, fetch_fn=_synthetic_ohlcv)

TICKERS = ["AAPL", "MSFT", "GOOG"]

for ticker in TICKERS:
    n = store.update(ticker)
    print(f"{ticker}: stored {n} rows")

print(f"\\nTracked tickers: {store.tickers()}")
"""

_PROJ_LOAD = """\
# Load and display a summary for each ticker
for ticker in store.tickers():
    df = store.load(ticker)
    ok, reason = validate_ohlcv(df)
    close = df["Close"]
    print(f"{ticker}: {len(df)} rows | valid={ok} | "
          f"close min={close.min():.2f} max={close.max():.2f} "
          f"mean={close.mean():.2f}")
"""

_PROJ_EXPORT = """\
# Export one ticker to CSV for inspection
aapl = store.load("AAPL")
csv_path = DB_PATH.replace(".db", "_AAPL.csv")
aapl.to_csv(csv_path)
print(f"Exported AAPL to {csv_path}")
print(aapl.head(3).to_string())
"""

_PROJ_CLEANUP = """\
# Cleanup temp files
os.unlink(DB_PATH)
if os.path.exists(csv_path):
    os.unlink(csv_path)
print("\\nProject complete. Temp files cleaned up.")
"""

PROJECT_NB = _nb([
    _md(f"# Day {DAY} Project — Mini Portfolio Data Store\n\n"
        "Build a `MarketDataStore` that fetches, validates, and persists OHLCV "
        "data for a small portfolio of tickers. Export a summary and a CSV. "
        "Use `fetch_fn=_synthetic_ohlcv` for offline testing; swap it out for "
        "`fetch_fn=None` to fetch real data with yfinance."),
    _code(_FULL_P),
    _md("## Step 1 — Define the synthetic data source (gate-safe)"),
    _code(_PROJ_SYNTHETIC),
    _md("## Step 2 — Create the store and fetch your portfolio"),
    _code(_PROJ_SETUP),
    _md("## Step 3 — Load and summarize each ticker"),
    _code(_PROJ_LOAD),
    _md("## Step 4 — Export to CSV"),
    _code(_PROJ_EXPORT),
    _md("## Step 5 — Cleanup"),
    _code(_PROJ_CLEANUP),
])

_SOL_SYNTHETIC = """\
def _synthetic_ohlcv(ticker="TEST", period="1y", interval="1d"):
    import math
    n = 252
    prices = [100.0 * (1 + 0.3 * math.sin(i * 2 * math.pi / 252)) for i in range(n)]
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

_SOL_CORE = """\
import tempfile, os

_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
DB_PATH = _db.name
_db.close()

store = MarketDataStore(db_path=DB_PATH, fetch_fn=_synthetic_ohlcv)

for ticker in ["AAPL", "MSFT", "GOOG"]:
    n = store.update(ticker)
    assert n == 252, f"expected 252 rows for {ticker}, got {n}"

assert store.tickers() == ["AAPL", "GOOG", "MSFT"], f"tickers={store.tickers()}"
"""

_SOL_VALIDATE = """\
for ticker in store.tickers():
    df = store.load(ticker)
    ok, reason = validate_ohlcv(df)
    assert ok, f"{ticker}: {reason}"
    assert isinstance(df.index, pd.DatetimeIndex)
    assert len(df) == 252
    print(f"{ticker}: {len(df)} rows | close mean={df['Close'].mean():.2f}")
"""

_SOL_EXPORT = """\
aapl = store.load("AAPL")
csv_path = DB_PATH.replace(".db", "_AAPL.csv")
aapl.to_csv(csv_path)
assert os.path.exists(csv_path)
print(f"\\nExported {len(aapl)} rows to {csv_path}")
"""

_SOL_CLEANUP = """\
os.unlink(DB_PATH)
os.unlink(csv_path)
print("Solution smoke-test passed.")
"""

SOLUTION_NB = _nb([
    _md(f"# Day {DAY} Solution — Mini Portfolio Data Store"),
    _code(_FULL_P),
    _code(_SOL_SYNTHETIC),
    _code(_SOL_CORE),
    _code(_SOL_VALIDATE),
    _code(_SOL_EXPORT),
    _code(_SOL_CLEANUP),
])

# ══════════════════════════════════════════════════════════════════════════════
# Gate inline validation
# ══════════════════════════════════════════════════════════════════════════════

GATE_PY = f"""\
import importlib.util, sys, tempfile, os, math, pandas as pd

spec = importlib.util.spec_from_file_location(
    "{SLUG}", r"{DIR / (SLUG + '.py')}"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# ── synthetic OHLCV (gate injection) ─────────────────────────────────────────
def _synthetic_ohlcv(ticker="TEST", period="1y", interval="1d"):
    n = 252
    prices = [100.0 * (1 + 0.3 * math.sin(i * 2 * math.pi / 252)) for i in range(n)]
    dates  = pd.date_range("2023-01-01", periods=n, freq="B")
    close  = pd.Series(prices, index=dates)
    return pd.DataFrame({{
        "Open":   close.shift(1).fillna(close.iloc[0]),
        "High":   close * 1.01,
        "Low":    close * 0.99,
        "Close":  close,
        "Volume": pd.Series([1_000_000 + i * 1_000 for i in range(n)], index=dates),
    }})

df = _synthetic_ohlcv()

# OHLCV_COLS
assert mod.OHLCV_COLS == ["Open", "High", "Low", "Close", "Volume"]

# fetch_ohlcv: injection
df2 = mod.fetch_ohlcv("TEST", fetch_fn=_synthetic_ohlcv)
assert "Close" in df2.columns and len(df2) == 252

# validate_ohlcv: valid
ok, reason = mod.validate_ohlcv(df)
assert ok, reason

# validate: missing column
ok2, r2 = mod.validate_ohlcv(df.drop(columns=["Volume"]))
assert not ok2 and "Volume" in r2

# validate: empty
ok3, r3 = mod.validate_ohlcv(pd.DataFrame(columns=mod.OHLCV_COLS))
assert not ok3

# validate: not a DataFrame
ok4, _ = mod.validate_ohlcv("not a df")
assert not ok4

# validate: High < Low
df_inv = df.copy()
df_inv.loc[df_inv.index[10], "High"] = df_inv["Low"].iloc[10] - 1.0
ok5, r5 = mod.validate_ohlcv(df_inv)
assert not ok5

# normalize_ohlcv: strips timezone
df_tz = df.copy()
df_tz.index = df_tz.index.tz_localize("UTC")
normed = mod.normalize_ohlcv(df_tz)
assert normed.index.tz is None
assert list(normed.columns) == mod.OHLCV_COLS

# normalize_ohlcv: does not mutate input
assert df_tz.index.tz is not None

# store_ohlcv + load_ohlcv: round-trip
with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
    db_path = f.name
try:
    n = mod.store_ohlcv(df, "TEST", db_path)
    assert n == 252, f"expected 252, got {{n}}"
    loaded = mod.load_ohlcv("TEST", db_path)
    assert len(loaded) == 252
    assert "Close" in loaded.columns
    assert isinstance(loaded.index, pd.DatetimeIndex)
    assert loaded.index.tz is None
    empty = mod.load_ohlcv("NOTEXIST", db_path)
    assert isinstance(empty, pd.DataFrame) and len(empty) == 0
finally:
    os.unlink(db_path)

# store_ohlcv: raises ValueError on invalid data
try:
    mod.store_ohlcv(pd.DataFrame(), "TEST")
    assert False, "should have raised ValueError"
except ValueError:
    pass

# MarketDataStore
with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
    db2 = f.name
try:
    store = mod.MarketDataStore(db_path=db2, fetch_fn=_synthetic_ohlcv)
    rows = store.update("AAPL")
    assert rows == 252
    loaded2 = store.load("AAPL")
    assert len(loaded2) == 252 and isinstance(loaded2.index, pd.DatetimeIndex)
    store.update("MSFT")
    t = store.tickers()
    assert "AAPL" in t and "MSFT" in t
    assert t == sorted(t)
    raw = store.fetch("GOOG")
    assert len(raw) == 252
    still_empty = store.load("GOOG")
    assert len(still_empty) == 0, "fetch() must not store data"
finally:
    os.unlink(db2)

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
