#!/usr/bin/env python3
"""Day 086 generator — Retrieval Agents (Agentic RAG)."""
import json, pathlib

ROOT  = pathlib.Path(__file__).parent.parent
DAY   = "086"
SLUG  = "retrieval_agent"
TITLE = "Retrieval Agents"
DIR   = ROOT / "06_agents" / f"day_{DAY}"

# ══════════════════════════════════════════════════════════════════════════════
# Deliverable source fragments
# ══════════════════════════════════════════════════════════════════════════════

_FRAG_DOC = '''\
"""
Day 086 — Retrieval Agents (Agentic RAG)
=========================================
Day 13 introduced RAG as a fixed pipeline: always retrieve, always generate.
**Agentic RAG** lets the agent decide when and what to retrieve — it can issue
multiple retrieval calls with different queries, inspect the returned documents,
and decide to keep searching or answer.

Architecture
------------
    Document          dataclass — content string + metadata dict
    SimpleRetriever   in-process keyword (word-overlap) search over Documents
    format_docs       render a doc list as numbered context for a prompt
    build_retrieval_prompt
    retrieve_and_answer  single-turn convenience: retrieve -> generate
    build_agent_step_prompt
    parse_agent_action   parse {"action": "retrieve"|"answer", ...}
    RetrievalAgent    iterative agentic loop with max_iterations cap

Gate helpers
    _mock_retrieval_llm   script-based llm_fn for deterministic tests
"""
'''

_FRAG_IMPORTS = '''\
import json
from dataclasses import dataclass, field
'''

_FRAG_HELPERS = '''\

# ── LLM + JSON helpers ────────────────────────────────────────────────────────

def call_llm(messages, llm_fn=None):
    """Call the LLM.  Routes to llm_fn when injected; else Ollama."""
    if llm_fn is not None:
        return str(llm_fn(messages))
    import ollama
    resp = ollama.chat(model="llama3.2", messages=messages)
    return resp["message"]["content"]


def safe_parse_json(text):
    """Return the first JSON object found in text, or None."""
    start = str(text).find("{")
    end   = str(text).rfind("}") + 1
    if start == -1 or end == 0:
        return None
    try:
        return json.loads(text[start:end])
    except (json.JSONDecodeError, ValueError):
        return None
'''

_FRAG_DOCUMENT = '''\

# ── document store ────────────────────────────────────────────────────────────

@dataclass
class Document:
    """A piece of text with optional metadata.

    content  — the text to index and return in search results
    metadata — dict of arbitrary key/value pairs (e.g. {"source": "file.txt"})
    """
    content:  str
    metadata: dict = field(default_factory=dict)


class SimpleRetriever:
    """A pure-Python keyword retriever using word-overlap (Jaccard) scoring.

    No ML libraries required.  Works well enough to demonstrate the agentic
    retrieval pattern; swap for a real vector store in production.
    """

    def __init__(self):
        self._docs = []

    def add(self, doc):
        """Add a single Document.  Returns self for chaining."""
        self._docs.append(doc)
        return self

    def add_all(self, docs):
        """Add an iterable of Documents.  Returns self."""
        for d in docs:
            self._docs.append(d)
        return self

    def _score(self, query, doc):
        """Word-overlap Jaccard similarity between query and doc content."""
        q = set(query.lower().split())
        d = set(doc.content.lower().split())
        return len(q & d) / (len(q | d) + 1e-9)

    def search(self, query, top_k=3):
        """Return up to top_k Documents ranked by word-overlap with query."""
        if not self._docs:
            return []
        scored = sorted(
            self._docs,
            key=lambda doc: self._score(query, doc),
            reverse=True,
        )
        return scored[:top_k]

    def __len__(self):
        return len(self._docs)
'''

_FRAG_FORMAT = '''\

# ── RAG prompt helpers ────────────────────────────────────────────────────────

def format_docs(docs):
    """Render a list of Documents as a numbered context block.

    Format:
        [1] (source) content
        [2] (source) content
        ...

    Returns "No documents found." for an empty list.
    """
    if not docs:
        return "No documents found."
    lines = []
    for i, d in enumerate(docs, 1):
        source = d.metadata.get("source", f"doc{i}")
        lines.append(f"[{i}] ({source}) {d.content}")
    return "\\n".join(lines)


def build_retrieval_prompt(question, docs):
    """Build a RAG answer prompt from retrieved documents.

    Instructs the model to answer using only the provided documents and to
    cite document numbers when referencing specific facts.
    """
    context = format_docs(docs)
    system  = "\\n".join([
        "You are a helpful assistant.",
        "Answer the question using ONLY the provided documents.",
        "If the answer is not in the documents, say: I don't have enough information.",
        "Cite document numbers like [1] when referencing specific facts.",
    ])
    user = "Documents:\\n" + context + "\\n\\nQuestion: " + str(question)
    return [
        {"role": "system", "content": system},
        {"role": "user",   "content": user},
    ]


def retrieve_and_answer(question, retriever, top_k=3, llm_fn=None):
    """Single-turn RAG: retrieve docs, then generate an answer.

    Returns {"question", "docs", "answer"}.
    This is the fixed-pipeline version; RetrievalAgent is the agentic version.
    """
    docs   = retriever.search(question, top_k=top_k)
    prompt = build_retrieval_prompt(question, docs)
    answer = call_llm(prompt, llm_fn=llm_fn)
    return {"question": question, "docs": docs, "answer": answer}
'''

_FRAG_DECISION = '''\

# ── agent decision layer ──────────────────────────────────────────────────────

def build_agent_step_prompt(question, context):
    """Build the decision prompt for one step of the retrieval agent loop.

    The agent sees the question and accumulated context, then decides:
        {"action": "retrieve", "query": "..."}  -- search for more info
        {"action": "answer",   "text":  "..."}  -- respond with final answer
    """
    has_context = bool(context) and context != "No documents found."
    ctx_line    = "Current context:\\n" + context if has_context else "No context retrieved yet."
    system      = "\\n".join([
        "You are a research agent. Decide your next action.",
        'To search: {"action": "retrieve", "query": "your search query"}',
        'To answer: {"action": "answer",   "text":  "your final answer"}',
        "Use retrieve to gather information; use answer when you have enough.",
        "Reply with ONLY valid JSON.",
    ])
    user = "Question: " + str(question) + "\\n\\n" + ctx_line
    return [
        {"role": "system", "content": system},
        {"role": "user",   "content": user},
    ]


def parse_agent_action(text):
    """Parse the agent's JSON response into a normalised action dict.

    Returns {"action": "answer", "text": ...} or {"action": "retrieve", "query": ...}.
    Falls back to a retrieve action on any parse failure — keeps the loop going
    rather than terminating on bad output.
    """
    data = safe_parse_json(text) or {}
    if data.get("action") == "answer":
        return {"action": "answer", "text": str(data.get("text", ""))}
    query = str(data.get("query", ""))
    return {"action": "retrieve", "query": query}
'''

_FRAG_AGENT = '''\

# ── retrieval agent ───────────────────────────────────────────────────────────

class RetrievalAgent:
    """An agent that iteratively retrieves documents and answers questions.

    Agentic RAG loop
    ----------------
    Each iteration:
      1. Build a decision prompt with the question + accumulated context
      2. Ask the LLM: retrieve more or answer now?
      3. If retrieve: call retriever.search(query, top_k), extend all_docs
      4. If answer:   record the answer and return immediately
    After max_iterations without an answer: generate a final answer from
    whatever documents were accumulated.

    Same four-method class shape as all prior Section 6 agents.
    """

    def __init__(self, retriever, llm_fn=None, top_k=3, max_iterations=5):
        self.retriever      = retriever
        self._llm_fn        = llm_fn
        self._top_k         = top_k
        self.max_iterations = max_iterations
        self._history       = []

    def ask(self, question):
        """Run the agentic retrieval loop and return the result dict."""
        all_docs = []
        steps    = []

        for iteration in range(self.max_iterations):
            context  = format_docs(all_docs) if all_docs else "No documents retrieved yet."
            prompt   = build_agent_step_prompt(question, context)
            response = call_llm(prompt, llm_fn=self._llm_fn)
            act      = parse_agent_action(response)

            if act["action"] == "answer":
                answer = act.get("text", "")
                steps.append({"step": iteration + 1, "action": "answer", "text": answer})
                record = {
                    "question": question,
                    "docs":     all_docs,
                    "answer":   answer,
                    "steps":    steps,
                }
                self._history.append(record)
                return record

            # retrieve
            query = act.get("query", question)
            docs  = self.retriever.search(query, top_k=self._top_k)
            all_docs.extend(docs)
            steps.append({
                "step":   iteration + 1,
                "action": "retrieve",
                "query":  query,
                "found":  len(docs),
            })

        # max_iterations exhausted — answer with accumulated docs
        ans_prompt = build_retrieval_prompt(question, all_docs)
        answer     = call_llm(ans_prompt, llm_fn=self._llm_fn)
        steps.append({"step": self.max_iterations + 1, "action": "answer", "text": answer})
        record = {
            "question": question,
            "docs":     all_docs,
            "answer":   answer,
            "steps":    steps,
        }
        self._history.append(record)
        return record

    def history(self):
        """Return a copy of the interaction history."""
        return list(self._history)

    def clear_history(self):
        """Clear the interaction history."""
        self._history.clear()
'''

_FRAG_MOCK = '''\

# ── gate helpers ──────────────────────────────────────────────────────────────

def _mock_retrieval_llm(script):
    """Return an llm_fn driven by a list of pre-canned action dicts.

    script  — list of dicts, e.g.:
        [{"action": "retrieve", "query": "AI"},
         {"action": "answer",   "text":  "AI is ..."}]

    Replays each item in order; repeats the last item once the list is exhausted.
    """
    idx = [0]
    def _fn(messages):
        i = min(idx[0], len(script) - 1)
        idx[0] += 1
        return json.dumps(script[i])
    return _fn
'''

DELIVERABLE = (
    _FRAG_DOC + _FRAG_IMPORTS + _FRAG_HELPERS + _FRAG_DOCUMENT
    + _FRAG_FORMAT + _FRAG_DECISION + _FRAG_AGENT + _FRAG_MOCK
)

# ══════════════════════════════════════════════════════════════════════════════
# Notebook helpers
# ══════════════════════════════════════════════════════════════════════════════

def _nb(cells):
    return {
        "nbformat": 4, "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3 (ipykernel)",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.10.0"},
        },
        "cells": cells,
    }

def _code(src, outputs=None):
    return {
        "cell_type": "code", "execution_count": None, "metadata": {},
        "outputs": outputs or [],
        "source": src.splitlines(keepends=True),
    }

def _md(src):
    return {"cell_type": "markdown", "metadata": {},
            "source": src.splitlines(keepends=True)}

# ── context preludes ──────────────────────────────────────────────────────────

_P_BASE = """\
import json
from dataclasses import dataclass, field
"""

_P_HELPERS = """\
def call_llm(messages, llm_fn=None):
    if llm_fn is not None:
        return str(llm_fn(messages))
    import ollama
    resp = ollama.chat(model="llama3.2", messages=messages)
    return resp["message"]["content"]

def safe_parse_json(text):
    start = str(text).find("{")
    end   = str(text).rfind("}") + 1
    if start == -1 or end == 0:
        return None
    try:
        return json.loads(text[start:end])
    except (json.JSONDecodeError, ValueError):
        return None
"""

_P_DOCUMENT = """\
@dataclass
class Document:
    content: str
    metadata: dict = field(default_factory=dict)

class SimpleRetriever:
    def __init__(self):
        self._docs = []
    def add(self, doc):
        self._docs.append(doc); return self
    def add_all(self, docs):
        for d in docs: self._docs.append(d)
        return self
    def _score(self, query, doc):
        q = set(query.lower().split())
        d = set(doc.content.lower().split())
        return len(q & d) / (len(q | d) + 1e-9)
    def search(self, query, top_k=3):
        if not self._docs: return []
        return sorted(self._docs, key=lambda doc: self._score(query, doc), reverse=True)[:top_k]
    def __len__(self): return len(self._docs)
"""

_P_FORMAT = """\
def format_docs(docs):
    if not docs:
        return "No documents found."
    lines = []
    for i, d in enumerate(docs, 1):
        source = d.metadata.get("source", f"doc{i}")
        lines.append(f"[{i}] ({source}) {d.content}")
    return "\\n".join(lines)

def build_retrieval_prompt(question, docs):
    context = format_docs(docs)
    system = "\\n".join([
        "You are a helpful assistant.",
        "Answer the question using ONLY the provided documents.",
        "If the answer is not in the documents, say: I don't have enough information.",
        "Cite document numbers like [1] when referencing specific facts.",
    ])
    user = "Documents:\\n" + context + "\\n\\nQuestion: " + str(question)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]

def retrieve_and_answer(question, retriever, top_k=3, llm_fn=None):
    docs = retriever.search(question, top_k=top_k)
    prompt = build_retrieval_prompt(question, docs)
    answer = call_llm(prompt, llm_fn=llm_fn)
    return {"question": question, "docs": docs, "answer": answer}
"""

_P_DECISION = """\
def build_agent_step_prompt(question, context):
    has_context = bool(context) and context != "No documents found."
    ctx_line = "Current context:\\n" + context if has_context else "No context retrieved yet."
    system = "\\n".join([
        "You are a research agent. Decide your next action.",
        'To search: {"action": "retrieve", "query": "your search query"}',
        'To answer: {"action": "answer",   "text":  "your final answer"}',
        "Use retrieve to gather information; use answer when you have enough.",
        "Reply with ONLY valid JSON.",
    ])
    user = "Question: " + str(question) + "\\n\\n" + ctx_line
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]

def parse_agent_action(text):
    data = safe_parse_json(text) or {}
    if data.get("action") == "answer":
        return {"action": "answer", "text": str(data.get("text", ""))}
    query = str(data.get("query", ""))
    return {"action": "retrieve", "query": query}
"""

_P_MOCK = """\
def _mock_retrieval_llm(script):
    idx = [0]
    def _fn(messages):
        i = min(idx[0], len(script) - 1)
        idx[0] += 1
        return json.dumps(script[i])
    return _fn
"""

_P_AGENT = """\
class RetrievalAgent:
    def __init__(self, retriever, llm_fn=None, top_k=3, max_iterations=5):
        self.retriever = retriever
        self._llm_fn = llm_fn
        self._top_k = top_k
        self.max_iterations = max_iterations
        self._history = []
    def ask(self, question):
        all_docs = []; steps = []
        for iteration in range(self.max_iterations):
            context = format_docs(all_docs) if all_docs else "No documents retrieved yet."
            prompt = build_agent_step_prompt(question, context)
            response = call_llm(prompt, llm_fn=self._llm_fn)
            act = parse_agent_action(response)
            if act["action"] == "answer":
                answer = act.get("text", "")
                steps.append({"step": iteration + 1, "action": "answer", "text": answer})
                record = {"question": question, "docs": all_docs, "answer": answer, "steps": steps}
                self._history.append(record); return record
            query = act.get("query", question)
            docs = self.retriever.search(query, top_k=self._top_k)
            all_docs.extend(docs)
            steps.append({"step": iteration + 1, "action": "retrieve", "query": query, "found": len(docs)})
        ans_prompt = build_retrieval_prompt(question, all_docs)
        answer = call_llm(ans_prompt, llm_fn=self._llm_fn)
        steps.append({"step": self.max_iterations + 1, "action": "answer", "text": answer})
        record = {"question": question, "docs": all_docs, "answer": answer, "steps": steps}
        self._history.append(record); return record
    def history(self): return list(self._history)
    def clear_history(self): self._history.clear()
"""

# ══════════════════════════════════════════════════════════════════════════════
# Exercise notebooks
# ══════════════════════════════════════════════════════════════════════════════

_EX1 = _nb([
    _md("# Exercise 1 — Document and SimpleRetriever\n\n"
        "**Document** is a simple dataclass: a content string plus a metadata "
        "dict (source, date, etc.).  **SimpleRetriever** stores documents and "
        "retrieves the most relevant ones using word-overlap (Jaccard) similarity "
        "— no ML libraries needed."),
    _code(_P_BASE + """\

# ── Exercise: implement Document and SimpleRetriever ─────────────────────────

@dataclass
class Document:
    content: str = ''       # TODO: two fields: content (str) and metadata (dict, default {})
    # metadata should default to an empty dict using field(default_factory=dict)


class SimpleRetriever:
    \"\"\"Pure-Python retriever using word-overlap similarity.\"\"\"

    def __init__(self):
        self._docs = []

    def add(self, doc):
        # TODO: append doc to self._docs and return self (for chaining)
        return self

    def add_all(self, docs):
        # TODO: call self.add() for each doc in docs; return self
        return self

    def _score(self, query, doc):
        # TODO: Jaccard similarity between query words and doc.content words
        # q = set of lowercase words in query
        # d = set of lowercase words in doc.content
        # return len(q & d) / (len(q | d) + 1e-9)
        return 0.0

    def search(self, query, top_k=3):
        # TODO: return up to top_k docs sorted by _score descending
        # Return [] if no docs are stored
        return []

    def __len__(self):
        # TODO: return number of stored documents
        return 0
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — Document dataclass
try:
    import dataclasses
    assert dataclasses.is_dataclass(Document)
    d = Document("Python is great.", {"source": "wiki"})
    assert d.content == "Python is great."
    assert d.metadata == {"source": "wiki"}
    checks += 1; print("✅ 1 Document instantiates correctly")
except Exception as e:
    print("❌ 1:", e)

# 2 — Document default metadata
try:
    d = Document("hello")
    assert d.metadata == {}
    checks += 1; print("✅ 2 default metadata is {}")
except Exception as e:
    print("❌ 2:", e)

# 3 — add and __len__
try:
    r = SimpleRetriever()
    r.add(Document("doc one"))
    r.add(Document("doc two"))
    assert len(r) == 2
    checks += 1; print("✅ 3 add() and __len__ work")
except Exception as e:
    print("❌ 3:", e)

# 4 — add_all returns self (chaining)
try:
    r = SimpleRetriever()
    result = r.add_all([Document("a"), Document("b"), Document("c")])
    assert result is r and len(r) == 3
    checks += 1; print("✅ 4 add_all() returns self, adds all docs")
except Exception as e:
    print("❌ 4:", e)

# 5 — search ranks by relevance
try:
    r = SimpleRetriever()
    r.add_all([
        Document("Python is a programming language."),
        Document("The sky is blue today."),
        Document("Python uses indentation for code blocks."),
    ])
    results = r.search("Python programming", top_k=2)
    assert len(results) == 2
    assert all("Python" in d.content or "python" in d.content.lower() for d in results)
    checks += 1; print("✅ 5 search returns most relevant docs")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX2 = _nb([
    _md("# Exercise 2 — format_docs and build_retrieval_prompt\n\n"
        "`format_docs` turns a list of Documents into a numbered context block "
        "for an LLM prompt.  `build_retrieval_prompt` wraps that context into a "
        "full RAG prompt — a fixed-pipeline approach (Day 13 pattern) that the "
        "agentic version will extend."),
    _code(_P_BASE + _P_DOCUMENT + """\

# ── Exercise: implement format_docs and build_retrieval_prompt ───────────────

def format_docs(docs):
    # TODO: if docs is empty, return "No documents found."
    # For each doc (1-indexed), get source from doc.metadata.get("source", f"doc{i}")
    # Append "[i] (source) content" to lines
    # Return lines joined with "\\n"
    return "No documents found."


def build_retrieval_prompt(question, docs):
    # TODO: call format_docs(docs) to get context
    # Build a system message instructing the model to answer from the documents
    # and cite doc numbers like [1]
    # Return [{"role": "system", ...}, {"role": "user", "content": "Documents:\\n...\\n\\nQuestion: ..."}]
    return [{"role": "system", "content": ""}, {"role": "user", "content": str(question)}]
"""),
    _md("### Checks"),
    _code("""\
checks = 0

docs = [
    Document("Python is a programming language.", {"source": "wiki"}),
    Document("Python uses indentation.", {"source": "docs"}),
]

# 1 — format_docs with empty list
try:
    result = format_docs([])
    assert result == "No documents found."
    checks += 1; print("✅ 1 format_docs([]) returns 'No documents found.'")
except Exception as e:
    print("❌ 1:", e)

# 2 — format_docs includes doc numbers
try:
    text = format_docs(docs)
    assert "[1]" in text and "[2]" in text
    checks += 1; print("✅ 2 format_docs includes [1], [2] numbering")
except Exception as e:
    print("❌ 2:", e)

# 3 — format_docs includes source from metadata
try:
    text = format_docs(docs)
    assert "wiki" in text
    checks += 1; print("✅ 3 format_docs includes source from metadata")
except Exception as e:
    print("❌ 3:", e)

# 4 — build_retrieval_prompt returns list of 2 messages
try:
    prompt = build_retrieval_prompt("What is Python?", docs)
    assert isinstance(prompt, list) and len(prompt) == 2
    assert prompt[0]["role"] == "system"
    assert prompt[1]["role"] == "user"
    checks += 1; print("✅ 4 build_retrieval_prompt returns [system, user] messages")
except Exception as e:
    print("❌ 4:", e)

# 5 — build_retrieval_prompt includes question and doc content
try:
    prompt = build_retrieval_prompt("What is Python?", docs)
    combined = " ".join(m["content"] for m in prompt)
    assert "Python" in combined and "What is Python?" in combined
    checks += 1; print("✅ 5 prompt includes question and document content")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX3 = _nb([
    _md("# Exercise 3 — retrieve_and_answer\n\n"
        "`retrieve_and_answer` is the single-turn RAG convenience function: "
        "search the retriever for the question, build a RAG prompt, call the LLM, "
        "and return `{question, docs, answer}`.  This is the fixed-pipeline "
        "baseline — the agent in Exercise 5 extends this with iteration."),
    _code(_P_BASE + _P_DOCUMENT + _P_HELPERS + _P_FORMAT.split("\ndef retrieve_and_answer")[0] + """\

# ── Exercise: implement retrieve_and_answer ──────────────────────────────────

def retrieve_and_answer(question, retriever, top_k=3, llm_fn=None):
    # TODO:
    # 1. docs = retriever.search(question, top_k=top_k)
    # 2. prompt = build_retrieval_prompt(question, docs)
    # 3. answer = call_llm(prompt, llm_fn=llm_fn)
    # 4. return {"question": question, "docs": docs, "answer": answer}
    return {"question": question, "docs": [], "answer": ""}
"""),
    _md("### Checks"),
    _code("""\
checks = 0

retriever = SimpleRetriever()
retriever.add_all([
    Document("Python is a high-level programming language.", {"source": "intro"}),
    Document("Python was created by Guido van Rossum.", {"source": "history"}),
    Document("The sky is blue.", {"source": "nature"}),
])

mock_llm = lambda messages: "Python is a high-level programming language [1]."

# 1 — returns dict with question, docs, answer keys
try:
    r = retrieve_and_answer("What is Python?", retriever, llm_fn=mock_llm)
    assert "question" in r and "docs" in r and "answer" in r
    checks += 1; print("✅ 1 returns dict with question, docs, answer")
except Exception as e:
    print("❌ 1:", e)

# 2 — docs are retrieved (non-empty for relevant query)
try:
    r = retrieve_and_answer("What is Python?", retriever, llm_fn=mock_llm)
    assert len(r["docs"]) > 0
    checks += 1; print("✅ 2 docs are retrieved")
except Exception as e:
    print("❌ 2:", e)

# 3 — answer comes from llm_fn
try:
    r = retrieve_and_answer("What is Python?", retriever, llm_fn=mock_llm)
    assert r["answer"] == "Python is a high-level programming language [1]."
    checks += 1; print("✅ 3 answer is the llm_fn return value")
except Exception as e:
    print("❌ 3:", e)

# 4 — question is preserved
try:
    r = retrieve_and_answer("Who created Python?", retriever, llm_fn=mock_llm)
    assert r["question"] == "Who created Python?"
    checks += 1; print("✅ 4 question is preserved in result")
except Exception as e:
    print("❌ 4:", e)

# 5 — top_k limits results
try:
    r = retrieve_and_answer("Python", retriever, top_k=1, llm_fn=mock_llm)
    assert len(r["docs"]) <= 1
    checks += 1; print("✅ 5 top_k limits number of retrieved docs")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX4 = _nb([
    _md("# Exercise 4 — build_agent_step_prompt and parse_agent_action\n\n"
        "The agent decision layer: at each step the agent sees the question plus "
        "accumulated context and decides whether to retrieve more or answer.  "
        "`build_agent_step_prompt` constructs that decision prompt.  "
        "`parse_agent_action` parses the LLM's JSON response, falling back to a "
        "retrieve action on any parse failure."),
    _code(_P_BASE + _P_DOCUMENT + _P_HELPERS + _P_FORMAT + """\

# ── Exercise: implement build_agent_step_prompt and parse_agent_action ───────

def build_agent_step_prompt(question, context):
    # TODO: check if context is non-empty and not "No documents found."
    # Build a system message explaining the two JSON actions:
    #   {"action": "retrieve", "query": "..."} and {"action": "answer", "text": "..."}
    # Build user message: "Question: " + question + "\\n\\n" + context summary
    # Return [{"role": "system", ...}, {"role": "user", ...}]
    return [{"role": "system", "content": ""}, {"role": "user", "content": str(question)}]


def parse_agent_action(text):
    # TODO: call safe_parse_json(text) -> data dict
    # If data.get("action") == "answer": return {"action": "answer", "text": str(data.get("text", ""))}
    # Otherwise: return {"action": "retrieve", "query": str(data.get("query", ""))}
    # Never raise — fall back to retrieve on bad parse
    return {"action": "retrieve", "query": ""}
"""),
    _md("### Checks"),
    _code("""\
import json
checks = 0

# 1 — build_agent_step_prompt returns [system, user]
try:
    prompt = build_agent_step_prompt("What is AI?", "No context retrieved yet.")
    assert isinstance(prompt, list) and len(prompt) == 2
    assert prompt[0]["role"] == "system" and prompt[1]["role"] == "user"
    checks += 1; print("✅ 1 build_agent_step_prompt returns [system, user]")
except Exception as e:
    print("❌ 1:", e)

# 2 — prompt mentions both actions
try:
    prompt = build_agent_step_prompt("What is AI?", "No context retrieved yet.")
    sys_content = prompt[0]["content"]
    assert "retrieve" in sys_content and "answer" in sys_content
    checks += 1; print("✅ 2 system message mentions both retrieve and answer actions")
except Exception as e:
    print("❌ 2:", e)

# 3 — parse_agent_action: answer action
try:
    text = json.dumps({"action": "answer", "text": "AI is artificial intelligence."})
    act = parse_agent_action(text)
    assert act["action"] == "answer"
    assert act["text"] == "AI is artificial intelligence."
    checks += 1; print("✅ 3 parse_agent_action returns answer action correctly")
except Exception as e:
    print("❌ 3:", e)

# 4 — parse_agent_action: retrieve action
try:
    text = json.dumps({"action": "retrieve", "query": "artificial intelligence history"})
    act = parse_agent_action(text)
    assert act["action"] == "retrieve"
    assert "artificial" in act["query"]
    checks += 1; print("✅ 4 parse_agent_action returns retrieve action correctly")
except Exception as e:
    print("❌ 4:", e)

# 5 — parse_agent_action falls back to retrieve on bad JSON
try:
    act = parse_agent_action("this is not json at all")
    assert act["action"] == "retrieve"
    checks += 1; print("✅ 5 parse_agent_action falls back to retrieve on bad input")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX5 = _nb([
    _md("# Exercise 5 — RetrievalAgent\n\n"
        "**RetrievalAgent** runs the agentic retrieval loop: at each step it "
        "decides to retrieve or answer, accumulates docs across iterations, and "
        "falls back to a final LLM call when `max_iterations` is reached.  "
        "Same four-method class shape as all prior Section 6 agents."),
    _code(_P_BASE + _P_DOCUMENT + _P_HELPERS + _P_FORMAT + _P_DECISION + _P_MOCK + """\

# ── Exercise: implement RetrievalAgent ───────────────────────────────────────

class RetrievalAgent:
    \"\"\"An agent that iteratively retrieves documents and answers questions.\"\"\"

    def __init__(self, retriever, llm_fn=None, top_k=3, max_iterations=5):
        self.retriever = retriever
        self._llm_fn = llm_fn
        self._top_k = top_k
        self.max_iterations = max_iterations   # required: prevents infinite loops
        self._history = []

    def ask(self, question):
        # TODO: run the agentic loop:
        # - all_docs = [], steps = []
        # - for iteration in range(self.max_iterations):
        #     context = format_docs(all_docs) or "No documents retrieved yet."
        #     prompt = build_agent_step_prompt(question, context)
        #     response = call_llm(prompt, llm_fn=self._llm_fn)
        #     act = parse_agent_action(response)
        #     if act["action"] == "answer": record + return
        #     else: search retriever, extend all_docs, append step
        # - if loop exhausts: build_retrieval_prompt -> call_llm -> record + return
        return {}

    def history(self):
        # TODO: return a copy of self._history
        return []

    def clear_history(self):
        # TODO: clear self._history
        pass
"""),
    _md("### Checks"),
    _code("""\
checks = 0

retriever = SimpleRetriever()
retriever.add_all([
    Document("Python is a high-level programming language.", {"source": "intro"}),
    Document("Python was created by Guido van Rossum in 1991.", {"source": "history"}),
])

# 1 — RetrievalAgent constructs with max_iterations
try:
    agent = RetrievalAgent(retriever, llm_fn=_mock_retrieval_llm([{"action": "answer", "text": "x"}]))
    assert agent.max_iterations == 5
    checks += 1; print("✅ 1 RetrievalAgent constructs with default max_iterations=5")
except Exception as e:
    print("❌ 1:", e)

# 2 — ask() returns dict with question, docs, answer, steps
try:
    script = [
        {"action": "retrieve", "query": "Python"},
        {"action": "answer",   "text":  "Python is a programming language."},
    ]
    agent = RetrievalAgent(retriever, llm_fn=_mock_retrieval_llm(script))
    r = agent.ask("What is Python?")
    assert "question" in r and "docs" in r and "answer" in r and "steps" in r
    checks += 1; print("✅ 2 ask() returns {question, docs, answer, steps}")
except Exception as e:
    print("❌ 2:", e)

# 3 — answer is returned from the answer action
try:
    script = [{"action": "answer", "text": "Python is great."}]
    agent = RetrievalAgent(retriever, llm_fn=_mock_retrieval_llm(script))
    r = agent.ask("Tell me about Python")
    assert r["answer"] == "Python is great."
    checks += 1; print("✅ 3 answer from 'answer' action is returned correctly")
except Exception as e:
    print("❌ 3:", e)

# 4 — retrieve step extends docs and is recorded
try:
    script = [
        {"action": "retrieve", "query": "Python"},
        {"action": "answer",   "text":  "Done."},
    ]
    agent = RetrievalAgent(retriever, llm_fn=_mock_retrieval_llm(script))
    r = agent.ask("Python?")
    retrieve_steps = [s for s in r["steps"] if s["action"] == "retrieve"]
    assert len(retrieve_steps) >= 1
    assert len(r["docs"]) > 0
    checks += 1; print("✅ 4 retrieve step recorded and docs accumulated")
except Exception as e:
    print("❌ 4:", e)

# 5 — history grows with each ask
try:
    script = [{"action": "answer", "text": "ok"}]
    agent = RetrievalAgent(retriever, llm_fn=_mock_retrieval_llm(script))
    agent.ask("q1"); agent.ask("q2")
    assert len(agent.history()) == 2
    checks += 1; print("✅ 5 history() grows with each ask()")
except Exception as e:
    print("❌ 5:", e)

# 6 — clear_history empties history
try:
    script = [{"action": "answer", "text": "ok"}]
    agent = RetrievalAgent(retriever, llm_fn=_mock_retrieval_llm(script))
    agent.ask("q")
    agent.clear_history()
    assert agent.history() == []
    checks += 1; print("✅ 6 clear_history() empties history")
except Exception as e:
    print("❌ 6:", e)

print(f"\\n{checks}/6 checks passed!")
"""),
])

EXERCISES = [_EX1, _EX2, _EX3, _EX4, _EX5]

# ══════════════════════════════════════════════════════════════════════════════
# YAML lessons
# ══════════════════════════════════════════════════════════════════════════════

LESSONS = [
    """\
day: "086"
lesson: 1
title: "Agentic RAG vs Pipeline RAG"
slides:
  - type: title
    heading: "Retrieval Agents"
    subheading: "From fixed pipelines to agent-directed retrieval"
    narration: >
      Day 13 introduced RAG as a fixed pipeline: retrieve some documents, then
      generate an answer. That works well when the retrieval step always finds
      the right context. But what if the first query misses? What if the answer
      requires combining information from multiple searches? Agentic RAG lets the
      agent decide when to retrieve, what to search for, and when it has gathered
      enough information to answer.

  - type: concept
    label: "Pipeline RAG"
    heading: "Day 13: Always Retrieve, Then Always Generate"
    body: >
      Fixed pipeline: the retrieval step runs exactly once, then generation runs.
    bullets:
      - "Retrieve: embed question, fetch top-k docs from vector store"
      - "Generate: build RAG prompt, call LLM with docs as context"
      - "Problem: retrieval query is always the original question"
      - "Problem: if first retrieval misses, the answer is wrong"
      - "Problem: complex questions often need multiple sub-queries"
    narration: >
      Pipeline RAG is simple and fast. It works well for direct questions where
      the first retrieval almost always returns the right docs. But a question
      like 'what are the tradeoffs between approach A and approach B, and which
      did project X choose' needs at least two retrieval steps: one for approach
      A, one for approach B, and one for project X. A fixed pipeline can't do that.

  - type: concept
    label: "Agentic RAG"
    heading: "Agent-Directed Retrieval"
    body: >
      The agent decides when and what to retrieve.
    bullets:
      - "Agent sees: question + accumulated context so far"
      - "Agent decides: retrieve more (with a custom query) or answer now"
      - "Loop: retrieve -> inspect -> retrieve again? -> answer"
      - "The agent can reformulate the query between steps"
      - "The agent stops when it decides it has enough information"
    narration: >
      Agentic RAG gives the agent control of the retrieval process. It can issue
      a first query, inspect the results, notice a gap, issue a second query with
      a different phrasing, and only then answer. The quality ceiling is higher
      because the agent can recover from a weak first retrieval step.

  - type: concept
    label: "Today's stack"
    heading: "What We Build"
    body: >
      A minimal agentic RAG stack in pure Python.
    bullets:
      - "Document: content string + metadata dict"
      - "SimpleRetriever: word-overlap (Jaccard) search, no ML libraries"
      - "format_docs + build_retrieval_prompt: context formatting"
      - "retrieve_and_answer: single-turn baseline (pipeline version)"
      - "build_agent_step_prompt + parse_agent_action: decision layer"
      - "RetrievalAgent: full agentic loop with max_iterations cap"
    narration: >
      We use word-overlap similarity rather than embeddings so the exercises run
      without any ML libraries. The agentic pattern is identical whether you swap
      in a ChromaDB vector store or a BM25 index. The retriever is injected, so
      you can replace SimpleRetriever with any search backend without touching
      the agent code.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "Pipeline RAG: fixed retrieve-then-generate; one shot"
      - "Agentic RAG: agent controls retrieval; can iterate"
      - "Agent benefits: reformulated queries, multi-step search, self-stopping"
      - "Today: SimpleRetriever + RetrievalAgent, no ML deps"
""",

    """\
day: "086"
lesson: 2
title: "Document and SimpleRetriever"
slides:
  - type: title
    heading: "Document and SimpleRetriever"
    subheading: "The document store layer"
    narration: >
      Before an agent can retrieve anything, it needs a place to store documents
      and a way to rank them by relevance. Document is a simple dataclass.
      SimpleRetriever stores them in a list and ranks by word-overlap similarity.
      No embeddings, no vector indices, no external services required.

  - type: concept
    label: "Document"
    heading: "Content Plus Metadata"
    body: >
      Every document has a text body and an optional metadata dict.
    bullets:
      - "content: the text to be searched and returned as context"
      - "metadata: dict of arbitrary key/value pairs"
      - "Common metadata: source (filename/URL), date, author, chunk_id"
      - "format_docs uses metadata['source'] for citation display"
      - "Same pattern as Day 12's ChromaDB document structure"
    narration: >
      Keeping metadata separate from content is a RAG design principle. The
      content goes into the prompt as context; the metadata goes into the citation
      so the user knows where the information came from. In production you might
      store a URL, a page number, a database row ID, or a timestamp.

  - type: code
    label: "SimpleRetriever"
    heading: "Word-Overlap Search"
    body: >
      Jaccard similarity between query words and document words.
    code: |
      retriever = SimpleRetriever()
      retriever.add(Document("Python is a programming language.", {"source": "intro"}))
      retriever.add(Document("Java is statically typed.", {"source": "java_intro"}))
      retriever.add(Document("Python uses indentation.", {"source": "syntax"}))

      results = retriever.search("Python", top_k=2)
      for doc in results:
          print(doc.metadata["source"], ":", doc.content[:40])
      # intro : Python is a programming language.
      # syntax : Python uses indentation.
    narration: >
      The Jaccard score is the size of the word intersection divided by the size
      of the word union. A query of 'Python programming' against 'Python is a
      programming language' gets 2 shared words out of 6 unique words, so 0.33.
      Against 'The sky is blue' the intersection is empty, score is 0. The top-k
      documents with the highest scores are returned.

  - type: concept
    label: "Limitations"
    heading: "Word Overlap vs Embeddings"
    body: >
      SimpleRetriever is good enough for learning; production needs embeddings.
    bullets:
      - "Word overlap misses synonyms: 'car' won't match 'automobile'"
      - "Embedding models capture semantic similarity: 'car' ~= 'automobile'"
      - "Day 11 covered embeddings; Day 12 covered ChromaDB"
      - "Swap SimpleRetriever for a ChromaDB retriever to get semantic search"
      - "RetrievalAgent accepts any object with a .search(query, top_k) method"
    narration: >
      The retriever is injected into RetrievalAgent, so you can swap
      SimpleRetriever for a ChromaDB collection, an Elasticsearch client, or any
      object that implements search. The agent code stays identical. Today we use
      SimpleRetriever to keep exercises dependency-free.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "Document: content + metadata dict — the atomic unit of RAG"
      - "SimpleRetriever: add/add_all/search/len — pure Python"
      - "Jaccard similarity: word intersection / word union"
      - "search() returns top-k docs sorted by relevance"
      - "Retriever is injectable — swap for any backend"
""",

    """\
day: "086"
lesson: 3
title: "From Docs to Answer"
slides:
  - type: title
    heading: "From Docs to Answer"
    subheading: "format_docs, build_retrieval_prompt, retrieve_and_answer"
    narration: >
      Once the retriever hands back a list of documents, the RAG layer has two
      jobs: format the documents into a context block the LLM can read, and build
      a prompt that instructs the LLM to answer from those documents. The
      retrieve_and_answer function combines both into a single-turn convenience
      function that works as a pipeline RAG baseline.

  - type: concept
    label: "format_docs"
    heading: "Numbered Context Block"
    body: >
      Each document gets a number and a source label for citation.
    bullets:
      - "[1] (wiki) Python is a high-level programming language."
      - "[2] (history) Python was created by Guido van Rossum in 1991."
      - "Numbers let the LLM cite facts: 'Python was created in 1991 [2]'"
      - "Source from metadata['source']; falls back to 'doc1', 'doc2', etc."
      - "Empty list returns 'No documents found.' (agent handles this safely)"
    narration: >
      The numbered format is a citation protocol. By putting numbers in the
      context block, you can prompt the LLM to cite sources, making it easier
      for users to verify claims. If the metadata doesn't have a source key, the
      fallback 'doc1', 'doc2' labels keep the format consistent.

  - type: code
    label: "retrieve_and_answer"
    heading: "Single-Turn RAG Baseline"
    body: >
      Three lines: retrieve, build prompt, call LLM.
    code: |
      retriever = SimpleRetriever()
      retriever.add_all([
          Document("Python was created in 1991.", {"source": "history"}),
          Document("Python uses indentation.", {"source": "syntax"}),
      ])

      result = retrieve_and_answer(
          "When was Python created?",
          retriever,
          top_k=2,
          llm_fn=my_llm,
      )
      print(result["answer"])   # "Python was created in 1991 [1]."
      print(len(result["docs"]))  # 2
    narration: >
      retrieve_and_answer is the fixed-pipeline version. It always retrieves top-k
      docs for the original question and calls the LLM once. This is exactly what
      Day 13 did, but wrapped into a reusable function. RetrievalAgent in the next
      lessons will replace this single step with an iterative decision loop.

  - type: concept
    label: "When to use each"
    heading: "Pipeline vs Agent"
    body: >
      Choose based on your question complexity.
    bullets:
      - "retrieve_and_answer: simple questions, fast, predictable"
      - "RetrievalAgent: multi-hop questions, sub-queries, uncertain retrieval"
      - "A single retrieve often works; use agentic when you see retrieval failures"
      - "RetrievalAgent is slower (multiple LLM calls per question)"
      - "Both functions accept the same retriever and llm_fn"
    narration: >
      In production you might use retrieve_and_answer as the fast path and fall
      back to RetrievalAgent when confidence is low. Or you might always use the
      agent for research-heavy tasks. The choice is a tradeoff between latency,
      cost, and answer quality.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "format_docs: documents -> numbered context block for prompts"
      - "build_retrieval_prompt: wraps context into a full RAG prompt"
      - "retrieve_and_answer: single-turn RAG (pipeline baseline)"
      - "Returns {question, docs, answer} dict"
      - "RetrievalAgent extends this with iteration"
""",

    """\
day: "086"
lesson: 4
title: "The Agent Decision Layer"
slides:
  - type: title
    heading: "The Agent Decision Layer"
    subheading: "build_agent_step_prompt and parse_agent_action"
    narration: >
      At each step of the agentic loop the agent sees the question plus whatever
      context it has accumulated so far, and it must decide: is this enough to
      answer, or should I search for more? build_agent_step_prompt constructs that
      decision prompt. parse_agent_action parses the LLM's JSON response into one
      of two actions: retrieve or answer.

  - type: concept
    label: "Two actions"
    heading: "Retrieve or Answer"
    body: >
      The agent chooses between exactly two actions each step.
    bullets:
      - 'Retrieve: {"action": "retrieve", "query": "search query"}'
      - 'Answer:   {"action": "answer",   "text":  "final answer"}'
      - "The query can differ from the original question — that is the key power"
      - "The agent reformulates: 'Python history' -> 'Guido van Rossum creator'"
      - "Answer terminates the loop; retrieve continues it"
    narration: >
      The query in the retrieve action is what distinguishes agentic RAG from the
      pipeline version. The agent might start by searching for 'Python history',
      read that Python was created by Guido van Rossum, then issue a second
      retrieval for 'Guido van Rossum biography' to get more detail. The pipeline
      version can only use the original question as the search query.

  - type: code
    label: "Decision prompt + parsing"
    heading: "Building and Parsing the Step"
    body: >
      Prompt construction and JSON parsing work together.
    code: |
      import json

      # Step 1: build the decision prompt
      context = "No context retrieved yet."
      prompt = build_agent_step_prompt("Who created Python?", context)
      # system message explains both actions, user message = question + context

      # Step 2: LLM responds (mocked here)
      response = json.dumps({"action": "retrieve", "query": "Python creator history"})

      # Step 3: parse the action
      act = parse_agent_action(response)
      print(act)
      # {"action": "retrieve", "query": "Python creator history"}
    narration: >
      The parsing step is defensive: if the LLM returns bad JSON, safe_parse_json
      returns None and parse_agent_action defaults to a retrieve action with an
      empty query. The agent will then search the retriever with an empty string
      and get some results back. This is worse than a good query, but it keeps the
      loop running rather than crashing the session.

  - type: concept
    label: "Fallback to retrieve"
    heading: "Why Retrieve is the Safe Default"
    body: >
      On parse failure, retrieving is safer than answering incorrectly.
    bullets:
      - "Parse fails -> default to retrieve (continue gathering info)"
      - "Bad query -> retriever returns low-relevance docs (not an error)"
      - "LLM eventually returns a proper 'answer' action"
      - "max_iterations prevents an infinite loop on persistent failures"
      - "Never raises: the agent loop is always in control"
    narration: >
      Choosing retrieve as the fallback action over answer is a deliberate design.
      If we defaulted to answering on a parse failure, the agent might return an
      empty string or a hallucinated answer with no documents. By falling back to
      retrieve, we give the agent another chance to gather information before it
      commits to an answer.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "Two actions: retrieve (with query) and answer (with text)"
      - "build_agent_step_prompt: question + accumulated context -> decision prompt"
      - "parse_agent_action: JSON -> action dict, fallback to retrieve on failure"
      - "The retrieval query can differ from the original question"
      - "Defensive fallback: retrieve is always the safe default"
""",

    """\
day: "086"
lesson: 5
title: "RetrievalAgent — The Full Loop"
slides:
  - type: title
    heading: "RetrievalAgent"
    subheading: "Iterative retrieval with a max_iterations cap"
    narration: >
      RetrievalAgent runs the full agentic loop: build a decision prompt, call the
      LLM, parse the action, retrieve or answer, repeat. It accumulates documents
      across iterations so each step sees more context than the last. The
      max_iterations cap prevents infinite loops. After the cap, it falls back to
      a final LLM call with all accumulated documents.

  - type: concept
    label: "The loop"
    heading: "Step-by-Step Execution"
    body: >
      Each iteration of the agent loop follows the same pattern.
    bullets:
      - "1. context = format_docs(all_docs) or 'No documents retrieved yet.'"
      - "2. prompt = build_agent_step_prompt(question, context)"
      - "3. response = call_llm(prompt)"
      - "4. act = parse_agent_action(response)"
      - "5a. If answer: record, return"
      - "5b. If retrieve: search, extend all_docs, record step, continue"
    narration: >
      The key design choice is passing all accumulated docs on every step. The
      agent sees a growing context as it retrieves more documents. This means it
      can decide 'I now have enough' after the second retrieval without having to
      see the same documents twice. The step list in the result is the audit trail.

  - type: code
    label: "RetrievalAgent usage"
    heading: "Running the Agent"
    body: >
      Build a retriever, add docs, create the agent, ask a question.
    code: |
      retriever = SimpleRetriever()
      retriever.add_all([
          Document("Python was created by Guido van Rossum.", {"source": "history"}),
          Document("Guido van Rossum started Python in 1989.", {"source": "timeline"}),
      ])

      script = [
          {"action": "retrieve", "query": "Python creator"},
          {"action": "answer",   "text":  "Python was created by Guido van Rossum."},
      ]
      agent = RetrievalAgent(retriever, llm_fn=_mock_retrieval_llm(script))

      r = agent.ask("Who created Python?")
      print(r["answer"])    # "Python was created by Guido van Rossum."
      print(r["steps"])     # [{step:1, action:retrieve, ...}, {step:2, action:answer, ...}]
    narration: >
      The mock LLM script replays actions in order. In production, Ollama would
      decide the action based on the actual context. The scripted mock lets the
      gate test the loop mechanics without a live model.

  - type: concept
    label: "max_iterations fallback"
    heading: "Handling the Edge Case"
    body: >
      After max_iterations without an answer, the agent generates one anyway.
    bullets:
      - "Loop runs up to max_iterations times"
      - "If the LLM never returns 'answer', the loop exhausts"
      - "Fallback: build_retrieval_prompt(question, all_docs) -> call_llm"
      - "This uses whatever docs were accumulated as context"
      - "Better than silence — the agent always returns something"
    narration: >
      The max_iterations fallback is the final safety net. It's analogous to
      SimpleAgent's max_iterations cap from Day 79 and PlannerAgent's max_tasks
      from Day 83. Every agentic loop in Section 6 has this cap because local
      models can loop unexpectedly. The fallback uses all accumulated documents,
      so the quality isn't too different from a successful exit.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "RetrievalAgent: iterative loop, accumulates docs across steps"
      - "Each step: build prompt -> call LLM -> parse action -> retrieve or answer"
      - "max_iterations cap with graceful fallback to final generation"
      - "Returns {question, docs, answer, steps} — full audit trail"
      - "Same four-method shape as all Section 6 agents"
""",
]

# ══════════════════════════════════════════════════════════════════════════════
# Project + Solution notebooks
# ══════════════════════════════════════════════════════════════════════════════

_PROJ_PRELUDE = (
    _P_BASE + _P_DOCUMENT + _P_HELPERS + _P_FORMAT + _P_DECISION + _P_MOCK + _P_AGENT
)

_AI_DOCS = [
    ("Neural networks are modelled loosely on the human brain with layers of interconnected nodes.",    "ai_basics"),
    ("Deep learning is a subset of machine learning that uses neural networks with many layers.",       "deep_learning"),
    ("Transformers use self-attention mechanisms to process sequences in parallel.",                     "transformers"),
    ("BERT is a transformer model pre-trained on masked language modelling and next sentence prediction.", "bert"),
    ("GPT models are decoder-only transformers trained to predict the next token.",                     "gpt"),
    ("Reinforcement learning trains agents by rewarding desired behaviour and penalising undesired behaviour.", "rl"),
    ("RAG (Retrieval-Augmented Generation) combines search with language model generation.",             "rag"),
    ("Embeddings map words or sentences to dense numerical vectors that capture meaning.",               "embeddings"),
    ("Fine-tuning adapts a pre-trained model to a specific task using a smaller labelled dataset.",      "fine_tuning"),
    ("Prompt engineering is the practice of crafting inputs to elicit better outputs from language models.", "prompting"),
]

_PROJ_ADD_DOCS = (
    "docs = [\n"
    + "".join(
        f'    Document({repr(content)}, {{"source": {repr(src)}}}),\n'
        for content, src in _AI_DOCS
    )
    + "]\nretriever.add_all(docs)\nprint(f'Loaded {len(retriever)} documents')\n"
)

PROJECT_NB = _nb([
    _md(f"# Day {DAY} Project — Research Agent over AI Documents\n\n"
        "Build a RetrievalAgent over a mini knowledge base of AI topic snippets.  "
        "Ask it questions that require one or more retrieval steps."),
    _code(_PROJ_PRELUDE),
    _md("## Step 1 — Build the Knowledge Base"),
    _code("retriever = SimpleRetriever()\n" + _PROJ_ADD_DOCS),
    _md("## Step 2 — Create the Agent\n\n"
        "Use `_mock_retrieval_llm` for the gate; replace with `llm_fn=None` "
        "for real Ollama."),
    _code("""\
script = [
    {"action": "retrieve", "query": "transformer attention"},
    {"action": "answer",   "text":  "Transformers use self-attention to process sequences in parallel."},
]
# For real Ollama: agent = RetrievalAgent(retriever, llm_fn=None)
agent = RetrievalAgent(retriever, llm_fn=_mock_retrieval_llm(script), max_iterations=5)
print("Agent ready. Tools: retriever with", len(retriever), "docs")
"""),
    _md("## Step 3 — Ask Questions"),
    _code("""\
question = "How do transformers work?"
r = agent.ask(question)
print("Question:", r["question"])
print("Steps taken:", len(r["steps"]))
for s in r["steps"]:
    if s["action"] == "retrieve":
        print(f"  [{s['step']}] Retrieve: '{s['query']}' ({s['found']} docs found)")
    else:
        print(f"  [{s['step']}] Answer: {s['text'][:80]}")
print("\\nAnswer:", r["answer"])
"""),
    _md("## Step 4 — Review History"),
    _code("""\
print(f"Total questions asked: {len(agent.history())}")
for i, entry in enumerate(agent.history(), 1):
    print(f"{i}. Q: {entry['question']}")
    print(f"   A: {entry['answer'][:80]}")
    print(f"   Steps: {len(entry['steps'])} | Docs retrieved: {len(entry['docs'])}")
"""),
])

_SOL_SCRIPTS = [
    [
        {"action": "retrieve", "query": "transformer attention mechanism"},
        {"action": "answer",   "text":  "Transformers use self-attention mechanisms to process sequences in parallel [3]."},
    ],
    [
        {"action": "retrieve", "query": "GPT model architecture"},
        {"action": "answer",   "text":  "GPT models are decoder-only transformers trained to predict the next token [5]."},
    ],
    [
        {"action": "retrieve", "query": "RAG retrieval generation"},
        {"action": "answer",   "text":  "RAG combines search with language model generation [7]."},
    ],
]

_SOL_SETUP = """\
_scripts = %s
_sidx = [0]
def _sol_llm(messages):
    s = _scripts[_sidx[0] %% len(_scripts)]
    _sidx[0] += 1
    return _sol_llm._sub(messages, s)
def _sol_sub(messages, script):
    idx = [0]
    def _fn(m):
        i = min(idx[0], len(script) - 1)
        idx[0] += 1
        import json
        return json.dumps(script[i])
    return _fn(messages)
_sol_llm._sub = _sol_sub
""" % json.dumps(_SOL_SCRIPTS)

_SOL_QUESTIONS = [
    "How do transformers work?",
    "What is a GPT model?",
    "What is RAG?",
]

SOLUTION_NB = _nb([
    _md(f"# Day {DAY} Solution — Research Agent over AI Documents"),
    _code(_PROJ_PRELUDE),
    _code("retriever = SimpleRetriever()\n" + _PROJ_ADD_DOCS),
    _code(_P_MOCK + """\

# script-driven LLM for gate testing
_scripts = """ + json.dumps(_SOL_SCRIPTS) + """
_script_states = [[0] for _ in _scripts]
_qidx = [0]

def _solution_llm(messages):
    si = _qidx[0] % len(_scripts)
    state = _script_states[si]
    script = _scripts[si]
    i = min(state[0], len(script) - 1)
    state[0] += 1
    return json.dumps(script[i])
"""),
    _code("""\
questions = """ + json.dumps(_SOL_QUESTIONS) + """

for q in questions:
    _qidx[0] = questions.index(q)
    for state in _script_states: state[0] = 0
    agent = RetrievalAgent(retriever, llm_fn=_solution_llm, max_iterations=5)
    r = agent.ask(q)
    print(f"Q: {r['question']}")
    print(f"  Steps: {len(r['steps'])}")
    print(f"  Answer: {r['answer'][:100]}")
    print()
"""),
    _code("""\
# Smoke-test: single agent with full scripted run
_for_test = RetrievalAgent(
    retriever,
    llm_fn=_mock_retrieval_llm([
        {"action": "retrieve", "query": "deep learning neural networks"},
        {"action": "answer",   "text":  "Deep learning uses neural networks with many layers [2]."},
    ]),
    max_iterations=5,
)
_r = _for_test.ask("What is deep learning?")
assert len(_r["steps"]) == 2
assert "Deep learning" in _r["answer"]
assert len(_for_test.history()) == 1
_for_test.clear_history()
assert _for_test.history() == []
print("Solution smoke-test passed.")
"""),
])

# ══════════════════════════════════════════════════════════════════════════════
# Gate inline validation
# ══════════════════════════════════════════════════════════════════════════════

GATE_PY = f"""\
import importlib.util, json, sys

spec = importlib.util.spec_from_file_location(
    "{SLUG}", r"{DIR / (SLUG + '.py')}"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# Document
d = mod.Document("Python is great.", {{"source": "test"}})
assert d.content == "Python is great."
assert d.metadata == {{"source": "test"}}
d2 = mod.Document("hello")
assert d2.metadata == {{}}

# SimpleRetriever
r = mod.SimpleRetriever()
r.add(mod.Document("Python is a programming language."))
r.add(mod.Document("The sky is blue."))
r.add(mod.Document("Python uses indentation."))
assert len(r) == 3
results = r.search("Python programming", top_k=2)
assert len(results) == 2
assert all("Python" in d.content or "python" in d.content.lower() for d in results)
assert r.search("anything", top_k=1) != []
assert r.search("xyz123", top_k=0) == []

# Empty retriever
empty_r = mod.SimpleRetriever()
assert empty_r.search("q") == []
assert len(empty_r) == 0

# format_docs
assert mod.format_docs([]) == "No documents found."
docs = [mod.Document("hello world", {{"source": "s1"}}), mod.Document("foo bar")]
text = mod.format_docs(docs)
assert "[1]" in text and "[2]" in text and "s1" in text and "doc2" in text

# build_retrieval_prompt
prompt = mod.build_retrieval_prompt("What is Python?", docs)
assert isinstance(prompt, list) and len(prompt) == 2
assert prompt[0]["role"] == "system" and prompt[1]["role"] == "user"
combined = " ".join(m["content"] for m in prompt)
assert "What is Python?" in combined and "hello world" in combined

# retrieve_and_answer
retriever = mod.SimpleRetriever()
retriever.add_all([
    mod.Document("Python is a programming language."),
    mod.Document("Java is statically typed."),
])
mock_llm = lambda messages: "Python answer."
res = mod.retrieve_and_answer("What is Python?", retriever, llm_fn=mock_llm)
assert res["answer"] == "Python answer."
assert len(res["docs"]) > 0
assert res["question"] == "What is Python?"

# build_agent_step_prompt
p = mod.build_agent_step_prompt("What is Python?", "No context retrieved yet.")
assert p[0]["role"] == "system" and p[1]["role"] == "user"
assert "retrieve" in p[0]["content"] and "answer" in p[0]["content"]

# parse_agent_action — answer
act = mod.parse_agent_action(json.dumps({{"action": "answer", "text": "42"}}))
assert act["action"] == "answer" and act["text"] == "42"

# parse_agent_action — retrieve
act2 = mod.parse_agent_action(json.dumps({{"action": "retrieve", "query": "Python"}}))
assert act2["action"] == "retrieve" and act2["query"] == "Python"

# parse_agent_action — fallback
act3 = mod.parse_agent_action("not json")
assert act3["action"] == "retrieve"

# RetrievalAgent — answer on first step
script_ans = [{{"action": "answer", "text": "Python is great."}}]
agent = mod.RetrievalAgent(retriever, llm_fn=mod._mock_retrieval_llm(script_ans))
r = agent.ask("What is Python?")
assert r["answer"] == "Python is great."
assert r["question"] == "What is Python?"
assert len(r["steps"]) >= 1

# RetrievalAgent — retrieve then answer
script_ra = [
    {{"action": "retrieve", "query": "Python"}},
    {{"action": "answer", "text": "Python is a programming language."}},
]
agent2 = mod.RetrievalAgent(retriever, llm_fn=mod._mock_retrieval_llm(script_ra), max_iterations=5)
r2 = agent2.ask("Python?")
assert r2["answer"] == "Python is a programming language."
assert len(r2["steps"]) == 2
assert r2["steps"][0]["action"] == "retrieve"
assert r2["steps"][1]["action"] == "answer"
assert len(r2["docs"]) > 0

# RetrievalAgent — history
assert len(agent2.history()) == 1
agent2.clear_history()
assert agent2.history() == []

# RetrievalAgent — max_iterations fallback
endless = [{{"action": "retrieve", "query": "x"}}] * 10
agent3 = mod.RetrievalAgent(retriever, llm_fn=mod._mock_retrieval_llm(endless), max_iterations=3)
agent3._llm_fn = lambda m: json.dumps({{"action": "retrieve", "query": "x"}}) if "research agent" in m[0]["content"].lower() else "fallback answer"
r3 = agent3.ask("anything?")
assert r3["answer"] is not None
assert len(r3["steps"]) >= 3

print("Gate: all inline checks passed")
"""

# ══════════════════════════════════════════════════════════════════════════════
# main
# ══════════════════════════════════════════════════════════════════════════════

def main():
    import subprocess, sys

    (DIR / "exercises").mkdir(parents=True, exist_ok=True)
    (DIR / "lessons").mkdir(parents=True, exist_ok=True)
    (DIR / "project" / "solution").mkdir(parents=True, exist_ok=True)

    (DIR / f"{SLUG}.py").write_text(DELIVERABLE, encoding="utf-8")
    (DIR / "project" / "solution" / f"{SLUG}.py").write_text(DELIVERABLE, encoding="utf-8")

    for i, nb in enumerate(EXERCISES, 1):
        (DIR / "exercises" / f"exercise_{i:02d}.ipynb").write_text(
            json.dumps(nb, indent=1), encoding="utf-8")

    for i, yaml_text in enumerate(LESSONS, 1):
        (DIR / "lessons" / f"day_{DAY}_lesson_{i:02d}.yaml").write_text(
            yaml_text, encoding="utf-8")

    (DIR / "project" / "project.ipynb").write_text(
        json.dumps(PROJECT_NB, indent=1), encoding="utf-8")
    (DIR / "project" / "solution" / "solution.ipynb").write_text(
        json.dumps(SOLUTION_NB, indent=1), encoding="utf-8")

    print(f"[gen_day{DAY}] files written — running gate …")

    # precaution 2a: inline validation
    result = subprocess.run(
        ["conda", "run", "-n", "ai-course", "--no-capture-output",
         "python", "-c", GATE_PY],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print("GATE FAILED (inline)\n", result.stdout, result.stderr)
        sys.exit(1)
    print(result.stdout.strip())

    # precaution 2b: nbclient
    nb_paths = (
        [DIR / "exercises" / f"exercise_{i:02d}.ipynb" for i in range(1, 6)]
        + [DIR / "project" / "solution" / "solution.ipynb"]
    )
    nbclient_script = "import nbformat, nbclient\n"
    for p in nb_paths:
        nbclient_script += (
            f"nb = nbformat.read(r'{p}', as_version=4)\n"
            f"nbclient.NotebookClient(nb, timeout=60, kernel_name='python3',"
            f" resources={{'metadata': {{'path': r'{p.parent}'}}}}).execute()\n"
            f"errs = [c for c in nb.cells if any(o.get('output_type')=='error'"
            f" for o in c.get('outputs',[]))]\n"
            f"assert not errs, 'Notebook {p.name} had errors'\n"
            f"print('  OK {p.name}')\n"
        )
    result2 = subprocess.run(
        ["conda", "run", "-n", "ai-course", "--no-capture-output",
         "python", "-c", nbclient_script],
        capture_output=True, text=True,
    )
    if result2.returncode != 0:
        print("GATE FAILED (nbclient)\n", result2.stdout, result2.stderr)
        sys.exit(1)
    print(result2.stdout.strip())

    # precaution 3: adversarial grep
    import re
    src = DELIVERABLE + "\n".join(
        json.dumps(nb) for nb in EXERCISES + [PROJECT_NB, SOLUTION_NB]
    )
    for pattern in ["openai", "anthropic", r"\beval\b"]:
        if re.search(pattern, src):
            print(f"GATE FAILED: banned pattern '{pattern}' found")
            sys.exit(1)
    print("Gate: adversarial grep clean")
    print(f"\n[gen_day{DAY}] gate-green ✓")


if __name__ == "__main__":
    main()
