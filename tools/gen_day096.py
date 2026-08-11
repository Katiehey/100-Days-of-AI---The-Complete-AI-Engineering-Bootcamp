#!/usr/bin/env python3
"""Day 096 generator — The Trading Bot II."""
import json, pathlib

ROOT  = pathlib.Path(__file__).parent.parent
DAY   = "096"
SLUG  = "bot_runner"
TITLE = "The Trading Bot II"
DIR   = ROOT / "07_finance" / f"day_{DAY}"

# ══════════════════════════════════════════════════════════════════════════════
# Deliverable
# ══════════════════════════════════════════════════════════════════════════════

DELIVERABLE = '''\
"""
Day 096 — The Trading Bot II
==============================
Operational wrapper for the paper-trading bot: logging, alerting, scheduling.
Complements paper_trader.py (Day 95); does NOT import it at module level so
the module loads cleanly even when paper_trader.py is not on the path.

Public API
----------
    format_log_entry(report_text)          -> str  (adds timestamp header)
    log_result(report_text, path)                  (appends to log file)
    send_alert(message, webhook_url=None)  -> bool
    next_run_time(run_time_str="16:00")    -> datetime
    seconds_until(target_dt)              -> float (≥ 0)
    run_daily_loop(bot_fn, run_time="16:00",
                   max_iterations=None,
                   _sleep_fn=None)         -> int   (run count)

    BotRunner(log_path, webhook_url=None, run_time="16:00")
        .run_once(df, signals,
                  initial_cash=10_000.0,
                  fraction=1.0)            -> dict  (result + "report" key)
        .run_count()                       -> int
        .read_log()                        -> str
"""
import datetime
import pathlib


# ── logging ───────────────────────────────────────────────────────────────────

def format_log_entry(report_text):
    """Prepend a UTC-local timestamp header to a report string.

    Args:
        report_text : str — formatted trading report

    Returns:
        str — header + report_text
    """
    ts  = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    bar = "=" * 52
    return f"\\n{bar}\\n[{ts}]\\n{bar}\\n{report_text}"


def log_result(report_text, path):
    """Append a timestamped report to a log file.

    Creates the file and any missing parent directories automatically.
    Each call appends one entry so the file grows as a session journal.

    Args:
        report_text : str — formatted trading report (from format_report)
        path        : str | pathlib.Path — log file destination
    """
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = format_log_entry(report_text)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(entry + "\\n")


# ── alerting ──────────────────────────────────────────────────────────────────

def send_alert(message, webhook_url=None):
    """Send an alert message via webhook or stdout.

    If webhook_url is None: print to stdout and return True.
    If webhook_url is provided: POST JSON {"text": message} to the URL.

    Returns:
        bool — True on success, False if the HTTP request failed.
    """
    if webhook_url is None:
        print(f"[ALERT] {message}")
        return True
    try:
        import requests
        resp = requests.post(webhook_url, json={"text": message}, timeout=5)
        return resp.ok
    except Exception:
        return False


# ── scheduling ────────────────────────────────────────────────────────────────

def next_run_time(run_time_str="16:00"):
    """Return the next local datetime matching run_time_str (HH:MM).

    If the time has not yet passed today, returns today at that time.
    If it has already passed, returns tomorrow at that time.

    Args:
        run_time_str : str — 24-hour "HH:MM" (default "16:00" = market close)

    Returns:
        datetime.datetime
    """
    now   = datetime.datetime.now()
    h, m  = (int(x) for x in run_time_str.split(":"))
    today = now.replace(hour=h, minute=m, second=0, microsecond=0)
    if today <= now:
        today += datetime.timedelta(days=1)
    return today


def seconds_until(target_dt):
    """Seconds from now until target_dt.

    Returns 0.0 if target_dt is in the past.

    Args:
        target_dt : datetime.datetime

    Returns:
        float ≥ 0
    """
    delta = target_dt - datetime.datetime.now()
    return max(0.0, delta.total_seconds())


def run_daily_loop(bot_fn, run_time="16:00", max_iterations=None,
                   _sleep_fn=None):
    """Run bot_fn once per day at run_time.

    Blocks (via _sleep_fn) until run_time, calls bot_fn(), then waits for
    the next occurrence. Runs indefinitely when max_iterations is None.

    Args:
        bot_fn         : callable — called with no arguments each iteration
        run_time       : str — "HH:MM" 24-hour time (default "16:00")
        max_iterations : int | None — stop after N calls; None = forever
        _sleep_fn      : callable(seconds) — injected for testing;
                         defaults to time.sleep

    Returns:
        int — number of times bot_fn was called
    """
    import time
    if _sleep_fn is None:
        _sleep_fn = time.sleep

    count = 0
    while max_iterations is None or count < max_iterations:
        target = next_run_time(run_time)
        secs   = seconds_until(target)
        _sleep_fn(secs)
        bot_fn()
        count += 1
    return count


# ── BotRunner ─────────────────────────────────────────────────────────────────

class BotRunner:
    """Stateful daily-bot wrapper: run → log → alert, with run count.

    Usage:
        runner = BotRunner("logs/trading.log", webhook_url=None)
        result = runner.run_once(df, signals)
        print(runner.read_log())
    """

    def __init__(self, log_path, webhook_url=None, run_time="16:00"):
        self.log_path    = pathlib.Path(log_path)
        self.webhook_url = webhook_url
        self.run_time    = run_time
        self._run_count  = 0

    def run_once(self, df, signals, initial_cash=10_000.0, fraction=1.0):
        """Run the full paper-trading pipeline once.

        Steps:
          1. run_paper_trader(df, signals, initial_cash, fraction)
          2. format_report(result)
          3. log_result to self.log_path
          4. send_alert if any trades were executed
          5. increment run_count; add "report" key to result

        Returns:
            dict — run_paper_trader result with "report" str added
        """
        from paper_trader import run_paper_trader, format_report  # lazy import

        result = run_paper_trader(df, signals,
                                  initial_cash=initial_cash, fraction=fraction)
        report = format_report(result)
        log_result(report, self.log_path)

        if result["n_trades"] > 0:
            send_alert(
                f"BOT: {result['n_trades']} trade(s) executed — "
                f"return {result['total_return']:.2%}",
                self.webhook_url,
            )

        self._run_count += 1
        result["report"] = report
        return result

    def run_count(self):
        """Number of times run_once has been called."""
        return self._run_count

    def read_log(self):
        """Return full log file contents.

        Returns empty string if the log has not been written yet.
        """
        if not self.log_path.exists():
            return ""
        return self.log_path.read_text(encoding="utf-8")
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
import pandas as pd, math, datetime, pathlib, tempfile

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

_P_TRADER = """\
from dataclasses import dataclass, field

@dataclass
class Trade:
    date: object; action: str; price: float
    shares: float; cash_after: float; value_after: float

@dataclass
class PaperAccount:
    initial_cash: float = 10_000.0
    cash:   float = field(init=False)
    shares: float = field(init=False)
    trades: list  = field(init=False)
    def __post_init__(self):
        self.cash = self.initial_cash; self.shares = 0.0; self.trades = []
    def portfolio_value(self, price):
        return self.cash + self.shares * float(price)
    def buy(self, date, price, fraction=1.0):
        price = float(price)
        if self.cash <= 0 or price <= 0: return None
        shares = (self.cash * fraction) / price
        cost   = shares * price
        if cost > self.cash: shares = self.cash / price; cost = shares * price
        self.cash -= cost; self.shares += shares
        t = Trade(date=date, action="BUY", price=price, shares=shares,
                  cash_after=self.cash, value_after=self.portfolio_value(price))
        self.trades.append(t); return t
    def sell(self, date, price):
        price = float(price)
        if self.shares <= 0: return None
        proceeds = self.shares * price; sold = self.shares
        self.cash += proceeds; self.shares = 0.0
        t = Trade(date=date, action="SELL", price=price, shares=sold,
                  cash_after=self.cash, value_after=self.portfolio_value(price))
        self.trades.append(t); return t

def run_paper_trader(df, signals, initial_cash=10_000.0, fraction=1.0):
    acc = PaperAccount(initial_cash=initial_cash)
    eq  = []; prev = 0
    for i in range(len(df)):
        date = df.index[i]; price = float(df["Close"].iloc[i])
        sig = int(signals.iloc[i])
        if sig == 1 and prev == 0: acc.buy(date, price, fraction=fraction)
        elif sig == 0 and prev == 1: acc.sell(date, price)
        eq.append(acc.portfolio_value(price)); prev = sig
    if acc.shares > 0: acc.sell(df.index[-1], float(df["Close"].iloc[-1]))
    equity = pd.Series(eq, index=df.index)
    tr     = float(equity.iloc[-1] / initial_cash - 1.0)
    peak   = equity.cummax()
    return {"account": acc, "trades": acc.trades, "equity": equity,
            "initial_cash": initial_cash, "final_value": float(equity.iloc[-1]),
            "total_return": tr, "max_drawdown": float(((equity - peak)/peak).min()),
            "n_trades": len(acc.trades),
            "n_buys":   sum(1 for t in acc.trades if t.action == "BUY"),
            "n_sells":  sum(1 for t in acc.trades if t.action == "SELL")}

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
        f_ = result["trades"][0]; l_ = result["trades"][-1]
        lines.append(f"First trade  :  {f_.action} @ ${f_.price:,.2f}  ({f_.date})")
        lines.append(f"Last trade   :  {l_.action} @ ${l_.price:,.2f}  ({l_.date})")
    return "\\n".join(lines)
"""

_P_RUNNER = """\
def format_log_entry(report_text):
    ts  = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    bar = "=" * 52
    return f"\\n{bar}\\n[{ts}]\\n{bar}\\n{report_text}"

def log_result(report_text, path):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = format_log_entry(report_text)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(entry + "\\n")

def send_alert(message, webhook_url=None):
    if webhook_url is None:
        print(f"[ALERT] {message}")
        return True
    try:
        import requests
        resp = requests.post(webhook_url, json={"text": message}, timeout=5)
        return resp.ok
    except Exception:
        return False

def next_run_time(run_time_str="16:00"):
    now = datetime.datetime.now()
    h, m = (int(x) for x in run_time_str.split(":"))
    target = now.replace(hour=h, minute=m, second=0, microsecond=0)
    if target <= now:
        target += datetime.timedelta(days=1)
    return target

def seconds_until(target_dt):
    delta = target_dt - datetime.datetime.now()
    return max(0.0, delta.total_seconds())

def run_daily_loop(bot_fn, run_time="16:00", max_iterations=None,
                   _sleep_fn=None):
    import time
    if _sleep_fn is None: _sleep_fn = time.sleep
    count = 0
    while max_iterations is None or count < max_iterations:
        _sleep_fn(seconds_until(next_run_time(run_time)))
        bot_fn()
        count += 1
    return count
"""

_P_BOT_CLASS = """\
class BotRunner:
    def __init__(self, log_path, webhook_url=None, run_time="16:00"):
        self.log_path    = pathlib.Path(log_path)
        self.webhook_url = webhook_url
        self.run_time    = run_time
        self._run_count  = 0

    def run_once(self, df, signals, initial_cash=10_000.0, fraction=1.0):
        result = run_paper_trader(df, signals,
                                  initial_cash=initial_cash, fraction=fraction)
        report = format_report(result)
        log_result(report, self.log_path)
        if result["n_trades"] > 0:
            send_alert(
                f"BOT: {result['n_trades']} trade(s) — "
                f"return {result['total_return']:.2%}",
                self.webhook_url,
            )
        self._run_count += 1
        result["report"] = report
        return result

    def run_count(self):
        return self._run_count

    def read_log(self):
        if not self.log_path.exists():
            return ""
        return self.log_path.read_text(encoding="utf-8")
"""

# ══════════════════════════════════════════════════════════════════════════════
# Exercises
# ══════════════════════════════════════════════════════════════════════════════

_EX1 = _nb([
    _md("# Exercise 1 — log_result and format_log_entry\n\n"
        "Logging is the safety net for any automated system. Every time the "
        "bot runs, it appends a timestamped entry to a log file. If the bot "
        "misbehaves in production, the log tells you exactly what happened "
        "and when. `format_log_entry` adds the timestamp; `log_result` "
        "handles file I/O with automatic directory creation."),
    _code(_P_BASE + """\

def format_log_entry(report_text):
    \"\"\"Prepend a timestamp header to report_text.

    Format:
        ====...====
        [2025-01-15 16:00:00]
        ====...====
        <report_text>

    Returns:
        str
    \"\"\"
    # TODO: ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # then build the header string and prepend to report_text
    return report_text


def log_result(report_text, path):
    \"\"\"Append a timestamped report entry to a log file.

    Steps:
      1. path = pathlib.Path(path)
      2. path.parent.mkdir(parents=True, exist_ok=True)
      3. entry = format_log_entry(report_text)
      4. open(path, "a") and write entry + "\\n"
    \"\"\"
    # TODO: ~5 lines
    pass
"""),
    _md("### Checks"),
    _code("""\
checks = 0
sample = "=== Paper Trading Report ===\\nTotal return: 5.00%"

# 1 — format_log_entry returns a string containing the original text
try:
    entry = format_log_entry(sample)
    assert isinstance(entry, str)
    assert sample in entry, "format_log_entry should include the original report text"
    checks += 1; print("✅ 1 format_log_entry includes the original report text")
except Exception as e:
    print("❌ 1:", e)

# 2 — format_log_entry includes a timestamp-like pattern
try:
    entry = format_log_entry(sample)
    import re
    has_ts = bool(re.search(r"\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2}", entry))
    assert has_ts, f"no YYYY-MM-DD HH:MM:SS pattern found in:\\n{entry}"
    checks += 1; print("✅ 2 format_log_entry includes a YYYY-MM-DD HH:MM:SS timestamp")
except Exception as e:
    print("❌ 2:", e)

# 3 — log_result creates the file
try:
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td) / "subdir" / "bot.log"
        log_result(sample, p)
        assert p.exists(), "log file should be created"
    checks += 1; print("✅ 3 log_result creates the file (and parent dirs)")
except Exception as e:
    print("❌ 3:", e)

# 4 — log_result content is readable and contains the report
try:
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td) / "bot.log"
        log_result(sample, p)
        content = p.read_text(encoding="utf-8")
        assert "Paper Trading Report" in content
        assert "5.00%" in content
    checks += 1; print("✅ 4 log file contains the report text")
except Exception as e:
    print("❌ 4:", e)

# 5 — log_result appends (multiple calls grow the file)
try:
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td) / "bot.log"
        log_result("Entry 1", p)
        log_result("Entry 2", p)
        content = p.read_text(encoding="utf-8")
        assert "Entry 1" in content and "Entry 2" in content
        assert content.count("Entry") == 2
    checks += 1; print("✅ 5 log_result appends — both entries appear in file")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX2 = _nb([
    _md("# Exercise 2 — send_alert\n\n"
        "`send_alert` is the notification layer: it prints to stdout when "
        "no webhook is configured, and POSTs to a webhook URL when one is "
        "provided. For paper trading, the stdout path is sufficient. "
        "The webhook path enables Slack, Discord, or any other notification "
        "system with a single URL."),
    _code(_P_BASE + """\

def send_alert(message, webhook_url=None):
    \"\"\"Send an alert via webhook or stdout.

    If webhook_url is None:
      print(f"[ALERT] {message}") and return True.

    If webhook_url is provided:
      POST JSON {\"text\": message} with requests.post(webhook_url, ..., timeout=5).
      Return resp.ok on success; return False on any exception.

    Returns:
        bool
    \"\"\"
    # TODO: ~8 lines
    return False
"""),
    _md("### Checks"),
    _code("""\
from unittest.mock import patch
checks = 0

# 1 — webhook_url=None returns True
try:
    with patch("builtins.print"):
        result = send_alert("Test message", webhook_url=None)
    assert result is True
    checks += 1; print("✅ 1 send_alert(webhook=None) returns True")
except Exception as e:
    print("❌ 1:", e)

# 2 — webhook_url=None calls print with [ALERT] prefix
try:
    with patch("builtins.print") as mock_print:
        send_alert("Hello world", webhook_url=None)
    assert mock_print.called, "send_alert should call print"
    call_str = " ".join(str(a) for a in mock_print.call_args[0])
    assert "[ALERT]" in call_str, f"expected [ALERT] in: {call_str}"
    assert "Hello world" in call_str
    checks += 1; print("✅ 2 send_alert calls print with [ALERT] + message")
except Exception as e:
    print("❌ 2:", e)

# 3 — empty message: still returns True
try:
    with patch("builtins.print"):
        result = send_alert("", webhook_url=None)
    assert result is True
    checks += 1; print("✅ 3 empty message with webhook=None still returns True")
except Exception as e:
    print("❌ 3:", e)

# 4 — bad webhook URL: returns False (exception caught)
try:
    result = send_alert("Test", webhook_url="http://localhost:0/bad")
    assert result is False, f"bad URL should return False, got {result}"
    checks += 1; print("✅ 4 bad webhook URL → False (exception caught gracefully)")
except Exception as e:
    print("❌ 4:", e)

# 5 — two consecutive alerts: print called twice, with distinct messages
try:
    calls = []
    with patch("builtins.print", side_effect=lambda *a, **kw: calls.extend(a)):
        send_alert("Alert A", None)
        send_alert("Alert B", None)
    assert len(calls) == 2, f"expected 2 print calls, got {len(calls)}"
    combined = " ".join(str(c) for c in calls)
    assert "Alert A" in combined and "Alert B" in combined
    checks += 1; print("✅ 5 two alerts → print called twice with distinct messages")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX3 = _nb([
    _md("# Exercise 3 — next_run_time and seconds_until\n\n"
        "Scheduling requires knowing WHEN to act. `next_run_time` computes "
        "the next occurrence of a given clock time (today if not yet passed, "
        "tomorrow otherwise). `seconds_until` converts that datetime into "
        "a sleep duration. Together, they are the core of the scheduler loop."),
    _code(_P_BASE + """\

def next_run_time(run_time_str="16:00"):
    \"\"\"Next local datetime matching run_time_str (HH:MM).

    If the time has not yet passed today, returns today at that time.
    If it has already passed, returns tomorrow at that time.

    Steps:
      1. now = datetime.datetime.now()
      2. h, m = (int(x) for x in run_time_str.split(":"))
      3. target = now.replace(hour=h, minute=m, second=0, microsecond=0)
      4. if target <= now: target += datetime.timedelta(days=1)
      5. return target
    \"\"\"
    # TODO: ~5 lines
    return datetime.datetime.now()


def seconds_until(target_dt):
    \"\"\"Seconds from now until target_dt; 0.0 if already past.

    Steps:
      1. delta = target_dt - datetime.datetime.now()
      2. return max(0.0, delta.total_seconds())
    \"\"\"
    # TODO: 2 lines
    return 0.0
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — next_run_time returns a future datetime
try:
    t = next_run_time("16:00")
    now = datetime.datetime.now()
    assert isinstance(t, datetime.datetime)
    assert t > now, f"expected future time, got {t} vs now {now}"
    checks += 1; print("✅ 1 next_run_time returns a datetime in the future")
except Exception as e:
    print("❌ 1:", e)

# 2 — next_run_time hours and minutes match the requested time
try:
    t = next_run_time("09:30")
    assert t.hour == 9 and t.minute == 30, \
        f"expected HH=9, MM=30, got {t.hour}:{t.minute}"
    checks += 1; print("✅ 2 next_run_time(09:30) has hour=9, minute=30")
except Exception as e:
    print("❌ 2:", e)

# 3 — past time today → tomorrow
try:
    past_str = "00:01"      # almost certainly already past
    t = next_run_time(past_str)
    now = datetime.datetime.now()
    diff_days = (t.date() - now.date()).days
    assert diff_days <= 1, f"past time should roll to tomorrow, got {diff_days} days ahead"
    checks += 1; print("✅ 3 past time today → scheduled for tomorrow")
except Exception as e:
    print("❌ 3:", e)

# 4 — seconds_until future → positive
try:
    future = datetime.datetime.now() + datetime.timedelta(seconds=60)
    secs   = seconds_until(future)
    assert secs > 0, f"future target should give positive seconds, got {secs}"
    assert secs <= 61, f"should be ~60 seconds, got {secs}"
    checks += 1; print(f"✅ 4 seconds_until(+60s from now) ≈ {secs:.1f}s (positive)")
except Exception as e:
    print("❌ 4:", e)

# 5 — seconds_until past → 0.0
try:
    past = datetime.datetime.now() - datetime.timedelta(seconds=30)
    secs = seconds_until(past)
    assert secs == 0.0, f"past target should return 0.0, got {secs}"
    checks += 1; print("✅ 5 seconds_until(past) == 0.0")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX4 = _nb([
    _md("# Exercise 4 — run_daily_loop and _sleep_fn injection\n\n"
        "`run_daily_loop` is the production scheduler: it runs forever (or N "
        "times), waiting for the daily run_time between iterations. The "
        "`_sleep_fn` injection parameter makes it testable without any actual "
        "waiting — a lambda that does nothing replaces time.sleep. This is the "
        "same injection pattern used throughout the course."),
    _code(_P_BASE + """\

def next_run_time(run_time_str="16:00"):
    now = datetime.datetime.now()
    h, m = (int(x) for x in run_time_str.split(":"))
    target = now.replace(hour=h, minute=m, second=0, microsecond=0)
    if target <= now: target += datetime.timedelta(days=1)
    return target

def seconds_until(target_dt):
    delta = target_dt - datetime.datetime.now()
    return max(0.0, delta.total_seconds())


def run_daily_loop(bot_fn, run_time="16:00", max_iterations=None,
                   _sleep_fn=None):
    \"\"\"Run bot_fn once per day at run_time.

    Algorithm:
      if _sleep_fn is None: _sleep_fn = time.sleep
      count = 0
      while max_iterations is None or count < max_iterations:
          _sleep_fn(seconds_until(next_run_time(run_time)))
          bot_fn()
          count += 1
      return count

    Returns:
        int — number of times bot_fn was called
    \"\"\"
    import time
    if _sleep_fn is None: _sleep_fn = time.sleep
    # TODO: ~5 lines
    return 0
"""),
    _md("### Checks"),
    _code("""\
checks = 0
NO_SLEEP = lambda s: None   # skip all waits

# 1 — max_iterations=1 calls bot_fn once
try:
    calls = []
    count = run_daily_loop(lambda: calls.append(1), max_iterations=1,
                           _sleep_fn=NO_SLEEP)
    assert len(calls) == 1, f"expected 1 call, got {len(calls)}"
    assert count == 1
    checks += 1; print("✅ 1 max_iterations=1 → bot_fn called once, returns 1")
except Exception as e:
    print("❌ 1:", e)

# 2 — max_iterations=5 calls bot_fn five times
try:
    calls = []
    count = run_daily_loop(lambda: calls.append(1), max_iterations=5,
                           _sleep_fn=NO_SLEEP)
    assert len(calls) == 5, f"expected 5 calls, got {len(calls)}"
    assert count == 5
    checks += 1; print("✅ 2 max_iterations=5 → bot_fn called 5 times, returns 5")
except Exception as e:
    print("❌ 2:", e)

# 3 — _sleep_fn is called with a non-negative number
try:
    slept = []
    run_daily_loop(lambda: None, max_iterations=3,
                   _sleep_fn=lambda s: slept.append(s))
    assert len(slept) == 3
    assert all(s >= 0 for s in slept), f"sleep times should be ≥ 0, got {slept}"
    checks += 1; print(f"✅ 3 _sleep_fn called 3× with non-negative seconds: {[round(s,1) for s in slept]}")
except Exception as e:
    print("❌ 3:", e)

# 4 — bot_fn exception propagates (loop does not swallow errors)
try:
    def failing_fn():
        raise ValueError("intentional error")
    try:
        run_daily_loop(failing_fn, max_iterations=1, _sleep_fn=NO_SLEEP)
        print("❌ 4: expected ValueError to propagate")
    except ValueError as ve:
        assert "intentional error" in str(ve)
        checks += 1; print("✅ 4 bot_fn exceptions propagate out of run_daily_loop")
except Exception as e:
    print("❌ 4:", e)

# 5 — max_iterations=0 calls bot_fn zero times
try:
    calls = []
    count = run_daily_loop(lambda: calls.append(1), max_iterations=0,
                           _sleep_fn=NO_SLEEP)
    assert len(calls) == 0 and count == 0
    checks += 1; print("✅ 5 max_iterations=0 → bot_fn never called, returns 0")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX5 = _nb([
    _md("# Exercise 5 — BotRunner end-to-end\n\n"
        "`BotRunner` is the complete daily bot: run once, log the result, "
        "alert on trades. It tracks how many times it has run and exposes "
        "`read_log()` so you can inspect the full session history. "
        "This exercise runs two strategies and compares their log entries."),
    _code(_P_BASE + _P_TRADER + _P_RUNNER + """\

class BotRunner:
    \"\"\"Stateful daily-bot wrapper.\"\"\"

    def __init__(self, log_path, webhook_url=None, run_time="16:00"):
        self.log_path    = pathlib.Path(log_path)
        self.webhook_url = webhook_url
        self.run_time    = run_time
        self._run_count  = 0

    def run_once(self, df, signals, initial_cash=10_000.0, fraction=1.0):
        \"\"\"Run the full pipeline: trade → log → alert.

        Steps:
          1. result = run_paper_trader(df, signals, initial_cash, fraction)
          2. report = format_report(result)
          3. log_result(report, self.log_path)
          4. if result["n_trades"] > 0: send_alert(...)
          5. self._run_count += 1
          6. result["report"] = report; return result
        \"\"\"
        # TODO: ~7 lines
        return {}

    def run_count(self):
        # TODO: return self._run_count
        return 0

    def read_log(self):
        if not self.log_path.exists(): return ""
        return self.log_path.read_text(encoding="utf-8")
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — run_once returns dict with "report" key
try:
    df  = _synthetic()
    sig = pd.Series(1, index=df.index)
    with tempfile.TemporaryDirectory() as td:
        runner = BotRunner(pathlib.Path(td) / "bot.log")
        result = runner.run_once(df, sig)
    assert isinstance(result, dict)
    assert "report" in result, "result should have 'report' key"
    assert isinstance(result["report"], str) and len(result["report"]) > 20
    checks += 1; print("✅ 1 run_once returns dict with non-empty 'report' key")
except Exception as e:
    print("❌ 1:", e)

# 2 — run_once writes to log file
try:
    df  = _synthetic()
    sig = pd.Series(1, index=df.index)
    with tempfile.TemporaryDirectory() as td:
        log_p  = pathlib.Path(td) / "bot.log"
        runner = BotRunner(log_p)
        runner.run_once(df, sig)
        assert log_p.exists(), "log file should be created"
        content = log_p.read_text()
        assert "Paper Trading Report" in content
        checks += 1; print("✅ 2 run_once writes to log file")
except Exception as e:
    print("❌ 2:", e)

# 3 — run_count increments each call
try:
    df  = _synthetic()
    sig = pd.Series(1, index=df.index)
    with tempfile.TemporaryDirectory() as td:
        runner = BotRunner(pathlib.Path(td) / "bot.log")
        assert runner.run_count() == 0
        runner.run_once(df, sig)
        assert runner.run_count() == 1
        runner.run_once(df, sig)
        assert runner.run_count() == 2
    checks += 1; print("✅ 3 run_count increments correctly: 0 → 1 → 2")
except Exception as e:
    print("❌ 3:", e)

# 4 — read_log returns empty string before first run
try:
    with tempfile.TemporaryDirectory() as td:
        runner = BotRunner(pathlib.Path(td) / "bot.log")
        assert runner.read_log() == ""
    checks += 1; print("✅ 4 read_log() returns '' before any run")
except Exception as e:
    print("❌ 4:", e)

# 5 — read_log grows with multiple runs
try:
    df   = _synthetic()
    sig1 = pd.Series(1, index=df.index)
    sig2 = pd.Series(0, index=df.index)
    with tempfile.TemporaryDirectory() as td:
        runner = BotRunner(pathlib.Path(td) / "bot.log")
        runner.run_once(df, sig1)
        runner.run_once(df, sig2)
        log    = runner.read_log()
        n_entries = log.count("=== Paper Trading Report ===")
        assert n_entries == 2, f"expected 2 report entries in log, got {n_entries}"
    checks += 1; print("✅ 5 read_log() has 2 report entries after 2 runs")
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
day: "096"
lesson: 1
title: "From Bot to Running Service"
slides:
  - type: title
    heading: "The Trading Bot II"
    subheading: "Scheduling, logging, and alerting"
    narration: >
      Day 96. Yesterday you built the bot logic — the paper-trading core.
      Today you build the operational wrapper: the code that makes the bot
      run automatically every day, write a log of what it did, and notify
      you when it takes a position. A bot that runs once is a script. A bot
      that runs reliably every day, logs its decisions, and alerts you when
      something happens is a service.

  - type: concept
    label: "Three pillars"
    heading: "The Three Pillars of a Running Bot"
    body: >
      Scheduling, logging, and alerting — the same three pillars in every
      production automated system.
    bullets:
      - "Scheduling: WHEN does the bot run? (daily at market close)"
      - "Logging: WHAT did it decide? (persistent, append-only record)"
      - "Alerting: WHO needs to know? (trade entries, exits, errors)"
      - "Without scheduling: you must run it manually"
      - "Without logging: you cannot audit or debug past behavior"
      - "Without alerting: you cannot react to positions in near-real-time"
    narration: >
      These three pillars are not unique to trading bots. Any automated process
      that runs without direct human interaction needs all three. Scheduling
      ensures the process runs on time. Logging creates the audit trail. Alerting
      closes the loop — it converts the autonomous system back into a human-in-the-
      loop system for the decisions that matter most. The pattern applies to
      every bot, pipeline, and agent you will ever build.

  - type: concept
    label: "Append-only log"
    heading: "Why Append-Only Logging?"
    body: >
      Never overwrite a log file — append to it.
    bullets:
      - "Overwriting: you lose all history every run — useless for debugging"
      - "Appending: every session adds one entry — full audit trail"
      - "open(path, 'a'): append mode; creates the file if it does not exist"
      - "Each entry has a timestamp so you can tell sessions apart"
      - "Log files are the primary forensic tool when something goes wrong"
    narration: >
      A log file written in append mode is an append-only journal of every
      bot run. If the strategy starts losing money on Thursday, you can read
      the log and see exactly what signals the bot received, what trades it
      executed, and what the equity curve looked like. Without the log, you
      have no way to determine whether the loss was due to a market event,
      a strategy bug, or a data quality issue. The append-only pattern also
      means the log is safe to read concurrently — there is never a partial
      overwrite.

  - type: exercise
    heading: "Exercise 1 — log_result and format_log_entry"
    prompt: >
      Implement format_log_entry(report_text) to prepend a YYYY-MM-DD HH:MM:SS
      timestamp header. Implement log_result(report_text, path) to append
      format_log_entry output to a file using open(path, "a"). Create parent
      directories with path.parent.mkdir(parents=True, exist_ok=True).
    hint: >
      ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"). The "a" mode
      in open() creates the file if it does not exist. Check 5 calls log_result
      twice and verifies both entries appear — the append mode test.
    narration: >
      Two functions, about ten lines total. The critical detail is the open mode:
      "a" not "w". The format string "%Y-%m-%d %H:%M:%S" produces "2025-01-15 16:00:00"
      — a human-readable timestamp that sorts lexicographically by time, making the
      log easy to search and parse later.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "Append-only logs: open(path, 'a') — never overwrite"
      - "format_log_entry: adds timestamp header to report"
      - "log_result: creates file (and dirs) if needed, appends entry"
      - "datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')"
      - "Next: send_alert — the notification layer"
    narration: >
      Logging is done. Next: alerting. The alert tells you immediately when
      the bot takes a position — so you can monitor the real-money equivalent
      or override a signal that looks wrong.
""",

    """\
day: "096"
lesson: 2
title: "Alerting with send_alert"
slides:
  - type: title
    heading: "Alerting"
    subheading: "Know immediately when your bot acts"
    narration: >
      An alert is a push notification from your bot to you. Without alerts,
      you must actively check the log to know what the bot did. With alerts,
      the bot notifies you the moment it buys or sells. For a paper-trading bot,
      a print statement is sufficient. For a production bot, you would connect
      it to Slack, Discord, or a custom webhook — but the interface is identical.

  - type: code
    label: "send_alert"
    heading: "Webhook or Print — Same Interface"
    body: >
      None webhook → stdout. URL webhook → HTTP POST.
    code: |
      def send_alert(message, webhook_url=None):
          if webhook_url is None:
              print(f"[ALERT] {message}")
              return True
          try:
              import requests
              resp = requests.post(webhook_url,
                                   json={"text": message}, timeout=5)
              return resp.ok
          except Exception:
              return False
    narration: >
      The two-branch design is the production pattern for notification systems.
      During development, webhook_url=None means you see the alert on screen.
      In production, a Slack incoming webhook URL sends the same message to a
      channel. The try/except ensures that a network failure does not crash the
      bot — the alert is best-effort, not a hard requirement. The bot logs the
      result regardless; the alert is just a convenience.

  - type: concept
    label: "Alert policy"
    heading: "When to Alert"
    body: >
      Alert on decisions that require human awareness, not on every heartbeat.
    bullets:
      - "ALWAYS alert: new trade entry (BUY) — capital is now at risk"
      - "ALWAYS alert: trade exit (SELL) — position closed, profit/loss realized"
      - "CONSIDER alerting: large drawdown, strategy error, data anomaly"
      - "NEVER alert: routine hold — no decision was made"
      - "BotRunner sends alert when n_trades > 0 (entry or exit occurred)"
    narration: >
      Alert fatigue is a real problem. If your bot sends an alert every time it
      runs — even when nothing happened — you will start ignoring the alerts.
      Then when something important happens, you will miss it. The BotRunner
      only alerts when trades were executed: when the bot bought or sold. A daily
      run that held the previous position generates no alert. This keeps the
      signal-to-noise ratio high.

  - type: exercise
    heading: "Exercise 2 — send_alert"
    prompt: >
      Implement send_alert(message, webhook_url=None). If webhook_url is None:
      print f"[ALERT] {message}" and return True. If webhook_url is provided:
      try requests.post(webhook_url, json={"text": message}, timeout=5);
      return resp.ok. Catch all exceptions and return False.
    hint: >
      Check 4 uses "http://localhost:0/bad" as the webhook URL — the port 0
      ensures a connection failure, testing the exception path. Use a bare
      except Exception: return False (not except requests.exceptions.RequestException
      — that requires requests to be imported at the outer scope).
    narration: >
      Eight lines. The key insight is the exception handling: if any error occurs
      (connection refused, timeout, DNS failure), return False instead of crashing.
      The bot must keep running even if the notification fails — a missed alert
      is much better than a stopped bot.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "send_alert: print (dev) or webhook POST (prod) — same interface"
      - "Alert policy: only alert on trades, not on holds"
      - "Exception handling: return False on webhook failure, never crash"
      - "timeout=5: don't block the bot waiting for a slow notification service"
      - "Next: scheduling — when does the bot run?"
    narration: >
      Alerting is done. Next: the scheduler — the code that keeps the bot
      waking up at market close every day without manual intervention.
""",

    """\
day: "096"
lesson: 3
title: "Scheduling: next_run_time and run_daily_loop"
slides:
  - type: title
    heading: "Scheduling"
    subheading: "Make the bot run itself"
    narration: >
      A bot that you have to start manually is not a bot — it is a script.
      A bot that runs automatically at the same time every day, without any
      human action, is a service. The scheduler answers the question: how long
      until the next run? Then it sleeps for that duration and wakes up to run.
      Two functions, ten lines, infinite automation.

  - type: code
    label: "next_run_time"
    heading: "next_run_time: When Is the Next Run?"
    body: >
      If 16:00 has passed today, schedule for tomorrow.
    code: |
      def next_run_time(run_time_str="16:00"):
          now   = datetime.datetime.now()
          h, m  = (int(x) for x in run_time_str.split(":"))
          today = now.replace(hour=h, minute=m, second=0, microsecond=0)
          if today <= now:          # already passed today
              today += datetime.timedelta(days=1)
          return today

      def seconds_until(target_dt):
          delta = target_dt - datetime.datetime.now()
          return max(0.0, delta.total_seconds())
    narration: >
      next_run_time uses datetime.replace() to construct today's target time
      from the current date. If that time is already in the past (the bot
      starts after 16:00 on the first day), it adds one day. This guarantees
      the bot always returns a future time. seconds_until converts the timedelta
      to a float, clamped to zero so a past target never produces a negative
      sleep duration.

  - type: code
    label: "run_daily_loop"
    heading: "run_daily_loop: The Infinite Scheduler"
    body: >
      Sleep until the target time; call bot_fn; repeat.
    code: |
      def run_daily_loop(bot_fn, run_time="16:00", max_iterations=None,
                         _sleep_fn=None):
          import time
          if _sleep_fn is None:
              _sleep_fn = time.sleep
          count = 0
          while max_iterations is None or count < max_iterations:
              _sleep_fn(seconds_until(next_run_time(run_time)))
              bot_fn()
              count += 1
          return count
    narration: >
      The injection pattern: _sleep_fn defaults to time.sleep (blocks until the
      target time), but in tests it is replaced with lambda s: None (no wait).
      This is the same pattern used throughout the course for network calls and
      LLM calls. max_iterations=None means run forever; max_iterations=N means
      run exactly N times, then stop. The function returns the run count — useful
      for testing and monitoring.

  - type: concept
    label: "Scheduling in production"
    heading: "Beyond run_daily_loop: Production Scheduling"
    body: >
      For real systems, use cron or a managed scheduler.
    bullets:
      - "run_daily_loop is educational — it blocks the process while sleeping"
      - "Production: cron (Linux/Mac), Task Scheduler (Windows), or APScheduler"
      - "Cloud: AWS EventBridge, GCP Cloud Scheduler, GitHub Actions workflow"
      - "Advantage: the bot process only runs when needed (no wasted memory)"
      - "The bot logic (bot_fn) is unchanged — only the trigger mechanism changes"
    narration: >
      run_daily_loop is the simplest possible scheduler: a loop that sleeps.
      It works fine for a single bot on a personal machine. For production
      deployments, you would use cron — a system service that runs commands
      at scheduled times. A cron entry of "0 16 * * 1-5 python bot.py" runs
      the bot at 16:00 Monday through Friday without any Python sleeping.
      The bot code remains identical; only the trigger changes.

  - type: exercise
    heading: "Exercises 3 and 4 — Scheduling"
    prompt: >
      Exercise 3: implement next_run_time and seconds_until.
      Exercise 4: implement run_daily_loop using the _sleep_fn injection.
      Check 3 in Ex4 verifies that _sleep_fn is called with non-negative values.
      Check 5 verifies max_iterations=0 → bot_fn never called → returns 0.
    hint: >
      Ex4 check 4: the failing_fn raises ValueError. run_daily_loop should NOT
      catch exceptions from bot_fn — let them propagate. This is intentional:
      an exception in the trading logic should be visible, not silently swallowed.
    narration: >
      Both exercises are under fifteen lines total. The key concepts are the
      injection pattern (same as every LLM/network call in the course) and the
      while loop condition (None → forever; int → finite). The failing_fn check
      is a reminder of the principle: only catch exceptions you know how to
      handle. Everything else propagates.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "next_run_time: today or tomorrow at HH:MM, always future"
      - "seconds_until: timedelta → float, clamped to 0"
      - "run_daily_loop: sleep → call → count, with _sleep_fn injection"
      - "Production scheduling: cron or managed service over run_daily_loop"
      - "Next: BotRunner — the complete stateful wrapper"
    narration: >
      Scheduling is done. Next: BotRunner, which combines all three pillars —
      paper trading, logging, and alerting — into a single stateful class.
""",

    """\
day: "096"
lesson: 4
title: "BotRunner — The Complete Service"
slides:
  - type: title
    heading: "BotRunner"
    subheading: "One class, one call, full automation"
    narration: >
      BotRunner is the final integration layer. It owns the log file path,
      the webhook URL, and the run count. A single call to run_once executes
      the full pipeline: trade, log, alert. At the end of 30 days of paper
      trading, you have a log file with 30 entries, a trade history in each
      PaperAccount, and a clear record of every decision the bot made.

  - type: code
    label: "BotRunner"
    heading: "Twelve Lines"
    body: >
      run → log → alert → count → return.
    code: |
      class BotRunner:
          def __init__(self, log_path, webhook_url=None, run_time="16:00"):
              self.log_path    = pathlib.Path(log_path)
              self.webhook_url = webhook_url
              self.run_time    = run_time
              self._run_count  = 0

          def run_once(self, df, signals, initial_cash=10_000.0, fraction=1.0):
              from paper_trader import run_paper_trader, format_report
              result = run_paper_trader(df, signals, initial_cash, fraction)
              report = format_report(result)
              log_result(report, self.log_path)
              if result["n_trades"] > 0:
                  send_alert(f"BOT: {result['n_trades']} trade(s) — "
                             f"return {result['total_return']:.2%}",
                             self.webhook_url)
              self._run_count += 1
              result["report"] = report
              return result

          def run_count(self): return self._run_count
          def read_log(self):
              return ("" if not self.log_path.exists()
                      else self.log_path.read_text(encoding="utf-8"))
    narration: >
      The lazy import inside run_once (from paper_trader import ...) means
      bot_runner.py can be imported without paper_trader.py being on the path.
      The module loads cleanly; the dependency is resolved only when run_once
      is actually called. This is the same pattern used in days 92–94 for Ollama:
      import inside the else branch, lazy, not at module level.

  - type: concept
    label: "State tracking"
    heading: "Why Track run_count?"
    body: >
      run_count is the simplest form of operational telemetry.
    bullets:
      - "run_count=0: bot has never executed (check that the scheduler started)"
      - "run_count=N: N successful iterations (N × initial_cash managed)"
      - "run_count unchanged after an exception: useful for monitoring"
      - "Extend: add last_run_time, last_result, error_count for richer telemetry"
      - "For now: run_count is sufficient to verify the bot is running"
    narration: >
      In a production system you would send run_count (and other metrics) to
      a monitoring service like Grafana, DataDog, or Prometheus. But even just
      checking runner.run_count() > 0 before going home tells you the bot ran
      at least once today. Simple counts are often the most reliable monitoring
      signal — they are hard to get wrong and easy to understand.

  - type: exercise
    heading: "Exercise 5 — BotRunner end-to-end"
    prompt: >
      Implement BotRunner. run_once: call run_paper_trader, format_report,
      log_result, send_alert (if n_trades > 0), increment run_count,
      add result["report"]. run_count: return self._run_count.
      read_log: return file contents or "" if not yet created.
    hint: >
      Check 5 calls run_once twice with different signals and verifies the log
      has 2 report entries. Use content.count("=== Paper Trading Report ===") == 2.
      The inline _P_TRADER prelude provides run_paper_trader and format_report
      directly so paper_trader.py does not need to be on the path.
    narration: >
      This is the last exercise of the course's bot section. After implementing
      BotRunner, the entire Section 7 system is operational. Exercise 5 runs
      two strategies end-to-end and reads the log back — the same workflow a
      real operator would use to review the bot's overnight decisions.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "BotRunner: log_path, webhook_url, run_time, _run_count"
      - "run_once: trade → log → alert → count → return with 'report' key"
      - "Lazy import inside run_once: bot_runner loads without paper_trader"
      - "read_log: returns '' before first run; grows with each run"
      - "Next: Day 97 — Productizing Your AI (packaging and docs)"
    narration: >
      Day 96 is complete. The paper-trading bot is fully operational: it runs
      daily, logs every decision, and alerts on trades. The next three days
      shift focus to productizing and launching: how to package what you have
      built into something others can use, pay for, and find.
""",

    """\
day: "096"
lesson: 5
title: "The Full Automated Pipeline"
slides:
  - type: title
    heading: "Putting It All Together"
    subheading: "From raw data to automated daily decisions"
    narration: >
      The fifth lesson shows the complete automated pipeline that Days 89–96
      have been building. Market data → indicators → strategy → risk → paper
      trade → log → alert. This is the bot in its final form. The only step
      missing for real money trading is replacing the paper_trader's Close
      price with a live feed and replacing account.buy() with a broker API call.

  - type: code
    label: "Full pipeline"
    heading: "The Eleven-Line Bot"
    body: >
      From market data to logged result — eleven lines.
    code: |
      # One-time setup
      runner = BotRunner("logs/trading.log", webhook_url=None)

      # Daily bot function (called by run_daily_loop at market close)
      def daily_bot():
          df      = add_indicators(store.load("AAPL"))
          raw_sig = combined_signal(df)
          rm      = RiskManager(stop_pct=0.05, drawdown_limit=-0.20)
          sig     = rm.filter(raw_sig, df["Close"])
          runner.run_once(df, sig, initial_cash=10_000.0)

      # Start the scheduler (blocks; runs daily at 16:00)
      run_daily_loop(daily_bot, run_time="16:00")
    narration: >
      Eleven lines. This is the complete system. Every module from Days 89–96
      appears: market_data (store.load), indicators (add_indicators, combined_signal),
      risk (RiskManager), paper_trader (inside run_once), bot_runner (BotRunner,
      run_daily_loop). The daily_bot function is the bot_fn that run_daily_loop
      calls every day at 16:00. In a real deployment, you would also add error
      handling around daily_bot so a single failure doesn't stop the scheduler.

  - type: concept
    label: "From paper to live"
    heading: "The Step from Paper to Live Trading"
    body: >
      One module changes. Everything else stays the same.
    bullets:
      - "Paper: run_paper_trader → simulates trades in Python memory"
      - "Live: replace with broker API calls (Alpaca, Interactive Brokers, etc.)"
      - "Signal generation: unchanged — same strategy, same risk filter"
      - "Logging: unchanged — same log_result call"
      - "Alerting: unchanged — same send_alert call"
      - "Only paper_trader.py is swapped; bot_runner.py is production-ready today"
    narration: >
      This is the payoff for the modular design. Going from paper to live trading
      means writing one new module — a broker adapter that replaces PaperAccount.
      The broker adapter implements the same interface: buy(date, price), sell(date,
      price), portfolio_value(price). Everything upstream (signals, risk) and
      downstream (logging, alerting) remains unchanged. You have built a production-
      grade architecture in 96 days.

  - type: exercise
    heading: "Project — 5-Day Paper Trading Simulation"
    prompt: >
      Simulate 5 daily bot runs using run_daily_loop with max_iterations=5
      and _sleep_fn=lambda s: None. Use a new BotRunner each call? No —
      the same BotRunner accumulates 5 log entries. The project runs three
      strategies and compares their final log files.
    hint: >
      Use tempfile.TemporaryDirectory() for the log path. At the end, call
      runner.read_log() and count "=== Paper Trading Report ===" entries to
      verify 5 runs were logged. The solution asserts run_count == 5.
    narration: >
      The project simulates five market-close runs of the bot in seconds.
      After completing it, you have a complete automated trading system:
      a strategy, risk management, a paper-trading engine, a scheduler, a
      logger, and an alerting system. The final three days package and launch
      this and your other course projects as products.

  - type: summary
    heading: "Day 96 and Section 7 Bot Complete"
    bullets:
      - "format_log_entry + log_result: append-only session journal"
      - "send_alert: webhook or stdout, same interface"
      - "next_run_time + seconds_until + run_daily_loop: minimal scheduler"
      - "BotRunner: stateful wrapper, run_once → log → alert → count"
      - "Full pipeline: 11 lines from data to daily automation"
      - "Paper → live: only paper_trader.py changes"
    narration: >
      Days 95 and 96 together form the complete paper-trading bot. Section 7
      is now three days from completion. Days 97–99 shift to productizing and
      launching the work from the entire bootcamp. Day 100 is the final capstone:
      your own AI product, fully deployed.
""",
]

# ══════════════════════════════════════════════════════════════════════════════
# Project + solution
# ══════════════════════════════════════════════════════════════════════════════

_FULL_P = _P_BASE + _P_TRADER + _P_RUNNER + _P_BOT_CLASS

PROJECT_NB = _nb([
    _md(f"# Day {DAY} Project — 5-Day Paper Trading Simulation\n\n"
        "Simulate 5 consecutive daily bot runs using `run_daily_loop` with "
        "`max_iterations=5` and `_sleep_fn=lambda s: None` (no actual waiting). "
        "Verify that the log file grows with each run and `run_count` reaches 5."),
    _code(_FULL_P),
    _code("""\
import tempfile

df  = _synthetic(n=252)
sig = pd.Series(1, index=df.index)   # always-long for this demo

with tempfile.TemporaryDirectory() as td:
    log_p  = pathlib.Path(td) / "bot.log"
    runner = BotRunner(log_p)

    def daily_bot():
        runner.run_once(df, sig, initial_cash=10_000.0)

    count = run_daily_loop(daily_bot, max_iterations=5, _sleep_fn=lambda s: None)
    log   = runner.read_log()
    n_entries = log.count("=== Paper Trading Report ===")

    print(f"Runs completed : {count}")
    print(f"Log entries    : {n_entries}")
    print(f"run_count      : {runner.run_count()}")
    print()
    print("--- Log preview (first 800 chars) ---")
    print(log[:800])
"""),
])

SOLUTION_NB = _nb([
    _md(f"# Day {DAY} Solution — 5-Day Paper Trading Simulation"),
    _code(_FULL_P),
    _code("""\
import tempfile

df  = _synthetic(n=252)
sig = pd.Series(1, index=df.index)

with tempfile.TemporaryDirectory() as td:
    log_p  = pathlib.Path(td) / "bot.log"
    runner = BotRunner(log_p)

    def daily_bot():
        runner.run_once(df, sig, initial_cash=10_000.0)

    count = run_daily_loop(daily_bot, max_iterations=5, _sleep_fn=lambda s: None)
    log   = runner.read_log()
    n_entries = log.count("=== Paper Trading Report ===")

    # Assertions
    assert count          == 5,  f"run_daily_loop should return 5, got {count}"
    assert runner.run_count() == 5, "run_count should be 5"
    assert n_entries      == 5,  f"expected 5 log entries, got {n_entries}"
    assert log_p.exists(),        "log file should exist"

    print(f"Runs completed : {count}")
    print(f"Log entries    : {n_entries}")
    print(f"run_count      : {runner.run_count()}")
    print()
    print(log[:800])
    print("\\nSolution smoke-test passed.")
"""),
])

# ══════════════════════════════════════════════════════════════════════════════
# Gate
# ══════════════════════════════════════════════════════════════════════════════

GATE_PY = f"""\
import importlib.util, sys, math, pathlib, tempfile
import pandas as pd

# Make paper_trader importable (needed by BotRunner.run_once)
sys.path.insert(0, str(pathlib.Path(r"{DIR}").parent / "day_095"))

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

import re, datetime

# format_log_entry: includes report text and timestamp
sample = "=== Paper Trading Report ===\\nTotal return: 5.00%"
entry  = mod.format_log_entry(sample)
assert isinstance(entry, str)
assert sample in entry
assert re.search(r"\\d{{4}}-\\d{{2}}-\\d{{2}} \\d{{2}}:\\d{{2}}:\\d{{2}}", entry), \
    f"no timestamp pattern in: {{entry}}"

# log_result: creates file, appends
with tempfile.TemporaryDirectory() as td:
    p = pathlib.Path(td) / "sub" / "bot.log"
    mod.log_result("Entry A", p)
    mod.log_result("Entry B", p)
    content = p.read_text(encoding="utf-8")
    assert "Entry A" in content and "Entry B" in content
    assert content.count("Entry") == 2

# send_alert: None webhook → True
assert mod.send_alert("hello", webhook_url=None) is True
# bad URL → False
assert mod.send_alert("test", webhook_url="http://localhost:0/bad") is False

# next_run_time: returns future datetime
t = mod.next_run_time("16:00")
assert isinstance(t, datetime.datetime) and t > datetime.datetime.now()
assert t.hour == 16 and t.minute == 0

# seconds_until: future → positive; past → 0
future = datetime.datetime.now() + datetime.timedelta(seconds=60)
secs   = mod.seconds_until(future)
assert 0 < secs <= 61
past   = datetime.datetime.now() - datetime.timedelta(seconds=30)
assert mod.seconds_until(past) == 0.0

# run_daily_loop: max_iterations=3, no sleep
calls = []
count = mod.run_daily_loop(lambda: calls.append(1), max_iterations=3,
                           _sleep_fn=lambda s: None)
assert len(calls) == 3 and count == 3

# run_daily_loop: max_iterations=0
count0 = mod.run_daily_loop(lambda: None, max_iterations=0,
                            _sleep_fn=lambda s: None)
assert count0 == 0

# BotRunner
sig_long = pd.Series(1, index=df.index)
sig_flat = pd.Series(0, index=df.index)
with tempfile.TemporaryDirectory() as td:
    log_p  = pathlib.Path(td) / "bot.log"
    runner = mod.BotRunner(log_p)

    # read_log before first run → ""
    assert runner.read_log() == ""
    assert runner.run_count() == 0

    # run_once: returns dict with "report" key
    result = runner.run_once(df, sig_long)
    assert isinstance(result, dict)
    assert "report" in result and len(result["report"]) > 20
    assert runner.run_count() == 1
    assert log_p.exists()

    # run_once second call: run_count increments
    runner.run_once(df, sig_flat)
    assert runner.run_count() == 2

    # read_log: two entries
    log = runner.read_log()
    assert log.count("=== Paper Trading Report ===") == 2

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
