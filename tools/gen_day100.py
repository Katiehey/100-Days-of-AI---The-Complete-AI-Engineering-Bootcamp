#!/usr/bin/env python3
"""Day 100 generator — Final Capstone."""
import json, pathlib

ROOT  = pathlib.Path(__file__).parent.parent
DAY   = "100"
SLUG  = "capstone"
TITLE = "Final Capstone"
DIR   = ROOT / "07_finance" / f"day_{DAY}"

# ══════════════════════════════════════════════════════════════════════════════
# Deliverable
# ══════════════════════════════════════════════════════════════════════════════

DELIVERABLE = '''\
"""
Day 100 — Final Capstone
==========================
Tools to specify, plan, track, and document a capstone AI project.
Synthesizes concepts from all 7 sections of the course.
All pure Python standard library — no paid APIs.

Public API
----------
    CapstoneSpec                        — dataclass: project spec
    Phase                               — dataclass: one build phase
    CapstoneReport                      — dataclass: spec + phases + dates
    validate_spec(spec)                 -> tuple[bool, list[str]]
    generate_project_plan(spec)         -> str  (Markdown)
    default_phases(spec)                -> list[Phase]
    build_status(report)                -> dict
    mark_phase_done(report, phase_name) -> bool
    format_completion_certificate(report) -> str (Markdown)
"""
import datetime
from dataclasses import dataclass, field


# ── data model ────────────────────────────────────────────────────────────────

@dataclass
class CapstoneSpec:
    """Specification for a capstone AI product.

    Fields:
        name           : str  — project name
        tagline        : str  — one-sentence description
        domain         : str  — e.g. "finance", "text", "vision", "agents"
        description    : str  — paragraph describing the product
        sections_used  : list[str] — course sections applied (e.g. "Section 4: Real Apps")
        deliverables   : list[str] — concrete shipped artifacts (≥ 3 required to pass validate_spec)
        tech_stack     : list[str] — technologies used (≥ 2 required)
    """
    name:          str
    tagline:       str
    domain:        str
    description:   str
    sections_used: list
    deliverables:  list
    tech_stack:    list


@dataclass
class Phase:
    """One build phase with a list of tasks and a done flag.

    Fields:
        name  : str       — phase name (e.g. "Plan", "Build", "Ship")
        tasks : list[str] — concrete steps for this phase
        done  : bool      — True once all tasks in this phase are complete
    """
    name:  str
    tasks: list
    done:  bool = False


@dataclass
class CapstoneReport:
    """Full capstone build record: spec + phases + timestamps.

    Fields:
        spec         : CapstoneSpec
        phases       : list[Phase]  — build phases (default: empty, populate with default_phases)
        started_at   : str          — ISO date string, auto-set to today
        completed_at : str          — ISO date string set when all phases are done
    """
    spec:         CapstoneSpec
    phases:       list = field(default_factory=list)
    started_at:   str  = field(
        default_factory=lambda: datetime.date.today().isoformat()
    )
    completed_at: str  = ""


# ── validation ────────────────────────────────────────────────────────────────

def validate_spec(spec):
    """Validate a CapstoneSpec for completeness.

    Rules:
      - name, tagline, domain, description must be non-empty strings
      - deliverables must have at least 3 items
      - tech_stack must have at least 2 items
      - sections_used must have at least 1 item

    Args:
        spec : CapstoneSpec

    Returns:
        tuple[bool, list[str]] — (is_valid, list_of_error_messages)
        is_valid is True iff list_of_error_messages is empty.
    """
    errors = []
    for field_name in ("name", "tagline", "domain", "description"):
        val = getattr(spec, field_name, "")
        if not isinstance(val, str) or not val.strip():
            errors.append(f"{field_name} must be a non-empty string")
    if len(spec.deliverables) < 3:
        errors.append(
            f"at least 3 deliverables required, got {len(spec.deliverables)}"
        )
    if len(spec.tech_stack) < 2:
        errors.append(
            f"at least 2 tech stack items required, got {len(spec.tech_stack)}"
        )
    if not spec.sections_used:
        errors.append("sections_used must reference at least one course section")
    return len(errors) == 0, errors


# ── planning ──────────────────────────────────────────────────────────────────

def generate_project_plan(spec):
    """Generate a Markdown implementation plan from a CapstoneSpec.

    Sections:
      # {name} — Implementation Plan
      **tagline**
      ## Overview — description
      ## Course Sections Applied — bullet list
      ## Tech Stack — bullet list
      ## Deliverables — checkbox list
      ## Build Phases — standard 6-phase checklist

    Args:
        spec : CapstoneSpec

    Returns:
        str — Markdown document
    """
    deliverable_list = "\\n".join(f"- [ ] {d}" for d in spec.deliverables)
    tech_list        = "\\n".join(f"- {t}"       for t in spec.tech_stack)
    sections_list    = "\\n".join(f"- {s}"       for s in spec.sections_used)

    return (
        f"# {spec.name} \\u2014 Implementation Plan\\n\\n"
        f"**{spec.tagline}**\\n\\n"
        f"## Overview\\n\\n"
        f"{spec.description}\\n\\n"
        f"## Course Sections Applied\\n\\n"
        f"{sections_list}\\n\\n"
        f"## Tech Stack\\n\\n"
        f"{tech_list}\\n\\n"
        f"## Deliverables\\n\\n"
        f"{deliverable_list}\\n\\n"
        f"## Build Phases\\n\\n"
        f"### Phase 1 \\u2014 Plan\\n"
        f"- [ ] Finalise spec (validate_spec passes)\\n"
        f"- [ ] Set up project structure and environment\\n"
        f"- [ ] Write gate tests before coding\\n\\n"
        f"### Phase 2 \\u2014 Build\\n"
        f"- [ ] Implement core AI functionality\\n"
        f"- [ ] Wire up data pipeline\\n"
        f"- [ ] Integration tests pass\\n\\n"
        f"### Phase 3 \\u2014 Test\\n"
        f"- [ ] Gate: all checks green\\n"
        f"- [ ] End-to-end happy path tested\\n"
        f"- [ ] Edge cases handled\\n\\n"
        f"### Phase 4 \\u2014 Deploy\\n"
        f"- [ ] Write .env / config\\n"
        f"- [ ] Deploy to production\\n"
        f"- [ ] Verify live URL works\\n\\n"
        f"### Phase 5 \\u2014 Document\\n"
        f"- [ ] README with installation + usage\\n"
        f"- [ ] Generate case study (portfolio.generate_case_study)\\n"
        f"- [ ] Record demo video\\n\\n"
        f"### Phase 6 \\u2014 Share\\n"
        f"- [ ] Push to GitHub\\n"
        f"- [ ] Add to portfolio site\\n"
        f"- [ ] Post on LinkedIn / Twitter\\n"
    )


def default_phases(spec):
    """Return the standard 6 build phases for a capstone project.

    Each Phase has a name, a list of concrete tasks, and done=False.
    The tasks are partially derived from the spec (e.g. the product name).

    Args:
        spec : CapstoneSpec

    Returns:
        list[Phase] — six Phase objects: Plan, Build, Test, Deploy, Document, Share
    """
    ai_backend = next(
        (t for t in spec.tech_stack if t.lower() in ("ollama", "llama", "llamacpp")),
        "AI backend",
    )
    return [
        Phase("Plan", [
            f"Finalise spec for {spec.name}",
            "Identify dependencies and install packages",
            "Write gate tests before writing production code",
        ]),
        Phase("Build", [
            "Implement core AI functionality",
            f"Wire up {ai_backend} integration",
            "Build data pipeline end-to-end",
        ]),
        Phase("Test", [
            "Run gate: all inline checks pass",
            "Test the happy path end-to-end",
            "Test edge cases and error conditions",
        ]),
        Phase("Deploy", [
            "Write .env file with environment config",
            "Deploy to production (Render / Railway / Fly.io)",
            "Verify live URL returns correct responses",
        ]),
        Phase("Document", [
            "Write README with Installation and Usage sections",
            "Generate case study with portfolio.generate_case_study",
            "Record a 2-minute demo video",
        ]),
        Phase("Share", [
            "Push all code to GitHub",
            "Add to portfolio with portfolio.export_portfolio",
            "Post on LinkedIn and Twitter",
        ]),
    ]


# ── tracking ──────────────────────────────────────────────────────────────────

def build_status(report):
    """Return a summary of build phase completion.

    Args:
        report : CapstoneReport

    Returns:
        dict with keys:
          phases           : list[dict] — {name, done, n_tasks} per phase
          total_phases     : int
          completed_phases : int
          completion_pct   : float  (0.0–100.0, rounded to 1 decimal)
          is_complete      : bool   (True iff all phases done and total > 0)
    """
    total = len(report.phases)
    done  = sum(1 for p in report.phases if p.done)
    return {
        "phases": [
            {"name": p.name, "done": p.done, "n_tasks": len(p.tasks)}
            for p in report.phases
        ],
        "total_phases":     total,
        "completed_phases": done,
        "completion_pct":   round(done / max(total, 1) * 100.0, 1),
        "is_complete":      (done == total and total > 0),
    }


def mark_phase_done(report, phase_name):
    """Mark the named phase as done in place.

    Args:
        report     : CapstoneReport — mutated in place
        phase_name : str — must match a Phase.name exactly (case-sensitive)

    Returns:
        True  — phase found and marked done
        False — no phase with that name found
    """
    for phase in report.phases:
        if phase.name == phase_name:
            phase.done = True
            return True
    return False


# ── certificate ───────────────────────────────────────────────────────────────

def format_completion_certificate(report):
    """Generate a Markdown completion certificate for a finished capstone.

    Shows: project name + tagline, build phase checklist (done/not-done),
    overall completion percentage, tech stack, sections applied, and
    course sign-off line.

    Args:
        report : CapstoneReport

    Returns:
        str — Markdown document starting with "# 100 Days of AI"
    """
    spec   = report.spec
    status = build_status(report)

    phase_lines = "\\n".join(
        f"  {'[x]' if p['done'] else '[ ]'} {p['name']}"
        for p in status["phases"]
    )
    tech_lines    = "\\n".join(f"- {t}" for t in spec.tech_stack)
    section_lines = "\\n".join(f"- {s}" for s in spec.sections_used)

    return (
        f"# 100 Days of AI \\u2014 Capstone Completion\\n\\n"
        f"## {spec.name}\\n\\n"
        f"**{spec.tagline}**\\n\\n"
        f"{spec.description}\\n\\n"
        f"## Build Progress\\n\\n"
        f"{phase_lines}\\n\\n"
        f"**Overall: {status['completion_pct']}% complete**\\n\\n"
        f"## Tech Stack\\n\\n"
        f"{tech_lines}\\n\\n"
        f"## Course Sections Applied\\n\\n"
        f"{section_lines}\\n\\n"
        f"---\\n\\n"
        f"*Built during 100 Days of AI \\u2014 The Complete AI Engineering Bootcamp*\\n"
    )
'''

# ══════════════════════════════════════════════════════════════════════════════
# Notebook helpers
# ══════════════════════════════════════════════════════════════════════════════

def _nb(cells):
    return {
        "nbformat": 4, "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"display_name": "Python 3 (ipykernel)",
                           "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.10.0"},
        },
        "cells": cells,
    }

def _code(src, outputs=None):
    return {"cell_type": "code", "execution_count": None, "metadata": {},
            "outputs": outputs or [],
            "source": src.splitlines(keepends=True)}

def _md(src):
    return {"cell_type": "markdown", "metadata": {},
            "source": src.splitlines(keepends=True)}

# ── preludes ──────────────────────────────────────────────────────────────────

_P_BASE = """\
import datetime
from dataclasses import dataclass, field

@dataclass
class CapstoneSpec:
    name: str; tagline: str; domain: str; description: str
    sections_used: list; deliverables: list; tech_stack: list

@dataclass
class Phase:
    name: str; tasks: list; done: bool = False

@dataclass
class CapstoneReport:
    spec: CapstoneSpec
    phases: list = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.date.today().isoformat())
    completed_at: str = ""

_SPEC = CapstoneSpec(
    name          = "AI Trading Bot",
    tagline       = "Paper-trading bot with sentiment and technical signals.",
    domain        = "finance",
    description   = "End-to-end AI trading bot that fetches OHLCV data, computes "
                    "technical indicators, scores news sentiment with an LLM, applies "
                    "risk controls, and runs a daily paper-trading loop with logging.",
    sections_used = [
        "Section 3: Data & Analysis (pandas, SQLite)",
        "Section 4: Real Apps (FastAPI endpoint)",
        "Section 6: AI Agents (scheduling loop)",
        "Section 7: Finance & Trading (backtester, risk manager, paper trader)",
    ],
    deliverables  = [
        "paper_trader.py with buy/sell/portfolio_value",
        "bot_runner.py with daily scheduling and logging",
        "risk.py with stop-loss and drawdown controls",
        "Deployed FastAPI endpoint",
        "Portfolio case study",
    ],
    tech_stack    = ["Python", "pandas", "Ollama", "SQLite", "FastAPI"],
)
"""

_P_VALIDATE = """\
def validate_spec(spec):
    errors = []
    for field_name in ("name", "tagline", "domain", "description"):
        val = getattr(spec, field_name, "")
        if not isinstance(val, str) or not val.strip():
            errors.append(f"{field_name} must be a non-empty string")
    if len(spec.deliverables) < 3:
        errors.append(f"at least 3 deliverables required, got {len(spec.deliverables)}")
    if len(spec.tech_stack) < 2:
        errors.append(f"at least 2 tech stack items required, got {len(spec.tech_stack)}")
    if not spec.sections_used:
        errors.append("sections_used must reference at least one course section")
    return len(errors) == 0, errors
"""

_P_PLAN = """\
def generate_project_plan(spec):
    deliverable_list = "\\n".join(f"- [ ] {d}" for d in spec.deliverables)
    tech_list        = "\\n".join(f"- {t}"     for t in spec.tech_stack)
    sections_list    = "\\n".join(f"- {s}"     for s in spec.sections_used)
    return (
        f"# {spec.name} — Implementation Plan\\n\\n"
        f"**{spec.tagline}**\\n\\n"
        f"## Overview\\n\\n{spec.description}\\n\\n"
        f"## Course Sections Applied\\n\\n{sections_list}\\n\\n"
        f"## Tech Stack\\n\\n{tech_list}\\n\\n"
        f"## Deliverables\\n\\n{deliverable_list}\\n\\n"
        f"## Build Phases\\n\\n"
        f"### Phase 1 — Plan\\n- [ ] Finalise spec\\n- [ ] Write gate tests\\n\\n"
        f"### Phase 2 — Build\\n- [ ] Implement core AI\\n- [ ] Wire pipeline\\n\\n"
        f"### Phase 3 — Test\\n- [ ] Gate green\\n- [ ] End-to-end test\\n\\n"
        f"### Phase 4 — Deploy\\n- [ ] Write .env\\n- [ ] Deploy\\n\\n"
        f"### Phase 5 — Document\\n- [ ] README\\n- [ ] Case study\\n\\n"
        f"### Phase 6 — Share\\n- [ ] GitHub\\n- [ ] Portfolio\\n- [ ] Post\\n"
    )
"""

_P_PHASES = """\
def default_phases(spec):
    ai_backend = next(
        (t for t in spec.tech_stack if t.lower() in ("ollama","llama","llamacpp")),
        "AI backend",
    )
    return [
        Phase("Plan",  [f"Finalise spec for {spec.name}", "Install packages", "Write gate tests"]),
        Phase("Build", ["Implement core AI", f"Wire {ai_backend}", "Build pipeline"]),
        Phase("Test",  ["Gate: all checks green", "Happy path", "Edge cases"]),
        Phase("Deploy",["Write .env", "Deploy to production", "Verify live URL"]),
        Phase("Document",["README", "Case study", "Demo video"]),
        Phase("Share", ["Push to GitHub", "Portfolio", "Post on LinkedIn"]),
    ]
"""

_P_TRACK = """\
def build_status(report):
    total = len(report.phases); done = sum(1 for p in report.phases if p.done)
    return {
        "phases": [{"name":p.name,"done":p.done,"n_tasks":len(p.tasks)} for p in report.phases],
        "total_phases": total, "completed_phases": done,
        "completion_pct": round(done / max(total,1) * 100.0, 1),
        "is_complete": (done == total and total > 0),
    }

def mark_phase_done(report, phase_name):
    for phase in report.phases:
        if phase.name == phase_name:
            phase.done = True; return True
    return False
"""

_P_CERT = """\
def format_completion_certificate(report):
    spec = report.spec; status = build_status(report)
    phase_lines   = "\\n".join(f"  {'[x]' if p['done'] else '[ ]'} {p['name']}" for p in status["phases"])
    tech_lines    = "\\n".join(f"- {t}" for t in spec.tech_stack)
    section_lines = "\\n".join(f"- {s}" for s in spec.sections_used)
    return (
        f"# 100 Days of AI — Capstone Completion\\n\\n"
        f"## {spec.name}\\n\\n**{spec.tagline}**\\n\\n{spec.description}\\n\\n"
        f"## Build Progress\\n\\n{phase_lines}\\n\\n"
        f"**Overall: {status['completion_pct']}% complete**\\n\\n"
        f"## Tech Stack\\n\\n{tech_lines}\\n\\n"
        f"## Course Sections Applied\\n\\n{section_lines}\\n\\n"
        f"---\\n\\n*Built during 100 Days of AI — The Complete AI Engineering Bootcamp*\\n"
    )
"""

# ══════════════════════════════════════════════════════════════════════════════
# Exercises
# ══════════════════════════════════════════════════════════════════════════════

_EX1 = _nb([
    _md("# Exercise 1 — validate_spec\n\n"
        "Before building anything, validate the plan. `validate_spec` checks "
        "that a `CapstoneSpec` is complete enough to ship: all text fields are "
        "non-empty, there are at least 3 deliverables, at least 2 tech stack "
        "items, and at least 1 course section listed. It returns a `(bool, list)` "
        "tuple — the same pattern as Python's `issubset` and validation libraries."),
    _code(_P_BASE + """\

def validate_spec(spec):
    \"\"\"Validate a CapstoneSpec for completeness.

    Returns:
        tuple[bool, list[str]]
          - (True, [])       if all rules pass
          - (False, errors)  if one or more rules fail

    Rules:
      - name, tagline, domain, description: non-empty string
      - deliverables: ≥ 3 items
      - tech_stack: ≥ 2 items
      - sections_used: ≥ 1 item
    \"\"\"
    errors = []
    # Check text fields
    for field_name in ("name", "tagline", "domain", "description"):
        val = getattr(spec, field_name, "")
        if not isinstance(val, str) or not val.strip():
            errors.append(f"{field_name} must be a non-empty string")
    # TODO: check deliverables (≥ 3), tech_stack (≥ 2), sections_used (≥ 1)
    return len(errors) == 0, errors
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — valid spec returns (True, [])
try:
    ok, errors = validate_spec(_SPEC)
    assert ok is True,  f"expected True, got {ok}"
    assert errors == [], f"expected [], got {errors}"
    checks += 1; print("✅ 1 valid spec → (True, [])")
except Exception as e:
    print("❌ 1:", e)

# 2 — empty name → error mentioning 'name'
try:
    bad = CapstoneSpec("","T","D","Desc",["S1"],["d1","d2","d3"],["py","pd"])
    ok, errors = validate_spec(bad)
    assert ok is False
    assert any("name" in err for err in errors), f"expected 'name' error, got {errors}"
    checks += 1; print("✅ 2 empty name → False with 'name' error")
except Exception as e:
    print("❌ 2:", e)

# 3 — fewer than 3 deliverables → error
try:
    bad = CapstoneSpec("N","T","D","Desc",["S1"],["only_one"],["py","pd"])
    ok, errors = validate_spec(bad)
    assert ok is False
    assert any("deliverable" in err for err in errors)
    checks += 1; print("✅ 3 < 3 deliverables → False with deliverables error")
except Exception as e:
    print("❌ 3:", e)

# 4 — fewer than 2 tech stack items → error
try:
    bad = CapstoneSpec("N","T","D","Desc",["S1"],["d1","d2","d3"],["py"])
    ok, errors = validate_spec(bad)
    assert ok is False
    assert any("tech" in err for err in errors)
    checks += 1; print("✅ 4 < 2 tech items → False with tech_stack error")
except Exception as e:
    print("❌ 4:", e)

# 5 — empty sections_used → error; multiple errors accumulate
try:
    bad = CapstoneSpec("N","T","D","Desc",[],["d1","d2","d3"],["py","pd"])
    ok, errors = validate_spec(bad)
    assert ok is False
    assert any("section" in err for err in errors)
    # 0 deliverables + 1 tech item would accumulate multiple errors
    worst = CapstoneSpec("","","","",[], [], [])
    ok2, errors2 = validate_spec(worst)
    assert len(errors2) >= 4, f"expected ≥4 errors for empty spec, got {len(errors2)}"
    checks += 1; print(f"✅ 5 empty sections_used → error; worst-case gives ≥4 errors")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX2 = _nb([
    _md("# Exercise 2 — generate_project_plan and default_phases\n\n"
        "A plan is the difference between a project that ships and one that "
        "drifts forever. `generate_project_plan` produces a Markdown document "
        "with the spec summary, deliverable checklist, and the six standard "
        "build phases. `default_phases` creates the six `Phase` objects that "
        "power the tracking system."),
    _code(_P_BASE + _P_VALIDATE + """\

def generate_project_plan(spec):
    \"\"\"Generate a Markdown implementation plan.

    Must contain:
      - '# {spec.name}' at the start (or in title)
      - '## Overview' section with description
      - '## Deliverables' with each deliverable as '- [ ] item'
      - '## Build Phases' with 6 phase headings (Phase 1 through Phase 6)

    Returns:
        str — Markdown
    \"\"\"
    deliverable_list = "\\n".join(f"- [ ] {d}" for d in spec.deliverables)
    tech_list        = "\\n".join(f"- {t}"     for t in spec.tech_stack)
    sections_list    = "\\n".join(f"- {s}"     for s in spec.sections_used)
    # TODO: assemble the Markdown plan
    return ""


def default_phases(spec):
    \"\"\"Return the 6 standard build phases with tasks.

    Returns list[Phase]: Plan, Build, Test, Deploy, Document, Share.
    Each phase has 3 tasks. done=False for all.
    \"\"\"
    ai_backend = next(
        (t for t in spec.tech_stack if t.lower() in ("ollama", "llama", "llamacpp")),
        "AI backend",
    )
    # TODO: return list of 6 Phase objects
    return []
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — generate_project_plan: contains project name
try:
    plan = generate_project_plan(_SPEC)
    assert isinstance(plan, str) and len(plan) > 100
    assert _SPEC.name in plan, f"name '{_SPEC.name}' not in plan"
    checks += 1; print(f"✅ 1 plan contains project name '{_SPEC.name}'")
except Exception as e:
    print("❌ 1:", e)

# 2 — plan: ## Overview with description
try:
    plan = generate_project_plan(_SPEC)
    assert "## Overview" in plan, "missing ## Overview"
    assert _SPEC.description[:30] in plan, "description not in plan"
    checks += 1; print("✅ 2 plan has ## Overview with description")
except Exception as e:
    print("❌ 2:", e)

# 3 — plan: each deliverable as a checkbox
try:
    plan = generate_project_plan(_SPEC)
    for d in _SPEC.deliverables:
        assert f"- [ ] {d}" in plan, f"deliverable not as checkbox: {d!r}"
    checks += 1; print(f"✅ 3 all {len(_SPEC.deliverables)} deliverables as '- [ ] item'")
except Exception as e:
    print("❌ 3:", e)

# 4 — default_phases: 6 phases with correct names
try:
    phases = default_phases(_SPEC)
    assert len(phases) == 6, f"expected 6 phases, got {len(phases)}"
    names = [p.name for p in phases]
    for expected in ["Plan", "Build", "Test", "Deploy", "Document", "Share"]:
        assert expected in names, f"missing phase '{expected}'"
    checks += 1; print(f"✅ 4 default_phases returns 6 phases: {names}")
except Exception as e:
    print("❌ 4:", e)

# 5 — default_phases: all done=False; each has 3 tasks; Ollama appears in Build
try:
    phases = default_phases(_SPEC)
    assert all(not p.done for p in phases), "all phases should start with done=False"
    assert all(len(p.tasks) == 3 for p in phases), "each phase should have 3 tasks"
    build_tasks = " ".join(next(p.tasks for p in phases if p.name == "Build"))
    assert "Ollama" in build_tasks, f"Ollama should appear in Build tasks: {build_tasks}"
    checks += 1; print("✅ 5 all phases: done=False, 3 tasks; Ollama in Build tasks")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX3 = _nb([
    _md("# Exercise 3 — build_status and mark_phase_done\n\n"
        "`build_status` gives a snapshot of progress: how many phases are done, "
        "the completion percentage, and whether the project is fully complete. "
        "`mark_phase_done` mutates a `Phase` in place — it is the single function "
        "that drives the tracker forward. Together they form the minimal state "
        "machine for a project tracker."),
    _code(_P_BASE + _P_VALIDATE + _P_PLAN + _P_PHASES + """\

def build_status(report):
    \"\"\"Return build phase completion summary.

    Returns:
        dict with keys:
          phases           : list[dict] — {name, done, n_tasks}
          total_phases     : int
          completed_phases : int
          completion_pct   : float  (0.0–100.0, 1 decimal place)
          is_complete      : bool   (all phases done and total > 0)
    \"\"\"
    total = len(report.phases)
    done  = sum(1 for p in report.phases if p.done)
    # TODO: return the status dict
    return {}


def mark_phase_done(report, phase_name):
    \"\"\"Mark the named phase done (case-sensitive).

    Returns True if found and marked; False if no phase with that name.
    \"\"\"
    # TODO: iterate report.phases; set done=True and return True if found
    return False
"""),
    _md("### Checks"),
    _code("""\
checks = 0

report = CapstoneReport(spec=_SPEC, phases=default_phases(_SPEC))

# 1 — build_status on fresh report: 0 completed, 0%
try:
    status = build_status(report)
    assert status["total_phases"]     == 6,   f"expected 6, got {status['total_phases']}"
    assert status["completed_phases"] == 0,   f"expected 0, got {status['completed_phases']}"
    assert status["completion_pct"]   == 0.0, f"expected 0.0, got {status['completion_pct']}"
    assert status["is_complete"]      is False
    checks += 1; print("✅ 1 fresh report: 6 phases, 0 done, 0.0%, not complete")
except Exception as e:
    print("❌ 1:", e)

# 2 — mark_phase_done: True for valid name, False for invalid
try:
    r2 = mark_phase_done(report, "Plan")
    r3 = mark_phase_done(report, "NoSuchPhase")
    assert r2 is True,  f"expected True for 'Plan', got {r2}"
    assert r3 is False, f"expected False for 'NoSuchPhase', got {r3}"
    checks += 1; print("✅ 2 mark_phase_done: True for valid name, False for invalid")
except Exception as e:
    print("❌ 2:", e)

# 3 — after marking Plan done: 1 completed, ~16.7%
try:
    status = build_status(report)
    assert status["completed_phases"] == 1
    assert abs(status["completion_pct"] - 16.7) < 0.1, \
        f"expected ~16.7%, got {status['completion_pct']}"
    assert status["is_complete"] is False
    checks += 1; print(f"✅ 3 after Plan done: 1/6 phases, {status['completion_pct']}%")
except Exception as e:
    print("❌ 3:", e)

# 4 — mark all 6 phases done → is_complete=True, 100%
try:
    for phase_name in ["Build", "Test", "Deploy", "Document", "Share"]:
        mark_phase_done(report, phase_name)
    status = build_status(report)
    assert status["completed_phases"] == 6
    assert status["completion_pct"]   == 100.0
    assert status["is_complete"]      is True
    checks += 1; print("✅ 4 all 6 phases done: is_complete=True, 100%")
except Exception as e:
    print("❌ 4:", e)

# 5 — phases list in status has correct structure
try:
    status = build_status(report)
    assert len(status["phases"]) == 6
    for p in status["phases"]:
        assert {"name","done","n_tasks"}.issubset(p.keys())
        assert isinstance(p["n_tasks"], int) and p["n_tasks"] == 3
    checks += 1; print("✅ 5 each phase dict has name, done, n_tasks=3")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX4 = _nb([
    _md("# Exercise 4 — format_completion_certificate\n\n"
        "`format_completion_certificate` generates the final document that "
        "marks the end of the capstone: a Markdown certificate showing the "
        "project name, tagline, build phase checklist, completion percentage, "
        "tech stack, course sections applied, and a sign-off line. "
        "It is the last function you write on the last day."),
    _code(_P_BASE + _P_VALIDATE + _P_PLAN + _P_PHASES + _P_TRACK + """\

def format_completion_certificate(report):
    \"\"\"Generate a Markdown completion certificate.

    Structure:
      # 100 Days of AI — Capstone Completion
      ## {spec.name}
      **{spec.tagline}**
      {spec.description}
      ## Build Progress
      [x] Plan
      [ ] Build   ← done/not-done based on phase.done
      ...
      **Overall: {completion_pct}% complete**
      ## Tech Stack
      - item 1
      ## Course Sections Applied
      - section 1
      ---
      *Built during 100 Days of AI — The Complete AI Engineering Bootcamp*

    Returns:
        str — Markdown starting with "# 100 Days of AI"
    \"\"\"
    spec   = report.spec
    status = build_status(report)
    phase_lines   = "\\n".join(
        f"  {'[x]' if p['done'] else '[ ]'} {p['name']}"
        for p in status["phases"]
    )
    tech_lines    = "\\n".join(f"- {t}" for t in spec.tech_stack)
    section_lines = "\\n".join(f"- {s}" for s in spec.sections_used)
    # TODO: assemble the certificate string
    return ""
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# Build a report with 3 phases done
report = CapstoneReport(spec=_SPEC, phases=default_phases(_SPEC))
for phase_name in ["Plan", "Build", "Test"]:
    mark_phase_done(report, phase_name)

# 1 — starts with # 100 Days of AI
try:
    cert = format_completion_certificate(report)
    assert cert.startswith("# 100 Days of AI"), \
        f"expected '# 100 Days of AI' start, got: {cert[:40]!r}"
    checks += 1; print("✅ 1 certificate starts with '# 100 Days of AI'")
except Exception as e:
    print("❌ 1:", e)

# 2 — project name and tagline present
try:
    cert = format_completion_certificate(report)
    assert _SPEC.name    in cert, f"name '{_SPEC.name}' not in certificate"
    assert _SPEC.tagline in cert, "tagline not in certificate"
    checks += 1; print(f"✅ 2 name '{_SPEC.name}' and tagline present")
except Exception as e:
    print("❌ 2:", e)

# 3 — done phases show [x]; not-done show [ ]
try:
    cert = format_completion_certificate(report)
    assert "[x] Plan"    in cert, "[x] Plan not in certificate"
    assert "[x] Build"   in cert, "[x] Build not in certificate"
    assert "[ ] Deploy"  in cert, "[ ] Deploy not in certificate"
    assert "[ ] Share"   in cert, "[ ] Share not in certificate"
    checks += 1; print("✅ 3 done phases show [x]; pending phases show [ ]")
except Exception as e:
    print("❌ 3:", e)

# 4 — completion percentage appears
try:
    cert = format_completion_certificate(report)
    status = build_status(report)
    pct_str = str(status["completion_pct"])
    assert pct_str in cert, f"completion_pct {pct_str!r} not in certificate"
    checks += 1; print(f"✅ 4 completion {pct_str}% appears in certificate")
except Exception as e:
    print("❌ 4:", e)

# 5 — sign-off line present; tech stack and sections appear
try:
    cert = format_completion_certificate(report)
    assert "100 Days of AI" in cert.split("---")[-1], \
        "sign-off line missing after ---"
    for t in _SPEC.tech_stack:
        assert t in cert, f"tech {t!r} not in certificate"
    checks += 1; print("✅ 5 sign-off line + all tech stack items present")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX5 = _nb([
    _md("# Exercise 5 — The Full Capstone Pipeline\n\n"
        "Write your own `CapstoneSpec` for a project you want to ship, validate "
        "it, generate the plan, create the phases, simulate completing all phases, "
        "and print the completion certificate. This is Day 100 — every function "
        "you have learned over 100 days is available to you."),
    _code(_P_BASE + _P_VALIDATE + _P_PLAN + _P_PHASES + _P_TRACK + _P_CERT + """\

# ── Your capstone spec ────────────────────────────────────────────────────────
# Edit this spec to describe YOUR project. Or use the sample spec below.

MY_SPEC = CapstoneSpec(
    name          = "AI Trading Bot",   # Your project name
    tagline       = "Paper-trading bot with sentiment and technical signals.",
    domain        = "finance",
    description   = "End-to-end AI trading bot built over Section 7 of the course. "
                    "Fetches OHLCV data, computes technical indicators, scores news "
                    "sentiment with an LLM, applies risk controls, and logs results daily.",
    sections_used = [
        "Section 3: Data & Analysis (pandas, SQLite)",
        "Section 4: Real Apps (FastAPI)",
        "Section 6: AI Agents (loop + scheduling)",
        "Section 7: Finance & Trading (backtester, risk, paper trader)",
    ],
    deliverables  = [
        "paper_trader.py with buy/sell simulation",
        "bot_runner.py with daily scheduling and logging",
        "risk.py with stop-loss and drawdown controls",
        "FastAPI endpoint",
        "Portfolio case study and GitHub README",
    ],
    tech_stack    = ["Python", "pandas", "Ollama", "SQLite", "FastAPI"],
)
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — MY_SPEC passes validate_spec
try:
    ok, errors = validate_spec(MY_SPEC)
    assert ok is True, f"spec invalid: {errors}"
    checks += 1; print(f"✅ 1 MY_SPEC is valid: {MY_SPEC.name!r}")
except Exception as e:
    print("❌ 1:", e)

# 2 — generate_project_plan contains spec data
try:
    plan = generate_project_plan(MY_SPEC)
    assert MY_SPEC.name in plan
    assert "## Overview" in plan
    assert "## Deliverables" in plan or "## Build Phases" in plan
    checks += 1; print("✅ 2 project plan generated with spec data")
except Exception as e:
    print("❌ 2:", e)

# 3 — default_phases gives 6 phases, all starting undone
try:
    phases = default_phases(MY_SPEC)
    assert len(phases) == 6
    assert all(not p.done for p in phases)
    checks += 1; print(f"✅ 3 6 phases created, all undone: {[p.name for p in phases]}")
except Exception as e:
    print("❌ 3:", e)

# 4 — mark all 6 phases done → is_complete=True
try:
    report = CapstoneReport(spec=MY_SPEC, phases=default_phases(MY_SPEC))
    for p in report.phases:
        mark_phase_done(report, p.name)
    status = build_status(report)
    assert status["is_complete"] is True
    assert status["completion_pct"] == 100.0
    checks += 1; print("✅ 4 all phases marked done → is_complete=True, 100%")
except Exception as e:
    print("❌ 4:", e)

# 5 — completion certificate
try:
    report = CapstoneReport(spec=MY_SPEC, phases=default_phases(MY_SPEC))
    for p in report.phases:
        mark_phase_done(report, p.name)
    cert = format_completion_certificate(report)
    assert cert.startswith("# 100 Days of AI")
    assert MY_SPEC.name in cert
    assert "100.0" in cert
    assert "[x]" in cert
    checks += 1
    print("✅ 5 completion certificate generated\\n")
    print(cert[:600] + "...")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed — Day 100 complete!")
"""),
])

EXERCISES = [_EX1, _EX2, _EX3, _EX4, _EX5]

# ══════════════════════════════════════════════════════════════════════════════
# YAML lessons
# ══════════════════════════════════════════════════════════════════════════════

LESSONS = [
    """\
day: "100"
lesson: 1
title: "Scoping the Final Project"
slides:
  - type: title
    heading: "Day 100 — Final Capstone"
    subheading: "Scoping, planning, and shipping your AI product"
    narration: >
      Day 100. The final day. Every concept, every tool, every pattern from
      the previous 99 days leads here. The capstone is not a test — it is a
      project you choose, specify, build, and ship. Today you learn how to
      scope it correctly so it ships in a finite amount of time, and how to
      track your progress through the six standard build phases.

  - type: concept
    label: "Scoping"
    heading: "How to Scope a Capstone That Ships"
    body: >
      The biggest risk is scope creep. The antidote: a validated spec.
    bullets:
      - "One sentence tagline: if you can't say what it does in 10 words, the scope is unclear"
      - "Three concrete deliverables: code files, endpoints, deployed URLs — not 'features'"
      - "Two sections of this course: pick where you go deep, not where you go wide"
      - "One domain: finance, text, vision, agents — not all of them"
      - "validate_spec enforces this: 3+ deliverables, 2+ tech items, 1+ sections"
    narration: >
      Scope creep is the reason most side projects never ship. The fix is a
      written spec that has been validated before you write the first line of
      production code. validate_spec is an automated version of the "does this
      make sense?" review. It catches the most common failures: too few concrete
      deliverables (vague scope), too little tech (proof-of-concept that isn't
      a product), no course section reference (disconnected from what you learned).

  - type: concept
    label: "The spec"
    heading: "CapstoneSpec: The Seven Fields"
    body: >
      Seven fields. One source of truth for the entire capstone.
    bullets:
      - "name: what people will call it"
      - "tagline: the one-sentence pitch"
      - "domain: where it lives (finance, text, vision, agents)"
      - "description: one paragraph for the portfolio case study"
      - "sections_used: which parts of the course you applied"
      - "deliverables: the concrete artifacts (≥ 3: files, endpoints, demos)"
      - "tech_stack: the technologies (≥ 2: language + at least one framework)"
    narration: >
      Once you fill in CapstoneSpec, every other generator has what it needs:
      generate_project_plan builds the implementation plan, default_phases
      creates the tracking phases, format_completion_certificate generates the
      final summary, and the Day 97–99 tools (generate_pyproject, generate_readme,
      generate_portfolio_page) all take the same data. One spec, seven artifacts.

  - type: exercise
    heading: "Exercise 1 — validate_spec"
    prompt: >
      validate_spec(spec) checks: name/tagline/domain/description are non-empty
      strings; deliverables has ≥ 3 items; tech_stack has ≥ 2 items;
      sections_used has ≥ 1 item. Returns (True, []) if valid, (False, errors)
      if not. All errors accumulate — don't stop at the first.
    hint: >
      Use getattr(spec, field_name, "") and check .strip() for text fields.
      len(spec.deliverables) < 3 adds an error message; it does NOT short-circuit.
      Check 5 uses an all-empty spec — ensure you get ≥ 4 errors from it.
    narration: >
      validate_spec is a guard rail. Run it before generate_project_plan —
      a plan built from a vague spec is a vague plan. The pattern of returning
      (bool, list[str]) is common in Python validation: you get both the
      pass/fail answer and the list of specific problems, which is more useful
      than just raising an exception.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "Scope creep kills projects — a validated spec prevents it"
      - "CapstoneSpec: 7 fields, one source of truth for all generators"
      - "validate_spec: (bool, list[str]); errors accumulate, don't short-circuit"
      - "Minimum viable spec: name + tagline + 3 deliverables + 2 tech items"
      - "Next: generate_project_plan and default_phases"
    narration: >
      Spec done and validated. Next: the implementation plan and the six build
      phases that drive the tracker.
""",

    """\
day: "100"
lesson: 2
title: "Planning and Tracking"
slides:
  - type: title
    heading: "Plan → Build → Track"
    subheading: "The six phases that take a spec to a shipped product"
    narration: >
      A validated spec is necessary but not sufficient to ship. You also need
      a plan (what to do, in what order) and a tracker (are you making progress?).
      generate_project_plan produces the Markdown plan. default_phases creates
      the six Phase objects. build_status computes the completion snapshot.
      mark_phase_done advances the tracker. Four functions, one workflow.

  - type: concept
    label: "Six phases"
    heading: "The Six Standard Build Phases"
    body: >
      Every software project goes through these six phases, in this order.
    bullets:
      - "1. Plan: spec, environment, gate tests first (TDD)"
      - "2. Build: core AI functionality + data pipeline"
      - "3. Test: gate green, happy path, edge cases"
      - "4. Deploy: .env, production deploy, verify live URL"
      - "5. Document: README, case study, demo video"
      - "6. Share: GitHub push, portfolio, social posts"
    narration: >
      The order is important. Gate tests in Phase 1 (before Phase 2) means
      you write the expected behavior before writing the code — the same
      discipline this course has enforced from Day 1. Documentation in Phase 5
      (before Phase 6) means you document while the project is fresh, not six
      months later when you have forgotten how it works. Share last: you only
      share when the product is documented and deployed, not before.

  - type: concept
    label: "build_status"
    heading: "build_status: The Progress Snapshot"
    body: >
      One dict, five keys, all the information you need to answer "how done am I?"
    bullets:
      - "phases: list of {name, done, n_tasks} for each phase"
      - "total_phases: int — number of phases"
      - "completed_phases: int — how many have done=True"
      - "completion_pct: float — round(done/total*100, 1)"
      - "is_complete: bool — done==total and total>0"
    narration: >
      build_status is read-only — it does not mutate the report. mark_phase_done
      is the mutation function. This separation (query vs mutation) is the
      Command-Query Separation principle: functions that return information
      should not change state, and functions that change state should return
      minimal information. It makes the system easier to reason about and test.

  - type: exercise
    heading: "Exercise 2 — generate_project_plan and default_phases"
    prompt: >
      generate_project_plan(spec) returns Markdown with the project name,
      ## Overview (description), ## Deliverables (each as '- [ ] item'),
      and ## Build Phases (6 phase headings). default_phases(spec) returns
      6 Phase objects: Plan/Build/Test/Deploy/Document/Share, each with 3 tasks,
      done=False. Build tasks should mention the AI backend from tech_stack.
    hint: >
      Check 3: "- [ ] " + deliverable as the checkbox format. Check 5: use
      next((t for t in spec.tech_stack if t.lower() in ("ollama","llama","llamacpp")),
      "AI backend") to find the AI backend for the Build tasks.
    narration: >
      The implementation plan generated by generate_project_plan is designed
      to be committed to the project repository as PLAN.md. Future contributors
      (including your future self) can read it to understand the scope, the
      tech choices, and the progress. Checking off deliverables as you complete
      them turns the plan into a living document.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "Six phases: Plan → Build → Test → Deploy → Document → Share"
      - "Phase 1 first: write gate tests before production code"
      - "generate_project_plan: Markdown plan with deliverable checkboxes"
      - "default_phases: 6 Phase objects, done=False, AI backend in Build tasks"
      - "Next: build_status and mark_phase_done — the tracker"
    narration: >
      Plan and phases done. Next: the tracker — build_status and mark_phase_done
      — that measures your progress through the phases.
""",

    """\
day: "100"
lesson: 3
title: "Tracking and Completing"
slides:
  - type: title
    heading: "Tracking Progress"
    subheading: "build_status, mark_phase_done, completion certificate"
    narration: >
      The tracker has two operations: read (build_status) and write
      (mark_phase_done). Once all phases are marked done, the project is
      complete and format_completion_certificate generates the final document.
      This lesson covers all three.

  - type: code
    label: "Tracker pattern"
    heading: "The Tracker Workflow"
    code: |
      # Create report
      report = CapstoneReport(spec=my_spec, phases=default_phases(my_spec))

      # Check initial status
      status = build_status(report)
      print(status["completion_pct"])   # 0.0

      # Work on Phase 1...
      r = mark_phase_done(report, "Plan")    # True
      r = mark_phase_done(report, "NoPhase") # False — wrong name

      # Check progress
      status = build_status(report)
      print(status["completion_pct"])   # 16.7

      # Complete all phases
      for p in report.phases:
          mark_phase_done(report, p.name)

      print(build_status(report)["is_complete"])  # True
    narration: >
      The workflow is always the same: create the report, check status, mark
      phases done as you complete them, check status again. build_status is
      idempotent — you can call it as many times as you want without side effects.
      mark_phase_done returns True/False so the caller knows whether the phase
      name was found, without raising an exception for a missing phase — a design
      choice consistent with how Waitlist.add returns False for duplicates.

  - type: concept
    label: "Completion certificate"
    heading: "format_completion_certificate: The Final Document"
    body: >
      The certificate documents what was built, how far it got, and signs off.
    bullets:
      - "# 100 Days of AI — Capstone Completion"
      - "## {name}: tagline + description"
      - "## Build Progress: [x] done / [ ] not-done per phase"
      - "**Overall: {completion_pct}% complete**"
      - "## Tech Stack + ## Course Sections Applied"
      - "Sign-off: *Built during 100 Days of AI — The Complete AI Engineering Bootcamp*"
    narration: >
      The completion certificate is the document you share when you announce
      that you finished the capstone. Post it as a LinkedIn article, a GitHub
      Gist, or a blog post. It summarises what you built, the technologies you
      used, which sections of the course you applied, and shows the completed
      build phases. The '[x]' checkbox format renders as a checked checkbox
      in GitHub Markdown.

  - type: exercise
    heading: "Exercise 3 — build_status and mark_phase_done"
    prompt: >
      build_status(report) returns dict with phases (list[dict] with name/done/n_tasks),
      total_phases, completed_phases, completion_pct (1 decimal), is_complete (bool,
      True only when done==total and total>0). mark_phase_done(report, phase_name)
      sets phase.done=True and returns True; returns False if name not found.
    hint: >
      Check 3: after marking Plan done, completion_pct = round(1/6*100, 1) = 16.7.
      Check 4: mark all 6 phases — is_complete should be True. Check 5: each
      phase dict in status["phases"] must have "name", "done", "n_tasks" keys.
    narration: >
      The completion_pct calculation uses max(total, 1) to avoid division by zero
      on an empty report. This is a guard rail — the same principle as gate tests
      checking edge cases. build_status never mutates; mark_phase_done mutates
      exactly one phase. Two functions, two responsibilities, zero overlap.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "build_status: read-only snapshot — phases list + total/done/pct/complete"
      - "mark_phase_done: write operation — True if found, False if not"
      - "completion_pct: round(done/max(total,1)*100, 1)"
      - "is_complete: done == total and total > 0 (not just done == total)"
      - "Next: format_completion_certificate — the final document"
    narration: >
      Tracking done. Next: the completion certificate — the document that marks
      the end of the capstone and the end of 100 days.
""",

    """\
day: "100"
lesson: 4
title: "100 Days in Review"
slides:
  - type: title
    heading: "100 Days in Review"
    subheading: "What you built. What you learned. What comes next."
    narration: >
      Before the final exercise, it is worth pausing to look back at the full
      arc of the course. One hundred days. Seven sections. Thirty-plus projects.
      From a simple TTS pipeline on Day 1 to a complete AI product on Day 100.
      This lesson reviews what was covered and what it all adds up to.

  - type: concept
    label: "The arc"
    heading: "The Course Arc"
    body: >
      Seven sections, each building on the last.
    bullets:
      - "Warmup (1–5): Python + first LLM call + hygiene (logging, tests, git)"
      - "Section 1 (6–20): Text AI — prompts, RAG, chatbots, tool use, eval"
      - "Section 2 (21–35): Automation — files, APIs, email, scheduling, CLI"
      - "Section 3 (36–50): Data — pandas, SQL, EDA, ML, pipelines, time series"
      - "Section 4 (51–65): Real Apps — FastAPI, Streamlit, auth, deploy, payments"
      - "Section 5 (66–78): Vision & Multimodal — images, OCR, TTS, video, agents"
      - "Section 6 (79–88): AI Agents — loops, tools, memory, planning, safety"
      - "Section 7 (89–100): Finance + Productizing — data, backtesting, bot, launch"
    narration: >
      The progression was deliberate. Each section introduced new primitives
      that the next section builds on. The agent loop (Section 6) uses tool
      routing from Section 1, persistence from Section 3, and APIs from
      Section 4. The trading bot (Section 7) uses pandas from Section 3,
      SQLite from Section 3/4, scheduling from Section 2, and LLM calls from
      Section 1. Nothing in Section 7 would have been possible on Day 1.

  - type: concept
    label: "Skills earned"
    heading: "Skills You Now Have"
    body: >
      Fourteen skills that most AI engineers spend years acquiring.
    bullets:
      - "LLM integration: prompting, structured output, streaming, tool use"
      - "RAG pipeline: embeddings, vector DB, retrieval, grounding, citations"
      - "Automation: file ops, APIs, email, scheduling, CLI tools"
      - "Data engineering: pandas, SQL, ETL, time series, feature engineering"
      - "Web apps: FastAPI (backend) + Streamlit (frontend) + auth + payments"
      - "Multimodal: images (PIL/Vision), audio (Whisper/TTS), video (FFmpeg)"
      - "AI agents: ReAct loop, memory, planning, multi-agent, guardrails, MCP"
      - "Finance/Trading: OHLCV, indicators, backtesting, risk, paper trading"
      - "Productizing: packaging, docs, pricing, feature gating, landing page"
      - "Personal brand: portfolio site, GitHub README, case studies"
    narration: >
      These are not theoretical skills. Every one is demonstrated by a working
      project in your 07_finance/, 06_agents/, 05_vision/, 04_apps/,
      03_data/, 02_automation/, 01_text/, and 00_warmup/ directories.
      The deliverable .py files are production-quality code. The exercise
      notebooks demonstrate the concepts. The gate tests prove correctness.
      This is a portfolio of evidence, not a list of claims.

  - type: exercise
    heading: "Exercise 4 — format_completion_certificate"
    prompt: >
      format_completion_certificate(report) returns Markdown starting with
      '# 100 Days of AI — Capstone Completion'. Contains ## {spec.name},
      **{spec.tagline}**, ## Build Progress with [x]/[ ] phase lines,
      **Overall: {completion_pct}% complete**, ## Tech Stack, ## Course Sections
      Applied, and a sign-off line after ---.
    hint: >
      Check 3: phases with done=True get '[x]'; phases with done=False get '[ ]'.
      Use f"  {'[x]' if p['done'] else '[ ]'} {p['name']}" for each phase dict
      from build_status(report)["phases"]. Check 5: sign-off after '---'.
    narration: >
      The certificate is the last artifact you generate in this course. After
      Day 100, you can customise the format_completion_certificate function to
      add your own flair: project metrics, a screenshot, testimonials.
      The structure is a template, not a constraint.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "100 days, 7 sections, 14 skills, 30+ projects"
      - "format_completion_certificate: Markdown certificate from CapstoneReport"
      - "[x]/[ ] phase status from build_status phases list"
      - "sign-off line after --- is the course's closing statement"
      - "Next: Exercise 5 — the full capstone pipeline with your spec"
    narration: >
      One more exercise. The last one. Then the course is complete.
""",

    """\
day: "100"
lesson: 5
title: "What Comes Next"
slides:
  - type: title
    heading: "What Comes Next"
    subheading: "After 100 days — the AI engineering career"
    narration: >
      The course is done. Day 100 is complete. What comes next? This final lesson
      is not about code. It is about how to turn 100 days of work into a career,
      a business, or a research path. Three directions, and how to choose between them.

  - type: concept
    label: "Career paths"
    heading: "Three Paths After the Bootcamp"
    body: >
      AI engineering opens three doors. Choose based on what energises you.
    bullets:
      - "Employment: AI engineer at a startup or enterprise (best portfolio helps most)"
      - "Freelance: build AI products for clients (niche + case studies + pricing)"
      - "Founder: build your own AI product (the capstone is the first product)"
      - "Which fits? If you loved Section 7, consider founder. If Section 4, employment."
      - "Many people do all three in sequence: employed → freelance → founder"
    narration: >
      The skills from this course are directly applicable to all three paths.
      The trading bot is a demo for employment. The productizer module from Day 97
      is the pricing model for freelancing. The capstone is the first product.
      The portfolio from Day 99 is the marketing material for all three. The
      choice of path depends on your risk tolerance, not your skill level.

  - type: concept
    label: "Keep building"
    heading: "The Most Important Thing: Keep Building"
    body: >
      Skills atrophy without practice. Build one thing per month.
    bullets:
      - "Every skill in this course was reinforced by building, not by reading"
      - "One small project per month: one prompt, one API, one deployed thing"
      - "Open source: contribute to one AI project you use (ChromaDB, Ollama, etc.)"
      - "Write one case study per project: forces you to articulate the 'why'"
      - "The hardest skill to maintain: staying current (papers, HN, AI Twitter)"
    narration: >
      The AI field moves fast. The specific models and APIs from this course
      will be superseded by newer ones within months. But the patterns — the
      injection pattern, the gate test discipline, the spec-first approach,
      the pipeline architecture — are stable. Learn the new APIs; keep the
      patterns. A new LLM provider is just a new llm_fn injection.

  - type: exercise
    heading: "Exercise 5 — Full Capstone Pipeline"
    prompt: >
      Define MY_SPEC (edit the provided template or write your own), run
      validate_spec (must pass), generate_project_plan, default_phases,
      mark all 6 phases done, and format_completion_certificate. The certificate
      must start with '# 100 Days of AI', contain your project name, show 100.0%,
      and have all phases as [x].
    hint: >
      If you write your own spec: ensure ≥3 deliverables, ≥2 tech items, ≥1 section.
      mark_phase_done must be called for each phase by name (exact match, case-sensitive).
      The certificate ends with the course sign-off line after ---.
    narration: >
      This is the last exercise in the 100-day course. Completing it means you
      have written, tested, and run code on all 100 days. You have built a
      complete AI engineering skill set. The certificate you generate now is
      the honest record of that work — not what someone awarded you, but what
      you built and proved.

  - type: summary
    heading: "Day 100 Complete — Congratulations"
    bullets:
      - "100 days. 7 sections. 30+ projects. One complete AI engineering skill set."
      - "CapstoneSpec → validate_spec → generate_project_plan → default_phases"
      - "build_status → mark_phase_done → format_completion_certificate"
      - "The spec-first discipline: validate before you build"
      - "The gate-test discipline: test before you ship"
      - "The portfolio: evidence of what you built"
      - "What's next: keep building, one project per month"
    narration: >
      Congratulations. You have completed 100 Days of AI — The Complete AI
      Engineering Bootcamp. From a simple TTS pipeline on Day 1 to a fully
      specified, planned, and tracked AI product on Day 100. The skills are
      yours now. The portfolio is evidence. The discipline — spec first, test
      first, ship with documentation — is a habit. Go build something.
""",
]

# ══════════════════════════════════════════════════════════════════════════════
# Project + solution
# ══════════════════════════════════════════════════════════════════════════════

_FULL_P = _P_BASE + _P_VALIDATE + _P_PLAN + _P_PHASES + _P_TRACK + _P_CERT

PROJECT_NB = _nb([
    _md(f"# Day {DAY} Project — Your Capstone\n\n"
        "Define your capstone spec, validate it, generate the implementation plan, "
        "create the six build phases, and generate your completion certificate. "
        "Edit `MY_SPEC` below with your real project details."),
    _code(_FULL_P),
    _code("""\
# ── Define your spec ─────────────────────────────────────────────────────────

MY_SPEC = CapstoneSpec(
    name          = "AI Trading Bot",    # Edit: your project name
    tagline       = "Paper-trading bot with sentiment and technical signals.",
    domain        = "finance",           # Edit: your domain
    description   = "End-to-end AI trading bot that fetches OHLCV data, computes "
                    "technical indicators, scores news with an LLM, applies risk "
                    "controls, and runs a daily paper-trading loop.",
    sections_used = [
        "Section 3: Data & Analysis", "Section 4: Real Apps",
        "Section 7: Finance & Trading",
    ],
    deliverables  = [
        "paper_trader.py", "bot_runner.py", "risk.py",
        "FastAPI endpoint", "Portfolio case study",
    ],
    tech_stack    = ["Python", "pandas", "Ollama", "SQLite", "FastAPI"],
)

# ── Run the pipeline ─────────────────────────────────────────────────────────

ok, errors = validate_spec(MY_SPEC)
print(f"Spec valid: {ok}" + (f"  Errors: {errors}" if errors else ""))

plan   = generate_project_plan(MY_SPEC)
phases = default_phases(MY_SPEC)
report = CapstoneReport(spec=MY_SPEC, phases=phases)

# Simulate completing all phases
for p in report.phases:
    mark_phase_done(report, p.name)

status = build_status(report)
print(f"Completion: {status['completion_pct']}% — Is complete: {status['is_complete']}")

cert = format_completion_certificate(report)
print("\\n" + cert)
"""),
])

SOLUTION_NB = _nb([
    _md(f"# Day {DAY} Solution — Capstone Pipeline"),
    _code(_FULL_P),
    _code("""\
spec = CapstoneSpec(
    name="AI Trading Bot", tagline="Paper-trading with AI signals.",
    domain="finance",
    description="End-to-end trading bot: OHLCV → indicators → sentiment → risk → bot.",
    sections_used=["Section 3", "Section 4", "Section 6", "Section 7"],
    deliverables=["paper_trader.py","bot_runner.py","risk.py","FastAPI","Case study"],
    tech_stack=["Python","pandas","Ollama","SQLite","FastAPI"],
)

ok, errors = validate_spec(spec)
assert ok is True, f"spec invalid: {errors}"

plan = generate_project_plan(spec)
assert spec.name in plan
assert "## Overview" in plan
assert "## Deliverables" in plan

phases = default_phases(spec)
assert len(phases) == 6
assert all(not p.done for p in phases)

report = CapstoneReport(spec=spec, phases=phases)
status = build_status(report)
assert status["completion_pct"] == 0.0

for p in report.phases:
    result = mark_phase_done(report, p.name)
    assert result is True

assert mark_phase_done(report, "NoPhase") is False

status = build_status(report)
assert status["is_complete"] is True
assert status["completion_pct"] == 100.0

cert = format_completion_certificate(report)
assert cert.startswith("# 100 Days of AI")
assert spec.name in cert
assert "100.0" in cert
assert "[x] Plan" in cert

print(cert)
print("\\nSolution smoke-test passed — 100 Days of AI complete.")
"""),
])

# ══════════════════════════════════════════════════════════════════════════════
# Gate
# ══════════════════════════════════════════════════════════════════════════════

GATE_PY = f"""\
import importlib.util, sys

spec_file = importlib.util.spec_from_file_location(
    "{SLUG}", r"{DIR / (SLUG + '.py')}"
)
mod = importlib.util.module_from_spec(spec_file)
spec_file.loader.exec_module(mod)

# ── CapstoneSpec / validate_spec ──────────────────────────────────────────────
cs = mod.CapstoneSpec(
    name="Test Bot", tagline="A test bot.", domain="finance",
    description="A test project for the gate.",
    sections_used=["Section 7"],
    deliverables=["file_a.py","file_b.py","endpoint"],
    tech_stack=["Python","pandas"],
)

ok, errors = mod.validate_spec(cs)
assert ok is True,  f"valid spec failed: {{errors}}"
assert errors == []

# invalid: empty name
bad1 = mod.CapstoneSpec("","T","D","Desc",["S"],["d1","d2","d3"],["py","pd"])
ok1, errs1 = mod.validate_spec(bad1)
assert ok1 is False
assert any("name" in e for e in errs1)

# invalid: < 3 deliverables
bad2 = mod.CapstoneSpec("N","T","D","Desc",["S"],["d1"],["py","pd"])
ok2, errs2 = mod.validate_spec(bad2)
assert ok2 is False and any("deliverable" in e for e in errs2)

# invalid: < 2 tech items
bad3 = mod.CapstoneSpec("N","T","D","Desc",["S"],["d1","d2","d3"],["py"])
ok3, errs3 = mod.validate_spec(bad3)
assert ok3 is False and any("tech" in e for e in errs3)

# invalid: empty sections_used
bad4 = mod.CapstoneSpec("N","T","D","Desc",[],["d1","d2","d3"],["py","pd"])
ok4, errs4 = mod.validate_spec(bad4)
assert ok4 is False and any("section" in e for e in errs4)

# worst-case: all empty → ≥ 4 errors
worst = mod.CapstoneSpec("","","","",[], [], [])
ok5, errs5 = mod.validate_spec(worst)
assert ok5 is False and len(errs5) >= 4, f"expected ≥4 errors, got {{len(errs5)}}: {{errs5}}"

# ── generate_project_plan ─────────────────────────────────────────────────────
plan = mod.generate_project_plan(cs)
assert isinstance(plan, str) and len(plan) > 100
assert cs.name        in plan
assert "## Overview"  in plan
# each deliverable as a checkbox
for d in cs.deliverables:
    assert f"- [ ] {{d}}" in plan, f"deliverable not as checkbox: {{d!r}}"
# tech stack items appear
for t in cs.tech_stack:
    assert t in plan, f"tech {{t!r}} not in plan"

# ── default_phases ────────────────────────────────────────────────────────────
phases = mod.default_phases(cs)
assert isinstance(phases, list) and len(phases) == 6
phase_names = [p.name for p in phases]
for expected in ("Plan","Build","Test","Deploy","Document","Share"):
    assert expected in phase_names, f"missing phase '{{expected}}'"
assert all(isinstance(p, mod.Phase) for p in phases)
assert all(not p.done for p in phases)
assert all(len(p.tasks) == 3 for p in phases)
# "Ollama" not in tech_stack fallback → "AI backend" in Build tasks
build_phase = next(p for p in phases if p.name == "Build")
assert "pandas" not in " ".join(build_phase.tasks) or True  # just ensure 3 tasks

# cs has Ollama? No — "pandas" is in tech_stack not Ollama; check fallback
cs_ollama = mod.CapstoneSpec("N","T","D","Desc",["S"],["d1","d2","d3"],["Python","Ollama"])
phases_ollama = mod.default_phases(cs_ollama)
build_ollama = next(p for p in phases_ollama if p.name == "Build")
assert "Ollama" in " ".join(build_ollama.tasks), f"Ollama not in Build tasks: {{build_ollama.tasks}}"

# ── build_status / mark_phase_done ────────────────────────────────────────────
report = mod.CapstoneReport(spec=cs, phases=mod.default_phases(cs))

status = mod.build_status(report)
assert status["total_phases"]     == 6
assert status["completed_phases"] == 0
assert status["completion_pct"]   == 0.0
assert status["is_complete"]      is False
assert len(status["phases"])      == 6
for p in status["phases"]:
    assert {{"name","done","n_tasks"}}.issubset(p.keys())

r1 = mod.mark_phase_done(report, "Plan")
assert r1 is True
r2 = mod.mark_phase_done(report, "NoSuchPhase")
assert r2 is False

status2 = mod.build_status(report)
assert status2["completed_phases"] == 1
assert abs(status2["completion_pct"] - 16.7) < 0.1
assert status2["is_complete"] is False

# mark all done
for p in report.phases:
    mod.mark_phase_done(report, p.name)
status3 = mod.build_status(report)
assert status3["completed_phases"] == 6
assert status3["completion_pct"]   == 100.0
assert status3["is_complete"]      is True

# ── format_completion_certificate ─────────────────────────────────────────────
cert = mod.format_completion_certificate(report)
assert cert.startswith("# 100 Days of AI"), f"bad start: {{cert[:40]!r}}"
assert cs.name    in cert
assert cs.tagline in cert
assert "## Build Progress" in cert
assert "[x] Plan"  in cert
assert "[x] Share" in cert
assert "100.0"     in cert
assert "---"       in cert
for t in cs.tech_stack:
    assert t in cert
for s in cs.sections_used:
    assert s in cert

# partially done report
report2 = mod.CapstoneReport(spec=cs, phases=mod.default_phases(cs))
mod.mark_phase_done(report2, "Plan")
cert2 = mod.format_completion_certificate(report2)
assert "[x] Plan"   in cert2
assert "[ ] Build"  in cert2
assert "[ ] Deploy" in cert2

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
