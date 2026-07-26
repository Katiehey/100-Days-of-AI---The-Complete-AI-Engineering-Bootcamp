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
