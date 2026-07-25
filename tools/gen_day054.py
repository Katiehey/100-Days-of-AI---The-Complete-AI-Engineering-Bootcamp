#!/usr/bin/env python3
"""Generate all Day 054 notebooks: exercises 1-5, project, solution.

Day 054 — Databases for Apps. Deliverable: a chat backend with saved state.

Builds on Day 44 (SQLAlchemy 2.x ORM). New here: relationships between tables
(Conversation 1--* Message), file-backed persistence that survives a restart,
a lightweight idempotent migration, and a ChatStore persistence facade.

Gate note: the ORM models are PROVIDED (not a student implementation target) —
redefining a mapped class on the same Base raises 'table already defined', and
the gate runs both the stub cell and the injected solution cell. So exercises
build the repository/facade layer over the provided models.
"""
import json
from pathlib import Path

ROOT    = Path(__file__).resolve().parent.parent
DAY_DIR = ROOT / "04_real_apps" / "day_054"

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
# Shared setup: imports + the provided ORM models
# ---------------------------------------------------------------------------

SETUP_IMPORTS = '''import warnings
warnings.filterwarnings('ignore')
import os
import tempfile
from datetime import datetime
from sqlalchemy import create_engine, ForeignKey, select, inspect as sa_inspect, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session
from sqlalchemy.pool import StaticPool'''


MODELS_ONLY = '''class Base(DeclarativeBase):
    pass


class Conversation(Base):
    """One chat conversation. Has many Messages (one-to-many)."""
    __tablename__ = 'conversations'

    id:         Mapped[int]      = mapped_column(primary_key=True)
    title:      Mapped[str]      = mapped_column(default='New chat')
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # relationship() is the ORM link (not a DB column). cascade deletes a
    # conversation's messages when the conversation is deleted.
    messages: Mapped[list['Message']] = relationship(
        back_populates='conversation', cascade='all, delete-orphan')


class Message(Base):
    """One message in a conversation. Belongs to one Conversation (many-to-one)."""
    __tablename__ = 'messages'

    id:              Mapped[int]      = mapped_column(primary_key=True)
    conversation_id: Mapped[int]      = mapped_column(ForeignKey('conversations.id'))
    role:            Mapped[str]      = mapped_column()
    content:         Mapped[str]      = mapped_column()
    created_at:      Mapped[datetime] = mapped_column(default=datetime.utcnow)

    conversation: Mapped['Conversation'] = relationship(back_populates='messages')'''


MEMORY_ENGINE = '''def memory_engine():
    """In-memory SQLite engine for tests. StaticPool makes every Session share the
    one in-memory database (see Day 44)."""
    return create_engine('sqlite:///:memory:',
                          connect_args={'check_same_thread': False},
                          poolclass=StaticPool)'''


SETUP = SETUP_IMPORTS + "\n\n\n" + MODELS_ONLY + "\n\n\n" + MEMORY_ENGINE


# ---------------------------------------------------------------------------
# Repository / facade implementations (the student build targets)
# ---------------------------------------------------------------------------

CREATE_SCHEMA_IMPL = '''def create_schema(engine) -> None:
    """Create every table registered on Base (CREATE TABLE IF NOT EXISTS)."""
    Base.metadata.create_all(engine)


def create_conversation(session, title: str = 'New chat') -> Conversation:
    """Insert a new conversation and flush so its auto id is assigned.
    The caller controls commit (unit-of-work pattern)."""
    conv = Conversation(title=title)
    session.add(conv)
    session.flush()
    return conv'''


ADD_MESSAGE_IMPL = '''def add_message(session, conversation_id: int, role: str, content: str) -> Message:
    """Append a message to a conversation via its foreign key, and flush to assign
    the id. The caller commits."""
    msg = Message(conversation_id=conversation_id, role=role, content=content)
    session.add(msg)
    session.flush()
    return msg'''


QUERIES_IMPL = '''def get_messages(session, conversation_id: int) -> list:
    """Return the conversation's messages, in insertion order, as plain
    [{'role', 'content'}] dicts (safe to use after the session closes)."""
    stmt = (select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.id))
    rows = session.execute(stmt).scalars().all()
    return [{'role': m.role, 'content': m.content} for m in rows]


def list_conversations(session) -> list:
    """Return all conversations as [{'id', 'title', 'message_count'}] by id."""
    convs = session.execute(
        select(Conversation).order_by(Conversation.id)).scalars().all()
    return [{'id': c.id, 'title': c.title, 'message_count': len(c.messages)}
            for c in convs]'''


PERSIST_IMPL = '''def make_engine(db_path: str):
    """File-backed SQLite engine — data SURVIVES a process restart. Creates the
    schema on first use (safe to call every startup)."""
    engine = create_engine(f'sqlite:///{db_path}')
    Base.metadata.create_all(engine)
    return engine


def column_exists(engine, table: str, column: str) -> bool:
    """True if `column` already exists on `table` (schema introspection)."""
    return column in [c['name'] for c in sa_inspect(engine).get_columns(table)]


def migrate_add_column(engine, table: str, column: str, sqltype: str = 'TEXT') -> bool:
    """A minimal, idempotent migration: add a column only if it is missing.
    Returns True if it added the column, False if it was already there.
    Safe to run on every startup — this is the essence of a migration."""
    if column_exists(engine, table, column):
        return False
    with engine.begin() as conn:
        conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} {sqltype}'))
    return True'''


CHATSTORE_IMPL = '''class ChatStore:
    """Persistence facade for the chat app. One file-backed database; each method
    opens a short-lived Session and commits atomically. The app calls these
    methods and never touches SQL — the same thin-shell pattern as the earlier
    days, now over a database."""

    def __init__(self, db_path: str):
        self.engine = make_engine(db_path)

    def start(self, title: str = 'New chat') -> int:
        with Session(self.engine) as s:
            conv = create_conversation(s, title)
            s.commit()
            return conv.id

    def append(self, conversation_id: int, role: str, content: str) -> int:
        with Session(self.engine) as s:
            msg = add_message(s, conversation_id, role, content)
            s.commit()
            return msg.id

    def history(self, conversation_id: int) -> list:
        with Session(self.engine) as s:
            return get_messages(s, conversation_id)

    def conversations(self) -> list:
        with Session(self.engine) as s:
            return list_conversations(s)'''


# Cumulative provided stacks
_BEFORE_EX02 = SETUP + "\n\n\n" + CREATE_SCHEMA_IMPL
_BEFORE_EX03 = _BEFORE_EX02 + "\n\n\n" + ADD_MESSAGE_IMPL
_BEFORE_EX04 = _BEFORE_EX03 + "\n\n\n" + QUERIES_IMPL
_BEFORE_EX05 = _BEFORE_EX04 + "\n\n\n" + PERSIST_IMPL
_ALL_REPO    = "\n\n\n".join([CREATE_SCHEMA_IMPL, ADD_MESSAGE_IMPL,
                               QUERIES_IMPL, PERSIST_IMPL])


# ---------------------------------------------------------------------------
# Deliverable: a persistent chat backend (backend.py)
# ---------------------------------------------------------------------------

BACKEND_PY_SRC = (
    "import warnings\n"
    "warnings.filterwarnings('ignore')\n"
    "from datetime import datetime\n"
    "from fastapi import FastAPI\n"
    "from pydantic import BaseModel, Field\n"
    "from sqlalchemy import create_engine, ForeignKey, select, inspect as sa_inspect, text\n"
    "from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session\n"
    "import ollama\n\n\n"
    + MODELS_ONLY + "\n\n\n"
    + _ALL_REPO + "\n\n\n"
    + CHATSTORE_IMPL + "\n\n\n"
    "class ConversationIn(BaseModel):\n"
    "    title: str = 'New chat'\n\n\n"
    "class MessageIn(BaseModel):\n"
    "    message: str = Field(min_length=1)\n\n\n"
    "store = ChatStore('chat.db')\n"
    "app = FastAPI(title='Persistent Chat API')\n\n\n"
    "@app.post('/conversations')\n"
    "def create_conv(req: ConversationIn):\n"
    "    return {'id': store.start(req.title)}\n\n\n"
    "@app.get('/conversations')\n"
    "def list_convs():\n"
    "    return {'conversations': store.conversations()}\n\n\n"
    "@app.get('/conversations/{cid}/messages')\n"
    "def get_history(cid: int):\n"
    "    return {'messages': store.history(cid)}\n\n\n"
    "@app.post('/conversations/{cid}/messages')\n"
    "def post_message(cid: int, req: MessageIn):\n"
    "    store.append(cid, 'user', req.message)\n"
    "    history = store.history(cid)          # full saved history each turn\n"
    "    try:\n"
    "        resp = ollama.chat(model='llama3.2', messages=history)\n"
    "        reply = resp['message']['content'].strip()\n"
    "    except Exception as e:\n"
    "        reply = f'[Model unavailable: {e}]'\n"
    "    store.append(cid, 'assistant', reply)\n"
    "    return {'reply': reply}\n\n\n"
    "if __name__ == '__main__':\n"
    "    import uvicorn\n"
    "    uvicorn.run(app, host='0.0.0.0', port=8000)\n"
)

WRITE_BACKEND_CELL = (
    "from pathlib import Path\n"
    "\n"
    "# The persistent chat backend: models + repository + ChatStore + FastAPI\n"
    "# routes, embedded as a string so the notebook can write it verbatim.\n"
    "_BACKEND_SRC = " + repr(BACKEND_PY_SRC) + "\n"
    "\n"
    "\n"
    "def write_backend(path: str = 'backend.py') -> str:\n"
    '    """Write the persistent chat backend to `path` and return the path."""\n'
    "    Path(path).write_text(_BACKEND_SRC, encoding='utf-8')\n"
    "    return path"
)


# ---------------------------------------------------------------------------
# Exercise 01 — schema + create_conversation
# ---------------------------------------------------------------------------

def ex01():
    global _cid; _cid = 0
    return [
        md(
            "# Day 054 — Exercise 1: Schema & Creating Conversations\n\n"
            "**What you'll build:** `create_schema(engine)` and "
            "`create_conversation(session, title)` over the provided `Conversation` "
            "and `Message` models (a one-to-many relationship).\n\n"
            "**Why it matters:** So far the chat app forgot everything on restart. "
            "Today it gets a database. The models define two related tables — a "
            "`Conversation` has many `Message`s — and `create_schema` builds them. "
            "`create_conversation` inserts a row and flushes so the database assigns "
            "its primary key. This is the foundation of saved state."
        ),
        md("## Provided: Setup + Models (Conversation 1--* Message)"),
        code(SETUP),
        md("## Your Implementation"),
        code(
            "def create_schema(engine) -> None:\n"
            '    """Create every table registered on Base."""\n'
            "    # TODO: Base.metadata.create_all(engine)\n"
            "    pass\n"
            "\n"
            "\n"
            "def create_conversation(session, title: str = 'New chat') -> Conversation:\n"
            '    """Insert a Conversation, flush to assign its id, and return it.\n'
            "    The caller commits.\"\"\"\n"
            "    # TODO: conv = Conversation(title=title)\n"
            "    # TODO: session.add(conv)\n"
            "    # TODO: session.flush()   # assigns conv.id without committing\n"
            "    # TODO: return conv\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    engine = memory_engine()\n"
            "\n"
            "    # Check 1: create_schema builds both tables\n"
            "    try:\n"
            "        create_schema(engine)\n"
            "        tables = set(sa_inspect(engine).get_table_names())\n"
            "        assert {'conversations', 'messages'} <= tables, f'missing tables: {tables}'\n"
            "        passed += 1; print('✅ Check 1: create_schema builds conversations + messages')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: create_conversation assigns an id after flush\n"
            "    try:\n"
            "        with Session(engine) as s:\n"
            "            conv = create_conversation(s, 'My first chat')\n"
            "            assert conv.id is not None, 'id should be assigned after flush'\n"
            "            s.commit()\n"
            "        passed += 1; print('✅ Check 2: create_conversation assigns an id')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 2: {e}')\n"
            "\n"
            "    # Check 3: title is stored\n"
            "    try:\n"
            "        with Session(engine) as s:\n"
            "            conv = create_conversation(s, 'Weather bot')\n"
            "            s.commit()\n"
            "            assert conv.title == 'Weather bot', f'title not stored: {conv.title}'\n"
            "        passed += 1; print('✅ Check 3: title is persisted')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 3: {e}')\n"
            "\n"
            "    # Check 4: default title + created_at timestamp\n"
            "    try:\n"
            "        with Session(engine) as s:\n"
            "            conv = create_conversation(s)\n"
            "            s.commit()\n"
            "            assert conv.title == 'New chat', f'default title wrong: {conv.title}'\n"
            "            assert isinstance(conv.created_at, datetime), 'created_at should be a datetime'\n"
            "        passed += 1; print('✅ Check 4: default title + created_at set')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 4: {e}')\n"
            "\n"
            "    # Check 5: distinct conversations get distinct ids\n"
            "    try:\n"
            "        with Session(engine) as s:\n"
            "            a = create_conversation(s, 'A')\n"
            "            b = create_conversation(s, 'B')\n"
            "            s.commit()\n"
            "            assert a.id != b.id, 'ids must be unique'\n"
            "        passed += 1; print('✅ Check 5: each conversation gets a unique id')\n"
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
            + CREATE_SCHEMA_IMPL + "\n"
            "```\n\n"
            "**Why this works:** `Base.metadata.create_all(engine)` emits `CREATE "
            "TABLE IF NOT EXISTS` for every model registered on `Base` — both tables "
            "at once. `create_conversation` adds the object and calls `session.flush()`, "
            "which sends the INSERT and lets the database assign the auto-increment "
            "`id` — without committing. Returning the object with its id lets the "
            "caller attach messages to it. The caller owns the commit, so several "
            "operations can share one transaction.\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 02 — add_message (the foreign key + relationship)
# ---------------------------------------------------------------------------

def ex02():
    global _cid; _cid = 100
    return [
        md(
            "# Day 054 — Exercise 2: Linking Messages to Conversations\n\n"
            "**What you'll build:** `add_message(session, conversation_id, role, "
            "content)` — insert a message that belongs to a conversation through its "
            "**foreign key**.\n\n"
            "**Why it matters:** A message is meaningless without its conversation. "
            "The `conversation_id` foreign key is the database-level link; the "
            "`relationship()` on the models turns that link into Python — "
            "`conversation.messages` gives you the list. `add_message` is how the app "
            "saves each turn of a chat."
        ),
        md("## Provided: Setup + Models + create_schema/create_conversation"),
        code(_BEFORE_EX02),
        md("## Your Implementation"),
        code(
            "def add_message(session, conversation_id: int, role: str, content: str) -> Message:\n"
            '    """Insert a Message linked to conversation_id via its foreign key,\n'
            "    flush to assign the id, and return it.\"\"\"\n"
            "    # TODO: msg = Message(conversation_id=conversation_id, role=role, content=content)\n"
            "    # TODO: session.add(msg)\n"
            "    # TODO: session.flush()\n"
            "    # TODO: return msg\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    engine = memory_engine()\n"
            "    create_schema(engine)\n"
            "\n"
            "    # Check 1: add_message assigns an id and the foreign key\n"
            "    try:\n"
            "        with Session(engine) as s:\n"
            "            conv = create_conversation(s, 'chat')\n"
            "            msg = add_message(s, conv.id, 'user', 'hello')\n"
            "            s.commit()\n"
            "            assert msg.id is not None, 'message id should be assigned'\n"
            "            assert msg.conversation_id == conv.id, 'foreign key not set'\n"
            "        passed += 1; print('✅ Check 1: message linked via conversation_id')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: the relationship exposes the message on the conversation\n"
            "    try:\n"
            "        with Session(engine) as s:\n"
            "            conv = create_conversation(s, 'chat2')\n"
            "            add_message(s, conv.id, 'user', 'hi there')\n"
            "            s.commit()\n"
            "            reloaded = s.get(Conversation, conv.id)\n"
            "            assert len(reloaded.messages) == 1, f'expected 1 message, got {len(reloaded.messages)}'\n"
            "            assert reloaded.messages[0].content == 'hi there'\n"
            "        passed += 1; print('✅ Check 2: conversation.messages reflects the insert')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 2: {e}')\n"
            "\n"
            "    # Check 3: role and content are stored\n"
            "    try:\n"
            "        with Session(engine) as s:\n"
            "            conv = create_conversation(s, 'chat3')\n"
            "            m = add_message(s, conv.id, 'assistant', 'the answer is 42')\n"
            "            s.commit()\n"
            "            assert m.role == 'assistant' and m.content == 'the answer is 42'\n"
            "        passed += 1; print('✅ Check 3: role + content stored')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 3: {e}')\n"
            "\n"
            "    # Check 4: multiple messages accumulate on one conversation\n"
            "    try:\n"
            "        with Session(engine) as s:\n"
            "            conv = create_conversation(s, 'chat4')\n"
            "            add_message(s, conv.id, 'user', 'a')\n"
            "            add_message(s, conv.id, 'assistant', 'b')\n"
            "            add_message(s, conv.id, 'user', 'c')\n"
            "            s.commit()\n"
            "            reloaded = s.get(Conversation, conv.id)\n"
            "            assert len(reloaded.messages) == 3, f'expected 3, got {len(reloaded.messages)}'\n"
            "        passed += 1; print('✅ Check 4: multiple messages accumulate')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 4: {e}')\n"
            "\n"
            "    # Check 5: messages of different conversations stay separate\n"
            "    try:\n"
            "        with Session(engine) as s:\n"
            "            c1 = create_conversation(s, 'one')\n"
            "            c2 = create_conversation(s, 'two')\n"
            "            add_message(s, c1.id, 'user', 'in one')\n"
            "            add_message(s, c2.id, 'user', 'in two')\n"
            "            s.commit()\n"
            "            assert len(s.get(Conversation, c1.id).messages) == 1\n"
            "            assert len(s.get(Conversation, c2.id).messages) == 1\n"
            "        passed += 1; print('✅ Check 5: conversations keep separate messages')\n"
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
            + ADD_MESSAGE_IMPL + "\n"
            "```\n\n"
            "**Why this works:** Setting `conversation_id` on the `Message` writes the "
            "foreign key that links the two rows in the database. Because the models "
            "declare a `relationship()` with `back_populates`, SQLAlchemy keeps the "
            "Python side in sync too: after the insert, `conversation.messages` "
            "includes the new message. One insert, two views of the same link — the "
            "row-level FK and the object-level list.\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 03 — queries
# ---------------------------------------------------------------------------

def ex03():
    global _cid; _cid = 200
    return [
        md(
            "# Day 054 — Exercise 3: Reading the Data Back\n\n"
            "**What you'll build:** `get_messages(session, conversation_id)` returning "
            "ordered `[{'role','content'}]` dicts, and `list_conversations(session)` "
            "returning `[{'id','title','message_count'}]`.\n\n"
            "**Why it matters:** Saving is half the story — the app has to read state "
            "back to rebuild a chat. `get_messages` returns plain dicts (safe to use "
            "after the session closes, and ready to feed straight to the model). "
            "`list_conversations` powers a sidebar of past chats."
        ),
        md("## Provided: Setup + Models + create/add helpers"),
        code(_BEFORE_EX03),
        md("## Your Implementation"),
        code(
            "def get_messages(session, conversation_id: int) -> list:\n"
            '    """Return the conversation\'s messages in insertion order as\n'
            "    [{'role', 'content'}] dicts.\"\"\"\n"
            "    # TODO: stmt = (select(Message)\n"
            "    #                .where(Message.conversation_id == conversation_id)\n"
            "    #                .order_by(Message.id))\n"
            "    # TODO: rows = session.execute(stmt).scalars().all()\n"
            "    # TODO: return [{'role': m.role, 'content': m.content} for m in rows]\n"
            "    pass\n"
            "\n"
            "\n"
            "def list_conversations(session) -> list:\n"
            '    """Return [{\'id\', \'title\', \'message_count\'}] for all conversations, by id."""\n'
            "    # TODO: convs = session.execute(select(Conversation).order_by(Conversation.id)).scalars().all()\n"
            "    # TODO: return [{'id': c.id, 'title': c.title, 'message_count': len(c.messages)} for c in convs]\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    engine = memory_engine()\n"
            "    create_schema(engine)\n"
            "    with Session(engine) as s:\n"
            "        conv = create_conversation(s, 'demo')\n"
            "        add_message(s, conv.id, 'user', 'first')\n"
            "        add_message(s, conv.id, 'assistant', 'second')\n"
            "        add_message(s, conv.id, 'user', 'third')\n"
            "        s.commit()\n"
            "        cid = conv.id\n"
            "\n"
            "    # Check 1: get_messages returns a list of role/content dicts\n"
            "    try:\n"
            "        with Session(engine) as s:\n"
            "            msgs = get_messages(s, cid)\n"
            "        assert isinstance(msgs, list) and all(set(m) == {'role', 'content'} for m in msgs), \\\n"
            "            f'expected role/content dicts, got {msgs}'\n"
            "        passed += 1; print('✅ Check 1: get_messages -> [{role, content}]')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: messages come back in insertion order\n"
            "    try:\n"
            "        with Session(engine) as s:\n"
            "            msgs = get_messages(s, cid)\n"
            "        assert [m['content'] for m in msgs] == ['first', 'second', 'third'], f'order wrong: {msgs}'\n"
            "        passed += 1; print('✅ Check 2: messages ordered by insertion')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 2: {e}')\n"
            "\n"
            "    # Check 3: unknown conversation -> empty list (no crash)\n"
            "    try:\n"
            "        with Session(engine) as s:\n"
            "            assert get_messages(s, 9999) == [], 'unknown conversation should give []'\n"
            "        passed += 1; print('✅ Check 3: unknown conversation -> []')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 3: {e}')\n"
            "\n"
            "    # Check 4: list_conversations returns id/title/message_count\n"
            "    try:\n"
            "        with Session(engine) as s:\n"
            "            convs = list_conversations(s)\n"
            "        assert convs and set(convs[0]) == {'id', 'title', 'message_count'}, f'bad shape: {convs}'\n"
            "        passed += 1; print('✅ Check 4: list_conversations -> [{id, title, message_count}]')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 4: {e}')\n"
            "\n"
            "    # Check 5: message_count is correct\n"
            "    try:\n"
            "        with Session(engine) as s:\n"
            "            convs = list_conversations(s)\n"
            "        row = [c for c in convs if c['id'] == cid][0]\n"
            "        assert row['message_count'] == 3, f\"expected 3, got {row['message_count']}\"\n"
            "        passed += 1; print('✅ Check 5: message_count matches')\n"
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
            + QUERIES_IMPL + "\n"
            "```\n\n"
            "**Why this works:** `select(Message).where(...).order_by(Message.id)` is "
            "the SQLAlchemy 2.x query from Day 44, now filtered by the foreign key and "
            "ordered. Converting rows to plain dicts *inside* the session means the "
            "result is detached data the caller can use anywhere — no lazy-load errors "
            "after the session closes. `list_conversations` reads each conversation's "
            "`messages` relationship for the count, giving the sidebar everything it "
            "needs in one call.\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 04 — file persistence + migration
# ---------------------------------------------------------------------------

def ex04():
    global _cid; _cid = 300
    return [
        md(
            "# Day 054 — Exercise 4: Persistence & Migrations\n\n"
            "**What you'll build:** `make_engine(db_path)` (a **file-backed** engine "
            "whose data survives a restart), `column_exists(engine, table, column)`, "
            "and `migrate_add_column(engine, table, column, sqltype)` — a minimal, "
            "idempotent migration.\n\n"
            "**Why it matters:** In-memory data vanishes when the process ends. A "
            "**file-backed** database is what gives the app *saved state*. And as the "
            "app evolves, its schema changes — a migration adds a column to an existing "
            "database without destroying the data already in it."
        ),
        md("## Provided: Setup + Models + repository functions"),
        code(_BEFORE_EX04),
        md("## Your Implementation"),
        code(
            "def make_engine(db_path: str):\n"
            '    """File-backed SQLite engine; create the schema. Data survives restarts."""\n'
            "    # TODO: engine = create_engine(f'sqlite:///{db_path}')\n"
            "    # TODO: Base.metadata.create_all(engine)\n"
            "    # TODO: return engine\n"
            "    pass\n"
            "\n"
            "\n"
            "def column_exists(engine, table: str, column: str) -> bool:\n"
            '    """True if `column` already exists on `table`."""\n'
            "    # TODO: return column in [c['name'] for c in sa_inspect(engine).get_columns(table)]\n"
            "    pass\n"
            "\n"
            "\n"
            "def migrate_add_column(engine, table: str, column: str, sqltype: str = 'TEXT') -> bool:\n"
            '    """Add the column only if missing. Return True if added, False if it existed."""\n'
            "    # TODO: if column_exists(engine, table, column): return False\n"
            "    # TODO: with engine.begin() as conn:\n"
            "    #     conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} {sqltype}'))\n"
            "    # TODO: return True\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    db_dir = tempfile.mkdtemp()\n"
            "    db_path = os.path.join(db_dir, 'app.db')\n"
            "\n"
            "    # Check 1: make_engine creates a real file with the schema\n"
            "    try:\n"
            "        engine = make_engine(db_path)\n"
            "        assert os.path.exists(db_path), 'database file was not created'\n"
            "        assert {'conversations', 'messages'} <= set(sa_inspect(engine).get_table_names())\n"
            "        passed += 1; print('✅ Check 1: make_engine creates a file-backed schema')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: data SURVIVES a restart (new engine, same file)\n"
            "    try:\n"
            "        with Session(engine) as s:\n"
            "            conv = create_conversation(s, 'persisted')\n"
            "            add_message(s, conv.id, 'user', 'remember me')\n"
            "            s.commit()\n"
            "            cid = conv.id\n"
            "        engine.dispose()                      # simulate shutdown\n"
            "        engine2 = make_engine(db_path)        # simulate restart\n"
            "        with Session(engine2) as s:\n"
            "            msgs = get_messages(s, cid)\n"
            "        assert msgs == [{'role': 'user', 'content': 'remember me'}], f'data lost: {msgs}'\n"
            "        passed += 1; print('✅ Check 2: data survives a restart (file-backed)')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 2: {e}')\n"
            "\n"
            "    # Check 3: column_exists reports existing vs missing columns\n"
            "    try:\n"
            "        assert column_exists(engine2, 'conversations', 'title') is True\n"
            "        assert column_exists(engine2, 'conversations', 'pinned') is False\n"
            "        passed += 1; print('✅ Check 3: column_exists is accurate')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 3: {e}')\n"
            "\n"
            "    # Check 4: migrate_add_column adds a new column\n"
            "    try:\n"
            "        added = migrate_add_column(engine2, 'conversations', 'pinned', 'INTEGER')\n"
            "        assert added is True, 'first migration should add the column (True)'\n"
            "        assert column_exists(engine2, 'conversations', 'pinned') is True\n"
            "        passed += 1; print('✅ Check 4: migrate_add_column adds the column')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 4: {e}')\n"
            "\n"
            "    # Check 5: the migration is idempotent (safe to re-run)\n"
            "    try:\n"
            "        again = migrate_add_column(engine2, 'conversations', 'pinned', 'INTEGER')\n"
            "        assert again is False, 'second run should be a no-op (False)'\n"
            "        passed += 1; print('✅ Check 5: migration is idempotent')\n"
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
            + PERSIST_IMPL + "\n"
            "```\n\n"
            "**Why this works:** `sqlite:///{db_path}` points the engine at a file "
            "instead of memory, so the data is on disk and outlives the process — that "
            "is *saved state*. `column_exists` introspects the live schema. "
            "`migrate_add_column` checks first and only issues `ALTER TABLE ADD COLUMN` "
            "when needed, so running it on every startup is safe: it upgrades an old "
            "database once and does nothing thereafter. That check-then-change pattern "
            "is the heart of every migration (production apps use Alembic to manage "
            "many of them in order).\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 05 — ChatStore facade
# ---------------------------------------------------------------------------

def ex05():
    global _cid; _cid = 400
    return [
        md(
            "# Day 054 — Exercise 5: The ChatStore Facade\n\n"
            "**What you'll build:** `ChatStore(db_path)` — the app's persistence "
            "facade. Methods: `start(title)`, `append(conversation_id, role, content)`, "
            "`history(conversation_id)`, `conversations()`.\n\n"
            "**Why it matters:** The app shouldn't sprinkle sessions and commits "
            "through its handlers. `ChatStore` hides all of that behind four verbs, "
            "each opening a short session and committing atomically. The backend calls "
            "`store.append(...)` and `store.history(...)` — clean, and its data lives "
            "in a file that survives every restart."
        ),
        md("## Provided: Setup + Models + all repository functions"),
        code(_BEFORE_EX05),
        md("## Your Implementation"),
        code(
            "class ChatStore:\n"
            '    """Persistence facade: one file-backed DB, a short Session per method."""\n'
            "\n"
            "    def __init__(self, db_path: str):\n"
            "        # TODO: self.engine = make_engine(db_path)\n"
            "        pass\n"
            "\n"
            "    def start(self, title: str = 'New chat') -> int:\n"
            "        # TODO: with Session(self.engine) as s:\n"
            "        #     conv = create_conversation(s, title); s.commit(); return conv.id\n"
            "        pass\n"
            "\n"
            "    def append(self, conversation_id: int, role: str, content: str) -> int:\n"
            "        # TODO: with Session(self.engine) as s:\n"
            "        #     msg = add_message(s, conversation_id, role, content); s.commit(); return msg.id\n"
            "        pass\n"
            "\n"
            "    def history(self, conversation_id: int) -> list:\n"
            "        # TODO: with Session(self.engine) as s:\n"
            "        #     return get_messages(s, conversation_id)\n"
            "        pass\n"
            "\n"
            "    def conversations(self) -> list:\n"
            "        # TODO: with Session(self.engine) as s:\n"
            "        #     return list_conversations(s)\n"
            "        pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    db_path = os.path.join(tempfile.mkdtemp(), 'store.db')\n"
            "\n"
            "    # Check 1: ChatStore exposes the four methods\n"
            "    try:\n"
            "        assert 'ChatStore' in globals()\n"
            "        for m in ('start', 'append', 'history', 'conversations'):\n"
            "            assert hasattr(ChatStore, m), f'missing method: {m}'\n"
            "        store = ChatStore(db_path)\n"
            "        passed += 1; print('✅ Check 1: ChatStore has start/append/history/conversations')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: start returns an int id; append works\n"
            "    try:\n"
            "        cid = store.start('Session A')\n"
            "        assert isinstance(cid, int), f'start must return an int id, got {type(cid).__name__}'\n"
            "        store.append(cid, 'user', 'hi')\n"
            "        store.append(cid, 'assistant', 'hello!')\n"
            "        passed += 1; print(f'✅ Check 2: start -> id {cid}, append works')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 2: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 3: history returns the messages in order\n"
            "    try:\n"
            "        h = store.history(cid)\n"
            "        assert h == [{'role': 'user', 'content': 'hi'},\n"
            "                     {'role': 'assistant', 'content': 'hello!'}], f'bad history: {h}'\n"
            "        passed += 1; print('✅ Check 3: history() returns the saved turns')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 3: {e}')\n"
            "\n"
            "    # Check 4: conversations() lists it with a message_count\n"
            "    try:\n"
            "        convs = store.conversations()\n"
            "        row = [c for c in convs if c['id'] == cid][0]\n"
            "        assert row['message_count'] == 2, f\"expected 2, got {row['message_count']}\"\n"
            "        passed += 1; print('✅ Check 4: conversations() reports message_count')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 4: {e}')\n"
            "\n"
            "    # Check 5: SAVED STATE survives a 'restart' (new ChatStore, same file)\n"
            "    try:\n"
            "        store2 = ChatStore(db_path)\n"
            "        assert store2.history(cid) == [{'role': 'user', 'content': 'hi'},\n"
            "                                       {'role': 'assistant', 'content': 'hello!'}], \\\n"
            "            'a fresh ChatStore on the same file must see the saved data'\n"
            "        passed += 1; print('✅ Check 5: data persists across a restart \U0001f4be')\n"
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
            + CHATSTORE_IMPL + "\n"
            "```\n\n"
            "**Why this works:** `ChatStore` owns one file-backed engine and opens a "
            "short `Session` per method — the classic web pattern of a session per unit "
            "of work. Each method commits before returning, so state is durable "
            "immediately. Because the database is a file, a brand-new `ChatStore` "
            "pointed at the same path sees every prior conversation — which is exactly "
            "what Check 5 proves and what 'saved state' means. The backend holds one "
            "`ChatStore` and calls these four verbs.\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Project notebook (student template — not executed by the gate)
# ---------------------------------------------------------------------------

def project_nb():
    global _cid; _cid = 500
    all_code = _BEFORE_EX05 + "\n\n\n" + CHATSTORE_IMPL
    return [
        md(
            "# Day 054 Project: A Chat Backend With a Memory\n\n"
            "## What You're Building\n\n"
            "A **persistent chat backend** (`backend.py`): a FastAPI service that saves "
            "every conversation and message to a SQLite database through your "
            "`ChatStore`. Restart the server and the history is still there. Endpoints: "
            "create a conversation, list conversations, read a conversation's messages, "
            "and post a message (which saves your turn, calls Ollama with the full "
            "saved history, and saves the reply).\n\n"
            "## Project Requirements\n\n"
            "1. Use the provided repository functions and `ChatStore`.\n"
            "2. Build a `ChatStore` on a temp file; start a conversation, append a few "
            "messages, read the history, list conversations.\n"
            "3. Prove persistence: open a **second** `ChatStore` on the same file and "
            "confirm it sees the data.\n"
            "4. Call `write_backend('backend.py')` to generate the service.\n"
            "5. Run `_run_project_checks()`, then `uvicorn backend:app --reload`.\n\n"
            "## Bonus Challenges\n\n"
            "- Add a `delete_conversation(store, cid)` (cascade removes its messages).\n"
            "- Add a `pinned` column with `migrate_add_column` and a `/pin` endpoint.\n"
            "- Point the frontend from Day 53 at this backend so chats persist."
        ),
        md("## Provided: Models + Repository + ChatStore"),
        code(all_code),
        md("## Provided: Backend File Writer"),
        code(WRITE_BACKEND_CELL),
        md("## Your Pipeline"),
        code(
            "# TODO: db_path = os.path.join(tempfile.mkdtemp(), 'chat.db')\n"
            "# TODO: store = ChatStore(db_path)\n"
            "# TODO: cid = store.start('My first saved chat')\n"
            "# TODO: store.append(cid, 'user', 'Remember this message.')\n"
            "# TODO: store.append(cid, 'assistant', 'Saved!')\n"
            "# TODO: print('history     :', store.history(cid))\n"
            "# TODO: print('conversations:', store.conversations())\n"
            "#\n"
            "# TODO: reopened = ChatStore(db_path)   # simulate a restart\n"
            "# TODO: print('after restart:', reopened.history(cid))\n"
            "#\n"
            "# TODO: print('wrote', write_backend('backend.py'))\n"
            "# TODO: print('Run:  uvicorn backend:app --reload')"
        ),
        md("## Checks"),
        code(
            "def _run_project_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: a ChatStore was created and used\n"
            "    try:\n"
            "        assert 'store' in globals() and isinstance(store, ChatStore), 'create store = ChatStore(...)'\n"
            "        assert 'cid' in globals(), 'start a conversation and keep its id in cid'\n"
            "        passed += 1; print('✅ Check 1: ChatStore created, conversation started')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: history has the saved turns\n"
            "    try:\n"
            "        h = store.history(cid)\n"
            "        assert len(h) >= 2, f'expected >= 2 saved messages, got {len(h)}'\n"
            "        passed += 1; print(f'✅ Check 2: {len(h)} messages saved')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 2: {e}')\n"
            "\n"
            "    # Check 3: persistence across a fresh ChatStore\n"
            "    try:\n"
            "        assert 'reopened' in globals() and isinstance(reopened, ChatStore), 'open a second ChatStore'\n"
            "        assert reopened.history(cid) == store.history(cid), 'reopened store must see the same data'\n"
            "        passed += 1; print('✅ Check 3: data persists across a restart')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 3: {e}')\n"
            "\n"
            "    # Check 4: backend.py generated + valid Python\n"
            "    try:\n"
            "        assert os.path.exists('backend.py'), 'backend.py not found — call write_backend()'\n"
            "        src = open('backend.py', encoding='utf-8').read()\n"
            "        assert 'ChatStore' in src and 'from fastapi import FastAPI' in src\n"
            "        compile(src, 'backend.py', 'exec')\n"
            "        passed += 1; print('✅ Check 4: backend.py generated and compiles')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 4: {e}')\n"
            "\n"
            "    # Check 5: backend persists via ChatStore + has the routes\n"
            "    try:\n"
            "        src = open('backend.py', encoding='utf-8').read()\n"
            "        assert \"store = ChatStore(\" in src, 'backend must instantiate a ChatStore'\n"
            "        assert \"@app.post('/conversations')\" in src and \"@app.get('/conversations')\" in src\n"
            "        passed += 1; print('✅ Check 5: backend wires ChatStore into routes')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\U0001f389 Project complete! Run: uvicorn backend:app --reload')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "\n"
            "_run_project_checks()"
        ),
    ]


# ---------------------------------------------------------------------------
# Solution notebook (runs clean under nbconvert — DB only, no server)
# ---------------------------------------------------------------------------

def solution_nb():
    global _cid; _cid = 600
    all_code = _BEFORE_EX05 + "\n\n\n" + CHATSTORE_IMPL
    return [
        md(
            "# Day 054 Solution — A Chat Backend With a Memory\n\n"
            "Section 4, Day 4. Builds the persistence layer (models + repository + "
            "`ChatStore`), proves data survives a restart, runs a minimal migration, "
            "then generates the persistent backend. DB-only — no server is launched."
        ),
        code(all_code),
        md("## Step 1 — Save a Conversation"),
        code(
            "db_path = os.path.join(tempfile.mkdtemp(), 'chat.db')\n"
            "store = ChatStore(db_path)\n"
            "\n"
            "cid = store.start('Trip planning')\n"
            "store.append(cid, 'user', 'Plan a 3-day trip to Cape Town.')\n"
            "store.append(cid, 'assistant', 'Day 1: Table Mountain...')\n"
            "store.append(cid, 'user', 'Add a wine tour.')\n"
            "\n"
            "print('history:')\n"
            "for m in store.history(cid):\n"
            "    print(f\"  {m['role']}: {m['content']}\")\n"
            "print('\\nconversations:', store.conversations())\n"
            "assert len(store.history(cid)) == 3"
        ),
        md("## Step 2 — Prove It Survives a Restart"),
        code(
            "# A brand-new ChatStore on the SAME file = the app restarting.\n"
            "reopened = ChatStore(db_path)\n"
            "print('After restart, history still has', len(reopened.history(cid)), 'messages:')\n"
            "print(reopened.history(cid))\n"
            "assert reopened.history(cid) == store.history(cid)\n"
            "print('\\n\\u2713 Saved state persists across restarts.')"
        ),
        md("## Step 3 — A Minimal Migration"),
        code(
            "before = column_exists(store.engine, 'conversations', 'pinned')\n"
            "added = migrate_add_column(store.engine, 'conversations', 'pinned', 'INTEGER')\n"
            "again = migrate_add_column(store.engine, 'conversations', 'pinned', 'INTEGER')\n"
            "print(f'pinned existed before: {before} | added now: {added} | second run: {again}')\n"
            "assert before is False and added is True and again is False\n"
            "assert column_exists(store.engine, 'conversations', 'pinned') is True\n"
            "print('Migration added the column once and is safe to re-run.')"
        ),
        md("## Step 4 — Generate the Persistent Backend"),
        code(WRITE_BACKEND_CELL),
        code(
            "path = write_backend('backend.py')\n"
            "src = open(path, encoding='utf-8').read()\n"
            "print(f'Wrote {path} ({len(src)} chars)')\n"
            "\n"
            "assert 'from fastapi import FastAPI' in src\n"
            "assert 'class ChatStore' in src and \"store = ChatStore('chat.db')\" in src\n"
            "assert \"@app.post('/conversations/{cid}/messages')\" in src\n"
            "compile(src, 'backend.py', 'exec')\n"
            "print('backend.py verified: FastAPI + ChatStore persistence + routes, compiles.')"
        ),
        md("## Step 5 — How to Run It"),
        code(
            "print('Start the persistent API:')\n"
            "print('    uvicorn backend:app --reload')\n"
            "print('It writes chat.db in the working directory; conversations survive restarts.')\n"
            "print('\\nDay 54 — Databases for Apps complete! \U0001f389')"
        ),
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Generating Day 054 notebooks...")
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
