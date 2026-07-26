#!/usr/bin/env python3
"""gen_day063.py — generate Day 063: Payments & Productization notebooks."""
from pathlib import Path
import json

ROOT    = Path(__file__).parent.parent
DAY     = "063"
SECTION = "04_real_apps"
OUT     = ROOT / SECTION / f"day_{DAY}"

(OUT / "exercises").mkdir(parents=True, exist_ok=True)
(OUT / "lessons").mkdir(parents=True, exist_ok=True)
(OUT / "project" / "solution").mkdir(parents=True, exist_ok=True)

# ── deliverable source ─────────────────────────────────────────────────────────
_GATED_API_SRC = '''\
"""gated_api.py — Day 063: feature gating + Stripe payments.

Setup (once):
  pip install stripe
  export STRIPE_SECRET_KEY=sk_test_...
  export STRIPE_WEBHOOK_SECRET=whsec_...

Run:
  uvicorn gated_api:app --reload
Docs:
  http://localhost:8000/docs
"""
import os
import stripe
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
APP_VER        = "1.0.0"

PLAN_PRICES = {
    "pro": os.environ.get("STRIPE_PRICE_PRO", "price_pro_monthly"),
}

FEATURE_MATRIX = {
    "free": {"basic_chat", "view_history"},
    "pro":  {"basic_chat", "view_history", "advanced_chat", "export", "api_access"},
}

DAILY_LIMITS = {"free": 10, "pro": 1_000}


def check_feature_access(plan: str, feature: str) -> bool:
    return feature in FEATURE_MATRIX.get(plan, set())


def check_rate_limit(usage_count: int, plan: str) -> tuple[bool, str]:
    limit = DAILY_LIMITS.get(plan, 0)
    if usage_count >= limit:
        return False, f"Daily limit reached for {plan!r} plan ({usage_count}/{limit})"
    return True, ""


import ollama

MODEL = os.environ.get("MODEL", "llama3.2")


def build_api(process_fn=None, initial_plan: str = "free",
              initial_usage: int = 0) -> FastAPI:
    """Build the gated API.

    process_fn: optional callable(prompt: str) -> str for testing.
    """
    app   = FastAPI(title="Gated API", version=APP_VER)
    _state = {"plan": initial_plan, "usage": initial_usage}

    class AskRequest(BaseModel):
        prompt: str = Field(min_length=1)

    class CheckoutRequest(BaseModel):
        plan: str

    @app.get("/health")
    def health():
        return {"status": "ok", "timestamp": datetime.utcnow().isoformat() + "Z"}

    @app.get("/plan")
    def get_plan():
        plan  = _state["plan"]
        limit = DAILY_LIMITS.get(plan, 0)
        return {"plan": plan, "usage_today": _state["usage"], "limit": limit}

    @app.post("/ask")
    def ask(req: AskRequest):
        plan    = _state["plan"]
        allowed, reason = check_rate_limit(_state["usage"], plan)
        if not allowed:
            raise HTTPException(status_code=429, detail=reason)
        if process_fn is not None:
            answer = process_fn(req.prompt)
        else:
            resp   = ollama.chat(
                model=MODEL,
                messages=[{"role": "user", "content": req.prompt}],
            )
            answer = resp["message"]["content"]
        _state["usage"] += 1
        return {"answer": answer, "plan": plan, "requests_remaining":
                DAILY_LIMITS.get(plan, 0) - _state["usage"]}

    @app.post("/checkout")
    def create_checkout(req: CheckoutRequest):
        if req.plan not in PLAN_PRICES:
            raise HTTPException(status_code=400,
                                detail=f"Unknown plan: {req.plan!r}")
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": PLAN_PRICES[req.plan], "quantity": 1}],
            mode="subscription",
            success_url="http://localhost:8000/checkout/success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="http://localhost:8000/checkout/cancel",
        )
        return {"session_id": session["id"], "checkout_url": session["url"]}

    @app.get("/checkout/success")
    def checkout_success(session_id: str):
        _state["plan"] = "pro"
        _state["usage"] = 0
        return {"success": True, "plan": "pro", "session_id": session_id}

    @app.get("/checkout/cancel")
    def checkout_cancel():
        return {"message": "Checkout cancelled. No charges were made."}

    @app.post("/webhook")
    async def stripe_webhook(request: Request):
        payload   = await request.body()
        sig       = request.headers.get("stripe-signature", "")
        try:
            event = stripe.Webhook.construct_event(payload, sig, WEBHOOK_SECRET)
        except (stripe.error.SignatureVerificationError, ValueError):
            raise HTTPException(status_code=400, detail="Invalid signature")
        etype = event["type"]
        if etype in ("customer.subscription.created", "customer.subscription.updated"):
            _state["plan"] = "pro"
        elif etype == "customer.subscription.deleted":
            _state["plan"] = "free"
        return {"received": True, "type": etype}

    return app


app = build_api()

if __name__ == "__main__":
    import uvicorn
    PORT = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=PORT)
'''

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

# shared constants for exercises
_SHARED_CONSTANTS = """\
FEATURE_MATRIX = {
    "free": {"basic_chat", "view_history"},
    "pro":  {"basic_chat", "view_history", "advanced_chat", "export", "api_access"},
    "enterprise": {"basic_chat", "view_history", "advanced_chat", "export",
                   "api_access", "white_label", "priority_support"},
}

DAILY_LIMITS = {
    "free":       10,
    "pro":        1_000,
    "enterprise": float("inf"),
}
"""

# ══════════════════════════════════════════════════════════════════════════════
# EXERCISE 1 — check_feature_access
# ══════════════════════════════════════════════════════════════════════════════
_EX1_STUB = """\
def check_feature_access(plan: str, feature: str) -> bool:
    \"\"\"Return True if the plan includes the feature.

    Use FEATURE_MATRIX to look up the set of features for the plan.
    Unknown plan → False.  Unknown feature → False.
    \"\"\"
    # TODO: look up plan in FEATURE_MATRIX, return feature in that set (or False)
    raise NotImplementedError
"""

_EX1_SOLUTION = """\
def check_feature_access(plan: str, feature: str) -> bool:
    return feature in FEATURE_MATRIX.get(plan, set())
"""

_EX1_CHECKS = """\
score, total = 0, 5
try:
    # free tier: has basic_chat
    assert check_feature_access("free", "basic_chat") is True
    score += 1; print("\\u2705 free plan has basic_chat")

    # free tier: does NOT have advanced_chat
    assert check_feature_access("free", "advanced_chat") is False
    score += 1; print("\\u2705 free plan does not have advanced_chat")

    # pro tier: has advanced_chat
    assert check_feature_access("pro", "advanced_chat") is True
    score += 1; print("\\u2705 pro plan has advanced_chat")

    # enterprise: has white_label
    assert check_feature_access("enterprise", "white_label") is True
    score += 1; print("\\u2705 enterprise plan has white_label")

    # unknown plan → False
    assert check_feature_access("starter", "basic_chat") is False
    # unknown feature → False
    assert check_feature_access("pro", "teleport") is False
    score += 1; print("\\u2705 unknown plan / unknown feature → False")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX1 = nb([
    md("# Day 063 — Exercise 1: check_feature_access\n\n"
       "**Feature gating** restricts capabilities by plan tier. Instead of "
       "copy-pasting `if plan == 'pro'` conditionals everywhere, a single "
       "feature matrix centralises the mapping from plans to allowed features.\n\n"
       "```\n"
       "FEATURE_MATRIX = {\n"
       "    'free': {'basic_chat', 'view_history'},\n"
       "    'pro':  {'basic_chat', 'view_history', 'advanced_chat', 'export', ...},\n"
       "    ...\n"
       "}\n"
       "```\n\n"
       "One dict to maintain instead of scattered conditionals."),
    code(_SHARED_CONSTANTS),
    md("## Task\n\n"
       "Implement `check_feature_access(plan, feature) -> bool`:\n\n"
       "- Look up `plan` in `FEATURE_MATRIX` (default to empty set for unknown plans)\n"
       "- Return `feature in <that set>`\n"
       "- Unknown plan → `False`; unknown feature → `False`"),
    md("## Your Implementation"),
    code(_EX1_STUB),
    code(_EX1_SOLUTION),
    md("## Automated checks"),
    code(_EX1_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX1_SOLUTION + "```\n\n"
       "**One line thanks to `dict.get(key, default)`**: if the plan is unknown, "
       "`get` returns an empty set, so `feature in set()` is always `False` — "
       "safe by default. Adding a new plan is a single dict entry; no code changes.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_01.ipynb", EX1)

# ══════════════════════════════════════════════════════════════════════════════
# EXERCISE 2 — check_rate_limit
# ══════════════════════════════════════════════════════════════════════════════
_EX2_STUB = """\
def check_rate_limit(usage_count: int, plan: str) -> tuple[bool, str]:
    \"\"\"Return (allowed, reason) based on daily usage limits.

    allowed=True, reason=''   — request can proceed
    allowed=False, reason=... — limit reached; include plan name and counts

    Use DAILY_LIMITS to look up the limit for the plan.
    Unknown plan limit defaults to 0 (nothing allowed).
    Enterprise limit is float('inf') — always allowed.
    \"\"\"
    # TODO: look up limit, compare usage_count, return (bool, str)
    raise NotImplementedError
"""

_EX2_SOLUTION = """\
def check_rate_limit(usage_count: int, plan: str) -> tuple[bool, str]:
    limit = DAILY_LIMITS.get(plan, 0)
    if usage_count >= limit:
        return False, f"Daily limit reached for {plan!r} plan"
    return True, ""
"""

_EX2_CHECKS = """\
score, total = 0, 5
try:
    # free user under limit
    allowed, msg = check_rate_limit(5, "free")
    assert allowed is True and msg == ""
    score += 1; print("\\u2705 free user (5/10) is allowed")

    # free user at limit
    allowed2, msg2 = check_rate_limit(10, "free")
    assert allowed2 is False and isinstance(msg2, str) and len(msg2) > 0
    score += 1; print("\\u2705 free user at limit (10/10) is blocked")

    # pro user well under limit
    allowed3, _ = check_rate_limit(500, "pro")
    assert allowed3 is True
    score += 1; print("\\u2705 pro user (500/1000) is allowed")

    # pro user at limit
    allowed4, msg4 = check_rate_limit(1000, "pro")
    assert allowed4 is False
    score += 1; print("\\u2705 pro user at limit (1000/1000) is blocked")

    # enterprise: always allowed (inf limit)
    allowed5, _ = check_rate_limit(999_999, "enterprise")
    assert allowed5 is True
    score += 1; print("\\u2705 enterprise user always allowed (inf limit)")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX2 = nb([
    md("# Day 063 — Exercise 2: check_rate_limit\n\n"
       "Rate limiting prevents free-tier abuse and ensures fair resource allocation. "
       "Each plan has a daily request allowance. When `usage_count >= limit`, the "
       "request is blocked and the API returns `429 Too Many Requests`.\n\n"
       "| Plan | Daily limit |\n"
       "|------|-------------|\n"
       "| free | 10 |\n"
       "| pro | 1,000 |\n"
       "| enterprise | unlimited (∞) |"),
    code(_SHARED_CONSTANTS),
    md("## Task\n\n"
       "Implement `check_rate_limit(usage_count, plan) -> tuple[bool, str]`:\n\n"
       "- Look up `plan` in `DAILY_LIMITS` (default `0` for unknown plans)\n"
       "- If `usage_count >= limit`: return `(False, descriptive_message)`\n"
       "- Otherwise: return `(True, '')`\n"
       "- `float('inf')` comparisons work correctly: `999_999 >= float('inf')` is `False`"),
    md("## Your Implementation"),
    code(_EX2_STUB),
    code(_EX2_SOLUTION),
    md("## Automated checks"),
    code(_EX2_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX2_SOLUTION + "```\n\n"
       "**Why `>= limit` not `> limit`?** If the limit is 10, usage_count=10 "
       "means the user has already made 10 requests (0 through 9). Request 11 "
       "would bring it to 10 completed — but since we check BEFORE incrementing, "
       "`usage_count == 10` means the 11th request is arriving. Block it.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_02.ipynb", EX2)

# ══════════════════════════════════════════════════════════════════════════════
# EXERCISE 3 — process_webhook_event
# ══════════════════════════════════════════════════════════════════════════════
_EX3_STUB = """\
PLAN_EVENTS = {
    \"customer.subscription.created\": \"pro\",
    \"customer.subscription.updated\": \"pro\",
    \"customer.subscription.deleted\": \"free\",
}

def process_webhook_event(event_type: str, payload: dict,
                          user_db: dict) -> dict:
    \"\"\"Handle a Stripe webhook event and update user_db.

    payload keys:
        customer_id  str — identifies the user in user_db

    Behaviour:
    - Missing customer_id in payload
        → {success: False, action: 'no_customer_id', customer_id: ''}
    - customer_id not in user_db
        → {success: False, action: 'customer_not_found', customer_id: ...}
    - event_type in PLAN_EVENTS
        → set user_db[customer_id]['plan'] = PLAN_EVENTS[event_type]
        → {success: True, action: f'plan_set_{new_plan}', customer_id: ...}
    - event_type == 'invoice.payment_failed'
        → set user_db[customer_id]['status'] = 'past_due'
        → {success: True, action: 'status_set_past_due', customer_id: ...}
    - any other event_type
        → {success: True, action: 'ignored', customer_id: ...}
    \"\"\"
    # TODO: implement the event routing logic
    raise NotImplementedError
"""

_EX3_SOLUTION = """\
PLAN_EVENTS = {
    "customer.subscription.created": "pro",
    "customer.subscription.updated": "pro",
    "customer.subscription.deleted": "free",
}

def process_webhook_event(event_type, payload, user_db):
    customer_id = payload.get("customer_id", "")
    if not customer_id:
        return {"success": False, "action": "no_customer_id", "customer_id": ""}
    if customer_id not in user_db:
        return {"success": False, "action": "customer_not_found",
                "customer_id": customer_id}
    if event_type in PLAN_EVENTS:
        new_plan = PLAN_EVENTS[event_type]
        user_db[customer_id]["plan"] = new_plan
        return {"success": True, "action": f"plan_set_{new_plan}",
                "customer_id": customer_id}
    if event_type == "invoice.payment_failed":
        user_db[customer_id]["status"] = "past_due"
        return {"success": True, "action": "status_set_past_due",
                "customer_id": customer_id}
    return {"success": True, "action": "ignored", "customer_id": customer_id}
"""

_EX3_CHECKS = """\
score, total = 0, 6
try:
    db = {
        "cus_123": {"plan": "free", "status": "active"},
        "cus_456": {"plan": "pro",  "status": "active"},
    }

    # subscription.created → pro
    r = process_webhook_event("customer.subscription.created",
                              {"customer_id": "cus_123"}, db)
    assert r["success"] is True and r["action"] == "plan_set_pro"
    assert db["cus_123"]["plan"] == "pro"
    score += 1; print("\\u2705 subscription.created upgrades plan to pro")

    # subscription.deleted → free
    r2 = process_webhook_event("customer.subscription.deleted",
                               {"customer_id": "cus_456"}, db)
    assert r2["success"] is True and r2["action"] == "plan_set_free"
    assert db["cus_456"]["plan"] == "free"
    score += 1; print("\\u2705 subscription.deleted downgrades plan to free")

    # invoice.payment_failed → status = past_due
    r3 = process_webhook_event("invoice.payment_failed",
                               {"customer_id": "cus_123"}, db)
    assert r3["success"] is True and r3["action"] == "status_set_past_due"
    assert db["cus_123"]["status"] == "past_due"
    score += 1; print("\\u2705 invoice.payment_failed marks status as past_due")

    # unknown customer
    r4 = process_webhook_event("customer.subscription.created",
                               {"customer_id": "cus_999"}, db)
    assert r4["success"] is False and r4["action"] == "customer_not_found"
    score += 1; print("\\u2705 unknown customer_id → success=False")

    # missing customer_id
    r5 = process_webhook_event("customer.subscription.created", {}, db)
    assert r5["success"] is False and r5["action"] == "no_customer_id"
    score += 1; print("\\u2705 missing customer_id → success=False")

    # unknown event → ignored
    r6 = process_webhook_event("payment_intent.created",
                               {"customer_id": "cus_123"}, db)
    assert r6["success"] is True and r6["action"] == "ignored"
    score += 1; print("\\u2705 unknown event type → ignored (success=True)")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX3 = nb([
    md("# Day 063 — Exercise 3: process_webhook_event\n\n"
       "Stripe notifies your server about payment events via **webhooks** — HTTP "
       "POST requests sent to your `/webhook` endpoint whenever something happens "
       "(subscription created, payment failed, etc.). Your server updates its "
       "database based on the event type.\n\n"
       "Key events for a subscription product:\n"
       "| Event | Meaning | Action |\n"
       "|-------|---------|--------|\n"
       "| `customer.subscription.created` | User subscribed | Set plan = pro |\n"
       "| `customer.subscription.deleted` | User cancelled | Set plan = free |\n"
       "| `invoice.payment_failed` | Payment declined | Mark as past_due |"),
    md("## Task\n\n"
       "Implement `process_webhook_event(event_type, payload, user_db) -> dict`:\n\n"
       "- `payload['customer_id']` identifies the user\n"
       "- Missing customer_id → `{success: False, action: 'no_customer_id'}`\n"
       "- Unknown customer → `{success: False, action: 'customer_not_found'}`\n"
       "- Event in `PLAN_EVENTS` → update `user_db[cid]['plan']`\n"
       "- `invoice.payment_failed` → set `user_db[cid]['status'] = 'past_due'`\n"
       "- Any other event → `{success: True, action: 'ignored'}`"),
    md("## Your Implementation"),
    code(_EX3_STUB),
    code(_EX3_SOLUTION),
    md("## Automated checks"),
    code(_EX3_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX3_SOLUTION + "```\n\n"
       "**Why `ignored` not an error for unknown events?** Stripe sends many event "
       "types (30+). Your server should handle the ones it cares about and silently "
       "accept the rest. Returning an error for unknown events would cause Stripe to "
       "retry the webhook repeatedly, flooding your logs.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_03.ipynb", EX3)

# ══════════════════════════════════════════════════════════════════════════════
# EXERCISE 4 — build_gated_api
# ══════════════════════════════════════════════════════════════════════════════
_EX4_GIVEN = _SHARED_CONSTANTS + """
def check_rate_limit(usage_count: int, plan: str) -> tuple[bool, str]:
    limit = DAILY_LIMITS.get(plan, 0)
    if usage_count >= limit:
        return False, f"Daily limit reached for {plan!r} plan"
    return True, ""
"""

_EX4_IMPORTS = """\
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from starlette.testclient import TestClient
"""

_EX4_STUB = """\
def build_gated_api(plan: str = "free", process_fn=None,
                    initial_usage: int = 0) -> FastAPI:
    \"\"\"FastAPI with rate-limited /ask endpoint.

    GET /plan                    → {plan, usage_today, limit}
    POST /ask {prompt: str}      → {answer, plan, requests_remaining}
                                 → 429 if rate limit exceeded
                                 → 422 if prompt is empty

    State:
        plan — fixed for this app instance (test parameter)
        usage — starts at initial_usage, increments on each successful /ask
    process_fn: optional callable(prompt: str) -> str for testing.
    \"\"\"
    # TODO: create app + state, add /plan and /ask routes, enforce rate limit
    raise NotImplementedError
"""

_EX4_SOLUTION = """\
def build_gated_api(plan: str = "free", process_fn=None,
                    initial_usage: int = 0) -> FastAPI:
    app    = FastAPI()
    _state = {"plan": plan, "usage": initial_usage}

    class _AskReq(BaseModel):
        prompt: str = Field(min_length=1)

    @app.get("/plan")
    def get_plan():
        lim = DAILY_LIMITS.get(_state["plan"], 0)
        return {"plan": _state["plan"],
                "usage_today": _state["usage"],
                "limit": lim if lim != float("inf") else -1}

    @app.post("/ask")
    def ask(req: _AskReq):
        allowed, reason = check_rate_limit(_state["usage"], _state["plan"])
        if not allowed:
            raise HTTPException(status_code=429, detail=reason)
        answer = process_fn(req.prompt) if process_fn else req.prompt.upper()
        _state["usage"] += 1
        lim = DAILY_LIMITS.get(_state["plan"], 0)
        remaining = (lim - _state["usage"]) if lim != float("inf") else -1
        return {"answer": answer, "plan": _state["plan"],
                "requests_remaining": remaining}

    return app
"""

_EX4_CHECKS = """\
score, total = 0, 6
try:
    from starlette.testclient import TestClient

    # /plan endpoint
    app = build_gated_api(plan="free", process_fn=str.upper)
    c   = TestClient(app, raise_server_exceptions=False)
    rp  = c.get("/plan")
    assert rp.status_code == 200
    p   = rp.json()
    assert p["plan"] == "free" and p["usage_today"] == 0
    score += 1; print("\\u2705 GET /plan returns plan and usage_today")

    # successful ask
    r = c.post("/ask", json={"prompt": "hello"})
    assert r.status_code == 200
    assert r.json()["answer"] == "HELLO"
    score += 1; print("\\u2705 POST /ask returns processed answer")

    # usage increments
    rp2 = c.get("/plan")
    assert rp2.json()["usage_today"] == 1
    score += 1; print("\\u2705 usage_today increments after /ask")

    # rate limit: at-limit app (initial_usage=10 for free plan)
    app2 = build_gated_api(plan="free", process_fn=str.upper, initial_usage=10)
    c2   = TestClient(app2, raise_server_exceptions=False)
    r2   = c2.post("/ask", json={"prompt": "hello"})
    assert r2.status_code == 429, f"Expected 429, got {r2.status_code}"
    score += 1; print("\\u2705 429 when free rate limit (10) is reached")

    # pro user with same usage is allowed
    app3 = build_gated_api(plan="pro", process_fn=str.upper, initial_usage=10)
    c3   = TestClient(app3, raise_server_exceptions=False)
    r3   = c3.post("/ask", json={"prompt": "hello"})
    assert r3.status_code == 200
    score += 1; print("\\u2705 pro user allowed at usage=10 (limit=1000)")

    # empty prompt → 422
    r4 = c.post("/ask", json={"prompt": ""})
    assert r4.status_code == 422
    score += 1; print("\\u2705 empty prompt \\u2192 422")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX4 = nb([
    md("# Day 063 — Exercise 4: Gated API\n\n"
       "Wire `check_rate_limit` into a FastAPI app. The `/ask` endpoint checks "
       "the user's plan before calling the process function and returns `429 Too "
       "Many Requests` when the daily limit is exceeded.\n\n"
       "`initial_usage` lets tests start the counter at any value — so you can "
       "test the at-limit case without making 10 actual requests."),
    code(_EX4_GIVEN),
    code(_EX4_IMPORTS),
    md("## Task\n\n"
       "Implement `build_gated_api(plan='free', process_fn=None, initial_usage=0) -> FastAPI`:\n\n"
       "```\n"
       "GET /plan  → {plan, usage_today, limit}\n"
       "POST /ask  → {answer, plan, requests_remaining}  or  429\n"
       "```\n\n"
       "- Check rate limit BEFORE calling process_fn\n"
       "- Return `HTTPException(429)` if blocked\n"
       "- Increment `usage` only on successful asks\n"
       "- `requests_remaining = limit - usage` (use `-1` when limit is `float('inf')`)"),
    md("## Your Implementation"),
    code(_EX4_STUB),
    code(_EX4_SOLUTION),
    md("## Automated checks"),
    code(_EX4_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX4_SOLUTION + "```\n\n"
       "**Why HTTP 429?** RFC 6585 defines 429 Too Many Requests specifically for "
       "rate limiting. Clients (browsers, SDKs) can detect 429 and implement "
       "automatic retry-with-backoff. A 403 Forbidden doesn't signal that the "
       "request could succeed later.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_04.ipynb", EX4)

# ══════════════════════════════════════════════════════════════════════════════
# EXERCISE 5 — build_stripe_checkout (mocked Stripe)
# ══════════════════════════════════════════════════════════════════════════════
_EX5_GIVEN = """\
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from starlette.testclient import TestClient

# Duck-typed mock: any object with .checkout.Session.create(**kwargs) works
class _MockStripe:
    class checkout:
        class Session:
            @staticmethod
            def create(**kwargs):
                return {"id": "cs_test_abc123",
                        "url": "https://checkout.stripe.com/pay/test"}

PLAN_PRICES = {
    "pro": "price_pro_monthly",
}
"""

_EX5_STUB = """\
def build_checkout_api(stripe_client=None) -> FastAPI:
    \"\"\"FastAPI with Stripe checkout endpoints.

    POST /checkout  {\"plan\": str}
        → 200 {\"session_id\": str, \"checkout_url\": str}
        → 400 if plan not in PLAN_PRICES
        Uses stripe_client.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{'price': price_id, 'quantity': 1}],
            mode='subscription',
            success_url='http://localhost/checkout/success',
            cancel_url='http://localhost/checkout/cancel',
        )

    GET /checkout/cancel
        → 200 {\"message\": \"Checkout cancelled. No charges were made.\"}

    If stripe_client is None, use _MockStripe().
    \"\"\"
    # TODO: create app, implement /checkout POST and /checkout/cancel GET
    raise NotImplementedError
"""

_EX5_SOLUTION = """\
def build_checkout_api(stripe_client=None) -> FastAPI:
    client = stripe_client if stripe_client is not None else _MockStripe()
    app    = FastAPI()

    class _CheckoutReq(BaseModel):
        plan: str

    @app.post("/checkout")
    def create_checkout(req: _CheckoutReq):
        if req.plan not in PLAN_PRICES:
            raise HTTPException(status_code=400,
                                detail=f"Unknown plan: {req.plan!r}")
        session = client.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": PLAN_PRICES[req.plan], "quantity": 1}],
            mode="subscription",
            success_url="http://localhost/checkout/success",
            cancel_url="http://localhost/checkout/cancel",
        )
        return {"session_id": session["id"], "checkout_url": session["url"]}

    @app.get("/checkout/cancel")
    def cancel():
        return {"message": "Checkout cancelled. No charges were made."}

    return app
"""

_EX5_CHECKS = """\
score, total = 0, 5
try:
    # default (mock) client
    app = build_checkout_api()
    c   = TestClient(app, raise_server_exceptions=False)

    # valid plan → 200 with session_id and checkout_url
    r = c.post("/checkout", json={"plan": "pro"})
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    d = r.json()
    assert "session_id"   in d, f"Missing session_id: {d}"
    assert "checkout_url" in d, f"Missing checkout_url: {d}"
    score += 1; print("\\u2705 POST /checkout returns session_id and checkout_url")

    # session_id and url are non-empty strings
    assert isinstance(d["session_id"], str) and d["session_id"]
    assert isinstance(d["checkout_url"], str) and d["checkout_url"]
    score += 1; print("\\u2705 session_id and checkout_url are non-empty strings")

    # unknown plan → 400
    r2 = c.post("/checkout", json={"plan": "enterprise"})
    assert r2.status_code == 400, f"Expected 400, got {r2.status_code}"
    score += 1; print("\\u2705 unknown plan \\u2192 400")

    # cancel endpoint
    r3 = c.get("/checkout/cancel")
    assert r3.status_code == 200
    assert "cancelled" in r3.json().get("message", "").lower()
    score += 1; print("\\u2705 GET /checkout/cancel returns cancellation message")

    # custom stripe_client is used (not the default mock)
    class _CustomMock:
        class checkout:
            class Session:
                @staticmethod
                def create(**kwargs):
                    return {"id": "cs_custom_xyz", "url": "https://custom.stripe.com"}
    app2 = build_checkout_api(stripe_client=_CustomMock())
    c2   = TestClient(app2, raise_server_exceptions=False)
    r4   = c2.post("/checkout", json={"plan": "pro"})
    assert r4.json()["session_id"] == "cs_custom_xyz"
    score += 1; print("\\u2705 custom stripe_client is injected and used")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX5 = nb([
    md("# Day 063 — Exercise 5: Stripe Checkout (Mocked)\n\n"
       "Stripe Checkout is a Stripe-hosted payment page. Your server creates a "
       "**checkout session** and redirects the user to the Stripe URL. After "
       "payment, Stripe redirects back to your success URL.\n\n"
       "```\n"
       "POST /checkout {\"plan\": \"pro\"}\n"
       "    → 200 {\"session_id\": \"cs_test_...\", \"checkout_url\": \"https://checkout.stripe.com/...\"}\n"
       "    → 302/redirect to checkout_url (in a browser)\n"
       "```\n\n"
       "For testing, the `stripe_client` is injected — replace the real `stripe` "
       "module with a duck-typed mock that returns predictable data."),
    code(_EX5_GIVEN),
    md("## Task\n\n"
       "Implement `build_checkout_api(stripe_client=None) -> FastAPI`:\n\n"
       "```\n"
       "POST /checkout  {\"plan\": str}  → {\"session_id\", \"checkout_url\"}  or 400\n"
       "GET /checkout/cancel           → {\"message\": \"Checkout cancelled...\"}\n"
       "```\n\n"
       "- Use `stripe_client.checkout.Session.create(**kwargs)` to get the session\n"
       "- If `plan` not in `PLAN_PRICES`: raise `HTTPException(400)`\n"
       "- If `stripe_client` is `None`: use `_MockStripe()`"),
    md("## Your Implementation"),
    code(_EX5_STUB),
    code(_EX5_SOLUTION),
    md("## Automated checks"),
    code(_EX5_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX5_SOLUTION + "```\n\n"
       "**Why inject the Stripe client?** The real `stripe` module makes network "
       "calls to Stripe's API. Tests should never make real API calls — they're "
       "slow, require credentials, and create test data. Duck-typing the client "
       "lets you swap the real Stripe SDK for a mock with zero code changes.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_05.ipynb", EX5)

# ══════════════════════════════════════════════════════════════════════════════
# PROJECT NOTEBOOK
# ══════════════════════════════════════════════════════════════════════════════
PROJECT = nb([
    md("# Day 063 — Project: Payments & Productization\n\n"
       "Build `gated_api.py` — a FastAPI server with plan-based feature gating, "
       "rate limiting, and Stripe Checkout integration."),
    md("## Deliverable\n\n"
       "`gated_api.py` in `project/solution/` — a FastAPI app with:\n\n"
       "| Endpoint | Description |\n"
       "|----------|-------------|\n"
       "| `GET /health` | Health check |\n"
       "| `GET /plan` | Current plan, usage, limit |\n"
       "| `POST /ask` | Rate-limited AI Q&A |\n"
       "| `POST /checkout` | Create Stripe checkout session |\n"
       "| `GET /checkout/success` | Handle post-payment redirect |\n"
       "| `GET /checkout/cancel` | Handle cancelled checkout |\n"
       "| `POST /webhook` | Handle Stripe webhook events |\n\n"
       "## Setup (requires a free Stripe account)\n\n"
       "```bash\n"
       "pip install stripe\n"
       "export STRIPE_SECRET_KEY=sk_test_...  # from dashboard.stripe.com\n"
       "export STRIPE_WEBHOOK_SECRET=whsec_...\n"
       "uvicorn gated_api:app --reload\n"
       "```\n\n"
       "## Testing without Stripe credentials\n\n"
       "The `build_api(process_fn=..., initial_plan=...)` factory accepts a `process_fn` "
       "for local testing without Ollama or Stripe.\n\n"
       "## Concepts used\n\n"
       "- Feature matrix: plan → set of allowed features\n"
       "- Rate limiting: usage_count >= daily_limit → 429\n"
       "- Stripe Checkout: session create → redirect URL\n"
       "- Webhook events: subscription.created/deleted → plan change\n"
       "- `stripe.Webhook.construct_event` — signature verification"),
])
save(OUT / "project" / "project.ipynb", PROJECT)

# ══════════════════════════════════════════════════════════════════════════════
# SOLUTION NOTEBOOK
# ══════════════════════════════════════════════════════════════════════════════
_SOL_CELL1 = (
    f"_GATED_API_SRC = {repr(_GATED_API_SRC)}\n"
    "from pathlib import Path\n"
    "Path('gated_api.py').write_text(_GATED_API_SRC)\n"
    "print('gated_api.py written.')"
)

_SOL_CELL2 = """\
# inline test — no Stripe credentials or Ollama needed
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from starlette.testclient import TestClient

FEATURE_MATRIX = {
    "free": {"basic_chat", "view_history"},
    "pro":  {"basic_chat", "view_history", "advanced_chat", "export", "api_access"},
}
DAILY_LIMITS = {"free": 10, "pro": 1_000, "enterprise": float("inf")}

def check_feature_access(plan, feature):
    return feature in FEATURE_MATRIX.get(plan, set())

def check_rate_limit(usage_count, plan):
    limit = DAILY_LIMITS.get(plan, 0)
    if usage_count >= limit:
        return False, f"Daily limit reached for {plan!r} plan"
    return True, ""

# --- inline gated API ---
def build_api(process_fn=None, initial_plan="free", initial_usage=0):
    app = FastAPI(); _s = {"plan": initial_plan, "usage": initial_usage}
    class _R(BaseModel):
        prompt: str = Field(min_length=1)
    @app.get("/plan")
    def plan():
        lim = DAILY_LIMITS.get(_s["plan"], 0)
        return {"plan": _s["plan"], "usage_today": _s["usage"],
                "limit": lim if lim != float("inf") else -1}
    @app.post("/ask")
    def ask(req: _R):
        ok, reason = check_rate_limit(_s["usage"], _s["plan"])
        if not ok: raise HTTPException(429, reason)
        answer = process_fn(req.prompt) if process_fn else req.prompt.upper()
        _s["usage"] += 1
        return {"answer": answer, "plan": _s["plan"]}
    return app

# tests
c = TestClient(build_api(process_fn=str.upper), raise_server_exceptions=False)

assert c.get("/plan").json()["plan"] == "free"
print("\\u2705 /plan returns free")

r = c.post("/ask", json={"prompt": "hello"})
assert r.status_code == 200 and r.json()["answer"] == "HELLO"
print("\\u2705 /ask works")

assert c.post("/ask", json={"prompt": ""}).status_code == 422
print("\\u2705 empty prompt \\u2192 422")

c2 = TestClient(build_api(process_fn=str.upper, initial_usage=10),
                raise_server_exceptions=False)
assert c2.post("/ask", json={"prompt": "x"}).status_code == 429
print("\\u2705 free at limit \\u2192 429")

# feature access checks
assert check_feature_access("free", "basic_chat") is True
assert check_feature_access("free", "advanced_chat") is False
assert check_feature_access("pro", "advanced_chat") is True
print("\\u2705 check_feature_access correct")

# rate limit checks
assert check_rate_limit(5, "free") == (True, "")
assert check_rate_limit(10, "free")[0] is False
assert check_rate_limit(999_999, "enterprise")[0] is True
print("\\u2705 check_rate_limit correct")

# webhook event processing
PLAN_EVENTS = {"customer.subscription.created": "pro",
               "customer.subscription.deleted": "free"}
def process_webhook_event(etype, payload, user_db):
    cid = payload.get("customer_id", "")
    if not cid: return {"success": False, "action": "no_customer_id", "customer_id": ""}
    if cid not in user_db: return {"success": False, "action": "customer_not_found", "customer_id": cid}
    if etype in PLAN_EVENTS:
        np = PLAN_EVENTS[etype]; user_db[cid]["plan"] = np
        return {"success": True, "action": f"plan_set_{np}", "customer_id": cid}
    if etype == "invoice.payment_failed":
        user_db[cid]["status"] = "past_due"
        return {"success": True, "action": "status_set_past_due", "customer_id": cid}
    return {"success": True, "action": "ignored", "customer_id": cid}

db = {"cus_1": {"plan": "free", "status": "active"}}
assert process_webhook_event("customer.subscription.created", {"customer_id": "cus_1"}, db)["action"] == "plan_set_pro"
assert db["cus_1"]["plan"] == "pro"
print("\\u2705 webhook event processing correct")

print("\\nDay 063 \\u2014 Payments & Productization complete! \\U0001f389")
"""

SOLUTION = nb([
    md("# Day 063 — Solution: Payments & Productization"),
    code(_SOL_CELL1),
    code(_SOL_CELL2),
])
save(OUT / "project" / "solution" / "solution.ipynb", SOLUTION)
(OUT / "project" / "solution" / "gated_api.py").write_text(_GATED_API_SRC)

print(f"Day {DAY} notebooks written to {OUT}")
print("  exercises/  exercise_01 – exercise_05")
print("  project/    project.ipynb")
print("  project/solution/  solution.ipynb + gated_api.py")
