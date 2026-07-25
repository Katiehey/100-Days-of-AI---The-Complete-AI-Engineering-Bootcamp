#!/usr/bin/env python3
"""Generate all Day 052 notebooks: exercises 1-5, project, solution.

Day 052 — FastAPI Fundamentals. Deliverable: an AI API served over HTTP.

Section 4 strategy: the gate runs Jupyter notebooks, not a live server. So the
EXERCISES build route-factory functions and test them with starlette's
``TestClient`` (in-process, no uvicorn), while the PROJECT/SOLUTION generate a
real, runnable ``main.py`` (launched with ``uvicorn main:app``). The main.py is
assembled from a pre-built source string via ``repr`` — never inspect.getsource,
which fails under nbconvert (notebook objects have no source file).
"""
import json
from pathlib import Path

ROOT    = Path(__file__).resolve().parent.parent
DAY_DIR = ROOT / "04_real_apps" / "day_052"

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
# Shared setup + implementations
# ---------------------------------------------------------------------------

SETUP = '''import warnings
warnings.filterwarnings('ignore')
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from starlette.testclient import TestClient
import ollama'''


MODELS_IMPL = '''class ChatRequest(BaseModel):
    """Request body for the chat endpoints."""
    message: str = Field(min_length=1, description='User message for the model')
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)


class ChatResponse(BaseModel):
    """Response body returned by the chat endpoints."""
    reply: str
    model: str


class HealthResponse(BaseModel):
    """Response body for the health check."""
    status: str
    model: str'''


HEALTH_IMPL = '''def create_health_app() -> FastAPI:
    """Return a FastAPI app with a single liveness route.

    GET /health -> {'status': 'ok', 'model': 'llama3.2'}  (HTTP 200)
    """
    app = FastAPI(title='AI API', version='1.0.0')

    @app.get('/health')
    def health():
        return {'status': 'ok', 'model': 'llama3.2'}

    return app'''


ECHO_IMPL = MODELS_IMPL + '''


def create_echo_app() -> FastAPI:
    """POST /echo — validate a ChatRequest and echo it back as a ChatResponse,
    WITHOUT calling the model. Deterministic, so it tests the request/response
    contract (and FastAPI's automatic 422 on bad input) with no LLM involved.
    """
    app = FastAPI()

    @app.post('/echo', response_model=ChatResponse)
    def echo(req: ChatRequest):
        return ChatResponse(reply=req.message, model='echo')

    return app'''


CHAT_IMPL = '''def create_chat_app(model: str = 'llama3.2') -> FastAPI:
    """POST /chat — send the message to Ollama and return a ChatResponse.

    Wrap the model call in try/except and convert any failure into an
    HTTPException(503) so the client gets a clean error, not a 500 stack trace.
    """
    app = FastAPI()

    @app.post('/chat', response_model=ChatResponse)
    def chat(req: ChatRequest):
        try:
            resp = ollama.chat(
                model=model,
                messages=[{'role': 'user', 'content': req.message}],
                options={'temperature': req.temperature},
            )
            return ChatResponse(reply=resp['message']['content'].strip(), model=model)
        except Exception as e:
            raise HTTPException(status_code=503, detail=f'Model unavailable: {e}')

    return app'''


TEMPLATES_IMPL = '''PROMPT_TEMPLATES = {
    'summary':  'Summarize the following topic in two sentences: {topic}',
    'explain':  'Explain {topic} to a complete beginner.',
    'critique': 'List three criticisms of {topic}.',
}'''


TEMPLATE_APP_IMPL = TEMPLATES_IMPL + '''


def create_template_app() -> FastAPI:
    """A prompt-template service using PATH and QUERY parameters.

    GET /templates                    -> list of template names
    GET /render/{name}?topic=...      -> the rendered prompt string
    Unknown template name             -> HTTPException(404)
    """
    app = FastAPI()

    @app.get('/templates')
    def list_templates():
        return {'templates': list(PROMPT_TEMPLATES.keys())}

    @app.get('/render/{name}')
    def render(name: str, topic: str = 'AI'):
        if name not in PROMPT_TEMPLATES:
            raise HTTPException(status_code=404, detail=f'template {name!r} not found')
        return {'name': name, 'prompt': PROMPT_TEMPLATES[name].format(topic=topic)}

    return app'''


RUN_MODEL_IMPL = '''def run_model(model: str, prompt: str, temperature: float = 0.7) -> str:
    """Call Ollama once and return the reply text. Raises on model error."""
    resp = ollama.chat(
        model=model,
        messages=[{'role': 'user', 'content': prompt}],
        options={'temperature': temperature},
    )
    return resp['message']['content'].strip()'''


BUILD_API_IMPL = '''def build_api(model: str = 'llama3.2') -> FastAPI:
    """Assemble the complete AI API: health, templates, chat, and templated chat."""
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


# Cumulative provided stacks
_BEFORE_EX03 = "\n\n\n".join([SETUP, MODELS_IMPL])
_BEFORE_EX04 = "\n\n\n".join([SETUP, MODELS_IMPL])
_BEFORE_EX05 = "\n\n\n".join([SETUP, MODELS_IMPL, TEMPLATES_IMPL, RUN_MODEL_IMPL])


# ---------------------------------------------------------------------------
# main.py source (assembled once; written verbatim by project + solution)
# ---------------------------------------------------------------------------

MAIN_PY_SRC = (
    "import warnings\n"
    "warnings.filterwarnings('ignore')\n"
    "from fastapi import FastAPI, HTTPException\n"
    "from pydantic import BaseModel, Field\n"
    "import ollama\n\n\n"
    + MODELS_IMPL + "\n\n\n"
    + TEMPLATES_IMPL + "\n\n\n"
    + RUN_MODEL_IMPL + "\n\n\n"
    + BUILD_API_IMPL + "\n\n\n"
    "app = build_api()\n\n\n"
    "if __name__ == '__main__':\n"
    "    import uvicorn\n"
    "    uvicorn.run(app, host='0.0.0.0', port=8000)\n"
)

WRITE_MAIN_CELL = (
    "from pathlib import Path\n"
    "\n"
    "# The full FastAPI app source (models + templates + run_model + build_api +\n"
    "# a uvicorn entry point). Embedded as a string so we can write it to a real\n"
    "# file — the runnable deliverable you launch with `uvicorn main:app`.\n"
    "_MAIN_SRC = " + repr(MAIN_PY_SRC) + "\n"
    "\n"
    "\n"
    "def write_api_app(path: str = 'main.py') -> str:\n"
    '    """Write the self-contained FastAPI app to `path` and return the path."""\n'
    "    Path(path).write_text(_MAIN_SRC, encoding='utf-8')\n"
    "    return path"
)


# ---------------------------------------------------------------------------
# Exercise 01 — first endpoint + TestClient
# ---------------------------------------------------------------------------

def ex01():
    global _cid; _cid = 0
    return [
        md(
            "# Day 052 — Exercise 1: Your First Endpoint\n\n"
            "**What you'll build:** `create_health_app()` — a FastAPI app with one "
            "route, `GET /health`, that returns `{'status': 'ok', 'model': "
            "'llama3.2'}`. You'll test it with `TestClient` — no server needed.\n\n"
            "**Why it matters:** Yesterday you built a UI. Today you build the other "
            "half of a real app: an HTTP API any client can call. FastAPI turns a "
            "Python function into a web endpoint with one decorator. And "
            "`TestClient` lets you call that endpoint *in-process* — the same way "
            "you'll test every API in this section, without ever starting a server."
        ),
        md("## Provided: Setup"),
        code(SETUP),
        md("## Your Implementation"),
        code(
            "def create_health_app() -> FastAPI:\n"
            '    """\n'
            "    Return a FastAPI app with one route:\n"
            "        GET /health -> {'status': 'ok', 'model': 'llama3.2'}\n"
            '    """\n'
            "    app = FastAPI(title='AI API', version='1.0.0')\n"
            "\n"
            "    # TODO: define a GET /health route with a decorator:\n"
            "    # @app.get('/health')\n"
            "    # def health():\n"
            "    #     return {'status': 'ok', 'model': 'llama3.2'}\n"
            "\n"
            "    return app"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: create_health_app returns a FastAPI instance\n"
            "    try:\n"
            "        app = create_health_app()\n"
            "        assert isinstance(app, FastAPI), f'expected FastAPI, got {type(app).__name__}'\n"
            "        client = TestClient(app)\n"
            "        passed += 1; print('✅ Check 1: create_health_app returns a FastAPI app')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: GET /health returns HTTP 200\n"
            "    try:\n"
            "        r = client.get('/health')\n"
            "        assert r.status_code == 200, f'expected 200, got {r.status_code}'\n"
            "        passed += 1; print('✅ Check 2: GET /health -> 200')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 2: {e}')\n"
            "\n"
            "    # Check 3: body is JSON with status == 'ok'\n"
            "    try:\n"
            "        body = client.get('/health').json()\n"
            "        assert body.get('status') == 'ok', f\"expected status ok, got {body}\"\n"
            "        passed += 1; print('✅ Check 3: /health body has status == ok')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 3: {e}')\n"
            "\n"
            "    # Check 4: unknown route returns 404\n"
            "    try:\n"
            "        assert client.get('/does-not-exist').status_code == 404, 'expected 404'\n"
            "        passed += 1; print('✅ Check 4: unknown route -> 404')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 4: {e}')\n"
            "\n"
            "    # Check 5: /health reports the model\n"
            "    try:\n"
            "        body = client.get('/health').json()\n"
            "        assert 'model' in body, f\"expected a model key, got {body}\"\n"
            "        passed += 1; print(f\"✅ Check 5: /health reports model={body['model']!r}\")\n"
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
            + HEALTH_IMPL + "\n"
            "```\n\n"
            "**Why this works:** `FastAPI()` is the app object; `@app.get('/health')` "
            "registers the function below it as the handler for that path and method. "
            "Return a dict and FastAPI serialises it to JSON with a 200 status "
            "automatically. `TestClient(app)` wraps the app and lets you call it like "
            "an HTTP client (`client.get('/health')`) entirely in-process — no uvicorn, "
            "no ports, no network. That is how every endpoint in this section is "
            "tested.\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 02 — request/response models
# ---------------------------------------------------------------------------

def ex02():
    global _cid; _cid = 100
    return [
        md(
            "# Day 052 — Exercise 2: Request & Response Models\n\n"
            "**What you'll build:** the Pydantic models `ChatRequest` and "
            "`ChatResponse`, plus `create_echo_app()` — a `POST /echo` endpoint that "
            "validates the request body and echoes it back as a typed response.\n\n"
            "**Why it matters:** An API is a contract. FastAPI uses Pydantic models "
            "(Day 4) as that contract: declare `ChatRequest` as the parameter type and "
            "FastAPI parses the JSON body, validates it, and returns a **422** "
            "automatically on bad input — before your code runs. `response_model` does "
            "the same on the way out. You write the shapes; FastAPI enforces them."
        ),
        md("## Provided: Setup"),
        code(SETUP),
        md("## Your Implementation"),
        code(
            "class ChatRequest(BaseModel):\n"
            '    """Request body for the chat endpoints."""\n'
            "    # TODO: message: str = Field(min_length=1, description='User message for the model')\n"
            "    # TODO: temperature: float = Field(default=0.7, ge=0.0, le=1.0)\n"
            "    pass\n"
            "\n"
            "\n"
            "class ChatResponse(BaseModel):\n"
            '    """Response body returned by the chat endpoints."""\n'
            "    # TODO: reply: str\n"
            "    # TODO: model: str\n"
            "    pass\n"
            "\n"
            "\n"
            "def create_echo_app() -> FastAPI:\n"
            '    """POST /echo — validate a ChatRequest, echo it as a ChatResponse (no model call)."""\n'
            "    app = FastAPI()\n"
            "\n"
            "    # TODO: @app.post('/echo', response_model=ChatResponse)\n"
            "    #       def echo(req: ChatRequest):\n"
            "    #           return ChatResponse(reply=req.message, model='echo')\n"
            "\n"
            "    return app"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: models validate a good dict (Pydantic v2)\n"
            "    try:\n"
            "        req = ChatRequest.model_validate({'message': 'hi', 'temperature': 0.5})\n"
            "        assert req.message == 'hi' and req.temperature == 0.5\n"
            "        assert ChatRequest.model_validate({'message': 'x'}).temperature == 0.7, 'temperature default should be 0.7'\n"
            "        passed += 1; print('✅ Check 1: ChatRequest validates + defaults temperature')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: POST /echo with a valid body returns 200 and echoes the message\n"
            "    try:\n"
            "        client = TestClient(create_echo_app())\n"
            "        r = client.post('/echo', json={'message': 'hello api'})\n"
            "        assert r.status_code == 200, f'expected 200, got {r.status_code}'\n"
            "        assert r.json()['reply'] == 'hello api', f\"bad echo: {r.json()}\"\n"
            "        passed += 1; print('✅ Check 2: POST /echo echoes the message (200)')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 2: {e}')\n"
            "\n"
            "    # Check 3: missing required field -> automatic 422\n"
            "    try:\n"
            "        client = TestClient(create_echo_app())\n"
            "        r = client.post('/echo', json={'temperature': 0.5})\n"
            "        assert r.status_code == 422, f'expected 422 on missing message, got {r.status_code}'\n"
            "        passed += 1; print('✅ Check 3: missing message -> 422')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 3: {e}')\n"
            "\n"
            "    # Check 4: empty message violates min_length -> 422\n"
            "    try:\n"
            "        client = TestClient(create_echo_app())\n"
            "        r = client.post('/echo', json={'message': ''})\n"
            "        assert r.status_code == 422, f'expected 422 on empty message, got {r.status_code}'\n"
            "        passed += 1; print('✅ Check 4: empty message -> 422 (min_length)')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 4: {e}')\n"
            "\n"
            "    # Check 5: temperature out of range -> 422\n"
            "    try:\n"
            "        client = TestClient(create_echo_app())\n"
            "        r = client.post('/echo', json={'message': 'hi', 'temperature': 2.0})\n"
            "        assert r.status_code == 422, f'expected 422 on temperature=2.0, got {r.status_code}'\n"
            "        passed += 1; print('✅ Check 5: temperature out of [0,1] -> 422')\n"
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
            + ECHO_IMPL + "\n"
            "```\n\n"
            "**Why this works:** Declaring `def echo(req: ChatRequest)` tells FastAPI "
            "the JSON body must match `ChatRequest`. `Field(min_length=1)` and "
            "`Field(ge=0.0, le=1.0)` are Pydantic v2 constraints — violate any of them "
            "and FastAPI returns a 422 with a precise error list, before `echo` ever "
            "runs. `response_model=ChatResponse` validates and shapes the output too. "
            "The endpoint is deterministic (no model call), so it's the perfect place "
            "to prove the request/response contract.\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 03 — the AI endpoint
# ---------------------------------------------------------------------------

def ex03():
    global _cid; _cid = 200
    return [
        md(
            "# Day 052 — Exercise 3: The AI Endpoint\n\n"
            "**What you'll build:** `create_chat_app(model)` — a `POST /chat` endpoint "
            "that sends the request message to Ollama and returns the reply as a "
            "`ChatResponse`. Model errors become an `HTTPException(503)`.\n\n"
            "**Why it matters:** This is the endpoint that makes it an *AI* API. It "
            "wires the validated request into `ollama.chat` and returns a typed "
            "response. The key discipline is error handling: a web handler must never "
            "leak a raw exception — you convert a model failure into a clean 503 so "
            "clients get a meaningful HTTP status, not a 500 stack trace."
        ),
        md("## Provided: Setup + Models (from Exercise 2)"),
        code(_BEFORE_EX03),
        md("## Your Implementation"),
        code(
            "def create_chat_app(model: str = 'llama3.2') -> FastAPI:\n"
            '    """\n'
            "    POST /chat — send req.message to Ollama, return a ChatResponse.\n"
            "    On any model error, raise HTTPException(status_code=503, ...).\n"
            '    """\n'
            "    app = FastAPI()\n"
            "\n"
            "    @app.post('/chat', response_model=ChatResponse)\n"
            "    def chat(req: ChatRequest):\n"
            "        # TODO: try:\n"
            "        #     resp = ollama.chat(model=model,\n"
            "        #         messages=[{'role': 'user', 'content': req.message}],\n"
            "        #         options={'temperature': req.temperature})\n"
            "        #     return ChatResponse(reply=resp['message']['content'].strip(), model=model)\n"
            "        # except Exception as e:\n"
            "        #     raise HTTPException(status_code=503, detail=f'Model unavailable: {e}')\n"
            "        pass\n"
            "\n"
            "    return app"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: create_chat_app returns a FastAPI app\n"
            "    try:\n"
            "        app = create_chat_app()\n"
            "        assert isinstance(app, FastAPI), f'expected FastAPI, got {type(app).__name__}'\n"
            "        client = TestClient(app)\n"
            "        passed += 1; print('✅ Check 1: create_chat_app returns a FastAPI app')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: POST /chat returns 200 with a non-empty reply (Ollama)\n"
            "    try:\n"
            "        r = client.post('/chat', json={'message': 'Reply with exactly: pong'})\n"
            "        assert r.status_code == 200, f'expected 200, got {r.status_code} ({r.text[:120]})'\n"
            "        reply = r.json()['reply']\n"
            "        assert isinstance(reply, str) and len(reply) > 0, f'empty reply: {r.json()}'\n"
            "        passed += 1; print(f'✅ Check 2: POST /chat -> 200 with reply ({len(reply)} chars)')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 2: {e}')\n"
            "\n"
            "    # Check 3: response reports the model name\n"
            "    try:\n"
            "        r = client.post('/chat', json={'message': 'hi'})\n"
            "        assert r.json().get('model') == 'llama3.2', f\"expected model llama3.2, got {r.json()}\"\n"
            "        passed += 1; print('✅ Check 3: response reports model == llama3.2')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 3: {e}')\n"
            "\n"
            "    # Check 4: invalid body (missing message) -> 422\n"
            "    try:\n"
            "        r = client.post('/chat', json={'temperature': 0.5})\n"
            "        assert r.status_code == 422, f'expected 422, got {r.status_code}'\n"
            "        passed += 1; print('✅ Check 4: missing message -> 422')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 4: {e}')\n"
            "\n"
            "    # Check 5: a bad model name is turned into a 503, not a crash\n"
            "    try:\n"
            "        bad = TestClient(create_chat_app(model='no-such-model-xyz'))\n"
            "        r = bad.post('/chat', json={'message': 'hi'})\n"
            "        assert r.status_code == 503, f'expected 503 on bad model, got {r.status_code}'\n"
            "        passed += 1; print('✅ Check 5: model error -> HTTPException(503)')\n"
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
            + CHAT_IMPL + "\n"
            "```\n\n"
            "**Why this works:** By the time `chat` runs, `req` is already a validated "
            "`ChatRequest` — no manual parsing. The `ollama.chat` call is wrapped so "
            "any failure (Ollama down, unknown model) is re-raised as "
            "`HTTPException(503)`, which FastAPI turns into a clean JSON error response "
            "with that status code. Raising `HTTPException` is how you return non-200 "
            "statuses from a handler — the equivalent of the try/except fallback you "
            "wrote for the Streamlit app, but expressed in HTTP terms.\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 04 — path & query params + error handling
# ---------------------------------------------------------------------------

def ex04():
    global _cid; _cid = 300
    return [
        md(
            "# Day 052 — Exercise 4: Path & Query Parameters\n\n"
            "**What you'll build:** `create_template_app()` — a prompt-template service. "
            "`GET /templates` lists names; `GET /render/{name}?topic=...` renders a "
            "prompt from a **path** parameter and a **query** parameter; an unknown "
            "name raises `HTTPException(404)`.\n\n"
            "**Why it matters:** Not every input comes in a JSON body. Path parameters "
            "(`/render/{name}`) identify a resource; query parameters (`?topic=...`) "
            "tune the request and can have defaults. FastAPI reads both straight from "
            "the function signature. And returning the right status code — 404 for "
            "'not found' — is what makes an API predictable to its callers."
        ),
        md("## Provided: Setup + Models"),
        code(_BEFORE_EX04),
        md("## Your Implementation"),
        code(
            "PROMPT_TEMPLATES = {\n"
            "    'summary':  'Summarize the following topic in two sentences: {topic}',\n"
            "    'explain':  'Explain {topic} to a complete beginner.',\n"
            "    'critique': 'List three criticisms of {topic}.',\n"
            "}\n"
            "\n"
            "\n"
            "def create_template_app() -> FastAPI:\n"
            '    """\n'
            "    GET /templates              -> {'templates': [names]}\n"
            "    GET /render/{name}?topic=.. -> {'name': name, 'prompt': rendered}\n"
            "    Unknown name                -> HTTPException(404)\n"
            '    """\n'
            "    app = FastAPI()\n"
            "\n"
            "    @app.get('/templates')\n"
            "    def list_templates():\n"
            "        # TODO: return {'templates': list(PROMPT_TEMPLATES.keys())}\n"
            "        pass\n"
            "\n"
            "    # TODO: define GET /render/{name} with a query param topic (default 'AI'):\n"
            "    # @app.get('/render/{name}')\n"
            "    # def render(name: str, topic: str = 'AI'):\n"
            "    #     if name not in PROMPT_TEMPLATES:\n"
            "    #         raise HTTPException(status_code=404, detail=f'template {name!r} not found')\n"
            "    #     return {'name': name, 'prompt': PROMPT_TEMPLATES[name].format(topic=topic)}\n"
            "\n"
            "    return app"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    try:\n"
            "        client = TestClient(create_template_app())\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 1: GET /templates lists the template names\n"
            "    try:\n"
            "        r = client.get('/templates')\n"
            "        assert r.status_code == 200, f'expected 200, got {r.status_code}'\n"
            "        assert 'summary' in r.json()['templates'], f\"missing 'summary': {r.json()}\"\n"
            "        passed += 1; print('✅ Check 1: GET /templates lists names')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 1: {e}')\n"
            "\n"
            "    # Check 2: path param + query param render a prompt with the topic\n"
            "    try:\n"
            "        r = client.get('/render/summary', params={'topic': 'Python'})\n"
            "        assert r.status_code == 200, f'expected 200, got {r.status_code}'\n"
            "        assert 'Python' in r.json()['prompt'], f\"topic not rendered: {r.json()}\"\n"
            "        passed += 1; print('✅ Check 2: /render/{name}?topic= renders the prompt')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 2: {e}')\n"
            "\n"
            "    # Check 3: query param has a default of 'AI'\n"
            "    try:\n"
            "        r = client.get('/render/explain')\n"
            "        assert r.status_code == 200\n"
            "        assert 'AI' in r.json()['prompt'], f\"default topic not applied: {r.json()}\"\n"
            "        passed += 1; print('✅ Check 3: topic defaults to AI')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 3: {e}')\n"
            "\n"
            "    # Check 4: unknown template name -> 404\n"
            "    try:\n"
            "        r = client.get('/render/does-not-exist')\n"
            "        assert r.status_code == 404, f'expected 404, got {r.status_code}'\n"
            "        passed += 1; print('✅ Check 4: unknown template -> 404')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 4: {e}')\n"
            "\n"
            "    # Check 5: the path param is reflected back in the response\n"
            "    try:\n"
            "        r = client.get('/render/critique')\n"
            "        assert r.json().get('name') == 'critique', f\"name not reflected: {r.json()}\"\n"
            "        passed += 1; print('✅ Check 5: path param reflected in response')\n"
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
            + TEMPLATE_APP_IMPL + "\n"
            "```\n\n"
            "**Why this works:** In `/render/{name}`, `name` appears in the path, so "
            "FastAPI binds it as a path parameter. `topic: str = 'AI'` is *not* in the "
            "path, so FastAPI treats it as a query parameter with a default — "
            "`/render/summary` and `/render/summary?topic=Python` both work. When the "
            "name isn't a known template, `raise HTTPException(404)` returns the "
            "correct 'not found' status instead of a generic error. Clean status codes "
            "are the difference between an API and a black box.\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 05 — assemble the full API
# ---------------------------------------------------------------------------

def ex05():
    global _cid; _cid = 400
    return [
        md(
            "# Day 052 — Exercise 5: Assemble the Full AI API\n\n"
            "**What you'll build:** `build_api(model)` — one FastAPI app that combines "
            "everything: `GET /health`, `GET /templates`, `POST /chat`, and "
            "`POST /render/{name}` (a templated chat call). This is the deliverable "
            "you'll ship as `main.py`.\n\n"
            "**Why it matters:** A real service is many routes on one app, sharing "
            "models and helpers. `build_api` is the factory that assembles them. The "
            "provided `run_model` helper keeps each route thin — the same "
            "thin-handler-over-logic pattern you used for the Streamlit `ChatApp`, now "
            "on the server side."
        ),
        md("## Provided: Setup + Models + Templates + run_model helper"),
        code(_BEFORE_EX05),
        md("## Your Implementation"),
        code(
            "def build_api(model: str = 'llama3.2') -> FastAPI:\n"
            '    """\n'
            "    Assemble the full AI API:\n"
            "      GET  /health            -> HealthResponse(status='ok', model=model)\n"
            "      GET  /templates         -> {'templates': [names]}\n"
            "      POST /chat              -> ChatResponse from run_model(model, req.message, ...)\n"
            "      POST /render/{name}     -> ChatResponse from the named template (404 if unknown)\n"
            '    """\n'
            "    app = FastAPI(title='AI API', version='1.0.0')\n"
            "\n"
            "    # TODO: @app.get('/health', response_model=HealthResponse)\n"
            "    #       def health(): return HealthResponse(status='ok', model=model)\n"
            "\n"
            "    # TODO: @app.get('/templates')\n"
            "    #       def list_templates(): return {'templates': list(PROMPT_TEMPLATES.keys())}\n"
            "\n"
            "    # TODO: @app.post('/chat', response_model=ChatResponse)\n"
            "    #       def chat(req: ChatRequest):\n"
            "    #           try: return ChatResponse(reply=run_model(model, req.message, req.temperature), model=model)\n"
            "    #           except Exception as e: raise HTTPException(status_code=503, detail=f'Model unavailable: {e}')\n"
            "\n"
            "    # TODO: @app.post('/render/{name}', response_model=ChatResponse)\n"
            "    #       def render_chat(name: str, req: ChatRequest):\n"
            "    #           if name not in PROMPT_TEMPLATES: raise HTTPException(status_code=404, detail=...)\n"
            "    #           prompt = PROMPT_TEMPLATES[name].format(topic=req.message)\n"
            "    #           try: return ChatResponse(reply=run_model(model, prompt, req.temperature), model=model)\n"
            "    #           except Exception as e: raise HTTPException(status_code=503, detail=f'Model unavailable: {e}')\n"
            "\n"
            "    return app"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: build_api returns an app exposing all four routes\n"
            "    try:\n"
            "        app = build_api()\n"
            "        assert isinstance(app, FastAPI)\n"
            "        paths = {r.path for r in app.routes}\n"
            "        for p in ('/health', '/templates', '/chat', '/render/{name}'):\n"
            "            assert p in paths, f'missing route: {p} (have {sorted(paths)})'\n"
            "        client = TestClient(app)\n"
            "        passed += 1; print('✅ Check 1: build_api exposes health/templates/chat/render')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: GET /health -> 200 with status + model\n"
            "    try:\n"
            "        b = client.get('/health').json()\n"
            "        assert b['status'] == 'ok' and b['model'] == 'llama3.2', f'bad health: {b}'\n"
            "        passed += 1; print('✅ Check 2: /health reports ok + model')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 2: {e}')\n"
            "\n"
            "    # Check 3: GET /templates lists the names\n"
            "    try:\n"
            "        assert 'summary' in client.get('/templates').json()['templates']\n"
            "        passed += 1; print('✅ Check 3: /templates lists names')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 3: {e}')\n"
            "\n"
            "    # Check 4: POST /chat -> 200 with a real reply (Ollama)\n"
            "    try:\n"
            "        r = client.post('/chat', json={'message': 'Reply with exactly: pong'})\n"
            "        assert r.status_code == 200, f'expected 200, got {r.status_code} ({r.text[:120]})'\n"
            "        assert len(r.json()['reply']) > 0\n"
            "        passed += 1; print('✅ Check 4: POST /chat returns a reply')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 4: {e}')\n"
            "\n"
            "    # Check 5: POST /render/{name} — valid renders (200), unknown -> 404\n"
            "    try:\n"
            "        ok = client.post('/render/summary', json={'message': 'Python'})\n"
            "        assert ok.status_code == 200, f'expected 200, got {ok.status_code} ({ok.text[:120]})'\n"
            "        assert len(ok.json()['reply']) > 0\n"
            "        missing = client.post('/render/nope', json={'message': 'x'})\n"
            "        assert missing.status_code == 404, f'expected 404, got {missing.status_code}'\n"
            "        passed += 1; print('✅ Check 5: /render works (200) and 404s on unknown template')\n"
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
            + BUILD_API_IMPL + "\n"
            "```\n\n"
            "**Why this works:** `build_api` registers four routes on one app, all "
            "sharing the `ChatRequest`/`ChatResponse` contract and the `run_model` "
            "helper. `/render/{name}` combines everything from the day: a path "
            "parameter, a request body, a 404 for unknown templates, a model call, and "
            "a 503 on failure. Returning the app from a factory (rather than a global) "
            "means the tests can build fresh instances — and `main.py` just calls "
            "`app = build_api()` for uvicorn to serve.\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Project notebook (student template — not executed by the gate)
# ---------------------------------------------------------------------------

def project_nb():
    global _cid; _cid = 500
    all_code = _BEFORE_EX05 + "\n\n\n" + BUILD_API_IMPL
    return [
        md(
            "# Day 052 Project: Ship an AI API\n\n"
            "## What You're Building\n\n"
            "A complete, runnable **FastAPI service** backed by local Ollama. You run "
            "one command — `uvicorn main:app --reload` — and get a live HTTP API with "
            "`/health`, `/templates`, `/chat`, and `/render/{name}`, plus automatic "
            "interactive docs at `/docs`. That `main.py` is the deliverable.\n\n"
            "## Project Requirements\n\n"
            "1. Use the provided `build_api` factory (built across Exercises 1–5).\n"
            "2. Build the app and exercise every route with `TestClient` to prove it "
            "works in-process.\n"
            "3. Call `write_api_app('main.py')` to generate the real service file.\n"
            "4. Run `_run_project_checks()` to verify the file is well-formed.\n"
            "5. Then, in a terminal: `uvicorn main:app --reload` and open "
            "`http://localhost:8000/docs`.\n\n"
            "## Bonus Challenges\n\n"
            "- Add a `GET /models` route that returns `ollama.list()` model names.\n"
            "- Add a `max_tokens` field to `ChatRequest` and pass it through "
            "`options={'num_predict': ...}`.\n"
            "- Add CORS with `from fastapi.middleware.cors import CORSMiddleware` so a "
            "browser front-end (tomorrow, Day 53) can call it."
        ),
        md("## Provided: All Logic (Exercises 1–5)"),
        code(all_code),
        md("## Provided: main.py Builder"),
        code(WRITE_MAIN_CELL),
        md("## Your Pipeline"),
        code(
            "# TODO: app = build_api()\n"
            "# TODO: client = TestClient(app)\n"
            "# TODO: print('health :', client.get('/health').json())\n"
            "# TODO: print('chat   :', client.post('/chat', json={'message': 'Say hello in 3 words.'}).json())\n"
            "# TODO: print('render :', client.post('/render/summary', json={'message': 'FastAPI'}).json())\n"
            "#\n"
            "# TODO: path = write_api_app('main.py')\n"
            "# TODO: print('Wrote', path)\n"
            "# TODO: print('Run it with:  uvicorn main:app --reload')"
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
            "    # Check 1: app built and served in-process\n"
            "    try:\n"
            "        assert 'app' in globals() and isinstance(app, FastAPI), 'create app = build_api()'\n"
            "        client = TestClient(app)\n"
            "        assert client.get('/health').status_code == 200\n"
            "        passed += 1; print('✅ Check 1: build_api() app responds to /health')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: main.py written\n"
            "    try:\n"
            "        assert os.path.exists('main.py'), 'main.py not found — call write_api_app()'\n"
            "        passed += 1; print('✅ Check 2: main.py exists')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 2: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    src = open('main.py', encoding='utf-8').read()\n"
            "\n"
            "    # Check 3: main.py imports FastAPI and defines build_api\n"
            "    try:\n"
            "        assert 'from fastapi import FastAPI' in src, 'main.py must import FastAPI'\n"
            "        assert 'def build_api' in src, 'main.py must define build_api'\n"
            "        assert 'app = build_api()' in src, 'main.py must expose module-level app'\n"
            "        passed += 1; print('✅ Check 3: main.py has FastAPI + build_api + app')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 3: {e}')\n"
            "\n"
            "    # Check 4: main.py has a uvicorn entry point\n"
            "    try:\n"
            "        assert 'uvicorn' in src, 'main.py should include a uvicorn run guard'\n"
            "        assert \"__main__\" in src, 'main.py should guard the run under __main__'\n"
            "        passed += 1; print('✅ Check 4: main.py has a uvicorn entry point')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 4: {e}')\n"
            "\n"
            "    # Check 5: main.py is valid Python (compiles)\n"
            "    try:\n"
            "        compile(src, 'main.py', 'exec')\n"
            "        passed += 1; print('✅ Check 5: main.py compiles as valid Python')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\U0001f389 Project complete! Run: uvicorn main:app --reload')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "\n"
            "_run_project_checks()"
        ),
    ]


# ---------------------------------------------------------------------------
# Solution notebook (runs clean under nbconvert — no uvicorn, TestClient only)
# ---------------------------------------------------------------------------

def solution_nb():
    global _cid; _cid = 600
    all_code = _BEFORE_EX05 + "\n\n\n" + BUILD_API_IMPL
    return [
        md(
            "# Day 052 Solution — AI API with FastAPI\n\n"
            "Section 4, Day 2. Builds the full AI API with `build_api`, exercises every "
            "route with `TestClient` (in-process — no server), then generates a real, "
            "runnable `main.py`. This notebook never starts uvicorn; it verifies the "
            "app and the generated file. Launch the service with `uvicorn main:app`."
        ),
        code(all_code),
        md("## Step 1 — Build the App and Test It In-Process"),
        code(
            "app = build_api()\n"
            "client = TestClient(app)\n"
            "\n"
            "print('GET /health   ->', client.get('/health').json())\n"
            "print('GET /templates->', client.get('/templates').json())\n"
            "assert client.get('/health').status_code == 200"
        ),
        md("## Step 2 — Call the AI Endpoints"),
        code(
            "r = client.post('/chat', json={'message': 'Say hello in exactly three words.'})\n"
            "print('POST /chat  ->', r.status_code, r.json())\n"
            "assert r.status_code == 200 and len(r.json()['reply']) > 0\n"
            "\n"
            "r = client.post('/render/summary', json={'message': 'FastAPI'})\n"
            "print('POST /render/summary ->', r.status_code)\n"
            "print('  reply:', r.json()['reply'][:200])\n"
            "assert r.status_code == 200 and len(r.json()['reply']) > 0"
        ),
        md("## Step 3 — Error Paths: 422 and 404"),
        code(
            "bad = client.post('/chat', json={'temperature': 0.5})  # missing message\n"
            "print('missing message ->', bad.status_code)\n"
            "assert bad.status_code == 422\n"
            "\n"
            "missing = client.post('/render/does-not-exist', json={'message': 'x'})\n"
            "print('unknown template ->', missing.status_code)\n"
            "assert missing.status_code == 404\n"
            "print('Validation (422) and not-found (404) behave correctly.')"
        ),
        md("## Step 4 — Generate the Runnable main.py"),
        code(WRITE_MAIN_CELL),
        code(
            "path = write_api_app('main.py')\n"
            "src = open(path, encoding='utf-8').read()\n"
            "print(f'Wrote {path} ({len(src)} chars)')\n"
            "\n"
            "assert 'from fastapi import FastAPI' in src\n"
            "assert 'def build_api' in src\n"
            "assert 'app = build_api()' in src\n"
            "assert 'uvicorn' in src\n"
            "compile(src, 'main.py', 'exec')  # must be valid Python\n"
            "print('main.py verified: imports FastAPI, defines build_api, exposes app, compiles.')"
        ),
        md("## Step 5 — Preview the Entry Point"),
        code(
            "tail = src[src.index('app = build_api()'):]\n"
            "print(tail)\n"
            "\n"
            "print('\\nTo launch the API, run in a terminal:')\n"
            "print('    uvicorn main:app --reload')\n"
            "print('Then open http://localhost:8000/docs for interactive docs.')\n"
            "print('\\nDay 52 — AI API complete! \U0001f389')"
        ),
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Generating Day 052 notebooks...")
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
