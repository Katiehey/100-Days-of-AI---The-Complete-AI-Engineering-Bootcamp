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
    return "\n".join(lines)

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

# ── tool selection ────────────────────────────────────────────────────────────

def build_mcp_selection_prompt(query, tools):
    """Build a router prompt that asks the LLM to pick one tool from the list."""
    menu   = tool_schema_text(tools)
    system = "\n".join([
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

# ── gate helpers ──────────────────────────────────────────────────────────────

def _mock_mcp_llm(tool="none", args=None):
    """Return an llm_fn that always selects the given tool with given args."""
    payload = json.dumps({"tool": tool, "args": args or {}})
    return lambda messages: payload


def _mock_tool_call(name, args):
    """A tool_call_fn that returns 'Result:<name>' without a real server."""
    return "Result:" + str(name)
