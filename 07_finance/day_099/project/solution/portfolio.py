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
        f'<span class="tag">{t}</span>' for t in project.tech_stack
    )
    links = []
    if project.github_url:
        links.append(f'<a href="{project.github_url}">GitHub</a>')
    if project.demo_url:
        links.append(f'<a href="{project.demo_url}">Demo</a>')
    links_html = " \u00b7 ".join(links)
    card = (
        '      <div class="card">\n'
        f'        <h3>{project.name}</h3>\n'
        f'        <p class="category">{project.category}</p>\n'
        f'        <p>{project.tagline}</p>\n'
        f'        <div class="tags">{tech_tags}</div>\n'
    )
    if links_html:
        card += f'        <p class="links">{links_html}</p>\n'
    card += '      </div>'
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
    project_cards = "\n".join(_render_project_card(p) for p in config.projects)

    contact_parts = []
    if config.email:
        contact_parts.append(
            f'<a href="mailto:{config.email}">{config.email}</a>'
        )
    if config.github_username:
        contact_parts.append(
            f'<a href="https://github.com/{config.github_username}">GitHub</a>'
        )
    if config.linkedin_url:
        contact_parts.append(
            f'<a href="{config.linkedin_url}">LinkedIn</a>'
        )
    contact_html = " \u00b7 ".join(contact_parts)

    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '  <meta charset="UTF-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f"  <title>{config.owner_name} \u2014 {config.title}</title>\n"
        "  <style>\n"
        "    body { font-family: system-ui, sans-serif; margin: 0; color: #1e293b; }\n"
        "    header { background: #0f172a; color: white; padding: 60px 40px; }\n"
        "    h1 { font-size: 2.5rem; margin: 0 0 8px; }\n"
        "    .subtitle { font-size: 1.2rem; opacity: 0.8; margin: 0 0 12px; }\n"
        "    .bio { max-width: 600px; opacity: 0.75; line-height: 1.6; margin: 0 0 16px; }\n"
        "    .contact a { color: #93c5fd; text-decoration: none; }\n"
        "    main { padding: 60px 40px; max-width: 1100px; margin: 0 auto; }\n"
        "    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 24px; }\n"
        "    .card { border: 1px solid #e2e8f0; border-radius: 12px; padding: 24px; }\n"
        "    .card h3 { margin: 0 0 4px; }\n"
        "    .category { font-size: 0.85rem; color: #64748b; margin: 0 0 12px; }\n"
        "    .tag { background: #f1f5f9; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; margin: 2px; display: inline-block; }\n"
        "    .links a { color: #2563eb; font-size: 0.9rem; }\n"
        "  </style>\n"
        "</head>\n"
        "<body>\n"
        "  <header>\n"
        f"    <h1>{config.owner_name}</h1>\n"
        f'    <p class="subtitle">{config.title}</p>\n'
        f'    <p class="bio">{config.bio}</p>\n'
        f'    <p class="contact">{contact_html}</p>\n'
        "  </header>\n"
        "  <main>\n"
        "    <h2>Projects</h2>\n"
        '    <div class="grid">\n'
        f"{project_cards}\n"
        "    </div>\n"
        "  </main>\n"
        "</body>\n"
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
    tech_list   = "\n".join(f"- {t}" for t in project.tech_stack)
    highlights  = (
        "\n".join(f"- {h}" for h in project.highlights)
        if project.highlights
        else "- See project README for details"
    )
    links = []
    if project.github_url:
        links.append(f"- GitHub: {project.github_url}")
    if project.demo_url:
        links.append(f"- Demo: {project.demo_url}")
    links_text = "\n".join(links) if links else "- See GitHub profile"

    return (
        f"# {project.name}\n\n"
        f"**Category:** {project.category}\n\n"
        f"## Overview\n\n"
        f"{project.tagline}\n\n"
        f"{project.description}\n\n"
        f"## Tech Stack\n\n"
        f"{tech_list}\n\n"
        f"## Key Achievements\n\n"
        f"{highlights}\n\n"
        f"## Links\n\n"
        f"{links_text}\n"
    )


def generate_github_readme(config):
    """Generate a GitHub profile README.md.

    This is the special README that appears at github.com/{username} when
    you create a repository named the same as your username.

    Structure:
      # Hi, I'm {owner_name}
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
    project_lines = "\n".join(
        f"- **[{p.name}]({p.github_url or '#'})** \u2014 {p.tagline}"
        for p in config.projects
    )
    all_tech = []
    for p in config.projects:
        all_tech.extend(p.tech_stack)
    unique_tech = list(dict.fromkeys(all_tech))[:8]
    tech_line = " \u00b7 ".join(unique_tech)

    linkedin_line = (
        f"- LinkedIn: {config.linkedin_url}\n"
        if config.linkedin_url
        else ""
    )

    return (
        f"# Hi, I'm {config.owner_name}\n\n"
        f"{config.bio}\n\n"
        f"## What I Build\n\n"
        f"I'm an **{config.title}** focused on building practical AI "
        f"applications with Python.\n\n"
        f"## Projects\n\n"
        f"{project_lines}\n\n"
        f"## Tech Stack\n\n"
        f"{tech_line}\n\n"
        f"## Contact\n\n"
        f"- Email: [{config.email}](mailto:{config.email})\n"
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
