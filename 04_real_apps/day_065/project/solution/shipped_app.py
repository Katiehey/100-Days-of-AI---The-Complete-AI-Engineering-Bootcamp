"""shipped_app.py — Day 065: Capstone Build II — shippable AI Writing Assistant.

All Day 064 features + monitoring middleware + /metrics endpoint.

Setup:
  pip install fastapi "uvicorn[standard]" ollama
  ollama pull llama3.2

Run:  uvicorn shipped_app:app --reload
Docs: http://localhost:8000/docs
Test: pytest test_shipped_app.py -v
"""
import os
import re
import secrets
import time
from datetime import datetime

import ollama
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

APP_VER = "1.1.0"
MODEL   = os.environ.get("MODEL", "llama3.2")

# ── plan configuration ────────────────────────────────────────────────────────

DAILY_LIMITS = {"free": 5, "pro": 500, "enterprise": float("inf")}

FEATURE_MATRIX = {
    "free": {"basic_generate", "view_history"},
    "pro":  {"basic_generate", "view_history", "improve_text", "export"},
}

TEMPLATES = {
    "email":      "Write a {tone} email to {recipient} about {topic}.",
    "tweet":      "Write a {tone} tweet about {topic} in under 280 characters.",
    "summary":    "Write a concise {length}-sentence summary of: {content}",
    "blog_intro": "Write an engaging blog intro about {topic} for a {audience} audience.",
}


def check_feature_access(plan: str, feature: str) -> bool:
    return feature in FEATURE_MATRIX.get(plan, set())


def check_rate_limit(usage_count: int, plan: str) -> tuple[bool, str]:
    limit = DAILY_LIMITS.get(plan, 0)
    if usage_count >= limit:
        return False, (
            f"Daily limit reached for {plan!r} plan "
            f"({usage_count}/{int(limit)}). Upgrade to pro for 500/day."
        )
    return True, ""


def render_template(template_str: str, **vars) -> str:
    required = set(re.findall(r'\{(\w+)\}', template_str))
    missing  = required - set(vars.keys())
    if missing:
        raise ValueError(f"Missing template variables: {missing}")
    result = template_str
    for key, value in vars.items():
        result = result.replace(f"{{{key}}}", str(value))
    return result


# ── storage ───────────────────────────────────────────────────────────────────

class ContentStore:
    def __init__(self):
        self._store: dict = {}

    def add(self, user_id: str, prompt: str, content: str) -> str:
        cid = secrets.token_urlsafe(8)
        self._store[cid] = {
            "content_id": cid, "user_id": user_id,
            "prompt": prompt, "content": content,
            "created_at": datetime.utcnow().isoformat() + "Z",
        }
        return cid

    def get(self, content_id: str) -> dict | None:
        return self._store.get(content_id)

    def list_user(self, user_id: str) -> list[dict]:
        return [v for v in self._store.values() if v["user_id"] == user_id]

    def count(self, user_id: str) -> int:
        return sum(1 for v in self._store.values() if v["user_id"] == user_id)


# ── metrics ───────────────────────────────────────────────────────────────────

class MetricsCollector:
    def __init__(self):
        self._requests  = 0
        self._errors    = 0
        self._latencies: list[float] = []

    def record(self, status_code: int, duration_ms: float) -> None:
        self._requests += 1
        if status_code >= 400:
            self._errors += 1
        self._latencies.append(duration_ms)

    def summary(self) -> dict:
        avg  = (sum(self._latencies) / len(self._latencies)
                if self._latencies else 0.0)
        rate = self._errors / self._requests if self._requests else 0.0
        return {
            "requests":       self._requests,
            "errors":         self._errors,
            "avg_latency_ms": round(avg, 1),
            "error_rate":     round(rate, 3),
        }


# ── FastAPI app ───────────────────────────────────────────────────────────────

def build_api(process_fn=None, initial_plan: str = "free",
              initial_usage: int = 0) -> FastAPI:
    app       = FastAPI(title="AI Writing Assistant", version=APP_VER)
    store     = ContentStore()
    collector = MetricsCollector()
    state     = {"plan": initial_plan, "usage": initial_usage}

    @app.middleware("http")
    async def metrics_middleware(request, call_next):
        start    = time.monotonic()
        response = await call_next(request)
        duration = (time.monotonic() - start) * 1000
        collector.record(response.status_code, duration)
        return response

    class _GenReq(BaseModel):
        prompt:  str = Field(min_length=1)
        user_id: str = Field(min_length=1)

    class _TplReq(BaseModel):
        template: str = Field(min_length=1)
        vars:     dict = {}
        user_id:  str  = Field(min_length=1)

    class _ImpReq(BaseModel):
        text:    str = Field(min_length=1)
        user_id: str = Field(min_length=1)

    @app.get("/health")
    def health():
        return {"status": "ok",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "version": APP_VER}

    @app.get("/plan")
    def get_plan():
        lim = DAILY_LIMITS.get(state["plan"], 0)
        return {"plan": state["plan"], "usage_today": state["usage"],
                "limit": lim if lim != float("inf") else -1}

    @app.get("/metrics")
    def get_metrics():
        return collector.summary()

    @app.get("/templates")
    def list_templates():
        return {"templates": list(TEMPLATES.keys())}

    @app.post("/generate")
    def generate(req: _GenReq):
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
    def gen_template(req: _TplReq):
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
    def improve(req: _ImpReq):
        if not check_feature_access(state["plan"], "improve_text"):
            raise HTTPException(403, "improve_text requires pro plan. "
                                     "Upgrade at /checkout")
        ok, reason = check_rate_limit(state["usage"], state["plan"])
        if not ok:
            raise HTTPException(429, reason)
        prompt = f"Improve this text for clarity and style:\n\n{req.text}"
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
    def history(user_id: str):
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
