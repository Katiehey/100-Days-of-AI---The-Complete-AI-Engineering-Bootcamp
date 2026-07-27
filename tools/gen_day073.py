#!/usr/bin/env python3
"""gen_day073.py — generate Day 073: Text-to-Speech Deep Dive."""
from pathlib import Path
import json

ROOT    = Path(__file__).parent.parent
DAY     = "073"
SECTION = "05_vision_multimodal"
OUT     = ROOT / SECTION / f"day_{DAY}"

(OUT / "exercises").mkdir(parents=True, exist_ok=True)
(OUT / "lessons").mkdir(parents=True, exist_ok=True)
(OUT / "project" / "solution").mkdir(parents=True, exist_ok=True)

# ── deliverable: podcast_generator.py ────────────────────────────────────────
_PODCAST_SRC = '''\
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
'''

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

# ── YAML lessons ──────────────────────────────────────────────────────────────
_LESSON_01 = """\
day: "073"
lesson: 1
title: "Neural TTS and Edge TTS"
slides:
  - type: title
    heading: "Text-to-Speech Deep Dive"
    subheading: "Day 73 — Edge TTS, voices, SSML, podcast generator"
    narration: >
      Day 1 used Edge TTS to turn headlines into spoken MP3. Today you go
      deeper: neural TTS architecture, voice selection across dozens of
      locales, prosody control with SSML, and assembling a multi-voice
      podcast generator. All free, all local API calls to Microsoft Edge.

  - type: concept
    label: "Neural TTS"
    heading: "How Neural TTS Works"
    body: >
      Neural text-to-speech converts text to audio using a neural network
      trained on hours of human speech. The result is far more natural
      than older concatenative or parametric systems.
    bullets:
      - "Text encoder: tokenise + embed the input text"
      - "Acoustic model: predict mel spectrogram (frequency-time heatmap) from tokens"
      - "Vocoder: convert mel spectrogram to raw audio waveform"
      - "FastSpeech2/VITS: end-to-end models that skip the mel spectrogram step"
    narration: >
      The mel spectrogram is a compact representation of audio: frequency on
      one axis, time on the other, with colour representing energy. The
      acoustic model (often a transformer) predicts one spectrogram frame per
      phoneme, with duration and pitch predicted in parallel. The vocoder
      (HiFi-GAN or similar) runs the inverse transform from spectrogram back
      to audio samples at high quality. Microsoft's Edge Neural TTS uses
      their internal SoundStorm or similar architecture — the exact details
      are proprietary, but the results are near-human quality.

  - type: concept
    label: "Edge TTS"
    heading: "Edge TTS: Free Neural TTS via the Browser"
    body: >
      Edge TTS is a free Python package that calls the same speech
      synthesis service used by Microsoft Edge's read-aloud feature.
    bullets:
      - "pip install edge-tts — installs the Python client"
      - "No API key — uses the same public endpoint as the Edge browser"
      - "300+ voices across 100+ locales"
      - "Outputs MP3 audio bytes via an async streaming API"
    narration: >
      Microsoft makes this synthesis service freely available through their
      Edge browser's read-aloud feature. The edge-tts Python package calls
      the same endpoint. There is no official public API documentation or
      SLA — use it for personal and course projects. For production
      commercial use, the Azure Cognitive Services TTS API is the supported
      alternative (paid, but same voice quality). For this course, edge-tts
      is the right choice: zero cost, excellent quality, 300+ voices.

  - type: code
    label: "Basic usage"
    heading: "Edge TTS: Basic Synthesis"
    code: |
      # Real usage (requires pip install edge-tts + network)
      import asyncio, edge_tts

      async def speak(text, voice='en-US-AriaNeural'):
          communicate = edge_tts.Communicate(text, voice)
          chunks = []
          async for chunk in communicate.stream():
              if chunk['type'] == 'audio':
                  chunks.append(chunk['data'])
          return b''.join(chunks)

      audio = asyncio.run(speak('Hello, welcome to the podcast!'))
      open('output.mp3', 'wb').write(audio)
      print(len(audio), 'bytes')

      # Testing mode — tts_fn=None injection, no network
      mock_tts = lambda text, **kw: b'AUDIO:' + text[:10].encode()
      result = mock_tts('Hello there')
      print(result)   # b'AUDIO:Hello the'
    narration: >
      The Communicate class wraps one synthesis request. The stream method
      returns an async generator of chunks — each chunk is a dict with type
      (audio, WordBoundary, or SessionEnd) and data (bytes for audio chunks).
      Collecting only the audio chunks and joining them produces the full
      MP3 file. The asyncio.run call works in scripts; in Jupyter notebooks
      install nest_asyncio and call apply() once to allow nested event loops.

  - type: exercise
    heading: "Exercise 1: build_prosody_ssml"
    prompt: >
      Implement build_prosody_ssml(text, rate='+0%', pitch='+0Hz', volume='+0%') -> str.
      Return a full SSML document string:
      '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">'
      '<prosody rate="{rate}" pitch="{pitch}" volume="{volume}">'
      '{text}'
      '</prosody></speak>'
      Use f-string substitution for the parameter values.
    hint: >
      Return a single f-string that concatenates all four XML tags with the
      text in the middle. Include the speak and prosody opening/closing tags.
    narration: >
      SSML is the bridge between plain text and fine-grained voice control.
      build_prosody_ssml is the foundation of all rate, pitch, and volume
      adjustments in the podcast generator.

  - type: summary
    heading: "Lesson 1 Summary"
    bullets:
      - "Neural TTS: text encoder + acoustic model + vocoder"
      - "Edge TTS: pip install edge-tts, free, 300+ voices, no API key"
      - "Communicate(text, voice, rate, pitch).stream() — async generator"
      - "Collect audio chunks, join bytes, write to .mp3"
      - "tts_fn=None injection: mock returns bytes, no network needed in exercises"
    narration: >
      The TTS foundation is laid. Next: the voice catalogue — how to
      select voices by locale, gender, and style.
"""

_LESSON_02 = """\
day: "073"
lesson: 2
title: "Voices and Voice Selection"
slides:
  - type: title
    heading: "Voices and Voice Selection"
    subheading: "Locales, genders, SSML prosody control"
    narration: >
      Edge TTS has over 300 voices. Choosing the right voice for a podcast
      means matching locale, gender, and style to the content. This lesson
      covers the voice catalogue structure, how to filter voices
      programmatically, and how SSML prosody parameters control the character
      of the speech.

  - type: concept
    label: "Voice dict"
    heading: "Voice Catalogue Structure"
    body: >
      Each Edge TTS voice is a dict with four key fields. select_voice
      filters the catalogue by locale and gender to find the best match.
    bullets:
      - "ShortName: unique voice identifier like en-US-AriaNeural"
      - "Gender: Female or Male"
      - "Locale: BCP-47 language code like en-US, fr-FR, ja-JP"
      - "SuggestedCodec: usually audio-24khz-48kbitrate-mono-mp3"
    narration: >
      ShortName is the string passed to Communicate. It uniquely identifies
      the voice. The naming convention is locale-NameNeural, where Name is
      the voice's persona name and Neural indicates it is a neural TTS voice
      (as opposed to the older Standard voices). Locale uses BCP-47 codes:
      en-US for American English, en-GB for British English, fr-FR for
      French French, zh-CN for Simplified Chinese, and so on. Gender is
      Female or Male. There are also multi-style voices that can speak in
      different emotional styles (cheerful, sad, newscast).

  - type: code
    label: "select_voice"
    heading: "select_voice: Filter by Locale and Gender"
    code: |
      COMMON_VOICES = [
          {'ShortName': 'en-US-AriaNeural',   'Gender': 'Female', 'Locale': 'en-US'},
          {'ShortName': 'en-US-GuyNeural',    'Gender': 'Male',   'Locale': 'en-US'},
          {'ShortName': 'en-GB-LibbyNeural',  'Gender': 'Female', 'Locale': 'en-GB'},
          {'ShortName': 'fr-FR-DeniseNeural', 'Gender': 'Female', 'Locale': 'fr-FR'},
      ]

      def select_voice(voices, locale='en-US', gender=None):
          for v in voices:
              if v.get('Locale') != locale:
                  continue
              if gender is not None and v.get('Gender','').lower() != gender.lower():
                  continue
              return v
          return None

      print(select_voice(COMMON_VOICES, 'en-US')['ShortName'])          # en-US-AriaNeural
      print(select_voice(COMMON_VOICES, 'en-US', 'Male')['ShortName']) # en-US-GuyNeural
      print(select_voice(COMMON_VOICES, 'zh-CN'))                       # None
    narration: >
      The filter iterates the voices list and returns the first voice that
      matches both criteria. Returning None when no match exists is safe:
      the caller can fall back to a default voice. The gender comparison
      is case-insensitive so the caller can pass Female, female, or FEMALE.
      In a podcast generator, select_voice lets you specify the podcast
      locale and automatically assign voices — host gets the first Female
      in the locale, guest gets the first Male.

  - type: concept
    label: "SSML prosody"
    heading: "SSML Prosody Parameters"
    body: >
      Three SSML parameters control how speech sounds: rate, pitch, and
      volume. Each uses a percentage or Hz offset from the neutral baseline.
    bullets:
      - "rate: speed — '+20%' faster, '-20%' slower, 'fast'/'slow' also valid"
      - "pitch: tone — '+5Hz' higher, '-5Hz' lower, 'high'/'low' also valid"
      - "volume: loudness — '+10%' louder, '-30%' quieter, 'loud'/'soft'"
      - "Combine: a fast excited guest vs slow measured narrator"
    narration: >
      The default for all three parameters is +0%/+0Hz/+0% — neutral. For
      a podcast host introducing sections, a slightly slower rate (like -5%)
      and lower pitch (-2Hz) creates a calm, authoritative tone. For guest
      responses, slightly faster (+10%) and higher pitch (+3Hz) sounds
      more animated and conversational. The narrator voice for story
      segments often benefits from a slightly slower rate and extra
      volume (+5%) for clarity. These are subtle adjustments — big
      values like +50% or -30Hz sound robotic or comical.

  - type: exercise
    heading: "Exercise 2: select_voice"
    prompt: >
      Implement select_voice(voices, locale='en-US', gender=None) -> dict | None.
      Iterate voices. For each voice: skip if v.get('Locale') != locale.
      If gender is not None: skip if v.get('Gender','').lower() != gender.lower().
      Return the first matching voice, or None if no match.
    hint: >
      for v in voices: if v.get('Locale') != locale: continue.
      if gender is not None and v.get('Gender','').lower() != gender.lower(): continue.
      return v. After loop: return None.
    narration: >
      select_voice is the voice routing table for the PodcastGenerator.
      Given a locale and optional gender preference, it finds the best
      available voice automatically.

  - type: summary
    heading: "Lesson 2 Summary"
    bullets:
      - "Voice dict: ShortName, Gender, Locale, SuggestedCodec"
      - "ShortName format: locale-NameNeural (e.g. en-US-AriaNeural)"
      - "select_voice: iterate, match Locale exactly, match Gender case-insensitively"
      - "Return first match or None (caller provides fallback)"
      - "SSML prosody: rate (+/-%), pitch (+/-Hz), volume (+/-%) — subtle adjustments"
    narration: >
      Voice selection is done. Next: the core synthesize function with
      tts_fn injection.
"""

_LESSON_03 = """\
day: "073"
lesson: 3
title: "The synthesize Function"
slides:
  - type: title
    heading: "The synthesize Function"
    subheading: "Core TTS with tts_fn=None injection"
    narration: >
      With SSML building and voice selection covered, this lesson builds
      the core synthesis function — synthesize, which converts text to audio
      bytes with the now-familiar fn=None injection pattern.

  - type: how_it_works
    label: "synthesize"
    heading: "synthesize: Edge TTS with Mock Injection"
    body: >
      Same contract as describe_fn (Day 67), embed_fn (Day 71), and
      transcribe_fn (Day 72): a callable that replaces the network call
      in tests.
    bullets:
      - "tts_fn(text, voice=voice, rate=rate, pitch=pitch) -> bytes"
      - "When None: async edge_tts.Communicate.stream() → collect audio chunks"
      - "asyncio.run(_run()): sync wrapper around the async API"
      - "Works in scripts; Jupyter needs nest_asyncio"
    narration: >
      The mock contract is: callable that takes text as the first positional
      argument and voice, rate, pitch as keyword arguments, and returns bytes.
      The simplest useful mock is a lambda that returns a fixed bytes object
      (for size tests) or encodes a snippet of the text (for content tests).
      The real implementation wraps the async Communicate.stream() call in
      a small async function and runs it with asyncio.run. The asyncio.run
      approach works in scripts and terminals; Jupyter users need to install
      nest_asyncio to allow nested event loops.

  - type: code
    label: "Implementation"
    heading: "synthesize Implementation"
    code: |
      import asyncio

      def synthesize(text, voice='en-US-AriaNeural', tts_fn=None,
                     rate='+0%', pitch='+0Hz'):
          if tts_fn is not None:
              return tts_fn(text, voice=voice, rate=rate, pitch=pitch)
          import edge_tts
          async def _run():
              comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
              chunks = []
              async for chunk in comm.stream():
                  if chunk['type'] == 'audio':
                      chunks.append(chunk['data'])
              return b''.join(chunks)
          return asyncio.run(_run())

      # Test with mock
      mock_tts = lambda text, **kw: b'AUDIO:' + text[:12].encode()
      audio = synthesize('Hello world!', tts_fn=mock_tts)
      print(audio)   # b'AUDIO:Hello world!'
    narration: >
      The lazy import of edge_tts means the module loads cleanly without
      edge-tts installed. The _run inner function is defined inside the
      else branch and immediately passed to asyncio.run. Keeping it as a
      nested function rather than a module-level async function avoids
      polluting the module namespace with an async function that has no
      standalone use.

  - type: code
    label: "SSML + synthesize"
    heading: "Combining SSML and synthesize"
    code: |
      # Build SSML with prosody, then synthesize
      ssml = build_prosody_ssml(
          'Welcome to the podcast. Today we discuss machine learning.',
          rate='-5%', pitch='-2Hz',
      )
      print(ssml[:80])   # <speak version="1.0" ...><prosody rate="-5%" ...>...

      # Pass the SSML string as text to synthesize
      audio = synthesize(ssml, voice='en-US-AriaNeural', tts_fn=mock_tts)
      print(len(audio))
    narration: >
      When text is an SSML string, Edge TTS uses the prosody parameters
      from the SSML rather than the constructor rate/pitch. This lets you
      embed fine-grained prosody control directly in the content. For a
      podcast generator, the simplest approach is to use the constructor
      parameters for global voice style and pass plain text — reserve SSML
      for special segments that need different pacing (like a fast-read
      disclaimer or a slow dramatic pause).

  - type: exercise
    heading: "Exercise 3: synthesize"
    prompt: >
      Implement synthesize(text, voice='en-US-AriaNeural', tts_fn=None,
      rate='+0%', pitch='+0Hz') -> bytes.
      If tts_fn is not None: return tts_fn(text, voice=voice, rate=rate, pitch=pitch).
      Otherwise: lazy import edge_tts, define async _run() that creates
      edge_tts.Communicate(text, voice, rate=rate, pitch=pitch), collects
      audio chunks from .stream(), joins and returns bytes. Call asyncio.run(_run()).
    hint: >
      if tts_fn is not None: return tts_fn(text, voice=voice, rate=rate, pitch=pitch).
      import asyncio, edge_tts.
      async def _run(): comm = edge_tts.Communicate(...); collect audio chunks; return b''.join(chunks).
      return asyncio.run(_run()).
    narration: >
      synthesize is the hub function that all higher-level code delegates
      to. Getting the injection pattern right means PodcastGenerator and
      synthesize_segments are automatically testable.

  - type: summary
    heading: "Lesson 3 Summary"
    bullets:
      - "synthesize: text + voice + rate + pitch + tts_fn → bytes"
      - "Mock contract: tts_fn(text, voice=..., rate=..., pitch=...) -> bytes"
      - "Real: async Communicate.stream(), collect audio chunks, asyncio.run"
      - "Lazy import edge_tts: module loads without edge-tts installed"
      - "SSML as text: pass build_prosody_ssml output directly to synthesize"
    narration: >
      The core synthesize function is complete. Next: synthesizing multiple
      segments for a full script.
"""

_LESSON_04 = """\
day: "073"
lesson: 4
title: "Multi-Segment Synthesis"
slides:
  - type: title
    heading: "Multi-Segment Synthesis"
    subheading: "synthesize_segments — script-to-audio pipeline"
    narration: >
      A podcast is not one voice reading one block of text. It is a script:
      multiple speakers, each with different voice, rate, and pitch settings.
      This lesson builds synthesize_segments, which takes a list of segment
      dicts and returns a list of audio bytes — one per segment.

  - type: how_it_works
    label: "Segment dict"
    heading: "The Segment Dict Format"
    body: >
      Each segment is a dict with text and optional voice, rate, pitch keys.
      Missing optional keys default to neutral values.
    bullets:
      - "text (required): the spoken content"
      - "voice (optional): voice ShortName, defaults to en-US-AriaNeural"
      - "rate (optional): speed adjustment, defaults to +0%"
      - "pitch (optional): pitch adjustment, defaults to +0Hz"
    narration: >
      The segment dict format is intentionally flat — all values at the top
      level, no nesting. This makes it easy to build from a simple script
      file (JSON or YAML), to log, and to debug. The defaults mean a
      minimal script can have just the text key. Using dict.get with a
      default value handles missing keys without raising KeyError, so the
      caller does not need to specify every key for every segment.

  - type: code
    label: "synthesize_segments"
    heading: "synthesize_segments Implementation"
    code: |
      def synthesize_segments(segments, tts_fn=None):
          out = []
          for seg in segments:
              audio = synthesize(
                  seg['text'],
                  voice=seg.get('voice', 'en-US-AriaNeural'),
                  tts_fn=tts_fn,
                  rate=seg.get('rate', '+0%'),
                  pitch=seg.get('pitch', '+0Hz'),
              )
              out.append(audio)
          return out

      # Example script
      script = [
          {'text': 'Welcome to the show.', 'voice': 'en-US-AriaNeural', 'rate': '-5%'},
          {'text': 'Thanks for having me!', 'voice': 'en-US-GuyNeural',  'rate': '+10%'},
          {'text': "Let's dive in.", 'voice': 'en-US-AriaNeural'},
      ]
      parts = synthesize_segments(script, tts_fn=mock_tts)
      print(len(parts))   # 3
    narration: >
      synthesize_segments is a thin loop: for each segment dict, delegate
      to synthesize with the segment's parameters. The result is a list of
      bytes objects — one per segment — that can be saved to individual files
      or joined. The tts_fn flows through from synthesize_segments to
      synthesize, so the mock works for all segments without any changes.

  - type: concept
    label: "Audio joining"
    heading: "Joining Audio Segments"
    body: >
      For MP3 output, concatenating bytes produces a valid file.
      For WAV output, headers must be combined carefully.
    bullets:
      - "MP3: MPEG frames are self-delineating — concatenation is valid"
      - "bytes concatenation: b''.join(parts) gives one playable MP3"
      - "WAV: has a file header with length fields — cannot naively concatenate"
      - "For WAV joining: use pydub or soundfile to re-encode"
    narration: >
      The easiest approach for the podcast generator is to save each
      segment as a numbered .mp3 file (segment_01.mp3, segment_02.mp3)
      and let the user join them with any audio editor or ffmpeg. If a
      single output file is required, pydub provides an AudioSegment class
      that handles concatenation with proper encoding. For this course,
      the PodcastGenerator.save method writes numbered files — clean,
      simple, and requires no additional audio packages.

  - type: exercise
    heading: "Exercise 4: synthesize_segments"
    prompt: >
      Implement synthesize_segments(segments, tts_fn=None) -> list[bytes].
      For each seg in segments: call synthesize with seg['text'],
      voice=seg.get('voice', 'en-US-AriaNeural'), tts_fn=tts_fn,
      rate=seg.get('rate', '+0%'), pitch=seg.get('pitch', '+0Hz').
      Append the result. Return the list.
    hint: >
      out = []; for seg in segments: out.append(synthesize(seg['text'],
      voice=seg.get('voice','en-US-AriaNeural'), tts_fn=tts_fn, ...)); return out.
    narration: >
      synthesize_segments assembles a script into a list of audio parts.
      Combined with PodcastGenerator.save, it drives the entire
      text-to-podcast pipeline.

  - type: summary
    heading: "Lesson 4 Summary"
    bullets:
      - "Segment dict: {text, voice?, rate?, pitch?} — optional keys default to neutral"
      - "synthesize_segments: loop → synthesize per segment → list[bytes]"
      - "tts_fn flows through from synthesize_segments to synthesize"
      - "MP3 concatenation: b''.join(parts) produces valid playable MP3"
      - "WAV concatenation: needs pydub or soundfile (re-encode approach)"
    narration: >
      All building blocks are ready. The final lesson assembles them into
      PodcastGenerator — the Day 73 deliverable.
"""

_LESSON_05 = """\
day: "073"
lesson: 5
title: "PodcastGenerator — Full Pipeline"
slides:
  - type: title
    heading: "PodcastGenerator"
    subheading: "Full pipeline class — script to audio files"
    narration: >
      The previous lessons built all the components. This lesson assembles
      them into PodcastGenerator: a class that maps role names (host, guest,
      narrator) to voices and synthesizes a full script to numbered audio
      files.

  - type: how_it_works
    label: "PodcastGenerator"
    heading: "PodcastGenerator Design"
    body: >
      A voice_map binds role names to voice ShortNames. Four methods
      cover: single segment, full script build, save to disk.
    bullets:
      - "PodcastGenerator(voice_map=None, tts_fn=None)"
      - "synthesize_segment(text, voice_key='host', rate, pitch) -> bytes"
      - "build(script) -> list[bytes] — one bytes per script entry"
      - "save(script, output_dir) -> list[Path] — writes segment_01.mp3, ..."
    narration: >
      The voice_map is a dict mapping role names to voice ShortNames —
      for example host maps to en-US-AriaNeural and guest to en-US-GuyNeural.
      This abstraction separates the script (which uses semantic role names)
      from the implementation (which uses specific voice names). Swapping a
      voice only requires changing the voice_map, not touching any script
      entries. build synthesizes all segments via synthesize_segment. save
      calls build and writes each bytes object to a numbered .mp3 file.

  - type: code
    label: "Implementation"
    heading: "PodcastGenerator Implementation"
    code: |
      DEFAULT_VOICE_MAP = {
          'host':     'en-US-AriaNeural',
          'guest':    'en-US-GuyNeural',
          'narrator': 'en-GB-LibbyNeural',
      }

      class PodcastGenerator:
          def __init__(self, voice_map=None, tts_fn=None):
              self._voice_map = voice_map if voice_map is not None else DEFAULT_VOICE_MAP
              self._tts_fn    = tts_fn

          def synthesize_segment(self, text, voice_key='host',
                                  rate='+0%', pitch='+0Hz'):
              voice = self._voice_map.get(voice_key, DEFAULT_VOICE_MAP['host'])
              return synthesize(text, voice=voice, tts_fn=self._tts_fn,
                                rate=rate, pitch=pitch)

          def build(self, script):
              return [self.synthesize_segment(
                          e['text'], e.get('voice_key', 'host'),
                          e.get('rate', '+0%'), e.get('pitch', '+0Hz'))
                      for e in script]

          def save(self, script, output_dir):
              parts = self.build(script)
              out = Path(output_dir)
              out.mkdir(parents=True, exist_ok=True)
              paths = []
              for i, audio in enumerate(parts, start=1):
                  p = out / f'segment_{i:02d}.mp3'
                  p.write_bytes(audio); paths.append(p)
              return paths
    narration: >
      synthesize_segment looks up the voice name from the voice_map using
      dict.get with a fallback to the default host voice — so unknown role
      names degrade gracefully rather than raising KeyError. build is a
      list comprehension over script entries. save calls build, creates
      the output directory, and writes numbered files. The from pathlib
      import Path at the top of the module makes Path available in the class
      body.

  - type: code
    label: "Full usage"
    heading: "Full Podcast Generation"
    code: |
      from podcast_generator import PodcastGenerator

      # With mock — no network needed
      mock = lambda text, **kw: b'AUDIO:' + text[:12].encode()
      gen = PodcastGenerator(tts_fn=mock)

      script = [
          {'text': 'Welcome to AI Engineering Daily.',   'voice_key': 'host'},
          {'text': "Today's topic: multimodal AI.",      'voice_key': 'host',   'rate': '-5%'},
          {'text': "I find this genuinely exciting!",    'voice_key': 'guest',  'rate': '+10%'},
          {'text': "We will explore vision and speech.", 'voice_key': 'narrator'},
      ]
      parts = gen.build(script)
      print(len(parts), [len(p) for p in parts])

      # Or save to files
      import tempfile, pathlib
      with tempfile.TemporaryDirectory() as tmpdir:
          paths = gen.save(script, tmpdir)
          for p in paths:
              print(pathlib.Path(p).name, pathlib.Path(p).stat().st_size, 'bytes')
    narration: >
      The full pipeline: define a script as a list of dicts with text and
      voice_key, call build or save, get audio. Swapping to real synthesis
      means removing the tts_fn argument from the constructor — one change,
      rest of the code unchanged. The voice_map can be customised per
      podcast: a French podcast would pass a voice_map with French voice
      names, the script logic remains identical.

  - type: exercise
    heading: "Exercise 5: PodcastGenerator Class"
    prompt: >
      Implement PodcastGenerator:
      __init__(voice_map=None, tts_fn=None): store both; use DEFAULT_VOICE_MAP if voice_map is None.
      synthesize_segment(text, voice_key='host', rate='+0%', pitch='+0Hz') -> bytes:
        voice = self._voice_map.get(voice_key, DEFAULT_VOICE_MAP['host']); call synthesize.
      build(script) -> list[bytes]: list comprehension calling synthesize_segment per entry.
      save(script, output_dir) -> list[Path]: build + mkdir + write segment_NN.mp3 files.
    hint: >
      synthesize_segment: voice = self._voice_map.get(voice_key, DEFAULT_VOICE_MAP['host']);
      return synthesize(text, voice=voice, tts_fn=self._tts_fn, rate=rate, pitch=pitch).
      build: [self.synthesize_segment(e['text'], e.get('voice_key','host'), ...) for e in script].
    narration: >
      PodcastGenerator is the Day 73 deliverable. It turns a plain-text
      script into numbered audio files with one call, using mock injection
      for development and real Edge TTS for production.

  - type: summary
    heading: "Lesson 5 Summary — Day 73 Complete"
    bullets:
      - "PodcastGenerator: voice_map + tts_fn bound at construction"
      - "synthesize_segment: role name → voice lookup → synthesize"
      - "build: list comprehension over script entries"
      - "save: build + mkdir + write segment_NN.mp3"
      - "Tomorrow (Day 74): Video Basics — frames, FFmpeg from Python"
    narration: >
      Day 73 is complete. You can write a multi-voice podcast script,
      assign voices by role, control rate and pitch per segment, and
      produce numbered audio files — all with a single class that runs
      in tests without any network access.
"""

for i, content in enumerate([_LESSON_01, _LESSON_02, _LESSON_03,
                               _LESSON_04, _LESSON_05], start=1):
    (OUT / "lessons" / f"day_{DAY}_lesson_0{i}.yaml").write_text(content)

# ── shared helpers ────────────────────────────────────────────────────────────
_HELPER_SRC = """\
import asyncio
from pathlib import Path

COMMON_VOICES = [
    {'ShortName': 'en-US-AriaNeural',    'Gender': 'Female', 'Locale': 'en-US'},
    {'ShortName': 'en-US-GuyNeural',     'Gender': 'Male',   'Locale': 'en-US'},
    {'ShortName': 'en-GB-LibbyNeural',   'Gender': 'Female', 'Locale': 'en-GB'},
    {'ShortName': 'en-AU-NatashaNeural', 'Gender': 'Female', 'Locale': 'en-AU'},
    {'ShortName': 'fr-FR-DeniseNeural',  'Gender': 'Female', 'Locale': 'fr-FR'},
    {'ShortName': 'de-DE-KatjaNeural',   'Gender': 'Female', 'Locale': 'de-DE'},
]

DEFAULT_VOICE_MAP = {
    'host':     'en-US-AriaNeural',
    'guest':    'en-US-GuyNeural',
    'narrator': 'en-GB-LibbyNeural',
}

def build_prosody_ssml(text, rate='+0%', pitch='+0Hz', volume='+0%'):
    return (
        '<speak version="1.0" '
        'xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">'
        f'<prosody rate="{rate}" pitch="{pitch}" volume="{volume}">'
        f'{text}'
        '</prosody></speak>'
    )

def select_voice(voices, locale='en-US', gender=None):
    for v in voices:
        if v.get('Locale') != locale:
            continue
        if gender is not None and v.get('Gender', '').lower() != gender.lower():
            continue
        return v
    return None

def synthesize(text, voice='en-US-AriaNeural', tts_fn=None, rate='+0%', pitch='+0Hz'):
    if tts_fn is not None:
        return tts_fn(text, voice=voice, rate=rate, pitch=pitch)
    import edge_tts
    async def _run():
        comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        chunks = []
        async for chunk in comm.stream():
            if chunk['type'] == 'audio':
                chunks.append(chunk['data'])
        return b''.join(chunks)
    return asyncio.run(_run())

def synthesize_segments(segments, tts_fn=None):
    out = []
    for seg in segments:
        audio = synthesize(
            seg['text'],
            voice=seg.get('voice', 'en-US-AriaNeural'),
            tts_fn=tts_fn,
            rate=seg.get('rate', '+0%'),
            pitch=seg.get('pitch', '+0Hz'),
        )
        out.append(audio)
    return out
"""

_MOCK_SRC = """\
_mock_tts = lambda text, **kw: b'AUDIO:' + text[:12].encode()
"""

# ── EXERCISE 1 — build_prosody_ssml ──────────────────────────────────────────
_EX1_STUB = """\
def build_prosody_ssml(text: str, rate: str = '+0%',
                        pitch: str = '+0Hz', volume: str = '+0%') -> str:
    \"\"\"Wrap text in a full SSML document with prosody control.

    Returns:
        SSML string with <speak><prosody rate=rate pitch=pitch volume=volume>text</prosody></speak>
    \"\"\"
    raise NotImplementedError
"""

_EX1_SOLUTION = """\
def build_prosody_ssml(text, rate='+0%', pitch='+0Hz', volume='+0%'):
    return (
        '<speak version="1.0" '
        'xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">'
        f'<prosody rate="{rate}" pitch="{pitch}" volume="{volume}">'
        f'{text}'
        '</prosody></speak>'
    )
"""

_EX1_CHECKS = r"""
score, total = 0, 5
try:
    ssml = build_prosody_ssml('Hello world.')

    # is a string
    assert isinstance(ssml, str) and len(ssml) > 0
    score += 1; print("✅ returns non-empty string")

    # contains the speak tag
    assert '<speak' in ssml and '</speak>' in ssml
    score += 1; print("✅ contains <speak> tag")

    # contains prosody with default values
    assert 'rate="+0%"' in ssml and 'pitch="+0Hz"' in ssml and 'volume="+0%"' in ssml
    score += 1; print("✅ default rate/pitch/volume in prosody tag")

    # contains the text
    assert 'Hello world.' in ssml
    score += 1; print("✅ text is embedded in the SSML")

    # custom values
    ssml2 = build_prosody_ssml('Fast!', rate='+20%', pitch='+5Hz', volume='+10%')
    assert 'rate="+20%"' in ssml2 and 'pitch="+5Hz"' in ssml2 and 'volume="+10%"' in ssml2
    score += 1; print("✅ custom rate/pitch/volume values substituted")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX1 = nb([
    md("# Day 073 — Exercise 1: build_prosody_ssml\n\n"
       "**What you'll build:** `build_prosody_ssml(text, rate, pitch, volume) -> str` — "
       "wrap text in a full SSML document for Edge TTS prosody control.\n\n"
       "**Why it matters:** SSML is the standard way to control TTS rate, pitch, "
       "and volume. Passing SSML to Edge TTS overrides the constructor parameters "
       "for fine-grained per-sentence control."),
    code(""),
    md("## Task\n\n"
       "Return this SSML string (use f-strings for substitution):\n\n"
       "```\n"
       '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">'
       '<prosody rate="{rate}" pitch="{pitch}" volume="{volume}">'
       "{text}"
       "</prosody></speak>\n"
       "```"),
    md("## Your Implementation"),
    code(_EX1_STUB),
    code(_EX1_SOLUTION),
    md("## Automated checks"),
    code(_EX1_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX1_SOLUTION + "```\n\n"
       "**Why concatenate strings rather than one big f-string?** The opening "
       "`<speak>` tag contains double quotes around attribute values, which "
       "would need escaping in an f-string. Splitting into separate strings "
       "keeps the XML clean and readable.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_01.ipynb", EX1)

# ── EXERCISE 2 — select_voice ─────────────────────────────────────────────────
_EX2_GIVEN = """\
COMMON_VOICES = [
    {'ShortName': 'en-US-AriaNeural',    'Gender': 'Female', 'Locale': 'en-US'},
    {'ShortName': 'en-US-GuyNeural',     'Gender': 'Male',   'Locale': 'en-US'},
    {'ShortName': 'en-GB-LibbyNeural',   'Gender': 'Female', 'Locale': 'en-GB'},
    {'ShortName': 'en-AU-NatashaNeural', 'Gender': 'Female', 'Locale': 'en-AU'},
    {'ShortName': 'fr-FR-DeniseNeural',  'Gender': 'Female', 'Locale': 'fr-FR'},
    {'ShortName': 'de-DE-KatjaNeural',   'Gender': 'Female', 'Locale': 'de-DE'},
]
"""

_EX2_STUB = """\
def select_voice(voices: list, locale: str = 'en-US',
                  gender: str = None) -> dict:
    \"\"\"Find the first voice matching locale and optionally gender.

    Args:
        voices: list of voice dicts (ShortName, Gender, Locale)
        locale: exact Locale string (e.g. 'en-US', 'fr-FR')
        gender: 'Female' or 'Male' (case-insensitive); None = any
    Returns:
        First matching voice dict, or None if not found
    \"\"\"
    raise NotImplementedError
"""

_EX2_SOLUTION = """\
def select_voice(voices, locale='en-US', gender=None):
    for v in voices:
        if v.get('Locale') != locale:
            continue
        if gender is not None and v.get('Gender', '').lower() != gender.lower():
            continue
        return v
    return None
"""

_EX2_CHECKS = r"""
score, total = 0, 5
try:
    # finds first voice for locale
    v = select_voice(COMMON_VOICES, locale='en-US')
    assert v is not None and v['ShortName'] == 'en-US-AriaNeural'
    score += 1; print("✅ returns first matching locale voice")

    # gender filter: Male
    v2 = select_voice(COMMON_VOICES, locale='en-US', gender='Male')
    assert v2 is not None and v2['ShortName'] == 'en-US-GuyNeural'
    score += 1; print("✅ gender='Male' returns male voice")

    # gender filter: case-insensitive
    v3 = select_voice(COMMON_VOICES, locale='en-US', gender='female')
    assert v3 is not None and v3['Gender'] == 'Female'
    score += 1; print("✅ gender comparison is case-insensitive")

    # no match returns None
    v4 = select_voice(COMMON_VOICES, locale='zh-CN')
    assert v4 is None, f"Expected None, got {v4}"
    score += 1; print("✅ no match returns None")

    # fr-FR match
    v5 = select_voice(COMMON_VOICES, locale='fr-FR')
    assert v5 is not None and v5['ShortName'] == 'fr-FR-DeniseNeural'
    score += 1; print("✅ fr-FR locale returns correct voice")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX2 = nb([
    md("# Day 073 — Exercise 2: select_voice\n\n"
       "**What you'll build:** `select_voice(voices, locale='en-US', gender=None) -> dict | None` — "
       "filter a voice catalogue to find the best matching voice.\n\n"
       "**Why it matters:** A podcast generator needs to map locales and roles "
       "to specific voice names. `select_voice` is the lookup function that "
       "makes scripts portable across locales."),
    code(_EX2_GIVEN),
    md("## Task\n\n"
       "Implement `select_voice`:\n\n"
       "```\n"
       "for v in voices:\n"
       "    if v.get('Locale') != locale: continue\n"
       "    if gender is not None and v.get('Gender','').lower() != gender.lower(): continue\n"
       "    return v\n"
       "return None\n"
       "```"),
    md("## Your Implementation"),
    code(_EX2_STUB),
    code(_EX2_SOLUTION),
    md("## Automated checks"),
    code(_EX2_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX2_SOLUTION + "```\n\n"
       "**Why `v.get('Gender', '').lower()`?** If Gender is missing from a voice "
       "dict, `.get` returns `''` and `.lower()` returns `''`, which never equals "
       "the requested gender — safe fallback without KeyError.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_02.ipynb", EX2)

# ── EXERCISE 3 — synthesize ──────────────────────────────────────────────────
_EX3_GIVEN = "import asyncio\n" + _MOCK_SRC

_EX3_STUB = """\
def synthesize(text: str, voice: str = 'en-US-AriaNeural',
               tts_fn=None, rate: str = '+0%', pitch: str = '+0Hz') -> bytes:
    \"\"\"Synthesize text to audio bytes using Edge TTS.

    Args:
        text:   Text or SSML string
        voice:  Edge TTS voice ShortName
        tts_fn: callable(text, voice, rate, pitch) -> bytes for testing
        rate:   Speed adjustment e.g. '+10%', '-20%'
        pitch:  Pitch adjustment e.g. '+5Hz', '-2Hz'
    Returns:
        Audio bytes (MP3 when using real Edge TTS)
    \"\"\"
    raise NotImplementedError
"""

_EX3_SOLUTION = """\
def synthesize(text, voice='en-US-AriaNeural', tts_fn=None,
               rate='+0%', pitch='+0Hz'):
    if tts_fn is not None:
        return tts_fn(text, voice=voice, rate=rate, pitch=pitch)
    import edge_tts
    async def _run():
        comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        chunks = []
        async for chunk in comm.stream():
            if chunk['type'] == 'audio':
                chunks.append(chunk['data'])
        return b''.join(chunks)
    return asyncio.run(_run())
"""

_EX3_CHECKS = r"""
score, total = 0, 5
try:
    # returns bytes
    audio = synthesize('Hello world!', tts_fn=_mock_tts)
    assert isinstance(audio, bytes) and len(audio) > 0
    score += 1; print("✅ returns non-empty bytes")

    # tts_fn receives text as first arg
    captured = {}
    def _cap(text, **kw):
        captured['text'] = text; captured.update(kw)
        return b'captured'
    synthesize('Test sentence.', voice='en-GB-LibbyNeural',
               tts_fn=_cap, rate='+10%', pitch='+2Hz')
    assert captured.get('text') == 'Test sentence.'
    score += 1; print("✅ tts_fn receives text as first positional arg")

    # all kwargs forwarded
    assert captured.get('voice') == 'en-GB-LibbyNeural'
    assert captured.get('rate')  == '+10%'
    assert captured.get('pitch') == '+2Hz'
    score += 1; print("✅ voice/rate/pitch forwarded as kwargs to tts_fn")

    # different text → different bytes (mock encodes text prefix)
    a1 = synthesize('Hello there.', tts_fn=_mock_tts)
    a2 = synthesize('Goodbye now.', tts_fn=_mock_tts)
    assert a1 != a2, "Different text should give different audio bytes"
    score += 1; print("✅ different text produces different bytes")

    # default voice used when not specified
    captured2 = {}
    def _cap2(text, **kw): captured2.update(kw); return b'x'
    synthesize('Hi', tts_fn=_cap2)
    assert captured2.get('voice') == 'en-US-AriaNeural'
    score += 1; print("✅ default voice en-US-AriaNeural when voice not specified")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX3 = nb([
    md("# Day 073 — Exercise 3: synthesize\n\n"
       "**What you'll build:** `synthesize(text, voice, tts_fn, rate, pitch) -> bytes` — "
       "the core TTS function with `tts_fn=None` injection.\n\n"
       "**Why it matters:** All higher-level functions delegate to `synthesize`. "
       "Getting the injection pattern and parameter forwarding right makes "
       "every downstream function automatically testable."),
    code(_EX3_GIVEN),
    md("## Task\n\n"
       "Implement `synthesize`:\n\n"
       "1. If `tts_fn is not None`: `return tts_fn(text, voice=voice, rate=rate, pitch=pitch)`\n"
       "2. `import edge_tts` (lazy)\n"
       "3. Define `async def _run()` that creates `edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)`, "
       "collects `chunk['data']` for chunks where `chunk['type'] == 'audio'`, "
       "returns `b''.join(chunks)`\n"
       "4. `return asyncio.run(_run())`"),
    md("## Your Implementation"),
    code(_EX3_STUB),
    code(_EX3_SOLUTION),
    md("## Automated checks"),
    code(_EX3_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX3_SOLUTION + "```\n\n"
       "**Why only collect `chunk['type'] == 'audio'` chunks?** The stream also "
       "yields `WordBoundary` chunks (timing data for word highlighting) and "
       "`SessionEnd`. Only the audio chunks contain the actual audio data.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_03.ipynb", EX3)

# ── EXERCISE 4 — synthesize_segments ─────────────────────────────────────────
_EX4_GIVEN = "import asyncio\n" + _HELPER_SRC.split("def synthesize_segments")[0] + _MOCK_SRC

_EX4_STUB = """\
def synthesize_segments(segments: list, tts_fn=None) -> list:
    \"\"\"Synthesize a list of segment dicts to audio bytes.

    Each segment: {text, voice?, rate?, pitch?}
    Defaults: voice='en-US-AriaNeural', rate='+0%', pitch='+0Hz'
    Returns: list of bytes, one per segment
    \"\"\"
    raise NotImplementedError
"""

_EX4_SOLUTION = """\
def synthesize_segments(segments, tts_fn=None):
    out = []
    for seg in segments:
        audio = synthesize(
            seg['text'],
            voice=seg.get('voice', 'en-US-AriaNeural'),
            tts_fn=tts_fn,
            rate=seg.get('rate', '+0%'),
            pitch=seg.get('pitch', '+0Hz'),
        )
        out.append(audio)
    return out
"""

_EX4_CHECKS = r"""
score, total = 0, 5
try:
    script = [
        {'text': 'Welcome to the show.', 'voice': 'en-US-AriaNeural'},
        {'text': 'Thanks for having me!', 'voice': 'en-US-GuyNeural', 'rate': '+10%'},
        {'text': "Let's dive in.",        'voice': 'en-US-AriaNeural'},
    ]
    parts = synthesize_segments(script, tts_fn=_mock_tts)

    # returns a list of correct length
    assert isinstance(parts, list) and len(parts) == 3
    score += 1; print("✅ returns list with correct item count")

    # each item is bytes
    assert all(isinstance(p, bytes) for p in parts)
    score += 1; print("✅ all items are bytes")

    # each item is non-empty
    assert all(len(p) > 0 for p in parts)
    score += 1; print("✅ all items are non-empty")

    # defaults work when voice/rate/pitch absent
    minimal = [{'text': 'No voice specified.'}]
    min_parts = synthesize_segments(minimal, tts_fn=_mock_tts)
    assert len(min_parts) == 1 and len(min_parts[0]) > 0
    score += 1; print("✅ segment with only text key works (defaults applied)")

    # different text → different audio
    assert parts[0] != parts[1], "Different text should give different bytes"
    score += 1; print("✅ different segments produce different audio bytes")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX4 = nb([
    md("# Day 073 — Exercise 4: synthesize_segments\n\n"
       "**What you'll build:** `synthesize_segments(segments, tts_fn=None) -> list[bytes]` — "
       "synthesize a full script to a list of audio byte blobs.\n\n"
       "**Why it matters:** `synthesize_segments` is the script-to-audio pipeline. "
       "It drives the PodcastGenerator and produces the ordered list of audio "
       "parts that become numbered output files."),
    code(_EX4_GIVEN),
    md("## Task\n\n"
       "Implement `synthesize_segments`:\n\n"
       "```\n"
       "out = []\n"
       "for seg in segments:\n"
       "    audio = synthesize(seg['text'],\n"
       "                       voice=seg.get('voice', 'en-US-AriaNeural'),\n"
       "                       tts_fn=tts_fn,\n"
       "                       rate=seg.get('rate', '+0%'),\n"
       "                       pitch=seg.get('pitch', '+0Hz'))\n"
       "    out.append(audio)\n"
       "return out\n"
       "```"),
    md("## Your Implementation"),
    code(_EX4_STUB),
    code(_EX4_SOLUTION),
    md("## Automated checks"),
    code(_EX4_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX4_SOLUTION + "```\n\n"
       "**Why not use a list comprehension?** A list comprehension would work, "
       "but the explicit loop is clearer for a multi-argument call. If an "
       "exception occurs, the explicit loop makes it easier to add error "
       "handling per segment in a production version.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_04.ipynb", EX4)

# ── EXERCISE 5 — PodcastGenerator ────────────────────────────────────────────
_EX5_GIVEN = "import asyncio\nfrom pathlib import Path\n" + _HELPER_SRC + _MOCK_SRC

_EX5_STUB = """\
class PodcastGenerator:
    \"\"\"Generate podcast-style audio from a script using Edge TTS.

    Inject tts_fn for testing without a network connection.
    \"\"\"

    def __init__(self, voice_map=None, tts_fn=None) -> None:
        raise NotImplementedError

    def synthesize_segment(self, text: str, voice_key: str = 'host',
                            rate: str = '+0%', pitch: str = '+0Hz') -> bytes:
        \"\"\"Synthesize one segment. Looks up voice from self._voice_map.\"\"\"
        raise NotImplementedError

    def build(self, script: list) -> list:
        \"\"\"Synthesize all script entries. Returns list[bytes].

        Each entry: {text, voice_key?, rate?, pitch?}
        \"\"\"
        raise NotImplementedError

    def save(self, script: list, output_dir) -> list:
        \"\"\"Build and save to segment_NN.mp3 files. Returns list[Path].\"\"\"
        raise NotImplementedError
"""

_EX5_SOLUTION = """\
class PodcastGenerator:
    def __init__(self, voice_map=None, tts_fn=None):
        self._voice_map = voice_map if voice_map is not None else DEFAULT_VOICE_MAP
        self._tts_fn    = tts_fn

    def synthesize_segment(self, text, voice_key='host', rate='+0%', pitch='+0Hz'):
        voice = self._voice_map.get(voice_key, DEFAULT_VOICE_MAP['host'])
        return synthesize(text, voice=voice, tts_fn=self._tts_fn,
                          rate=rate, pitch=pitch)

    def build(self, script):
        return [
            self.synthesize_segment(
                e['text'],
                e.get('voice_key', 'host'),
                e.get('rate', '+0%'),
                e.get('pitch', '+0Hz'),
            )
            for e in script
        ]

    def save(self, script, output_dir):
        parts = self.build(script)
        out   = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        paths = []
        for i, audio in enumerate(parts, start=1):
            p = out / f'segment_{i:02d}.mp3'
            p.write_bytes(audio)
            paths.append(p)
        return paths
"""

_EX5_CHECKS = r"""
import tempfile
score, total = 0, 5
try:
    gen = PodcastGenerator(tts_fn=_mock_tts)

    # synthesize_segment returns bytes
    seg_audio = gen.synthesize_segment('Welcome to the show.', voice_key='host')
    assert isinstance(seg_audio, bytes) and len(seg_audio) > 0
    score += 1; print("✅ synthesize_segment returns non-empty bytes")

    # build returns list of correct length
    script = [
        {'text': 'Hello everyone.', 'voice_key': 'host'},
        {'text': 'Hi there!',        'voice_key': 'guest'},
        {'text': 'And we begin.',    'voice_key': 'narrator'},
    ]
    parts = gen.build(script)
    assert isinstance(parts, list) and len(parts) == 3
    assert all(isinstance(p, bytes) for p in parts)
    score += 1; print("✅ build returns list of 3 bytes objects")

    # different voice_keys → voice map used
    captured = {}
    def _cap_voice(text, **kw): captured['voice'] = kw.get('voice'); return b'x'
    gen2 = PodcastGenerator(tts_fn=_cap_voice)
    gen2.synthesize_segment('Test', voice_key='guest')
    assert captured.get('voice') == DEFAULT_VOICE_MAP['guest']
    score += 1; print("✅ voice_key correctly mapped to voice ShortName")

    # save writes files
    with tempfile.TemporaryDirectory() as tmpdir:
        paths = gen.save(script, tmpdir)
        assert len(paths) == 3
        names = [Path(p).name for p in paths]
        assert names == ['segment_01.mp3', 'segment_02.mp3', 'segment_03.mp3']
        assert all(Path(p).stat().st_size > 0 for p in paths)
    score += 1; print("✅ save creates segment_NN.mp3 files with content")

    # unknown voice_key falls back to host voice
    captured2 = {}
    def _cap2(text, **kw): captured2['voice'] = kw.get('voice'); return b'x'
    gen3 = PodcastGenerator(tts_fn=_cap2)
    gen3.synthesize_segment('Hi', voice_key='unknown_role_xyz')
    assert captured2.get('voice') == DEFAULT_VOICE_MAP['host']
    score += 1; print("✅ unknown voice_key falls back to host voice")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX5 = nb([
    md("# Day 073 — Exercise 5: PodcastGenerator\n\n"
       "**What you'll build:** `PodcastGenerator` — the full podcast pipeline "
       "with role-to-voice mapping, multi-segment synthesis, and file output.\n\n"
       "**Why it matters:** The class abstracts the script format from the voice "
       "implementation. A script using role names (host, guest) works unchanged "
       "whether voices are English, French, or any other locale."),
    code(_EX5_GIVEN),
    md("## Task\n\nImplement `PodcastGenerator`:\n\n"
       "- `__init__(voice_map=None, tts_fn=None)`: store both; "
       "`self._voice_map = voice_map if voice_map is not None else DEFAULT_VOICE_MAP`\n"
       "- `synthesize_segment(text, voice_key='host', rate='+0%', pitch='+0Hz') -> bytes`: "
       "`voice = self._voice_map.get(voice_key, DEFAULT_VOICE_MAP['host'])`; call `synthesize`\n"
       "- `build(script) -> list[bytes]`: list comprehension calling `synthesize_segment` "
       "per entry using `e.get('voice_key','host')`, `e.get('rate','+0%')`, `e.get('pitch','+0Hz')`\n"
       "- `save(script, output_dir) -> list[Path]`: `build` + mkdir + "
       "write `segment_NN.mp3` + return paths"),
    md("## Your Implementation"),
    code(_EX5_STUB),
    code(_EX5_SOLUTION),
    md("## Automated checks"),
    code(_EX5_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX5_SOLUTION + "```\n\n"
       "**Why `voice_map if voice_map is not None else DEFAULT_VOICE_MAP`?** "
       "The same `is not None` check used for template injection (Day 64) and "
       "style templates (Day 70). An explicit empty dict `{}` would mean no "
       "voices — don't fall back to defaults silently.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_05.ipynb", EX5)

# ── PROJECT NOTEBOOK ──────────────────────────────────────────────────────────
PROJECT = nb([
    md("# Day 073 — Project: Podcast Generator\n\n"
       "## What You're Building\n\n"
       "`podcast_generator.py` — a `PodcastGenerator` class for multi-voice TTS.\n\n"
       "## Setup\n\n"
       "```bash\n"
       "pip install edge-tts\n"
       "pip install nest_asyncio   # for Jupyter\n"
       "```\n\n"
       "## Design\n\n"
       "```\n"
       "build_prosody_ssml(text, rate, pitch, volume) -> str\n"
       "select_voice(voices, locale, gender) -> dict | None\n"
       "synthesize(text, voice, tts_fn, rate, pitch) -> bytes\n"
       "synthesize_segments(segments, tts_fn) -> list[bytes]\n"
       "PodcastGenerator(voice_map, tts_fn)\n"
       "  .synthesize_segment(text, voice_key, rate, pitch) -> bytes\n"
       "  .build(script) -> list[bytes]\n"
       "  .save(script, output_dir) -> list[Path]\n"
       "```"),
    code("# Your implementation here — build PodcastGenerator and write podcast_generator.py\n"),
])
save(OUT / "project" / "project.ipynb", PROJECT)

# ── SOLUTION NOTEBOOK ─────────────────────────────────────────────────────────
_SOL_CELL1 = (
    f"_PODCAST_SRC = {repr(_PODCAST_SRC)}\n"
    "from pathlib import Path\n"
    "Path('podcast_generator.py').write_text(_PODCAST_SRC, encoding='utf-8')\n"
    "print('podcast_generator.py written.')"
)

_SOL_CELL2 = """\
import tempfile
from pathlib import Path
from podcast_generator import (
    COMMON_VOICES, DEFAULT_VOICE_MAP,
    build_prosody_ssml, select_voice, synthesize,
    synthesize_segments, PodcastGenerator,
)

mock = lambda text, **kw: b'AUDIO:' + text[:12].encode()

# 1. build_prosody_ssml
ssml = build_prosody_ssml('Hello.', rate='-5%', pitch='-2Hz')
assert '<speak' in ssml and 'rate="-5%"' in ssml and 'Hello.' in ssml
print("\\u2705 build_prosody_ssml correct")

# 2. select_voice
v = select_voice(COMMON_VOICES, locale='en-US', gender='Male')
assert v['ShortName'] == 'en-US-GuyNeural'
assert select_voice(COMMON_VOICES, locale='xx-XX') is None
print("\\u2705 select_voice correct")

# 3. synthesize
audio = synthesize('Test text.', tts_fn=mock, rate='+10%')
assert isinstance(audio, bytes) and len(audio) > 0
print("\\u2705 synthesize correct")

# 4. synthesize_segments
script = [
    {'text': 'Hello.', 'voice': 'en-US-AriaNeural'},
    {'text': 'Hi!',    'voice': 'en-US-GuyNeural', 'rate': '+10%'},
]
parts = synthesize_segments(script, tts_fn=mock)
assert len(parts) == 2 and all(isinstance(p, bytes) for p in parts)
print("\\u2705 synthesize_segments correct")

# 5. PodcastGenerator
gen = PodcastGenerator(tts_fn=mock)
podcast = [
    {'text': 'Welcome to the show.',    'voice_key': 'host'},
    {'text': 'Glad to be here!',        'voice_key': 'guest', 'rate': '+10%'},
    {'text': 'And we are underway.',    'voice_key': 'narrator'},
]
built = gen.build(podcast)
assert len(built) == 3 and all(isinstance(p, bytes) for p in built)

with tempfile.TemporaryDirectory() as tmpdir:
    paths = gen.save(podcast, tmpdir)
    names = [Path(p).name for p in paths]
    assert names == ['segment_01.mp3', 'segment_02.mp3', 'segment_03.mp3']
    assert all(Path(p).stat().st_size > 0 for p in paths)

print("\\u2705 PodcastGenerator correct")
print("\\nPodcast Generator complete!")
"""

SOLUTION = nb([
    md("# Day 073 — Solution: Podcast Generator"),
    code(_SOL_CELL1),
    code(_SOL_CELL2),
])
save(OUT / "project" / "solution" / "solution.ipynb", SOLUTION)
(OUT / "project" / "solution" / "podcast_generator.py").write_text(_PODCAST_SRC)

print(f"Day {DAY} notebooks written to {OUT}")
print("  lessons/    day_073_lesson_01.yaml – lesson_05.yaml")
print("  exercises/  exercise_01 – exercise_05")
print("  project/    project.ipynb")
print("  project/solution/  solution.ipynb + podcast_generator.py")
