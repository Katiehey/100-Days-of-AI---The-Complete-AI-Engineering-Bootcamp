#!/usr/bin/env python3
"""Day 095 generator — The Trading Bot I."""
import json, pathlib

ROOT  = pathlib.Path(__file__).parent.parent
DAY   = "095"
SLUG  = "paper_trader"
TITLE = "The Trading Bot I"
DIR   = ROOT / "07_finance" / f"day_{DAY}"

# ══════════════════════════════════════════════════════════════════════════════
# Deliverable
# ══════════════════════════════════════════════════════════════════════════════

DELIVERABLE = '''\
"""
Day 095 — The Trading Bot I
============================
Paper-trading bot: explicit cash/share accounting for simulated trading.
Distinct from Day 91 (vectorised returns algebra) — this module tracks every
order, cash balance, and position in dollar terms, ready for extension to
live execution.

Public API
----------
    Trade           — dataclass: one order record
    PaperAccount    — stateful cash + position tracker
        .portfolio_value(price)        -> float
        .buy(date, price, fraction=1.0) -> Trade
        .sell(date, price)             -> Trade | None
    run_paper_trader(df, signals,
                     initial_cash=10_000.0,
                     fraction=1.0)     -> dict
    format_report(result)              -> str
"""
from dataclasses import dataclass, field
import pandas as pd


# ── data types ────────────────────────────────────────────────────────────────

@dataclass
class Trade:
    """One executed order in the paper-trading session."""
    date:       object   # pd.Timestamp
    action:     str      # "BUY" or "SELL"
    price:      float    # execution price (Close of the signal bar)
    shares:     float    # shares transacted
    cash_after: float    # cash remaining after the order
    value_after: float   # total portfolio value after the order


@dataclass
class PaperAccount:
    """Stateful cash and position tracker for paper trading.

    Usage:
        acc = PaperAccount(initial_cash=10_000.0)
        acc.buy(date, price)          # invest all cash at market
        acc.sell(date, price)         # liquidate entire position
        acc.portfolio_value(price)    # current mark-to-market value
    """

    initial_cash: float = 10_000.0
    cash:         float = field(init=False)
    shares:       float = field(init=False)
    trades:       list  = field(init=False)

    def __post_init__(self):
        self.cash   = self.initial_cash
        self.shares = 0.0
        self.trades = []

    def portfolio_value(self, price):
        """Cash + mark-to-market value of open position.

        Args:
            price : float — current market price per share

        Returns:
            float — total portfolio value
        """
        return self.cash + self.shares * float(price)

    def buy(self, date, price, fraction=1.0):
        """Buy as many shares as `fraction` of available cash allows.

        fraction=1.0 (default) invests all cash; 0.5 invests half.
        Guard: if cash ≤ 0 or price ≤ 0, returns None without trading.

        Records a Trade and updates cash and shares.

        Returns:
            Trade — the executed order record, or None if no funds.
        """
        price = float(price)
        if self.cash <= 0 or price <= 0:
            return None
        shares = (self.cash * fraction) / price
        cost   = shares * price
        if cost > self.cash:          # float-rounding guard
            shares = self.cash / price
            cost   = shares * price
        self.cash   -= cost
        self.shares += shares
        t = Trade(date=date, action="BUY", price=price, shares=shares,
                  cash_after=self.cash,
                  value_after=self.portfolio_value(price))
        self.trades.append(t)
        return t

    def sell(self, date, price):
        """Liquidate the entire open position.

        If no shares are held, returns None without recording a trade.

        Records a Trade and updates cash (shares reset to 0).

        Returns:
            Trade — the executed order record, or None if already flat.
        """
        price = float(price)
        if self.shares <= 0:
            return None
        proceeds    = self.shares * price
        sold_shares = self.shares
        self.cash  += proceeds
        self.shares = 0.0
        t = Trade(date=date, action="SELL", price=price, shares=sold_shares,
                  cash_after=self.cash,
                  value_after=self.portfolio_value(price))
        self.trades.append(t)
        return t


# ── bot loop ──────────────────────────────────────────────────────────────────

def run_paper_trader(df, signals, initial_cash=10_000.0, fraction=1.0):
    """Run a paper-trading simulation bar by bar.

    On each bar, compare current signal to the previous one:
      • 0 → 1 transition: BUY  (enter long)
      • 1 → 0 transition: SELL (exit long)
      • no change:        HOLD

    Equity is recorded at each bar as portfolio_value(close).
    Any open position at the end of the series is force-liquidated
    at the final close so the account is always fully flat at exit.

    Args:
        df           : pd.DataFrame with "Close" column
        signals      : pd.Series of {0, 1}, same index as df
        initial_cash : float — starting capital in dollars
        fraction     : float — fraction of cash to invest per entry (default 1.0)

    Returns dict with keys:
        account       PaperAccount (post-simulation state)
        trades        list[Trade]
        equity        pd.Series — portfolio value at each close
        initial_cash  float
        final_value   float
        total_return  float
        max_drawdown  float
        n_trades      int — total order count (buys + sells)
        n_buys        int
        n_sells       int
    """
    account     = PaperAccount(initial_cash=initial_cash)
    eq_values   = []
    prev_signal = 0

    for i in range(len(df)):
        date  = df.index[i]
        price = float(df["Close"].iloc[i])
        sig   = int(signals.iloc[i])

        if sig == 1 and prev_signal == 0:
            account.buy(date, price, fraction=fraction)
        elif sig == 0 and prev_signal == 1:
            account.sell(date, price)

        eq_values.append(account.portfolio_value(price))
        prev_signal = sig

    # Force-liquidate any open position at end
    if account.shares > 0:
        account.sell(df.index[-1], float(df["Close"].iloc[-1]))

    equity       = pd.Series(eq_values, index=df.index)
    total_return = float(equity.iloc[-1] / initial_cash - 1.0)
    peak         = equity.cummax()
    max_dd       = float(((equity - peak) / peak).min())

    return {
        "account":      account,
        "trades":       account.trades,
        "equity":       equity,
        "initial_cash": initial_cash,
        "final_value":  float(equity.iloc[-1]),
        "total_return": total_return,
        "max_drawdown": max_dd,
        "n_trades":     len(account.trades),
        "n_buys":       sum(1 for t in account.trades if t.action == "BUY"),
        "n_sells":      sum(1 for t in account.trades if t.action == "SELL"),
    }


# ── reporting ─────────────────────────────────────────────────────────────────

def format_report(result):
    """Format a paper-trading result as a human-readable string.

    Suitable for logging to a file or sending as a notification (Day 96).

    Args:
        result : dict from run_paper_trader

    Returns:
        str
    """
    lines = [
        "=== Paper Trading Report ===",
        f"Initial cash :  ${result['initial_cash']:>12,.2f}",
        f"Final value  :  ${result['final_value']:>12,.2f}",
        f"Total return :  {result['total_return']:>12.2%}",
        f"Max drawdown :  {result['max_drawdown']:>12.2%}",
        f"Trades total :  {result['n_trades']:>12d}",
        f"  Buys       :  {result['n_buys']:>12d}",
        f"  Sells      :  {result['n_sells']:>12d}",
    ]
    if result["trades"]:
        first = result["trades"][0]
        last  = result["trades"][-1]
        lines.append(f"First trade  :  {first.action} @ ${first.price:,.2f}"
                     f"  ({first.date})")
        lines.append(f"Last trade   :  {last.action} @ ${last.price:,.2f}"
                     f"  ({last.date})")
    return "\\n".join(lines)
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
from dataclasses import dataclass, field

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

_P_TRADE = """\
@dataclass
class Trade:
    date:        object
    action:      str
    price:       float
    shares:      float
    cash_after:  float
    value_after: float
"""

_P_ACCOUNT = """\
@dataclass
class PaperAccount:
    initial_cash: float = 10_000.0
    cash:         float = field(init=False)
    shares:       float = field(init=False)
    trades:       list  = field(init=False)

    def __post_init__(self):
        self.cash   = self.initial_cash
        self.shares = 0.0
        self.trades = []

    def portfolio_value(self, price):
        return self.cash + self.shares * float(price)

    def buy(self, date, price, fraction=1.0):
        price = float(price)
        if self.cash <= 0 or price <= 0:
            return None
        shares = (self.cash * fraction) / price
        cost   = shares * price
        if cost > self.cash:
            shares = self.cash / price
            cost   = shares * price
        self.cash   -= cost
        self.shares += shares
        t = Trade(date=date, action="BUY", price=price, shares=shares,
                  cash_after=self.cash,
                  value_after=self.portfolio_value(price))
        self.trades.append(t)
        return t

    def sell(self, date, price):
        price = float(price)
        if self.shares <= 0:
            return None
        proceeds    = self.shares * price
        sold_shares = self.shares
        self.cash  += proceeds
        self.shares = 0.0
        t = Trade(date=date, action="SELL", price=price, shares=sold_shares,
                  cash_after=self.cash,
                  value_after=self.portfolio_value(price))
        self.trades.append(t)
        return t
"""

_P_BOT = """\
def run_paper_trader(df, signals, initial_cash=10_000.0, fraction=1.0):
    account = PaperAccount(initial_cash=initial_cash)
    eq_values   = []
    prev_signal = 0
    for i in range(len(df)):
        date  = df.index[i]
        price = float(df["Close"].iloc[i])
        sig   = int(signals.iloc[i])
        if sig == 1 and prev_signal == 0:
            account.buy(date, price, fraction=fraction)
        elif sig == 0 and prev_signal == 1:
            account.sell(date, price)
        eq_values.append(account.portfolio_value(price))
        prev_signal = sig
    if account.shares > 0:
        account.sell(df.index[-1], float(df["Close"].iloc[-1]))
    equity       = pd.Series(eq_values, index=df.index)
    total_return = float(equity.iloc[-1] / initial_cash - 1.0)
    peak         = equity.cummax()
    max_dd       = float(((equity - peak) / peak).min())
    return {
        "account":      account,
        "trades":       account.trades,
        "equity":       equity,
        "initial_cash": initial_cash,
        "final_value":  float(equity.iloc[-1]),
        "total_return": total_return,
        "max_drawdown": max_dd,
        "n_trades":     len(account.trades),
        "n_buys":       sum(1 for t in account.trades if t.action == "BUY"),
        "n_sells":      sum(1 for t in account.trades if t.action == "SELL"),
    }
"""

_P_REPORT = """\
def format_report(result):
    lines = [
        "=== Paper Trading Report ===",
        f"Initial cash :  ${result['initial_cash']:>12,.2f}",
        f"Final value  :  ${result['final_value']:>12,.2f}",
        f"Total return :  {result['total_return']:>12.2%}",
        f"Max drawdown :  {result['max_drawdown']:>12.2%}",
        f"Trades total :  {result['n_trades']:>12d}",
        f"  Buys       :  {result['n_buys']:>12d}",
        f"  Sells      :  {result['n_sells']:>12d}",
    ]
    if result["trades"]:
        first = result["trades"][0]
        last  = result["trades"][-1]
        lines.append(f"First trade  :  {first.action} @ ${first.price:,.2f}  ({first.date})")
        lines.append(f"Last trade   :  {last.action} @ ${last.price:,.2f}  ({last.date})")
    return "\\n".join(lines)
"""

_P_STRAT = """\
def _sma_cross(df, fast=20, slow=50):
    c = df["Close"]
    return (c.rolling(fast).mean() > c.rolling(slow).mean()).fillna(False).astype(int)

def _apply_sl(signals, prices, stop_pct=0.05):
    result = signals.copy().astype(float)
    entry  = None
    for i in range(len(result)):
        if result.iloc[i] == 1:
            if entry is None:
                entry = float(prices.iloc[i])
            elif float(prices.iloc[i]) <= entry * (1 - stop_pct):
                result.iloc[i] = 0
                entry = None
        else:
            entry = None
    return result.astype(int)

def _apply_dd(signals, prices, limit=-0.20):
    peak = prices.cummax()
    dd   = (prices - peak) / peak
    r    = signals.copy().astype(int)
    r[dd < limit] = 0
    return r
"""

# ══════════════════════════════════════════════════════════════════════════════
# Exercises
# ══════════════════════════════════════════════════════════════════════════════

_EX1 = _nb([
    _md("# Exercise 1 — PaperAccount: buy and portfolio_value\n\n"
        "`PaperAccount` is the core state machine. It tracks cash and shares "
        "separately so every dollar is accounted for. `portfolio_value` is the "
        "mark-to-market total at the current price. `buy` converts cash into "
        "shares using a `fraction` of available cash."),
    _code(_P_BASE + _P_TRADE + """\

@dataclass
class PaperAccount:
    initial_cash: float = 10_000.0
    cash:         float = field(init=False)
    shares:       float = field(init=False)
    trades:       list  = field(init=False)

    def __post_init__(self):
        # TODO: self.cash = initial_cash, shares = 0.0, trades = []
        self.cash   = self.initial_cash
        self.shares = 0.0
        self.trades = []

    def portfolio_value(self, price):
        \"\"\"Cash + shares * price.\"\"\"
        # TODO: one line
        return 0.0

    def buy(self, date, price, fraction=1.0):
        \"\"\"Buy fraction of cash worth of shares.

        Steps:
          1. Guard: if cash<=0 or price<=0, return None
          2. shares = (self.cash * fraction) / price
          3. cost   = shares * price
          4. Guard: if cost > self.cash: recalculate to avoid float rounding
          5. self.cash -= cost; self.shares += shares
          6. Append Trade(...) to self.trades
          7. Return the Trade
        \"\"\"
        # TODO: ~8 lines
        return None

    def sell(self, date, price):
        \"\"\"Placeholder — implement in Exercise 2.\"\"\"
        return None
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — __post_init__: correct initial state
try:
    acc = PaperAccount(initial_cash=10_000.0)
    assert abs(acc.cash   - 10_000.0) < 1e-9
    assert abs(acc.shares - 0.0)      < 1e-9
    assert acc.trades == []
    checks += 1; print("✅ 1 PaperAccount initial state: cash=10000, shares=0, trades=[]")
except Exception as e:
    print("❌ 1:", e)

# 2 — portfolio_value: cash + shares * price
try:
    acc = PaperAccount(10_000.0)
    acc.cash   = 5_000.0
    acc.shares = 25.0
    assert abs(acc.portfolio_value(100.0) - 7_500.0) < 1e-9, \
        f"expected 7500, got {acc.portfolio_value(100.0)}"
    checks += 1; print("✅ 2 portfolio_value = cash + shares × price = 7500")
except Exception as e:
    print("❌ 2:", e)

# 3 — buy: reduces cash, increases shares
try:
    acc = PaperAccount(10_000.0)
    t   = acc.buy("2023-01-01", 100.0)
    assert t is not None and t.action == "BUY"
    assert abs(acc.shares - 100.0) < 1e-6, f"expected 100 shares, got {acc.shares}"
    assert abs(acc.cash)           < 1e-6, f"expected 0 cash, got {acc.cash}"
    checks += 1; print("✅ 3 buy(price=100, cash=10000) → 100 shares, 0 cash")
except Exception as e:
    print("❌ 3:", e)

# 4 — portfolio_value unchanged after buy (price same as buy price)
try:
    acc = PaperAccount(10_000.0)
    acc.buy("2023-01-01", 100.0)
    pv = acc.portfolio_value(100.0)
    assert abs(pv - 10_000.0) < 1e-6, \
        f"portfolio_value should be 10000 right after buy, got {pv}"
    checks += 1; print("✅ 4 portfolio_value equals initial_cash immediately after buy")
except Exception as e:
    print("❌ 4:", e)

# 5 — buy with fraction=0.5: half invested, half cash remains
try:
    acc = PaperAccount(10_000.0)
    t   = acc.buy("2023-01-01", 100.0, fraction=0.5)
    assert abs(acc.shares - 50.0)   < 1e-6, f"expected 50 shares, got {acc.shares}"
    assert abs(acc.cash - 5_000.0)  < 1e-6, f"expected 5000 cash, got {acc.cash}"
    checks += 1; print("✅ 5 buy(fraction=0.5) → 50 shares, $5000 cash remaining")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX2 = _nb([
    _md("# Exercise 2 — PaperAccount.sell and trade log\n\n"
        "`sell` is the mirror of `buy`: it converts shares back to cash. "
        "The trade log (`self.trades`) records every order with full context — "
        "date, action, price, shares, cash balance, and portfolio value. "
        "This log is what makes paper trading useful for debugging and review."),
    _code(_P_BASE + _P_TRADE + _P_ACCOUNT[: _P_ACCOUNT.index("    def sell")] + """\
    def sell(self, date, price):
        \"\"\"Liquidate the entire position.

        Steps:
          1. Guard: if shares <= 0, return None (already flat)
          2. proceeds    = self.shares * price
          3. sold_shares = self.shares
          4. self.cash  += proceeds; self.shares = 0.0
          5. Append Trade(action="SELL", shares=sold_shares, ...)
          6. Return the Trade
        \"\"\"
        # TODO: ~8 lines
        return None
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — sell when flat returns None
try:
    acc = PaperAccount(10_000.0)
    result = acc.sell("2023-01-01", 100.0)
    assert result is None, f"sell with no shares should return None, got {result}"
    checks += 1; print("✅ 1 sell() with no position returns None")
except Exception as e:
    print("❌ 1:", e)

# 2 — buy then sell: cash fully restored
try:
    acc = PaperAccount(10_000.0)
    acc.buy("2023-01-02",  100.0)
    acc.sell("2023-01-03", 100.0)
    assert abs(acc.shares)             < 1e-6
    assert abs(acc.cash - 10_000.0)   < 1e-6
    checks += 1; print("✅ 2 buy then sell at same price → cash fully restored, shares=0")
except Exception as e:
    print("❌ 2:", e)

# 3 — profit: sell above buy price
try:
    acc = PaperAccount(10_000.0)
    acc.buy("2023-01-02",  100.0)    # 100 shares
    acc.sell("2023-01-10", 110.0)    # sell at +10%
    expected = 100 * 110.0           # 11000
    assert abs(acc.cash - expected)  < 1e-6, \
        f"expected cash={expected}, got {acc.cash}"
    checks += 1; print("✅ 3 sell at +10% → $11000 cash (profit)")
except Exception as e:
    print("❌ 3:", e)

# 4 — trade log: 2 records after buy+sell
try:
    acc = PaperAccount(10_000.0)
    acc.buy("2023-01-02",  100.0)
    acc.sell("2023-01-10", 120.0)
    assert len(acc.trades) == 2
    assert acc.trades[0].action == "BUY"
    assert acc.trades[1].action == "SELL"
    assert abs(acc.trades[1].cash_after - 12_000.0) < 1e-6
    checks += 1; print("✅ 4 trade log has 2 records: BUY then SELL")
except Exception as e:
    print("❌ 4:", e)

# 5 — sell clears shares (double-sell returns None)
try:
    acc = PaperAccount(10_000.0)
    acc.buy("2023-01-02",  100.0)
    acc.sell("2023-01-10", 100.0)
    result2 = acc.sell("2023-01-11", 100.0)  # already flat
    assert result2 is None, "double-sell should return None"
    assert len(acc.trades) == 2, "double-sell should not add a trade"
    checks += 1; print("✅ 5 second sell on flat position returns None, no extra trade")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX3 = _nb([
    _md("# Exercise 3 — run_paper_trader\n\n"
        "The bot loop iterates bar by bar. On a 0→1 signal transition it buys; "
        "on a 1→0 transition it sells. At each bar it records the current "
        "portfolio value. At the end, any open position is force-liquidated "
        "so the account is fully settled."),
    _code(_P_BASE + _P_TRADE + _P_ACCOUNT + """\

def run_paper_trader(df, signals, initial_cash=10_000.0, fraction=1.0):
    \"\"\"Simulate paper trading bar by bar.

    Algorithm:
      account     = PaperAccount(initial_cash)
      prev_signal = 0
      for i in range(len(df)):
          sig = int(signals.iloc[i])
          if sig == 1 and prev_signal == 0:  → buy
          elif sig == 0 and prev_signal == 1: → sell
          append portfolio_value to eq_values
          prev_signal = sig
      if account.shares > 0: → force-sell at last close
      compute equity Series, total_return, max_drawdown
      return result dict

    Returns dict with:
        account, trades, equity, initial_cash, final_value,
        total_return, max_drawdown, n_trades, n_buys, n_sells
    \"\"\"
    account     = PaperAccount(initial_cash=initial_cash)
    eq_values   = []
    prev_signal = 0

    for i in range(len(df)):
        date  = df.index[i]
        price = float(df["Close"].iloc[i])
        sig   = int(signals.iloc[i])
        # TODO: buy on 0→1, sell on 1→0
        eq_values.append(account.portfolio_value(price))
        prev_signal = sig

    # TODO: force-sell if open position
    equity       = pd.Series(eq_values, index=df.index)
    total_return = float(equity.iloc[-1] / initial_cash - 1.0)
    peak         = equity.cummax()
    max_dd       = float(((equity - peak) / peak).min())
    return {
        "account":      account,
        "trades":       account.trades,
        "equity":       equity,
        "initial_cash": initial_cash,
        "final_value":  float(equity.iloc[-1]),
        "total_return": total_return,
        "max_drawdown": max_dd,
        "n_trades":     len(account.trades),
        "n_buys":       sum(1 for t in account.trades if t.action == "BUY"),
        "n_sells":      sum(1 for t in account.trades if t.action == "SELL"),
    }
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — flat signal: equity = initial_cash throughout
try:
    df  = _synthetic()
    sig = pd.Series(0, index=df.index)
    r   = run_paper_trader(df, sig, initial_cash=10_000.0)
    assert (r["equity"] == 10_000.0).all(), "flat signal → equity always equals initial_cash"
    assert r["n_trades"]  == 0
    assert r["n_buys"]    == 0
    assert r["n_sells"]   == 0
    checks += 1; print("✅ 1 flat signal → equity=10000 throughout, 0 trades")
except Exception as e:
    print("❌ 1:", e)

# 2 — always-long signal: 1 BUY + 1 forced SELL = 2 trades
try:
    df  = _synthetic()
    sig = pd.Series(1, index=df.index)
    r   = run_paper_trader(df, sig, initial_cash=10_000.0)
    assert r["n_buys"]  == 1, f"expected 1 buy, got {r['n_buys']}"
    assert r["n_sells"] == 1, f"expected 1 sell, got {r['n_sells']}"
    checks += 1; print("✅ 2 always-long: 1 BUY + 1 forced SELL = 2 total trades")
except Exception as e:
    print("❌ 2:", e)

# 3 — always-long equity tracks Close / initial_price × initial_cash
try:
    df  = _synthetic()
    sig = pd.Series(1, index=df.index)
    r   = run_paper_trader(df, sig, initial_cash=10_000.0)
    # Bought at close[0]: shares = 10000 / close[0]
    shares0  = 10_000.0 / df["Close"].iloc[0]
    expected = df["Close"] * shares0
    diff     = (r["equity"] - expected).abs().max()
    assert diff < 1e-6, f"equity tracks price × shares, max diff = {diff}"
    checks += 1; print("✅ 3 equity tracks Close × shares bought at entry")
except Exception as e:
    print("❌ 3:", e)

# 4 — equity Series has correct length and index
try:
    df  = _synthetic()
    sig = pd.Series(1, index=df.index)
    r   = run_paper_trader(df, sig)
    assert len(r["equity"]) == len(df)
    assert (r["equity"].index == df.index).all()
    checks += 1; print("✅ 4 equity Series has same length and index as df")
except Exception as e:
    print("❌ 4:", e)

# 5 — total_return = final_value / initial_cash - 1
try:
    df  = _synthetic()
    sig = pd.Series(1, index=df.index)
    r   = run_paper_trader(df, sig, initial_cash=10_000.0)
    expected_tr = r["final_value"] / 10_000.0 - 1.0
    assert abs(r["total_return"] - expected_tr) < 1e-9
    assert r["max_drawdown"] <= 1e-9   # always ≤ 0
    checks += 1; print("✅ 5 total_return = final_value/initial_cash - 1; max_drawdown ≤ 0")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX4 = _nb([
    _md("# Exercise 4 — format_report\n\n"
        "`format_report` turns the result dict into a human-readable string "
        "for logging and alerts. Day 96 will extend this to write to a log file "
        "and optionally send a notification. The function must include all key "
        "metrics and, if trades exist, the first and last trade."),
    _code(_P_BASE + _P_TRADE + _P_ACCOUNT + _P_BOT + """\

def format_report(result):
    \"\"\"Format the run_paper_trader result as a multiline string.

    Required fields in output:
        - initial cash, final value, total return, max drawdown
        - total trades, buys, sells
        - first and last trade (date, action, price) if any trades exist

    Returns:
        str
    \"\"\"
    # TODO: build a list of lines, join with "\\n"
    return ""
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — returns a non-empty string
try:
    df  = _synthetic()
    sig = pd.Series(1, index=df.index)
    r   = run_paper_trader(df, sig)
    rep = format_report(r)
    assert isinstance(rep, str) and len(rep) > 50, \
        f"expected a non-trivial string, got: {repr(rep)}"
    checks += 1; print("✅ 1 format_report returns a non-empty string")
except Exception as e:
    print("❌ 1:", e)

# 2 — contains key metrics as strings
try:
    df  = _synthetic()
    sig = pd.Series(1, index=df.index)
    r   = run_paper_trader(df, sig)
    rep = format_report(r)
    text = rep.lower()
    assert "initial" in text, "should mention initial cash"
    assert "return"  in text, "should mention total return"
    assert "drawdown" in text, "should mention max drawdown"
    checks += 1; print("✅ 2 report mentions initial cash, return, and drawdown")
except Exception as e:
    print("❌ 2:", e)

# 3 — total return value appears correctly formatted
try:
    df  = _synthetic()
    sig = pd.Series(1, index=df.index)
    r   = run_paper_trader(df, sig)
    rep = format_report(r)
    tr_pct = f"{r['total_return']:.2%}"
    assert tr_pct.replace("-","") in rep.replace("-",""), \
        f"total_return {tr_pct} not found in report"
    checks += 1; print(f"✅ 3 total return {tr_pct} appears in report")
except Exception as e:
    print("❌ 3:", e)

# 4 — flat signal: report mentions 0 trades
try:
    df  = _synthetic()
    sig = pd.Series(0, index=df.index)
    r   = run_paper_trader(df, sig)
    rep = format_report(r)
    assert "0" in rep, "report should show 0 trades for flat signal"
    checks += 1; print("✅ 4 flat signal report shows 0 trades")
except Exception as e:
    print("❌ 4:", e)

# 5 — print the full report
try:
    df  = _synthetic()
    sig = pd.Series(1, index=df.index)
    r   = run_paper_trader(df, sig, initial_cash=10_000.0)
    rep = format_report(r)
    print(rep)
    checks += 1; print("✅ 5 report printed successfully")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX5 = _nb([
    _md("# Exercise 5 — Full Pipeline: Strategy + Risk + Paper Trader\n\n"
        "The complete Section 7 stack, end to end: generate signals with an "
        "SMA crossover, apply risk filters (stop-loss + drawdown limit), "
        "then run the paper-trading bot. Compare raw vs. risk-filtered results "
        "to see what risk management costs and what it buys."),
    _code(_P_BASE + _P_TRADE + _P_ACCOUNT + _P_BOT + _P_REPORT + _P_STRAT),
    _code("""\
df = _synthetic(n=252)

# Generate raw signals
raw_signals = _sma_cross(df)

# Apply risk filters
sl_signals  = _apply_sl(raw_signals, df["Close"], stop_pct=0.05)
safe_signals = _apply_dd(sl_signals, df["Close"], limit=-0.20)

# Run paper traders
r_raw  = run_paper_trader(df, raw_signals,  initial_cash=10_000.0)
r_safe = run_paper_trader(df, safe_signals, initial_cash=10_000.0)

print("--- RAW STRATEGY ---")
print(format_report(r_raw))
print()
print("--- RISK-FILTERED ---")
print(format_report(r_safe))
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — risk-filtered max_drawdown ≥ raw (less severe)
try:
    assert r_safe["max_drawdown"] >= r_raw["max_drawdown"], \
        f"risk max_dd ({r_safe['max_drawdown']:.2%}) should be ≥ raw ({r_raw['max_drawdown']:.2%})"
    checks += 1; print("✅ 1 risk-filtered max_drawdown is less severe (or equal)")
except Exception as e:
    print("❌ 1:", e)

# 2 — risk-filtered has ≤ raw n_trades
try:
    assert r_safe["n_trades"] <= r_raw["n_trades"], \
        f"risk {r_safe['n_trades']} trades should be ≤ raw {r_raw['n_trades']}"
    checks += 1; print("✅ 2 risk-filtered has fewer or equal trades than raw")
except Exception as e:
    print("❌ 2:", e)

# 3 — equity length and index match df
try:
    for label, r in [("raw", r_raw), ("safe", r_safe)]:
        assert len(r["equity"]) == len(df)
        assert (r["equity"].index == df.index).all()
    checks += 1; print("✅ 3 equity Series length and index correct for both")
except Exception as e:
    print("❌ 3:", e)

# 4 — final_value = equity.iloc[-1]
try:
    for label, r in [("raw", r_raw), ("safe", r_safe)]:
        assert abs(r["final_value"] - r["equity"].iloc[-1]) < 1e-9, \
            f"{label}: final_value != equity[-1]"
    checks += 1; print("✅ 4 final_value == equity.iloc[-1] for both strategies")
except Exception as e:
    print("❌ 4:", e)

# 5 — n_buys == n_sells (or n_sells == n_buys - 1 if force-sold)
try:
    for label, r in [("raw", r_raw), ("safe", r_safe)]:
        diff = abs(r["n_buys"] - r["n_sells"])
        assert diff <= 1, f"{label}: |buys-sells| should be 0 or 1, got {diff}"
    checks += 1; print("✅ 5 |n_buys - n_sells| ≤ 1 for both (forced sell closes last trade)")
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
day: "095"
lesson: 1
title: "Paper Trading vs Real Trading"
slides:
  - type: title
    heading: "The Trading Bot I"
    subheading: "Paper trading: test before you risk real money"
    narration: >
      Day 95. You have every building block: market data (Day 89), indicators
      (Day 90), backtesting (Day 91), strategies (Day 92), sentiment (Day 93),
      and risk management (Day 94). Today you assemble them into a paper-trading
      bot — a simulation that acts exactly like a real trading system, but with
      fake money. Paper trading is the standard industry practice for testing
      strategies before going live.

  - type: concept
    label: "Paper vs vectorised"
    heading: "Why Paper Trading If We Have run_backtest?"
    body: >
      Day 91's vectorised backtester and Day 95's paper trader serve different purposes.
    bullets:
      - "run_backtest: fast, returns-algebra, no explicit cash/shares tracking"
      - "PaperAccount: slow bar-by-bar loop, tracks every dollar and share"
      - "Paper trader → can be adapted for live execution with minimal changes"
      - "Paper trader → trade log shows WHEN and at WHAT PRICE each order executes"
      - "Paper trader → dollar-level position sizing (not signal fraction algebra)"
    narration: >
      The vectorised backtester from Day 91 is ideal for rapid strategy research —
      you can test thousands of parameter combinations quickly. But it produces
      aggregate metrics, not order-by-order detail. The paper trader runs the same
      strategy bar by bar, maintains explicit cash and share counts, and logs every
      trade. This makes it easy to adapt for live trading: replace the Close price
      with a live market feed and the simulated order with a real broker API call.
      The only line that changes.

  - type: concept
    label: "Paper trading workflow"
    heading: "The Paper Trading Workflow"
    body: >
      Run the strategy in simulation for N days; review the trade log; go live.
    bullets:
      - "Step 1: research on run_backtest (fast, many parameters)"
      - "Step 2: validate on paper trader (explicit trades, realistic detail)"
      - "Step 3: paper trade forward for 30+ days (observe live behavior)"
      - "Step 4: go live with the same code, just swap the price source"
      - "Step 5: monitor vs. paper performance — large divergence = data issue"
    narration: >
      Paper trading solves the forward-test problem. A backtest is always tested
      on historical data the researcher has already seen. Paper trading is tested
      on data that arrives daily — the researcher cannot overfit to it. After 30
      days of paper trading that matches the backtested performance, the strategy
      has passed a meaningful out-of-sample test. Only then should real capital
      be risked.

  - type: exercise
    heading: "Exercise 1 — PaperAccount.buy and portfolio_value"
    prompt: >
      Implement portfolio_value(price) → cash + shares * price.
      Implement buy(date, price, fraction=1.0): convert fraction of cash to shares,
      append a Trade, update self.cash and self.shares.
    hint: >
      shares = (self.cash * fraction) / price. cost = shares * price. If cost > self.cash
      due to float rounding, recalculate. Then self.cash -= cost; self.shares += shares.
      Create a Trade and append to self.trades. Buying at price 100 with $10000 → 100 shares, 0 cash.
    narration: >
      portfolio_value is one line. buy is about eight. The guard for cost > self.cash
      prevents floating-point accumulation from making the cash balance slightly negative.
      After implementing, verify check 4: portfolio_value equals initial_cash immediately
      after buying at the same price — because you spent exactly as much cash as the
      shares are worth.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "Paper trading: bar-by-bar simulation with explicit cash/share tracking"
      - "Paper trader vs. backtester: different tools for different stages"
      - "PaperAccount: cash and shares updated on every buy/sell"
      - "portfolio_value = cash + shares × price (mark-to-market)"
      - "Next: sell and the trade log"
    narration: >
      The first exercise establishes the core state. Next lesson: sell, and
      how the trade log captures every order for review.
""",

    """\
day: "095"
lesson: 2
title: "The Trade Log"
slides:
  - type: title
    heading: "Trade Log"
    subheading: "Every order, every dollar, every timestamp"
    narration: >
      The trade log is the paper trader's paper trail. Every buy and sell is
      recorded with its date, price, shares, cash balance after the order, and
      total portfolio value after the order. This log is invaluable for debugging
      strategy behavior — you can look at exactly which bars triggered which orders
      and why the equity curve looks the way it does.

  - type: code
    label: "Trade dataclass"
    heading: "The Trade Record"
    body: >
      Six fields describe a complete order record.
    code: |
      @dataclass
      class Trade:
          date:        object   # pd.Timestamp — bar date
          action:      str      # "BUY" or "SELL"
          price:       float    # execution price (bar's Close)
          shares:      float    # shares transacted
          cash_after:  float    # cash remaining after execution
          value_after: float    # total portfolio value after execution
    narration: >
      Using a dataclass is cleaner than a dict for structured data you will
      read back frequently. You can access trade.price, trade.date, trade.action
      instead of trade["price"] — more readable and less error-prone. The
      value_after field makes it easy to reconstruct the equity curve from just
      the trade log: on bars with no trade, portfolio value = cash + shares × close.

  - type: concept
    label: "Sell logic"
    heading: "Selling: Mirror of Buy"
    body: >
      sell liquidates the entire position and records the trade.
    bullets:
      - "Guard: if shares ≤ 0, return None (already flat — nothing to sell)"
      - "proceeds = self.shares × price"
      - "self.cash += proceeds; self.shares = 0.0"
      - "Record Trade(action='SELL', shares=sold_shares, ...)"
      - "The second call to sell (when flat) returns None — no duplicate trade"
    narration: >
      The sell-all approach is standard for a simple paper trader. In a more
      sophisticated system, you might sell a fraction of the position. But for
      the bot in Days 95–96, every exit liquidates the entire position — simple,
      clear, and easy to verify from the trade log. The guard prevents a second
      sell from creating a spurious trade record when the bot processes a 1→0
      transition but shares are already 0.

  - type: exercise
    heading: "Exercise 2 — PaperAccount.sell"
    prompt: >
      Implement sell(date, price). Guard: if shares <= 0, return None.
      Otherwise: proceeds = shares × price; update cash and shares;
      append Trade(action="SELL", shares=sold_shares, ...).
      Check 3: buy at 100 → 100 shares; sell at 110 → cash = $11,000.
    hint: >
      sold_shares = self.shares (before zeroing). After: self.cash += proceeds,
      self.shares = 0.0. value_after = self.portfolio_value(price) which with
      shares=0 is just self.cash. Check 5: calling sell a second time when flat
      should return None and NOT add a second trade record.
    narration: >
      The sell method is symmetric to buy. The most common mistake is setting
      self.shares = 0.0 before computing sold_shares. Always record what you
      sold before clearing the position. Check 3 tests a profit: 100 shares
      bought at $100 and sold at $110 yields $11,000 — a $1,000 or 10% gain.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "Trade dataclass: six fields, full order context"
      - "sell: guard for flat position; proceeds → cash; shares → 0"
      - "Trade log: buy+sell → 2 records; double-sell → only 1 record"
      - "value_after = cash (after sell), since shares = 0"
      - "Next: the bot loop in run_paper_trader"
    narration: >
      With buy and sell complete, the PaperAccount state machine is finished.
      Next: the bot loop that calls buy/sell on every signal transition.
""",

    """\
day: "095"
lesson: 3
title: "The Bot Loop"
slides:
  - type: title
    heading: "The Bot Loop"
    subheading: "Signal → decision → order → record"
    narration: >
      The bot loop is the inner engine of run_paper_trader. It iterates over
      every bar in the dataset, comparing the current signal to the previous
      one. A 0→1 transition triggers a buy; a 1→0 triggers a sell; no change
      means hold. At each bar, the equity is recorded. After the loop, any
      open position is force-liquidated.

  - type: code
    label: "Bot loop"
    heading: "The Signal Transition Logic"
    body: >
      Five state transitions; one bar-by-bar loop.
    code: |
      prev_signal = 0
      for i in range(len(df)):
          sig   = int(signals.iloc[i])
          price = float(df["Close"].iloc[i])

          if sig == 1 and prev_signal == 0:    # entry: go long
              account.buy(date, price)
          elif sig == 0 and prev_signal == 1:  # exit: go flat
              account.sell(date, price)
          # else: hold (no action)

          eq_values.append(account.portfolio_value(price))
          prev_signal = sig

      # Force-liquidate any open position at end
      if account.shares > 0:
          account.sell(df.index[-1], df["Close"].iloc[-1])
    narration: >
      The signal transition logic is the trading rule in code. prev_signal
      tracks the state from the previous bar. On a 0→1 transition, the
      strategy just went long — buy. On a 1→0 transition, the strategy
      exited — sell. If the signal stays the same (0→0 or 1→1), hold.
      Note that this uses the current bar's Close as the execution price.
      In a real system you would use the next bar's Open; for paper trading
      at daily frequency, Close is standard.

  - type: concept
    label: "Force liquidation"
    heading: "Why Force-Liquidate at the End?"
    body: >
      Always end the simulation fully flat for clean accounting.
    bullets:
      - "Without force-sell: final equity = cash + open position value (unrealized)"
      - "With force-sell: final equity = cash only (all realized)"
      - "Both give the same dollar value (selling at close doesn't change value)"
      - "But the account object is clean: cash = final_value, shares = 0"
      - "Necessary for Day 96: the daily bot should always be fully settled each day"
    narration: >
      The force-sell is a bookkeeping convenience. Selling shares at the current
      market price does not change the portfolio value — you just convert shares
      to cash at market. But it leaves the account object in a clean state:
      account.cash equals the final portfolio value and account.shares is zero.
      This is important for Day 96, where the bot runs daily and needs a clean
      start each morning.

  - type: exercise
    heading: "Exercise 3 — run_paper_trader"
    prompt: >
      Implement the for loop: on 0→1 signal → buy; on 1→0 → sell; always
      append portfolio_value. After the loop, force-sell if shares > 0.
      Build the result dict. Check 1: flat signal → equity always equals
      initial_cash and n_trades=0. Check 2: always-long → n_buys=1, n_sells=1.
    hint: >
      Check 3: buy 10000 / close[0] shares at close[0]; equity[i] = shares × close[i].
      So equity tracks the price series scaled by initial_cash / close[0].
      The force-sell adds a SELL to account.trades, so n_trades=2 for always-long.
    narration: >
      The TODO in the exercise is just two if/elif lines inside the loop,
      plus the force-sell check after. If check 1 fails, the hold case is
      not working — make sure you only call buy on 0→1 and sell on 1→0.
      If check 2 fails, count the trades: the force-sell after the loop
      should be the second trade for always-long.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "Bot loop: prev_signal tracks last bar; transitions trigger orders"
      - "0→1: buy; 1→0: sell; same: hold"
      - "Force-liquidate at end for clean accounting"
      - "equity Series: portfolio_value at each bar's Close"
      - "Next: format_report and the full pipeline"
    narration: >
      The bot loop is done. Next: format_report to generate the daily summary
      report, and the full Section 7 pipeline from raw data to formatted results.
""",

    """\
day: "095"
lesson: 4
title: "Reporting and the Full Stack"
slides:
  - type: title
    heading: "format_report"
    subheading: "From result dict to readable report"
    narration: >
      format_report converts the result dictionary from run_paper_trader into
      a human-readable string. This is the output that gets logged to a file
      (Day 96) and optionally sent as a notification. A good report shows
      everything needed to evaluate the session at a glance: initial capital,
      final value, return, drawdown, and the number and details of trades.

  - type: code
    label: "format_report"
    heading: "A Simple Text Report"
    body: >
      Build a list of lines; join with newline.
    code: |
      def format_report(result):
          lines = [
              "=== Paper Trading Report ===",
              f"Initial cash :  ${result['initial_cash']:>12,.2f}",
              f"Final value  :  ${result['final_value']:>12,.2f}",
              f"Total return :  {result['total_return']:>12.2%}",
              f"Max drawdown :  {result['max_drawdown']:>12.2%}",
              f"Trades total :  {result['n_trades']:>12d}",
              f"  Buys       :  {result['n_buys']:>12d}",
              f"  Sells      :  {result['n_sells']:>12d}",
          ]
          if result["trades"]:
              first = result["trades"][0]
              last  = result["trades"][-1]
              lines.append(f"First trade  :  {first.action} @ ${first.price:,.2f}"
                           f"  ({first.date})")
              lines.append(f"Last trade   :  {last.action} @ ${last.price:,.2f}"
                           f"  ({last.date})")
          return "\n".join(lines)
    narration: >
      The format string {:>12,.2f} right-aligns in 12 characters with commas
      and 2 decimal places — standard for financial formatting. The {:>12.2%}
      format converts a decimal like 0.15 to 15.00%. The trade details at the
      bottom — first and last trade — give a quick sanity check: does the first
      trade look right? Did the bot actually exit?

  - type: concept
    label: "Day 96 extension"
    heading: "Day 96: Scheduling and Logging"
    body: >
      Tomorrow's session wraps the bot in a scheduler and adds file logging.
    bullets:
      - "Day 96 adds: log_result(result, path) → appends report to a log file"
      - "Day 96 adds: schedule_daily(fn) → run the bot at market close each day"
      - "Day 96 adds: send_alert(message) → webhook notification on entry/exit"
      - "Day 95 (today): the bot logic; Day 96: the operational wrapper"
      - "format_report is the bridge: same string goes to log file and alert"
    narration: >
      The bot logic (today) is completely separate from the operational wrapper
      (Day 96). This is a good software engineering pattern: the trading algorithm
      should not know or care whether its output goes to a file, a Slack webhook,
      or a screen. format_report returns a plain string that the wrapper decides
      what to do with. This makes the bot easy to test in isolation.

  - type: exercise
    heading: "Exercises 4 and 5 — format_report and Full Pipeline"
    prompt: >
      Exercise 4: implement format_report. Build a list of lines including all
      required fields; add first/last trade details if trades exist. Exercise 5:
      run SMA-crossover strategy through risk filters then paper trader; compare
      raw vs. risk-filtered reports.
    hint: >
      Exercise 5 check 1: risk max_drawdown >= raw max_drawdown (less negative).
      Check 5: |n_buys - n_sells| <= 1 for both — should be 0 if the last
      signal was a sell, or 1 if the last position was force-liquidated.
    narration: >
      The full pipeline exercise is the payoff for the last 7 days of work.
      Every module from Days 89–95 is in play. Observe the comparison: risk
      filtering typically reduces both return and max_drawdown, and fewer trades
      are executed. That is the correct behavior.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "format_report: multiline string with all key metrics and trade details"
      - "Financial formatting: {:,.2f} for dollars, {:.2%} for percentages"
      - "Bot design: algorithm (Day 95) separate from operational wrapper (Day 96)"
      - "format_report output → log file, notification, or screen (Day 96 decides)"
      - "Next: Day 96 wraps the bot in a scheduler + logger"
    narration: >
      Day 95 is complete. The paper-trading bot is built and tested end-to-end.
      Tomorrow you wrap it in scheduling and logging to make it production-like:
      running daily at market close, logging every session, sending alerts on
      trade entries and exits.
""",

    """\
day: "095"
lesson: 5
title: "Paper Trader Architecture"
slides:
  - type: title
    heading: "Architecture"
    subheading: "How the Section 7 modules fit together"
    narration: >
      The fifth lesson steps back and looks at the architecture of the full
      Section 7 system. Each module built from Days 89–95 has a clear
      responsibility: fetch, validate, enrich, signal, filter, or simulate.
      Understanding the boundary between each module is what lets you swap
      components — change the strategy, add a new risk filter, or plug in
      a live data feed — without touching the rest.

  - type: concept
    label: "Module map"
    heading: "The Section 7 Module Map"
    body: >
      Seven modules, one pipeline: data → indicators → signal → risk → simulate.
    bullets:
      - "market_data.py: fetch, validate, normalize, store, load OHLCV"
      - "indicators.py: sma, ema, rsi, macd, bollinger_bands, add_indicators"
      - "backtester.py: compute_returns, compute_equity, run_backtest (vectorised)"
      - "strategy.py: sma_crossover, rsi_mean_reversion, macd_cross, combined"
      - "sentiment.py: score_headline, aggregate_sentiment, SentimentSignal"
      - "risk.py: kelly_fraction, apply_stop_loss, apply_drawdown_limit, RiskManager"
      - "paper_trader.py: PaperAccount, run_paper_trader, format_report"
    narration: >
      Each module is independent: strategy.py does not import from indicators.py;
      paper_trader.py does not import from risk.py. The pipeline is assembled in
      the calling code — the bot script (Day 96) or a notebook. This independence
      makes each module easy to test in isolation and easy to swap out. The calling
      code decides which modules to compose, which is the correct place for that
      decision.

  - type: concept
    label: "Bot architecture"
    heading: "The Paper Trading Bot Architecture"
    body: >
      The bot is a pipeline with one stateful object (PaperAccount).
    bullets:
      - "Stateless: market_data → indicators → strategy → risk → signals"
      - "Stateful: PaperAccount (cash, shares, trade log)"
      - "All stateless steps can be re-run; only PaperAccount holds history"
      - "Day 96 wraps the stateless pipeline in a daily scheduler"
      - "For live trading: replace Close price source with a broker's live feed"
    narration: >
      The clean separation between stateless signal generation and stateful
      account tracking is what makes the paper trader easy to adapt for live
      trading. Every step before PaperAccount.buy() can be run repeatedly
      without side effects. PaperAccount holds the account state. In a live
      system, the broker API is the external state — the bot just needs to call
      broker.place_order() instead of account.buy().

  - type: exercise
    heading: "Project — Paper Trading Dashboard"
    prompt: >
      Run three strategies (SMA-cross, always-long, always-flat) through
      the paper trader with $10,000 initial cash. Print the format_report
      for each. Assert that always-flat has n_trades=0, that always-long
      has n_buys=n_sells=1, and that max_drawdown ≤ 0 for all strategies.
    hint: >
      Always-flat: signal = pd.Series(0, index=df.index).
      Always-long: signal = pd.Series(1, index=df.index).
      The solution asserts |n_buys - n_sells| <= 1 for all strategies
      (force-liquidation may add one extra sell).
    narration: >
      The project is a quick integration test of the full system. Three
      strategies, three reports. If always-flat shows non-zero equity changes,
      something is wrong with portfolio_value. If always-long shows n_trades > 2,
      the bot is re-entering a position mid-loop.

  - type: summary
    heading: "Day 95 Complete"
    bullets:
      - "Trade dataclass: six-field order record"
      - "PaperAccount: cash + shares state; buy, sell, portfolio_value"
      - "run_paper_trader: bar-by-bar loop + force-liquidate + result dict"
      - "format_report: human-readable string for logging and alerts"
      - "Architecture: stateless pipeline → stateful account"
      - "Next: Day 96 — scheduling, logging, and live-simulation alerts"
    narration: >
      The paper-trading bot is complete. Day 96 adds the production wrapper:
      scheduling the bot to run daily, logging every session to a file, and
      sending an alert when the strategy takes a position. At that point, the
      entire Section 7 system is operational.
""",
]

# ══════════════════════════════════════════════════════════════════════════════
# Project + solution
# ══════════════════════════════════════════════════════════════════════════════

_FULL_P = _P_BASE + _P_TRADE + _P_ACCOUNT + _P_BOT + _P_REPORT + _P_STRAT

PROJECT_NB = _nb([
    _md(f"# Day {DAY} Project — Paper Trading Dashboard\n\n"
        "Run three strategies through the paper trader and compare their "
        "reports: always-flat (baseline), always-long (buy-and-hold), and "
        "SMA-crossover (tactical). Verify invariants about the trade log."),
    _code(_FULL_P),
    _code("""\
df = _synthetic(n=252)

strategies = [
    ("Always-Flat", pd.Series(0, index=df.index)),
    ("Always-Long", pd.Series(1, index=df.index)),
    ("SMA-cross",   _sma_cross(df)),
]

results = {}
for label, sig in strategies:
    r = run_paper_trader(df, sig, initial_cash=10_000.0)
    results[label] = r
    print(f"\\n{'='*40}")
    print(format_report(r))
"""),
])

SOLUTION_NB = _nb([
    _md(f"# Day {DAY} Solution — Paper Trading Dashboard"),
    _code(_FULL_P),
    _code("""\
df = _synthetic(n=252)

strategies = [
    ("Always-Flat", pd.Series(0, index=df.index)),
    ("Always-Long", pd.Series(1, index=df.index)),
    ("SMA-cross",   _sma_cross(df)),
]

results = {}
for label, sig in strategies:
    r = run_paper_trader(df, sig, initial_cash=10_000.0)
    results[label] = r

# Assertions
flat  = results["Always-Flat"]
long_ = results["Always-Long"]
sma   = results["SMA-cross"]

assert flat["n_trades"]  == 0,  f"always-flat should have 0 trades, got {flat['n_trades']}"
assert (flat["equity"] == 10_000.0).all(), "always-flat equity should be constant"
assert long_["n_buys"]  == 1,   f"always-long: 1 buy"
assert long_["n_sells"] == 1,   f"always-long: 1 sell (forced)"
for label, r in results.items():
    assert r["max_drawdown"] <= 1e-9, f"{label}: max_drawdown should be ≤ 0"
    assert abs(r["final_value"] - r["equity"].iloc[-1]) < 1e-9
    diff = abs(r["n_buys"] - r["n_sells"])
    assert diff <= 1, f"{label}: |buys-sells| should be 0 or 1"

for label, r in results.items():
    print(f"\\n{'='*40}")
    print(format_report(r))

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

# PaperAccount basics
acc = mod.PaperAccount(10_000.0)
assert abs(acc.cash   - 10_000.0) < 1e-9
assert abs(acc.shares - 0.0)      < 1e-9
assert acc.trades == []

# portfolio_value
acc2 = mod.PaperAccount(10_000.0)
acc2.cash = 5_000.0; acc2.shares = 25.0
assert abs(acc2.portfolio_value(100.0) - 7_500.0) < 1e-9

# buy
acc3 = mod.PaperAccount(10_000.0)
t = acc3.buy("2023-01-01", 100.0)
assert t is not None and t.action == "BUY"
assert abs(acc3.shares - 100.0) < 1e-6
assert abs(acc3.cash)           < 1e-6
assert abs(acc3.portfolio_value(100.0) - 10_000.0) < 1e-6

# buy with fraction
acc4 = mod.PaperAccount(10_000.0)
acc4.buy("2023-01-01", 100.0, fraction=0.5)
assert abs(acc4.shares - 50.0)  < 1e-6
assert abs(acc4.cash - 5_000.0) < 1e-6

# sell when flat → None
acc5 = mod.PaperAccount(10_000.0)
assert acc5.sell("2023-01-01", 100.0) is None

# buy then sell
acc6 = mod.PaperAccount(10_000.0)
acc6.buy("2023-01-02", 100.0)
acc6.sell("2023-01-10", 110.0)
assert abs(acc6.shares)             < 1e-6
assert abs(acc6.cash - 11_000.0)    < 1e-6
assert len(acc6.trades) == 2
assert acc6.trades[0].action == "BUY"
assert acc6.trades[1].action == "SELL"

# double-sell guard
acc6.sell("2023-01-11", 110.0)   # should return None, no new trade
assert len(acc6.trades) == 2, "double-sell should not add a trade"

# run_paper_trader — flat signal
sig_flat = pd.Series(0, index=df.index)
r_flat   = mod.run_paper_trader(df, sig_flat, initial_cash=10_000.0)
assert isinstance(r_flat["equity"], pd.Series) and len(r_flat["equity"]) == n
assert (r_flat["equity"] == 10_000.0).all()
assert r_flat["n_trades"] == 0

# run_paper_trader — always-long
sig_long = pd.Series(1, index=df.index)
r_long   = mod.run_paper_trader(df, sig_long, initial_cash=10_000.0)
assert r_long["n_buys"]  == 1
assert r_long["n_sells"] == 1
assert r_long["n_trades"] == 2
# equity tracks price
shares0  = 10_000.0 / df["Close"].iloc[0]
expected = df["Close"] * shares0
assert (r_long["equity"] - expected).abs().max() < 1e-6
# accounting invariants
assert abs(r_long["final_value"] - r_long["equity"].iloc[-1]) < 1e-9
assert r_long["max_drawdown"] <= 1e-9
assert abs(r_long["total_return"] - (r_long["final_value"] / 10_000.0 - 1.0)) < 1e-9

# format_report returns string
rep = mod.format_report(r_long)
assert isinstance(rep, str) and len(rep) > 50
assert "BUY" in rep or "buy" in rep.lower()

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
