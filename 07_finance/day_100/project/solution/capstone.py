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
    deliverable_list = "\n".join(f"- [ ] {d}" for d in spec.deliverables)
    tech_list        = "\n".join(f"- {t}"       for t in spec.tech_stack)
    sections_list    = "\n".join(f"- {s}"       for s in spec.sections_used)

    return (
        f"# {spec.name} \u2014 Implementation Plan\n\n"
        f"**{spec.tagline}**\n\n"
        f"## Overview\n\n"
        f"{spec.description}\n\n"
        f"## Course Sections Applied\n\n"
        f"{sections_list}\n\n"
        f"## Tech Stack\n\n"
        f"{tech_list}\n\n"
        f"## Deliverables\n\n"
        f"{deliverable_list}\n\n"
        f"## Build Phases\n\n"
        f"### Phase 1 \u2014 Plan\n"
        f"- [ ] Finalise spec (validate_spec passes)\n"
        f"- [ ] Set up project structure and environment\n"
        f"- [ ] Write gate tests before coding\n\n"
        f"### Phase 2 \u2014 Build\n"
        f"- [ ] Implement core AI functionality\n"
        f"- [ ] Wire up data pipeline\n"
        f"- [ ] Integration tests pass\n\n"
        f"### Phase 3 \u2014 Test\n"
        f"- [ ] Gate: all checks green\n"
        f"- [ ] End-to-end happy path tested\n"
        f"- [ ] Edge cases handled\n\n"
        f"### Phase 4 \u2014 Deploy\n"
        f"- [ ] Write .env / config\n"
        f"- [ ] Deploy to production\n"
        f"- [ ] Verify live URL works\n\n"
        f"### Phase 5 \u2014 Document\n"
        f"- [ ] README with installation + usage\n"
        f"- [ ] Generate case study (portfolio.generate_case_study)\n"
        f"- [ ] Record demo video\n\n"
        f"### Phase 6 \u2014 Share\n"
        f"- [ ] Push to GitHub\n"
        f"- [ ] Add to portfolio site\n"
        f"- [ ] Post on LinkedIn / Twitter\n"
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

    phase_lines = "\n".join(
        f"  {'[x]' if p['done'] else '[ ]'} {p['name']}"
        for p in status["phases"]
    )
    tech_lines    = "\n".join(f"- {t}" for t in spec.tech_stack)
    section_lines = "\n".join(f"- {s}" for s in spec.sections_used)

    return (
        f"# 100 Days of AI \u2014 Capstone Completion\n\n"
        f"## {spec.name}\n\n"
        f"**{spec.tagline}**\n\n"
        f"{spec.description}\n\n"
        f"## Build Progress\n\n"
        f"{phase_lines}\n\n"
        f"**Overall: {status['completion_pct']}% complete**\n\n"
        f"## Tech Stack\n\n"
        f"{tech_lines}\n\n"
        f"## Course Sections Applied\n\n"
        f"{section_lines}\n\n"
        f"---\n\n"
        f"*Built during 100 Days of AI \u2014 The Complete AI Engineering Bootcamp*\n"
    )
