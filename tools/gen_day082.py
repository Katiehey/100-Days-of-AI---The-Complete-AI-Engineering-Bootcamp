#!/usr/bin/env python3
"""gen_day082.py — generate Day 082: Agent Memory."""
from pathlib import Path
import json

ROOT    = Path(__file__).parent.parent
DAY     = "082"
SECTION = "06_agents"
OUT     = ROOT / SECTION / f"day_{DAY}"

(OUT / "exercises").mkdir(parents=True, exist_ok=True)
(OUT / "lessons").mkdir(parents=True, exist_ok=True)
(OUT / "project" / "solution").mkdir(parents=True, exist_ok=True)

# ── deliverable fragments (composed into memory_agent.py AND reused as ────────
# ── given-code / embedded solutions in the exercises, so they stay in sync) ────

_DOC = '''\
"""memory_agent.py — Day 082: Agent Memory.

Days 79-81 built agents that act, reason, and route across many tools - but every
one of them starts each task from a blank slate. This day gives an agent memory:
short-term working memory for the current conversation, and long-term memory that
persists across sessions in SQLite, so the agent remembers you the next time.

Pieces:
  safe_parse_json / call_llm   - reused (Day 79)
  WorkingMemory                - short-term, in-session, bounded turn log
  LongTermMemory               - durable key/value facts in SQLite (persists)
  build_extraction_prompt / extract_memories - decide what is worth remembering
  build_memory_prompt          - inject long-term profile + recent turns
  MemoryAgent                  - an assistant that remembers you

Setup:
    pip install ollama
    ollama pull llama3.2
"""
'''

_FRAG_HELPERS = '''\
import json

# ── helpers reused from Day 79 ───────────────────────────────────────────────
def safe_parse_json(text):
    """Slice first '{' to last '}' and parse. Returns dict|None (Day 79)."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None
    try:
        data = json.loads(text[start:end + 1])
    except (json.JSONDecodeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def call_llm(messages, llm_fn=None):
    """Call the chat model, or the injected llm_fn(messages) -> str (Day 79)."""
    if llm_fn is not None:
        return llm_fn(messages)
    import ollama
    resp = ollama.chat(model="llama3.2", messages=messages)
    return resp["message"]["content"]
'''

_FRAG_WORKING = '''\

# ── short-term working memory (this session only) ────────────────────────────
class WorkingMemory:
    """Short-term memory: the recent turns of the current session.

    Bounded to the last `max_turns` messages so the prompt never grows without
    limit, and cleared at a session boundary. This is the agent's scratchpad -
    it does NOT survive a restart.
    """

    def __init__(self, max_turns=10):
        self.max_turns = max_turns
        self._turns = []

    def add(self, role, content):
        """Append a {role, content} turn; keep only the last max_turns. Returns self."""
        self._turns.append({"role": role, "content": str(content)})
        if len(self._turns) > self.max_turns:
            self._turns = self._turns[-self.max_turns:]
        return self

    def turns(self):
        """Return a copy of the recent turns."""
        return list(self._turns)

    def render(self):
        """Render the turns as text, one 'role: content' line each."""
        return "\\n".join(t["role"] + ": " + t["content"] for t in self._turns)

    def clear(self):
        """Forget the session (end-of-session boundary)."""
        self._turns.clear()

    def __len__(self):
        return len(self._turns)
'''

_FRAG_LONGTERM = '''\

# ── long-term memory (persists across sessions, SQLite) ──────────────────────
import sqlite3


class LongTermMemory:
    """Durable key/value memory backed by SQLite - survives restarts.

    Default db_path is ":memory:" (a private in-process database). Pass a file
    path to persist across sessions: a new LongTermMemory on the same path sees
    everything a previous one remembered.
    """

    def __init__(self, db_path=":memory:"):
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS memories "
            "(key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        self._conn.commit()

    def remember(self, key, value):
        """Store or overwrite a fact by key. Returns self."""
        self._conn.execute(
            "INSERT OR REPLACE INTO memories(key, value) VALUES(?, ?)",
            (str(key), str(value)))
        self._conn.commit()
        return self

    def recall(self, key):
        """Return the stored value for a key, or None if unknown."""
        row = self._conn.execute(
            "SELECT value FROM memories WHERE key = ?", (str(key),)).fetchone()
        return row[0] if row else None

    def search(self, term):
        """Return [{key, value}] where term (case-insensitive) is in key or value."""
        term = str(term).lower()
        rows = self._conn.execute("SELECT key, value FROM memories").fetchall()
        return [{"key": k, "value": v} for k, v in rows
                if term in k.lower() or term in v.lower()]

    def all(self):
        """Return every fact as [{key, value}], ordered by key."""
        rows = self._conn.execute(
            "SELECT key, value FROM memories ORDER BY key").fetchall()
        return [{"key": k, "value": v} for k, v in rows]

    def forget(self, key):
        """Delete a fact by key. Returns self."""
        self._conn.execute("DELETE FROM memories WHERE key = ?", (str(key),))
        self._conn.commit()
        return self

    def __len__(self):
        return self._conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]

    def close(self):
        """Close the database connection."""
        self._conn.close()
'''

_FRAG_EXTRACT = '''\

# ── deciding what is worth remembering (LLM-driven) ──────────────────────────
def build_extraction_prompt(message):
    """Ask the model which durable facts about the user to store long-term."""
    system = "\\n".join([
        "You extract durable facts about the user that are worth remembering.",
        "Return ONLY a JSON object mapping short snake_case keys to string values.",
        "Store only stable facts - name, location, preferences, goals.",
        "Ignore small talk and one-off questions.",
        "If there is nothing worth remembering, return {}.",
    ])
    return [{"role": "system", "content": system},
            {"role": "user", "content": str(message)}]


def extract_memories(message, llm_fn=None):
    """Return durable facts to store as {key: value}. Never raises.

    Unparseable model output falls back to an empty dict, so a bad extraction
    simply stores nothing rather than crashing the turn.
    """
    response = call_llm(build_extraction_prompt(message), llm_fn=llm_fn)
    data = safe_parse_json(response) or {}
    return {str(k): str(v) for k, v in data.items()}
'''

_FRAG_PROMPT = '''\

# ── recall: injecting memory into the prompt ─────────────────────────────────
def build_memory_prompt(message, working, longterm):
    """Build a chat prompt that injects long-term profile + short-term turns.

    The system message carries what we durably know about the user; the recent
    working-memory turns follow; the new message comes last.
    """
    facts = longterm.all()
    profile = "\\n".join("- " + f["key"] + ": " + f["value"] for f in facts)
    system = "\\n".join([
        "You are a helpful assistant with memory of the user.",
        "",
        "What you remember about the user:",
        profile if profile else "(nothing yet)",
    ])
    messages = [{"role": "system", "content": system}]
    messages.extend(working.turns())
    messages.append({"role": "user", "content": str(message)})
    return messages
'''

_FRAG_AGENT = '''\

# ── the agent that remembers you ─────────────────────────────────────────────
class MemoryAgent:
    """An assistant that remembers you within a session and across sessions.

    Two memories work together: a WorkingMemory for the current conversation
    (short-term, cleared at a session boundary) and a LongTermMemory for durable
    facts (persisted in SQLite). Each turn extracts new facts, injects everything
    remembered into the prompt, answers, and records the exchange.

    Example::

        mem = LongTermMemory("user.db")          # persists across runs
        agent = MemoryAgent(longterm=mem, llm_fn=my_llm_fn)
        agent.chat("Hi, I'm Kutlwano and I love SQL.")
        agent.chat("What do you know about me?")
    """

    def __init__(self, longterm=None, llm_fn=None, max_turns=10):
        self.longterm = longterm if longterm is not None else LongTermMemory()
        self.working = WorkingMemory(max_turns=max_turns)
        self._llm_fn = llm_fn

    def chat(self, message):
        """Remember new facts, answer with memory in context, record the turn."""
        for key, value in extract_memories(message, llm_fn=self._llm_fn).items():
            self.longterm.remember(key, value)
        prompt = build_memory_prompt(message, self.working, self.longterm)
        reply = call_llm(prompt, llm_fn=self._llm_fn)
        self.working.add("user", message)
        self.working.add("assistant", reply)
        return reply

    def remember(self, key, value):
        """Store a durable fact directly. Returns self."""
        self.longterm.remember(key, value)
        return self

    def recall(self, key):
        """Look up a durable fact by key."""
        return self.longterm.recall(key)

    def profile(self):
        """Everything remembered about the user, as [{key, value}]."""
        return self.longterm.all()

    def end_session(self):
        """Clear short-term working memory; long-term persists."""
        self.working.clear()
'''

_MEMORY_AGENT_SRC = (_DOC + _FRAG_HELPERS + _FRAG_WORKING + _FRAG_LONGTERM
                     + _FRAG_EXTRACT + _FRAG_PROMPT + _FRAG_AGENT)


# ── notebook helpers ──────────────────────────────────────────────────────────
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


# ── shared mock helper ────────────────────────────────────────────────────────
_MOCK_HELPER = """\
import json

def _mock_llm(facts=None, reply='Sure!'):
    \"\"\"An llm_fn: returns extracted `facts` (as JSON) to the extraction prompt,
    and `reply` to a normal chat prompt - it branches on the system message.\"\"\"
    payload = json.dumps(facts or {})
    def _fn(messages):
        system = messages[0]['content'] if messages else ''
        if 'extract' in system.lower():
            return payload
        return reply
    return _fn
"""

# ── EX1: WorkingMemory ───────────────────────────────────────────────────────
_EX1_GIVEN = "# Short-term working memory - a pure Python class, no imports needed.\n"

_EX1_STUB = """\
class WorkingMemory:
    \"\"\"Short-term, in-session memory: recent turns, bounded and clearable.\"\"\"

    def __init__(self, max_turns=10):
        raise NotImplementedError

    def add(self, role, content):
        raise NotImplementedError

    def turns(self):
        raise NotImplementedError

    def render(self):
        raise NotImplementedError

    def clear(self):
        raise NotImplementedError

    def __len__(self):
        raise NotImplementedError
"""

_EX1_CHECKS = r"""
score, total = 0, 5
try:
    wm = WorkingMemory(max_turns=3)
    wm.add('user', 'hi').add('assistant', 'hello')
    assert len(wm) == 2
    score += 1; print("✅ add records turns and returns self (chainable)")

    assert wm.turns()[0] == {'role': 'user', 'content': 'hi'}
    score += 1; print("✅ turns() returns the {role, content} log")

    wm.turns().clear()
    assert len(wm) == 2
    score += 1; print("✅ turns() returns a copy, not the live list")

    for i in range(5):
        wm.add('user', str(i))
    assert len(wm) == 3 and wm.turns()[0]['content'] == '2'
    score += 1; print("✅ bounded to the last max_turns messages")

    assert 'user: hi' not in wm.render()      # 'hi' was evicted long ago
    wm.clear()
    assert len(wm) == 0
    score += 1; print("✅ render() formats the turns; clear() ends the session")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX1 = nb([
    md("# Day 082 — Exercise 1: Short-Term Working Memory\n\n"
       "**What you'll build:** `WorkingMemory` — a bounded log of the recent turns "
       "in the current conversation.\n\n"
       "**Why it matters:** an agent needs to remember what was *just* said to stay "
       "coherent across a few turns. Working memory is that scratchpad — but it's "
       "bounded (so the prompt never grows forever) and disposable (cleared when the "
       "session ends). Tomorrow's other half, long-term memory, is what actually "
       "persists."),
    code(_EX1_GIVEN),
    md("## Task\n\n"
       "`WorkingMemory(max_turns=10)`\n\n"
       "- `add(role, content)` — append `{'role', 'content'}` (stringify content); if "
       "over `max_turns`, keep only the last `max_turns`; return `self`.\n"
       "- `turns()` — a **copy** of the turn list.\n"
       "- `render()` — one `role: content` line per turn.\n"
       "- `clear()` — empty the log in place.\n"
       "- `__len__` — number of turns held."),
    md("## Your Implementation"),
    code(_EX1_STUB),
    code(_FRAG_WORKING),
    md("## Automated checks"),
    code(_EX1_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _FRAG_WORKING + "```\n\n"
       "**Why bound the turns?** Every turn goes into the next prompt. Without a cap "
       "the context grows without limit — slower, costlier, and eventually past the "
       "model's window. Keeping the last `max_turns` is the simplest sliding-window "
       "policy that keeps recent context while staying bounded.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_01.ipynb", EX1)

# ── EX2: LongTermMemory ──────────────────────────────────────────────────────
_EX2_GIVEN = "# Long-term memory persists facts in SQLite (sqlite3 is stdlib).\n"

_EX2_STUB = """\
class LongTermMemory:
    \"\"\"Durable key/value memory backed by SQLite (persists across sessions).\"\"\"

    def __init__(self, db_path=":memory:"):
        raise NotImplementedError

    def remember(self, key, value):
        raise NotImplementedError

    def recall(self, key):
        raise NotImplementedError

    def search(self, term):
        raise NotImplementedError

    def all(self):
        raise NotImplementedError

    def forget(self, key):
        raise NotImplementedError

    def __len__(self):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError
"""

_EX2_CHECKS = r"""
import os, tempfile
score, total = 0, 6
try:
    m = LongTermMemory()      # ":memory:" - private in-process db
    m.remember('name', 'Kutlwano').remember('lang', 'Python')
    assert len(m) == 2 and m.recall('name') == 'Kutlwano'
    score += 1; print("✅ remember/recall store and fetch facts")

    m.remember('name', 'Kutlwano M.')     # same key overwrites
    assert m.recall('name') == 'Kutlwano M.' and len(m) == 2
    score += 1; print("✅ remember overwrites an existing key (upsert)")

    assert m.recall('missing') is None
    score += 1; print("✅ recall returns None for an unknown key")

    hits = m.search('python')
    assert len(hits) == 1 and hits[0]['key'] == 'lang'
    score += 1; print("✅ search matches key or value, case-insensitively")

    m.forget('lang')
    assert m.recall('lang') is None and len(m) == 1
    score += 1; print("✅ forget deletes a fact")

    path = tempfile.NamedTemporaryFile(suffix='.db', delete=False).name
    try:
        a = LongTermMemory(path); a.remember('goal', 'ship agents'); a.close()
        b = LongTermMemory(path)
        assert b.recall('goal') == 'ship agents'
        b.close()
        score += 1; print("✅ long-term memory persists across sessions (SQLite file)")
    finally:
        os.unlink(path)

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX2 = nb([
    md("# Day 082 — Exercise 2: Long-Term Memory (SQLite)\n\n"
       "**What you'll build:** `LongTermMemory` — a durable key/value store, backed "
       "by SQLite, that survives a restart.\n\n"
       "**Why it matters:** working memory vanishes when the session ends. For an "
       "agent to remember *you* — your name, your preferences, your goals — it needs "
       "storage that persists. SQLite (stdlib, zero setup) is the workhorse: point it "
       "at a file and the facts are still there next run."),
    code(_EX2_GIVEN),
    md("## Task\n\n"
       "`LongTermMemory(db_path=\":memory:\")` — connect and "
       "`CREATE TABLE IF NOT EXISTS memories(key TEXT PRIMARY KEY, value TEXT)`.\n\n"
       "- `remember(key, value)` — `INSERT OR REPLACE` (upsert); return `self`.\n"
       "- `recall(key)` — the value, or `None`.\n"
       "- `search(term)` — `[{key, value}]` where `term` is in key or value "
       "(case-insensitive).\n"
       "- `all()` — every fact as `[{key, value}]`, ordered by key.\n"
       "- `forget(key)` — delete; return `self`. `__len__` — row count. "
       "`close()` — close the connection.\n\n"
       "Pass a file path (not `:memory:`) and a **new** `LongTermMemory` on that path "
       "sees what an earlier one stored — that's persistence."),
    md("## Your Implementation"),
    code(_EX2_STUB),
    code(_FRAG_LONGTERM),
    md("## Automated checks"),
    code(_EX2_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _FRAG_LONGTERM + "```\n\n"
       "**Why `INSERT OR REPLACE`?** Memory is keyed by a stable name — `name`, "
       "`goal`. When a fact changes you want to overwrite, not accumulate duplicates. "
       "`INSERT OR REPLACE` on a `PRIMARY KEY` column is SQLite's one-line upsert: new "
       "key inserts, existing key overwrites.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_02.ipynb", EX2)

# ── EX3: extract_memories ────────────────────────────────────────────────────
_EX3_GIVEN = _MOCK_HELPER + _FRAG_HELPERS

_EX3_STUB = """\
def build_extraction_prompt(message):
    \"\"\"Ask the model which durable facts about the user to store.\"\"\"
    raise NotImplementedError

def extract_memories(message, llm_fn=None):
    \"\"\"Return durable facts as {key: value}. Never raises.\"\"\"
    raise NotImplementedError
"""

_EX3_CHECKS = r"""
score, total = 0, 4
try:
    msgs = build_extraction_prompt("I'm Kutlwano and I love SQL")
    assert msgs[0]['role'] == 'system' and 'extract' in msgs[0]['content'].lower()
    assert msgs[1]['content'] == "I'm Kutlwano and I love SQL"
    score += 1; print("✅ extraction prompt asks for durable facts as JSON")

    facts = extract_memories('x', llm_fn=_mock_llm(facts={'name': 'Kutlwano'}))
    assert facts == {'name': 'Kutlwano'}
    score += 1; print("✅ extract_memories returns the parsed facts")

    empty = extract_memories('hello', llm_fn=_mock_llm(facts={}))
    assert empty == {}
    score += 1; print("✅ nothing worth remembering -> empty dict")

    junk = extract_memories('x', llm_fn=lambda m: 'no json here, sorry')
    assert junk == {}
    score += 1; print("✅ unparseable output -> {} (never raises)")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX3 = nb([
    md("# Day 082 — Exercise 3: Deciding What to Remember\n\n"
       "**What you'll build:** `build_extraction_prompt` and `extract_memories` — the "
       "model reads a message and returns the durable facts worth storing.\n\n"
       "**Why it matters:** you can't save *everything* — most chatter isn't worth "
       "remembering. Extraction is the judgement step: pull out the stable facts "
       "(name, preferences, goals) and drop the small talk. And like every parser this "
       "section, it must degrade to *nothing* rather than crash on messy output."),
    code(_EX3_GIVEN),
    md("## Task\n\n"
       "1. `build_extraction_prompt(message)` — a `system` message instructing the "
       "model to return **only** a JSON object of `snake_case_key: value` durable "
       "facts (or `{}` if none), and a `user` message with the raw text.\n"
       "2. `extract_memories(message, llm_fn=None) -> dict` — call the model, "
       "`safe_parse_json` the reply (`or {}`), and return "
       "`{str(k): str(v) for k, v in data.items()}`. **Never raises.**"),
    md("## Your Implementation"),
    code(_EX3_STUB),
    code(_FRAG_EXTRACT),
    md("## Automated checks"),
    code(_EX3_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _FRAG_EXTRACT + "```\n\n"
       "**Why `safe_parse_json(response) or {}`?** The model might wrap its JSON in "
       "prose, or emit no JSON at all. `safe_parse_json` returns `None` on failure; "
       "`or {}` turns that into an empty result, so a bad extraction stores nothing "
       "instead of raising and killing the turn.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_03.ipynb", EX3)

# ── EX4: build_memory_prompt ─────────────────────────────────────────────────
_EX4_GIVEN = _FRAG_WORKING + _FRAG_LONGTERM

_EX4_STUB = """\
def build_memory_prompt(message, working, longterm):
    \"\"\"Inject long-term profile + working-memory turns, then the new message.\"\"\"
    raise NotImplementedError
"""

_EX4_CHECKS = r"""
score, total = 0, 4
try:
    wm = WorkingMemory()
    lt = LongTermMemory()
    lt.remember('name', 'Kutlwano')

    prompt = build_memory_prompt('hello', wm, lt)
    assert prompt[0]['role'] == 'system' and 'name: Kutlwano' in prompt[0]['content']
    score += 1; print("✅ long-term facts are injected into the system message")

    assert prompt[-1] == {'role': 'user', 'content': 'hello'}
    score += 1; print("✅ the new message comes last")

    wm.add('user', 'earlier').add('assistant', 'noted')
    p2 = build_memory_prompt('now', wm, lt)
    assert {'role': 'assistant', 'content': 'noted'} in p2 and p2[-1]['content'] == 'now'
    score += 1; print("✅ working-memory turns sit between system and new message")

    empty = build_memory_prompt('hi', WorkingMemory(), LongTermMemory())
    assert 'nothing yet' in empty[0]['content']
    score += 1; print("✅ an empty profile still builds a valid prompt")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX4 = nb([
    md("# Day 082 — Exercise 4: Recall — Injecting Memory into the Prompt\n\n"
       "**What you'll build:** `build_memory_prompt` — assemble the chat prompt so "
       "the model *sees* what's remembered: the long-term profile up top, the recent "
       "turns next, the new message last.\n\n"
       "**Why it matters:** storing memory is only half the job. Memory only helps if "
       "it's put back *in front of the model* at the right place. This is recall: the "
       "durable profile becomes system context, working memory supplies recent turns, "
       "and the new question follows."),
    code(_EX4_GIVEN),
    md("## Task\n\n"
       "`build_memory_prompt(message, working, longterm) -> list[dict]`\n\n"
       "1. `facts = longterm.all()`; render a profile of `- key: value` lines (use "
       "`\"(nothing yet)\"` when empty).\n"
       "2. A `system` message: an assistant intro + `What you remember about the "
       "user:` + the profile.\n"
       "3. Then `working.turns()`, then the new `{'role': 'user', 'content': "
       "message}` last."),
    md("## Your Implementation"),
    code(_EX4_STUB),
    code(_FRAG_PROMPT),
    md("## Automated checks"),
    code(_EX4_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _FRAG_PROMPT + "```\n\n"
       "**Why put the profile in the *system* message?** The durable facts are "
       "standing context that should color every reply, not a one-off user turn. "
       "System is where persistent instructions live, so the profile shapes the whole "
       "conversation rather than being buried mid-history.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_04.ipynb", EX4)

# ── EX5: MemoryAgent ─────────────────────────────────────────────────────────
_EX5_GIVEN = (_MOCK_HELPER + _FRAG_HELPERS + _FRAG_WORKING + _FRAG_LONGTERM
              + _FRAG_EXTRACT + _FRAG_PROMPT)

_EX5_STUB = """\
class MemoryAgent:
    \"\"\"An assistant that remembers you within and across sessions.\"\"\"

    def __init__(self, longterm=None, llm_fn=None, max_turns=10):
        raise NotImplementedError

    def chat(self, message):
        raise NotImplementedError

    def remember(self, key, value):
        raise NotImplementedError

    def recall(self, key):
        raise NotImplementedError

    def profile(self):
        raise NotImplementedError

    def end_session(self):
        raise NotImplementedError
"""

_EX5_CHECKS = r"""
score, total = 0, 6
try:
    agent = MemoryAgent(llm_fn=_mock_llm(facts={'name': 'Kutlwano'}, reply='Hi Kutlwano!'))
    out = agent.chat("I'm Kutlwano")
    assert out == 'Hi Kutlwano!'
    score += 1; print("✅ chat returns the model reply")

    assert agent.recall('name') == 'Kutlwano'
    score += 1; print("✅ chat extracts and stores durable facts")

    assert len(agent.working) == 2       # user + assistant recorded
    score += 1; print("✅ each turn is recorded in working memory")

    agent.remember('lang', 'Python')
    assert {'key': 'lang', 'value': 'Python'} in agent.profile()
    score += 1; print("✅ remember/profile expose long-term memory directly")

    agent.end_session()
    assert len(agent.working) == 0 and agent.recall('name') == 'Kutlwano'
    score += 1; print("✅ end_session clears working memory but keeps long-term")

    fresh = MemoryAgent(longterm=agent.longterm, llm_fn=_mock_llm(reply='ok'))
    assert fresh.recall('name') == 'Kutlwano'
    score += 1; print("✅ a new agent on the same long-term memory remembers you")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX5 = nb([
    md("# Day 082 — Exercise 5: MemoryAgent\n\n"
       "**What you'll build:** `MemoryAgent` — an assistant that ties the two "
       "memories together: it extracts and stores durable facts, recalls them into "
       "every prompt, and remembers you across sessions.\n\n"
       "**Why it matters:** this is the day's payoff. Where Days 79–81 agents began "
       "each task blank, this one carries a profile of you forward — the difference "
       "between a stateless tool and an assistant that actually knows who it's talking "
       "to."),
    code(_EX5_GIVEN),
    md("## Task\n\n"
       "`MemoryAgent(longterm=None, llm_fn=None, max_turns=10)`\n\n"
       "1. `__init__` — use the given `longterm` or a fresh `LongTermMemory()`; build "
       "a `WorkingMemory(max_turns)`; store `_llm_fn`.\n"
       "2. `chat(message)` — `extract_memories` and `remember` each fact; "
       "`build_memory_prompt`; `call_llm`; `add` the user + assistant turns to working "
       "memory; return the reply.\n"
       "3. `remember(key, value)` → `self`; `recall(key)`; `profile()` → "
       "`longterm.all()`; `end_session()` → clear working memory (long-term "
       "persists)."),
    md("## Your Implementation"),
    code(_EX5_STUB),
    code(_FRAG_AGENT),
    md("## Automated checks"),
    code(_EX5_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _FRAG_AGENT + "```\n\n"
       "**Why does `chat` call the model twice?** Once to *extract* what to remember "
       "from the new message, once to *answer* it with memory in context. Separating "
       "the two keeps each prompt focused — extraction judges what's durable; the "
       "answer draws on the whole profile — and it's why the mock branches on the "
       "system message.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_05.ipynb", EX5)

# ── YAML lessons ──────────────────────────────────────────────────────────────
_LESSON_01 = """\
day: "082"
lesson: 1
title: "Two Kinds of Memory"
slides:
  - type: title
    heading: "Agent Memory"
    subheading: "Short-term working memory and long-term persistence"
    narration: >
      Every agent so far - the action loop, the reasoning loop, the tool router -
      starts each task from a blank slate. Today we fix that with memory. There are
      two kinds, and the distinction runs through the whole day: short-term working
      memory that lives inside one conversation, and long-term memory that persists
      across sessions. This first lesson builds the short-term half.

  - type: concept
    label: "Two memories"
    heading: "Working Memory vs Long-Term Memory"
    body: >
      Agents need both, for different jobs.
    bullets:
      - "Working memory: the recent turns of THIS conversation"
      - "Bounded and disposable - cleared when the session ends"
      - "Long-term memory: durable facts about the user"
      - "Persisted to storage - survives a restart"
      - "Together: coherent now, and remembers you next time"
    narration: >
      Think of it like human memory. Working memory holds what was just said, so you
      stay coherent across a few turns - but it is small, and you let it go when the
      conversation is over. Long-term memory is different: the durable facts, your
      name, your preferences, your goals, written down so they are still there
      tomorrow. An agent needs both. Today's first class is working memory; the next
      lesson builds the long-term store.

  - type: code
    label: "WorkingMemory"
    heading: "A Bounded Log of Recent Turns"
    code: |
      class WorkingMemory:
          def __init__(self, max_turns=10):
              self.max_turns = max_turns
              self._turns = []

          def add(self, role, content):
              self._turns.append({"role": role, "content": str(content)})
              if len(self._turns) > self.max_turns:
                  self._turns = self._turns[-self.max_turns:]
              return self
    narration: >
      WorkingMemory is a list of role-and-content turns with one rule: keep only the
      last max_turns. Every turn you add eventually goes back into the prompt, so if
      you never cap it the context grows without limit - slower, costlier, and
      eventually past the model's window. Slicing to the last max_turns is the
      simplest sliding window: it keeps recent context while staying bounded. add
      returns self so you can chain.

  - type: concept
    label: "Session boundary"
    heading: "Working Memory Is Disposable"
    body: >
      Clearing working memory is a feature, not a loss.
    bullets:
      - "turns() returns a COPY - callers can't mutate the log"
      - "render() formats the turns for a prompt"
      - "clear() empties it - the session boundary"
      - "Nothing here survives a restart - that's long-term's job"
      - "Short-term forgets on purpose; long-term remembers on purpose"
    narration: >
      Working memory is meant to be thrown away. When a conversation ends you call
      clear, and the scratchpad is empty for the next one. That is deliberate - you
      do not want last week's chit-chat bleeding into today. Anything that should
      outlast the session is not working memory's job; it belongs in the long-term
      store. Notice turns returns a copy, the same defensive habit from every history
      method this course - callers read it, they do not mutate the live log.

  - type: exercise
    heading: "Exercise 1: Short-Term Working Memory"
    prompt: >
      Build WorkingMemory(max_turns=10): add(role, content) appends a {role, content}
      turn, keeps only the last max_turns, returns self; turns() returns a copy;
      render() formats one 'role: content' line per turn; clear() empties it; __len__
      counts the turns.
    hint: >
      Store a list of dicts. In add, after appending, slice to self._turns[-max_turns:]
      if it's too long. turns() returns list(self._turns) - a copy.
    narration: >
      This builds the short-term scratchpad the agent keeps for the current
      conversation.

  - type: summary
    heading: "Lesson 1 Summary"
    bullets:
      - "Two memories: short-term working + long-term persistent"
      - "WorkingMemory = a bounded log of recent turns"
      - "Bounded to max_turns so the prompt never grows forever"
      - "turns() returns a copy; clear() is the session boundary"
      - "Working memory forgets on purpose - long-term is next"
    narration: >
      Lesson 2 builds the other half: long-term memory that persists across sessions
      in SQLite.
"""

_LESSON_02 = """\
day: "082"
lesson: 2
title: "Long-Term Memory with SQLite"
slides:
  - type: title
    heading: "Long-Term Memory"
    subheading: "Durable facts that survive a restart, in SQLite"
    narration: >
      Working memory vanishes when the session ends. For an agent to remember you -
      not just this conversation, but you, across days - it needs storage that
      persists. This lesson builds LongTermMemory: a durable key-value store backed
      by SQLite, the zero-setup database that ships with Python.

  - type: concept
    label: "Why persist"
    heading: "Memory That Outlives the Process"
    body: >
      Long-term memory is a small database of facts.
    bullets:
      - "Keyed by a stable name: name, location, favourite_language"
      - "SQLite: a real database in a single file, stdlib, no server"
      - "':memory:' for a private in-process db; a file path to persist"
      - "remember / recall / search / all / forget - a tiny CRUD"
      - "A new object on the same file sees the old facts"
    narration: >
      Long-term memory is just a small table of key-value facts, but backed by a real
      database so it survives the process ending. SQLite is perfect here: it is part
      of the standard library, needs no server, and stores everything in one file.
      Point it at ":memory:" and you get a fast private database for testing; point it
      at a file path and the facts are still there the next time you open it. That
      file is what makes the memory long-term.

  - type: code
    label: "remember / recall"
    heading: "Upsert and Fetch"
    code: |
      import sqlite3

      class LongTermMemory:
          def __init__(self, db_path=":memory:"):
              self._conn = sqlite3.connect(db_path)
              self._conn.execute("CREATE TABLE IF NOT EXISTS memories "
                                 "(key TEXT PRIMARY KEY, value TEXT NOT NULL)")
              self._conn.commit()

          def remember(self, key, value):
              self._conn.execute("INSERT OR REPLACE INTO memories(key, value) "
                                 "VALUES(?, ?)", (str(key), str(value)))
              self._conn.commit()
              return self

          def recall(self, key):
              row = self._conn.execute("SELECT value FROM memories WHERE key = ?",
                                       (str(key),)).fetchone()
              return row[0] if row else None
    narration: >
      The table has two columns - key as the primary key, and value. remember uses
      INSERT OR REPLACE: on a new key it inserts, on an existing key it overwrites.
      That is exactly what you want for memory - when a fact changes you update it in
      place, you do not pile up duplicates. recall runs a parameterised SELECT and
      returns the value or None. Notice the question-mark placeholders: never format
      SQL with string concatenation, always pass parameters, so a value can never be
      read as SQL.

  - type: concept
    label: "Search and forget"
    heading: "The Rest of the Store"
    body: >
      A few more methods round out the memory.
    bullets:
      - "search(term): facts whose key or value contains term"
      - "all(): every fact, ordered - the whole profile"
      - "forget(key): delete a fact that's wrong or stale"
      - "__len__: how many facts are stored"
      - "close(): release the database connection"
    narration: >
      Beyond remember and recall you want to browse and prune. search scans keys and
      values for a term, case-insensitively - a simple way to find relevant facts.
      all returns the whole profile, ordered, which is what the next lesson feeds into
      the prompt. forget deletes a fact that has gone stale or was wrong, because a
      memory you cannot correct becomes a liability. These five methods - remember,
      recall, search, all, forget - are the entire long-term store.

  - type: exercise
    heading: "Exercise 2: Long-Term Memory (SQLite)"
    prompt: >
      Build LongTermMemory(db_path=":memory:") over a SQLite memories(key PRIMARY KEY,
      value) table: remember (INSERT OR REPLACE, returns self), recall (value or None),
      search (key or value contains term, case-insensitive), all (ordered
      [{key,value}]), forget, __len__, close. A new object on the same file path sees
      the stored facts.
    hint: >
      sqlite3.connect(db_path); CREATE TABLE IF NOT EXISTS. Use ? placeholders, never
      string formatting. remember: INSERT OR REPLACE. recall: fetchone(), return
      row[0] if row else None.
    narration: >
      This is the durable half of the agent's memory - the facts that make it remember
      you next time.

  - type: summary
    heading: "Lesson 2 Summary"
    bullets:
      - "LongTermMemory persists facts in SQLite (stdlib, one file)"
      - "':memory:' for tests; a file path to survive restarts"
      - "INSERT OR REPLACE = upsert on a PRIMARY KEY column"
      - "Always use ? placeholders - never format SQL strings"
      - "remember / recall / search / all / forget - a tiny CRUD"
    narration: >
      Lesson 3 asks the harder question: given a message, which facts are even worth
      remembering? That's LLM-driven extraction.
"""

_LESSON_03 = """\
day: "082"
lesson: 3
title: "Deciding What to Remember"
slides:
  - type: title
    heading: "What Is Worth Remembering?"
    subheading: "The model extracts durable facts from a message"
    narration: >
      You have a place to store memories now - but you cannot store everything. Most
      of what a user says is passing chatter that is not worth keeping. Deciding what
      is durable is a judgement call, and it is exactly the kind of judgement a
      language model is good at. This lesson uses the model itself to extract the
      facts worth remembering.

  - type: concept
    label: "Extraction"
    heading: "Memory as a Filter"
    body: >
      Extraction separates the durable from the disposable.
    bullets:
      - "Not everything said is worth storing"
      - "Durable: name, location, preferences, goals"
      - "Disposable: 'what time is it', 'thanks', small talk"
      - "Ask the model for a JSON object of key -> value facts"
      - "Empty object when there is nothing worth keeping"
    narration: >
      Extraction is a filter. If you saved every message the store would fill with
      noise and the useful facts would drown. So you ask the model a focused question:
      from this message, what durable facts about the user are worth remembering?
      Return them as a small JSON object mapping short keys to values - and return an
      empty object when there is nothing worth keeping, which is most of the time. The
      model is doing the judging; your code just stores what comes back.

  - type: code
    label: "extract_memories"
    heading: "Extract, Parse, Never Crash"
    code: |
      def extract_memories(message, llm_fn=None):
          response = call_llm(build_extraction_prompt(message), llm_fn=llm_fn)
          data = safe_parse_json(response) or {}
          return {str(k): str(v) for k, v in data.items()}
    narration: >
      extract_memories builds the extraction prompt, calls the model, and parses the
      reply with the tolerant safe_parse_json from Day 79. The key defensive move is
      "or empty dict": if the model wraps its JSON in prose, or returns no JSON at all,
      safe_parse_json gives back None and we fall to an empty dict. A failed
      extraction simply stores nothing - it never raises and kills the turn. Then we
      coerce keys and values to strings so they drop straight into the SQLite store.

  - type: concept
    label: "Extract then store"
    heading: "Two Steps: Judge, Then Persist"
    body: >
      Extraction decides; the store keeps.
    bullets:
      - "extract_memories: the model judges what's durable"
      - "remember: LongTermMemory persists each fact"
      - "Same-key facts overwrite - the profile stays current"
      - "Extraction can be wrong - forget() is the correction"
      - "The agent (Lesson 5) chains extract -> remember every turn"
    narration: >
      Keep the two responsibilities separate. Extraction is the model's judgement
      about what matters; storing is your database's job. Every turn, the agent will
      extract facts and remember each one - and because remember upserts by key, a
      changed fact overwrites the old value and the profile stays current. Extraction
      is not perfect; the model will sometimes store something it should not. That is
      why forget exists - memory you can correct is memory you can trust.

  - type: exercise
    heading: "Exercise 3: Deciding What to Remember"
    prompt: >
      Implement build_extraction_prompt(message) - a system message asking for ONLY a
      JSON object of snake_case key -> value durable facts (or {}), plus the user
      message - and extract_memories(message, llm_fn=None) which calls the model,
      safe_parse_json (or {}), and returns {str(k): str(v)}. Never raises.
    hint: >
      build_extraction_prompt returns [system, user] messages. extract_memories:
      data = safe_parse_json(response) or {}; return a str-keyed, str-valued dict
      comprehension over data.items().
    narration: >
      This is the judgement step - the model deciding, per message, what is worth
      remembering.

  - type: summary
    heading: "Lesson 3 Summary"
    bullets:
      - "You can't store everything - extraction is the filter"
      - "The model returns durable facts as a JSON object"
      - "extract_memories parses with safe_parse_json - never raises"
      - "Bad or missing JSON -> {} -> store nothing"
      - "Extract (judge) then remember (persist) are separate steps"
    narration: >
      Lesson 4 does the reverse direction: recall - putting the stored memory back in
      front of the model at the right place in the prompt.
"""

_LESSON_04 = """\
day: "082"
lesson: 4
title: "Recall - Injecting Memory into the Prompt"
slides:
  - type: title
    heading: "Recall"
    subheading: "Memory only helps if the model sees it"
    narration: >
      Storing facts is only half the loop. A memory the model never sees changes
      nothing. Recall is the other half: putting the right memories back into the
      prompt, in the right place, so they actually shape the answer. This lesson
      builds build_memory_prompt, which assembles long-term profile, recent turns, and
      the new message into one prompt.

  - type: concept
    label: "Recall"
    heading: "Three Layers of Context"
    body: >
      A memory-aware prompt has a clear structure.
    bullets:
      - "System: the long-term profile - what we durably know"
      - "Then: working-memory turns - the recent conversation"
      - "Last: the new user message"
      - "Order matters: standing context first, live turn last"
      - "Empty profile still builds a valid prompt"
    narration: >
      A memory-aware prompt has three layers. The system message carries the long-term
      profile - the durable facts that should color every reply. Then come the recent
      turns from working memory, giving the model the flow of the current
      conversation. Finally the new message. The order is deliberate: standing context
      up top, the live turn at the bottom, right where the model expects the thing it
      must respond to.

  - type: code
    label: "build_memory_prompt"
    heading: "Assemble the Layers"
    code: |
      def build_memory_prompt(message, working, longterm):
          facts = longterm.all()
          profile = "\\n".join("- " + f["key"] + ": " + f["value"] for f in facts)
          system = "\\n".join([
              "You are a helpful assistant with memory of the user.",
              "",
              "What you remember about the user:",
              profile if profile else "(nothing yet)",
          ])
          messages = [{"role": "system", "content": system}]
          messages.extend(working.turns())
          messages.append({"role": "user", "content": str(message)})
          return messages
    narration: >
      build_memory_prompt pulls the whole profile with longterm.all and renders it as
      a bullet list inside the system message. If there is nothing yet, it says so -
      an empty profile still produces a valid prompt, it just has no facts to lean on.
      Then it extends the message list with the working-memory turns and appends the
      new user message. One function, three layers, and the model now sees everything
      the agent remembers.

  - type: concept
    label: "Store and recall"
    heading: "The Full Memory Loop"
    body: >
      Memory is a two-way street.
    bullets:
      - "Store: extract durable facts -> remember (Lesson 3)"
      - "Recall: all() -> inject into the prompt (this lesson)"
      - "Working memory supplies the recent turns"
      - "Long-term memory supplies the standing profile"
      - "Both directions must work for memory to help"
    narration: >
      Step back and see the whole loop. On the way in, extraction decides what is
      durable and remember stores it. On the way out, recall reads the profile back
      and injects it into the prompt. Working memory feeds the recent turns; long-term
      memory feeds the standing profile. Both directions have to work: store without
      recall is a diary no one reads, and recall without store has nothing to show.
      The next lesson wires both into a single agent.

  - type: exercise
    heading: "Exercise 4: Recall - Injecting Memory"
    prompt: >
      Implement build_memory_prompt(message, working, longterm): render longterm.all()
      as '- key: value' lines (or '(nothing yet)') inside a system message; then
      working.turns(); then the new {'role':'user','content':message} last. Return the
      message list.
    hint: >
      profile = "\\n".join of '- key: value' over longterm.all(). messages = [system];
      messages.extend(working.turns()); messages.append(the user message). Return
      messages.
    narration: >
      This is recall - the step that actually puts memory in front of the model.

  - type: summary
    heading: "Lesson 4 Summary"
    bullets:
      - "Recall = inject stored memory back into the prompt"
      - "System = long-term profile; then recent turns; then new message"
      - "longterm.all() renders the standing profile"
      - "Empty profile still builds a valid prompt ('nothing yet')"
      - "Store + recall together make memory actually useful"
    narration: >
      Lesson 5 wires storage and recall into one MemoryAgent - the assistant that
      remembers you.
"""

_LESSON_05 = """\
day: "082"
lesson: 5
title: "MemoryAgent - The Assistant That Remembers You"
slides:
  - type: title
    heading: "MemoryAgent"
    subheading: "Extract, recall, answer, remember - every turn"
    narration: >
      Now we wire it all together. MemoryAgent binds a working memory, a long-term
      store, and a model, and on every turn it does the full loop: extract durable
      facts from the message, recall everything into the prompt, answer, and record
      the exchange. Same class shape as SimpleAgent, ReactAgent, and ToolAgent - only
      the engine inside is memory.

  - type: code
    label: "MemoryAgent"
    heading: "The Turn Loop"
    code: |
      class MemoryAgent:
          def __init__(self, longterm=None, llm_fn=None, max_turns=10):
              self.longterm = longterm if longterm is not None else LongTermMemory()
              self.working = WorkingMemory(max_turns=max_turns)
              self._llm_fn = llm_fn

          def chat(self, message):
              for key, value in extract_memories(message, llm_fn=self._llm_fn).items():
                  self.longterm.remember(key, value)
              prompt = build_memory_prompt(message, self.working, self.longterm)
              reply = call_llm(prompt, llm_fn=self._llm_fn)
              self.working.add("user", message)
              self.working.add("assistant", reply)
              return reply

          def end_session(self):
              self.working.clear()
    narration: >
      chat is the whole day in one method. First it extracts durable facts and remembers
      each one, so the store is up to date before we answer. Then build_memory_prompt
      recalls the profile and recent turns into a prompt, and call_llm answers. Finally
      it records both the user message and the reply into working memory for the next
      turn. Notice chat calls the model twice - once to judge what to remember, once to
      answer with memory in context - two focused prompts rather than one that tries to
      do both.

  - type: concept
    label: "Session boundary"
    heading: "End the Session, Keep the Knowledge"
    body: >
      A session boundary clears one memory, not the other.
    bullets:
      - "end_session(): clear working memory only"
      - "Long-term memory persists - it's in SQLite"
      - "Next session starts fresh but still knows you"
      - "A new agent on the same LongTermMemory remembers you"
      - "That split is the whole point of two memories"
    narration: >
      end_session is where the two memories part ways. It clears working memory, so the
      next conversation does not carry over the last one's turns - but it leaves
      long-term memory untouched, because those facts are in SQLite. Start a brand new
      agent pointed at the same long-term store and it already knows your name and your
      preferences, even though it has never seen this conversation. Fresh context,
      remembered knowledge - that split is exactly why an agent needs two kinds of
      memory.

  - type: concept
    label: "Four agents, one shape"
    heading: "The Section's Class Pattern, Again"
    body: >
      Every Section 6 agent wears the same skeleton.
    bullets:
      - "Day 79 SimpleAgent: bare action loop"
      - "Day 80 ReactAgent: reasoning loop with a trace"
      - "Day 81 ToolAgent: one-shot routing over many tools"
      - "Day 82 MemoryAgent: extract -> recall -> answer -> record"
      - "All: bind at construction, delegate, keep state"
    narration: >
      This is the fourth agent in four days with the same class shape: bind the
      collaborators at construction, delegate the real work to module functions, and
      keep some state. What changed today is the state - two memories instead of a
      history list - and the engine, which now stores and recalls around every model
      call. Keeping the shape constant means each new agent is easy to pick up; you
      spend your attention on the new idea, not the scaffolding.

  - type: exercise
    heading: "Exercise 5: MemoryAgent"
    prompt: >
      Implement MemoryAgent(longterm=None, llm_fn=None, max_turns=10): __init__ builds
      the two memories; chat extracts + remembers facts, build_memory_prompt, call_llm,
      records user + assistant turns, returns the reply; remember/recall/profile expose
      long-term memory; end_session clears working memory only.
    hint: >
      chat: for k,v in extract_memories(message, llm_fn=self._llm_fn).items():
      self.longterm.remember(k,v). prompt = build_memory_prompt(...); reply =
      call_llm(prompt, llm_fn=self._llm_fn); add both turns; return reply.
    narration: >
      This completes the assistant that remembers you - hand it a persistent
      LongTermMemory and it carries your profile across sessions.

  - type: summary
    heading: "Lesson 5 Summary - Day 82 Complete"
    bullets:
      - "MemoryAgent = extract -> recall -> answer -> record, every turn"
      - "chat calls the model twice: judge what to store, then answer"
      - "end_session clears working memory; long-term persists in SQLite"
      - "A new agent on the same store still remembers you"
      - "Same class shape as SimpleAgent / ReactAgent / ToolAgent"
    narration: >
      Your agent now has memory - short-term for coherence, long-term for continuity.
      Day 83 gives it foresight: planning and decomposition, breaking a big goal into
      an ordered set of subtasks.
"""

for i, content in enumerate([_LESSON_01, _LESSON_02, _LESSON_03,
                               _LESSON_04, _LESSON_05], start=1):
    (OUT / "lessons" / f"day_{DAY}_lesson_0{i}.yaml").write_text(content)

# ── PROJECT NOTEBOOK ──────────────────────────────────────────────────────────
PROJECT = nb([
    md(f"# Day {DAY} — Project: An Agent That Remembers You\n\n"
       "## Objective\n\n"
       "Build `memory_agent.py` — an assistant that remembers you within a "
       "conversation *and* across sessions.\n\n"
       "## Deliverable\n\n"
       "`memory_agent.py` with:\n\n"
       "- `WorkingMemory` — bounded short-term turn log "
       "(`add/turns/render/clear/__len__`)\n"
       "- `LongTermMemory` — durable SQLite key/value store "
       "(`remember/recall/search/all/forget/__len__/close`)\n"
       "- `build_extraction_prompt(message)` / `extract_memories(message, llm_fn=None)`\n"
       "- `build_memory_prompt(message, working, longterm)`\n"
       "- `MemoryAgent(longterm=None, llm_fn=None, max_turns=10)` with "
       "`chat/remember/recall/profile/end_session`\n\n"
       "## Usage (with Ollama running + llama3.2 pulled)\n\n"
       "```python\n"
       "from memory_agent import MemoryAgent, LongTermMemory\n"
       "mem = LongTermMemory('user.db')          # persists across runs\n"
       "agent = MemoryAgent(longterm=mem)\n"
       "agent.chat(\"Hi, I'm Kutlwano and I love SQL.\")\n"
       "print(agent.chat('What do you know about me?'))\n"
       "```\n\n"
       "**The deliverable:** you run it, tell it something about yourself, end the "
       "session — and a fresh agent on the same `LongTermMemory` still knows you. "
       "Short-term memory keeps the conversation coherent; long-term memory carries "
       "your profile across sessions."),
    code("# Your implementation here — build memory_agent.py\n"),
])
save(OUT / "project" / "project.ipynb", PROJECT)

# ── SOLUTION NOTEBOOK ─────────────────────────────────────────────────────────
_SOL_CELL1 = (
    f"_SRC = {repr(_MEMORY_AGENT_SRC)}\n"
    "from pathlib import Path\n"
    "Path('memory_agent.py').write_text(_SRC, encoding='utf-8')\n"
    "print('memory_agent.py written.')"
)

_SOL_CELL2 = r"""
import os, tempfile, json
from memory_agent import (
    WorkingMemory, LongTermMemory, build_extraction_prompt, extract_memories,
    build_memory_prompt, MemoryAgent,
)

def _mock_llm(facts=None, reply='Sure!'):
    payload = json.dumps(facts or {})
    def _fn(messages):
        system = messages[0]['content'] if messages else ''
        return payload if 'extract' in system.lower() else reply
    return _fn

# 1. WorkingMemory
wm = WorkingMemory(max_turns=3)
wm.add('user', 'hi').add('assistant', 'hello')
assert len(wm) == 2 and wm.turns()[0] == {'role': 'user', 'content': 'hi'}
for i in range(5):
    wm.add('user', str(i))
assert len(wm) == 3 and wm.turns()[0]['content'] == '2'   # bounded
print("✅ WorkingMemory (bounded, copy, clear)")

# 2. LongTermMemory
lt = LongTermMemory()
lt.remember('name', 'Kutlwano').remember('lang', 'Python')
assert lt.recall('name') == 'Kutlwano' and lt.recall('missing') is None
lt.remember('name', 'Kutlwano M.')
assert lt.recall('name') == 'Kutlwano M.' and len(lt) == 2   # upsert
assert lt.search('python')[0]['key'] == 'lang'
lt.forget('lang'); assert lt.recall('lang') is None
path = tempfile.NamedTemporaryFile(suffix='.db', delete=False).name
try:
    a = LongTermMemory(path); a.remember('goal', 'ship agents'); a.close()
    assert LongTermMemory(path).recall('goal') == 'ship agents'   # persists
finally:
    os.unlink(path)
print("✅ LongTermMemory (SQLite upsert / search / forget / persistence)")

# 3. extract_memories
msgs = build_extraction_prompt('I am Kutlwano')
assert 'extract' in msgs[0]['content'].lower()
assert extract_memories('x', llm_fn=_mock_llm(facts={'name': 'K'})) == {'name': 'K'}
assert extract_memories('x', llm_fn=lambda m: 'no json') == {}       # never raises
print("✅ extract_memories (LLM-driven, safe fallback)")

# 4. build_memory_prompt
lt2 = LongTermMemory(); lt2.remember('name', 'Kutlwano')
p = build_memory_prompt('hello', WorkingMemory(), lt2)
assert p[0]['role'] == 'system' and 'name: Kutlwano' in p[0]['content']
assert p[-1] == {'role': 'user', 'content': 'hello'}
assert 'nothing yet' in build_memory_prompt('hi', WorkingMemory(), LongTermMemory())[0]['content']
print("✅ build_memory_prompt (profile in system, message last)")

# 5. MemoryAgent
agent = MemoryAgent(llm_fn=_mock_llm(facts={'name': 'Kutlwano'}, reply='Hi Kutlwano!'))
assert agent.chat('I am Kutlwano') == 'Hi Kutlwano!'
assert agent.recall('name') == 'Kutlwano' and len(agent.working) == 2
agent.remember('lang', 'Python')
assert {'key': 'lang', 'value': 'Python'} in agent.profile()
agent.end_session()
assert len(agent.working) == 0 and agent.recall('name') == 'Kutlwano'   # long-term kept
fresh = MemoryAgent(longterm=agent.longterm, llm_fn=_mock_llm(reply='ok'))
assert fresh.recall('name') == 'Kutlwano'   # a new agent still remembers you
print("✅ MemoryAgent (extract / recall / persist across sessions)")

print("\nAgent memory complete!")
"""

SOLUTION = nb([
    md(f"# Day {DAY} — Solution: An Agent That Remembers You"),
    code(_SOL_CELL1),
    code(_SOL_CELL2),
])
save(OUT / "project" / "solution" / "solution.ipynb", SOLUTION)
(OUT / "project" / "solution" / "memory_agent.py").write_text(_MEMORY_AGENT_SRC)

print(f"Day {DAY} notebooks written to {OUT}")
print("  lessons/    day_082_lesson_01.yaml – lesson_05.yaml")
print("  exercises/  exercise_01 – exercise_05")
print("  project/    project.ipynb")
print("  project/solution/  solution.ipynb + memory_agent.py")
