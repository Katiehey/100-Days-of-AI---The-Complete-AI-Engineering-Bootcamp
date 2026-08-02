#!/usr/bin/env python3
"""gen_day079.py — generate Day 079: What Is an Agent?"""
from pathlib import Path
import json

ROOT    = Path(__file__).parent.parent
DAY     = "079"
SECTION = "06_agents"
OUT     = ROOT / SECTION / f"day_{DAY}"

(OUT / "exercises").mkdir(parents=True, exist_ok=True)
(OUT / "lessons").mkdir(parents=True, exist_ok=True)
(OUT / "project" / "solution").mkdir(parents=True, exist_ok=True)

# ── deliverable fragments (composed into simple_agent.py AND reused as ─────────
# ── given-code / embedded solutions in the exercises, so they stay in sync) ────

_DOC = '''\
"""simple_agent.py — Day 079: What Is an Agent?

A minimal agent, built from scratch. An *agent* is an LLM wrapped in a loop
that can call tools and decide for itself when it is finished. That is the one
difference from a *pipeline*: a pipeline runs a fixed sequence of steps with no
decisions; an agent chooses its next action each turn until the task is done.

Pieces (each introduced on Day 079):
  safe_calculate           - evaluate arithmetic safely (no eval)
  DEFAULT_TOOLS            - a small tool registry (calculator, word_count)
  build_tool_descriptions  - render the registry as prompt text
  safe_parse_json          - tolerant JSON parser for messy LLM output
  parse_action             - turn LLM text into an action dict (never raises)
  execute_tool             - run one tool from the registry
  call_llm                 - Ollama wrapper with an llm_fn injection point
  build_agent_prompt       - assemble the messages for one step
  run_agent                - the agent loop (bounded by max_iterations)
  SimpleAgent              - a stateful agent binding tools + llm_fn

Setup:
    pip install ollama
    ollama pull llama3.2
"""
'''

_FRAG_CALC = '''\
import ast
import json
import operator

# ── a safe calculator tool (no eval) ─────────────────────────────────────────
_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def _eval_node(node):
    """Recursively evaluate an arithmetic AST node. Raises on anything unsafe."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.operand))
    raise ValueError("unsupported expression")


def safe_calculate(expression):
    """Evaluate a basic arithmetic expression without eval().

    Supports + - * / ** % and parentheses. Anything else (names, calls,
    attribute access) raises ValueError. This is the safe way to give an
    agent a calculator: never eval() untrusted model output.
    """
    tree = ast.parse(expression, mode="eval")
    return _eval_node(tree.body)


# ── the tool registry ────────────────────────────────────────────────────────
# A tool = {description, parameters, fn}. fn takes an args dict, returns a str.
DEFAULT_TOOLS = {
    "calculator": {
        "description": "Evaluate an arithmetic expression, e.g. 2 * (3 + 4).",
        "parameters": {"expression": "string - the arithmetic to evaluate"},
        "fn": lambda args: str(safe_calculate(args["expression"])),
    },
    "word_count": {
        "description": "Count the words in a piece of text.",
        "parameters": {"text": "string - the text to count words in"},
        "fn": lambda args: str(len(str(args["text"]).split())),
    },
}


def build_tool_descriptions(tools):
    """Render a tool registry as a text block for the prompt."""
    lines = []
    for name, spec in tools.items():
        params = ", ".join(spec.get("parameters", {}))
        lines.append("- " + name + "(" + params + "): " + spec["description"])
    return "\\n".join(lines)
'''

_FRAG_PARSE = '''\

# ── parsing messy LLM output ──────────────────────────────────────────────────
def safe_parse_json(text):
    """Extract and parse the first JSON object from messy LLM output.

    LLMs wrap JSON in markdown fences or prose. Instead of fighting that,
    slice from the first '{' to the last '}' and parse that. Returns a dict,
    or None if no valid JSON object is present.
    """
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None
    try:
        data = json.loads(text[start:end + 1])
    except (json.JSONDecodeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def parse_action(text):
    """Turn raw LLM output into an action dict. NEVER raises.

    Returns one of:
      {"type": "tool",   "tool": name, "args": {...}}
      {"type": "finish", "answer": str}
    If the text is not a valid tool call, it falls back to a finish action
    holding the raw text - so a badly-formatted model reply still terminates
    the loop instead of crashing it.
    """
    data = safe_parse_json(text)
    if not isinstance(data, dict):
        return {"type": "finish", "answer": text.strip()}
    tool = data.get("tool")
    if tool and tool != "finish":
        return {"type": "tool", "tool": tool, "args": data.get("args", {})}
    return {"type": "finish", "answer": data.get("answer", text.strip())}
'''

_FRAG_EXEC = '''\

# ── executing tools + calling the model ──────────────────────────────────────
def execute_tool(action, tools):
    """Run one tool action against the registry. Returns a result string.

    Never raises: an unknown tool or a tool error is returned as text so the
    agent can read it and recover on its next turn.
    """
    name = action.get("tool")
    if name not in tools:
        return "Error: unknown tool " + repr(name) + ". Available: " + ", ".join(tools)
    try:
        return str(tools[name]["fn"](action.get("args", {})))
    except Exception as exc:
        return "Error running " + str(name) + ": " + str(exc)


def call_llm(messages, llm_fn=None):
    """Call the chat model. Inject llm_fn(messages) -> str for testing.

    llm_fn=None uses Ollama (llama3.2). A mock llm_fn lets the whole agent
    run offline with no model - which is how the tests drive the loop.
    """
    if llm_fn is not None:
        return llm_fn(messages)
    import ollama
    resp = ollama.chat(model="llama3.2", messages=messages)
    return resp["message"]["content"]
'''

_FRAG_LOOP = '''\

# ── the agent loop ────────────────────────────────────────────────────────────
def build_agent_prompt(task, tools, history):
    """Build the [system, user] messages for one step of the loop."""
    system = "\\n".join([
        "You are a tool-using agent. Solve the task by choosing ONE action at "
        "a time, returned as a single JSON object.",
        "",
        "Available tools:",
        build_tool_descriptions(tools),
        "",
        "To use a tool, reply with exactly:",
        '{"tool": "<name>", "args": {...}}',
        "When you know the final answer, reply with exactly:",
        '{"tool": "finish", "answer": "<answer>"}',
        "",
        "Reply with only the JSON object, nothing else.",
    ])
    lines = ["Task: " + str(task)]
    for step in history:
        lines.append("You called: " + json.dumps(step["action"]))
        lines.append("Result: " + str(step["result"]))
    lines.append("What is your next action?")
    user = "\\n".join(lines)
    return [{"role": "system", "content": system},
            {"role": "user", "content": user}]


def run_agent(task, tools=None, llm_fn=None, max_iterations=10):
    """Run the agent loop until it finishes or hits max_iterations.

    The loop is the whole idea of an agent: build a prompt from the task and
    what has happened so far, ask the model for one action, run it, repeat.
    max_iterations is the safeguard - without it a confused model could loop
    forever. Returns:
      {"answer": str, "steps": [...], "iterations": int, "stopped": bool}
    stopped is True if the loop ran out of iterations without finishing.
    """
    if tools is None:
        tools = DEFAULT_TOOLS
    history = []
    for i in range(max_iterations):
        messages = build_agent_prompt(task, tools, history)
        response = call_llm(messages, llm_fn=llm_fn)
        action = parse_action(response)
        if action["type"] == "finish":
            return {"answer": action["answer"], "steps": history,
                    "iterations": i + 1, "stopped": False}
        result = execute_tool(action, tools)
        history.append({"action": action, "result": result})
    return {"answer": "Stopped: reached max_iterations without finishing.",
            "steps": history, "iterations": max_iterations, "stopped": True}
'''

_FRAG_AGENT = '''\

# ── the agent as a class ──────────────────────────────────────────────────────
class SimpleAgent:
    """A minimal tool-using agent.

    Binds a tool registry and an optional llm_fn at construction, then runs
    tasks through run_agent and keeps a history of every run.

    Example::

        agent = SimpleAgent(llm_fn=my_llm_fn)
        result = agent.run("What is 2 + 2?")
        print(result["answer"])
    """

    def __init__(self, tools=None, llm_fn=None, max_iterations=10):
        # copy so add_tool never mutates the shared DEFAULT_TOOLS global
        self.tools = dict(DEFAULT_TOOLS if tools is None else tools)
        self._llm_fn = llm_fn
        self.max_iterations = max_iterations
        self._history = []

    def add_tool(self, name, description, fn, parameters=None):
        """Register a new tool. fn takes an args dict and returns a result."""
        self.tools[name] = {"description": description,
                            "parameters": parameters or {},
                            "fn": fn}
        return self

    def run(self, task):
        """Run one task through the agent loop. Returns the result dict."""
        result = run_agent(task, tools=self.tools, llm_fn=self._llm_fn,
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

_SIMPLE_AGENT_SRC = (_DOC + _FRAG_CALC + _FRAG_PARSE + _FRAG_EXEC
                     + _FRAG_LOOP + _FRAG_AGENT)


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

    Repeats the last reply once the script is exhausted - handy for testing
    a runaway loop (a model that never says 'finish').
    \"\"\"
    state = {'i': 0}
    def _fn(messages):
        i = state['i']
        state['i'] = min(i + 1, len(script) - 1)
        return script[i]
    return _fn
"""

# ── EX1: safe_calculate + DEFAULT_TOOLS + build_tool_descriptions ─────────────
_EX1_STUB = """\
import ast, operator

def safe_calculate(expression):
    \"\"\"Evaluate arithmetic (+ - * / ** %, parens) without eval().\"\"\"
    raise NotImplementedError

DEFAULT_TOOLS = {}  # calculator + word_count

def build_tool_descriptions(tools):
    \"\"\"Render the registry as a text block for the prompt.\"\"\"
    raise NotImplementedError
"""

_EX1_CHECKS = r"""
score, total = 0, 5
try:
    assert safe_calculate('2 + 3') == 5
    assert safe_calculate('2 * (3 + 4)') == 14
    assert safe_calculate('10 / 4') == 2.5
    score += 1; print("✅ safe_calculate handles arithmetic")

    raised = False
    try:
        safe_calculate('__import__("os").system("echo hi")')
    except Exception:
        raised = True
    assert raised, "safe_calculate should reject non-arithmetic input"
    score += 1; print("✅ safe_calculate rejects non-arithmetic (no eval)")

    assert 'calculator' in DEFAULT_TOOLS and 'word_count' in DEFAULT_TOOLS
    score += 1; print("✅ DEFAULT_TOOLS has calculator and word_count")

    assert DEFAULT_TOOLS['calculator']['fn']({'expression': '6 * 7'}) == '42'
    assert DEFAULT_TOOLS['word_count']['fn']({'text': 'a b c'}) == '3'
    score += 1; print("✅ tool fns run and return strings")

    desc = build_tool_descriptions(DEFAULT_TOOLS)
    assert 'calculator' in desc and 'word_count' in desc
    score += 1; print("✅ build_tool_descriptions lists every tool")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX1 = nb([
    md("# Day 079 — Exercise 1: Tools and the Registry\n\n"
       "**What you'll build:** a safe calculator, a tool registry, and a function "
       "that renders the registry into prompt text.\n\n"
       "**Why it matters:** an agent is an LLM plus a loop plus **tools**. The tool "
       "registry is how the agent knows what it can do. A calculator built on `eval()` "
       "would let model output run arbitrary code — so we parse arithmetic with `ast` "
       "instead."),
    code(_MOCK_HELPER),
    md("## Task\n\n"
       "1. `safe_calculate(expression) -> number` — `ast.parse(expression, mode='eval')`, "
       "then recursively evaluate only `BinOp`/`UnaryOp`/numeric `Constant` nodes using an "
       "`_OPS` dict `{ast.Add: operator.add, ...}`. Raise `ValueError` on anything else.\n"
       "2. `DEFAULT_TOOLS` — a dict `{name: {'description', 'parameters', 'fn'}}` with a "
       "`calculator` (`fn = lambda args: str(safe_calculate(args['expression']))`) and a "
       "`word_count` (`fn = lambda args: str(len(str(args['text']).split()))`).\n"
       "3. `build_tool_descriptions(tools) -> str` — one line per tool: "
       "`- name(params): description`, joined with newlines."),
    md("## Your Implementation"),
    code(_EX1_STUB),
    code(_FRAG_CALC),
    md("## Automated checks"),
    code(_EX1_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _FRAG_CALC + "```\n\n"
       "**Why `ast` instead of `eval`?** `eval('__import__(\"os\").system(...)')` runs "
       "arbitrary code. Walking the AST and only allowing arithmetic nodes means the "
       "worst a malicious expression can do is raise `ValueError`.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_01.ipynb", EX1)

# ── EX2: safe_parse_json + parse_action ──────────────────────────────────────
_EX2_GIVEN = _MOCK_HELPER + _FRAG_CALC

_EX2_STUB = """\
def safe_parse_json(text):
    \"\"\"Extract + parse the first JSON object from messy text. Returns dict|None.\"\"\"
    raise NotImplementedError

def parse_action(text):
    \"\"\"Turn LLM text into an action dict. NEVER raises.
    {'type':'tool','tool':..,'args':..} or {'type':'finish','answer':..}.
    \"\"\"
    raise NotImplementedError
"""

_EX2_CHECKS = r"""
score, total = 0, 5
try:
    clean = safe_parse_json('{"tool": "calculator", "args": {"expression": "2+2"}}')
    assert clean['tool'] == 'calculator'
    score += 1; print("✅ safe_parse_json parses clean JSON")

    fenced = 'Sure!\n```json\n{"tool": "finish", "answer": "hi"}\n```'
    assert safe_parse_json(fenced)['answer'] == 'hi'
    score += 1; print("✅ safe_parse_json tolerates fences and prose")

    assert safe_parse_json('no json here at all') is None
    score += 1; print("✅ safe_parse_json returns None on garbage")

    a = parse_action('{"tool": "calculator", "args": {"expression": "1+1"}}')
    assert a['type'] == 'tool' and a['tool'] == 'calculator'
    assert a['args']['expression'] == '1+1'
    score += 1; print("✅ parse_action extracts a tool action")

    f = parse_action('The answer is 42, no JSON here.')
    assert f['type'] == 'finish' and '42' in f['answer']
    score += 1; print("✅ parse_action falls back to finish (never raises)")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX2 = nb([
    md("# Day 079 — Exercise 2: Parsing LLM Output\n\n"
       "**What you'll build:** a tolerant JSON parser and an action parser that "
       "never raises.\n\n"
       "**Why it matters:** llama3.2 won't always return perfect JSON — it wraps "
       "output in ```` ```json ```` fences or adds a sentence first. The parser has to "
       "cope, and `parse_action` must always return *something* so the loop can't "
       "crash on a malformed reply."),
    code(_EX2_GIVEN),
    md("## Task\n\n"
       "1. `safe_parse_json(text) -> dict | None` — slice from the first `{` to the "
       "last `}` (`text.find('{')`, `text.rfind('}')`), `json.loads` that slice inside "
       "`try/except`. Return the dict, or `None` if there's no object or it doesn't parse.\n"
       "2. `parse_action(text) -> dict` — call `safe_parse_json`. If it's a dict with a "
       "`tool` that isn't `'finish'`: return `{'type':'tool','tool':..,'args':..}`. "
       "Otherwise return `{'type':'finish','answer':..}` (use the parsed `answer`, or the "
       "raw text). Must **never** raise."),
    md("## Your Implementation"),
    code(_EX2_STUB),
    code(_FRAG_PARSE),
    md("## Automated checks"),
    code(_EX2_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _FRAG_PARSE + "```\n\n"
       "**Why slice the braces instead of a regex?** The first `{` to the last `}` is "
       "the JSON object regardless of any fences or prose around it — one line, no "
       "regex, and it degrades to `None` cleanly when there's no object.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_02.ipynb", EX2)

# ── EX3: execute_tool + call_llm ─────────────────────────────────────────────
_EX3_GIVEN = _MOCK_HELPER + _FRAG_CALC + _FRAG_PARSE

_EX3_STUB = """\
def execute_tool(action, tools):
    \"\"\"Run one tool from the registry. Returns a result string. Never raises.\"\"\"
    raise NotImplementedError

def call_llm(messages, llm_fn=None):
    \"\"\"Call the chat model, or the injected llm_fn(messages) -> str.\"\"\"
    raise NotImplementedError
"""

_EX3_CHECKS = r"""
score, total = 0, 5
try:
    r = execute_tool({'type': 'tool', 'tool': 'calculator',
                      'args': {'expression': '2+2'}}, DEFAULT_TOOLS)
    assert r == '4'
    score += 1; print("✅ execute_tool runs a real tool")

    r2 = execute_tool({'type': 'tool', 'tool': 'nope', 'args': {}}, DEFAULT_TOOLS)
    assert 'unknown tool' in r2.lower()
    score += 1; print("✅ execute_tool reports unknown tools (no crash)")

    r3 = execute_tool({'type': 'tool', 'tool': 'calculator', 'args': {}},
                      DEFAULT_TOOLS)
    assert 'error' in r3.lower()
    score += 1; print("✅ execute_tool captures tool errors (never raises)")

    got = call_llm([{'role': 'user', 'content': 'hi'}], llm_fn=lambda m: 'MOCK')
    assert got == 'MOCK'
    score += 1; print("✅ call_llm uses the injected llm_fn")

    captured = {}
    def _spy(m):
        captured['m'] = m
        return 'ok'
    call_llm([{'role': 'user', 'content': 'x'}], llm_fn=_spy)
    assert isinstance(captured['m'], list) and captured['m'][0]['role'] == 'user'
    score += 1; print("✅ llm_fn receives the messages list")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX3 = nb([
    md("# Day 079 — Exercise 3: Executing Tools\n\n"
       "**What you'll build:** the two functions that touch the outside world — "
       "`execute_tool` (runs a tool) and `call_llm` (calls the model).\n\n"
       "**Why it matters:** both are **injection points**. `call_llm` takes an "
       "`llm_fn` so the whole agent can run with a mock model — that's exactly how "
       "these tests, and the gate, run with no Ollama at all."),
    code(_EX3_GIVEN),
    md("## Task\n\n"
       "1. `execute_tool(action, tools) -> str` — look up `action['tool']` in `tools`. "
       "If missing, return an `Error: unknown tool ...` string. Otherwise call "
       "`tools[name]['fn'](action.get('args', {}))` inside `try/except` and return the "
       "result as a string (return the exception text on error). Must **never** raise.\n"
       "2. `call_llm(messages, llm_fn=None) -> str` — if `llm_fn` is given, "
       "`return llm_fn(messages)`. Otherwise `import ollama`, "
       "`ollama.chat(model='llama3.2', messages=messages)`, return "
       "`resp['message']['content']`."),
    md("## Your Implementation"),
    code(_EX3_STUB),
    code(_FRAG_EXEC),
    md("## Automated checks"),
    code(_EX3_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _FRAG_EXEC + "```\n\n"
       "**Why return errors as text instead of raising?** The agent reads the result "
       "string on its next turn. An error it can *see* (`Error running calculator: ...`) "
       "is something it can recover from; an exception just kills the loop.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_03.ipynb", EX3)

# ── EX4: build_agent_prompt + run_agent ──────────────────────────────────────
_EX4_GIVEN = _MOCK_HELPER + _FRAG_CALC + _FRAG_PARSE + _FRAG_EXEC

_EX4_STUB = """\
def build_agent_prompt(task, tools, history):
    \"\"\"Build the [system, user] messages for one step of the loop.\"\"\"
    raise NotImplementedError

def run_agent(task, tools=None, llm_fn=None, max_iterations=10):
    \"\"\"Run the agent loop. Returns {answer, steps, iterations, stopped}.\"\"\"
    raise NotImplementedError
"""

_EX4_CHECKS = r"""
score, total = 0, 5
try:
    msgs = build_agent_prompt('add 2 and 2', DEFAULT_TOOLS, [])
    assert isinstance(msgs, list) and msgs[0]['role'] == 'system'
    assert 'calculator' in msgs[0]['content']
    score += 1; print("✅ build_agent_prompt returns system+user messages")

    msgs2 = build_agent_prompt('t', DEFAULT_TOOLS,
                               [{'action': {'tool': 'calculator'}, 'result': '4'}])
    assert '4' in msgs2[1]['content']
    score += 1; print("✅ history is rendered into the user message")

    script = ['{"tool": "calculator", "args": {"expression": "2+2"}}',
              '{"tool": "finish", "answer": "It is 4."}']
    out = run_agent('what is 2+2', DEFAULT_TOOLS, llm_fn=_make_mock_llm(script))
    assert out['answer'] == 'It is 4.' and out['stopped'] is False
    score += 1; print("✅ run_agent loops: tool call, then finish")

    assert len(out['steps']) == 1 and out['steps'][0]['result'] == '4'
    score += 1; print("✅ run_agent records each tool step with its result")

    never = _make_mock_llm(['{"tool": "calculator", "args": {"expression": "1+1"}}'])
    loop = run_agent('x', DEFAULT_TOOLS, llm_fn=never, max_iterations=3)
    assert loop['stopped'] is True and loop['iterations'] == 3
    score += 1; print("✅ max_iterations stops a runaway loop")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX4 = nb([
    md("# Day 079 — Exercise 4: The Agent Loop\n\n"
       "**What you'll build:** `build_agent_prompt` (assembles one step) and "
       "`run_agent` (the loop itself).\n\n"
       "**Why it matters:** the loop is the whole difference between an agent and a "
       "pipeline. It asks the model for one action, runs it, feeds the result back, "
       "and repeats — until the model says *finish* or `max_iterations` runs out. That "
       "iteration cap is the safeguard against a confused model looping forever."),
    code(_EX4_GIVEN),
    md("## Task\n\n"
       "1. `build_agent_prompt(task, tools, history) -> list[dict]` — a `system` message "
       "describing the tools (use `build_tool_descriptions`) and the JSON action format, "
       "and a `user` message with the task plus each past step "
       "(`You called: ...` / `Result: ...`). Return `[system_msg, user_msg]`.\n"
       "2. `run_agent(task, tools=None, llm_fn=None, max_iterations=10) -> dict` — "
       "default `tools` to `DEFAULT_TOOLS`; loop `for i in range(max_iterations)`: "
       "`build_agent_prompt` → `call_llm` → `parse_action`. On `finish` return "
       "`{answer, steps, iterations, stopped: False}`. Otherwise `execute_tool`, append "
       "`{action, result}` to history, continue. If the loop ends, return "
       "`stopped: True`."),
    md("## Your Implementation"),
    code(_EX4_STUB),
    code(_FRAG_LOOP),
    md("## Automated checks"),
    code(_EX4_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _FRAG_LOOP + "```\n\n"
       "**Why `for i in range(max_iterations)` and not `while True`?** A model that "
       "never emits `finish` would spin forever. Bounding the loop turns a hang into a "
       "clean `stopped: True` result — the single most important agent safeguard.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_04.ipynb", EX4)

# ── EX5: SimpleAgent ─────────────────────────────────────────────────────────
_EX5_GIVEN = (_MOCK_HELPER + _FRAG_CALC + _FRAG_PARSE + _FRAG_EXEC + _FRAG_LOOP)

_EX5_STUB = """\
class SimpleAgent:
    \"\"\"A minimal tool-using agent binding tools + llm_fn.\"\"\"

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
    script = ['{"tool": "calculator", "args": {"expression": "2+2"}}',
              '{"tool": "finish", "answer": "4"}']
    agent = SimpleAgent(llm_fn=_make_mock_llm(script))
    out = agent.run('what is 2+2?')
    assert out['answer'] == '4'
    score += 1; print("✅ SimpleAgent.run returns the final answer")

    assert 'calculator' in agent.tools and 'word_count' in agent.tools
    score += 1; print("✅ SimpleAgent uses DEFAULT_TOOLS by default")

    agent.add_tool('shout', 'Uppercase text.',
                   lambda args: str(args['text']).upper(), {'text': 'string'})
    assert 'shout' in agent.tools
    assert 'shout' not in DEFAULT_TOOLS
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
    md("# Day 079 — Exercise 5: SimpleAgent\n\n"
       "**What you'll build:** the capstone class that binds tools + `llm_fn` and "
       "keeps a run history.\n\n"
       "**Why it matters:** the module functions do the work; the class is a "
       "convenient binding layer so you set up the model and tools once, then call "
       "`.run()` many times. `add_tool` extends the agent at runtime — the start of "
       "an open-ended assistant."),
    code(_EX5_GIVEN),
    md("## Task\n\n"
       "`SimpleAgent(tools=None, llm_fn=None, max_iterations=10)`\n\n"
       "1. `__init__` — store `dict(DEFAULT_TOOLS if tools is None else tools)` "
       "(**copy**, so `add_tool` doesn't mutate the global), plus `_llm_fn`, "
       "`max_iterations`, and `_history = []`.\n"
       "2. `add_tool(name, description, fn, parameters=None)` — add "
       "`{'description','parameters','fn'}` to `self.tools`; return `self`.\n"
       "3. `run(task)` — call `run_agent` with the bound tools/llm_fn; append "
       "`{'task','result'}` to `_history`; return the result.\n"
       "4. `history()` — return `list(self._history)` (a copy).\n"
       "5. `clear_history()` — `self._history.clear()` (in place)."),
    md("## Your Implementation"),
    code(_EX5_STUB),
    code(_FRAG_AGENT),
    md("## Automated checks"),
    code(_EX5_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _FRAG_AGENT + "```\n\n"
       "**Why `dict(DEFAULT_TOOLS ...)`?** Without the copy, `self.tools` would *be* "
       "the module-level `DEFAULT_TOOLS`, so `add_tool` would leak into every other "
       "agent. Copying gives each agent its own registry.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_05.ipynb", EX5)

# ── YAML lessons ──────────────────────────────────────────────────────────────
_LESSON_01 = """\
day: "079"
lesson: 1
title: "What Is an Agent?"
slides:
  - type: title
    heading: "What Is an Agent?"
    subheading: "Section 6 opens - from fixed pipelines to autonomous loops"
    narration: >
      Sections 1 through 5 built pipelines: a fixed sequence of steps that runs
      the same way every time. Section 6 builds agents. An agent is a language
      model wrapped in a loop that can call tools and decide for itself when it
      is finished. Over the next ten days you build agents from scratch: the
      loop, ReAct reasoning, tool routing, memory, planning, multi-agent teams,
      MCP, retrieval, and guardrails. Day 79 is the foundation - the smallest
      thing that is genuinely an agent.

  - type: concept
    label: "Pipeline vs agent"
    heading: "Pipeline vs Agent"
    body: >
      The one difference is who decides the next step.
    bullets:
      - "Pipeline: you hard-code the steps - describe, then summarise, then save"
      - "Agent: the model chooses the next action each turn, from a set of tools"
      - "Pipeline path is fixed; agent path depends on what it sees along the way"
      - "Agent = LLM + a loop + tools + a stop condition"
      - "More flexible, but needs safeguards - a loop can misbehave"
    narration: >
      In a pipeline you decide the order of operations in advance. In an agent
      the model decides: given the task and what has happened so far, it picks
      the next action. That is the whole idea. It buys flexibility - the agent
      can handle tasks whose steps you could not enumerate ahead of time - at
      the cost of needing guardrails, because a loop that decides its own steps
      can also decide to loop forever.

  - type: concept
    label: "The loop"
    heading: "The Agent Loop"
    body: >
      Every agent, no matter how fancy, is this loop.
    bullets:
      - "1. Build a prompt from the task + history so far"
      - "2. Ask the model for ONE action"
      - "3. If the action is 'finish', return the answer"
      - "4. Otherwise run the tool and record the result"
      - "5. Repeat - up to max_iterations"
    narration: >
      Read the five steps. Build a prompt, ask for one action, check whether it
      is a finish, run the tool if not, record what happened, and go around
      again. The loop terminates two ways: the model says it is done, or it hits
      the iteration cap. Today you build exactly this. Day 80 makes the model
      reason out loud before each action - the ReAct pattern - but the skeleton
      never changes.

  - type: concept
    label: "Tool registry"
    heading: "Tools Live in a Registry"
    body: >
      A tool is a name, a description, and a function.
    bullets:
      - "Registry: dict of name -> {description, parameters, fn}"
      - "description + parameters go into the prompt so the model can choose"
      - "fn(args_dict) -> str is what actually runs"
      - "Add a capability by adding one dict entry - nothing else changes"
      - "This is the same tool-use idea as Day 17, now driven by a loop"
    narration: >
      The registry is the menu of things the agent can do. Each entry has a
      description and parameter list, which get rendered into the prompt so the
      model knows the option exists, and a function that does the work. Adding a
      new ability is one dict entry. You saw tool use on Day 17 as a single call
      and response; an agent is that same idea placed inside a loop so tools can
      be chained without you scripting the chain.

  - type: code
    label: "safe_calculate"
    heading: "A Safe Calculator - Never eval()"
    code: |
      import ast, operator
      _OPS = {ast.Add: operator.add, ast.Sub: operator.sub,
              ast.Mult: operator.mul, ast.Div: operator.truediv,
              ast.Pow: operator.pow, ast.Mod: operator.mod,
              ast.USub: operator.neg}

      def _eval_node(node):
          if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
              return node.value
          if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
              return _OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
          if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
              return _OPS[type(node.op)](_eval_node(node.operand))
          raise ValueError("unsupported expression")

      def safe_calculate(expression):
          tree = ast.parse(expression, mode="eval")
          return _eval_node(tree.body)
    narration: >
      The calculator is the agent's first tool, and it shows a rule you will
      follow all section: never call eval on model output. eval would happily
      run underscore-underscore-import to open a shell. Instead we parse the
      expression into an abstract syntax tree and walk it, allowing only numbers
      and arithmetic operators. Anything else - a name, a function call - raises
      ValueError. The worst a malicious expression can do is fail.

  - type: exercise
    heading: "Exercise 1: Tools and the Registry"
    prompt: >
      Implement safe_calculate with an _OPS dict and a recursive _eval_node.
      Build DEFAULT_TOOLS with a calculator and a word_count tool, each with
      description, parameters, and fn. Implement build_tool_descriptions(tools)
      to render one line per tool for the prompt.
    hint: >
      ast.parse(expression, mode="eval"); walk node.body. _OPS maps ast node
      types to operator functions. Tool fn takes an args dict and returns a
      string. build_tool_descriptions joins '- name(params): description' lines.
    narration: >
      This exercise builds the agent's hands - the tools - and the safe
      calculator that keeps model output from running as code.

  - type: summary
    heading: "Lesson 1 Summary"
    bullets:
      - "Pipeline = fixed steps; agent = model chooses the next action in a loop"
      - "Agent = LLM + loop + tools + stop condition"
      - "Tool registry: name -> {description, parameters, fn(args) -> str}"
      - "safe_calculate uses ast, never eval - never run model output as code"
      - "Day 80 adds ReAct reasoning; the loop skeleton stays the same"
    narration: >
      Lesson 2 tackles the messy reality of LLM output: parsing it into an
      action the loop can act on, without ever crashing.
"""

_LESSON_02 = """\
day: "079"
lesson: 2
title: "Parsing LLM Output"
slides:
  - type: title
    heading: "Parsing LLM Output"
    subheading: "Turn messy text into an action - and never crash"
    narration: >
      The model's reply is just text. Before the loop can act on it, you have to
      turn that text into a structured action: which tool, which arguments, or a
      final answer. Small local models like llama3.2 do not always return clean
      JSON, so the parser must be forgiving - and it must never raise, or one bad
      reply takes down the whole agent.

  - type: concept
    label: "Why parsing is hard"
    heading: "LLMs Don't Return Clean JSON"
    body: >
      Real replies are messy in predictable ways.
    bullets:
      - "Wrapped in markdown fences: ```json ... ```"
      - "A sentence of preamble before the JSON"
      - "Single quotes, trailing commas, or extra prose after"
      - "Sometimes just a plain-English answer with no JSON at all"
      - "The parser has to survive all of these"
    narration: >
      Large hosted models can be pinned to strict JSON, but a small local model
      will add a friendly sentence, or fence the JSON, or occasionally just
      answer in plain English. Rather than fight this with an ever-growing pile
      of regexes, use a robust trick: find the first opening brace and the last
      closing brace, and parse whatever is between them. Fences and prose fall
      away automatically.

  - type: code
    label: "safe_parse_json"
    heading: "Slice the Braces, Then Parse"
    code: |
      import json

      def safe_parse_json(text):
          start, end = text.find("{"), text.rfind("}")
          if start == -1 or end == -1 or end < start:
              return None
          try:
              data = json.loads(text[start:end + 1])
          except (json.JSONDecodeError, ValueError):
              return None
          return data if isinstance(data, dict) else None
    narration: >
      find returns the index of the first opening brace; rfind the last closing
      brace. The slice between them is the JSON object, whatever surrounds it.
      json.loads runs inside a try, so a malformed slice returns None instead of
      raising. And we confirm the result is a dict, because the loop expects a
      dict. One short function, no regex, and it degrades cleanly to None.

  - type: code
    label: "parse_action"
    heading: "parse_action - Never Raises"
    code: |
      def parse_action(text):
          data = safe_parse_json(text)
          if not isinstance(data, dict):
              return {"type": "finish", "answer": text.strip()}
          tool = data.get("tool")
          if tool and tool != "finish":
              return {"type": "tool", "tool": tool, "args": data.get("args", {})}
          return {"type": "finish", "answer": data.get("answer", text.strip())}
    narration: >
      parse_action turns the parsed dict into one of two shapes: a tool action
      or a finish action. If there is no JSON at all, it treats the whole reply
      as a final answer - so even a plain-English response ends the loop
      gracefully. This is the fallback rule for the whole section: a parser for
      agent output must always return something the loop can act on, never throw.

  - type: concept
    label: "Fail-safe design"
    heading: "Fallbacks Keep the Loop Alive"
    body: >
      A parser that raises turns a bad reply into a dead agent.
    bullets:
      - "No JSON -> treat the whole text as the final answer"
      - "Unknown shape -> finish, don't guess a tool"
      - "The loop always gets a valid action dict back"
      - "Errors become data the agent can see, not exceptions"
      - "Same principle drives execute_tool in Lesson 3"
    narration: >
      The theme is fail-safe design. Every place the agent meets uncertain input
      - the model's reply here, a tool's result next lesson - you convert
      problems into data rather than exceptions. A finish fallback means the
      worst case is a slightly wrong answer, not a crash. That resilience is what
      lets an agent run unattended.

  - type: exercise
    heading: "Exercise 2: Parsing LLM Output"
    prompt: >
      Implement safe_parse_json (slice first brace to last brace, json.loads in
      a try, return dict or None) and parse_action (tool action when there is a
      non-finish tool key, otherwise a finish action with the answer or raw
      text). parse_action must never raise.
    hint: >
      text.find('{'), text.rfind('}'); json.loads(text[start:end+1]) in
      try/except. parse_action: safe_parse_json first; branch on data.get('tool').
    narration: >
      This exercise makes the agent robust to real model output - the difference
      between a demo and something that survives contact with llama3.2.

  - type: summary
    heading: "Lesson 2 Summary"
    bullets:
      - "LLM replies are messy: fences, preamble, plain prose"
      - "safe_parse_json: slice first '{' to last '}', json.loads in try -> dict|None"
      - "parse_action returns {'type':'tool'|'finish', ...} and NEVER raises"
      - "No JSON -> finish with the raw text as the answer"
      - "Fail-safe: turn uncertain input into data, not exceptions"
    narration: >
      Lesson 3 runs the action the parser produced - executing tools and calling
      the model, both as injection points so the agent can run offline.
"""

_LESSON_03 = """\
day: "079"
lesson: 3
title: "Executing Tools"
slides:
  - type: title
    heading: "Executing Tools"
    subheading: "Run the action - and make the model an injection point"
    narration: >
      Now the agent acts. execute_tool takes the action the parser produced and
      runs the matching tool. call_llm asks the model for the next action. Both
      are written so they can be swapped for mocks - that injection is what lets
      the entire agent run in tests with no Ollama, no network, and no cost.

  - type: code
    label: "execute_tool"
    heading: "execute_tool - Errors Become Text"
    code: |
      def execute_tool(action, tools):
          name = action.get("tool")
          if name not in tools:
              return "Error: unknown tool " + repr(name)
          try:
              return str(tools[name]["fn"](action.get("args", {})))
          except Exception as exc:
              return "Error running " + str(name) + ": " + str(exc)
    narration: >
      execute_tool looks up the tool by name and calls its function with the
      args dict. Two things can go wrong: the model names a tool that does not
      exist, or the tool itself errors - say the calculator gets a bad
      expression. Both are caught and returned as a string. That is deliberate:
      the agent sees the error text on its next turn and can correct course,
      which is impossible if the tool throws and kills the loop.

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
      call_llm is one if-statement. If an llm_fn is supplied, call it and return.
      Otherwise talk to Ollama. The signature is the section-wide contract:
      llm_fn takes the messages list and returns the content string. Because the
      whole agent reaches the model only through this function, injecting a mock
      llm_fn makes the entire loop testable offline - exactly how the gate runs.

  - type: concept
    label: "Injection for agents"
    heading: "Mock the Model, Mock the Tools"
    body: >
      Two injection points make an agent fully testable.
    bullets:
      - "llm_fn(messages) -> str replaces the model"
      - "The tool registry itself is injectable - pass mock tools"
      - "A scripted llm_fn drives the loop: tool call, then finish"
      - "Tests assert on the path taken, not on model quality"
      - "Zero cost, deterministic, no network - runs anywhere"
    narration: >
      This is the pattern that makes agents testable. The model is behind
      llm_fn; the tools are the registry you pass in. Give the agent a scripted
      llm_fn that returns a tool call and then a finish, and you can assert that
      the loop ran the tool, recorded the result, and stopped - all without a
      real model. Determinism turns an unpredictable LLM system into something
      you can unit-test.

  - type: exercise
    heading: "Exercise 3: Executing Tools"
    prompt: >
      Implement execute_tool(action, tools): unknown tool -> error string; else
      call the tool fn in try/except and return the result as a string, never
      raising. Implement call_llm(messages, llm_fn=None): use llm_fn if given,
      else ollama.chat with llama3.2.
    hint: >
      execute_tool: check name in tools; str(tools[name]['fn'](args)) in
      try/except. call_llm: if llm_fn is not None return llm_fn(messages).
    narration: >
      This exercise gives the agent its ability to act and its testable seam -
      the model behind a single injectable function.

  - type: summary
    heading: "Lesson 3 Summary"
    bullets:
      - "execute_tool runs the tool fn; unknown tool + errors -> text, never raises"
      - "call_llm(messages, llm_fn=None): llm_fn injection or ollama.chat llama3.2"
      - "llm_fn(messages) -> str is the section-wide model contract"
      - "Two injection points: the model (llm_fn) and the tools (registry)"
      - "A scripted llm_fn makes the whole loop deterministic and offline"
    narration: >
      Lesson 4 assembles these pieces into the loop itself - run_agent, with the
      max_iterations safeguard that keeps an agent from running forever.
"""

_LESSON_04 = """\
day: "079"
lesson: 4
title: "The Agent Loop"
slides:
  - type: title
    heading: "The Agent Loop"
    subheading: "run_agent - where autonomy actually happens"
    narration: >
      Everything so far has been parts. run_agent is the engine that turns them
      into an agent. It builds a prompt from the task and the history, asks the
      model for an action, runs it, and repeats until the model finishes or the
      iteration cap is reached. This one function is where a pipeline becomes an
      agent.

  - type: code
    label: "build_agent_prompt"
    heading: "build_agent_prompt - Task + History"
    code: |
      def build_agent_prompt(task, tools, history):
          system = "\\n".join([
              "You are a tool-using agent. Choose ONE action as JSON.",
              "Available tools:", build_tool_descriptions(tools),
              'To use a tool: {"tool": "<name>", "args": {...}}',
              'To finish:      {"tool": "finish", "answer": "<answer>"}',
          ])
          lines = ["Task: " + str(task)]
          for step in history:
              lines.append("You called: " + json.dumps(step["action"]))
              lines.append("Result: " + str(step["result"]))
          lines.append("What is your next action?")
          return [{"role": "system", "content": system},
                  {"role": "user", "content": "\\n".join(lines)}]
    narration: >
      The system message tells the model its job, lists the tools, and shows the
      exact JSON format for a tool call and for finishing. The user message
      carries the task followed by every past step - what the agent called and
      what came back. Feeding the history back each turn is what lets the model
      build on its own earlier actions instead of starting from scratch.

  - type: code
    label: "run_agent"
    heading: "run_agent - The Bounded Loop"
    code: |
      def run_agent(task, tools=None, llm_fn=None, max_iterations=10):
          if tools is None:
              tools = DEFAULT_TOOLS
          history = []
          for i in range(max_iterations):
              messages = build_agent_prompt(task, tools, history)
              action = parse_action(call_llm(messages, llm_fn=llm_fn))
              if action["type"] == "finish":
                  return {"answer": action["answer"], "steps": history,
                          "iterations": i + 1, "stopped": False}
              result = execute_tool(action, tools)
              history.append({"action": action, "result": result})
          return {"answer": "Stopped: reached max_iterations without finishing.",
                  "steps": history, "iterations": max_iterations, "stopped": True}
    narration: >
      Read the loop. Build the prompt, call the model, parse the action. If it is
      a finish, return the answer along with the steps and a stopped flag set to
      false. Otherwise execute the tool, append the step, and go round again. The
      for-range over max_iterations is the safeguard: if the model never finishes,
      the loop returns with stopped set to true instead of hanging forever.

  - type: concept
    label: "max_iterations"
    heading: "Why the Iteration Cap Matters"
    body: >
      An unbounded agent loop is a bug waiting to happen.
    bullets:
      - "A confused model can call tools forever, never finishing"
      - "for i in range(max_iterations) turns a hang into a clean return"
      - "Return stopped: True so the caller knows it did not finish"
      - "Default 10 is plenty for simple tasks; raise it for harder ones"
      - "Every agent loop in this course carries this cap"
    narration: >
      The iteration cap is the single most important safety feature of an agent
      loop. Without it, a model that keeps asking for tools - or gets stuck in a
      two-step cycle - hangs your program. With it, the worst case is a bounded
      amount of work and an honest stopped-equals-true result. Every loop you
      write this section has this cap; it is not optional.

  - type: exercise
    heading: "Exercise 4: The Agent Loop"
    prompt: >
      Implement build_agent_prompt(task, tools, history) returning [system, user]
      messages with the tools and history rendered in. Implement
      run_agent(task, tools=None, llm_fn=None, max_iterations=10) as the bounded
      loop returning {answer, steps, iterations, stopped}.
    hint: >
      build_agent_prompt: system lists tools + JSON format; user has task + each
      step. run_agent: for i in range(max_iterations); finish -> return; else
      execute_tool + append; loop end -> stopped True.
    narration: >
      This is the heart of the day. When your scripted mock drives it - tool
      call, then finish - you have a working agent.

  - type: summary
    heading: "Lesson 4 Summary"
    bullets:
      - "build_agent_prompt: system (tools + format) + user (task + history)"
      - "History is fed back every turn so the model builds on past steps"
      - "run_agent: for i in range(max_iterations); finish returns, else run + record"
      - "Returns {answer, steps, iterations, stopped}"
      - "max_iterations turns a potential hang into a clean stopped: True"
    narration: >
      Lesson 5 wraps the loop in a class - SimpleAgent - that binds the model and
      tools once and remembers every run.
"""

_LESSON_05 = """\
day: "079"
lesson: 5
title: "SimpleAgent - Putting It Together"
slides:
  - type: title
    heading: "SimpleAgent"
    subheading: "One class: bind tools + model, run tasks, remember runs"
    narration: >
      The module functions already form a complete agent. SimpleAgent is the
      convenience layer: bind the tools and the model once at construction, then
      call run as many times as you like. It also keeps a history of runs and
      lets you add new tools at runtime - the first step toward an open-ended
      assistant.

  - type: code
    label: "SimpleAgent"
    heading: "SimpleAgent - Bind Once, Run Often"
    code: |
      class SimpleAgent:
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
              result = run_agent(task, tools=self.tools, llm_fn=self._llm_fn,
                                 max_iterations=self.max_iterations)
              self._history.append({"task": task, "result": result})
              return result

          def history(self):
              return list(self._history)

          def clear_history(self):
              self._history.clear()
    narration: >
      The constructor copies DEFAULT_TOOLS with dict, then stores the model, the
      iteration cap, and an empty history. run delegates straight to run_agent
      with the bound tools and model, then records the run. history returns a
      copy so a caller can not mutate the log by accident, and clear_history
      empties it in place. Same class pattern as all of Section 5: bind at
      construction, delegate in methods.

  - type: concept
    label: "The copy matters"
    heading: "Copy the Registry, Don't Share It"
    body: >
      dict(DEFAULT_TOOLS) gives each agent its own tools.
    bullets:
      - "Without the copy, self.tools IS the global DEFAULT_TOOLS"
      - "add_tool would then leak into every other agent and future default"
      - "dict(...) makes a shallow copy - a fresh registry per agent"
      - "Same class as Section 5: bind at construction, delegate in methods"
      - "history() returns a copy; clear_history() empties in place"
    narration: >
      One subtle bug worth naming: if you write self.tools equals
      DEFAULT_TOOLS, every agent shares the same dictionary, so a tool added to
      one appears in all of them. Wrapping it in dict gives each agent its own
      copy. It is the same reason history returns list of the history rather than
      the live list - shared mutable state is where surprising bugs live.

  - type: exercise
    heading: "Exercise 5: SimpleAgent"
    prompt: >
      Implement SimpleAgent: __init__ copies DEFAULT_TOOLS and stores llm_fn,
      max_iterations, and an empty history; add_tool registers a tool and returns
      self; run delegates to run_agent and records the run; history returns a
      copy; clear_history empties in place.
    hint: >
      self.tools = dict(DEFAULT_TOOLS if tools is None else tools). run calls
      run_agent with the bound tools/llm_fn. history() returns list(self._history).
    narration: >
      This completes your minimal agent - a class you can hand a model and a set
      of tools and ask to solve tasks.

  - type: summary
    heading: "Lesson 5 Summary - Day 79 Complete"
    bullets:
      - "SimpleAgent binds tools + llm_fn once, runs tasks, remembers runs"
      - "dict(DEFAULT_TOOLS ...) - copy so add_tool doesn't mutate the global"
      - "run delegates to run_agent and appends to _history"
      - "history() returns a copy; clear_history() empties in place"
      - "Agent = LLM + loop + tools + max_iterations - you built it from scratch"
    narration: >
      You built an agent from nothing: a safe tool, a forgiving parser, an
      injectable model, a bounded loop, and a class to hold it. Day 80 keeps this
      skeleton and adds ReAct - making the model reason out loud, Thought then
      Action then Observation, before every step.
"""

for i, content in enumerate([_LESSON_01, _LESSON_02, _LESSON_03,
                               _LESSON_04, _LESSON_05], start=1):
    (OUT / "lessons" / f"day_{DAY}_lesson_0{i}.yaml").write_text(content)

# ── PROJECT NOTEBOOK ──────────────────────────────────────────────────────────
PROJECT = nb([
    md(f"# Day {DAY} — Project: A Minimal Agent from Scratch\n\n"
       "## Objective\n\n"
       "Build `simple_agent.py` — an agent that is an LLM wrapped in a loop, able "
       "to call tools and decide when it is finished.\n\n"
       "## Deliverable\n\n"
       "`simple_agent.py` with:\n\n"
       "- `safe_calculate(expression)` — arithmetic via `ast`, never `eval`\n"
       "- `DEFAULT_TOOLS` — registry of `calculator` + `word_count`\n"
       "- `build_tool_descriptions(tools) -> str`\n"
       "- `safe_parse_json(text) -> dict | None`\n"
       "- `parse_action(text) -> dict` (never raises)\n"
       "- `execute_tool(action, tools) -> str`\n"
       "- `call_llm(messages, llm_fn=None) -> str`\n"
       "- `build_agent_prompt(task, tools, history) -> list[dict]`\n"
       "- `run_agent(task, tools=None, llm_fn=None, max_iterations=10) -> dict`\n"
       "- `SimpleAgent(tools=None, llm_fn=None, max_iterations=10)` with "
       "`add_tool/run/history/clear_history`\n\n"
       "## Usage (with Ollama running + llama3.2 pulled)\n\n"
       "```python\n"
       "from simple_agent import SimpleAgent\n"
       "agent = SimpleAgent()\n"
       "result = agent.run('What is 17 * 23, and how many words are in this sentence?')\n"
       "print(result['answer'])\n"
       "```\n\n"
       "**The deliverable:** you run it, it loops — calling the calculator, reading "
       "the result, and finishing with an answer. That loop is the agent."),
    code("# Your implementation here — build simple_agent.py\n"),
])
save(OUT / "project" / "project.ipynb", PROJECT)

# ── SOLUTION NOTEBOOK ─────────────────────────────────────────────────────────
_SOL_CELL1 = (
    f"_SRC = {repr(_SIMPLE_AGENT_SRC)}\n"
    "from pathlib import Path\n"
    "Path('simple_agent.py').write_text(_SRC, encoding='utf-8')\n"
    "print('simple_agent.py written.')"
)

_SOL_CELL2 = r"""
from simple_agent import (
    safe_calculate, DEFAULT_TOOLS, build_tool_descriptions,
    safe_parse_json, parse_action, execute_tool, call_llm,
    build_agent_prompt, run_agent, SimpleAgent,
)

def _make_mock_llm(script):
    state = {'i': 0}
    def _fn(messages):
        i = state['i']
        state['i'] = min(i + 1, len(script) - 1)
        return script[i]
    return _fn

# 1. safe_calculate (no eval)
assert safe_calculate('2 * (3 + 4)') == 14
try:
    safe_calculate('__import__("os")'); raise AssertionError('should have raised')
except ValueError:
    pass
print("✅ safe_calculate")

# 2. tools + descriptions
assert DEFAULT_TOOLS['calculator']['fn']({'expression': '6*7'}) == '42'
assert 'calculator' in build_tool_descriptions(DEFAULT_TOOLS)
print("✅ DEFAULT_TOOLS + build_tool_descriptions")

# 3. parsing
assert safe_parse_json('prefix {"tool": "finish", "answer": "x"} suffix')['answer'] == 'x'
assert safe_parse_json('nope') is None
assert parse_action('plain answer')['type'] == 'finish'
assert parse_action('{"tool": "calculator", "args": {"expression": "1+1"}}')['type'] == 'tool'
print("✅ safe_parse_json + parse_action")

# 4. execute_tool
assert execute_tool({'tool': 'calculator', 'args': {'expression': '2+2'}}, DEFAULT_TOOLS) == '4'
assert 'unknown tool' in execute_tool({'tool': 'zzz', 'args': {}}, DEFAULT_TOOLS).lower()
assert 'error' in execute_tool({'tool': 'calculator', 'args': {}}, DEFAULT_TOOLS).lower()
print("✅ execute_tool")

# 5. call_llm injection
assert call_llm([{'role': 'user', 'content': 'hi'}], llm_fn=lambda m: 'MOCK') == 'MOCK'
print("✅ call_llm (llm_fn injection)")

# 6. run_agent: tool call then finish
script = ['{"tool": "calculator", "args": {"expression": "2+2"}}',
          '{"tool": "finish", "answer": "It is 4."}']
out = run_agent('what is 2+2', DEFAULT_TOOLS, llm_fn=_make_mock_llm(script))
assert out['answer'] == 'It is 4.' and out['stopped'] is False
assert len(out['steps']) == 1 and out['steps'][0]['result'] == '4'
print("✅ run_agent (loop: tool -> finish)")

# 7. max_iterations safeguard
never = _make_mock_llm(['{"tool": "calculator", "args": {"expression": "1+1"}}'])
loop = run_agent('x', DEFAULT_TOOLS, llm_fn=never, max_iterations=3)
assert loop['stopped'] is True and loop['iterations'] == 3
print("✅ run_agent (max_iterations stops runaway loop)")

# 8. SimpleAgent
agent = SimpleAgent(llm_fn=_make_mock_llm(script))
assert agent.run('2+2?')['answer'] == 'It is 4.'
agent.add_tool('shout', 'Uppercase.', lambda args: str(args['text']).upper(), {'text': 'string'})
assert 'shout' in agent.tools and 'shout' not in DEFAULT_TOOLS
assert len(agent.history()) == 1
agent.history().clear()
assert len(agent.history()) == 1   # history() returns a copy
agent.clear_history()
assert len(agent.history()) == 0
print("✅ SimpleAgent (run / add_tool / history / clear_history)")

print("\nSimple agent complete! Section 6 begins.")
"""

SOLUTION = nb([
    md(f"# Day {DAY} — Solution: A Minimal Agent from Scratch"),
    code(_SOL_CELL1),
    code(_SOL_CELL2),
])
save(OUT / "project" / "solution" / "solution.ipynb", SOLUTION)
(OUT / "project" / "solution" / "simple_agent.py").write_text(_SIMPLE_AGENT_SRC)

print(f"Day {DAY} notebooks written to {OUT}")
print("  lessons/    day_079_lesson_01.yaml – lesson_05.yaml")
print("  exercises/  exercise_01 – exercise_05")
print("  project/    project.ipynb")
print("  project/solution/  solution.ipynb + simple_agent.py")
