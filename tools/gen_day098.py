#!/usr/bin/env python3
"""Day 098 generator — Launching."""
import json, pathlib

ROOT  = pathlib.Path(__file__).parent.parent
DAY   = "098"
SLUG  = "launcher"
TITLE = "Launching"
DIR   = ROOT / "07_finance" / f"day_{DAY}"

# ══════════════════════════════════════════════════════════════════════════════
# Deliverable
# ══════════════════════════════════════════════════════════════════════════════

DELIVERABLE = '''\
"""
Day 098 — Launching
====================
Tools to generate a product landing page, manage a waitlist, and produce
launch marketing copy. All pure Python standard library — no paid APIs.

Public API
----------
    LandingPageConfig           — dataclass for landing-page configuration
    generate_landing_page(cfg)  -> str  (complete HTML document)
    WaitlistEntry               — dataclass for one waitlist subscriber
    Waitlist(path)              — file-backed waitlist manager
    generate_tagline_prompt(product_name, description, n=3) -> list[dict]
    parse_taglines(llm_response) -> list[str]
    generate_launch_email(product_name, tagline, cta_url, recipient_name="") -> dict
    generate_social_post(product_name, tagline, cta_url, platform="twitter") -> str
"""
import csv, datetime, io, json, pathlib
from dataclasses import dataclass, field


# ── landing page ──────────────────────────────────────────────────────────────

@dataclass
class LandingPageConfig:
    """Configuration for generate_landing_page.

    Fields:
        product_name  : str  — displayed in <title> and hero <h1>
        tagline       : str  — one-sentence hero sub-heading
        description   : str  — paragraph below the feature list
        features      : list[str] — rendered as <li> items
        cta_text      : str  — call-to-action button label (default "Join the Waitlist")
        cta_url       : str  — href for the CTA button (default "#waitlist")
        primary_color : str  — CSS color for hero background + accents (default "#2563eb")
    """
    product_name:  str
    tagline:       str
    description:   str
    features:      list
    cta_text:      str = "Join the Waitlist"
    cta_url:       str = "#waitlist"
    primary_color: str = "#2563eb"


def generate_landing_page(cfg):
    """Generate a complete, self-contained HTML landing page.

    Sections:
      .hero     — product name (h1), tagline, CTA button
      .features — feature list (ul) + description paragraph
      #waitlist — email input + CTA button

    The output is a valid HTML5 document with inline CSS.
    All color accents use cfg.primary_color.

    Args:
        cfg : LandingPageConfig

    Returns:
        str — complete HTML document starting with <!DOCTYPE html>
    """
    feature_items = "\\n".join(f"      <li>{f}</li>" for f in cfg.features)
    return (
        "<!DOCTYPE html>\\n"
        '<html lang="en">\\n'
        "<head>\\n"
        '  <meta charset="UTF-8">\\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">\\n'
        f"  <title>{cfg.product_name}</title>\\n"
        "  <style>\\n"
        "    body { font-family: system-ui, sans-serif; margin: 0; padding: 0; }\\n"
        f"    .hero {{ background: {cfg.primary_color}; color: white; padding: 80px 40px; text-align: center; }}\\n"
        "    h1 { font-size: 3rem; margin: 0 0 16px; }\\n"
        "    .tagline { font-size: 1.5rem; opacity: 0.9; margin-bottom: 32px; }\\n"
        f"    .cta {{ background: white; color: {cfg.primary_color}; padding: 16px 32px; "
        "border-radius: 8px; font-size: 1.1rem; text-decoration: none; font-weight: bold; }\\n"
        "    .features { padding: 60px 40px; max-width: 800px; margin: 0 auto; }\\n"
        "    .features ul { font-size: 1.1rem; line-height: 2; }\\n"
        "    #waitlist { padding: 60px 40px; background: #f8fafc; text-align: center; }\\n"
        "    input { padding: 12px; font-size: 1rem; width: 300px; "
        "border: 1px solid #ccc; border-radius: 4px; }\\n"
        f"    button {{ padding: 12px 24px; font-size: 1rem; background: {cfg.primary_color}; "
        "color: white; border: none; border-radius: 4px; cursor: pointer; }\\n"
        "  </style>\\n"
        "</head>\\n"
        "<body>\\n"
        '  <section class="hero">\\n'
        f"    <h1>{cfg.product_name}</h1>\\n"
        f'    <p class="tagline">{cfg.tagline}</p>\\n'
        f'    <a class="cta" href="{cfg.cta_url}">{cfg.cta_text}</a>\\n'
        "  </section>\\n"
        '  <section class="features">\\n'
        "    <h2>Features</h2>\\n"
        "    <ul>\\n"
        f"{feature_items}\\n"
        "    </ul>\\n"
        f"    <p>{cfg.description}</p>\\n"
        "  </section>\\n"
        '  <section id="waitlist">\\n'
        "    <h2>Join the Waitlist</h2>\\n"
        "    <p>Be the first to know when we launch.</p>\\n"
        '    <input type="email" placeholder="your@email.com" />\\n'
        f"    <button type=\\"button\\">{cfg.cta_text}</button>\\n"
        "  </section>\\n"
        "</body>\\n"
        "</html>"
    )


# ── waitlist ──────────────────────────────────────────────────────────────────

@dataclass
class WaitlistEntry:
    """One waitlist subscriber.

    Fields:
        email      : str — normalised to lowercase, stripped
        name       : str — optional display name (default "")
        joined_at  : str — ISO datetime string, auto-set on creation
        source     : str — acquisition channel (default "landing_page")
    """
    email:     str
    name:      str = ""
    joined_at: str = field(
        default_factory=lambda: datetime.datetime.now().isoformat()
    )
    source:    str = "landing_page"


class Waitlist:
    """File-backed waitlist manager.

    Stores subscribers as a JSON array at the given path.
    Safe to instantiate multiple times on the same file — each instantiation
    loads the current state from disk.

    Usage:
        wl = Waitlist("waitlist.json")
        added = wl.add("user@example.com", name="Alice")
        print(wl.count())
        print(wl.list_emails())
        print(wl.export_csv())
    """

    def __init__(self, path):
        self.path = pathlib.Path(path)
        self._entries = []
        if self.path.exists():
            self._load()

    def _load(self):
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self._entries = [WaitlistEntry(**e) for e in data]

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = [
            {"email": e.email, "name": e.name,
             "joined_at": e.joined_at, "source": e.source}
            for e in self._entries
        ]
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def add(self, email, name="", source="landing_page"):
        """Add an email to the waitlist.

        Args:
            email  : str — stripped + lowercased before storing
            name   : str — optional display name
            source : str — acquisition channel (default "landing_page")

        Returns:
            True  — added successfully
            False — already on the list (duplicate; not added again)

        Raises:
            ValueError — if email is empty or has no "@"
        """
        email = email.strip().lower()
        if not email or "@" not in email:
            raise ValueError(f"Invalid email: {email!r}")
        if any(e.email == email for e in self._entries):
            return False
        self._entries.append(WaitlistEntry(email=email, name=name, source=source))
        self._save()
        return True

    def count(self):
        """Return number of subscribers."""
        return len(self._entries)

    def list_emails(self):
        """Return list of subscriber email strings."""
        return [e.email for e in self._entries]

    def export_csv(self):
        """Return the full waitlist as a CSV string (email, name, joined_at, source)."""
        buf = io.StringIO()
        writer = csv.DictWriter(
            buf, fieldnames=["email", "name", "joined_at", "source"]
        )
        writer.writeheader()
        for e in self._entries:
            writer.writerow({
                "email": e.email, "name": e.name,
                "joined_at": e.joined_at, "source": e.source,
            })
        return buf.getvalue()


# ── marketing copy ────────────────────────────────────────────────────────────

def generate_tagline_prompt(product_name, description, n=3):
    """Build a messages list for an LLM to generate tagline variants.

    The system prompt instructs the LLM to return a JSON array of strings only
    (no markdown, no explanation) — suitable for parse_taglines.

    Args:
        product_name : str — name of the product
        description  : str — one-sentence product description
        n            : int — number of taglines to request (default 3)

    Returns:
        list[dict] — messages in the format [{"role": ..., "content": ...}, ...]
    """
    return [
        {
            "role": "system",
            "content": (
                "You are a SaaS copywriter. Respond with a JSON array of strings only. "
                "No explanation. No markdown. Just the JSON array."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Write {n} punchy taglines for a product called '{product_name}'. "
                f"Product description: {description}. "
                f"Each tagline: 10 words or fewer, clear benefit, no jargon. "
                f"Return as a JSON array of {n} strings."
            ),
        },
    ]


def parse_taglines(llm_response):
    """Parse a JSON array of taglines from an LLM response string.

    Handles responses that may be wrapped in markdown code fences (```json...```).

    Args:
        llm_response : str — raw LLM output, expected to contain a JSON array

    Returns:
        list[str] — the parsed tagline strings

    Raises:
        json.JSONDecodeError — if the response cannot be parsed as JSON
    """
    text = llm_response.strip()
    if text.startswith("```"):
        lines = text.split("\\n")
        text = "\\n".join(lines[1:-1]) if len(lines) > 2 else text
    return json.loads(text)


def generate_launch_email(product_name, tagline, cta_url, recipient_name=""):
    """Generate a launch announcement email dict.

    Args:
        product_name   : str — product name for subject and sign-off
        tagline        : str — one-line product pitch
        cta_url        : str — URL for the main call-to-action
        recipient_name : str — personalisation; omit for generic greeting

    Returns:
        dict with keys:
            "subject" : str — email subject line
            "body"    : str — plain-text email body
    """
    greeting = f"Hi {recipient_name}," if recipient_name else "Hi there,"
    return {
        "subject": f"{product_name} is live — you\'re in!",
        "body": (
            f"{greeting}\\n\\n"
            f"The wait is over. {product_name} is officially live.\\n\\n"
            f"{tagline}\\n\\n"
            f"As an early member of our waitlist, you get first access.\\n\\n"
            f"\\u2192 {cta_url}\\n\\n"
            f"Questions? Just reply to this email.\\n\\n"
            f"\\u2014 The {product_name} Team"
        ),
    }


def generate_social_post(product_name, tagline, cta_url, platform="twitter"):
    """Generate a launch social media post.

    Args:
        product_name : str
        tagline      : str
        cta_url      : str
        platform     : str — "twitter", "linkedin", or any other (generic)

    Returns:
        str — post text, ≤280 chars for Twitter (truncated if needed)
    """
    if platform == "twitter":
        post = f"\\U0001f680 {product_name} is live!\\n\\n{tagline}\\n\\n{cta_url}"
        if len(post) > 280:
            post = post[:277] + "..."
        return post
    if platform == "linkedin":
        return (
            f"Excited to announce that {product_name} is officially live! \\U0001f389\\n\\n"
            f"{tagline}\\n\\n"
            f"We built this to solve a real problem and we can\'t wait to see "
            f"what you do with it.\\n\\n"
            f"Try it here: {cta_url}\\n\\n"
            f"#AI #ProductLaunch #BuildInPublic"
        )
    return f"{product_name}: {tagline} — {cta_url}"
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
import csv, datetime, io, json, pathlib, tempfile
from dataclasses import dataclass, field

@dataclass
class LandingPageConfig:
    product_name: str; tagline: str; description: str; features: list
    cta_text: str = "Join the Waitlist"; cta_url: str = "#waitlist"
    primary_color: str = "#2563eb"

_CFG = LandingPageConfig(
    product_name  = "AI Trading Bot",
    tagline       = "Automate your trading strategy with AI-powered signals.",
    description   = "Built with sentiment analysis, technical indicators, and risk controls.",
    features      = ["Sentiment-driven signals", "Stop-loss protection", "Daily scheduling"],
)
"""

_P_LP = """\
def generate_landing_page(cfg):
    feature_items = "\\n".join(f"      <li>{f}</li>" for f in cfg.features)
    return (
        "<!DOCTYPE html>\\n"
        '<html lang=\\"en\\">\\n'
        "<head>\\n"
        '  <meta charset=\\"UTF-8\\">\\n'
        f"  <title>{cfg.product_name}</title>\\n"
        "  <style>\\n"
        f"    .hero {{ background: {cfg.primary_color}; color: white; padding: 80px 40px; text-align: center; }}\\n"
        "    h1 { font-size: 3rem; margin: 0 0 16px; }\\n"
        f"    .cta {{ background: white; color: {cfg.primary_color}; padding: 16px 32px; border-radius: 8px; }}\\n"
        "  </style>\\n"
        "</head>\\n"
        "<body>\\n"
        '  <section class=\\"hero\\">\\n'
        f"    <h1>{cfg.product_name}</h1>\\n"
        f'    <p class=\\"tagline\\">{cfg.tagline}</p>\\n'
        f'    <a class=\\"cta\\" href=\\"{cfg.cta_url}\\">{cfg.cta_text}</a>\\n'
        "  </section>\\n"
        '  <section class=\\"features\\">\\n'
        "    <h2>Features</h2>\\n"
        "    <ul>\\n"
        f"{feature_items}\\n"
        "    </ul>\\n"
        f"    <p>{cfg.description}</p>\\n"
        "  </section>\\n"
        '  <section id=\\"waitlist\\">\\n'
        "    <h2>Join the Waitlist</h2>\\n"
        '    <input type=\\"email\\" placeholder=\\"your@email.com\\" />\\n'
        f"    <button type=\\"button\\">{cfg.cta_text}</button>\\n"
        "  </section>\\n"
        "</body>\\n"
        "</html>"
    )
"""

_P_WL = """\
@dataclass
class WaitlistEntry:
    email: str; name: str = ""
    joined_at: str = field(default_factory=lambda: datetime.datetime.now().isoformat())
    source: str = "landing_page"

class Waitlist:
    def __init__(self, path):
        self.path = pathlib.Path(path); self._entries = []
        if self.path.exists(): self._load()
    def _load(self):
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self._entries = [WaitlistEntry(**e) for e in data]
    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = [{"email": e.email,"name":e.name,"joined_at":e.joined_at,"source":e.source}
                for e in self._entries]
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    def add(self, email, name="", source="landing_page"):
        email = email.strip().lower()
        if not email or "@" not in email: raise ValueError(f"Invalid email: {email!r}")
        if any(e.email == email for e in self._entries): return False
        self._entries.append(WaitlistEntry(email=email, name=name, source=source))
        self._save(); return True
    def count(self): return len(self._entries)
    def list_emails(self): return [e.email for e in self._entries]
    def export_csv(self):
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=["email","name","joined_at","source"])
        w.writeheader()
        for e in self._entries:
            w.writerow({"email":e.email,"name":e.name,"joined_at":e.joined_at,"source":e.source})
        return buf.getvalue()
"""

_P_COPY = """\
def generate_tagline_prompt(product_name, description, n=3):
    return [
        {"role":"system","content":(
            "You are a SaaS copywriter. Respond with a JSON array of strings only. "
            "No explanation. No markdown. Just the JSON array."
        )},
        {"role":"user","content":(
            f"Write {n} punchy taglines for a product called '{product_name}'. "
            f"Product description: {description}. "
            f"Each tagline: 10 words or fewer, clear benefit, no jargon. "
            f"Return as a JSON array of {n} strings."
        )},
    ]

def parse_taglines(llm_response):
    text = llm_response.strip()
    if text.startswith("```"):
        lines = text.split("\\n"); text = "\\n".join(lines[1:-1]) if len(lines) > 2 else text
    return json.loads(text)

def generate_launch_email(product_name, tagline, cta_url, recipient_name=""):
    greeting = f"Hi {recipient_name}," if recipient_name else "Hi there,"
    return {
        "subject": f"{product_name} is live \\u2014 you're in!",
        "body": (
            f"{greeting}\\n\\nThe wait is over. {product_name} is officially live.\\n\\n"
            f"{tagline}\\n\\nAs an early member of our waitlist, you get first access.\\n\\n"
            f"\\u2192 {cta_url}\\n\\nQuestions? Just reply to this email.\\n\\n"
            f"\\u2014 The {product_name} Team"
        ),
    }

def generate_social_post(product_name, tagline, cta_url, platform="twitter"):
    if platform == "twitter":
        post = f"\\U0001f680 {product_name} is live!\\n\\n{tagline}\\n\\n{cta_url}"
        return post[:277] + "..." if len(post) > 280 else post
    if platform == "linkedin":
        return (
            f"Excited to announce that {product_name} is officially live! \\U0001f389\\n\\n"
            f"{tagline}\\n\\nWe built this to solve a real problem.\\n\\n"
            f"Try it here: {cta_url}\\n\\n#AI #ProductLaunch #BuildInPublic"
        )
    return f"{product_name}: {tagline} \\u2014 {cta_url}"
"""

# ══════════════════════════════════════════════════════════════════════════════
# Exercises
# ══════════════════════════════════════════════════════════════════════════════

_EX1 = _nb([
    _md("# Exercise 1 — generate_landing_page\n\n"
        "A landing page is the product's front door — the web page that converts "
        "a curious visitor into a subscriber or customer. "
        "`generate_landing_page` takes a `LandingPageConfig` and returns a complete, "
        "self-contained HTML document with a hero section, feature list, and "
        "waitlist signup form. No frameworks, no external assets — pure HTML + CSS."),
    _code(_P_BASE + """\

def generate_landing_page(cfg):
    \"\"\"Generate a complete HTML landing page.

    Required sections (checked by the tests below):
      - starts with <!DOCTYPE html>
      - <title> contains cfg.product_name
      - <h1> contains cfg.product_name
      - cfg.tagline appears in the page
      - each feature in cfg.features appears as a <li>
      - cfg.cta_text appears at least once
      - cfg.primary_color appears in the CSS
      - a #waitlist section exists

    Returns:
        str — valid HTML document
    \"\"\"
    feature_items = "\\n".join(f"<li>{f}</li>" for f in cfg.features)
    # TODO: build the HTML string (~40 lines)
    return ""
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — starts with <!DOCTYPE html>
try:
    html = generate_landing_page(_CFG)
    assert html.strip().startswith("<!DOCTYPE html"), \
        f"expected <!DOCTYPE html>, got: {html[:30]!r}"
    checks += 1; print("✅ 1 starts with <!DOCTYPE html>")
except Exception as e:
    print("❌ 1:", e)

# 2 — title and h1 contain product name
try:
    html = generate_landing_page(_CFG)
    assert f"<title>{_CFG.product_name}</title>" in html, "missing <title>"
    assert f"<h1>{_CFG.product_name}</h1>"       in html, "missing <h1>"
    checks += 1; print(f"✅ 2 <title> and <h1> contain '{_CFG.product_name}'")
except Exception as e:
    print("❌ 2:", e)

# 3 — tagline and all features appear in output
try:
    html = generate_landing_page(_CFG)
    assert _CFG.tagline in html, "tagline not in HTML"
    for feat in _CFG.features:
        assert feat in html, f"feature {feat!r} not found"
    checks += 1; print("✅ 3 tagline and all features present")
except Exception as e:
    print("❌ 3:", e)

# 4 — CTA text and primary color appear
try:
    html = generate_landing_page(_CFG)
    assert _CFG.cta_text      in html, "cta_text not found"
    assert _CFG.primary_color in html, "primary_color not in CSS"
    checks += 1; print(f"✅ 4 CTA '{_CFG.cta_text}' and color '{_CFG.primary_color}' present")
except Exception as e:
    print("❌ 4:", e)

# 5 — #waitlist section exists
try:
    html = generate_landing_page(_CFG)
    assert 'id="waitlist"' in html or "id='waitlist'" in html, \
        "missing id=waitlist section"
    checks += 1; print("✅ 5 #waitlist section found")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX2 = _nb([
    _md("# Exercise 2 — Waitlist\n\n"
        "A waitlist is the simplest way to validate demand before building. "
        "The `Waitlist` class stores subscribers in a JSON file on disk. "
        "It deduplicates by email, normalises to lowercase, validates the "
        "`@` character, and can export to CSV for use in email tools like "
        "Mailchimp or ConvertKit."),
    _code(_P_BASE + """\

@dataclass
class WaitlistEntry:
    \"\"\"One waitlist subscriber.\"\"\"
    email:     str
    name:      str = ""
    joined_at: str = field(default_factory=lambda: datetime.datetime.now().isoformat())
    source:    str = "landing_page"


class Waitlist:
    \"\"\"File-backed waitlist manager.

    Stores subscribers as a JSON array at self.path.
    add()        — add email; return True if added, False if duplicate
    count()      — number of subscribers
    list_emails() — list of email strings
    export_csv() — CSV string with columns: email, name, joined_at, source

    Raises ValueError for invalid emails (empty or no '@').
    Strips and lowercases emails before storing.
    \"\"\"
    def __init__(self, path):
        self.path = pathlib.Path(path)
        self._entries = []
        if self.path.exists():
            self._load()

    def _load(self):
        # TODO: load JSON from self.path; populate self._entries
        pass

    def _save(self):
        # TODO: mkdir parents; write JSON to self.path
        pass

    def add(self, email, name="", source="landing_page"):
        # TODO: strip+lower email; validate; deduplicate; append; save; return bool
        return False

    def count(self):
        # TODO: 1 line
        return 0

    def list_emails(self):
        # TODO: 1 line
        return []

    def export_csv(self):
        # TODO: use csv.DictWriter with io.StringIO; return string
        return ""
"""),
    _md("### Checks"),
    _code("""\
checks = 0

with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
    wl_path = f.name

try:
    import os; os.unlink(wl_path)  # start with no file
except FileNotFoundError:
    pass

# 1 — add returns True for new email, count increments
try:
    wl = Waitlist(wl_path)
    r1 = wl.add("alice@example.com", name="Alice")
    r2 = wl.add("bob@example.com",   name="Bob")
    assert r1 is True and r2 is True, f"expected True, True; got {r1}, {r2}"
    assert wl.count() == 2, f"expected count=2, got {wl.count()}"
    checks += 1; print("✅ 1 add() returns True, count() = 2")
except Exception as e:
    print("❌ 1:", e)

# 2 — duplicate returns False, count unchanged
try:
    wl = Waitlist(wl_path)
    r3 = wl.add("alice@example.com")
    assert r3 is False, f"expected False for duplicate, got {r3}"
    assert wl.count() == 2
    checks += 1; print("✅ 2 duplicate add() returns False, count stays 2")
except Exception as e:
    print("❌ 2:", e)

# 3 — email normalisation (uppercase → lowercase)
try:
    wl = Waitlist(wl_path)
    r4 = wl.add("CAROL@Example.COM", name="Carol")
    assert r4 is True
    assert "carol@example.com" in wl.list_emails()
    checks += 1; print("✅ 3 email normalised to lowercase: carol@example.com")
except Exception as e:
    print("❌ 3:", e)

# 4 — persistence: reload from file
try:
    wl2 = Waitlist(wl_path)   # fresh instance, same file
    emails = wl2.list_emails()
    assert "alice@example.com" in emails
    assert "bob@example.com"   in emails
    assert "carol@example.com" in emails
    assert wl2.count() == 3
    checks += 1; print("✅ 4 persisted to disk; reload gives 3 entries")
except Exception as e:
    print("❌ 4:", e)

# 5 — CSV export has header and all emails
try:
    wl = Waitlist(wl_path)
    csv_out = wl.export_csv()
    lines = csv_out.strip().split("\\n")
    assert "email" in lines[0], f"expected header, got: {lines[0]}"
    assert "alice@example.com" in csv_out
    assert "bob@example.com"   in csv_out
    assert len(lines) == 4      # header + 3 rows
    checks += 1; print("✅ 5 CSV has header + 3 data rows with correct emails")
except Exception as e:
    print("❌ 5:", e)

import os
try: os.unlink(wl_path)
except: pass

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX3 = _nb([
    _md("# Exercise 3 — generate_tagline_prompt and parse_taglines\n\n"
        "Marketing copy — taglines, headlines, CTAs — is one of the highest-value "
        "uses of LLMs in a product context. `generate_tagline_prompt` builds a "
        "messages list that instructs the LLM to return a JSON array of taglines. "
        "`parse_taglines` extracts the list from the response, handling the common "
        "case where the model wraps the JSON in a markdown code fence."),
    _code(_P_BASE + """\

def generate_tagline_prompt(product_name, description, n=3):
    \"\"\"Build a messages list for an LLM to generate tagline variants.

    The system prompt instructs the LLM to return a JSON array only.
    The user message specifies the product, description, n, and constraints.

    Returns:
        list[dict] — [{"role": ..., "content": ...}, ...]
    \"\"\"
    # TODO: ~9 lines — return list with "system" and "user" messages
    return []


def parse_taglines(llm_response):
    \"\"\"Parse a JSON array of taglines from an LLM response.

    Strips markdown code fences (```...```) if present before parsing.

    Returns:
        list[str]

    Raises:
        json.JSONDecodeError — if not valid JSON after stripping
    \"\"\"
    # TODO: ~4 lines
    return []
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — returns list with exactly 2 messages
try:
    msgs = generate_tagline_prompt("TestBot", "A bot for testing.", n=4)
    assert isinstance(msgs, list) and len(msgs) == 2, \
        f"expected list of 2 messages, got {msgs}"
    checks += 1; print("✅ 1 returns list of 2 message dicts")
except Exception as e:
    print("❌ 1:", e)

# 2 — first message is system role
try:
    msgs = generate_tagline_prompt("TestBot", "A bot.", n=3)
    assert msgs[0]["role"] == "system", f"first role should be 'system', got {msgs[0]['role']!r}"
    checks += 1; print("✅ 2 first message role == 'system'")
except Exception as e:
    print("❌ 2:", e)

# 3 — user message contains product name, description, and n
try:
    msgs = generate_tagline_prompt("AI Trading Bot", "Automates trades.", n=5)
    user_content = msgs[1]["content"]
    assert "AI Trading Bot"   in user_content, "product name missing from user message"
    assert "Automates trades" in user_content, "description missing from user message"
    assert "5"                in user_content, "n=5 missing from user message"
    checks += 1; print("✅ 3 user message contains product name, description, n=5")
except Exception as e:
    print("❌ 3:", e)

# 4 — parse_taglines: plain JSON array
try:
    raw = '["Trade smarter.", "AI-powered edge.", "Your strategy, automated."]'
    tags = parse_taglines(raw)
    assert tags == ["Trade smarter.", "AI-powered edge.", "Your strategy, automated."]
    checks += 1; print("✅ 4 parse_taglines parses plain JSON array correctly")
except Exception as e:
    print("❌ 4:", e)

# 5 — parse_taglines: markdown-fenced JSON
try:
    fenced = '```json\\n["Tag A", "Tag B", "Tag C"]\\n```'
    tags = parse_taglines(fenced)
    assert tags == ["Tag A", "Tag B", "Tag C"]
    checks += 1; print("✅ 5 parse_taglines strips markdown fences and parses correctly")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX4 = _nb([
    _md("# Exercise 4 — generate_launch_email and generate_social_post\n\n"
        "The launch email and the social post are the two most important pieces "
        "of launch-day communication. The email goes to your waitlist — it is "
        "personal, direct, and action-oriented. The social post is public — "
        "it is punchy, shareable, and platform-aware. Twitter posts must stay "
        "under 280 characters; LinkedIn posts can be longer and use hashtags."),
    _code(_P_BASE + """\

def generate_launch_email(product_name, tagline, cta_url, recipient_name=""):
    \"\"\"Generate a launch announcement email.

    Returns:
        dict with keys:
          "subject" : str — email subject line
          "body"    : str — plain-text email body

    Body structure:
      greeting (personalised if recipient_name is given)
      product name is officially live
      tagline
      early-access note
      → cta_url
      sign-off from The {product_name} Team
    \"\"\"
    # TODO: ~8 lines
    return {}


def generate_social_post(product_name, tagline, cta_url, platform="twitter"):
    \"\"\"Generate a launch social media post.

    platform="twitter"  : max 280 chars; truncated to 277 + "..." if too long
    platform="linkedin" : longer, includes #AI #ProductLaunch #BuildInPublic
    other               : "{product_name}: {tagline} — {cta_url}"

    Returns:
        str
    \"\"\"
    # TODO: ~8 lines
    return ""
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — generate_launch_email returns dict with subject and body
try:
    email = generate_launch_email("AI Bot", "Automate everything.", "https://aibot.io")
    assert isinstance(email, dict), f"expected dict, got {type(email)}"
    assert "subject" in email and "body" in email, f"missing keys: {list(email.keys())}"
    checks += 1; print("✅ 1 returns dict with 'subject' and 'body' keys")
except Exception as e:
    print("❌ 1:", e)

# 2 — subject contains product name
try:
    email = generate_launch_email("AI Bot", "Automate.", "https://aibot.io")
    assert "AI Bot" in email["subject"], f"product name not in subject: {email['subject']!r}"
    checks += 1; print(f"✅ 2 subject: {email['subject']!r}")
except Exception as e:
    print("❌ 2:", e)

# 3 — body is personalised when name is given; generic otherwise
try:
    e_named   = generate_launch_email("P", "T.", "u", recipient_name="Alice")
    e_generic = generate_launch_email("P", "T.", "u")
    assert "Alice" in e_named["body"],    "recipient_name 'Alice' not in body"
    assert "Alice" not in e_generic["body"], "generic body should not contain 'Alice'"
    checks += 1; print("✅ 3 personalised body when name given; generic otherwise")
except Exception as e:
    print("❌ 3:", e)

# 4 — twitter post ≤ 280 chars
try:
    post = generate_social_post("AI Bot", "Automate everything.", "https://aibot.io", platform="twitter")
    assert isinstance(post, str) and len(post) <= 280, \
        f"twitter post must be ≤280 chars, got {len(post)}"
    assert "AI Bot" in post, "product name missing from twitter post"
    checks += 1; print(f"✅ 4 twitter post: {len(post)} chars (≤280), contains product name")
except Exception as e:
    print("❌ 4:", e)

# 5 — linkedin post contains hashtags; generic platform is a one-liner
try:
    li = generate_social_post("AI Bot", "Automate everything.", "https://aibot.io", platform="linkedin")
    assert "#AI" in li or "#ai" in li, "linkedin post missing #AI hashtag"
    generic = generate_social_post("P", "T.", "http://x.com", platform="other")
    assert "P" in generic and "T." in generic and "http://x.com" in generic
    checks += 1; print("✅ 5 linkedin has hashtags; generic platform returns one-liner")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX5 = _nb([
    _md("# Exercise 5 — Full Launch Pipeline\n\n"
        "Combine all four Day 98 components into a complete launch sequence: "
        "generate the landing page HTML, build the waitlist, generate and parse "
        "taglines from a mock LLM, and produce the launch email + social posts. "
        "This is the workflow you would run on launch day."),
    _code(_P_BASE + _P_LP + _P_WL + _P_COPY),
    _md("### Checks"),
    _code("""\
import os, tempfile
checks = 0

# Setup
with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
    wl_path = f.name
try: os.unlink(wl_path)
except: pass

PRODUCT = "AI Trading Bot"
TAGLINE = "Automate your strategy with AI-driven signals."
URL     = "https://aitradingbot.io"

# 1 — landing page: valid HTML with product name
try:
    html = generate_landing_page(_CFG)
    assert html.startswith("<!DOCTYPE html")
    assert PRODUCT in html
    checks += 1; print("✅ 1 landing page HTML generated")
except Exception as e:
    print("❌ 1:", e)

# 2 — waitlist: add 3 subscribers
try:
    wl = Waitlist(wl_path)
    for addr in ["a@x.com", "b@x.com", "c@x.com"]:
        wl.add(addr)
    assert wl.count() == 3
    checks += 1; print("✅ 2 waitlist has 3 subscribers")
except Exception as e:
    print("❌ 2:", e)

# 3 — parse_taglines from mock LLM response (fenced)
try:
    mock_llm_resp = '```json\\n["Trade smarter with AI.", "Your edge, automated.", "Signals, not noise."]\\n```'
    tags = parse_taglines(mock_llm_resp)
    assert len(tags) == 3
    assert all(isinstance(t, str) and len(t) > 0 for t in tags)
    checks += 1; print(f"✅ 3 parsed 3 taglines from mock LLM response: {tags[0]!r}...")
except Exception as e:
    print("❌ 3:", e)

# 4 — launch email for each waitlist subscriber
try:
    emails_sent = 0
    for addr in wl.list_emails():
        em = generate_launch_email(PRODUCT, TAGLINE, URL)
        assert "subject" in em and "body" in em
        assert PRODUCT in em["subject"] or PRODUCT in em["body"]
        emails_sent += 1
    assert emails_sent == 3
    checks += 1; print(f"✅ 4 generated {emails_sent} launch emails")
except Exception as e:
    print("❌ 4:", e)

# 5 — social posts for twitter + linkedin
try:
    tw = generate_social_post(PRODUCT, TAGLINE, URL, platform="twitter")
    li = generate_social_post(PRODUCT, TAGLINE, URL, platform="linkedin")
    assert len(tw) <= 280, f"twitter post too long: {len(tw)}"
    assert PRODUCT in tw
    assert "#AI" in li or "#ProductLaunch" in li
    checks += 1; print(f"✅ 5 twitter ({len(tw)} chars) + linkedin posts generated")
except Exception as e:
    print("❌ 5:", e)

try: os.unlink(wl_path)
except: pass

print(f"\\n{checks}/5 checks passed!")
"""),
])

EXERCISES = [_EX1, _EX2, _EX3, _EX4, _EX5]

# ══════════════════════════════════════════════════════════════════════════════
# YAML lessons
# ══════════════════════════════════════════════════════════════════════════════

LESSONS = [
    """\
day: "098"
lesson: 1
title: "Product Launch Fundamentals"
slides:
  - type: title
    heading: "Launching"
    subheading: "Getting from product to users"
    narration: >
      Day 98. The product is built and packaged. Today you learn how to get
      it in front of users: a landing page that explains it, a waitlist that
      captures interest, marketing copy that communicates the value, and the
      social posts that spread the word. These are not optional extras —
      without them, a great product gets zero users.

  - type: concept
    label: "Launch components"
    heading: "The Four Components of a Product Launch"
    body: >
      Landing page → waitlist → marketing copy → distribution.
    bullets:
      - "Landing page: the product's front door; converts visitors to subscribers"
      - "Waitlist: captures demand before launch; social proof; launch fuel"
      - "Marketing copy: taglines, emails, social posts that communicate value"
      - "Distribution: the channels that bring users to the page (SEO, social, HN)"
      - "Order: build the page first, then drive traffic"
    narration: >
      A landing page is not a polished website — it is a single page with one
      job: convince the visitor to sign up. A waitlist is a list of email
      addresses from people who want the product before it exists. Marketing
      copy is the language that makes people understand and want the product.
      Distribution is where those people come from. Today you build the first
      three. Distribution (SEO, content, paid ads) is a subject for another
      course — but the tools you build today are what distribution leads to.

  - type: concept
    label: "Landing page job"
    heading: "The Landing Page's Only Job"
    body: >
      One page. One action. Everything else is noise.
    bullets:
      - "Hero: what it is + why it matters (tagline + h1) in < 5 seconds"
      - "Features: why choose this over alternatives (3–5 bullets)"
      - "Social proof: who else uses it (testimonials, logos, numbers)"
      - "CTA: one clear action (waitlist email, 'Start free', 'Try demo')"
      - "Remove everything that doesn't help the visitor take the action"
    narration: >
      The most common landing page mistake is including too much information.
      Every additional paragraph, link, or option reduces conversion. The page
      has one job: get the visitor to click the CTA. generate_landing_page
      produces a four-section page with exactly that structure. In production
      you would add analytics (Plausible, Fathom, Posthog) to measure the
      conversion rate and A/B test the copy.

  - type: exercise
    heading: "Exercise 1 — generate_landing_page"
    prompt: >
      generate_landing_page(cfg) returns a complete HTML5 document.
      Required: <!DOCTYPE html> start; <title> and <h1> with product_name;
      tagline in the hero; each feature as a <li>; cta_text as a button/link;
      primary_color in the CSS; a section with id="waitlist".
    hint: >
      Build the string with concatenation or a big f-string. The feature items
      can be built with "\\n".join(f"<li>{f}</li>" for f in cfg.features).
      The #waitlist section just needs the id attribute — it doesn't need to
      actually submit a form for these checks.
    narration: >
      In production you would use a static site generator (Astro, Hugo, Next.js)
      or a no-code tool (Carrd, Webflow). But generating HTML from Python is
      useful for programmatically creating personalised pages, email templates,
      and report outputs — skills you use throughout the course.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "Landing page: hero + features + waitlist form, one CTA"
      - "LandingPageConfig: metadata dataclass drives all generators"
      - "generate_landing_page: complete HTML5 doc from config"
      - "Next: the Waitlist — capturing and managing subscribers"
    narration: >
      The front door is built. Next: the mechanism that captures email addresses
      from visitors who want to hear more.
""",

    """\
day: "098"
lesson: 2
title: "The Waitlist Strategy"
slides:
  - type: title
    heading: "The Waitlist"
    subheading: "Capturing demand before you build"
    narration: >
      The waitlist is one of the highest-signal things you can do before
      launching a product. A visitor who types their email address is telling
      you "I want this". A hundred email addresses are strong evidence of real
      demand — much stronger than a hundred page views. Today's Waitlist class
      stores subscribers in a JSON file, handles deduplication, normalises
      emails, and exports to CSV for use in email tools.

  - type: concept
    label: "Waitlist mechanics"
    heading: "What the Waitlist Does"
    body: >
      Email addresses from interested users, stored and ready to use on launch day.
    bullets:
      - "add(email): validate, normalise, deduplicate, persist"
      - "count(): how many people want the product"
      - "list_emails(): get all addresses for batch email sending"
      - "export_csv(): CSV for import into Mailchimp/ConvertKit/Postmark"
      - "File-backed: survives restarts, trivial to inspect and edit"
    narration: >
      The Waitlist class stores subscribers as a JSON file. Every add() call
      loads the file, checks for duplicates, appends the new entry, and writes
      back. This is safe for a waitlist size up to a few thousand — at that
      scale, you would migrate to a database (SQLite or Postgres). The export_csv
      method generates CSV with the standard columns (email, name, joined_at,
      source) that every major email marketing tool can import.

  - type: concept
    label: "Email validation"
    heading: "Why Email Validation Matters"
    body: >
      Garbage in, bounced emails out. Validate at the boundary.
    bullets:
      - "Minimum check: stripped, lowercase, contains '@'"
      - "Better: regex for RFC 5322 format (overkill for most products)"
      - "Best: send a confirmation email and require the click"
      - "Today: stripped + lower + '@' check — practical minimum"
      - "Duplicate check: same email once, case-insensitively"
    narration: >
      The Waitlist.add() method strips whitespace, lowercases the email, and
      checks for '@'. This catches the most common mistakes (accidental spaces,
      capitalisation) without requiring a complex regex. The duplicate check is
      case-insensitive because 'Alice@Example.com' and 'alice@example.com' are
      the same address. In production you would add a confirmation email flow
      (double opt-in) to verify the address is real and the owner consented —
      required by GDPR and CAN-SPAM.

  - type: exercise
    heading: "Exercise 2 — Waitlist"
    prompt: >
      Implement the Waitlist class: _load (JSON → WaitlistEntry list),
      _save (list → JSON file, mkdir parents), add (strip+lower, validate '@',
      deduplicate, append, save, return True/False), count, list_emails, export_csv.
      WaitlistEntry has email, name, joined_at (auto-ISO), source.
    hint: >
      _load: json.loads(self.path.read_text()) → [WaitlistEntry(**e) for e in data].
      _save: json.dumps([{"email":e.email,...} for e in self._entries], indent=2).
      export_csv: csv.DictWriter(io.StringIO(), fieldnames=[...]).
    narration: >
      The persistence pattern here (load → mutate → save) is the simplest
      possible approach. It works well at small scale. The key design decisions:
      lowercase emails (so dedup is case-insensitive), return True/False from
      add (so callers know whether a new subscriber was added), and persist
      after every add (so no subscriber is lost if the process crashes).

  - type: summary
    heading: "What You Learned"
    bullets:
      - "Waitlist: JSON-backed subscriber list with add/count/list/export"
      - "Email normalisation: strip + lower before storing"
      - "Deduplication: check existing entries before appending"
      - "CSV export: csv.DictWriter + io.StringIO → importable string"
      - "Next: LLM-generated taglines + marketing copy"
    narration: >
      The waitlist is done. Next: how to use an LLM to generate the marketing
      copy — taglines, launch emails, and social posts.
""",

    """\
day: "098"
lesson: 3
title: "AI-Assisted Marketing Copy"
slides:
  - type: title
    heading: "Marketing Copy with LLMs"
    subheading: "Generate taglines, emails, and social posts"
    narration: >
      Marketing copy — taglines, headlines, call-to-action text — is one of
      the highest-leverage uses of LLMs for solo developers. Writing great copy
      is hard and time-consuming. An LLM can generate ten variants in seconds,
      and you pick the best one. Today you build the prompt-building and
      response-parsing functions for tagline generation, then generate the
      launch email and social post directly (no LLM needed for those).

  - type: concept
    label: "Tagline prompt design"
    heading: "Building the Tagline Prompt"
    body: >
      System: JSON array only. User: n taglines, ≤10 words, clear benefit.
    bullets:
      - "System prompt: constrain the format strictly (JSON array, no markdown)"
      - "User prompt: name, description, count, word limit, benefit requirement"
      - "parse_taglines: strip markdown fences; json.loads → list[str]"
      - "Generate 5–10 variants; pick the best two or three"
      - "A/B test taglines: run two landing pages, measure conversion"
    narration: >
      The system prompt is the key to reliable structured output. By telling
      the LLM "respond with a JSON array of strings only, no explanation, no
      markdown", you maximise the chance of getting clean JSON. parse_taglines
      handles the case where the model still adds a markdown code fence — a
      common failure mode. After stripping the fence, json.loads does the rest.
      In Exercise 3, you will see how this fits into the injection pattern:
      llm_fn(generate_tagline_prompt(...)) → parse_taglines(response).

  - type: code
    label: "Injection pattern"
    heading: "The Full Tagline Generation Flow"
    code: |
      # 1. Build the prompt
      messages = generate_tagline_prompt("AI Bot", "Automates trading.", n=5)

      # 2. Call the LLM (injected — same pattern throughout the course)
      response = llm_fn(messages)   # llm_fn = ollama.chat or any compatible fn

      # 3. Parse the response
      taglines = parse_taglines(response)
      # → ["Your edge, automated.", "Trade smarter, not harder.", ...]

      # 4. Pick the best one for the landing page
      best = taglines[0]
    narration: >
      This is the injection pattern from Day 93 (sentiment signals) applied to
      marketing copy. llm_fn is injected — in development it is a mock that
      returns a fixed JSON string, in production it calls Ollama or a cloud
      model. The gate uses a mock LLM that returns a hardcoded JSON array.
      The functions are testable without a running LLM.

  - type: exercise
    heading: "Exercise 3 — generate_tagline_prompt and parse_taglines"
    prompt: >
      generate_tagline_prompt(product_name, description, n=3) returns a list
      of two message dicts: system (JSON array only, no markdown) and user
      (n taglines, name, description, ≤10 words, JSON array of n strings).
      parse_taglines(llm_response) strips markdown fences and json.loads the result.
    hint: >
      Check 5: the fenced input is '```json\\n[...]\\n```'. Split on "\\n",
      take lines[1:-1], rejoin, then json.loads. Make sure your fence-stripping
      handles the case where there are exactly 3 lines correctly.
    narration: >
      The two most common LLM output failures: (1) the model adds a code fence
      despite the instruction not to; (2) the model adds extra text before or
      after the JSON. parse_taglines handles failure mode 1 with the fence
      stripping. For failure mode 2, you would extend parse_taglines with a
      regex search for the first '[' and last ']'. Today's implementation handles
      the common case.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "Tagline generation: system prompt constrains format; user prompt specifies n"
      - "parse_taglines: strip fences → json.loads → list[str]"
      - "Injection pattern: generate_prompt → llm_fn → parse → pick best"
      - "A/B test taglines on the landing page to find the highest converter"
      - "Next: launch email + social post generation"
    narration: >
      Taglines done. Next: the two most important launch-day pieces of content —
      the email to your waitlist and the social post that spreads the word.
""",

    """\
day: "098"
lesson: 4
title: "The Launch Email and Social Posts"
slides:
  - type: title
    heading: "Launch Day Content"
    subheading: "The email to your waitlist + the posts that spread the word"
    narration: >
      Launch day has two content jobs: the email to your waitlist (your most
      interested users) and the social posts (your bid for wider distribution).
      Both are generated deterministically from the product config — no LLM
      needed because the format is fixed. The only variables are the product
      name, the chosen tagline, and the URL.

  - type: concept
    label: "Launch email structure"
    heading: "The Launch Email Structure"
    body: >
      Seven lines. That's all a good launch email needs.
    bullets:
      - "Greeting: personalised if you have a name; generic if not"
      - "Hook: 'The wait is over. {product} is officially live.'"
      - "Tagline: the one-line reason to care"
      - "Early-access note: reward them for being on the waitlist"
      - "CTA: → the URL (simple arrow link, not a designed button)"
      - "Escape hatch: 'Questions? Just reply to this email.'"
      - "Sign-off: The {product} Team"
    narration: >
      The launch email is not a newsletter. It is a moment-of-truth communication
      that every person on your waitlist will open. Keep it short. Plain text
      outperforms HTML in deliverability and open rates for launch emails. The
      personalised greeting (using the subscriber's name from the waitlist) adds
      warmth without requiring dynamic template rendering. The arrow link (→)
      is more readable in plain text than a button, and it works in every email
      client.

  - type: concept
    label: "Platform-specific copy"
    heading: "Twitter vs LinkedIn vs Generic"
    body: >
      Same message, different format, different audience.
    bullets:
      - "Twitter: ≤280 chars; punchy; emoji for visibility; link at end"
      - "LinkedIn: longer; story-driven; hashtags for discovery; professional tone"
      - "Hacker News: no marketing speak; technical; 'Ask HN' or 'Show HN'"
      - "generic: one-liner for bots, RSS, SMS — just name + tagline + url"
      - "Truncate Twitter posts to 277 + '...' if the content exceeds 280 chars"
    narration: >
      Platform fit matters. A LinkedIn post with emoji and casual language gets
      dismissed by LinkedIn's professional audience. A long formal post on Twitter
      gets ignored because nobody reads past 280 chars. generate_social_post
      takes the platform as a parameter and formats accordingly. In production
      you would add Reddit, Product Hunt, and IndieHackers variants — each with
      their own community norms.

  - type: exercise
    heading: "Exercise 4 — generate_launch_email and generate_social_post"
    prompt: >
      generate_launch_email(product_name, tagline, cta_url, recipient_name="")
      returns {"subject": ..., "body": ...}. Subject must contain product_name.
      Body: greeting → product live → tagline → early access → URL → sign-off.
      generate_social_post(product, tagline, url, platform="twitter") returns str.
      Twitter ≤280 chars; LinkedIn has hashtags; other → one-liner.
    hint: >
      Twitter: build the post first, then truncate: post[:277]+"..." if len>280.
      LinkedIn: include "#AI", "#ProductLaunch", "#BuildInPublic" — check 5
      tests for at least one of these. generic: f"{name}: {tagline} — {url}".
    narration: >
      The generate_launch_email function is called once per waitlist subscriber.
      If you have 200 subscribers, you call it 200 times with different
      recipient_name values. In production you would feed the output into a
      transactional email service (Postmark, Resend, SendGrid) via their API.
      The Waitlist.export_csv() method from Exercise 2 gives you the CSV to
      import into those services if you prefer a no-code email tool.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "Launch email: 7-line structure — greeting, hook, tagline, CTA, sign-off"
      - "generate_launch_email: personalised or generic greeting from recipient_name"
      - "Twitter: ≤280 chars, truncate at 277; LinkedIn: hashtags, professional"
      - "generate_social_post: platform-specific formatting in one function"
      - "Next: Exercise 5 — full launch pipeline end-to-end"
    narration: >
      All four tools are ready. Exercise 5 chains them together into a complete
      launch day pipeline.
""",

    """\
day: "098"
lesson: 5
title: "The Complete Launch Pipeline"
slides:
  - type: title
    heading: "Launch Day"
    subheading: "Page → waitlist → copy → distribution"
    narration: >
      Lesson 5 shows the complete launch pipeline: generate the landing page,
      populate a waitlist with test subscribers, generate taglines from a mock
      LLM response, build launch emails for each subscriber, and produce the
      social posts. After Exercise 5, you have every artifact needed to launch
      the AI trading bot as a real product.

  - type: concept
    label: "Launch sequence"
    heading: "The Launch Day Sequence"
    body: >
      Seven steps from 'ready to ship' to 'users arriving'.
    bullets:
      - "1. Publish landing page (Vercel, Netlify, GitHub Pages — free)"
      - "2. Post to Twitter/LinkedIn/HN — the first traffic spike"
      - "3. Send launch email to waitlist — your highest-intent audience"
      - "4. Submit to Product Hunt (launches at midnight PT)"
      - "5. Monitor analytics + email opens for the first 24 hours"
      - "6. Respond to every comment and question personally"
      - "7. Iterate: update landing page copy based on what's converting"
    narration: >
      The launch is not a one-time event — it is a 48-hour sprint followed by
      a week of follow-up. The first 24 hours are about distribution: getting
      the page in front of as many interested people as possible. The second
      24 hours are about conversion: understanding who clicked, who signed up,
      and why. After day two, you ship the first real user feedback into the
      product. The tools you built today handle steps 1, 2, and 3 programmatically.

  - type: concept
    label: "Metrics to watch"
    heading: "Three Metrics That Matter on Launch Day"
    body: >
      Visitor → subscriber → user. Three conversion steps.
    bullets:
      - "Landing page conversion: subscribers / visitors (target ≥ 10%)"
      - "Email open rate: opens / sent (target ≥ 40% for launch email)"
      - "Click-through rate: CTA clicks / opens (target ≥ 20%)"
      - "These compound: 1000 visitors × 10% × 40% × 20% = 8 activated users"
      - "If any step is low: improve the copy or the offer, not the next step"
    narration: >
      The funnel math is humbling. Even with good conversion rates at every
      step, the absolute numbers are small at launch. This is why the waitlist
      matters: it trades immediate low-intent visitors for higher-intent future
      users. A launch email to 200 waitlist subscribers will outperform
      a cold email to 2000 strangers by a large margin. Invest in the quality
      of each stage of the funnel before trying to increase volume.

  - type: exercise
    heading: "Exercise 5 — Full Launch Pipeline"
    prompt: >
      Chain all four components: generate_landing_page (valid HTML with product
      name), Waitlist (3 subscribers), parse_taglines from fenced mock LLM output,
      generate_launch_email for each subscriber, generate_social_post for
      twitter + linkedin.
    hint: >
      Check 3: the mock LLM response is fenced (```json...```). parse_taglines
      must strip the fence and return a list of 3 non-empty strings. Check 5:
      assert len(tw) <= 280 and ("#AI" in li or "#ProductLaunch" in li).
    narration: >
      This pipeline is what you would run on launch morning: generate the page,
      confirm the waitlist is ready, pick the best tagline, send the launch
      emails, schedule the social posts. The code is fast — the entire pipeline
      runs in milliseconds because all four components are pure Python with no
      network calls.

  - type: summary
    heading: "Day 98 Complete"
    bullets:
      - "generate_landing_page: complete HTML5 from LandingPageConfig"
      - "Waitlist: file-backed; add/count/list_emails/export_csv"
      - "generate_tagline_prompt + parse_taglines: LLM tagline variants"
      - "generate_launch_email: personalised plain-text launch email"
      - "generate_social_post: Twitter (≤280) + LinkedIn (hashtags) + generic"
      - "Next: Day 99 — Portfolio & Personal Brand"
    narration: >
      Day 98 is complete. The product is now packaged (Day 97), documented,
      priced, access-controlled, and ready to launch. Day 99 builds the
      portfolio site that showcases all 100 days of work to potential employers,
      clients, and collaborators. One day after that: the final capstone.
""",
]

# ══════════════════════════════════════════════════════════════════════════════
# Project + solution
# ══════════════════════════════════════════════════════════════════════════════

_FULL_P = _P_BASE + _P_LP + _P_WL + _P_COPY

PROJECT_NB = _nb([
    _md(f"# Day {DAY} Project — Trading Bot Launch Pipeline\n\n"
        "Run the complete launch pipeline for the AI trading bot: generate the "
        "landing page, populate a test waitlist, generate taglines from a mock "
        "LLM response, and produce launch emails + social posts for all subscribers."),
    _code(_FULL_P),
    _code("""\
import os, tempfile

# Config
with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
    wl_path = f.name
try: os.unlink(wl_path)
except: pass

PRODUCT = "AI Trading Bot"
TAGLINE = "Automate your strategy with AI-driven signals."
URL     = "https://aitradingbot.io"

# 1. Landing page
html = generate_landing_page(_CFG)

# 2. Waitlist
wl = Waitlist(wl_path)
for addr, name in [("alice@test.com","Alice"),("bob@test.com","Bob"),("carol@test.com","Carol")]:
    wl.add(addr, name=name)

# 3. Taglines (mock LLM)
mock_resp = '```json\\n["Trade smarter with AI.", "Your edge, automated.", "Signals, not noise."]\\n```'
taglines = parse_taglines(mock_resp)
chosen = taglines[0]

# 4. Launch emails
emails = [generate_launch_email(PRODUCT, TAGLINE, URL, e.name) for e in wl._entries]

# 5. Social posts
tw = generate_social_post(PRODUCT, TAGLINE, URL, platform="twitter")
li = generate_social_post(PRODUCT, TAGLINE, URL, platform="linkedin")

print(f"Landing page: {len(html)} chars HTML")
print(f"Waitlist: {wl.count()} subscribers")
print(f"Taglines: {taglines}")
print(f"Twitter ({len(tw)} chars):\\n{tw}")
print(f"\\nLinkedIn:\\n{li[:200]}...")

try: os.unlink(wl_path)
except: pass
"""),
])

SOLUTION_NB = _nb([
    _md(f"# Day {DAY} Solution — Trading Bot Launch Pipeline"),
    _code(_FULL_P),
    _code("""\
import os, tempfile

with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
    wl_path = f.name
try: os.unlink(wl_path)
except: pass

PRODUCT = "AI Trading Bot"
TAGLINE = "Automate your strategy with AI-driven signals."
URL     = "https://aitradingbot.io"

html = generate_landing_page(_CFG)
assert html.startswith("<!DOCTYPE html")
assert PRODUCT in html
for feat in _CFG.features:
    assert feat in html

wl = Waitlist(wl_path)
for addr, name in [("alice@test.com","Alice"),("bob@test.com","Bob"),("carol@test.com","Carol")]:
    wl.add(addr, name=name)
assert wl.count() == 3
assert "alice@test.com" in wl.list_emails()

mock_resp = '```json\\n["Trade smarter with AI.", "Your edge, automated.", "Signals, not noise."]\\n```'
taglines = parse_taglines(mock_resp)
assert len(taglines) == 3

for entry in wl._entries:
    em = generate_launch_email(PRODUCT, TAGLINE, URL, entry.name)
    assert "subject" in em and "body" in em
    assert PRODUCT in em["subject"]

tw = generate_social_post(PRODUCT, TAGLINE, URL, platform="twitter")
li = generate_social_post(PRODUCT, TAGLINE, URL, platform="linkedin")
assert len(tw) <= 280
assert "#AI" in li or "#ProductLaunch" in li

print(f"HTML: {len(html)} chars | Subscribers: {wl.count()} | Taglines: {taglines}")
print(f"Twitter ({len(tw)} chars): {tw}")
print("\\nSolution smoke-test passed.")

try: os.unlink(wl_path)
except: pass
"""),
])

# ══════════════════════════════════════════════════════════════════════════════
# Gate
# ══════════════════════════════════════════════════════════════════════════════

GATE_PY = f"""\
import importlib.util, sys, json, tempfile, os, pathlib

spec = importlib.util.spec_from_file_location(
    "{SLUG}", r"{DIR / (SLUG + '.py')}"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

cfg = mod.LandingPageConfig(
    product_name  = "Test Product",
    tagline       = "The best product ever made.",
    description   = "A description of the product.",
    features      = ["Feature One", "Feature Two", "Feature Three"],
    cta_text      = "Sign Up Free",
    cta_url       = "#waitlist",
    primary_color = "#e11d48",
)

# generate_landing_page
html = mod.generate_landing_page(cfg)
assert isinstance(html, str) and len(html) > 200
assert html.strip().startswith("<!DOCTYPE html"), f"bad start: {{html[:30]!r}}"
assert "<title>Test Product</title>" in html
assert "<h1>Test Product</h1>"       in html
assert "The best product ever made." in html
assert "Feature One"                 in html
assert "Feature Two"                 in html
assert "Sign Up Free"                in html
assert "#e11d48"                     in html
assert 'id="waitlist"' in html or "id='waitlist'" in html

# custom primary_color propagates
cfg2 = mod.LandingPageConfig("P","T","D",["F1"], primary_color="#abc123")
html2 = mod.generate_landing_page(cfg2)
assert "#abc123" in html2

# Waitlist
with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
    wl_path = f.name
try: os.unlink(wl_path)
except FileNotFoundError: pass

wl = mod.Waitlist(wl_path)
assert wl.count() == 0

r1 = wl.add("Alice@TEST.com", name="Alice")
assert r1 is True
assert wl.count() == 1
assert "alice@test.com" in wl.list_emails()

r2 = wl.add("bob@test.com")
assert r2 is True and wl.count() == 2

r3 = wl.add("alice@test.com")  # duplicate
assert r3 is False and wl.count() == 2

try:
    wl.add("notanemail")
    assert False, "should raise ValueError for bad email"
except ValueError:
    pass

# persistence
wl2 = mod.Waitlist(wl_path)
assert wl2.count() == 2
assert "alice@test.com" in wl2.list_emails()

# CSV
csv_out = wl2.export_csv()
assert "email" in csv_out.split("\\n")[0]
assert "alice@test.com" in csv_out

try: os.unlink(wl_path)
except: pass

# generate_tagline_prompt
msgs = mod.generate_tagline_prompt("TestBot", "A bot for testing.", n=4)
assert isinstance(msgs, list) and len(msgs) == 2
assert msgs[0]["role"] == "system"
assert msgs[1]["role"] == "user"
assert "TestBot"         in msgs[1]["content"]
assert "A bot for testing" in msgs[1]["content"]
assert "4"               in msgs[1]["content"]
assert "JSON"            in msgs[0]["content"]

# parse_taglines
tags1 = mod.parse_taglines('["Tag A", "Tag B"]')
assert tags1 == ["Tag A", "Tag B"]

tags2 = mod.parse_taglines('```json\\n["X","Y","Z"]\\n```')
assert tags2 == ["X","Y","Z"]

# generate_launch_email
em = mod.generate_launch_email("MyBot", "Automate everything.", "https://mybot.io")
assert "subject" in em and "body" in em
assert "MyBot"           in em["subject"]
assert "MyBot"           in em["body"]
assert "https://mybot.io" in em["body"]

em2 = mod.generate_launch_email("MyBot", "T.", "U", recipient_name="Carol")
assert "Carol" in em2["body"]
assert "Carol" not in em["body"]   # generic should not have Carol

# generate_social_post
tw = mod.generate_social_post("MyBot", "Automate.", "http://x.com", platform="twitter")
assert isinstance(tw, str) and len(tw) <= 280
assert "MyBot" in tw

li = mod.generate_social_post("MyBot", "Automate.", "http://x.com", platform="linkedin")
assert "MyBot" in li
assert "#AI" in li or "#ProductLaunch" in li or "#BuildInPublic" in li

gen = mod.generate_social_post("MyBot", "T.", "http://x.com", platform="other")
assert "MyBot" in gen and "T." in gen and "http://x.com" in gen

# long twitter post truncation
tw_long = mod.generate_social_post("MyBot", "A"*300, "http://x.com", platform="twitter")
assert len(tw_long) <= 280

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
