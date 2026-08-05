"""multi_agent.py — Day 084: Multi-Agent Systems.

Days 79-83 gave one agent tools, reasoning, memory, and planning. Today two
agents collaborate: a ResearcherAgent gathers facts, then hands off to a
WriterAgent that turns them into a polished document. An Orchestrator owns both,
runs the pipeline, and keeps a record of every Handoff between agents.

Pieces:
  safe_parse_json / call_llm  - reused (Day 79)
  build_researcher_prompt / ResearcherAgent   - specialist researcher
  build_writer_prompt / WriterAgent           - specialist writer
  Handoff                                     - explicit data transfer between agents
  summarize_handoffs                          - render the handoff chain as text
  run_duo                                     - chain researcher -> writer
  Orchestrator                                - owns both agents; runs and records

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

# ── researcher specialist ─────────────────────────────────────────────────────
def build_researcher_prompt(query):
    """Build a prompt for the researcher role: gather facts on a topic."""
    system = "\n".join([
        "You are a research specialist. Your job is to gather relevant facts and",
        "key information about the topic given to you.",
        "",
        "Return a structured list of the most important findings.",
        "Be factual, concise, and cover the main points.",
    ])
    return [{"role": "system", "content": system},
            {"role": "user", "content": "Research topic: " + str(query)}]


class ResearcherAgent:
    """A specialist that researches a topic and returns structured findings.

    Each call to research() returns a string of findings and records the
    exchange in history. The agent has one job: gather facts. It passes its
    output to the next agent via a Handoff — it does not write, review, or
    plan.

    Example::

        researcher = ResearcherAgent(llm_fn=my_llm_fn)
        findings = researcher.research("topological sort algorithms")
    """

    def __init__(self, llm_fn=None):
        self._llm_fn = llm_fn
        self._history = []

    def research(self, query):
        """Research a query and return findings as a string."""
        messages = build_researcher_prompt(query)
        findings = call_llm(messages, llm_fn=self._llm_fn)
        self._history.append({"query": query, "findings": findings})
        return findings

    def history(self):
        """Return a copy of the research history."""
        return list(self._history)

    def clear_history(self):
        """Clear the history in place."""
        self._history.clear()

# ── writer specialist ─────────────────────────────────────────────────────────
def build_writer_prompt(findings, style="concise", instructions=None):
    """Build a prompt for the writer role: turn findings into a document."""
    system_parts = [
        "You are a writing specialist. Turn the provided findings into",
        "a polished, well-structured document.",
        "Style: " + str(style) + ".",
    ]
    if instructions:
        system_parts.append("Additional instructions: " + str(instructions))
    system = "\n".join(system_parts)
    user = "Findings:\n" + str(findings)
    return [{"role": "system", "content": system},
            {"role": "user", "content": user}]


class WriterAgent:
    """A specialist that turns research findings into a polished document.

    The writer has one job: take findings (a string from the ResearcherAgent
    or any other source) and produce a well-structured document. The style
    controls the tone (e.g. 'concise', 'detailed', 'formal').

    Example::

        writer = WriterAgent(llm_fn=my_llm_fn, style="concise")
        document = writer.write(findings)
    """

    def __init__(self, llm_fn=None, style="concise"):
        self._llm_fn = llm_fn
        self.style = style
        self._history = []

    def write(self, findings, instructions=None):
        """Write a document from findings. Returns the document string."""
        messages = build_writer_prompt(findings, style=self.style,
                                       instructions=instructions)
        document = call_llm(messages, llm_fn=self._llm_fn)
        self._history.append({"findings": findings, "document": document})
        return document

    def history(self):
        """Return a copy of the writing history."""
        return list(self._history)

    def clear_history(self):
        """Clear the history in place."""
        self._history.clear()

# ── handoffs: explicit data passing between agents ────────────────────────────
from dataclasses import dataclass, field


@dataclass
class Handoff:
    """An explicit record of data passed from one agent to the next.

    Attributes:
        from_agent: name of the sending agent ('researcher', 'writer', ...).
        to_agent:   name of the receiving agent.
        content:    the data being passed (findings string, document, ...).
        metadata:   optional dict for any extra context (topic, style, ...).
    """
    from_agent: str
    to_agent: str
    content: str
    metadata: dict = field(default_factory=dict)


def summarize_handoffs(handoffs):
    """Render the handoff chain as a human-readable text for debugging.

    Each line shows the sender, receiver, and the first 80 characters of the
    content, so you can see the full flow at a glance.
    """
    lines = []
    for h in handoffs:
        preview = h.content[:80].replace("\n", " ")
        lines.append(h.from_agent + " -> " + h.to_agent + ": " + preview)
    return "\n".join(lines)

# ── the researcher-writer pipeline ───────────────────────────────────────────
def run_duo(task, researcher, writer):
    """Chain a ResearcherAgent then a WriterAgent for one task.

    The researcher gathers findings; a Handoff carries them to the writer;
    the writer produces the document; a second Handoff records the output.

    Returns {"findings": str, "document": str, "handoffs": list[Handoff]}.
    """
    findings = researcher.research(task)
    h1 = Handoff("researcher", "writer", findings, metadata={"task": str(task)})
    document = writer.write(findings)
    h2 = Handoff("writer", "user", document, metadata={"task": str(task)})
    return {"findings": findings, "document": document, "handoffs": [h1, h2]}

# ── the orchestrator ──────────────────────────────────────────────────────────
class Orchestrator:
    """Owns specialist agents; coordinates the researcher -> writer pipeline.

    An Orchestrator is one object that owns a ResearcherAgent and a WriterAgent,
    runs them in sequence for each task, and keeps a record of every run and
    every Handoff. Give it a task, get back findings, a document, and the full
    handoff trail.

    Example::

        orch = Orchestrator(llm_fn=my_llm_fn)
        result = orch.run("What is the CAP theorem?")
        print(result["document"])
        print(summarize_handoffs(orch.handoffs()))
    """

    def __init__(self, llm_fn=None, style="concise"):
        self.researcher = ResearcherAgent(llm_fn=llm_fn)
        self.writer = WriterAgent(llm_fn=llm_fn, style=style)
        self._runs = []

    def run(self, task):
        """Research then write. Returns {"findings","document","handoffs"}."""
        result = run_duo(task, self.researcher, self.writer)
        self._runs.append({"task": task, **result})
        return result

    def handoffs(self):
        """All Handoff objects across every run, in order."""
        all_h = []
        for r in self._runs:
            all_h.extend(r.get("handoffs", []))
        return all_h

    def history(self):
        """Return a copy of the run history."""
        return list(self._runs)

    def clear_history(self):
        """Clear history and per-agent histories in place."""
        self._runs.clear()
        self.researcher.clear_history()
        self.writer.clear_history()
