"""
Build a complete lesson video from a YAML outline.

Usage:
    conda activate ai-course

    # Step 1 — local: generate slides + audio
    python 00_pipeline/lesson_build.py 00_warmup/day_001/lessons/day_001_lesson_01.yaml --prep

    # Then: upload the printed audio path to Colab, run SadTalker, download
    #       talking head to 00_pipeline/talking_heads/<lesson_id>_talking_head.mp4

    # Step 2 — local: composite final video
    python 00_pipeline/lesson_build.py 00_warmup/day_001/lessons/day_001_lesson_01.yaml --finalize
"""

import argparse
import asyncio
import os
import subprocess
import sys

import yaml
import edge_tts

# Add pipeline dir to path so slide_gen can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from slide_gen import generate_slides

PIPELINE = os.path.dirname(os.path.abspath(__file__))
VOICE    = "en-US-JennyNeural"
FPS      = 25
PIP_SIZE = 200
PIP_X    = 1280 - PIP_SIZE - 20   # 1060
PIP_Y    = 720  - PIP_SIZE - 20   # 500


# ── Helpers ───────────────────────────────────────────────────────────────────

def _lesson_id(lesson: dict) -> str:
    day = str(lesson["day"]).zfill(3)
    les = str(lesson["lesson"]).zfill(2)
    return f"day_{day}_lesson_{les}"


def _slides_dir(lid: str)  -> str:
    return os.path.join(PIPELINE, "slides",        lid)

def _audio_dir(lid: str)   -> str:
    return os.path.join(PIPELINE, "audio",         lid)

def _th_path(lid: str)     -> str:
    return os.path.join(PIPELINE, "talking_heads", f"{lid}_talking_head.mp4")

def _final_path(lid: str)  -> str:
    return os.path.join(PIPELINE, "final",         f"{lid}_final.mp4")

def _full_audio(lid: str)  -> str:
    return os.path.join(PIPELINE, "audio",         f"{lid}.mp3")


async def _tts(text: str, path: str) -> None:
    await edge_tts.Communicate(text, VOICE).save(path)


def _duration(path: str) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True,
    )
    return float(r.stdout.strip())


def _ffmpeg(*args, label: str = "") -> None:
    r = subprocess.run(["ffmpeg", "-y", *args],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"\nFFmpeg error ({label}):\n{r.stderr[-2000:]}")
        sys.exit(1)


# ── Prep ──────────────────────────────────────────────────────────────────────

def prep(yaml_path: str) -> None:
    """Generate slides + per-slide audio + concatenated full audio."""
    with open(yaml_path, encoding="utf-8") as f:
        lesson = yaml.safe_load(f)

    lid   = _lesson_id(lesson)
    s_dir = _slides_dir(lid)
    a_dir = _audio_dir(lid)
    os.makedirs(a_dir, exist_ok=True)

    print(f"Lesson : {lid}")
    print(f"Title  : {lesson['title']}")

    # 1. Slides
    print(f"\n[1/3] Generating slides → {s_dir}")
    slide_paths = generate_slides(yaml_path, s_dir)

    # 2. Per-slide audio
    print(f"\n[2/3] Generating audio per slide...")
    timed = []   # (slide_png, audio_mp3, duration_seconds)
    for i, slide in enumerate(lesson["slides"], 1):
        narration = slide.get("narration", "").strip()
        if not narration:
            print(f"  Slide {i:03d}: no narration — skipping")
            continue
        png   = slide_paths[i - 1]
        mp3   = os.path.join(a_dir, f"slide_{i:03d}.mp3")
        asyncio.run(_tts(narration, mp3))
        dur   = _duration(mp3)
        timed.append((png, mp3, dur))
        print(f"  Slide {i:03d}: {dur:5.1f}s")

    if not timed:
        print("No slides with narration found.")
        sys.exit(1)

    # 3. Concatenate into full lesson audio
    print(f"\n[3/3] Concatenating audio...")
    concat_txt = os.path.join(a_dir, "audio_concat.txt")
    with open(concat_txt, "w") as f:
        for _, mp3, _ in timed:
            f.write(f"file '{mp3}'\n")

    full = _full_audio(lid)
    _ffmpeg("-f", "concat", "-safe", "0", "-i", concat_txt,
            "-c", "copy", full, label="audio concat")

    total = sum(d for _, _, d in timed)
    print(f"Full audio : {full}")
    print(f"Duration   : {total:.0f}s  ({total/60:.1f} min)")

    # Save timing manifest for finalize step
    manifest = os.path.join(a_dir, "manifest.yaml")
    with open(manifest, "w") as f:
        yaml.dump([{"png": p, "mp3": m, "duration": d}
                   for p, m, d in timed], f)

    print(f"\n── Next steps ──────────────────────────────────────────────")
    print(f"1. Upload to Colab : {full}")
    print(f"2. Run SadTalker   : DAY variable doesn't apply — use the lesson audio")
    print(f"3. Download to     : {_th_path(lid)}")
    print(f"4. Run finalize    : python lesson_build.py {yaml_path} --finalize")


# ── Finalize ──────────────────────────────────────────────────────────────────

def finalize(yaml_path: str) -> None:
    """Composite slide video + talking head PiP → final MP4."""
    with open(yaml_path, encoding="utf-8") as f:
        lesson = yaml.safe_load(f)

    lid     = _lesson_id(lesson)
    a_dir   = _audio_dir(lid)
    th      = _th_path(lid)
    out     = _final_path(lid)
    full    = _full_audio(lid)
    manifest_path = os.path.join(a_dir, "manifest.yaml")

    for path, label in [(th, "Talking head"), (full, "Full audio"),
                        (manifest_path, "Manifest")]:
        if not os.path.exists(path):
            print(f"Error: {label} not found: {path}")
            print("Run --prep first, then run Colab.")
            sys.exit(1)

    with open(manifest_path) as f:
        timed = yaml.safe_load(f)   # list of {png, mp3, duration}

    total = sum(s["duration"] for s in timed)
    print(f"Lesson : {lid}  ({total:.0f}s / {total/60:.1f} min)")
    print(f"Slides : {len(timed)}")

    # 1. Build slide-timed video via concat demuxer
    concat_txt = os.path.join(a_dir, "slides_concat.txt")
    with open(concat_txt, "w") as f:
        for s in timed:
            f.write(f"file '{s['png']}'\n")
            f.write(f"duration {s['duration']}\n")
        f.write(f"file '{timed[-1]['png']}'\n")   # termination frame

    slide_vid = os.path.join(a_dir, "slides.mp4")
    print("Building slide video...")
    _ffmpeg(
        "-f", "concat", "-safe", "0", "-i", concat_txt,
        "-vf", f"scale={1280}:{720}:flags=lanczos,fps={FPS}",
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        "-pix_fmt", "yuv420p",
        slide_vid,
        label="slide video",
    )

    # 2. Composite PiP talking head onto slide video
    os.makedirs(os.path.dirname(out), exist_ok=True)
    print("Compositing PiP talking head...")
    filt = (
        f"[1:v]scale={PIP_SIZE}:{PIP_SIZE}:flags=lanczos[pip];"
        f"[0:v][pip]overlay=x={PIP_X}:y={PIP_Y}[out]"
    )
    _ffmpeg(
        "-i", slide_vid,   # 0: slide video
        "-i", th,          # 1: talking head (PiP)
        "-i", full,        # 2: full audio
        "-filter_complex", filt,
        "-map", "[out]",
        "-map", "2:a",
        "-c:v", "libx264", "-crf", "18", "-preset", "slow",
        "-c:a", "aac", "-b:a", "192k",
        "-t", str(total),
        "-movflags", "+faststart",
        out,
        label="final composite",
    )

    size_mb = os.path.getsize(out) / 1_000_000
    print(f"\nDone → {out}  ({size_mb:.1f} MB)")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("yaml",      help="Path to lesson YAML file")
    parser.add_argument("--prep",    action="store_true",
                        help="Generate slides + audio (run before Colab)")
    parser.add_argument("--finalize", action="store_true",
                        help="Composite final video (run after Colab)")
    args = parser.parse_args()

    if not args.prep and not args.finalize:
        parser.print_help()
        sys.exit(1)

    if args.prep:
        prep(args.yaml)
    else:
        finalize(args.yaml)
