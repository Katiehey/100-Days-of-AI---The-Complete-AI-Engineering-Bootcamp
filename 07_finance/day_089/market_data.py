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
import sqlite3
import pandas as pd

OHLCV_COLS = ["Open", "High", "Low", "Close", "Volume"]

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
