"""
Run this once to hear the American voice options.
Each voice generates a short sample audio file in 00_pipeline/samples/.
Listen and pick your favourite — that voice gets used for all 100 days.

Usage:
    conda activate ai-course
    python 00_pipeline/voice_sampler.py
"""

import asyncio
import os
import edge_tts

SAMPLE_TEXT = (
    "Welcome to 100 Days of AI — The Complete AI Engineering Bootcamp. "
    "Today you're going to build something real. Let's get started."
)

VOICES = [
    "en-US-JennyNeural",       # Female — Friendly, Considerate
    "en-US-AriaNeural",        # Female — Positive, Confident
    "en-US-AvaNeural",         # Female — Expressive, Caring, Friendly
    "en-US-EmmaNeural",        # Female — Cheerful, Clear, Conversational
    "en-US-GuyNeural",         # Male   — Passion
    "en-US-ChristopherNeural", # Male   — Reliable, Authority
    "en-US-BrianNeural",       # Male   — Approachable, Casual, Sincere
]

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "samples")


async def generate_sample(voice: str):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, f"{voice}.mp3")
    communicate = edge_tts.Communicate(SAMPLE_TEXT, voice)
    await communicate.save(output_path)
    print(f"Saved: {output_path}")


async def main():
    print("Generating voice samples...\n")
    for voice in VOICES:
        await generate_sample(voice)
        await asyncio.sleep(2)
    print(f"\nDone. Open the files in {OUTPUT_DIR} and listen.")
    print("Then tell me which voice you want and we'll lock it in.")


if __name__ == "__main__":
    asyncio.run(main())
