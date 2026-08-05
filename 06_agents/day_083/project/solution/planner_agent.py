"""planner_agent.py — Day 083: Planning & Decomposition.

Days 79-82 gave an agent memory of what was just said and who it is talking to.
But every day so far the agent has worked on one task at a time. This day teaches
decomposition: given a complex goal, the agent breaks it into an ordered list of
subtasks, resolves their dependencies, and executes them step by step.

Pieces:
  safe_parse_json / call_llm  - reused (Day 79)
  safe_parse_list              - list-aware variant of safe_parse_json
  Task                         - a dataclass: id, title, description, depends_on
  build_plan_prompt            - ask the LLM to decompose a goal into tasks
  parse_plan                   - extract the task list from LLM output (never raises)
  topo_sort                    - Kahn's topological sort: resolve dependency order
  build_execution_context      - inject prior task results into the current prompt
  execute_task                 - run one task; uses executor_fn or the LLM
  run_plan                     - plan -> sort -> execute; max_tasks safety guard
  PlannerAgent                 - an agent that plans, sorts, and executes

Setup:
    pip install ollama
    ollama pull llama3.2
"""
import json
from dataclasses import dataclass, field

# ── helpers reused from Day 79 ───────────────────────────────────────────────
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


def safe_parse_list(text):
    """Slice first '[' to last ']' and parse. Returns list|None. Never raises."""
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end == -1 or end < start:
        return None
    try:
        data = json.loads(text[start:end + 1])
    except (json.JSONDecodeError, ValueError):
        return None
    return data if isinstance(data, list) else None


def call_llm(messages, llm_fn=None):
    """Call the chat model, or the injected llm_fn(messages) -> str (Day 79)."""
    if llm_fn is not None:
        return llm_fn(messages)
    import ollama
    resp = ollama.chat(model="llama3.2", messages=messages)
    return resp["message"]["content"]

# ── the Task dataclass ────────────────────────────────────────────────────────
@dataclass
class Task:
    """One step in a plan.

    Attributes:
        id:          short snake_case identifier (e.g. 't1', 'write_outline').
        title:       brief human-readable label (5 words max).
        description: one sentence describing what to do.
        depends_on:  ids of tasks that must complete before this one.
        status:      'pending' | 'done' | 'failed'.
        result:      the output of executing this task.
    """
    id: str
    title: str
    description: str
    depends_on: list = field(default_factory=list)
    status: str = "pending"
    result: str = ""

# ── planning: ask the LLM to decompose a goal ─────────────────────────────────
def build_plan_prompt(goal, context=None):
    """Build a prompt that asks the LLM to break a goal into a JSON task list."""
    system = "\n".join([
        "You are a planning assistant. Break the goal into an ordered list of tasks.",
        "",
        "Return ONLY a JSON array. Each item must have these exact keys:",
        '  "id": short snake_case identifier (t1, t2, ...)',
        '  "title": brief label (5 words max)',
        '  "description": one sentence - what to do',
        '  "depends_on": list of task ids that must finish before this one ([] if none)',
        "",
        "Return ONLY the JSON array. No prose, no markdown fences.",
    ])
    user_parts = ["Goal: " + str(goal)]
    if context:
        user_parts.append("Context: " + str(context))
    return [{"role": "system", "content": system},
            {"role": "user", "content": "\n".join(user_parts)}]


def parse_plan(text):
    """Extract a task list from LLM output. Returns list[Task]; never raises.

    Tolerates markdown fences, prose before/after, missing fields, and invalid
    JSON. Invalid or missing fields are filled with safe defaults so any
    parseable item becomes a valid Task.
    """
    items = safe_parse_list(text) or []
    tasks = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        tasks.append(Task(
            id=str(item.get("id", "t" + str(i + 1))),
            title=str(item.get("title", "Task " + str(i + 1))),
            description=str(item.get("description", "")),
            depends_on=[str(d) for d in item.get("depends_on", [])
                        if isinstance(d, str)],
        ))
    return tasks

# ── dependency ordering: Kahn's topological sort ──────────────────────────────
def topo_sort(tasks):
    """Sort tasks so every dependency comes before the task that needs it.

    Uses Kahn's algorithm (BFS on a DAG). If a cycle exists the cyclic tasks
    are appended at the end in their original order rather than raising, so
    execution can still proceed on the non-cyclic portion.
    """
    by_id = {t.id: t for t in tasks}
    # count incoming edges (how many unresolved deps each task has)
    in_deg = {t.id: 0 for t in tasks}
    for t in tasks:
        for dep in t.depends_on:
            if dep in in_deg:
                in_deg[t.id] += 1
    # start with tasks that have no deps
    queue = [t.id for t in tasks if in_deg[t.id] == 0]
    order = []
    while queue:
        tid = queue.pop(0)
        order.append(by_id[tid])
        # for every task that listed tid as a dep, reduce its in-degree
        for t in tasks:
            if tid in t.depends_on:
                in_deg[t.id] -= 1
                if in_deg[t.id] == 0:
                    queue.append(t.id)
    # cycle guard: any task not yet emitted has a circular dependency
    done_ids = {t.id for t in order}
    for t in tasks:
        if t.id not in done_ids:
            order.append(t)
    return order

# ── executing tasks ───────────────────────────────────────────────────────────
def build_execution_context(task, results):
    """Render prior results that this task depends on, for injection into the prompt."""
    lines = ["You are executing one step of a multi-task plan."]
    prior = [(dep, results[dep]) for dep in task.depends_on if dep in results]
    if prior:
        lines.append("Results from earlier steps:")
        for dep_id, res in prior:
            lines.append("  " + dep_id + ": " + str(res))
    lines.append("Task: " + task.title)
    lines.append("Description: " + task.description)
    lines.append("Complete this task concisely.")
    return "\n".join(lines)


def execute_task(task, results, executor_fn=None, llm_fn=None):
    """Run one task. Returns the result string; never raises.

    If executor_fn is provided, call executor_fn(task) -> str.
    Otherwise use the LLM, passing prior results as context.
    Exceptions are caught and returned as 'Error: ...' strings.
    """
    try:
        if executor_fn is not None:
            return str(executor_fn(task))
        context = build_execution_context(task, results)
        messages = [{"role": "system", "content": context},
                    {"role": "user", "content": "Execute this task now."}]
        return call_llm(messages, llm_fn=llm_fn)
    except Exception as exc:
        return "Error: " + str(exc)

# ── end-to-end plan runner ────────────────────────────────────────────────────
def run_plan(goal, executor_fn=None, llm_fn=None, max_tasks=20):
    """Plan a goal, sort by dependencies, and execute step by step.

    Returns {"tasks": list[Task], "results": {id: result}, "answer": str}.
    The answer is the result of the last task in execution order.
    max_tasks caps the plan so a model that returns 1000 tasks cannot hang the gate.
    """
    plan_text = call_llm(build_plan_prompt(goal), llm_fn=llm_fn)
    tasks = parse_plan(plan_text)
    if not tasks:
        return {"tasks": [], "results": {}, "answer": "No plan generated."}
    ordered = topo_sort(tasks[:max_tasks])
    results = {}
    for task in ordered:
        result = execute_task(task, results,
                              executor_fn=executor_fn, llm_fn=llm_fn)
        task.result = result
        task.status = "done"
        results[task.id] = result
    answer = ordered[-1].result if ordered else "No tasks executed."
    return {"tasks": ordered, "results": results, "answer": answer}

# ── the planning assistant ────────────────────────────────────────────────────
class PlannerAgent:
    """An agent that breaks a goal into subtasks and executes them in order.

    plan() decomposes a goal without executing - useful for reviewing the plan.
    execute() runs a task list produced by plan() (or built manually).
    run() does both in one call and records the outcome in history.

    Example::

        agent = PlannerAgent(executor_fn=my_executor, llm_fn=my_llm_fn)
        result = agent.run("Write a short report on prompt engineering")
        print(result["answer"])
    """

    def __init__(self, executor_fn=None, llm_fn=None, max_tasks=20):
        self._executor_fn = executor_fn
        self._llm_fn = llm_fn
        self.max_tasks = max_tasks
        self._history = []

    def plan(self, goal):
        """Decompose goal into a topologically sorted task list; do not execute."""
        plan_text = call_llm(build_plan_prompt(goal), llm_fn=self._llm_fn)
        return topo_sort(parse_plan(plan_text)[:self.max_tasks])

    def execute(self, tasks):
        """Execute a task list in dependency order. Returns {id: result} dict."""
        ordered = topo_sort(tasks[:self.max_tasks])
        results = {}
        for task in ordered:
            result = execute_task(task, results,
                                  executor_fn=self._executor_fn,
                                  llm_fn=self._llm_fn)
            task.result = result
            task.status = "done"
            results[task.id] = result
        return results

    def run(self, goal):
        """Plan + execute. Records the run in history and returns the result dict."""
        tasks = self.plan(goal)
        results = self.execute(tasks)
        answer = tasks[-1].result if tasks else "No tasks."
        record = {"goal": goal, "tasks": tasks, "results": results, "answer": answer}
        self._history.append(record)
        return record

    def history(self):
        """Return a copy of the run history."""
        return list(self._history)

    def clear_history(self):
        """Clear run history in place."""
        self._history.clear()
