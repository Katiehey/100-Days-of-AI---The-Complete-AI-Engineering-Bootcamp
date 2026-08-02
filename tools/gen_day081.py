#!/usr/bin/env python3
"""gen_day081.py — generate Day 081: Tool-Using Agents."""
from pathlib import Path
import json

ROOT    = Path(__file__).parent.parent
DAY     = "081"
SECTION = "06_agents"
OUT     = ROOT / SECTION / f"day_{DAY}"

(OUT / "exercises").mkdir(parents=True, exist_ok=True)
(OUT / "lessons").mkdir(parents=True, exist_ok=True)
(OUT / "project" / "solution").mkdir(parents=True, exist_ok=True)

# ── deliverable fragments (composed into tool_agent.py AND reused as ──────────
# ── given-code / embedded solutions in the exercises, so they stay in sync) ────

_DOC = '''\
"""tool_agent.py — Day 081: Tool-Using Agents.

Days 79-80 gave an agent a couple of tools and let it call them. This day is
about tools *at scale*: a toolbox of many tools, each with a typed parameter
schema; argument validation before anything runs; a first-class ToolRegistry;
and tool *selection* - having the model route a request to the single best
tool and extract its arguments.

Pieces (new on Day 081; helpers reused from Days 79-80):
  safe_calculate / safe_parse_json / call_llm  - reused (Days 79-80)
  DEFAULT_TOOLS            - a toolbox: each tool has a typed parameter schema
  validate_args            - check args against a tool's schema before running
  ToolRegistry             - register / get / describe / validate / execute
  build_default_registry   - a ToolRegistry preloaded with DEFAULT_TOOLS
  build_selection_prompt   - ask the model to pick one tool + its args
  select_tool              - parse the model's choice (never raises)
  route_query              - select -> validate -> execute
  ToolAgent                - a multi-tool assistant over a registry

Setup:
    pip install ollama
    ollama pull llama3.2
"""
'''

_FRAG_HELPERS = '''\
import ast
import json
import operator

# ── helpers reused from Days 79-80 ───────────────────────────────────────────
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
    """Evaluate arithmetic without eval() (Day 79)."""
    return _eval_node(ast.parse(expression, mode="eval").body)


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

_FRAG_TOOLBOX = '''\

# ── typed parameter schemas + argument validation ────────────────────────────
def _is_number(s):
    try:
        float(s)
        return True
    except (TypeError, ValueError):
        return False


# each check answers: does this value satisfy the declared type?
_TYPE_CHECKS = {
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: (isinstance(v, int) and not isinstance(v, bool))
                         or (isinstance(v, str) and v.strip().lstrip("-").isdigit()),
    "number": lambda v: (isinstance(v, (int, float)) and not isinstance(v, bool))
                        or (isinstance(v, str) and _is_number(v)),
    "boolean": lambda v: isinstance(v, bool),
}


def validate_args(tool, args):
    """Validate args against a tool's parameter schema.

    Returns (ok: bool, error: str). Checks two things per declared parameter:
    required parameters must be present, and present values must match the
    declared type. An unknown declared type is treated as no constraint.
    """
    for pname, pspec in tool.get("parameters", {}).items():
        if pspec.get("required") and pname not in args:
            return False, "missing required parameter: " + pname
        if pname in args:
            check = _TYPE_CHECKS.get(pspec.get("type"))
            if check is not None and not check(args[pname]):
                return False, "parameter " + pname + " must be " + str(pspec.get("type"))
    return True, ""


# ── the toolbox: each tool declares name, description, typed schema, fn ───────
def _p(type_, required=True, description=""):
    """Shorthand for a parameter spec."""
    return {"type": type_, "required": required, "description": description}


DEFAULT_TOOLS = [
    {"name": "calculator",
     "description": "Evaluate an arithmetic expression, e.g. 2 * (3 + 4).",
     "parameters": {"expression": _p("string", description="the arithmetic")},
     "fn": lambda args: str(safe_calculate(args["expression"]))},
    {"name": "word_count",
     "description": "Count the words in a piece of text.",
     "parameters": {"text": _p("string", description="text to count")},
     "fn": lambda args: str(len(str(args["text"]).split()))},
    {"name": "uppercase",
     "description": "Convert text to UPPERCASE.",
     "parameters": {"text": _p("string", description="text to upcase")},
     "fn": lambda args: str(args["text"]).upper()},
    {"name": "reverse",
     "description": "Reverse a piece of text.",
     "parameters": {"text": _p("string", description="text to reverse")},
     "fn": lambda args: str(args["text"])[::-1]},
    {"name": "repeat",
     "description": "Repeat a piece of text N times.",
     "parameters": {"text": _p("string", description="text to repeat"),
                    "times": _p("integer", description="how many times")},
     "fn": lambda args: str(args["text"]) * int(args["times"])},
]
'''

_FRAG_REGISTRY = '''\

# ── the ToolRegistry ──────────────────────────────────────────────────────────
class ToolRegistry:
    """A first-class collection of tools with validation and execution.

    A registry owns its tools, renders them for a prompt, validates arguments
    against each tool's schema, and executes safely (never raises).
    """

    def __init__(self, tools=None):
        self._tools = {}
        for tool in (tools or []):
            self.register(tool)

    def register(self, tool):
        """Add a fully-formed tool dict; returns self."""
        self._tools[tool["name"]] = tool
        return self

    def add(self, name, description, fn, parameters=None):
        """Add a tool from parts; returns self."""
        return self.register({"name": name, "description": description,
                              "parameters": parameters or {}, "fn": fn})

    def get(self, name):
        return self._tools.get(name)

    def names(self):
        return list(self._tools)

    def __contains__(self, name):
        return name in self._tools

    def __len__(self):
        return len(self._tools)

    def describe(self):
        """Render the toolbox as prompt text: one line per tool."""
        lines = []
        for name, tool in self._tools.items():
            params = ", ".join(tool.get("parameters", {}))
            lines.append("- " + name + "(" + params + "): " + tool["description"])
        return "\\n".join(lines)

    def validate(self, name, args):
        """Validate args for a named tool. Returns (ok, error)."""
        tool = self.get(name)
        if tool is None:
            return False, "unknown tool: " + repr(name)
        return validate_args(tool, args)

    def execute(self, name, args):
        """Validate then run a tool. Returns a result string; never raises."""
        tool = self.get(name)
        if tool is None:
            return "Error: unknown tool " + repr(name)
        ok, err = validate_args(tool, args)
        if not ok:
            return "Error: " + err
        try:
            return str(tool["fn"](args))
        except Exception as exc:
            return "Error running " + name + ": " + str(exc)


def build_default_registry():
    """A ToolRegistry preloaded with the DEFAULT_TOOLS toolbox."""
    return ToolRegistry(DEFAULT_TOOLS)
'''

_FRAG_SELECT = '''\

# ── tool selection (routing) ──────────────────────────────────────────────────
def build_selection_prompt(query, registry):
    """Ask the model to choose ONE tool for the request and extract its args."""
    system = "\\n".join([
        "You are a router. Choose the single best tool for the user request "
        "and extract its arguments.",
        "",
        "Available tools:",
        registry.describe(),
        "",
        "Reply with ONLY a JSON object:",
        '{"tool": "<tool name>", "args": {...}}',
        'If no tool fits, reply {"tool": "none", "args": {}}.',
    ])
    return [{"role": "system", "content": system},
            {"role": "user", "content": "Request: " + str(query)}]


def select_tool(query, registry, llm_fn=None):
    """Route a request to one tool. Returns {"tool": name, "args": dict}.

    NEVER raises: unparseable output or an unknown tool name both fall back to
    {"tool": "none", "args": {}}.
    """
    response = call_llm(build_selection_prompt(query, registry), llm_fn=llm_fn)
    data = safe_parse_json(response) or {}
    name = data.get("tool", "none")
    args = data.get("args", {})
    if name not in registry:
        name = "none"
    return {"tool": name, "args": args if isinstance(args, dict) else {}}
'''

_FRAG_ROUTE = '''\

# ── the router: select -> validate -> execute ────────────────────────────────
def route_query(query, registry, llm_fn=None):
    """Select a tool for the query and run it.

    Returns {"tool", "args", "result"}. If no tool fits, tool is "none" and no
    tool runs. Validation and execution errors come back as the result string.
    """
    choice = select_tool(query, registry, llm_fn=llm_fn)
    if choice["tool"] == "none":
        return {"tool": "none", "args": {}, "result": "No suitable tool found."}
    result = registry.execute(choice["tool"], choice["args"])
    return {"tool": choice["tool"], "args": choice["args"], "result": result}
'''

_FRAG_AGENT = '''\

# ── the multi-tool assistant ──────────────────────────────────────────────────
class ToolAgent:
    """A multi-tool assistant: routes each request to the best tool.

    Binds a ToolRegistry and an optional llm_fn, answers requests by routing,
    and keeps a history of every ask.

    Example::

        agent = ToolAgent(llm_fn=my_llm_fn)
        print(agent.ask("shout the word hello")["result"])
    """

    def __init__(self, registry=None, llm_fn=None):
        self.registry = registry if registry is not None else build_default_registry()
        self._llm_fn = llm_fn
        self._history = []

    def add_tool(self, name, description, fn, parameters=None):
        """Register a new tool on this agent's registry; returns self."""
        self.registry.add(name, description, fn, parameters)
        return self

    def tools(self):
        """List the names of available tools."""
        return self.registry.names()

    def ask(self, query):
        """Route one request to the best tool and run it. Returns the result dict."""
        result = route_query(query, self.registry, llm_fn=self._llm_fn)
        self._history.append({"query": query, "result": result})
        return result

    def history(self):
        """Return a copy of the ask history."""
        return list(self._history)

    def clear_history(self):
        """Clear the ask history in place."""
        self._history.clear()
'''

_TOOL_AGENT_SRC = (_DOC + _FRAG_HELPERS + _FRAG_TOOLBOX + _FRAG_REGISTRY
                   + _FRAG_SELECT + _FRAG_ROUTE + _FRAG_AGENT)


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

def _mock_pick(tool, args):
    \"\"\"Return an llm_fn that always routes to `tool` with `args` (as JSON).\"\"\"
    payload = json.dumps({'tool': tool, 'args': args})
    return lambda messages: payload
"""

# ── EX1: DEFAULT_TOOLS + validate_args ───────────────────────────────────────
_EX1_GIVEN = _MOCK_HELPER + _FRAG_HELPERS

_EX1_STUB = """\
def validate_args(tool, args):
    \"\"\"Validate args against tool['parameters']. Returns (ok: bool, error: str).\"\"\"
    raise NotImplementedError

DEFAULT_TOOLS = []  # calculator, word_count, uppercase, reverse, repeat
"""

_EX1_CHECKS = r"""
score, total = 0, 5
try:
    names = {t['name'] for t in DEFAULT_TOOLS}
    assert {'calculator', 'word_count', 'uppercase', 'reverse', 'repeat'} <= names
    score += 1; print("✅ the toolbox has the expected tools")

    repeat = next(t for t in DEFAULT_TOOLS if t['name'] == 'repeat')
    assert repeat['fn']({'text': 'ab', 'times': 3}) == 'ababab'
    score += 1; print("✅ tool functions run")

    assert repeat['parameters']['times']['required'] is True
    assert repeat['parameters']['times']['type'] == 'integer'
    score += 1; print("✅ parameters carry a schema (type + required)")

    ok, err = validate_args(repeat, {'text': 'hi', 'times': 2})
    assert ok and err == ''
    score += 1; print("✅ validate_args accepts valid args")

    miss, _ = validate_args(repeat, {'text': 'hi'})
    wrong, _ = validate_args(repeat, {'text': 'hi', 'times': 'lots'})
    assert miss is False and wrong is False
    score += 1; print("✅ validate_args rejects missing and wrong-type args")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX1 = nb([
    md("# Day 081 — Exercise 1: The Toolbox and Argument Validation\n\n"
       "**What you'll build:** a toolbox where every tool declares a *typed "
       "parameter schema*, plus `validate_args` to check arguments before a tool "
       "runs.\n\n"
       "**Why it matters:** with many tools, the model *will* sometimes pick the "
       "right tool but pass the wrong arguments — a missing field, or a word where a "
       "number belongs. Validating against the schema catches that before the tool "
       "throws, and gives the agent a clear error to recover from."),
    code(_EX1_GIVEN),
    md("## Task\n\n"
       "1. `DEFAULT_TOOLS` — a list of tool dicts, each `{'name', 'description', "
       "'parameters', 'fn'}`. Every parameter is `{'type', 'required', 'description'}`. "
       "Include `calculator`, `word_count`, `uppercase`, `reverse`, and `repeat` "
       "(`repeat` takes `text: string` and `times: integer`).\n"
       "2. `validate_args(tool, args) -> (ok, error)` — for each declared parameter: "
       "if it's `required` and missing → fail; if present, check its value against the "
       "declared `type` (`string`, `integer`, `number`, `boolean`). Return "
       "`(True, '')` when everything checks out."),
    md("## Your Implementation"),
    code(_EX1_STUB),
    code(_FRAG_TOOLBOX),
    md("## Automated checks"),
    code(_EX1_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _FRAG_TOOLBOX + "```\n\n"
       "**Why validate before running?** A tool that throws on bad input gives a "
       "cryptic traceback. Validating against the schema turns that into a precise, "
       "recoverable message like `parameter times must be integer` — which the agent "
       "can read and correct.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_01.ipynb", EX1)

# ── EX2: ToolRegistry ────────────────────────────────────────────────────────
_EX2_GIVEN = _MOCK_HELPER + _FRAG_HELPERS + _FRAG_TOOLBOX

_EX2_STUB = """\
class ToolRegistry:
    \"\"\"A collection of tools with validation + safe execution.\"\"\"

    def __init__(self, tools=None):
        raise NotImplementedError

    def register(self, tool):
        raise NotImplementedError

    def add(self, name, description, fn, parameters=None):
        raise NotImplementedError

    def get(self, name):
        raise NotImplementedError

    def names(self):
        raise NotImplementedError

    def __contains__(self, name):
        raise NotImplementedError

    def __len__(self):
        raise NotImplementedError

    def describe(self):
        raise NotImplementedError

    def validate(self, name, args):
        raise NotImplementedError

    def execute(self, name, args):
        raise NotImplementedError

def build_default_registry():
    raise NotImplementedError
"""

_EX2_CHECKS = r"""
score, total = 0, 6
try:
    reg = build_default_registry()
    assert len(reg) >= 5
    score += 1; print("✅ build_default_registry populates the toolbox")

    assert 'calculator' in reg and reg.get('calculator')['name'] == 'calculator'
    score += 1; print("✅ get() and `in` (contains) work")

    assert set(reg.names()) >= {'calculator', 'repeat'}
    score += 1; print("✅ names() lists the tools")

    desc = reg.describe()
    assert 'calculator' in desc and 'repeat(' in desc
    score += 1; print("✅ describe() renders the toolbox for a prompt")

    assert reg.execute('uppercase', {'text': 'hi'}) == 'HI'
    score += 1; print("✅ execute() runs a tool with valid args")

    out = reg.execute('repeat', {'text': 'hi'})   # missing 'times'
    assert out.lower().startswith('error')
    score += 1; print("✅ execute() blocks invalid args (validation gate)")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX2 = nb([
    md("# Day 081 — Exercise 2: The ToolRegistry\n\n"
       "**What you'll build:** `ToolRegistry` — a first-class object that owns the "
       "tools, renders them for a prompt, and *validates then executes* safely.\n\n"
       "**Why it matters:** in Days 79-80 the registry was a bare dict and execution "
       "just called the function. As the toolbox grows you want one place that "
       "guarantees every call is validated first — so a bad argument can never reach "
       "the tool body."),
    code(_EX2_GIVEN),
    md("## Task\n\n"
       "`ToolRegistry(tools=None)` — store tools by name. Implement:\n\n"
       "- `register(tool)` / `add(name, description, fn, parameters=None)` — both "
       "return `self`\n"
       "- `get(name)`, `names()`, `__contains__`, `__len__`\n"
       "- `describe()` — one `- name(params): description` line per tool\n"
       "- `validate(name, args)` — `(ok, error)`, unknown tool → `(False, ...)`\n"
       "- `execute(name, args)` — unknown tool or invalid args → `Error: ...` "
       "string; else run `tool['fn'](args)` in `try/except`. **Never raises.**\n\n"
       "Then `build_default_registry()` returns `ToolRegistry(DEFAULT_TOOLS)`."),
    md("## Your Implementation"),
    code(_EX2_STUB),
    code(_FRAG_REGISTRY),
    md("## Automated checks"),
    code(_EX2_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _FRAG_REGISTRY + "```\n\n"
       "**Why route execution through `execute()`?** It's the one choke point that "
       "always validates first. No caller can skip the check and hand raw model "
       "output straight to a tool function.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_02.ipynb", EX2)

# ── EX3: build_selection_prompt + select_tool ────────────────────────────────
_EX3_GIVEN = _MOCK_HELPER + _FRAG_HELPERS + _FRAG_TOOLBOX + _FRAG_REGISTRY

_EX3_STUB = """\
def build_selection_prompt(query, registry):
    \"\"\"Ask the model to choose ONE tool for the request + extract its args.\"\"\"
    raise NotImplementedError

def select_tool(query, registry, llm_fn=None):
    \"\"\"Route a request to one tool. Returns {'tool': name, 'args': dict}. Never raises.\"\"\"
    raise NotImplementedError
"""

_EX3_CHECKS = r"""
score, total = 0, 5
try:
    reg = build_default_registry()
    msgs = build_selection_prompt('shout hello', reg)
    assert msgs[0]['role'] == 'system' and 'calculator' in msgs[0]['content']
    score += 1; print("✅ selection prompt lists the tools")

    pick = select_tool('x', reg, llm_fn=_mock_pick('uppercase', {'text': 'hi'}))
    assert pick['tool'] == 'uppercase' and pick['args']['text'] == 'hi'
    score += 1; print("✅ select_tool parses the chosen tool + args")

    bad = select_tool('x', reg, llm_fn=_mock_pick('teleport', {}))
    assert bad['tool'] == 'none'
    score += 1; print("✅ an unknown tool choice falls back to 'none'")

    n = select_tool('x', reg, llm_fn=_mock_pick('none', {}))
    assert n['tool'] == 'none'
    score += 1; print("✅ 'none' is respected when no tool fits")

    g = select_tool('x', reg, llm_fn=lambda m: 'I have no idea, sorry')
    assert g['tool'] == 'none'
    score += 1; print("✅ garbage output falls back to 'none' (never raises)")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX3 = nb([
    md("# Day 081 — Exercise 3: Tool Selection (Routing)\n\n"
       "**What you'll build:** `build_selection_prompt` and `select_tool` — the "
       "model reads the request and the toolbox, then picks the single best tool and "
       "extracts its arguments.\n\n"
       "**Why it matters:** *selection* is the new skill of the day. With one tool "
       "there's nothing to choose; with a dozen, routing to the right one is the "
       "whole game. And the router must degrade to `none` — never crash — on messy "
       "output."),
    code(_EX3_GIVEN),
    md("## Task\n\n"
       "1. `build_selection_prompt(query, registry)` — a `system` message that lists "
       "the tools (`registry.describe()`) and asks for `{\"tool\": \"<name>\", "
       "\"args\": {...}}`, or `{\"tool\": \"none\", \"args\": {}}` if nothing fits; a "
       "`user` message `Request: <query>`.\n"
       "2. `select_tool(query, registry, llm_fn=None) -> dict` — call the model, "
       "`safe_parse_json` the reply, read `tool` and `args`. If the tool name isn't "
       "in the registry, coerce to `'none'`. Ensure `args` is a dict. **Never "
       "raises.**"),
    md("## Your Implementation"),
    code(_EX3_STUB),
    code(_FRAG_SELECT),
    md("## Automated checks"),
    code(_EX3_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _FRAG_SELECT + "```\n\n"
       "**Why coerce unknown names to `none`?** The model can hallucinate a tool "
       "that doesn't exist. Checking `name not in registry` and falling back to "
       "`none` means a made-up tool never reaches execution.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_03.ipynb", EX3)

# ── EX4: route_query ─────────────────────────────────────────────────────────
_EX4_GIVEN = (_MOCK_HELPER + _FRAG_HELPERS + _FRAG_TOOLBOX + _FRAG_REGISTRY
              + _FRAG_SELECT)

_EX4_STUB = """\
def route_query(query, registry, llm_fn=None):
    \"\"\"Select a tool for the query and run it. Returns {'tool','args','result'}.\"\"\"
    raise NotImplementedError
"""

_EX4_CHECKS = r"""
score, total = 0, 5
try:
    reg = build_default_registry()

    r = route_query('shout', reg, llm_fn=_mock_pick('uppercase', {'text': 'hi'}))
    assert r['tool'] == 'uppercase' and r['result'] == 'HI'
    score += 1; print("✅ route_query selects then executes")

    r2 = route_query('x', reg, llm_fn=_mock_pick('repeat', {'text': 'ab', 'times': 3}))
    assert r2['result'] == 'ababab'
    score += 1; print("✅ route_query passes args to the tool")

    r3 = route_query('x', reg, llm_fn=_mock_pick('none', {}))
    assert r3['tool'] == 'none' and 'No suitable tool' in r3['result']
    score += 1; print("✅ route_query handles 'none' (no tool fits)")

    r4 = route_query('x', reg, llm_fn=_mock_pick('repeat', {'text': 'ab'}))  # missing times
    assert r4['result'].lower().startswith('error')
    score += 1; print("✅ route_query surfaces validation errors")

    r5 = route_query('x', reg, llm_fn=lambda m: 'nonsense')
    assert r5['tool'] == 'none'
    score += 1; print("✅ route_query never raises on bad model output")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX4 = nb([
    md("# Day 081 — Exercise 4: The Router\n\n"
       "**What you'll build:** `route_query` — the one call that selects a tool, and "
       "runs it through the registry's validate-then-execute gate.\n\n"
       "**Why it matters:** this ties the day together: selection (Ex3) + validation "
       "and execution (Ex2). One request in, one `{tool, args, result}` out — with "
       "every failure mode (no tool, bad args, garbage output) handled as data, not "
       "a crash."),
    code(_EX4_GIVEN),
    md("## Task\n\n"
       "`route_query(query, registry, llm_fn=None) -> dict`\n\n"
       "- `choice = select_tool(query, registry, llm_fn=llm_fn)`\n"
       "- if `choice['tool'] == 'none'` → return "
       "`{'tool':'none','args':{},'result':'No suitable tool found.'}`\n"
       "- else `result = registry.execute(choice['tool'], choice['args'])` and return "
       "`{'tool', 'args', 'result'}`"),
    md("## Your Implementation"),
    code(_EX4_STUB),
    code(_FRAG_ROUTE),
    md("## Automated checks"),
    code(_EX4_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _FRAG_ROUTE + "```\n\n"
       "**Why does `execute` re-validate when `route_query` already selected a "
       "tool?** Selection only chooses *which* tool; the arguments still come from "
       "the model and can be wrong. `execute` is the gate that guarantees they're "
       "checked before the tool runs.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_04.ipynb", EX4)

# ── EX5: ToolAgent ───────────────────────────────────────────────────────────
_EX5_GIVEN = (_MOCK_HELPER + _FRAG_HELPERS + _FRAG_TOOLBOX + _FRAG_REGISTRY
              + _FRAG_SELECT + _FRAG_ROUTE)

_EX5_STUB = """\
class ToolAgent:
    \"\"\"A multi-tool assistant that routes each request to the best tool.\"\"\"

    def __init__(self, registry=None, llm_fn=None):
        raise NotImplementedError

    def add_tool(self, name, description, fn, parameters=None):
        raise NotImplementedError

    def tools(self):
        raise NotImplementedError

    def ask(self, query):
        raise NotImplementedError

    def history(self):
        raise NotImplementedError

    def clear_history(self):
        raise NotImplementedError
"""

_EX5_CHECKS = r"""
score, total = 0, 6
try:
    agent = ToolAgent(llm_fn=_mock_pick('uppercase', {'text': 'hi'}))
    out = agent.ask('shout hi')
    assert out['result'] == 'HI'
    score += 1; print("✅ ToolAgent.ask routes and runs")

    assert 'calculator' in agent.tools() and 'repeat' in agent.tools()
    score += 1; print("✅ ToolAgent uses the default registry")

    agent.add_tool('double', 'Double a number.',
                   lambda a: str(int(a['n']) * 2),
                   {'n': {'type': 'integer', 'required': True}})
    assert 'double' in agent.tools()
    score += 1; print("✅ add_tool extends the registry")

    assert len(agent.history()) == 1
    score += 1; print("✅ history records each ask")

    agent.history().clear()
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
    md("# Day 081 — Exercise 5: ToolAgent\n\n"
       "**What you'll build:** `ToolAgent` — a multi-tool assistant that routes each "
       "request to the best tool and remembers the conversation.\n\n"
       "**Why it matters:** where Day 80's agent worked one hard task through a "
       "reasoning loop, this assistant fields varied one-shot requests and dispatches "
       "each to the right tool — the everyday shape of a tool-using assistant."),
    code(_EX5_GIVEN),
    md("## Task\n\n"
       "`ToolAgent(registry=None, llm_fn=None)`\n\n"
       "1. `__init__` — use the given `registry`, or `build_default_registry()`; store "
       "`_llm_fn` and `_history = []`.\n"
       "2. `add_tool(name, description, fn, parameters=None)` — `self.registry.add(...)`; "
       "return `self`.\n"
       "3. `tools()` — `self.registry.names()`.\n"
       "4. `ask(query)` — `route_query(query, self.registry, llm_fn=self._llm_fn)`; "
       "append `{'query','result'}` to `_history`; return the result.\n"
       "5. `history()` — `list(self._history)`; `clear_history()` — `.clear()`."),
    md("## Your Implementation"),
    code(_EX5_STUB),
    code(_FRAG_AGENT),
    md("## Automated checks"),
    code(_EX5_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _FRAG_AGENT + "```\n\n"
       "**Why does each ToolAgent build its own registry?** `build_default_registry()` "
       "returns a fresh `ToolRegistry` each call, so one agent's `add_tool` never "
       "leaks into another — the same isolation principle as copying `DEFAULT_TOOLS` "
       "on Days 79-80.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_05.ipynb", EX5)

# ── YAML lessons ──────────────────────────────────────────────────────────────
_LESSON_01 = """\
day: "081"
lesson: 1
title: "Tools at Scale"
slides:
  - type: title
    heading: "Tool-Using Agents"
    subheading: "A toolbox, typed schemas, and validation"
    narration: >
      Days 79 and 80 gave an agent a couple of tools and let it call them. Today
      is about tools at scale: a real toolbox of many tools, each declaring a
      typed parameter schema, with validation that runs before any tool touches
      the model's arguments. The lesson starts with the two foundations - the
      schema and the validator - because everything else this day depends on
      them.

  - type: concept
    label: "Why schemas"
    heading: "Every Tool Declares a Schema"
    body: >
      A tool is more than a name and a function.
    bullets:
      - "name + description: so the model can choose it"
      - "parameters: each with a type and whether it is required"
      - "fn: the function that runs"
      - "The schema is the contract the model must satisfy"
      - "repeat(text: string, times: integer) - times is required and typed"
    narration: >
      When an agent has one tool, you can be sloppy about arguments. When it has a
      dozen, the model will sometimes pick the right tool but pass the wrong
      arguments - a missing field, or a word where a number belongs. Declaring a
      schema for every parameter - its type, and whether it is required - turns
      those mistakes into something you can detect before the tool runs, instead
      of a confusing crash inside the tool body.

  - type: code
    label: "validate_args"
    heading: "Validating Against the Schema"
    code: |
      _TYPE_CHECKS = {
          "string": lambda v: isinstance(v, str),
          "integer": lambda v: (isinstance(v, int) and not isinstance(v, bool))
                               or (isinstance(v, str) and v.strip().lstrip("-").isdigit()),
          "number": lambda v: isinstance(v, (int, float)) or _is_number(v),
      }

      def validate_args(tool, args):
          for pname, pspec in tool.get("parameters", {}).items():
              if pspec.get("required") and pname not in args:
                  return False, "missing required parameter: " + pname
              if pname in args:
                  check = _TYPE_CHECKS.get(pspec.get("type"))
                  if check is not None and not check(args[pname]):
                      return False, "parameter " + pname + " must be " + str(pspec.get("type"))
          return True, ""
    narration: >
      validate_args walks the declared parameters and checks two things: required
      parameters must be present, and present values must match their declared
      type. It returns a pair - ok, and an error message - rather than raising, so
      the caller decides what to do. Notice it is lenient about numbers as
      strings, because models often send a number as text. The point is not strict
      typing; it is catching the mistakes that would otherwise blow up a tool.

  - type: concept
    label: "Fail early, clearly"
    heading: "A Clear Error Beats a Traceback"
    body: >
      Validation converts a crash into a recoverable message.
    bullets:
      - "No validation: repeat with no 'times' -> KeyError deep in the tool"
      - "With validation: 'missing required parameter: times'"
      - "The agent can read that and try again"
      - "Errors are data the agent reasons about - the Day 79-80 principle"
      - "Validation is the gate every tool call passes through"
    narration: >
      This continues the fail-safe theme from the last two days. A tool that throws
      a KeyError from three functions deep tells the agent nothing useful. A message
      that says missing required parameter times tells it exactly what went wrong
      and what to fix. Turning failures into clear, structured data - rather than
      exceptions - is what lets an agent recover instead of falling over.

  - type: exercise
    heading: "Exercise 1: The Toolbox and Argument Validation"
    prompt: >
      Build DEFAULT_TOOLS - a list of tools (calculator, word_count, uppercase,
      reverse, repeat), each with a typed parameter schema. Implement
      validate_args(tool, args) returning (ok, error): required params must be
      present, present values must match their declared type.
    hint: >
      Each parameter is {'type', 'required', 'description'}. validate_args loops
      the parameters; check required-and-missing first, then type via a
      _TYPE_CHECKS lookup. Return (True, '') when all pass.
    narration: >
      This builds the toolbox and the validator that guards every call the rest of
      the day makes.

  - type: summary
    heading: "Lesson 1 Summary"
    bullets:
      - "At scale, every tool declares a typed parameter schema"
      - "parameters: name -> {type, required, description}"
      - "validate_args returns (ok, error), never raises"
      - "Required-and-missing and wrong-type are both caught before running"
      - "A clear error is recoverable; a deep traceback is not"
    narration: >
      Lesson 2 wraps the toolbox and the validator in a first-class ToolRegistry.
"""

_LESSON_02 = """\
day: "081"
lesson: 2
title: "The ToolRegistry"
slides:
  - type: title
    heading: "The ToolRegistry"
    subheading: "One object that owns, describes, validates, and runs tools"
    narration: >
      In Days 79 and 80 the registry was a bare dict and execution just called the
      function. As the toolbox grows you want a proper object: one place that owns
      the tools, renders them for a prompt, and - crucially - always validates
      before it executes. That object is the ToolRegistry.

  - type: concept
    label: "Why an object"
    heading: "From Bare Dict to First-Class Object"
    body: >
      A registry is more than storage - it enforces the rules.
    bullets:
      - "register / add: put tools in"
      - "get / names / contains / len: inspect what's there"
      - "describe: render the toolbox as prompt text"
      - "validate: check args against a tool's schema"
      - "execute: validate THEN run - the single choke point"
    narration: >
      The registry gives you one object with a clear job. You can add tools, look
      them up, count them, and ask whether a name exists. describe renders the
      whole toolbox into the text the model reads when choosing. But the most
      important method is execute, because it is the single choke point through
      which every tool call passes - and it always validates first.

  - type: code
    label: "execute"
    heading: "execute - Validate, Then Run"
    code: |
      def execute(self, name, args):
          tool = self.get(name)
          if tool is None:
              return "Error: unknown tool " + repr(name)
          ok, err = validate_args(tool, args)
          if not ok:
              return "Error: " + err
          try:
              return str(tool["fn"](args))
          except Exception as exc:
              return "Error running " + name + ": " + str(exc)
    narration: >
      execute is three guards and a call. Unknown tool - return an error string.
      Invalid arguments - return the validation error. Otherwise run the function,
      and even then wrap it in try-except so an unexpected failure still comes back
      as text. Because every caller goes through execute, no one can skip the
      validation and hand raw model output straight to a tool. That single
      guarantee is why the registry is an object and not a loose dict.

  - type: code
    label: "describe"
    heading: "describe - Render for the Prompt"
    code: |
      def describe(self):
          lines = []
          for name, tool in self._tools.items():
              params = ", ".join(tool.get("parameters", {}))
              lines.append("- " + name + "(" + params + "): " + tool["description"])
          return "\\n".join(lines)
    narration: >
      describe turns the toolbox into the menu the model sees. One line per tool -
      the name, its parameter names in parentheses, and the description. This is the
      same idea as build_tool_descriptions from Day 79, now a method on the object
      that owns the tools. When you add a tool to the registry, it automatically
      appears in the next prompt - no separate list to keep in sync.

  - type: exercise
    heading: "Exercise 2: The ToolRegistry"
    prompt: >
      Implement ToolRegistry: register/add (return self), get, names, __contains__,
      __len__, describe, validate, and execute (unknown tool or invalid args ->
      error string; else run fn in try/except). Then build_default_registry()
      returns ToolRegistry(DEFAULT_TOOLS).
    hint: >
      Store tools in a dict keyed by name. execute: get the tool, validate_args,
      then run in try/except - all failures return an 'Error: ...' string, never
      raise.
    narration: >
      This registry becomes the backbone every later piece of the day runs on.

  - type: summary
    heading: "Lesson 2 Summary"
    bullets:
      - "ToolRegistry owns the tools and enforces the rules"
      - "register/add, get, names, contains, len, describe"
      - "execute is the choke point: validate THEN run, never raises"
      - "describe renders the toolbox straight into the prompt"
      - "build_default_registry() = ToolRegistry(DEFAULT_TOOLS)"
    narration: >
      Lesson 3 uses the registry's description to let the model select a tool -
      routing.
"""

_LESSON_03 = """\
day: "081"
lesson: 3
title: "Tool Selection"
slides:
  - type: title
    heading: "Tool Selection"
    subheading: "The model routes a request to the right tool"
    narration: >
      With one tool there is nothing to choose. With a dozen, picking the right one
      is the whole game - and that is tool selection, or routing. The model reads
      the request and the toolbox, and returns the single best tool along with the
      arguments to call it. This lesson builds the selection prompt and the parser
      that turns the model's choice into a structured decision.

  - type: concept
    label: "What routing is"
    heading: "Routing = Choose One Tool + Its Args"
    body: >
      Selection is a single, focused decision.
    bullets:
      - "Input: the request + the toolbox description"
      - "Output: {tool, args} - which tool, called how"
      - "A special 'none' choice for when nothing fits"
      - "One shot: pick and extract in a single model call"
      - "Different from Day 80's loop - here, one decision per request"
    narration: >
      Routing is a single decision: given the request and the list of tools, which
      one, and with what arguments. The model returns a small JSON object naming the
      tool and its args. Crucially there is a none option, because sometimes no tool
      fits and the honest answer is to run nothing. This is a different shape from
      the Day 80 reasoning loop - there the agent worked one task over many steps;
      here it makes one routing decision per request.

  - type: code
    label: "select_tool"
    heading: "select_tool - Parse the Choice, Safely"
    code: |
      def select_tool(query, registry, llm_fn=None):
          response = call_llm(build_selection_prompt(query, registry), llm_fn=llm_fn)
          data = safe_parse_json(response) or {}
          name = data.get("tool", "none")
          args = data.get("args", {})
          if name not in registry:
              name = "none"
          return {"tool": name, "args": args if isinstance(args, dict) else {}}
    narration: >
      select_tool builds the prompt, calls the model, and parses the reply with the
      tolerant safe_parse_json from Day 79. Two guards make it robust: if the model
      names a tool that is not in the registry - a hallucinated tool - coerce the
      choice to none; and if args is not a dict, replace it with an empty one. Like
      every parser this section, it never raises. Garbage in still gives a valid
      choice out - just none.

  - type: concept
    label: "Guard the choice"
    heading: "The Model Can Choose Wrong"
    body: >
      Never trust the selected name blindly.
    bullets:
      - "Models hallucinate tool names that don't exist"
      - "name not in registry -> coerce to 'none'"
      - "Unparseable reply -> {} -> 'none'"
      - "Selection chooses the tool; it does NOT validate the args yet"
      - "Argument validation happens at execute time (Lesson 2)"
    narration: >
      A subtle but important point: selection decides which tool, not whether the
      arguments are any good. The model can hallucinate a tool that does not exist,
      so you check the name against the registry and fall back to none. But even a
      valid tool name can come with bad arguments - and those are caught later, at
      execute time, by the validator from Lesson 1. Selection and validation are two
      separate guards, and the next lesson chains them.

  - type: exercise
    heading: "Exercise 3: Tool Selection"
    prompt: >
      Implement build_selection_prompt(query, registry) - system lists the tools
      and asks for {"tool","args"} or {"tool":"none"} - and select_tool(query,
      registry, llm_fn=None) which parses the reply, coerces unknown tool names to
      'none', and never raises.
    hint: >
      build_selection_prompt uses registry.describe() for the tool list. select_tool:
      safe_parse_json(response) or {}; if name not in registry: name='none';
      guard args is a dict.
    narration: >
      This is the routing brain of the assistant - one call that turns a request
      into a tool choice.

  - type: summary
    heading: "Lesson 3 Summary"
    bullets:
      - "Selection = route a request to one tool + its args"
      - "build_selection_prompt lists the tools and asks for {tool, args}"
      - "select_tool parses the choice and NEVER raises"
      - "Unknown/hallucinated tool name -> coerced to 'none'"
      - "Selection picks the tool; validation of args comes at execute time"
    narration: >
      Lesson 4 chains selection with validation and execution into one router:
      route_query.
"""

_LESSON_04 = """\
day: "081"
lesson: 4
title: "The Router"
slides:
  - type: title
    heading: "route_query"
    subheading: "Select, validate, execute - in one call"
    narration: >
      Now the pieces connect. route_query takes a request, selects a tool, and runs
      it through the registry's validate-then-execute gate. One request goes in; a
      structured tool, args, and result come out - with every failure mode handled
      as data rather than a crash.

  - type: code
    label: "route_query"
    heading: "The Whole Router"
    code: |
      def route_query(query, registry, llm_fn=None):
          choice = select_tool(query, registry, llm_fn=llm_fn)
          if choice["tool"] == "none":
              return {"tool": "none", "args": {}, "result": "No suitable tool found."}
          result = registry.execute(choice["tool"], choice["args"])
          return {"tool": choice["tool"], "args": choice["args"], "result": result}
    narration: >
      route_query is short because the hard work lives in the pieces it calls.
      select_tool decides which tool and with what arguments. If the answer is none,
      return a clear result and run nothing. Otherwise, registry.execute validates
      the arguments and runs the tool, returning the result or a precise error
      string. The return dict always has the same three keys - tool, args, result -
      so the caller handles every outcome the same way.

  - type: concept
    label: "Two guards, in order"
    heading: "Selection Then Validation"
    body: >
      Two independent guards protect the tool call.
    bullets:
      - "Guard 1 (select): is this a real tool, or none?"
      - "Guard 2 (execute): are the arguments valid for it?"
      - "Both must pass before the tool function runs"
      - "Either failing yields a result string, never an exception"
      - "This is defence in depth for tool calls"
    narration: >
      Notice the two guards in sequence. Selection asks: is this a real tool, and
      does anything fit at all. Execution asks: are the arguments valid for the tool
      that was chosen. Both have to pass before the tool function ever runs, and if
      either fails the caller gets a readable result string rather than an
      exception. Two small, independent checks give you defence in depth - the model
      has to get both the tool and the arguments right to make anything happen.

  - type: exercise
    heading: "Exercise 4: The Router"
    prompt: >
      Implement route_query(query, registry, llm_fn=None): select_tool first; if
      the tool is 'none', return a no-tool result; otherwise registry.execute the
      chosen tool with its args and return {tool, args, result}.
    hint: >
      choice = select_tool(...); if choice['tool']=='none' return the no-tool dict;
      else result = registry.execute(choice['tool'], choice['args']); return the
      three-key dict.
    narration: >
      This is the single entry point the assistant will call for every request.

  - type: summary
    heading: "Lesson 4 Summary"
    bullets:
      - "route_query = select_tool -> registry.execute"
      - "'none' -> run nothing, return a clear result"
      - "Always returns {tool, args, result} - one shape for every outcome"
      - "Two guards in order: valid tool, then valid args"
      - "Every failure is a result string, never an exception"
    narration: >
      Lesson 5 wraps the router in a ToolAgent - the multi-tool assistant.
"""

_LESSON_05 = """\
day: "081"
lesson: 5
title: "ToolAgent - The Multi-Tool Assistant"
slides:
  - type: title
    heading: "ToolAgent"
    subheading: "Route every request to the right tool"
    narration: >
      The last piece is the assistant. ToolAgent binds a registry and a model,
      answers each request by routing it to the best tool, and keeps a history.
      Where Day 80's agent worked a single hard task through a reasoning loop, this
      assistant fields varied one-shot requests and dispatches each one - the
      everyday shape of a tool-using assistant.

  - type: code
    label: "ToolAgent"
    heading: "ToolAgent - Bind, Route, Remember"
    code: |
      class ToolAgent:
          def __init__(self, registry=None, llm_fn=None):
              self.registry = registry if registry is not None else build_default_registry()
              self._llm_fn = llm_fn
              self._history = []

          def add_tool(self, name, description, fn, parameters=None):
              self.registry.add(name, description, fn, parameters)
              return self

          def tools(self):
              return self.registry.names()

          def ask(self, query):
              result = route_query(query, self.registry, llm_fn=self._llm_fn)
              self._history.append({"query": query, "result": result})
              return result

          def history(self):
              return list(self._history)

          def clear_history(self):
              self._history.clear()
    narration: >
      ToolAgent follows the same class pattern as SimpleAgent and ReactAgent: bind
      the registry and model once, delegate the real work, and keep a history.
      ask routes one request and records it. add_tool extends the agent's own
      registry, so you can teach it new abilities at runtime. tools lists what it
      can do. Each agent gets a fresh registry from build_default_registry, so one
      agent's new tool never leaks into another.

  - type: concept
    label: "Three agents, one shape"
    heading: "The Section's Class Pattern"
    body: >
      Every agent this section wears the same skeleton.
    bullets:
      - "Day 79 SimpleAgent: bare action loop"
      - "Day 80 ReactAgent: reasoning loop with a trace"
      - "Day 81 ToolAgent: one-shot routing over many tools"
      - "All: bind at construction, delegate, keep a history copy"
      - "Only the engine inside changes - the handle stays familiar"
    narration: >
      Step back and notice the pattern. Three days, three agents, one class shape:
      bind the tools and model at construction, delegate the work to module
      functions, keep a history, and return a copy of it. What changes is the engine
      inside - a bare loop, a reasoning loop, a router. Keeping the class shape
      constant means each new agent is easy to pick up, and you can focus on the new
      idea rather than relearning the scaffolding.

  - type: exercise
    heading: "Exercise 5: ToolAgent"
    prompt: >
      Implement ToolAgent: __init__ uses the given registry or
      build_default_registry(), stores llm_fn and an empty history; add_tool extends
      the registry and returns self; tools() lists names; ask() routes via
      route_query and records the ask; history() returns a copy; clear_history()
      empties in place.
    hint: >
      self.registry = registry if registry is not None else build_default_registry().
      ask: route_query(query, self.registry, llm_fn=self._llm_fn); append
      {'query','result'}; return result.
    narration: >
      This completes the multi-tool assistant - hand it a model and a registry and
      it routes every request to the right tool.

  - type: summary
    heading: "Lesson 5 Summary - Day 81 Complete"
    bullets:
      - "ToolAgent binds a registry + llm_fn, routes each request, keeps history"
      - "add_tool extends the agent's own registry at runtime"
      - "Same class shape as SimpleAgent and ReactAgent"
      - "Day 81 adds: typed schemas, validation, a registry, and routing"
      - "Selection + validation = two guards on every tool call"
    narration: >
      You built a tool-using assistant that scales to a whole toolbox. Day 82 gives
      an agent memory - short-term working memory and long-term memory that persists
      across sessions.
"""

for i, content in enumerate([_LESSON_01, _LESSON_02, _LESSON_03,
                               _LESSON_04, _LESSON_05], start=1):
    (OUT / "lessons" / f"day_{DAY}_lesson_0{i}.yaml").write_text(content)

# ── PROJECT NOTEBOOK ──────────────────────────────────────────────────────────
PROJECT = nb([
    md(f"# Day {DAY} — Project: A Multi-Tool Assistant\n\n"
       "## Objective\n\n"
       "Build `tool_agent.py` — an assistant that routes each request to the best "
       "tool from a validated toolbox.\n\n"
       "## Deliverable\n\n"
       "`tool_agent.py` with:\n\n"
       "- `DEFAULT_TOOLS` — a toolbox where each tool has a typed parameter schema\n"
       "- `validate_args(tool, args) -> (ok, error)`\n"
       "- `ToolRegistry` — `register/add/get/names/describe/validate/execute`\n"
       "- `build_default_registry()`\n"
       "- `build_selection_prompt(query, registry)` / `select_tool(...)`\n"
       "- `route_query(query, registry, llm_fn=None) -> dict`\n"
       "- `ToolAgent(registry=None, llm_fn=None)` with "
       "`add_tool/tools/ask/history/clear_history`\n\n"
       "## Usage (with Ollama running + llama3.2 pulled)\n\n"
       "```python\n"
       "from tool_agent import ToolAgent\n"
       "agent = ToolAgent()\n"
       "print(agent.ask('reverse the word hello')['result'])\n"
       "print(agent.ask('what is 19 * 23')['result'])\n"
       "```\n\n"
       "**The deliverable:** you run it, and each request is routed to the right "
       "tool — validated, executed, and answered. Two guards (a real tool, valid "
       "args) stand between the model and every tool call."),
    code("# Your implementation here — build tool_agent.py\n"),
])
save(OUT / "project" / "project.ipynb", PROJECT)

# ── SOLUTION NOTEBOOK ─────────────────────────────────────────────────────────
_SOL_CELL1 = (
    f"_SRC = {repr(_TOOL_AGENT_SRC)}\n"
    "from pathlib import Path\n"
    "Path('tool_agent.py').write_text(_SRC, encoding='utf-8')\n"
    "print('tool_agent.py written.')"
)

_SOL_CELL2 = r"""
from tool_agent import (
    DEFAULT_TOOLS, validate_args, ToolRegistry, build_default_registry,
    build_selection_prompt, select_tool, route_query, ToolAgent,
)
import json

def _pick(tool, args):
    payload = json.dumps({'tool': tool, 'args': args})
    return lambda messages: payload

# 1. validate_args + toolbox
repeat = next(t for t in DEFAULT_TOOLS if t['name'] == 'repeat')
assert repeat['fn']({'text': 'ab', 'times': 3}) == 'ababab'
assert validate_args(repeat, {'text': 'hi', 'times': 2})[0] is True
assert validate_args(repeat, {'text': 'hi'})[0] is False            # missing
assert validate_args(repeat, {'text': 'hi', 'times': 'x'})[0] is False  # wrong type
print("✅ DEFAULT_TOOLS + validate_args")

# 2. ToolRegistry
reg = build_default_registry()
assert len(reg) >= 5 and 'calculator' in reg
assert reg.execute('uppercase', {'text': 'hi'}) == 'HI'
assert reg.execute('repeat', {'text': 'hi'}).lower().startswith('error')  # validation gate
assert 'repeat(' in reg.describe()
print("✅ ToolRegistry (describe / validate / execute)")

# 3. select_tool
msgs = build_selection_prompt('shout', reg)
assert 'calculator' in msgs[0]['content']
assert select_tool('x', reg, llm_fn=_pick('uppercase', {'text': 'hi'}))['tool'] == 'uppercase'
assert select_tool('x', reg, llm_fn=_pick('teleport', {}))['tool'] == 'none'  # hallucinated
assert select_tool('x', reg, llm_fn=lambda m: 'no idea')['tool'] == 'none'    # garbage
print("✅ select_tool (routing, fallback to none)")

# 4. route_query
r = route_query('x', reg, llm_fn=_pick('repeat', {'text': 'ab', 'times': 3}))
assert r['tool'] == 'repeat' and r['result'] == 'ababab'
assert route_query('x', reg, llm_fn=_pick('none', {}))['tool'] == 'none'
assert route_query('x', reg, llm_fn=_pick('repeat', {'text': 'ab'}))['result'].lower().startswith('error')
print("✅ route_query (select -> validate -> execute)")

# 5. ToolAgent
agent = ToolAgent(llm_fn=_pick('uppercase', {'text': 'hi'}))
assert agent.ask('shout hi')['result'] == 'HI'
assert 'calculator' in agent.tools() and 'repeat' in agent.tools()
agent.add_tool('double', 'Double a number.', lambda a: str(int(a['n']) * 2),
               {'n': {'type': 'integer', 'required': True}})
assert 'double' in agent.tools() and 'double' not in {t['name'] for t in DEFAULT_TOOLS}
assert len(agent.history()) == 1
agent.history().clear()
assert len(agent.history()) == 1     # history() returns a copy
agent.clear_history()
assert len(agent.history()) == 0
print("✅ ToolAgent (ask / add_tool / history / clear_history)")

print("\nMulti-tool assistant complete!")
"""

SOLUTION = nb([
    md(f"# Day {DAY} — Solution: A Multi-Tool Assistant"),
    code(_SOL_CELL1),
    code(_SOL_CELL2),
])
save(OUT / "project" / "solution" / "solution.ipynb", SOLUTION)
(OUT / "project" / "solution" / "tool_agent.py").write_text(_TOOL_AGENT_SRC)

print(f"Day {DAY} notebooks written to {OUT}")
print("  lessons/    day_081_lesson_01.yaml – lesson_05.yaml")
print("  exercises/  exercise_01 – exercise_05")
print("  project/    project.ipynb")
print("  project/solution/  solution.ipynb + tool_agent.py")
