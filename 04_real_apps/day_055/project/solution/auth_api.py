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
