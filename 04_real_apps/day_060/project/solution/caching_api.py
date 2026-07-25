"""caching_api.py — Day 060: response caching for AI apps.

Run:  uvicorn caching_api:app --reload
Docs: http://localhost:8000/docs
"""
import os
import time
from datetime import datetime

import ollama
from fastapi import FastAPI
from pydantic import BaseModel, Field

MODEL     = os.environ.get("MODEL", "llama3.2")
CACHE_TTL = float(os.environ.get("CACHE_TTL_SECONDS", "300"))
APP_VER   = "1.0.0"


class SimpleCache:
    """In-memory key-value cache with per-entry TTL."""

    def __init__(self):
        self._store: dict = {}   # key -> (value, expires_at)

    def set(self, key: str, value, ttl: float = 60.0) -> None:
        self._store[key] = (value, time.monotonic() + ttl)

    def get(self, key: str):
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return value

    def has(self, key: str) -> bool:
        return self.get(key) is not None

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> int:
        n = len(self._store)
        self._store.clear()
        return n

    def __len__(self) -> int:
        now = time.monotonic()
        return sum(1 for _, exp in self._store.values() if now <= exp)


class AskRequest(BaseModel):
    prompt: str = Field(min_length=1)


def build_api(process_fn=None) -> FastAPI:
    """Build the caching API.

    process_fn: optional callable(prompt: str) -> str for testing.
    """
    app   = FastAPI(title="Caching API", version=APP_VER)
    cache = SimpleCache()
    stats = {"hits": 0, "misses": 0}

    @app.get("/health")
    def health():
        return {"status": "ok",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "version": APP_VER}

    @app.post("/ask")
    def ask(req: AskRequest):
        cached = cache.get(req.prompt)
        if cached is not None:
            stats["hits"] += 1
            return {"answer": cached, "cache_hit": True}

        stats["misses"] += 1
        if process_fn is not None:
            answer = process_fn(req.prompt)
        else:
            resp = ollama.chat(
                model=MODEL,
                messages=[{"role": "user", "content": req.prompt}],
            )
            answer = resp["message"]["content"]
        cache.set(req.prompt, answer, ttl=CACHE_TTL)
        return {"answer": answer, "cache_hit": False}

    @app.get("/cache/stats")
    def cache_stats():
        return {"hits": stats["hits"], "misses": stats["misses"],
                "size": len(cache)}

    @app.delete("/cache")
    def clear_cache():
        n = cache.clear()
        stats["hits"] = 0
        stats["misses"] = 0
        return {"cleared": n}

    return app


app = build_api()

if __name__ == "__main__":
    import uvicorn
    PORT = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=PORT)
