"""
Diagnose YouTube upload state — is it a quota limit, or a render/upload gap?

Answers two questions with no expensive API calls:

  1. Are you over the YouTube API quota RIGHT NOW?  A single channels.list call
     costs 1 unit (an upload costs ~1600). If you're over quota, even this cheap
     read fails with a 403 / "quotaExceeded" — so it's a reliable probe.
  2. For each lesson, what artifacts exist locally (talking head, final mp4) and
     is it already in docs/videos.json? This shows whether a lesson stopped at
     render or at upload.

Usage:
    conda activate ai-course
    python tools/youtube_diagnose.py --day 5      # inspect one day's 5 lessons
    python tools/youtube_diagnose.py              # quota probe + whole-course summary

Reuses the .env / OAuth logic from youtube_upload.py — nothing new to configure.
"""

import argparse
import os
import re

import requests

from youtube_upload import (
    ROOT, FINAL_DIR, VIDEOS_JSON,
    load_env, access_token, load_videos, final_path,
)

TALKING_DIR = os.path.join(ROOT, "00_pipeline", "talking_heads")
CHANNELS_URL = ("https://www.googleapis.com/youtube/v3/channels"
                "?part=snippet,status,contentDetails&mine=true")


def talking_head_path(lesson_id: str) -> str:
    return os.path.join(TALKING_DIR, f"{lesson_id}_talking_head.mp4")


def quota_probe(env: dict) -> None:
    """1-unit channels.list call. Distinguishes 'over quota' from other failures."""
    print("── YouTube quota / auth probe ──────────────────────────────")
    try:
        token = access_token(env)  # this itself will SystemExit on bad creds
    except SystemExit as e:
        print(f"  AUTH FAILED: {e}")
        print("  → Not a quota issue — your OAuth creds/refresh token are the problem.")
        return

    r = requests.get(CHANNELS_URL, headers={"Authorization": f"Bearer {token}"},
                     timeout=30)
    if r.status_code == 200:
        item = (r.json().get("items") or [{}])[0]
        title = item.get("snippet", {}).get("title", "?")
        print(f"  OK — authenticated as channel: {title!r}")
        print("  → Quota is NOT exhausted right now. Uploads should work;")
        print("    a stalled lesson stopped at render, not at the YouTube API.")
        return

    body = r.text.lower()
    if r.status_code == 403 and ("quota" in body or "ratelimit" in body):
        print(f"  403 quotaExceeded — you ARE over the daily quota ({r.status_code}).")
        print("  → Default is 10,000 units/day ≈ 6 uploads. Resets ~midnight")
        print("    US Pacific. Wait for reset or request a quota increase.")
    else:
        print(f"  Unexpected {r.status_code}: {r.text[:300]}")
        print("  → Not a clean quota signal; inspect the message above.")


def lesson_report(lesson_id: str, videos: dict) -> str:
    th = "TH✓" if os.path.exists(talking_head_path(lesson_id)) else "TH✗"
    fin = "FINAL✓" if os.path.exists(final_path(lesson_id)) else "FINAL✗"
    vid = videos.get(lesson_id)
    up = f"UP✓ https://youtu.be/{vid}" if vid else "UP✗"

    if vid:
        verdict = "uploaded"
    elif os.path.exists(final_path(lesson_id)):
        verdict = "rendered, NOT uploaded  ← re-run upload"
    elif os.path.exists(talking_head_path(lesson_id)):
        verdict = "lip-synced, NOT finalized  ← stopped at --finalize"
    else:
        verdict = "not rendered  ← stopped at/​before inference"
    return f"  {lesson_id}: {th:5} {fin:8} {up:40}  {verdict}"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--day", type=int, help="inspect this day's 5 lessons")
    args = ap.parse_args()

    env = load_env()
    quota_probe(env)

    videos = load_videos()
    print("\n── Render / upload state ───────────────────────────────────")
    if args.day is not None:
        for i in range(1, 6):
            print(lesson_report(f"day_{args.day:03d}_lesson_{i:02d}", videos))
    else:
        ids = set(videos)
        if os.path.isdir(FINAL_DIR):
            for f in os.listdir(FINAL_DIR):
                m = re.match(r"(day_\d+_lesson_\d+)_final\.mp4$", f)
                if m:
                    ids.add(m.group(1))
        for lid in sorted(ids):
            print(lesson_report(lid, videos))
        print(f"\n  Total in videos.json: {len(videos)}")


if __name__ == "__main__":
    main()
