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
    feature_items = "\n".join(f"      <li>{f}</li>" for f in cfg.features)
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '  <meta charset="UTF-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f"  <title>{cfg.product_name}</title>\n"
        "  <style>\n"
        "    body { font-family: system-ui, sans-serif; margin: 0; padding: 0; }\n"
        f"    .hero {{ background: {cfg.primary_color}; color: white; padding: 80px 40px; text-align: center; }}\n"
        "    h1 { font-size: 3rem; margin: 0 0 16px; }\n"
        "    .tagline { font-size: 1.5rem; opacity: 0.9; margin-bottom: 32px; }\n"
        f"    .cta {{ background: white; color: {cfg.primary_color}; padding: 16px 32px; "
        "border-radius: 8px; font-size: 1.1rem; text-decoration: none; font-weight: bold; }\n"
        "    .features { padding: 60px 40px; max-width: 800px; margin: 0 auto; }\n"
        "    .features ul { font-size: 1.1rem; line-height: 2; }\n"
        "    #waitlist { padding: 60px 40px; background: #f8fafc; text-align: center; }\n"
        "    input { padding: 12px; font-size: 1rem; width: 300px; "
        "border: 1px solid #ccc; border-radius: 4px; }\n"
        f"    button {{ padding: 12px 24px; font-size: 1rem; background: {cfg.primary_color}; "
        "color: white; border: none; border-radius: 4px; cursor: pointer; }\n"
        "  </style>\n"
        "</head>\n"
        "<body>\n"
        '  <section class="hero">\n'
        f"    <h1>{cfg.product_name}</h1>\n"
        f'    <p class="tagline">{cfg.tagline}</p>\n'
        f'    <a class="cta" href="{cfg.cta_url}">{cfg.cta_text}</a>\n'
        "  </section>\n"
        '  <section class="features">\n'
        "    <h2>Features</h2>\n"
        "    <ul>\n"
        f"{feature_items}\n"
        "    </ul>\n"
        f"    <p>{cfg.description}</p>\n"
        "  </section>\n"
        '  <section id="waitlist">\n'
        "    <h2>Join the Waitlist</h2>\n"
        "    <p>Be the first to know when we launch.</p>\n"
        '    <input type="email" placeholder="your@email.com" />\n'
        f"    <button type=\"button\">{cfg.cta_text}</button>\n"
        "  </section>\n"
        "</body>\n"
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
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if len(lines) > 2 else text
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
        "subject": f"{product_name} is live — you're in!",
        "body": (
            f"{greeting}\n\n"
            f"The wait is over. {product_name} is officially live.\n\n"
            f"{tagline}\n\n"
            f"As an early member of our waitlist, you get first access.\n\n"
            f"\u2192 {cta_url}\n\n"
            f"Questions? Just reply to this email.\n\n"
            f"\u2014 The {product_name} Team"
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
        post = f"\U0001f680 {product_name} is live!\n\n{tagline}\n\n{cta_url}"
        if len(post) > 280:
            post = post[:277] + "..."
        return post
    if platform == "linkedin":
        return (
            f"Excited to announce that {product_name} is officially live! \U0001f389\n\n"
            f"{tagline}\n\n"
            f"We built this to solve a real problem and we can't wait to see "
            f"what you do with it.\n\n"
            f"Try it here: {cta_url}\n\n"
            f"#AI #ProductLaunch #BuildInPublic"
        )
    return f"{product_name}: {tagline} — {cta_url}"
