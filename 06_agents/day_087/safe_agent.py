"""
Day 087 — Guardrails & Safety
==============================
Agents that can take real actions need boundaries.  Four guardrail layers keep
them controllable:

    1. Input Guard  — validate what goes in (max length, banned patterns)
    2. Budget       — cap how many calls happen per session
    3. Approval Gate — pause for human confirmation on sensitive actions
    4. Output Guard — validate what comes out before returning to the caller

The layers compose into a pipeline:
    input_guard -> budget -> gate -> agent_fn -> output_guard

Public API
----------
    validate_text(text, max_length, banned)    standalone validation function
    Guard(max_length, banned)                  reusable Guard config; .check(text)
    ApprovalGate(approve_fn)                   injectable human-in-the-loop
    BudgetTracker(max_calls)                   call counter with ok()/record()/reset()
    safe_ask(query, agent_fn, ...)             stateless pipeline with all four layers
    SafeAgent(agent_fn, ...)                   class with history + reset_budget()
"""
import json

# ── LLM helper (used when agent_fn calls an LLM internally) ──────────────────

def call_llm(messages, llm_fn=None):
    """Call the LLM.  Routes to llm_fn when injected; else Ollama."""
    if llm_fn is not None:
        return str(llm_fn(messages))
    import ollama
    resp = ollama.chat(model="llama3.2", messages=messages)
    return resp["message"]["content"]

# ── input / output validation ─────────────────────────────────────────────────

def validate_text(text, max_length=None, banned=None):
    """Validate text against length and banned-pattern rules.

    Returns (ok: bool, reason: str).
    ok=True  -> text passes all checks; reason is ""
    ok=False -> first failed check; reason explains why
    Never raises.
    """
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


class Guard:
    """A reusable text validator.

    Wraps validate_text with a persistent config (max_length, banned list).
    Use one Guard instance per boundary point (input or output).
    """

    def __init__(self, max_length=None, banned=None):
        self.max_length = max_length
        self.banned     = list(banned) if banned else []

    def check(self, text):
        """Return (ok: bool, reason: str)."""
        return validate_text(text, self.max_length, self.banned)

# ── approval gate ─────────────────────────────────────────────────────────────

class ApprovalGate:
    """Human-in-the-loop gate with an injectable approve_fn.

    In production approve_fn would prompt a human and wait for a y/n reply.
    For gate testing inject a lambda: ``ApprovalGate(approve_fn=lambda a: True)``.

    approve_fn(action: str) -> bool
        Receives a description of the action about to run.
        Returns True to allow, False to block.
        Exceptions inside approve_fn are caught and treated as a rejection.
    """

    def __init__(self, approve_fn=None):
        self._approve_fn = approve_fn if approve_fn is not None else (lambda action: True)

    def check(self, action):
        """Return (approved: bool, reason: str)."""
        try:
            result = bool(self._approve_fn(str(action)))
        except Exception:
            result = False
        if result:
            return True, "approved"
        return False, "rejected by approval gate"

# ── budget tracker ────────────────────────────────────────────────────────────

class BudgetTracker:
    """Counts protected operations and enforces a maximum.

    Workflow::

        budget = BudgetTracker(max_calls=10)

        ok, reason = budget.ok()      # check before running
        if not ok:
            ...block...
        budget.record()               # record after allowed
        budget.reset()                # start a new session

    count property returns the current call count.
    """

    def __init__(self, max_calls=None):
        self.max_calls = max_calls
        self._count    = 0

    def ok(self):
        """Return (ok: bool, reason: str).  True while under budget."""
        if self.max_calls is not None and self._count >= self.max_calls:
            return False, (
                "budget exceeded ("
                + str(self._count) + "/" + str(self.max_calls) + " calls)"
            )
        return True, ""

    def record(self):
        """Increment the call counter."""
        self._count += 1

    def reset(self):
        """Reset the counter to zero (start a new session)."""
        self._count = 0

    @property
    def count(self):
        """Current number of recorded calls."""
        return self._count

# ── safe_ask pipeline ─────────────────────────────────────────────────────────

def safe_ask(query, agent_fn, input_guard=None, output_guard=None,
             budget=None, gate=None, llm_fn=None):
    """Run agent_fn through all four guardrail layers.

    Pipeline
    --------
    input_guard -> budget -> gate -> agent_fn -> output_guard

    Parameters
    ----------
    query       : the user's question / instruction
    agent_fn    : callable(query, llm_fn=None) -> str
    input_guard : Guard or None — validates query before running
    output_guard: Guard or None — validates answer before returning
    budget      : BudgetTracker or None — blocks when max_calls exceeded
    gate        : ApprovalGate or None — blocks when approve_fn returns False
    llm_fn      : injected LLM function passed through to agent_fn

    Returns
    -------
    dict with keys:
        "query"   — original query
        "answer"  — str answer, "[blocked]" if output guard fired, None if blocked earlier
        "blocked" — True if any guard blocked the request
        "reason"  — "" if not blocked; description of which guard fired and why
    """
    record = {"query": query, "answer": None, "blocked": False, "reason": ""}

    if input_guard is not None:
        ok, reason = input_guard.check(str(query))
        if not ok:
            record["blocked"] = True
            record["reason"]  = "input: " + reason
            return record

    if budget is not None:
        ok, reason = budget.ok()
        if not ok:
            record["blocked"] = True
            record["reason"]  = "budget: " + reason
            return record
        budget.record()

    if gate is not None:
        approved, reason = gate.check(str(query))
        if not approved:
            record["blocked"] = True
            record["reason"]  = "gate: " + reason
            return record

    try:
        answer = str(agent_fn(query, llm_fn=llm_fn))
    except Exception as exc:
        answer = "Error: " + str(exc)

    if output_guard is not None:
        ok, reason = output_guard.check(answer)
        if not ok:
            record["blocked"] = True
            record["reason"]  = "output: " + reason
            record["answer"]  = "[blocked]"
            return record

    record["answer"] = answer
    return record

# ── safe agent ────────────────────────────────────────────────────────────────

class SafeAgent:
    """An agent wrapped in all four guardrail layers with persistent history.

    Delegates each ask() to safe_ask() — all guardrail logic lives there.
    Adds history tracking and reset_budget() for multi-turn sessions.

    Same four-method class shape as all prior Section 6 agents.
    """

    def __init__(self, agent_fn, input_guard=None, output_guard=None,
                 budget=None, gate=None, llm_fn=None):
        self._agent_fn     = agent_fn
        self._input_guard  = input_guard
        self._output_guard = output_guard
        self._budget       = budget
        self._gate         = gate
        self._llm_fn       = llm_fn
        self._history      = []

    def ask(self, query):
        """Run the guardrail pipeline and record the result."""
        record = safe_ask(
            query, self._agent_fn,
            input_guard  = self._input_guard,
            output_guard = self._output_guard,
            budget       = self._budget,
            gate         = self._gate,
            llm_fn       = self._llm_fn,
        )
        self._history.append(record)
        return record

    def history(self):
        """Return a copy of the interaction history."""
        return list(self._history)

    def clear_history(self):
        """Clear the interaction history."""
        self._history.clear()

    def reset_budget(self):
        """Reset the budget tracker (start a new session)."""
        if self._budget is not None:
            self._budget.reset()
