"""
Day 097 — Productizing Your AI
================================
Tooling to package, document, price, and gate access to an AI project.
No external dependencies — pure Python standard library.

Public API
----------
    ProductConfig           — dataclass for project metadata
    generate_pyproject(cfg) -> str   (pyproject.toml content)
    generate_readme(cfg, features, examples) -> str
    generate_changelog_entry(version, changes) -> str
    calculate_price(cost_per_call, calls_per_month, margin=0.5) -> float
    generate_pricing_tiers(cost_per_call, tiers)   -> list[dict]
    format_pricing_table(tiers)                    -> str (Markdown)
    validate_api_key(key, valid_keys)              -> bool
    gate_feature(api_key, valid_keys, fn, *a, **kw) -> any
"""
from dataclasses import dataclass, field


# ── metadata ──────────────────────────────────────────────────────────────────

@dataclass
class ProductConfig:
    """Project metadata for packaging and documentation.

    Fields:
        name         : PyPI-style package name (hyphens OK, e.g. "my-bot")
        version      : semver string (e.g. "0.1.0")
        description  : one-sentence description shown on PyPI / README header
        author       : author full name
        email        : author contact email
        dependencies : list of PEP 508 dependency strings (default [])
        license      : SPDX license ID (default "MIT")
        python_requires : minimum Python version (default ">=3.10")
    """
    name:             str
    version:          str
    description:      str
    author:           str
    email:            str
    dependencies:     list = field(default_factory=list)
    license:          str  = "MIT"
    python_requires:  str  = ">=3.10"


# ── packaging ─────────────────────────────────────────────────────────────────

def generate_pyproject(cfg):
    """Generate pyproject.toml content from a ProductConfig.

    Follows PEP 517/518/621 standards (setuptools backend).
    The [project.scripts] CLI name is derived from cfg.name with hyphens
    replaced by underscores.

    Args:
        cfg : ProductConfig

    Returns:
        str — valid TOML suitable for writing to pyproject.toml
    """
    cli_name = cfg.name.replace("-", "_")
    if cfg.dependencies:
        deps_lines = "\n".join(f'    "{d}",' for d in cfg.dependencies)
        deps_block = f"[\n{deps_lines}\n]"
    else:
        deps_block = "[]"

    return (
        f"[build-system]\n"
        f'requires = ["setuptools>=68", "wheel"]\n'
        f'build-backend = "setuptools.backends.legacy:build"\n'
        f"\n"
        f"[project]\n"
        f'name = "{cfg.name}"\n'
        f'version = "{cfg.version}"\n'
        f'description = "{cfg.description}"\n'
        f'authors = [{{name = "{cfg.author}", email = "{cfg.email}"}}]\n'
        f'license = {{text = "{cfg.license}"}}\n'
        f'requires-python = "{cfg.python_requires}"\n'
        f"dependencies = {deps_block}\n"
        f"\n"
        f"[project.scripts]\n"
        f'{cli_name} = "{cli_name}:main"\n'
    )


# ── documentation ─────────────────────────────────────────────────────────────

def generate_readme(cfg, features, examples):
    """Generate a README.md string.

    Args:
        cfg      : ProductConfig
        features : list[str] — bullet points for the ## Features section
        examples : list[dict] with keys "title" (str) and "code" (str)
                   — each becomes a code block under ## Usage

    Returns:
        str — Markdown
    """
    feature_bullets = "\n".join(f"- {f}" for f in features)
    usage_blocks    = "\n\n".join(
        f"### {ex['title']}\n```python\n{ex['code']}\n```"
        for ex in examples
    )
    return (
        f"# {cfg.name}\n\n"
        f"{cfg.description}\n\n"
        f"## Features\n\n"
        f"{feature_bullets}\n\n"
        f"## Installation\n\n"
        f"```bash\n"
        f"pip install {cfg.name}\n"
        f"```\n\n"
        f"## Usage\n\n"
        f"{usage_blocks}\n\n"
        f"## License\n\n"
        f"{cfg.license}\n"
    )


def generate_changelog_entry(version, changes):
    """Generate one CHANGELOG.md entry.

    Args:
        version : str — semver string (e.g. "0.2.0")
        changes : list[str] — change descriptions

    Returns:
        str — Markdown section
    """
    import datetime
    today       = datetime.date.today().isoformat()
    change_list = "\n".join(f"- {c}" for c in changes)
    return f"## [{version}] — {today}\n\n{change_list}\n"


# ── pricing ───────────────────────────────────────────────────────────────────

def calculate_price(cost_per_call, calls_per_month, margin=0.5):
    """Cost-plus pricing: price = total_cost / (1 − margin).

    A margin of 0.5 means the price is twice the cost (50% gross margin).

    Args:
        cost_per_call    : float — your cost to serve one API call
        calls_per_month  : int | float — expected monthly volume
        margin           : float in [0, 1) — target gross margin (default 0.5)

    Returns:
        float — monthly price rounded to 2 decimal places
    """
    if margin >= 1.0 or margin < 0:
        raise ValueError(f"margin must be in [0, 1); got {margin}")
    total_cost = cost_per_call * calls_per_month
    return round(total_cost / (1.0 - margin), 2)


def generate_pricing_tiers(cost_per_call, tiers):
    """Generate SaaS pricing tiers using cost-plus pricing.

    Args:
        cost_per_call : float — cost to serve one call
        tiers         : list[dict] — each dict has:
                        "name"   : str — tier display name
                        "calls"  : int — monthly call quota
                        "margin" : float — gross margin target (default 0.5)

    Returns:
        list[dict] — each dict has:
            name, calls, price_per_month, price_per_call
    """
    result = []
    for tier in tiers:
        calls  = tier["calls"]
        margin = tier.get("margin", 0.5)
        price  = calculate_price(cost_per_call, calls, margin)
        result.append({
            "name":            tier["name"],
            "calls":           calls,
            "price_per_month": price,
            "price_per_call":  round(price / max(calls, 1), 6),
        })
    return result


def format_pricing_table(tiers):
    """Format generate_pricing_tiers output as a Markdown table.

    Args:
        tiers : list[dict] — output from generate_pricing_tiers

    Returns:
        str — Markdown table
    """
    header = "| Plan | Calls/month | Price/month | Price/call |"
    sep    = "|------|-------------|-------------|------------|"
    rows   = [
        f"| {t['name']} | {t['calls']:,} | ${t['price_per_month']:.2f} | "
        f"${t['price_per_call']:.6f} |"
        for t in tiers
    ]
    return "\n".join([header, sep] + rows)


# ── access control ────────────────────────────────────────────────────────────

def validate_api_key(key, valid_keys):
    """True if key is present in valid_keys (case-sensitive exact match).

    Args:
        key        : str — the API key to validate
        valid_keys : set | list | frozenset — the allowed keys

    Returns:
        bool
    """
    return key in valid_keys


def gate_feature(api_key, valid_keys, feature_fn, *args, **kwargs):
    """Call feature_fn only if api_key is valid.

    Args:
        api_key    : str — caller's API key
        valid_keys : collection — valid keys
        feature_fn : callable — the gated function
        *args      : passed to feature_fn
        **kwargs   : passed to feature_fn

    Returns:
        Whatever feature_fn returns.

    Raises:
        PermissionError — if api_key is not in valid_keys
    """
    if not validate_api_key(api_key, valid_keys):
        raise PermissionError(f"Invalid API key: {api_key!r}")
    return feature_fn(*args, **kwargs)
