"""background_api.py — Day 059: background job processing API.

Run:  uvicorn background_api:app --reload
Docs: http://localhost:8000/docs
"""
import os
import threading
import uuid
from datetime import datetime

import ollama
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

MODEL       = os.environ.get("MODEL", "llama3.2")
APP_VERSION = "1.0.0"


class _JobStore:
    """Thread-safe in-memory job store."""

    def __init__(self):
        self._jobs: dict = {}
        self._lock = threading.Lock()

    def create(self, job_id: str) -> None:
        with self._lock:
            self._jobs[job_id] = {"status": "pending"}

    def set_running(self, job_id: str) -> None:
        with self._lock:
            self._jobs[job_id] = {"status": "running"}

    def set_done(self, job_id: str, result: str) -> None:
        with self._lock:
            self._jobs[job_id] = {"status": "done", "result": result}

    def set_error(self, job_id: str, error: str) -> None:
        with self._lock:
            self._jobs[job_id] = {"status": "error", "error": error}

    def get(self, job_id: str) -> dict | None:
        with self._lock:
            data = self._jobs.get(job_id)
            return dict(data) if data else None


class SummarizeRequest(BaseModel):
    text: str = Field(min_length=1)


def build_api(process_fn=None) -> FastAPI:
    """Build the background job API.

    process_fn: optional callable(text: str) -> str for testing.
                If None, uses ollama.chat to summarize.
    """
    app = FastAPI(title="Background Job API", version=APP_VERSION)
    store = _JobStore()

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": APP_VERSION,
        }

    @app.post("/summarize", status_code=202)
    def submit_summarize(req: SummarizeRequest):
        job_id = uuid.uuid4().hex[:8]
        store.create(job_id)

        def worker():
            store.set_running(job_id)
            try:
                if process_fn is not None:
                    summary = process_fn(req.text)
                else:
                    prompt = "Summarize in one sentence:\n\n" + req.text[:3000]
                    resp = ollama.chat(
                        model=MODEL,
                        messages=[{"role": "user", "content": prompt}],
                    )
                    summary = resp["message"]["content"]
                store.set_done(job_id, summary)
            except Exception as exc:
                store.set_error(job_id, str(exc))

        threading.Thread(target=worker, daemon=True).start()
        return {"job_id": job_id, "status": "pending"}

    @app.get("/jobs/{job_id}")
    def get_job(job_id: str):
        job = store.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return job

    return app


app = build_api()

if __name__ == "__main__":
    import uvicorn
    PORT = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=PORT)
