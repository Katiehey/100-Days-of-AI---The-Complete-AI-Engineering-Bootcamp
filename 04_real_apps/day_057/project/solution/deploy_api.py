"""deploy_api.py — Day 057: deployment-ready Doc-Upload AI API.

Config from environment variables (set these before running):
  PORT               - port to bind (default 8000)
  MODEL              - Ollama model name (default llama3.2)
  SECRET_KEY         - secret for future auth; set a real value in production
  MAX_UPLOAD_BYTES   - max upload size in bytes (default 5242880 = 5 MB)

Run:  uvicorn deploy_api:app --host 0.0.0.0 --port ${PORT:-8000}
"""
import io
import os
import re
import secrets
from datetime import datetime
from pathlib import Path

import pypdf
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import ollama

# --- config from environment -----------------------------------------------
PORT            = int(os.environ.get("PORT", "8000"))
MODEL           = os.environ.get("MODEL", "llama3.2")
SECRET_KEY      = os.environ.get("SECRET_KEY", "change-me-in-production")
MAX_SIZE        = int(os.environ.get("MAX_UPLOAD_BYTES", str(5 * 1024 * 1024)))
MAX_DOC_CHARS   = 4000
ALLOWED_TYPES   = {"text/plain", "application/pdf"}
UPLOAD_DIR      = Path("uploads")
APP_VERSION     = "1.0.0"

# --- helpers ----------------------------------------------------------------

def validate_upload(content: bytes, filename: str,
                    allowed_types: set[str], content_type: str,
                    max_bytes: int) -> tuple[bool, str]:
    if len(content) == 0:
        return False, "File is empty"
    if len(content) > max_bytes:
        return False, f"File too large ({len(content)} bytes, max {max_bytes})"
    ext = Path(filename).suffix.lower()
    if content_type not in allowed_types and ext not in {".txt", ".pdf"}:
        return False, f"Unsupported type: {content_type}"
    return True, ""


def safe_filename(original: str) -> str:
    name = Path(original).name
    name = re.sub(r"[^\w\-.]", "_", name)
    return f"{secrets.token_hex(4)}_{name}"


def save_upload(content: bytes, filename: str, upload_dir: Path) -> Path:
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / safe_filename(filename)
    dest.write_bytes(content)
    return dest


def extract_text(content: bytes, content_type: str) -> str:
    if "pdf" in content_type:
        reader = pypdf.PdfReader(io.BytesIO(content))
        return "\n".join(p.extract_text() or "" for p in reader.pages)
    return content.decode("utf-8", errors="replace")


def build_doc_prompt(document_text: str, question: str,
                     max_doc_chars: int = MAX_DOC_CHARS) -> str:
    snippet = document_text[:max_doc_chars]
    return (
        "You are a helpful assistant. Answer based only on the document below.\n\n"
        f"DOCUMENT:\n{snippet}\n\nQUESTION: {question}"
    )

# --- in-memory store --------------------------------------------------------
_docs: dict[str, dict] = {}

# --- app --------------------------------------------------------------------
app = FastAPI(title="Doc Upload AI API", version=APP_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": APP_VERSION,
    }


@app.post("/upload", status_code=201)
async def upload_doc(file: UploadFile = File(...)):
    content = await file.read()
    ok, err = validate_upload(
        content, file.filename or "unnamed",
        ALLOWED_TYPES, file.content_type or "", MAX_SIZE
    )
    if not ok:
        raise HTTPException(status_code=400, detail=err)
    text   = extract_text(content, file.content_type or "text/plain")
    doc_id = secrets.token_urlsafe(8)
    _docs[doc_id] = {"filename": file.filename, "text": text}
    save_upload(content, file.filename or "unnamed", UPLOAD_DIR)
    return {"doc_id": doc_id, "filename": file.filename, "chars": len(text)}


@app.get("/documents")
def list_documents():
    return {"documents": [{"doc_id": k, "filename": v["filename"]}
                          for k, v in _docs.items()]}


@app.post("/ask/{doc_id}")
def ask(doc_id: str, question: str):
    entry = _docs.get(doc_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Document not found")
    prompt = build_doc_prompt(entry["text"], question)
    reply  = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}]
    )["message"]["content"]
    return {"reply": reply, "doc_id": doc_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
