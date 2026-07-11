#!/usr/bin/env python3
"""
Structural validator for a course day (safety precaution #2).

Deterministic, instant, free. Checks that a day has the RIGHT SHAPE against
AUTHORING_TEMPLATE.md. It does NOT judge whether the content is correct or good
— that's the adversarial review (#3) and human review.

Usage:
    python tools/validate_day.py 2
    python tools/validate_day.py 002

Exit code 0 = all hard checks pass. Exit code 1 = at least one hard failure.
Import: `from validate_day import validate` -> (ok: bool, lines: list[str]).
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ALLOWED_SLIDE_TYPES = {"title", "concept", "how_it_works", "code", "exercise", "summary"}
MIN_LESSONS, MAX_LESSONS = 4, 6

# Day number -> section folder (matches SYLLABUS.md)
SECTION_RANGES = [
    (1, 5, "00_warmup"),
    (6, 20, "01_text_ai"),
    (21, 35, "02_automation"),
    (36, 50, "03_data_analysis"),
    (51, 65, "04_real_apps"),
    (66, 78, "05_vision_multimodal"),
    (79, 88, "06_ai_agents"),
    (89, 100, "07_finance_trading"),
]

PASS, FAIL, WARN = "✅", "❌", "⚠️"


def section_for(day: int) -> str | None:
    for lo, hi, name in SECTION_RANGES:
        if lo <= day <= hi:
            return name
    return None


def lessons_dir(day: int) -> Path:
    """Per-day lesson-scripts folder: <section>/day_NNN/lessons/."""
    section = section_for(day) or ""
    return ROOT / section / f"day_{day:03d}" / "lessons"


def end_of_section_reminder(day: int) -> str | None:
    """If `day` is the last day of a section, return a 'start a fresh session'
    reminder with the ready-to-paste resume prompt for the next day. Else None.

    Rationale: a fresh Claude session per section resets context and avoids drift
    (safety precaution #1). This surfaces the exact prompt at the right moment.
    """
    section = next((name for lo, hi, name in SECTION_RANGES if day == hi), None)
    if section is None:
        return None  # not a section boundary
    nxt = day + 1
    nxt_section = section_for(nxt)
    bar = "─" * 64
    if nxt_section is None:
        return (f"\n{bar}\n🎉 That was the FINAL day — the 100-day authoring phase is "
                f"complete.\n{bar}")
    return (
        f"\n{bar}\n"
        f"📁 Section complete: {section} (finished at Day {day:03d}).\n\n"
        f"Start a FRESH Claude session (resets context, avoids drift), then paste:\n\n"
        f"    Continue authoring the course. Read AUTHORING_TEMPLATE.md and\n"
        f"    SYLLABUS.md, then author Day {nxt}.\n\n"
        f"(next section: {nxt_section})\n"
        f"{bar}"
    )


def _nb_sources(path: Path) -> list[str]:
    """Return each cell's joined source string for a notebook, or [] on error."""
    try:
        nb = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    out = []
    for cell in nb.get("cells", []):
        src = cell.get("source", "")
        out.append("".join(src) if isinstance(src, list) else str(src))
    return out


def validate(day: int) -> tuple[bool, list[str]]:
    """Validate one day. Returns (all_hard_checks_passed, report_lines)."""
    lines: list[str] = []
    hard_ok = True

    def hard(cond: bool, msg: str) -> bool:
        nonlocal hard_ok
        lines.append(f"  {PASS if cond else FAIL} {msg}")
        if not cond:
            hard_ok = False
        return cond

    def warn(cond: bool, msg: str):
        lines.append(f"  {PASS if cond else WARN} {msg}")

    nnn = f"{day:03d}"
    section = section_for(day)
    lines.append(f"Validating Day {nnn}  (section: {section})")

    if not hard(section is not None, f"day {day} maps to a known section (1-100)"):
        return hard_ok, lines
    day_dir = ROOT / section / f"day_{nnn}"

    # ---- Lessons ----------------------------------------------------------
    l_dir = lessons_dir(day)
    lesson_files = sorted(l_dir.glob(f"day_{nnn}_lesson_*.yaml"))
    n = len(lesson_files)
    hard(MIN_LESSONS <= n <= MAX_LESSONS,
         f"lesson count {n} within {MIN_LESSONS}-{MAX_LESSONS}  ({l_dir})")

    import yaml  # local import so --help works without PyYAML
    for i, lf in enumerate(lesson_files, 1):
        expected = f"day_{nnn}_lesson_{i:02d}.yaml"
        hard(lf.name == expected, f"lesson {i} named {expected} (got {lf.name})")
        try:
            data = yaml.safe_load(lf.read_text(encoding="utf-8"))
        except Exception as e:
            hard(False, f"lesson {i} parses as YAML ({e})")
            continue
        hard(isinstance(data, dict), f"lesson {i} is a mapping")
        if not isinstance(data, dict):
            continue
        hard(str(data.get("day", "")).zfill(3) == nnn, f"lesson {i} day == {nnn}")
        hard(bool(str(data.get("title", "")).strip()), f"lesson {i} has a title")
        slides = data.get("slides")
        if not hard(isinstance(slides, list) and slides, f"lesson {i} has slides"):
            continue
        # slide types
        types = [s.get("type") for s in slides if isinstance(s, dict)]
        bad = [t for t in types if t not in ALLOWED_SLIDE_TYPES]
        hard(not bad, f"lesson {i} slide types valid (bad: {bad})")
        hard(types[:1] == ["title"], f"lesson {i} opens with a title slide")
        hard(types[-1:] == ["summary"], f"lesson {i} ends with a summary slide")
        # narration present on every non-title slide
        missing = [
            j for j, s in enumerate(slides, 1)
            if isinstance(s, dict) and s.get("type") != "title"
            and not str(s.get("narration", "")).strip()
        ]
        hard(not missing, f"lesson {i} every non-title slide has narration (missing: {missing})")

    # ---- Exercises --------------------------------------------------------
    ex_dir = day_dir / "exercises"
    ex_files = sorted(ex_dir.glob("exercise_*.ipynb"))
    hard(len(ex_files) >= 1, f"at least one exercise notebook ({ex_dir})")
    warn(len(ex_files) == n, f"exercise count ({len(ex_files)}) matches lesson count ({n})")
    for ef in ex_files:
        srcs = _nb_sources(ef)
        blob = "\n".join(srcs)
        hard(bool(srcs), f"{ef.name} parses as a notebook")
        hard(any(s.lstrip().startswith("# Day") for s in srcs),
             f"{ef.name} has a '# Day ...' title cell")
        hard(("assert" in blob) or (PASS in blob) or ("Check Your Work" in blob),
             f"{ef.name} has an automated checks cell")
        hard(("<details>" in blob) or ("## Solution" in blob),
             f"{ef.name} has a solution section")
        # async/await not introduced until Day 33
        if day <= 32:
            try:
                nb = json.loads(ef.read_text(encoding="utf-8"))
                code_src = "\n".join(
                    "".join(c.get("source", []))
                    for c in nb.get("cells", [])
                    if c.get("cell_type") == "code"
                )
                hard("async def" not in code_src,
                     f"{ef.name} has no 'async def' in code cells (async not until Day 33)")
            except Exception:
                pass  # parse failure already caught above

    # ---- Project + solution ----------------------------------------------
    proj = day_dir / "project" / "project.ipynb"
    sol = day_dir / "project" / "solution" / "solution.ipynb"
    if hard(proj.exists(), f"project notebook exists ({proj.relative_to(ROOT)})"):
        pblob = "\n".join(_nb_sources(proj))
        hard("Project" in pblob, "project notebook states the project / deliverable")
    hard(sol.exists(), f"solution notebook exists ({sol.relative_to(ROOT)})")

    lines.append(f"\n{'PASS' if hard_ok else 'FAIL'} — Day {nnn} structure")
    return hard_ok, lines


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate a course day's structure (#2).")
    ap.add_argument("day", help="Day number, e.g. 2 or 002")
    args = ap.parse_args()
    try:
        day = int(args.day)
    except ValueError:
        print(f"Invalid day: {args.day!r}")
        return 2
    ok, lines = validate(day)
    print("\n".join(lines))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
