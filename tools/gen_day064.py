#!/usr/bin/env python3
"""gen_day064.py — generate Day 064: Capstone Build I notebooks."""
from pathlib import Path
import json

ROOT    = Path(__file__).parent.parent
DAY     = "064"
SECTION = "04_real_apps"
OUT     = ROOT / SECTION / f"day_{DAY}"

(OUT / "exercises").mkdir(parents=True, exist_ok=True)
(OUT / "lessons").mkdir(parents=True, exist_ok=True)
(OUT / "project" / "solution").mkdir(parents=True, exist_ok=True)

# ── deliverable source ─────────────────────────────────────────────────────────
_APP_SRC = '''\
"""writing_assistant.py — Day 064: AI Writing Assistant MVP.

Setup:
  pip install fastapi "uvicorn[standard]" ollama
  ollama pull llama3.2

Run:
  uvicorn writing_assistant:app --reload
Docs:
  http://localhost:8000/docs
"""
import os
import re
import secrets
import time
from datetime import datetime

import ollama
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

APP_VER = "1.0.0"
MODEL   = os.environ.get("MODEL", "llama3.2")

# ── plan configuration ────────────────────────────────────────────────────────

DAILY_LIMITS = {"free": 5, "pro": 500, "enterprise": float("inf")}

FEATURE_MATRIX = {
    "free": {"basic_generate", "view_history"},
    "pro":  {"basic_generate", "view_history", "improve_text", "export"},
}

TEMPLATES = {
    "email":     "Write a {tone} email to {recipient} about {topic}.",
    "tweet":     "Write a {tone} tweet about {topic} in under 280 characters.",
    "summary":   "Write a concise {length}-sentence summary of: {content}",
    "blog_intro": "Write an engaging blog introduction about {topic} for a {audience} audience.",
}


def check_feature_access(plan: str, feature: str) -> bool:
    return feature in FEATURE_MATRIX.get(plan, set())


def check_rate_limit(usage_count: int, plan: str) -> tuple[bool, str]:
    limit = DAILY_LIMITS.get(plan, 0)
    if usage_count >= limit:
        return False, f"Daily limit reached for {plan!r} plan ({usage_count}/{int(limit)})"
    return True, ""


# ── content store ─────────────────────────────────────────────────────────────

class ContentStore:
    def __init__(self):
        self._store: dict = {}

    def add(self, user_id: str, prompt: str, content: str) -> str:
        cid = secrets.token_urlsafe(8)
        self._store[cid] = {
            "content_id": cid,
            "user_id":    user_id,
            "prompt":     prompt,
            "content":    content,
            "created_at": datetime.utcnow().isoformat() + "Z",
        }
        return cid

    def get(self, content_id: str) -> dict | None:
        return self._store.get(content_id)

    def list_user(self, user_id: str) -> list[dict]:
        return [v for v in self._store.values() if v["user_id"] == user_id]

    def count(self, user_id: str) -> int:
        return sum(1 for v in self._store.values() if v["user_id"] == user_id)


# ── template engine ───────────────────────────────────────────────────────────

def render_template(template_str: str, **vars) -> str:
    required = set(re.findall(r\'\\{(\\w+)\\}\', template_str))
    missing  = required - set(vars.keys())
    if missing:
        raise ValueError(f"Missing template variables: {missing}")
    result = template_str
    for key, value in vars.items():
        result = result.replace(f"{{{key}}}", str(value))
    return result


# ── FastAPI app ───────────────────────────────────────────────────────────────

def build_api(process_fn=None, initial_plan: str = "free",
              initial_usage: int = 0) -> FastAPI:
    app   = FastAPI(title="AI Writing Assistant", version=APP_VER)
    store = ContentStore()
    state = {"plan": initial_plan, "usage": initial_usage}

    class GenerateRequest(BaseModel):
        prompt:  str = Field(min_length=1)
        user_id: str = Field(min_length=1)

    class TemplateRequest(BaseModel):
        template: str = Field(min_length=1)
        vars:     dict = {}
        user_id:  str = Field(min_length=1)

    class ImproveRequest(BaseModel):
        text:    str = Field(min_length=1)
        user_id: str = Field(min_length=1)

    @app.get("/health")
    def health():
        return {"status": "ok", "timestamp": datetime.utcnow().isoformat() + "Z",
                "version": APP_VER}

    @app.get("/plan")
    def get_plan():
        lim = DAILY_LIMITS.get(state["plan"], 0)
        return {"plan": state["plan"], "usage_today": state["usage"],
                "limit": lim if lim != float("inf") else -1}

    @app.get("/templates")
    def list_templates():
        return {"templates": list(TEMPLATES.keys())}

    @app.post("/generate")
    def generate(req: GenerateRequest):
        ok, reason = check_rate_limit(state["usage"], state["plan"])
        if not ok:
            raise HTTPException(429, reason)
        answer = (process_fn(req.prompt) if process_fn
                  else ollama.chat(model=MODEL,
                                   messages=[{"role": "user",
                                              "content": req.prompt}])
                  ["message"]["content"])
        state["usage"] += 1
        cid = store.add(req.user_id, req.prompt, answer)
        return {"content_id": cid, "content": answer, "user_id": req.user_id}

    @app.post("/generate/template")
    def generate_from_template(req: TemplateRequest):
        ok, reason = check_rate_limit(state["usage"], state["plan"])
        if not ok:
            raise HTTPException(429, reason)
        tmpl = TEMPLATES.get(req.template)
        if tmpl is None:
            raise HTTPException(400, f"Unknown template: {req.template!r}")
        try:
            prompt = render_template(tmpl, **req.vars)
        except ValueError as e:
            raise HTTPException(400, str(e))
        answer = (process_fn(prompt) if process_fn
                  else ollama.chat(model=MODEL,
                                   messages=[{"role": "user",
                                              "content": prompt}])
                  ["message"]["content"])
        state["usage"] += 1
        cid = store.add(req.user_id, prompt, answer)
        return {"content_id": cid, "content": answer,
                "template": req.template, "user_id": req.user_id}

    @app.post("/improve")
    def improve(req: ImproveRequest):
        if not check_feature_access(state["plan"], "improve_text"):
            raise HTTPException(403, "improve_text requires a pro plan")
        ok, reason = check_rate_limit(state["usage"], state["plan"])
        if not ok:
            raise HTTPException(429, reason)
        prompt = f"Improve this text for clarity and style:\\n\\n{req.text}"
        answer = (process_fn(prompt) if process_fn
                  else ollama.chat(model=MODEL,
                                   messages=[{"role": "user",
                                              "content": prompt}])
                  ["message"]["content"])
        state["usage"] += 1
        cid = store.add(req.user_id, prompt, answer)
        return {"content_id": cid, "original": req.text,
                "improved": answer, "user_id": req.user_id}

    @app.get("/history/{user_id}")
    def get_history(user_id: str):
        items = store.list_user(user_id)
        return {"user_id": user_id, "count": len(items), "items": items}

    @app.get("/content/{content_id}")
    def get_content(content_id: str):
        item = store.get(content_id)
        if item is None:
            raise HTTPException(404, f"Content {content_id!r} not found")
        return item

    return app


app = build_api()

if __name__ == "__main__":
    import uvicorn
    PORT = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=PORT)
'''

_PROCFILE     = "web: uvicorn writing_assistant:app --host 0.0.0.0 --port $PORT\n"
_REQUIREMENTS = "fastapi\nhttpx\nollama\nuvicorn[standard]\n"

# ── notebook helpers ───────────────────────────────────────────────────────────
def nb(cells):
    return {
        "nbformat": 4, "nbformat_minor": 5,
        "metadata": {"kernelspec": {"display_name": "Python 3",
                                    "language": "python",
                                    "name": "python3"}},
        "cells": cells,
    }

def md(src):
    return {"cell_type": "markdown", "metadata": {}, "source": src}

def code(src):
    return {"cell_type": "code", "metadata": {}, "source": src,
            "outputs": [], "execution_count": None}

def save(path, notebook):
    Path(path).write_text(json.dumps(notebook, indent=1))

# ══════════════════════════════════════════════════════════════════════════════
# EXERCISE 1 — plan_mvp
# ══════════════════════════════════════════════════════════════════════════════
_EX1_STUB = """\
def plan_mvp(features: list[str], free_count: int,
             pro_count: int) -> dict:
    \"\"\"Split a list of feature ideas into plan tiers.

    Returns:
        {
          'free_tier': list of first free_count features,
          'pro_tier':  next pro_count features (after free tier),
          'backlog':   remaining features,
          'summary':   '{n} free / {m} pro / {k} backlog',
        }

    If the feature list is shorter than free_count, free_tier is
    all features and pro_tier + backlog are empty.
    \"\"\"
    # TODO: slice the list into three parts, build the summary string
    raise NotImplementedError
"""

_EX1_SOLUTION = """\
def plan_mvp(features: list[str], free_count: int,
             pro_count: int) -> dict:
    free    = features[:free_count]
    pro     = features[free_count: free_count + pro_count]
    backlog = features[free_count + pro_count:]
    return {
        "free_tier": free,
        "pro_tier":  pro,
        "backlog":   backlog,
        "summary":   f"{len(free)} free / {len(pro)} pro / {len(backlog)} backlog",
    }
"""

_EX1_CHECKS = """\
score, total = 0, 5
try:
    ALL = ["basic_chat", "view_history", "advanced_chat", "export",
           "api_access", "white_label", "priority_support", "custom_domain"]

    plan = plan_mvp(ALL, free_count=2, pro_count=3)
    assert plan["free_tier"] == ["basic_chat", "view_history"]
    score += 1; print("\\u2705 free_tier = first free_count items")

    assert plan["pro_tier"] == ["advanced_chat", "export", "api_access"]
    score += 1; print("\\u2705 pro_tier = next pro_count items")

    assert plan["backlog"] == ["white_label", "priority_support", "custom_domain"]
    score += 1; print("\\u2705 backlog = remaining items")

    assert "2 free" in plan["summary"] and "3 pro" in plan["summary"]
    assert "3 backlog" in plan["summary"]
    score += 1; print("\\u2705 summary string contains counts")

    # fewer features than free_count
    short = plan_mvp(["a", "b"], free_count=5, pro_count=3)
    assert short["free_tier"] == ["a", "b"]
    assert short["pro_tier"] == [] and short["backlog"] == []
    score += 1; print("\\u2705 short list: all go to free_tier, rest empty")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX1 = nb([
    md("# Day 064 — Exercise 1: MVP Scoping\n\n"
       "**Scope creep** is the #1 reason MVPs never ship. The fix: write down "
       "every feature idea, then ruthlessly slot them into tiers:\n\n"
       "| Tier | Rule | Goal |\n"
       "|------|------|------|\n"
       "| Free | First N features | Attract users, demonstrate value |\n"
       "| Pro | Next M features | Justify upgrade |\n"
       "| Backlog | Everything else | Build *after* first paying customer |\n\n"
       "A good MVP has 2-3 free features and 2-3 pro features. Everything else "
       "waits until the product is validated."),
    md("## Task\n\n"
       "Implement `plan_mvp(features, free_count, pro_count) -> dict`:\n\n"
       "- `free_tier`: first `free_count` features from the list\n"
       "- `pro_tier`: the next `pro_count` features\n"
       "- `backlog`: all remaining features\n"
       "- `summary`: `'{n} free / {m} pro / {k} backlog'`\n"
       "- If fewer features than `free_count`: all go to `free_tier`, others empty"),
    md("## Your Implementation"),
    code(_EX1_STUB),
    code(_EX1_SOLUTION),
    md("## Automated checks"),
    code(_EX1_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX1_SOLUTION + "```\n\n"
       "**Three list slices**: `[:free_count]`, `[free_count:free_count+pro_count]`, "
       "`[free_count+pro_count:]`. Slicing past the end of a list returns an "
       "empty list — no bounds checks needed. The summary string is an f-string "
       "using `len()` of each slice.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_01.ipynb", EX1)

# ══════════════════════════════════════════════════════════════════════════════
# EXERCISE 2 — ContentStore
# ══════════════════════════════════════════════════════════════════════════════
_EX2_GIVEN = """\
import secrets
from datetime import datetime

# secrets.token_urlsafe(8) generates an 11-char URL-safe random ID
# Use it for content_id generation
"""

_EX2_STUB = """\
class ContentStore:
    \"\"\"In-memory store for generated content items.

    Each item: {content_id, user_id, prompt, content, created_at}
    created_at: ISO-8601 UTC string  (datetime.utcnow().isoformat() + 'Z')
    \"\"\"

    def __init__(self):
        self._store: dict = {}   # content_id -> item dict

    def add(self, user_id: str, prompt: str, content: str) -> str:
        \"\"\"Store item and return its content_id.\"\"\"
        # TODO: generate content_id, build item dict, store, return id
        raise NotImplementedError

    def get(self, content_id: str) -> dict | None:
        \"\"\"Return item dict or None if not found.\"\"\"
        # TODO
        raise NotImplementedError

    def list_user(self, user_id: str) -> list[dict]:
        \"\"\"Return all items for the given user_id.\"\"\"
        # TODO
        raise NotImplementedError

    def count(self, user_id: str) -> int:
        \"\"\"Return number of items for the given user_id.\"\"\"
        # TODO
        raise NotImplementedError
"""

_EX2_SOLUTION = """\
class ContentStore:
    def __init__(self):
        self._store: dict = {}

    def add(self, user_id: str, prompt: str, content: str) -> str:
        cid = secrets.token_urlsafe(8)
        self._store[cid] = {
            "content_id": cid,
            "user_id":    user_id,
            "prompt":     prompt,
            "content":    content,
            "created_at": datetime.utcnow().isoformat() + "Z",
        }
        return cid

    def get(self, content_id: str) -> dict | None:
        return self._store.get(content_id)

    def list_user(self, user_id: str) -> list[dict]:
        return [v for v in self._store.values() if v["user_id"] == user_id]

    def count(self, user_id: str) -> int:
        return sum(1 for v in self._store.values() if v["user_id"] == user_id)
"""

_EX2_CHECKS = """\
score, total = 0, 6
try:
    store = ContentStore()

    # add returns a content_id string
    cid = store.add("alice", "prompt1", "content1")
    assert isinstance(cid, str) and len(cid) > 0
    score += 1; print("\\u2705 add returns a non-empty content_id string")

    # get returns the item
    item = store.get(cid)
    assert item is not None
    assert item["user_id"] == "alice"
    assert item["prompt"] == "prompt1"
    assert item["content"] == "content1"
    assert "content_id" in item and "created_at" in item
    score += 1; print("\\u2705 get returns correct item with all fields")

    # get returns None for unknown id
    assert store.get("nonexistent") is None
    score += 1; print("\\u2705 get returns None for unknown content_id")

    # add more items for two users
    store.add("alice", "p2", "c2")
    store.add("bob",   "p3", "c3")
    store.add("alice", "p4", "c4")

    # list_user returns only that user's items
    alice_items = store.list_user("alice")
    assert len(alice_items) == 3  # alice added 3 items
    assert all(i["user_id"] == "alice" for i in alice_items)
    score += 1; print("\\u2705 list_user returns only the user's items")

    # count
    assert store.count("alice") == 3
    assert store.count("bob")   == 1
    assert store.count("carol") == 0
    score += 1; print("\\u2705 count returns correct per-user count")

    # IDs are unique
    ids = [store.add("x", "p", "c") for _ in range(10)]
    assert len(set(ids)) == 10
    score += 1; print("\\u2705 content_ids are unique across 10 additions")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX2 = nb([
    md("# Day 064 — Exercise 2: ContentStore\n\n"
       "Every AI app that generates content needs a way to store and retrieve "
       "past generations. A `ContentStore` is the in-memory version — fast, "
       "simple, and good enough for an MVP. (Day 54 taught SQLAlchemy for "
       "durable storage; that's the upgrade path once the product is validated.)\n\n"
       "Each item has: `content_id` (random), `user_id`, `prompt`, `content`, "
       "`created_at` (ISO-8601 UTC)."),
    code(_EX2_GIVEN),
    md("## Task\n\n"
       "Implement `ContentStore` with four methods:\n\n"
       "- `add(user_id, prompt, content) -> str` — store item, return `content_id`\n"
       "- `get(content_id) -> dict | None` — retrieve by id\n"
       "- `list_user(user_id) -> list[dict]` — all items for one user\n"
       "- `count(user_id) -> int` — how many items a user has\n\n"
       "Use `secrets.token_urlsafe(8)` for unique IDs."),
    md("## Your Implementation"),
    code(_EX2_STUB),
    code(_EX2_SOLUTION),
    md("## Automated checks"),
    code(_EX2_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX2_SOLUTION + "```\n\n"
       "**Why `secrets.token_urlsafe(8)` not `uuid4()`?** Both produce unique IDs. "
       "`token_urlsafe` generates URL-safe base64 — shorter (11 chars vs 36) and "
       "safe to use directly in URLs. Use `secrets` not `random` — secrets uses "
       "the OS CSPRNG, random does not.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_02.ipynb", EX2)

# ══════════════════════════════════════════════════════════════════════════════
# EXERCISE 3 — render_template
# ══════════════════════════════════════════════════════════════════════════════
_EX3_GIVEN = """\
import re

TEMPLATES = {
    "email":      "Write a {tone} email to {recipient} about {topic}.",
    "tweet":      "Write a {tone} tweet about {topic} in under 280 characters.",
    "summary":    "Write a concise {length}-sentence summary of: {content}",
    "blog_intro": "Write a blog intro about {topic} for a {audience} audience.",
}
"""

_EX3_STUB = """\
def render_template(template_str: str, **vars) -> str:
    \"\"\"Replace {key} placeholders in template_str.

    - All {key} placeholders in template_str must have matching kwargs.
    - Missing variable -> raise ValueError('Missing template variables: {...}')
    - Extra kwargs are silently ignored.
    - Use re.findall(r'\\\\{(\\\\w+)\\\\}', template_str) to find required keys.
    \"\"\"
    # TODO: find required keys, check for missing, replace placeholders
    raise NotImplementedError
"""

_EX3_SOLUTION = """\
def render_template(template_str: str, **vars) -> str:
    required = set(re.findall(r'\\{(\\w+)\\}', template_str))
    missing  = required - set(vars.keys())
    if missing:
        raise ValueError(f"Missing template variables: {missing}")
    result = template_str
    for key, value in vars.items():
        result = result.replace(f"{{{key}}}", str(value))
    return result
"""

_EX3_CHECKS = """\
score, total = 0, 5
try:
    # basic substitution
    t = "Write a {tone} email to {recipient} about {topic}."
    r = render_template(t, tone="professional", recipient="Alice", topic="AI")
    assert r == "Write a professional email to Alice about AI."
    score += 1; print("\\u2705 basic substitution works")

    # all placeholders in TEMPLATES are replaceable
    tweet = render_template(TEMPLATES["tweet"], tone="casual", topic="Python")
    assert "casual" in tweet and "Python" in tweet
    score += 1; print("\\u2705 renders a TEMPLATES entry correctly")

    # missing variable → ValueError
    try:
        render_template(t, tone="casual")  # missing recipient, topic
        assert False, "should raise ValueError"
    except ValueError as e:
        assert "Missing" in str(e)
    score += 1; print("\\u2705 missing variable \\u2192 ValueError")

    # extra kwargs are ignored
    r2 = render_template("Hello {name}", name="World", extra="ignored")
    assert r2 == "Hello World"
    score += 1; print("\\u2705 extra kwargs are silently ignored")

    # numeric value is stringified
    r3 = render_template(TEMPLATES["summary"], length=3, content="some text")
    assert "3" in r3
    score += 1; print("\\u2705 numeric value is converted to string")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX3 = nb([
    md("# Day 064 — Exercise 3: Template Engine\n\n"
       "A template engine turns parameterised strings into full prompts. "
       "A product ships with a curated set of templates (email, tweet, blog "
       "intro, summary) and lets users fill in the blanks — much lower friction "
       "than writing a prompt from scratch.\n\n"
       "```\n"
       "TEMPLATES[\"email\"] = \"Write a {tone} email to {recipient} about {topic}.\"\n"
       "\n"
       "render_template(TEMPLATES[\"email\"], tone=\"professional\",\n"
       "                recipient=\"Alice\", topic=\"AI\")\n"
       "# → 'Write a professional email to Alice about AI.'\n"
       "```"),
    code(_EX3_GIVEN),
    md("## Task\n\n"
       "Implement `render_template(template_str, **vars) -> str`:\n\n"
       "1. Find all `{key}` placeholders with `re.findall(r'\\{(\\w+)\\}', ...)`\n"
       "2. Compute `missing = required_keys - set(vars.keys())`\n"
       "3. If missing: `raise ValueError(f'Missing template variables: {missing}')`\n"
       "4. Replace each `{key}` with `str(vars[key])`\n"
       "5. Return the rendered string (extra kwargs silently ignored)"),
    md("## Your Implementation"),
    code(_EX3_STUB),
    code(_EX3_SOLUTION),
    md("## Automated checks"),
    code(_EX3_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX3_SOLUTION + "```\n\n"
       "**Why not Python's `str.format_map`?** `'hello {name}'.format_map(vars)` "
       "raises `KeyError` on missing keys but doesn't tell you *which* keys are "
       "missing. Our version collects all missing keys at once and reports them "
       "all in one error — much friendlier for a UI that shows the user what "
       "fields to fill in.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_03.ipynb", EX3)

# ══════════════════════════════════════════════════════════════════════════════
# EXERCISE 4 — build_core_api
# ══════════════════════════════════════════════════════════════════════════════
_EX4_GIVEN = """\
import re, secrets
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from starlette.testclient import TestClient

DAILY_LIMITS = {"free": 5, "pro": 500, "enterprise": float("inf")}

TEMPLATES = {
    "email":      "Write a {tone} email to {recipient} about {topic}.",
    "tweet":      "Write a {tone} tweet about {topic} in under 280 characters.",
}

def check_rate_limit(usage_count, plan):
    limit = DAILY_LIMITS.get(plan, 0)
    if usage_count >= limit:
        return False, f"Daily limit reached for {plan!r} plan"
    return True, ""

def render_template(template_str, **vars):
    required = set(re.findall(r'\\{(\\w+)\\}', template_str))
    missing  = required - set(vars.keys())
    if missing:
        raise ValueError(f"Missing template variables: {missing}")
    result = template_str
    for k, v in vars.items():
        result = result.replace(f"{{{k}}}", str(v))
    return result

class ContentStore:
    def __init__(self):
        self._store = {}
    def add(self, user_id, prompt, content):
        cid = secrets.token_urlsafe(8)
        self._store[cid] = {"content_id": cid, "user_id": user_id,
                             "prompt": prompt, "content": content,
                             "created_at": datetime.utcnow().isoformat() + "Z"}
        return cid
    def get(self, content_id):
        return self._store.get(content_id)
    def list_user(self, user_id):
        return [v for v in self._store.values() if v["user_id"] == user_id]
    def count(self, user_id):
        return sum(1 for v in self._store.values() if v["user_id"] == user_id)
"""

_EX4_STUB = """\
def build_core_api(plan: str = "free", process_fn=None,
                   initial_usage: int = 0) -> FastAPI:
    \"\"\"FastAPI AI Writing Assistant.

    GET /health              → {status: 'ok', timestamp}
    GET /templates           → {templates: list[str]}
    POST /generate           {prompt, user_id}
                             → {content_id, content, user_id}
                             → 429 if rate limit exceeded
    POST /generate/template  {template, vars, user_id}
                             → {content_id, content, template, user_id}
                             → 400 unknown template or missing vars
                             → 429 rate limit
    GET /history/{user_id}   → {user_id, count, items}
    GET /content/{content_id} → item dict or 404

    process_fn: optional callable(prompt: str) -> str for testing.
    \"\"\"
    # TODO: create app and store, add all routes
    raise NotImplementedError
"""

_EX4_SOLUTION = """\
def build_core_api(plan: str = "free", process_fn=None,
                   initial_usage: int = 0) -> FastAPI:
    app   = FastAPI()
    store = ContentStore()
    state = {"plan": plan, "usage": initial_usage}

    class _Gen(BaseModel):
        prompt:  str = Field(min_length=1)
        user_id: str = Field(min_length=1)

    class _TGen(BaseModel):
        template: str = Field(min_length=1)
        vars:     dict = {}
        user_id:  str  = Field(min_length=1)

    @app.get("/health")
    def health():
        return {"status": "ok",
                "timestamp": datetime.utcnow().isoformat() + "Z"}

    @app.get("/templates")
    def list_templates():
        return {"templates": list(TEMPLATES.keys())}

    @app.post("/generate")
    def generate(req: _Gen):
        ok, reason = check_rate_limit(state["usage"], state["plan"])
        if not ok: raise HTTPException(429, reason)
        answer = process_fn(req.prompt) if process_fn else req.prompt.upper()
        state["usage"] += 1
        cid = store.add(req.user_id, req.prompt, answer)
        return {"content_id": cid, "content": answer, "user_id": req.user_id}

    @app.post("/generate/template")
    def gen_template(req: _TGen):
        ok, reason = check_rate_limit(state["usage"], state["plan"])
        if not ok: raise HTTPException(429, reason)
        tmpl = TEMPLATES.get(req.template)
        if tmpl is None: raise HTTPException(400, f"Unknown template: {req.template!r}")
        try:
            prompt = render_template(tmpl, **req.vars)
        except ValueError as e:
            raise HTTPException(400, str(e))
        answer = process_fn(prompt) if process_fn else prompt.upper()
        state["usage"] += 1
        cid = store.add(req.user_id, prompt, answer)
        return {"content_id": cid, "content": answer,
                "template": req.template, "user_id": req.user_id}

    @app.get("/history/{user_id}")
    def history(user_id: str):
        items = store.list_user(user_id)
        return {"user_id": user_id, "count": len(items), "items": items}

    @app.get("/content/{content_id}")
    def get_content(content_id: str):
        item = store.get(content_id)
        if item is None: raise HTTPException(404, f"Not found: {content_id!r}")
        return item

    return app
"""

_EX4_CHECKS = """\
score, total = 0, 7
try:
    app = build_core_api(plan="free", process_fn=str.upper)
    c   = TestClient(app, raise_server_exceptions=False)

    # GET /health
    r = c.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"
    score += 1; print("\\u2705 GET /health returns ok")

    # GET /templates
    rt = c.get("/templates")
    assert rt.status_code == 200
    tmpl_names = rt.json()["templates"]
    assert isinstance(tmpl_names, list) and len(tmpl_names) > 0
    score += 1; print("\\u2705 GET /templates returns list of template names")

    # POST /generate
    rg = c.post("/generate", json={"prompt": "hello", "user_id": "u1"})
    assert rg.status_code == 200, f"Got {rg.status_code}: {rg.text}"
    d  = rg.json()
    assert "content_id" in d and "content" in d and d["user_id"] == "u1"
    score += 1; print("\\u2705 POST /generate returns content_id + content")

    # GET /history
    rh = c.get("/history/u1")
    assert rh.status_code == 200 and rh.json()["count"] == 1
    score += 1; print("\\u2705 GET /history/{user_id} returns user items")

    # GET /content/{id}
    cid = d["content_id"]
    rc  = c.get(f"/content/{cid}")
    assert rc.status_code == 200 and rc.json()["content_id"] == cid
    score += 1; print("\\u2705 GET /content/{id} returns stored item")

    # 404 for unknown content_id
    r404 = c.get("/content/nonexistent_xyz")
    assert r404.status_code == 404
    score += 1; print("\\u2705 GET /content/unknown \\u2192 404")

    # 429 when rate limited
    at_limit = build_core_api(plan="free", process_fn=str.upper, initial_usage=5)
    cl = TestClient(at_limit, raise_server_exceptions=False)
    r429 = cl.post("/generate", json={"prompt": "x", "user_id": "u1"})
    assert r429.status_code == 429, f"Expected 429, got {r429.status_code}"
    score += 1; print("\\u2705 429 when free rate limit (5) is reached")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX4 = nb([
    md("# Day 064 — Exercise 4: Core API\n\n"
       "Wire the components from exercises 1-3 into a FastAPI app. This is the "
       "same `build_*_api` factory pattern used throughout Section 4:\n\n"
       "- `process_fn` injection for testability (no Ollama needed in tests)\n"
       "- `initial_usage` to test rate limits without N real requests\n"
       "- `ContentStore` as the in-process history backend\n"
       "- `render_template` for template-based generation"),
    code(_EX4_GIVEN),
    md("## Task\n\n"
       "Implement `build_core_api(plan='free', process_fn=None, initial_usage=0) -> FastAPI`:\n\n"
       "```\n"
       "GET  /health              → {status, timestamp}\n"
       "GET  /templates           → {templates: [...]}\n"
       "POST /generate            → {content_id, content, user_id} | 429\n"
       "POST /generate/template   → {content_id, content, template, user_id} | 400 | 429\n"
       "GET  /history/{user_id}   → {user_id, count, items}\n"
       "GET  /content/{content_id} → item | 404\n"
       "```"),
    md("## Your Implementation"),
    code(_EX4_STUB),
    code(_EX4_SOLUTION),
    md("## Automated checks"),
    code(_EX4_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX4_SOLUTION + "```\n\n"
       "**Architecture note**: `store` and `state` are closures inside the factory. "
       "Each `build_core_api()` call creates a fresh, independent app — perfect "
       "for tests (no shared state between test functions). In production, call "
       "`build_core_api()` once at module level and the same store persists for "
       "the lifetime of the server process.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_04.ipynb", EX4)

# ══════════════════════════════════════════════════════════════════════════════
# EXERCISE 5 — write_scaffold
# ══════════════════════════════════════════════════════════════════════════════
_SCAFFOLD_APP = '''\
"""app.py — AI Writing Assistant scaffold.

Replace each TODO with real code following the pattern from Day 064.

Run:  uvicorn app:app --reload
Docs: http://localhost:8000/docs
"""
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

APP_VER = "0.1.0"

# TODO: import ollama for production usage
# TODO: define DAILY_LIMITS, TEMPLATES, FEATURE_MATRIX

app = FastAPI(title="AI Writing Assistant", version=APP_VER)


@app.get("/health")
def health():
    return {"status": "ok", "version": APP_VER}


@app.get("/templates")
def list_templates():
    # TODO: return {"templates": list(TEMPLATES.keys())}
    return {"templates": []}


@app.post("/generate")
def generate():
    # TODO: add request model, rate-limit check, ollama call, store result
    raise HTTPException(501, "Not implemented")


@app.get("/history/{user_id}")
def history(user_id: str):
    # TODO: return stored items for this user
    return {"user_id": user_id, "count": 0, "items": []}
'''

_EX5_GIVEN = """\
from pathlib import Path
import tempfile

# Content to write into each scaffold file
SCAFFOLD_FILES = {
    "app.py":           \"\"\"<placeholder — see _SCAFFOLD_APP in generator>\"\"\",
    "requirements.txt": "fastapi\\nhttpx\\nollama\\nuvicorn[standard]\\n",
    "Procfile":         "web: uvicorn app:app --host 0.0.0.0 --port $PORT\\n",
}
"""

_EX5_STUB = """\
def write_scaffold(directory: str) -> list[str]:
    \"\"\"Write MVP scaffold files to directory.

    Creates these files inside `directory`:
        app.py           — FastAPI scaffold with TODO stubs
        requirements.txt — package list (fastapi, ollama, uvicorn[standard], httpx)
        Procfile         — 'web: uvicorn app:app --host 0.0.0.0 --port $PORT'

    Returns the list of filenames created (just names, not full paths).
    \"\"\"
    # TODO: create Path(directory), write each file, return list of names
    raise NotImplementedError
"""

_EX5_SOLUTION = """\
def write_scaffold(directory: str) -> list[str]:
    base  = Path(directory)
    base.mkdir(parents=True, exist_ok=True)
    files = list(SCAFFOLD_FILES.keys())
    for filename, content in SCAFFOLD_FILES.items():
        (base / filename).write_text(content, encoding="utf-8")
    return files
"""

_EX5_CHECKS = """\
score, total = 0, 5
try:
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        created = write_scaffold(tmpdir)

        # returns a list
        assert isinstance(created, list) and len(created) > 0
        score += 1; print("\\u2705 write_scaffold returns a non-empty list")

        # at least 3 files
        assert len(created) >= 3, f"Expected >=3 files, got {len(created)}"
        score += 1; print("\\u2705 at least 3 files created")

        # all files actually exist
        for fname in created:
            assert (Path(tmpdir) / fname).exists(), f"{fname} not created"
        score += 1; print("\\u2705 all listed filenames exist on disk")

        # requirements.txt contains fastapi
        req = next((f for f in created if "requirements" in f.lower()), None)
        assert req is not None, "requirements.txt not found in created list"
        req_text = (Path(tmpdir) / req).read_text()
        assert "fastapi" in req_text.lower()
        score += 1; print("\\u2705 requirements.txt contains 'fastapi'")

        # Procfile contains uvicorn
        proc = next((f for f in created if "procfile" in f.lower()), None)
        assert proc is not None, "Procfile not found in created list"
        proc_text = (Path(tmpdir) / proc).read_text()
        assert "uvicorn" in proc_text
        score += 1; print("\\u2705 Procfile contains 'uvicorn'")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

_EX5_GIVEN_REAL = f"""\
from pathlib import Path

_APP_CONTENT = {repr(_SCAFFOLD_APP)}

SCAFFOLD_FILES = {{
    "app.py":           _APP_CONTENT,
    "requirements.txt": "fastapi\\nhttpx\\nollama\\nuvicorn[standard]\\n",
    "Procfile":         "web: uvicorn app:app --host 0.0.0.0 --port $PORT\\n",
}}
"""

EX5 = nb([
    md("# Day 064 — Exercise 5: Write Scaffold\n\n"
       "The last step of Capstone Build I: write the MVP scaffold to disk. "
       "A scaffold is a working skeleton — the file structure a developer "
       "needs to start adding real logic. It should:\n\n"
       "- Run without errors (even with TODO stubs)\n"
       "- Include all dependency and deployment config\n"
       "- Be self-documenting (each TODO says exactly what to add)\n\n"
       "Generating it programmatically from a notebook uses the `repr()` "
       "source-embedding pattern from Day 051."),
    code(_EX5_GIVEN_REAL),
    md("## Task\n\n"
       "Implement `write_scaffold(directory: str) -> list[str]`:\n\n"
       "- Create `directory` if it doesn't exist (`mkdir(parents=True, exist_ok=True)`)\n"
       "- Write each file from `SCAFFOLD_FILES` into the directory\n"
       "- Return the list of filenames created (just names, not full paths)"),
    md("## Your Implementation"),
    code(_EX5_STUB),
    code(_EX5_SOLUTION),
    md("## Automated checks"),
    code(_EX5_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX5_SOLUTION + "```\n\n"
       "**Pattern**: `SCAFFOLD_FILES` is a dict of `{filename: content}`. "
       "Iterating it gives both at once. `exist_ok=True` makes the function "
       "idempotent — safe to call twice (overwrites files, doesn't error on "
       "existing directory). Return the keys (filenames), not the full paths — "
       "callers can reconstruct the full path themselves.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_05.ipynb", EX5)

# ══════════════════════════════════════════════════════════════════════════════
# PROJECT NOTEBOOK
# ══════════════════════════════════════════════════════════════════════════════
PROJECT = nb([
    md("# Day 064 — Project: Capstone Build I\n\n"
       "Build `writing_assistant.py` — the MVP of an AI Writing Assistant product."),
    md("## What You're Building\n\n"
       "`writing_assistant.py` — a FastAPI app that combines everything from "
       "Section 4:\n\n"
       "| Feature | From Day |\n"
       "|---------|----------|\n"
       "| FastAPI routes | 52 |\n"
       "| Pydantic request/response | 52 |\n"
       "| In-process state (ContentStore) | 54 |\n"
       "| Health endpoint | 57 |\n"
       "| Feature gating | 63 |\n"
       "| Rate limiting (429) | 63 |\n"
       "| Template engine | 064 |\n"
       "| Content history | 064 |\n\n"
       "## Endpoints\n\n"
       "```\n"
       "GET  /health                  — health check\n"
       "GET  /plan                    — plan, usage, limit\n"
       "GET  /templates               — list template names\n"
       "POST /generate                — free-text generation\n"
       "POST /generate/template       — template-based generation\n"
       "POST /improve                 — improve text (pro tier only)\n"
       "GET  /history/{user_id}       — content history\n"
       "GET  /content/{content_id}    — retrieve one item\n"
       "```\n\n"
       "## Run\n\n"
       "```bash\n"
       "uvicorn writing_assistant:app --reload\n"
       "# → http://localhost:8000/docs\n"
       "```\n\n"
       "Day 065 adds tests and deployment files for this app."),
])
save(OUT / "project" / "project.ipynb", PROJECT)

# ══════════════════════════════════════════════════════════════════════════════
# SOLUTION NOTEBOOK
# ══════════════════════════════════════════════════════════════════════════════
_SOL_CELL1 = (
    f"_APP_SRC = {repr(_APP_SRC)}\n"
    "from pathlib import Path\n"
    "Path('writing_assistant.py').write_text(_APP_SRC)\n"
    "print('writing_assistant.py written.')"
)

_SOL_CELL2 = """\
# inline tests — no Ollama needed
import re, secrets
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from starlette.testclient import TestClient

# ─── plan_mvp ────────────────────────────────────────────────────────────────
def plan_mvp(features, free_count, pro_count):
    free    = features[:free_count]
    pro     = features[free_count: free_count + pro_count]
    backlog = features[free_count + pro_count:]
    return {"free_tier": free, "pro_tier": pro, "backlog": backlog,
            "summary": f"{len(free)} free / {len(pro)} pro / {len(backlog)} backlog"}

plan = plan_mvp(["a","b","c","d","e","f"], free_count=2, pro_count=2)
assert plan["free_tier"]  == ["a","b"]
assert plan["pro_tier"]   == ["c","d"]
assert plan["backlog"]    == ["e","f"]
assert "2 free" in plan["summary"]
print("\\u2705 plan_mvp correct")

# ─── ContentStore ─────────────────────────────────────────────────────────────
class ContentStore:
    def __init__(self): self._store = {}
    def add(self, uid, p, c):
        cid = secrets.token_urlsafe(8)
        self._store[cid] = {"content_id": cid, "user_id": uid, "prompt": p,
                            "content": c, "created_at": datetime.utcnow().isoformat()+"Z"}
        return cid
    def get(self, cid): return self._store.get(cid)
    def list_user(self, uid): return [v for v in self._store.values() if v["user_id"]==uid]
    def count(self, uid): return sum(1 for v in self._store.values() if v["user_id"]==uid)

store = ContentStore()
cid   = store.add("u1", "prompt", "content")
assert store.get(cid)["content"] == "content"
assert store.count("u1") == 1
assert store.get("bad") is None
print("\\u2705 ContentStore correct")

# ─── render_template ──────────────────────────────────────────────────────────
def render_template(template_str, **vars):
    required = set(re.findall(r'\\{(\\w+)\\}', template_str))
    missing  = required - set(vars.keys())
    if missing: raise ValueError(f"Missing template variables: {missing}")
    result = template_str
    for k, v in vars.items(): result = result.replace(f"{{{k}}}", str(v))
    return result

assert render_template("Hello {name}!", name="World") == "Hello World!"
try:
    render_template("Hello {name}!")
    assert False
except ValueError:
    pass
print("\\u2705 render_template correct")

# ─── build_core_api ───────────────────────────────────────────────────────────
DAILY_LIMITS = {"free": 5, "pro": 500, "enterprise": float("inf")}
TEMPLATES    = {"email": "Write a {tone} email to {recipient} about {topic}.",
                "tweet": "Write a {tone} tweet about {topic}."}

def check_rate_limit(usage_count, plan):
    limit = DAILY_LIMITS.get(plan, 0)
    if usage_count >= limit: return False, f"Daily limit reached for {plan!r} plan"
    return True, ""

def build_core_api(plan="free", process_fn=None, initial_usage=0):
    app = FastAPI(); store = ContentStore(); state = {"plan": plan, "usage": initial_usage}
    class _G(BaseModel): prompt: str = Field(min_length=1); user_id: str = Field(min_length=1)
    class _T(BaseModel): template: str = Field(min_length=1); vars: dict = {}; user_id: str = Field(min_length=1)
    @app.get("/health")
    def health(): return {"status": "ok", "timestamp": datetime.utcnow().isoformat()+"Z"}
    @app.get("/templates")
    def tmpls(): return {"templates": list(TEMPLATES.keys())}
    @app.post("/generate")
    def gen(req: _G):
        ok, reason = check_rate_limit(state["usage"], state["plan"])
        if not ok: raise HTTPException(429, reason)
        ans = process_fn(req.prompt) if process_fn else req.prompt.upper()
        state["usage"] += 1; cid = store.add(req.user_id, req.prompt, ans)
        return {"content_id": cid, "content": ans, "user_id": req.user_id}
    @app.get("/history/{user_id}")
    def hist(user_id: str):
        items = store.list_user(user_id); return {"user_id": user_id, "count": len(items), "items": items}
    @app.get("/content/{content_id}")
    def get_content(content_id: str):
        item = store.get(content_id)
        if item is None: raise HTTPException(404)
        return item
    return app

c = TestClient(build_core_api(plan="free", process_fn=str.upper), raise_server_exceptions=False)
assert c.get("/health").json()["status"] == "ok"
rg = c.post("/generate", json={"prompt": "hi", "user_id": "u1"})
assert rg.status_code == 200 and rg.json()["content"] == "HI"
assert c.get("/history/u1").json()["count"] == 1
cid2 = rg.json()["content_id"]
assert c.get(f"/content/{cid2}").status_code == 200
assert c.get("/content/bad").status_code == 404
c2 = TestClient(build_core_api(plan="free", process_fn=str.upper, initial_usage=5), raise_server_exceptions=False)
assert c2.post("/generate", json={"prompt": "x", "user_id": "u"}).status_code == 429
print("\\u2705 build_core_api correct")

# ─── write_scaffold ───────────────────────────────────────────────────────────
import tempfile
SCAFFOLD_FILES = {
    "app.py": "# scaffold app\\n",
    "requirements.txt": "fastapi\\nollama\\nuvicorn[standard]\\nhttpx\\n",
    "Procfile": "web: uvicorn app:app --host 0.0.0.0 --port $PORT\\n",
}
def write_scaffold(directory):
    base = Path(directory); base.mkdir(parents=True, exist_ok=True)
    for fname, content in SCAFFOLD_FILES.items():
        (base / fname).write_text(content)
    return list(SCAFFOLD_FILES.keys())

with tempfile.TemporaryDirectory() as td:
    files = write_scaffold(td)
    assert len(files) >= 3
    for f in files:
        assert (Path(td) / f).exists()
    assert "fastapi" in (Path(td) / "requirements.txt").read_text()
    assert "uvicorn" in (Path(td) / "Procfile").read_text()
print("\\u2705 write_scaffold correct")

print("\\nDay 064 \\u2014 Capstone Build I complete! \\U0001f389")
"""

SOLUTION = nb([
    md("# Day 064 — Solution: Capstone Build I"),
    code(_SOL_CELL1),
    code(_SOL_CELL2),
])
save(OUT / "project" / "solution" / "solution.ipynb", SOLUTION)
(OUT / "project" / "solution" / "writing_assistant.py").write_text(_APP_SRC)
(OUT / "project" / "solution" / "requirements.txt").write_text(_REQUIREMENTS)
(OUT / "project" / "solution" / "Procfile").write_text(_PROCFILE)

print(f"Day {DAY} notebooks written to {OUT}")
print("  exercises/  exercise_01 – exercise_05")
print("  project/    project.ipynb")
print("  project/solution/  solution.ipynb + writing_assistant.py + requirements.txt + Procfile")
