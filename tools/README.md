# Authoring Guardrails (`tools/`)

The five safety precautions that gate every authored day, so mistakes are caught
by machines and fresh eyes before they reach human review — and before they
compound across the 100 days. See `../AUTHORING_TEMPLATE.md` for the day shape and
`../SYLLABUS.md` for the curriculum backbone.

## The tools

| Tool | Precaution | What it checks |
|------|-----------|----------------|
| `validate_day.py` | #2 structure | Deterministic: lesson count, YAML keys, narration, slide arc, exercise/project/solution presence, naming. Hard-fails on any violation. |
| `run_day.py` | #1 execute + render | Runs slides+audio through the pipeline; executes the project solution (must be clean) and every exercise (harness must not crash); and **verifies each exercise's embedded solution passes its own checks** (proves it's solvable, not just non-crashing). |
| `check_day.py` | #1 + #2 | Orchestrator — the single gate. Runs validate then run, one report. |
| `REVIEW_CHECKLIST.md` | #3 adversarial review | Mandate for the fresh-eyes critic pass (correctness, coherence, pedagogy). |
| `../CONCEPTS.md` | #5 concepts ledger | Record of what each day introduces, so nothing is used before it's taught. |
| `../requirements.txt` | #5 pinned deps | Free/local only; core vs per-section; `pip freeze > requirements.lock.txt` to pin. |

## The per-day gate

```
author Day NNN
  → python tools/check_day.py NNN        # #1 execute+render + #2 structure — must be GREEN
  → adversarial review (REVIEW_CHECKLIST) # #3 fresh-eyes critic — fix blockers, re-run check
  → human review                          # is it genuinely good teaching?
  → git commit "Day NNN: <title>"         # #4 one commit per verified day = clean rollback point
  → update SYLLABUS status line + CONCEPTS.md   # #5 keep the ledger + progress current
```

Quick commands:
```
conda activate ai-course
python tools/validate_day.py 2        # structure only (instant)
python tools/check_day.py 2           # full gate
python tools/check_day.py 2 --fast    # skip slow TTS audio while iterating
python tools/check_day.py 2 --no-exec # structure + render, skip notebook execution
```

## Section-boundary reminder

When `check_day.py` passes on the **last day of a section** (Days 5, 20, 35, 50,
65, 78, 88, 100), it automatically prints a reminder to start a FRESH Claude
session for the next section, with the exact resume prompt to paste — e.g. after
Day 20 passes:

```
Continue authoring the course. Read AUTHORING_TEMPLATE.md and
SYLLABUS.md, then author Day 21.
```

Fresh-session-per-section resets context and avoids drift (safety precaution #1).

## #4 — commit convention

One commit per day, only after the gate is green **and** you've reviewed it:
`Day NNN: <title>`. Each day is then an independent, revertible checkpoint — if a
later day exposes a flaw in an earlier one, you roll back exactly one day.
