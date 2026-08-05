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
import json
from dataclasses import dataclass, field

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
    return "\n".join(lines)


def build_retrieval_prompt(question, docs):
    """Build a RAG answer prompt from retrieved documents.

    Instructs the model to answer using only the provided documents and to
    cite document numbers when referencing specific facts.
    """
    context = format_docs(docs)
    system  = "\n".join([
        "You are a helpful assistant.",
        "Answer the question using ONLY the provided documents.",
        "If the answer is not in the documents, say: I don't have enough information.",
        "Cite document numbers like [1] when referencing specific facts.",
    ])
    user = "Documents:\n" + context + "\n\nQuestion: " + str(question)
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

# ── agent decision layer ──────────────────────────────────────────────────────

def build_agent_step_prompt(question, context):
    """Build the decision prompt for one step of the retrieval agent loop.

    The agent sees the question and accumulated context, then decides:
        {"action": "retrieve", "query": "..."}  -- search for more info
        {"action": "answer",   "text":  "..."}  -- respond with final answer
    """
    has_context = bool(context) and context != "No documents found."
    ctx_line    = "Current context:\n" + context if has_context else "No context retrieved yet."
    system      = "\n".join([
        "You are a research agent. Decide your next action.",
        'To search: {"action": "retrieve", "query": "your search query"}',
        'To answer: {"action": "answer",   "text":  "your final answer"}',
        "Use retrieve to gather information; use answer when you have enough.",
        "Reply with ONLY valid JSON.",
    ])
    user = "Question: " + str(question) + "\n\n" + ctx_line
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
