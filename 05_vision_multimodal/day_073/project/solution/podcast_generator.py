"""podcast_generator.py — Day 073: Text-to-Speech Deep Dive.

Generates podcast-style audio using Microsoft Edge TTS (free, local API).
Extends the Edge TTS introduced on Day 1.

Setup:
    pip install edge-tts

For Jupyter notebooks (avoids "event loop already running" error):
    pip install nest_asyncio
    import nest_asyncio; nest_asyncio.apply()

Usage:
    from podcast_generator import PodcastGenerator

    # Testing — no network needed
    mock_tts = lambda text, **kw: b"AUDIO:" + text[:10].encode()
    gen = PodcastGenerator(tts_fn=mock_tts)
    parts = gen.build([
        {"text": "Welcome to the show.", "voice_key": "host"},
        {"text": "Thanks for having me!", "voice_key": "guest"},
    ])
    print(len(parts), parts[0][:12])   # 2  b'AUDIO:Welcom'

    # Real generation (requires network)
    gen = PodcastGenerator()
    parts = gen.build([{"text": "Hello world.", "voice_key": "host"}])
    open("out.mp3", "wb").write(parts[0])
"""
import asyncio
from pathlib import Path
from typing import Callable, Optional

# Common Edge TTS voices — subset for reference
COMMON_VOICES = [
    {"ShortName": "en-US-AriaNeural",    "Gender": "Female", "Locale": "en-US"},
    {"ShortName": "en-US-GuyNeural",     "Gender": "Male",   "Locale": "en-US"},
    {"ShortName": "en-GB-LibbyNeural",   "Gender": "Female", "Locale": "en-GB"},
    {"ShortName": "en-AU-NatashaNeural", "Gender": "Female", "Locale": "en-AU"},
    {"ShortName": "fr-FR-DeniseNeural",  "Gender": "Female", "Locale": "fr-FR"},
    {"ShortName": "de-DE-KatjaNeural",   "Gender": "Female", "Locale": "de-DE"},
    {"ShortName": "es-ES-ElviraNeural",  "Gender": "Female", "Locale": "es-ES"},
    {"ShortName": "ja-JP-NanamiNeural",  "Gender": "Female", "Locale": "ja-JP"},
]

# Role → voice name mapping used by PodcastGenerator
DEFAULT_VOICE_MAP = {
    "host":    "en-US-AriaNeural",
    "guest":   "en-US-GuyNeural",
    "narrator":"en-GB-LibbyNeural",
}


def build_prosody_ssml(text: str, rate: str = "+0%",
                        pitch: str = "+0Hz", volume: str = "+0%") -> str:
    """Wrap text in SSML prosody tags for rate/pitch/volume control.

    Returns a full SSML document string ready to pass to Edge TTS as text.
    """
    return (
        '<speak version="1.0" '
        'xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">'
        f'<prosody rate="{rate}" pitch="{pitch}" volume="{volume}">'
        f"{text}"
        "</prosody></speak>"
    )


def select_voice(voices: list, locale: str = "en-US",
                  gender: Optional[str] = None) -> Optional[dict]:
    """Find the first voice matching locale (and optionally gender).

    Args:
        voices: list of voice dicts (ShortName, Gender, Locale)
        locale: exact Locale string to match (e.g. 'en-US', 'fr-FR')
        gender: 'Female' or 'Male' (case-insensitive); None = any
    Returns:
        First matching voice dict, or None if not found
    """
    for v in voices:
        if v.get("Locale") != locale:
            continue
        if gender is not None and v.get("Gender", "").lower() != gender.lower():
            continue
        return v
    return None


def synthesize(text: str, voice: str = "en-US-AriaNeural",
               tts_fn: Optional[Callable] = None,
               rate: str = "+0%", pitch: str = "+0Hz") -> bytes:
    """Synthesize text to audio bytes using Edge TTS.

    Args:
        text:    Text or SSML string to synthesize
        voice:   Edge TTS voice ShortName
        tts_fn:  callable(text, voice, rate, pitch) -> bytes for testing
        rate:    Speed adjustment e.g. '+10%', '-20%', '+0%'
        pitch:   Pitch adjustment e.g. '+5Hz', '-2Hz', '+0Hz'
    Returns:
        Audio bytes (MP3 format when using real Edge TTS)
    Note:
        In Jupyter: pip install nest_asyncio; nest_asyncio.apply() before use.
    """
    if tts_fn is not None:
        return tts_fn(text, voice=voice, rate=rate, pitch=pitch)
    import edge_tts

    async def _run() -> bytes:
        communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        chunks: list[bytes] = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                chunks.append(chunk["data"])
        return b"".join(chunks)

    return asyncio.run(_run())


def synthesize_segments(segments: list,
                         tts_fn: Optional[Callable] = None) -> list:
    """Synthesize a list of segment dicts to audio bytes.

    Each segment dict: {text, voice?, rate?, pitch?}
    Returns list of bytes, one per segment.
    """
    out = []
    for seg in segments:
        audio = synthesize(
            seg["text"],
            voice=seg.get("voice", "en-US-AriaNeural"),
            tts_fn=tts_fn,
            rate=seg.get("rate", "+0%"),
            pitch=seg.get("pitch", "+0Hz"),
        )
        out.append(audio)
    return out


class PodcastGenerator:
    """Generate podcast-style audio from a script using Edge TTS.

    Inject tts_fn for testing without a network connection::

        mock_tts = lambda text, **kw: b"AUDIO:" + text[:10].encode()
        gen = PodcastGenerator(tts_fn=mock_tts)
    """

    def __init__(self, voice_map: Optional[dict] = None,
                 tts_fn: Optional[Callable] = None) -> None:
        self._voice_map = voice_map if voice_map is not None else DEFAULT_VOICE_MAP
        self._tts_fn    = tts_fn

    def synthesize_segment(self, text: str, voice_key: str = "host",
                            rate: str = "+0%", pitch: str = "+0Hz") -> bytes:
        """Synthesize one script segment. Returns audio bytes."""
        voice = self._voice_map.get(voice_key, DEFAULT_VOICE_MAP["host"])
        return synthesize(text, voice=voice, tts_fn=self._tts_fn,
                          rate=rate, pitch=pitch)

    def build(self, script: list) -> list:
        """Synthesize all script entries. Returns list of bytes.

        Each script entry: {text, voice_key?, rate?, pitch?}
        """
        return [
            self.synthesize_segment(
                entry["text"],
                voice_key=entry.get("voice_key", "host"),
                rate=entry.get("rate", "+0%"),
                pitch=entry.get("pitch", "+0Hz"),
            )
            for entry in script
        ]

    def save(self, script: list, output_dir) -> list:
        """Build and save each segment as segment_01.mp3, segment_02.mp3, …

        Returns list of Path objects.
        """
        parts = self.build(script)
        out   = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        paths = []
        for i, audio in enumerate(parts, start=1):
            p = out / f"segment_{i:02d}.mp3"
            p.write_bytes(audio)
            paths.append(p)
        return paths
