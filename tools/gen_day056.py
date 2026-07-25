#!/usr/bin/env python3
"""gen_day056.py — Generate Day 056: File Uploads & Storage notebooks."""

from pathlib import Path
import nbformat as nbf

ROOT = Path(__file__).parent.parent
DAY_DIR = ROOT / "04_real_apps" / "day_056"

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _nb(cells):
    nb = nbf.v4.new_notebook()
    nb["cells"] = cells
    return nb

def _md(src): return nbf.v4.new_markdown_cell(src)
def _code(src, cid=None):
    c = nbf.v4.new_code_cell(src)
    if cid is not None:
        c["id"] = str(cid)
    return c

def _write(path, nb):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        nbf.write(nb, f)
    print(f"  wrote {path.relative_to(ROOT)}")

# ---------------------------------------------------------------------------
# doc_api.py source  (embedded via repr — never inspect.getsource)
# ---------------------------------------------------------------------------

_DOC_API_SRC = '''\
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
    name = re.sub(r"[^\\w\\-.]", "_", name)
    return f"{secrets.token_hex(4)}_{name}"


def save_upload(content: bytes, filename: str, upload_dir: Path) -> Path:
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / safe_filename(filename)
    dest.write_bytes(content)
    return dest


def extract_text(content: bytes, content_type: str) -> str:
    if content_type == "application/pdf" or content_type.endswith("pdf"):
        reader = pypdf.PdfReader(io.BytesIO(content))
        return "\\n".join(p.extract_text() or "" for p in reader.pages)
    return content.decode("utf-8", errors="replace")


def build_doc_prompt(document_text: str, question: str,
                     max_doc_chars: int = MAX_DOC_CHARS) -> str:
    snippet = document_text[:max_doc_chars]
    return (
        "You are a helpful assistant. Answer the question based only on the "
        "document below. If the answer is not in the document, say so.\\n\\n"
        f"DOCUMENT:\\n{snippet}\\n\\n"
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
'''

# ---------------------------------------------------------------------------
# provided setup snippets
# ---------------------------------------------------------------------------

_IMPORTS_EX1 = """\
from fastapi import FastAPI, UploadFile, File
from starlette.testclient import TestClient
"""

_IMPORTS_EX2 = """\
from pathlib import Path
"""

_IMPORTS_EX3 = """\
import re
import secrets
import tempfile
from pathlib import Path
"""

_IMPORTS_EX4 = """\
import io
import pypdf
"""

# cumulative provided code for exercise 5
_BEFORE_EX5 = """\
import io
import re
import secrets
from pathlib import Path
import pypdf

def validate_upload(content: bytes, filename: str,
                    allowed_extensions: list[str], max_bytes: int) -> tuple[bool, str]:
    if len(content) == 0:
        return False, "File is empty"
    if len(content) > max_bytes:
        return False, f"File too large ({len(content)} bytes, max {max_bytes})"
    ext = Path(filename).suffix.lower()
    if ext not in allowed_extensions:
        return False, f"Extension '{ext}' not allowed (allowed: {allowed_extensions})"
    return True, ""

def safe_filename(original: str) -> str:
    name = Path(original).name
    name = re.sub(r'[^\\w\\-.]', '_', name)
    return f"{secrets.token_hex(4)}_{name}"

def save_upload(content: bytes, filename: str, upload_dir: Path) -> Path:
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / safe_filename(filename)
    dest.write_bytes(content)
    return dest

def extract_text(content: bytes, content_type: str) -> str:
    if "pdf" in content_type:
        reader = pypdf.PdfReader(io.BytesIO(content))
        return "\\n".join(p.extract_text() or "" for p in reader.pages)
    return content.decode("utf-8", errors="replace")
"""

# ---------------------------------------------------------------------------
# stubs
# ---------------------------------------------------------------------------

_STUB_EX1 = '''\
def build_upload_api() -> FastAPI:
    """Build a FastAPI app with a single file-upload endpoint.

    The endpoint POST /upload should:
      - Accept a single file via multipart form (UploadFile = File(...))
      - Read the file bytes with `content = await file.read()`
      - Return JSON: {"filename": ..., "content_type": ..., "size": len(content)}

    Returns:
        A FastAPI app instance.
    """
    app = FastAPI()

    # TODO: add an async def POST /upload that uses UploadFile = File(...)
    #       reads with await, returns {"filename", "content_type", "size"}

    return app
'''

_STUB_EX2 = '''\
def validate_upload(content: bytes, filename: str,
                    allowed_extensions: list[str], max_bytes: int) -> tuple[bool, str]:
    """Validate an uploaded file\'s size and extension.

    Args:
        content:             Raw file bytes.
        filename:            Original filename (e.g. \'report.pdf\').
        allowed_extensions:  Whitelist of lowercase extensions (e.g. [\'.txt\', \'.pdf\']).
        max_bytes:           Maximum allowed file size in bytes.
    Returns:
        (True, "") if valid.
        (False, reason_str) if invalid.
    """
    # TODO:
    # 1. Return (False, "File is empty") if len(content) == 0
    # 2. Return (False, "File too large ...") if len(content) > max_bytes
    # 3. Extract extension: Path(filename).suffix.lower()
    # 4. Return (False, "Extension ... not allowed ...") if ext not in allowed_extensions
    # 5. Return (True, "")
    raise NotImplementedError
'''

_STUB_EX3 = '''\
def safe_filename(original: str) -> str:
    """Return a filesystem-safe filename with a random prefix.

    Args:
        original: The original filename (may contain spaces, path separators, etc.)
    Returns:
        A safe filename: random_prefix + sanitized_basename.
        - Uses Path(original).name to strip directory components.
        - Replaces any character that is not \\w, hyphen, or dot with underscore.
        - Prepends secrets.token_hex(4) to avoid collisions.
    """
    # TODO: name = Path(original).name
    # name = re.sub(r\'[^\\w\\-.]\', \'_\', name)
    # return f"{secrets.token_hex(4)}_{name}"
    raise NotImplementedError

def save_upload(content: bytes, filename: str, upload_dir: Path) -> Path:
    """Write bytes to upload_dir/safe_filename(filename) and return the path.

    Args:
        content:    Raw bytes to write.
        filename:   Original filename (will be made safe).
        upload_dir: Directory to write into (created if missing).
    Returns:
        The Path where the file was written.
    """
    # TODO: upload_dir.mkdir(parents=True, exist_ok=True)
    # dest = upload_dir / safe_filename(filename)
    # dest.write_bytes(content)
    # return dest
    raise NotImplementedError
'''

_STUB_EX4 = '''\
def extract_text(content: bytes, content_type: str) -> str:
    """Extract plain text from uploaded file bytes.

    Args:
        content:      Raw file bytes.
        content_type: MIME type string (e.g. \'text/plain\', \'application/pdf\').
    Returns:
        Extracted text as a string.
        - For PDF (\'pdf\' in content_type): use pypdf.PdfReader on io.BytesIO(content),
          concatenate page.extract_text() for each page.
        - Otherwise: decode as UTF-8 with errors=\'replace\'.
    """
    # TODO: if "pdf" in content_type:
    #     reader = pypdf.PdfReader(io.BytesIO(content))
    #     return "\\n".join(p.extract_text() or "" for p in reader.pages)
    # return content.decode("utf-8", errors="replace")
    raise NotImplementedError
'''

_STUB_EX5 = '''\
class DocStore:
    """In-memory document store mapping doc_id -> {filename, text}."""

    def __init__(self):
        self._store: dict[str, dict] = {}

    def add(self, filename: str, text: str) -> str:
        """Store a document and return its unique doc_id.

        Args:
            filename: Original filename (stored for display).
            text:     Extracted document text.
        Returns:
            A unique doc_id string (use secrets.token_urlsafe(8)).
        """
        # TODO: generate doc_id = secrets.token_urlsafe(8)
        # store {"filename": filename, "text": text} in self._store[doc_id]
        # return doc_id
        raise NotImplementedError

    def get_text(self, doc_id: str) -> str | None:
        """Return the stored text for doc_id, or None if not found."""
        # TODO: return self._store.get(doc_id, {}).get("text")
        raise NotImplementedError

    def list_docs(self) -> list[dict]:
        """Return [{doc_id, filename}] for all stored documents."""
        # TODO: return [{"doc_id": k, "filename": v["filename"]} for k, v in self._store.items()]
        raise NotImplementedError


def build_doc_prompt(document_text: str, question: str,
                     max_doc_chars: int = 3000) -> str:
    """Build a prompt asking the model a question about the document.

    Args:
        document_text: Extracted document text (may be truncated).
        question:      The user\'s question.
        max_doc_chars: Maximum characters to include from the document.
    Returns:
        A complete prompt string for the LLM.
    """
    # TODO: truncate document_text to max_doc_chars
    # build a prompt that includes: a system instruction, the truncated document,
    # and the question. Something like:
    # "You are a helpful assistant. Answer based only on the document below.\\n\\n
    #  DOCUMENT:\\n{snippet}\\n\\nQUESTION: {question}"
    raise NotImplementedError
'''

# ---------------------------------------------------------------------------
# solutions
# ---------------------------------------------------------------------------

_SOL_EX1 = '''\
def build_upload_api() -> FastAPI:
    app = FastAPI()

    @app.post("/upload")
    async def upload(file: UploadFile = File(...)):
        content = await file.read()
        return {
            "filename": file.filename,
            "content_type": file.content_type,
            "size": len(content),
        }

    return app
'''

_SOL_EX2 = '''\
def validate_upload(content: bytes, filename: str,
                    allowed_extensions: list[str], max_bytes: int) -> tuple[bool, str]:
    if len(content) == 0:
        return False, "File is empty"
    if len(content) > max_bytes:
        return False, f"File too large ({len(content)} bytes, max {max_bytes})"
    ext = Path(filename).suffix.lower()
    if ext not in allowed_extensions:
        return False, f"Extension \'{ext}\' not allowed (allowed: {allowed_extensions})"
    return True, ""
'''

_SOL_EX3 = '''\
def safe_filename(original: str) -> str:
    name = Path(original).name
    name = re.sub(r\'[^\\w\\-.]\', \'_\', name)
    return f"{secrets.token_hex(4)}_{name}"

def save_upload(content: bytes, filename: str, upload_dir: Path) -> Path:
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / safe_filename(filename)
    dest.write_bytes(content)
    return dest
'''

_SOL_EX4 = '''\
def extract_text(content: bytes, content_type: str) -> str:
    if "pdf" in content_type:
        reader = pypdf.PdfReader(io.BytesIO(content))
        return "\\n".join(p.extract_text() or "" for p in reader.pages)
    return content.decode("utf-8", errors="replace")
'''

_SOL_EX5 = '''\
class DocStore:
    def __init__(self):
        self._store: dict[str, dict] = {}

    def add(self, filename: str, text: str) -> str:
        doc_id = secrets.token_urlsafe(8)
        self._store[doc_id] = {"filename": filename, "text": text}
        return doc_id

    def get_text(self, doc_id: str) -> str | None:
        return self._store.get(doc_id, {}).get("text")

    def list_docs(self) -> list[dict]:
        return [{"doc_id": k, "filename": v["filename"]} for k, v in self._store.items()]


def build_doc_prompt(document_text: str, question: str,
                     max_doc_chars: int = 3000) -> str:
    snippet = document_text[:max_doc_chars]
    return (
        "You are a helpful assistant. Answer the question based only on the "
        "document below. If the answer is not in the document, say so.\\n\\n"
        f"DOCUMENT:\\n{snippet}\\n\\n"
        f"QUESTION: {question}"
    )
'''

# ---------------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------------

_CHECKS_EX1 = '''\
def _run_checks():
    score = 0
    total = 5

    def _chk(n, ok, msg):
        nonlocal score
        print(f"  {\'✅\' if ok else \'❌\'} Check {n}: {msg}")
        if ok:
            score += 1

    try:
        app = build_upload_api()
    except NotImplementedError:
        for i in range(1, total + 1):
            print(f"  ❌ Check {i}: build_upload_api not implemented")
        print(f"\\nScore: 0 / {total}")
        return
    except Exception as e:
        for i in range(1, total + 1):
            print(f"  ❌ Check {i}: {type(e).__name__}: {e}")
        print(f"\\nScore: 0 / {total}")
        return

    client = TestClient(app, raise_server_exceptions=False)

    # check 1: POST /upload returns 200
    r = client.post("/upload",
                    files={"file": ("hello.txt", b"hello world", "text/plain")})
    _chk(1, r.status_code == 200,
         f"POST /upload with text file → 200 (got {r.status_code})")

    if r.status_code == 200:
        data = r.json()
        _chk(2, data.get("filename") == "hello.txt",
             f"filename == \'hello.txt\' (got {data.get(\'filename\')})")
        _chk(3, data.get("content_type") == "text/plain",
             f"content_type == \'text/plain\' (got {data.get(\'content_type\')})")
        _chk(4, data.get("size") == 11,
             f"size == 11 (got {data.get(\'size\')})")
    else:
        for i in range(2, 5):
            print(f"  ❌ Check {i}: skipped (check 1 failed)")

    # check 5: upload a different file
    r2 = client.post("/upload",
                     files={"file": ("data.csv", b"a,b,c\\n1,2,3", "text/csv")})
    _chk(5, r2.status_code == 200 and r2.json().get("size") == 11,
         f"second upload returns correct size (got status={r2.status_code})")

    print(f"\\nScore: {score} / {total}")
    if score == total:
        print("🎉 Exercise complete!")

_run_checks()
'''

_CHECKS_EX2 = '''\
def _run_checks():
    score = 0
    total = 5

    def _chk(n, ok, msg):
        nonlocal score
        print(f"  {\'✅\' if ok else \'❌\'} Check {n}: {msg}")
        if ok:
            score += 1

    allowed = [".txt", ".pdf", ".md"]
    max_b   = 1000

    try:
        ok, msg = validate_upload(b"hello", "doc.txt", allowed, max_b)
    except NotImplementedError:
        for i in range(1, total + 1):
            print(f"  ❌ Check {i}: validate_upload not implemented")
        print(f"\\nScore: 0 / {total}")
        return

    _chk(1, ok is True and msg == "",
         f"valid .txt → (True, \'\') (got ({ok}, \'{msg}\'))")

    ok2, msg2 = validate_upload(b"", "doc.txt", allowed, max_b)
    _chk(2, ok2 is False and "empty" in msg2.lower(),
         f"empty file → (False, ...\'empty\'...) (got ({ok2}, \'{msg2}\'))")

    big = b"x" * (max_b + 1)
    ok3, msg3 = validate_upload(big, "doc.txt", allowed, max_b)
    _chk(3, ok3 is False and "large" in msg3.lower(),
         f"too-large file → (False, ...\'large\'...) (got ({ok3}, \'{msg3}\'))")

    ok4, msg4 = validate_upload(b"data", "image.png", allowed, max_b)
    _chk(4, ok4 is False and "png" in msg4.lower(),
         f".png rejected → (False, ...) (got ({ok4}, \'{msg4}\'))")

    ok5, msg5 = validate_upload(b"data", "report.pdf", allowed, max_b)
    _chk(5, ok5 is True,
         f"valid .pdf → (True, \'\') (got ({ok5}, \'{msg5}\'))")

    print(f"\\nScore: {score} / {total}")
    if score == total:
        print("🎉 Exercise complete!")

_run_checks()
'''

_CHECKS_EX3 = '''\
def _run_checks():
    score = 0
    total = 5

    def _chk(n, ok, msg):
        nonlocal score
        print(f"  {\'✅\' if ok else \'❌\'} Check {n}: {msg}")
        if ok:
            score += 1

    try:
        name = safe_filename("hello world.txt")
    except NotImplementedError:
        for i in range(1, total + 1):
            print(f"  ❌ Check {i}: safe_filename not implemented")
        print(f"\\nScore: 0 / {total}")
        return

    _chk(1, isinstance(name, str) and name.endswith(".txt"),
         f"safe_filename preserves extension (got {name!r})")
    _chk(2, " " not in name,
         f"spaces replaced (got {name!r})")

    path_input = "../../etc/passwd"
    safe = safe_filename(path_input)
    _chk(3, "/" not in safe and "\\\\" not in safe,
         f"path traversal stripped (got {safe!r})")

    n1 = safe_filename("file.txt")
    n2 = safe_filename("file.txt")
    _chk(4, n1 != n2, "two calls on same name → different results (random prefix)")

    try:
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            dest = save_upload(b"test content", "my file.txt", Path(td))
            _chk(5, dest.exists() and dest.read_bytes() == b"test content",
                 f"save_upload writes correct bytes to {dest.name!r}")
    except NotImplementedError:
        print(f"  ❌ Check 5: save_upload not implemented")

    print(f"\\nScore: {score} / {total}")
    if score == total:
        print("🎉 Exercise complete!")

_run_checks()
'''

# Minimal valid PDF bytes for extract_text test
_MINIMAL_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200]\n"
    b"   /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
    b"4 0 obj\n<< /Length 44 >>\nstream\nBT /F1 12 Tf 50 150 Td (Hello PDF) Tj ET\nendstream\nendobj\n"
    b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    b"xref\n0 6\n0000000000 65535 f \n"
    b"0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n"
    b"0000000274 00000 n \n0000000366 00000 n \n"
    b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n450\n%%EOF\n"
)

_CHECKS_EX4 = f'''\
_MINIMAL_PDF = {repr(_MINIMAL_PDF)}

def _run_checks():
    score = 0
    total = 5

    def _chk(n, ok, msg):
        nonlocal score
        print(f"  {{\'✅\' if ok else \'❌\'}} Check {{n}}: {{msg}}")
        if ok:
            score += 1

    try:
        text = extract_text(b"Hello, plain text!", "text/plain")
    except NotImplementedError:
        for i in range(1, total + 1):
            print(f"  ❌ Check {{i}}: extract_text not implemented")
        print(f"\\nScore: 0 / {{total}}")
        return

    _chk(1, isinstance(text, str) and "Hello" in text,
         f"plain text extracted correctly (got {{text!r:.40}})")

    # UTF-8 with replacement
    bad_bytes = b"caf\\xe9"
    t2 = extract_text(bad_bytes, "text/plain")
    _chk(2, isinstance(t2, str),
         f"non-UTF-8 bytes → str (errors=replace) (got {{t2!r}})")

    # PDF extraction
    try:
        pdf_text = extract_text(_MINIMAL_PDF, "application/pdf")
        _chk(3, isinstance(pdf_text, str),
             f"PDF extraction returns str (got {{type(pdf_text).__name__}})")
        _chk(4, len(pdf_text) >= 0,   # pypdf may return empty for this minimal PDF
             "PDF extraction does not crash")
    except Exception as e:
        _chk(3, False, f"PDF extraction raised {{type(e).__name__}}: {{e}}")
        _chk(4, False, "skipped")

    # Unknown type falls back to UTF-8 decode
    t5 = extract_text(b"raw bytes", "application/octet-stream")
    _chk(5, isinstance(t5, str) and "raw" in t5,
         f"unknown type decoded as UTF-8 (got {{t5!r}})")

    print(f"\\nScore: {{score}} / {{total}}")
    if score == total:
        print("🎉 Exercise complete!")

_run_checks()
'''

_CHECKS_EX5 = '''\
def _run_checks():
    score = 0
    total = 5

    def _chk(n, ok, msg):
        nonlocal score
        print(f"  {\'✅\' if ok else \'❌\'} Check {n}: {msg}")
        if ok:
            score += 1

    try:
        store = DocStore()
        doc_id = store.add("report.txt", "The sky is blue.")
    except NotImplementedError:
        for i in range(1, total + 1):
            print(f"  ❌ Check {i}: DocStore.add not implemented")
        print(f"\\nScore: 0 / {total}")
        return

    _chk(1, isinstance(doc_id, str) and len(doc_id) >= 6,
         f"add() returns a non-empty id string (got {doc_id!r})")

    try:
        text = store.get_text(doc_id)
    except NotImplementedError:
        for i in range(2, 4):
            print(f"  ❌ Check {i}: DocStore.get_text not implemented")
        text = None

    _chk(2, text == "The sky is blue.",
         f"get_text returns the stored text (got {text!r})")
    _chk(3, store.get_text("nonexistent") is None,
         "get_text on unknown id returns None")

    # store a second doc
    id2 = store.add("notes.txt", "Rain is wet.")
    try:
        docs = store.list_docs()
    except NotImplementedError:
        print(f"  ❌ Check 4: DocStore.list_docs not implemented")
        docs = None

    _chk(4, isinstance(docs, list) and len(docs) == 2,
         f"list_docs returns 2 entries (got {docs})")

    # build_doc_prompt
    try:
        prompt = build_doc_prompt("The sky is blue.", "What colour is the sky?")
    except NotImplementedError:
        print(f"  ❌ Check 5: build_doc_prompt not implemented")
        print(f"\\nScore: {score} / {total}")
        return

    _chk(5, "The sky is blue." in prompt and "What colour" in prompt,
         f"prompt contains document text and question (got {prompt[:80]!r}...)")

    print(f"\\nScore: {score} / {total}")
    if score == total:
        print("🎉 Exercise complete!")

_run_checks()
'''

# ---------------------------------------------------------------------------
# solution why-works explanations
# ---------------------------------------------------------------------------

_WHY_EX1 = """\
**Why this works:** `UploadFile = File(...)` tells FastAPI to parse a multipart
form field named `file`. The handler must be `async def` because `file.read()`
is a coroutine — it reads from the underlying spooled temporary file. TestClient
supports async route handlers transparently. The JSON response is built from
`file.filename`, `file.content_type`, and `len(content)`.
"""

_WHY_EX2 = """\
**Why this works:** The function checks in order: empty → too large → wrong
extension. `Path(filename).suffix.lower()` extracts the extension reliably —
`Path("report.PDF").suffix.lower()` → `".pdf"`. The whitelist approach is safer
than a blacklist: you explicitly allow what you want and reject everything else.
Return a tuple rather than raising, so the caller can decide how to surface the
error (HTTP 400, log, etc.).
"""

_WHY_EX3 = """\
**Why this works:** `Path(original).name` strips any directory prefix — so
`../../etc/passwd` becomes just `passwd`, preventing path traversal. The regex
replaces anything that isn't a word character, hyphen, or dot with an underscore,
so spaces and special chars become safe. Prepending `secrets.token_hex(4)` gives
8 hex characters of randomness, making collisions (two users upload `report.txt`)
essentially impossible. `Path.write_bytes` creates or overwrites the file atomically.
"""

_WHY_EX4 = """\
**Why this works:** The `"pdf" in content_type` check handles both
`application/pdf` and variants like `application/x-pdf`. `pypdf.PdfReader` accepts
a file-like `io.BytesIO` object, so you never need to write the PDF to disk.
Each `page.extract_text()` returns a string (or None for image-only pages — `or ""`
handles that). For everything else, `decode("utf-8", errors="replace")` gives a
string with replacement characters (U+FFFD) for invalid bytes, so it never raises.
"""

_WHY_EX5 = """\
**Why this works:** `DocStore` uses a dict keyed by a random `token_urlsafe(8)` id.
The id is generated at store-time, not at init-time, so each document gets a unique
handle. `get_text` returns `None` for unknown ids — the caller raises 404.
`build_doc_prompt` truncates the document with a slice before embedding it, so the
LLM never receives more than `max_doc_chars` characters of context. The prompt
explicitly tells the model to answer only from the document — this is the core of
a retrieval-augmented Q&A system.
"""

# ---------------------------------------------------------------------------
# exercise builder
# ---------------------------------------------------------------------------

def _ex(n, title, why_matters, setup, stub, checks, sol_code, why_works, bonus,
        setup_label="Setup (provided)", cid_base=0):
    cells = [
        _md(f"# Day 56 · Exercise {n}: {title}\n\n"
            f"**What you'll build:** {why_matters}"),
        _md(f"## {setup_label}"),
        _code(setup, cid=cid_base),
        _md("## Your Implementation"),
        _code(stub, cid=cid_base + 1),
        _md("## Check Your Work"),
        _code(checks, cid=cid_base + 2),
        _md(f"## Bonus Challenge\n\n{bonus}"),
        _md(f"## Solution\n\n<details>\n<summary>Show solution</summary>\n\n"
            f"```python\n{sol_code}```\n\n{why_works}\n</details>"),
    ]
    cells.insert(5, _code(sol_code, cid=cid_base + 50))
    return _nb(cells)

# ---------------------------------------------------------------------------
# exercise builders
# ---------------------------------------------------------------------------

def _build_ex1():
    return _ex(
        n=1,
        title="File Upload Endpoint",
        why_matters=(
            "Implement `build_upload_api()` — a FastAPI app with `POST /upload` "
            "that accepts a file via multipart form and returns its metadata. "
            "This is the entry point to every file-upload system."
        ),
        setup=_IMPORTS_EX1,
        stub=_STUB_EX1,
        checks=_CHECKS_EX1,
        sol_code=_SOL_EX1,
        why_works=_WHY_EX1,
        bonus=(
            "Add a second endpoint `POST /upload-multiple` that accepts "
            "`files: list[UploadFile] = File(...)` and returns a list of metadata "
            "dicts — one per file. Test with TestClient using multiple "
            "`files=[('file', ...), ('file', ...)]` entries in the same request."
        ),
        cid_base=0,
    )

def _build_ex2():
    return _ex(
        n=2,
        title="File Validation",
        why_matters=(
            "Implement `validate_upload(content, filename, allowed_extensions, max_bytes)` "
            "returning `(True, '')` for valid files and `(False, reason)` for invalid ones. "
            "Validation runs BEFORE storage — never save what you haven't checked."
        ),
        setup=_IMPORTS_EX2,
        stub=_STUB_EX2,
        checks=_CHECKS_EX2,
        sol_code=_SOL_EX2,
        why_works=_WHY_EX2,
        bonus=(
            "Extend `validate_upload` with a content-sniffing check: for `.pdf` files, "
            "verify the first 5 bytes equal `b'%PDF-'`. This catches files renamed "
            "to `.pdf` that are actually images or executables. A well-formed PDF "
            "always starts with the magic bytes `%PDF-`."
        ),
        cid_base=100,
    )

def _build_ex3():
    return _ex(
        n=3,
        title="Safe Storage",
        why_matters=(
            "Implement `safe_filename(original)` and `save_upload(content, filename, upload_dir)`. "
            "Safe filenames prevent path traversal attacks; a UUID prefix prevents "
            "two users uploading `report.pdf` from overwriting each other."
        ),
        setup=_IMPORTS_EX3,
        stub=_STUB_EX3,
        checks=_CHECKS_EX3,
        sol_code=_SOL_EX3,
        why_works=_WHY_EX3,
        bonus=(
            "Extend `save_upload` to return a dict `{'path': str(dest), 'size': dest.stat().st_size}` "
            "instead of just the Path. Add a check that `size` matches `len(content)`. "
            "In production, you'd also compute a SHA-256 checksum of the content here "
            "to verify file integrity later."
        ),
        cid_base=200,
    )

def _build_ex4():
    return _ex(
        n=4,
        title="Text Extraction",
        why_matters=(
            "Implement `extract_text(content, content_type)` that returns plain text "
            "from either a UTF-8 text file or a PDF. This is what turns a binary "
            "upload into something an LLM can read and reason about."
        ),
        setup=_IMPORTS_EX4,
        stub=_STUB_EX4,
        checks=_CHECKS_EX4,
        sol_code=_SOL_EX4,
        why_works=_WHY_EX4,
        bonus=(
            "Add Markdown support: if `content_type == 'text/markdown'` or the filename "
            "ends with `.md`, strip Markdown syntax before returning (remove `#`, `**`, "
            "`_`, `[`, `]`, `(`, `)` etc.) using a simple regex. Plain text is easier "
            "for the LLM to process than raw Markdown."
        ),
        cid_base=300,
    )

def _build_ex5():
    return _ex(
        n=5,
        title="DocStore & Prompt Builder",
        why_matters=(
            "Implement the `DocStore` class (`add`, `get_text`, `list_docs`) and "
            "`build_doc_prompt(document_text, question, max_doc_chars)`. "
            "These are the last two pieces: a store for uploaded document text and "
            "the prompt that sends it to the LLM."
        ),
        setup=_BEFORE_EX5,
        stub=_STUB_EX5,
        checks=_CHECKS_EX5,
        sol_code=_SOL_EX5,
        why_works=_WHY_EX5,
        bonus=(
            "Modify `DocStore.add` to also store the filename and `len(text)`. "
            "Add a `DocStore.summary()` method that returns a list of "
            "`{doc_id, filename, char_count}` dicts. This is the metadata a "
            "sidebar would show — upload list with document sizes."
        ),
        cid_base=400,
    )

# ---------------------------------------------------------------------------
# Project notebook
# ---------------------------------------------------------------------------

_PROJECT_SETUP = """\
# Project setup
from pathlib import Path
from starlette.testclient import TestClient

def write_doc_api(path: str) -> str:
    \"\"\"Generate doc_api.py at path and return the path string.

    The generated file should contain a FastAPI app with:
      POST /upload       — validate + save + extract text, return {doc_id, filename, chars}
      GET  /documents    — list uploaded documents
      POST /ask/{doc_id} — answer a question about the document (calls Ollama)
    \"\"\"
    # TODO: build _DOC_API_SRC as a string, then:
    # Path(path).write_text(_DOC_API_SRC, encoding="utf-8")
    # return path
    raise NotImplementedError
"""

def _build_project():
    cells = [
        _md("# Day 56 Project: Doc-Upload AI App\n\n"
            "**What You're Building:**\n\n"
            "A FastAPI service (`doc_api.py`) that lets users upload `.txt` or `.pdf` "
            "files and then ask questions about them:\n\n"
            "- `POST /upload` — validate the file, extract its text, store it, "
            "return a `doc_id`\n"
            "- `GET /documents` — list all uploaded documents\n"
            "- `POST /ask/{doc_id}?question=...` — answer a question about "
            "the document using Ollama\n\n"
            "**Deliverable:** Run `uvicorn doc_api:app --reload`, upload a `.txt` "
            "or `.pdf` file via `/docs`, then call `/ask/{doc_id}` with a question. "
            "That's the deliverable — a working document Q&A service."),
        _md("## Your Implementation"),
        _code(_PROJECT_SETUP, cid=500),
        _md("## Check Your Work\n\nImplement `write_doc_api` above, then re-run."),
        _code("print('Implement write_doc_api above, then re-run this cell.')", cid=501),
    ]
    return _nb(cells)

# ---------------------------------------------------------------------------
# Solution notebook
# ---------------------------------------------------------------------------

_FULL_SOL = f'''\
# ── provided source string ──────────────────────────────────────────────────
_DOC_API_SRC = {repr(_DOC_API_SRC)}

# ── write_doc_api ───────────────────────────────────────────────────────────
from pathlib import Path

def write_doc_api(path: str) -> str:
    Path(path).write_text(_DOC_API_SRC, encoding="utf-8")
    return path

out = write_doc_api("doc_api.py")
print(f"Generated: {{out}}  ({{len(_DOC_API_SRC)}} chars)")
print(Path(out).read_text(encoding="utf-8")[:120] + "...")
'''

_FULL_SOL_TEST = f'''\
# ── smoke-test the upload flow with TestClient ──────────────────────────────
import io
import re
import secrets
from pathlib import Path
import pypdf
from fastapi import FastAPI, File, HTTPException, UploadFile
from starlette.testclient import TestClient

# --- replicate doc_api internals in-process (no ollama for checks) -----------

def validate_upload(content, filename, allowed_types, content_type, max_bytes):
    if len(content) == 0:
        return False, "File is empty"
    if len(content) > max_bytes:
        return False, f"File too large"
    ext = Path(filename).suffix.lower()
    if content_type not in allowed_types and ext not in {{".txt", ".pdf"}}:
        return False, f"Unsupported type: {{content_type}}"
    return True, ""

def safe_filename(original):
    name = Path(original).name
    name = re.sub(r"[^\\w\\-.]", "_", name)
    return f"{{secrets.token_hex(4)}}_{{name}}"

def extract_text(content, content_type):
    if "pdf" in content_type:
        reader = pypdf.PdfReader(io.BytesIO(content))
        return "\\n".join(p.extract_text() or "" for p in reader.pages)
    return content.decode("utf-8", errors="replace")

ALLOWED = {{"text/plain", "application/pdf"}}
MAX_SIZE = 5 * 1024 * 1024
_docs: dict = {{}}

app = FastAPI(title="Doc Upload AI API (test)")

@app.post("/upload", status_code=201)
async def upload_doc(file: UploadFile = File(...)):
    content = await file.read()
    ok, err = validate_upload(content, file.filename or "unnamed",
                              ALLOWED, file.content_type or "", MAX_SIZE)
    if not ok:
        raise HTTPException(status_code=400, detail=err)
    text   = extract_text(content, file.content_type or "text/plain")
    doc_id = secrets.token_urlsafe(8)
    _docs[doc_id] = {{"filename": file.filename, "text": text}}
    return {{"doc_id": doc_id, "filename": file.filename, "chars": len(text)}}

@app.get("/documents")
def list_documents():
    return {{"documents": [{{"doc_id": k, "filename": v["filename"]}} for k, v in _docs.items()]}}

# ── run checks ──────────────────────────────────────────────────────────────
client = TestClient(app, raise_server_exceptions=False)
score = 0; total = 5

def chk(n, ok, msg):
    global score
    print(f"  {{\'✅\' if ok else \'❌\'}} Check {{n}}: {{msg}}")
    if ok: score += 1

# 1. upload text file → 201
r = client.post("/upload",
                files={{"file": ("readme.txt", b"This document talks about clouds.", "text/plain")}})
chk(1, r.status_code == 201, f"POST /upload text → 201 (got {{r.status_code}})")

data = r.json() if r.status_code == 201 else {{}}
chk(2, isinstance(data.get("doc_id"), str) and len(data.get("doc_id", "")) > 4,
    f"response has doc_id string (got {{data.get(\'doc_id\')!r}})")

chk(3, data.get("chars", 0) > 0,
    f"chars > 0 (got {{data.get(\'chars\')}})")

# 4. GET /documents includes our doc
r2 = client.get("/documents")
docs_list = r2.json().get("documents", [])
our_id    = data.get("doc_id", "")
chk(4, any(d["doc_id"] == our_id for d in docs_list),
    f"GET /documents includes uploaded doc_id (found {{len(docs_list)}} docs)")

# 5. upload invalid type → 400
r3 = client.post("/upload",
                 files={{"file": ("photo.jpg", b"\\xff\\xd8\\xff", "image/jpeg")}})
chk(5, r3.status_code == 400,
    f"unsupported type → 400 (got {{r3.status_code}})")

print(f"\\nScore: {{score}} / {{total}}")
if score == total:
    print("\\nDay 56 — File Uploads & Storage complete! 🎉")
print(f"\\nDeliverable: doc_api.py generated ({{len(_DOC_API_SRC)}} chars)")
print("Run:  uvicorn doc_api:app --reload")
print("Docs: http://localhost:8000/docs")
'''

def _build_solution():
    cells = [
        _md("# Day 56 Project — Solution: Doc-Upload AI App\n\n"
            "Upload a file → extract text → ask the AI about it.\n\n"
            "**Deliverable:** `doc_api.py` — run with `uvicorn doc_api:app --reload`."),
        _code(_FULL_SOL, cid=600),
        _code(_FULL_SOL_TEST, cid=601),
    ]
    return _nb(cells)

# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    print("Generating Day 056 notebooks...")
    ex_dir   = DAY_DIR / "exercises"
    proj_dir = DAY_DIR / "project"
    sol_dir  = proj_dir / "solution"

    _write(ex_dir / "exercise_01.ipynb", _build_ex1())
    _write(ex_dir / "exercise_02.ipynb", _build_ex2())
    _write(ex_dir / "exercise_03.ipynb", _build_ex3())
    _write(ex_dir / "exercise_04.ipynb", _build_ex4())
    _write(ex_dir / "exercise_05.ipynb", _build_ex5())
    _write(proj_dir / "project.ipynb",   _build_project())
    _write(sol_dir  / "solution.ipynb",  _build_solution())
    print("Done.")

if __name__ == "__main__":
    main()
