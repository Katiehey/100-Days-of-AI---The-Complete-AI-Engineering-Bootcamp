#!/usr/bin/env python3
"""Generate all Day 053 notebooks: exercises 1-5, project, solution.

Day 053 — Frontend <-> Backend. Deliverable: a full-stack AI app (Streamlit
frontend calling a FastAPI backend over HTTP).

Section 4 strategy: the client functions take an INJECTED HTTP client (duck-typed
httpx interface). In production the frontend passes httpx.Client(base_url=...);
in the gated notebooks we pass TestClient(backend_app) — same code path, tested
in-process with no live server. The PROJECT/SOLUTION generate two runnable files,
backend.py and frontend.py, assembled from source strings via repr (never
inspect.getsource, which fails under nbconvert).
"""
import json
from pathlib import Path

ROOT    = Path(__file__).resolve().parent.parent
DAY_DIR = ROOT / "04_real_apps" / "day_053"

_cid = 0


def cid():
    global _cid
    _cid += 1
    return f"c{_cid:04d}"


def md(source: str) -> dict:
    return {"cell_type": "markdown", "id": cid(), "metadata": {}, "source": source}


def code(source: str) -> dict:
    return {
        "cell_type": "code",
        "id": cid(),
        "metadata": {},
        "outputs": [],
        "execution_count": None,
        "source": source,
    }


def nb(cells: list) -> dict:
    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "display_name": "ai-course",
                "language": "python",
                "name": "ai-course",
            },
            "language_info": {"name": "python", "version": "3.10.0"},
        },
        "cells": cells,
    }


def write_nb(path: Path, cells: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(nb(cells), indent=1), encoding="utf-8")
    print(f"  wrote {path.relative_to(ROOT)}")


# ---------------------------------------------------------------------------
# Shared setup + the provided backend (from Day 52)
# ---------------------------------------------------------------------------

SETUP = '''import warnings
warnings.filterwarnings('ignore')
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.testclient import TestClient
import httpx
import ollama'''


BACKEND_SRC = '''# ---- The AI backend (built on Day 52 — provided here) ----
class ChatRequest(BaseModel):
    message: str = Field(min_length=1, description='User message for the model')
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)


class ChatResponse(BaseModel):
    reply: str
    model: str


class HealthResponse(BaseModel):
    status: str
    model: str


PROMPT_TEMPLATES = {
    'summary':  'Summarize the following topic in two sentences: {topic}',
    'explain':  'Explain {topic} to a complete beginner.',
    'critique': 'List three criticisms of {topic}.',
}


def run_model(model: str, prompt: str, temperature: float = 0.7) -> str:
    resp = ollama.chat(
        model=model,
        messages=[{'role': 'user', 'content': prompt}],
        options={'temperature': temperature},
    )
    return resp['message']['content'].strip()


def build_api(model: str = 'llama3.2') -> FastAPI:
    app = FastAPI(title='AI API', version='1.0.0')

    @app.get('/health', response_model=HealthResponse)
    def health():
        return HealthResponse(status='ok', model=model)

    @app.get('/templates')
    def list_templates():
        return {'templates': list(PROMPT_TEMPLATES.keys())}

    @app.post('/chat', response_model=ChatResponse)
    def chat(req: ChatRequest):
        try:
            return ChatResponse(reply=run_model(model, req.message, req.temperature),
                                model=model)
        except Exception as e:
            raise HTTPException(status_code=503, detail=f'Model unavailable: {e}')

    @app.post('/render/{name}', response_model=ChatResponse)
    def render_chat(name: str, req: ChatRequest):
        if name not in PROMPT_TEMPLATES:
            raise HTTPException(status_code=404, detail=f'template {name!r} not found')
        prompt = PROMPT_TEMPLATES[name].format(topic=req.message)
        try:
            return ChatResponse(reply=run_model(model, prompt, req.temperature),
                                model=model)
        except Exception as e:
            raise HTTPException(status_code=503, detail=f'Model unavailable: {e}')

    return app'''


# ---------------------------------------------------------------------------
# Client-layer implementations (the thing the exercises build)
# ---------------------------------------------------------------------------

CHECK_HEALTH_IMPL = '''def check_health(client) -> bool:
    """Ping the backend's GET /health through an injected HTTP client.

    Returns True only if the request succeeds with 200 AND status == 'ok'.
    Any exception (backend down, connection refused) -> False, never raises.
    The `client` is duck-typed: an httpx.Client in production, a TestClient in
    tests — both expose .get / .post / .request.
    """
    try:
        resp = client.get('/health')
        return resp.status_code == 200 and resp.json().get('status') == 'ok'
    except Exception:
        return False'''


POST_CHAT_IMPL = '''def post_chat(client, message: str, temperature: float = 0.7) -> dict:
    """POST /chat honouring the JSON contract {message, temperature}.

    Returns the parsed {reply, model} on 200. On a non-200 status returns
    {'error': ..., 'status': code}; on a connection failure returns
    {'error': ...}. The frontend never sees a raw exception.
    """
    try:
        resp = client.post('/chat', json={'message': message, 'temperature': temperature})
    except Exception as e:
        return {'error': f'request failed: {e}'}
    if resp.status_code != 200:
        return {'error': f'backend returned {resp.status_code}', 'status': resp.status_code}
    return resp.json()'''


REQUEST_JSON_IMPL = '''def request_json(client, method: str, path: str, payload: dict = None) -> dict:
    """Call the backend and normalise EVERY outcome into one envelope:

        {'ok': bool, 'status': int | None, 'data': dict | None, 'error': str | None}

    - success (2xx):        ok=True,  status=code, data=json
    - error status (4xx/5xx): ok=False, status=code, error='HTTP <code>'
    - connection failure:   ok=False, status=None, error='connection error: ...'

    One shape for the whole frontend to branch on — no scattered try/except.
    """
    try:
        resp = client.request(method, path, json=payload)
    except Exception as e:
        return {'ok': False, 'status': None, 'data': None,
                'error': f'connection error: {e}'}
    ok = 200 <= resp.status_code < 300
    try:
        data = resp.json()
    except Exception:
        data = None
    return {
        'ok':     ok,
        'status': resp.status_code,
        'data':   data if ok else None,
        'error':  None if ok else f'HTTP {resp.status_code}',
    }'''


ADD_CORS_IMPL = '''def add_cors(app: FastAPI, origins: list) -> FastAPI:
    """Enable CORS so a browser front-end on a DIFFERENT origin can call this API.

    A browser enforces the same-origin policy: JavaScript on http://localhost:8501
    may not call http://localhost:8000 unless the server opts in with CORS
    headers. CORSMiddleware adds the `access-control-allow-origin` header (and
    answers preflight OPTIONS requests) for the origins you allow.
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )
    return app'''


AIAPPCLIENT_IMPL = '''class AIAppClient:
    """The frontend's typed gateway to the AI backend.

    Wraps an injected HTTP client (httpx.Client in production, TestClient in
    tests) so the exact same code runs against a live server or in-process.
    Every method returns plain data the UI can render — no HTTP details leak out.
    """

    def __init__(self, client):
        self.client = client

    def health(self) -> bool:
        return check_health(self.client)

    def chat(self, message: str, temperature: float = 0.7) -> dict:
        return post_chat(self.client, message, temperature)

    def templates(self) -> list:
        env = request_json(self.client, 'GET', '/templates')
        return env['data']['templates'] if env['ok'] else []

    def render(self, name: str, topic: str, temperature: float = 0.7) -> dict:
        env = request_json(self.client, 'POST', f'/render/{name}',
                           {'message': topic, 'temperature': temperature})
        return env['data'] if env['ok'] else {'error': env['error']}'''


# Cumulative provided stacks
_BASE          = SETUP + "\n\n\n" + BACKEND_SRC
_BEFORE_EX02   = _BASE + "\n\n\n" + CHECK_HEALTH_IMPL
_BEFORE_EX03   = _BASE + "\n\n\n" + CHECK_HEALTH_IMPL + "\n\n\n" + POST_CHAT_IMPL
_BEFORE_EX05   = _BASE + "\n\n\n" + "\n\n\n".join(
    [CHECK_HEALTH_IMPL, POST_CHAT_IMPL, REQUEST_JSON_IMPL])


# ---------------------------------------------------------------------------
# Deliverable file sources: backend.py + frontend.py
# ---------------------------------------------------------------------------

_BACKEND_LOGIC = BACKEND_SRC.split("\n", 1)[1]  # drop the leading provided-comment line

BACKEND_PY_SRC = (
    "import warnings\n"
    "warnings.filterwarnings('ignore')\n"
    "from fastapi import FastAPI, HTTPException\n"
    "from fastapi.middleware.cors import CORSMiddleware\n"
    "from pydantic import BaseModel, Field\n"
    "import ollama\n\n\n"
    + _BACKEND_LOGIC + "\n\n\n"
    + ADD_CORS_IMPL + "\n\n\n"
    "app = build_api()\n"
    "add_cors(app, ['http://localhost:8501'])\n\n\n"
    "if __name__ == '__main__':\n"
    "    import uvicorn\n"
    "    uvicorn.run(app, host='0.0.0.0', port=8000)\n"
)


FRONTEND_UI = '''BACKEND_URL = 'http://localhost:8000'

st.set_page_config(page_title='Full-Stack AI Chat', page_icon='\U0001f517')
st.title('\U0001f517 Full-Stack AI Chat')


@st.cache_resource
def get_client():
    """One HTTP client + gateway per session (cached across reruns)."""
    return AIAppClient(httpx.Client(base_url=BACKEND_URL, timeout=60.0))


api = get_client()

# Health badge: does the backend answer?
if api.health():
    st.success('Backend online')
else:
    st.error('Backend offline \\u2014 start it with:  uvicorn backend:app --reload')

if 'messages' not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m['role']):
        st.markdown(m['content'])

prompt = st.chat_input('Type a message...')
if prompt:
    st.session_state.messages.append({'role': 'user', 'content': prompt})
    with st.spinner('Calling backend...'):
        result = api.chat(prompt)
    reply = result.get('reply') or result.get('error') or '(no response)'
    st.session_state.messages.append({'role': 'assistant', 'content': reply})
    st.rerun()
'''

FRONTEND_PY_SRC = (
    "import streamlit as st\n"
    "import httpx\n\n\n"
    + CHECK_HEALTH_IMPL + "\n\n\n"
    + POST_CHAT_IMPL + "\n\n\n"
    + REQUEST_JSON_IMPL + "\n\n\n"
    + AIAPPCLIENT_IMPL + "\n\n\n"
    + FRONTEND_UI
)


WRITE_STACK_CELL = (
    "from pathlib import Path\n"
    "\n"
    "# The two runnable files of the full-stack app, embedded as strings so the\n"
    "# notebook can write them verbatim (no inspect.getsource under nbconvert).\n"
    "_BACKEND_SRC = " + repr(BACKEND_PY_SRC) + "\n"
    "_FRONTEND_SRC = " + repr(FRONTEND_PY_SRC) + "\n"
    "\n"
    "\n"
    "def write_full_stack(directory: str = '.') -> tuple:\n"
    '    """Write backend.py + frontend.py into `directory`; return (backend, frontend) paths."""\n'
    "    d = Path(directory)\n"
    "    d.mkdir(parents=True, exist_ok=True)\n"
    "    (d / 'backend.py').write_text(_BACKEND_SRC, encoding='utf-8')\n"
    "    (d / 'frontend.py').write_text(_FRONTEND_SRC, encoding='utf-8')\n"
    "    return str(d / 'backend.py'), str(d / 'frontend.py')"
)


# ---------------------------------------------------------------------------
# Exercise 01 — health check over HTTP
# ---------------------------------------------------------------------------

def ex01():
    global _cid; _cid = 0
    return [
        md(
            "# Day 053 — Exercise 1: Talk to the Backend\n\n"
            "**What you'll build:** `check_health(client)` — the frontend's first "
            "HTTP call. It pings the backend's `GET /health` and returns `True` only "
            "if the backend answers `200` with `status == 'ok'`; any failure returns "
            "`False`.\n\n"
            "**Why it matters:** Day 51 was a UI, Day 52 was an API. Today you connect "
            "them: the frontend talks to the backend over HTTP. The pattern that makes "
            "this testable is **an injected client** — your function takes a `client` "
            "object. In production it's an `httpx.Client`; in these checks it's a "
            "`TestClient` wrapping the backend in-process. Same code, no live server."
        ),
        md("## Provided: Setup + the Backend (from Day 52)"),
        code(_BASE),
        md("## Your Implementation"),
        code(
            "def check_health(client) -> bool:\n"
            '    """\n'
            "    GET /health via the injected client. Return True iff the response is\n"
            "    200 AND its JSON status is 'ok'. Any exception -> False (never raises).\n"
            '    """\n'
            "    # TODO: try:\n"
            "    #     resp = client.get('/health')\n"
            "    #     return resp.status_code == 200 and resp.json().get('status') == 'ok'\n"
            "    # TODO: except Exception:\n"
            "    #     return False\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    backend = TestClient(build_api())\n"
            "\n"
            "    # Check 1: healthy backend -> True\n"
            "    try:\n"
            "        assert check_health(backend) is True, 'expected True for a healthy backend'\n"
            "        passed += 1; print('✅ Check 1: healthy backend -> True')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: returns an actual bool\n"
            "    try:\n"
            "        assert isinstance(check_health(backend), bool), 'must return a bool'\n"
            "        passed += 1; print('✅ Check 2: returns a bool')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 2: {e}')\n"
            "\n"
            "    # Check 3: connection failure -> False (no raise)\n"
            "    try:\n"
            "        class _Dead:\n"
            "            def get(self, *a, **k):\n"
            "                raise httpx.ConnectError('connection refused')\n"
            "        assert check_health(_Dead()) is False, 'backend down must give False'\n"
            "        passed += 1; print('✅ Check 3: backend down -> False (no crash)')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 3: {e}')\n"
            "\n"
            "    # Check 4: wrong status value -> False\n"
            "    try:\n"
            "        degraded = FastAPI()\n"
            "        @degraded.get('/health')\n"
            "        def _h():\n"
            "            return {'status': 'degraded'}\n"
            "        assert check_health(TestClient(degraded)) is False, \"status != 'ok' must give False\"\n"
            "        passed += 1; print('✅ Check 4: non-ok status -> False')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 4: {e}')\n"
            "\n"
            "    # Check 5: missing /health route (404) -> False\n"
            "    try:\n"
            "        empty = TestClient(FastAPI())\n"
            "        assert check_health(empty) is False, 'a 404 must give False'\n"
            "        passed += 1; print('✅ Check 5: no /health route (404) -> False')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\U0001f389 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "\n"
            "_run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + CHECK_HEALTH_IMPL + "\n"
            "```\n\n"
            "**Why this works:** The function never assumes the backend is up. It "
            "wraps the call in try/except so a refused connection becomes a clean "
            "`False` instead of a crash — exactly what a health badge needs. Taking "
            "`client` as a parameter (dependency injection) is the key move: the check "
            "cell passes a `TestClient(build_api())` that runs the backend in-process, "
            "while `frontend.py` will pass a real `httpx.Client(base_url=...)`. One "
            "function, both worlds.\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 02 — POST the JSON contract
# ---------------------------------------------------------------------------

def ex02():
    global _cid; _cid = 100
    return [
        md(
            "# Day 053 — Exercise 2: The JSON Contract\n\n"
            "**What you'll build:** `post_chat(client, message, temperature)` — the "
            "frontend call that sends a chat message to the backend and reads the "
            "reply, honouring the shared JSON contract `{message, temperature}` → "
            "`{reply, model}`.\n\n"
            "**Why it matters:** Frontend and backend agree on *shapes*: the keys the "
            "client sends must match what the API's `ChatRequest` expects, and the "
            "client reads back exactly the keys `ChatResponse` promises. Get a key "
            "wrong and you get a 422. `post_chat` also turns any non-200 into a plain "
            "error dict, so the UI always has something to show."
        ),
        md("## Provided: Setup + Backend + check_health"),
        code(_BEFORE_EX02),
        md("## Your Implementation"),
        code(
            "def post_chat(client, message: str, temperature: float = 0.7) -> dict:\n"
            '    """\n'
            "    POST /chat with body {message, temperature}.\n"
            "    - 200 -> return the parsed JSON ({reply, model})\n"
            "    - non-200 -> {'error': ..., 'status': code}\n"
            "    - connection failure -> {'error': ...}\n"
            '    """\n'
            "    # TODO: try:\n"
            "    #     resp = client.post('/chat', json={'message': message, 'temperature': temperature})\n"
            "    # TODO: except Exception as e:\n"
            "    #     return {'error': f'request failed: {e}'}\n"
            "    # TODO: if resp.status_code != 200:\n"
            "    #     return {'error': f'backend returned {resp.status_code}', 'status': resp.status_code}\n"
            "    # TODO: return resp.json()\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    backend = TestClient(build_api())\n"
            "\n"
            "    # Check 1: valid call returns reply + model (Ollama)\n"
            "    try:\n"
            "        out = post_chat(backend, 'Reply with exactly: pong')\n"
            "        assert isinstance(out, dict), f'expected dict, got {type(out).__name__}'\n"
            "        assert 'reply' in out and 'model' in out, f'missing contract keys: {out}'\n"
            "        passed += 1; print('✅ Check 1: valid call -> {reply, model}')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: reply is a non-empty string\n"
            "    try:\n"
            "        out = post_chat(backend, 'Say hello in three words.')\n"
            "        assert isinstance(out['reply'], str) and len(out['reply']) > 0\n"
            "        passed += 1; print(f\"✅ Check 2: reply is non-empty ({len(out['reply'])} chars)\")\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 2: {e}')\n"
            "\n"
            "    # Check 3: empty message violates the contract -> error with status 422\n"
            "    try:\n"
            "        out = post_chat(backend, '')\n"
            "        assert 'error' in out, f'expected an error dict, got {out}'\n"
            "        assert out.get('status') == 422, f\"expected 422, got {out.get('status')}\"\n"
            "        passed += 1; print('✅ Check 3: empty message -> error (status 422)')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 3: {e}')\n"
            "\n"
            "    # Check 4: connection failure -> error dict (no crash)\n"
            "    try:\n"
            "        class _Dead:\n"
            "            def post(self, *a, **k):\n"
            "                raise httpx.ConnectError('refused')\n"
            "        out = post_chat(_Dead(), 'hi')\n"
            "        assert 'error' in out, 'connection failure must return an error dict'\n"
            "        passed += 1; print('✅ Check 4: backend down -> error dict')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 4: {e}')\n"
            "\n"
            "    # Check 5: the client sends the message under the agreed key\n"
            "    try:\n"
            "        spy = FastAPI()\n"
            "        @spy.post('/chat')\n"
            "        def _echo(req: ChatRequest):\n"
            "            return {'reply': req.message, 'model': 'echo'}\n"
            "        out = post_chat(TestClient(spy), 'contract-check')\n"
            "        assert out.get('reply') == 'contract-check', f'contract mismatch: {out}'\n"
            "        passed += 1; print('✅ Check 5: JSON contract keys line up front-to-back')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\U0001f389 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "\n"
            "_run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + POST_CHAT_IMPL + "\n"
            "```\n\n"
            "**Why this works:** The `json=` argument serialises the dict to a JSON "
            "body with the keys `message` and `temperature` — the exact fields the "
            "backend's `ChatRequest` declares. That agreement *is* the contract; the "
            "spy backend in Check 5 proves the keys line up. Non-200 responses become "
            "an `{'error', 'status'}` dict so the UI can show 'backend returned 422' "
            "instead of throwing. The connection-error branch keeps the frontend alive "
            "when the backend isn't running yet.\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 03 — one envelope for every outcome
# ---------------------------------------------------------------------------

def ex03():
    global _cid; _cid = 200
    return [
        md(
            "# Day 053 — Exercise 3: A Uniform Response Envelope\n\n"
            "**What you'll build:** `request_json(client, method, path, payload)` — a "
            "single helper that calls any backend route and normalises *every* outcome "
            "into one shape: `{'ok', 'status', 'data', 'error'}`.\n\n"
            "**Why it matters:** A frontend calls many endpoints, and each can succeed, "
            "return a 4xx/5xx, or fail to connect. Handling those three cases inline at "
            "every call site is a mess. One envelope function means the UI branches on "
            "`if env['ok']:` everywhere — the same discipline as the `(is_valid, "
            "result)` tuple from Day 51, generalised to HTTP."
        ),
        md("## Provided: Setup + Backend + check_health + post_chat"),
        code(_BEFORE_EX03),
        md("## Your Implementation"),
        code(
            "def request_json(client, method: str, path: str, payload: dict = None) -> dict:\n"
            '    """\n'
            "    Normalise every outcome into:\n"
            "        {'ok': bool, 'status': int|None, 'data': dict|None, 'error': str|None}\n"
            "    - 2xx           -> ok=True,  status=code, data=json\n"
            "    - 4xx/5xx       -> ok=False, status=code, error='HTTP <code>'\n"
            "    - conn failure  -> ok=False, status=None, error='connection error: ...'\n"
            '    """\n'
            "    # TODO: try:\n"
            "    #     resp = client.request(method, path, json=payload)\n"
            "    # TODO: except Exception as e:\n"
            "    #     return {'ok': False, 'status': None, 'data': None, 'error': f'connection error: {e}'}\n"
            "    # TODO: ok = 200 <= resp.status_code < 300\n"
            "    # TODO: try: data = resp.json()\n"
            "    #       except Exception: data = None\n"
            "    # TODO: return {'ok': ok, 'status': resp.status_code,\n"
            "    #               'data': data if ok else None,\n"
            "    #               'error': None if ok else f'HTTP {resp.status_code}'}\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    backend = TestClient(build_api())\n"
            "\n"
            "    # Check 1: success envelope for GET /templates\n"
            "    try:\n"
            "        env = request_json(backend, 'GET', '/templates')\n"
            "        assert env['ok'] is True and env['status'] == 200, f'bad envelope: {env}'\n"
            "        assert env['data'] is not None and env['error'] is None\n"
            "        passed += 1; print('✅ Check 1: 2xx -> ok=True with data')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: envelope always has the four keys\n"
            "    try:\n"
            "        env = request_json(backend, 'GET', '/templates')\n"
            "        for k in ('ok', 'status', 'data', 'error'):\n"
            "            assert k in env, f'missing key: {k}'\n"
            "        passed += 1; print('✅ Check 2: envelope has ok/status/data/error')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 2: {e}')\n"
            "\n"
            "    # Check 3: error status -> ok=False with status + error\n"
            "    try:\n"
            "        env = request_json(backend, 'GET', '/no-such-route')\n"
            "        assert env['ok'] is False and env['status'] == 404, f'expected 404 envelope: {env}'\n"
            "        assert env['data'] is None and env['error'] is not None\n"
            "        passed += 1; print('✅ Check 3: 404 -> ok=False, status=404')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 3: {e}')\n"
            "\n"
            "    # Check 4: connection failure -> ok=False, status=None\n"
            "    try:\n"
            "        class _Dead:\n"
            "            def request(self, *a, **k):\n"
            "                raise httpx.ConnectError('refused')\n"
            "        env = request_json(_Dead(), 'GET', '/health')\n"
            "        assert env['ok'] is False and env['status'] is None, f'bad conn envelope: {env}'\n"
            "        passed += 1; print('✅ Check 4: connection failure -> ok=False, status=None')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 4: {e}')\n"
            "\n"
            "    # Check 5: POST with a payload works (round-trips through /chat)\n"
            "    try:\n"
            "        env = request_json(backend, 'POST', '/chat', {'message': 'Say hi in 3 words.'})\n"
            "        assert env['ok'] is True and env['status'] == 200, f'expected 200: {env}'\n"
            "        assert 'reply' in env['data']\n"
            "        passed += 1; print('✅ Check 5: POST with payload -> ok=True')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\U0001f389 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "\n"
            "_run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + REQUEST_JSON_IMPL + "\n"
            "```\n\n"
            "**Why this works:** `client.request(method, path, json=payload)` is the "
            "generic form of `.get`/`.post`, so one function covers every verb. The "
            "envelope collapses three failure modes into a single predictable shape: "
            "the caller checks `env['ok']` and reads `env['data']` or `env['error']` — "
            "never a try/except at the call site. This is the backbone the `AIAppClient` "
            "class is built on in Exercise 5.\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 04 — CORS
# ---------------------------------------------------------------------------

def ex04():
    global _cid; _cid = 300
    return [
        md(
            "# Day 053 — Exercise 4: CORS — Let the Browser In\n\n"
            "**What you'll build:** `add_cors(app, origins)` — enable Cross-Origin "
            "Resource Sharing on the backend so a browser front-end served from a "
            "different origin can call the API.\n\n"
            "**Why it matters:** Your Python tests can call the backend freely, but a "
            "*browser* can't. The same-origin policy blocks JavaScript on "
            "`http://localhost:8501` from calling `http://localhost:8000` unless the "
            "server sends `access-control-allow-origin`. This is the #1 'it works in "
            "my script but not in the browser' bug — and one middleware fixes it."
        ),
        md("## Provided: Setup + Backend"),
        code(_BASE),
        md("## Your Implementation"),
        code(
            "def add_cors(app: FastAPI, origins: list) -> FastAPI:\n"
            '    """\n'
            "    Add CORSMiddleware allowing the given origins. Return the same app.\n"
            "    Allow all methods and headers; allow credentials.\n"
            '    """\n'
            "    # TODO: app.add_middleware(\n"
            "    #     CORSMiddleware,\n"
            "    #     allow_origins=origins,\n"
            "    #     allow_credentials=True,\n"
            "    #     allow_methods=['*'],\n"
            "    #     allow_headers=['*'],\n"
            "    # )\n"
            "    # TODO: return app\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "ALLOWED = 'http://localhost:8501'\n"
            "\n"
            "\n"
            "def _make_app():\n"
            "    app = FastAPI()\n"
            "    @app.get('/health')\n"
            "    def _h():\n"
            "        return {'status': 'ok'}\n"
            "    return app\n"
            "\n"
            "\n"
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: add_cors returns the app (a FastAPI instance)\n"
            "    try:\n"
            "        app = add_cors(_make_app(), [ALLOWED])\n"
            "        assert isinstance(app, FastAPI), 'add_cors must return the app'\n"
            "        client = TestClient(app)\n"
            "        passed += 1; print('✅ Check 1: add_cors returns the FastAPI app')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: allowed origin gets the access-control-allow-origin header\n"
            "    try:\n"
            "        r = client.get('/health', headers={'Origin': ALLOWED})\n"
            "        assert r.headers.get('access-control-allow-origin') == ALLOWED, \\\n"
            "            f\"missing/wrong ACAO header: {r.headers.get('access-control-allow-origin')}\"\n"
            "        passed += 1; print('✅ Check 2: allowed origin -> ACAO header set')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 2: {e}')\n"
            "\n"
            "    # Check 3: preflight OPTIONS is answered with 200 + ACAO\n"
            "    try:\n"
            "        pre = client.options('/health', headers={\n"
            "            'Origin': ALLOWED,\n"
            "            'Access-Control-Request-Method': 'GET',\n"
            "        })\n"
            "        assert pre.status_code == 200, f'preflight status {pre.status_code}'\n"
            "        assert pre.headers.get('access-control-allow-origin') == ALLOWED\n"
            "        passed += 1; print('✅ Check 3: preflight OPTIONS handled (200 + ACAO)')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 3: {e}')\n"
            "\n"
            "    # Check 4: a normal request (no Origin) still works\n"
            "    try:\n"
            "        r = client.get('/health')\n"
            "        assert r.status_code == 200 and r.json()['status'] == 'ok'\n"
            "        passed += 1; print('✅ Check 4: same-origin request still works')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 4: {e}')\n"
            "\n"
            "    # Check 5: a disallowed origin does NOT get an allow header for itself\n"
            "    try:\n"
            "        r = client.get('/health', headers={'Origin': 'http://evil.example'})\n"
            "        assert r.headers.get('access-control-allow-origin') != 'http://evil.example', \\\n"
            "            'disallowed origin must not be echoed as allowed'\n"
            "        passed += 1; print('✅ Check 5: disallowed origin is not allowed')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\U0001f389 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "\n"
            "_run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + ADD_CORS_IMPL + "\n"
            "```\n\n"
            "**Why this works:** `CORSMiddleware` intercepts responses and, when the "
            "request's `Origin` is in `allow_origins`, adds the "
            "`access-control-allow-origin` header the browser demands. It also answers "
            "the preflight `OPTIONS` request browsers send before a real cross-origin "
            "POST. Note this is a *browser* mechanism — `TestClient` and `httpx` ignore "
            "it, which is why your notebook tests worked without CORS but the deployed "
            "browser app needs it. `backend.py` calls `add_cors(app, ['http://localhost:8501'])`.\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 05 — the AIAppClient gateway
# ---------------------------------------------------------------------------

def ex05():
    global _cid; _cid = 400
    return [
        md(
            "# Day 053 — Exercise 5: The Frontend Gateway\n\n"
            "**What you'll build:** `AIAppClient` — the frontend's typed gateway to the "
            "backend. It wraps an injected HTTP client and exposes `health()`, "
            "`chat(message)`, `templates()`, and `render(name, topic)`, each returning "
            "plain data the UI renders.\n\n"
            "**Why it matters:** This is the seam between the two halves of your app. "
            "The Streamlit UI holds one `AIAppClient` and never touches HTTP directly — "
            "the same thin-shell-over-logic pattern as Days 51 and 52, now spanning the "
            "network. Because the client is injected, the tests drive it against an "
            "in-process backend; `frontend.py` drives it against a live `httpx.Client`."
        ),
        md("## Provided: Setup + Backend + check_health + post_chat + request_json"),
        code(_BEFORE_EX05),
        md("## Your Implementation"),
        code(
            "class AIAppClient:\n"
            '    """Typed gateway to the AI backend. Wraps an injected HTTP client."""\n'
            "\n"
            "    def __init__(self, client):\n"
            "        # TODO: self.client = client\n"
            "        pass\n"
            "\n"
            "    def health(self) -> bool:\n"
            "        # TODO: return check_health(self.client)\n"
            "        pass\n"
            "\n"
            "    def chat(self, message: str, temperature: float = 0.7) -> dict:\n"
            "        # TODO: return post_chat(self.client, message, temperature)\n"
            "        pass\n"
            "\n"
            "    def templates(self) -> list:\n"
            "        # TODO: env = request_json(self.client, 'GET', '/templates')\n"
            "        # TODO: return env['data']['templates'] if env['ok'] else []\n"
            "        pass\n"
            "\n"
            "    def render(self, name: str, topic: str, temperature: float = 0.7) -> dict:\n"
            "        # TODO: env = request_json(self.client, 'POST', f'/render/{name}',\n"
            "        #                          {'message': topic, 'temperature': temperature})\n"
            "        # TODO: return env['data'] if env['ok'] else {'error': env['error']}\n"
            "        pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    backend = TestClient(build_api())\n"
            "\n"
            "    # Check 1: gateway exposes the four methods\n"
            "    try:\n"
            "        assert 'AIAppClient' in globals()\n"
            "        for m in ('health', 'chat', 'templates', 'render'):\n"
            "            assert hasattr(AIAppClient, m), f'missing method: {m}'\n"
            "        api = AIAppClient(backend)\n"
            "        passed += 1; print('✅ Check 1: AIAppClient has health/chat/templates/render')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: health() -> True against the live in-process backend\n"
            "    try:\n"
            "        assert api.health() is True, 'health() should be True'\n"
            "        passed += 1; print('✅ Check 2: api.health() is True')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 2: {e}')\n"
            "\n"
            "    # Check 3: chat() returns a reply (Ollama)\n"
            "    try:\n"
            "        out = api.chat('Say hello in three words.')\n"
            "        assert isinstance(out, dict) and len(out.get('reply', '')) > 0, f'bad chat: {out}'\n"
            "        passed += 1; print('✅ Check 3: api.chat() returns a reply')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 3: {e}')\n"
            "\n"
            "    # Check 4: templates() lists the names\n"
            "    try:\n"
            "        names = api.templates()\n"
            "        assert isinstance(names, list) and 'summary' in names, f'bad templates: {names}'\n"
            "        passed += 1; print('✅ Check 4: api.templates() lists names')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 4: {e}')\n"
            "\n"
            "    # Check 5: render() works for a known name, errors for an unknown one\n"
            "    try:\n"
            "        ok = api.render('summary', 'Python')\n"
            "        assert len(ok.get('reply', '')) > 0, f'expected a reply: {ok}'\n"
            "        missing = api.render('does-not-exist', 'x')\n"
            "        assert 'error' in missing, f'expected an error for unknown template: {missing}'\n"
            "        passed += 1; print('✅ Check 5: render() renders known / errors unknown')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\U0001f389 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "\n"
            "_run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + AIAPPCLIENT_IMPL + "\n"
            "```\n\n"
            "**Why this works:** `AIAppClient` composes the three functions you built "
            "into one object with a clean method per backend route. It never exposes "
            "HTTP details — `health()` gives a bool, `chat()` gives a dict, "
            "`templates()` gives a list — so the Streamlit UI code stays about "
            "*display*, not networking. Injecting the client keeps it testable: the "
            "checks use `TestClient(build_api())`; `frontend.py` uses "
            "`httpx.Client(base_url='http://localhost:8000')`.\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Project notebook (student template — not executed by the gate)
# ---------------------------------------------------------------------------

def project_nb():
    global _cid; _cid = 500
    all_code = _BEFORE_EX05 + "\n\n\n" + ADD_CORS_IMPL + "\n\n\n" + AIAPPCLIENT_IMPL
    return [
        md(
            "# Day 053 Project: Full-Stack AI App\n\n"
            "## What You're Building\n\n"
            "The two halves finally meet. A **FastAPI backend** (`backend.py`, with "
            "CORS) and a **Streamlit frontend** (`frontend.py`) that calls it over HTTP "
            "through your `AIAppClient`. Run the backend, run the frontend, and the "
            "browser UI talks to the API which talks to Ollama. Two files, one app.\n\n"
            "## Project Requirements\n\n"
            "1. Use the provided `build_api`, `add_cors`, and `AIAppClient`.\n"
            "2. Build an in-process backend with `TestClient(build_api())`, wrap it in "
            "an `AIAppClient`, and exercise `health`, `chat`, `templates`, `render`.\n"
            "3. Call `write_full_stack('.')` to generate `backend.py` + `frontend.py`.\n"
            "4. Run `_run_project_checks()` to verify both files.\n"
            "5. Then, in **two terminals**:\n"
            "   `uvicorn backend:app --reload`  and  `streamlit run frontend.py`.\n\n"
            "## Bonus Challenges\n\n"
            "- Add a sidebar dropdown in `frontend.py` that calls `api.templates()` and "
            "lets the user run a template via `api.render(name, topic)`.\n"
            "- Show the backend health as a coloured badge that refreshes each rerun.\n"
            "- Add a `timeout` to the httpx client and surface a friendly message when "
            "the backend is slow."
        ),
        md("## Provided: Backend + Client Layer + AIAppClient"),
        code(all_code),
        md("## Provided: Full-Stack File Writer"),
        code(WRITE_STACK_CELL),
        md("## Your Pipeline"),
        code(
            "# TODO: backend = TestClient(build_api())\n"
            "# TODO: api = AIAppClient(backend)\n"
            "# TODO: print('health   :', api.health())\n"
            "# TODO: print('chat     :', api.chat('Say hello in 3 words.'))\n"
            "# TODO: print('templates:', api.templates())\n"
            "# TODO: print('render   :', api.render('summary', 'FastAPI'))\n"
            "#\n"
            "# TODO: b, f = write_full_stack('.')\n"
            "# TODO: print('Wrote', b, 'and', f)\n"
            "# TODO: print('Run:  uvicorn backend:app --reload   (terminal 1)')\n"
            "# TODO: print('Run:  streamlit run frontend.py       (terminal 2)')"
        ),
        md("## Checks"),
        code(
            "import os\n"
            "\n"
            "\n"
            "def _run_project_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: AIAppClient works against the in-process backend\n"
            "    try:\n"
            "        assert 'api' in globals() and isinstance(api, AIAppClient), 'create api = AIAppClient(...)'\n"
            "        assert api.health() is True, 'api.health() should be True'\n"
            "        passed += 1; print('✅ Check 1: AIAppClient talks to the backend')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: both files written\n"
            "    try:\n"
            "        assert os.path.exists('backend.py'), 'backend.py not found — call write_full_stack()'\n"
            "        assert os.path.exists('frontend.py'), 'frontend.py not found — call write_full_stack()'\n"
            "        passed += 1; print('✅ Check 2: backend.py + frontend.py written')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 2: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    back = open('backend.py', encoding='utf-8').read()\n"
            "    front = open('frontend.py', encoding='utf-8').read()\n"
            "\n"
            "    # Check 3: backend.py is a FastAPI app with CORS + module-level app\n"
            "    try:\n"
            "        assert 'from fastapi import FastAPI' in back\n"
            "        assert 'CORSMiddleware' in back, 'backend.py must enable CORS'\n"
            "        assert 'app = build_api()' in back, 'backend.py must expose module-level app'\n"
            "        passed += 1; print('✅ Check 3: backend.py has FastAPI + CORS + app')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 3: {e}')\n"
            "\n"
            "    # Check 4: frontend.py is a Streamlit app using httpx + AIAppClient\n"
            "    try:\n"
            "        assert 'import streamlit as st' in front\n"
            "        assert 'httpx.Client' in front, 'frontend.py must use httpx.Client'\n"
            "        assert 'AIAppClient' in front, 'frontend.py must use AIAppClient'\n"
            "        assert 'st.chat_input' in front, 'frontend.py must have a chat UI'\n"
            "        passed += 1; print('✅ Check 4: frontend.py wires httpx -> AIAppClient -> UI')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 4: {e}')\n"
            "\n"
            "    # Check 5: both files compile\n"
            "    try:\n"
            "        compile(back, 'backend.py', 'exec')\n"
            "        compile(front, 'frontend.py', 'exec')\n"
            "        passed += 1; print('✅ Check 5: both files compile as valid Python')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\U0001f389 Project complete! Two terminals: uvicorn backend:app  +  streamlit run frontend.py')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "\n"
            "_run_project_checks()"
        ),
    ]


# ---------------------------------------------------------------------------
# Solution notebook (runs clean under nbconvert — TestClient only, no servers)
# ---------------------------------------------------------------------------

def solution_nb():
    global _cid; _cid = 600
    all_code = _BEFORE_EX05 + "\n\n\n" + ADD_CORS_IMPL + "\n\n\n" + AIAPPCLIENT_IMPL
    return [
        md(
            "# Day 053 Solution — Full-Stack AI App\n\n"
            "Section 4, Day 3. Wires the Streamlit frontend to the FastAPI backend over "
            "HTTP. This notebook drives the `AIAppClient` against an in-process "
            "`TestClient` backend (no live server), verifies CORS, then generates the "
            "two runnable files. Launch with `uvicorn backend:app` + `streamlit run "
            "frontend.py`."
        ),
        code(all_code),
        md("## Step 1 — Wire the Client to an In-Process Backend"),
        code(
            "backend = TestClient(build_api())\n"
            "api = AIAppClient(backend)\n"
            "\n"
            "print('health   :', api.health())\n"
            "print('templates:', api.templates())\n"
            "assert api.health() is True\n"
            "assert 'summary' in api.templates()"
        ),
        md("## Step 2 — Call Through the Full Stack (Ollama)"),
        code(
            "chat = api.chat('Say hello in exactly three words.')\n"
            "print('chat   :', chat)\n"
            "assert 'reply' in chat and len(chat['reply']) > 0\n"
            "\n"
            "rendered = api.render('summary', 'FastAPI')\n"
            "print('render :', rendered.get('reply', rendered)[:200])\n"
            "assert 'reply' in rendered and len(rendered['reply']) > 0"
        ),
        md("## Step 3 — Verify CORS on the Backend"),
        code(
            "cors_app = add_cors(build_api(), ['http://localhost:8501'])\n"
            "cc = TestClient(cors_app)\n"
            "r = cc.get('/health', headers={'Origin': 'http://localhost:8501'})\n"
            "print('ACAO header:', r.headers.get('access-control-allow-origin'))\n"
            "assert r.headers.get('access-control-allow-origin') == 'http://localhost:8501'\n"
            "print('CORS is enabled for the Streamlit origin.')"
        ),
        md("## Step 4 — Generate backend.py + frontend.py"),
        code(WRITE_STACK_CELL),
        code(
            "b, f = write_full_stack('.')\n"
            "back = open(b, encoding='utf-8').read()\n"
            "front = open(f, encoding='utf-8').read()\n"
            "print(f'Wrote {b} ({len(back)} chars) and {f} ({len(front)} chars)')\n"
            "\n"
            "assert 'CORSMiddleware' in back and 'app = build_api()' in back\n"
            "assert 'httpx.Client' in front and 'AIAppClient' in front and 'st.chat_input' in front\n"
            "compile(back, 'backend.py', 'exec')\n"
            "compile(front, 'frontend.py', 'exec')\n"
            "print('Both files verified: valid Python, CORS on backend, httpx+AIAppClient on frontend.')"
        ),
        md("## Step 5 — How to Run It"),
        code(
            "print('Terminal 1:  uvicorn backend:app --reload')\n"
            "print('Terminal 2:  streamlit run frontend.py')\n"
            "print('Then open http://localhost:8501 — the UI calls the API over HTTP.')\n"
            "print('\\nDay 53 — Full-Stack AI App complete! \U0001f389')"
        ),
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Generating Day 053 notebooks...")
    ex_dir   = DAY_DIR / "exercises"
    proj_dir = DAY_DIR / "project"
    sol_dir  = proj_dir / "solution"
    for d in (ex_dir, proj_dir, sol_dir):
        d.mkdir(parents=True, exist_ok=True)

    write_nb(ex_dir   / "exercise_01.ipynb", ex01())
    write_nb(ex_dir   / "exercise_02.ipynb", ex02())
    write_nb(ex_dir   / "exercise_03.ipynb", ex03())
    write_nb(ex_dir   / "exercise_04.ipynb", ex04())
    write_nb(ex_dir   / "exercise_05.ipynb", ex05())
    write_nb(proj_dir / "project.ipynb",     project_nb())
    write_nb(sol_dir  / "solution.ipynb",    solution_nb())
    print("Done.")


if __name__ == "__main__":
    main()
