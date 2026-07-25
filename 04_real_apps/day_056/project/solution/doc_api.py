"""doc_api.py — Day 056 project: FastAPI with file upload + AI Q&A.

Run:  uvicorn doc_api:app --reload
Docs: http://localhost:8000/docs
"""
import io
import re
import secrets
from pathlib import Path
from typing import Annotated

import pypdf
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import ollama

# --- config ---------------------------------------------------------------
UPLOAD_DIR  = Path("uploads")
ALLOWED_TYPES = {"text/plain", "application/pdf"}
MAX_SIZE    = 5 * 1024 * 1024   # 5 MB
MAX_DOC_CHARS = 4000             # chars sent to LLM
MODEL = "llama3.2"

# --- helpers --------------------------------------------------------------

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
    if content_type == "application/pdf" or content_type.endswith("pdf"):
        reader = pypdf.PdfReader(io.BytesIO(content))
        return "\n".join(p.extract_text() or "" for p in reader.pages)
    return content.decode("utf-8", errors="replace")


def build_doc_prompt(document_text: str, question: str,
                     max_doc_chars: int = MAX_DOC_CHARS) -> str:
    snippet = document_text[:max_doc_chars]
    return (
        "You are a helpful assistant. Answer the question based only on the "
        "document below. If the answer is not in the document, say so.\n\n"
        f"DOCUMENT:\n{snippet}\n\n"
        f"QUESTION: {question}"
    )

# --- in-memory store ------------------------------------------------------
_docs: dict[str, dict] = {}   # doc_id -> {filename, text}

# --- app ------------------------------------------------------------------
app = FastAPI(title="Doc Upload AI API", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    reply  = ollama.chat(model=MODEL,
                         messages=[{"role": "user", "content": prompt}])["message"]["content"]
    return {"reply": reply, "doc_id": doc_id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
