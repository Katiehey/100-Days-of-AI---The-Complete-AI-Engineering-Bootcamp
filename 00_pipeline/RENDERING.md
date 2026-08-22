# Rendering a Lesson to Video

End-to-end steps to turn a lesson YAML into a watchable talking-head video.

**Pipeline:** `lesson YAML → slides + audio (local) → talking head (Colab GPU) → final composite (local)`

There are **3 stages**. Stages 1 and 3 run locally on your Mac; stage 2 (the
talking head) needs a GPU, so it runs on Google Colab. Do all three **once per
lesson** — a day has 5 lessons, so you repeat this 5 times per day.

> **Want zero local compute?** [`render_and_publish_colab.ipynb`](render_and_publish_colab.ipynb)
> runs **all three stages plus the YouTube upload entirely on Colab** — call
> `render_and_publish(day, lesson)` and your Mac does nothing. The stage-by-stage
> guide below is the local/hybrid path; use it when you want to run parts yourself.

Throughout, the worked example is **`day_001_lesson_05`**. This is the
`<LESSON_ID>` — the pattern is `day_<NNN>_lesson_<NN>` (zero-padded). Swap it for
whatever you're rendering.

---

## Stage 1 — Local: slides + audio

```bash
conda activate ai-course
python 00_pipeline/lesson_build.py 00_warmup/day_001/lessons/day_001_lesson_05.yaml --prep
```

`--prep` runs three sub-steps (you'll see `[1/3]`, `[2/3]`, `[3/3]` in the output):

1. Renders each slide from the YAML to a PNG.
2. Generates Edge TTS (Jenny voice) audio for each slide's `narration:`.
3. Concatenates the per-slide audio into one lesson MP3 and writes a timing manifest.

**Where things land:**

| Artifact | Path |
|---|---|
| Slide images | `00_pipeline/slides/day_001_lesson_05/slide_NNN.png` |
| Per-slide audio | `00_pipeline/audio/day_001_lesson_05/slide_NNN.mp3` |
| Timing manifest | `00_pipeline/audio/day_001_lesson_05/manifest.yaml` |
| **Full lesson audio** | **`00_pipeline/audio/day_001_lesson_05.mp3`** ← upload this to Colab |

The command prints the full-audio path and total duration at the end. That
`00_pipeline/audio/<LESSON_ID>.mp3` file is the only thing you carry to Colab.

---

## Stage 2 — Colab (GPU): the talking head

Open <https://colab.research.google.com>, then **File → Upload notebook** and pick
`00_pipeline/wav2lip_colab.ipynb`. Set the runtime:
**Runtime → Change runtime type → T4 GPU → Save**.

Wav2Lip takes a portrait + the MP3 and produces a lip-synced video by repainting
only the mouth region (minutes, not the hours SadTalker takes).

### Setup — run ONCE per Colab session (cells 1–5)

| Cell | What it does | Notes |
|---|---|---|
| **1** | `nvidia-smi` GPU check | Errors if you forgot to pick T4. Should show a **Tesla T4, 15360 MiB**. |
| **2** | Clone Wav2Lip fork + install deps (`numpy<2.0`, `librosa`, `opencv`, `numba`, `tqdm`, `batch-face`) | The red NumPy dependency-conflict warnings are expected and harmless — the pin to `numpy<2.0` is deliberate. |
| **2b** | Compatibility patches (librosa keyword args, `librosa.core.*`, NumPy alias removal) | Prints `Patches applied.` |
| **3** | Download model weights: `wav2lip_gan.pth` (lip-sync) + `mobilenet.pth` (RetinaFace face detector) into `checkpoints/` | ~415 MB + ~86 MB from the fork's GitHub releases. |
| **4** | Mount Google Drive; create `MyDrive/100DaysOfAI/{audio,videos}/` | Approve the Google auth popup. |
| **5** | Portrait setup | **First session:** uploads `Avatar.png` and saves it to Drive. **Later sessions:** reused from Drive automatically. Shows a 200px preview. |

> If the face detector errors, the detector weights are the usual cause. This fork
> can use either `mobilenet.pth` (RetinaFace, via the `batch-face` package — the
> default) or `s3fd.pth`. Cell 3 fetches `mobilenet.pth`; if you hit a detector
> error, also run `!wget -q 'https://github.com/justinjohn0306/Wav2Lip/releases/download/models/s3fd.pth' -O /content/Wav2Lip/face_detection/detection/sfd/s3fd.pth`.

### Per lesson — run cells 6 → 7 → 8

**Cell 6 — upload the audio.**
Click the picker and choose `00_pipeline/audio/day_001_lesson_05.mp3` from your Mac.
- Lands at `/content/day_001_lesson_05.mp3` in Colab.
- Mirrored to Drive at `MyDrive/100DaysOfAI/audio/day_001_lesson_05.mp3`.

**Cell 7 — run Wav2Lip.** Edit the one line at the top to match the file you just
uploaded (no `.mp3`):
```python
LESSON = 'day_001_lesson_05'
```
Then run. It loads the checkpoint, detects the face, and repaints the mouth frame
by frame. For an ~11-minute lesson expect roughly **5–10 minutes** on a T4
(the day_001_lesson_05 run: face-detect ~3s, prediction ~289s, then H.264 encode).
- **Output lands at `/content/results/day_001_lesson_05_talking_head.mp4`.**
- 1024×1536 portrait, H.264 + AAC. (~43 MB for lesson 5.)

**Cell 8 — save to Drive + preview.** Copies the result to Drive and shows an
inline player.
- **Saved to `MyDrive/100DaysOfAI/videos/day_001_lesson_05_talking_head.mp4`.**

> To render another lesson in the same session, **do not** re-run setup. Just go
> back to Cell 6, upload the next MP3, change `LESSON` in Cell 7, and run 6→7→8 again.

### Bring the talking head back to your Mac

Download from Google Drive (`MyDrive/100DaysOfAI/videos/`) and place it at **exactly**:

```
00_pipeline/talking_heads/day_001_lesson_05_talking_head.mp4
```

The filename must stay `<LESSON_ID>_talking_head.mp4` — Stage 3 looks for that
exact name and will error if it's renamed or in the wrong folder.

---

## Stage 3 — Local: composite the final video

```bash
conda activate ai-course
python 00_pipeline/lesson_build.py 00_warmup/day_001/lessons/day_001_lesson_05.yaml --finalize
```

`--finalize` needs three inputs to already exist (it checks and errors if any are missing):
- `00_pipeline/talking_heads/day_001_lesson_05_talking_head.mp4` (from Colab)
- `00_pipeline/audio/day_001_lesson_05.mp3` (from Stage 1)
- `00_pipeline/audio/day_001_lesson_05/manifest.yaml` (from Stage 1)

It builds a slide video timed to the manifest, then overlays the talking head as a
200×200 picture-in-picture in the bottom-right corner with the lesson audio.

**Intermediate + final outputs:**

| Artifact | Path |
|---|---|
| Timed slide video (intermediate) | `00_pipeline/audio/day_001_lesson_05/slides.mp4` |
| **Final video** | **`00_pipeline/final/day_001_lesson_05_final.mp4`** |

Watch it:
```bash
open 00_pipeline/final/day_001_lesson_05_final.mp4
```

---

## Path cheat-sheet (for `<LESSON_ID>` = `day_001_lesson_05`)

```
Stage 1 (local)   00_pipeline/audio/day_001_lesson_05.mp3            ← upload to Colab
                  00_pipeline/slides/day_001_lesson_05/*.png
                  00_pipeline/audio/day_001_lesson_05/manifest.yaml

Stage 2 (Colab)   /content/day_001_lesson_05.mp3                     (Cell 6 upload)
                  /content/results/day_001_lesson_05_talking_head.mp4 (Cell 7 output)
                  Drive: MyDrive/100DaysOfAI/videos/day_001_lesson_05_talking_head.mp4 (Cell 8)
   ↓ download to
                  00_pipeline/talking_heads/day_001_lesson_05_talking_head.mp4

Stage 3 (local)   00_pipeline/final/day_001_lesson_05_final.mp4      ← the watchable video
```

## Doing a whole day

Repeat all three stages for `_lesson_01` through `_lesson_05`. In Colab, run the
setup cells (1–5) once, then loop cells 6→7→8 for each lesson — uploading the next
MP3 and changing `LESSON` each time — so you generate all five talking heads in one
session, then run `--finalize` five times locally.
