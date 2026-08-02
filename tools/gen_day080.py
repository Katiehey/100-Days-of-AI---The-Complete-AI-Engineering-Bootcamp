#!/usr/bin/env python3
"""gen_day080.py — generate Day 080: The Agent Loop (ReAct)."""
from pathlib import Path
import json

ROOT    = Path(__file__).parent.parent
DAY     = "080"
SECTION = "06_agents"
OUT     = ROOT / SECTION / f"day_{DAY}"

(OUT / "exercises").mkdir(parents=True, exist_ok=True)
(OUT / "lessons").mkdir(parents=True, exist_ok=True)
(OUT / "project" / "solution").mkdir(parents=True, exist_ok=True)

# ── deliverable fragments (composed into react_agent.py AND reused as ─────────
# ── given-code / embedded solutions in the exercises, so they stay in sync) ────

_DOC = '''\
"""react_agent.py — Day 080: The Agent Loop (ReAct).

Day 79 built an agent that emitted a bare JSON action each turn. ReAct
(Reason + Act) makes the model *think out loud* first: every turn is a
Thought, then an Action with an Input, and the loop feeds back an Observation.
Reasoning before acting measurably improves multi-step tool use.

The ReAct turn format:
    Thought: <reasoning about what to do next>
    Action: <one tool name>
    Input: {"<param>": "<value>"}
...and, when done:
    Thought: <final reasoning>
    Final Answer: <the answer>

Pieces (ReAct-specific parts are new on Day 080; tools reuse Day 79):
  safe_calculate / _lookup / DEFAULT_TOOLS / build_tool_descriptions  (Day 79)
  safe_parse_json          - tolerant JSON parser                     (Day 79)
  parse_react_step         - parse one Thought/Action/Input step (never raises)
  format_step              - render an action step back into ReAct text
  format_observation       - render a tool result as an Observation line
  build_react_prompt       - assemble the messages, including the scratchpad
  execute_action           - run the tool named in a step
  call_llm                 - Ollama wrapper with llm_fn injection       (Day 79)
  run_react_agent          - the ReAct loop (bounded by max_iterations)
  ReactAgent               - a stateful ReAct agent

Setup:
    pip install ollama
    ollama pull llama3.2
"""
'''

_FRAG_TOOLS = '''\
import ast
import json
import operator

# ── tools reused from Day 79: a safe calculator + a fact-lookup tool ──────────
_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def _eval_node(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.operand))
    raise ValueError("unsupported expression")


def safe_calculate(expression):
    """Evaluate arithmetic without eval() (see Day 79)."""
    return _eval_node(ast.parse(expression, mode="eval").body)


_FACTS = {
    "speed of light": "299792458 m/s",
    "pi": "3.14159",
    "earth radius": "6371 km",
    "days in a year": "365",
}


def _lookup(args):
    query = str(args.get("query", "")).lower().strip()
    for key, value in _FACTS.items():
        if query and (query in key or key in query):
            return value
    return "No result found for " + repr(args.get("query", ""))


DEFAULT_TOOLS = {
    "calculator": {
        "description": "Evaluate an arithmetic expression, e.g. 2 * (3 + 4).",
        "parameters": {"expression": "string - the arithmetic to evaluate"},
        "fn": lambda args: str(safe_calculate(args["expression"])),
    },
    "lookup": {
        "description": "Look up a known fact: speed of light, pi, earth radius, "
                       "days in a year.",
        "parameters": {"query": "string - what to look up"},
        "fn": _lookup,
    },
}


def build_tool_descriptions(tools):
    """Render a tool registry as prompt text (Day 79)."""
    lines = []
    for name, spec in tools.items():
        params = ", ".join(spec.get("parameters", {}))
        lines.append("- " + name + "(" + params + "): " + spec["description"])
    return "\\n".join(lines)


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
'''

_FRAG_PARSE = '''\

# ── parsing the ReAct format ──────────────────────────────────────────────────
def _line_value(text, prefix):
    """Text after the first line starting with prefix (case-insensitive), else ''."""
    for line in text.splitlines():
        if line.strip().lower().startswith(prefix.lower()):
            return line.strip()[len(prefix):].strip()
    return ""


def _after_marker(text, marker):
    """Everything after marker (case-insensitive), or None if absent."""
    idx = text.lower().find(marker.lower())
    if idx == -1:
        return None
    return text[idx + len(marker):].strip()


def parse_react_step(text):
    """Parse one ReAct step. NEVER raises.

    Returns either:
      {"type": "action", "thought": str, "tool": str, "input": dict}
      {"type": "final",  "thought": str, "answer": str}
    A reply with no recognisable Action falls back to a final answer holding
    the raw text - so a malformed step still ends the loop cleanly.
    """
    thought = _line_value(text, "Thought:")
    final = _after_marker(text, "Final Answer:")
    if final is not None:
        return {"type": "final", "thought": thought, "answer": final}
    action = _line_value(text, "Action:")
    if action:
        args = safe_parse_json(_line_value(text, "Input:")) or {}
        return {"type": "action", "thought": thought, "tool": action, "input": args}
    return {"type": "final", "thought": thought, "answer": text.strip()}
'''

_FRAG_FORMAT = '''\

# ── formatting the trace (the scratchpad) ─────────────────────────────────────
def format_step(step):
    """Render an action step back into ReAct text for the scratchpad."""
    return ("Thought: " + step["thought"] + "\\n"
            + "Action: " + step["tool"] + "\\n"
            + "Input: " + json.dumps(step["input"]))


def format_observation(result):
    """Render a tool result as an Observation line."""
    return "Observation: " + str(result)


def build_react_prompt(task, tools, scratchpad):
    """Build the [system, user] messages for one ReAct step."""
    system = "\\n".join([
        "You are a reasoning agent. Solve the task step by step using the "
        "ReAct format: reason, act, observe, repeat.",
        "",
        "Available tools:",
        build_tool_descriptions(tools),
        "",
        "On each turn reply in EXACTLY this format:",
        "Thought: <your reasoning about what to do next>",
        "Action: <one tool name from the list above>",
        'Input: {"<param>": "<value>"}',
        "",
        "You will then receive an Observation with the tool's result.",
        "When you can answer, reply instead with:",
        "Thought: <your final reasoning>",
        "Final Answer: <the answer>",
    ])
    user = "Task: " + str(task)
    if scratchpad:
        user = user + "\\n\\n" + scratchpad.rstrip()
    user = user + "\\n\\nThought:"
    return [{"role": "system", "content": system},
            {"role": "user", "content": user}]
'''

_FRAG_EXEC = '''\

# ── acting + calling the model ────────────────────────────────────────────────
def execute_action(step, tools):
    """Run the tool named in a ReAct action step. Returns a string, never raises."""
    name = step.get("tool")
    if name not in tools:
        return "Error: unknown tool " + repr(name) + ". Available: " + ", ".join(tools)
    try:
        return str(tools[name]["fn"](step.get("input", {})))
    except Exception as exc:
        return "Error running " + str(name) + ": " + str(exc)


def call_llm(messages, llm_fn=None):
    """Call the chat model, or the injected llm_fn(messages) -> str (Day 79)."""
    if llm_fn is not None:
        return llm_fn(messages)
    import ollama
    resp = ollama.chat(model="llama3.2", messages=messages)
    return resp["message"]["content"]
'''

_FRAG_LOOP = '''\

# ── the ReAct loop ────────────────────────────────────────────────────────────
def run_react_agent(task, tools=None, llm_fn=None, max_iterations=10):
    """Run the ReAct loop until a Final Answer or max_iterations.

    Each turn: build a prompt from the task + scratchpad, ask the model for a
    Thought/Action/Input, run the tool, append the step and its Observation to
    the scratchpad, repeat. Feeding the growing scratchpad back is what lets the
    model reason over its own earlier observations.

    Returns {"answer", "thought", "trace", "iterations", "stopped"}.
    """
    if tools is None:
        tools = DEFAULT_TOOLS
    scratchpad = ""
    trace = []
    for i in range(max_iterations):
        messages = build_react_prompt(task, tools, scratchpad)
        step = parse_react_step(call_llm(messages, llm_fn=llm_fn))
        if step["type"] == "final":
            trace.append(step)
            return {"answer": step["answer"], "thought": step["thought"],
                    "trace": trace, "iterations": i + 1, "stopped": False}
        result = execute_action(step, tools)
        step["observation"] = result
        trace.append(step)
        scratchpad = scratchpad + format_step(step) + "\\n"
        scratchpad = scratchpad + format_observation(result) + "\\n"
    return {"answer": "Stopped: reached max_iterations without a final answer.",
            "thought": "", "trace": trace,
            "iterations": max_iterations, "stopped": True}
'''

_FRAG_AGENT = '''\

# ── the ReAct agent as a class ────────────────────────────────────────────────
class ReactAgent:
    """A reasoning agent using the ReAct loop.

    Binds a tool registry and an optional llm_fn, runs tasks through
    run_react_agent, and keeps a history of runs.

    Example::

        agent = ReactAgent(llm_fn=my_llm_fn)
        result = agent.run("What is 12 * 12?")
        print(result["answer"])
        for step in result["trace"]:
            print(step)
    """

    def __init__(self, tools=None, llm_fn=None, max_iterations=10):
        # copy so add_tool never mutates the shared DEFAULT_TOOLS global (Day 79)
        self.tools = dict(DEFAULT_TOOLS if tools is None else tools)
        self._llm_fn = llm_fn
        self.max_iterations = max_iterations
        self._history = []

    def add_tool(self, name, description, fn, parameters=None):
        """Register a new tool; returns self."""
        self.tools[name] = {"description": description,
                            "parameters": parameters or {}, "fn": fn}
        return self

    def run(self, task):
        """Run one task through the ReAct loop. Returns the result dict."""
        result = run_react_agent(task, tools=self.tools, llm_fn=self._llm_fn,
                                 max_iterations=self.max_iterations)
        self._history.append({"task": task, "result": result})
        return result

    def history(self):
        """Return a copy of the run history."""
        return list(self._history)

    def clear_history(self):
        """Clear the run history in place."""
        self._history.clear()
'''

_REACT_AGENT_SRC = (_DOC + _FRAG_TOOLS + _FRAG_PARSE + _FRAG_FORMAT
                    + _FRAG_EXEC + _FRAG_LOOP + _FRAG_AGENT)


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

def _make_mock_llm(script):
    \"\"\"Return an llm_fn(messages) that yields each scripted reply in turn.

    Repeats the last reply once the script is exhausted - handy for testing a
    runaway loop (a model that never emits a Final Answer).
    \"\"\"
    state = {'i': 0}
    def _fn(messages):
        i = state['i']
        state['i'] = min(i + 1, len(script) - 1)
        return script[i]
    return _fn
"""

# ── EX1: parse_react_step ─────────────────────────────────────────────────────
_EX1_GIVEN = _MOCK_HELPER + _FRAG_TOOLS

_EX1_STUB = """\
def _line_value(text, prefix):
    \"\"\"Text after the first line starting with prefix (case-insensitive).\"\"\"
    raise NotImplementedError

def _after_marker(text, marker):
    \"\"\"Everything after marker (case-insensitive), or None if absent.\"\"\"
    raise NotImplementedError

def parse_react_step(text):
    \"\"\"Parse one ReAct step. NEVER raises.
    {'type':'action','thought','tool','input'} or {'type':'final','thought','answer'}.
    \"\"\"
    raise NotImplementedError
"""

_EX1_CHECKS = r"""
score, total = 0, 5
try:
    s = parse_react_step('Thought: I should add.\nAction: calculator\nInput: {"expression": "2+2"}')
    assert s['type'] == 'action' and s['tool'] == 'calculator'
    assert s['input']['expression'] == '2+2'
    score += 1; print("✅ parses a Thought/Action/Input step")

    assert 'add' in s['thought'].lower()
    score += 1; print("✅ extracts the Thought text")

    f = parse_react_step('Thought: done.\nFinal Answer: The result is 4.')
    assert f['type'] == 'final' and '4' in f['answer']
    score += 1; print("✅ parses a Final Answer step")

    g = parse_react_step('I have no idea, just rambling here.')
    assert g['type'] == 'final'
    score += 1; print("✅ falls back to final (never raises)")

    m = parse_react_step('thought: hmm\naction: lookup\ninput: {"query": "pi"}')
    assert m['type'] == 'action' and m['tool'] == 'lookup' and m['input']['query'] == 'pi'
    score += 1; print("✅ tolerant of lowercase markers")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX1 = nb([
    md("# Day 080 — Exercise 1: Parsing the ReAct Format\n\n"
       "**What you'll build:** `parse_react_step` — turns one "
       "`Thought / Action / Input` (or `Final Answer`) reply into a structured "
       "step.\n\n"
       "**Why it matters:** ReAct's whole value is that the model *reasons before "
       "it acts*. But the reply is still just text — you have to parse the "
       "`Thought`, the `Action`, and the JSON `Input` out of it, and never crash on "
       "a malformed step."),
    code(_EX1_GIVEN),
    md("## Task\n\n"
       "1. `_line_value(text, prefix)` — return the text after the first line that "
       "starts with `prefix` (case-insensitive), else `''`.\n"
       "2. `_after_marker(text, marker)` — return everything after `marker` "
       "(case-insensitive), or `None` if it's absent.\n"
       "3. `parse_react_step(text)` — extract the `Thought:`. If a `Final Answer:` "
       "marker is present → `{'type':'final','thought','answer'}`. Else if there's an "
       "`Action:` → `{'type':'action','thought','tool','input'}` (parse `Input:` with "
       "`safe_parse_json`, default `{}`). Otherwise fall back to a `final` action with "
       "the raw text. **Never raises.**"),
    md("## Your Implementation"),
    code(_EX1_STUB),
    code(_FRAG_PARSE),
    md("## Automated checks"),
    code(_EX1_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _FRAG_PARSE + "```\n\n"
       "**Why line-by-line instead of one big regex?** The ReAct format is "
       "line-oriented, so scanning lines for `Thought:` / `Action:` / `Input:` is "
       "simpler and more forgiving than a multiline regex — and it has no backslash "
       "or escaping traps.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_01.ipynb", EX1)

# ── EX2: format_step + format_observation + build_react_prompt ────────────────
_EX2_GIVEN = _MOCK_HELPER + _FRAG_TOOLS + _FRAG_PARSE

_EX2_STUB = """\
def format_step(step):
    \"\"\"Render an action step back into ReAct text for the scratchpad.\"\"\"
    raise NotImplementedError

def format_observation(result):
    \"\"\"Render a tool result as an 'Observation: ...' line.\"\"\"
    raise NotImplementedError

def build_react_prompt(task, tools, scratchpad):
    \"\"\"Build the [system, user] messages for one ReAct step.\"\"\"
    raise NotImplementedError
"""

_EX2_CHECKS = r"""
score, total = 0, 5
try:
    step = {'thought': 'add them', 'tool': 'calculator', 'input': {'expression': '2+2'}}
    fs = format_step(step)
    assert 'Thought: add them' in fs and 'Action: calculator' in fs and 'Input:' in fs
    score += 1; print("✅ format_step renders Thought/Action/Input")

    assert '2+2' in fs
    score += 1; print("✅ format_step serialises the input dict")

    ob = format_observation('4')
    assert ob.startswith('Observation:') and '4' in ob
    score += 1; print("✅ format_observation prefixes 'Observation:'")

    msgs = build_react_prompt('add 2 and 2', DEFAULT_TOOLS, '')
    assert msgs[0]['role'] == 'system' and 'calculator' in msgs[0]['content']
    assert 'Thought' in msgs[0]['content'] and 'Final Answer' in msgs[0]['content']
    score += 1; print("✅ build_react_prompt describes the format + tools")

    msgs2 = build_react_prompt('t', DEFAULT_TOOLS, 'Observation: 4')
    assert '4' in msgs2[1]['content']
    score += 1; print("✅ scratchpad is included in the user message")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX2 = nb([
    md("# Day 080 — Exercise 2: Building the Trace\n\n"
       "**What you'll build:** the functions that turn steps back into text — "
       "`format_step`, `format_observation`, and `build_react_prompt`.\n\n"
       "**Why it matters:** ReAct keeps a *scratchpad* — a running transcript of "
       "everything the agent thought, did, and observed. Each turn you render the "
       "latest step and observation back into text and feed the whole scratchpad to "
       "the model, so it can reason over its own history."),
    code(_EX2_GIVEN),
    md("## Task\n\n"
       "1. `format_step(step)` — render an action step as "
       "`Thought: ...` / `Action: ...` / `Input: <json>` (use `json.dumps(step['input'])`).\n"
       "2. `format_observation(result)` — `'Observation: ' + str(result)`.\n"
       "3. `build_react_prompt(task, tools, scratchpad)` — a `system` message "
       "describing the ReAct format and the tools (`build_tool_descriptions`), and a "
       "`user` message with `Task: ...`, then the `scratchpad` if any, ending on "
       "`Thought:` to prompt the model. Return `[system, user]`."),
    md("## Your Implementation"),
    code(_EX2_STUB),
    code(_FRAG_FORMAT),
    md("## Automated checks"),
    code(_EX2_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _FRAG_FORMAT + "```\n\n"
       "**Why re-serialise the step into text?** The model only understands text. "
       "The scratchpad is the agent's memory of this task — writing each step and "
       "observation back into ReAct text is how that memory is carried forward.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_02.ipynb", EX2)

# ── EX3: execute_action + call_llm ───────────────────────────────────────────
_EX3_GIVEN = _MOCK_HELPER + _FRAG_TOOLS + _FRAG_PARSE + _FRAG_FORMAT

_EX3_STUB = """\
def execute_action(step, tools):
    \"\"\"Run the tool named in a ReAct action step. Returns a string. Never raises.\"\"\"
    raise NotImplementedError

def call_llm(messages, llm_fn=None):
    \"\"\"Call the chat model, or the injected llm_fn(messages) -> str.\"\"\"
    raise NotImplementedError
"""

_EX3_CHECKS = r"""
score, total = 0, 5
try:
    r = execute_action({'tool': 'calculator', 'input': {'expression': '6*7'}}, DEFAULT_TOOLS)
    assert r == '42'
    score += 1; print("✅ execute_action runs a tool")

    r2 = execute_action({'tool': 'nope', 'input': {}}, DEFAULT_TOOLS)
    assert 'unknown tool' in r2.lower()
    score += 1; print("✅ execute_action reports unknown tools (no crash)")

    r3 = execute_action({'tool': 'calculator', 'input': {}}, DEFAULT_TOOLS)
    assert 'error' in r3.lower()
    score += 1; print("✅ execute_action captures tool errors (never raises)")

    r4 = execute_action({'tool': 'lookup', 'input': {'query': 'pi'}}, DEFAULT_TOOLS)
    assert '3.14' in r4
    score += 1; print("✅ the lookup tool returns a known fact")

    got = call_llm([{'role': 'user', 'content': 'hi'}], llm_fn=lambda m: 'X')
    assert got == 'X'
    score += 1; print("✅ call_llm uses the injected llm_fn")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX3 = nb([
    md("# Day 080 — Exercise 3: Acting and Observing\n\n"
       "**What you'll build:** `execute_action` (runs the tool a step names) and "
       "`call_llm` (the injectable model call, from Day 79).\n\n"
       "**Why it matters:** the *observe* half of ReAct. `execute_action` produces "
       "the result that becomes the next `Observation` — the fact the model reasons "
       "over on its next turn."),
    code(_EX3_GIVEN),
    md("## Task\n\n"
       "1. `execute_action(step, tools) -> str` — look up `step['tool']`; unknown → "
       "an `Error: unknown tool ...` string; else call "
       "`tools[name]['fn'](step.get('input', {}))` in `try/except`, returning the "
       "result (or error text) as a string. **Never raises.**\n"
       "2. `call_llm(messages, llm_fn=None) -> str` — `llm_fn(messages)` if given, "
       "else `ollama.chat(model='llama3.2', messages=messages)['message']['content']`."),
    md("## Your Implementation"),
    code(_EX3_STUB),
    code(_FRAG_EXEC),
    md("## Automated checks"),
    code(_EX3_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _FRAG_EXEC + "```\n\n"
       "**Why does a tool error become the Observation?** In ReAct the model reads "
       "each Observation and reasons about it. An error it can *see* "
       "(`Error running calculator: ...`) is something it can reason its way around; "
       "an exception just ends the run.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_03.ipynb", EX3)

# ── EX4: run_react_agent ─────────────────────────────────────────────────────
_EX4_GIVEN = _MOCK_HELPER + _FRAG_TOOLS + _FRAG_PARSE + _FRAG_FORMAT + _FRAG_EXEC

_EX4_STUB = """\
def run_react_agent(task, tools=None, llm_fn=None, max_iterations=10):
    \"\"\"Run the ReAct loop. Returns {answer, thought, trace, iterations, stopped}.\"\"\"
    raise NotImplementedError
"""

_EX4_CHECKS = r"""
score, total = 0, 5
try:
    script = ['Thought: I should add.\nAction: calculator\nInput: {"expression": "2+2"}',
              'Thought: I know now.\nFinal Answer: The answer is 4.']
    out = run_react_agent('what is 2+2', DEFAULT_TOOLS, llm_fn=_make_mock_llm(script))
    assert out['answer'] == 'The answer is 4.' and out['stopped'] is False
    score += 1; print("✅ run_react_agent loops: act, observe, then finish")

    assert len(out['trace']) == 2 and out['trace'][0]['type'] == 'action'
    assert out['trace'][0]['observation'] == '4'
    score += 1; print("✅ trace records each step with its observation")

    # the observation must be fed back into the next prompt
    seen = []
    def _spy(messages):
        seen.append(messages[1]['content'])
        if len(seen) == 1:
            return 'Thought: add.\nAction: calculator\nInput: {"expression": "2+2"}'
        return 'Thought: done.\nFinal Answer: 4'
    run_react_agent('2+2', DEFAULT_TOOLS, llm_fn=_spy)
    assert 'Observation: 4' in seen[1]
    score += 1; print("✅ the scratchpad (with Observation) is fed back")

    assert 'Observation' not in seen[0] and 'Task:' in seen[0]
    score += 1; print("✅ first turn has the task but no observations yet")

    never = _make_mock_llm(['Thought: loop.\nAction: calculator\nInput: {"expression": "1+1"}'])
    loop = run_react_agent('x', DEFAULT_TOOLS, llm_fn=never, max_iterations=3)
    assert loop['stopped'] is True and loop['iterations'] == 3
    score += 1; print("✅ max_iterations stops a runaway loop")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX4 = nb([
    md("# Day 080 — Exercise 4: The ReAct Loop\n\n"
       "**What you'll build:** `run_react_agent` — reason, act, observe, repeat.\n\n"
       "**Why it matters:** this is the loop that makes ReAct work. It keeps a "
       "scratchpad, appends each `Thought/Action/Input` and its `Observation`, and "
       "feeds the whole thing back so the model reasons over its own trail — until a "
       "`Final Answer` or `max_iterations`."),
    code(_EX4_GIVEN),
    md("## Task\n\n"
       "`run_react_agent(task, tools=None, llm_fn=None, max_iterations=10) -> dict`\n\n"
       "- default `tools` to `DEFAULT_TOOLS`; start `scratchpad = ''`, `trace = []`\n"
       "- loop `for i in range(max_iterations)`: `build_react_prompt(task, tools, "
       "scratchpad)` → `call_llm` → `parse_react_step`\n"
       "- on a `final` step: append to trace, return "
       "`{answer, thought, trace, iterations: i+1, stopped: False}`\n"
       "- else: `execute_action`, store the result on `step['observation']`, append "
       "to trace, and add `format_step(step)` + `format_observation(result)` to the "
       "scratchpad\n"
       "- if the loop ends: return `stopped: True`"),
    md("## Your Implementation"),
    code(_EX4_STUB),
    code(_FRAG_LOOP),
    md("## Automated checks"),
    code(_EX4_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _FRAG_LOOP + "```\n\n"
       "**Why keep a text scratchpad and not just the trace list?** The model reads "
       "text. The scratchpad is the ReAct transcript the model sees each turn; the "
       "`trace` list is the structured version *you* inspect afterwards. Same events, "
       "two audiences.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_04.ipynb", EX4)

# ── EX5: ReactAgent ──────────────────────────────────────────────────────────
_EX5_GIVEN = (_MOCK_HELPER + _FRAG_TOOLS + _FRAG_PARSE + _FRAG_FORMAT
              + _FRAG_EXEC + _FRAG_LOOP)

_EX5_STUB = """\
class ReactAgent:
    \"\"\"A reasoning agent using the ReAct loop.\"\"\"

    def __init__(self, tools=None, llm_fn=None, max_iterations=10):
        raise NotImplementedError

    def add_tool(self, name, description, fn, parameters=None):
        raise NotImplementedError

    def run(self, task):
        raise NotImplementedError

    def history(self):
        raise NotImplementedError

    def clear_history(self):
        raise NotImplementedError
"""

_EX5_CHECKS = r"""
score, total = 0, 6
try:
    script = ['Thought: add.\nAction: calculator\nInput: {"expression": "2+2"}',
              'Thought: done.\nFinal Answer: The answer is 4.']
    agent = ReactAgent(llm_fn=_make_mock_llm(script))
    out = agent.run('what is 2+2?')
    assert out['answer'] == 'The answer is 4.'
    score += 1; print("✅ ReactAgent.run returns the final answer")

    assert 'calculator' in agent.tools and 'lookup' in agent.tools
    score += 1; print("✅ ReactAgent uses DEFAULT_TOOLS by default")

    agent.add_tool('shout', 'Uppercase text.',
                   lambda args: str(args['text']).upper(), {'text': 'string'})
    assert 'shout' in agent.tools and 'shout' not in DEFAULT_TOOLS
    score += 1; print("✅ add_tool registers a tool without mutating DEFAULT_TOOLS")

    assert len(agent.history()) == 1
    score += 1; print("✅ history records each run")

    h = agent.history(); h.clear()
    assert len(agent.history()) == 1
    score += 1; print("✅ history() returns a copy, not the live list")

    agent.clear_history()
    assert len(agent.history()) == 0
    score += 1; print("✅ clear_history empties the log")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX5 = nb([
    md("# Day 080 — Exercise 5: ReactAgent\n\n"
       "**What you'll build:** the `ReactAgent` class — binds tools + `llm_fn`, runs "
       "tasks, and keeps a history (the same class shape as Day 79's `SimpleAgent`).\n\n"
       "**Why it matters:** the reasoning loop is the engine; the class is the "
       "convenient handle. Bind the model and tools once, call `.run()` many times, "
       "and inspect `result['trace']` to see the agent's reasoning."),
    code(_EX5_GIVEN),
    md("## Task\n\n"
       "`ReactAgent(tools=None, llm_fn=None, max_iterations=10)`\n\n"
       "1. `__init__` — `self.tools = dict(DEFAULT_TOOLS if tools is None else tools)` "
       "(**copy**), plus `_llm_fn`, `max_iterations`, `_history = []`.\n"
       "2. `add_tool(name, description, fn, parameters=None)` — add to `self.tools`; "
       "return `self`.\n"
       "3. `run(task)` — delegate to `run_react_agent` with the bound tools/llm_fn; "
       "append `{'task','result'}` to `_history`; return the result.\n"
       "4. `history()` — return `list(self._history)`.\n"
       "5. `clear_history()` — `self._history.clear()`."),
    md("## Your Implementation"),
    code(_EX5_STUB),
    code(_FRAG_AGENT),
    md("## Automated checks"),
    code(_EX5_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _FRAG_AGENT + "```\n\n"
       "**Same shape as SimpleAgent?** Yes — bind at construction, delegate in "
       "methods, copy the registry, return a history copy. Every agent in this "
       "section wears the same class skeleton; only the loop inside changes.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_05.ipynb", EX5)

# ── YAML lessons ──────────────────────────────────────────────────────────────
_LESSON_01 = """\
day: "080"
lesson: 1
title: "The ReAct Pattern"
slides:
  - type: title
    heading: "The Agent Loop: ReAct"
    subheading: "Reason, Act, Observe - repeat"
    narration: >
      Yesterday your agent emitted a bare JSON action each turn and got straight
      to work. Today you make it think first. ReAct - short for Reason and Act -
      has the model write a Thought before every Action, then read an Observation
      before the next Thought. That out-loud reasoning is not decoration: on
      multi-step tool tasks it measurably improves how often the agent picks the
      right tool and reaches the right answer. The loop skeleton from Day 79 is
      unchanged; what changes is the shape of each turn.

  - type: concept
    label: "Why reason first"
    heading: "Reasoning Before Acting"
    body: >
      A Thought is a cheap planning step the model takes before committing.
    bullets:
      - "Day 79: model jumps straight to an action - no visible reasoning"
      - "ReAct: Thought first, then Action, then Observation - then repeat"
      - "The Thought lets the model plan, catch mistakes, and stay on track"
      - "The Observation grounds the next Thought in a real tool result"
      - "Same loop as Day 79; each turn is now Thought/Action/Observation"
    narration: >
      Think about how you solve a multi-step problem: you reason about what to do,
      do one thing, look at the result, then reason again. ReAct gives the model
      that same rhythm. The Thought is a short planning step - what do I know, what
      do I need next. The Action carries it out. The Observation feeds the real
      result back so the next Thought is grounded in fact, not guesswork. It is
      the same loop you built yesterday, with a reasoning step bolted onto the
      front of every turn.

  - type: concept
    label: "The format"
    heading: "The ReAct Turn Format"
    body: >
      Each turn is a small, fixed text template.
    bullets:
      - "Thought: reasoning about what to do next"
      - "Action: one tool name from the list"
      - 'Input: {"param": "value"} - JSON arguments for the tool'
      - "Then the loop appends: Observation: <tool result>"
      - "To finish: Thought: ... then Final Answer: <answer>"
    narration: >
      The format is deliberately simple text, not strict JSON, because small
      local models follow a light template far more reliably than they emit
      perfect JSON. Thought, Action, Input on the way out; Observation appended by
      your loop on the way back. When the model has enough to answer, it swaps the
      Action for a Final Answer line. Your job in Lesson 1 is to parse this format
      out of the model's reply.

  - type: code
    label: "parse_react_step"
    heading: "Parsing One Step - Line by Line"
    code: |
      def _line_value(text, prefix):
          for line in text.splitlines():
              if line.strip().lower().startswith(prefix.lower()):
                  return line.strip()[len(prefix):].strip()
          return ""

      def parse_react_step(text):
          thought = _line_value(text, "Thought:")
          final = _after_marker(text, "Final Answer:")
          if final is not None:
              return {"type": "final", "thought": thought, "answer": final}
          action = _line_value(text, "Action:")
          if action:
              args = safe_parse_json(_line_value(text, "Input:")) or {}
              return {"type": "action", "thought": thought,
                      "tool": action, "input": args}
          return {"type": "final", "thought": thought, "answer": text.strip()}
    narration: >
      Because the format is line-oriented, you parse it line by line. _line_value
      scans for the first line starting with a label and returns the rest. Check
      for a Final Answer first - if the model is done, that wins. Otherwise pull
      the Action name and parse the Input with the same tolerant safe_parse_json
      from Day 79. And crucially, if there is no recognisable action at all, fall
      back to a final answer holding the raw text. Like Day 79's parse_action,
      this function never raises - a garbled step still ends the loop cleanly.

  - type: exercise
    heading: "Exercise 1: Parsing the ReAct Format"
    prompt: >
      Implement _line_value, _after_marker, and parse_react_step. Handle a
      Thought/Action/Input step, a Final Answer step, and a fallback to final
      when there is no recognisable action. Must never raise, and tolerate
      lowercase markers.
    hint: >
      _line_value: loop over text.splitlines(), match line.strip().lower()
      .startswith(prefix.lower()). Check Final Answer before Action. Parse Input
      with safe_parse_json(...) or {}.
    narration: >
      This parser is what turns the model's reasoning into structured steps your
      loop can act on.

  - type: summary
    heading: "Lesson 1 Summary"
    bullets:
      - "ReAct = Reason + Act: Thought, then Action, then Observation, repeat"
      - "Reasoning out loud improves multi-step tool use"
      - "Turn format is light text (Thought/Action/Input), not strict JSON"
      - "parse_react_step reads it line by line and NEVER raises"
      - "Final Answer ends the loop; no action -> fall back to final"
    narration: >
      Lesson 2 builds the scratchpad - rendering steps and observations back into
      text so the model can reason over its own history.
"""

_LESSON_02 = """\
day: "080"
lesson: 2
title: "The Scratchpad"
slides:
  - type: title
    heading: "The Scratchpad"
    subheading: "The agent's working memory for one task"
    narration: >
      A ReAct agent needs to remember what it has already tried within a single
      task. It does this with a scratchpad: a running transcript of every Thought,
      Action, Input, and Observation so far. Each turn you render the latest step
      back into text, append the observation, and feed the whole scratchpad to the
      model. This lesson builds the formatting functions that create it.

  - type: concept
    label: "What the scratchpad is"
    heading: "A Running Transcript"
    body: >
      The scratchpad is the ReAct trace, as text, fed back each turn.
    bullets:
      - "Turn 1 out: Thought / Action / Input"
      - "Turn 1 back: Observation (your loop appends it)"
      - "Turn 2 sees the full turn-1 transcript before reasoning again"
      - "It grows each turn - the model always sees the whole task so far"
      - "This is per-task working memory, not long-term memory (that's Day 82)"
    narration: >
      The scratchpad is short-term memory scoped to one task. It starts empty. The
      model produces a Thought, Action, and Input; your loop runs the tool and
      appends the Observation. On the next turn the model sees that entire
      exchange and reasons about what to do next. The scratchpad grows until the
      task is done, then it is discarded. Persisting memory across tasks and
      sessions is a different problem - that is Day 82.

  - type: code
    label: "format_step"
    heading: "Rendering Steps Back to Text"
    code: |
      def format_step(step):
          return ("Thought: " + step["thought"] + "\\n"
                  + "Action: " + step["tool"] + "\\n"
                  + "Input: " + json.dumps(step["input"]))

      def format_observation(result):
          return "Observation: " + str(result)
    narration: >
      format_step is the inverse of parse_react_step: it takes the structured step
      and writes it back out in ReAct text. format_observation prefixes the tool
      result with the Observation label the model expects. Together they turn one
      round of the loop into the two-or-three lines that get appended to the
      scratchpad. The model only understands text, so everything it needs to
      remember has to be rendered back into text.

  - type: code
    label: "build_react_prompt"
    heading: "Assembling the Prompt"
    code: |
      def build_react_prompt(task, tools, scratchpad):
          system = "\\n".join([
              "You are a reasoning agent. Use the ReAct format...",
              "Available tools:", build_tool_descriptions(tools),
              "Thought: ...", "Action: <tool>", 'Input: {"param": "value"}',
              "When done: Thought: ... then Final Answer: <answer>",
          ])
          user = "Task: " + str(task)
          if scratchpad:
              user = user + "\\n\\n" + scratchpad.rstrip()
          user = user + "\\n\\nThought:"
          return [{"role": "system", "content": system},
                  {"role": "user", "content": user}]
    narration: >
      The system message explains the ReAct format and lists the tools with
      build_tool_descriptions from Day 79. The user message carries the task, then
      the scratchpad if there is one, and ends on the word Thought to nudge the
      model to continue reasoning rather than restart. That trailing Thought colon
      is a small but effective prompt-engineering trick: it puts the model right
      where you want it in the format.

  - type: exercise
    heading: "Exercise 2: Building the Trace"
    prompt: >
      Implement format_step (Thought/Action/Input text, json.dumps the input),
      format_observation ('Observation: ' + str(result)), and build_react_prompt
      (system describes the format + tools; user has the task, the scratchpad,
      and a trailing 'Thought:').
    hint: >
      format_step joins three lines with newlines. build_react_prompt: use
      build_tool_descriptions for the tool list; append scratchpad.rstrip() to the
      user message when non-empty; end with 'Thought:'.
    narration: >
      These functions create the scratchpad the model reasons over - the agent's
      memory of the task in progress.

  - type: summary
    heading: "Lesson 2 Summary"
    bullets:
      - "Scratchpad = running ReAct transcript, fed back each turn"
      - "format_step: structured step -> Thought/Action/Input text"
      - "format_observation: 'Observation: ' + result"
      - "build_react_prompt: system (format + tools) + user (task + scratchpad)"
      - "Trailing 'Thought:' nudges the model to keep reasoning"
    narration: >
      Lesson 3 runs the action and calls the model - the act-and-observe half of
      ReAct.
"""

_LESSON_03 = """\
day: "080"
lesson: 3
title: "Acting and Observing"
slides:
  - type: title
    heading: "Acting and Observing"
    subheading: "Run the tool, turn the result into an Observation"
    narration: >
      With parsing and formatting in place, the agent needs to act. execute_action
      runs the tool a step names and returns its result as a string - which becomes
      the next Observation. call_llm is the same injectable model call from Day 79.
      Both are deliberately thin, and both are testable with mocks.

  - type: code
    label: "execute_action"
    heading: "execute_action - Errors Become Observations"
    code: |
      def execute_action(step, tools):
          name = step.get("tool")
          if name not in tools:
              return "Error: unknown tool " + repr(name)
          try:
              return str(tools[name]["fn"](step.get("input", {})))
          except Exception as exc:
              return "Error running " + str(name) + ": " + str(exc)
    narration: >
      execute_action is Day 79's execute_tool adapted to a ReAct step: it reads the
      tool name and the parsed Input, runs the tool function, and returns the
      result as a string. If the tool is unknown or throws, the error comes back as
      text. That is the point - the error becomes the Observation, and the model
      reads it on the next turn and can reason its way around it. An exception would
      just kill the loop.

  - type: concept
    label: "The observe step"
    heading: "Observation Closes the Loop"
    body: >
      The Observation is the bridge from acting back to reasoning.
    bullets:
      - "execute_action produces the raw result string"
      - "format_observation wraps it as 'Observation: ...'"
      - "It is appended to the scratchpad the model sees next turn"
      - "Real result in, grounded reasoning out"
      - "A tool error is just an Observation the model can react to"
    narration: >
      The Observation is what makes ReAct more than a fixed plan. The model does
      not know in advance what the calculator will return, or whether a lookup will
      find anything. It acts, observes the real result, and adjusts. That
      act-observe-reason cycle is how an agent handles tasks whose steps depend on
      intermediate results - the kind of task a fixed pipeline cannot.

  - type: code
    label: "call_llm"
    heading: "call_llm - The Injection Point"
    code: |
      def call_llm(messages, llm_fn=None):
          if llm_fn is not None:
              return llm_fn(messages)
          import ollama
          resp = ollama.chat(model="llama3.2", messages=messages)
          return resp["message"]["content"]
    narration: >
      call_llm is unchanged from Day 79 and for the same reason: it is the single
      seam where the agent meets the model. Inject a mock llm_fn that returns
      scripted ReAct steps, and the whole loop runs offline and deterministically -
      which is exactly how the tests drive it. Reasoning quality is the model's job;
      loop correctness is yours, and the injection lets you test the loop without
      the model.

  - type: exercise
    heading: "Exercise 3: Acting and Observing"
    prompt: >
      Implement execute_action(step, tools): unknown tool -> error string; else run
      the tool fn on step['input'] in try/except and return the result as a string,
      never raising. Implement call_llm(messages, llm_fn=None) as on Day 79.
    hint: >
      execute_action mirrors Day 79's execute_tool but reads step['tool'] and
      step['input']. call_llm: if llm_fn is not None return llm_fn(messages).
    narration: >
      This is the act-and-observe half of ReAct: run the tool, and let even errors
      come back as observations.

  - type: summary
    heading: "Lesson 3 Summary"
    bullets:
      - "execute_action runs the step's tool; unknown/errors -> text, never raises"
      - "The result becomes the next Observation via format_observation"
      - "Observation grounds the next Thought in a real result"
      - "call_llm(messages, llm_fn=None): same injectable seam as Day 79"
      - "A scripted llm_fn makes the ReAct loop deterministic and offline"
    narration: >
      Lesson 4 assembles it all into run_react_agent - the reason-act-observe loop
      with the max_iterations safeguard.
"""

_LESSON_04 = """\
day: "080"
lesson: 4
title: "The ReAct Loop"
slides:
  - type: title
    heading: "The ReAct Loop"
    subheading: "run_react_agent - reason, act, observe, repeat"
    narration: >
      Now everything comes together. run_react_agent keeps a scratchpad, and each
      turn it builds a prompt, gets a step, and either finishes or runs a tool and
      appends the observation. The growing scratchpad is fed back every turn, so the
      model reasons over its own trail. And like every loop this section, it is
      bounded by max_iterations.

  - type: code
    label: "run_react_agent"
    heading: "The Loop in Full"
    code: |
      def run_react_agent(task, tools=None, llm_fn=None, max_iterations=10):
          if tools is None:
              tools = DEFAULT_TOOLS
          scratchpad, trace = "", []
          for i in range(max_iterations):
              messages = build_react_prompt(task, tools, scratchpad)
              step = parse_react_step(call_llm(messages, llm_fn=llm_fn))
              if step["type"] == "final":
                  trace.append(step)
                  return {"answer": step["answer"], "thought": step["thought"],
                          "trace": trace, "iterations": i + 1, "stopped": False}
              result = execute_action(step, tools)
              step["observation"] = result
              trace.append(step)
              scratchpad += format_step(step) + "\\n"
              scratchpad += format_observation(result) + "\\n"
          return {"answer": "Stopped: reached max_iterations without a final answer.",
                  "thought": "", "trace": trace,
                  "iterations": max_iterations, "stopped": True}
    narration: >
      Read the loop. Build the prompt from the task and scratchpad, call the model,
      parse the step. If it is final, return the answer. Otherwise run the tool,
      attach the observation to the step, record it in the trace, and append both
      the step and the observation to the scratchpad. Next turn, that scratchpad
      goes back in. Two records are kept: the scratchpad text for the model, and the
      trace list for you. The for-range over max_iterations is the same safeguard as
      Day 79 - a model that never says Final Answer returns stopped, it does not
      hang.

  - type: concept
    label: "Two views of the run"
    heading: "Scratchpad vs Trace"
    body: >
      The same events, recorded twice, for two audiences.
    bullets:
      - "scratchpad: text - what the MODEL reads each turn"
      - "trace: list of step dicts - what YOU inspect afterwards"
      - "trace[i]['observation'] holds each tool result"
      - "Return dict: {answer, thought, trace, iterations, stopped}"
      - "Inspecting the trace is how you debug an agent's reasoning"
    narration: >
      Keeping both a text scratchpad and a structured trace is a deliberate design
      choice. The model needs text, so the scratchpad is text. But when you debug an
      agent - why did it pick that tool, what did it observe - you want structured
      data, so the trace is a list of dicts. Being able to read the trace after a run
      is one of the most practical debugging tools you have when an agent
      misbehaves.

  - type: exercise
    heading: "Exercise 4: The ReAct Loop"
    prompt: >
      Implement run_react_agent(task, tools=None, llm_fn=None, max_iterations=10).
      Keep a scratchpad and a trace. Each turn: build prompt, call model, parse
      step; finish -> return; else execute_action, attach observation, append to
      trace and scratchpad. Bound by max_iterations, returning stopped=True on
      overrun.
    hint: >
      scratchpad='' and trace=[]. for i in range(max_iterations). On final return
      {answer, thought, trace, iterations:i+1, stopped:False}. Else append
      format_step(step) and format_observation(result) to scratchpad.
    narration: >
      This is the day's centrepiece. When your scripted mock drives it - act, then
      finish - you have a working reasoning agent.

  - type: summary
    heading: "Lesson 4 Summary"
    bullets:
      - "run_react_agent: build prompt -> call -> parse -> finish or act+observe"
      - "Scratchpad (text, for the model) grows each turn with steps + observations"
      - "Trace (list of dicts, for you) records every step + its observation"
      - "Returns {answer, thought, trace, iterations, stopped}"
      - "max_iterations turns a non-finishing model into a clean stopped: True"
    narration: >
      Lesson 5 wraps the loop in the ReactAgent class - the same class shape as
      Day 79's SimpleAgent.
"""

_LESSON_05 = """\
day: "080"
lesson: 5
title: "ReactAgent - Putting It Together"
slides:
  - type: title
    heading: "ReactAgent"
    subheading: "The reasoning agent as a reusable class"
    narration: >
      The final piece is a class. ReactAgent binds the tools and the model once,
      runs tasks through run_react_agent, and keeps a history of runs. It is the
      same class shape you built on Day 79 - bind at construction, delegate in
      methods, copy the registry, return a history copy. Only the loop inside is
      different.

  - type: code
    label: "ReactAgent"
    heading: "ReactAgent - Same Shape, New Engine"
    code: |
      class ReactAgent:
          def __init__(self, tools=None, llm_fn=None, max_iterations=10):
              self.tools = dict(DEFAULT_TOOLS if tools is None else tools)
              self._llm_fn = llm_fn
              self.max_iterations = max_iterations
              self._history = []

          def add_tool(self, name, description, fn, parameters=None):
              self.tools[name] = {"description": description,
                                  "parameters": parameters or {}, "fn": fn}
              return self

          def run(self, task):
              result = run_react_agent(task, tools=self.tools,
                                       llm_fn=self._llm_fn,
                                       max_iterations=self.max_iterations)
              self._history.append({"task": task, "result": result})
              return result

          def history(self):
              return list(self._history)

          def clear_history(self):
              self._history.clear()
    narration: >
      The constructor copies DEFAULT_TOOLS with dict so add_tool never leaks into
      the global registry - the same subtle bug you guarded against on Day 79. run
      delegates straight to run_react_agent and records the run. history returns a
      copy; clear_history empties in place. Because the class is so thin, the
      reasoning power all lives in the loop, and the class just makes it convenient
      to use across many tasks.

  - type: concept
    label: "Reading the trace"
    heading: "Inspecting the Reasoning"
    body: >
      Every run returns a trace you can read step by step.
    bullets:
      - "result['answer'] - the final answer"
      - "result['trace'] - every Thought/Action/Input + Observation"
      - "Print the trace to watch the agent reason through a task"
      - "This visibility is ReAct's big practical win over a bare loop"
      - "Day 79 -> Day 80: same skeleton, added reasoning + a readable trace"
    narration: >
      One real advantage of ReAct is transparency. Because the model reasons in
      text and you keep the trace, you can read exactly how the agent reached its
      answer: what it thought, which tool it chose, what it observed, and how that
      changed its next move. When an agent gives a wrong answer, the trace usually
      shows you precisely where its reasoning went off the rails - far easier to
      debug than a single opaque output.

  - type: exercise
    heading: "Exercise 5: ReactAgent"
    prompt: >
      Implement ReactAgent: __init__ copies DEFAULT_TOOLS and stores llm_fn,
      max_iterations, and an empty history; add_tool registers a tool and returns
      self; run delegates to run_react_agent and records the run; history returns a
      copy; clear_history empties in place.
    hint: >
      self.tools = dict(DEFAULT_TOOLS if tools is None else tools). run calls
      run_react_agent with the bound tools/llm_fn. history() returns
      list(self._history).
    narration: >
      This completes your reasoning agent - hand it a model and tools and watch it
      think its way to an answer.

  - type: summary
    heading: "Lesson 5 Summary - Day 80 Complete"
    bullets:
      - "ReactAgent binds tools + llm_fn, runs tasks, keeps a readable trace"
      - "Same class shape as SimpleAgent: bind, delegate, copy, copy-out"
      - "result['trace'] exposes the full Thought/Action/Observation reasoning"
      - "ReAct = Day 79 loop + reason-before-act + a scratchpad"
      - "Transparency: the trace shows exactly how the agent reasoned"
    narration: >
      You turned a bare action loop into a reasoning agent. Day 81 gives the agent
      many more tools and teaches it to route to the right one - tool selection at
      scale.
"""

for i, content in enumerate([_LESSON_01, _LESSON_02, _LESSON_03,
                               _LESSON_04, _LESSON_05], start=1):
    (OUT / "lessons" / f"day_{DAY}_lesson_0{i}.yaml").write_text(content)

# ── PROJECT NOTEBOOK ──────────────────────────────────────────────────────────
PROJECT = nb([
    md(f"# Day {DAY} — Project: A ReAct Reasoning Agent\n\n"
       "## Objective\n\n"
       "Build `react_agent.py` — an agent that reasons out loud in the "
       "`Thought → Action → Observation` ReAct loop before answering.\n\n"
       "## Deliverable\n\n"
       "`react_agent.py` with:\n\n"
       "- `DEFAULT_TOOLS` — calculator + lookup (tools reused from Day 79)\n"
       "- `parse_react_step(text) -> dict` (never raises)\n"
       "- `format_step(step)` / `format_observation(result)`\n"
       "- `build_react_prompt(task, tools, scratchpad) -> list[dict]`\n"
       "- `execute_action(step, tools) -> str`\n"
       "- `call_llm(messages, llm_fn=None) -> str`\n"
       "- `run_react_agent(task, tools=None, llm_fn=None, max_iterations=10) -> dict`\n"
       "- `ReactAgent(tools=None, llm_fn=None, max_iterations=10)` with "
       "`add_tool/run/history/clear_history`\n\n"
       "## Usage (with Ollama running + llama3.2 pulled)\n\n"
       "```python\n"
       "from react_agent import ReactAgent\n"
       "agent = ReactAgent()\n"
       "result = agent.run('What is the speed of light in km/s, rounded to millions?')\n"
       "print(result['answer'])\n"
       "for step in result['trace']:\n"
       "    print(step)\n"
       "```\n\n"
       "**The deliverable:** you run it, and `result['trace']` shows the agent "
       "reasoning — Thought, Action, Observation — on its way to the answer. That "
       "visible reasoning is what ReAct buys you."),
    code("# Your implementation here — build react_agent.py\n"),
])
save(OUT / "project" / "project.ipynb", PROJECT)

# ── SOLUTION NOTEBOOK ─────────────────────────────────────────────────────────
_SOL_CELL1 = (
    f"_SRC = {repr(_REACT_AGENT_SRC)}\n"
    "from pathlib import Path\n"
    "Path('react_agent.py').write_text(_SRC, encoding='utf-8')\n"
    "print('react_agent.py written.')"
)

_SOL_CELL2 = r"""
from react_agent import (
    DEFAULT_TOOLS, build_tool_descriptions, safe_parse_json,
    parse_react_step, format_step, format_observation, build_react_prompt,
    execute_action, call_llm, run_react_agent, ReactAgent,
)

def _make_mock_llm(script):
    state = {'i': 0}
    def _fn(messages):
        i = state['i']
        state['i'] = min(i + 1, len(script) - 1)
        return script[i]
    return _fn

# 1. parse_react_step
a = parse_react_step('Thought: add\nAction: calculator\nInput: {"expression": "2+2"}')
assert a['type'] == 'action' and a['tool'] == 'calculator' and a['input']['expression'] == '2+2'
f = parse_react_step('Thought: done\nFinal Answer: 4')
assert f['type'] == 'final' and f['answer'] == '4'
assert parse_react_step('rambling, no format')['type'] == 'final'
print("✅ parse_react_step (action / final / fallback)")

# 2. formatting
step = {'thought': 't', 'tool': 'calculator', 'input': {'expression': '2+2'}}
assert 'Action: calculator' in format_step(step) and '2+2' in format_step(step)
assert format_observation('4') == 'Observation: 4'
print("✅ format_step + format_observation")

# 3. build_react_prompt
msgs = build_react_prompt('t', DEFAULT_TOOLS, 'Observation: 4')
assert msgs[0]['role'] == 'system' and 'calculator' in msgs[0]['content']
assert '4' in msgs[1]['content']
print("✅ build_react_prompt (tools + scratchpad)")

# 4. execute_action
assert execute_action({'tool': 'calculator', 'input': {'expression': '6*7'}}, DEFAULT_TOOLS) == '42'
assert 'unknown tool' in execute_action({'tool': 'zzz', 'input': {}}, DEFAULT_TOOLS).lower()
assert 'error' in execute_action({'tool': 'calculator', 'input': {}}, DEFAULT_TOOLS).lower()
assert '3.14' in execute_action({'tool': 'lookup', 'input': {'query': 'pi'}}, DEFAULT_TOOLS)
print("✅ execute_action (tool / unknown / error / lookup)")

# 5. call_llm injection
assert call_llm([{'role': 'user', 'content': 'hi'}], llm_fn=lambda m: 'X') == 'X'
print("✅ call_llm (llm_fn injection)")

# 6. run_react_agent: act, observe, finish
script = ['Thought: I should add.\nAction: calculator\nInput: {"expression": "2+2"}',
          'Thought: done.\nFinal Answer: The answer is 4.']
out = run_react_agent('what is 2+2', DEFAULT_TOOLS, llm_fn=_make_mock_llm(script))
assert out['answer'] == 'The answer is 4.' and out['stopped'] is False
assert len(out['trace']) == 2 and out['trace'][0]['observation'] == '4'
print("✅ run_react_agent (act -> observe -> finish, trace recorded)")

# 7. observation fed back into the scratchpad
seen = []
def _spy(messages):
    seen.append(messages[1]['content'])
    if len(seen) == 1:
        return 'Thought: add.\nAction: calculator\nInput: {"expression": "2+2"}'
    return 'Thought: done.\nFinal Answer: 4'
run_react_agent('2+2', DEFAULT_TOOLS, llm_fn=_spy)
assert 'Observation: 4' in seen[1] and 'Observation' not in seen[0]
print("✅ run_react_agent (scratchpad feedback)")

# 8. max_iterations safeguard
never = _make_mock_llm(['Thought: loop.\nAction: calculator\nInput: {"expression": "1+1"}'])
loop = run_react_agent('x', DEFAULT_TOOLS, llm_fn=never, max_iterations=3)
assert loop['stopped'] is True and loop['iterations'] == 3
print("✅ run_react_agent (max_iterations stops runaway loop)")

# 9. ReactAgent
agent = ReactAgent(llm_fn=_make_mock_llm(script))
assert agent.run('2+2?')['answer'] == 'The answer is 4.'
agent.add_tool('shout', 'Uppercase.', lambda args: str(args['text']).upper(), {'text': 'string'})
assert 'shout' in agent.tools and 'shout' not in DEFAULT_TOOLS
assert len(agent.history()) == 1
agent.history().clear()
assert len(agent.history()) == 1
agent.clear_history()
assert len(agent.history()) == 0
print("✅ ReactAgent (run / add_tool / history / clear_history)")

print("\nReAct agent complete!")
"""

SOLUTION = nb([
    md(f"# Day {DAY} — Solution: A ReAct Reasoning Agent"),
    code(_SOL_CELL1),
    code(_SOL_CELL2),
])
save(OUT / "project" / "solution" / "solution.ipynb", SOLUTION)
(OUT / "project" / "solution" / "react_agent.py").write_text(_REACT_AGENT_SRC)

print(f"Day {DAY} notebooks written to {OUT}")
print("  lessons/    day_080_lesson_01.yaml – lesson_05.yaml")
print("  exercises/  exercise_01 – exercise_05")
print("  project/    project.ipynb")
print("  project/solution/  solution.ipynb + react_agent.py")
