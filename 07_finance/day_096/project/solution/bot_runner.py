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
    return f"\n{bar}\n[{ts}]\n{bar}\n{report_text}"


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
        fh.write(entry + "\n")


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
