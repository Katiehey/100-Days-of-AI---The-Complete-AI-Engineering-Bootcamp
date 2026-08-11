#!/usr/bin/env python3
"""Day 097 generator — Productizing Your AI."""
import json, pathlib

ROOT  = pathlib.Path(__file__).parent.parent
DAY   = "097"
SLUG  = "productizer"
TITLE = "Productizing Your AI"
DIR   = ROOT / "07_finance" / f"day_{DAY}"

# ══════════════════════════════════════════════════════════════════════════════
# Deliverable
# ══════════════════════════════════════════════════════════════════════════════

DELIVERABLE = '''\
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
        deps_lines = "\\n".join(f'    "{d}",' for d in cfg.dependencies)
        deps_block = f"[\\n{deps_lines}\\n]"
    else:
        deps_block = "[]"

    return (
        f"[build-system]\\n"
        f'requires = ["setuptools>=68", "wheel"]\\n'
        f'build-backend = "setuptools.backends.legacy:build"\\n'
        f"\\n"
        f"[project]\\n"
        f'name = "{cfg.name}"\\n'
        f'version = "{cfg.version}"\\n'
        f'description = "{cfg.description}"\\n'
        f'authors = [{{name = "{cfg.author}", email = "{cfg.email}"}}]\\n'
        f'license = {{text = "{cfg.license}"}}\\n'
        f'requires-python = "{cfg.python_requires}"\\n'
        f"dependencies = {deps_block}\\n"
        f"\\n"
        f"[project.scripts]\\n"
        f'{cli_name} = "{cli_name}:main"\\n'
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
    feature_bullets = "\\n".join(f"- {f}" for f in features)
    usage_blocks    = "\\n\\n".join(
        f"### {ex['title']}\\n```python\\n{ex['code']}\\n```"
        for ex in examples
    )
    return (
        f"# {cfg.name}\\n\\n"
        f"{cfg.description}\\n\\n"
        f"## Features\\n\\n"
        f"{feature_bullets}\\n\\n"
        f"## Installation\\n\\n"
        f"```bash\\n"
        f"pip install {cfg.name}\\n"
        f"```\\n\\n"
        f"## Usage\\n\\n"
        f"{usage_blocks}\\n\\n"
        f"## License\\n\\n"
        f"{cfg.license}\\n"
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
    change_list = "\\n".join(f"- {c}" for c in changes)
    return f"## [{version}] — {today}\\n\\n{change_list}\\n"


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
    return "\\n".join([header, sep] + rows)


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
from dataclasses import dataclass, field
import datetime

@dataclass
class ProductConfig:
    name: str; version: str; description: str
    author: str; email: str
    dependencies: list = field(default_factory=list)
    license: str  = "MIT"
    python_requires: str = ">=3.10"

_CFG = ProductConfig(
    name="my-trading-bot",
    version="0.1.0",
    description="AI-powered paper-trading bot using sentiment and technical signals.",
    author="Jane Doe",
    email="jane@example.com",
    dependencies=["pandas>=2.0", "requests>=2.28"],
)
"""

_P_PKG = """\
def generate_pyproject(cfg):
    cli_name = cfg.name.replace("-", "_")
    if cfg.dependencies:
        deps_lines = "\\n".join(f'    "{d}",' for d in cfg.dependencies)
        deps_block = f"[\\n{deps_lines}\\n]"
    else:
        deps_block = "[]"
    return (
        f"[build-system]\\n"
        f'requires = ["setuptools>=68", "wheel"]\\n'
        f'build-backend = "setuptools.backends.legacy:build"\\n'
        f"\\n[project]\\n"
        f'name = "{cfg.name}"\\n'
        f'version = "{cfg.version}"\\n'
        f'description = "{cfg.description}"\\n'
        f'authors = [{{name = "{cfg.author}", email = "{cfg.email}"}}]\\n'
        f'license = {{text = "{cfg.license}"}}\\n'
        f'requires-python = "{cfg.python_requires}"\\n'
        f"dependencies = {deps_block}\\n"
        f"\\n[project.scripts]\\n"
        f'{cli_name} = "{cli_name}:main"\\n'
    )
"""

_P_DOC = """\
def generate_readme(cfg, features, examples):
    feature_bullets = "\\n".join(f"- {f}" for f in features)
    usage_blocks    = "\\n\\n".join(
        f"### {ex['title']}\\n```python\\n{ex['code']}\\n```"
        for ex in examples
    )
    return (
        f"# {cfg.name}\\n\\n{cfg.description}\\n\\n"
        f"## Features\\n\\n{feature_bullets}\\n\\n"
        f"## Installation\\n\\npip install {cfg.name}\\n\\n"
        f"## Usage\\n\\n{usage_blocks}\\n\\n"
        f"## License\\n\\n{cfg.license}\\n"
    )

def generate_changelog_entry(version, changes):
    today = datetime.date.today().isoformat()
    change_list = "\\n".join(f"- {c}" for c in changes)
    return f"## [{version}] — {today}\\n\\n{change_list}\\n"
"""

_P_PRICE = """\
def calculate_price(cost_per_call, calls_per_month, margin=0.5):
    if margin >= 1.0 or margin < 0:
        raise ValueError(f"margin must be in [0,1); got {margin}")
    return round(cost_per_call * calls_per_month / (1.0 - margin), 2)

def generate_pricing_tiers(cost_per_call, tiers):
    result = []
    for tier in tiers:
        calls  = tier["calls"]; margin = tier.get("margin", 0.5)
        price  = calculate_price(cost_per_call, calls, margin)
        result.append({
            "name": tier["name"], "calls": calls,
            "price_per_month": price,
            "price_per_call":  round(price / max(calls, 1), 6),
        })
    return result

def format_pricing_table(tiers):
    header = "| Plan | Calls/month | Price/month | Price/call |"
    sep    = "|------|-------------|-------------|------------|"
    rows   = [
        f"| {t['name']} | {t['calls']:,} | ${t['price_per_month']:.2f} | "
        f"${t['price_per_call']:.6f} |"
        for t in tiers
    ]
    return "\\n".join([header, sep] + rows)
"""

_P_GATE = """\
def validate_api_key(key, valid_keys):
    return key in valid_keys

def gate_feature(api_key, valid_keys, feature_fn, *args, **kwargs):
    if not validate_api_key(api_key, valid_keys):
        raise PermissionError(f"Invalid API key: {api_key!r}")
    return feature_fn(*args, **kwargs)
"""

# ══════════════════════════════════════════════════════════════════════════════
# Exercises
# ══════════════════════════════════════════════════════════════════════════════

_EX1 = _nb([
    _md("# Exercise 1 — generate_pyproject\n\n"
        "A `pyproject.toml` is the modern Python packaging standard (PEP 621). "
        "It tells pip, build tools, and PyPI everything they need to install "
        "your package. `generate_pyproject` produces a valid TOML string from "
        "a `ProductConfig`, handling the dependencies list and CLI entry point."),
    _code(_P_BASE + """\

def generate_pyproject(cfg):
    \"\"\"Generate pyproject.toml content.

    Required sections:
      [build-system] — requires + build-backend
      [project]      — name, version, description, authors, license,
                       requires-python, dependencies
      [project.scripts] — CLI entry point: cfg.name (hyphens→underscores) = "module:main"

    If cfg.dependencies is empty, dependencies = []
    Otherwise:
        dependencies = [
            "dep-a",
            "dep-b",
        ]

    Returns:
        str — valid TOML
    \"\"\"
    # TODO: ~15 lines
    return ""
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — returns a non-empty string
try:
    out = generate_pyproject(_CFG)
    assert isinstance(out, str) and len(out) > 50
    checks += 1; print("✅ 1 returns non-empty string")
except Exception as e:
    print("❌ 1:", e)

# 2 — contains [project] and [build-system] sections
try:
    out = generate_pyproject(_CFG)
    assert "[project]" in out,       "missing [project] section"
    assert "[build-system]" in out,  "missing [build-system] section"
    checks += 1; print("✅ 2 contains [project] and [build-system] sections")
except Exception as e:
    print("❌ 2:", e)

# 3 — name, version, description appear in output
try:
    out = generate_pyproject(_CFG)
    assert _CFG.name        in out, f"name {_CFG.name!r} not found"
    assert _CFG.version     in out, f"version {_CFG.version!r} not found"
    assert _CFG.description in out, f"description not found"
    checks += 1; print(f"✅ 3 name={_CFG.name!r}, version={_CFG.version!r} present")
except Exception as e:
    print("❌ 3:", e)

# 4 — dependencies appear in output
try:
    out = generate_pyproject(_CFG)
    for dep in _CFG.dependencies:
        assert dep in out, f"dependency {dep!r} not found"
    checks += 1; print(f"✅ 4 all dependencies present: {_CFG.dependencies}")
except Exception as e:
    print("❌ 4:", e)

# 5 — empty dependencies → dependencies = []
try:
    cfg2 = ProductConfig("bare-pkg","0.0.1","Bare","A","a@b.com")
    out2 = generate_pyproject(cfg2)
    assert "dependencies = []" in out2, f"expected 'dependencies = []' for empty deps"
    checks += 1; print("✅ 5 empty dependencies → 'dependencies = []'")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX2 = _nb([
    _md("# Exercise 2 — generate_readme and generate_changelog_entry\n\n"
        "The README is the first thing a user sees. A well-structured README "
        "converts a curious visitor into an installer. `generate_readme` "
        "produces a Markdown document with a feature list, installation "
        "instructions, and usage examples. `generate_changelog_entry` creates "
        "one entry for CHANGELOG.md with today's date."),
    _code(_P_BASE + """\

def generate_readme(cfg, features, examples):
    \"\"\"Generate README.md Markdown content.

    Structure:
      # {cfg.name}
      {cfg.description}
      ## Features
      - feature 1
      - feature 2
      ## Installation
      pip install {cfg.name}
      ## Usage
      ### {example title}
      ```python
      {example code}
      ```
      ## License
      {cfg.license}

    Args:
        cfg      : ProductConfig
        features : list[str]
        examples : list[dict] with keys "title" and "code"
    \"\"\"
    # TODO: build the Markdown string
    return ""


def generate_changelog_entry(version, changes):
    \"\"\"Generate one CHANGELOG.md entry.

    Format:
      ## [{version}] — {today's date ISO}
      - change 1
      - change 2
    \"\"\"
    # TODO: 3 lines
    return ""
"""),
    _md("### Checks"),
    _code("""\
checks = 0

features = [
    "AI-driven sentiment signals",
    "Technical indicator calculator",
    "Paper-trading bot with logging",
]
examples = [
    {"title": "Quick Start", "code": "from my_trading_bot import BotRunner"},
    {"title": "Run a backtest", "code": "result = run_backtest(df, signals)"},
]

# 1 — starts with # cfg.name
try:
    readme = generate_readme(_CFG, features, examples)
    assert readme.startswith(f"# {_CFG.name}"), \
        f"expected '# {_CFG.name}' at start, got: {readme[:40]!r}"
    checks += 1; print(f"✅ 1 README starts with '# {_CFG.name}'")
except Exception as e:
    print("❌ 1:", e)

# 2 — ## sections present
try:
    readme = generate_readme(_CFG, features, examples)
    for section in ["## Features", "## Installation", "## Usage", "## License"]:
        assert section in readme, f"missing section: {section}"
    checks += 1; print("✅ 2 all ## sections present (Features, Installation, Usage, License)")
except Exception as e:
    print("❌ 2:", e)

# 3 — features appear as bullet points
try:
    readme = generate_readme(_CFG, features, examples)
    for feat in features:
        assert f"- {feat}" in readme, f"feature {feat!r} not in README"
    checks += 1; print("✅ 3 all features appear as bullet points")
except Exception as e:
    print("❌ 3:", e)

# 4 — example code appears in a code block
try:
    readme = generate_readme(_CFG, features, examples)
    for ex in examples:
        assert ex["code"] in readme, f"example code {ex['code']!r} not found"
    checks += 1; print("✅ 4 example code blocks present in Usage section")
except Exception as e:
    print("❌ 4:", e)

# 5 — changelog entry: version and today's date
try:
    import datetime
    entry = generate_changelog_entry("0.2.0", ["Added sentiment signal", "Fixed stop-loss bug"])
    today = datetime.date.today().isoformat()
    assert "0.2.0"                        in entry
    assert today                          in entry
    assert "Added sentiment signal"       in entry
    assert "Fixed stop-loss bug"          in entry
    checks += 1; print(f"✅ 5 changelog entry has version, today ({today}), and changes")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX3 = _nb([
    _md("# Exercise 3 — calculate_price and generate_pricing_tiers\n\n"
        "Pricing an AI product starts with knowing your costs. "
        "`calculate_price` uses cost-plus pricing: you know what each API call "
        "costs you (LLM tokens, compute), you decide your target margin, and "
        "the formula tells you what to charge. `generate_pricing_tiers` applies "
        "this to multiple tiers with different call volumes and margins."),
    _code(_P_BASE + """\

def calculate_price(cost_per_call, calls_per_month, margin=0.5):
    \"\"\"Cost-plus pricing: price = total_cost / (1 − margin).

    Example: cost=$0.001/call, 1000 calls, margin=0.5
      total_cost = $1.00
      price = $1.00 / 0.5 = $2.00

    Raises ValueError if margin not in [0, 1).
    Returns float rounded to 2 decimal places.
    \"\"\"
    # TODO: ~4 lines
    return 0.0


def generate_pricing_tiers(cost_per_call, tiers):
    \"\"\"Generate SaaS pricing tiers.

    Args:
        cost_per_call : float
        tiers : list[dict] with keys:
          "name"   : str
          "calls"  : int
          "margin" : float (optional, default 0.5)

    Returns:
        list[dict] with keys: name, calls, price_per_month, price_per_call
    \"\"\"
    # TODO: ~7 lines
    return []
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — calculate_price: known example
try:
    p = calculate_price(0.001, 1000, margin=0.5)
    assert abs(p - 2.0) < 1e-9, f"expected $2.00, got ${p}"
    checks += 1; print("✅ 1 calculate_price(0.001, 1000, 0.5) = $2.00")
except Exception as e:
    print("❌ 1:", e)

# 2 — margin=0.8 → 5× cost
try:
    p = calculate_price(0.001, 1000, margin=0.8)
    assert abs(p - 5.0) < 1e-9, f"expected $5.00 (80% margin), got ${p}"
    checks += 1; print("✅ 2 calculate_price(0.001, 1000, 0.8) = $5.00 (80% margin)")
except Exception as e:
    print("❌ 2:", e)

# 3 — invalid margin raises ValueError
try:
    try:
        calculate_price(0.001, 1000, margin=1.0)
        print("❌ 3: expected ValueError for margin=1.0")
    except ValueError:
        checks += 1; print("✅ 3 margin=1.0 raises ValueError")
except Exception as e:
    print("❌ 3:", e)

# 4 — generate_pricing_tiers: structure
try:
    tiers = [
        {"name": "Free",  "calls":    100},
        {"name": "Indie", "calls":  1_000},
        {"name": "Pro",   "calls": 10_000, "margin": 0.7},
    ]
    result = generate_pricing_tiers(0.001, tiers)
    assert len(result) == 3
    for t in result:
        assert {"name","calls","price_per_month","price_per_call"}.issubset(t.keys())
    checks += 1; print("✅ 4 generate_pricing_tiers returns 3 dicts with correct keys")
except Exception as e:
    print("❌ 4:", e)

# 5 — pricing math is correct across tiers
try:
    tiers = [
        {"name": "Free",  "calls":   100, "margin": 0.5},
        {"name": "Pro",   "calls": 1_000, "margin": 0.5},
    ]
    result = generate_pricing_tiers(0.001, tiers)
    # Free: 0.001*100 / 0.5 = 0.20
    assert abs(result[0]["price_per_month"] - 0.20) < 1e-6, \
        f"Free tier: expected $0.20, got ${result[0]['price_per_month']}"
    # Pro: 0.001*1000 / 0.5 = 2.00
    assert abs(result[1]["price_per_month"] - 2.00) < 1e-6, \
        f"Pro tier: expected $2.00, got ${result[1]['price_per_month']}"
    # price_per_call = price_per_month / calls
    assert abs(result[0]["price_per_call"] - 0.002) < 1e-6
    checks += 1; print("✅ 5 pricing math correct: Free=$0.20, Pro=$2.00")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX4 = _nb([
    _md("# Exercise 4 — validate_api_key and gate_feature\n\n"
        "Feature gating is how you enforce paid access to your product. "
        "`validate_api_key` checks whether a key is in the set of valid keys. "
        "`gate_feature` wraps any function with an access check — valid key "
        "allows the call, invalid key raises `PermissionError`. This is the "
        "minimal access control layer before adding a real billing system."),
    _code(_P_BASE + """\

def validate_api_key(key, valid_keys):
    \"\"\"True if key is in valid_keys (case-sensitive exact match).\"\"\"
    # TODO: 1 line
    return False


def gate_feature(api_key, valid_keys, feature_fn, *args, **kwargs):
    \"\"\"Call feature_fn(*args, **kwargs) only if api_key is valid.

    Raises PermissionError if the key is not in valid_keys.
    \"\"\"
    # TODO: ~3 lines
    return None
"""),
    _md("### Checks"),
    _code("""\
checks = 0
KEYS = {"key-abc-123", "key-xyz-456"}

# 1 — valid key returns True
try:
    assert validate_api_key("key-abc-123", KEYS) is True
    checks += 1; print("✅ 1 valid key → True")
except Exception as e:
    print("❌ 1:", e)

# 2 — invalid key returns False
try:
    assert validate_api_key("bad-key", KEYS) is False
    assert validate_api_key("KEY-ABC-123", KEYS) is False  # case-sensitive
    checks += 1; print("✅ 2 invalid/wrong-case key → False")
except Exception as e:
    print("❌ 2:", e)

# 3 — gate_feature calls fn with valid key
try:
    result = gate_feature("key-abc-123", KEYS, lambda x: x * 2, 21)
    assert result == 42, f"expected 42, got {result}"
    checks += 1; print("✅ 3 gate_feature calls fn(21) → 42 with valid key")
except Exception as e:
    print("❌ 3:", e)

# 4 — gate_feature raises PermissionError for invalid key
try:
    try:
        gate_feature("bad-key", KEYS, lambda: "secret")
        print("❌ 4: expected PermissionError")
    except PermissionError as pe:
        assert "bad-key" in str(pe), f"PermissionError should mention the bad key: {pe}"
        checks += 1; print("✅ 4 invalid key → PermissionError (mentions the key)")
except Exception as e:
    print("❌ 4:", e)

# 5 — gate_feature passes kwargs to fn
try:
    def multiply(x, factor=1):
        return x * factor
    result = gate_feature("key-xyz-456", KEYS, multiply, 5, factor=10)
    assert result == 50, f"expected 50, got {result}"
    checks += 1; print("✅ 5 gate_feature passes *args and **kwargs to fn")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX5 = _nb([
    _md("# Exercise 5 — Full Productization Pipeline\n\n"
        "Apply all four components to the Section 7 trading bot: generate "
        "a pyproject.toml, a README, a changelog entry, pricing tiers, and "
        "verify the feature gate. This is what 'productizing' looks like in "
        "practice — generating all the artifacts that make a script into a "
        "distributable product."),
    _code(_P_BASE + _P_PKG + _P_DOC + _P_PRICE + _P_GATE),
    _code("""\
# Trading bot product config
bot_cfg = ProductConfig(
    name        = "ai-trading-bot",
    version     = "1.0.0",
    description = "AI-powered paper-trading bot with sentiment and technical signals.",
    author      = "AI Engineer",
    email       = "bot@example.com",
    dependencies= ["pandas>=2.0", "requests>=2.28"],
)
features = [
    "SMA crossover and RSI mean-reversion strategies",
    "AI sentiment analysis from news headlines",
    "Kelly Criterion position sizing",
    "Stop-loss and drawdown limit risk controls",
    "Paper-trading bot with daily scheduling and logging",
]
examples = [
    {"title": "Quick Start",
     "code": "from ai_trading_bot import BotRunner\\nrunner = BotRunner('bot.log')"},
    {"title": "Run paper trader",
     "code": "result = runner.run_once(df, signals, initial_cash=10_000)"},
]
tiers = [
    {"name": "Free",       "calls":    100, "margin": 0.50},
    {"name": "Hobbyist",   "calls":  1_000, "margin": 0.55},
    {"name": "Pro",        "calls": 10_000, "margin": 0.65},
    {"name": "Enterprise", "calls": 50_000, "margin": 0.70},
]
VALID_KEYS = {"demo-key-001", "demo-key-002"}

# Generate artifacts
pyproject  = generate_pyproject(bot_cfg)
readme     = generate_readme(bot_cfg, features, examples)
changelog  = generate_changelog_entry("1.0.0", ["Initial release"])
tier_data  = generate_pricing_tiers(0.001, tiers)
price_table = format_pricing_table(tier_data)

print("=== pyproject.toml ===")
print(pyproject)
print("=== Pricing Table ===")
print(price_table)
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — pyproject has correct name and version
try:
    assert "ai-trading-bot" in pyproject and "1.0.0" in pyproject
    assert "[project]" in pyproject
    checks += 1; print("✅ 1 pyproject contains name, version, [project]")
except Exception as e:
    print("❌ 1:", e)

# 2 — readme has all major sections
try:
    for section in ["## Features", "## Installation", "## Usage", "## License"]:
        assert section in readme, f"missing {section}"
    assert "ai-trading-bot" in readme
    checks += 1; print("✅ 2 README has all required sections")
except Exception as e:
    print("❌ 2:", e)

# 3 — pricing tiers: 4 tiers, prices increase with volume
try:
    assert len(tier_data) == 4
    prices = [t["price_per_month"] for t in tier_data]
    assert all(prices[i] < prices[i+1] for i in range(len(prices)-1)), \
        f"prices should increase with volume: {prices}"
    checks += 1; print(f"✅ 3 4 tiers, prices increase: {[f'${p:.2f}' for p in prices]}")
except Exception as e:
    print("❌ 3:", e)

# 4 — pricing table is a markdown table
try:
    lines = price_table.split("\\n")
    assert lines[0].startswith("|") and lines[0].endswith("|")
    assert "---" in lines[1]
    assert len(lines) >= 6  # header + sep + 4 tiers
    checks += 1; print("✅ 4 format_pricing_table returns a valid Markdown table")
except Exception as e:
    print("❌ 4:", e)

# 5 — feature gate
try:
    result = gate_feature("demo-key-001", VALID_KEYS, lambda: "premium data")
    assert result == "premium data"
    try:
        gate_feature("bad-key", VALID_KEYS, lambda: "premium data")
        print("❌ 5: expected PermissionError for bad key")
    except PermissionError:
        checks += 1; print("✅ 5 gate_feature: valid key → result; invalid → PermissionError")
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
day: "097"
lesson: 1
title: "From Script to Product"
slides:
  - type: title
    heading: "Productizing Your AI"
    subheading: "Packaging, documentation, pricing, access control"
    narration: >
      Day 97. The trading bot is complete and automated. Today you take a step
      back from implementation and think about the product layer: what does it
      take to turn a working script into something other people can install,
      pay for, and rely on? Four components: packaging (how they install it),
      documentation (how they understand it), pricing (how you charge for it),
      and access control (how you enforce who can use it).

  - type: concept
    label: "Script vs product"
    heading: "What Makes a Product Different from a Script?"
    body: >
      A script works for you. A product works for strangers.
    bullets:
      - "Script: lives on your machine, runs when you run it"
      - "Product: installable by strangers, documented, versioned, priced"
      - "Packaging: pip install my-bot — one command installs everything"
      - "Documentation: README, usage examples, changelog"
      - "Pricing: how you capture value from the product's utility"
      - "Access control: who can call which features (API keys, tiers)"
    narration: >
      The gap between a working script and a distributable product is mostly
      packaging and documentation. The code itself often barely changes. What
      changes is everything around it: the pyproject.toml that makes it pip-
      installable, the README that explains what it does and how to start,
      the changelog that tracks what changed between versions, the pricing
      page that converts visitors into customers, and the API key check that
      ensures only paying users access premium features.

  - type: concept
    label: "Product development order"
    heading: "The Order of Productization"
    body: >
      Build in this order: package → document → price → gate.
    bullets:
      - "1. Package: make it installable (pyproject.toml)"
      - "2. Document: make it understandable (README, examples)"
      - "3. Price: decide what to charge (cost-plus or value-based)"
      - "4. Gate: enforce access (API keys, tier checks)"
      - "5. Ship: publish to PyPI, host the API, tell people about it"
    narration: >
      The order matters because each step depends on the previous one. You
      cannot document a product you have not packaged — what would you tell
      people to install? You cannot price a product whose value you have not
      articulated in documentation. You cannot gate access until you have
      decided what each tier can access. Today you build all four layers.
      Tomorrow (Day 98) you build the landing page that brings users to the
      product.

  - type: exercise
    heading: "Exercise 1 — generate_pyproject"
    prompt: >
      Implement generate_pyproject(cfg) to return a pyproject.toml string.
      Include [build-system], [project] (name, version, description, authors,
      license, requires-python, dependencies), and [project.scripts] with the
      CLI entry point. If cfg.dependencies is empty, write "dependencies = []".
    hint: >
      The CLI name is cfg.name.replace("-", "_"). Use an f-string or string
      concatenation to build the TOML. For non-empty deps, format each as
      "    \"dep\"," on its own line inside square brackets.
    narration: >
      pyproject.toml is the PEP 621 standard for Python packaging. Once you have
      this file, pip install . (in the project directory) installs your package.
      pip install my-bot installs it from PyPI after you run twine upload. The
      [project.scripts] section creates a CLI command — after installation,
      users can run "my_bot" in their terminal.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "Products require: packaging, documentation, pricing, access control"
      - "ProductConfig: metadata dataclass for all artifact generators"
      - "pyproject.toml: PEP 621 standard, enables pip install"
      - "CLI entry point in [project.scripts]: name = 'module:main'"
      - "Next: generate_readme and generate_changelog_entry"
    narration: >
      Packaging is done. Next: documentation — the README and changelog that
      explain the product to users who have never seen your code.
""",

    """\
day: "097"
lesson: 2
title: "Documentation as a Product Feature"
slides:
  - type: title
    heading: "Documentation"
    subheading: "The README is the product's first impression"
    narration: >
      Documentation is not an afterthought — it is a product feature. A
      great product with bad documentation fails. A mediocre product with
      great documentation sells. The README is the first thing a potential
      user sees, and it has about 10 seconds to answer three questions:
      what does it do, how do I install it, and what does it look like in use?

  - type: concept
    label: "README structure"
    heading: "The Anatomy of a Good README"
    body: >
      Five sections, one goal: convert the reader into an installer.
    bullets:
      - "# Name + tagline: what it is in one sentence"
      - "## Features: why to choose this over alternatives"
      - "## Installation: pip install — one command"
      - "## Usage: a working code example they can copy-paste"
      - "## License: required for open source; important for commercial use"
    narration: >
      The Features section answers 'why'. Installation answers 'how to start'.
      Usage answers 'what does it look like'. If a user can read your README
      in 60 seconds and understand what your product does, whether it fits
      their needs, how to install it, and how to use it — you have a good
      README. generate_readme builds this structure from a ProductConfig and
      two lists: feature strings and example dicts.

  - type: concept
    label: "CHANGELOG"
    heading: "The Changelog: Trust Through Transparency"
    body: >
      A changelog shows users that the project is maintained and improving.
    bullets:
      - "Every release gets one entry: ## [version] — YYYY-MM-DD"
      - "Breaking changes: listed prominently (users need to upgrade carefully)"
      - "New features: what they gained in this release"
      - "Bug fixes: what stopped working and now works again"
      - "Format: Keep a Changelog (keepachangelog.com) is the standard"
    narration: >
      The changelog is especially important for libraries and APIs that other
      code depends on. Users need to know what changed between versions before
      upgrading. A missing or inconsistent changelog is a red flag that suggests
      the maintainer does not think about their users' upgrade experience.
      generate_changelog_entry produces one entry in the standard format.

  - type: exercise
    heading: "Exercise 2 — generate_readme and generate_changelog_entry"
    prompt: >
      generate_readme(cfg, features, examples) should return a Markdown string
      starting with "# {cfg.name}", containing ## Features (bullet list),
      ## Installation (pip install ...), ## Usage (code blocks), and ## License.
      generate_changelog_entry(version, changes) should return "## [{version}] — {today}"
      followed by change bullet points.
    hint: >
      For features: "\\n".join(f"- {f}" for f in features). For examples:
      use "\\n\\n".join(...) to separate code blocks with a blank line.
      datetime.date.today().isoformat() gives "2025-01-15".
    narration: >
      Both functions are primarily string manipulation. The key is the structure:
      each section starts with ## and is separated by blank lines. Check 1 verifies
      the README starts with "# cfg.name" — if the header is wrong, users see the
      wrong name in GitHub's rendered preview.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "README: # name + tagline, ## Features, Installation, Usage, License"
      - "generate_readme: ProductConfig + features list + examples list → str"
      - "Changelog: ## [version] — YYYY-MM-DD + change bullet points"
      - "datetime.date.today().isoformat() for today's date"
      - "Next: pricing — calculating what to charge"
    narration: >
      Documentation is done. Next: pricing — how to decide what to charge and
      how to structure tiers to serve different customer segments.
""",

    """\
day: "097"
lesson: 3
title: "Pricing AI Products"
slides:
  - type: title
    heading: "Pricing"
    subheading: "Cost-plus: know your costs, add margin"
    narration: >
      Pricing an AI product is different from pricing a traditional software
      product because AI has variable marginal costs — every API call costs
      real money in compute and tokens. The most common first approach for
      AI products is cost-plus pricing: calculate your cost to serve a
      customer, then add a margin. Simple, defensible, and easy to adjust.

  - type: concept
    label: "Cost-plus formula"
    heading: "The Cost-Plus Formula"
    body: >
      price = cost / (1 − margin)
    bullets:
      - "cost = cost_per_call × calls_per_month"
      - "margin = 0.5 → price = 2 × cost (50% gross margin)"
      - "margin = 0.8 → price = 5 × cost (80% gross margin)"
      - "margin = 0.0 → price = cost (break-even, no profit)"
      - "SaaS benchmark: 70%+ gross margin is healthy at scale"
    narration: >
      If your LLM calls cost $0.001 per call and a customer makes 1000 calls
      per month, your cost is $1.00. At 50% margin, you charge $2.00. At 80%
      margin, you charge $5.00. The formula price = cost / (1 - margin) ensures
      that margin is the fraction of the price that is profit — not the fraction
      of the cost that is added on top. These are different: 50% margin means
      50% of the $2.00 price is profit ($1.00), not 50% added to cost ($1.50).

  - type: concept
    label: "Tier design"
    heading: "Designing Pricing Tiers"
    body: >
      Most SaaS products use 3–4 tiers to serve different customer segments.
    bullets:
      - "Free / Hobbyist (100–1000 calls): acquisition — get users in the door"
      - "Pro (1000–10000 calls): the main revenue tier for individuals"
      - "Enterprise (10000+ calls): teams, higher margin, annual contracts"
      - "Rule: each higher tier costs less per call (volume discount)"
      - "Rule: higher tiers have higher absolute margin (enterprise pays more)"
    narration: >
      Tiers serve different purposes. The Free tier is customer acquisition —
      it has thin margins but converts curious users into paying customers.
      The Pro tier is the profit center — most paying customers land here.
      Enterprise tiers command higher margins because they include SLAs, support,
      and dedicated onboarding. The price_per_call decreases with volume (good
      deal for high-volume customers) but the absolute monthly spend increases
      (good revenue for you).

  - type: exercise
    heading: "Exercise 3 — calculate_price and generate_pricing_tiers"
    prompt: >
      calculate_price(cost_per_call, calls_per_month, margin=0.5) → round(cost*calls/(1-margin), 2).
      Raise ValueError if margin ≥ 1.0 or margin < 0.
      generate_pricing_tiers(cost_per_call, tiers) → list of dicts with
      name, calls, price_per_month, and price_per_call (price_per_month / calls).
    hint: >
      Check 2: margin=0.8 → cost=$1.00 → price=1.00/0.2=5.00.
      Check 5: Free tier (100 calls, 0.5 margin) → $0.001*100/0.5 = $0.20.
      price_per_call = price_per_month / max(calls, 1).
    narration: >
      The math is simple. The value is in understanding what the numbers mean:
      a Free tier at $0.20/month means you break even at 100 calls if your
      infrastructure has zero fixed costs. In practice you eat the fixed costs
      for free users in exchange for acquisition. The Pro tier at $2.00/month
      is where you actually build a business.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "Cost-plus: price = cost / (1 − margin)"
      - "50% margin → 2× cost; 80% margin → 5× cost"
      - "Tiers: Free (acquisition), Pro (revenue), Enterprise (high margin)"
      - "price_per_call decreases with volume — reward high-usage customers"
      - "Next: feature gating — enforce who accesses which tier"
    narration: >
      Pricing is done. Next: feature gating — the mechanism that connects your
      pricing tiers to your code, ensuring only authorized keys can call
      premium features.
""",

    """\
day: "097"
lesson: 4
title: "Feature Gating and Access Control"
slides:
  - type: title
    heading: "Feature Gating"
    subheading: "API keys: connect pricing to code"
    narration: >
      A pricing tier is just marketing until you enforce it in code. Feature
      gating is the mechanism: an API key identifies the customer, the key maps
      to a tier, and the tier determines which features are accessible. In the
      simplest form — which is where every product starts — it is a set of
      valid keys and a function that checks membership.

  - type: code
    label: "Gate pattern"
    heading: "validate_api_key and gate_feature"
    body: >
      Three lines. The entire access control layer.
    code: |
      def validate_api_key(key, valid_keys):
          return key in valid_keys

      def gate_feature(api_key, valid_keys, feature_fn, *args, **kwargs):
          if not validate_api_key(api_key, valid_keys):
              raise PermissionError(f"Invalid API key: {api_key!r}")
          return feature_fn(*args, **kwargs)

      # Usage:
      result = gate_feature(user_key, PAID_KEYS, run_backtest, df, signals)
    narration: >
      validate_api_key is a one-liner. gate_feature wraps any function with
      an access check. PermissionError is the correct built-in exception for
      "you don't have permission to do this" — it maps naturally to HTTP 403
      if you expose this as an API endpoint. The *args/**kwargs pass-through
      means gate_feature is generic: it can wrap any function, with any
      arguments, with no changes to the gated function itself.

  - type: concept
    label: "Production gating"
    heading: "Beyond Simple Key Validation"
    body: >
      Real production systems add: database lookup, rate limiting, tier checks.
    bullets:
      - "Step 1 (today): key in set — works for small number of customers"
      - "Step 2: key → database lookup → tier, usage count, expiry"
      - "Step 3: rate limiter — N calls per minute, M per month"
      - "Step 4: tiered features — Free can call X but not Y"
      - "Libraries: slowapi (FastAPI rate limiting), stripe-python (billing)"
    narration: >
      Today's implementation is deliberately minimal: it is exactly the
      validation logic you need, and nothing more. Once you have paying
      customers, you will extend it: the API key lookup becomes a database
      query, which returns the customer's tier, remaining call quota, and
      expiry date. The gate_feature wrapper remains the same — only the
      valid_keys lookup changes from a set to a database call. Good design.

  - type: exercise
    heading: "Exercise 4 — validate_api_key and gate_feature"
    prompt: >
      validate_api_key(key, valid_keys) → key in valid_keys (case-sensitive).
      gate_feature(api_key, valid_keys, feature_fn, *args, **kwargs) →
      call feature_fn(*args, **kwargs) if valid; raise PermissionError if not.
    hint: >
      Check 2: "KEY-ABC-123" (uppercase) should return False — exact match
      only. Check 4: the PermissionError message should include the bad key
      string (e.g. f"Invalid API key: {api_key!r}"). Check 5: kwargs are
      passed through (*args and **kwargs in gate_feature).
    narration: >
      Four lines total. The most common mistake: forgetting to raise PermissionError
      and just returning None instead. The caller must be able to distinguish
      "feature returned None" from "feature was blocked" — an exception is
      the correct signal for "you don't have access."

  - type: summary
    heading: "What You Learned"
    bullets:
      - "validate_api_key: key in valid_keys — one line"
      - "gate_feature: check key → raise PermissionError or call fn"
      - "PermissionError → HTTP 403 when exposing as an API"
      - "Production extension: set → database lookup → tier → rate limit"
      - "Next: Exercise 5 — full productization of the trading bot"
    narration: >
      Access control is done. Exercise 5 brings all four components together
      in a complete productization pipeline for the trading bot.
""",

    """\
day: "097"
lesson: 5
title: "The Complete Productization Pipeline"
slides:
  - type: title
    heading: "Shipping a Product"
    subheading: "Package → document → price → gate → publish"
    narration: >
      The final lesson shows the complete pipeline: take a working AI project,
      run it through all four productization steps, and produce the artifacts
      needed to publish on PyPI, host on GitHub, and sell to customers. After
      Exercise 5, you have a pyproject.toml, a README, a changelog, a pricing
      table, and a feature gate — everything needed to ship.

  - type: concept
    label: "PyPI publishing"
    heading: "Publishing to PyPI"
    body: >
      Three commands to publish a Python package.
    bullets:
      - "pip install build twine  — the publishing tools"
      - "python -m build  — creates dist/*.whl and dist/*.tar.gz"
      - "twine upload dist/*  — uploads to PyPI (requires API token)"
      - "After: anyone can pip install your-package-name"
      - "Test first on test.pypi.org: twine upload --repository testpypi dist/*"
    narration: >
      Once you have a pyproject.toml, publishing is three commands. The
      python -m build command creates a wheel (binary distribution) and a
      source distribution. twine upload sends them to PyPI. The PyPI API
      token can be created at pypi.org/manage/account/token — store it
      as an environment variable (TWINE_PASSWORD) so you never commit it
      to git. After publishing, your package is installable worldwide in
      seconds.

  - type: concept
    label: "The shipping checklist"
    heading: "The Product Shipping Checklist"
    body: >
      Seven items before you call it shipped.
    bullets:
      - "□ pyproject.toml with correct name, version, dependencies"
      - "□ README with Features, Installation, Usage, License"
      - "□ CHANGELOG.md with this release's changes"
      - "□ Tests pass (the gate system from this course)"
      - "□ Pricing tiers defined and documented on landing page"
      - "□ API key gate in place for premium features"
      - "□ Published to PyPI or hosted (Render/Railway/Fly.io)"
    narration: >
      This checklist is the difference between a side project and a product.
      Every item is covered by what you have built in Days 89–97. The gate
      tests from this course satisfy 'tests pass'. The productizer.py from
      today generates the packaging, docs, and pricing. The bot from Days
      95–96 is the deployable product. All that remains is the landing page
      (Day 98) and the portfolio to showcase it (Day 99).

  - type: exercise
    heading: "Project — Trading Bot Product Artifacts"
    prompt: >
      Generate all four artifacts for the trading bot: pyproject.toml,
      README.md, changelog entry, pricing tiers table. Use the provided
      ProductConfig, features list, and tiers from the exercise.
      Verify: [project] in pyproject, ## Features in README,
      prices increase with volume, pricing table is Markdown.
    hint: >
      Check 3: assert prices[0] < prices[1] < prices[2] < prices[3] for
      the four tiers. Since all tiers use cost-plus with fixed cost_per_call,
      higher call volume = higher absolute monthly price.
    narration: >
      The project is the final step of productization. After completing it,
      you have all the artifacts needed to publish the trading bot as a real
      package. Day 98 adds the landing page — the web page that explains
      the product to potential customers before they install it.

  - type: summary
    heading: "Day 97 Complete"
    bullets:
      - "ProductConfig: metadata dataclass for all generators"
      - "generate_pyproject: valid pyproject.toml from config"
      - "generate_readme: Markdown with Features, Installation, Usage"
      - "calculate_price + generate_pricing_tiers: cost-plus SaaS pricing"
      - "format_pricing_table: Markdown pricing table"
      - "validate_api_key + gate_feature: minimal access control"
      - "Next: Day 98 — the landing page to bring users to the product"
    narration: >
      Day 97 is complete. The product layer is built. Three days remain:
      landing page (Day 98), portfolio (Day 99), and the final capstone
      (Day 100) where you ship your own AI product from scratch.
""",
]

# ══════════════════════════════════════════════════════════════════════════════
# Project + solution
# ══════════════════════════════════════════════════════════════════════════════

_FULL_P = _P_BASE + _P_PKG + _P_DOC + _P_PRICE + _P_GATE

PROJECT_NB = _nb([
    _md(f"# Day {DAY} Project — Trading Bot Product Artifacts\n\n"
        "Generate all four productization artifacts for the AI trading bot: "
        "pyproject.toml, README.md, changelog entry, and a tiered pricing table. "
        "Verify that each artifact has the correct structure."),
    _code(_FULL_P),
    _code("""\
bot_cfg = ProductConfig(
    name        = "ai-trading-bot",
    version     = "1.0.0",
    description = "AI-powered paper-trading bot with sentiment and technical signals.",
    author      = "AI Engineer",
    email       = "bot@example.com",
    dependencies= ["pandas>=2.0", "requests>=2.28"],
)
features = [
    "SMA crossover and RSI mean-reversion strategies",
    "AI sentiment analysis from news headlines",
    "Stop-loss and drawdown-limit risk controls",
    "Paper-trading bot with daily scheduling",
]
examples = [
    {"title": "Quick Start",
     "code": "from ai_trading_bot import BotRunner\\nrunner = BotRunner('bot.log')"},
]
tiers = [
    {"name": "Free",       "calls":    100, "margin": 0.50},
    {"name": "Indie",      "calls":  1_000, "margin": 0.55},
    {"name": "Pro",        "calls": 10_000, "margin": 0.65},
    {"name": "Enterprise", "calls": 50_000, "margin": 0.70},
]

pyproject  = generate_pyproject(bot_cfg)
readme     = generate_readme(bot_cfg, features, examples)
changelog  = generate_changelog_entry("1.0.0", ["Initial release", "Paper-trading bot"])
tier_data  = generate_pricing_tiers(0.001, tiers)
table      = format_pricing_table(tier_data)

print(pyproject)
print("---")
print(table)
"""),
])

SOLUTION_NB = _nb([
    _md(f"# Day {DAY} Solution — Trading Bot Product Artifacts"),
    _code(_FULL_P),
    _code("""\
bot_cfg = ProductConfig(
    name        = "ai-trading-bot",
    version     = "1.0.0",
    description = "AI-powered paper-trading bot with sentiment and technical signals.",
    author      = "AI Engineer",
    email       = "bot@example.com",
    dependencies= ["pandas>=2.0", "requests>=2.28"],
)
features = [
    "SMA crossover and RSI mean-reversion strategies",
    "AI sentiment analysis from news headlines",
    "Stop-loss and drawdown-limit risk controls",
    "Paper-trading bot with daily scheduling",
]
examples = [
    {"title": "Quick Start",
     "code": "from ai_trading_bot import BotRunner\\nrunner = BotRunner('bot.log')"},
]
tiers = [
    {"name": "Free",       "calls":    100, "margin": 0.50},
    {"name": "Indie",      "calls":  1_000, "margin": 0.55},
    {"name": "Pro",        "calls": 10_000, "margin": 0.65},
    {"name": "Enterprise", "calls": 50_000, "margin": 0.70},
]

pyproject = generate_pyproject(bot_cfg)
readme    = generate_readme(bot_cfg, features, examples)
changelog = generate_changelog_entry("1.0.0", ["Initial release"])
tier_data = generate_pricing_tiers(0.001, tiers)
table     = format_pricing_table(tier_data)

# Assertions
assert "[project]" in pyproject
assert "ai-trading-bot" in pyproject and "1.0.0" in pyproject
assert pyproject.startswith("[build-system]")

assert readme.startswith("# ai-trading-bot")
for s in ["## Features","## Installation","## Usage","## License"]:
    assert s in readme

prices = [t["price_per_month"] for t in tier_data]
assert all(prices[i] < prices[i+1] for i in range(len(prices)-1)), \
    f"prices not increasing: {prices}"

lines = table.split("\\n")
assert lines[0].startswith("|") and "---" in lines[1]

import datetime
assert datetime.date.today().isoformat() in changelog
assert "Initial release" in changelog

print(pyproject)
print(table)
print("\\nSolution smoke-test passed.")
"""),
])

# ══════════════════════════════════════════════════════════════════════════════
# Gate
# ══════════════════════════════════════════════════════════════════════════════

GATE_PY = f"""\
import importlib.util, sys, datetime
spec = importlib.util.spec_from_file_location(
    "{SLUG}", r"{DIR / (SLUG + '.py')}"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

cfg = mod.ProductConfig(
    name="my-bot", version="0.1.0",
    description="A trading bot", author="Jane", email="jane@test.com",
    dependencies=["pandas>=2.0", "requests>=2.28"],
)

# generate_pyproject
out = mod.generate_pyproject(cfg)
assert isinstance(out, str) and len(out) > 50
assert "[project]"       in out
assert "[build-system]"  in out
assert "my-bot"          in out
assert "0.1.0"           in out
assert "pandas>=2.0"     in out
assert "my_bot"          in out   # hyphens → underscores in scripts section

# empty dependencies
cfg2 = mod.ProductConfig("bare","0.0.1","Bare","A","a@b.com")
out2 = mod.generate_pyproject(cfg2)
assert "dependencies = []" in out2

# generate_readme
features = ["Feature A", "Feature B"]
examples = [{{"title": "Quick Start", "code": "import my_bot"}}]
readme = mod.generate_readme(cfg, features, examples)
assert readme.startswith("# my-bot")
assert "## Features"     in readme
assert "## Installation" in readme
assert "## Usage"        in readme
assert "## License"      in readme
assert "- Feature A"     in readme
assert "import my_bot"   in readme

# generate_changelog_entry
entry = mod.generate_changelog_entry("0.2.0", ["Fix bug", "Add feature"])
today = datetime.date.today().isoformat()
assert "0.2.0" in entry
assert today   in entry
assert "Fix bug" in entry

# calculate_price
import math
p = mod.calculate_price(0.001, 1000, margin=0.5)
assert abs(p - 2.0) < 1e-9
p2 = mod.calculate_price(0.001, 1000, margin=0.8)
assert abs(p2 - 5.0) < 1e-9
try:
    mod.calculate_price(0.001, 1000, margin=1.0)
    assert False, "should raise ValueError"
except ValueError:
    pass

# generate_pricing_tiers
tiers = [
    {{"name": "Free", "calls": 100, "margin": 0.5}},
    {{"name": "Pro",  "calls": 1000, "margin": 0.5}},
]
result = mod.generate_pricing_tiers(0.001, tiers)
assert len(result) == 2
for t in result:
    assert {{"name","calls","price_per_month","price_per_call"}}.issubset(t.keys())
assert abs(result[0]["price_per_month"] - 0.20) < 1e-6
assert abs(result[1]["price_per_month"] - 2.00) < 1e-6

# format_pricing_table
table = mod.format_pricing_table(result)
lines = table.split("\\n")
assert lines[0].startswith("|") and lines[0].endswith("|")
assert "---" in lines[1]
assert len(lines) >= 4

# validate_api_key
KEYS = {{"key-abc", "key-xyz"}}
assert     mod.validate_api_key("key-abc", KEYS)
assert not mod.validate_api_key("bad-key", KEYS)
assert not mod.validate_api_key("KEY-ABC", KEYS)  # case-sensitive

# gate_feature: valid
result2 = mod.gate_feature("key-abc", KEYS, lambda x: x * 3, 7)
assert result2 == 21

# gate_feature: invalid
try:
    mod.gate_feature("bad", KEYS, lambda: "secret")
    assert False, "should raise PermissionError"
except PermissionError as pe:
    assert "bad" in str(pe)

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
