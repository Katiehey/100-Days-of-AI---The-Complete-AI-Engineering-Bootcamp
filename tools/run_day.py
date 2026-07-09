#!/usr/bin/env python3
"""
Execute + render gate for a course day (safety precaution #1).

Turns "looks right" into "verified runs". Runs in the ai-course conda env.

Steps:
  1. Render each lesson — slides (+ audio) through the pipeline, confirming the
     YAML is well-formed enough to feed the video build.
  2. Execute the project solution notebook — must finish with NO exception.
     This is the strong correctness signal: an invented or wrong API surfaces
     here as an ImportError/AttributeError instead of shipping silently.
  3. Execute each exercise notebook — must finish without an *uncaught*
     exception. This verifies the automated-checks harness is well-formed. The
     checks may still print ❌, because exercises are intentionally incomplete
     (the learner fills them in) — that is expected and not a failure here.

Usage:
    python tools/run_day.py 2
    python tools/run_day.py 2 --fast      # slides only, skip slow TTS audio
    python tools/run_day.py 2 --no-exec   # render only, skip notebook execution
"""

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from validate_day import ROOT, lessons_dir, section_for

PIPELINE = ROOT / "00_pipeline"
PASS, FAIL = "✅", "❌"
NB_TIMEOUT = 900  # seconds per notebook


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def _render(day: int, fast: bool, lines: list[str]) -> bool:
    ok = True
    nnn = f"{day:03d}"
    lessons = sorted(lessons_dir(day).glob(f"day_{nnn}_lesson_*.yaml"))
    if not lessons:
        lines.append(f"  {FAIL} no lesson YAMLs found to render")
        return False
    for lf in lessons:
        if fast:
            cmd = [sys.executable, str(PIPELINE / "slide_gen.py"), str(lf)]
            what = f"render slides {lf.name}"
        else:
            cmd = [sys.executable, str(PIPELINE / "lesson_build.py"), str(lf), "--prep"]
            what = f"render slides+audio {lf.name}"
        r = _run(cmd)
        good = r.returncode == 0
        ok = ok and good
        lines.append(f"  {PASS if good else FAIL} {what}"
                     + ("" if good else f"\n      {r.stderr.strip()[-800:]}"))
    return ok


def _exec_nb(path: Path, label: str, lines: list[str]) -> bool:
    with tempfile.TemporaryDirectory() as td:
        cmd = ["jupyter", "nbconvert", "--to", "notebook", "--execute",
               f"--ExecutePreprocessor.timeout={NB_TIMEOUT}",
               "--ExecutePreprocessor.kernel_name=ai-course",
               "--output", str(Path(td) / "out.ipynb"), str(path)]
        r = _run(cmd)
    good = r.returncode == 0
    lines.append(f"  {PASS if good else FAIL} execute {label}"
                 + ("" if good else f"\n      {r.stderr.strip()[-1200:]}"))
    return good


_SOLUTION_RE = re.compile(r"```python\n(.*?)```", re.S)


def _verify_solutions(day: int, lines: list[str]) -> bool:
    """For each exercise, inject its EMBEDDED solution into the notebook and run
    it through the real kernel against the exercise's own checks — requiring all
    checks pass. The stub-execution gate only proves the harness doesn't crash;
    this proves the exercise is actually solvable and the provided answer reaches
    all-green. Runs via the kernel (so async / top-level await work) in an
    isolated temp dir (so file-based checks don't leak)."""
    import nbformat
    from nbformat.v4 import new_code_cell

    ok = True
    section = section_for(day)
    ex_dir = ROOT / section / f"day_{day:03d}" / "exercises"
    exercises = sorted(ex_dir.glob("exercise_*.ipynb"))
    if not exercises:
        lines.append(f"  {FAIL} no exercises found to verify")
        return False

    for ef in exercises:
        nb = nbformat.read(str(ef), as_version=4)
        solution, impl_idx = None, None
        want_impl = False
        for i, c in enumerate(nb.cells):
            if c.cell_type == "markdown" and "## Your Implementation" in c.source:
                want_impl = True
                continue
            if want_impl and c.cell_type == "code":
                impl_idx = i
                want_impl = False
            if c.cell_type == "markdown" and ("<details>" in c.source or "## Solution" in c.source):
                m = _SOLUTION_RE.search(c.source)
                if m:
                    solution = m.group(1)
        if solution is None or impl_idx is None:
            lines.append(f"  {FAIL} {ef.name}: could not locate the implementation cell and/or solution block")
            ok = False
            continue

        # Insert the solution just after the stub so it overrides it while keeping
        # the stub cell's imports intact.
        nb.cells.insert(impl_idx + 1, new_code_cell(solution))
        with tempfile.TemporaryDirectory() as td:
            src_nb = Path(td) / "verify.ipynb"
            nbformat.write(nb, str(src_nb))
            r = subprocess.run(
                ["jupyter", "nbconvert", "--to", "notebook", "--execute",
                 "--ExecutePreprocessor.timeout=300",
                 "--ExecutePreprocessor.kernel_name=ai-course",
                 "--output", "out.ipynb", "--output-dir", td, str(src_nb)],
                capture_output=True, text=True, cwd=td)
            out_nb = Path(td) / "out.ipynb"
            if r.returncode == 0 and out_nb.exists():
                executed = nbformat.read(str(out_nb), as_version=4)
                text = "".join(
                    (o.get("text", "") or "")
                    for c in executed.cells for o in getattr(c, "outputs", [])
                )
                passed = ("complete!" in text) and ("❌" not in text)
                detail = text.strip()[-400:]
            else:
                passed = False
                detail = (r.stderr or "").strip()[-400:]
        ok = ok and passed
        lines.append(f"  {PASS if passed else FAIL} {ef.name}: embedded solution passes its own checks"
                     + ("" if passed else f"\n      {detail}"))
    return ok


def run(day: int, fast: bool = False, no_exec: bool = False) -> tuple[bool, list[str]]:
    lines: list[str] = []
    ok = True
    nnn = f"{day:03d}"
    section = section_for(day)
    lines.append(f"Running Day {nnn}  (render{'' if no_exec else ' + execute'})")
    if section is None:
        lines.append(f"  {FAIL} day {day} maps to no known section")
        return False, lines
    day_dir = ROOT / section / f"day_{nnn}"

    lines.append("Render:")
    ok &= _render(day, fast, lines)

    if not no_exec:
        lines.append("Execute:")
        sol = day_dir / "project" / "solution" / "solution.ipynb"
        if sol.exists():
            ok &= _exec_nb(sol, "project solution (must be clean)", lines)
        else:
            lines.append(f"  {FAIL} missing {sol.relative_to(ROOT)}")
            ok = False
        for ef in sorted((day_dir / "exercises").glob("exercise_*.ipynb")):
            ok &= _exec_nb(ef, f"{ef.name} (harness must not crash)", lines)

        lines.append("Verify solutions (each embedded answer passes its own checks):")
        ok &= _verify_solutions(day, lines)

    lines.append(f"\n{'PASS' if ok else 'FAIL'} — Day {nnn} run")
    return ok, lines


def main() -> int:
    ap = argparse.ArgumentParser(description="Execute + render gate (#1).")
    ap.add_argument("day", help="Day number, e.g. 2 or 002")
    ap.add_argument("--fast", action="store_true", help="slides only, skip TTS audio")
    ap.add_argument("--no-exec", action="store_true", help="render only, skip notebooks")
    args = ap.parse_args()
    try:
        day = int(args.day)
    except ValueError:
        print(f"Invalid day: {args.day!r}")
        return 2
    ok, lines = run(day, args.fast, args.no_exec)
    print("\n".join(lines))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
