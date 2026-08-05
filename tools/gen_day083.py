#!/usr/bin/env python3
"""gen_day083.py — generate Day 083: Planning & Decomposition."""
from pathlib import Path
import json

ROOT    = Path(__file__).parent.parent
DAY     = "083"
SECTION = "06_agents"
OUT     = ROOT / SECTION / f"day_{DAY}"

(OUT / "exercises").mkdir(parents=True, exist_ok=True)
(OUT / "lessons").mkdir(parents=True, exist_ok=True)
(OUT / "project" / "solution").mkdir(parents=True, exist_ok=True)

# ── deliverable fragments (composed into planner_agent.py AND reused as ───────
# ── given-code / embedded solutions in the exercises, so they stay in sync) ────

_DOC = '''\
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
'''

_FRAG_HELPERS = '''\
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
'''

_FRAG_TASK = '''\

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
'''

_FRAG_PLAN = '''\

# ── planning: ask the LLM to decompose a goal ─────────────────────────────────
def build_plan_prompt(goal, context=None):
    """Build a prompt that asks the LLM to break a goal into a JSON task list."""
    system = "\\n".join([
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
            {"role": "user", "content": "\\n".join(user_parts)}]


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
'''

_FRAG_TOPO = '''\

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
'''

_FRAG_EXECUTE = '''\

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
    return "\\n".join(lines)


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
'''

_FRAG_RUN = '''\

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
'''

_FRAG_AGENT = '''\

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
'''

_PLANNER_AGENT_SRC = (_DOC + _FRAG_HELPERS + _FRAG_TASK + _FRAG_PLAN
                      + _FRAG_TOPO + _FRAG_EXECUTE + _FRAG_RUN + _FRAG_AGENT)


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
_PLAN_JSON = json.dumps([
    {"id": "t1", "title": "Gather facts",
     "description": "Collect the relevant information.", "depends_on": []},
    {"id": "t2", "title": "Draft outline",
     "description": "Organize the facts into an outline.", "depends_on": ["t1"]},
    {"id": "t3", "title": "Write summary",
     "description": "Write the final summary.", "depends_on": ["t2"]},
])

_MOCK_HELPER = """\
import json

_PLAN_JSON = json.dumps([
    {'id': 't1', 'title': 'Gather facts',
     'description': 'Collect the relevant information.', 'depends_on': []},
    {'id': 't2', 'title': 'Draft outline',
     'description': 'Organize the facts into an outline.', 'depends_on': ['t1']},
    {'id': 't3', 'title': 'Write summary',
     'description': 'Write the final summary.', 'depends_on': ['t2']},
])

def _mock_planner(plan_json=None, task_result='Task done.'):
    \"\"\"Return an llm_fn: the plan JSON on planning calls, task_result on execution calls.\"\"\"
    plan = plan_json if plan_json is not None else _PLAN_JSON
    def _fn(messages):
        system = messages[0]['content'] if messages else ''
        if 'json array' in system.lower() or 'planning' in system.lower():
            return plan
        return task_result
    return _fn

def _mock_executor(task):
    return 'Result: ' + task.title
"""

# ── EX1: Task + build_plan_prompt + parse_plan ───────────────────────────────
_EX1_GIVEN = "# Task dataclass needs dataclasses stdlib; parse_plan uses safe_parse_list below.\n"

_EX1_STUB = """\
from dataclasses import dataclass, field
import json

def safe_parse_list(text):
    \"\"\"Slice first '[' to last ']' and parse. Returns list|None. Never raises.\"\"\"
    raise NotImplementedError

@dataclass
class Task:
    \"\"\"One step in a plan: id, title, description, depends_on, status, result.\"\"\"
    id: str = ''             # TODO: add all six fields with correct defaults
    title: str = ''
    description: str = ''

def build_plan_prompt(goal, context=None):
    \"\"\"Build a prompt asking the LLM to decompose goal into a JSON task list.\"\"\"
    raise NotImplementedError

def parse_plan(text):
    \"\"\"Extract list[Task] from LLM output. Never raises; missing fields -> defaults.\"\"\"
    raise NotImplementedError
"""

_EX1_CHECKS = r"""
score, total = 0, 5
try:
    t = Task(id='t1', title='Step', description='Do it.')
    assert t.status == 'pending' and t.result == '' and t.depends_on == []
    score += 1; print("✅ Task has correct fields and defaults")

    assert safe_parse_list('[1, 2, 3]') == [1, 2, 3]
    assert safe_parse_list('{"a":1}') is None     # dict, not list
    assert safe_parse_list('no json here') is None
    score += 1; print("✅ safe_parse_list parses lists, returns None for non-lists")

    msgs = build_plan_prompt('write a report')
    assert msgs[0]['role'] == 'system' and 'json array' in msgs[0]['content'].lower()
    assert msgs[1]['content'].startswith('Goal:')
    score += 1; print("✅ build_plan_prompt asks for a JSON array")

    tasks = parse_plan(_PLAN_JSON)
    assert len(tasks) == 3 and tasks[0].id == 't1' and tasks[1].depends_on == ['t1']
    score += 1; print("✅ parse_plan extracts a valid task list")

    assert parse_plan('no json at all') == []
    t_bad = parse_plan('[{"id":"x"}]')
    assert len(t_bad) == 1 and t_bad[0].title != ''   # missing fields get defaults
    score += 1; print("✅ parse_plan returns [] on garbage; missing fields get defaults")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX1 = nb([
    md("# Day 083 — Exercise 1: Task Representation and Parsing the Plan\n\n"
       "**What you'll build:** the `Task` dataclass, a list-aware JSON parser "
       "(`safe_parse_list`), a planning prompt, and `parse_plan` — the function "
       "that turns raw LLM output into a structured task list.\n\n"
       "**Why it matters:** decomposition starts with a representation. Every task "
       "needs an id (so others can depend on it), a title, a description (what to "
       "do), and a dependency list. And like every LLM parser this section, "
       "`parse_plan` must tolerate garbage output — missing fields, prose, invalid "
       "JSON — without crashing."),
    code(_MOCK_HELPER + _EX1_GIVEN),
    md("## Task\n\n"
       "1. `safe_parse_list(text)` — like `safe_parse_json` but finds `[` to `]`; "
       "returns a `list` or `None`; never raises.\n"
       "2. `Task` dataclass — fields: `id: str`, `title: str`, `description: str`, "
       "`depends_on: list = []`, `status: str = 'pending'`, `result: str = ''`.\n"
       "3. `build_plan_prompt(goal, context=None)` — a `system` message instructing "
       "the LLM to return **only** a JSON array of task objects; a `user` message "
       "with the goal.\n"
       "4. `parse_plan(text) -> list[Task]` — `safe_parse_list(text) or []`; build "
       "a `Task` for each dict item, filling missing fields with safe defaults. "
       "**Never raises.**"),
    md("## Your Implementation"),
    code(_EX1_STUB),
    code(_FRAG_HELPERS + _FRAG_TASK + _FRAG_PLAN),
    md("## Automated checks"),
    code(_EX1_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _FRAG_HELPERS + _FRAG_TASK + _FRAG_PLAN + "```\n\n"
       "**Why fill defaults for missing fields?** The model might return `{\"id\": "
       "\"t1\"}` without a title. Raising on a partial item would drop a task that "
       "could be valid enough to execute. Defaults keep the plan alive; the human "
       "can spot a blank title and fix it.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_01.ipynb", EX1)

# ── EX2: topo_sort ───────────────────────────────────────────────────────────
_EX2_GIVEN = _MOCK_HELPER + _FRAG_HELPERS + _FRAG_TASK + _FRAG_PLAN

_EX2_STUB = """\
def topo_sort(tasks):
    \"\"\"Sort tasks so every dependency runs before the task that needs it.
    Uses Kahn's algorithm; appends cyclic tasks at the end rather than raising.
    \"\"\"
    raise NotImplementedError
"""

_EX2_CHECKS = r"""
score, total = 0, 5
try:
    tasks = parse_plan(_PLAN_JSON)     # t1 -> t2 -> t3 chain
    ordered = topo_sort(tasks)
    ids = [t.id for t in ordered]
    assert ids.index('t1') < ids.index('t2') < ids.index('t3')
    score += 1; print("✅ linear chain is sorted t1 -> t2 -> t3")

    no_deps = [Task('a','A','a'), Task('b','B','b'), Task('c','C','c')]
    assert len(topo_sort(no_deps)) == 3
    score += 1; print("✅ tasks with no dependencies are all included")

    # diamond: d1, d2 depend on base; final depends on both
    diamond = [
        Task('base','Base','do'), Task('d1','D1','do', depends_on=['base']),
        Task('d2','D2','do', depends_on=['base']),
        Task('final','Final','do', depends_on=['d1','d2']),
    ]
    di = topo_sort(diamond)
    di_ids = [t.id for t in di]
    assert di_ids.index('base') < di_ids.index('d1')
    assert di_ids.index('base') < di_ids.index('d2')
    assert di_ids.index('d1') < di_ids.index('final')
    assert di_ids.index('d2') < di_ids.index('final')
    score += 1; print("✅ diamond dependency resolved correctly")

    cycle = [Task('x','X','x',depends_on=['y']), Task('y','Y','y',depends_on=['x'])]
    result = topo_sort(cycle)
    assert len(result) == 2   # cycle: both tasks still returned, not dropped
    score += 1; print("✅ cycle detected: tasks still returned (not dropped or raised)")

    assert topo_sort([]) == []
    score += 1; print("✅ empty task list returns empty list")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX2 = nb([
    md("# Day 083 — Exercise 2: Dependency Ordering (Topological Sort)\n\n"
       "**What you'll build:** `topo_sort` — given a list of tasks with dependency "
       "ids, return them in an order where every dependency comes before the task "
       "that needs it.\n\n"
       "**Why it matters:** the LLM may return tasks in any order. Executing them "
       "naively would try to 'Write summary' before 'Gather facts'. Topological sort "
       "is the classic algorithm for scheduling tasks with dependencies, and it's the "
       "only thing standing between you and executing a plan backwards."),
    code(_EX2_GIVEN),
    md("## Task\n\n"
       "`topo_sort(tasks) -> list[Task]` using Kahn's algorithm:\n\n"
       "1. Build `in_deg = {task.id: 0}` for each task; for each task's "
       "`depends_on`, increment `in_deg[task.id]` for each dep that exists.\n"
       "2. Seed a queue with all tasks where `in_deg == 0`.\n"
       "3. While the queue has tasks: pop, emit, then decrement `in_deg` for every "
       "task that depended on the one just emitted; enqueue any that hit zero.\n"
       "4. Any tasks not emitted (cycle victims) are appended at the end. "
       "**Never raises.**"),
    md("## Your Implementation"),
    code(_EX2_STUB),
    code(_FRAG_TOPO),
    md("## Automated checks"),
    code(_EX2_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _FRAG_TOPO + "```\n\n"
       "**Why append cycle victims instead of raising?** Raising on a circular "
       "dependency stops the whole plan. Appending them means the non-cyclic "
       "portion of the plan can still execute, and the cyclic tasks at least run "
       "in some order rather than being silently dropped.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_02.ipynb", EX2)

# ── EX3: build_execution_context + execute_task ──────────────────────────────
_EX3_GIVEN = _MOCK_HELPER + _FRAG_HELPERS + _FRAG_TASK + _FRAG_PLAN + _FRAG_TOPO

_EX3_STUB = """\
def build_execution_context(task, results):
    \"\"\"Render prior results for tasks this one depends on, for the prompt.\"\"\"
    raise NotImplementedError

def execute_task(task, results, executor_fn=None, llm_fn=None):
    \"\"\"Run one task. Uses executor_fn if provided, else the LLM. Never raises.\"\"\"
    raise NotImplementedError
"""

_EX3_CHECKS = r"""
score, total = 0, 5
try:
    t1 = Task('t1', 'Step 1', 'First step.')
    t2 = Task('t2', 'Step 2', 'Second step.', depends_on=['t1'])

    ctx = build_execution_context(t2, {'t1': 'step 1 done'})
    assert 'step 1 done' in ctx and 'Step 2' in ctx
    score += 1; print("✅ build_execution_context injects prior results")

    ctx_no_deps = build_execution_context(t1, {})
    assert 'Step 1' in ctx_no_deps    # still mentions the task
    score += 1; print("✅ build_execution_context works with no prior results")

    out = execute_task(t1, {}, executor_fn=_mock_executor)
    assert out == 'Result: Step 1'
    score += 1; print("✅ execute_task uses executor_fn when provided")

    out_llm = execute_task(t1, {}, llm_fn=_mock_planner(task_result='llm answer'))
    assert out_llm == 'llm answer'
    score += 1; print("✅ execute_task falls back to llm_fn")

    def _bad(task): raise RuntimeError("tool broke")
    out_err = execute_task(t1, {}, executor_fn=_bad)
    assert out_err.startswith('Error:')
    score += 1; print("✅ execute_task catches exceptions as 'Error: ...' (never raises)")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX3 = nb([
    md("# Day 083 — Exercise 3: Executing One Task\n\n"
       "**What you'll build:** `build_execution_context` (inject prior results into "
       "the prompt for one task) and `execute_task` (run it, using an injected "
       "executor or the LLM, without ever raising).\n\n"
       "**Why it matters:** each task's result may feed the next. 'Write summary' "
       "needs to know what 'Gather facts' found. `build_execution_context` is the "
       "glue that passes prior outputs forward — the same injection-of-context idea "
       "as Day 82's working memory, applied to a plan's intermediate results."),
    code(_EX3_GIVEN),
    md("## Task\n\n"
       "1. `build_execution_context(task, results) -> str` — build a prompt string "
       "that lists the prior results for each id in `task.depends_on` (if in "
       "`results`), then states the task title and description.\n"
       "2. `execute_task(task, results, executor_fn=None, llm_fn=None) -> str` — "
       "if `executor_fn` is provided, call `str(executor_fn(task))`; otherwise "
       "build a prompt with `build_execution_context` and call `call_llm`. Wrap "
       "everything in `try/except` — return `'Error: ' + str(exc)` on failure. "
       "**Never raises.**"),
    md("## Your Implementation"),
    code(_EX3_STUB),
    code(_FRAG_EXECUTE),
    md("## Automated checks"),
    code(_EX3_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _FRAG_EXECUTE + "```\n\n"
       "**Why two modes (executor_fn vs LLM)?** For the gate, executor_fn is a "
       "deterministic mock with no model calls. In production, you might have real "
       "tools (a web search, a code runner) or you might just ask the LLM to do the "
       "work — same interface, swappable at construction time.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_03.ipynb", EX3)

# ── EX4: run_plan ────────────────────────────────────────────────────────────
_EX4_GIVEN = (_MOCK_HELPER + _FRAG_HELPERS + _FRAG_TASK + _FRAG_PLAN
              + _FRAG_TOPO + _FRAG_EXECUTE)

_EX4_STUB = """\
def run_plan(goal, executor_fn=None, llm_fn=None, max_tasks=20):
    \"\"\"Plan a goal, sort by dependencies, and execute step by step.
    Returns {'tasks': list[Task], 'results': {id: result}, 'answer': str}.
    \"\"\"
    raise NotImplementedError
"""

_EX4_CHECKS = r"""
score, total = 0, 5
try:
    r = run_plan('test goal',
                 executor_fn=_mock_executor,
                 llm_fn=_mock_planner())
    assert 'tasks' in r and 'results' in r and 'answer' in r
    score += 1; print("✅ run_plan returns {tasks, results, answer}")

    assert len(r['tasks']) == 3 and r['tasks'][0].status == 'done'
    score += 1; print("✅ all tasks are executed and marked done")

    ids = [t.id for t in r['tasks']]
    assert ids.index('t1') < ids.index('t2') < ids.index('t3')
    score += 1; print("✅ tasks run in dependency order")

    assert r['results']['t2'] == 'Result: Draft outline'
    assert r['answer'] == 'Result: Write summary'
    score += 1; print("✅ results and answer are correct")

    empty = run_plan('x', executor_fn=_mock_executor,
                     llm_fn=_mock_planner(plan_json='no json here'))
    assert empty['tasks'] == [] and 'No plan' in empty['answer']
    score += 1; print("✅ empty plan returns a safe fallback (no crash)")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX4 = nb([
    md("# Day 083 — Exercise 4: run_plan — End to End\n\n"
       "**What you'll build:** `run_plan` — the end-to-end orchestrator that plans "
       "a goal, sorts the tasks by dependency, and executes them in order.\n\n"
       "**Why it matters:** this is the payoff of the day's three earlier pieces. "
       "One function takes a goal, hands it to the LLM for decomposition, sorts the "
       "task list, feeds results forward, and returns the final answer — all with a "
       "`max_tasks` guard so a runaway plan can't hang the gate."),
    code(_EX4_GIVEN),
    md("## Task\n\n"
       "`run_plan(goal, executor_fn=None, llm_fn=None, max_tasks=20) -> dict`\n\n"
       "1. Call `call_llm(build_plan_prompt(goal), llm_fn=llm_fn)` to get the plan.\n"
       "2. `parse_plan` and `topo_sort` it (cap at `max_tasks` before sorting).\n"
       "3. If empty, return `{'tasks': [], 'results': {}, 'answer': 'No plan "
       "generated.'}`.\n"
       "4. Loop: for each task, `execute_task(task, results, ...)`, update "
       "`task.result`, `task.status = 'done'`, and `results[task.id] = result`.\n"
       "5. Return `{'tasks': ordered, 'results': results, 'answer': last task's "
       "result}`."),
    md("## Your Implementation"),
    code(_EX4_STUB),
    code(_FRAG_RUN),
    md("## Automated checks"),
    code(_EX4_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _FRAG_RUN + "```\n\n"
       "**Why cap at `max_tasks` before sorting?** The sort and execution loop both "
       "iterate over the task list. A model that returns 100 tasks would cause 100 "
       "executor calls and a very large sort. Capping first keeps both bounded — "
       "same principle as `max_iterations` on the agent loops.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_04.ipynb", EX4)

# ── EX5: PlannerAgent ────────────────────────────────────────────────────────
_EX5_GIVEN = (_MOCK_HELPER + _FRAG_HELPERS + _FRAG_TASK + _FRAG_PLAN
              + _FRAG_TOPO + _FRAG_EXECUTE + _FRAG_RUN)

_EX5_STUB = """\
class PlannerAgent:
    \"\"\"An agent that breaks a goal into subtasks and executes them in order.\"\"\"

    def __init__(self, executor_fn=None, llm_fn=None, max_tasks=20):
        raise NotImplementedError

    def plan(self, goal):
        \"\"\"Decompose goal into a sorted task list; do not execute.\"\"\"
        raise NotImplementedError

    def execute(self, tasks):
        \"\"\"Execute a task list in dependency order. Returns {id: result}.\"\"\"
        raise NotImplementedError

    def run(self, goal):
        \"\"\"Plan + execute; records in history. Returns {goal,tasks,results,answer}.\"\"\"
        raise NotImplementedError

    def history(self):
        raise NotImplementedError

    def clear_history(self):
        raise NotImplementedError
"""

_EX5_CHECKS = r"""
score, total = 0, 6
try:
    agent = PlannerAgent(executor_fn=_mock_executor,
                         llm_fn=_mock_planner())

    tasks = agent.plan('test goal')
    assert len(tasks) == 3 and tasks[0].id == 't1'
    score += 1; print("✅ plan() returns sorted tasks without executing them")

    assert all(t.status == 'pending' for t in tasks)
    score += 1; print("✅ plan() leaves tasks pending (no execution)")

    results = agent.execute(tasks)
    assert results['t1'] == 'Result: Gather facts'
    assert tasks[0].status == 'done'
    score += 1; print("✅ execute() runs tasks in order and marks them done")

    record = agent.run('another goal')
    assert 'goal' in record and 'tasks' in record and 'answer' in record
    score += 1; print("✅ run() returns the full result dict")

    assert len(agent.history()) == 1
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
    md("# Day 083 — Exercise 5: PlannerAgent\n\n"
       "**What you'll build:** `PlannerAgent` — an agent that encapsulates "
       "planning, sorting, and execution, with separate `plan()`, `execute()`, "
       "and `run()` methods so you can inspect the plan before committing to it.\n\n"
       "**Why it matters:** `plan()` lets you review and approve the decomposition "
       "before anything executes — an early form of human-in-the-loop that Day 87 "
       "will formalise as a proper guardrail. And separating plan from execute means "
       "you can inject a manually-crafted task list or revise the plan before "
       "running."),
    code(_EX5_GIVEN),
    md("## Task\n\n"
       "`PlannerAgent(executor_fn=None, llm_fn=None, max_tasks=20)`\n\n"
       "1. `plan(goal)` — `call_llm(build_plan_prompt(goal))` → `parse_plan` → "
       "`topo_sort`; cap at `max_tasks`; return the sorted list **without** "
       "executing.\n"
       "2. `execute(tasks)` — `topo_sort(tasks[:max_tasks])`; loop calling "
       "`execute_task`; update `task.result`/`task.status`; return `{id: result}`.\n"
       "3. `run(goal)` — `plan` + `execute`; build the result dict; append to "
       "`_history`; return it.\n"
       "4. `history()` — copy; `clear_history()` — in-place."),
    md("## Your Implementation"),
    code(_EX5_STUB),
    code(_FRAG_AGENT),
    md("## Automated checks"),
    code(_EX5_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _FRAG_AGENT + "```\n\n"
       "**Why separate `plan` and `execute`?** You might want to inspect — or even "
       "edit — the task list before running it. Keeping them separate costs nothing "
       "and gives you the hook you need for human review. Day 87 will put an "
       "approval gate right at this seam.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_05.ipynb", EX5)

# ── YAML lessons ──────────────────────────────────────────────────────────────
_LESSON_01 = """\
day: "083"
lesson: 1
title: "Decomposing a Goal into Tasks"
slides:
  - type: title
    heading: "Planning & Decomposition"
    subheading: "Break a complex goal into an ordered list of subtasks"
    narration: >
      Days 79 through 82 gave an agent tools, reasoning, and memory. But every one
      of those agents tackled one task at a time. Today's new skill is decomposition:
      given a complex goal, break it into an ordered list of subtasks, resolve their
      dependencies, and execute them step by step. This is how a planner agent turns
      an ambitious goal into something an agent can actually execute.

  - type: concept
    label: "Why decompose"
    heading: "One Goal, Many Steps"
    body: >
      Complex goals need to be broken down before they can be executed.
    bullets:
      - "Direct execution: the model tries everything at once, gets confused"
      - "Decomposition: ordered list of concrete, doable subtasks"
      - "Each subtask feeds the next - results propagate forward"
      - "Dependencies make the order explicit (not guessed)"
      - "A plan is a program; the planner is the compiler"
    narration: >
      When you hand a complex goal directly to a language model in one shot, it tends
      to try to do everything at once - and gets tangled. Decomposition breaks that
      goal into concrete, doable subtasks, each small enough to tackle individually.
      The results of one step feed forward into the next, so Write summary knows what
      Gather facts found. Dependencies make the order explicit and checkable: the plan
      is a little program, and the planner is the compiler that turns a goal into
      something executable.

  - type: code
    label: "Task dataclass"
    heading: "Representing One Step"
    code: |
      from dataclasses import dataclass, field

      @dataclass
      class Task:
          id: str
          title: str
          description: str
          depends_on: list = field(default_factory=list)
          status: str = "pending"   # pending | done | failed
          result: str = ""
    narration: >
      A Task is five fields. The id is what other tasks reference in their
      depends_on list - it is the dependency graph's node label. The title and
      description say what to do in human terms. depends_on is the list of ids that
      must finish first - it is the edges of the dependency graph. status and result
      are updated as execution proceeds. This small dataclass is the shared currency
      of the whole day: planning returns a list of Tasks, sorting reorders them,
      execution fills in result and status.

  - type: code
    label: "parse_plan"
    heading: "Tolerant Parsing - Never Crashes"
    code: |
      def parse_plan(text):
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
    narration: >
      parse_plan is the same tolerant pattern as every Day 79 to 82 parser: find
      the JSON, parse it, and handle every failure case as data rather than raising.
      safe_parse_list finds the first square bracket to the last and parses - it
      handles fences and prose. For each item, missing fields get safe defaults rather
      than throwing a KeyError. The result is that parse_plan never raises - it
      returns an empty list on garbage, or a list of Tasks with whatever it could
      extract.

  - type: exercise
    heading: "Exercise 1: Task Representation and Parsing"
    prompt: >
      Build the Task dataclass (id, title, description, depends_on=[], status='pending',
      result=''); safe_parse_list (find '[' to ']', parse, return list or None, never
      raises); build_plan_prompt (system asks for a JSON array); and parse_plan (safe
      parse, fill missing fields with defaults, never raises).
    hint: >
      Task: use @dataclass with field(default_factory=list) for depends_on.
      safe_parse_list: same pattern as safe_parse_json but brackets. parse_plan:
      items = safe_parse_list(text) or []; for each dict item, Task(...get with
      defaults...).
    narration: >
      This builds the building blocks that every later function depends on.

  - type: summary
    heading: "Lesson 1 Summary"
    bullets:
      - "Decomposition breaks a goal into concrete, ordered subtasks"
      - "Task dataclass: id, title, description, depends_on, status, result"
      - "depends_on makes the dependency graph explicit"
      - "parse_plan: safe_parse_list -> Task per item, defaults for missing fields"
      - "Tolerant parsing never raises - empty or partial plans are still valid"
    narration: >
      Lesson 2 solves the ordering problem: given a task list with dependencies,
      find the right execution order with topological sort.
"""

_LESSON_02 = """\
day: "083"
lesson: 2
title: "Dependency Ordering with Topological Sort"
slides:
  - type: title
    heading: "Topological Sort"
    subheading: "Execute tasks in dependency order"
    narration: >
      The LLM may return tasks in any order. Executing them naively risks running
      Write summary before Gather facts exists. Topological sort is the classic
      algorithm that fixes this: given a directed acyclic graph of dependencies,
      it finds an order where every dependency comes before the task that needs it.
      This lesson builds topo_sort using Kahn's BFS algorithm.

  - type: concept
    label: "The problem"
    heading: "Dependencies Define the Order"
    body: >
      A plan is a directed graph; topological sort finds a valid traversal.
    bullets:
      - "t1 -> t2 -> t3: t2 needs t1's result; t3 needs t2's result"
      - "Diamond: t1 -> t2, t1 -> t3, t2+t3 -> t4 (fan-out then fan-in)"
      - "Cycle: t1 depends on t2, t2 depends on t1 (impossible to satisfy)"
      - "Topo sort: any valid ordering where deps always come first"
      - "Multiple valid orderings may exist (t2 and t3 can swap in the diamond)"
    narration: >
      A plan is a directed acyclic graph - each task is a node, each dependency is
      a directed edge. Topological sort walks this graph and returns a linear order
      where for every edge from A to B, A comes before B in the output. For a linear
      chain t1 to t2 to t3, there is one valid order. For a diamond with two parallel
      branches, either branch can go first - topological sort finds one of the valid
      orderings. Cycles are impossible to satisfy, and the next slide covers how to
      handle them gracefully.

  - type: code
    label: "Kahn's algorithm"
    heading: "Kahn's Algorithm - BFS on the DAG"
    code: |
      def topo_sort(tasks):
          by_id = {t.id: t for t in tasks}
          in_deg = {t.id: 0 for t in tasks}
          for t in tasks:
              for dep in t.depends_on:
                  if dep in in_deg:
                      in_deg[t.id] += 1
          queue = [t.id for t in tasks if in_deg[t.id] == 0]
          order = []
          while queue:
              tid = queue.pop(0)
              order.append(by_id[tid])
              for t in tasks:
                  if tid in t.depends_on:
                      in_deg[t.id] -= 1
                      if in_deg[t.id] == 0:
                          queue.append(t.id)
          done_ids = {t.id for t in order}
          for t in tasks:
              if t.id not in done_ids:
                  order.append(t)
          return order
    narration: >
      Kahn's algorithm counts incoming edges - how many unresolved dependencies each
      task has. Tasks with zero incoming edges have nothing to wait for; they go into
      the starting queue. Each time a task is emitted, it decrement the count for
      every task that depended on it. When a task's count hits zero, all its deps
      have been emitted and it joins the queue. The cycle guard at the end appends
      any tasks that never made it to zero - their counts never drained because the
      cycle kept them permanently blocked.

  - type: concept
    label: "Cycle guard"
    heading: "Cycles: Append, Don't Raise"
    body: >
      A cycle is a plan error - but not a crash.
    bullets:
      - "t1 depends on t2, t2 depends on t1 - in_deg never drains"
      - "Neither joins the queue; neither is emitted"
      - "Cycle guard: append remaining tasks at the end"
      - "Result: the non-cyclic portion still executes correctly"
      - "The cyclic tasks run last in original order - better than being dropped"
    narration: >
      A cycle in the dependency graph is a planning error - two tasks that each need
      the other to go first. Kahn's algorithm detects this naturally: the cyclic tasks
      never reach zero incoming edges, so they never join the queue, so they are never
      emitted. Raising on a cycle would stop the whole plan. Instead, appending the
      remaining tasks at the end lets the non-cyclic portion execute correctly, and
      the cycle victims at least run in some order. Execution that gets 90 percent of
      the plan right is better than execution that stops at the first cycle.

  - type: exercise
    heading: "Exercise 2: Topological Sort"
    prompt: >
      Implement topo_sort(tasks) using Kahn's algorithm: build an in-degree dict,
      seed a queue with zero-in-degree tasks, emit and drain in BFS order, then
      append any remaining tasks (cycle guard). Returns list[Task]; never raises.
    hint: >
      in_deg = {t.id: 0}; for each task, for each dep in depends_on: if dep in in_deg:
      in_deg[t.id] += 1. queue = [t.id for t in tasks if in_deg[t.id] == 0].
      After BFS: append tasks whose id is not in done_ids.
    narration: >
      This is the scheduler that makes the plan executable rather than just a list.

  - type: summary
    heading: "Lesson 2 Summary"
    bullets:
      - "A plan is a DAG; topo sort finds a valid execution order"
      - "Kahn's algorithm: count incoming edges, BFS from zero-in-degree tasks"
      - "Cycle guard: append cyclic tasks at the end, never raise"
      - "Result: dependencies always execute before the tasks that need them"
      - "Multiple valid orderings exist for parallel branches - any is fine"
    narration: >
      Lesson 3 executes the sorted tasks one at a time, feeding prior results
      forward into each step.
"""

_LESSON_03 = """\
day: "083"
lesson: 3
title: "Executing Tasks Step by Step"
slides:
  - type: title
    heading: "Executing the Plan"
    subheading: "Run each task and pass its result to the next"
    narration: >
      The plan is sorted. Now execute it. This lesson builds two functions: one that
      packages prior results into the prompt for the current task, and one that runs
      a task - using an injected executor or the LLM - and captures any exception as
      a result string rather than a crash.

  - type: concept
    label: "Context injection"
    heading: "Results Propagate Forward"
    body: >
      Each task needs the outputs of its dependencies.
    bullets:
      - "results dict: {task_id: result_string} grows as tasks complete"
      - "build_execution_context: render prior results for depends_on ids"
      - "Task gets: prior results + its own title and description"
      - "Same injection principle as Day 82 working memory in the prompt"
      - "Only the relevant deps are injected - not every task's result"
    narration: >
      As each task completes, its result goes into a running dict keyed by task id.
      When the next task starts, build_execution_context looks at its depends_on list
      and injects just those results - the facts from the earlier steps that this task
      actually needs. This is the same idea as Day 82's recall: putting the right
      context in front of the model at the right time. Only injecting the relevant
      deps keeps the prompt small and focused rather than pasting in every prior
      result.

  - type: code
    label: "execute_task"
    heading: "Two Modes: executor_fn or LLM"
    code: |
      def execute_task(task, results, executor_fn=None, llm_fn=None):
          try:
              if executor_fn is not None:
                  return str(executor_fn(task))
              context = build_execution_context(task, results)
              messages = [{"role": "system", "content": context},
                          {"role": "user", "content": "Execute this task now."}]
              return call_llm(messages, llm_fn=llm_fn)
          except Exception as exc:
              return "Error: " + str(exc)
    narration: >
      execute_task has two modes. If executor_fn is provided, call it - this is the
      gate mode, where a deterministic mock replaces all model calls. Otherwise build
      the execution prompt with prior context and call the LLM. Either way, the whole
      thing is wrapped in try-except: if a tool throws or the model returns something
      unparseable, the result is an Error string rather than an exception that stops
      the whole plan. The plan runner sees that string, records it, and continues.

  - type: concept
    label: "Fail as data"
    heading: "A Failed Task is Data, Not a Crash"
    body: >
      An error in one task should not stop the whole plan.
    bullets:
      - "execute_task: exceptions -> 'Error: ...' result string"
      - "task.status is still marked 'done' (it ran; it just failed)"
      - "The next task sees the error string as its dep's result"
      - "The plan records what went wrong without stopping"
      - "This is the same principle as Day 79's execute_tool"
    narration: >
      When a task fails, the plan has a choice: stop, or record the failure and
      continue. Stopping is the safe choice when tasks are strictly sequential and
      one failure makes all later steps meaningless. But in many plans a failed step
      is still information - the next task can see the error string and respond to it.
      Returning the error as a result keeps the plan moving and gives you a complete
      record of what worked and what did not. Day 87 will add proper guardrails for
      deciding when to stop and when to continue.

  - type: exercise
    heading: "Exercise 3: Executing One Task"
    prompt: >
      Implement build_execution_context(task, results): render prior results for
      each dep in task.depends_on (if present in results), then state the task title
      and description. Implement execute_task(task, results, executor_fn=None,
      llm_fn=None): use executor_fn if provided, else call_llm with the context;
      wrap everything in try/except and return 'Error: ...' on failure.
    hint: >
      build_execution_context: lines = [...]; for dep in task.depends_on: if dep in
      results: append "dep: result". execute_task: try: if executor_fn is not None:
      return str(executor_fn(task)); else build context + call_llm. except Exception
      as exc: return 'Error: ' + str(exc).
    narration: >
      These two functions are the workhorse of plan execution - context in, result
      out, never crashes.

  - type: summary
    heading: "Lesson 3 Summary"
    bullets:
      - "results dict grows as tasks complete: {id: result_string}"
      - "build_execution_context injects relevant deps into the task prompt"
      - "execute_task: executor_fn for the gate, LLM fallback for production"
      - "try/except: a failed task returns 'Error: ...' not an exception"
      - "Failed tasks are recorded, not dropped - the plan continues"
    narration: >
      Lesson 4 chains these pieces into run_plan - the end-to-end orchestrator.
"""

_LESSON_04 = """\
day: "083"
lesson: 4
title: "run_plan - End to End"
slides:
  - type: title
    heading: "run_plan"
    subheading: "Plan, sort, execute - one call"
    narration: >
      The three pieces are ready: a prompt to decompose the goal, a sort to resolve
      dependencies, and a step executor that feeds results forward. run_plan chains
      them together: one function that takes a goal and returns the completed tasks,
      all results, and the final answer - with a max_tasks guard so a runaway plan
      cannot hang the gate.

  - type: code
    label: "run_plan"
    heading: "The Full Orchestrator"
    code: |
      def run_plan(goal, executor_fn=None, llm_fn=None, max_tasks=20):
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
    narration: >
      run_plan is short because the hard work lives in the pieces it calls. One
      model call generates the plan; parse_plan tolerates any mess; topo_sort
      resolves the order; the loop feeds results forward; the final answer is the
      last task's result. The cap at max_tasks happens before sorting - so a model
      that hallucinates a hundred tasks can't cause a hundred LLM calls. Empty plan
      has a clear fallback. Every failure mode returns data rather than raising.

  - type: concept
    label: "max_tasks"
    heading: "The max_tasks Safety Guard"
    body: >
      Cap the plan length before execution.
    bullets:
      - "A misbehaving model can return arbitrarily long task lists"
      - "Each task triggers an LLM call or executor call"
      - "Cap at max_tasks (default 20) before sorting"
      - "Sorting 5 tasks is trivial; sorting 1000 tasks wastes time"
      - "Same principle as max_iterations on the agent loops"
    narration: >
      The max_tasks cap is the planning equivalent of max_iterations on the agent
      loop. A language model can return a plan with thirty tasks when five would do,
      or a hundred tasks when it misunderstands the goal. Each task triggers an
      executor or LLM call. Capping before sorting and before execution bounds both
      the sort cost and the execution cost. Twenty is a sensible default for most
      goals - more than that and the plan is probably not well-decomposed.

  - type: exercise
    heading: "Exercise 4: run_plan"
    prompt: >
      Implement run_plan(goal, executor_fn=None, llm_fn=None, max_tasks=20):
      build_plan_prompt -> call_llm -> parse_plan -> cap at max_tasks -> topo_sort ->
      execute loop (execute_task, update task.result/status, results[id]). Return
      {tasks, results, answer}. If no tasks, return a safe fallback.
    hint: >
      tasks = parse_plan(plan_text); if not tasks: return the empty-plan dict.
      ordered = topo_sort(tasks[:max_tasks]); results = {}. For each task in ordered:
      result = execute_task(...); task.result = result; task.status = 'done';
      results[task.id] = result. answer = ordered[-1].result.
    narration: >
      This is the complete plan runner - a goal goes in, a finished plan comes out.

  - type: summary
    heading: "Lesson 4 Summary"
    bullets:
      - "run_plan = plan -> sort -> execute loop, one function"
      - "max_tasks caps before sorting so a long list cannot hang execution"
      - "Empty plan -> safe fallback dict (no crash)"
      - "Returns {tasks, results, answer} - same shape every time"
      - "answer = the last task's result in execution order"
    narration: >
      Lesson 5 wraps run_plan in PlannerAgent and separates plan from execute so you
      can inspect the task list before committing to it.
"""

_LESSON_05 = """\
day: "083"
lesson: 5
title: "PlannerAgent - The Planning Assistant"
slides:
  - type: title
    heading: "PlannerAgent"
    subheading: "Plan, inspect, then execute"
    narration: >
      The final piece is PlannerAgent. It wraps run_plan in the same class shape as
      SimpleAgent, ReactAgent, ToolAgent, and MemoryAgent - bind the dependencies at
      construction, delegate the work, keep a history. The key addition is the split
      between plan and execute: you can generate the task list, review it, and only
      then run it - an early form of human oversight that Day 87 will formalize as a
      guardrail.

  - type: code
    label: "PlannerAgent"
    heading: "Plan Separately from Execute"
    code: |
      class PlannerAgent:
          def __init__(self, executor_fn=None, llm_fn=None, max_tasks=20):
              self._executor_fn = executor_fn
              self._llm_fn = llm_fn
              self.max_tasks = max_tasks
              self._history = []

          def plan(self, goal):
              plan_text = call_llm(build_plan_prompt(goal), llm_fn=self._llm_fn)
              return topo_sort(parse_plan(plan_text)[:self.max_tasks])

          def execute(self, tasks):
              ordered = topo_sort(tasks[:self.max_tasks])
              results = {}
              for task in ordered:
                  result = execute_task(task, results,
                                        executor_fn=self._executor_fn,
                                        llm_fn=self._llm_fn)
                  task.result = result; task.status = "done"
                  results[task.id] = result
              return results

          def run(self, goal):
              tasks = self.plan(goal)
              results = self.execute(tasks)
              answer = tasks[-1].result if tasks else "No tasks."
              record = {"goal": goal, "tasks": tasks,
                        "results": results, "answer": answer}
              self._history.append(record)
              return record
    narration: >
      PlannerAgent has three public methods beyond history and clear_history. plan
      returns the sorted task list without running any of them - you can print it,
      edit it, or pass it to a different executor. execute takes any task list and
      runs it - not just plans that plan generated. run does both and records the
      outcome. This split is deliberate: a plan you can inspect before execution is
      a plan you can trust, and trust is the foundation of Day 87's guardrails.

  - type: concept
    label: "Five agents, one shape"
    heading: "The Section's Class Pattern, Again"
    body: >
      Five agents, five days, one skeleton.
    bullets:
      - "Day 79 SimpleAgent: action loop"
      - "Day 80 ReactAgent: reasoning loop with trace"
      - "Day 81 ToolAgent: one-shot routing"
      - "Day 82 MemoryAgent: extract / recall / remember"
      - "Day 83 PlannerAgent: decompose / sort / execute"
      - "All: bind at construction, delegate, keep history copy"
    narration: >
      Five agents in five days, and the shape has stayed the same: bind at
      construction, delegate the hard work to module functions, keep a history, and
      return a copy of it. What changes is the engine. SimpleAgent had a bare loop.
      ReactAgent added reasoning and a trace. ToolAgent routed to one of many tools.
      MemoryAgent learned to store and recall. PlannerAgent decomposes a goal into
      steps and executes them in order. Each day adds a new capability while keeping
      the handle familiar.

  - type: exercise
    heading: "Exercise 5: PlannerAgent"
    prompt: >
      Implement PlannerAgent(executor_fn=None, llm_fn=None, max_tasks=20):
      plan(goal) -> sorted task list without executing; execute(tasks) -> {id:result}
      dict running tasks in order; run(goal) -> plan+execute, record in history,
      return {goal,tasks,results,answer}; history() copy; clear_history() in-place.
    hint: >
      plan: topo_sort(parse_plan(call_llm(build_plan_prompt(goal), llm_fn=self._llm_fn))[:max_tasks]).
      execute: same as run_plan's loop but takes tasks directly. run: tasks=plan(goal);
      results=execute(tasks); answer=tasks[-1].result if tasks else 'No tasks.'.
    narration: >
      This completes the planning assistant - give it a goal and it returns a finished
      plan.

  - type: summary
    heading: "Lesson 5 Summary - Day 83 Complete"
    bullets:
      - "PlannerAgent: plan / execute / run — separate concerns"
      - "plan() returns the task list without running it (inspect first)"
      - "execute() takes any task list - not just plans that plan() made"
      - "run() = plan + execute + record history"
      - "Five Section 6 agents, all the same class shape"
    narration: >
      Your agent can now break any goal into steps and execute them in dependency
      order. Day 84 gives the next level: multiple agents collaborating - a
      researcher and a writer working in sequence, each a specialist in its role.
"""

for i, content in enumerate([_LESSON_01, _LESSON_02, _LESSON_03,
                               _LESSON_04, _LESSON_05], start=1):
    (OUT / "lessons" / f"day_{DAY}_lesson_0{i}.yaml").write_text(content)

# ── PROJECT NOTEBOOK ──────────────────────────────────────────────────────────
PROJECT = nb([
    md(f"# Day {DAY} — Project: A Planning Agent\n\n"
       "## Objective\n\n"
       "Build `planner_agent.py` — an agent that breaks a complex goal into an "
       "ordered list of subtasks and executes them step by step.\n\n"
       "## Deliverable\n\n"
       "`planner_agent.py` with:\n\n"
       "- `safe_parse_list(text)` — list-aware tolerant JSON parser\n"
       "- `Task` dataclass — `id, title, description, depends_on, status, result`\n"
       "- `build_plan_prompt(goal, context=None)` / `parse_plan(text)`\n"
       "- `topo_sort(tasks)` — Kahn's topological sort, cycle-tolerant\n"
       "- `build_execution_context(task, results)` / `execute_task(...)`\n"
       "- `run_plan(goal, executor_fn=None, llm_fn=None, max_tasks=20)`\n"
       "- `PlannerAgent(executor_fn=None, llm_fn=None, max_tasks=20)` with "
       "`plan / execute / run / history / clear_history`\n\n"
       "## Usage (with Ollama running + llama3.2 pulled)\n\n"
       "```python\n"
       "from planner_agent import PlannerAgent\n"
       "agent = PlannerAgent()\n"
       "result = agent.run('Write a short blog post about topological sort')\n"
       "for task in result['tasks']:\n"
       "    print(f'{task.id}: {task.title}')\n"
       "print(result['answer'])\n"
       "```\n\n"
       "**The deliverable:** you give the agent a complex goal, it returns an ordered "
       "task list with each result filled in — and the final answer is the last "
       "task's output. Inspect the plan before it runs; edit it if you want. That "
       "separation is what makes a planner agent trustworthy."),
    code("# Your implementation here — build planner_agent.py\n"),
])
save(OUT / "project" / "project.ipynb", PROJECT)

# ── SOLUTION NOTEBOOK ─────────────────────────────────────────────────────────
_SOL_CELL1 = (
    f"_SRC = {repr(_PLANNER_AGENT_SRC)}\n"
    "from pathlib import Path\n"
    "Path('planner_agent.py').write_text(_SRC, encoding='utf-8')\n"
    "print('planner_agent.py written.')"
)

_SOL_CELL2 = r"""
import json
from planner_agent import (
    Task, safe_parse_list, build_plan_prompt, parse_plan,
    topo_sort, build_execution_context, execute_task,
    run_plan, PlannerAgent,
)

_PLAN_JSON = json.dumps([
    {'id': 't1', 'title': 'Gather facts',
     'description': 'Collect the relevant information.', 'depends_on': []},
    {'id': 't2', 'title': 'Draft outline',
     'description': 'Organize the facts into an outline.', 'depends_on': ['t1']},
    {'id': 't3', 'title': 'Write summary',
     'description': 'Write the final summary.', 'depends_on': ['t2']},
])

def _mock_planner(plan_json=None, task_result='Task done.'):
    plan = plan_json if plan_json is not None else _PLAN_JSON
    def _fn(messages):
        system = messages[0]['content'] if messages else ''
        return plan if 'json array' in system.lower() or 'planning' in system.lower() else task_result
    return _fn

def _mock_executor(task):
    return 'Result: ' + task.title

# 1. Task + safe_parse_list + parse_plan
t = Task(id='x', title='T', description='d')
assert t.status == 'pending' and t.result == '' and t.depends_on == []
assert safe_parse_list('[1,2,3]') == [1, 2, 3]
assert safe_parse_list('{}') is None and safe_parse_list('no json') is None
tasks = parse_plan(_PLAN_JSON)
assert len(tasks) == 3 and tasks[1].depends_on == ['t1']
assert parse_plan('garbage') == []
print("✅ Task / safe_parse_list / parse_plan")

# 2. topo_sort
ordered = topo_sort(tasks)
ids = [t.id for t in ordered]
assert ids.index('t1') < ids.index('t2') < ids.index('t3')
diamond = [
    Task('base','B','b'), Task('d1','D1','d',depends_on=['base']),
    Task('d2','D2','d',depends_on=['base']),
    Task('final','F','f',depends_on=['d1','d2']),
]
di = topo_sort(diamond); di_ids = [t.id for t in di]
assert di_ids.index('base') < di_ids.index('final')
cycle = [Task('x','X','x',depends_on=['y']), Task('y','Y','y',depends_on=['x'])]
assert len(topo_sort(cycle)) == 2          # cycle guard: both returned
print("✅ topo_sort (chain, diamond, cycle guard)")

# 3. build_execution_context + execute_task
t2 = Task('t2','Step2','do',depends_on=['t1'])
ctx = build_execution_context(t2, {'t1': 'step1 done'})
assert 'step1 done' in ctx and 'Step2' in ctx
assert execute_task(Task('x','X','x'), {}, executor_fn=_mock_executor) == 'Result: X'
assert execute_task(Task('x','X','x'), {}, llm_fn=_mock_planner(task_result='llm reply')) == 'llm reply'
def _bad(t): raise RuntimeError('boom')
assert execute_task(Task('x','X','x'), {}, executor_fn=_bad).startswith('Error:')
print("✅ build_execution_context / execute_task (inject, executor, LLM, exception guard)")

# 4. run_plan
r = run_plan('test', executor_fn=_mock_executor, llm_fn=_mock_planner())
assert len(r['tasks']) == 3 and r['tasks'][0].status == 'done'
assert r['results']['t2'] == 'Result: Draft outline'
assert r['answer'] == 'Result: Write summary'
assert run_plan('x', executor_fn=_mock_executor,
                llm_fn=_mock_planner(plan_json='no json'))['tasks'] == []
print("✅ run_plan (end-to-end, results, answer, empty plan)")

# 5. PlannerAgent
agent = PlannerAgent(executor_fn=_mock_executor, llm_fn=_mock_planner())
plan_tasks = agent.plan('test')
assert len(plan_tasks) == 3 and all(t.status == 'pending' for t in plan_tasks)
results = agent.execute(plan_tasks)
assert plan_tasks[0].status == 'done' and results['t1'] == 'Result: Gather facts'
record = agent.run('another goal')
assert 'goal' in record and record['answer'] == 'Result: Write summary'
assert len(agent.history()) == 1
agent.history().clear(); assert len(agent.history()) == 1  # copy
agent.clear_history(); assert len(agent.history()) == 0
print("✅ PlannerAgent (plan/execute/run/history/clear_history)")

print("\nPlanning agent complete!")
"""

SOLUTION = nb([
    md(f"# Day {DAY} — Solution: A Planning Agent"),
    code(_SOL_CELL1),
    code(_SOL_CELL2),
])
save(OUT / "project" / "solution" / "solution.ipynb", SOLUTION)
(OUT / "project" / "solution" / "planner_agent.py").write_text(_PLANNER_AGENT_SRC)

print(f"Day {DAY} notebooks written to {OUT}")
print("  lessons/    day_083_lesson_01.yaml – lesson_05.yaml")
print("  exercises/  exercise_01 – exercise_05")
print("  project/    project.ipynb")
print("  project/solution/  solution.ipynb + planner_agent.py")
