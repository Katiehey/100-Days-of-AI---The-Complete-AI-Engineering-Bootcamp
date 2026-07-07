#!/usr/bin/env python3
"""
Per-day gate orchestrator — the single command that must go green before a day
reaches human review.

Runs, in order:
  #2  validate_day  — structure (deterministic, instant)
  #1  run_day       — execute + render (proves the code runs, YAML feeds pipeline)

Usage:
    python tools/check_day.py 2
    python tools/check_day.py 2 --fast      # slides only, skip slow audio
    python tools/check_day.py 2 --no-exec   # structure + render only
"""

import argparse
import sys

from validate_day import validate, end_of_section_reminder
from run_day import run


def main() -> int:
    ap = argparse.ArgumentParser(description="Full per-day gate: structure (#2) + execute/render (#1).")
    ap.add_argument("day", help="Day number, e.g. 2 or 002")
    ap.add_argument("--fast", action="store_true", help="slides only, skip TTS audio")
    ap.add_argument("--no-exec", action="store_true", help="render only, skip notebooks")
    args = ap.parse_args()
    try:
        day = int(args.day)
    except ValueError:
        print(f"Invalid day: {args.day!r}")
        return 2

    vok, vlines = validate(day)
    print("\n".join(vlines))
    print()
    rok, rlines = run(day, args.fast, args.no_exec)
    print("\n".join(rlines))

    ok = vok and rok
    bar = "=" * 52
    print(f"\n{bar}\nGATE {'PASSED ✅' if ok else 'FAILED ❌'} — Day {day:03d}"
          f"  (structure={'ok' if vok else 'FAIL'}, run={'ok' if rok else 'FAIL'})\n{bar}")

    if ok:
        reminder = end_of_section_reminder(day)
        if reminder:
            print(reminder)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
