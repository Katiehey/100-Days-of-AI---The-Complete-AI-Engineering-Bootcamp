"""
Day 088 — Capstone: Ops Agent
===============================
The Section 6 capstone.  An autonomous operations agent that combines every
pattern from Days 79–87 into one coherent system:

    Day 79/80  agent loop + ReAct reasoning
    Day 81     tool registry and execution
    Day 82     task-level memory (TaskStore)
    Day 83     decomposing a goal into tasks
    Day 84     multi-step orchestration
    Day 87     input/budget/approval/output guardrails

An "ops agent" manages a queue of operational tasks (diagnostics, checks,
reports).  It reasons in ReAct steps (Thought/Action/Observation), executes
tools against a TaskStore, enforces guardrails on every iteration, and
records a full audit trace.

Public API
----------
    OpsTask(id, title, description, status, result)   — unit of work
    TaskStore                                          — in-memory task registry
    build_ops_tools(store, executor_fn)               — 4 tool functions
    OpsGuardrails(max_budget, banned_inputs, approve_fn)
    parse_ops_step(text)                              — parse one ReAct step
    format_ops_step(step, observation)                — format for scratchpad
    run_ops_step(goal, tools, scratchpad, llm_fn)     — one LLM + parse round
    run_ops_loop(goal, tools, llm_fn, guardrails, max_iterations)
    OpsAgent(store, guardrails, llm_fn, max_iterations)
"""
import json
from dataclasses import dataclass, field

# ── LLM + JSON helpers ────────────────────────────────────────────────────────

def call_llm(messages, llm_fn=None):
    if llm_fn is not None:
        return str(llm_fn(messages))
    import ollama
    resp = ollama.chat(model="llama3.2", messages=messages)
    return resp["message"]["content"]


def safe_parse_json(text):
    """Extract and parse the first JSON object from text. Returns dict or None."""
    text = str(text)
    start = text.find("{")
    end   = text.rfind("}") + 1
    if start == -1 or end == 0:
        return None
    try:
        return json.loads(text[start:end])
    except Exception:
        return None

# ── Day-87 guardrail building blocks (inlined for standalone use) ─────────────

def _validate_text(text, max_length=None, banned=None):
    text_str = str(text)
    if max_length is not None and len(text_str) > max_length:
        return False, (
            "text exceeds max_length ("
            + str(len(text_str)) + " > " + str(max_length) + " chars)"
        )
    if banned:
        lower = text_str.lower()
        for pattern in banned:
            if str(pattern).lower() in lower:
                return False, "banned pattern found: " + repr(pattern)
    return True, ""


class _Guard:
    def __init__(self, max_length=None, banned=None):
        self.max_length = max_length
        self.banned     = list(banned) if banned else []
    def check(self, text):
        return _validate_text(text, self.max_length, self.banned)


class _ApprovalGate:
    def __init__(self, approve_fn=None):
        self._fn = approve_fn if approve_fn is not None else (lambda a: True)
    def check(self, action):
        try:
            result = bool(self._fn(str(action)))
        except Exception:
            result = False
        return (True, "approved") if result else (False, "rejected by approval gate")


class _BudgetTracker:
    def __init__(self, max_calls=None):
        self.max_calls = max_calls
        self._count    = 0
    def ok(self):
        if self.max_calls is not None and self._count >= self.max_calls:
            return False, (
                "budget exceeded ("
                + str(self._count) + "/" + str(self.max_calls) + " calls)"
            )
        return True, ""
    def record(self): self._count += 1
    def reset(self):  self._count = 0
    @property
    def count(self): return self._count


class OpsGuardrails:
    """All three guardrail layers bundled into one ops-specific config.

    max_budget    : maximum ReAct iterations across all run() calls
    banned_inputs : list of strings blocked at the input boundary
    approve_fn    : callable(goal: str) -> bool  (default: auto-approve)

    Methods
    -------
    check_input(query)   -> (ok, reason)     — validate the goal string
    check_budget()       -> (ok, reason)     — check + record one iteration
    check_approval(goal) -> (approved, reason)
    reset()                                  — reset the iteration counter
    """

    def __init__(self, max_budget=20, banned_inputs=None, approve_fn=None):
        self._input_guard = _Guard(
            max_length=500,
            banned=list(banned_inputs) if banned_inputs else [],
        )
        self._budget = _BudgetTracker(max_calls=max_budget)
        self._gate   = _ApprovalGate(approve_fn=approve_fn)

    def check_input(self, query):
        return self._input_guard.check(str(query))

    def check_budget(self):
        ok, reason = self._budget.ok()
        if ok:
            self._budget.record()
        return ok, reason

    def check_approval(self, goal):
        return self._gate.check(str(goal))

    def reset(self):
        self._budget.reset()

    @property
    def budget_count(self):
        return self._budget.count

# ── task store ────────────────────────────────────────────────────────────────

@dataclass
class OpsTask:
    """A single unit of ops work.

    status: "pending" | "running" | "done" | "failed"
    result: output string, set when the task completes or fails
    """
    id:          str
    title:       str
    description: str  = ""
    status:      str  = "pending"
    result:      str  = ""


class TaskStore:
    """In-memory registry of OpsTask objects.

    Auto-assigns ids in the form task_001, task_002, …
    """

    def __init__(self):
        self._tasks   = {}
        self._counter = 0

    def add(self, title, description=""):
        """Create and register a new OpsTask. Returns the task."""
        self._counter += 1
        task_id = f"task_{self._counter:03d}"
        task    = OpsTask(id=task_id, title=title, description=description)
        self._tasks[task_id] = task
        return task

    def get(self, task_id):
        """Return the OpsTask with this id, or None if not found."""
        return self._tasks.get(task_id)

    def all(self):
        """Return all tasks as a list."""
        return list(self._tasks.values())

    def pending(self):
        """Return tasks whose status is 'pending'."""
        return [t for t in self._tasks.values() if t.status == "pending"]

    def update(self, task_id, status, result=""):
        """Update status (and optionally result) of a task. Returns task or None."""
        task = self._tasks.get(task_id)
        if task is not None:
            task.status = status
            if result:
                task.result = result
        return task

    def __len__(self):
        return len(self._tasks)

# ── ops tool functions ────────────────────────────────────────────────────────

def build_ops_tools(store, executor_fn=None):
    """Build the four standard ops tools backed by a TaskStore.

    Returns a dict: {"list_tasks": fn, "run_task": fn,
                     "check_status": fn, "generate_report": fn}

    executor_fn(task: OpsTask) -> str
        Injectable replacement for the actual task execution logic.
        Default: returns "Completed: <title>".
    """

    def list_tasks(status=None):
        tasks = store.all() if status is None else [
            t for t in store.all() if t.status == status
        ]
        if not tasks:
            return "No tasks found."
        return "\n".join(
            "[" + t.id + "] [" + t.status + "] " + t.title for t in tasks
        )

    def run_task(task_id):
        task = store.get(task_id)
        if task is None:
            return "Error: task " + repr(task_id) + " not found"
        if task.status not in ("pending", "failed"):
            return "Task " + task_id + " is already " + task.status
        store.update(task_id, "running")
        try:
            if executor_fn is not None:
                result = str(executor_fn(task))
            else:
                result = "Completed: " + task.title
        except Exception as exc:
            store.update(task_id, "failed", str(exc))
            return "Error running " + task_id + ": " + str(exc)
        store.update(task_id, "done", result)
        return "Task " + task_id + " done: " + result

    def check_status(task_id):
        task = store.get(task_id)
        if task is None:
            return "Error: task " + repr(task_id) + " not found"
        line = "[" + task_id + "] " + task.title + ": " + task.status
        if task.result:
            line += " — " + task.result
        return line

    def generate_report(scope="all"):
        tasks = store.all()
        if not tasks:
            return "No tasks in store."
        counts = {}
        for t in tasks:
            counts[t.status] = counts.get(t.status, 0) + 1
        summary = ", ".join(str(v) + " " + k for k, v in sorted(counts.items()))
        return (
            "Ops Report (" + str(scope) + "): "
            + str(len(tasks)) + " tasks — " + summary
        )

    return {
        "list_tasks":      list_tasks,
        "run_task":        run_task,
        "check_status":    check_status,
        "generate_report": generate_report,
    }

# ── ReAct prompt + parsing ────────────────────────────────────────────────────

def _line_value(text, prefix):
    """Return the value after prefix on the first matching line (case-insensitive)."""
    prefix_lower = prefix.lower()
    for line in str(text).splitlines():
        stripped = line.strip()
        if stripped.lower().startswith(prefix_lower):
            return stripped[len(prefix):].strip()
    return ""


def parse_ops_step(text):
    """Parse one ReAct step from LLM output.

    Returns a dict with keys:
      "thought" : str   (may be empty)
      "action"  : str or None   — tool name; None if this is a final-answer step
      "input"   : dict          — tool args; {} if not present or unparseable
      "final"   : str or None   — the final answer text; None if not a final step

    Never raises.
    """
    thought   = _line_value(text, "Thought:")
    final_ans = _line_value(text, "Final Answer:")
    if final_ans:
        return {"thought": thought, "action": None, "input": {}, "final": final_ans}
    action    = _line_value(text, "Action:")
    raw_input = _line_value(text, "Input:")
    args      = safe_parse_json(raw_input) if raw_input else {}
    if not isinstance(args, dict):
        args = {}
    return {"thought": thought, "action": action or None, "input": args, "final": None}


def format_ops_step(step, observation=""):
    """Format a parsed step + observation into a scratchpad fragment."""
    lines = []
    if step.get("thought"):
        lines.append("Thought: " + str(step["thought"]))
    if step.get("final"):
        lines.append("Final Answer: " + str(step["final"]))
    elif step.get("action"):
        lines.append("Action: " + str(step["action"]))
        lines.append("Input: " + json.dumps(step.get("input", {})))
        if observation:
            lines.append("Observation: " + str(observation))
    return "\n".join(lines) + "\n"


def build_ops_prompt(goal, tools, scratchpad=""):
    """Build the ReAct system+user prompt for one ops step."""
    tool_names = "\n".join("  - " + name for name in tools)
    system = "\n".join([
        "You are an autonomous ops agent. Complete the goal using the available tools.",
        "Available tools:",
        tool_names,
        "",
        "Reply with EXACTLY this format:",
        "Thought: <your reasoning>",
        "Action: <tool_name>",
        "Input: <json dict of args, or {}>",
        "",
        "OR if the goal is fully accomplished:",
        "Thought: <your reasoning>",
        "Final Answer: <summary of what was accomplished>",
    ])
    user = "Goal: " + str(goal)
    if scratchpad:
        user += "\n\n" + scratchpad.rstrip()
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def run_ops_step(goal, tools, scratchpad="", llm_fn=None):
    """Call the LLM for one ReAct step and parse the response.

    Returns parse_ops_step result dict.
    """
    prompt   = build_ops_prompt(goal, tools, scratchpad)
    response = call_llm(prompt, llm_fn=llm_fn)
    return parse_ops_step(response)

# ── ops agent loop ────────────────────────────────────────────────────────────

def run_ops_loop(goal, tools, llm_fn=None, guardrails=None, max_iterations=10):
    """Main ReAct loop for the ops agent.

    Each iteration:
      1. Check guardrail budget (if guardrails provided).
      2. Call run_ops_step to get the next Thought/Action or Final Answer.
      3. If Final Answer: return.
      4. Execute the named tool with the parsed args.
      5. Append step + observation to the scratchpad.

    Returns
    -------
    dict:
      "answer"     : str   — final answer or timeout message
      "trace"      : list  — one dict per iteration
      "iterations" : int   — how many iterations ran
      "stopped"    : str   — "" | "max_iterations" | "budget"
    """
    scratchpad = ""
    trace      = []

    for iteration in range(max_iterations):
        if guardrails is not None:
            ok, reason = guardrails.check_budget()
            if not ok:
                return {
                    "answer":     "Stopped: " + reason,
                    "trace":      trace,
                    "iterations": iteration,
                    "stopped":    "budget",
                }

        step = run_ops_step(goal, tools, scratchpad, llm_fn=llm_fn)

        if step.get("final"):
            step["observation"] = ""
            trace.append(step)
            return {
                "answer":     step["final"],
                "trace":      trace,
                "iterations": iteration + 1,
                "stopped":    "",
            }

        action = step.get("action") or ""
        args   = step.get("input") or {}
        if action and action in tools:
            try:
                obs = str(tools[action](**args))
            except Exception as exc:
                obs = "Error: " + str(exc)
        else:
            obs = "Error: unknown tool " + repr(action)

        step["observation"] = obs
        trace.append(step)
        scratchpad += format_ops_step(step, obs)

    return {
        "answer":     "Task incomplete after max iterations.",
        "trace":      trace,
        "iterations": max_iterations,
        "stopped":    "max_iterations",
    }

# ── ops agent ─────────────────────────────────────────────────────────────────

class OpsAgent:
    """Autonomous ops agent: ReAct loop over a TaskStore, with guardrails.

    The Section 6 capstone agent.  Wires together:
      - OpsTask / TaskStore / build_ops_tools (Days 79–83 patterns)
      - run_ops_loop with ReAct reasoning (Day 80)
      - OpsGuardrails for input + budget + approval gates (Day 87)
      - Full audit history with trace per run (Day 82 pattern)

    run(goal, executor_fn) -> record dict:
      {goal, answer, blocked, reason, trace, iterations, stopped}

    executor_fn(task: OpsTask) -> str
      Injectable task execution; default returns "Completed: <title>".
    """

    def __init__(self, store=None, guardrails=None, llm_fn=None,
                 max_iterations=10):
        self._store         = store or TaskStore()
        self._guardrails    = guardrails
        self._llm_fn        = llm_fn
        self.max_iterations = max_iterations
        self._history       = []

    def run(self, goal, executor_fn=None):
        """Run the agent on a goal. Returns a record dict."""
        # input guard
        if self._guardrails is not None:
            ok, reason = self._guardrails.check_input(goal)
            if not ok:
                record = {
                    "goal": goal, "answer": None, "blocked": True,
                    "reason": "input: " + reason, "trace": [],
                    "iterations": 0, "stopped": "input",
                }
                self._history.append(record)
                return record

            approved, reason = self._guardrails.check_approval(goal)
            if not approved:
                record = {
                    "goal": goal, "answer": None, "blocked": True,
                    "reason": "gate: " + reason, "trace": [],
                    "iterations": 0, "stopped": "gate",
                }
                self._history.append(record)
                return record

        tools  = build_ops_tools(self._store, executor_fn=executor_fn)
        result = run_ops_loop(
            goal, tools,
            llm_fn        = self._llm_fn,
            guardrails    = self._guardrails,
            max_iterations = self.max_iterations,
        )
        record = {
            "goal":       goal,
            "answer":     result["answer"],
            "blocked":    False,
            "reason":     "",
            "trace":      result["trace"],
            "iterations": result["iterations"],
            "stopped":    result["stopped"],
        }
        self._history.append(record)
        return record

    def history(self):
        """Return a copy of all run records."""
        return list(self._history)

    def clear_history(self):
        """Clear run history (does not reset budget or task store)."""
        self._history.clear()
