# Day Authoring Template

The source-of-truth spec for authoring every day of the course. Day 1 established
this shape; every day follows it so the 100 days stay consistent and I don't
reinvent the format each session.

> **Golden rule:** every day ends in *something that runs*. If a learner can't
> execute a working artifact by the end of the day, the day isn't done.

---

## 1. Anatomy of a Day

Each day (`day_NNN`) is made of four parts:

| Part | Where it lives | Purpose |
|------|----------------|---------|
| **Lessons** (4–6) | `<section>/day_NNN/lessons/day_NNN_lesson_XX.yaml` | The taught content → becomes the videos |
| **Exercises** (1 per lesson concept) | `<section>/day_NNN/exercises/exercise_XX.ipynb` | Hands-on practice with automated tests |
| **Project** (1) | `<section>/day_NNN/project/project.ipynb` | The day's real, runnable deliverable |
| **Solution** (1) | `<section>/day_NNN/project/solution/solution.ipynb` | Reference build, revealed after attempt |

Lesson count flexes **4–6** by topic weight (Day 1 = 5). Simpler days can be 4;
dense days 6. Never fewer than 4, never more than 6 — keeps daily runtime ~1 hour.

---

## 2. Lesson YAML schema

Each lesson is one YAML file. Top keys:

```yaml
day: "NNN"
lesson: "XX"
title: "Short lesson title"
slides:
  - type: <slide_type>
    ...fields per type...
    narration: >    # ALWAYS present except pure title — this is the spoken track
```

**Slide types** (use in roughly this arc):

| type | Role | Key fields |
|------|------|-----------|
| `title` | Opens the lesson | `heading`, `subheading`, `narration` |
| `concept` | Explains an idea / the "why" | `label`, `heading`, `body`, optional `bullets`, `narration` |
| `how_it_works` | Mechanism of a tool/API | `label`, `heading`, `body`, `narration` |
| `code` | Shows real code | `label`, `heading`, `code`, `narration` |
| `exercise` | Hands off to a notebook | `heading`, `prompt`, `hint`, `narration` |
| `summary` | Locks in takeaways + teases next | `heading`, `bullets`, `narration` |

**Standard lesson arc:** `title → concept(s) → how_it_works/code → exercise → summary`
(8–9 slides is the Day 1 norm; aim for that.)

**Narration rules:**
- `body`/`bullets` = terse on-slide text. `narration` = the fuller spoken version.
- Narration is conversational, ~60–100s of speech per slide, second person ("you").
- Never read the slide verbatim — narration expands and explains.

---

## 3. Exercise notebook structure

Every exercise notebook follows this cell order (from Day 1's proven shape):

1. **Markdown** — `# Day N · Exercise X: <name>` + **What you'll build** + **Why it matters**
2. **Markdown** — `## Your Implementation`
3. **Code** — starter code: function signature + full docstring (Args/Returns), body left `# TODO`
4. **Markdown** — `## Check Your Work` (explains the auto-checks)
5. **Code** — **automated checks**: 3–5 assertions printing ✅/❌ per check + a score
6. **Markdown** — `## Bonus Challenge` (optional stretch, ties to a later day)
7. **Markdown** — `## Solution` inside `<details>` collapsible, with a **"Why this works"** explainer

The **automated checks are non-negotiable** — they're how the course teaches
testing instead of vibecoding. Learners get objective pass/fail, not vibes.

Two hard rules for the checks harness (both caught by `run_day.py` #1):
- **Use top-level `await`, never `asyncio.run(...)`** — checks run inside a
  Jupyter kernel, which already has a running event loop, so `asyncio.run()`
  raises. If the checks are async, end the cell with `await _run_checks()`.
- **Degrade gracefully when the implementation is incomplete** — a learner runs
  the checks *before* finishing. A foundational check that fails (e.g. no output
  file created) must `return`, so later checks don't crash with an uncaught
  exception (e.g. `os.path.getsize` on a missing file). All checks show ❌, none
  throw.

---

## 4. Project notebook structure

1. **Markdown** — `# Day N Project: <name>` + **What You're Building** + the concrete
   deliverable stated plainly ("You run it, it produces X. That's the deliverable.")
2. **Code** — `# Your implementation here` (mostly empty; they build from scratch)
3. A matching **solution.ipynb** with the full working build + commentary.

The project **composes the day's lesson concepts** into one working thing.

---

## 5. Difficulty ramp (coherence across 100 days)

- **Sequential dependency:** a day may only assume concepts from **earlier** days.
  Never use something before it's been taught.
- **Section arc:** Warmup (1–5) → Text AI (6–20) → Automation (21–35) →
  Data & Analysis (36–50) → Real Apps (51–65) → Vision & Multimodal (66–78) →
  Agents (79–88) → Finance/Trading & Productizing (89–100).
- **Systematic-engineering thread** runs throughout: tests, schemas, logging,
  git, error handling — reinforced a little more each section, not front-loaded.
- **No repeats:** the master syllabus (see §6) is the single record of what each
  day covers. Check it before authoring so Day 40 doesn't re-teach Day 22.

---

## 6. The master syllabus (built once, next)

Before mass authoring, we build `SYLLABUS.md`: one row per day —
`day | title | objective (1 line) | key concepts | project deliverable`.
This is the coherence backbone. Every day's authoring **reads from it first**,
so difficulty ramps correctly and nothing repeats. It's reviewed and locked
before we sprint.

---

## 7. Naming conventions

- Days: `day_001` … `day_100` (zero-padded to 3).
- Lessons: `day_NNN_lesson_XX` (zero-padded to 2).
- Section folders already exist: `00_warmup`, `01_text_ai`, `02_automation`,
  `03_data_analysis`, `04_real_apps`, `05_vision_multimodal`, `06_ai_agents`,
  `07_finance_trading`.
- Voice: Edge TTS `en-US-JennyNeural`. FPS 25. (Pipeline handles rendering.)

---

## 8. Per-day authoring checklist (what I produce each time)

- [ ] Re-read the day's row in `SYLLABUS.md` + the 2 prior days for continuity
- [ ] 4–6 lesson YAMLs following the arc in §2
- [ ] 1 exercise notebook per lesson concept, with automated checks (§3)
- [ ] 1 project notebook + 1 solution notebook (§4)
- [ ] Verify every named API/library/model against real docs — don't trust memory
- [ ] Confirm no concept is used before it's taught
