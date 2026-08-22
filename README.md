# 100 Days of AI — The Complete AI Engineering Bootcamp

A self-built, project-first AI engineering course. 100 projects, ~1 hour each, delivered as AI-generated videos (Edge TTS voice + Wav2Lip talking head + FFmpeg). Inspired by Angela Yu's 100 Days of Code bootcamp format.

## Format

Each day = 1 project you build and see working by the end of the session. No passive reading — every concept is taught through building.

Videos are generated via the pipeline in `00_pipeline/`: script → audio (Edge TTS) → talking head (Wav2Lip on Colab) → final video (FFmpeg).

## Environment

```bash
conda activate ai-course
```

## Taking a Lesson (video format)

Each `day_NNN/` folder has three parts:

- `lessons/` — 5 lesson outlines (`day_NNN_lesson_01..05.yaml`): slides + narration
- `exercises/` — 5 notebooks (`exercise_01..05.ipynb`), each with a self-checking test cell
- `project/` — `project.ipynb` you build, plus `project/solution/` to compare against

The intended experience is **video**: watch the 5 lesson videos for the day, do
each exercise when the lesson tells you to, then build the project.

**Prefer a browser?** There's a static course website in [`docs/`](docs/README.md)
that plays the lesson videos (YouTube) and opens each exercise/project in Google
Colab — so you can take the course from any browser without using your own
processor. Deploy it free on GitHub Pages; see [`docs/README.md`](docs/README.md).

### Watch (if the day is already rendered)

Rendered videos live in `00_pipeline/final/<lesson_id>_final.mp4`.

```bash
open 00_pipeline/final/day_001_lesson_01_final.mp4
```

> **Render status:** Day 1 is fully rendered (5 videos). Other days are written
> but not yet rendered to video — render them with the pipeline below before watching.

### Render a lesson to video

Three stages per lesson (repeat for each of the day's 5 lessons):

1. **Local — `--prep`:** slides + Edge TTS audio → `00_pipeline/audio/<lesson_id>.mp3`
   ```bash
   conda activate ai-course
   python 00_pipeline/lesson_build.py 00_warmup/day_001/lessons/day_001_lesson_01.yaml --prep
   ```
2. **Colab (T4 GPU) — talking head:** upload `00_pipeline/wav2lip_colab.ipynb` to
   <https://colab.research.google.com>, run setup cells 1–5 once, then cells 6→7→8
   per lesson. Download the result to `00_pipeline/talking_heads/<lesson_id>_talking_head.mp4`.
3. **Local — `--finalize`:** composite → `00_pipeline/final/<lesson_id>_final.mp4`
   ```bash
   python 00_pipeline/lesson_build.py 00_warmup/day_001/lessons/day_001_lesson_01.yaml --finalize
   ```

**Full step-by-step with every file path and Colab cell explained:
[`00_pipeline/RENDERING.md`](00_pipeline/RENDERING.md).**

> Prefer to read instead of watch? The `narration:` field in each lesson YAML is
> the full spoken script — read it top to bottom for the same content, no render.

## Course Structure

| Folder | Days | Theme |
|---|---|---|
| `00_warmup` | 1–5 | Python refresh + first AI API call |
| `01_text_ai` | 6–20 | Text AI |
| `02_automation` | 21–35 | Automation with AI |
| `03_data_analysis` | 36–50 | Data & Analysis |
| `04_real_apps` | 51–65 | Building Real Apps |
| `05_vision_multimodal` | 66–78 | Vision & Multimodal |
| `06_ai_agents` | 79–88 | AI Agents |
| `07_finance_trading` | 89–100 | Finance, Trading & Productizing |

## Progress

| Day | Project | Done |
|---|---|---|
| 1 | Video generation pipeline (TTS → Wav2Lip → FFmpeg) | [x] |
| 2 | | [ ] |
| 3 | | [ ] |
