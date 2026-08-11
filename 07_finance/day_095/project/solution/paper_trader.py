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
    return "\n".join(lines)
