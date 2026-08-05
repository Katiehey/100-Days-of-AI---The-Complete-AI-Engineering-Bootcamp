#!/usr/bin/env python3
"""Day 085 generator — Model Context Protocol (MCP)."""
import json, pathlib

ROOT  = pathlib.Path(__file__).parent.parent
DAY   = "085"
SLUG  = "mcp_agent"
TITLE = "Model Context Protocol (MCP)"
DIR   = ROOT / "06_agents" / f"day_{DAY}"

# ══════════════════════════════════════════════════════════════════════════════
# Deliverable source fragments
# ══════════════════════════════════════════════════════════════════════════════

_FRAG_DOC = '''\
"""
Day 085 — Model Context Protocol (MCP)
=======================================
MCP (Model Context Protocol) is an open standard for connecting AI models to
external tools, data sources, and context providers without writing custom
integration code for every combination.

Core idea
---------
An **MCP server** hosts tools (callable functions) and resources (data blobs).
An **MCP client** connects to a server, discovers what it exposes, and calls
those tools on behalf of an agent.  The protocol separates who defines the
tool from who calls it, making agents composable and interoperable.

Real MCP uses stdio or SSE transport between processes with async I/O.  This
module teaches the same concepts through a simple in-process implementation
that is identical from the agent perspective.

Public API
----------
    MCPToolDef              dataclass — name, description, input_schema dict
    tool_schema_text        render tool list as a prompt-ready menu
    MCPServer               hosts callable functions as named MCP tools
    MCPClient               connects to a server; injectable for gate testing
    build_mcp_selection_prompt
    select_mcp_tool         LLM picks the right tool from the client's list
    MCPAgent                discover -> select -> call -> record

Gate helpers (underscore prefix — not for production)
    _mock_mcp_llm           returns an llm_fn that always selects one tool
    _mock_tool_call         a tool_call_fn that echoes the tool name
    call_llm                thin wrapper; uses Ollama when llm_fn is None
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

_FRAG_TOOLDEF = '''\

# ── MCP tool definition ───────────────────────────────────────────────────────

@dataclass
class MCPToolDef:
    """An MCP-style tool definition.

    In the Model Context Protocol every tool advertised by a server carries a
    structured schema that clients can discover at runtime.  Here we use a flat
    dict (param_name -> description string) for input_schema, which captures
    the concept without the full JSON Schema machinery.
    """
    name:         str
    description:  str
    input_schema: dict = field(default_factory=dict)


def tool_schema_text(tools):
    """Render an MCPToolDef list as a compact tool menu for an LLM prompt.

    Format per tool:
        - tool_name(param1, param2, ...): description
    """
    lines = []
    for t in tools:
        params = ", ".join(t.input_schema.keys())
        lines.append("- " + t.name + "(" + params + "): " + t.description)
    return "\\n".join(lines)
'''

_FRAG_SERVER = '''\

# ── MCP server ────────────────────────────────────────────────────────────────

class MCPServer:
    """An in-process MCP server.

    In real MCP a server is a separate process reached over stdio or SSE.
    This version lives in the same process so you can learn the API without a
    subprocess.  The interface mirrors the real thing: decorate functions with
    @server.tool(...) to register them, then let clients discover and call them.
    """

    def __init__(self, name="mcp_server"):
        self.name   = name
        self._tools = {}          # name -> {"def": MCPToolDef, "fn": callable}

    def tool(self, name, description, schema=None):
        """Decorator that registers a function as a named MCP tool.

        Usage::

            @server.tool("word_count", "Count words.", {"text": "input text"})
            def word_count(text):
                return str(len(str(text).split()))
        """
        def _decorator(fn):
            self._tools[name] = {
                "def": MCPToolDef(name, description, schema or {}),
                "fn":  fn,
            }
            return fn
        return _decorator

    def list_tools(self):
        """Return a list of MCPToolDef for every registered tool."""
        return [entry["def"] for entry in self._tools.values()]

    def call_tool(self, name, args):
        """Call a registered tool by name with keyword arguments from args dict.

        Returns the string result.  Never raises — errors come back as strings.
        """
        entry = self._tools.get(name)
        if entry is None:
            return "Error: unknown tool " + repr(name)
        try:
            return str(entry["fn"](**args))
        except Exception as exc:
            return "Error: " + str(exc)
'''

_FRAG_CLIENT = '''\

# ── MCP client ────────────────────────────────────────────────────────────────

class MCPClient:
    """A client that connects to an MCPServer.

    In real MCP this opens a transport (stdio pipe or SSE connection) to a
    server process.  Here it holds a direct reference to an MCPServer, giving
    the same interface with no subprocess required.

    Inject tool_call_fn instead of server to mock all calls during gate testing.
    """

    def __init__(self, server=None, tool_call_fn=None):
        self._server       = server
        self._tool_call_fn = tool_call_fn

    def list_tools(self):
        """Return the server's tool list, or [] if no server is configured."""
        if self._server is not None:
            return self._server.list_tools()
        return []

    def call_tool(self, name, args):
        """Call a tool.  Uses tool_call_fn if injected, then server, then error."""
        if self._tool_call_fn is not None:
            return self._tool_call_fn(name, args)
        if self._server is not None:
            return self._server.call_tool(name, args)
        return "Error: no server or tool_call_fn configured"
'''

_FRAG_SELECT = '''\

# ── tool selection ────────────────────────────────────────────────────────────

def build_mcp_selection_prompt(query, tools):
    """Build a router prompt that asks the LLM to pick one tool from the list."""
    menu   = tool_schema_text(tools)
    system = "\\n".join([
        "You are a tool router. Pick the best tool for the request.",
        "Available tools:",
        menu,
        "Return ONLY a JSON object with keys 'tool' and 'args'.",
        "Use tool name 'none' if no tool fits.",
    ])
    return [
        {"role": "system", "content": system},
        {"role": "user",   "content": "Request: " + str(query)},
    ]


def select_mcp_tool(query, client, llm_fn=None):
    """Ask the LLM to pick the right tool from the client's tool list.

    Returns {"tool": <name or "none">, "args": <dict>}.  Never raises.
    """
    tools = client.list_tools()
    if not tools:
        return {"tool": "none", "args": {}}
    messages = build_mcp_selection_prompt(query, tools)
    response  = call_llm(messages, llm_fn=llm_fn)
    data      = safe_parse_json(response) or {}
    name      = data.get("tool", "none")
    args      = data.get("args", {})
    known     = {t.name for t in tools}
    if name not in known:
        name = "none"
    return {"tool": name, "args": args if isinstance(args, dict) else {}}
'''

_FRAG_AGENT = '''\

# ── MCP agent ─────────────────────────────────────────────────────────────────

class MCPAgent:
    """An agent that discovers and uses tools from an MCP client.

    Workflow per query
    ------------------
    1. Discover available tools via client.list_tools()
    2. Ask the LLM to select the right tool  (select_mcp_tool)
    3. Call the chosen tool via client.call_tool()
    4. Record the result in history
    5. Return {"query", "tool", "args", "result"} dict

    Compatible class shape: .tools() / .ask() / .history() / .clear_history()
    matches SimpleAgent, ReactAgent, ToolAgent, MemoryAgent, PlannerAgent.
    """

    def __init__(self, client, llm_fn=None):
        self.client   = client
        self._llm_fn  = llm_fn
        self._history = []

    def tools(self):
        """Return the MCPToolDef list from the connected client."""
        return self.client.list_tools()

    def ask(self, query):
        """Route query to the best tool and return the result dict."""
        selection = select_mcp_tool(query, self.client, llm_fn=self._llm_fn)
        if selection["tool"] == "none":
            record = {
                "query":  query,
                "tool":   "none",
                "args":   {},
                "result": "No suitable tool found.",
            }
        else:
            result = self.client.call_tool(selection["tool"], selection["args"])
            record = {
                "query":  query,
                "tool":   selection["tool"],
                "args":   selection["args"],
                "result": result,
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

def _mock_mcp_llm(tool="none", args=None):
    """Return an llm_fn that always selects the given tool with given args."""
    payload = json.dumps({"tool": tool, "args": args or {}})
    return lambda messages: payload


def _mock_tool_call(name, args):
    """A tool_call_fn that returns 'Result:<name>' without a real server."""
    return "Result:" + str(name)
'''

DELIVERABLE = (
    _FRAG_DOC + _FRAG_IMPORTS + _FRAG_HELPERS + _FRAG_TOOLDEF
    + _FRAG_SERVER + _FRAG_CLIENT + _FRAG_SELECT + _FRAG_AGENT + _FRAG_MOCK
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

# ── context preludes (compact, complete implementations for later exercises) ──

_P_BASE = """\
import json
from dataclasses import dataclass, field
"""

_P_TOOLDEF = """\
@dataclass
class MCPToolDef:
    name: str
    description: str
    input_schema: dict = field(default_factory=dict)

def tool_schema_text(tools):
    lines = []
    for t in tools:
        params = ", ".join(t.input_schema.keys())
        lines.append("- " + t.name + "(" + params + "): " + t.description)
    return "\\n".join(lines)
"""

_P_SERVER = """\
class MCPServer:
    def __init__(self, name="mcp_server"):
        self.name = name
        self._tools = {}
    def tool(self, name, description, schema=None):
        def _decorator(fn):
            self._tools[name] = {"def": MCPToolDef(name, description, schema or {}), "fn": fn}
            return fn
        return _decorator
    def list_tools(self):
        return [e["def"] for e in self._tools.values()]
    def call_tool(self, name, args):
        e = self._tools.get(name)
        if e is None:
            return "Error: unknown tool " + repr(name)
        try:
            return str(e["fn"](**args))
        except Exception as exc:
            return "Error: " + str(exc)
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

_P_CLIENT = """\
class MCPClient:
    def __init__(self, server=None, tool_call_fn=None):
        self._server = server
        self._tool_call_fn = tool_call_fn
    def list_tools(self):
        if self._server is not None:
            return self._server.list_tools()
        return []
    def call_tool(self, name, args):
        if self._tool_call_fn is not None:
            return self._tool_call_fn(name, args)
        if self._server is not None:
            return self._server.call_tool(name, args)
        return "Error: no server or tool_call_fn configured"
"""

_P_SELECT = """\
def build_mcp_selection_prompt(query, tools):
    menu = tool_schema_text(tools)
    system = "\\n".join([
        "You are a tool router. Pick the best tool for the request.",
        "Available tools:", menu,
        "Return ONLY a JSON object with keys 'tool' and 'args'.",
        "Use tool name 'none' if no tool fits.",
    ])
    return [{"role": "system", "content": system},
            {"role": "user",   "content": "Request: " + str(query)}]

def select_mcp_tool(query, client, llm_fn=None):
    tools = client.list_tools()
    if not tools:
        return {"tool": "none", "args": {}}
    messages = build_mcp_selection_prompt(query, tools)
    response = call_llm(messages, llm_fn=llm_fn)
    data = safe_parse_json(response) or {}
    name = data.get("tool", "none")
    args = data.get("args", {})
    known = {t.name for t in tools}
    if name not in known:
        name = "none"
    return {"tool": name, "args": args if isinstance(args, dict) else {}}
"""

_P_MOCK = """\
def _mock_mcp_llm(tool="none", args=None):
    payload = json.dumps({"tool": tool, "args": args or {}})
    return lambda messages: payload

def _mock_tool_call(name, args):
    return "Result:" + str(name)
"""

# ══════════════════════════════════════════════════════════════════════════════
# Exercise notebooks
# ══════════════════════════════════════════════════════════════════════════════

_EX1 = _nb([
    _md("# Exercise 1 — MCPToolDef and tool_schema_text\n\n"
        "Every MCP server advertises its tools using a structured schema.  "
        "**MCPToolDef** captures that schema: a name, a description, and a "
        "dict of parameter names to description strings.  "
        "**tool_schema_text** renders a list of MCPToolDef objects into a "
        "compact menu that can be dropped into an LLM prompt."),
    _code(_P_BASE + """\

# ── Exercise: implement MCPToolDef and tool_schema_text ──────────────────────

@dataclass
class MCPToolDef:
    name: str = ''            # TODO: three fields — name, description, input_schema
    description: str = ''
    # input_schema should default to an empty dict (use field(default_factory=dict))


def tool_schema_text(tools):
    # TODO: for each MCPToolDef in tools:
    #   - join the keys of tool.input_schema with ", " as params
    #   - append "- name(params): description" to a lines list
    # Return the lines joined with "\\n"
    return ""
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — MCPToolDef instantiates correctly
try:
    import dataclasses
    assert dataclasses.is_dataclass(MCPToolDef)
    t = MCPToolDef("calc", "Evaluate arithmetic.", {"expression": "math expression"})
    assert t.name == "calc" and t.description == "Evaluate arithmetic."
    checks += 1; print("✅ 1 MCPToolDef instantiates with name, description, input_schema")
except Exception as e:
    print("❌ 1:", e)

# 2 — default input_schema is empty dict
try:
    t = MCPToolDef("x", "y")
    assert t.input_schema == {}
    checks += 1; print("✅ 2 default input_schema is {}")
except Exception as e:
    print("❌ 2:", e)

# 3 — input_schema stores provided params
try:
    t = MCPToolDef("wc", "Count words.", {"text": "the text"})
    assert "text" in t.input_schema
    checks += 1; print("✅ 3 input_schema stores param names")
except Exception as e:
    print("❌ 3:", e)

# 4 — tool_schema_text includes name and description
try:
    t = MCPToolDef("calc", "Math.", {"expression": "str"})
    text = tool_schema_text([t])
    assert "calc" in text and "Math." in text
    checks += 1; print("✅ 4 tool_schema_text includes name and description")
except Exception as e:
    print("❌ 4:", e)

# 5 — tool_schema_text includes param names
try:
    t = MCPToolDef("fn", "Desc.", {"a": "first", "b": "second"})
    text = tool_schema_text([t])
    assert "a" in text and "b" in text
    checks += 1; print("✅ 5 tool_schema_text includes param names from input_schema")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX2 = _nb([
    _md("# Exercise 2 — MCPServer\n\n"
        "An **MCPServer** hosts callable tools.  Use the `@server.tool()` "
        "decorator to register a function.  `list_tools()` returns the schema "
        "list for discovery; `call_tool(name, args)` invokes the function with "
        "keyword arguments from the args dict.  Errors never raise — they come "
        "back as error strings."),
    _code(_P_BASE + _P_TOOLDEF + """\

# ── Exercise: implement MCPServer ────────────────────────────────────────────

class MCPServer:
    \"\"\"An in-process MCP server that registers and calls tools.\"\"\"

    def __init__(self, name="mcp_server"):
        self.name = name
        self._tools = {}

    def tool(self, name, description, schema=None):
        \"\"\"Return a decorator that registers the function as a named MCP tool.\"\"\"
        def _decorator(fn):
            # TODO: store {"def": MCPToolDef(name, description, schema or {}),
            #              "fn": fn} in self._tools[name]
            return fn
        return _decorator

    def list_tools(self):
        # TODO: return a list of entry["def"] for each entry in self._tools.values()
        return []

    def call_tool(self, name, args):
        # TODO: look up entry in self._tools; call entry["fn"](**args); return str(result)
        # If name is not in self._tools, return "Error: unknown tool ..."
        # Never raise — catch exceptions and return "Error: ..."
        return "Error: not implemented"
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — MCPServer creates
try:
    server = MCPServer("test_server")
    assert server.name == "test_server"
    checks += 1; print("✅ 1 MCPServer created with name")
except Exception as e:
    print("❌ 1:", e)

# 2 — @server.tool decorator preserves the function
try:
    server = MCPServer("s")
    @server.tool("word_count", "Count words.", {"text": "text to count"})
    def word_count(text):
        return str(len(str(text).split()))
    assert word_count("hello world") == "2"
    checks += 1; print("✅ 2 @server.tool decorator preserves the function")
except Exception as e:
    print("❌ 2:", e)

# 3 — list_tools returns MCPToolDef list
try:
    server = MCPServer("s")
    @server.tool("wc", "Count.", {"text": "str"})
    def wc(text): return str(len(text.split()))
    tools = server.list_tools()
    assert len(tools) == 1 and tools[0].name == "wc"
    checks += 1; print("✅ 3 list_tools returns MCPToolDef list")
except Exception as e:
    print("❌ 3:", e)

# 4 — call_tool invokes the function with **args
try:
    server = MCPServer("s")
    @server.tool("upper", "Uppercase.", {"text": "str"})
    def upper(text): return str(text).upper()
    assert server.call_tool("upper", {"text": "hello"}) == "HELLO"
    checks += 1; print("✅ 4 call_tool returns correct result")
except Exception as e:
    print("❌ 4:", e)

# 5 — call_tool returns error string for unknown tool (does not raise)
try:
    server = MCPServer("s")
    result = server.call_tool("no_such_tool", {})
    assert isinstance(result, str)
    assert "error" in result.lower() or "unknown" in result.lower() or "no_such_tool" in result
    checks += 1; print("✅ 5 call_tool returns error string for unknown tool")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX3 = _nb([
    _md("# Exercise 3 — MCPClient\n\n"
        "The **MCPClient** is the consumer side of MCP.  In real MCP it opens "
        "a transport to a server subprocess.  Here it holds a reference to an "
        "MCPServer (same interface, no subprocess).  For gate testing, inject "
        "a `tool_call_fn` instead of a server — the client uses whichever is "
        "provided."),
    _code(_P_BASE + _P_TOOLDEF + _P_SERVER + """\

# ── Exercise: implement MCPClient ────────────────────────────────────────────

class MCPClient:
    \"\"\"Connects to an MCPServer and calls tools on behalf of an agent.\"\"\"

    def __init__(self, server=None, tool_call_fn=None):
        # TODO: store server and tool_call_fn as instance attributes
        pass

    def list_tools(self):
        # TODO: if self._server is not None, return self._server.list_tools()
        # else return []
        return []

    def call_tool(self, name, args):
        # TODO: if self._tool_call_fn is not None, call it with (name, args)
        # elif self._server is not None, call self._server.call_tool(name, args)
        # else return "Error: no server or tool_call_fn configured"
        return "Error: not implemented"
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# helper server for tests
_srv = MCPServer("test")
@_srv.tool("add", "Add two numbers.", {"a": "first", "b": "second"})
def _add(a, b): return str(int(a) + int(b))

# 1 — MCPClient constructs with server=
try:
    client = MCPClient(server=_srv)
    checks += 1; print("✅ 1 MCPClient constructs with server=")
except Exception as e:
    print("❌ 1:", e)

# 2 — list_tools delegates to server
try:
    client = MCPClient(server=_srv)
    tools = client.list_tools()
    assert any(t.name == "add" for t in tools)
    checks += 1; print("✅ 2 list_tools returns server's tool list")
except Exception as e:
    print("❌ 2:", e)

# 3 — call_tool delegates to server
try:
    client = MCPClient(server=_srv)
    assert client.call_tool("add", {"a": "3", "b": "4"}) == "7"
    checks += 1; print("✅ 3 call_tool delegates to server")
except Exception as e:
    print("❌ 3:", e)

# 4 — tool_call_fn overrides server
try:
    mock_fn = lambda name, args: "mocked:" + name
    client = MCPClient(tool_call_fn=mock_fn)
    assert client.call_tool("any_tool", {}) == "mocked:any_tool"
    checks += 1; print("✅ 4 tool_call_fn is used when provided")
except Exception as e:
    print("❌ 4:", e)

# 5 — empty client is safe
try:
    client = MCPClient()
    assert client.list_tools() == []
    result = client.call_tool("x", {})
    assert isinstance(result, str) and len(result) > 0
    checks += 1; print("✅ 5 MCPClient() with no args is safe")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX4 = _nb([
    _md("# Exercise 4 — select_mcp_tool\n\n"
        "`build_mcp_selection_prompt` renders the client's tool list into a "
        "router prompt.  `select_mcp_tool` calls the LLM, parses the JSON "
        "response, validates the tool name, and falls back to `\"none\"` if "
        "anything goes wrong."),
    _code(_P_BASE + _P_TOOLDEF + _P_SERVER + _P_HELPERS + _P_CLIENT + """\

# ── Exercise: implement selection functions ──────────────────────────────────

def build_mcp_selection_prompt(query, tools):
    # TODO: call tool_schema_text(tools) to get the menu string
    # Build a system message that lists the tools and asks for JSON with
    # "tool" and "args" keys; include the fallback to "none"
    # Return [{"role": "system", ...}, {"role": "user", "content": "Request: " + str(query)}]
    return [{"role": "system", "content": ""}, {"role": "user", "content": str(query)}]


def select_mcp_tool(query, client, llm_fn=None):
    # TODO: get tools from client.list_tools()
    # If no tools, return {"tool": "none", "args": {}}
    # Build prompt, call LLM, safe_parse_json the response
    # Validate: if name not in known tool names, set name = "none"
    # Return {"tool": name, "args": args_dict}
    return {"tool": "none", "args": {}}
"""),
    _md("### Checks"),
    _code("""\
import json

def _mock_llm(tool, args=None):
    payload = json.dumps({"tool": tool, "args": args or {}})
    return lambda messages: payload

checks = 0

# helper server
_srv = MCPServer("t")
@_srv.tool("wc", "Count words.", {"text": "str"})
def _wc(text): return str(len(str(text).split()))
_client = MCPClient(server=_srv)

# 1 — select_mcp_tool returns dict with "tool" and "args"
try:
    sel = select_mcp_tool("count words", _client, llm_fn=_mock_llm("wc", {"text": "hi"}))
    assert "tool" in sel and "args" in sel
    checks += 1; print("✅ 1 select_mcp_tool returns {tool, args}")
except Exception as e:
    print("❌ 1:", e)

# 2 — correct tool selected
try:
    sel = select_mcp_tool("how many words?", _client, llm_fn=_mock_llm("wc", {"text": "hello world"}))
    assert sel["tool"] == "wc" and sel["args"] == {"text": "hello world"}
    checks += 1; print("✅ 2 correct tool and args returned")
except Exception as e:
    print("❌ 2:", e)

# 3 — unknown tool name -> "none"
try:
    sel = select_mcp_tool("something", _client, llm_fn=_mock_llm("nonexistent"))
    assert sel["tool"] == "none"
    checks += 1; print("✅ 3 unknown tool name coerced to 'none'")
except Exception as e:
    print("❌ 3:", e)

# 4 — build_mcp_selection_prompt includes tool names
try:
    tools = _client.list_tools()
    prompt = build_mcp_selection_prompt("test", tools)
    combined = " ".join(m.get("content", "") for m in prompt)
    assert "wc" in combined
    checks += 1; print("✅ 4 build_mcp_selection_prompt includes tool names")
except Exception as e:
    print("❌ 4:", e)

# 5 — empty client returns "none" without calling LLM
try:
    empty_client = MCPClient()
    sel = select_mcp_tool("anything", empty_client, llm_fn=None)
    assert sel["tool"] == "none"
    checks += 1; print("✅ 5 empty client returns 'none' immediately")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX5 = _nb([
    _md("# Exercise 5 — MCPAgent\n\n"
        "**MCPAgent** wires the MCP stack together: it holds a client, uses "
        "`select_mcp_tool` to route each query to the right tool, calls the "
        "tool via the client, and records the interaction in history.  "
        "Same class shape as all prior section agents."),
    _code(_P_BASE + _P_TOOLDEF + _P_SERVER + _P_HELPERS + _P_CLIENT + _P_SELECT + _P_MOCK + """\

# ── Exercise: implement MCPAgent ─────────────────────────────────────────────

class MCPAgent:
    \"\"\"An agent that discovers and uses tools from an MCP client.\"\"\"

    def __init__(self, client, llm_fn=None):
        # TODO: store client, llm_fn, and an empty history list
        pass

    def tools(self):
        # TODO: return self.client.list_tools()
        return []

    def ask(self, query):
        # TODO: call select_mcp_tool(query, self.client, llm_fn=self._llm_fn)
        # If selection["tool"] == "none": result = "No suitable tool found."
        # Else: result = self.client.call_tool(tool, args)
        # Append {"query", "tool", "args", "result"} to self._history
        # Return the record dict
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

# helper setup
_srv = MCPServer("s")
@_srv.tool("upper", "Uppercase text.", {"text": "str"})
def _upper(text): return str(text).upper()
_client = MCPClient(server=_srv)

# 1 — MCPAgent constructs
try:
    agent = MCPAgent(_client, llm_fn=_mock_mcp_llm("upper", {"text": "hello"}))
    checks += 1; print("✅ 1 MCPAgent constructs")
except Exception as e:
    print("❌ 1:", e)

# 2 — tools() returns client's tool list
try:
    agent = MCPAgent(_client)
    assert any(t.name == "upper" for t in agent.tools())
    checks += 1; print("✅ 2 tools() returns client's tool list")
except Exception as e:
    print("❌ 2:", e)

# 3 — ask() returns dict with tool, args, result
try:
    agent = MCPAgent(_client, llm_fn=_mock_mcp_llm("upper", {"text": "hello"}))
    r = agent.ask("uppercase hello")
    assert r["tool"] == "upper" and r["result"] == "HELLO"
    checks += 1; print("✅ 3 ask() routes and returns result")
except Exception as e:
    print("❌ 3:", e)

# 4 — ask() with no tool returns "No suitable tool found."
try:
    agent = MCPAgent(_client, llm_fn=_mock_mcp_llm("none"))
    r = agent.ask("something unrelated")
    assert r["tool"] == "none" and "No suitable tool" in r["result"]
    checks += 1; print("✅ 4 ask() with no tool returns fallback message")
except Exception as e:
    print("❌ 4:", e)

# 5 — history grows with each ask
try:
    agent = MCPAgent(_client, llm_fn=_mock_mcp_llm("upper", {"text": "x"}))
    agent.ask("q1"); agent.ask("q2")
    assert len(agent.history()) == 2
    checks += 1; print("✅ 5 history() grows with each ask()")
except Exception as e:
    print("❌ 5:", e)

# 6 — clear_history empties history
try:
    agent = MCPAgent(_client, llm_fn=_mock_mcp_llm("upper", {"text": "x"}))
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
day: "085"
lesson: 1
title: "What Is MCP?"
slides:
  - type: title
    heading: "Model Context Protocol"
    subheading: "The universal connector for AI tool access"
    narration: >
      Day 81 gave an agent a ToolRegistry with a fixed list of tools baked into
      the code. That works for one project, but if you want to reuse those tools
      in a different framework, or let someone else's agent call them, you have
      to rewrite the integration. MCP solves this problem with a standard
      protocol: any MCP client can talk to any MCP server, regardless of what
      language or framework each was written in.

  - type: concept
    label: "The problem"
    heading: "Every Framework Invents Its Own Tool Format"
    body: >
      Before MCP, every AI framework had its own tool-calling convention.
    bullets:
      - "OpenAI function calling: JSON schema in the API request"
      - "LangChain tools: Python classes with a run() method"
      - "LlamaIndex tools: FunctionTool wrappers"
      - "Result: a tool built for one framework must be rewritten for another"
      - "MCP fixes this: one server definition, any client can call it"
    narration: >
      If you built a database query tool for LangChain and then wanted to use it
      in a custom agent, you had to port it. MCP eliminates that work by defining
      a standard wire format that all agents and all tool servers can speak.

  - type: concept
    label: "MCP architecture"
    heading: "Server, Client, Transport"
    body: >
      MCP separates tool definition from tool consumption.
    bullets:
      - "MCP Server: a process that hosts tools and exposes them over a protocol"
      - "MCP Client: connects to a server, discovers tools, calls them"
      - "Transport: how client and server communicate"
      - "  stdio: server is a subprocess, communication over stdin/stdout"
      - "  SSE: server is an HTTP endpoint, communication via Server-Sent Events"
      - "Today: in-process server (same concept, no subprocess)"
    narration: >
      The server and client are deliberately separate. A server written in Python
      can be called by a client written in TypeScript. A server hosted remotely
      can serve many clients. The transport layer handles the connection; the
      protocol layer handles what gets sent.

  - type: concept
    label: "Three primitives"
    heading: "Tools, Resources, Prompts"
    body: >
      MCP defines three things a server can expose.
    bullets:
      - "Tools: callable functions with a name, description, and parameter schema"
      - "Resources: data blobs (files, DB rows) an agent can read as context"
      - "Prompts: reusable prompt templates with named parameters"
      - "Today focuses on tools - the most commonly used primitive"
    narration: >
      Today's module implements the tools primitive in full. Resources and prompts
      follow the same server-client pattern but return data or prompt text instead
      of function results. Once you understand tools, the others follow naturally.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "MCP solves the tool integration fragmentation problem"
      - "Server hosts tools; client discovers and calls them"
      - "Transport connects them (stdio, SSE, or in-process for learning)"
      - "Three primitives: tools, resources, prompts"
      - "Today: full in-process implementation of the tools primitive"
""",

    """\
day: "085"
lesson: 2
title: "MCPToolDef and Servers"
slides:
  - type: title
    heading: "MCPToolDef and MCPServer"
    subheading: "Defining and hosting tools in MCP"
    narration: >
      Before an agent can call a tool, the tool must be described in a way the
      LLM can understand. MCPToolDef captures that description. MCPServer hosts
      a collection of MCPToolDef objects alongside the functions they describe,
      and exposes two operations: list the tools and call one of them.

  - type: concept
    label: "MCPToolDef"
    heading: "The Tool Schema"
    body: >
      Every MCP tool has three pieces of information.
    bullets:
      - "name: the identifier the LLM uses to request the tool"
      - "description: what the tool does (appears in the LLM prompt)"
      - "input_schema: dict of param_name -> description"
      - "In real MCP: input_schema is a full JSON Schema object"
      - "Here: simpler flat dict, same concept"
    narration: >
      The name and description are what the LLM sees in the router prompt. The
      input_schema tells both the LLM and the calling code what arguments to
      provide. In production MCP servers, input_schema is a full JSON Schema
      object with types, required fields, and constraints. Our simplified version
      uses a flat dict of param names to description strings.

  - type: code
    label: "MCPServer usage"
    heading: "Registering Tools with @server.tool"
    body: >
      The decorator pattern keeps tool definition close to the implementation.
    code: |
      server = MCPServer("my_server")

      @server.tool("word_count", "Count words in text.", {"text": "input text"})
      def word_count(text):
          return str(len(str(text).split()))

      @server.tool("uppercase", "Convert text to uppercase.", {"text": "input text"})
      def uppercase(text):
          return str(text).upper()

      # Discovery
      tools = server.list_tools()   # [MCPToolDef("word_count", ...), MCPToolDef("uppercase", ...)]

      # Invocation
      result = server.call_tool("word_count", {"text": "hello world"})  # "2"
    narration: >
      The decorator is a two-level closure. The outer call takes the tool's
      metadata and returns a decorator. The decorator takes the function, stores
      both the metadata and the function under the tool name, and returns the
      original function unchanged. So the function still works normally after
      registration — you can call word_count directly just as before.

  - type: concept
    label: "Discovery and invocation"
    heading: "list_tools and call_tool"
    body: >
      Two operations, two directions of the protocol.
    bullets:
      - "list_tools(): client calls this at startup to discover what the server offers"
      - "call_tool(name, args): client calls this to invoke a specific tool"
      - "args is a dict; the server unpacks it as **args when calling the function"
      - "Never raises: unknown tool or runtime error -> error string returned"
      - "Error strings let the agent decide how to handle failures"
    narration: >
      Keeping call_tool from raising is important for agent reliability. If a
      tool crashes, the agent receives an error string it can include in its
      reasoning, rather than an exception that would abort the entire agent loop.
      This is the same defensive pattern used in Day 79's execute_tool.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "MCPToolDef: name, description, input_schema — the tool contract"
      - "MCPServer: hosts tools via @server.tool decorator"
      - "list_tools(): discovery — what does this server offer?"
      - "call_tool(name, args): invocation — run this tool with these args"
      - "Never raises: errors are returned as strings"
""",

    """\
day: "085"
lesson: 3
title: "MCPClient — Connecting to a Server"
slides:
  - type: title
    heading: "MCPClient"
    subheading: "The consumer side of the MCP protocol"
    narration: >
      The server defines and hosts tools. The client is how an agent reaches
      them. In real MCP, the client opens a transport connection to a server
      subprocess or HTTP endpoint. In today's module, the client holds a direct
      reference to an MCPServer — same interface, no subprocess needed. And for
      gate testing, you can inject a mock function instead of any server at all.

  - type: concept
    label: "What a client does"
    heading: "Discovery and Invocation from the Agent's Side"
    body: >
      The client is a thin adapter between the agent and the server.
    bullets:
      - "client.list_tools(): discover what tools are available"
      - "client.call_tool(name, args): invoke one tool"
      - "The agent never talks to the server directly — always through the client"
      - "This indirection is what makes MCP composable"
    narration: >
      Why have a client layer at all? Because it means the agent doesn't need to
      know whether it's talking to an in-process server, a subprocess over stdio,
      or a remote server over SSE. The agent just calls list_tools and call_tool.
      Swap the client backend and the agent works unchanged.

  - type: code
    label: "MCPClient usage"
    heading: "Connecting a Client to a Server"
    body: >
      Pass the server at construction time; the client handles the rest.
    code: |
      # With a real (in-process) server
      server = MCPServer("demo")

      @server.tool("reverse", "Reverse words.", {"text": "str"})
      def reverse(text):
          return " ".join(reversed(str(text).split()))

      client = MCPClient(server=server)

      # Discovery
      tools = client.list_tools()
      print(tools[0].name)          # "reverse"

      # Invocation
      result = client.call_tool("reverse", {"text": "one two three"})
      print(result)                 # "three two one"
    narration: >
      The client delegates list_tools and call_tool directly to the server. In
      real MCP, those calls would be serialized into JSON-RPC messages and sent
      over the transport. The agent code doesn't change regardless.

  - type: concept
    label: "Dependency injection"
    heading: "Swapping the Server for a Mock"
    body: >
      Pass tool_call_fn instead of server for gate testing.
    bullets:
      - "MCPClient(tool_call_fn=fn): fn(name, args) -> str replaces server.call_tool"
      - "list_tools() returns [] when no server is configured"
      - "Gate tests: inject mock, never depend on a live server or Ollama"
      - "Production: swap to a real MCPServer (or a remote one) with no code changes"
    narration: >
      The gate for today's exercises runs with a mock tool_call_fn injected. This
      keeps the test fast and deterministic. When you run the project notebook for
      real, you swap in an MCPServer with actual tool implementations and Ollama
      as the LLM. The MCPAgent code stays identical either way.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "MCPClient sits between the agent and the server"
      - "list_tools() and call_tool() mirror the server interface"
      - "In-process: pass server= at construction"
      - "For testing: pass tool_call_fn= instead"
      - "Agent code is identical regardless of which backend the client uses"
""",

    """\
day: "085"
lesson: 4
title: "Tool Selection with MCP"
slides:
  - type: title
    heading: "Tool Selection with MCP"
    subheading: "The LLM as a router over MCP-discovered tools"
    narration: >
      The agent knows what tools exist because the client called list_tools. Now
      it needs to pick the right one for the current query. build_mcp_selection_prompt
      turns the tool list into a router prompt. select_mcp_tool calls the LLM,
      parses the JSON response, validates the result, and falls back gracefully.

  - type: concept
    label: "The selection loop"
    heading: "From Tool List to Chosen Tool"
    body: >
      Four steps every time the agent receives a query.
    bullets:
      - "1. client.list_tools() -> [MCPToolDef, ...]"
      - "2. tool_schema_text(tools) -> compact menu string"
      - "3. LLM reads menu + query -> JSON {tool, args}"
      - "4. Validate: name in known tools? If not -> 'none'"
    narration: >
      This is the same routing pattern as Day 81's select_tool, but the tool list
      now comes from a live client discovery call instead of a static registry.
      That means if the server adds a new tool at runtime, the agent will find it
      the next time it calls list_tools — no code change required.

  - type: code
    label: "select_mcp_tool"
    heading: "Routing a Query to the Right Tool"
    body: >
      The function handles the full selection cycle, including fallbacks.
    code: |
      import json
      from dataclasses import dataclass, field

      @dataclass
      class MCPToolDef:
          name: str
          description: str
          input_schema: dict = field(default_factory=dict)

      def _mock_llm(messages):
          return json.dumps({"tool": "word_count", "args": {"text": "hello world"}})

      # Assume client already has word_count tool registered
      sel = select_mcp_tool("how many words?", client, llm_fn=_mock_llm)
      print(sel)
      # {"tool": "word_count", "args": {"text": "hello world"}}

      result = client.call_tool(sel["tool"], sel["args"])
      print(result)   # "2"
    narration: >
      Notice the mock LLM is injected via llm_fn. The real Ollama call happens
      only when llm_fn is None, so the gate never touches the network or a live
      model. The validation step after parsing ensures that if the LLM hallucinates
      a tool name, the agent gets "none" back instead of a KeyError.

  - type: concept
    label: "Validation and fallback"
    heading: "Defensive Parsing"
    body: >
      Everything that can go wrong is handled without raising.
    bullets:
      - "No tools: return {'tool': 'none', 'args': {}} immediately"
      - "LLM returns non-JSON: safe_parse_json returns None -> default to 'none'"
      - "LLM picks unknown tool: coerce name to 'none'"
      - "LLM returns non-dict args: replace with {}"
      - "None of these paths raise an exception"
    narration: >
      In a long agent loop, a single exception from the router aborts the whole
      session. The fallback chain in select_mcp_tool prevents that. The agent gets
      a predictable no-tool-found result it can handle — surface to the user,
      retry, or choose a different approach.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "tool_schema_text converts MCPToolDef list to a prompt menu"
      - "build_mcp_selection_prompt wraps the menu in a router system message"
      - "select_mcp_tool: discover -> prompt -> LLM -> parse -> validate -> return"
      - "Unknown tool name is always coerced to 'none'"
      - "Same defensive pattern as Day 81, but tool list is live-discovered"
""",

    """\
day: "085"
lesson: 5
title: "MCPAgent — The Full Picture"
slides:
  - type: title
    heading: "MCPAgent"
    subheading: "Discover, select, call, record"
    narration: >
      The previous four lessons built the stack bottom-up: tool definition,
      server, client, selection. MCPAgent sits at the top and wires everything
      together. Each call to ask() runs the full MCP workflow in four steps,
      records the interaction, and returns a dict the caller can act on.

  - type: concept
    label: "Workflow"
    heading: "What ask() Does"
    body: >
      Four steps happen every time the agent receives a query.
    bullets:
      - "1. Discover: client.list_tools() -- what tools exist right now?"
      - "2. Select: select_mcp_tool -> {tool, args}"
      - "3. Call: client.call_tool(tool, args) -> result string"
      - "4. Record: append {query, tool, args, result} to history"
    narration: >
      Discovery happens on every ask() call, not just at startup. This means if
      the MCP server adds or removes tools between calls, the agent will pick them
      up automatically. For an in-process server this doesn't matter much, but in
      real MCP -- where a remote server might update its tool list -- this live
      discovery is a genuine advantage.

  - type: code
    label: "MCPAgent usage"
    heading: "Building and Running an MCPAgent"
    body: >
      Three objects, three lines of setup, one call to ask().
    code: |
      server = MCPServer("assistant")

      @server.tool("word_count", "Count words.", {"text": "str"})
      def word_count(text): return str(len(str(text).split()))

      @server.tool("uppercase", "Uppercase text.", {"text": "str"})
      def uppercase(text): return str(text).upper()

      client = MCPAgent(MCPClient(server=server))
      # -- wait, MCPAgent takes a client, not a server:
      agent = MCPAgent(MCPClient(server=server), llm_fn=my_llm)

      r = agent.ask("how many words in hello world")
      print(r["tool"])    # "word_count"
      print(r["result"])  # "2"

      for entry in agent.history():
          print(entry["query"], "->", entry["tool"])
    narration: >
      The three-layer stack -- server, client, agent -- gives you flexibility at
      each layer. Swap the server for a remote MCP server without changing the
      agent. Swap the llm_fn for a different model without changing the client.
      The layers are independently replaceable.

  - type: concept
    label: "Composability"
    heading: "Same Shape as Every Other Agent in Section 6"
    body: >
      MCPAgent matches the class shape used throughout this section.
    bullets:
      - ".tools()         -- what can this agent do?"
      - ".ask(query)      -- route and execute one query"
      - ".history()       -- what has it done so far?"
      - ".clear_history() -- start a new session"
      - "Consistent API: swap agents without rewriting the caller"
    narration: >
      All six agent classes in Section 6 -- SimpleAgent, ReactAgent, ToolAgent,
      MemoryAgent, PlannerAgent, and now MCPAgent -- share this four-method shape.
      That consistency is intentional. Once you know how to use one, you know how
      to use all of them. And when you build a system that wires multiple agents
      together, like Day 84's Orchestrator, you can treat them interchangeably.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "MCPAgent: client + llm_fn -> full MCP workflow per ask()"
      - "ask() discovers tools live on every call"
      - "Returns {query, tool, args, result} dict"
      - "history() and clear_history() for session management"
      - "Same four-method shape as all prior Section 6 agents"
""",
]

# ══════════════════════════════════════════════════════════════════════════════
# Project + Solution notebooks
# ══════════════════════════════════════════════════════════════════════════════

_PROJ_SETUP = _P_BASE + _P_TOOLDEF + _P_SERVER + _P_HELPERS + _P_CLIENT + _P_SELECT + _P_MOCK + """\

# ── Copy of MCPAgent (from mcp_agent.py) ────────────────────────────────────
class MCPAgent:
    def __init__(self, client, llm_fn=None):
        self.client = client
        self._llm_fn = llm_fn
        self._history = []
    def tools(self): return self.client.list_tools()
    def ask(self, query):
        selection = select_mcp_tool(query, self.client, llm_fn=self._llm_fn)
        if selection["tool"] == "none":
            record = {"query": query, "tool": "none", "args": {}, "result": "No suitable tool found."}
        else:
            result = self.client.call_tool(selection["tool"], selection["args"])
            record = {"query": query, "tool": selection["tool"], "args": selection["args"], "result": result}
        self._history.append(record)
        return record
    def history(self): return list(self._history)
    def clear_history(self): self._history.clear()
"""

PROJECT_NB = _nb([
    _md(f"# Day {DAY} Project — MCP-Connected Assistant\n\n"
        "Build an MCPServer with three tools, connect an MCPAgent to it, "
        "and run several queries through the full MCP stack."),
    _code(_PROJ_SETUP),
    _md("## Step 1 — Build the Server\n\nRegister three tools on an MCPServer."),
    _code("""\
server = MCPServer("assistant_server")

@server.tool("word_count", "Count the number of words in text.", {"text": "the text to count"})
def word_count(text):
    return str(len(str(text).split()))

@server.tool("uppercase", "Convert text to uppercase.", {"text": "the text to convert"})
def uppercase(text):
    return str(text).upper()

@server.tool("reverse_words", "Reverse the word order in text.", {"text": "the text to reverse"})
def reverse_words(text):
    return " ".join(reversed(str(text).split()))

print("Registered tools:", [t.name for t in server.list_tools()])
"""),
    _md("## Step 2 — Create Client and Agent\n\n"
        "Connect a client to the server, then wire it into an MCPAgent."),
    _code("""\
client = MCPClient(server=server)

# For gate testing we inject a mock LLM.
# Remove llm_fn=... and add llm_fn=None (or omit it) to use real Ollama.
llm_fn = _mock_mcp_llm("word_count", {"text": "the quick brown fox"})

agent = MCPAgent(client, llm_fn=llm_fn)
print("Agent tools:", [t.name for t in agent.tools()])
"""),
    _md("## Step 3 — Run Queries"),
    _code("""\
queries = [
    "How many words are in 'the quick brown fox'?",
]

for q in queries:
    r = agent.ask(q)
    print(f"Q: {r['query']}")
    print(f"  Tool: {r['tool']}  Args: {r['args']}")
    print(f"  Result: {r['result']}")
    print()
"""),
    _md("## Step 4 — Inspect History"),
    _code("""\
print(f"Total interactions: {len(agent.history())}")
for i, entry in enumerate(agent.history(), 1):
    print(f"{i}. [{entry['tool']}] {entry['result'][:60]}")
"""),
])

_SOL_QUERIES = [
    ("word_count",    {"text": "the quick brown fox jumps over the lazy dog"}),
    ("uppercase",     {"text": "hello mcp world"}),
    ("reverse_words", {"text": "one two three four five"}),
]

_SOL_SCRIPT = (
    "import json\n"
    "_SCRIPTS = [\n"
    + "".join(
        f'    json.dumps({{"tool": {repr(t)}, "args": {json.dumps(a)}}}),\n'
        for t, a in _SOL_QUERIES
    )
    + "]\n"
    "_script_idx = [0]\n"
    "\n"
    "def _scripted_llm(messages):\n"
    "    idx = _script_idx[0] % len(_SCRIPTS)\n"
    "    _script_idx[0] += 1\n"
    "    return _SCRIPTS[idx]\n"
)

SOLUTION_NB = _nb([
    _md(f"# Day {DAY} Solution — MCP-Connected Assistant"),
    _code(_PROJ_SETUP),
    _code(_SOL_SCRIPT),
    _code("""\
server = MCPServer("assistant_server")

@server.tool("word_count", "Count the number of words in text.", {"text": "the text to count"})
def word_count(text):
    return str(len(str(text).split()))

@server.tool("uppercase", "Convert text to uppercase.", {"text": "the text to convert"})
def uppercase(text):
    return str(text).upper()

@server.tool("reverse_words", "Reverse the word order in text.", {"text": "the text to reverse"})
def reverse_words(text):
    return " ".join(reversed(str(text).split()))

client = MCPClient(server=server)
agent  = MCPAgent(client, llm_fn=_scripted_llm)
print("Tools:", [t.name for t in agent.tools()])
"""),
    _code("""\
queries = [
    "How many words are in the sentence?",
    "Make this text uppercase.",
    "Reverse the word order please.",
]
for q in queries:
    r = agent.ask(q)
    print(f"[{r['tool']}] {r['result']}")
"""),
    _code("""\
print(f"History entries: {len(agent.history())}")
for entry in agent.history():
    print(f"  {entry['tool']}: {entry['result'][:60]}")
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

# MCPToolDef
t = mod.MCPToolDef("calc", "Evaluate arithmetic.", {{"expression": "math expression"}})
assert t.name == "calc"
assert t.description == "Evaluate arithmetic."
assert "expression" in t.input_schema

# tool_schema_text
text = mod.tool_schema_text([t])
assert "calc" in text and "expression" in text

# MCPServer
server = mod.MCPServer("test")
@server.tool("wc", "Count words.", {{"text": "input"}})
def wc(text): return str(len(str(text).split()))
tools = server.list_tools()
assert len(tools) == 1 and tools[0].name == "wc"
assert server.call_tool("wc", {{"text": "hello world"}}) == "2"
err = server.call_tool("nope", {{}})
assert "error" in err.lower() or "unknown" in err.lower() or "nope" in err

# MCPClient with server
client = mod.MCPClient(server=server)
assert len(client.list_tools()) == 1
assert client.call_tool("wc", {{"text": "a b c"}}) == "3"

# MCPClient with tool_call_fn
mock_fn = lambda name, args: "mocked:" + name
client2 = mod.MCPClient(tool_call_fn=mock_fn)
assert client2.call_tool("anything", {{}}) == "mocked:anything"
assert client2.list_tools() == []

# MCPClient empty
empty = mod.MCPClient()
assert empty.list_tools() == []
assert isinstance(empty.call_tool("x", {{}}), str)

# select_mcp_tool
mock_llm = mod._mock_mcp_llm("wc", {{"text": "hello"}})
sel = mod.select_mcp_tool("count words", client, llm_fn=mock_llm)
assert sel["tool"] == "wc" and sel["args"] == {{"text": "hello"}}

# select_mcp_tool unknown -> none
bad_llm = mod._mock_mcp_llm("nonexistent")
sel2 = mod.select_mcp_tool("something", client, llm_fn=bad_llm)
assert sel2["tool"] == "none"

# select_mcp_tool empty client
sel3 = mod.select_mcp_tool("anything", mod.MCPClient(), llm_fn=mock_llm)
assert sel3["tool"] == "none"

# MCPAgent
agent = mod.MCPAgent(client, llm_fn=mod._mock_mcp_llm("wc", {{"text": "hi"}}))
r = agent.ask("count words in hi")
assert r["tool"] == "wc"
assert r["result"] == "1"
assert len(agent.history()) == 1
agent.clear_history()
assert agent.history() == []

# MCPAgent no-tool fallback
agent2 = mod.MCPAgent(client, llm_fn=mod._mock_mcp_llm("none"))
r2 = agent2.ask("unrelated")
assert r2["tool"] == "none"
assert "No suitable tool" in r2["result"]

print("Gate: all inline checks passed")
"""

# ══════════════════════════════════════════════════════════════════════════════
# main
# ══════════════════════════════════════════════════════════════════════════════

def main():
    import subprocess, sys

    # directories
    (DIR / "exercises").mkdir(parents=True, exist_ok=True)
    (DIR / "lessons").mkdir(parents=True, exist_ok=True)
    (DIR / "project" / "solution").mkdir(parents=True, exist_ok=True)

    # deliverable
    (DIR / f"{SLUG}.py").write_text(DELIVERABLE, encoding="utf-8")
    (DIR / "project" / "solution" / f"{SLUG}.py").write_text(DELIVERABLE, encoding="utf-8")

    # exercises
    for i, nb in enumerate(EXERCISES, 1):
        path = DIR / "exercises" / f"exercise_{i:02d}.ipynb"
        path.write_text(json.dumps(nb, indent=1), encoding="utf-8")

    # lessons
    for i, yaml_text in enumerate(LESSONS, 1):
        path = DIR / "lessons" / f"day_{DAY}_lesson_{i:02d}.yaml"
        path.write_text(yaml_text, encoding="utf-8")

    # project + solution
    (DIR / "project" / "project.ipynb").write_text(
        json.dumps(PROJECT_NB, indent=1), encoding="utf-8")
    (DIR / "project" / "solution" / "solution.ipynb").write_text(
        json.dumps(SOLUTION_NB, indent=1), encoding="utf-8")

    print(f"[gen_day{DAY}] files written — running gate …")

    # ── precaution 2: inline validation ──────────────────────────────────────
    result = subprocess.run(
        ["conda", "run", "-n", "ai-course", "--no-capture-output",
         "python", "-c", GATE_PY],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print("GATE FAILED (inline)\n", result.stdout, result.stderr)
        sys.exit(1)
    print(result.stdout.strip())

    # ── precaution 2: nbclient notebook execution ─────────────────────────────
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
            f"assert not errs, 'Notebook {p.name} had errors: ' + str([c['outputs'] for c in errs])\n"
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

    # ── precaution 3: adversarial grep ───────────────────────────────────────
    banned = ["openai", "anthropic", r"\beval\b"]
    import re
    src = DELIVERABLE + "\n".join(
        json.dumps(nb) for nb in EXERCISES + [PROJECT_NB, SOLUTION_NB]
    )
    for pattern in banned:
        if re.search(pattern, src):
            print(f"GATE FAILED: banned pattern '{pattern}' found")
            sys.exit(1)
    print("Gate: adversarial grep clean")
    print(f"\n[gen_day{DAY}] gate-green ✓")


if __name__ == "__main__":
    main()
