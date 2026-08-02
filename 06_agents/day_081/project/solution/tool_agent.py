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
        return "\n".join(lines)

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

# ── tool selection (routing) ──────────────────────────────────────────────────
def build_selection_prompt(query, registry):
    """Ask the model to choose ONE tool for the request and extract its args."""
    system = "\n".join([
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
