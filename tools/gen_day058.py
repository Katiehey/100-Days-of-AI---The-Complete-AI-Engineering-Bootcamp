#!/usr/bin/env python3
"""gen_day058.py — generate Day 058: Streaming in Web Apps notebooks."""
from pathlib import Path
import json

ROOT    = Path(__file__).parent.parent
DAY     = "058"
SECTION = "04_real_apps"
OUT     = ROOT / SECTION / f"day_{DAY}"

(OUT / "exercises").mkdir(parents=True, exist_ok=True)
(OUT / "lessons").mkdir(parents=True, exist_ok=True)
(OUT / "project" / "solution").mkdir(parents=True, exist_ok=True)

# ── deliverable source ─────────────────────────────────────────────────────────
_STREAMING_API_SRC = '''\
"""streaming_api.py — Day 058: streaming chat API with SSE and WebSocket.

Run:  uvicorn streaming_api:app --reload
Docs: http://localhost:8000/docs
"""
import json
import os
from datetime import datetime

import ollama
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

MODEL       = os.environ.get("MODEL", "llama3.2")
APP_VERSION = "1.0.0"


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1)
    system: str = ""


app = FastAPI(title="Streaming Chat API", version=APP_VERSION)
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


@app.get("/stream/count")
def stream_count(n: int = 5):
    """Demo SSE endpoint — streams n count events (no Ollama)."""
    def generate():
        for i in range(n):
            yield "data: " + str(i) + "\\n\\n"
        yield "data: [DONE]\\n\\n"
    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/chat/stream")
def chat_stream(req: ChatRequest):
    """Stream Ollama response tokens as SSE events."""
    messages = []
    if req.system:
        messages.append({"role": "system", "content": req.system})
    messages.append({"role": "user", "content": req.prompt})

    def generate():
        chunks = ollama.chat(model=MODEL, messages=messages, stream=True)
        for chunk in chunks:
            token = chunk["message"]["content"]
            if token:
                payload = json.dumps({"token": token})
                yield "data: " + payload + "\\n\\n"
        yield "data: [DONE]\\n\\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.websocket("/ws")
async def websocket_chat(ws: WebSocket):
    """WebSocket endpoint — receives prompts, streams response token by token."""
    await ws.accept()
    try:
        while True:
            prompt = await ws.receive_text()
            chunks = ollama.chat(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
            )
            for chunk in chunks:
                token = chunk["message"]["content"]
                if token:
                    await ws.send_text(token)
            await ws.send_text("[DONE]")
    except WebSocketDisconnect:
        pass


if __name__ == "__main__":
    import uvicorn
    PORT = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=PORT)
'''

# ── notebook helpers ───────────────────────────────────────────────────────────
def nb(cells):
    return {
        "nbformat": 4, "nbformat_minor": 5,
        "metadata": {"kernelspec": {"display_name": "Python 3",
                                    "language": "python",
                                    "name": "python3"}},
        "cells": cells,
    }

def md(src):
    return {"cell_type": "markdown", "metadata": {}, "source": src}

def code(src):
    return {"cell_type": "code", "metadata": {}, "source": src,
            "outputs": [], "execution_count": None}

def save(path, notebook):
    Path(path).write_text(json.dumps(notebook, indent=1))

# Gate requires: markdown "## Your Implementation" → code stub (impl_idx)
#                → code solution (impl_idx+1) → checks → markdown "## Solution"
#                with ```python block (source of extracted solution).

# ══════════════════════════════════════════════════════════════════════════════
# EXERCISE 1 — build_sse_api
# ══════════════════════════════════════════════════════════════════════════════
_EX1_IMPORTS = """\
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from starlette.testclient import TestClient
"""

_EX1_STUB = """\
def build_sse_api() -> FastAPI:
    \"\"\"Return a FastAPI app with GET /count?n=5 that streams SSE events.

    Each event:   'data: {i}\\\\n\\\\n' for i in range(n)
    Final event:  'data: [DONE]\\\\n\\\\n'
    Content-Type: text/event-stream
    \"\"\"
    # TODO: create app, add GET /count route, return StreamingResponse
    raise NotImplementedError
"""

_EX1_SOLUTION = """\
def build_sse_api() -> FastAPI:
    app = FastAPI()

    @app.get("/count")
    def stream_count(n: int = 5):
        def generate():
            for i in range(n):
                yield "data: " + str(i) + "\\n\\n"
            yield "data: [DONE]\\n\\n"
        return StreamingResponse(generate(), media_type="text/event-stream")

    return app
"""

_EX1_CHECKS = """\
score, total = 0, 4
try:
    app    = build_sse_api()
    client = TestClient(app, raise_server_exceptions=False)

    r = client.get("/count?n=3")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    score += 1; print("\\u2705 /count returns 200")

    ct = r.headers.get("content-type", "")
    assert "text/event-stream" in ct, f"Expected text/event-stream, got {ct}"
    score += 1; print("\\u2705 content-type is text/event-stream")

    assert "data: 0" in r.text and "data: 1" in r.text and "data: 2" in r.text, (
        f"Body missing expected data lines: {r.text!r}")
    score += 1; print("\\u2705 body contains SSE data lines")

    assert "[DONE]" in r.text, f"[DONE] sentinel missing from body"
    score += 1; print("\\u2705 [DONE] sentinel present")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX1 = nb([
    md("# Day 058 — Exercise 1: SSE Counting Stream\n\n"
       "**Server-Sent Events (SSE)** let the server push data to the client over a single "
       "HTTP connection. FastAPI's `StreamingResponse` with `media_type='text/event-stream'` "
       "implements SSE. Each event is a `'data: ...\\n\\n'` string (two newlines = event delimiter).\n\n"
       "TestClient buffers the full response body, so you can assert on it as a plain string."),
    code(_EX1_IMPORTS),
    md("## Task\n\n"
       "Implement `build_sse_api()` — return a FastAPI app with:\n\n"
       "```\n"
       "GET /count?n=5\n"
       "```\n\n"
       "- Streams n SSE events: `data: 0\\n\\n`, `data: 1\\n\\n`, …, `data: {n-1}\\n\\n`\n"
       "- Ends with `data: [DONE]\\n\\n`\n"
       "- Returns `Content-Type: text/event-stream`"),
    md("## Your Implementation"),
    code(_EX1_STUB),
    code(_EX1_SOLUTION),
    md("## Automated checks"),
    code(_EX1_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX1_SOLUTION + "```\n\n"
       "**Why it works:** `StreamingResponse` accepts any Python generator. Each `yield` "
       "immediately flushes one SSE event to the client. The `[DONE]` sentinel is a "
       "convention so the browser `EventSource` knows when to stop listening.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_01.ipynb", EX1)

# ══════════════════════════════════════════════════════════════════════════════
# EXERCISE 2 — extract_tokens
# ══════════════════════════════════════════════════════════════════════════════
_EX2_IMPORTS = """\
import types
from typing import Generator, Iterable
"""

_EX2_STUB = """\
def extract_tokens(chunks: Iterable[dict]) -> Generator[str, None, None]:
    \"\"\"Yield non-empty content strings from Ollama streaming chunk dicts.

    Ollama chunk format: {\"message\": {\"content\": \"token\"}, ...}
    Skip chunks where content is empty string or the key is missing.
    \"\"\"
    # TODO: iterate chunks, yield chunk["message"]["content"] when non-empty
    raise NotImplementedError
"""

_EX2_SOLUTION = """\
def extract_tokens(chunks):
    for chunk in chunks:
        content = chunk.get("message", {}).get("content", "")
        if content:
            yield content
"""

_EX2_CHECKS = """\
score, total = 0, 4
try:
    # basic extraction
    chunks = [
        {"message": {"content": "Hello"}},
        {"message": {"content": " world"}},
        {"message": {"content": "!"}},
    ]
    tokens = list(extract_tokens(chunks))
    assert tokens == ["Hello", " world", "!"], f"Got {tokens}"
    score += 1; print("\\u2705 extracts non-empty content")

    # skip empty content
    chunks2 = [
        {"message": {"content": "A"}},
        {"message": {"content": ""}},
        {"message": {"content": "B"}},
    ]
    tokens2 = list(extract_tokens(chunks2))
    assert tokens2 == ["A", "B"], f"Got {tokens2}"
    score += 1; print("\\u2705 skips empty content")

    # missing content key
    chunks3 = [{"message": {}}, {"message": {"content": "hi"}}]
    tokens3 = list(extract_tokens(chunks3))
    assert tokens3 == ["hi"], f"Got {tokens3}"
    score += 1; print("\\u2705 handles missing content key")

    # must be a generator
    result = extract_tokens([{"message": {"content": "x"}}])
    assert isinstance(result, types.GeneratorType), "Must return a generator (use yield)"
    score += 1; print("\\u2705 returns a generator")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX2 = nb([
    md("# Day 058 — Exercise 2: Token Extraction from Ollama Chunks\n\n"
       "Ollama's `stream=True` mode returns an iterator of chunk dicts:\n\n"
       "```python\n"
       "{'message': {'content': 'Hello', 'role': 'assistant'}, 'done': False}\n"
       "```\n\n"
       "We need a **generator** that pulls out non-empty `content` strings and skips "
       "empty tokens (which Ollama emits on the final chunk and sometimes mid-stream). "
       "Because it is a pure function taking any iterable, it is testable with mock data."),
    code(_EX2_IMPORTS),
    md("## Task\n\n"
       "Implement `extract_tokens(chunks)` — a generator that:\n\n"
       "- Iterates over `chunks` (each is a dict)\n"
       "- `yield`s `chunk['message']['content']` when it is a non-empty string\n"
       "- Skips chunks where `content` is `''` or the key is missing"),
    md("## Your Implementation"),
    code(_EX2_STUB),
    code(_EX2_SOLUTION),
    md("## Automated checks"),
    code(_EX2_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX2_SOLUTION + "```\n\n"
       "**Why it works:** `.get` with nested defaults handles missing keys without "
       "raising `KeyError`. The `if content:` guard skips both empty strings and `None`. "
       "`yield` makes it a generator — lazy evaluation, no list allocation.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_02.ipynb", EX2)

# ══════════════════════════════════════════════════════════════════════════════
# EXERCISE 3 — build_streaming_chat_api
# ══════════════════════════════════════════════════════════════════════════════
_EX3_IMPORTS = """\
import json
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from starlette.testclient import TestClient
"""

_EX3_STUB = """\
class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1)


def build_streaming_chat_api(stream_fn=None) -> FastAPI:
    \"\"\"Build a FastAPI app with POST /chat/stream.

    stream_fn: optional callable(prompt: str) -> Iterable[str]
               Pass a fake generator for testing (no Ollama).
               If None, uses ollama.chat(model='llama3.2', stream=True).

    The endpoint:
    - Accepts JSON body {\"prompt\": \"...\"}
    - Returns 422 if prompt is empty (Pydantic Field(min_length=1) does this)
    - Streams SSE: 'data: {\"token\": \"...\"}\\\\n\\\\n' then 'data: [DONE]\\\\n\\\\n'
    \"\"\"
    # TODO: build app with POST /chat/stream → StreamingResponse
    raise NotImplementedError
"""

_EX3_SOLUTION = """\
def build_streaming_chat_api(stream_fn=None) -> FastAPI:
    app = FastAPI()

    class _ChatRequest(BaseModel):
        prompt: str = Field(min_length=1)

    @app.post("/chat/stream")
    def chat_stream(req: _ChatRequest):
        def generate():
            if stream_fn is not None:
                tokens = stream_fn(req.prompt)
            else:
                import ollama
                chunks = ollama.chat(
                    model="llama3.2",
                    messages=[{"role": "user", "content": req.prompt}],
                    stream=True,
                )
                tokens = (
                    c["message"]["content"]
                    for c in chunks
                    if c["message"]["content"]
                )
            for token in tokens:
                payload = json.dumps({"token": token})
                yield "data: " + payload + "\\n\\n"
            yield "data: [DONE]\\n\\n"

        return StreamingResponse(generate(), media_type="text/event-stream")

    return app
"""

_EX3_CHECKS = """\
score, total = 0, 5

def fake_stream(prompt):
    for token in ["Hello", " ", "world", "!"]:
        yield token

try:
    app    = build_streaming_chat_api(stream_fn=fake_stream)
    client = TestClient(app, raise_server_exceptions=False)

    r = client.post("/chat/stream", json={"prompt": "hi"})
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    score += 1; print("\\u2705 POST /chat/stream returns 200")

    ct = r.headers.get("content-type", "")
    assert "text/event-stream" in ct, f"Expected text/event-stream, got {ct}"
    score += 1; print("\\u2705 content-type is text/event-stream")

    assert "data:" in r.text, "Expected 'data:' SSE lines in body"
    assert '"token"' in r.text, "Expected JSON with 'token' key"
    score += 1; print('\\u2705 body contains SSE data: lines with token JSON')

    assert "[DONE]" in r.text, "[DONE] sentinel missing"
    score += 1; print("\\u2705 [DONE] sentinel present")

    r2 = client.post("/chat/stream", json={"prompt": ""})
    assert r2.status_code == 422, f"Expected 422 for empty prompt, got {r2.status_code}"
    score += 1; print("\\u2705 empty prompt returns 422")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX3 = nb([
    md("# Day 058 — Exercise 3: Streaming Chat API\n\n"
       "Combine `StreamingResponse` with Ollama's streaming mode to build a chat endpoint "
       "that yields tokens as SSE events. We use **dependency injection** via an optional "
       "`stream_fn` parameter — pass a fake generator in tests, use real Ollama in production."),
    code(_EX3_IMPORTS),
    md("## Task\n\n"
       "Implement `build_streaming_chat_api(stream_fn=None)` — return a FastAPI app with:\n\n"
       "```\n"
       "POST /chat/stream   body: {\"prompt\": \"...\"}   → SSE token stream\n"
       "```\n\n"
       "- If `stream_fn` is not None: call `stream_fn(prompt)` → iterate tokens\n"
       "- If `stream_fn` is None: use `ollama.chat(stream=True)` + `extract_tokens`\n"
       "- Emit each token as `data: {\"token\": \"...\"}\\n\\n`\n"
       "- End with `data: [DONE]\\n\\n`\n"
       "- `Field(min_length=1)` → Pydantic returns 422 on empty prompt automatically"),
    md("## Your Implementation"),
    code(_EX3_STUB),
    code(_EX3_SOLUTION),
    md("## Automated checks"),
    code(_EX3_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX3_SOLUTION + "```\n\n"
       "**Why it works:** The inner class `_ChatRequest` inherits Pydantic validation "
       "including the `min_length=1` constraint — empty prompt → 422 before `generate()` "
       "is ever called. The generator dispatches on `stream_fn` for testability.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_03.ipynb", EX3)

# ══════════════════════════════════════════════════════════════════════════════
# EXERCISE 4 — build_ws_app
# ══════════════════════════════════════════════════════════════════════════════
_EX4_IMPORTS = """\
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from starlette.testclient import TestClient
"""

_EX4_STUB = """\
def build_ws_app() -> FastAPI:
    \"\"\"Build a FastAPI app with a WebSocket endpoint at /ws.

    The endpoint should:
    1. Accept the connection: await ws.accept()
    2. Loop: receive text, send back 'Echo: {message}'
    3. Exit cleanly on WebSocketDisconnect
    \"\"\"
    # TODO: build app with @app.websocket("/ws") async def endpoint
    raise NotImplementedError
"""

_EX4_SOLUTION = """\
def build_ws_app() -> FastAPI:
    app = FastAPI()

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket):
        await ws.accept()
        try:
            while True:
                data = await ws.receive_text()
                await ws.send_text(f"Echo: {data}")
        except WebSocketDisconnect:
            pass

    return app
"""

_EX4_CHECKS = """\
score, total = 0, 3
try:
    app    = build_ws_app()
    client = TestClient(app, raise_server_exceptions=False)

    with client.websocket_connect("/ws") as ws:
        score += 1; print("\\u2705 /ws accepts WebSocket connection")

        ws.send_text("hello")
        data = ws.receive_text()
        assert data == "Echo: hello", f"Expected 'Echo: hello', got {data!r}"
        score += 1; print("\\u2705 echoes first message with 'Echo: ' prefix")

        ws.send_text("world")
        data2 = ws.receive_text()
        assert data2 == "Echo: world", f"Expected 'Echo: world', got {data2!r}"
        score += 1; print("\\u2705 echoes second message correctly")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX4 = nb([
    md("# Day 058 — Exercise 4: WebSocket Echo App\n\n"
       "**WebSockets** provide a full-duplex channel: both client and server can send "
       "messages at any time. Unlike SSE (one-way), WebSockets are bidirectional.\n\n"
       "`@app.websocket('/ws')` + `async def endpoint(ws: WebSocket):` is the FastAPI "
       "pattern. `TestClient.websocket_connect()` lets you test without a real browser — "
       "no async event loop setup needed on your side."),
    code(_EX4_IMPORTS),
    md("## Task\n\n"
       "Implement `build_ws_app()` — return a FastAPI app with:\n\n"
       "```\n"
       "WebSocket /ws\n"
       "```\n\n"
       "1. `await ws.accept()` — complete the WebSocket handshake\n"
       "2. Loop: `data = await ws.receive_text()` → `await ws.send_text(f'Echo: {data}')`\n"
       "3. `except WebSocketDisconnect: pass` — exit cleanly when client closes"),
    md("## Your Implementation"),
    code(_EX4_STUB),
    code(_EX4_SOLUTION),
    md("## Automated checks"),
    code(_EX4_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX4_SOLUTION + "```\n\n"
       "**Why it works:** The `with client.websocket_connect('/ws')` context manager "
       "opens the handshake and closes it on exit, which triggers `WebSocketDisconnect` "
       "in the server — that is why we catch it instead of letting it propagate.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_04.ipynb", EX4)

# ══════════════════════════════════════════════════════════════════════════════
# EXERCISE 5 — ChatHistory
# ══════════════════════════════════════════════════════════════════════════════
_EX5_STUB = """\
class ChatHistory:
    \"\"\"Manage conversation history for a streaming chat app.

    Methods
    -------
    add_message(role, content)
        Append {\"role\": role, \"content\": content} to history.
    build_messages()
        Return [system msg if set] + conversation history.
    clear()
        Clear history; keep the system prompt.
    __len__()
        Number of user/assistant messages (system prompt not counted).
    \"\"\"

    def __init__(self, system_prompt: str = ""):
        # TODO: store system_prompt; init empty message list
        raise NotImplementedError

    def add_message(self, role: str, content: str) -> None:
        raise NotImplementedError

    def build_messages(self) -> list:
        raise NotImplementedError

    def clear(self) -> None:
        raise NotImplementedError

    def __len__(self) -> int:
        raise NotImplementedError
"""

_EX5_SOLUTION = """\
class ChatHistory:
    def __init__(self, system_prompt: str = ""):
        self._system   = system_prompt
        self._messages: list = []

    def add_message(self, role: str, content: str) -> None:
        self._messages.append({"role": role, "content": content})

    def build_messages(self) -> list:
        messages = []
        if self._system:
            messages.append({"role": "system", "content": self._system})
        messages.extend(self._messages)
        return messages

    def clear(self) -> None:
        self._messages.clear()

    def __len__(self) -> int:
        return len(self._messages)
"""

_EX5_CHECKS = """\
score, total = 0, 5
try:
    # empty history, no system
    h = ChatHistory()
    assert h.build_messages() == [], f"Empty history should return [], got {h.build_messages()}"
    assert len(h) == 0
    score += 1; print("\\u2705 empty history returns []")

    # system prompt included first
    h2 = ChatHistory(system_prompt="You are helpful.")
    msgs = h2.build_messages()
    assert msgs == [{"role": "system", "content": "You are helpful."}], f"Got {msgs}"
    score += 1; print("\\u2705 system prompt appears first in build_messages()")

    # add_message
    h3 = ChatHistory(system_prompt="Be concise.")
    h3.add_message("user", "Hi")
    h3.add_message("assistant", "Hello!")
    msgs3 = h3.build_messages()
    assert len(msgs3) == 3, f"Expected 3, got {len(msgs3)}"
    assert msgs3[1] == {"role": "user", "content": "Hi"}
    assert msgs3[2] == {"role": "assistant", "content": "Hello!"}
    score += 1; print("\\u2705 add_message appends to history correctly")

    # __len__ counts user/assistant only
    assert len(h3) == 2, f"Expected 2 (user+assistant), got {len(h3)}"
    score += 1; print("\\u2705 __len__ counts only user/assistant messages")

    # clear keeps system prompt
    h3.clear()
    msgs_after = h3.build_messages()
    assert len(msgs_after) == 1 and msgs_after[0]["role"] == "system", (
        f"After clear expected [system], got {msgs_after}")
    assert len(h3) == 0
    score += 1; print("\\u2705 clear() empties history but keeps system prompt")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX5 = nb([
    md("# Day 058 — Exercise 5: ChatHistory\n\n"
       "A streaming chat app is stateless by default — each `POST /chat/stream` starts a "
       "fresh context. `ChatHistory` accumulates `user` and `assistant` messages across "
       "turns and serialises them into the list format Ollama's `messages=` parameter expects.\n\n"
       "An optional **system prompt** appears first in every call to set the assistant's persona."),
    code(""),   # no imports needed
    md("## Task\n\n"
       "Implement `ChatHistory`:\n\n"
       "| Method | Behaviour |\n"
       "|--------|-----------|\n"
       "| `__init__(system_prompt='')` | Store system prompt; init empty list |\n"
       "| `add_message(role, content)` | Append `{\"role\": role, \"content\": content}` |\n"
       "| `build_messages()` | System msg first (if set), then history list |\n"
       "| `clear()` | Wipe history; keep system prompt |\n"
       "| `__len__()` | Count of user/assistant messages only |"),
    md("## Your Implementation"),
    code(_EX5_STUB),
    code(_EX5_SOLUTION),
    md("## Automated checks"),
    code(_EX5_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX5_SOLUTION + "```\n\n"
       "**Why it works:** `_messages` holds only user/assistant entries; the system prompt "
       "is stored separately so `__len__` counts conversation turns, not system overhead. "
       "`build_messages()` constructs a fresh list each call — no aliasing bugs.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_05.ipynb", EX5)

# ══════════════════════════════════════════════════════════════════════════════
# PROJECT NOTEBOOK
# ══════════════════════════════════════════════════════════════════════════════
PROJECT = nb([
    md("# Day 058 — Project: Streaming Chat API\n\n"
       "Build `streaming_api.py` — a production-ready FastAPI server that streams "
       "Ollama responses via **Server-Sent Events** (SSE) and **WebSockets**."),
    md("## Deliverable\n\n"
       "`streaming_api.py` in `project/solution/` — a FastAPI app with four endpoints:\n\n"
       "| Endpoint | Method | Description |\n"
       "|----------|--------|-------------|\n"
       "| `/health` | GET | Health check |\n"
       "| `/stream/count` | GET | Demo SSE counting stream (no Ollama) |\n"
       "| `/chat/stream` | POST | Streams Ollama tokens as SSE events |\n"
       "| `/ws` | WebSocket | Bidirectional streaming chat |\n\n"
       "## How to run\n\n"
       "```bash\n"
       "uvicorn streaming_api:app --reload\n"
       "```\n\n"
       "- REST docs: http://localhost:8000/docs\n"
       "- Test SSE: `curl -N http://localhost:8000/stream/count?n=5`\n"
       "- Test WebSocket: `wscat -c ws://localhost:8000/ws`\n\n"
       "## Concepts used\n\n"
       "- `StreamingResponse` + `media_type='text/event-stream'` → SSE\n"
       "- Sync generator functions as the streaming body\n"
       "- `ollama.chat(stream=True)` → token-by-token Ollama responses\n"
       "- `WebSocket` / `WebSocketDisconnect` from FastAPI\n"
       "- `ChatHistory` class for multi-turn context management"),
])
save(OUT / "project" / "project.ipynb", PROJECT)

# ══════════════════════════════════════════════════════════════════════════════
# SOLUTION NOTEBOOK
# ══════════════════════════════════════════════════════════════════════════════
_FULL_SOL_CELL1 = (
    f"_STREAMING_API_SRC = {repr(_STREAMING_API_SRC)}\n"
    "from pathlib import Path\n"
    "Path('streaming_api.py').write_text(_STREAMING_API_SRC)\n"
    "print('streaming_api.py written.')"
)

_FULL_SOL_CELL2 = """\
import json
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from starlette.testclient import TestClient

# ── inline test app (no Ollama required) ──────────────────────────────────────
class _ChatReq(BaseModel):
    prompt: str = Field(min_length=1)

test_app = FastAPI()

@test_app.get("/health")
def _health():
    return {"status": "ok",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": "1.0.0"}

@test_app.get("/stream/count")
def _stream_count(n: int = 5):
    def gen():
        for i in range(n):
            yield "data: " + str(i) + "\\n\\n"
        yield "data: [DONE]\\n\\n"
    return StreamingResponse(gen(), media_type="text/event-stream")

@test_app.post("/chat/stream")
def _chat_stream(req: _ChatReq):
    def gen():
        for token in ["Day", " 058", " complete!"]:
            payload = json.dumps({"token": token})
            yield "data: " + payload + "\\n\\n"
        yield "data: [DONE]\\n\\n"
    return StreamingResponse(gen(), media_type="text/event-stream")

@test_app.websocket("/ws")
async def _ws(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            data = await ws.receive_text()
            await ws.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        pass

client = TestClient(test_app, raise_server_exceptions=False)

# /health
r = client.get("/health")
assert r.status_code == 200 and r.json()["status"] == "ok"
print("\\u2705 /health works")

# /stream/count
r2 = client.get("/stream/count?n=3")
assert r2.status_code == 200
assert "text/event-stream" in r2.headers["content-type"]
assert "data: 0" in r2.text and "[DONE]" in r2.text
print("\\u2705 GET /stream/count streams SSE")

# /chat/stream
r3 = client.post("/chat/stream", json={"prompt": "hello"})
assert r3.status_code == 200
assert "text/event-stream" in r3.headers["content-type"]
assert '"token"' in r3.text and "[DONE]" in r3.text
print("\\u2705 POST /chat/stream streams SSE tokens")

# empty prompt → 422
r4 = client.post("/chat/stream", json={"prompt": ""})
assert r4.status_code == 422
print("\\u2705 empty prompt \\u2192 422")

# WebSocket
with client.websocket_connect("/ws") as ws:
    ws.send_text("ping")
    msg = ws.receive_text()
    assert msg == "Echo: ping", f"Got {msg!r}"
print("\\u2705 WebSocket /ws echoes messages")

print("\\nDay 058 \\u2014 Streaming in Web Apps complete! \\U0001f389")
"""

SOLUTION = nb([
    md("# Day 058 — Solution: Streaming Chat API"),
    code(_FULL_SOL_CELL1),
    code(_FULL_SOL_CELL2),
])
save(OUT / "project" / "solution" / "solution.ipynb", SOLUTION)

# Write streaming_api.py to solution directory
(OUT / "project" / "solution" / "streaming_api.py").write_text(_STREAMING_API_SRC)

print(f"Day {DAY} notebooks written to {OUT}")
print("  exercises/  exercise_01 – exercise_05")
print("  project/    project.ipynb")
print("  project/solution/  solution.ipynb + streaming_api.py")
