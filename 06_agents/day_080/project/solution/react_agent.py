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
    return "\n".join(lines)


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

# ── formatting the trace (the scratchpad) ─────────────────────────────────────
def format_step(step):
    """Render an action step back into ReAct text for the scratchpad."""
    return ("Thought: " + step["thought"] + "\n"
            + "Action: " + step["tool"] + "\n"
            + "Input: " + json.dumps(step["input"]))


def format_observation(result):
    """Render a tool result as an Observation line."""
    return "Observation: " + str(result)


def build_react_prompt(task, tools, scratchpad):
    """Build the [system, user] messages for one ReAct step."""
    system = "\n".join([
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
        user = user + "\n\n" + scratchpad.rstrip()
    user = user + "\n\nThought:"
    return [{"role": "system", "content": system},
            {"role": "user", "content": user}]

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
        scratchpad = scratchpad + format_step(step) + "\n"
        scratchpad = scratchpad + format_observation(result) + "\n"
    return {"answer": "Stopped: reached max_iterations without a final answer.",
            "thought": "", "trace": trace,
            "iterations": max_iterations, "stopped": True}

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
