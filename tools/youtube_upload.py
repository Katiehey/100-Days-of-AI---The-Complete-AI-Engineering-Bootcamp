"""
Automated YouTube upload for rendered lesson videos.

Reads OAuth creds from .env (gitignored), uploads a rendered final video as
**unlisted**, writes the returned video ID into docs/videos.json, and regenerates
the site manifest — so a lesson goes from "rendered" to "playable on the site"
with one command.

Usage:
    conda activate ai-course
    python tools/youtube_upload.py day_001_lesson_01     # one lesson
    python tools/youtube_upload.py --day 1               # all 5 lessons of a day
    python tools/youtube_upload.py --all-local           # every final/*.mp4 present
    python tools/youtube_upload.py day_001_lesson_01 --force   # re-upload even if an ID exists

Looks for the video at 00_pipeline/final/<lesson_id>_final.mp4.
Requires only `requests`. The refresh token must carry the
https://www.googleapis.com/auth/youtube.upload scope.
"""

import argparse
import json
import os
import re
import subprocess
import sys

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = os.path.join(ROOT, ".env")
FINAL_DIR = os.path.join(ROOT, "00_pipeline", "final")
DOCS = os.path.join(ROOT, "docs")
VIDEOS_JSON = os.path.join(DOCS, "videos.json")
COURSE_JSON = os.path.join(DOCS, "course.json")

TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = ("https://www.googleapis.com/upload/youtube/v3/videos"
              "?uploadType=resumable&part=snippet,status")


def github_slug() -> str:
    """Return 'owner/repo' from the origin remote (for authenticated push URLs)."""
    try:
        url = subprocess.run(
            ["git", "-C", ROOT, "remote", "get-url", "origin"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except subprocess.CalledProcessError:
        return "OWNER/REPO"
    m = re.search(r"github\.com[:/](.+?)(?:\.git)?$", url)
    return m.group(1) if m else "OWNER/REPO"


# ── .env ─────────────────────────────────────────────────────────────────────

def load_env() -> dict:
    env = {}
    if os.path.exists(ENV):
        with open(ENV, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    # Allow real environment variables to override the file.
    for k in ("YOUTUBE_REFRESH_TOKEN", "YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET"):
        if os.environ.get(k):
            env[k] = os.environ[k]
    missing = [k for k in ("YOUTUBE_REFRESH_TOKEN", "YOUTUBE_CLIENT_ID",
                           "YOUTUBE_CLIENT_SECRET") if not env.get(k)]
    if missing:
        sys.exit(f"Missing in .env: {', '.join(missing)}")
    return env


# ── OAuth ────────────────────────────────────────────────────────────────────

def access_token(env: dict) -> str:
    r = requests.post(TOKEN_URL, data={
        "client_id": env["YOUTUBE_CLIENT_ID"],
        "client_secret": env["YOUTUBE_CLIENT_SECRET"],
        "refresh_token": env["YOUTUBE_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }, timeout=30)
    if r.status_code != 200:
        sys.exit(f"Token refresh failed ({r.status_code}): {r.text}")
    return r.json()["access_token"]


# ── Titles from the manifest ─────────────────────────────────────────────────

def lesson_meta(lesson_id: str) -> dict:
    """Return {day, day_title, num, title} for a lesson id, from course.json."""
    m = re.match(r"day_(\d+)_lesson_(\d+)", lesson_id)
    day_n, les_n = int(m.group(1)), int(m.group(2))
    if os.path.exists(COURSE_JSON):
        course = json.load(open(COURSE_JSON, encoding="utf-8"))
        for section in course["sections"]:
            for day in section["days"]:
                if day["day"] == day_n:
                    for les in day["lessons"]:
                        if les["num"] == les_n:
                            return {"day": day_n, "day_title": day["title"],
                                    "num": les_n, "title": les["title"]}
    return {"day": day_n, "day_title": f"Day {day_n}", "num": les_n,
            "title": f"Lesson {les_n}"}


def build_snippet(lesson_id: str) -> dict:
    meta = lesson_meta(lesson_id)
    title = f"Day {meta['day']} · L{meta['num']}: {meta['title']}"
    if len(title) > 100:
        title = title[:97] + "..."
    description = (
        f"{meta['day_title']} — Day {meta['day']}, Lesson {meta['num']}.\n\n"
        f"100 Days of AI — The Complete AI Engineering Bootcamp.\n"
        f"Lesson id: {lesson_id}"
    )
    return {
        "snippet": {
            "title": title,
            "description": description,
            "categoryId": "27",  # Education
        },
        "status": {
            "privacyStatus": "unlisted",
            "selfDeclaredMadeForKids": False,
        },
    }


# ── Upload (resumable, single PUT) ───────────────────────────────────────────

def upload_video(token: str, file_path: str, snippet: dict) -> str:
    size = os.path.getsize(file_path)
    init = requests.post(
        UPLOAD_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": "video/mp4",
            "X-Upload-Content-Length": str(size),
        },
        data=json.dumps(snippet),
        timeout=60,
    )
    if init.status_code not in (200, 201):
        sys.exit(f"Upload init failed ({init.status_code}): {init.text}")
    location = init.headers.get("Location")
    if not location:
        sys.exit("Upload init returned no Location header.")

    with open(file_path, "rb") as f:
        put = requests.put(
            location,
            headers={"Content-Type": "video/mp4", "Content-Length": str(size)},
            data=f,
            timeout=None,
        )
    if put.status_code not in (200, 201):
        sys.exit(f"Upload failed ({put.status_code}): {put.text}")
    return put.json()["id"]


# ── videos.json ──────────────────────────────────────────────────────────────

def load_videos() -> dict:
    if os.path.exists(VIDEOS_JSON):
        return json.load(open(VIDEOS_JSON, encoding="utf-8"))
    return {}


def save_videos(videos: dict) -> None:
    os.makedirs(DOCS, exist_ok=True)
    with open(VIDEOS_JSON, "w", encoding="utf-8") as f:
        json.dump(videos, f, indent=2, ensure_ascii=False)
        f.write("\n")


# ── Orchestration ────────────────────────────────────────────────────────────

def final_path(lesson_id: str) -> str:
    return os.path.join(FINAL_DIR, f"{lesson_id}_final.mp4")


def discover(args) -> list:
    if args.all_local:
        found = []
        if os.path.isdir(FINAL_DIR):
            for f in sorted(os.listdir(FINAL_DIR)):
                m = re.match(r"(day_\d+_lesson_\d+)_final\.mp4$", f)
                if m:
                    found.append(m.group(1))
        return found
    if args.day is not None:
        return [f"day_{args.day:03d}_lesson_{i:02d}" for i in range(1, 6)]
    return args.lessons


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("lessons", nargs="*", help="lesson ids, e.g. day_001_lesson_01")
    ap.add_argument("--day", type=int, help="upload all 5 lessons of this day")
    ap.add_argument("--all-local", action="store_true",
                    help="upload every 00_pipeline/final/*_final.mp4")
    ap.add_argument("--force", action="store_true",
                    help="re-upload even if videos.json already has an ID")
    ap.add_argument("--push", action="store_true",
                    help="git commit + push docs/videos.json & course.json after upload "
                         "(updates a GitHub Pages site with no further steps)")
    args = ap.parse_args()

    targets = discover(args)
    if not targets:
        ap.error("give a lesson id, --day N, or --all-local")

    env = load_env()
    videos = load_videos()
    token = access_token(env)
    print(f"Authenticated. {len(targets)} lesson(s) to process.\n")

    changed = False
    for lid in targets:
        path = final_path(lid)
        if not os.path.exists(path):
            print(f"  {lid}: SKIP — no rendered video at {os.path.relpath(path, ROOT)}")
            continue
        if videos.get(lid) and not args.force:
            print(f"  {lid}: SKIP — already uploaded ({videos[lid]}). Use --force to redo.")
            continue
        mb = os.path.getsize(path) / 1_000_000
        print(f"  {lid}: uploading ({mb:.1f} MB)...", flush=True)
        vid = upload_video(token, path, build_snippet(lid))
        videos[lid] = vid
        save_videos(videos)          # persist after each success
        changed = True
        print(f"  {lid}: done → https://youtu.be/{vid}")

    if changed:
        print("\nRegenerating site manifest...")
        subprocess.run([sys.executable, os.path.join(ROOT, "tools",
                        "build_site_manifest.py")], check=True)
    else:
        print("\nNothing uploaded.")

    # Always try to publish when --push: flushes any commit a previous run left
    # unpushed (e.g. if the push raced with another commit and failed).
    if args.push:
        git_push(targets)


def git_push(targets: list) -> None:
    """Commit docs changes, rebase on origin, and push. Never raises; masks the token.

    Rebasing first means a racing commit on main (e.g. a Colab 'Save in GitHub')
    can't cause a non-fast-forward failure that aborts a render loop.
    """
    token = os.environ.get("GITHUB_TOKEN")
    mask = (lambda s: s.replace(token, "***")) if token else (lambda s: s)

    def run(*cmd):
        return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)

    print("\nPublishing site update...")
    run("git", "add", "docs/videos.json", "docs/course.json")
    label = targets[0] if len(targets) == 1 else f"{len(targets)} lessons"
    run("git", "commit", "-m", f"site: add YouTube video(s) for {label}")  # no-op if nothing staged

    pull = run("git", "pull", "--rebase", "--autostash", "origin", "main")
    if pull.returncode != 0:
        print("  pull --rebase failed:\n  " + mask(pull.stderr).strip())
        return

    if token:
        push = run("git", "push", f"https://{token}@github.com/{github_slug()}.git", "HEAD:main")
    else:
        push = run("git", "push", "origin", "HEAD:main")
    if push.returncode != 0:
        print("  push failed:\n  " + mask(push.stderr).strip())
        return
    print("  pushed. GitHub Pages will rebuild shortly.")


if __name__ == "__main__":
    main()
