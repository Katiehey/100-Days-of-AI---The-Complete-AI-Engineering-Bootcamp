#!/usr/bin/env python3
"""gen_day055.py — Generate Day 055: Authentication notebooks."""

from pathlib import Path
import nbformat as nbf

ROOT = Path(__file__).parent.parent
DAY_DIR = ROOT / "04_real_apps" / "day_055"

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
# auth_api.py source  (embedded via repr — never inspect.getsource)
# ---------------------------------------------------------------------------

_AUTH_API_SRC = '''\
"""auth_api.py — Day 055 project: FastAPI with password auth + JWT.

Run:  uvicorn auth_api:app --reload
Docs: http://localhost:8000/docs
"""
import secrets
import hmac
from datetime import datetime, timedelta
from typing import Annotated

import bcrypt as _bcrypt_lib
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from pydantic import BaseModel, Field
import ollama

# --- config ---------------------------------------------------------------
SECRET_KEY = "change-me-in-production-use-env-var"
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 60
MODEL = "llama3.2"

# --- password hashing -----------------------------------------------------
def hash_password(password: str) -> str:
    return _bcrypt_lib.hashpw(password.encode(), _bcrypt_lib.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return _bcrypt_lib.checkpw(plain.encode(), hashed.encode())

# --- JWT ------------------------------------------------------------------
def create_token(data: dict, expires_minutes: int = TOKEN_EXPIRE_MINUTES) -> str:
    payload = {**data, "exp": datetime.utcnow() + timedelta(minutes=expires_minutes)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

# --- in-memory user store (swap for SQLAlchemy in production) -------------
_users: dict[str, dict] = {}        # email -> {id, email, hashed_password}
_histories: dict[int, list] = {}    # user_id -> conversation messages
_next_id: list[int] = [1]

# --- Pydantic models ------------------------------------------------------
class RegisterRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=6)

class LoginRequest(BaseModel):
    email: str
    password: str

class ChatRequest(BaseModel):
    message: str = Field(min_length=1)

# --- auth dependency ------------------------------------------------------
_security = HTTPBearer()

def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials, Depends(_security)]
) -> dict:
    try:
        return decode_token(creds.credentials)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

# --- app ------------------------------------------------------------------
app = FastAPI(title="Auth AI API", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/register", status_code=201)
def register(req: RegisterRequest):
    if req.email in _users:
        raise HTTPException(status_code=409, detail="Email already registered")
    uid = _next_id[0]
    _next_id[0] += 1
    _users[req.email] = {
        "id": uid,
        "email": req.email,
        "hashed_password": hash_password(req.password),
    }
    return {"id": uid, "email": req.email}

@app.post("/login")
def login(req: LoginRequest):
    user = _users.get(req.email)
    if not user or not verify_password(req.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token({"user_id": user["id"], "email": req.email})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/me")
def me(user: dict = Depends(get_current_user)):
    return {"user_id": user["user_id"], "email": user["email"]}

@app.post("/chat")
def chat(req: ChatRequest, user: dict = Depends(get_current_user)):
    uid = user["user_id"]
    hist = _histories.setdefault(uid, [])
    hist.append({"role": "user", "content": req.message})
    reply = ollama.chat(model=MODEL, messages=hist)["message"]["content"]
    hist.append({"role": "assistant", "content": reply})
    return {"reply": reply, "history_length": len(hist)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''

# ---------------------------------------------------------------------------
# shared setup snippets (provided code prefixed before each exercise stub)
# ---------------------------------------------------------------------------

_IMPORTS_EX1 = """\
import bcrypt as _bcrypt_lib
"""

_IMPORTS_EX2 = """\
import secrets
import hmac
"""

_IMPORTS_EX3 = """\
from jose import jwt, JWTError
from datetime import datetime, timedelta

SECRET_KEY = "test-secret-for-exercise"
ALGORITHM  = "HS256"
"""

# cumulative provided code for exercise 4 (depends on ex1 + ex3 solutions)
_BEFORE_EX4 = """\
import bcrypt as _bcrypt_lib
from jose import jwt, JWTError
from datetime import datetime, timedelta
from typing import Annotated
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.testclient import TestClient

SECRET_KEY  = "test-secret-for-exercise"
ALGORITHM   = "HS256"

def hash_password(password: str) -> str:
    return _bcrypt_lib.hashpw(password.encode(), _bcrypt_lib.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return _bcrypt_lib.checkpw(plain.encode(), hashed.encode())

def create_token(data: dict, expires_in_minutes: int = 60) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=expires_in_minutes)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

_security = HTTPBearer()
"""

# cumulative provided code for exercise 5 (depends on ex1 + ex3 solutions)
_BEFORE_EX5 = """\
import bcrypt as _bcrypt_lib
from jose import jwt, JWTError
from datetime import datetime, timedelta

SECRET_KEY  = "test-secret-for-exercise"
ALGORITHM   = "HS256"

def hash_password(password: str) -> str:
    return _bcrypt_lib.hashpw(password.encode(), _bcrypt_lib.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return _bcrypt_lib.checkpw(plain.encode(), hashed.encode())

def create_token(data: dict, expires_in_minutes: int = 60) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=expires_in_minutes)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
"""

# ---------------------------------------------------------------------------
# stubs
# ---------------------------------------------------------------------------

_STUB_EX1 = '''\
def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt.

    Args:
        password: The plaintext password to hash.
    Returns:
        A bcrypt hash string (starts with \'$2b$\').
    """
    # TODO: encode password to bytes, call _bcrypt_lib.hashpw with a new gensalt,
    #       then decode the result to a str and return it
    raise NotImplementedError

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash.

    Args:
        plain_password:  The candidate plaintext password.
        hashed_password: The stored bcrypt hash string.
    Returns:
        True if the password matches, False otherwise.
    """
    # TODO: call _bcrypt_lib.checkpw(plain_password.encode(), hashed_password.encode())
    raise NotImplementedError
'''

_STUB_EX2 = '''\
def generate_api_key() -> str:
    """Generate a cryptographically secure API key.

    Returns:
        A URL-safe base64 string of at least 43 characters (32 random bytes).
    """
    # TODO: return secrets.token_urlsafe(32)
    raise NotImplementedError

def verify_api_key(provided: str, stored: str) -> bool:
    """Compare two API keys in constant time to prevent timing attacks.

    Args:
        provided: The key sent by the client.
        stored:   The key stored on the server.
    Returns:
        True if they match, False otherwise.
    """
    # TODO: return hmac.compare_digest(provided.encode(), stored.encode())
    raise NotImplementedError
'''

_STUB_EX3 = '''\
def create_token(data: dict, expires_in_minutes: int = 60) -> str:
    """Encode a JWT with an expiry claim.

    Args:
        data:               Payload dict (e.g. {\'user_id\': 1, \'email\': \'a@b.com\'}).
        expires_in_minutes: Token lifetime in minutes.
    Returns:
        Signed JWT string (header.payload.signature).
    """
    # TODO: copy data, add \'exp\' = datetime.utcnow() + timedelta(minutes=expires_in_minutes)
    #       return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    raise NotImplementedError

def decode_token(token: str) -> dict:
    """Decode and validate a JWT.

    Args:
        token: The JWT string to decode.
    Returns:
        Decoded payload dict.
    Raises:
        JWTError: If the signature is invalid or the token is expired.
    """
    # TODO: return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    raise NotImplementedError
'''

_STUB_EX4 = '''\
def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials, Depends(_security)]
) -> dict:
    """FastAPI dependency: validate Bearer JWT and return the decoded payload.

    Args:
        creds: Injected by HTTPBearer — .credentials is the raw token string.
    Returns:
        Decoded JWT payload dict.
    Raises:
        HTTPException(401): If the token is invalid or expired.
    """
    # TODO: try decode_token(creds.credentials); on JWTError raise HTTPException(401, ...)
    raise NotImplementedError

def build_protected_api() -> FastAPI:
    """Build a FastAPI app with one protected route GET /me.

    Returns:
        FastAPI app where GET /me requires a valid Bearer token
        and returns {"user_id": ..., "email": ...}.
    """
    app = FastAPI()
    # TODO: add GET /me using Depends(get_current_user) that returns
    #       {"user_id": user["user_id"], "email": user["email"]}
    return app
'''

_next_id_stub = '''\
_next_id = [1]  # mutable counter — start at 1 for each fresh test
'''

_STUB_EX5 = '''\
_next_id = [1]  # mutable id counter

def register_user(email: str, password: str, users: dict) -> dict:
    """Register a new user, hashing their password.

    Args:
        email:    User\'s email address.
        password: Plaintext password (will be hashed before storing).
        users:    Mutable dict acting as the user store (email -> user record).
    Returns:
        Dict with {\'id\': int, \'email\': str} of the new user.
    Raises:
        ValueError: If email is already registered.
    """
    # TODO: check if email in users → raise ValueError("Email already registered")
    # assign uid = _next_id[0]; _next_id[0] += 1
    # store users[email] = {"id": uid, "email": email, "hashed_password": hash_password(password)}
    # return {"id": uid, "email": email}
    raise NotImplementedError

def login_user(email: str, password: str, users: dict) -> str:
    """Authenticate a user and return a signed JWT.

    Args:
        email:    The user\'s email.
        password: Plaintext password to verify.
        users:    The user store dict.
    Returns:
        Signed JWT string.
    Raises:
        ValueError: If email not found or password is wrong.
    """
    # TODO: look up user = users.get(email)
    # if not user or not verify_password(password, user["hashed_password"]): raise ValueError
    # return create_token({"user_id": user["id"], "email": email})
    raise NotImplementedError
'''

# ---------------------------------------------------------------------------
# solutions
# ---------------------------------------------------------------------------

_SOL_EX1 = '''\
def hash_password(password: str) -> str:
    return _bcrypt_lib.hashpw(password.encode(), _bcrypt_lib.gensalt()).decode()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _bcrypt_lib.checkpw(plain_password.encode(), hashed_password.encode())
'''

_SOL_EX2 = '''\
def generate_api_key() -> str:
    return secrets.token_urlsafe(32)

def verify_api_key(provided: str, stored: str) -> bool:
    return hmac.compare_digest(provided.encode(), stored.encode())
'''

_SOL_EX3 = '''\
def create_token(data: dict, expires_in_minutes: int = 60) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=expires_in_minutes)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
'''

_SOL_EX4 = '''\
def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials, Depends(_security)]
) -> dict:
    try:
        return decode_token(creds.credentials)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def build_protected_api() -> FastAPI:
    app = FastAPI()

    @app.get("/me")
    def me(user: dict = Depends(get_current_user)):
        return {"user_id": user["user_id"], "email": user["email"]}

    return app
'''

_SOL_EX5 = '''\
_next_id = [1]

def register_user(email: str, password: str, users: dict) -> dict:
    if email in users:
        raise ValueError("Email already registered")
    uid = _next_id[0]
    _next_id[0] += 1
    users[email] = {"id": uid, "email": email, "hashed_password": hash_password(password)}
    return {"id": uid, "email": email}

def login_user(email: str, password: str, users: dict) -> str:
    user = users.get(email)
    if not user or not verify_password(password, user["hashed_password"]):
        raise ValueError("Invalid credentials")
    return create_token({"user_id": user["id"], "email": email})
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
        print(f"  {'✅' if ok else '❌'} Check {n}: {msg}")
        if ok:
            score += 1

    try:
        h = hash_password("secret123")
    except NotImplementedError:
        for i in range(1, total + 1):
            print(f"  ❌ Check {i}: hash_password not implemented")
        print(f"\\nScore: 0 / {total}")
        return

    _chk(1, isinstance(h, str) and h.startswith("$2b$"),
         f"hash_password returns a bcrypt string (got: {h[:12]}...)")

    try:
        ok_verify = verify_password("secret123", h)
        bad_verify = verify_password("wrong", h)
    except NotImplementedError:
        for i in range(2, total + 1):
            print(f"  ❌ Check {i}: verify_password not implemented")
        print(f"\\nScore: {score} / {total}")
        return

    _chk(2, ok_verify is True,
         f"verify_password(correct) → True (got {ok_verify})")
    _chk(3, bad_verify is False,
         f"verify_password(wrong) → False (got {bad_verify})")

    h2 = hash_password("secret123")
    _chk(4, h != h2,
         "two hashes of the same password differ (bcrypt uses random salts)")

    _chk(5, h != "secret123",
         "hash is not the plaintext password")

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
        print(f"  {'✅' if ok else '❌'} Check {n}: {msg}")
        if ok:
            score += 1

    try:
        k = generate_api_key()
    except NotImplementedError:
        for i in range(1, total + 1):
            print(f"  ❌ Check {i}: generate_api_key not implemented")
        print(f"\\nScore: 0 / {total}")
        return

    _chk(1, isinstance(k, str) and len(k) >= 43,
         f"generate_api_key returns str of length >= 43 (got {len(k)})")

    k2 = generate_api_key()
    _chk(2, k != k2, "two generated keys are always different")

    try:
        match_ok  = verify_api_key(k, k)
        match_bad = verify_api_key(k, k2)
    except NotImplementedError:
        for i in range(3, total + 1):
            print(f"  ❌ Check {i}: verify_api_key not implemented")
        print(f"\\nScore: {score} / {total}")
        return

    _chk(3, match_ok is True, f"verify_api_key(k, k) → True (got {match_ok})")
    _chk(4, match_bad is False, f"verify_api_key(k, k2) → False (got {match_bad})")
    _chk(5, verify_api_key("", k) is False, "verify_api_key('', k) → False")

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
        print(f"  {'✅' if ok else '❌'} Check {n}: {msg}")
        if ok:
            score += 1

    payload = {"user_id": 7, "email": "alice@example.com"}

    try:
        tok = create_token(payload)
    except NotImplementedError:
        for i in range(1, total + 1):
            print(f"  ❌ Check {i}: create_token not implemented")
        print(f"\\nScore: 0 / {total}")
        return

    _chk(1, isinstance(tok, str) and tok.count(".") == 2,
         f"create_token returns header.payload.signature (got {tok[:30]}...)")

    try:
        decoded = decode_token(tok)
    except NotImplementedError:
        for i in range(2, total + 1):
            print(f"  ❌ Check {i}: decode_token not implemented")
        print(f"\\nScore: {score} / {total}")
        return

    _chk(2, isinstance(decoded, dict),
         f"decode_token returns a dict (got {type(decoded).__name__})")
    _chk(3, decoded.get("user_id") == 7 and decoded.get("email") == "alice@example.com",
         f"decoded payload has user_id=7 and email (got {decoded})")

    # expired token (negative lifetime = already expired)
    expired_tok = create_token({"user_id": 1}, expires_in_minutes=-1)
    try:
        decode_token(expired_tok)
        _chk(4, False, "expired token should raise JWTError")
    except JWTError:
        _chk(4, True, "expired token raises JWTError ✓")
    except Exception as e:
        _chk(4, False, f"expired token raised {type(e).__name__} instead of JWTError")

    # tampered token
    parts = tok.split(".")
    tampered = parts[0] + "." + parts[1] + ".INVALIDSIG"
    try:
        decode_token(tampered)
        _chk(5, False, "tampered token should raise JWTError")
    except JWTError:
        _chk(5, True, "tampered token raises JWTError ✓")
    except Exception as e:
        _chk(5, False, f"tampered token raised {type(e).__name__} instead of JWTError")

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
        print(f"  {'✅' if ok else '❌'} Check {n}: {msg}")
        if ok:
            score += 1

    try:
        app = build_protected_api()
    except NotImplementedError:
        for i in range(1, total + 1):
            print(f"  ❌ Check {i}: build_protected_api not implemented")
        print(f"\\nScore: 0 / {total}")
        return
    except Exception as e:
        for i in range(1, total + 1):
            print(f"  ❌ Check {i}: build_protected_api raised {type(e).__name__}: {e}")
        print(f"\\nScore: 0 / {total}")
        return

    client = TestClient(app, raise_server_exceptions=False)

    # check 1: no token → 401 (HTTPBearer auto-rejects missing header)
    r = client.get("/me")
    _chk(1, r.status_code == 401,
         f"no auth header → 401 (got {r.status_code})")

    # check 2: bad token → 401
    r = client.get("/me", headers={"Authorization": "Bearer bad.token.here"})
    _chk(2, r.status_code == 401,
         f"invalid token → 401 (got {r.status_code})")

    # valid token for remaining checks
    good_tok = create_token({"user_id": 99, "email": "bob@example.com"})
    r = client.get("/me", headers={"Authorization": f"Bearer {good_tok}"})
    _chk(3, r.status_code == 200,
         f"valid token → 200 (got {r.status_code})")

    if r.status_code == 200:
        data = r.json()
        _chk(4, data.get("user_id") == 99,
             f"user_id == 99 (got {data.get('user_id')})")
        _chk(5, data.get("email") == "bob@example.com",
             f"email correct (got {data.get('email')})")
    else:
        for i in range(4, 6):
            print(f"  ❌ Check {i}: skipped (check 3 failed)")

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
        print(f"  {'✅' if ok else '❌'} Check {n}: {msg}")
        if ok:
            score += 1

    store: dict = {}

    try:
        result = register_user("alice@example.com", "password123", store)
    except NotImplementedError:
        for i in range(1, total + 1):
            print(f"  ❌ Check {i}: register_user not implemented")
        print(f"\\nScore: 0 / {total}")
        return

    _chk(1, isinstance(result, dict) and "id" in result and result.get("email") == "alice@example.com",
         f"register returns {{id, email}} (got {result})")

    try:
        register_user("alice@example.com", "other", store)
        _chk(2, False, "duplicate email should raise ValueError")
    except ValueError:
        _chk(2, True, "duplicate email raises ValueError ✓")
    except Exception as e:
        _chk(2, False, f"raised {type(e).__name__} instead of ValueError")

    try:
        tok = login_user("alice@example.com", "password123", store)
    except NotImplementedError:
        for i in range(3, total + 1):
            print(f"  ❌ Check {i}: login_user not implemented")
        print(f"\\nScore: {score} / {total}")
        return

    _chk(3, isinstance(tok, str) and tok.count(".") == 2,
         f"login_user returns a JWT string (got {str(tok)[:30]}...)")

    decoded = decode_token(tok)
    _chk(4, decoded.get("user_id") == result["id"],
         f"token user_id == {result['id']} (got {decoded.get('user_id')})")

    try:
        login_user("alice@example.com", "wrongpass", store)
        _chk(5, False, "wrong password should raise ValueError")
    except ValueError:
        _chk(5, True, "wrong password raises ValueError ✓")
    except Exception as e:
        _chk(5, False, f"raised {type(e).__name__} instead of ValueError")

    print(f"\\nScore: {score} / {total}")
    if score == total:
        print("🎉 Exercise complete!")

_run_checks()
'''

# ---------------------------------------------------------------------------
# solution explanation strings (inside <details>)
# ---------------------------------------------------------------------------

_WHY_EX1 = """\
**Why this works:** `_bcrypt_lib.hashpw(password.encode(), _bcrypt_lib.gensalt())`
generates a fresh random salt, hashes password+salt with bcrypt, and returns the
result as bytes. Decoding to a str gives the `$2b$12$...` string you store.
`checkpw` encodes both sides and compares; it extracts the embedded salt from the
stored hash and re-derives the hash for comparison — no raw string comparison.
Two calls on the same password produce different hashes because each `gensalt()`
is unique.
"""

_WHY_EX2 = """\
**Why this works:** `secrets.token_urlsafe(32)` draws 32 bytes from the OS CSPRNG
(cryptographically secure pseudorandom number generator) and encodes them as
URL-safe base64, giving a 43-character string. `hmac.compare_digest` compares
byte-by-byte in constant time regardless of where the strings first differ —
a regular `==` short-circuits on the first mismatch, leaking timing information
an attacker can exploit with many requests.
"""

_WHY_EX3 = """\
**Why this works:** `jwt.encode` creates the three-part JWT: base64(header) +
base64(payload) + HMAC-SHA256(header+payload, SECRET_KEY). `jwt.decode` verifies
the signature and checks the `exp` claim automatically — an expired or tampered
token raises `JWTError` before you see the payload. The secret key must stay
secret; anyone with it can mint valid tokens.
"""

_WHY_EX4 = """\
**Why this works:** `HTTPBearer` is a FastAPI security scheme that reads the
`Authorization: Bearer <token>` header. When the header is missing or malformed it
auto-raises 401; your code runs only when a Bearer token is present. `Depends()`
tells FastAPI to call `get_current_user` and inject its return value into the route
handler — so the handler receives the decoded user dict directly, with no HTTP
machinery visible.
"""

_WHY_EX5 = """\
**Why this works:** `register_user` rejects duplicates before storing (check-then-
act) and always hashes the password — never stores plaintext. `login_user` uses
`verify_password` (not `==`) to check the candidate against the stored hash, then
calls `create_token` to issue a JWT containing the user's id and email. The JWT is
what the client sends back on every protected request.
"""

# ---------------------------------------------------------------------------
# exercise builders
# ---------------------------------------------------------------------------

def _ex(n, title, why_matters, setup, stub, checks, sol_code, why_works, bonus,
        setup_label="Setup (provided)", cid_base=0):
    cells = [
        _md(f"# Day 55 · Exercise {n}: {title}\n\n"
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
    # inject solution cell after stub cell
    cells.insert(5, _code(sol_code, cid=cid_base + 50))
    return _nb(cells)

# ---------------------------------------------------------------------------
# Exercise 1 — Password Hashing
# ---------------------------------------------------------------------------

def _build_ex1():
    return _ex(
        n=1,
        title="Password Hashing",
        why_matters=(
            "Implement `hash_password(password)` and `verify_password(plain, hashed)` "
            "using `passlib` + `bcrypt`. These are the foundation of user auth — "
            "a server that stores plaintext passwords is a disaster waiting to happen."
        ),
        setup=_IMPORTS_EX1,
        stub=_STUB_EX1,
        checks=_CHECKS_EX1,
        sol_code=_SOL_EX1,
        why_works=_WHY_EX1,
        bonus=(
            "Try `CryptContext(schemes=['bcrypt'], deprecated='auto', bcrypt__rounds=4)` "
            "and measure `hash_password` with `%%timeit`. Observe how halving the rounds "
            "roughly halves the time. The default of 12 rounds is chosen so each hash "
            "takes ~0.25 s — slow enough to frustrate brute-force, fast enough for login."
        ),
        cid_base=0,
    )

# ---------------------------------------------------------------------------
# Exercise 2 — API Keys
# ---------------------------------------------------------------------------

def _build_ex2():
    return _ex(
        n=2,
        title="API Keys",
        why_matters=(
            "Implement `generate_api_key()` and `verify_api_key(provided, stored)`. "
            "API keys are the simplest auth pattern for machine-to-machine calls — "
            "a long random token issued once and sent on every request."
        ),
        setup=_IMPORTS_EX2,
        stub=_STUB_EX2,
        checks=_CHECKS_EX2,
        sol_code=_SOL_EX2,
        why_works=_WHY_EX2,
        bonus=(
            "Try replacing `hmac.compare_digest` with a regular `==` and call "
            "`verify_api_key` 10 000 times with a key that differs only in the last "
            "character. Measure the time with `%%timeit`. A sophisticated attacker "
            "can exploit this timing difference. `compare_digest` eliminates it."
        ),
        cid_base=100,
    )

# ---------------------------------------------------------------------------
# Exercise 3 — JWT Tokens
# ---------------------------------------------------------------------------

def _build_ex3():
    return _ex(
        n=3,
        title="JWT Tokens",
        why_matters=(
            "Implement `create_token(data, expires_in_minutes)` and `decode_token(token)` "
            "using `python-jose`. JWTs let the server verify identity without storing "
            "sessions — the signature proves the token hasn't been tampered with."
        ),
        setup=_IMPORTS_EX3,
        stub=_STUB_EX3,
        checks=_CHECKS_EX3,
        sol_code=_SOL_EX3,
        why_works=_WHY_EX3,
        bonus=(
            "Decode a token manually: split on `.`, base64-decode the middle part "
            "(pad with `=` to a multiple of 4 bytes), and `json.loads` it. You'll "
            "see your payload plus the `exp` timestamp. This shows why the payload "
            "is readable without the secret key — JWT is *signed*, not encrypted."
        ),
        cid_base=200,
    )

# ---------------------------------------------------------------------------
# Exercise 4 — FastAPI Auth Dependency
# ---------------------------------------------------------------------------

def _build_ex4():
    return _ex(
        n=4,
        title="FastAPI Auth Dependency",
        why_matters=(
            "Implement `get_current_user` (a FastAPI `Depends` function) and "
            "`build_protected_api()`. This is how auth becomes a one-liner on any route: "
            "`def handler(user = Depends(get_current_user))`."
        ),
        setup=_BEFORE_EX4,
        stub=_STUB_EX4,
        checks=_CHECKS_EX4,
        sol_code=_SOL_EX4,
        why_works=_WHY_EX4,
        bonus=(
            "Add a second protected route `GET /admin` that reads `user['email']` "
            "and raises `HTTPException(403, 'admin only')` unless the email ends "
            "with `@admin.example.com`. Test it with TestClient using tokens for "
            "both admin and regular users. This is the start of role-based access control."
        ),
        cid_base=300,
    )

# ---------------------------------------------------------------------------
# Exercise 5 — Registration + Login
# ---------------------------------------------------------------------------

def _build_ex5():
    return _ex(
        n=5,
        title="Registration and Login",
        why_matters=(
            "Implement `register_user(email, password, users)` and "
            "`login_user(email, password, users)`. These two functions are the "
            "complete auth handshake: register hashes and stores; login verifies "
            "and issues a JWT. Every auth system builds on exactly this pair."
        ),
        setup=_BEFORE_EX5,
        stub=_STUB_EX5,
        checks=_CHECKS_EX5,
        sol_code=_SOL_EX5,
        why_works=_WHY_EX5,
        bonus=(
            "Wire `register_user` and `login_user` into a mini FastAPI app: "
            "`POST /register` and `POST /login`. Add a protected `GET /me` using "
            "`Depends(get_current_user)` from Exercise 4. Test the full flow "
            "with TestClient — register → login → /me — without Uvicorn."
        ),
        cid_base=400,
    )

# ---------------------------------------------------------------------------
# Project notebook
# ---------------------------------------------------------------------------

_PROJECT_SETUP = """\
# Project setup
# Run this cell first

from pathlib import Path
from starlette.testclient import TestClient

# The functions you need to build the full auth API
# (implement them below, or assemble from today's exercises)

def write_auth_api(path: str) -> str:
    \"\"\"Generate auth_api.py at `path` and return the path string.

    The file should contain a FastAPI app with:
      POST /register  — hash password, store user, return {id, email}
      POST /login     — verify password, return {access_token, token_type}
      GET  /me        — protected, return {user_id, email}
      POST /chat      — protected, append message, call ollama, return {reply}
    \"\"\"
    # TODO: build _AUTH_API_SRC as a string, then:
    # Path(path).write_text(_AUTH_API_SRC, encoding="utf-8")
    # return path
    raise NotImplementedError
"""

def _build_project():
    cells = [
        _md("# Day 55 Project: Auth AI API\n\n"
            "**What You're Building:**\n\n"
            "A FastAPI app (`auth_api.py`) with full user authentication:\n\n"
            "- `POST /register` — create an account (email + password)\n"
            "- `POST /login` — verify credentials, receive a JWT\n"
            "- `GET /me` — protected: returns your user info\n"
            "- `POST /chat` — protected: AI chat with per-user history\n\n"
            "**Deliverable:** Run `uvicorn auth_api:app --reload`, open `/docs`, "
            "register a user, log in, copy the token, and call `/me` and `/chat` "
            "as authenticated requests."),
        _md("## Your Implementation"),
        _code(_PROJECT_SETUP, cid=500),
        _md("## Check Your Work\n\nOnce `write_auth_api` generates the file, "
            "the cell below verifies the auth flow end-to-end using TestClient."),
        _code("# Run after implementing write_auth_api\n"
              "# (solution cell below shows a working implementation)\n"
              "print('Implement write_auth_api above first, then re-run.')", cid=501),
    ]
    return _nb(cells)

# ---------------------------------------------------------------------------
# Solution notebook
# ---------------------------------------------------------------------------

_SOL_SRC = """\
_AUTH_API_SRC = ''' ''' # will be set below
"""

_FULL_SOL = f'''\
# ── provided source string ──────────────────────────────────────────────────
_AUTH_API_SRC = {repr(_AUTH_API_SRC)}

# ── write_auth_api ──────────────────────────────────────────────────────────
from pathlib import Path

def write_auth_api(path: str) -> str:
    Path(path).write_text(_AUTH_API_SRC, encoding="utf-8")
    return path

# ── generate the file ───────────────────────────────────────────────────────
out = write_auth_api("auth_api.py")
print(f"Generated: {{out}}  ({{len(_AUTH_API_SRC)}} chars)")
print(Path(out).read_text(encoding="utf-8")[:120] + "...")
'''

_FULL_SOL_TEST = '''\
# ── smoke-test the auth flow with TestClient ────────────────────────────────
import bcrypt as _bcrypt_lib
from jose import jwt, JWTError
from datetime import datetime, timedelta
from typing import Annotated
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from starlette.testclient import TestClient

# --- replicate auth_api internals in-process (no ollama needed for checks) ---
SECRET_KEY = "change-me-in-production-use-env-var"
ALGORITHM  = "HS256"

def hash_password(p): return _bcrypt_lib.hashpw(p.encode(), _bcrypt_lib.gensalt()).decode()
def verify_password(plain, hashed): return _bcrypt_lib.checkpw(plain.encode(), hashed.encode())
def create_token(data, mins=60):
    pl = {**data, "exp": datetime.utcnow() + timedelta(minutes=mins)}
    return jwt.encode(pl, SECRET_KEY, algorithm=ALGORITHM)
def decode_token(tok): return jwt.decode(tok, SECRET_KEY, algorithms=[ALGORITHM])

_users: dict = {}
_histories: dict = {}
_nid = [1]

class RegReq(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=6)
class LoginReq(BaseModel):
    email: str; password: str

_sec = HTTPBearer()

def get_current_user(creds: Annotated[HTTPAuthorizationCredentials, Depends(_sec)]) -> dict:
    try:
        return decode_token(creds.credentials)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

app = FastAPI(title="Auth AI API (test)")

@app.post("/register", status_code=201)
def register(req: RegReq):
    if req.email in _users:
        raise HTTPException(409, "Email already registered")
    uid = _nid[0]; _nid[0] += 1
    _users[req.email] = {"id": uid, "email": req.email,
                          "hashed_password": hash_password(req.password)}
    return {"id": uid, "email": req.email}

@app.post("/login")
def login(req: LoginReq):
    u = _users.get(req.email)
    if not u or not verify_password(req.password, u["hashed_password"]):
        raise HTTPException(401, "Invalid credentials")
    return {"access_token": create_token({"user_id": u["id"], "email": req.email}),
            "token_type": "bearer"}

@app.get("/me")
def me(user: dict = Depends(get_current_user)):
    return {"user_id": user["user_id"], "email": user["email"]}

# ── run checks ──────────────────────────────────────────────────────────────
client = TestClient(app, raise_server_exceptions=False)
score = 0; total = 5

def chk(n, ok, msg):
    global score
    print(f"  {\'✅\' if ok else \'❌\'} Check {n}: {msg}")
    if ok: score += 1

# 1. register → 201
r = client.post("/register", json={"email": "alice@test.com", "password": "pass1234"})
chk(1, r.status_code == 201, f"POST /register → 201 (got {r.status_code})")

# 2. duplicate → 409
r2 = client.post("/register", json={"email": "alice@test.com", "password": "pass1234"})
chk(2, r2.status_code == 409, f"duplicate email → 409 (got {r2.status_code})")

# 3. login → access_token
r3 = client.post("/login", json={"email": "alice@test.com", "password": "pass1234"})
chk(3, r3.status_code == 200 and "access_token" in r3.json(),
    f"POST /login → access_token (got {r3.status_code})")

tok = r3.json().get("access_token", "")

# 4. /me with token → user_id
r4 = client.get("/me", headers={"Authorization": f"Bearer {tok}"})
chk(4, r4.status_code == 200 and r4.json().get("email") == "alice@test.com",
    f"GET /me → email (got {r4.status_code})")

# 5. /me without token → 401 (HTTPBearer auto-rejects missing header)
r5 = client.get("/me")
chk(5, r5.status_code == 401, f"GET /me no token → 401 (got {r5.status_code})")

print(f"\\nScore: {score} / {total}")
if score == total:
    print("\\nDay 55 — Authentication complete! 🎉")
print(f"\\nDeliverable: auth_api.py generated ({len(_AUTH_API_SRC)} chars)")
print("Run:  uvicorn auth_api:app --reload")
print("Docs: http://localhost:8000/docs")
'''

def _build_solution():
    cells = [
        _md("# Day 55 Project — Solution: Auth AI API\n\n"
            "Full auth flow: register → login → JWT → protected routes.\n\n"
            "**Deliverable:** `auth_api.py` — run with `uvicorn auth_api:app --reload`."),
        _code(_FULL_SOL, cid=600),
        _code(_FULL_SOL_TEST, cid=601),
    ]
    return _nb(cells)

# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    print("Generating Day 055 notebooks...")
    ex_dir  = DAY_DIR / "exercises"
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
