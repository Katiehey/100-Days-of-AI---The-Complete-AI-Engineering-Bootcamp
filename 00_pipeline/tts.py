"""
Convert a lesson script to MP3 audio using Edge TTS (Jenny voice).

Usage:
    conda activate ai-course
    python 00_pipeline/tts.py <script_file> [output_file]

Examples:
    python 00_pipeline/tts.py 00_pipeline/scripts/day_001.txt
    python 00_pipeline/tts.py 00_pipeline/scripts/day_001.txt 00_pipeline/audio/day_001.mp3
"""

import asyncio
import os
import sys
import edge_tts

VOICE = "en-US-JennyNeural"
DEFAULT_AUDIO_DIR = os.path.join(os.path.dirname(__file__), "audio")


async def script_to_audio(script_path: str, output_path: str):
    with open(script_path, "r", encoding="utf-8") as f:
        text = f.read().strip()

    if not text:
        raise ValueError(f"Script file is empty: {script_path}")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(output_path)
    print(f"Audio saved: {output_path}")


def resolve_output_path(script_path: str, output_arg: str | None) -> str:
    if output_arg:
        return output_arg
    stem = os.path.splitext(os.path.basename(script_path))[0]
    return os.path.join(DEFAULT_AUDIO_DIR, f"{stem}.mp3")


async def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    script_path = sys.argv[1]
    output_path = resolve_output_path(script_path, sys.argv[2] if len(sys.argv) > 2 else None)

    if not os.path.exists(script_path):
        print(f"Error: script not found: {script_path}")
        sys.exit(1)

    print(f"Voice : {VOICE}")
    print(f"Script: {script_path}")
    print(f"Output: {output_path}")
    print()
    await script_to_audio(script_path, output_path)


if __name__ == "__main__":
    asyncio.run(main())
