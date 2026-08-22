"""
Build the course website manifest (docs/course.json) by scanning the repo.

Walks every section folder for `day_NNN/` dirs that contain a `lessons/` folder,
reads each lesson's title from its YAML, lists exercises + project, pulls day
titles + section names from SYLLABUS.md, and merges in YouTube video IDs from
docs/videos.json (which you edit by hand as you upload videos).

Run it again any time content or video IDs change:

    python tools/build_site_manifest.py

Output: docs/course.json  (consumed by docs/app.js). Pure standard library.
"""

import json
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
SYLLABUS = os.path.join(ROOT, "SYLLABUS.md")
VIDEOS_JSON = os.path.join(DOCS, "videos.json")
OUT = os.path.join(DOCS, "course.json")

DAY_RE = re.compile(r"^day_(\d+)$")


# ── GitHub repo (for "Open in Colab" links) ──────────────────────────────────

def github_slug() -> str:
    """Return 'owner/repo' from the origin remote, or a safe placeholder."""
    try:
        url = subprocess.run(
            ["git", "-C", ROOT, "remote", "get-url", "origin"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except subprocess.CalledProcessError:
        return "OWNER/REPO"
    m = re.search(r"github\.com[:/](.+?)(?:\.git)?$", url)
    return m.group(1) if m else "OWNER/REPO"


SLUG = github_slug()
BRANCH = "main"


def colab_url(rel_path: str) -> str:
    return (f"https://colab.research.google.com/github/{SLUG}/blob/{BRANCH}/"
            f"{rel_path}")


# ── SYLLABUS parsing: section names + per-day titles ─────────────────────────

def parse_syllabus():
    """Return (day_title: {int: str}, section_of_day: {int: str})."""
    day_title, section_of_day = {}, {}
    current_section = "Course"
    if not os.path.exists(SYLLABUS):
        return day_title, section_of_day
    with open(SYLLABUS, encoding="utf-8") as f:
        for line in f:
            if line.startswith("## "):
                # e.g. "## Section 1 — Text AI · Days 6–20" or "## Warmup — Days 1–5 · ..."
                current_section = line[3:].split("·")[0].strip()
                continue
            m = re.match(r"^\|\s*(\d+)\s*\|\s*(.+?)\s*\|", line)
            if m:
                n = int(m.group(1))
                day_title[n] = m.group(2).strip()
                section_of_day[n] = current_section
    return day_title, section_of_day


# ── Lesson YAML title (no yaml dependency) ───────────────────────────────────

def lesson_title(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("title:"):
                return line.split(":", 1)[1].strip().strip('"').strip("'")
    return os.path.basename(path)


# ── Walk the repo for day folders ────────────────────────────────────────────

def find_days():
    """Return {day_num: {'section_folder', 'dir', 'lessons', 'exercises', 'project'}}."""
    days = {}
    for entry in sorted(os.listdir(ROOT)):
        sec_dir = os.path.join(ROOT, entry)
        if not os.path.isdir(sec_dir) or entry.startswith(".") or entry == "docs":
            continue
        for sub in sorted(os.listdir(sec_dir)):
            m = DAY_RE.match(sub)
            if not m:
                continue
            day_dir = os.path.join(sec_dir, sub)
            lessons_dir = os.path.join(day_dir, "lessons")
            if not os.path.isdir(lessons_dir):
                continue  # stub / empty folder
            n = int(m.group(1))
            lessons = sorted(f for f in os.listdir(lessons_dir)
                             if f.endswith(".yaml"))
            ex_dir = os.path.join(day_dir, "exercises")
            exercises = sorted(f for f in os.listdir(ex_dir)
                               if f.endswith(".ipynb")) if os.path.isdir(ex_dir) else []
            proj = os.path.join(day_dir, "project", "project.ipynb")
            days[n] = {
                "section_folder": entry,
                "dir": day_dir,
                "lessons": [os.path.join(lessons_dir, l) for l in lessons],
                "exercises": [os.path.join(ex_dir, e) for e in exercises],
                "project": proj if os.path.exists(proj) else None,
            }
    return days


def rel(path: str) -> str:
    return os.path.relpath(path, ROOT).replace(os.sep, "/")


def lesson_id(day_num: int, lesson_num: int) -> str:
    return f"day_{day_num:03d}_lesson_{lesson_num:02d}"


# ── Build ────────────────────────────────────────────────────────────────────

def main():
    day_title, section_of_day = parse_syllabus()
    days = find_days()

    videos = {}
    if os.path.exists(VIDEOS_JSON):
        with open(VIDEOS_JSON, encoding="utf-8") as f:
            videos = json.load(f)

    # Group days into sections, preserving day order.
    sections = []
    seen_sections = {}
    for n in sorted(days):
        info = days[n]
        sec_name = section_of_day.get(n, info["section_folder"])
        if sec_name not in seen_sections:
            seen_sections[sec_name] = {"name": sec_name, "days": []}
            sections.append(seen_sections[sec_name])

        lessons = []
        for i, lpath in enumerate(info["lessons"], 1):
            lid = lesson_id(n, i)
            lessons.append({
                "id": lid,
                "num": i,
                "title": lesson_title(lpath),
                "youtube": videos.get(lid, ""),
            })
        exercises = [{
            "num": i,
            "path": rel(e),
            "colab": colab_url(rel(e)),
        } for i, e in enumerate(info["exercises"], 1)]
        project = None
        if info["project"]:
            project = {"path": rel(info["project"]),
                       "colab": colab_url(rel(info["project"]))}

        seen_sections[sec_name]["days"].append({
            "day": n,
            "title": day_title.get(n, f"Day {n}"),
            "lessons": lessons,
            "exercises": exercises,
            "project": project,
        })

    manifest = {
        "repo": SLUG,
        "branch": BRANCH,
        "total_days": len(days),
        "sections": sections,
    }
    os.makedirs(DOCS, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    rendered = sum(1 for s in sections for d in s["days"]
                   for l in d["lessons"] if l["youtube"])
    total_lessons = sum(len(d["lessons"]) for s in sections for d in s["days"])
    print(f"Wrote {rel(OUT)}")
    print(f"  repo     : {SLUG}")
    print(f"  days     : {len(days)} across {len(sections)} sections")
    print(f"  lessons  : {total_lessons}  ({rendered} with a YouTube ID set)")


if __name__ == "__main__":
    main()
