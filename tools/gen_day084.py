#!/usr/bin/env python3
"""gen_day084.py — generate Day 084: Multi-Agent Systems."""
from pathlib import Path
import json

ROOT    = Path(__file__).parent.parent
DAY     = "084"
SECTION = "06_agents"
OUT     = ROOT / SECTION / f"day_{DAY}"

(OUT / "exercises").mkdir(parents=True, exist_ok=True)
(OUT / "lessons").mkdir(parents=True, exist_ok=True)
(OUT / "project" / "solution").mkdir(parents=True, exist_ok=True)

# ── deliverable fragments (composed into multi_agent.py AND reused as ─────────
# ── given-code / embedded solutions in the exercises, so they stay in sync) ────

_DOC = '''\
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

_FRAG_RESEARCHER = '''\

# ── researcher specialist ─────────────────────────────────────────────────────
def build_researcher_prompt(query):
    """Build a prompt for the researcher role: gather facts on a topic."""
    system = "\\n".join([
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
'''

_FRAG_WRITER = '''\

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
    system = "\\n".join(system_parts)
    user = "Findings:\\n" + str(findings)
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
'''

_FRAG_HANDOFF = '''\

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
        preview = h.content[:80].replace("\\n", " ")
        lines.append(h.from_agent + " -> " + h.to_agent + ": " + preview)
    return "\\n".join(lines)
'''

_FRAG_PIPELINE = '''\

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
'''

_FRAG_ORCHESTRATOR = '''\

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
'''

_MULTI_AGENT_SRC = (_DOC + _FRAG_HELPERS + _FRAG_RESEARCHER + _FRAG_WRITER
                    + _FRAG_HANDOFF + _FRAG_PIPELINE + _FRAG_ORCHESTRATOR)


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
def _mock_multi(findings='Finding: AI agents collaborate.', document='Doc: Agents work together.'):
    \"\"\"Branch on system message: 'research specialist' -> findings, else -> document.\"\"\"
    def _fn(messages):
        system = messages[0]['content'] if messages else ''
        if 'research specialist' in system.lower():
            return findings
        return document
    return _fn
"""

# ── EX1: ResearcherAgent ─────────────────────────────────────────────────────
_EX1_GIVEN = _MOCK_HELPER + _FRAG_HELPERS

_EX1_STUB = """\
def build_researcher_prompt(query):
    \"\"\"Build a prompt for the researcher role: gather facts on a topic.\"\"\"
    raise NotImplementedError

class ResearcherAgent:
    \"\"\"A specialist that researches a topic and returns structured findings.\"\"\"

    def __init__(self, llm_fn=None):
        raise NotImplementedError

    def research(self, query):
        raise NotImplementedError

    def history(self):
        raise NotImplementedError

    def clear_history(self):
        raise NotImplementedError
"""

_EX1_CHECKS = r"""
score, total = 0, 5
try:
    msgs = build_researcher_prompt('topological sort')
    assert msgs[0]['role'] == 'system' and 'research' in msgs[0]['content'].lower()
    assert msgs[1]['content'].startswith('Research topic:')
    score += 1; print("✅ build_researcher_prompt has the right shape")

    r = ResearcherAgent(llm_fn=_mock_multi(findings='Fact: X.'))
    out = r.research('AI agents')
    assert out == 'Fact: X.'
    score += 1; print("✅ research() returns the LLM output")

    assert len(r.history()) == 1 and r.history()[0]['query'] == 'AI agents'
    score += 1; print("✅ history records each call")

    r.history().clear()
    assert len(r.history()) == 1
    score += 1; print("✅ history() returns a copy, not the live list")

    r.clear_history()
    assert len(r.history()) == 0
    score += 1; print("✅ clear_history() empties in place")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX1 = nb([
    md("# Day 084 — Exercise 1: The Researcher Agent\n\n"
       "**What you'll build:** `build_researcher_prompt` and `ResearcherAgent` — a "
       "specialist whose only job is to gather facts on a topic and return them as "
       "a string.\n\n"
       "**Why it matters:** specialisation is the core idea of multi-agent systems. "
       "A researcher that only researches, and a writer that only writes, each does "
       "its job better than one agent trying to do both. The specialist pattern is "
       "also reusable: a research agent can feed a planner, a writer, or a reviewer "
       "— because its interface is a simple `research(query) -> str`."),
    code(_EX1_GIVEN),
    md("## Task\n\n"
       "1. `build_researcher_prompt(query)` — a `system` message orienting the agent "
       "as a research specialist (gather facts, be concise and factual); a `user` "
       "message: `'Research topic: ' + query`.\n"
       "2. `ResearcherAgent(llm_fn=None)` — `research(query)` calls `call_llm` with "
       "the prompt and records `{'query', 'findings'}` in `_history`; returns the "
       "findings string. `history()` returns a copy; `clear_history()` empties in "
       "place."),
    md("## Your Implementation"),
    code(_EX1_STUB),
    code(_FRAG_RESEARCHER),
    md("## Automated checks"),
    code(_EX1_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _FRAG_RESEARCHER + "```\n\n"
       "**Why does the researcher *only* research?** Single responsibility makes "
       "each agent predictable and replaceable. If the researcher also tried to "
       "write, you could not swap it for a different researcher without rewriting "
       "both jobs. The clean interface — `research(query) -> str` — is what lets "
       "any downstream agent (writer, planner, reviewer) consume its output.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_01.ipynb", EX1)

# ── EX2: WriterAgent ─────────────────────────────────────────────────────────
_EX2_GIVEN = _MOCK_HELPER + _FRAG_HELPERS + _FRAG_RESEARCHER

_EX2_STUB = """\
def build_writer_prompt(findings, style='concise', instructions=None):
    \"\"\"Build a prompt for the writer role: turn findings into a document.\"\"\"
    raise NotImplementedError

class WriterAgent:
    \"\"\"A specialist that turns research findings into a polished document.\"\"\"

    def __init__(self, llm_fn=None, style='concise'):
        raise NotImplementedError

    def write(self, findings, instructions=None):
        raise NotImplementedError

    def history(self):
        raise NotImplementedError

    def clear_history(self):
        raise NotImplementedError
"""

_EX2_CHECKS = r"""
score, total = 0, 5
try:
    msgs = build_writer_prompt('Fact: X.', style='formal')
    assert msgs[0]['role'] == 'system' and 'formal' in msgs[0]['content'].lower()
    assert 'Fact: X.' in msgs[1]['content']
    score += 1; print("✅ build_writer_prompt includes style and findings")

    w = WriterAgent(llm_fn=_mock_multi(document='The document.'), style='concise')
    doc = w.write('some findings')
    assert doc == 'The document.'
    score += 1; print("✅ write() returns the LLM output")

    assert len(w.history()) == 1 and 'findings' in w.history()[0]
    score += 1; print("✅ history records each write")

    w.history().clear()
    assert len(w.history()) == 1
    score += 1; print("✅ history() returns a copy")

    w.clear_history()
    assert len(w.history()) == 0
    score += 1; print("✅ clear_history() empties in place")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX2 = nb([
    md("# Day 084 — Exercise 2: The Writer Agent\n\n"
       "**What you'll build:** `build_writer_prompt` and `WriterAgent` — a "
       "specialist that takes findings (from the researcher or any other source) "
       "and produces a polished document.\n\n"
       "**Why it matters:** the writer is the second half of the collaboration. "
       "It receives findings as a plain string and has full freedom to shape the "
       "output — the style (concise, detailed, formal) is set at construction time "
       "so the same agent can serve different audiences. The clean interface — "
       "`write(findings) -> str` — mirrors the researcher's."),
    code(_EX2_GIVEN),
    md("## Task\n\n"
       "1. `build_writer_prompt(findings, style='concise', instructions=None)` — a "
       "`system` message orienting the agent as a writing specialist with the given "
       "style; append `instructions` to the system if provided; a `user` message "
       "with the findings.\n"
       "2. `WriterAgent(llm_fn=None, style='concise')` — `write(findings, "
       "instructions=None)` calls `call_llm` and records `{'findings', 'document'}` "
       "in `_history`; returns the document string. `history()` copy; "
       "`clear_history()` in place."),
    md("## Your Implementation"),
    code(_EX2_STUB),
    code(_FRAG_WRITER),
    md("## Automated checks"),
    code(_EX2_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _FRAG_WRITER + "```\n\n"
       "**Why set style at construction, not per call?** Style is a property of "
       "the agent's *role* in this pipeline — a formal-writing agent stays formal "
       "across all its calls. If you want a different style, create a new "
       "WriterAgent. Binding it at construction makes each agent's behavior "
       "predictable and stable.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_02.ipynb", EX2)

# ── EX3: Handoff + summarize_handoffs ────────────────────────────────────────
_EX3_GIVEN = _MOCK_HELPER + _FRAG_HELPERS + _FRAG_RESEARCHER + _FRAG_WRITER

_EX3_STUB = """\
from dataclasses import dataclass, field

@dataclass
class Handoff:
    \"\"\"An explicit record of data passed from one agent to the next.\"\"\"
    from_agent: str = ''      # TODO: correct type + all four fields
    to_agent: str = ''
    content: str = ''

def summarize_handoffs(handoffs):
    \"\"\"Render the handoff chain as text: one 'from -> to: preview' line each.\"\"\"
    raise NotImplementedError
"""

_EX3_CHECKS = r"""
score, total = 0, 5
try:
    h = Handoff('researcher', 'writer', 'here are the facts')
    assert h.from_agent == 'researcher' and h.to_agent == 'writer'
    assert h.content == 'here are the facts'
    score += 1; print("✅ Handoff stores from_agent, to_agent, content")

    assert h.metadata == {}
    h2 = Handoff('a', 'b', 'x', metadata={'key': 'val'})
    assert h2.metadata == {'key': 'val'}
    score += 1; print("✅ metadata defaults to {} and can be set")

    summary = summarize_handoffs([h, h2])
    assert 'researcher -> writer' in summary and 'a -> b' in summary
    score += 1; print("✅ summarize_handoffs renders the chain")

    long_content = 'x' * 200
    h_long = Handoff('a', 'b', long_content)
    line = summarize_handoffs([h_long]).splitlines()[0]
    assert len(line) < 200           # preview is capped, not the full content
    score += 1; print("✅ summarize_handoffs truncates long content to a preview")

    assert summarize_handoffs([]) == ''
    score += 1; print("✅ summarize_handoffs handles an empty list")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX3 = nb([
    md("# Day 084 — Exercise 3: Handoffs — Explicit Data Passing\n\n"
       "**What you'll build:** the `Handoff` dataclass and `summarize_handoffs` — "
       "a record of what was passed from one agent to the next, and a way to render "
       "the full handoff chain at a glance.\n\n"
       "**Why it matters:** in a multi-agent system, data flows from agent to agent. "
       "Without explicit handoffs, that flow is invisible — you have to guess what "
       "the researcher passed to the writer. A `Handoff` makes it an auditable "
       "record: who sent what to whom, and with what metadata. "
       "`summarize_handoffs` turns that record into a one-glance debug trace, "
       "analogous to Day 80's `trace` on the ReAct agent."),
    code(_EX3_GIVEN),
    md("## Task\n\n"
       "1. `Handoff` dataclass — four fields: `from_agent: str`, `to_agent: str`, "
       "`content: str`, `metadata: dict = field(default_factory=dict)`.\n"
       "2. `summarize_handoffs(handoffs) -> str` — one line per handoff: "
       "`'from -> to: <first 80 chars of content>'`. Return `''` for an empty list."),
    md("## Your Implementation"),
    code(_EX3_STUB),
    code(_FRAG_HANDOFF),
    md("## Automated checks"),
    code(_EX3_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _FRAG_HANDOFF + "```\n\n"
       "**Why make handoffs explicit instead of just chaining function calls?** "
       "An explicit `Handoff` is an audit trail. When a multi-agent run goes wrong, "
       "you want to know exactly what the researcher sent to the writer — not just "
       "that something went wrong in the middle. `summarize_handoffs` gives you that "
       "trace in one print call.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_03.ipynb", EX3)

# ── EX4: run_duo ─────────────────────────────────────────────────────────────
_EX4_GIVEN = (_MOCK_HELPER + _FRAG_HELPERS + _FRAG_RESEARCHER + _FRAG_WRITER
              + _FRAG_HANDOFF)

_EX4_STUB = """\
def run_duo(task, researcher, writer):
    \"\"\"Chain a ResearcherAgent then a WriterAgent for one task.
    Returns {'findings': str, 'document': str, 'handoffs': list[Handoff]}.
    \"\"\"
    raise NotImplementedError
"""

_EX4_CHECKS = r"""
score, total = 0, 5
try:
    researcher = ResearcherAgent(llm_fn=_mock_multi(findings='Key fact: X.'))
    writer = WriterAgent(llm_fn=_mock_multi(document='Final doc.'))

    result = run_duo('AI agents', researcher, writer)
    assert 'findings' in result and 'document' in result and 'handoffs' in result
    score += 1; print("✅ run_duo returns {findings, document, handoffs}")

    assert result['findings'] == 'Key fact: X.'
    assert result['document'] == 'Final doc.'
    score += 1; print("✅ findings and document are the agents' outputs")

    assert len(result['handoffs']) == 2
    score += 1; print("✅ two handoffs: researcher->writer and writer->user")

    h1, h2 = result['handoffs']
    assert h1.from_agent == 'researcher' and h1.to_agent == 'writer'
    assert h1.content == 'Key fact: X.'
    score += 1; print("✅ first handoff carries findings from researcher to writer")

    assert h2.from_agent == 'writer' and h2.to_agent == 'user'
    assert h2.content == 'Final doc.'
    score += 1; print("✅ second handoff carries document from writer to user")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX4 = nb([
    md("# Day 084 — Exercise 4: run_duo — The Pipeline\n\n"
       "**What you'll build:** `run_duo` — a free function that chains the "
       "ResearcherAgent and WriterAgent into a pipeline, creating a `Handoff` at "
       "each transition.\n\n"
       "**Why it matters:** `run_duo` is where the two agents actually collaborate. "
       "The researcher gathers findings; a Handoff carries them to the writer; the "
       "writer produces the document; a second Handoff records the output. The "
       "return dict gives the caller everything — the intermediate findings, the "
       "final document, and the audit trail."),
    code(_EX4_GIVEN),
    md("## Task\n\n"
       "`run_duo(task, researcher, writer) -> dict`\n\n"
       "1. `findings = researcher.research(task)`\n"
       "2. `h1 = Handoff('researcher', 'writer', findings, metadata={'task': task})`\n"
       "3. `document = writer.write(findings)`\n"
       "4. `h2 = Handoff('writer', 'user', document, metadata={'task': task})`\n"
       "5. Return `{'findings': findings, 'document': document, 'handoffs': [h1, h2]}`"),
    md("## Your Implementation"),
    code(_EX4_STUB),
    code(_FRAG_PIPELINE),
    md("## Automated checks"),
    code(_EX4_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _FRAG_PIPELINE + "```\n\n"
       "**Why a free function and not a method?** `run_duo` takes agents as "
       "arguments rather than owning them — so you can pass any researcher and any "
       "writer, including mocks or future specialists. The Orchestrator (next "
       "exercise) *owns* the agents and calls `run_duo`; callers that want full "
       "control can skip the orchestrator and call `run_duo` directly.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_04.ipynb", EX4)

# ── EX5: Orchestrator ────────────────────────────────────────────────────────
_EX5_GIVEN = (_MOCK_HELPER + _FRAG_HELPERS + _FRAG_RESEARCHER + _FRAG_WRITER
              + _FRAG_HANDOFF + _FRAG_PIPELINE)

_EX5_STUB = """\
class Orchestrator:
    \"\"\"Owns specialist agents; coordinates the researcher -> writer pipeline.\"\"\"

    def __init__(self, llm_fn=None, style='concise'):
        raise NotImplementedError

    def run(self, task):
        \"\"\"Research then write. Returns {'findings','document','handoffs'}.\"\"\"
        raise NotImplementedError

    def handoffs(self):
        \"\"\"All Handoff objects across every run, in order.\"\"\"
        raise NotImplementedError

    def history(self):
        raise NotImplementedError

    def clear_history(self):
        raise NotImplementedError
"""

_EX5_CHECKS = r"""
score, total = 0, 6
try:
    orch = Orchestrator(llm_fn=_mock_multi(findings='Fact A.', document='Doc A.'))

    result = orch.run('first task')
    assert result['findings'] == 'Fact A.' and result['document'] == 'Doc A.'
    score += 1; print("✅ Orchestrator.run() returns the pipeline result")

    orch.run('second task')
    assert len(orch.history()) == 2
    score += 1; print("✅ history records every run")

    orch.history().clear()
    assert len(orch.history()) == 2
    score += 1; print("✅ history() returns a copy, not the live list")

    assert len(orch.handoffs()) == 4   # 2 runs × 2 handoffs each
    h0 = orch.handoffs()[0]
    assert h0.from_agent == 'researcher' and h0.to_agent == 'writer'
    score += 1; print("✅ handoffs() accumulates all Handoffs across runs")

    assert isinstance(orch.researcher, ResearcherAgent)
    assert isinstance(orch.writer, WriterAgent)
    score += 1; print("✅ orchestrator exposes its specialist agents")

    orch.clear_history()
    assert len(orch.history()) == 0 and len(orch.handoffs()) == 0
    score += 1; print("✅ clear_history() empties runs (and per-agent histories)")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX5 = nb([
    md("# Day 084 — Exercise 5: Orchestrator\n\n"
       "**What you'll build:** `Orchestrator` — the coordinator that owns the "
       "specialist agents, runs the pipeline, and accumulates every handoff across "
       "every run.\n\n"
       "**Why it matters:** `run_duo` is the mechanism; the Orchestrator is the "
       "manager. It creates and owns the agents, exposes a single `.run(task)` "
       "entry point, and keeps the complete history and handoff trail. Scale it to "
       "more agents and you have a multi-agent system; the caller still sees one "
       "object with one method."),
    code(_EX5_GIVEN),
    md("## Task\n\n"
       "`Orchestrator(llm_fn=None, style='concise')`\n\n"
       "1. `__init__` — create `self.researcher = ResearcherAgent(llm_fn=llm_fn)` "
       "and `self.writer = WriterAgent(llm_fn=llm_fn, style=style)`; `self._runs = []`.\n"
       "2. `run(task)` — `result = run_duo(task, self.researcher, self.writer)`; "
       "append `{'task': task, **result}` to `_runs`; return `result`.\n"
       "3. `handoffs()` — flatten `r['handoffs']` from every run into one list.\n"
       "4. `history()` — copy; `clear_history()` — `_runs.clear()` + call "
       "`clear_history()` on both agents."),
    md("## Your Implementation"),
    code(_EX5_STUB),
    code(_FRAG_ORCHESTRATOR),
    md("## Automated checks"),
    code(_EX5_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _FRAG_ORCHESTRATOR + "```\n\n"
       "**Why does `clear_history` also clear the agents' histories?** The "
       "orchestrator owns the agents. If you clear the orchestrator's runs but "
       "leave the researcher and writer with stale histories, they are in an "
       "inconsistent state. Clearing both keeps the system coherent — one "
       "responsibility, one place.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_05.ipynb", EX5)

# ── YAML lessons ──────────────────────────────────────────────────────────────
_LESSON_01 = """\
day: "084"
lesson: 1
title: "Specialist Agents and Roles"
slides:
  - type: title
    heading: "Multi-Agent Systems"
    subheading: "Specialist agents that collaborate"
    narration: >
      Days 79 to 83 gave one agent tools, reasoning, memory, and planning. Today
      we add collaboration: two agents working together, each doing one job well.
      The first specialist is the researcher. This lesson builds it and explains why
      splitting a complex task into specialist roles produces better results than
      asking one agent to do everything.

  - type: concept
    label: "Why specialize"
    heading: "One Agent, One Job"
    body: >
      A specialist agent does one thing well and hands off the rest.
    bullets:
      - "Generalist: research AND write AND review - prompt gets confused"
      - "Specialist: one system prompt, one focused task"
      - "ResearcherAgent: gather facts, return findings"
      - "WriterAgent: take findings, produce a document"
      - "Each is predictable, replaceable, and reusable"
    narration: >
      When you ask one agent to research a topic, write it up, check for errors, and
      format it nicely, the system prompt becomes a contradiction - researcher logic
      fights writer logic. Specialist agents fix this by giving each agent one job
      and one clear system prompt. The ResearcherAgent gathers facts and nothing else.
      The WriterAgent takes those facts and produces a document. Each is small enough
      to understand and test independently, and replaceable without breaking the
      other.

  - type: code
    label: "ResearcherAgent"
    heading: "A Specialist That Gathers Facts"
    code: |
      def build_researcher_prompt(query):
          system = "\\n".join([
              "You are a research specialist. Your job is to gather relevant",
              "facts and key information about the topic given to you.",
              "Return a structured list of the most important findings.",
          ])
          return [{"role": "system", "content": system},
                  {"role": "user", "content": "Research topic: " + str(query)}]

      class ResearcherAgent:
          def __init__(self, llm_fn=None):
              self._llm_fn = llm_fn
              self._history = []

          def research(self, query):
              findings = call_llm(build_researcher_prompt(query), llm_fn=self._llm_fn)
              self._history.append({"query": query, "findings": findings})
              return findings
    narration: >
      ResearcherAgent is three things: a system prompt that orients it as a research
      specialist, a research method that calls the model and records the exchange,
      and a history list. The clean interface is research of query returns a string.
      That is all the next agent needs - a string of findings, with no knowledge of
      who produced it or how. The single-responsibility boundary is enforced by what
      the agent exposes: one method, one return type.

  - type: concept
    label: "Interface matters"
    heading: "The Interface Is the Contract"
    body: >
      research(query) -> str is all the next agent needs.
    bullets:
      - "One method: research(query)"
      - "One return type: str"
      - "No knowledge of the downstream agent required"
      - "Swap for a mock, a web scraper, or a database - same interface"
      - "The mock branches on 'research' in the system message"
    narration: >
      The most important design decision is the interface. research takes a query
      and returns a string. That is the whole contract. The writer does not care
      whether the researcher used llama3.2 or searched the web or read a database
      - it just receives a string. The mock follows the same contract: if 'research'
      appears in the system message, return the mock findings. Keeping the interface
      simple is what makes specialist agents composable.

  - type: exercise
    heading: "Exercise 1: The Researcher Agent"
    prompt: >
      Build build_researcher_prompt(query) - a system message orienting the agent as
      a research specialist, user message 'Research topic: query'. Then
      ResearcherAgent(llm_fn=None): research(query) calls call_llm and records
      {query, findings} in history; history() returns a copy; clear_history()
      empties in place.
    hint: >
      build_researcher_prompt returns [system, user] messages. research():
      messages = build_researcher_prompt(query); findings = call_llm(messages,
      llm_fn=self._llm_fn); self._history.append({...}); return findings.
    narration: >
      This builds the first specialist - the one that gathers the raw material.

  - type: summary
    heading: "Lesson 1 Summary"
    bullets:
      - "Specialists do one job and hand off the rest"
      - "ResearcherAgent: build_researcher_prompt + research(query) -> str"
      - "One focused system prompt, one return type"
      - "Interface is the contract: str in, str out"
      - "Swap the implementation for any source - same interface"
    narration: >
      Lesson 2 builds the second specialist: a WriterAgent that turns findings into
      a polished document.
"""

_LESSON_02 = """\
day: "084"
lesson: 2
title: "The Writer Agent"
slides:
  - type: title
    heading: "The Writer Agent"
    subheading: "Turn findings into a document"
    narration: >
      The researcher returns a string of facts. The writer takes that string and
      produces something readable. This lesson builds WriterAgent - the second
      specialist - and introduces style as a construction-time parameter. Like the
      researcher, the writer has one job: write. It does not research, plan, or
      review.

  - type: code
    label: "WriterAgent"
    heading: "Style Set at Construction"
    code: |
      def build_writer_prompt(findings, style="concise", instructions=None):
          system_parts = [
              "You are a writing specialist. Turn the provided findings into",
              "a polished, well-structured document.",
              "Style: " + str(style) + ".",
          ]
          if instructions:
              system_parts.append("Additional instructions: " + str(instructions))
          system = "\\n".join(system_parts)
          return [{"role": "system", "content": system},
                  {"role": "user", "content": "Findings:\\n" + str(findings)}]

      class WriterAgent:
          def __init__(self, llm_fn=None, style="concise"):
              self._llm_fn = llm_fn
              self.style = style
              self._history = []

          def write(self, findings, instructions=None):
              messages = build_writer_prompt(findings, style=self.style,
                                             instructions=instructions)
              document = call_llm(messages, llm_fn=self._llm_fn)
              self._history.append({"findings": findings, "document": document})
              return document
    narration: >
      WriterAgent follows the same shape as ResearcherAgent - one constructor
      parameter for the model, a history list, and one main method. The difference
      is style: it is set at construction time, not per call. A formal-writing agent
      stays formal across all its tasks; a concise one stays concise. If you want
      a different style, you create a different writer. This keeps each agent's
      behavior predictable and stable across the pipeline.

  - type: concept
    label: "Separation of concerns"
    heading: "Separation Is What Makes Each Agent Better"
    body: >
      Separate system prompts = separate quality.
    bullets:
      - "Researcher prompt: optimised for fact-gathering"
      - "Writer prompt: optimised for document structure and flow"
      - "Each system prompt is short enough to be precise"
      - "A combined prompt is a compromise - both jobs suffer"
      - "Two small, focused calls beat one large, confused one"
    narration: >
      This is the practical payoff of specialisation. When you write the researcher's
      system prompt, you can say 'be factual and concise' without worrying about
      document flow. When you write the writer's, you can say 'be well-structured'
      without worrying about which facts to include. A combined prompt that tries to
      do both ends up giving vague instructions that produce mediocre results on
      both fronts. Two short, focused prompts produce better work than one long,
      confused one.

  - type: concept
    label: "Mock branching"
    heading: "The Mock Branches on the System Message"
    body: >
      Both agents share the same llm_fn in tests.
    bullets:
      - "_mock_multi(findings, document)"
      - "If 'research specialist' in system -> return findings"
      - "Otherwise -> return document"
      - "Both agents use the same injected llm_fn"
      - "The system message is the only distinguishing signal"
    narration: >
      In the gate both agents receive the same injected llm_fn. The mock resolves
      which response to return by looking for 'research' in the system message: if
      it's there, return the findings string; otherwise return the document. This
      is the multi-agent version of the same mock branching pattern from Day 82's
      extract/answer split. One mock, two behaviors, cleanly separated by context.

  - type: exercise
    heading: "Exercise 2: The Writer Agent"
    prompt: >
      Build build_writer_prompt(findings, style='concise', instructions=None) - system
      includes style (and instructions if provided), user is the findings string. Then
      WriterAgent(llm_fn=None, style='concise'): write(findings, instructions=None)
      calls call_llm, records {findings, document}; history() copy; clear_history()
      in place.
    hint: >
      build_writer_prompt: system_parts as a list; if instructions: append to list.
      WriterAgent.write: messages = build_writer_prompt(findings, style=self.style,
      instructions=instructions); document = call_llm(messages, llm_fn=self._llm_fn).
    narration: >
      This builds the second specialist - the one that turns raw findings into a
      readable document.

  - type: summary
    heading: "Lesson 2 Summary"
    bullets:
      - "WriterAgent: build_writer_prompt + write(findings) -> str"
      - "Style set at construction: each writer is consistent across tasks"
      - "Separate system prompts = each agent can be precisely instructed"
      - "Same class shape as ResearcherAgent: one method, history copy"
      - "Mock: branch on 'research specialist' in system to tell the two apart"
    narration: >
      Lesson 3 connects the two agents with explicit Handoffs - the audit trail that
      records who passed what to whom.
"""

_LESSON_03 = """\
day: "084"
lesson: 3
title: "Handoffs - Explicit Data Passing"
slides:
  - type: title
    heading: "Handoffs"
    subheading: "An audit trail for data between agents"
    narration: >
      The researcher passes findings to the writer via a plain function call - but
      that leaves no trace of what was sent. A Handoff makes that transfer an
      explicit, auditable record: who sent what to whom, and with what metadata. This
      lesson builds the Handoff dataclass and a summarizer that renders the full
      handoff chain at a glance.

  - type: concept
    label: "Why explicit"
    heading: "Invisible Data Flow Is a Debug Nightmare"
    body: >
      Explicit handoffs make the data flow auditable.
    bullets:
      - "Implicit: researcher(...) -> writer(findings) - no trace"
      - "Explicit: Handoff(from_agent, to_agent, content, metadata)"
      - "When something goes wrong, you know exactly what each agent received"
      - "Metadata: the task, the style, the timestamp - any context"
      - "summarize_handoffs: the whole chain in one print call"
    narration: >
      When a multi-agent pipeline produces a bad document, the first question is:
      what did the researcher actually pass to the writer? Without explicit handoffs,
      you have to add logging, re-run, and hope. With a Handoff object for every
      transfer, the answer is one attribute read away. This is the same idea as Day
      80's trace on the ReAct agent, applied to the data flow between agents: make
      the invisible flow visible, and debugging becomes straightforward.

  - type: code
    label: "Handoff"
    heading: "The Handoff Dataclass"
    code: |
      from dataclasses import dataclass, field

      @dataclass
      class Handoff:
          from_agent: str
          to_agent: str
          content: str
          metadata: dict = field(default_factory=dict)

      def summarize_handoffs(handoffs):
          lines = []
          for h in handoffs:
              preview = h.content[:80].replace("\\n", " ")
              lines.append(h.from_agent + " -> " + h.to_agent + ": " + preview)
          return "\\n".join(lines)
    narration: >
      Handoff reuses the dataclass pattern from Day 83's Task. Four fields: who sent,
      who receives, what was sent, and an optional metadata dict for any extra context
      like the task name or a timestamp. summarize_handoffs renders the chain as one
      line per handoff - sender, receiver, and the first 80 characters of the content.
      You can add a print call to any orchestrator and immediately see the full data
      flow.

  - type: exercise
    heading: "Exercise 3: Handoffs"
    prompt: >
      Build the Handoff dataclass (from_agent, to_agent, content: str; metadata: dict
      defaulting to {}). Implement summarize_handoffs(handoffs): one 'from -> to:
      preview' line per handoff (first 80 chars of content, newlines replaced with
      spaces); return '' for an empty list.
    hint: >
      @dataclass with field(default_factory=dict) for metadata. summarize_handoffs:
      lines = []; for h in handoffs: preview = h.content[:80].replace('\\n',' ');
      lines.append(h.from_agent+' -> '+h.to_agent+': '+preview); return
      '\\n'.join(lines).
    narration: >
      This builds the audit trail that makes a multi-agent pipeline debuggable.

  - type: summary
    heading: "Lesson 3 Summary"
    bullets:
      - "Handoff: from_agent, to_agent, content, metadata={}"
      - "Makes every data transfer between agents auditable"
      - "summarize_handoffs: the full chain in one print"
      - "metadata carries task, style, timestamp, or any context"
      - "Same dataclass pattern as Day 83's Task"
    narration: >
      Lesson 4 uses the Handoff to build run_duo - the function that chains the two
      agents into a pipeline.
"""

_LESSON_04 = """\
day: "084"
lesson: 4
title: "run_duo - The Pipeline"
slides:
  - type: title
    heading: "run_duo"
    subheading: "Chain researcher and writer with explicit handoffs"
    narration: >
      The two specialists are ready. The Handoff dataclass is ready. run_duo connects
      them: researcher produces findings, a Handoff carries those findings to the
      writer, the writer produces a document, a second Handoff records the output.
      One function in, one result dict out with the full trail attached.

  - type: code
    label: "run_duo"
    heading: "The Two-Agent Pipeline"
    code: |
      def run_duo(task, researcher, writer):
          findings = researcher.research(task)
          h1 = Handoff("researcher", "writer", findings,
                       metadata={"task": str(task)})
          document = writer.write(findings)
          h2 = Handoff("writer", "user", document,
                       metadata={"task": str(task)})
          return {"findings": findings, "document": document,
                  "handoffs": [h1, h2]}
    narration: >
      run_duo is short because the hard work lives in the specialists it calls.
      Four lines: research, record the handoff, write, record the handoff. The
      return dict carries everything: the intermediate findings (useful for
      debugging), the final document (the deliverable), and the two Handoffs (the
      audit trail). Notice run_duo takes the agents as arguments - it is a free
      function, not a method. That means you can pass any researcher and any writer,
      including mocks, without changing the pipeline logic.

  - type: concept
    label: "Free function"
    heading: "Free Function vs Method"
    body: >
      run_duo takes agents as arguments - it doesn't own them.
    bullets:
      - "run_duo(task, researcher, writer) - agents are passed in"
      - "Swap researcher for a mock, a web scraper, or a RAG agent - same call"
      - "The Orchestrator owns the agents and calls run_duo"
      - "Callers that want control skip the Orchestrator and call run_duo directly"
      - "Separation of ownership from pipeline logic"
    narration: >
      The distinction between a free function and a class method matters here. run_duo
      doesn't own the agents - it receives them as arguments. That means you can
      test the pipeline with two mocks without touching the Orchestrator. It also
      means you can extend it: pass a researcher that queries a vector database, or
      a writer with a custom style, and the pipeline function doesn't change. The
      Orchestrator (next lesson) owns the agents for convenience; run_duo exists for
      composability.

  - type: exercise
    heading: "Exercise 4: run_duo"
    prompt: >
      Implement run_duo(task, researcher, writer): call researcher.research(task),
      create Handoff('researcher','writer', findings, metadata={'task':task}), call
      writer.write(findings), create Handoff('writer','user', document, ...). Return
      {'findings', 'document', 'handoffs': [h1, h2]}.
    hint: >
      findings = researcher.research(task); h1 = Handoff('researcher','writer',
      findings, metadata={'task':str(task)}); document = writer.write(findings);
      h2 = Handoff('writer','user', document, metadata={'task':str(task)}).
      Return the three-key dict.
    narration: >
      This is the pipeline function - researcher feeds writer, two Handoffs record
      the transfers.

  - type: summary
    heading: "Lesson 4 Summary"
    bullets:
      - "run_duo chains researcher -> writer with a Handoff at each step"
      - "Returns {findings, document, handoffs} - complete trail included"
      - "Free function: takes agents as arguments, doesn't own them"
      - "Swap either agent without changing the pipeline"
      - "Orchestrator owns the agents and calls run_duo"
    narration: >
      Lesson 5 wraps run_duo in an Orchestrator - the coordinator that owns both
      agents, tracks every run, and accumulates the handoff trail.
"""

_LESSON_05 = """\
day: "084"
lesson: 5
title: "Orchestrator - Multi-Agent Coordination"
slides:
  - type: title
    heading: "Orchestrator"
    subheading: "Own the agents, run the pipeline, keep the trail"
    narration: >
      run_duo is the mechanism. The Orchestrator is the manager. It owns the
      ResearcherAgent and WriterAgent, provides a single run method, and accumulates
      every Handoff across every run. The caller sees one object with one method - the
      multi-agent complexity is hidden inside.

  - type: code
    label: "Orchestrator"
    heading: "One Object, Complete History"
    code: |
      class Orchestrator:
          def __init__(self, llm_fn=None, style="concise"):
              self.researcher = ResearcherAgent(llm_fn=llm_fn)
              self.writer = WriterAgent(llm_fn=llm_fn, style=style)
              self._runs = []

          def run(self, task):
              result = run_duo(task, self.researcher, self.writer)
              self._runs.append({"task": task, **result})
              return result

          def handoffs(self):
              all_h = []
              for r in self._runs:
                  all_h.extend(r.get("handoffs", []))
              return all_h
    narration: >
      Orchestrator follows the pattern of every Section 6 agent: bind at construction,
      delegate the work, keep state. __init__ creates the two specialists with the
      same llm_fn - so one model powers both. run delegates to run_duo and appends
      the result to _runs. handoffs flattens every Handoff from every run into a
      single list - so after three tasks you can see all six handoffs in one call.
      The caller never touches the individual agents unless they want to.

  - type: concept
    label: "Six agents"
    heading: "The Section's Class Pattern, Complete"
    body: >
      Six Section 6 agents, one class skeleton.
    bullets:
      - "Day 79 SimpleAgent: action loop"
      - "Day 80 ReactAgent: reasoning loop"
      - "Day 81 ToolAgent: routing"
      - "Day 82 MemoryAgent: store + recall"
      - "Day 83 PlannerAgent: decompose + sort + execute"
      - "Day 84 Orchestrator: coordinate specialists"
      - "All: bind at construction, delegate, keep state"
    narration: >
      Six days, six agents, one skeleton: bind the dependencies at construction,
      delegate the hard work to module functions, keep a history, return a copy. What
      changes is the engine. Today the engine is collaboration - two specialists
      handshaking through explicit Handoffs. The Orchestrator hides that complexity
      behind a single run method, so from the outside it looks like every other
      agent in this section.

  - type: exercise
    heading: "Exercise 5: Orchestrator"
    prompt: >
      Implement Orchestrator(llm_fn=None, style='concise'): __init__ creates researcher
      and writer with the shared llm_fn; run(task) calls run_duo, appends
      {'task',...result} to _runs, returns result; handoffs() flattens all Handoffs
      from _runs; history() copy; clear_history() clears _runs AND both agents'
      histories.
    hint: >
      __init__: self.researcher = ResearcherAgent(llm_fn=llm_fn);
      self.writer = WriterAgent(llm_fn=llm_fn, style=style); self._runs = [].
      run: result = run_duo(task, self.researcher, self.writer);
      self._runs.append({'task':task, **result}). handoffs: flatten r['handoffs'].
      clear_history: self._runs.clear() + each agent's clear_history().
    narration: >
      This completes the multi-agent system - a researcher and writer collaborating
      under one coordinator.

  - type: summary
    heading: "Lesson 5 Summary - Day 84 Complete"
    bullets:
      - "Orchestrator owns both agents, calls run_duo, accumulates handoffs"
      - "handoffs() flattens all Handoffs across all runs"
      - "clear_history() clears runs AND per-agent histories - one owner"
      - "Six Section 6 agents, same class shape throughout"
      - "Day 85: Model Context Protocol - connecting agents to external tools"
    narration: >
      Your researcher and writer now collaborate through an Orchestrator, with every
      data transfer recorded as an explicit Handoff. Day 85 introduces the Model
      Context Protocol - a standard for connecting agents to external tools and data
      sources.
"""

for i, content in enumerate([_LESSON_01, _LESSON_02, _LESSON_03,
                               _LESSON_04, _LESSON_05], start=1):
    (OUT / "lessons" / f"day_{DAY}_lesson_0{i}.yaml").write_text(content)

# ── PROJECT NOTEBOOK ──────────────────────────────────────────────────────────
PROJECT = nb([
    md(f"# Day {DAY} — Project: A Researcher + Writer Duo\n\n"
       "## Objective\n\n"
       "Build `multi_agent.py` — a system where a researcher agent and a writer "
       "agent collaborate, with every data transfer recorded as an explicit Handoff.\n\n"
       "## Deliverable\n\n"
       "`multi_agent.py` with:\n\n"
       "- `build_researcher_prompt(query)` / `ResearcherAgent` "
       "(`research/history/clear_history`)\n"
       "- `build_writer_prompt(findings, style, instructions)` / `WriterAgent` "
       "(`write/history/clear_history`)\n"
       "- `Handoff` dataclass (`from_agent, to_agent, content, metadata`)\n"
       "- `summarize_handoffs(handoffs) -> str`\n"
       "- `run_duo(task, researcher, writer) -> dict`\n"
       "- `Orchestrator(llm_fn=None, style='concise')` with "
       "`run / handoffs / history / clear_history`\n\n"
       "## Usage (with Ollama running + llama3.2 pulled)\n\n"
       "```python\n"
       "from multi_agent import Orchestrator, summarize_handoffs\n"
       "orch = Orchestrator()\n"
       "result = orch.run('What is the CAP theorem?')\n"
       "print(result['document'])\n"
       "print(summarize_handoffs(orch.handoffs()))\n"
       "```\n\n"
       "**The deliverable:** you give the orchestrator a topic, it researches and "
       "writes a document. The Handoff trail shows exactly what each agent received "
       "and produced — a complete audit of the collaboration."),
    code("# Your implementation here — build multi_agent.py\n"),
])
save(OUT / "project" / "project.ipynb", PROJECT)

# ── SOLUTION NOTEBOOK ─────────────────────────────────────────────────────────
_SOL_CELL1 = (
    f"_SRC = {repr(_MULTI_AGENT_SRC)}\n"
    "from pathlib import Path\n"
    "Path('multi_agent.py').write_text(_SRC, encoding='utf-8')\n"
    "print('multi_agent.py written.')"
)

_SOL_CELL2 = r"""
from multi_agent import (
    ResearcherAgent, WriterAgent, Handoff, summarize_handoffs,
    run_duo, Orchestrator,
)

def _mock_multi(findings='Fact: X.', document='Doc: done.'):
    def _fn(messages):
        system = messages[0]['content'] if messages else ''
        return findings if 'research specialist' in system.lower() else document
    return _fn

# 1. ResearcherAgent
r = ResearcherAgent(llm_fn=_mock_multi(findings='Found it.'))
out = r.research('AI')
assert out == 'Found it.' and len(r.history()) == 1
r.history().clear(); assert len(r.history()) == 1   # copy
r.clear_history(); assert len(r.history()) == 0
print("✅ ResearcherAgent (research / history / clear_history)")

# 2. WriterAgent
w = WriterAgent(llm_fn=_mock_multi(document='Written.'), style='formal')
doc = w.write('some findings')
assert doc == 'Written.' and 'formal' in str(w.style)
assert len(w.history()) == 1
print("✅ WriterAgent (write / style / history)")

# 3. Handoff + summarize
h1 = Handoff('researcher', 'writer', 'the facts')
assert h1.metadata == {}
h2 = Handoff('a', 'b', 'x' * 200)
summary = summarize_handoffs([h1, h2])
assert 'researcher -> writer' in summary
lines = summary.splitlines()
assert len(lines[1]) < 200          # preview truncated
assert summarize_handoffs([]) == ''
print("✅ Handoff / summarize_handoffs")

# 4. run_duo
researcher = ResearcherAgent(llm_fn=_mock_multi(findings='Key fact.'))
writer = WriterAgent(llm_fn=_mock_multi(document='Final doc.'))
result = run_duo('test topic', researcher, writer)
assert result['findings'] == 'Key fact.' and result['document'] == 'Final doc.'
assert len(result['handoffs']) == 2
h_r, h_w = result['handoffs']
assert h_r.from_agent == 'researcher' and h_r.to_agent == 'writer'
assert h_w.from_agent == 'writer' and h_w.to_agent == 'user'
print("✅ run_duo (findings / document / handoffs)")

# 5. Orchestrator
orch = Orchestrator(llm_fn=_mock_multi(findings='Fact A.', document='Doc A.'))
res = orch.run('first task')
assert res['findings'] == 'Fact A.' and res['document'] == 'Doc A.'
orch.run('second task')
assert len(orch.history()) == 2
orch.history().clear(); assert len(orch.history()) == 2   # copy
assert len(orch.handoffs()) == 4     # 2 runs × 2 handoffs
orch.clear_history()
assert len(orch.history()) == 0 and len(orch.handoffs()) == 0
print("✅ Orchestrator (run / handoffs / history / clear_history)")

print("\nMulti-agent system complete!")
"""

SOLUTION = nb([
    md(f"# Day {DAY} — Solution: A Researcher + Writer Duo"),
    code(_SOL_CELL1),
    code(_SOL_CELL2),
])
save(OUT / "project" / "solution" / "solution.ipynb", SOLUTION)
(OUT / "project" / "solution" / "multi_agent.py").write_text(_MULTI_AGENT_SRC)

print(f"Day {DAY} notebooks written to {OUT}")
print("  lessons/    day_084_lesson_01.yaml – lesson_05.yaml")
print("  exercises/  exercise_01 – exercise_05")
print("  project/    project.ipynb")
print("  project/solution/  solution.ipynb + multi_agent.py")
