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
    return "\n".join(lines)

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

# ── the agent loop ────────────────────────────────────────────────────────────
def build_agent_prompt(task, tools, history):
    """Build the [system, user] messages for one step of the loop."""
    system = "\n".join([
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
    user = "\n".join(lines)
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
