#!/usr/bin/env python3
"""Day 088 generator — Capstone: Ops Agent."""
import json, pathlib

ROOT  = pathlib.Path(__file__).parent.parent
DAY   = "088"
SLUG  = "ops_agent"
TITLE = "Capstone: Ops Agent"
DIR   = ROOT / "06_agents" / f"day_{DAY}"

# ══════════════════════════════════════════════════════════════════════════════
# Deliverable source fragments
# ══════════════════════════════════════════════════════════════════════════════

_FRAG_DOC = '''\
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
'''

_FRAG_IMPORTS = '''\
import json
from dataclasses import dataclass, field
'''

_FRAG_HELPERS = '''\

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
'''

_FRAG_GUARDRAILS = '''\

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
'''

_FRAG_TASKS = '''\

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
'''

_FRAG_OPS_TOOLS = '''\

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
        return "\\n".join(
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
'''

_FRAG_PROMPT = '''\

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
    return "\\n".join(lines) + "\\n"


def build_ops_prompt(goal, tools, scratchpad=""):
    """Build the ReAct system+user prompt for one ops step."""
    tool_names = "\\n".join("  - " + name for name in tools)
    system = "\\n".join([
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
        user += "\\n\\n" + scratchpad.rstrip()
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def run_ops_step(goal, tools, scratchpad="", llm_fn=None):
    """Call the LLM for one ReAct step and parse the response.

    Returns parse_ops_step result dict.
    """
    prompt   = build_ops_prompt(goal, tools, scratchpad)
    response = call_llm(prompt, llm_fn=llm_fn)
    return parse_ops_step(response)
'''

_FRAG_LOOP = '''\

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
'''

_FRAG_AGENT = '''\

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
'''

DELIVERABLE = (
    _FRAG_DOC + _FRAG_IMPORTS + _FRAG_HELPERS + _FRAG_GUARDRAILS
    + _FRAG_TASKS + _FRAG_OPS_TOOLS + _FRAG_PROMPT + _FRAG_LOOP + _FRAG_AGENT
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

# ── shared preludes ───────────────────────────────────────────────────────────

_P_BASE = """\
import json
from dataclasses import dataclass, field

def call_llm(messages, llm_fn=None):
    if llm_fn is not None:
        return str(llm_fn(messages))
    import ollama
    resp = ollama.chat(model="llama3.2", messages=messages)
    return resp["message"]["content"]

def safe_parse_json(text):
    text = str(text)
    start = text.find("{")
    end   = text.rfind("}") + 1
    if start == -1 or end == 0:
        return None
    try:
        return json.loads(text[start:end])
    except Exception:
        return None
"""

_P_TASK = """\
@dataclass
class OpsTask:
    id:          str
    title:       str
    description: str = ""
    status:      str = "pending"
    result:      str = ""

class TaskStore:
    def __init__(self):
        self._tasks = {}; self._counter = 0
    def add(self, title, description=""):
        self._counter += 1
        tid = f"task_{self._counter:03d}"
        t = OpsTask(id=tid, title=title, description=description)
        self._tasks[tid] = t; return t
    def get(self, task_id): return self._tasks.get(task_id)
    def all(self): return list(self._tasks.values())
    def pending(self): return [t for t in self._tasks.values() if t.status == "pending"]
    def update(self, task_id, status, result=""):
        t = self._tasks.get(task_id)
        if t: t.status = status
        if t and result: t.result = result
        return t
    def __len__(self): return len(self._tasks)
"""

_P_TOOLS = """\
def build_ops_tools(store, executor_fn=None):
    def list_tasks(status=None):
        tasks = store.all() if status is None else [t for t in store.all() if t.status == status]
        if not tasks: return "No tasks found."
        return "\\n".join("[" + t.id + "] [" + t.status + "] " + t.title for t in tasks)
    def run_task(task_id):
        t = store.get(task_id)
        if t is None: return "Error: task " + repr(task_id) + " not found"
        if t.status not in ("pending", "failed"): return "Task " + task_id + " is already " + t.status
        store.update(task_id, "running")
        try:
            result = str(executor_fn(t)) if executor_fn else "Completed: " + t.title
        except Exception as exc:
            store.update(task_id, "failed", str(exc)); return "Error: " + str(exc)
        store.update(task_id, "done", result)
        return "Task " + task_id + " done: " + result
    def check_status(task_id):
        t = store.get(task_id)
        if t is None: return "Error: task " + repr(task_id) + " not found"
        return "[" + task_id + "] " + t.title + ": " + t.status + (" — " + t.result if t.result else "")
    def generate_report(scope="all"):
        tasks = store.all()
        if not tasks: return "No tasks in store."
        counts = {}
        for t in tasks: counts[t.status] = counts.get(t.status, 0) + 1
        summary = ", ".join(str(v) + " " + k for k, v in sorted(counts.items()))
        return "Ops Report (" + str(scope) + "): " + str(len(tasks)) + " tasks — " + summary
    return {"list_tasks": list_tasks, "run_task": run_task,
            "check_status": check_status, "generate_report": generate_report}
"""

_P_GUARD = """\
def _validate_text(text, max_length=None, banned=None):
    text_str = str(text)
    if max_length is not None and len(text_str) > max_length:
        return False, "text exceeds max_length (" + str(len(text_str)) + " > " + str(max_length) + " chars)"
    if banned:
        lower = text_str.lower()
        for p in banned:
            if str(p).lower() in lower: return False, "banned pattern found: " + repr(p)
    return True, ""

class _Guard:
    def __init__(self, max_length=None, banned=None):
        self.max_length = max_length; self.banned = list(banned) if banned else []
    def check(self, text): return _validate_text(text, self.max_length, self.banned)

class _ApprovalGate:
    def __init__(self, approve_fn=None):
        self._fn = approve_fn if approve_fn is not None else (lambda a: True)
    def check(self, action):
        try: result = bool(self._fn(str(action)))
        except Exception: result = False
        return (True, "approved") if result else (False, "rejected by approval gate")

class _BudgetTracker:
    def __init__(self, max_calls=None):
        self.max_calls = max_calls; self._count = 0
    def ok(self):
        if self.max_calls is not None and self._count >= self.max_calls:
            return False, "budget exceeded (" + str(self._count) + "/" + str(self.max_calls) + " calls)"
        return True, ""
    def record(self): self._count += 1
    def reset(self): self._count = 0
    @property
    def count(self): return self._count

class OpsGuardrails:
    def __init__(self, max_budget=20, banned_inputs=None, approve_fn=None):
        self._input_guard = _Guard(max_length=500, banned=list(banned_inputs) if banned_inputs else [])
        self._budget = _BudgetTracker(max_calls=max_budget)
        self._gate   = _ApprovalGate(approve_fn=approve_fn)
    def check_input(self, query): return self._input_guard.check(str(query))
    def check_budget(self):
        ok, reason = self._budget.ok()
        if ok: self._budget.record()
        return ok, reason
    def check_approval(self, goal): return self._gate.check(str(goal))
    def reset(self): self._budget.reset()
    @property
    def budget_count(self): return self._budget.count
"""

_P_PROMPT = """\
def _line_value(text, prefix):
    plow = prefix.lower()
    for line in str(text).splitlines():
        s = line.strip()
        if s.lower().startswith(plow): return s[len(prefix):].strip()
    return ""

def parse_ops_step(text):
    thought = _line_value(text, "Thought:")
    final   = _line_value(text, "Final Answer:")
    if final:
        return {"thought": thought, "action": None, "input": {}, "final": final}
    action = _line_value(text, "Action:")
    raw    = _line_value(text, "Input:")
    args   = safe_parse_json(raw) if raw else {}
    if not isinstance(args, dict): args = {}
    return {"thought": thought, "action": action or None, "input": args, "final": None}

def format_ops_step(step, observation=""):
    lines = []
    if step.get("thought"): lines.append("Thought: " + str(step["thought"]))
    if step.get("final"):   lines.append("Final Answer: " + str(step["final"]))
    elif step.get("action"):
        lines.append("Action: " + str(step["action"]))
        lines.append("Input: " + json.dumps(step.get("input", {})))
        if observation: lines.append("Observation: " + str(observation))
    return "\\n".join(lines) + "\\n"

def build_ops_prompt(goal, tools, scratchpad=""):
    tool_names = "\\n".join("  - " + n for n in tools)
    system = "\\n".join([
        "You are an autonomous ops agent. Complete the goal using the available tools.",
        "Available tools:", tool_names, "",
        "Reply with EXACTLY this format:",
        "Thought: <your reasoning>", "Action: <tool_name>", "Input: <json dict or {}>", "",
        "OR if the goal is fully accomplished:",
        "Thought: <your reasoning>", "Final Answer: <summary of what was accomplished>",
    ])
    user = "Goal: " + str(goal)
    if scratchpad: user += "\\n\\n" + scratchpad.rstrip()
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]

def run_ops_step(goal, tools, scratchpad="", llm_fn=None):
    return parse_ops_step(call_llm(build_ops_prompt(goal, tools, scratchpad), llm_fn=llm_fn))
"""

_P_LOOP = """\
def run_ops_loop(goal, tools, llm_fn=None, guardrails=None, max_iterations=10):
    scratchpad = ""; trace = []
    for iteration in range(max_iterations):
        if guardrails is not None:
            ok, reason = guardrails.check_budget()
            if not ok:
                return {"answer": "Stopped: " + reason, "trace": trace,
                        "iterations": iteration, "stopped": "budget"}
        step = run_ops_step(goal, tools, scratchpad, llm_fn=llm_fn)
        if step.get("final"):
            step["observation"] = ""; trace.append(step)
            return {"answer": step["final"], "trace": trace,
                    "iterations": iteration + 1, "stopped": ""}
        action = step.get("action") or ""
        args   = step.get("input") or {}
        obs = (str(tools[action](**args)) if action and action in tools
               else "Error: unknown tool " + repr(action))
        step["observation"] = obs; trace.append(step)
        scratchpad += format_ops_step(step, obs)
    return {"answer": "Task incomplete after max iterations.", "trace": trace,
            "iterations": max_iterations, "stopped": "max_iterations"}
"""

_P_AGENT_CLASS = """\
class OpsAgent:
    def __init__(self, store=None, guardrails=None, llm_fn=None, max_iterations=10):
        self._store = store or TaskStore(); self._guardrails = guardrails
        self._llm_fn = llm_fn; self.max_iterations = max_iterations; self._history = []
    def run(self, goal, executor_fn=None):
        if self._guardrails is not None:
            ok, reason = self._guardrails.check_input(goal)
            if not ok:
                r = {"goal": goal, "answer": None, "blocked": True,
                     "reason": "input: " + reason, "trace": [], "iterations": 0, "stopped": "input"}
                self._history.append(r); return r
            approved, reason = self._guardrails.check_approval(goal)
            if not approved:
                r = {"goal": goal, "answer": None, "blocked": True,
                     "reason": "gate: " + reason, "trace": [], "iterations": 0, "stopped": "gate"}
                self._history.append(r); return r
        tools = build_ops_tools(self._store, executor_fn=executor_fn)
        result = run_ops_loop(goal, tools, llm_fn=self._llm_fn,
                              guardrails=self._guardrails, max_iterations=self.max_iterations)
        r = {"goal": goal, "answer": result["answer"], "blocked": False, "reason": "",
             "trace": result["trace"], "iterations": result["iterations"], "stopped": result["stopped"]}
        self._history.append(r); return r
    def history(self): return list(self._history)
    def clear_history(self): self._history.clear()
"""

# ══════════════════════════════════════════════════════════════════════════════
# Exercise notebooks
# ══════════════════════════════════════════════════════════════════════════════

_ALL_P = _P_BASE + _P_TASK + _P_TOOLS + _P_GUARD + _P_PROMPT + _P_LOOP

_EX1 = _nb([
    _md("# Exercise 1 — OpsTask and TaskStore\n\n"
        "`OpsTask` is a simple dataclass representing one unit of operational "
        "work.  `TaskStore` is an in-memory registry that assigns auto-ids, "
        "tracks status transitions, and supports filtering by status."),
    _code(_P_BASE + """\

# ── Exercise: implement OpsTask and TaskStore ─────────────────────────────────

@dataclass
class OpsTask:
    \"\"\"A single unit of ops work.  status: pending/running/done/failed.\"\"\"
    id:          str
    title:       str
    description: str = ""
    status:      str = "pending"
    result:      str = ""


class TaskStore:
    \"\"\"In-memory registry of OpsTask objects with auto-incrementing ids.\"\"\"

    def __init__(self):
        self._tasks   = {}
        self._counter = 0

    def add(self, title, description=""):
        # TODO: increment counter, create id "task_001" etc., create OpsTask,
        # store in self._tasks, return the task
        return OpsTask(id="task_001", title=title, description=description)

    def get(self, task_id):
        # TODO: return self._tasks.get(task_id)
        return None

    def all(self):
        # TODO: return list(self._tasks.values())
        return []

    def pending(self):
        # TODO: return tasks where status == "pending"
        return []

    def update(self, task_id, status, result=""):
        # TODO: look up task, set status (and result if non-empty), return task or None
        return None

    def __len__(self):
        # TODO: return number of tasks
        return 0
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — OpsTask constructs with defaults
try:
    t = OpsTask(id="t1", title="Check disk")
    assert t.status == "pending" and t.result == "" and t.description == ""
    checks += 1; print("✅ 1 OpsTask constructs with correct defaults")
except Exception as e:
    print("❌ 1:", e)

# 2 — TaskStore.add returns OpsTask with auto id
try:
    store = TaskStore()
    t1 = store.add("Lint check")
    t2 = store.add("Test run", "run pytest")
    assert t1.id == "task_001" and t2.id == "task_002"
    assert t1.title == "Lint check" and t2.description == "run pytest"
    checks += 1; print("✅ 2 TaskStore.add assigns auto ids correctly")
except Exception as e:
    print("❌ 2:", e)

# 3 — TaskStore.get retrieves by id
try:
    store = TaskStore()
    t = store.add("Check logs")
    assert store.get(t.id) is t
    assert store.get("task_999") is None
    checks += 1; print("✅ 3 TaskStore.get retrieves task by id")
except Exception as e:
    print("❌ 3:", e)

# 4 — TaskStore.pending returns only pending tasks
try:
    store = TaskStore()
    t1 = store.add("Task A")
    t2 = store.add("Task B")
    store.update(t1.id, "done")
    pending = store.pending()
    assert len(pending) == 1 and pending[0].id == t2.id
    checks += 1; print("✅ 4 TaskStore.pending returns only pending tasks")
except Exception as e:
    print("❌ 4:", e)

# 5 — TaskStore.update changes status and result
try:
    store = TaskStore()
    t = store.add("Deploy")
    store.update(t.id, "done", "Deployed v1.2")
    assert t.status == "done" and t.result == "Deployed v1.2"
    assert len(store) == 1
    checks += 1; print("✅ 5 TaskStore.update changes status and result; __len__ works")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX2 = _nb([
    _md("# Exercise 2 — OpsTools\n\n"
        "`build_ops_tools` returns a dict of four callable tools backed by a "
        "`TaskStore`.  The `executor_fn` is injectable — it replaces the real "
        "task execution logic so tests can run without any external system."),
    _code(_P_BASE + _P_TASK + """\

# ── Exercise: implement build_ops_tools ──────────────────────────────────────

def build_ops_tools(store, executor_fn=None):
    \"\"\"Build the four standard ops tools backed by a TaskStore.

    Returns {"list_tasks": fn, "run_task": fn,
             "check_status": fn, "generate_report": fn}
    \"\"\"

    def list_tasks(status=None):
        # TODO: if status given, filter store.all(); otherwise return all.
        # Format each task as "[task_001] [pending] Title"
        # Return "No tasks found." if empty.
        return "No tasks found."

    def run_task(task_id):
        # TODO: get task; error if not found.
        # If status not in ("pending","failed"), return already-status message.
        # update to "running"; call executor_fn(task) or "Completed: <title>".
        # update to "done" with result; return "Task <id> done: <result>".
        # On exception: update to "failed" and return error.
        return "Not implemented"

    def check_status(task_id):
        # TODO: return "[task_id] title: status — result" (omit result if empty)
        return "Not implemented"

    def generate_report(scope="all"):
        # TODO: count tasks per status; return
        # "Ops Report (<scope>): <n> tasks — <k done, m pending, ...>"
        return "No tasks in store."

    return {
        "list_tasks":      list_tasks,
        "run_task":        run_task,
        "check_status":    check_status,
        "generate_report": generate_report,
    }
"""),
    _md("### Checks"),
    _code("""\
checks = 0
_exec = lambda t: "Simulated: " + t.title

# 1 — build_ops_tools returns dict with 4 keys
try:
    store = TaskStore()
    tools = build_ops_tools(store, executor_fn=_exec)
    assert set(tools.keys()) == {"list_tasks", "run_task", "check_status", "generate_report"}
    checks += 1; print("✅ 1 build_ops_tools returns dict with correct keys")
except Exception as e:
    print("❌ 1:", e)

# 2 — list_tasks shows all tasks
try:
    store = TaskStore()
    store.add("Task A"); store.add("Task B")
    tools = build_ops_tools(store)
    listing = tools["list_tasks"]()
    assert "Task A" in listing and "Task B" in listing
    checks += 1; print("✅ 2 list_tasks shows all tasks")
except Exception as e:
    print("❌ 2:", e)

# 3 — run_task marks task done and returns result
try:
    store = TaskStore()
    t = store.add("Lint check")
    tools = build_ops_tools(store, executor_fn=_exec)
    msg = tools["run_task"](t.id)
    assert "done" in msg.lower() or t.id in msg
    assert t.status == "done" and "Lint check" in t.result
    checks += 1; print("✅ 3 run_task marks task done with result")
except Exception as e:
    print("❌ 3:", e)

# 4 — check_status returns task status string
try:
    store = TaskStore()
    t = store.add("Deploy"); store.update(t.id, "done", "v2.0 deployed")
    tools = build_ops_tools(store)
    status = tools["check_status"](t.id)
    assert "done" in status.lower() and t.id in status
    checks += 1; print("✅ 4 check_status returns task status")
except Exception as e:
    print("❌ 4:", e)

# 5 — generate_report summarises the store
try:
    store = TaskStore()
    t1 = store.add("A"); t2 = store.add("B"); t3 = store.add("C")
    store.update(t1.id, "done", "ok"); store.update(t2.id, "done", "ok")
    tools = build_ops_tools(store)
    report = tools["generate_report"]()
    assert "3" in report or "three" in report.lower() or "2 done" in report or "done" in report
    assert "pending" in report.lower() or "1 pending" in report
    checks += 1; print("✅ 5 generate_report includes task counts by status")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX3 = _nb([
    _md("# Exercise 3 — parse_ops_step and run_ops_step\n\n"
        "`parse_ops_step` reads one ReAct turn from the LLM's raw text and "
        "returns a structured dict.  It handles two cases: an action step "
        "(Thought/Action/Input) and a final-answer step (Thought/Final Answer).  "
        "`run_ops_step` calls the LLM once and passes the result to the parser."),
    _code(_P_BASE + _P_TASK + _P_TOOLS + """\

# ── Exercise: implement parse_ops_step, format_ops_step, run_ops_step ─────────

def _line_value(text, prefix):
    \"\"\"Return the value after prefix on the first matching line (case-insensitive).\"\"\"
    prefix_lower = prefix.lower()
    for line in str(text).splitlines():
        stripped = line.strip()
        if stripped.lower().startswith(prefix_lower):
            return stripped[len(prefix):].strip()
    return ""


def parse_ops_step(text):
    \"\"\"Parse one ReAct step.

    Returns {"thought": str, "action": str|None, "input": dict, "final": str|None}.
    Never raises.
    \"\"\"
    # TODO:
    # 1. thought = _line_value(text, "Thought:")
    # 2. final   = _line_value(text, "Final Answer:")
    # 3. If final is non-empty: return {thought, action=None, input={}, final}
    # 4. action  = _line_value(text, "Action:")
    # 5. raw_input = _line_value(text, "Input:")
    # 6. args = safe_parse_json(raw_input) if raw_input else {}; if not dict: {}
    # 7. return {thought, action=action or None, input=args, final=None}
    return {"thought": "", "action": None, "input": {}, "final": None}


def format_ops_step(step, observation=""):
    \"\"\"Format a parsed step + observation into a scratchpad string.\"\"\"
    # TODO: build lines list:
    # - if step["thought"]: append "Thought: " + thought
    # - if step["final"]:   append "Final Answer: " + final
    # - elif step["action"]: append "Action: " + action, "Input: " + json.dumps(input)
    #   if observation: append "Observation: " + observation
    # return "\\n".join(lines) + "\\n"
    return ""


def build_ops_prompt(goal, tools, scratchpad=""):
    tool_names = "\\n".join("  - " + n for n in tools)
    system = "\\n".join([
        "You are an autonomous ops agent. Complete the goal using the available tools.",
        "Available tools:", tool_names, "",
        "Thought: <reasoning>  Action: <tool>  Input: <json>",
        "OR  Thought: <reasoning>  Final Answer: <summary>",
    ])
    user = "Goal: " + str(goal)
    if scratchpad: user += "\\n\\n" + scratchpad.rstrip()
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def run_ops_step(goal, tools, scratchpad="", llm_fn=None):
    \"\"\"Call LLM once and parse the response into a step dict.\"\"\"
    # TODO: call call_llm(build_ops_prompt(goal, tools, scratchpad), llm_fn=llm_fn)
    # then return parse_ops_step(response)
    return {"thought": "", "action": None, "input": {}, "final": None}
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — parse_ops_step parses an action step correctly
try:
    text = 'Thought: I should list tasks\\nAction: list_tasks\\nInput: {"status": "pending"}'
    step = parse_ops_step(text)
    assert step["action"] == "list_tasks"
    assert step["input"] == {"status": "pending"}
    assert step["final"] is None
    assert "list tasks" in step["thought"].lower()
    checks += 1; print("✅ 1 parse_ops_step parses action step correctly")
except Exception as e:
    print("❌ 1:", e)

# 2 — parse_ops_step parses a final-answer step correctly
try:
    text = "Thought: All done\\nFinal Answer: All tasks completed successfully."
    step = parse_ops_step(text)
    assert step["final"] == "All tasks completed successfully."
    assert step["action"] is None
    assert step["input"] == {}
    checks += 1; print("✅ 2 parse_ops_step parses final-answer step correctly")
except Exception as e:
    print("❌ 2:", e)

# 3 — parse_ops_step never raises on garbage input
try:
    for bad in ["", "random text", "Action: only", '{"json": "object"}']:
        result = parse_ops_step(bad)
        assert isinstance(result, dict)
        assert "action" in result and "final" in result
    checks += 1; print("✅ 3 parse_ops_step never raises on garbage input")
except Exception as e:
    print("❌ 3:", e)

# 4 — run_ops_step calls llm_fn and parses the result
try:
    mock_llm = lambda m: "Thought: checking\\nAction: generate_report\\nInput: {}"
    store = TaskStore(); store.add("T1")
    tools = build_ops_tools(store)
    step = run_ops_step("generate report", tools, llm_fn=mock_llm)
    assert step["action"] == "generate_report"
    assert step["final"] is None
    checks += 1; print("✅ 4 run_ops_step calls llm_fn and parses result")
except Exception as e:
    print("❌ 4:", e)

# 5 — format_ops_step produces a scratchpad fragment
try:
    step = {"thought": "I'll list tasks", "action": "list_tasks", "input": {}, "final": None}
    fragment = format_ops_step(step, observation="task_001 pending Task A")
    assert "Thought:" in fragment and "Action: list_tasks" in fragment
    assert "Observation:" in fragment
    checks += 1; print("✅ 5 format_ops_step produces readable scratchpad fragment")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX4 = _nb([
    _md("# Exercise 4 — OpsGuardrails\n\n"
        "`OpsGuardrails` is the Day-87 guardrail trio — Guard, BudgetTracker, "
        "ApprovalGate — bundled into a single ops-specific config object.  "
        "`check_budget()` both checks *and* records in one call, so the loop "
        "only needs to call it once per iteration."),
    _code(_P_BASE + _P_GUARD[:_P_GUARD.index("class OpsGuardrails")] + """\

# ── Exercise: implement OpsGuardrails ────────────────────────────────────────

class OpsGuardrails:
    \"\"\"Three guardrail layers bundled for the OpsAgent.

    max_budget    : max ReAct iterations across all run() calls
    banned_inputs : list of strings blocked at the input boundary
    approve_fn    : callable(goal: str) -> bool  (default: auto-approve)
    \"\"\"

    def __init__(self, max_budget=20, banned_inputs=None, approve_fn=None):
        # TODO: build self._input_guard = _Guard(max_length=500, banned=...)
        # self._budget = _BudgetTracker(max_calls=max_budget)
        # self._gate   = _ApprovalGate(approve_fn=approve_fn)
        pass

    def check_input(self, query):
        # TODO: return self._input_guard.check(str(query))
        return True, ""

    def check_budget(self):
        # TODO: call self._budget.ok(); if ok record and return (True, "")
        # if not ok return (False, reason) WITHOUT recording
        return True, ""

    def check_approval(self, goal):
        # TODO: return self._gate.check(str(goal))
        return True, "approved"

    def reset(self):
        # TODO: self._budget.reset()
        pass

    @property
    def budget_count(self):
        # TODO: return self._budget.count
        return 0
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — OpsGuardrails constructs; default auto-approves everything
try:
    g = OpsGuardrails(max_budget=10)
    ok, _ = g.check_input("Run all checks")
    assert ok
    approved, _ = g.check_approval("any goal")
    assert approved
    checks += 1; print("✅ 1 OpsGuardrails constructs and auto-approves by default")
except Exception as e:
    print("❌ 1:", e)

# 2 — check_input blocks a banned pattern
try:
    g = OpsGuardrails(banned_inputs=["rm -rf", "drop table"])
    ok, reason = g.check_input("please rm -rf /")
    assert not ok and "rm -rf" in reason.lower()
    ok2, _ = g.check_input("safe query")
    assert ok2
    checks += 1; print("✅ 2 check_input blocks banned patterns")
except Exception as e:
    print("❌ 2:", e)

# 3 — check_budget allows calls under the limit and records
try:
    g = OpsGuardrails(max_budget=3)
    ok1, _ = g.check_budget(); assert ok1 and g.budget_count == 1
    ok2, _ = g.check_budget(); assert ok2 and g.budget_count == 2
    ok3, _ = g.check_budget(); assert ok3 and g.budget_count == 3
    checks += 1; print("✅ 3 check_budget allows calls and increments count")
except Exception as e:
    print("❌ 3:", e)

# 4 — check_budget blocks when limit reached
try:
    g = OpsGuardrails(max_budget=2)
    g.check_budget(); g.check_budget()  # use up budget
    ok, reason = g.check_budget()
    assert not ok and ("budget" in reason.lower() or "exceeded" in reason.lower())
    assert g.budget_count == 2   # count did NOT increment on the blocked call
    checks += 1; print("✅ 4 check_budget blocks at limit; count not incremented on block")
except Exception as e:
    print("❌ 4:", e)

# 5 — check_approval blocks when approve_fn returns False; reset works
try:
    g = OpsGuardrails(max_budget=5, approve_fn=lambda goal: False)
    approved, reason = g.check_approval("any goal")
    assert not approved
    g.reset(); assert g.budget_count == 0
    checks += 1; print("✅ 5 check_approval blocks with reject fn; reset() clears count")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX5 = _nb([
    _md("# Exercise 5 — OpsAgent\n\n"
        "`OpsAgent` is the capstone class.  It wires together the `TaskStore`, "
        "`build_ops_tools`, `run_ops_loop`, and `OpsGuardrails` into one "
        "object with a simple `run(goal)` interface.  Every run — including "
        "blocked ones — is recorded in history for auditing."),
    _code(_ALL_P + """\

# ── Exercise: implement OpsAgent ─────────────────────────────────────────────

class OpsAgent:
    \"\"\"Autonomous ops agent with guardrails and full audit history.\"\"\"

    def __init__(self, store=None, guardrails=None, llm_fn=None,
                 max_iterations=10):
        # TODO: store all args; self._history = []
        self._store = store or TaskStore()
        self._guardrails = guardrails
        self._llm_fn = llm_fn
        self.max_iterations = max_iterations
        self._history = []

    def run(self, goal, executor_fn=None):
        \"\"\"Run the agent on a goal.

        Returns a record dict:
          {goal, answer, blocked, reason, trace, iterations, stopped}
        \"\"\"
        # TODO:
        # 1. If guardrails: check_input(goal) → if not ok, return blocked record
        #    check_approval(goal) → if not approved, return blocked record
        # 2. tools = build_ops_tools(self._store, executor_fn=executor_fn)
        # 3. result = run_ops_loop(goal, tools, llm_fn=self._llm_fn,
        #             guardrails=self._guardrails, max_iterations=self.max_iterations)
        # 4. Build record dict, append to self._history, return it
        return {"goal": goal, "answer": None, "blocked": False, "reason": "",
                "trace": [], "iterations": 0, "stopped": ""}

    def history(self):
        # TODO: return list(self._history)
        return []

    def clear_history(self):
        # TODO: self._history.clear()
        pass
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# Mock that immediately gives a final answer
_final_llm = lambda m: "Thought: done\\nFinal Answer: All tasks processed."
_exec       = lambda t: "Simulated: " + t.title

# 1 — OpsAgent constructs and has expected attributes
try:
    agent = OpsAgent(llm_fn=_final_llm)
    assert hasattr(agent, "max_iterations") and hasattr(agent, "_store")
    checks += 1; print("✅ 1 OpsAgent constructs correctly")
except Exception as e:
    print("❌ 1:", e)

# 2 — run() executes a goal and returns a valid record
try:
    store = TaskStore(); store.add("Lint check"); store.add("Tests")
    agent = OpsAgent(store=store, llm_fn=_final_llm)
    r = agent.run("Run all tasks", executor_fn=_exec)
    assert r["answer"] == "All tasks processed."
    assert not r["blocked"] and r["goal"] == "Run all tasks"
    assert isinstance(r["trace"], list)
    checks += 1; print("✅ 2 run() executes goal and returns valid record")
except Exception as e:
    print("❌ 2:", e)

# 3 — guardrail blocks bad input; blocked record in history
try:
    g = OpsGuardrails(banned_inputs=["rm -rf"])
    agent = OpsAgent(guardrails=g, llm_fn=_final_llm)
    r = agent.run("please rm -rf /")
    assert r["blocked"] and "input" in r["reason"]
    assert r["answer"] is None
    checks += 1; print("✅ 3 guardrail blocks bad input; record stored in history")
except Exception as e:
    print("❌ 3:", e)

# 4 — run_ops_loop stops at max_iterations
try:
    never_done = lambda m: "Thought: still working\\nAction: list_tasks\\nInput: {}"
    store = TaskStore(); store.add("Task")
    agent = OpsAgent(store=store, llm_fn=never_done, max_iterations=3)
    r = agent.run("impossible goal", executor_fn=_exec)
    assert r["stopped"] == "max_iterations" and r["iterations"] == 3
    checks += 1; print("✅ 4 run_ops_loop stops at max_iterations")
except Exception as e:
    print("❌ 4:", e)

# 5 — history() grows with each run
try:
    agent = OpsAgent(llm_fn=_final_llm)
    agent.run("goal 1"); agent.run("goal 2"); agent.run("goal 3")
    assert len(agent.history()) == 3
    checks += 1; print("✅ 5 history() grows with each run()")
except Exception as e:
    print("❌ 5:", e)

# 6 — clear_history() empties history
try:
    agent = OpsAgent(llm_fn=_final_llm)
    agent.run("something")
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
day: "088"
lesson: 1
title: "What Is an Ops Agent?"
slides:
  - type: title
    heading: "Capstone: Ops Agent"
    subheading: "Section 6 in one coherent system"
    narration: >
      This is the capstone day for Section 6. You have built eight agents in
      the last nine days. Today you wire them into one coherent system: an
      autonomous operations agent that reasons, acts, enforces guardrails, and
      produces a full audit trail. An ops agent is a practical pattern that
      appears in real engineering: CI/CD orchestrators, incident responders,
      deployment pipelines, and monitoring systems all follow the same shape.

  - type: concept
    label: "What ops agents do"
    heading: "Operations as an Agent Problem"
    body: >
      Ops agents manage a queue of tasks across a system lifecycle.
    bullets:
      - "Tasks: discrete units of work with status (pending/running/done/failed)"
      - "Tools: list, run, check, report — the four basic ops verbs"
      - "Reasoning: decide which task to run next based on current state"
      - "Safety: guardrails prevent runaway execution or harmful commands"
      - "Audit: every action logged for post-hoc review"
    narration: >
      The ops pattern is everywhere once you see it. A deployment agent asks:
      which services are pending? Runs them. Checks status. Reports. An incident
      agent asks: which alerts are unacknowledged? Runs diagnostics. Generates a
      summary. A code review agent asks: which files need linting? Runs the linter.
      Reports results. Same four verbs. Same ReAct loop.

  - type: concept
    label: "Section 6 synthesis"
    heading: "What This Day Pulls Together"
    body: >
      Every Section 6 day appears in the ops agent.
    bullets:
      - "Day 79/80: agent loop + ReAct (Thought/Action/Observation)"
      - "Day 81: tool registry and execution"
      - "Day 82: TaskStore as persistent task memory"
      - "Day 83: goals decomposed into tasks"
      - "Day 84: orchestrator orchestrates tool agents"
      - "Day 87: OpsGuardrails (input + budget + approval)"
    narration: >
      Days 85 and 86 — MCP and retrieval agents — are specialisations that
      could be wired in as additional tools. The capstone doesn't include every
      pattern from the section; it includes the ones that form the backbone of
      an operational system. MCP would be how you expose the ops agent to
      external clients; retrieval would be how it answers questions about its
      own history.

  - type: concept
    label: "Anatomy"
    heading: "The Four Components"
    body: >
      OpsAgent = TaskStore + OpsTools + run_ops_loop + OpsGuardrails
    bullets:
      - "TaskStore: the source of truth for what needs to be done"
      - "OpsTools: the four functions the agent can call"
      - "run_ops_loop: the ReAct loop that reasons and acts"
      - "OpsGuardrails: the safety layer that wraps the loop"
      - "OpsAgent: one class that wires all four together"
    narration: >
      Each component is independently testable. You can unit-test TaskStore
      without the agent. You can test each tool function without the loop. You
      can test the loop with a mock LLM without the guardrails. And you can test
      OpsAgent end-to-end by injecting mocks for all four. This layered
      testability is the key engineering property of the design.

  - type: summary
    heading: "What You Will Build"
    bullets:
      - "OpsTask + TaskStore: the unit of work and its registry"
      - "build_ops_tools: four injectable tool functions"
      - "parse_ops_step + run_ops_loop: the ReAct reasoning machinery"
      - "OpsGuardrails: input + budget + approval gates"
      - "OpsAgent: the capstone class wiring all four components"
""",

    """\
day: "088"
lesson: 2
title: "Task Management — OpsTask and TaskStore"
slides:
  - type: title
    heading: "Task Management"
    subheading: "OpsTask, TaskStore, and OpsTools"
    narration: >
      Before the agent can reason about work, it needs a model of work.
      OpsTask is a simple dataclass with four status values. TaskStore manages
      a dict of tasks and exposes five operations. build_ops_tools wraps the
      store in four callable tool functions that the LLM can select and invoke.

  - type: concept
    label: "OpsTask"
    heading: "The Unit of Work"
    body: >
      Four fields define everything the agent knows about a task.
    bullets:
      - "id: auto-assigned string (task_001, task_002, ...)"
      - "title: human-readable name"
      - "description: optional context"
      - "status: pending | running | done | failed"
      - "result: output string, empty until the task completes"
    narration: >
      The status machine is linear: pending → running → done or failed. The
      agent drives these transitions by calling run_task. It checks them by
      calling check_status. The status is what the agent reasons about when
      deciding what to do next. A task in 'failed' state can be retried;
      a task in 'done' state is skipped.

  - type: concept
    label: "TaskStore"
    heading: "The Task Registry"
    body: >
      TaskStore is a simple dict wrapper with five operations.
    bullets:
      - "add(title, description) -> OpsTask: creates and registers a task"
      - "get(task_id) -> OpsTask or None"
      - "all() -> list[OpsTask]"
      - "pending() -> list[OpsTask]: only status=='pending'"
      - "update(task_id, status, result) -> OpsTask"
    narration: >
      The TaskStore is deliberately simple. In a production system you would
      replace it with a database (SQLite as in Day 82, or Postgres). But for
      learning the agent pattern, an in-memory dict is enough. The interface
      is the same either way: the tools call the same five methods regardless
      of what backs the store.

  - type: code
    label: "OpsTools"
    heading: "Four Tool Functions"
    body: >
      build_ops_tools returns a dict the agent's loop can dispatch into.
    code: |
      store = TaskStore()
      store.add("Run linter")
      store.add("Run tests")
      store.add("Generate report")

      executor = lambda task: f"Ran {task.title}: OK"
      tools = build_ops_tools(store, executor_fn=executor)

      print(tools["list_tasks"]())
      # [task_001] [pending] Run linter
      # [task_002] [pending] Run tests
      # [task_003] [pending] Generate report

      print(tools["run_task"]("task_001"))
      # Task task_001 done: Ran Run linter: OK

      print(tools["generate_report"]())
      # Ops Report (all): 3 tasks — 1 done, 2 pending
    narration: >
      The executor_fn is the injection point for the actual work. In tests we
      inject a lambda. In production you would inject a function that actually
      runs the command, calls the CI API, or executes the script. The tool
      functions themselves never need to change — only the executor.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "OpsTask: id/title/description/status/result dataclass"
      - "TaskStore: dict-backed registry with add/get/all/pending/update"
      - "build_ops_tools: four tool fns (list, run, check, report)"
      - "executor_fn: injectable — separates what to run from how to run it"
      - "The store is the agent's working memory for this session"
""",

    """\
day: "088"
lesson: 3
title: "The Ops Reasoning Loop"
slides:
  - type: title
    heading: "The Ops Reasoning Loop"
    subheading: "parse_ops_step, format_ops_step, run_ops_loop"
    narration: >
      The reasoning loop is the heart of the ops agent. It follows the ReAct
      pattern from Day 80: Thought, Action, Observation, repeat. Each iteration
      calls the LLM once, parses the response, executes the named tool, and
      appends the result to a growing scratchpad that feeds back into the next
      prompt. The loop stops when the LLM emits a Final Answer.

  - type: concept
    label: "parse_ops_step"
    heading: "Two Output Formats"
    body: >
      The LLM can respond in one of two ways per turn.
    bullets:
      - "Action step: Thought / Action / Input (JSON args)"
      - "Final answer step: Thought / Final Answer"
      - "parse_ops_step detects which format by checking for 'Final Answer:'"
      - "Never raises: returns safe defaults on parse failure"
      - "Unknown action -> 'Error: unknown tool' in the observation"
    narration: >
      The two-format design is intentional. The agent must explicitly commit to
      a final answer — it cannot accidentally stop in the middle. If the LLM
      output is unparseable, parse_ops_step returns a step with action=None and
      final=None. The loop treats this as an unknown tool and records an error
      observation, then tries again on the next iteration.

  - type: code
    label: "Loop trace"
    heading: "Three Iterations to Completion"
    body: >
      A typical three-step ops run.
    code: |
      # Iteration 0: list tasks
      Thought: First I'll see what needs doing
      Action: list_tasks
      Input: {}
      Observation: [task_001] [pending] Run tests
                   [task_002] [pending] Generate report

      # Iteration 1: run the first task
      Thought: I'll run the tests
      Action: run_task
      Input: {"task_id": "task_001"}
      Observation: Task task_001 done: All 42 tests passed

      # Iteration 2: final answer
      Thought: Tests passed; report was already done
      Final Answer: Ran all pending tasks. Tests: 42 passed.
    narration: >
      Notice that the scratchpad grows from iteration to iteration. By iteration
      2, the LLM has seen the full history of what it did and can synthesise a
      meaningful final answer. The scratchpad is the agent's short-term working
      memory — it exists only for the duration of this run() call.

  - type: concept
    label: "Budget integration"
    heading: "Budget as Loop Control"
    body: >
      The OpsGuardrails budget is checked at the top of each iteration.
    bullets:
      - "Every iteration = one LLM call = one budget unit"
      - "check_budget() is called before run_ops_step, not after"
      - "If budget exhausted: return {'stopped': 'budget'} immediately"
      - "The budget persists across run() calls — shared session limit"
      - "reset() starts a new session without recreating the agent"
    narration: >
      Budget-as-loop-control is cleaner than a timeout. Timeouts are
      non-deterministic: the same agent can hit or miss a timeout depending on
      LLM latency. A budget is deterministic: exactly N iterations, every time.
      This makes the agent's behaviour reproducible and auditable.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "parse_ops_step: two formats — action or final answer"
      - "format_ops_step: appends thought + action + observation to scratchpad"
      - "run_ops_loop: budget check → step → execute → repeat"
      - "Scratchpad grows per iteration — the agent's short-term memory"
      - "Final Answer is the only way to exit normally; budget exits early"
""",

    """\
day: "088"
lesson: 4
title: "OpsGuardrails — Controlling the Agent"
slides:
  - type: title
    heading: "OpsGuardrails"
    subheading: "Three guardrail layers for the ops agent"
    narration: >
      Ops agents are especially dangerous without guardrails because they take
      real actions: running commands, changing state, generating reports that
      might be acted on. Day 87's three layers — input guard, budget tracker,
      approval gate — are bundled into OpsGuardrails, which is the single object
      passed to OpsAgent at construction time.

  - type: concept
    label: "Three layers"
    heading: "What Each Layer Protects Against"
    body: >
      Each layer catches a different category of misuse.
    bullets:
      - "Input guard: blocks injection attacks and malformed goals"
      - "Budget: caps the total iterations across all run() calls"
      - "Approval gate: pauses for human confirmation before running"
      - "All three are injectable — testing uses mocks, production uses real logic"
      - "check_budget() both checks AND records in one atomic call"
    narration: >
      The atomic check-and-record design of check_budget() prevents a race
      condition: if you called ok() and record() separately, two threads could
      both pass the ok() check and both record, exceeding the budget. Calling
      check_budget() as one unit avoids this — the increment only happens if the
      check passed.

  - type: code
    label: "OpsGuardrails usage"
    heading: "Configuring a Production Guardrail"
    body: >
      One object, three layers of protection.
    code: |
      guardrails = OpsGuardrails(
          max_budget    = 50,
          banned_inputs = ["rm -rf", "drop table", "shutdown"],
          approve_fn    = lambda goal: True,   # auto-approve for testing
      )

      # In a CLI app: ask the operator
      def cli_approve(goal):
          print(f"Agent wants to: {goal}")
          return input("Proceed? (y/n) ").strip().lower() == "y"
      guardrails = OpsGuardrails(approve_fn=cli_approve)

      # Check input before the loop
      ok, reason = guardrails.check_input("Run all pending tasks")
      # Check + record once per iteration
      ok, reason = guardrails.check_budget()
      # Reset between sessions
      guardrails.reset()
    narration: >
      The approve_fn in production would do something meaningful: prompt a
      human operator, check a feature flag, verify that the deployment window
      is open, or consult a policy engine. The interface doesn't care — it just
      calls approve_fn and acts on the boolean result.

  - type: concept
    label: "Audit through history"
    heading: "Every Blocked Call Is in History"
    body: >
      OpsAgent records blocked runs just like successful ones.
    bullets:
      - "Blocked record: {goal, answer=None, blocked=True, reason, trace=[], ...}"
      - "reason prefix: 'input: ...' or 'gate: ...' (matched to the blocking layer)"
      - "Budget-stopped runs: blocked=False but stopped='budget'"
      - "Iterate history() to build an audit report of all goals attempted"
      - "Never delete history during a session — it is the audit log"
    narration: >
      The distinction between blocked=True and stopped='budget' is deliberate.
      A blocked run never reached the agent. A budget-stopped run got some work
      done but didn't finish. An operator reviewing history can see both and
      react appropriately: resubmit the blocked goal with a corrected phrasing,
      or reset the budget and rerun the budget-stopped goal.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "OpsGuardrails bundles input guard + budget + approval gate"
      - "check_budget(): atomic check-and-record prevents over-counting"
      - "All three approve_fn patterns: auto, CLI, conditional"
      - "Blocked runs (input/gate) vs stopped runs (budget) are distinct"
      - "History is the audit log — never discard it mid-session"
""",

    """\
day: "088"
lesson: 5
title: "The Full OpsAgent — Section 6 in Review"
slides:
  - type: title
    heading: "The Full OpsAgent"
    subheading: "Section 6 complete"
    narration: >
      You have now built ten agents across ten days. The OpsAgent is the
      synthesis: a system that can autonomously manage a queue of operational
      tasks, reason about what to do next, execute tools safely, enforce
      guardrails, and produce a full audit trail. This lesson reviews what you
      built across the section and previews what comes next.

  - type: concept
    label: "OpsAgent"
    heading: "One Class, All the Pieces"
    body: >
      OpsAgent.run() is a four-stage pipeline before any loop starts.
    bullets:
      - "Stage 1: check_input(goal) — block injection at the door"
      - "Stage 2: check_approval(goal) — human confirmation if needed"
      - "Stage 3: build_ops_tools(store) — assemble tool functions"
      - "Stage 4: run_ops_loop(...) — the ReAct loop with budget"
      - "All four stages wrapped in one try/append/return pattern"
    narration: >
      The structure of run() mirrors the safe_ask() pipeline from Day 87, with
      two differences. First, the output guard is omitted — ops agents return
      internal state (task results), not user-facing text that needs filtering.
      Second, the loop itself is the budget boundary, so there is no separate
      budget check at the run() level — it happens inside run_ops_loop.

  - type: concept
    label: "Section 6 review"
    heading: "Ten Agents, Ten Patterns"
    body: >
      Each day introduced one transferable pattern.
    bullets:
      - "Day 79: tool registry + action parsing (never raises)"
      - "Day 80: ReAct loop + scratchpad as working memory"
      - "Day 81: tool schemas + validation before execution"
      - "Day 82: short-term (session) + long-term (SQLite) memory"
      - "Day 83: Kahn topological sort for task dependencies"
      - "Day 84: specialist agents + Handoff audit records"
      - "Day 85: MCP — open standard for agent-tool connections"
      - "Day 86: agentic RAG — decide when and what to retrieve"
      - "Day 87: four-layer guardrail pipeline (validate_text / Guard / gate / budget)"
      - "Day 88: capstone — compose all patterns into a deployable system"
    narration: >
      These ten patterns cover most of what you will encounter in real agent
      engineering. The specific class names will differ — every framework has
      its own vocabulary — but the underlying ideas are stable. A ReAct loop
      is a ReAct loop whether you build it in LangChain, LlamaIndex, or raw
      Python. A guardrail is a guardrail whether you call it a filter, a policy,
      or a fence.

  - type: concept
    label: "What comes next"
    heading: "Section 7 — Finance, Trading & Productizing"
    body: >
      Days 89–100 take these skills to a new domain.
    bullets:
      - "Days 89–94: financial data, analysis, backtesting, AI signals"
      - "Days 95–96: building a paper-trading bot"
      - "Days 97–100: productizing, launching, portfolio, final capstone"
      - "The agent patterns from Section 6 reappear as trading agents"
      - "The web app skills from Section 4 reappear as the trading dashboard"
    narration: >
      Section 7 is not a fresh start. It is the same skills applied to a new
      domain with higher stakes. A trading agent is an ops agent that manages
      a portfolio of positions instead of a queue of tasks. An AI signal
      generator is a retrieval agent over news data. The patterns are the same;
      the domain is different.

  - type: summary
    heading: "Section 6 Complete"
    bullets:
      - "OpsAgent = TaskStore + OpsTools + run_ops_loop + OpsGuardrails"
      - "Ten agents built: simple → ReAct → tool → memory → plan → multi → MCP → RAG → safe → ops"
      - "Every agent follows: injectable LLM fn, max_iterations, 4-method class shape"
      - "Guardrails make agents deployable; without them they are demos"
      - "Next: Section 7 — Finance, Trading & Productizing (Days 89–100)"
""",
]

# ══════════════════════════════════════════════════════════════════════════════
# Project + solution notebooks
# ══════════════════════════════════════════════════════════════════════════════

_FULL_P = _P_BASE + _P_TASK + _P_TOOLS + _P_GUARD + _P_PROMPT + _P_LOOP + _P_AGENT_CLASS

_PROJ_SETUP = """\
# Ops scenario: automated code-quality pipeline
# Four tasks: lint, test, security scan, generate report
store = TaskStore()
store.add("Lint check",      "Run flake8 on src/")
store.add("Test suite",      "Run pytest with coverage")
store.add("Security scan",   "Run bandit static analysis")
store.add("Generate report", "Summarise all check results")

print(f"TaskStore ready: {len(store)} tasks pending")
for t in store.all():
    print(f"  {t.id}: {t.title}")
"""

_PROJ_GUARDRAILS = """\
guardrails = OpsGuardrails(
    max_budget    = 20,
    banned_inputs = ["rm -rf", "drop table", "shutdown"],
    approve_fn    = lambda goal: True,   # auto-approve; swap for cli_approve in production
)

# Gate-safe LLM: replace llm_fn=None to use real Ollama
_mock_llm = None   # ← set to a lambda for testing; None uses Ollama
"""

_PROJ_RUN = """\
# For gate execution we need a mock LLM
_gate_llm = lambda m: "Thought: Done\\nFinal Answer: All ops tasks completed."

agent = OpsAgent(
    store         = store,
    guardrails    = guardrails,
    llm_fn        = _gate_llm,   # replace with _mock_llm or None for real Ollama
    max_iterations = 10,
)

executor = lambda t: f"✓ {t.title} passed"

result = agent.run("Run all pending ops tasks and generate a final report",
                   executor_fn=executor)
print("Answer:", result["answer"])
print("Iterations:", result["iterations"])
print("Stopped:", result["stopped"] or "normally")
"""

_PROJ_HISTORY = """\
print(f"\\nAudit history ({len(agent.history())} run(s)):")
for i, r in enumerate(agent.history(), 1):
    status = "BLOCKED" if r["blocked"] else ("STOPPED:" + r["stopped"] if r["stopped"] else "OK")
    print(f"  {i}. [{status}] {r['goal'][:60]}")
    if r["blocked"]:
        print(f"      Reason: {r['reason']}")
    else:
        print(f"      Iterations: {r['iterations']}  |  Answer: {(r['answer'] or '')[:80]}")
"""

PROJECT_NB = _nb([
    _md(f"# Day {DAY} Project — Automated Ops Pipeline\n\n"
        "Build an `OpsAgent` that autonomously manages a code-quality "
        "pipeline: lint check, test suite, security scan, and report "
        "generation.  Use `OpsGuardrails` to keep it safe."),
    _code(_FULL_P),
    _md("## Step 1 — Create the task store"),
    _code(_PROJ_SETUP),
    _md("## Step 2 — Configure guardrails"),
    _code(_PROJ_GUARDRAILS),
    _md("## Step 3 — Run the agent"),
    _code(_PROJ_RUN),
    _md("## Step 4 — Review the audit history"),
    _code(_PROJ_HISTORY),
])

_SOL_SETUP = """\
_mock_llm = lambda m: "Thought: Done\\nFinal Answer: All ops checks passed."
_exec = lambda t: f"OK: {t.title} completed in 0.3s"

store = TaskStore()
store.add("Lint check",      "flake8 src/")
store.add("Test suite",      "pytest --cov")
store.add("Security scan",   "bandit -r src/")
store.add("Generate report", "build html summary")
"""

_SOL_AGENT = """\
guardrails = OpsGuardrails(max_budget=15, banned_inputs=["rm -rf", "drop table"])
agent = OpsAgent(store=store, guardrails=guardrails, llm_fn=_mock_llm, max_iterations=8)
"""

_SOL_NORMAL = """\
r = agent.run("Run all pending ops tasks and generate a report", executor_fn=_exec)
assert not r["blocked"]
assert r["answer"] == "All ops checks passed."
print("Normal run:", r["answer"])
print("Iterations:", r["iterations"])
"""

_SOL_BLOCKED = """\
r2 = agent.run("rm -rf / and delete everything")
assert r2["blocked"] and "input" in r2["reason"]
print("\\nBlocked run reason:", r2["reason"])
"""

_SOL_GATE = """\
r3 = agent.run("another goal", executor_fn=_exec)  # uses another budget unit
agent.clear_history()
assert agent.history() == []
print("\\nHistory cleared. Agent ready for next session.")
"""

_SOL_STORE = """\
done_tasks = [t for t in store.all() if t.status == "done"]
print(f"\\nTaskStore: {len(store)} tasks, {len(done_tasks)} done")
for t in store.all():
    print(f"  [{t.status}] {t.title}: {t.result[:40] if t.result else ''}")
print("\\nSolution smoke-test passed.")
"""

SOLUTION_NB = _nb([
    _md(f"# Day {DAY} Solution — Automated Ops Pipeline"),
    _code(_FULL_P),
    _code(_SOL_SETUP),
    _code(_SOL_AGENT),
    _code(_SOL_NORMAL),
    _code(_SOL_BLOCKED),
    _code(_SOL_GATE),
    _code(_SOL_STORE),
])

# ══════════════════════════════════════════════════════════════════════════════
# Gate inline validation
# ══════════════════════════════════════════════════════════════════════════════

GATE_PY = f"""\
import importlib.util, sys

spec = importlib.util.spec_from_file_location(
    "{SLUG}", r"{DIR / (SLUG + '.py')}"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

_mock = lambda m: "Thought: done\\nFinal Answer: All tasks processed."
_exec = lambda t: "OK: " + t.title

# OpsTask
t = mod.OpsTask(id="t1", title="Check")
assert t.status == "pending" and t.result == ""

# TaskStore
store = mod.TaskStore()
t1 = store.add("Lint"); t2 = store.add("Test", "pytest")
assert t1.id == "task_001" and t2.id == "task_002"
assert store.get(t1.id) is t1
assert store.get("x") is None
store.update(t1.id, "done", "ok")
assert t1.status == "done" and t1.result == "ok"
assert len(store.pending()) == 1
assert len(store) == 2

# build_ops_tools
store2 = mod.TaskStore(); store2.add("A"); store2.add("B")
tools = mod.build_ops_tools(store2, executor_fn=_exec)
assert set(tools.keys()) == {{"list_tasks","run_task","check_status","generate_report"}}
listing = tools["list_tasks"]()
assert "task_001" in listing and "A" in listing
msg = tools["run_task"]("task_001")
assert "done" in msg.lower() or "task_001" in msg
assert store2.get("task_001").status == "done"
status = tools["check_status"]("task_001")
assert "task_001" in status
report = tools["generate_report"]()
assert "2" in report or "tasks" in report.lower()

# parse_ops_step
step_a = mod.parse_ops_step('Thought: listing\\nAction: list_tasks\\nInput: {{}}')
assert step_a["action"] == "list_tasks" and step_a["final"] is None
step_f = mod.parse_ops_step("Thought: done\\nFinal Answer: Done!")
assert step_f["final"] == "Done!" and step_f["action"] is None
step_bad = mod.parse_ops_step("garbage ~~~")
assert isinstance(step_bad, dict) and "action" in step_bad

# format_ops_step
frag = mod.format_ops_step({{"thought": "ok", "action": "list_tasks", "input": {{}}, "final": None}}, "obs here")
assert "Thought:" in frag and "Action: list_tasks" in frag and "Observation: obs here" in frag

# run_ops_step
step = mod.run_ops_step("list tasks", tools, llm_fn=lambda m: "Thought: ok\\nAction: list_tasks\\nInput: {{}}")
assert step["action"] == "list_tasks"

# OpsGuardrails
g = mod.OpsGuardrails(max_budget=3, banned_inputs=["rm -rf"])
assert g.check_input("safe query")[0]
assert not g.check_input("rm -rf /")[0]
ok1, _ = g.check_budget(); assert ok1 and g.budget_count == 1
ok2, _ = g.check_budget(); assert ok2 and g.budget_count == 2
ok3, _ = g.check_budget(); assert ok3 and g.budget_count == 3
ok4, r4 = g.check_budget(); assert not ok4 and g.budget_count == 3  # no increment on block
g.reset(); assert g.budget_count == 0
g_no = mod.OpsGuardrails(approve_fn=lambda goal: False)
assert not g_no.check_approval("anything")[0]

# run_ops_loop — immediate final answer
store3 = mod.TaskStore(); store3.add("X")
tools3 = mod.build_ops_tools(store3, executor_fn=_exec)
res = mod.run_ops_loop("do it", tools3, llm_fn=_mock)
assert res["answer"] == "All tasks processed." and res["iterations"] == 1 and res["stopped"] == ""

# run_ops_loop — max_iterations
never = lambda m: "Thought: working\\nAction: list_tasks\\nInput: {{}}"
store4 = mod.TaskStore(); store4.add("Y")
tools4 = mod.build_ops_tools(store4, executor_fn=_exec)
res2 = mod.run_ops_loop("impossible", tools4, llm_fn=never, max_iterations=3)
assert res2["stopped"] == "max_iterations" and res2["iterations"] == 3

# OpsAgent
store5 = mod.TaskStore(); store5.add("Lint"); store5.add("Test")
agent = mod.OpsAgent(store=store5, llm_fn=_mock, max_iterations=5)
r = agent.run("run all", executor_fn=_exec)
assert r["answer"] == "All tasks processed." and not r["blocked"]
assert len(agent.history()) == 1

g2 = mod.OpsGuardrails(banned_inputs=["evil"])
agent2 = mod.OpsAgent(guardrails=g2, llm_fn=_mock)
rb = agent2.run("evil command")
assert rb["blocked"] and "input" in rb["reason"]
agent2.clear_history()
assert agent2.history() == []

print("Gate: all inline checks passed")
"""

# ══════════════════════════════════════════════════════════════════════════════
# main
# ══════════════════════════════════════════════════════════════════════════════

def main():
    import subprocess, sys, re

    (DIR / "exercises").mkdir(parents=True, exist_ok=True)
    (DIR / "lessons").mkdir(parents=True, exist_ok=True)
    (DIR / "project" / "solution").mkdir(parents=True, exist_ok=True)

    (DIR / f"{SLUG}.py").write_text(DELIVERABLE, encoding="utf-8")
    (DIR / "project" / "solution" / f"{SLUG}.py").write_text(DELIVERABLE, encoding="utf-8")

    for i, nb in enumerate(EXERCISES, 1):
        (DIR / "exercises" / f"exercise_{i:02d}.ipynb").write_text(
            json.dumps(nb, indent=1), encoding="utf-8")

    for i, yaml_text in enumerate(LESSONS, 1):
        (DIR / "lessons" / f"day_{DAY}_lesson_{i:02d}.yaml").write_text(
            yaml_text, encoding="utf-8")

    (DIR / "project" / "project.ipynb").write_text(
        json.dumps(PROJECT_NB, indent=1), encoding="utf-8")
    (DIR / "project" / "solution" / "solution.ipynb").write_text(
        json.dumps(SOLUTION_NB, indent=1), encoding="utf-8")

    print(f"[gen_day{DAY}] files written — running gate …")

    result = subprocess.run(
        ["conda", "run", "-n", "ai-course", "--no-capture-output",
         "python", "-c", GATE_PY],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print("GATE FAILED (inline)\n", result.stdout, result.stderr)
        sys.exit(1)
    print(result.stdout.strip())

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
            f"assert not errs, 'Notebook {p.name} had errors'\n"
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

    src = DELIVERABLE + "\n".join(
        json.dumps(nb) for nb in EXERCISES + [PROJECT_NB, SOLUTION_NB]
    )
    for pattern in ["openai", "anthropic", r"\beval\b"]:
        if re.search(pattern, src):
            print(f"GATE FAILED: banned pattern '{pattern}' found")
            sys.exit(1)
    print("Gate: adversarial grep clean")
    print(f"\n[gen_day{DAY}] gate-green ✓")


if __name__ == "__main__":
    main()
