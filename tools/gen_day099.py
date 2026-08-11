#!/usr/bin/env python3
"""Day 099 generator — Portfolio & Personal Brand."""
import json, pathlib

ROOT  = pathlib.Path(__file__).parent.parent
DAY   = "099"
SLUG  = "portfolio"
TITLE = "Portfolio & Personal Brand"
DIR   = ROOT / "07_finance" / f"day_{DAY}"

# ══════════════════════════════════════════════════════════════════════════════
# Deliverable
# ══════════════════════════════════════════════════════════════════════════════

DELIVERABLE = '''\
"""
Day 099 — Portfolio & Personal Brand
======================================
Tools to generate a static portfolio site, case study documents,
a GitHub profile README, and portfolio analytics. All pure Python stdlib.

Public API
----------
    ProjectEntry                    — dataclass for one portfolio project
    PortfolioConfig                 — dataclass for portfolio metadata
    generate_portfolio_page(config) -> str  (HTML5 index page)
    generate_case_study(project)    -> str  (Markdown case study)
    generate_github_readme(config)  -> str  (GitHub profile README.md)
    summarize_portfolio(config)     -> dict (stats: n_projects, categories, top_tech)
    export_portfolio(config, output_dir) -> list[str]  (written file paths)
"""
import pathlib
from collections import Counter
from dataclasses import dataclass, field


# ── data model ────────────────────────────────────────────────────────────────

@dataclass
class ProjectEntry:
    """One portfolio project.

    Fields:
        name        : str  — project display name
        tagline     : str  — one-sentence description (shown on card + README)
        description : str  — paragraph for the case study Overview section
        tech_stack  : list[str] — technologies used (shown as tags on card)
        github_url  : str  — link to the GitHub repo (default "")
        demo_url    : str  — link to a live demo (default "")
        category    : str  — e.g. "AI Agents", "Finance" (default "AI Engineering")
        highlights  : list[str] — key achievements/metrics for the case study
    """
    name:        str
    tagline:     str
    description: str
    tech_stack:  list
    github_url:  str  = ""
    demo_url:    str  = ""
    category:    str  = "AI Engineering"
    highlights:  list = field(default_factory=list)


@dataclass
class PortfolioConfig:
    """Portfolio configuration used by all generators.

    Fields:
        owner_name      : str  — full name (shown in header and README)
        title           : str  — professional title, e.g. "AI Engineer"
        bio             : str  — 1-2 sentence personal summary
        email           : str  — contact email
        github_username : str  — GitHub username (used to build profile URL)
        linkedin_url    : str  — full LinkedIn profile URL (default "")
        projects        : list[ProjectEntry] — portfolio projects (default [])
    """
    owner_name:      str
    title:           str
    bio:             str
    email:           str
    github_username: str
    linkedin_url:    str  = ""
    projects:        list = field(default_factory=list)


# ── internal helpers ──────────────────────────────────────────────────────────

def _render_project_card(project):
    """Return an HTML <div class="card"> string for one project."""
    tech_tags = " ".join(
        f\'<span class="tag">{t}</span>\' for t in project.tech_stack
    )
    links = []
    if project.github_url:
        links.append(f\'<a href="{project.github_url}">GitHub</a>\')
    if project.demo_url:
        links.append(f\'<a href="{project.demo_url}">Demo</a>\')
    links_html = " \\u00b7 ".join(links)
    card = (
        \'      <div class="card">\\n\'
        f\'        <h3>{project.name}</h3>\\n\'
        f\'        <p class="category">{project.category}</p>\\n\'
        f\'        <p>{project.tagline}</p>\\n\'
        f\'        <div class="tags">{tech_tags}</div>\\n\'
    )
    if links_html:
        card += f\'        <p class="links">{links_html}</p>\\n\'
    card += \'      </div>\'
    return card


# ── generators ────────────────────────────────────────────────────────────────

def generate_portfolio_page(config):
    """Generate a complete HTML5 portfolio index page.

    Sections:
      <header>  — owner name (h1), title, bio, contact links
      <main>    — project grid (.grid) with one .card per project

    Each card shows: project name, category, tagline, tech tags, and
    optional GitHub/Demo links.

    Args:
        config : PortfolioConfig

    Returns:
        str — complete HTML document starting with <!DOCTYPE html>
    """
    project_cards = "\\n".join(_render_project_card(p) for p in config.projects)

    contact_parts = []
    if config.email:
        contact_parts.append(
            f\'<a href="mailto:{config.email}">{config.email}</a>\'
        )
    if config.github_username:
        contact_parts.append(
            f\'<a href="https://github.com/{config.github_username}">GitHub</a>\'
        )
    if config.linkedin_url:
        contact_parts.append(
            f\'<a href="{config.linkedin_url}">LinkedIn</a>\'
        )
    contact_html = " \\u00b7 ".join(contact_parts)

    return (
        "<!DOCTYPE html>\\n"
        \'<html lang="en">\\n\'
        "<head>\\n"
        \'  <meta charset="UTF-8">\\n\'
        \'  <meta name="viewport" content="width=device-width, initial-scale=1.0">\\n\'
        f"  <title>{config.owner_name} \\u2014 {config.title}</title>\\n"
        "  <style>\\n"
        "    body { font-family: system-ui, sans-serif; margin: 0; color: #1e293b; }\\n"
        "    header { background: #0f172a; color: white; padding: 60px 40px; }\\n"
        "    h1 { font-size: 2.5rem; margin: 0 0 8px; }\\n"
        "    .subtitle { font-size: 1.2rem; opacity: 0.8; margin: 0 0 12px; }\\n"
        "    .bio { max-width: 600px; opacity: 0.75; line-height: 1.6; margin: 0 0 16px; }\\n"
        "    .contact a { color: #93c5fd; text-decoration: none; }\\n"
        "    main { padding: 60px 40px; max-width: 1100px; margin: 0 auto; }\\n"
        "    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 24px; }\\n"
        "    .card { border: 1px solid #e2e8f0; border-radius: 12px; padding: 24px; }\\n"
        "    .card h3 { margin: 0 0 4px; }\\n"
        "    .category { font-size: 0.85rem; color: #64748b; margin: 0 0 12px; }\\n"
        "    .tag { background: #f1f5f9; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; margin: 2px; display: inline-block; }\\n"
        "    .links a { color: #2563eb; font-size: 0.9rem; }\\n"
        "  </style>\\n"
        "</head>\\n"
        "<body>\\n"
        "  <header>\\n"
        f"    <h1>{config.owner_name}</h1>\\n"
        f\'    <p class="subtitle">{config.title}</p>\\n\'
        f\'    <p class="bio">{config.bio}</p>\\n\'
        f\'    <p class="contact">{contact_html}</p>\\n\'
        "  </header>\\n"
        "  <main>\\n"
        "    <h2>Projects</h2>\\n"
        \'    <div class="grid">\\n\'
        f"{project_cards}\\n"
        "    </div>\\n"
        "  </main>\\n"
        "</body>\\n"
        "</html>"
    )


def generate_case_study(project):
    """Generate a Markdown case study document for one project.

    Structure:
      # project.name
      **Category:** ...
      ## Overview — tagline + description
      ## Tech Stack — bullet list
      ## Key Achievements — bullet list (or placeholder if highlights is empty)
      ## Links — GitHub + Demo URLs

    Args:
        project : ProjectEntry

    Returns:
        str — Markdown document starting with "# {project.name}"
    """
    tech_list   = "\\n".join(f"- {t}" for t in project.tech_stack)
    highlights  = (
        "\\n".join(f"- {h}" for h in project.highlights)
        if project.highlights
        else "- See project README for details"
    )
    links = []
    if project.github_url:
        links.append(f"- GitHub: {project.github_url}")
    if project.demo_url:
        links.append(f"- Demo: {project.demo_url}")
    links_text = "\\n".join(links) if links else "- See GitHub profile"

    return (
        f"# {project.name}\\n\\n"
        f"**Category:** {project.category}\\n\\n"
        f"## Overview\\n\\n"
        f"{project.tagline}\\n\\n"
        f"{project.description}\\n\\n"
        f"## Tech Stack\\n\\n"
        f"{tech_list}\\n\\n"
        f"## Key Achievements\\n\\n"
        f"{highlights}\\n\\n"
        f"## Links\\n\\n"
        f"{links_text}\\n"
    )


def generate_github_readme(config):
    """Generate a GitHub profile README.md.

    This is the special README that appears at github.com/{username} when
    you create a repository named the same as your username.

    Structure:
      # Hi, I\'m {owner_name}
      bio
      ## What I Build — title + one-liner
      ## Projects — bullet list from config.projects
      ## Tech Stack — up to 8 unique technologies (deduplicated, order-preserved)
      ## Contact — email + optional LinkedIn

    Args:
        config : PortfolioConfig

    Returns:
        str — Markdown document
    """
    project_lines = "\\n".join(
        f"- **[{p.name}]({p.github_url or \'#\'})** \\u2014 {p.tagline}"
        for p in config.projects
    )
    all_tech = []
    for p in config.projects:
        all_tech.extend(p.tech_stack)
    unique_tech = list(dict.fromkeys(all_tech))[:8]
    tech_line = " \\u00b7 ".join(unique_tech)

    linkedin_line = (
        f"- LinkedIn: {config.linkedin_url}\\n"
        if config.linkedin_url
        else ""
    )

    return (
        f"# Hi, I\'m {config.owner_name}\\n\\n"
        f"{config.bio}\\n\\n"
        f"## What I Build\\n\\n"
        f"I\'m an **{config.title}** focused on building practical AI "
        f"applications with Python.\\n\\n"
        f"## Projects\\n\\n"
        f"{project_lines}\\n\\n"
        f"## Tech Stack\\n\\n"
        f"{tech_line}\\n\\n"
        f"## Contact\\n\\n"
        f"- Email: [{config.email}](mailto:{config.email})\\n"
        f"{linkedin_line}"
    )


def summarize_portfolio(config):
    """Return summary statistics for the portfolio.

    Args:
        config : PortfolioConfig

    Returns:
        dict with keys:
            n_projects       : int — total number of projects
            categories       : list[str] — sorted unique category names
            n_categories     : int — number of unique categories
            top_tech         : list[str] — up to 5 most-used tech items
            total_tech_entries : int — total tech stack entries (with repetition)
    """
    categories = [p.category for p in config.projects]
    tech = []
    for p in config.projects:
        tech.extend(p.tech_stack)
    top_tech = [item for item, _ in Counter(tech).most_common(5)]
    return {
        "n_projects":         len(config.projects),
        "categories":         sorted(set(categories)),
        "n_categories":       len(set(categories)),
        "top_tech":           top_tech,
        "total_tech_entries": len(tech),
    }


def export_portfolio(config, output_dir):
    """Write portfolio files to output_dir.

    Writes:
      output_dir/index.html          — the portfolio index page
      output_dir/case_studies/<slug>.md — one case study per project
        (slug = project.name lowercased with spaces and hyphens → underscores)

    Creates output_dir and output_dir/case_studies/ if they do not exist.

    Args:
        config     : PortfolioConfig
        output_dir : str | pathlib.Path

    Returns:
        list[str] — absolute paths of all written files (index first, then cases)
    """
    out = pathlib.Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    written = []

    index_path = out / "index.html"
    index_path.write_text(generate_portfolio_page(config), encoding="utf-8")
    written.append(str(index_path))

    cases_dir = out / "case_studies"
    cases_dir.mkdir(exist_ok=True)
    for p in config.projects:
        slug = p.name.lower().replace(" ", "_").replace("-", "_")
        md_path = cases_dir / f"{slug}.md"
        md_path.write_text(generate_case_study(p), encoding="utf-8")
        written.append(str(md_path))

    return written
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
import pathlib, tempfile, os
from collections import Counter
from dataclasses import dataclass, field

@dataclass
class ProjectEntry:
    name: str; tagline: str; description: str; tech_stack: list
    github_url: str = ""; demo_url: str = ""; category: str = "AI Engineering"
    highlights: list = field(default_factory=list)

@dataclass
class PortfolioConfig:
    owner_name: str; title: str; bio: str; email: str; github_username: str
    linkedin_url: str = ""; projects: list = field(default_factory=list)

_P1 = ProjectEntry(
    name        = "AI Trading Bot",
    tagline     = "Paper-trading bot with sentiment + technical signals.",
    description = "Built over Days 89-96, this bot fetches OHLCV data, computes "
                  "technical indicators, scores news headlines with an LLM, applies "
                  "stop-loss and drawdown controls, and logs results daily.",
    tech_stack  = ["Python", "pandas", "Ollama", "SQLite"],
    github_url  = "https://github.com/testuser/ai-trading-bot",
    category    = "Finance",
    highlights  = ["Fully automated daily paper-trading loop",
                   "Kelly Criterion position sizing", "Stop-loss + drawdown gating"],
)
_P2 = ProjectEntry(
    name        = "Ops Agent",
    tagline     = "Autonomous multi-step ops agent with guardrails.",
    description = "Agent loop with tool routing, human-in-the-loop approval gates, "
                  "and task queue persistence.",
    tech_stack  = ["Python", "Ollama", "ChromaDB"],
    category    = "AI Agents",
    highlights  = ["Handles 5 operations autonomously", "Approval gate for destructive ops"],
)
_P3 = ProjectEntry(
    name        = "RAG Chatbot",
    tagline     = "Q&A chatbot grounded in your documents.",
    description = "Retrieval-augmented generation over a personal knowledge base.",
    tech_stack  = ["Python", "ChromaDB", "Ollama", "FastAPI"],
    github_url  = "https://github.com/testuser/rag-chatbot",
    demo_url    = "https://rag-chatbot.example.com",
    category    = "Text AI",
)

_CFG = PortfolioConfig(
    owner_name      = "Jane Doe",
    title           = "AI Engineer",
    bio             = "I build practical AI applications with Python. "
                      "100 days of AI engineering, shipped.",
    email           = "jane@example.com",
    github_username = "janedoe",
    linkedin_url    = "https://linkedin.com/in/janedoe",
    projects        = [_P1, _P2, _P3],
)
"""

_P_CARD = """\
def _render_project_card(project):
    tech_tags = " ".join(f'<span class="tag">{t}</span>' for t in project.tech_stack)
    links = []
    if project.github_url: links.append(f'<a href="{project.github_url}">GitHub</a>')
    if project.demo_url:   links.append(f'<a href="{project.demo_url}">Demo</a>')
    links_html = " · ".join(links)
    card = (
        '      <div class="card">\\n'
        f'        <h3>{project.name}</h3>\\n'
        f'        <p class="category">{project.category}</p>\\n'
        f'        <p>{project.tagline}</p>\\n'
        f'        <div class="tags">{tech_tags}</div>\\n'
    )
    if links_html:
        card += f'        <p class="links">{links_html}</p>\\n'
    card += '      </div>'
    return card
"""

_P_PAGE = """\
def generate_portfolio_page(config):
    project_cards = "\\n".join(_render_project_card(p) for p in config.projects)
    contact_parts = []
    if config.email:
        contact_parts.append(f'<a href="mailto:{config.email}">{config.email}</a>')
    if config.github_username:
        contact_parts.append(f'<a href="https://github.com/{config.github_username}">GitHub</a>')
    if config.linkedin_url:
        contact_parts.append(f'<a href="{config.linkedin_url}">LinkedIn</a>')
    contact_html = " · ".join(contact_parts)
    return (
        "<!DOCTYPE html>\\n"
        '<html lang="en">\\n'
        "<head>\\n"
        '  <meta charset="UTF-8">\\n'
        f"  <title>{config.owner_name} — {config.title}</title>\\n"
        "  <style>\\n"
        "    body { font-family: system-ui, sans-serif; margin: 0; }\\n"
        "    header { background: #0f172a; color: white; padding: 60px 40px; }\\n"
        "    h1 { font-size: 2.5rem; margin: 0 0 8px; }\\n"
        "    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 24px; }\\n"
        "    .card { border: 1px solid #e2e8f0; border-radius: 12px; padding: 24px; }\\n"
        "    .tag { background: #f1f5f9; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; }\\n"
        "  </style>\\n"
        "</head>\\n"
        "<body>\\n"
        "  <header>\\n"
        f"    <h1>{config.owner_name}</h1>\\n"
        f'    <p class="subtitle">{config.title}</p>\\n'
        f'    <p class="bio">{config.bio}</p>\\n'
        f'    <p class="contact">{contact_html}</p>\\n'
        "  </header>\\n"
        "  <main>\\n"
        "    <h2>Projects</h2>\\n"
        '    <div class="grid">\\n'
        f"{project_cards}\\n"
        "    </div>\\n"
        "  </main>\\n"
        "</body>\\n"
        "</html>"
    )
"""

_P_CASE = """\
def generate_case_study(project):
    tech_list  = "\\n".join(f"- {t}" for t in project.tech_stack)
    highlights = (
        "\\n".join(f"- {h}" for h in project.highlights)
        if project.highlights else "- See project README for details"
    )
    links = []
    if project.github_url: links.append(f"- GitHub: {project.github_url}")
    if project.demo_url:   links.append(f"- Demo: {project.demo_url}")
    links_text = "\\n".join(links) if links else "- See GitHub profile"
    return (
        f"# {project.name}\\n\\n"
        f"**Category:** {project.category}\\n\\n"
        f"## Overview\\n\\n"
        f"{project.tagline}\\n\\n"
        f"{project.description}\\n\\n"
        f"## Tech Stack\\n\\n"
        f"{tech_list}\\n\\n"
        f"## Key Achievements\\n\\n"
        f"{highlights}\\n\\n"
        f"## Links\\n\\n"
        f"{links_text}\\n"
    )
"""

_P_GH = """\
def generate_github_readme(config):
    project_lines = "\\n".join(
        f"- **[{p.name}]({p.github_url or '#'})** — {p.tagline}"
        for p in config.projects
    )
    all_tech = []
    for p in config.projects: all_tech.extend(p.tech_stack)
    unique_tech = list(dict.fromkeys(all_tech))[:8]
    tech_line = " · ".join(unique_tech)
    linkedin_line = f"- LinkedIn: {config.linkedin_url}\\n" if config.linkedin_url else ""
    return (
        f"# Hi, I'm {config.owner_name}\\n\\n"
        f"{config.bio}\\n\\n"
        f"## What I Build\\n\\n"
        f"I'm an **{config.title}** focused on building practical AI applications.\\n\\n"
        f"## Projects\\n\\n"
        f"{project_lines}\\n\\n"
        f"## Tech Stack\\n\\n"
        f"{tech_line}\\n\\n"
        f"## Contact\\n\\n"
        f"- Email: [{config.email}](mailto:{config.email})\\n"
        f"{linkedin_line}"
    )
"""

_P_STATS = """\
def summarize_portfolio(config):
    categories = [p.category for p in config.projects]
    tech = []
    for p in config.projects: tech.extend(p.tech_stack)
    top_tech = [item for item, _ in Counter(tech).most_common(5)]
    return {
        "n_projects":         len(config.projects),
        "categories":         sorted(set(categories)),
        "n_categories":       len(set(categories)),
        "top_tech":           top_tech,
        "total_tech_entries": len(tech),
    }
"""

_P_EXPORT = """\
def export_portfolio(config, output_dir):
    out = pathlib.Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    written = []
    index_path = out / "index.html"
    index_path.write_text(generate_portfolio_page(config), encoding="utf-8")
    written.append(str(index_path))
    cases_dir = out / "case_studies"
    cases_dir.mkdir(exist_ok=True)
    for p in config.projects:
        slug = p.name.lower().replace(" ", "_").replace("-", "_")
        md_path = cases_dir / f"{slug}.md"
        md_path.write_text(generate_case_study(p), encoding="utf-8")
        written.append(str(md_path))
    return written
"""

# ══════════════════════════════════════════════════════════════════════════════
# Exercises
# ══════════════════════════════════════════════════════════════════════════════

_EX1 = _nb([
    _md("# Exercise 1 — generate_portfolio_page\n\n"
        "The portfolio page is the HTML site that showcases your 100 days of work. "
        "`generate_portfolio_page` takes a `PortfolioConfig` and returns a complete "
        "HTML5 document with a dark header (name, title, bio, contact links) and "
        "a responsive project grid. Each project is rendered as a card with its "
        "name, category, tagline, tech stack tags, and optional GitHub/Demo links."),
    _code(_P_BASE + _P_CARD + """\

def generate_portfolio_page(config):
    \"\"\"Generate a complete HTML5 portfolio index page.

    Required (checked by tests below):
      - starts with <!DOCTYPE html>
      - <title> contains owner_name
      - <h1> contains owner_name
      - bio appears in the page
      - every project name appears as an <h3>
      - email, github_username appear as links
      - a .grid div wraps the project cards

    Args:
        config : PortfolioConfig

    Returns:
        str — valid HTML document
    \"\"\"
    project_cards = "\\n".join(_render_project_card(p) for p in config.projects)
    contact_parts = []
    # Build contact_parts from config.email, config.github_username, config.linkedin_url
    contact_html = " · ".join(contact_parts)
    # TODO: build the HTML string using the patterns from Day 98
    return ""
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — starts with <!DOCTYPE html>
try:
    html = generate_portfolio_page(_CFG)
    assert html.strip().startswith("<!DOCTYPE html"), \
        f"expected <!DOCTYPE html>, got: {html[:30]!r}"
    checks += 1; print("✅ 1 starts with <!DOCTYPE html>")
except Exception as e:
    print("❌ 1:", e)

# 2 — <title> and <h1> contain owner_name
try:
    html = generate_portfolio_page(_CFG)
    assert "Jane Doe" in html, "owner_name 'Jane Doe' not found"
    assert "<h1>" in html, "missing <h1>"
    checks += 1; print("✅ 2 owner_name 'Jane Doe' in title and h1")
except Exception as e:
    print("❌ 2:", e)

# 3 — bio and title appear
try:
    html = generate_portfolio_page(_CFG)
    assert _CFG.bio   in html, "bio not in HTML"
    assert _CFG.title in html, "title not in HTML"
    checks += 1; print("✅ 3 bio and title present in page")
except Exception as e:
    print("❌ 3:", e)

# 4 — all project names appear as <h3>
try:
    html = generate_portfolio_page(_CFG)
    for p in _CFG.projects:
        assert f"<h3>{p.name}</h3>" in html, f"project {p.name!r} not in page as <h3>"
    checks += 1; print(f"✅ 4 all {len(_CFG.projects)} project names appear as <h3>")
except Exception as e:
    print("❌ 4:", e)

# 5 — email and GitHub link appear
try:
    html = generate_portfolio_page(_CFG)
    assert "jane@example.com" in html, "email not in page"
    assert "github.com/janedoe" in html, "GitHub link not in page"
    checks += 1; print("✅ 5 email and GitHub links present")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX2 = _nb([
    _md("# Exercise 2 — generate_case_study\n\n"
        "A case study is what turns a GitHub repo into a portfolio piece. "
        "It tells the story: what problem you solved, what you built, which "
        "technologies you used, and what you achieved. `generate_case_study` "
        "produces a Markdown document with structured sections that can be "
        "hosted as a GitHub Gist, a blog post, or a page on your portfolio site."),
    _code(_P_BASE + """\

def generate_case_study(project):
    \"\"\"Generate a Markdown case study for one project.

    Structure:
      # {project.name}
      **Category:** {project.category}
      ## Overview
      {project.tagline}
      {project.description}
      ## Tech Stack
      - item 1
      - item 2
      ## Key Achievements
      - highlight 1 (or placeholder if highlights is empty)
      ## Links
      - GitHub: {url}
      - Demo: {url}   (only if demo_url is set)

    Returns:
        str — Markdown starting with "# {project.name}"
    \"\"\"
    tech_list  = "\\n".join(f"- {t}" for t in project.tech_stack)
    highlights = (
        "\\n".join(f"- {h}" for h in project.highlights)
        if project.highlights else "- See project README for details"
    )
    links = []
    if project.github_url: links.append(f"- GitHub: {project.github_url}")
    if project.demo_url:   links.append(f"- Demo: {project.demo_url}")
    links_text = "\\n".join(links) if links else "- See GitHub profile"
    # TODO: assemble and return the Markdown string
    return ""
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — starts with # project.name
try:
    md = generate_case_study(_P1)
    assert md.startswith(f"# {_P1.name}"), \
        f"expected '# {_P1.name}', got: {md[:40]!r}"
    checks += 1; print(f"✅ 1 case study starts with '# {_P1.name}'")
except Exception as e:
    print("❌ 1:", e)

# 2 — required ## sections present
try:
    md = generate_case_study(_P1)
    for section in ["## Overview", "## Tech Stack", "## Key Achievements", "## Links"]:
        assert section in md, f"missing {section}"
    checks += 1; print("✅ 2 all ## sections present (Overview, Tech Stack, Achievements, Links)")
except Exception as e:
    print("❌ 2:", e)

# 3 — tech stack items appear as bullet points
try:
    md = generate_case_study(_P1)
    for tech in _P1.tech_stack:
        assert f"- {tech}" in md, f"tech {tech!r} not as bullet point"
    checks += 1; print(f"✅ 3 all {len(_P1.tech_stack)} tech stack items as bullet points")
except Exception as e:
    print("❌ 3:", e)

# 4 — highlights appear; empty highlights → placeholder
try:
    md_with = generate_case_study(_P1)
    for h in _P1.highlights:
        assert h in md_with, f"highlight {h!r} not in case study"
    p_no_highlights = _P1.__class__(
        name="X", tagline="T", description="D", tech_stack=["py"]
    )
    md_empty = generate_case_study(p_no_highlights)
    assert "See project README" in md_empty, "empty highlights should have placeholder"
    checks += 1; print("✅ 4 highlights present; empty highlights → placeholder text")
except Exception as e:
    print("❌ 4:", e)

# 5 — GitHub URL present; demo_url included only when set
try:
    md = generate_case_study(_P1)      # has github_url, no demo
    assert _P1.github_url in md,       f"github_url not in links"
    assert "Demo:" not in md,          "demo URL should not appear (_P1 has no demo)"
    md3 = generate_case_study(_P3)     # has both github_url and demo_url
    assert _P3.demo_url in md3,        "demo_url not in _P3 case study"
    checks += 1; print("✅ 5 GitHub link present; Demo link only when demo_url is set")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX3 = _nb([
    _md("# Exercise 3 — generate_github_readme\n\n"
        "GitHub's profile README is the most-visited page in your personal brand. "
        "When someone visits `github.com/yourusername`, they see the README from "
        "the repository named `yourusername/yourusername`. `generate_github_readme` "
        "builds this document from your PortfolioConfig: a greeting, bio, project "
        "list, deduplicated tech stack, and contact info."),
    _code(_P_BASE + """\

def generate_github_readme(config):
    \"\"\"Generate a GitHub profile README.md.

    Structure:
      # Hi, I'm {config.owner_name}
      {config.bio}
      ## What I Build
      I'm an **{config.title}** focused on ...
      ## Projects
      - **[Project Name](url)** — tagline
      ## Tech Stack
      tech1 · tech2 · tech3 ...  (unique, order-preserved, max 8)
      ## Contact
      - Email: [email](mailto:email)
      - LinkedIn: url  (only if linkedin_url is set)

    Returns:
        str — Markdown starting with "# Hi, I'm {owner_name}"
    \"\"\"
    project_lines = "\\n".join(
        f"- **[{p.name}]({p.github_url or '#'})** — {p.tagline}"
        for p in config.projects
    )
    all_tech = []
    for p in config.projects: all_tech.extend(p.tech_stack)
    unique_tech = list(dict.fromkeys(all_tech))[:8]   # deduplicate, preserve order
    tech_line = " · ".join(unique_tech)
    linkedin_line = f"- LinkedIn: {config.linkedin_url}\\n" if config.linkedin_url else ""
    # TODO: assemble and return the Markdown string
    return ""
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — starts with # Hi, I'm {owner_name}
try:
    readme = generate_github_readme(_CFG)
    expected_start = f"# Hi, I'm {_CFG.owner_name}"
    assert readme.startswith(expected_start), \
        f"expected '{expected_start}', got: {readme[:50]!r}"
    checks += 1; print(f"✅ 1 README starts with '# Hi, I'm {_CFG.owner_name}'")
except Exception as e:
    print("❌ 1:", e)

# 2 — bio and ## sections present
try:
    readme = generate_github_readme(_CFG)
    assert _CFG.bio in readme, "bio not in README"
    for section in ["## What I Build", "## Projects", "## Tech Stack", "## Contact"]:
        assert section in readme, f"missing section {section}"
    checks += 1; print("✅ 2 bio and all ## sections present")
except Exception as e:
    print("❌ 2:", e)

# 3 — all project names appear
try:
    readme = generate_github_readme(_CFG)
    for p in _CFG.projects:
        assert p.name in readme, f"project {p.name!r} not in README"
    checks += 1; print(f"✅ 3 all {len(_CFG.projects)} project names in README")
except Exception as e:
    print("❌ 3:", e)

# 4 — tech stack: deduplicated, order preserved, max 8
try:
    readme = generate_github_readme(_CFG)
    # Collect unique tech manually to verify
    all_t = []
    for p in _CFG.projects: all_t.extend(p.tech_stack)
    unique = list(dict.fromkeys(all_t))[:8]
    for t in unique:
        assert t in readme, f"tech {t!r} not in README"
    # Python appears in P1 and P2 — check it appears only once in the tech line
    tech_section = readme.split("## Tech Stack")[1].split("##")[0]
    assert tech_section.count("Python") == 1, \
        f"'Python' should appear once in tech stack, found {tech_section.count('Python')}"
    checks += 1; print("✅ 4 tech stack deduplicated; each item appears once")
except Exception as e:
    print("❌ 4:", e)

# 5 — email present; LinkedIn only if set; absent when not set
try:
    readme = generate_github_readme(_CFG)
    assert _CFG.email        in readme, "email not in README"
    assert _CFG.linkedin_url in readme, "linkedin_url not in README"
    cfg2 = PortfolioConfig("A","E","B","a@b.com","gh")  # no linkedin
    readme2 = generate_github_readme(cfg2)
    assert "LinkedIn" not in readme2, "LinkedIn should not appear without linkedin_url"
    checks += 1; print("✅ 5 email + LinkedIn when set; LinkedIn absent when not set")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX4 = _nb([
    _md("# Exercise 4 — summarize_portfolio\n\n"
        "Portfolio analytics tell you at a glance what your portfolio covers: "
        "how many projects, which categories, which technologies you use most. "
        "`summarize_portfolio` returns a summary dict using `collections.Counter` "
        "to find the top technologies across all projects."),
    _code(_P_BASE + """\

def summarize_portfolio(config):
    \"\"\"Return summary statistics for the portfolio.

    Returns:
        dict with keys:
          n_projects         : int — total project count
          categories         : list[str] — sorted unique category names
          n_categories       : int — number of unique categories
          top_tech           : list[str] — up to 5 most-used tech items
          total_tech_entries : int — total tech stack entries (with repetition)
    \"\"\"
    categories = [p.category for p in config.projects]
    tech = []
    for p in config.projects: tech.extend(p.tech_stack)
    # TODO: compute top_tech using Counter(tech).most_common(5)
    # TODO: return the summary dict
    return {}
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — n_projects is correct
try:
    stats = summarize_portfolio(_CFG)
    assert stats["n_projects"] == 3, f"expected 3, got {stats['n_projects']}"
    checks += 1; print("✅ 1 n_projects = 3")
except Exception as e:
    print("❌ 1:", e)

# 2 — categories: sorted, unique, correct values
try:
    stats = summarize_portfolio(_CFG)
    expected = sorted({"Finance", "AI Agents", "Text AI"})
    assert stats["categories"] == expected, \
        f"expected {expected}, got {stats['categories']}"
    assert stats["n_categories"] == 3
    checks += 1; print(f"✅ 2 categories = {stats['categories']}")
except Exception as e:
    print("❌ 2:", e)

# 3 — top_tech is a list of strings
try:
    stats = summarize_portfolio(_CFG)
    assert isinstance(stats["top_tech"], list)
    assert all(isinstance(t, str) for t in stats["top_tech"])
    assert len(stats["top_tech"]) <= 5
    checks += 1; print(f"✅ 3 top_tech is list[str] of ≤5 items: {stats['top_tech']}")
except Exception as e:
    print("❌ 3:", e)

# 4 — Python is the most common tech (appears in P1 + P2 + P3)
try:
    stats = summarize_portfolio(_CFG)
    assert stats["top_tech"][0] == "Python", \
        f"expected 'Python' as #1 tech, got {stats['top_tech'][0]!r}"
    checks += 1; print("✅ 4 Python is the top tech (appears in all 3 projects)")
except Exception as e:
    print("❌ 4:", e)

# 5 — total_tech_entries = sum of all tech_stack lengths
try:
    stats = summarize_portfolio(_CFG)
    expected_total = sum(len(p.tech_stack) for p in _CFG.projects)
    assert stats["total_tech_entries"] == expected_total, \
        f"expected {expected_total}, got {stats['total_tech_entries']}"
    checks += 1; print(f"✅ 5 total_tech_entries = {stats['total_tech_entries']} (correct)")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX5 = _nb([
    _md("# Exercise 5 — export_portfolio\n\n"
        "The `export_portfolio` function brings everything together: it writes "
        "`index.html` and one Markdown case study per project to a given directory. "
        "This produces a complete static portfolio site — upload `index.html` to "
        "GitHub Pages, Netlify, or Vercel and your portfolio is live."),
    _code(_P_BASE + _P_CARD + _P_PAGE + _P_CASE + _P_STATS + """\

def export_portfolio(config, output_dir):
    \"\"\"Write portfolio files to output_dir and return list of written paths.

    Writes:
      output_dir/index.html
      output_dir/case_studies/{slug}.md   — one per project

    slug = project.name.lower().replace(' ', '_').replace('-', '_')

    Creates directories as needed. Returns list of absolute path strings,
    index.html first then case studies in project order.
    \"\"\"
    out = pathlib.Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    written = []
    # TODO: write index.html, then case study .md files
    return written
"""),
    _md("### Checks"),
    _code("""\
checks = 0

with tempfile.TemporaryDirectory() as tmp:
    written = export_portfolio(_CFG, tmp)
    out = pathlib.Path(tmp)

    # 1 — returns a list of paths with correct count (1 + n_projects)
    try:
        expected_count = 1 + len(_CFG.projects)
        assert isinstance(written, list), f"expected list, got {type(written)}"
        assert len(written) == expected_count, \
            f"expected {expected_count} paths, got {len(written)}"
        checks += 1; print(f"✅ 1 export_portfolio returns {len(written)} paths (1 HTML + {len(_CFG.projects)} MD)")
    except Exception as e:
        print("❌ 1:", e)

    # 2 — index.html exists and contains owner_name
    try:
        index = out / "index.html"
        assert index.exists(), "index.html not created"
        content = index.read_text(encoding="utf-8")
        assert _CFG.owner_name in content, "owner_name not in index.html"
        checks += 1; print("✅ 2 index.html exists and contains owner_name")
    except Exception as e:
        print("❌ 2:", e)

    # 3 — case_studies/ directory exists with correct number of files
    try:
        cases = out / "case_studies"
        assert cases.is_dir(), "case_studies/ directory not created"
        md_files = list(cases.glob("*.md"))
        assert len(md_files) == len(_CFG.projects), \
            f"expected {len(_CFG.projects)} .md files, got {len(md_files)}"
        checks += 1; print(f"✅ 3 case_studies/ has {len(md_files)} .md files")
    except Exception as e:
        print("❌ 3:", e)

    # 4 — each case study starts with # project.name
    try:
        for p in _CFG.projects:
            slug = p.name.lower().replace(" ", "_").replace("-", "_")
            md_path = out / "case_studies" / f"{slug}.md"
            assert md_path.exists(), f"{slug}.md not found"
            content = md_path.read_text(encoding="utf-8")
            assert content.startswith(f"# {p.name}"), \
                f"{slug}.md should start with '# {p.name}'"
        checks += 1; print("✅ 4 each case study starts with '# project.name'")
    except Exception as e:
        print("❌ 4:", e)

    # 5 — index.html is first in returned list; all paths exist
    try:
        assert "index.html" in written[0], \
            f"first path should be index.html, got {written[0]}"
        for path in written:
            assert pathlib.Path(path).exists(), f"path does not exist: {path}"
        checks += 1; print("✅ 5 index.html is first in list; all returned paths exist")
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
day: "099"
lesson: 1
title: "Why Portfolio?"
slides:
  - type: title
    heading: "Portfolio & Personal Brand"
    subheading: "Showing the world 100 days of AI engineering"
    narration: >
      Day 99. You have built 30+ projects over 99 days. Today you package
      them into a portfolio that communicates your skills to employers, clients,
      and collaborators. A portfolio is proof of work — it answers the question
      "can you build AI things?" with "here are the AI things I built." No
      certification, no course completion badge, does what a live portfolio does.

  - type: concept
    label: "Portfolio vs resume"
    heading: "Portfolio vs Resume: What Each Does"
    body: >
      A resume lists skills. A portfolio proves them.
    bullets:
      - "Resume: claims ('proficient in Python, ML, LLMs')"
      - "Portfolio: evidence ('here is the trading bot I built')"
      - "For AI engineering: most hiring is portfolio-driven, not credential-driven"
      - "Three formats: GitHub projects, case study site, deployed demos"
      - "Minimum viable portfolio: 3 projects, each with a README + case study"
    narration: >
      AI engineering is a practical field. Hiring managers and clients want to
      see that you can build things, not that you attended courses. A portfolio
      of 5 working projects beats a resume with 10 bullet points every time.
      The projects from this course — the trading bot, the ops agent, the RAG
      chatbot, the multimodal studio — are real portfolio pieces. Today's
      portfolio.py generates the HTML site that showcases them.

  - type: concept
    label: "What to show"
    heading: "What to Include in Your Portfolio"
    body: >
      Three project types tell a complete story.
    bullets:
      - "1. End-to-end product (Day 100 capstone) — shows you can ship"
      - "2. Domain-specific tool (trading bot, ops agent) — shows depth"
      - "3. Foundation skill (RAG chatbot, embeddings) — shows breadth"
      - "For each project: tagline, tech stack, one key metric or achievement"
      - "Best is 3–6 projects. More is not better — quality over quantity"
    narration: >
      A hiring manager spends 30 seconds on a portfolio. Three well-presented
      projects are more effective than ten poorly documented ones. Each project
      needs: a tagline (what it is), a tech stack (what you used), and one
      achievement or metric (why it matters). The case study generator from
      today's exercises produces exactly this structure.

  - type: exercise
    heading: "Exercise 1 — generate_portfolio_page"
    prompt: >
      generate_portfolio_page(config) returns a complete HTML5 document.
      Use the provided _render_project_card helper for each project.
      Required: <!DOCTYPE html> start; <title> and <h1> with owner_name;
      bio visible; each project as <h3>; email and GitHub links;
      a .grid div wrapping the cards.
    hint: >
      Use the string concatenation pattern from Day 98. The contact links
      are built with contact_parts: append formatted <a> tags for each
      of email, github_username, linkedin_url (if set), then join with " · ".
    narration: >
      The portfolio page is a single HTML file. Once complete, you can open it
      in any browser immediately — no build step, no server. To deploy it:
      push to a GitHub repo, enable GitHub Pages (Settings → Pages → Deploy
      from branch), and it's live at {username}.github.io/{repo-name}.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "Portfolio = evidence, not claims — proves skills better than a resume"
      - "Three project types: end-to-end product, domain tool, foundation skill"
      - "ProjectEntry: 8 fields covering everything a case study needs"
      - "PortfolioConfig: metadata for all generators"
      - "_render_project_card: private helper produces one .card div"
      - "Next: generate_case_study — the case study format"
    narration: >
      The portfolio page structure is in place. Next: the case study format
      that turns each GitHub repo into a story.
""",

    """\
day: "099"
lesson: 2
title: "Writing Case Studies"
slides:
  - type: title
    heading: "Case Studies"
    subheading: "Turning a GitHub repo into a portfolio piece"
    narration: >
      A case study is not documentation. It is a story: the problem, the
      solution, the technology, and the result. generate_case_study produces
      a structured Markdown document that can be posted as a GitHub Gist,
      a blog post, a DEV.to article, or a page on your portfolio site. Well-
      written case studies get shared and attract inbound interest.

  - type: concept
    label: "Case study structure"
    heading: "The Case Study Structure"
    body: >
      Six sections: name, category, overview, stack, achievements, links.
    bullets:
      - "# Name — immediately identifies the project"
      - "**Category:** — context for the reader (Finance, AI Agents, etc.)"
      - "## Overview — tagline + description: what it is and why it matters"
      - "## Tech Stack — bullet list of technologies"
      - "## Key Achievements — concrete metrics or milestones"
      - "## Links — GitHub repo + live demo"
    narration: >
      The Overview section is the most important. The tagline (one sentence)
      answers "what is this?" The description paragraph answers "why did you
      build it and what does it do?". Together they give the reader enough
      context to decide whether to keep reading or follow the GitHub link.
      Key Achievements is where metrics go: "runs daily paper-trading loop
      over 10 stocks", "processes 1000 documents in 45 seconds", "achieves
      8% annual return in backtest". Real numbers beat vague adjectives.

  - type: concept
    label: "Good vs bad achievements"
    heading: "Writing Key Achievements That Land"
    body: >
      Specificity wins. Vague claims are filtered out.
    bullets:
      - "❌ 'High performance' → ✅ 'Processes 500 docs/second on M2 laptop'"
      - "❌ 'Robust error handling' → ✅ 'Retries 3× with exponential backoff'"
      - "❌ 'AI-powered' → ✅ 'Llama 3.2 sentiment scoring at 200 tokens/s'"
      - "❌ 'Used machine learning' → ✅ 'SVM classifier at 94% F1 on test set'"
      - "Use numbers from your gate tests — they are the performance spec"
    narration: >
      The gate tests you wrote over 100 days contain concrete numbers: 5-bar
      stop-loss tests, 252-row backtest results, n_buys/n_sells invariants.
      These are the raw material for achievement bullets. "Stop-loss exits
      a position within one bar of the trigger price" is a verifiable claim.
      "Handles edge cases well" is not.

  - type: exercise
    heading: "Exercise 2 — generate_case_study"
    prompt: >
      generate_case_study(project) returns a Markdown string starting with
      "# {project.name}". Include **Category:**, ## Overview (tagline + description),
      ## Tech Stack (bullet list), ## Key Achievements (highlights or placeholder),
      ## Links (GitHub + Demo if set). Use "\\n".join(...) for bullet lists.
    hint: >
      Check 4: for an empty highlights list, output "- See project README for details".
      Check 5: _P1 has github_url but no demo_url — the ## Links section should
      not contain "Demo:". _P3 has both — its Links section should have both.
    narration: >
      The case study is generated from the ProjectEntry dataclass — the same
      data that powers the portfolio page cards. This is the key principle:
      one source of truth. Update the ProjectEntry, and all outputs (card,
      case study, README) update automatically. Keep the highlights list
      accurate and up-to-date as you ship.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "Case study = story: problem → solution → tech → achievements → links"
      - "Key Achievements: use concrete numbers from gate tests"
      - "generate_case_study: Markdown from ProjectEntry in six sections"
      - "Empty highlights → placeholder; demo_url optional"
      - "Next: GitHub profile README — the most-visited page in your brand"
    narration: >
      Case studies done. Next: the GitHub profile README — the page at
      github.com/yourusername that every visitor sees before they look at
      any of your repositories.
""",

    """\
day: "099"
lesson: 3
title: "GitHub Profile README"
slides:
  - type: title
    heading: "GitHub Profile README"
    subheading: "Your most-visited page"
    narration: >
      GitHub has a hidden feature: create a repository named the same as your
      username, add a README.md, and it appears on your profile page at
      github.com/yourusername. This is the highest-visibility page in your
      personal brand — recruiters, potential collaborators, and clients all
      land there when they look you up. generate_github_readme builds this
      document from your PortfolioConfig.

  - type: concept
    label: "Profile README structure"
    heading: "Profile README Structure"
    body: >
      Six sections, all visible above the fold on a laptop screen.
    bullets:
      - "# Hi, I'm {name} — personal, immediate"
      - "{bio} — one sentence on who you are and what you build"
      - "## What I Build — title + one sentence on focus area"
      - "## Projects — bullet list: **[name](url)** — tagline"
      - "## Tech Stack — dot-separated unique tech from all projects"
      - "## Contact — email + LinkedIn"
    narration: >
      The greeting "Hi, I'm {name}" is deliberate — it makes the page feel
      like a person, not a CV. The bio is the same text from PortfolioConfig,
      so it stays consistent across the portfolio page and the README. The
      project list links directly to the GitHub repos. The tech stack is
      deduplicated across all projects and shows the top 8 items in the order
      they first appear — which is roughly the order of importance.

  - type: concept
    label: "Deduplication"
    heading: "Tech Stack: Order-Preserved Deduplication"
    body: >
      dict.fromkeys(all_tech)[:8] — the one-liner for ordered dedup.
    bullets:
      - "Problem: Python appears in 5 projects — show it once"
      - "dict.fromkeys(list) preserves order and removes duplicates"
      - "list(dict.fromkeys(all_tech)) → unique items in first-seen order"
      - "[:8] caps at 8 items — readable; more than 8 is overwhelming"
      - "Alternative: Counter(all_tech).most_common(8) — but loses first-seen order"
    narration: >
      The technique list(dict.fromkeys(iterable)) is a Python idiom worth
      memorising. dict keys are insertion-ordered since Python 3.7, and a
      dict cannot have duplicate keys — so fromkeys(list) gives you a
      dict with one entry per unique item in the list, in the order of first
      appearance. Converting back to a list gives the deduplicated version.
      Counter would give frequency order, which might not be what you want
      for the tech stack (you don't necessarily want the most-used tech first).

  - type: exercise
    heading: "Exercise 3 — generate_github_readme"
    prompt: >
      generate_github_readme(config) returns Markdown starting with
      "# Hi, I'm {config.owner_name}". Include bio, ## What I Build,
      ## Projects (one bullet per project), ## Tech Stack (unique, ≤8, dot-separated),
      ## Contact (email, LinkedIn if set). LinkedIn line omitted when linkedin_url is "".
    hint: >
      Check 4: the tech stack section should contain "Python" exactly once even
      though Python appears in all 3 sample projects. Split ## Tech Stack section
      and count occurrences. Check 5: PortfolioConfig("A","E","B","a@b.com","gh")
      has no linkedin_url — "LinkedIn" should not appear in the README.
    narration: >
      To activate the GitHub profile README after running generate_github_readme:
      (1) create a new repository at github.com/new named exactly your username,
      (2) add the generated text as README.md in that repo, (3) commit and push.
      The README appears immediately on your profile page.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "GitHub profile README: username/username repo → appears on profile"
      - "generate_github_readme: PortfolioConfig → Markdown"
      - "dict.fromkeys(list)[:8]: order-preserved deduplication, max 8"
      - "LinkedIn line: included only when linkedin_url is set"
      - "Next: summarize_portfolio — analytics across all projects"
    narration: >
      The GitHub profile README is built. Next: summarize_portfolio — a quick
      analytics function that shows what the portfolio covers.
""",

    """\
day: "099"
lesson: 4
title: "Portfolio Analytics"
slides:
  - type: title
    heading: "Portfolio Analytics"
    subheading: "Understanding your portfolio at a glance"
    narration: >
      summarize_portfolio gives you a quick read on what your portfolio
      covers: how many projects, which categories, and which technologies
      appear most frequently. This is useful for identifying gaps (do you
      have too many projects in one category?) and for writing the About
      section on your portfolio site.

  - type: concept
    label: "Counter usage"
    heading: "collections.Counter for Tech Frequency"
    body: >
      Counter counts hashable elements. most_common(n) returns the top n.
    bullets:
      - "Counter(['a','b','a','c','a']) → Counter({'a':3,'b':1,'c':1})"
      - "counter.most_common(5) → [('a',3),('b',1),('c',1)]"
      - "Extract just the items: [item for item, _ in counter.most_common(5)]"
      - "Built from a flat list: extend() each project's tech_stack list"
      - "Alternative to dict approach: dict preserves order; Counter gives frequency"
    narration: >
      Counter is the standard Python tool for counting frequencies. It is used
      throughout AI engineering: counting token frequencies, computing word
      distributions, tallying results from evaluation runs. In this context,
      we use it to find which technologies you use most across your portfolio —
      useful for answering the question "what's your primary stack?" on a
      hiring call.

  - type: concept
    label: "Portfolio gaps"
    heading: "Using Analytics to Spot Gaps"
    body: >
      A balanced portfolio shows breadth + depth.
    bullets:
      - "Too many in one category: add a project from a different domain"
      - "Tech stack too narrow: show a second language or framework"
      - "All backend, no frontend: add a Streamlit or FastAPI project (Days 51–53)"
      - "No deployed demo: deploy the trading bot or RAG chatbot"
      - "n_categories should be ≥ 3 for a well-rounded AI portfolio"
    narration: >
      summarize_portfolio's output can be used programmatically to check the
      portfolio before publishing. For example: assert stats["n_categories"] >= 3.
      This is the same principle as the gate tests throughout this course —
      automated checks catch problems early. A portfolio that passes its own
      automated checks is a portfolio you can be confident in.

  - type: exercise
    heading: "Exercise 4 — summarize_portfolio"
    prompt: >
      summarize_portfolio(config) returns a dict with n_projects (int),
      categories (sorted list of unique strings), n_categories (int),
      top_tech (list[str] from Counter.most_common(5)), and total_tech_entries
      (int — sum of all tech_stack lengths, with repetition).
    hint: >
      Check 4: Python appears in all 3 sample projects (_P1, _P2, _P3) and
      should be top_tech[0]. categories must be sorted — use sorted(set(...)).
      total_tech_entries = sum(len(p.tech_stack) for p in config.projects) —
      do NOT deduplicate this count.
    narration: >
      Note the distinction: total_tech_entries counts with repetition (3 projects
      each using Python → 3 entries), while top_tech is deduplicated by Counter
      (Python appears once, with count 3). This is a common distinction in
      analytics: raw count vs unique count. Both are useful in different contexts.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "Counter(tech).most_common(5): top 5 technologies by frequency"
      - "total_tech_entries: raw count (with repetition, not deduplicated)"
      - "categories: sorted(set(...)) for stable, alphabetical ordering"
      - "Use analytics to check portfolio balance before publishing"
      - "Next: export_portfolio — writing all files to disk"
    narration: >
      Analytics done. The final exercise puts it all together: export_portfolio
      writes every artifact to disk, ready to deploy.
""",

    """\
day: "099"
lesson: 5
title: "Exporting and Deploying"
slides:
  - type: title
    heading: "export_portfolio"
    subheading: "From Python to a live site"
    narration: >
      export_portfolio writes the HTML index page and all Markdown case studies
      to a directory. From there, deploying is a single command: push the
      directory to GitHub and enable Pages, or drop it into a Netlify site.
      Today's lesson covers the full export → deploy path.

  - type: concept
    label: "Static site deployment"
    heading: "Three Ways to Deploy the Portfolio"
    body: >
      Free, fast, and permanent. Three options.
    bullets:
      - "GitHub Pages: push to {username}.github.io repo → live at {username}.github.io"
      - "Netlify: drag the export directory to app.netlify.com → live in 30 seconds"
      - "Vercel: vercel deploy --prod from the export directory → live instantly"
      - "Custom domain: buy a domain (~$12/year), point CNAME to Pages/Netlify"
      - "All three are free for a static portfolio site"
    narration: >
      A static site is the right format for a portfolio — no server to maintain,
      no database, no auth. Just HTML, CSS, and optionally JavaScript. export_portfolio
      produces exactly what GitHub Pages and Netlify need: an index.html at the
      root and supporting files in subdirectories. The case_studies/ directory
      won't be rendered as HTML (they're Markdown files), but they can be converted
      with a Markdown-to-HTML step or just linked from the portfolio page.

  - type: concept
    label: "slug generation"
    heading: "File Naming: Slugs"
    body: >
      A slug is a URL-safe filename derived from a title.
    bullets:
      - "Rule: lowercase, spaces → underscores, hyphens → underscores"
      - "'AI Trading Bot' → 'ai_trading_bot.md'"
      - "'RAG Chatbot' → 'rag_chatbot.md'"
      - "Avoids URL-encoding issues (%20 for space, etc.)"
      - "Pattern: name.lower().replace(' ', '_').replace('-', '_')"
    narration: >
      Slugs appear throughout web development: URL paths, file names, database
      keys. The pattern is always the same: lowercase, spaces and hyphens become
      underscores or hyphens. export_portfolio uses underscores for the .md
      file names. If you were generating HTML URLs, you would use hyphens
      instead (hyphens are preferred in URLs for SEO).

  - type: exercise
    heading: "Exercise 5 — export_portfolio"
    prompt: >
      export_portfolio(config, output_dir) writes index.html and case_studies/{slug}.md
      for each project. Returns list[str] of absolute paths — index.html first,
      then case studies in project order. Use pathlib.Path throughout.
      mkdir(parents=True, exist_ok=True) for output_dir; mkdir(exist_ok=True)
      for case_studies/.
    hint: >
      Check 4: the slug for "AI Trading Bot" is "ai_trading_bot" and the file
      is case_studies/ai_trading_bot.md. Check 5: written[0] should contain
      "index.html". Use str(path) to convert pathlib.Path to string.
    narration: >
      After export_portfolio runs, open output_dir/index.html in a browser.
      You will see your complete portfolio site — all three projects as cards,
      your name and bio in the header, your contact links. The case_studies/
      directory holds the Markdown files. This is a deployable product.

  - type: summary
    heading: "Day 99 Complete"
    bullets:
      - "ProjectEntry + PortfolioConfig: one source of truth for all generators"
      - "generate_portfolio_page: HTML5 site with header + project grid"
      - "generate_case_study: Markdown with Overview/Stack/Achievements/Links"
      - "generate_github_readme: profile README with deduped tech stack"
      - "summarize_portfolio: n_projects, categories, top_tech via Counter"
      - "export_portfolio: writes index.html + case studies, returns paths"
      - "Next: Day 100 — Final Capstone (ship your own AI product)"
    narration: >
      Day 99 is complete. Tomorrow is the final day: Day 100, the capstone where
      you ship your own AI product from scratch — your choice of domain, your
      choice of stack, fully deployed and documented. Everything from this course
      has been building to that day.
""",
]

# ══════════════════════════════════════════════════════════════════════════════
# Project + solution
# ══════════════════════════════════════════════════════════════════════════════

_FULL_P = _P_BASE + _P_CARD + _P_PAGE + _P_CASE + _P_GH + _P_STATS + _P_EXPORT

PROJECT_NB = _nb([
    _md(f"# Day {DAY} Project — Build Your Portfolio\n\n"
        "Generate the complete portfolio for the 100 Days of AI course: "
        "HTML site, case studies, GitHub profile README, and summary stats. "
        "Use the provided sample projects or update `_CFG` with your real projects."),
    _code(_FULL_P),
    _code("""\
import tempfile, os

with tempfile.TemporaryDirectory() as tmp:
    # 1. Export the portfolio
    written = export_portfolio(_CFG, tmp)
    out = __import__("pathlib").Path(tmp)

    # 2. Verify the output
    print(f"Written {len(written)} files:")
    for path in written:
        rel = __import__("pathlib").Path(path).relative_to(tmp)
        print(f"  {rel}")

    # 3. Show portfolio stats
    stats = summarize_portfolio(_CFG)
    print(f"\\nPortfolio summary:")
    print(f"  Projects:    {stats['n_projects']}")
    print(f"  Categories:  {stats['categories']}")
    print(f"  Top tech:    {stats['top_tech']}")

    # 4. Show GitHub README preview
    readme = generate_github_readme(_CFG)
    print(f"\\nGitHub README (first 400 chars):")
    print(readme[:400])
"""),
])

SOLUTION_NB = _nb([
    _md(f"# Day {DAY} Solution — Build Your Portfolio"),
    _code(_FULL_P),
    _code("""\
import tempfile, pathlib

with tempfile.TemporaryDirectory() as tmp:
    written = export_portfolio(_CFG, tmp)
    out = pathlib.Path(tmp)

    # Assertions
    assert len(written) == 1 + len(_CFG.projects)
    assert "index.html" in written[0]
    index_content = (out / "index.html").read_text(encoding="utf-8")
    assert index_content.startswith("<!DOCTYPE html")
    assert _CFG.owner_name in index_content
    for p in _CFG.projects:
        assert f"<h3>{p.name}</h3>" in index_content

    for p in _CFG.projects:
        slug = p.name.lower().replace(" ", "_").replace("-", "_")
        md = (out / "case_studies" / f"{slug}.md").read_text(encoding="utf-8")
        assert md.startswith(f"# {p.name}")
        for t in p.tech_stack:
            assert f"- {t}" in md

    readme = generate_github_readme(_CFG)
    assert readme.startswith(f"# Hi, I'm {_CFG.owner_name}")
    for p in _CFG.projects:
        assert p.name in readme

    stats = summarize_portfolio(_CFG)
    assert stats["n_projects"] == 3
    assert stats["top_tech"][0] == "Python"
    assert "Finance" in stats["categories"]

    print("HTML:", len(index_content), "chars")
    print("Stats:", stats)
    print("\\nSolution smoke-test passed.")
"""),
])

# ══════════════════════════════════════════════════════════════════════════════
# Gate
# ══════════════════════════════════════════════════════════════════════════════

GATE_PY = f"""\
import importlib.util, sys, tempfile, pathlib, os

spec = importlib.util.spec_from_file_location(
    "{SLUG}", r"{DIR / (SLUG + '.py')}"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

p1 = mod.ProjectEntry(
    name="Trading Bot", tagline="Paper-trading with AI signals.",
    description="Bar-by-bar bot.", tech_stack=["Python","pandas","SQLite"],
    github_url="https://github.com/u/bot", category="Finance",
    highlights=["Daily loop","Kelly Criterion"],
)
p2 = mod.ProjectEntry(
    name="Ops Agent", tagline="Autonomous ops agent.",
    description="Tool-routing agent.",
    tech_stack=["Python","ChromaDB"],
    category="AI Agents",
)
p3 = mod.ProjectEntry(
    name="RAG Chatbot", tagline="Q&A over your docs.",
    description="Retrieval-augmented generation.",
    tech_stack=["Python","ChromaDB","FastAPI"],
    github_url="https://github.com/u/rag",
    demo_url="https://rag.example.com",
    category="Text AI",
)

cfg = mod.PortfolioConfig(
    owner_name="Jane Doe", title="AI Engineer",
    bio="I build practical AI.", email="jane@example.com",
    github_username="janedoe",
    linkedin_url="https://linkedin.com/in/janedoe",
    projects=[p1, p2, p3],
)

# generate_portfolio_page
html = mod.generate_portfolio_page(cfg)
assert html.strip().startswith("<!DOCTYPE html"), f"bad start: {{html[:30]!r}}"
assert "Jane Doe"              in html
assert "<h1>"                  in html
assert "I build practical AI." in html
assert "<h3>Trading Bot</h3>"  in html
assert "<h3>Ops Agent</h3>"    in html
assert "<h3>RAG Chatbot</h3>"  in html
assert "jane@example.com"      in html
assert "github.com/janedoe"    in html
assert "Finance"               in html

# generate_case_study — with highlights
cs1 = mod.generate_case_study(p1)
assert cs1.startswith("# Trading Bot"), f"bad start: {{cs1[:30]!r}}"
assert "## Overview"          in cs1
assert "## Tech Stack"        in cs1
assert "## Key Achievements"  in cs1
assert "## Links"             in cs1
assert "- Python"             in cs1
assert "Daily loop"           in cs1
assert p1.github_url          in cs1
assert "Demo:"            not in cs1   # p1 has no demo_url

# generate_case_study — empty highlights → placeholder
cs2 = mod.generate_case_study(p2)
assert "See project README" in cs2, "empty highlights should have placeholder"

# generate_case_study — both URLs
cs3 = mod.generate_case_study(p3)
assert p3.github_url in cs3
assert p3.demo_url   in cs3

# generate_github_readme
readme = mod.generate_github_readme(cfg)
assert readme.startswith("# Hi, I'm Jane Doe"), f"bad start: {{readme[:40]!r}}"
assert "## Projects"       in readme
assert "## Tech Stack"     in readme
assert "## Contact"        in readme
assert "Trading Bot"       in readme
assert "jane@example.com"  in readme
assert "linkedin.com"      in readme
# dedup: Python in all 3 projects → appears once in tech line
tech_section = readme.split("## Tech Stack")[1].split("##")[0]
assert tech_section.count("Python") == 1, \
    f"Python should appear once in tech stack: {{tech_section.count('Python')}}"
# no linkedin when not set
cfg2 = mod.PortfolioConfig("A","T","B","a@b.com","gh", projects=[])
readme2 = mod.generate_github_readme(cfg2)
assert "LinkedIn" not in readme2

# summarize_portfolio
stats = mod.summarize_portfolio(cfg)
assert stats["n_projects"]   == 3
assert stats["n_categories"] == 3
assert set(stats["categories"]) == {{"Finance","AI Agents","Text AI"}}
assert stats["categories"] == sorted(stats["categories"])  # must be sorted
assert isinstance(stats["top_tech"], list)
assert "Python" == stats["top_tech"][0]  # Python in all 3 projects
expected_total = sum(len(p.tech_stack) for p in cfg.projects)
assert stats["total_tech_entries"] == expected_total

# export_portfolio
with tempfile.TemporaryDirectory() as tmp:
    written = mod.export_portfolio(cfg, tmp)
    out = pathlib.Path(tmp)

    assert len(written) == 4  # index + 3 projects
    assert "index.html" in written[0]

    index_content = (out / "index.html").read_text(encoding="utf-8")
    assert "Jane Doe" in index_content

    assert (out / "case_studies").is_dir()
    for p in cfg.projects:
        slug = p.name.lower().replace(" ", "_").replace("-", "_")
        md_path = out / "case_studies" / f"{{slug}}.md"
        assert md_path.exists(), f"{{slug}}.md not found"
        md_content = md_path.read_text(encoding="utf-8")
        assert md_content.startswith(f"# {{p.name}}")

    for path in written:
        assert pathlib.Path(path).exists(), f"path does not exist: {{path}}"

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
