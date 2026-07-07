# Adversarial Review Checklist (safety precaution #3)

The mandate for the per-day **review pass** — a critic with fresh eyes whose only
job is to *attack* a freshly-authored day and find what's wrong. Run this after
`check_day.py` is green (structure + execution already pass), before human review.

The reviewer did NOT author the day. Its bias is to find fault, not to approve.
Default to "flag it" when unsure — a false alarm costs a glance; a missed error
compounds across every day that builds on it.

## What to attack

**1. Factual correctness (highest priority — this is where hallucination hides)**
- Every named API / function / class / library / model — is the signature real
  and current? (e.g. Ollama client call shape, pandas method names, stdlib usage)
- Any code that looks plausible but wouldn't run or would behave differently.
- Version-specific claims that may be stale.

**2. Coherence vs the rest of the course**
- Does this day repeat a concept already taught? (cross-check `SYLLABUS.md` + `CONCEPTS.md`)
- Does it use a concept/library that hasn't been introduced yet? (check `CONCEPTS.md`
  for all earlier days — nothing may be used before it's taught)
- Does the difficulty jump too far from the previous day?

**3. Pedagogy**
- Is each concept actually *explained*, or just asserted?
- Does the narration add understanding, or just restate the slide text?
- Would a learner at this point in the course be able to follow it?

**4. Internal consistency**
- Do the exercises test what the lessons taught?
- Does the project compose the day's concepts into the promised deliverable?
- Do the automated checks actually verify the right thing (not pass for wrong reasons)?

**5. Zero-cost / local constraint**
- Any reliance on a paid API sneaking in? Everything must run free/local (Ollama etc.).

## Output format

A findings list, each: `[severity: blocker|warn|nit] <file/lesson> — <the problem> — <fix>`.
End with a one-line verdict: **SHIP** (no blockers) or **REWORK** (blockers listed).
The author then addresses every blocker and re-runs `check_day.py` before human review.
