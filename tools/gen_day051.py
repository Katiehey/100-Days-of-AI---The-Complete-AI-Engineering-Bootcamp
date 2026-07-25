#!/usr/bin/env python3
"""Generate all Day 051 notebooks: exercises 1-5, project, solution.

Day 051 — Web Apps with Streamlit. Deliverable: interactive AI chat app UI.

Section 4 strategy: the gate runs Jupyter notebooks, but the deliverable is a
Streamlit app. So the EXERCISES test the pure-Python logic functions the app
calls (session state, input validation, model wiring, display helpers), while
the PROJECT/SOLUTION generate a real, runnable ``app.py`` via inspect.getsource.
No ``import streamlit`` runs inside the gated cells (a Streamlit script only
runs under ``streamlit run``); the logic layer is plain Python + Ollama.
"""
import json
from pathlib import Path

ROOT    = Path(__file__).resolve().parent.parent
DAY_DIR = ROOT / "04_real_apps" / "day_051"

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
# Shared setup
# ---------------------------------------------------------------------------

SETUP = '''import warnings
warnings.filterwarnings('ignore')
import ollama'''


# ---------------------------------------------------------------------------
# Implementations (each is the block revealed in <details> AND injected by gate)
# ---------------------------------------------------------------------------

SESSION_IMPL = '''def init_session(state: dict) -> dict:
    """
    Idempotently initialise a Streamlit-style session_state dict.

    Streamlit reruns the WHOLE script top-to-bottom on every interaction, so
    initialisation must never overwrite existing data. Only set a key if absent.

    Ensures keys:
        'messages'  -> list of {'role', 'content'} dicts (starts empty)
        'settings'  -> {'model', 'temperature', 'system_prompt'}
    Returns the same dict, mutated in place.
    """
    if 'messages' not in state:
        state['messages'] = []
    if 'settings' not in state:
        state['settings'] = {
            'model': 'llama3.2',
            'temperature': 0.7,
            'system_prompt': 'You are a helpful assistant.',
        }
    return state


def add_message(state: dict, role: str, content: str) -> dict:
    """Append a {'role', 'content'} message to state['messages']; return it."""
    if role not in ('user', 'assistant', 'system'):
        raise ValueError(f'invalid role: {role!r}')
    msg = {'role': role, 'content': content}
    state['messages'].append(msg)
    return msg


def reset_messages(state: dict) -> None:
    """Clear the conversation but keep settings (a 'Clear chat' button)."""
    state['messages'] = []'''


INPUT_IMPL = '''def validate_user_input(text: str, max_chars: int = 2000) -> tuple[bool, str]:
    """
    Validate raw text from an st.chat_input / st.text_area widget before it is
    sent to the model.

    Returns (is_valid, result):
      - empty/whitespace : (False, 'Please enter a message.')
      - too long         : (False, 'Message too long (max N chars).')
      - valid            : (True, cleaned_text)   # stripped
    """
    cleaned = text.strip()
    if not cleaned:
        return (False, 'Please enter a message.')
    if len(cleaned) > max_chars:
        return (False, f'Message too long (max {max_chars} chars).')
    return (True, cleaned)


def clamp(value: float, lo: float, hi: float) -> float:
    """Clamp a widget value into [lo, hi]. st.slider bounds live input, but a
    value restored from session_state or a URL param may be out of range."""
    return max(lo, min(hi, value))


def build_settings(model: str, temperature: float, system_prompt: str) -> dict:
    """
    Assemble a validated settings dict from sidebar widget values.
    - temperature clamped to [0.0, 1.0]
    - system_prompt stripped; empty falls back to a default
    """
    sp = system_prompt.strip() or 'You are a helpful assistant.'
    return {
        'model': model,
        'temperature': float(clamp(temperature, 0.0, 1.0)),
        'system_prompt': sp,
    }'''


CHAT_IMPL = '''def build_messages(state: dict, user_text: str) -> list:
    """
    Build the messages list for ollama.chat:
        [system_prompt] + prior conversation + new user turn.
    Reads the system prompt from state['settings']. Does NOT mutate state.
    """
    settings = state.get('settings', {})
    system_prompt = settings.get('system_prompt', 'You are a helpful assistant.')
    messages = [{'role': 'system', 'content': system_prompt}]
    messages.extend(state.get('messages', []))
    messages.append({'role': 'user', 'content': user_text})
    return messages


def chat_with_history(state: dict, user_text: str, model: str = 'llama3.2') -> str:
    """
    Send the full conversation to Ollama and return the assistant's reply.
    Reads temperature from state['settings']. Returns a fallback string if
    Ollama is unavailable so the app never crashes on a model error.
    """
    settings = state.get('settings', {})
    temperature = settings.get('temperature', 0.7)
    messages = build_messages(state, user_text)
    try:
        response = ollama.chat(
            model=model,
            messages=messages,
            options={'temperature': temperature},
        )
        return response['message']['content'].strip()
    except Exception as e:
        return f'[Model unavailable: {e}]' '''


DISPLAY_IMPL = '''def format_transcript(messages: list) -> str:
    """
    Render the conversation as a plain-text transcript for st.download_button.
    One block per turn as 'ROLE: content'. System messages are skipped.
    """
    lines = []
    for m in messages:
        role = m.get('role', '')
        if role == 'system':
            continue
        lines.append(f"{role.upper()}: {m.get('content', '')}")
    return '\\n\\n'.join(lines)


def chat_stats(messages: list) -> dict:
    """
    Compute display metrics for st.metric widgets. System messages excluded.
    Returns: {'total', 'user', 'assistant', 'chars'}.
    """
    non_system = [m for m in messages if m.get('role') != 'system']
    user = sum(1 for m in non_system if m.get('role') == 'user')
    assistant = sum(1 for m in non_system if m.get('role') == 'assistant')
    chars = sum(len(m.get('content', '')) for m in non_system)
    return {
        'total': len(non_system),
        'user': user,
        'assistant': assistant,
        'chars': chars,
    }'''


CHATAPP_IMPL = '''class ChatApp:
    """
    The logic core of the Streamlit chat app. One instance is stored in
    st.session_state and reused across reruns. The Streamlit layer only calls
    these methods and renders their return values — no business logic in the UI.

    Usage (inside app.py):
        if 'app' not in st.session_state:
            st.session_state.app = ChatApp()
        app = st.session_state.app
        reply = app.send(prompt)          # on chat_input submit
        st.metric('Messages', app.stats()['total'])
    """

    def __init__(self, model: str = 'llama3.2',
                 system_prompt: str = 'You are a helpful assistant.'):
        self.state = {}
        init_session(self.state)
        self.state['settings']['model'] = model
        self.state['settings']['system_prompt'] = system_prompt
        self.model = model

    def send(self, user_text: str) -> str:
        """
        Validate -> append user turn -> call model -> append assistant turn.
        Returns the assistant reply, or a validation error string (in which
        case NOTHING is appended to the conversation).
        """
        ok, result = validate_user_input(user_text)
        if not ok:
            return result
        add_message(self.state, 'user', result)
        reply = chat_with_history(self.state, result, self.model)
        add_message(self.state, 'assistant', reply)
        return reply

    def stats(self) -> dict:
        return chat_stats(self.state['messages'])

    def transcript(self) -> str:
        return format_transcript(self.state['messages'])

    def reset(self) -> None:
        reset_messages(self.state)'''


# Cumulative provided stacks
_BEFORE_EX02 = "\n\n\n".join([SETUP, SESSION_IMPL])
_BEFORE_EX03 = "\n\n\n".join([SETUP, SESSION_IMPL, INPUT_IMPL])
_BEFORE_EX04 = "\n\n\n".join([SETUP, SESSION_IMPL, INPUT_IMPL, CHAT_IMPL])
ALL_LOGIC    = "\n\n\n".join([SESSION_IMPL, INPUT_IMPL, CHAT_IMPL, DISPLAY_IMPL])
_BEFORE_EX05 = SETUP + "\n\n\n" + ALL_LOGIC


# ---------------------------------------------------------------------------
# Streamlit UI code (embedded into the generated app.py; not run by the gate)
# ---------------------------------------------------------------------------

UI_CODE = '''# ---- Streamlit UI (runs only under: streamlit run app.py) ----
st.set_page_config(page_title="Local AI Chat", page_icon="\U0001f4ac")
st.title("\U0001f4ac Local AI Chat")

# One ChatApp instance per browser session, persisted across reruns.
if "app" not in st.session_state:
    st.session_state.app = ChatApp()
app = st.session_state.app

# Sidebar: settings + live stats + controls.
with st.sidebar:
    st.header("Settings")
    temp = st.slider("Temperature", 0.0, 1.0, 0.7, 0.1)
    sysp = st.text_area("System prompt", app.state["settings"]["system_prompt"])
    app.state["settings"] = build_settings(app.model, temp, sysp)

    st.header("Stats")
    s = app.stats()
    c1, c2 = st.columns(2)
    c1.metric("Messages", s["total"])
    c2.metric("Characters", s["chars"])

    if st.button("Clear chat"):
        app.reset()
        st.rerun()

    st.download_button("Download transcript", app.transcript(), "chat.txt")

# Replay the whole conversation from session state.
for m in app.state["messages"]:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# Handle a new user turn.
prompt = st.chat_input("Type a message...")
if prompt:
    with st.spinner("Thinking..."):
        app.send(prompt)          # appends user + assistant to session state
    st.rerun()                    # rerun so the replay loop renders them
'''


# ---------------------------------------------------------------------------
# Exercise 01 — session state
# ---------------------------------------------------------------------------

def ex01():
    global _cid; _cid = 0
    return [
        md(
            "# Day 051 — Exercise 1: Session State\n\n"
            "**What you'll build:** `init_session(state)`, `add_message(state, role, "
            "content)`, and `reset_messages(state)` — the functions that manage a "
            "Streamlit-style `st.session_state` dict for a chat app.\n\n"
            "**Why it matters:** Streamlit reruns your *entire script* top-to-bottom "
            "on every click, keystroke, or slider drag. The only thing that survives "
            "a rerun is `st.session_state` — a plain dict. So your initialisation must "
            "be **idempotent**: set a key only if it's missing, or every rerun would "
            "wipe the conversation. That single rule is the heart of Streamlit state."
        ),
        md("## Provided: Setup"),
        code(SETUP),
        md("## Your Implementation"),
        code(
            "def init_session(state: dict) -> dict:\n"
            '    """\n'
            "    Idempotently initialise a session_state dict. Only set a key if ABSENT.\n"
            "    Ensure: 'messages' (empty list) and 'settings'\n"
            "    (model='llama3.2', temperature=0.7, system_prompt='You are a helpful assistant.').\n"
            '    """\n'
            "    # TODO: if 'messages' not in state: state['messages'] = []\n"
            "    # TODO: if 'settings' not in state: state['settings'] = {..model, temperature, system_prompt..}\n"
            "    return state\n"
            "\n"
            "\n"
            "def add_message(state: dict, role: str, content: str) -> dict:\n"
            '    """Append {\'role\', \'content\'} to state[\'messages\']; reject bad roles; return it."""\n'
            "    # TODO: if role not in ('user', 'assistant', 'system'): raise ValueError(...)\n"
            "    # TODO: msg = {'role': role, 'content': content}\n"
            "    # TODO: state['messages'].append(msg); return msg\n"
            "    pass\n"
            "\n"
            "\n"
            "def reset_messages(state: dict) -> None:\n"
            '    """Clear state[\'messages\'] but keep state[\'settings\']."""\n'
            "    # TODO: state['messages'] = []\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: init_session returns a dict with 'messages' and 'settings'\n"
            "    try:\n"
            "        st_state = {}\n"
            "        out = init_session(st_state)\n"
            "        assert isinstance(out, dict), f'expected dict, got {type(out).__name__}'\n"
            "        assert 'messages' in out and 'settings' in out, 'missing messages/settings'\n"
            "        assert out['messages'] == [], 'messages should start empty'\n"
            "        passed += 1; print('✅ Check 1: init_session sets messages + settings')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: init_session is IDEMPOTENT (does not wipe existing data)\n"
            "    try:\n"
            "        st_state = {}\n"
            "        init_session(st_state)\n"
            "        st_state['messages'].append({'role': 'user', 'content': 'hi'})\n"
            "        init_session(st_state)  # rerun simulation\n"
            "        assert len(st_state['messages']) == 1, 'idempotent init must NOT clear messages'\n"
            "        passed += 1; print('✅ Check 2: init_session is idempotent across reruns')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 2: {e}')\n"
            "\n"
            "    # Check 3: add_message appends and returns the message\n"
            "    try:\n"
            "        st_state = init_session({})\n"
            "        msg = add_message(st_state, 'user', 'hello')\n"
            "        assert msg == {'role': 'user', 'content': 'hello'}, f'bad message: {msg}'\n"
            "        assert st_state['messages'][-1] == msg, 'message not appended'\n"
            "        passed += 1; print('✅ Check 3: add_message appends + returns the message')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 3: {e}')\n"
            "\n"
            "    # Check 4: add_message rejects an invalid role\n"
            "    try:\n"
            "        st_state = init_session({})\n"
            "        raised = False\n"
            "        try:\n"
            "            add_message(st_state, 'robot', 'nope')\n"
            "        except ValueError:\n"
            "            raised = True\n"
            "        assert raised, 'expected ValueError on invalid role'\n"
            "        passed += 1; print('✅ Check 4: add_message rejects invalid roles')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 4: {e}')\n"
            "\n"
            "    # Check 5: reset_messages clears messages but keeps settings\n"
            "    try:\n"
            "        st_state = init_session({})\n"
            "        add_message(st_state, 'user', 'a')\n"
            "        add_message(st_state, 'assistant', 'b')\n"
            "        reset_messages(st_state)\n"
            "        assert st_state['messages'] == [], 'messages not cleared'\n"
            "        assert 'settings' in st_state, 'settings should survive a reset'\n"
            "        passed += 1; print('✅ Check 5: reset_messages clears messages, keeps settings')\n"
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
            + SESSION_IMPL + "\n"
            "```\n\n"
            "**Why this works:** The `if key not in state` guard is what makes init "
            "safe to call on every rerun — Streamlit runs the whole script each time, "
            "so a naive `state['messages'] = []` would erase the chat on every "
            "interaction. `add_message` validates the role up front (fail fast) so bad "
            "data never reaches the model. `reset_messages` rebinds only `messages`, "
            "leaving `settings` intact — exactly what a 'Clear chat' button should do.\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 02 — widget input handling
# ---------------------------------------------------------------------------

def ex02():
    global _cid; _cid = 100
    return [
        md(
            "# Day 051 — Exercise 2: Widget Input Handling\n\n"
            "**What you'll build:** `validate_user_input(text, max_chars)`, "
            "`clamp(value, lo, hi)`, and `build_settings(model, temperature, "
            "system_prompt)` — the functions that turn raw widget values into safe, "
            "validated inputs.\n\n"
            "**Why it matters:** Widgets return whatever the user typed or dragged. "
            "`st.chat_input` can return empty strings; a `system_prompt` text area can "
            "be blank; a temperature restored from session state can be out of range. "
            "Validate at the boundary — *before* the value reaches the model — so the "
            "UI stays a thin shell over trustworthy data."
        ),
        md("## Provided: Setup + Session State (from Exercise 1)"),
        code(_BEFORE_EX02),
        md("## Your Implementation"),
        code(
            "def validate_user_input(text: str, max_chars: int = 2000) -> tuple[bool, str]:\n"
            '    """\n'
            "    Returns (is_valid, result):\n"
            "      - empty/whitespace : (False, 'Please enter a message.')\n"
            "      - too long         : (False, 'Message too long (max N chars).')\n"
            "      - valid            : (True, cleaned_text)   # stripped\n"
            '    """\n'
            "    # TODO: cleaned = text.strip()\n"
            "    # TODO: if not cleaned: return (False, 'Please enter a message.')\n"
            "    # TODO: if len(cleaned) > max_chars: return (False, f'Message too long (max {max_chars} chars).')\n"
            "    # TODO: return (True, cleaned)\n"
            "    pass\n"
            "\n"
            "\n"
            "def clamp(value: float, lo: float, hi: float) -> float:\n"
            '    """Clamp value into [lo, hi]."""\n'
            "    # TODO: return max(lo, min(hi, value))\n"
            "    pass\n"
            "\n"
            "\n"
            "def build_settings(model: str, temperature: float, system_prompt: str) -> dict:\n"
            '    """temperature clamped to [0,1]; empty system_prompt -> default."""\n'
            "    # TODO: sp = system_prompt.strip() or 'You are a helpful assistant.'\n"
            "    # TODO: return {'model': model, 'temperature': float(clamp(temperature, 0.0, 1.0)), 'system_prompt': sp}\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: valid input returns (True, stripped_text)\n"
            "    try:\n"
            "        ok, result = validate_user_input('  hello world  ')\n"
            "        assert ok is True, f'expected valid, got {ok}'\n"
            "        assert result == 'hello world', f'expected stripped text, got {result!r}'\n"
            "        passed += 1; print('✅ Check 1: valid input -> (True, stripped)')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: empty / whitespace input is rejected\n"
            "    try:\n"
            "        ok1, _ = validate_user_input('')\n"
            "        ok2, _ = validate_user_input('   ')\n"
            "        assert ok1 is False and ok2 is False, 'empty/whitespace must be invalid'\n"
            "        passed += 1; print('✅ Check 2: empty/whitespace rejected')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 2: {e}')\n"
            "\n"
            "    # Check 3: over-length input is rejected\n"
            "    try:\n"
            "        ok, msg = validate_user_input('x' * 50, max_chars=10)\n"
            "        assert ok is False, 'over-length input must be invalid'\n"
            "        assert 'too long' in msg.lower(), f'expected a length message, got {msg!r}'\n"
            "        passed += 1; print('✅ Check 3: over-length input rejected')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 3: {e}')\n"
            "\n"
            "    # Check 4: clamp bounds values correctly\n"
            "    try:\n"
            "        assert clamp(-0.5, 0.0, 1.0) == 0.0, 'below-range should clamp to lo'\n"
            "        assert clamp(1.5, 0.0, 1.0) == 1.0, 'above-range should clamp to hi'\n"
            "        assert clamp(0.3, 0.0, 1.0) == 0.3, 'in-range should pass through'\n"
            "        passed += 1; print('✅ Check 4: clamp bounds values into [lo, hi]')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 4: {e}')\n"
            "\n"
            "    # Check 5: build_settings clamps temperature + defaults empty prompt\n"
            "    try:\n"
            "        s = build_settings('llama3.2', 2.0, '   ')\n"
            "        assert s['temperature'] == 1.0, f\"temperature not clamped: {s['temperature']}\"\n"
            "        assert s['system_prompt'] == 'You are a helpful assistant.', 'empty prompt not defaulted'\n"
            "        assert s['model'] == 'llama3.2', 'model not carried through'\n"
            "        passed += 1; print('✅ Check 5: build_settings clamps + defaults correctly')\n"
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
            + INPUT_IMPL + "\n"
            "```\n\n"
            "**Why this works:** Returning a `(bool, str)` tuple lets the UI branch "
            "cleanly: on `False` show `st.warning(result)`, on `True` send `result` to "
            "the model. `clamp` is a one-liner but guards against out-of-range values "
            "that slip past the slider (e.g. restored from state). `build_settings` "
            "centralises every defaulting rule so the sidebar code stays declarative.\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 03 — wiring state to the model
# ---------------------------------------------------------------------------

def ex03():
    global _cid; _cid = 200
    return [
        md(
            "# Day 051 — Exercise 3: Wiring State to the Model\n\n"
            "**What you'll build:** `build_messages(state, user_text)` and "
            "`chat_with_history(state, user_text, model)` — the functions the app "
            "calls when the user submits a message.\n\n"
            "**Why it matters:** A chat app must send the *whole* conversation to the "
            "model each turn — the system prompt, the prior turns, and the new one — "
            "or the model forgets everything. `build_messages` assembles that list "
            "without mutating state, and `chat_with_history` calls Ollama with a "
            "try/except fallback so a model hiccup never takes the UI down."
        ),
        md("## Provided: Setup + Session State + Input Handling"),
        code(_BEFORE_EX03),
        md("## Your Implementation"),
        code(
            "def build_messages(state: dict, user_text: str) -> list:\n"
            '    """\n'
            "    Build the ollama.chat messages list:\n"
            "        [system_prompt] + prior conversation + new user turn.\n"
            "    Read the system prompt from state['settings']. Do NOT mutate state.\n"
            '    """\n'
            "    settings = state.get('settings', {})\n"
            "    system_prompt = settings.get('system_prompt', 'You are a helpful assistant.')\n"
            "    # TODO: messages = [{'role': 'system', 'content': system_prompt}]\n"
            "    # TODO: messages.extend(state.get('messages', []))\n"
            "    # TODO: messages.append({'role': 'user', 'content': user_text})\n"
            "    # TODO: return messages\n"
            "    pass\n"
            "\n"
            "\n"
            "def chat_with_history(state: dict, user_text: str, model: str = 'llama3.2') -> str:\n"
            '    """\n'
            "    Send the conversation to Ollama; return the assistant reply.\n"
            "    Read temperature from state['settings']. Return a fallback string on error.\n"
            '    """\n'
            "    settings = state.get('settings', {})\n"
            "    temperature = settings.get('temperature', 0.7)\n"
            "    messages = build_messages(state, user_text)\n"
            "    # TODO: try: call ollama.chat(model=model, messages=messages,\n"
            "    #                              options={'temperature': temperature})\n"
            "    #        return response['message']['content'].strip()\n"
            "    # TODO: except Exception as e: return f'[Model unavailable: {e}]'\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    state = init_session({})\n"
            "    add_message(state, 'user', 'first question')\n"
            "    add_message(state, 'assistant', 'first answer')\n"
            "\n"
            "    # Check 1: build_messages returns a list starting with system, ending with user\n"
            "    try:\n"
            "        msgs = build_messages(state, 'second question')\n"
            "        assert isinstance(msgs, list), f'expected list, got {type(msgs).__name__}'\n"
            "        assert msgs[0]['role'] == 'system', 'first message must be system'\n"
            "        assert msgs[-1] == {'role': 'user', 'content': 'second question'}, 'last must be new user turn'\n"
            "        passed += 1; print('✅ Check 1: build_messages system-first, user-last')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: prior conversation is included in the middle\n"
            "    try:\n"
            "        msgs = build_messages(state, 'second question')\n"
            "        contents = [m['content'] for m in msgs]\n"
            "        assert 'first question' in contents and 'first answer' in contents, 'history missing'\n"
            "        assert len(msgs) == 4, f'expected system+2 history+user = 4, got {len(msgs)}'\n"
            "        passed += 1; print('✅ Check 2: prior history included')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 2: {e}')\n"
            "\n"
            "    # Check 3: build_messages does NOT mutate state\n"
            "    try:\n"
            "        before = len(state['messages'])\n"
            "        build_messages(state, 'temp')\n"
            "        assert len(state['messages']) == before, 'build_messages mutated state!'\n"
            "        passed += 1; print('✅ Check 3: build_messages leaves state unchanged')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 3: {e}')\n"
            "\n"
            "    # Check 4: chat_with_history returns a non-empty string\n"
            "    try:\n"
            "        reply = chat_with_history(state, 'Reply with the single word: pong')\n"
            "        assert isinstance(reply, str) and len(reply) > 0, f'expected non-empty str, got {reply!r}'\n"
            "        passed += 1; print(f'✅ Check 4: chat_with_history -> str ({len(reply)} chars)')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 4: {e}')\n"
            "\n"
            "    # Check 5: a bad model name is handled gracefully (fallback string, no crash)\n"
            "    try:\n"
            "        reply = chat_with_history(state, 'hi', model='no-such-model-xyz')\n"
            "        assert isinstance(reply, str), 'must return a string even on model error'\n"
            "        passed += 1; print('✅ Check 5: model error handled gracefully')\n"
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
            "**Why this works:** `build_messages` reads from state but returns a fresh "
            "list — it never appends to `state['messages']`, so the app controls "
            "exactly when history is committed. `chat_with_history` wraps the network "
            "call in try/except and returns a string on *every* path, so the UI can "
            "always render a reply — a crashed model becomes a visible message, not a "
            "500 page. `options={'temperature': ...}` is how Ollama takes sampling "
            "parameters.\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 04 — display helpers
# ---------------------------------------------------------------------------

def ex04():
    global _cid; _cid = 300
    return [
        md(
            "# Day 051 — Exercise 4: Display Helpers\n\n"
            "**What you'll build:** `format_transcript(messages)` for an "
            "`st.download_button`, and `chat_stats(messages)` for `st.metric` "
            "widgets.\n\n"
            "**Why it matters:** A good app doesn't just show the chat — it lets you "
            "export it and see it at a glance. These are pure functions that turn the "
            "message list into *display artifacts*: a downloadable transcript and a "
            "set of live counters. Keeping them out of the UI code means you can test "
            "them here, with no Streamlit runtime required."
        ),
        md("## Provided: Setup + Session State + Input + Model Wiring"),
        code(_BEFORE_EX04),
        md("## Your Implementation"),
        code(
            "def format_transcript(messages: list) -> str:\n"
            '    """\n'
            "    Plain-text transcript for st.download_button. One block per turn as\n"
            "    'ROLE: content'. Skip system messages. Join blocks with a blank line.\n"
            '    """\n'
            "    lines = []\n"
            "    # TODO: for m in messages:\n"
            "    #     role = m.get('role', '')\n"
            "    #     if role == 'system': continue\n"
            "    #     lines.append(f\"{role.upper()}: {m.get('content', '')}\")\n"
            "    # TODO: return '\\n\\n'.join(lines)\n"
            "    pass\n"
            "\n"
            "\n"
            "def chat_stats(messages: list) -> dict:\n"
            '    """\n'
            "    Metrics for st.metric. System messages excluded.\n"
            "    Return {'total', 'user', 'assistant', 'chars'}.\n"
            '    """\n'
            "    non_system = [m for m in messages if m.get('role') != 'system']\n"
            "    # TODO: user = sum(1 for m in non_system if m.get('role') == 'user')\n"
            "    # TODO: assistant = sum(1 for m in non_system if m.get('role') == 'assistant')\n"
            "    # TODO: chars = sum(len(m.get('content', '')) for m in non_system)\n"
            "    # TODO: return {'total': len(non_system), 'user': user, 'assistant': assistant, 'chars': chars}\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    convo = [\n"
            "        {'role': 'system', 'content': 'You are helpful.'},\n"
            "        {'role': 'user', 'content': 'hi'},\n"
            "        {'role': 'assistant', 'content': 'hello there'},\n"
            "        {'role': 'user', 'content': 'bye'},\n"
            "    ]\n"
            "\n"
            "    # Check 1: format_transcript returns a str with ROLE: prefixes\n"
            "    try:\n"
            "        t = format_transcript(convo)\n"
            "        assert isinstance(t, str), f'expected str, got {type(t).__name__}'\n"
            "        assert 'USER: hi' in t and 'ASSISTANT: hello there' in t, f'bad transcript:\\n{t}'\n"
            "        passed += 1; print('✅ Check 1: format_transcript uses ROLE: prefixes')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: system messages are skipped in the transcript\n"
            "    try:\n"
            "        t = format_transcript(convo)\n"
            "        assert 'SYSTEM' not in t and 'You are helpful' not in t, 'system message leaked into transcript'\n"
            "        passed += 1; print('✅ Check 2: system messages skipped')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 2: {e}')\n"
            "\n"
            "    # Check 3: chat_stats counts user + assistant correctly\n"
            "    try:\n"
            "        s = chat_stats(convo)\n"
            "        assert s['user'] == 2, f\"expected 2 user, got {s['user']}\"\n"
            "        assert s['assistant'] == 1, f\"expected 1 assistant, got {s['assistant']}\"\n"
            "        passed += 1; print('✅ Check 3: chat_stats counts roles')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 3: {e}')\n"
            "\n"
            "    # Check 4: total == user + assistant (system excluded)\n"
            "    try:\n"
            "        s = chat_stats(convo)\n"
            "        assert s['total'] == 3, f\"expected total 3 (no system), got {s['total']}\"\n"
            "        assert s['total'] == s['user'] + s['assistant'], 'total must equal user + assistant'\n"
            "        passed += 1; print('✅ Check 4: total excludes system messages')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 4: {e}')\n"
            "\n"
            "    # Check 5: chars counts non-system content characters\n"
            "    try:\n"
            "        s = chat_stats(convo)\n"
            "        expected = len('hi') + len('hello there') + len('bye')\n"
            "        assert s['chars'] == expected, f\"expected {expected} chars, got {s['chars']}\"\n"
            "        passed += 1; print(f\"✅ Check 5: chars={s['chars']} counts non-system content\")\n"
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
            + DISPLAY_IMPL + "\n"
            "```\n\n"
            "**Why this works:** Both functions are *pure* — same input, same output, "
            "no side effects — so they're trivial to test without a browser. "
            "`format_transcript` skips system messages because the user never sees "
            "them in the chat. `chat_stats` returns a flat dict that maps one-to-one "
            "onto `st.metric` calls, so the sidebar code is just "
            "`st.metric('Messages', chat_stats(msgs)['total'])`.\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 05 — ChatApp class
# ---------------------------------------------------------------------------

def ex05():
    global _cid; _cid = 400
    return [
        md(
            "# Day 051 — Exercise 5: The ChatApp Class\n\n"
            "**What you'll build:** `ChatApp` — the logic core stored in "
            "`st.session_state` and reused across reruns. Methods: `__init__(model, "
            "system_prompt)`, `send(user_text) -> str`, `stats() -> dict`, "
            "`transcript() -> str`, `reset()`.\n\n"
            "**Why it matters:** This is the whole pattern in one object. The Streamlit "
            "file stays a thin shell — it instantiates one `ChatApp`, calls `send()` on "
            "submit, and renders `stats()`/`transcript()`. Every function you wrote in "
            "Exercises 1–4 is wired together here, and *none* of it depends on "
            "Streamlit, so it's fully testable in this notebook."
        ),
        md("## Provided: All Helper Functions (Exercises 1–4)"),
        code(_BEFORE_EX05),
        md("## Your Implementation"),
        code(
            "class ChatApp:\n"
            '    """\n'
            "    Logic core of the Streamlit chat app. One instance per session,\n"
            "    reused across reruns. The UI only calls these methods.\n"
            '    """\n'
            "\n"
            "    def __init__(self, model: str = 'llama3.2',\n"
            "                 system_prompt: str = 'You are a helpful assistant.'):\n"
            "        # TODO: self.state = {}; init_session(self.state)\n"
            "        # TODO: self.state['settings']['model'] = model\n"
            "        # TODO: self.state['settings']['system_prompt'] = system_prompt\n"
            "        # TODO: self.model = model\n"
            "        pass\n"
            "\n"
            "    def send(self, user_text: str) -> str:\n"
            '        """Validate -> append user -> call model -> append assistant -> return reply.\n'
            "        On invalid input, return the error string and append NOTHING.\"\"\"\n"
            "        # TODO: ok, result = validate_user_input(user_text)\n"
            "        # TODO: if not ok: return result\n"
            "        # TODO: add_message(self.state, 'user', result)\n"
            "        # TODO: reply = chat_with_history(self.state, result, self.model)\n"
            "        # TODO: add_message(self.state, 'assistant', reply)\n"
            "        # TODO: return reply\n"
            "        pass\n"
            "\n"
            "    def stats(self) -> dict:\n"
            "        # TODO: return chat_stats(self.state['messages'])\n"
            "        pass\n"
            "\n"
            "    def transcript(self) -> str:\n"
            "        # TODO: return format_transcript(self.state['messages'])\n"
            "        pass\n"
            "\n"
            "    def reset(self) -> None:\n"
            "        # TODO: reset_messages(self.state)\n"
            "        pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: ChatApp has the four public methods\n"
            "    try:\n"
            "        assert 'ChatApp' in globals()\n"
            "        for m in ('send', 'stats', 'transcript', 'reset'):\n"
            "            assert hasattr(ChatApp, m), f'missing method: {m}'\n"
            "        passed += 1; print('✅ Check 1: ChatApp has send/stats/transcript/reset')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: send() appends one user + one assistant message\n"
            "    try:\n"
            "        app = ChatApp()\n"
            "        reply = app.send('Reply with the single word: pong')\n"
            "        assert isinstance(reply, str) and len(reply) > 0, 'send must return a non-empty reply'\n"
            "        s = app.stats()\n"
            "        assert s['total'] == 2, f\"expected 2 messages after one send, got {s['total']}\"\n"
            "        assert s['user'] == 1 and s['assistant'] == 1, 'expected 1 user + 1 assistant'\n"
            "        passed += 1; print(f'✅ Check 2: send() appended user + assistant ({len(reply)} char reply)')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 2: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 3: invalid input returns an error and appends nothing\n"
            "    try:\n"
            "        app = ChatApp()\n"
            "        out = app.send('   ')\n"
            "        assert isinstance(out, str) and 'enter a message' in out.lower(), f'expected error msg, got {out!r}'\n"
            "        assert app.stats()['total'] == 0, 'invalid input must not append messages'\n"
            "        passed += 1; print('✅ Check 3: invalid input -> error, nothing appended')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 3: {e}')\n"
            "\n"
            "    # Check 4: transcript() reflects the conversation\n"
            "    try:\n"
            "        app = ChatApp()\n"
            "        app.state['messages'] = [\n"
            "            {'role': 'user', 'content': 'hello'},\n"
            "            {'role': 'assistant', 'content': 'hi back'},\n"
            "        ]\n"
            "        t = app.transcript()\n"
            "        assert 'USER: hello' in t, f'transcript missing user turn:\\n{t}'\n"
            "        passed += 1; print('✅ Check 4: transcript() renders the conversation')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 4: {e}')\n"
            "\n"
            "    # Check 5: reset() clears the conversation\n"
            "    try:\n"
            "        app = ChatApp()\n"
            "        app.state['messages'] = [{'role': 'user', 'content': 'x'}]\n"
            "        app.reset()\n"
            "        assert app.stats()['total'] == 0, 'reset() must clear messages'\n"
            "        assert 'settings' in app.state, 'reset() must keep settings'\n"
            "        passed += 1; print('✅ Check 5: reset() clears the conversation')\n"
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
            + CHATAPP_IMPL + "\n"
            "```\n\n"
            "**Why this works:** `ChatApp` owns its own `state` dict — the same shape "
            "`st.session_state` would hold — so the Streamlit layer just stores one "
            "instance in `st.session_state.app` and calls methods on it. `send()` "
            "composes the whole turn (validate → user → model → assistant) and only "
            "commits messages when the input is valid, so a stray Enter key never "
            "pollutes the history. Because nothing here imports Streamlit, the entire "
            "app is testable in a plain notebook — which is exactly what these five "
            "exercises did.\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# app.py builder cell (shared by project + solution)
# ---------------------------------------------------------------------------

# The complete, self-contained Streamlit app: the same logic the exercises built
# (visible in the cell above) plus the UI layer. Assembled here so the notebook
# can write it verbatim — no inspect.getsource (which fails under nbconvert
# because notebook cells have no source file on disk).
APP_PY_SRC = (
    "import streamlit as st\n"
    "import ollama\n\n\n"
    + ALL_LOGIC + "\n\n\n"
    + CHATAPP_IMPL + "\n\n\n"
    + UI_CODE.strip() + "\n"
)

WRITE_APP_CELL = (
    "from pathlib import Path\n"
    "\n"
    "# The full Streamlit app source: the logic functions + ChatApp shown above,\n"
    "# plus the UI layer. Embedded as a string so we can write it to a real file.\n"
    "_APP_SRC = " + repr(APP_PY_SRC) + "\n"
    "\n"
    "\n"
    "def write_streamlit_app(path: str = 'app.py') -> str:\n"
    '    """Write the self-contained Streamlit app to `path` and return the path."""\n'
    "    Path(path).write_text(_APP_SRC, encoding='utf-8')\n"
    "    return path"
)


# ---------------------------------------------------------------------------
# Project notebook (student template — not executed by the gate)
# ---------------------------------------------------------------------------

def project_nb():
    global _cid; _cid = 500
    all_code = _BEFORE_EX05 + "\n\n\n" + CHATAPP_IMPL
    return [
        md(
            "# Day 051 Project: Local AI Chat App\n\n"
            "## What You're Building\n\n"
            "A complete, runnable **Streamlit chat app** backed by local Ollama. You "
            "run one command — `streamlit run app.py` — and get a browser UI with a "
            "chat window, a settings sidebar (temperature + system prompt), live "
            "message/character metrics, a *Clear chat* button, and a *Download "
            "transcript* button. That `app.py` is the deliverable.\n\n"
            "## Project Requirements\n\n"
            "1. Use the provided `ChatApp` logic core (built across Exercises 1–5).\n"
            "2. Instantiate `app = ChatApp()` and run a few `app.send(...)` turns to "
            "prove the logic works headlessly.\n"
            "3. Call `write_streamlit_app('app.py')` to generate the real app.\n"
            "4. Run `_run_project_checks()` to verify the app file is well-formed.\n"
            "5. Then, in a terminal: `streamlit run app.py` and chat with it.\n\n"
            "## Bonus Challenges\n\n"
            "- Add a model picker to the sidebar with `st.selectbox` (list your local "
            "Ollama models) and pass the choice through `build_settings`.\n"
            "- Add an `st.metric` for the average assistant reply length.\n"
            "- Persist the transcript to disk on each turn so a refresh restores it."
        ),
        md("## Provided: All Logic (Exercises 1–5)"),
        code(all_code),
        md("## Provided: app.py Builder"),
        code(WRITE_APP_CELL),
        md("## Your Pipeline"),
        code(
            "# TODO: app = ChatApp()\n"
            "# TODO: print(app.send('Give me one tip for writing clean Python.'))\n"
            "# TODO: print(app.send('Now summarise that in five words.'))\n"
            "# TODO: print('Stats:', app.stats())\n"
            "#\n"
            "# TODO: path = write_streamlit_app('app.py')\n"
            "# TODO: print('Wrote', path)\n"
            "# TODO: print('Run it with:  streamlit run app.py')"
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
            "    # Check 1: ChatApp instantiated and used\n"
            "    try:\n"
            "        assert 'app' in globals() and isinstance(app, ChatApp), 'create app = ChatApp()'\n"
            "        passed += 1; print('✅ Check 1: ChatApp instance created')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: app.py written\n"
            "    try:\n"
            "        assert os.path.exists('app.py'), 'app.py not found — call write_streamlit_app()'\n"
            "        passed += 1; print('✅ Check 2: app.py exists')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 2: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    src = open('app.py', encoding='utf-8').read()\n"
            "\n"
            "    # Check 3: app.py imports streamlit and defines ChatApp\n"
            "    try:\n"
            "        assert 'import streamlit as st' in src, 'app.py must import streamlit'\n"
            "        assert 'class ChatApp' in src, 'app.py must contain the ChatApp class'\n"
            "        passed += 1; print('✅ Check 3: app.py has streamlit import + ChatApp')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 3: {e}')\n"
            "\n"
            "    # Check 4: app.py uses session_state + chat_input (real Streamlit chat UI)\n"
            "    try:\n"
            "        assert 'st.session_state' in src, 'app.py must use st.session_state'\n"
            "        assert 'st.chat_input' in src, 'app.py must use st.chat_input'\n"
            "        passed += 1; print('✅ Check 4: app.py uses session_state + chat_input')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 4: {e}')\n"
            "\n"
            "    # Check 5: app.py is valid Python (compiles)\n"
            "    try:\n"
            "        compile(src, 'app.py', 'exec')\n"
            "        passed += 1; print('✅ Check 5: app.py compiles as valid Python')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\U0001f389 Project complete! Run: streamlit run app.py')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "\n"
            "_run_project_checks()"
        ),
    ]


# ---------------------------------------------------------------------------
# Solution notebook (runs clean under nbconvert — no Streamlit runtime)
# ---------------------------------------------------------------------------

def solution_nb():
    global _cid; _cid = 600
    all_code = _BEFORE_EX05 + "\n\n\n" + CHATAPP_IMPL
    return [
        md(
            "# Day 051 Solution — Local AI Chat App\n\n"
            "Section 4, Day 1. Builds the `ChatApp` logic core, drives it headlessly "
            "against Ollama, then generates a real, runnable `app.py` Streamlit file. "
            "This notebook never launches a server — it verifies the logic and the "
            "generated app instead. Run the app with `streamlit run app.py`."
        ),
        code(all_code),
        md("## Step 1 — Drive the ChatApp Logic Headlessly"),
        code(
            "app = ChatApp(system_prompt='You are a terse assistant. Answer briefly.')\n"
            "print('Reply 1:', app.send('Give me one tip for writing clean Python.'))\n"
            "print('Reply 2:', app.send('Summarise that in five words.'))\n"
            "print()\n"
            "print('Stats:', app.stats())\n"
            "assert app.stats()['total'] == 4, 'expected 2 user + 2 assistant turns'"
        ),
        md("## Step 2 — Validation + Reset Behaviour"),
        code(
            "err = app.send('   ')  # blank input\n"
            "print('Blank input ->', err)\n"
            "assert 'enter a message' in err.lower()\n"
            "assert app.stats()['total'] == 4, 'blank input must not append'\n"
            "\n"
            "print('\\nTranscript so far:')\n"
            "print(app.transcript())\n"
            "\n"
            "app.reset()\n"
            "assert app.stats()['total'] == 0\n"
            "print('\\nAfter reset, messages =', app.stats()['total'])"
        ),
        md("## Step 3 — Generate the Real Streamlit app.py"),
        code(WRITE_APP_CELL),
        code(
            "path = write_streamlit_app('app.py')\n"
            "src = open(path, encoding='utf-8').read()\n"
            "print(f'Wrote {path} ({len(src)} chars)')\n"
            "\n"
            "# Verify the generated app is well-formed\n"
            "assert 'import streamlit as st' in src\n"
            "assert 'class ChatApp' in src\n"
            "assert 'st.session_state' in src\n"
            "assert 'st.chat_input' in src\n"
            "compile(src, 'app.py', 'exec')  # must be valid Python\n"
            "print('app.py verified: imports streamlit, defines ChatApp, uses chat UI, compiles.')"
        ),
        md("## Step 4 — Preview the Generated UI Section"),
        code(
            "ui_start = src.index('# ---- Streamlit UI')\n"
            "print(src[ui_start:ui_start + 700])\n"
            "\n"
            "print('\\nTo launch the app, run in a terminal:')\n"
            "print('    streamlit run app.py')\n"
            "print('\\nDay 51 — Local AI Chat App complete! \U0001f389')"
        ),
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Generating Day 051 notebooks...")
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
