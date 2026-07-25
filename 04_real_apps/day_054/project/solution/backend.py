import warnings
warnings.filterwarnings('ignore')
from datetime import datetime
from fastapi import FastAPI
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, ForeignKey, select, inspect as sa_inspect, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session
import ollama


class Base(DeclarativeBase):
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

    conversation: Mapped['Conversation'] = relationship(back_populates='messages')


def create_schema(engine) -> None:
    """Create every table registered on Base (CREATE TABLE IF NOT EXISTS)."""
    Base.metadata.create_all(engine)


def create_conversation(session, title: str = 'New chat') -> Conversation:
    """Insert a new conversation and flush so its auto id is assigned.
    The caller controls commit (unit-of-work pattern)."""
    conv = Conversation(title=title)
    session.add(conv)
    session.flush()
    return conv


def add_message(session, conversation_id: int, role: str, content: str) -> Message:
    """Append a message to a conversation via its foreign key, and flush to assign
    the id. The caller commits."""
    msg = Message(conversation_id=conversation_id, role=role, content=content)
    session.add(msg)
    session.flush()
    return msg


def get_messages(session, conversation_id: int) -> list:
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
            for c in convs]


def make_engine(db_path: str):
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
    return True


class ChatStore:
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
            return list_conversations(s)


class ConversationIn(BaseModel):
    title: str = 'New chat'


class MessageIn(BaseModel):
    message: str = Field(min_length=1)


store = ChatStore('chat.db')
app = FastAPI(title='Persistent Chat API')


@app.post('/conversations')
def create_conv(req: ConversationIn):
    return {'id': store.start(req.title)}


@app.get('/conversations')
def list_convs():
    return {'conversations': store.conversations()}


@app.get('/conversations/{cid}/messages')
def get_history(cid: int):
    return {'messages': store.history(cid)}


@app.post('/conversations/{cid}/messages')
def post_message(cid: int, req: MessageIn):
    store.append(cid, 'user', req.message)
    history = store.history(cid)          # full saved history each turn
    try:
        resp = ollama.chat(model='llama3.2', messages=history)
        reply = resp['message']['content'].strip()
    except Exception as e:
        reply = f'[Model unavailable: {e}]'
    store.append(cid, 'assistant', reply)
    return {'reply': reply}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
