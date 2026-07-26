"""monitored_api.py — Day 061: monitoring and logging for AI apps.

Run:  uvicorn monitored_api:app --reload
Docs: http://localhost:8000/docs
"""
import json
import logging
import os
import time
from datetime import datetime

import ollama
from fastapi import FastAPI, Request
from pydantic import BaseModel, Field

MODEL   = os.environ.get("MODEL", "llama3.2")
APP_VER = "1.0.0"
LOG_LVL = os.environ.get("LOG_LEVEL", "INFO")


class JsonFormatter(logging.Formatter):
    """Emit one JSON object per log record."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level":     record.levelname,
            "logger":    record.name,
            "message":   record.getMessage(),
        }
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry)


def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Return a named logger with a JsonFormatter on stdout."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    if not logger.handlers:
        h = logging.StreamHandler()
        h.setFormatter(JsonFormatter())
        logger.addHandler(h)
    logger.propagate = False
    return logger


class MetricsCollector:
    """Thread-safe request metrics accumulator."""

    def __init__(self):
        self._requests = 0
        self._errors   = 0
        self._latencies: list[float] = []

    def record(self, status_code: int, duration_ms: float) -> None:
        self._requests += 1
        if status_code >= 400:
            self._errors += 1
        self._latencies.append(duration_ms)

    def summary(self) -> dict:
        avg        = sum(self._latencies) / len(self._latencies) if self._latencies else 0.0
        error_rate = self._errors / self._requests if self._requests else 0.0
        return {
            "requests":       self._requests,
            "errors":         self._errors,
            "avg_latency_ms": round(avg, 1),
            "error_rate":     round(error_rate, 3),
        }

    def reset(self) -> None:
        self._requests = 0
        self._errors   = 0
        self._latencies.clear()


class AskRequest(BaseModel):
    prompt: str = Field(min_length=1)


def build_api(process_fn=None) -> FastAPI:
    """Build the monitored API.

    process_fn: optional callable(prompt: str) -> str for testing.
    """
    app       = FastAPI(title="Monitored API", version=APP_VER)
    collector = MetricsCollector()
    logger    = setup_logger("monitored_api", LOG_LVL)

    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        start    = time.monotonic()
        response = await call_next(request)
        duration = (time.monotonic() - start) * 1000
        collector.record(response.status_code, duration)
        entry = {"method": request.method, "path": request.url.path,
                 "status": response.status_code, "duration_ms": round(duration, 1)}
        logger.info(json.dumps(entry))
        return response

    @app.get("/health")
    def health():
        return {"status": "ok",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "version": APP_VER}

    @app.get("/metrics")
    def metrics():
        return collector.summary()

    @app.post("/ask")
    def ask(req: AskRequest):
        if process_fn is not None:
            answer = process_fn(req.prompt)
        else:
            resp   = ollama.chat(
                model=MODEL,
                messages=[{"role": "user", "content": req.prompt}],
            )
            answer = resp["message"]["content"]
        return {"answer": answer}

    return app


app = build_api()

if __name__ == "__main__":
    import uvicorn
    PORT = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=PORT)
