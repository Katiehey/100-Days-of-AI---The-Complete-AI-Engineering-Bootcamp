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
        return "\n".join(t["role"] + ": " + t["content"] for t in self._turns)

    def clear(self):
        """Forget the session (end-of-session boundary)."""
        self._turns.clear()

    def __len__(self):
        return len(self._turns)

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

# ── deciding what is worth remembering (LLM-driven) ──────────────────────────
def build_extraction_prompt(message):
    """Ask the model which durable facts about the user to store long-term."""
    system = "\n".join([
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

# ── recall: injecting memory into the prompt ─────────────────────────────────
def build_memory_prompt(message, working, longterm):
    """Build a chat prompt that injects long-term profile + short-term turns.

    The system message carries what we durably know about the user; the recent
    working-memory turns follow; the new message comes last.
    """
    facts = longterm.all()
    profile = "\n".join("- " + f["key"] + ": " + f["value"] for f in facts)
    system = "\n".join([
        "You are a helpful assistant with memory of the user.",
        "",
        "What you remember about the user:",
        profile if profile else "(nothing yet)",
    ])
    messages = [{"role": "system", "content": system}]
    messages.extend(working.turns())
    messages.append({"role": "user", "content": str(message)})
    return messages

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
