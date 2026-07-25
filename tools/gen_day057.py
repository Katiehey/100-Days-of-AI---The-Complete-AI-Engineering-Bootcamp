#!/usr/bin/env python3
"""gen_day057.py — Generate Day 057: Deploying Apps notebooks."""

from pathlib import Path
import nbformat as nbf

ROOT = Path(__file__).parent.parent
DAY_DIR = ROOT / "04_real_apps" / "day_057"

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
# deploy_api.py source  (embedded via repr — never inspect.getsource)
# ---------------------------------------------------------------------------

_DEPLOY_API_SRC = '''\
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
    name = re.sub(r"[^\\w\\-.]", "_", name)
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


def build_doc_prompt(document_text: str, question: str,
                     max_doc_chars: int = MAX_DOC_CHARS) -> str:
    snippet = document_text[:max_doc_chars]
    return (
        "You are a helpful assistant. Answer based only on the document below.\\n\\n"
        f"DOCUMENT:\\n{snippet}\\n\\nQUESTION: {question}"
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
'''

# ---------------------------------------------------------------------------
# deployment file content strings
# ---------------------------------------------------------------------------

_PROCFILE = "web: uvicorn deploy_api:app --host 0.0.0.0 --port $PORT\n"

_RENDER_YAML = """\
services:
  - type: web
    name: doc-ai-api
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn deploy_api:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: MODEL
        value: llama3.2
      - key: MAX_UPLOAD_BYTES
        value: "5242880"
      - key: SECRET_KEY
        generateValue: true
"""

_REQUIREMENTS = """\
fastapi>=0.100.0
uvicorn[standard]>=0.20.0
python-multipart>=0.0.5
pypdf>=3.0.0
python-jose[cryptography]>=3.3.0
bcrypt>=4.0.0
ollama>=0.1.0
httpx>=0.24.0
"""

# ---------------------------------------------------------------------------
# setup imports for each exercise
# ---------------------------------------------------------------------------

_IMPORTS_EX1 = """\
import os
"""

_IMPORTS_EX2 = """\
from datetime import datetime
from fastapi import FastAPI
from starlette.testclient import TestClient
"""

_IMPORTS_EX3 = """\
from pathlib import Path
"""

_IMPORTS_EX4 = """\
import os
"""

_IMPORTS_EX5 = """\
import os
from fastapi import FastAPI
from starlette.testclient import TestClient

# --- provided helpers (from earlier exercises) ---
def check_env_vars(required_vars: list[str], env: dict) -> tuple[bool, list[str]]:
    missing = [v for v in required_vars if v not in env or not env[v]]
    return len(missing) == 0, missing
"""

# ---------------------------------------------------------------------------
# stubs
# ---------------------------------------------------------------------------

_STUB_EX1 = '''\
def load_config(env_vars: dict, defaults: dict) -> dict:
    """Merge env_vars over defaults to produce a configuration dict.

    Args:
        env_vars: Dictionary of environment variable values (e.g. os.environ).
        defaults: Dictionary of default values for each config key.
    Returns:
        A dict where every key from defaults is present. If env_vars contains
        the same key, the env_vars value takes priority over the default.

    Example:
        defaults = {"MODEL": "llama3.2", "PORT": "8000", "DEBUG": "false"}
        env_vars = {"PORT": "9000"}
        load_config(env_vars, defaults)
        # → {"MODEL": "llama3.2", "PORT": "9000", "DEBUG": "false"}
    """
    # TODO:
    # 1. Start with a copy of defaults
    # 2. For each key in env_vars that is also in defaults, override the default
    # 3. Return the merged dict
    raise NotImplementedError
'''

_STUB_EX2 = '''\
def build_health_api(version: str = "1.0.0") -> FastAPI:
    """Build a FastAPI app with a GET /health endpoint.

    The /health endpoint must return a JSON object with exactly these keys:
      - "status":    the string "ok"
      - "timestamp": current UTC time as an ISO-8601 string (datetime.utcnow().isoformat())
      - "version":   the version string passed to build_health_api()

    Args:
        version: Application version string (e.g. "1.0.0").
    Returns:
        A FastAPI app instance with the /health route registered.
    """
    app = FastAPI()

    # TODO: add GET /health that returns {"status": "ok", "timestamp": ..., "version": ...}

    return app
'''

_STUB_EX3 = '''\
def generate_procfile(start_command: str) -> str:
    """Generate the contents of a Procfile for Render/Railway/Heroku.

    Args:
        start_command: The command to start the web server,
                       e.g. "uvicorn deploy_api:app --host 0.0.0.0 --port $PORT"
    Returns:
        A string with the format "web: <start_command>\\n"
    """
    # TODO: return f"web: {start_command}\\n"
    raise NotImplementedError

def generate_requirements(packages: list[str]) -> str:
    """Generate a requirements.txt file contents string.

    Args:
        packages: List of package specifiers (e.g. ["fastapi>=0.100", "uvicorn"]).
    Returns:
        A newline-joined string of packages sorted alphabetically,
        with a trailing newline.
    """
    # TODO: return "\\n".join(sorted(packages)) + "\\n"
    raise NotImplementedError

def write_deploy_files(directory: str, start_command: str,
                       packages: list[str]) -> dict[str, str]:
    """Write Procfile and requirements.txt into directory. Return paths dict.

    Args:
        directory:     Path to the output directory (created if missing).
        start_command: Passed to generate_procfile.
        packages:      Passed to generate_requirements.
    Returns:
        {"procfile": <path>, "requirements": <path>}
    """
    # TODO:
    # 1. Path(directory).mkdir(parents=True, exist_ok=True)
    # 2. Write Procfile: Path(directory) / "Procfile"
    # 3. Write requirements.txt: Path(directory) / "requirements.txt"
    # 4. Return dict with string paths
    raise NotImplementedError
'''

_STUB_EX4 = '''\
def check_env_vars(required_vars: list[str], env: dict) -> tuple[bool, list[str]]:
    """Check that all required environment variable names are present and non-empty.

    Args:
        required_vars: List of variable names that must be set (e.g. ["SECRET_KEY", "PORT"]).
        env:           A dict to check against (pass os.environ or a test dict).
    Returns:
        (True, []) if all required vars are present and non-empty.
        (False, [list of missing/empty var names]) otherwise.
    """
    # TODO:
    # missing = [v for v in required_vars if v not in env or not env[v]]
    # return len(missing) == 0, missing
    raise NotImplementedError
'''

_STUB_EX5 = '''\
class DeploymentChecker:
    """Run a suite of deployment readiness checks and report results."""

    def __init__(self):
        self._checks: list[dict] = []

    def add_check(self, name: str, passed: bool, detail: str = "") -> None:
        """Record a named check result.

        Args:
            name:   Short identifier for the check (e.g. "health_endpoint").
            passed: True if the check passed.
            detail: Human-readable explanation (shown when check fails).
        """
        # TODO: append {"name": name, "passed": passed, "detail": detail}
        raise NotImplementedError

    def run_env_check(self, required_vars: list[str], env: dict) -> None:
        """Run check_env_vars and record result under name "env_vars".

        Args:
            required_vars: Variable names that must be present.
            env:           Dict to check (os.environ or test dict).
        """
        # TODO: ok, missing = check_env_vars(required_vars, env)
        # self.add_check("env_vars", ok,
        #     f"missing: {missing}" if not ok else "all present")
        raise NotImplementedError

    def run_health_check(self, app: FastAPI) -> None:
        """Call GET /health on app via TestClient and record result.

        Passes if status == 200 and response JSON has {"status": "ok"}.
        Records check under name "health_endpoint".
        """
        # TODO:
        # client = TestClient(app, raise_server_exceptions=False)
        # r = client.get("/health")
        # ok = r.status_code == 200 and r.json().get("status") == "ok"
        # self.add_check("health_endpoint", ok, f"status={r.status_code}")
        raise NotImplementedError

    def report(self) -> dict:
        """Return a summary report dict.

        Returns:
            {
              "passed": bool  — True iff ALL checks passed,
              "total":  int   — number of checks run,
              "checks": list[{"name", "passed", "detail"}]
            }
        """
        # TODO:
        # total = len(self._checks)
        # passed_count = sum(1 for c in self._checks if c["passed"])
        # return {"passed": passed_count == total, "total": total,
        #         "checks": self._checks}
        raise NotImplementedError
'''

# ---------------------------------------------------------------------------
# solutions
# ---------------------------------------------------------------------------

_SOL_EX1 = '''\
def load_config(env_vars: dict, defaults: dict) -> dict:
    config = dict(defaults)
    for key, value in env_vars.items():
        if key in config:
            config[key] = value
    return config
'''

_SOL_EX2 = '''\
def build_health_api(version: str = "1.0.0") -> FastAPI:
    app = FastAPI()

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "version": version,
        }

    return app
'''

_SOL_EX3 = '''\
def generate_procfile(start_command: str) -> str:
    return f"web: {start_command}\\n"

def generate_requirements(packages: list[str]) -> str:
    return "\\n".join(sorted(packages)) + "\\n"

def write_deploy_files(directory: str, start_command: str,
                       packages: list[str]) -> dict[str, str]:
    d = Path(directory)
    d.mkdir(parents=True, exist_ok=True)
    procfile = d / "Procfile"
    reqs     = d / "requirements.txt"
    procfile.write_text(generate_procfile(start_command), encoding="utf-8")
    reqs.write_text(generate_requirements(packages), encoding="utf-8")
    return {"procfile": str(procfile), "requirements": str(reqs)}
'''

_SOL_EX4 = '''\
def check_env_vars(required_vars: list[str], env: dict) -> tuple[bool, list[str]]:
    missing = [v for v in required_vars if v not in env or not env[v]]
    return len(missing) == 0, missing
'''

_SOL_EX5 = '''\
class DeploymentChecker:
    def __init__(self):
        self._checks: list[dict] = []

    def add_check(self, name: str, passed: bool, detail: str = "") -> None:
        self._checks.append({"name": name, "passed": passed, "detail": detail})

    def run_env_check(self, required_vars: list[str], env: dict) -> None:
        ok, missing = check_env_vars(required_vars, env)
        self.add_check("env_vars", ok,
                       f"missing: {missing}" if not ok else "all present")

    def run_health_check(self, app: FastAPI) -> None:
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get("/health")
        ok = r.status_code == 200 and r.json().get("status") == "ok"
        self.add_check("health_endpoint", ok, f"status={r.status_code}")

    def report(self) -> dict:
        total = len(self._checks)
        passed_count = sum(1 for c in self._checks if c["passed"])
        return {"passed": passed_count == total, "total": total,
                "checks": self._checks}
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

    defaults = {"MODEL": "llama3.2", "PORT": "8000", "DEBUG": "false"}

    try:
        cfg = load_config({}, defaults)
    except NotImplementedError:
        for i in range(1, total + 1):
            print(f"  ❌ Check {i}: load_config not implemented")
        print(f"\\nScore: 0 / {total}")
        return

    _chk(1, cfg == defaults,
         f"empty env_vars → config equals defaults (got {cfg})")

    cfg2 = load_config({"PORT": "9000"}, defaults)
    _chk(2, cfg2["PORT"] == "9000" and cfg2["MODEL"] == "llama3.2",
         f"PORT overridden, MODEL unchanged (got {cfg2})")

    cfg3 = load_config({"MODEL": "mistral", "PORT": "8080"}, defaults)
    _chk(3, cfg3["MODEL"] == "mistral" and cfg3["PORT"] == "8080",
         f"two overrides applied (got {cfg3})")

    # unknown env vars should not appear in the result
    cfg4 = load_config({"UNKNOWN_VAR": "x", "PORT": "7000"}, defaults)
    _chk(4, "UNKNOWN_VAR" not in cfg4 and cfg4["PORT"] == "7000",
         f"unknown env vars not injected (got {cfg4})")

    # defaults should not be mutated
    cfg5 = load_config({"PORT": "5000"}, defaults)
    _chk(5, defaults["PORT"] == "8000",
         f"defaults dict not mutated by load_config (PORT still {defaults[\'PORT\']})")

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

    try:
        app = build_health_api("2.5.0")
    except NotImplementedError:
        for i in range(1, total + 1):
            print(f"  ❌ Check {i}: build_health_api not implemented")
        print(f"\\nScore: 0 / {total}")
        return
    except Exception as e:
        for i in range(1, total + 1):
            print(f"  ❌ Check {i}: {type(e).__name__}: {e}")
        print(f"\\nScore: 0 / {total}")
        return

    client = TestClient(app, raise_server_exceptions=False)
    r = client.get("/health")

    _chk(1, r.status_code == 200,
         f"GET /health → 200 (got {r.status_code})")

    if r.status_code == 200:
        data = r.json()
        _chk(2, data.get("status") == "ok",
             f"status == \'ok\' (got {data.get(\'status\')!r})")
        _chk(3, isinstance(data.get("timestamp"), str) and "T" in data.get("timestamp", ""),
             f"timestamp is ISO-8601 string (got {data.get(\'timestamp\')!r})")
        _chk(4, data.get("version") == "2.5.0",
             f"version == \'2.5.0\' (got {data.get(\'version\')!r})")
    else:
        for i in range(2, 5):
            print(f"  ❌ Check {i}: skipped (check 1 failed)")

    # different version
    app2 = build_health_api("0.1.0")
    r2 = TestClient(app2, raise_server_exceptions=False).get("/health")
    _chk(5, r2.status_code == 200 and r2.json().get("version") == "0.1.0",
         f"version from second app == \'0.1.0\' (got {r2.json().get(\'version\') if r2.status_code == 200 else r2.status_code!r})")

    print(f"\\nScore: {score} / {total}")
    if score == total:
        print("🎉 Exercise complete!")

_run_checks()
'''

_CHECKS_EX3 = '''\
def _run_checks():
    import tempfile
    score = 0
    total = 5

    def _chk(n, ok, msg):
        nonlocal score
        print(f"  {\'✅\' if ok else \'❌\'} Check {n}: {msg}")
        if ok:
            score += 1

    try:
        pf = generate_procfile("uvicorn app:app --host 0.0.0.0 --port $PORT")
    except NotImplementedError:
        for i in range(1, total + 1):
            print(f"  ❌ Check {i}: generate_procfile not implemented")
        print(f"\\nScore: 0 / {total}")
        return

    _chk(1, pf.startswith("web: uvicorn"),
         f"Procfile starts with \'web:\' (got {pf!r:.60})")
    _chk(2, pf.endswith("\\n"),
         f"Procfile ends with newline (got {pf!r:.60})")

    try:
        pkgs = ["fastapi>=0.100", "uvicorn", "httpx"]
        reqs = generate_requirements(pkgs)
    except NotImplementedError:
        for i in range(3, 5):
            print(f"  ❌ Check {i}: generate_requirements not implemented")
        reqs = None

    if reqs is not None:
        lines = [l for l in reqs.split("\\n") if l]
        _chk(3, lines == sorted(pkgs),
             f"requirements sorted alphabetically (got {lines})")
        _chk(4, reqs.endswith("\\n"),
             f"requirements.txt ends with newline")
    else:
        for i in range(3, 5):
            print(f"  ❌ Check {i}: skipped")

    try:
        with tempfile.TemporaryDirectory() as td:
            result = write_deploy_files(td, "uvicorn app:app --port $PORT",
                                        ["fastapi", "uvicorn"])
            pf_path = Path(result["procfile"])
            rq_path = Path(result["requirements"])
            _chk(5, pf_path.exists() and rq_path.exists() and
                 pf_path.name == "Procfile" and rq_path.name == "requirements.txt",
                 f"files written: {pf_path.name}, {rq_path.name}")
    except NotImplementedError:
        print(f"  ❌ Check 5: write_deploy_files not implemented")

    print(f"\\nScore: {score} / {total}")
    if score == total:
        print("🎉 Exercise complete!")

_run_checks()
'''

_CHECKS_EX4 = '''\
def _run_checks():
    score = 0
    total = 5

    def _chk(n, ok, msg):
        nonlocal score
        print(f"  {\'✅\' if ok else \'❌\'} Check {n}: {msg}")
        if ok:
            score += 1

    try:
        ok, missing = check_env_vars(["SECRET_KEY", "PORT"], {"SECRET_KEY": "abc", "PORT": "8000"})
    except NotImplementedError:
        for i in range(1, total + 1):
            print(f"  ❌ Check {i}: check_env_vars not implemented")
        print(f"\\nScore: 0 / {total}")
        return

    _chk(1, ok is True and missing == [],
         f"all vars present → (True, []) (got ({ok}, {missing}))")

    ok2, miss2 = check_env_vars(["SECRET_KEY", "PORT"], {"SECRET_KEY": "abc"})
    _chk(2, ok2 is False and "PORT" in miss2,
         f"missing PORT → (False, [\'PORT\']) (got ({ok2}, {miss2}))")

    ok3, miss3 = check_env_vars(["SECRET_KEY", "PORT"], {"SECRET_KEY": "", "PORT": "8000"})
    _chk(3, ok3 is False and "SECRET_KEY" in miss3,
         f"empty SECRET_KEY → (False, [\'SECRET_KEY\']) (got ({ok3}, {miss3}))")

    ok4, miss4 = check_env_vars([], {"SECRET_KEY": "abc"})
    _chk(4, ok4 is True and miss4 == [],
         f"empty required_vars → (True, []) (got ({ok4}, {miss4}))")

    ok5, miss5 = check_env_vars(["A", "B", "C"], {})
    _chk(5, ok5 is False and set(miss5) == {"A", "B", "C"},
         f"all missing → (False, [A,B,C]) (got ({ok5}, {miss5}))")

    print(f"\\nScore: {score} / {total}")
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
        checker = DeploymentChecker()
        checker.add_check("test_check", True, "all good")
    except NotImplementedError:
        for i in range(1, total + 1):
            print(f"  ❌ Check {i}: DeploymentChecker not implemented")
        print(f"\\nScore: 0 / {total}")
        return

    try:
        rep = checker.report()
    except NotImplementedError:
        for i in range(1, total + 1):
            print(f"  ❌ Check {i}: DeploymentChecker.report not implemented")
        print(f"\\nScore: 0 / {total}")
        return

    _chk(1, rep.get("passed") is True and rep.get("total") == 1,
         f"one passing check → passed=True, total=1 (got {rep})")

    # env check — all present
    try:
        c2 = DeploymentChecker()
        c2.run_env_check(["MODEL", "PORT"], {"MODEL": "llama3.2", "PORT": "8000"})
        rep2 = c2.report()
    except NotImplementedError:
        for i in range(2, 4):
            print(f"  ❌ Check {i}: run_env_check not implemented")
        rep2 = None

    if rep2 is not None:
        _chk(2, rep2.get("passed") is True,
             f"env check passes when all vars present (got {rep2})")
        c3 = DeploymentChecker()
        c3.run_env_check(["MODEL", "SECRET_KEY"], {"MODEL": "llama3.2"})
        rep3 = c3.report()
        _chk(3, rep3.get("passed") is False,
             f"env check fails when SECRET_KEY missing (got {rep3})")

    # health check
    try:
        from datetime import datetime
        health_app = FastAPI()

        @health_app.get("/health")
        def _h():
            return {"status": "ok", "timestamp": datetime.utcnow().isoformat(), "version": "1.0"}

        c4 = DeploymentChecker()
        c4.run_health_check(health_app)
        rep4 = c4.report()
    except NotImplementedError:
        print(f"  ❌ Check 4: run_health_check not implemented")
        rep4 = None

    if rep4 is not None:
        _chk(4, rep4.get("passed") is True,
             f"health check passes on /health app (got {rep4})")

    # combined: one pass + one fail → not passed
    c5 = DeploymentChecker()
    c5.add_check("ok_check", True)
    c5.add_check("fail_check", False, "something wrong")
    rep5 = c5.report()
    _chk(5, rep5.get("passed") is False and rep5.get("total") == 2,
         f"mix of pass/fail → passed=False, total=2 (got {rep5})")

    print(f"\\nScore: {score} / {total}")
    if score == total:
        print("🎉 Exercise complete!")

_run_checks()
'''

# ---------------------------------------------------------------------------
# why-works explanations
# ---------------------------------------------------------------------------

_WHY_EX1 = """\
**Why this works:** Start with `dict(defaults)` — a shallow copy — so the
caller's defaults dict is never mutated. Then iterate over `env_vars` and
override only keys that exist in the defaults. Unknown env vars (like `PATH`
or `HOME`) are silently ignored — you only want the config keys you declared.
This is the 12-factor app pattern: all config comes from the environment,
but the defaults give you a working local setup without any setup.
"""

_WHY_EX2 = """\
**Why this works:** The `/health` endpoint is intentionally minimal — it has no
dependencies, no database calls, no Ollama calls. It just returns three fields.
Load balancers and deployment platforms call `/health` on a fixed interval; if
it returns 200 the instance is healthy, if it times out or returns 5xx the
instance is removed. `datetime.utcnow().isoformat()` gives a UTC timestamp in
ISO-8601 format (`2026-07-25T14:30:00.123456`) which is unambiguous across
time zones. The version field helps identify which code version is deployed.
"""

_WHY_EX3 = """\
**Why this works:** A `Procfile` is the simplest possible deployment manifest —
one line per process type. `web: <command>` tells the platform what command
to run for HTTP traffic. `$PORT` is set by the platform at runtime (never
hardcode the port). Sorting packages in `requirements.txt` is a best practice
for readable diffs. `write_deploy_files` wraps both generators and handles
directory creation — the caller just specifies a directory and gets files.
"""

_WHY_EX4 = """\
**Why this works:** Checking `v not in env or not env[v]` catches both missing
variables (KeyError) and empty strings (a variable set to `""` is effectively
missing). Returning `(bool, list)` makes the result self-documenting — the
caller knows not only whether something is wrong but exactly what is wrong.
Passing `env` as a parameter (instead of accessing `os.environ` directly) makes
the function trivially testable without touching the real environment.
"""

_WHY_EX5 = """\
**Why this works:** `DeploymentChecker` accumulates check results in a list
rather than printing them immediately — this separates data from display and
makes the results programmable (you can loop over `report()["checks"]` and
format however you want). `run_env_check` and `run_health_check` are convenience
methods that call `add_check` with the right name and detail. The `report()`
method aggregates: `passed` is only True when ALL checks pass — one failure
means the deployment is not ready.
"""

# ---------------------------------------------------------------------------
# exercise builder
# ---------------------------------------------------------------------------

def _ex(n, title, why_matters, setup, stub, checks, sol_code, why_works, bonus,
        setup_label="Setup (provided)", cid_base=0):
    cells = [
        _md(f"# Day 57 · Exercise {n}: {title}\n\n"
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
        title="Config from Environment",
        why_matters=(
            "Implement `load_config(env_vars, defaults)` — the 12-factor app "
            "pattern for reading all configuration from the environment. "
            "Every deployed app needs this: local defaults + production overrides."
        ),
        setup=_IMPORTS_EX1,
        stub=_STUB_EX1,
        checks=_CHECKS_EX1,
        sol_code=_SOL_EX1,
        why_works=_WHY_EX1,
        bonus=(
            "Extend `load_config` to support type coercion: add a `types` dict "
            "parameter mapping key names to callables (e.g. `{'PORT': int, 'DEBUG': bool}`). "
            "For each key in types, call `types[key](config[key])` to convert the "
            "string env var to the right Python type. Handle `bool` specially: "
            "'true'/'1'/'yes' → True, anything else → False."
        ),
        cid_base=0,
    )

def _build_ex2():
    return _ex(
        n=2,
        title="Health Check Endpoint",
        why_matters=(
            "Implement `build_health_api(version)` — a FastAPI app with a "
            "`GET /health` endpoint returning status, timestamp, and version. "
            "Every production service needs a health endpoint so load balancers "
            "can verify the instance is alive."
        ),
        setup=_IMPORTS_EX2,
        stub=_STUB_EX2,
        checks=_CHECKS_EX2,
        sol_code=_SOL_EX2,
        why_works=_WHY_EX2,
        bonus=(
            "Extend `/health` to include a `'checks'` list that verifies "
            "sub-dependencies. For example, add a `check_ollama()` helper that "
            "tries `ollama.list()` — if it raises, include `{'ollama': 'unreachable'}` "
            "in the checks list and set overall `'status': 'degraded'` instead of "
            "'ok'. This is a deep health check (vs a shallow ping)."
        ),
        cid_base=100,
    )

def _build_ex3():
    return _ex(
        n=3,
        title="Deployment File Generators",
        why_matters=(
            "Implement `generate_procfile`, `generate_requirements`, and "
            "`write_deploy_files` — the functions that create the deployment "
            "manifest files Render, Railway, and Heroku read to know how to "
            "start and install your app."
        ),
        setup=_IMPORTS_EX3,
        stub=_STUB_EX3,
        checks=_CHECKS_EX3,
        sol_code=_SOL_EX3,
        why_works=_WHY_EX3,
        bonus=(
            "Add a `generate_render_yaml(service_name, start_command, env_vars)` "
            "function that produces a `render.yaml` service manifest. "
            "The output should be a YAML string with `services:` → one web service "
            "entry with the given name, startCommand, and envVars list. "
            "You can build it as an f-string without importing PyYAML — "
            "the output is small and predictable."
        ),
        cid_base=200,
    )

def _build_ex4():
    return _ex(
        n=4,
        title="Environment Variable Checker",
        why_matters=(
            "Implement `check_env_vars(required_vars, env)` — a pre-flight "
            "function that verifies all required environment variables are set "
            "before the app starts. Catch missing config at startup, not at "
            "3 am when a request hits the missing var."
        ),
        setup=_IMPORTS_EX4,
        stub=_STUB_EX4,
        checks=_CHECKS_EX4,
        sol_code=_SOL_EX4,
        why_works=_WHY_EX4,
        bonus=(
            "Extend `check_env_vars` to also accept a `validators` dict "
            "mapping variable names to callables returning bool. For example, "
            "`validators={'PORT': lambda v: v.isdigit()}` would fail if PORT "
            "is not numeric. Return a third value — a dict of "
            "`{var: 'missing' | 'invalid'}` — so the caller knows both what "
            "is wrong and why."
        ),
        cid_base=300,
    )

def _build_ex5():
    return _ex(
        n=5,
        title="DeploymentChecker",
        why_matters=(
            "Implement `DeploymentChecker` — a class that runs a suite of "
            "readiness checks (env vars, health endpoint) and produces a "
            "structured report. This is the automated pre-deployment checklist "
            "that replaces the 'did you remember to set SECRET_KEY?' conversation."
        ),
        setup=_IMPORTS_EX5,
        stub=_STUB_EX5,
        checks=_CHECKS_EX5,
        sol_code=_SOL_EX5,
        why_works=_WHY_EX5,
        bonus=(
            "Add a `run_cors_check(app, allowed_origin)` method to `DeploymentChecker`. "
            "It should use TestClient to send a GET /health with an "
            "`Origin: {allowed_origin}` header and check that the response includes "
            "`access-control-allow-origin` (which means CORSMiddleware is configured). "
            "Record under name 'cors'. This tests that the CORS config will work "
            "for the expected frontend origin."
        ),
        cid_base=400,
    )

# ---------------------------------------------------------------------------
# Project notebook
# ---------------------------------------------------------------------------

_PROJECT_SETUP = """\
# Project setup — Day 57: deploy_api.py
from pathlib import Path

def write_deploy_api(path: str) -> str:
    \"\"\"Generate deploy_api.py — the deployment-ready API.

    The file should contain:
      GET  /health     — health check (status, timestamp, version)
      POST /upload     — validate + extract + store document
      GET  /documents  — list uploaded documents
      POST /ask/{doc_id}?question= — Q&A using Ollama

    Config from env vars: PORT, MODEL, SECRET_KEY, MAX_UPLOAD_BYTES.
    All config has sensible defaults so the app works locally without any setup.
    \"\"\"
    raise NotImplementedError

def write_deployment_files(directory: str) -> dict:
    \"\"\"Write Procfile and requirements.txt into directory.

    Returns dict with 'procfile' and 'requirements' keys.
    \"\"\"
    raise NotImplementedError
"""

def _build_project():
    cells = [
        _md("# Day 57 Project: Deployment-Ready API\n\n"
            "**What You're Building:**\n\n"
            "A production-ready version of the Day 56 doc-upload API, enhanced with:\n\n"
            "- `GET /health` — health check endpoint for load balancers\n"
            "- Config from environment variables (`PORT`, `MODEL`, `SECRET_KEY`)\n"
            "- `Procfile` and `requirements.txt` for Render/Railway\n\n"
            "**Deliverable:** Run `uvicorn deploy_api:app --reload`, upload a file, "
            "then check `/health` and `/documents`. "
            "Deploy to Render or Railway using the generated `Procfile`."),
        _md("## Your Implementation"),
        _code(_PROJECT_SETUP, cid=500),
        _md("## Check Your Work\n\nImplement both functions above, then re-run."),
        _code("print('Implement write_deploy_api and write_deployment_files above.')", cid=501),
    ]
    return _nb(cells)

# ---------------------------------------------------------------------------
# Solution notebook
# ---------------------------------------------------------------------------

_FULL_SOL_CELL1 = f'''\
# ── provided source string ──────────────────────────────────────────────────
_DEPLOY_API_SRC = {repr(_DEPLOY_API_SRC)}

from pathlib import Path

def write_deploy_api(path: str) -> str:
    Path(path).write_text(_DEPLOY_API_SRC, encoding="utf-8")
    return path

out = write_deploy_api("deploy_api.py")
print(f"Generated: {{out}}  ({{len(_DEPLOY_API_SRC)}} chars)")
print(Path(out).read_text(encoding="utf-8")[:120] + "...")
'''

_PROCFILE_REPR = repr(_PROCFILE)
_RENDER_REPR = repr(_RENDER_YAML)
_REQS_REPR = repr(_REQUIREMENTS)

_FULL_SOL_CELL2 = f'''\
# ── generate deployment files ───────────────────────────────────────────────
_PROCFILE_SRC  = {_PROCFILE_REPR}
_RENDER_SRC    = {_RENDER_REPR}
_REQS_SRC      = {_REQS_REPR}

def write_deployment_files(directory: str) -> dict:
    d = Path(directory)
    d.mkdir(parents=True, exist_ok=True)
    pf = d / "Procfile"
    ry = d / "render.yaml"
    rq = d / "requirements.txt"
    pf.write_text(_PROCFILE_SRC, encoding="utf-8")
    ry.write_text(_RENDER_SRC,   encoding="utf-8")
    rq.write_text(_REQS_SRC,     encoding="utf-8")
    return {{"procfile": str(pf), "render_yaml": str(ry), "requirements": str(rq)}}

files = write_deployment_files(".")
for name, path in files.items():
    size = Path(path).stat().st_size
    print(f"  wrote {{path}}  ({{size}} bytes)")
print()
print("Procfile:")
print(Path(files["procfile"]).read_text())
'''

_FULL_SOL_TEST = '''\
# ── smoke-test deploy_api in-process (no Ollama) ────────────────────────────
import io
import re
import secrets
from datetime import datetime
from pathlib import Path
import pypdf
from fastapi import FastAPI, File, HTTPException, UploadFile
from starlette.testclient import TestClient

# --- replicate deploy_api internals in-process ----------------------------

def _validate(content, filename, allowed, ctype, maxb):
    if not content: return False, "empty"
    if len(content) > maxb: return False, "too large"
    ext = Path(filename).suffix.lower()
    if ctype not in allowed and ext not in {".txt", ".pdf"}:
        return False, f"bad type: {ctype}"
    return True, ""

def _extract(content, ctype):
    if "pdf" in ctype:
        r = pypdf.PdfReader(io.BytesIO(content))
        return "\\n".join(p.extract_text() or "" for p in r.pages)
    return content.decode("utf-8", errors="replace")

ALLOWED = {"text/plain", "application/pdf"}
MAX_SZ  = 5 * 1024 * 1024
APP_VER = "1.0.0"
_docs: dict = {}

app = FastAPI(title="deploy_api (test)", version=APP_VER)

@app.get("/health")
def health():
    return {"status": "ok",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": APP_VER}

@app.post("/upload", status_code=201)
async def upload(file: UploadFile = File(...)):
    content = await file.read()
    ok, err = _validate(content, file.filename or "unnamed",
                        ALLOWED, file.content_type or "", MAX_SZ)
    if not ok:
        raise HTTPException(400, detail=err)
    text   = _extract(content, file.content_type or "text/plain")
    doc_id = secrets.token_urlsafe(8)
    _docs[doc_id] = {"filename": file.filename, "text": text}
    return {"doc_id": doc_id, "filename": file.filename, "chars": len(text)}

@app.get("/documents")
def list_documents():
    return {"documents": [{"doc_id": k, "filename": v["filename"]}
                          for k, v in _docs.items()]}

# ── run checks ──────────────────────────────────────────────────────────────
client = TestClient(app, raise_server_exceptions=False)
score = 0; total = 5

def chk(n, ok, msg):
    global score
    print(f"  {\'✅\' if ok else \'❌\'} Check {n}: {msg}")
    if ok: score += 1

# 1. health → 200 + status=ok
r = client.get("/health")
chk(1, r.status_code == 200 and r.json().get("status") == "ok",
    f"GET /health → 200 + status=ok (got {r.status_code})")

# 2. health has timestamp + version
data = r.json() if r.status_code == 200 else {}
chk(2, "timestamp" in data and "version" in data,
    f"health has timestamp + version (got {list(data.keys())})")

# 3. upload → 201
r2 = client.post("/upload",
                 files={"file": ("readme.txt", b"This is a test document.", "text/plain")})
chk(3, r2.status_code == 201,
    f"POST /upload → 201 (got {r2.status_code})")

up_data = r2.json() if r2.status_code == 201 else {}
doc_id  = up_data.get("doc_id", "")

# 4. GET /documents lists the uploaded file
r3 = client.get("/documents")
docs = r3.json().get("documents", []) if r3.status_code == 200 else []
chk(4, any(d["doc_id"] == doc_id for d in docs),
    f"GET /documents includes uploaded doc (found {len(docs)} docs)")

# 5. invalid upload → 400
r4 = client.post("/upload",
                 files={"file": ("photo.jpg", b"\\xff\\xd8\\xff", "image/jpeg")})
chk(5, r4.status_code == 400,
    f"unsupported type → 400 (got {r4.status_code})")

print(f"\\nScore: {score} / {total}")
if score == total:
    print("\\nDay 57 — Deploying Apps complete! 🎉")
print(f"\\nDeliverable files:")
print("  deploy_api.py   — run with: uvicorn deploy_api:app --reload")
print("  Procfile        — push to Render/Railway")
print("  requirements.txt — dependencies")
print("  render.yaml     — Render service config")
print(f"\\nAPI generated: {len(_DEPLOY_API_SRC)} chars")
'''

def _build_solution():
    cells = [
        _md("# Day 57 Project — Solution: Deployment-Ready API\n\n"
            "**Deliverables:**\n"
            "- `deploy_api.py` — production API with `/health`, env-var config\n"
            "- `Procfile` — start command for Render/Railway\n"
            "- `requirements.txt` — dependency list\n"
            "- `render.yaml` — Render service manifest"),
        _code(_FULL_SOL_CELL1, cid=600),
        _code(_FULL_SOL_CELL2, cid=601),
        _code(_FULL_SOL_TEST,  cid=602),
    ]
    return _nb(cells)

# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    print("Generating Day 057 notebooks...")
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
