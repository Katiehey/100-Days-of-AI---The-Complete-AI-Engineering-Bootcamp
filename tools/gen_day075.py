#!/usr/bin/env python3
"""gen_day075.py — generate Day 075: Talking-Head Pipeline."""
from pathlib import Path
import json

ROOT    = Path(__file__).parent.parent
DAY     = "075"
SECTION = "05_vision_multimodal"
OUT     = ROOT / SECTION / f"day_{DAY}"

(OUT / "exercises").mkdir(parents=True, exist_ok=True)
(OUT / "lessons").mkdir(parents=True, exist_ok=True)
(OUT / "project" / "solution").mkdir(parents=True, exist_ok=True)

# ── deliverable: talking_head.py ──────────────────────────────────────────────
_TALKING_HEAD_SRC = '''\
"""talking_head.py — Day 075: Talking-Head Video Pipeline.

Create a talking-head video from a text script:
1. generate_speech  — TTS audio bytes (edge-tts)
2. image_to_frames  — face image → repeated BGR numpy frame list
3. mux_audio_video  — FFmpeg: combine silent video + audio → MP4
4. add_captions     — FFmpeg drawtext: burn caption onto video

All functions accept injection callables for headless testing.

Jupyter note: generate_speech uses asyncio.run(). In Jupyter, first run:
    import nest_asyncio; nest_asyncio.apply()

Setup:
    pip install edge-tts opencv-python-headless Pillow
    brew install ffmpeg   # macOS
"""
import subprocess
import tempfile
from pathlib import Path
from typing import Callable, Optional


def generate_speech(text: str, voice: str = 'en-US-AriaNeural',
                    rate: str = '+0%', pitch: str = '+0Hz',
                    tts_fn: Optional[Callable] = None) -> bytes:
    """Generate speech audio bytes from text using edge-tts.

    Args:
        text:   text to synthesise
        voice:  edge-tts ShortName (e.g. 'en-US-AriaNeural')
        rate:   speaking rate adjustment ('+10%', '-5%', ...)
        pitch:  pitch adjustment ('+5Hz', '-10Hz', ...)
        tts_fn: callable(text, voice, rate, pitch) -> bytes for testing
    Returns:
        MP3 audio bytes
    """
    if tts_fn is not None:
        return tts_fn(text, voice, rate, pitch)
    import asyncio
    import edge_tts

    async def _run():
        comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        chunks = []
        async for chunk in comm.stream():
            if chunk['type'] == 'audio':
                chunks.append(chunk['data'])
        return b''.join(chunks)

    return asyncio.run(_run())


def image_to_frames(image, n_frames: int,
                    capture_fn: Optional[Callable] = None) -> list:
    """Create n_frames identical BGR frames from a face image.

    Args:
        image:      PIL Image object or path to image file (str or Path)
        n_frames:   number of frames to generate
        capture_fn: callable(image, n_frames) -> list[np.ndarray] for testing
    Returns:
        list of numpy arrays (H, W, 3) uint8 BGR — n_frames elements
    """
    if capture_fn is not None:
        return capture_fn(image, n_frames)
    import numpy as np
    from PIL import Image as PILImage
    if not isinstance(image, PILImage.Image):
        image = PILImage.open(str(image)).convert('RGB')
    arr = np.array(image)[:, :, ::-1].astype(np.uint8)  # RGB -> BGR
    return [arr.copy() for _ in range(n_frames)]


def mux_audio_video(video_path, audio_bytes: bytes, output_path,
                    ffmpeg_fn: Optional[Callable] = None) -> Path:
    """Combine a silent video file with audio bytes into a new MP4.

    Args:
        video_path:  path to silent video file
        audio_bytes: MP3 audio bytes to add as soundtrack
        output_path: destination MP4 path
        ffmpeg_fn:   callable(video_path, audio_bytes, output_path) -> Path
    Returns:
        Path to the output video with audio
    """
    if ffmpeg_fn is not None:
        return ffmpeg_fn(video_path, audio_bytes, output_path)
    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
        f.write(audio_bytes)
        audio_path = f.name
    try:
        out_path = Path(output_path)
        result = subprocess.run(
            ['ffmpeg', '-y', '-i', str(video_path), '-i', audio_path,
             '-c:v', 'copy', '-c:a', 'aac', '-shortest', str(out_path)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f'FFmpeg mux error: {result.stderr[-500:]}')
        return out_path
    finally:
        Path(audio_path).unlink(missing_ok=True)


def add_captions(video_path, text: str, output_path,
                 fontsize: int = 24, color: str = 'white',
                 ffmpeg_fn: Optional[Callable] = None) -> Path:
    """Burn a caption onto a video using FFmpeg drawtext filter.

    Args:
        video_path:  source video
        text:        caption text (single line)
        output_path: destination path
        fontsize:    font size in pixels
        color:       text colour ('white', 'yellow', 'black', ...)
        ffmpeg_fn:   callable(video_path, text, output_path) -> Path
    Returns:
        Path to captioned video
    """
    if ffmpeg_fn is not None:
        return ffmpeg_fn(video_path, text, output_path)
    safe_text = text.replace("'", r"\\'").replace(':', r'\\:')
    out_path = Path(output_path)
    result = subprocess.run(
        ['ffmpeg', '-y', '-i', str(video_path),
         '-vf', (f"drawtext=text='{safe_text}':fontsize={fontsize}:"
                 f"fontcolor={color}:x=(w-text_w)/2:y=h-text_h-20"),
         str(out_path)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f'FFmpeg caption error: {result.stderr[-500:]}')
    return out_path


class TalkingHeadPipeline:
    """Create talking-head videos from text and a face image.

    Bind injection functions at construction for easy testing::

        pipe = TalkingHeadPipeline(
            tts_fn=lambda text, voice, rate, pitch: b'MP3_AUDIO',
            capture_fn=lambda img, n: [np.zeros((64,64,3), np.uint8)] * n,
            mux_fn=lambda vp, ab, op: (Path(op).write_bytes(b'V'), Path(op))[1],
            caption_fn=lambda vp, t, op: (Path(op).write_bytes(b'C'), Path(op))[1],
        )
    """

    def __init__(self, tts_fn: Optional[Callable] = None,
                 capture_fn: Optional[Callable] = None,
                 mux_fn: Optional[Callable] = None,
                 caption_fn: Optional[Callable] = None) -> None:
        self._tts_fn     = tts_fn
        self._capture_fn = capture_fn
        self._mux_fn     = mux_fn
        self._caption_fn = caption_fn

    def speech(self, text: str, voice: str = 'en-US-AriaNeural',
               rate: str = '+0%', pitch: str = '+0Hz') -> bytes:
        """Generate speech audio bytes."""
        return generate_speech(text, voice=voice, rate=rate, pitch=pitch,
                               tts_fn=self._tts_fn)

    def frames(self, image, n_frames: int) -> list:
        """Return n_frames BGR numpy arrays from a face image."""
        return image_to_frames(image, n_frames, capture_fn=self._capture_fn)

    def mux(self, video_path, audio_bytes: bytes, output_path) -> Path:
        """Combine silent video + audio into output MP4."""
        return mux_audio_video(video_path, audio_bytes, output_path,
                               ffmpeg_fn=self._mux_fn)

    def caption(self, video_path, text: str, output_path,
                fontsize: int = 24, color: str = 'white') -> Path:
        """Burn a caption onto a video."""
        return add_captions(video_path, text, output_path,
                            fontsize=fontsize, color=color,
                            ffmpeg_fn=self._caption_fn)
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
day: "075"
lesson: 1
title: "Talking-Head Pipeline Overview"
slides:
  - type: title
    heading: "Talking-Head Pipeline"
    subheading: "Day 75 — TTS + frames + mux + captions"
    narration: >
      Day 75 assembles everything built in Section 5 into a single production
      pipeline: take a text script and a face image, synthesise speech, create
      video frames, combine audio and video with FFmpeg, then burn captions.
      This is the lesson-video pipeline that underpins the whole course — you
      are rebuilding it from scratch today.

  - type: concept
    label: "Pipeline stages"
    heading: "Four Stages of a Talking-Head Video"
    body: >
      A talking-head video is a face that appears to speak text. Building one
      requires four independent operations that compose into a pipeline.
    bullets:
      - "1. generate_speech: text → MP3 audio bytes (edge-tts)"
      - "2. image_to_frames: face image → list of BGR numpy frame arrays"
      - "3. mux_audio_video: silent video + audio bytes → MP4 with soundtrack"
      - "4. add_captions: video + caption text → video with burned-in text"
    narration: >
      Each stage is a pure function with an injection parameter for testing.
      You never need a real video file, FFmpeg binary, or edge-tts API key to
      run the exercises — every stage is mockable. The four functions are
      independent: you can replace any stage (e.g. swap edge-tts for a
      different TTS engine) without touching the others. The TalkingHeadPipeline
      class binds all four injection functions at construction, giving the same
      ergonomic interface as VideoProcessor (Day 74), AudioTranscriber (Day 72),
      and PodcastGenerator (Day 73).

  - type: how_it_works
    label: "Pipeline composition"
    heading: "Composing the Pipeline"
    body: >
      The four stages connect output-to-input: audio bytes flow into mux,
      video path flows into both mux and captions.
    bullets:
      - "audio = generate_speech(text, voice, rate, pitch)"
      - "frames = image_to_frames(face_img, n_frames)"
      - "silent  = VideoProcessor.to_video(frames, 'silent.mp4', fps=30)"
      - "muxed   = mux_audio_video(silent, audio, 'with_audio.mp4')"
      - "final   = add_captions(muxed, caption_text, 'final.mp4')"
    narration: >
      The frames-to-video step uses VideoProcessor from Day 74. This is
      deliberate: each day's deliverable is a reusable module, and Day 75
      builds on Day 74 rather than duplicating it. The pipeline is explicitly
      sequential — each function's output becomes the next function's input.
      In a real production pipeline you would parallelise the TTS and
      frame-generation steps (they are independent) and pipeline the video
      write and mux steps. For learning purposes, the sequential form is
      clearer.

  - type: concept
    label: "n_frames from audio"
    heading: "Estimating Frame Count from Audio Duration"
    body: >
      The video and audio must have compatible durations for mux to work.
      Frame count controls video duration: duration_sec = n_frames / fps.
    bullets:
      - "MP3 at 128 kbps: bytes = duration_sec * 128_000 / 8"
      - "Rearranged: duration_sec = len(audio_bytes) * 8 / 128_000"
      - "n_frames = int(duration_sec * fps) — at least 1"
      - "For 30 fps: 1 second of 128kbps MP3 ≈ 16 KB"
      - "FFmpeg -shortest flag: video ends with the shorter stream"
    narration: >
      The -shortest flag in FFmpeg mux means the output duration equals
      whichever stream ends first — audio or video. If you generate more
      frames than the audio covers, the silent tail is trimmed. If you generate
      fewer frames than the audio duration, the audio tail is trimmed. For
      exact sync, compute n_frames from the audio byte count: at 128kbps,
      one second of MP3 is 128_000 / 8 = 16_000 bytes. So n_frames = int(
      len(audio_bytes) / 16_000 * fps). In tests, the mock TTS returns small
      byte strings, so use max(int(...), 1) to guarantee at least one frame.

  - type: summary
    heading: "Lesson 1 Summary"
    bullets:
      - "Pipeline: generate_speech → image_to_frames → to_video → mux → caption"
      - "Each stage is independent and fully mockable"
      - "n_frames controls video duration: duration = n_frames / fps"
      - "Estimate from 128kbps MP3: n = int(len(audio)*8/128_000 * fps)"
      - "FFmpeg -shortest trims to the shorter stream"
      - "TalkingHeadPipeline binds all 4 injection fns at construction"
    narration: >
      The pipeline architecture is clear. Next: the first stage — generating
      speech audio with edge-tts.
"""

_LESSON_02 = """\
day: "075"
lesson: 2
title: "generate_speech — TTS Audio Synthesis"
slides:
  - type: title
    heading: "generate_speech"
    subheading: "edge-tts Communicate — async wrapper — bytes output"
    narration: >
      The first pipeline stage wraps edge-tts to produce MP3 audio bytes.
      Day 73 built PodcastGenerator with multi-voice synthesis. Day 75 uses
      a simpler single-call wrapper: one text, one voice, one call, one bytes
      result. The tts_fn injection lets every exercise run without edge-tts
      installed.

  - type: code
    label: "generate_speech"
    heading: "generate_speech Implementation"
    code: |
      import asyncio
      import edge_tts

      def generate_speech(text, voice='en-US-AriaNeural',
                          rate='+0%', pitch='+0Hz', tts_fn=None):
          if tts_fn is not None:
              return tts_fn(text, voice, rate, pitch)

          async def _run():
              comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
              chunks = []
              async for chunk in comm.stream():
                  if chunk['type'] == 'audio':
                      chunks.append(chunk['data'])
              return b''.join(chunks)

          return asyncio.run(_run())

      # Mock for testing (no edge-tts needed)
      _mock_tts = lambda text, voice, rate, pitch: b'MP3:' + text[:8].encode()
      audio = generate_speech('Hello!', tts_fn=_mock_tts)
      print(len(audio), audio[:10])   # 10  b'MP3:Hello!'
    narration: >
      The tts_fn signature is (text, voice, rate, pitch) -> bytes. All four
      positional arguments are included even though many mocks only use text,
      because the real function always receives all four. This makes it easy
      to write a mock that checks which voice was used or what rate was
      requested. The asyncio.run(_run()) pattern is the same as Day 73 — a
      sync wrapper around an async function. In a Jupyter cell, wrap with
      nest_asyncio.apply() first if the event loop is already running.

  - type: concept
    label: "rate and pitch"
    heading: "Rate and Pitch Parameters"
    body: >
      edge-tts supports relative rate and pitch adjustments using a sign-
      percentage or sign-Hz notation.
    bullets:
      - "rate='+0%': no change (default)"
      - "rate='+20%': 20% faster speaking"
      - "rate='-10%': 10% slower speaking"
      - "pitch='+0Hz': no change (default)"
      - "pitch='+5Hz': slightly higher pitch"
    narration: >
      Rate adjustment is particularly useful for lesson videos: a rate of
      +5% to +10% keeps pacing brisk without sounding rushed. Very fast rates
      (+50% and above) become difficult to understand. Pitch is more subtle
      — large pitch shifts can make the voice sound artificial. The notation
      is the same SSML prosody notation from Day 73: edge-tts sends it as
      SSML to the Microsoft neural TTS service. Both parameters are forwarded
      directly to Communicate() without modification.

  - type: concept
    label: "asyncio in Jupyter"
    heading: "asyncio.run() in Jupyter"
    body: >
      Jupyter runs its own event loop. asyncio.run() fails if an event loop
      is already running. Two solutions for generate_speech in notebooks.
    bullets:
      - "Solution 1: tts_fn injection — never call asyncio.run() in exercises"
      - "Solution 2 (real use): import nest_asyncio; nest_asyncio.apply()"
      - "nest_asyncio patches asyncio to allow nested loops in Jupyter"
      - "After apply(): asyncio.run() works normally inside notebook cells"
      - "Or: use top-level await in a cell (avoids asyncio.run() entirely)"
    narration: >
      In the exercises, the tts_fn injection means asyncio.run() is never
      called — the mock returns bytes directly. For real use in a Jupyter
      notebook, import nest_asyncio and call apply() once at the top of the
      notebook. This is the same pattern used in Day 73's PodcastGenerator
      exercise. Alternatively, restructure the calling cell to use top-level
      await: await generate_speech_async(text) where the async version skips
      the asyncio.run() wrapper. Day 75 keeps the sync interface for
      consistency with the rest of the pipeline.

  - type: exercise
    heading: "Exercise 1: generate_speech"
    prompt: >
      Implement generate_speech(text, voice='en-US-AriaNeural',
      rate='+0%', pitch='+0Hz', tts_fn=None) -> bytes.
      If tts_fn is not None: return tts_fn(text, voice, rate, pitch).
      Otherwise: import asyncio, edge_tts; define async _run() that creates
      edge_tts.Communicate(text, voice, rate=rate, pitch=pitch), streams
      chunks, collects chunk['data'] for chunks where chunk['type']=='audio',
      returns b''.join(chunks). Then return asyncio.run(_run()).
    hint: >
      if tts_fn is not None: return tts_fn(text, voice, rate, pitch).
      import asyncio, edge_tts. async def _run(): comm = edge_tts.Communicate(
      text, voice, rate=rate, pitch=pitch); chunks=[]; async for chunk in comm.stream():
      if chunk['type']=='audio': chunks.append(chunk['data']); return b''.join(chunks).
      return asyncio.run(_run()).
    narration: >
      generate_speech is the Day 75 TTS entry point — simpler than
      PodcastGenerator (single segment, no voice map), but the core
      asyncio + edge-tts pattern is identical.

  - type: summary
    heading: "Lesson 2 Summary"
    bullets:
      - "generate_speech(text, voice, rate, pitch, tts_fn=None) -> bytes"
      - "tts_fn injection: lambda text, voice, rate, pitch: mock_bytes"
      - "Real path: asyncio.run(_run()) where _run uses edge_tts.Communicate"
      - "Stream chunks: only collect chunk['data'] when chunk['type']=='audio'"
      - "Join chunks: b''.join(chunks) → valid MP3 byte string"
      - "Jupyter: nest_asyncio.apply() or top-level await for real use"
    narration: >
      Speech generation is complete. Next: turning a face image into repeated
      video frames.
"""

_LESSON_03 = """\
day: "075"
lesson: 3
title: "image_to_frames — Face Image to BGR Frame List"
slides:
  - type: title
    heading: "image_to_frames"
    subheading: "PIL → BGR numpy → repeated frames"
    narration: >
      The second pipeline stage converts a single face image into the frame
      list that VideoProcessor needs to write a video file. The talking head
      does not move in the simplest version — the same frame is repeated for
      the full duration. Real lip-sync systems (Wav2Lip, SadTalker) modify
      each frame individually; today's pipeline makes the face static but the
      audio plays correctly.

  - type: code
    label: "image_to_frames"
    heading: "image_to_frames Implementation"
    code: |
      import numpy as np
      from PIL import Image as PILImage

      def image_to_frames(image, n_frames, capture_fn=None):
          if capture_fn is not None:
              return capture_fn(image, n_frames)
          if not isinstance(image, PILImage.Image):
              image = PILImage.open(str(image)).convert('RGB')
          arr = np.array(image)[:, :, ::-1].astype(np.uint8)  # RGB -> BGR
          return [arr.copy() for _ in range(n_frames)]

      # Mock for testing (no PIL or numpy at top level)
      def _make_mock_frames(n=5, height=32, width=32):
          import numpy as np
          return [np.zeros((height, width, 3), dtype=np.uint8) for _ in range(n)]

      _mock_capture = lambda img, n: _make_mock_frames(n)
      frames = image_to_frames('face.png', 10, capture_fn=_mock_capture)
      print(len(frames), frames[0].shape)   # 10  (32, 32, 3)
    narration: >
      The conversion path: PIL opens the image and converts it to RGB
      (normalising formats like RGBA or palette images). np.array(image)
      produces an (H, W, 3) uint8 array in RGB order. The [:, :, ::-1] slice
      reverses the channel axis to BGR, which OpenCV's VideoWriter expects.
      arr.copy() is essential: without it, every frame in the list would point
      to the same underlying numpy array, so modifying one frame would modify
      all. The copy() makes each frame independent.

  - type: concept
    label: "capture_fn signature"
    heading: "capture_fn vs capture_fn in Day 74"
    body: >
      image_to_frames uses a different capture_fn signature than Day 74's
      extract_frames. The signature matches the operation's inputs.
    bullets:
      - "Day 74 extract_frames: capture_fn(source) -> list[ndarray]"
      - "Day 75 image_to_frames: capture_fn(image, n_frames) -> list[ndarray]"
      - "n_frames is needed because the mock must create the right count"
      - "Rule: injection fn mirrors the real function's input (minus the fn itself)"
      - "Never pass inject_fn as first arg — it replaces the whole function body"
    narration: >
      The capture_fn for image_to_frames must accept both the image reference
      and n_frames because the real function uses both to produce the output.
      A mock that ignores n_frames would return a fixed-size list, which would
      fail checks that verify the frame count matches the request. The general
      rule is: the injection function's signature equals the real function's
      signature minus the injection parameter itself. This makes the mock easy
      to write and the intent clear.

  - type: concept
    label: "Static vs animated"
    heading: "Static vs Lip-Sync Talking Head"
    body: >
      Repeating one frame produces a static talking head. Real lip-sync
      requires per-frame mouth region generation.
    bullets:
      - "Static: [arr.copy() for _ in range(n)] — same frame repeated"
      - "Wav2Lip: generate mouth region per frame from audio mel spectrogram"
      - "SadTalker: 3D head pose + expression coefficients driven by audio"
      - "Both require pretrained model weights and GPU for real-time generation"
      - "Day 75 builds the surrounding pipeline that feeds these models"
    narration: >
      Wav2Lip and SadTalker are open-source models that take a face image and
      an audio file and produce a video where the mouth moves in sync with the
      audio. They require gigabytes of pretrained weights and a GPU to run at
      usable speed. Today's pipeline is the scaffolding: generate_speech
      produces the audio, image_to_frames produces the base frames, mux
      combines them. Plugging in a real lip-sync model means replacing the
      image_to_frames call with a lip_sync_frames call — the rest of the
      pipeline is unchanged. The modular design makes the upgrade path obvious.

  - type: exercise
    heading: "Exercise 2: image_to_frames"
    prompt: >
      Implement image_to_frames(image, n_frames, capture_fn=None) -> list.
      If capture_fn is not None: return capture_fn(image, n_frames).
      Otherwise (lazy imports numpy, PIL): if image is not a PIL Image,
      open and convert to RGB. Convert to numpy array and reverse channels
      ([:, :, ::-1]) to BGR. Return [arr.copy() for _ in range(n_frames)].
    hint: >
      if capture_fn is not None: return capture_fn(image, n_frames).
      import numpy as np; from PIL import Image as PILImage.
      if not isinstance(image, PILImage.Image): image = PILImage.open(str(image)).convert('RGB').
      arr = np.array(image)[:,:,::-1].astype(np.uint8).
      return [arr.copy() for _ in range(n_frames)].
    narration: >
      image_to_frames is the bridge between the image domain (PIL) and the
      video domain (OpenCV BGR numpy arrays). The arr.copy() pattern ensures
      each frame is mutable independently — important for downstream transforms
      like adding a text overlay per frame.

  - type: summary
    heading: "Lesson 3 Summary"
    bullets:
      - "image_to_frames(image, n_frames, capture_fn=None) -> list[ndarray]"
      - "capture_fn(image, n_frames): signature mirrors the real function inputs"
      - "PIL open → convert('RGB') → np.array → [:, :, ::-1] for BGR"
      - "arr.copy() per frame: each frame is an independent numpy array"
      - "Static pipeline: same frame n times; lip-sync: modify per frame"
      - "Frames feed into VideoProcessor.to_video() from Day 74"
    narration: >
      Frame generation is done. Next: combining a silent video with audio using
      FFmpeg.
"""

_LESSON_04 = """\
day: "075"
lesson: 4
title: "mux_audio_video and add_captions — FFmpeg Operations"
slides:
  - type: title
    heading: "mux + captions"
    subheading: "FFmpeg: two-input mux, drawtext filter"
    narration: >
      Stages 3 and 4 of the pipeline both use FFmpeg: mux combines a silent
      video file with audio bytes, and add_captions burns text onto the video
      using the drawtext filter. Both functions use the higher-level injection
      pattern where the entire function is replaced by the mock — not just the
      FFmpeg call.

  - type: code
    label: "mux_audio_video"
    heading: "mux_audio_video Implementation"
    code: |
      import subprocess, tempfile
      from pathlib import Path

      def mux_audio_video(video_path, audio_bytes, output_path, ffmpeg_fn=None):
          if ffmpeg_fn is not None:
              return ffmpeg_fn(video_path, audio_bytes, output_path)
          with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
              f.write(audio_bytes)
              audio_path = f.name
          try:
              out_path = Path(output_path)
              result = subprocess.run(
                  ['ffmpeg', '-y', '-i', str(video_path), '-i', audio_path,
                   '-c:v', 'copy', '-c:a', 'aac', '-shortest', str(out_path)],
                  capture_output=True, text=True,
              )
              if result.returncode != 0:
                  raise RuntimeError(f'FFmpeg mux error: {result.stderr[-500:]}')
              return out_path
          finally:
              Path(audio_path).unlink(missing_ok=True)
    narration: >
      The audio bytes cannot be passed directly to FFmpeg — FFmpeg needs a
      file path. The solution is to write the bytes to a named temp file,
      pass the temp path to FFmpeg, then delete it in a finally block so it
      is cleaned up even if FFmpeg raises an error. The -c:v copy flag tells
      FFmpeg not to re-encode the video frames (fast), while -c:a aac encodes
      the audio to AAC (required for MP4 containers). -shortest ensures the
      output stops at the end of the shorter stream. The two -i flags provide
      two input streams: the video file and the audio file.

  - type: code
    label: "add_captions"
    heading: "add_captions and drawtext Filter"
    code: |
      def add_captions(video_path, text, output_path,
                       fontsize=24, color='white', ffmpeg_fn=None):
          if ffmpeg_fn is not None:
              return ffmpeg_fn(video_path, text, output_path)
          safe_text = text.replace("'", r"\\'").replace(':', r'\\:')
          result = subprocess.run(
              ['ffmpeg', '-y', '-i', str(video_path),
               '-vf', (f"drawtext=text='{safe_text}':fontsize={fontsize}:"
                       f"fontcolor={color}:x=(w-text_w)/2:y=h-text_h-20"),
               str(Path(output_path))],
              capture_output=True, text=True,
          )
          if result.returncode != 0:
              raise RuntimeError(f'FFmpeg caption error: {result.stderr[-500:]}')
          return Path(output_path)

      # Key FFmpeg drawtext options:
      # x=(w-text_w)/2  — horizontally centred
      # y=h-text_h-20   — 20px above bottom edge
    narration: >
      The drawtext filter is one of FFmpeg's video filter graph options. The
      filter string uses a colon-separated key=value format. Special characters
      in the text must be escaped: a single quote ends the shell string, so
      it is escaped as backslash-quote. A colon is the filter option separator,
      so it is escaped as backslash-colon. The x and y expressions are
      evaluated at runtime against the frame dimensions w and h, and the
      rendered text dimensions text_w and text_h. Centering is the most common
      layout for lesson captions.

  - type: concept
    label: "Higher-level injection"
    heading: "Higher-Level vs Lower-Level Injection"
    body: >
      Day 74's run_ffmpeg injects at the raw-args level. Day 75's mux_fn and
      caption_fn inject at the whole-operation level.
    bullets:
      - "Day 74 low-level: ffmpeg_fn(args) -> dict — replaces subprocess.run"
      - "Day 75 high-level: mux_fn(video_path, audio_bytes, output_path) -> Path"
      - "High-level mock knows the operation's purpose, not just raw args"
      - "Trade-off: high-level is easier to mock, low-level is more general"
      - "Choose based on what the test needs to verify"
    narration: >
      Both injection patterns are valid. Low-level injection (Day 74 run_ffmpeg)
      lets you inspect exactly what command FFmpeg received. High-level
      injection (Day 75 mux_fn) lets you mock the whole mux operation without
      knowing the FFmpeg command details. For pipeline testing where you only
      care that the output file exists, high-level is simpler. For unit testing
      the FFmpeg argument construction, low-level is better. Day 75 uses
      high-level because the tests verify output files, not FFmpeg command
      structure.

  - type: exercise
    heading: "Exercise 3: mux_audio_video"
    prompt: >
      Implement mux_audio_video(video_path, audio_bytes, output_path, ffmpeg_fn=None) -> Path.
      If ffmpeg_fn is not None: return ffmpeg_fn(video_path, audio_bytes, output_path).
      Otherwise: write audio_bytes to a NamedTemporaryFile(.mp3); in a try/finally
      run subprocess.run(['ffmpeg','-y','-i',str(video_path),'-i',audio_path,
      '-c:v','copy','-c:a','aac','-shortest',str(out_path)],
      capture_output=True, text=True); raise RuntimeError if returncode != 0;
      return Path(output_path); finally: unlink(audio temp file).
    hint: >
      if ffmpeg_fn is not None: return ffmpeg_fn(video_path, audio_bytes, output_path).
      with NamedTemporaryFile(suffix='.mp3', delete=False) as f: f.write(audio_bytes); audio_path=f.name.
      try: out_path=Path(output_path); result=subprocess.run([...], capture_output=True, text=True);
      if result.returncode!=0: raise RuntimeError; return out_path.
      finally: Path(audio_path).unlink(missing_ok=True).
    narration: >
      mux_audio_video is the stage that gives the video its voice — combining
      the silent frame sequence with the generated speech track.

  - type: summary
    heading: "Lesson 4 Summary"
    bullets:
      - "mux: write audio_bytes to temp .mp3 → ffmpeg -i video -i audio -shortest"
      - "finally: unlink temp audio file (cleanup even on exception)"
      - "-c:v copy: no video re-encode (fast); -c:a aac: encode audio for MP4"
      - "add_captions: drawtext filter with x=(w-text_w)/2 y=h-text_h-20"
      - "Escape text for drawtext: leading backslash before single-quote and colon"
      - "High-level injection: mux_fn(video_path, audio_bytes, output_path) -> Path"
    narration: >
      Both FFmpeg stages are done. The final lesson assembles them into
      TalkingHeadPipeline.
"""

_LESSON_05 = """\
day: "075"
lesson: 5
title: "TalkingHeadPipeline — Full Pipeline Class"
slides:
  - type: title
    heading: "TalkingHeadPipeline"
    subheading: "speech, frames, mux, caption — all bound at construction"
    narration: >
      The fifth lesson completes the talking-head pipeline by binding all four
      injection functions into a single TalkingHeadPipeline class. The pattern
      is identical to every Section 5 pipeline class: bind mocks once at
      construction, call methods naturally, swap to real implementations by
      removing the injection arguments.

  - type: code
    label: "TalkingHeadPipeline"
    heading: "TalkingHeadPipeline Implementation"
    code: |
      class TalkingHeadPipeline:
          def __init__(self, tts_fn=None, capture_fn=None,
                       mux_fn=None, caption_fn=None):
              self._tts_fn     = tts_fn
              self._capture_fn = capture_fn
              self._mux_fn     = mux_fn
              self._caption_fn = caption_fn

          def speech(self, text, voice='en-US-AriaNeural',
                     rate='+0%', pitch='+0Hz'):
              return generate_speech(text, voice=voice, rate=rate, pitch=pitch,
                                     tts_fn=self._tts_fn)

          def frames(self, image, n_frames):
              return image_to_frames(image, n_frames,
                                     capture_fn=self._capture_fn)

          def mux(self, video_path, audio_bytes, output_path):
              return mux_audio_video(video_path, audio_bytes, output_path,
                                     ffmpeg_fn=self._mux_fn)

          def caption(self, video_path, text, output_path,
                      fontsize=24, color='white'):
              return add_captions(video_path, text, output_path,
                                  fontsize=fontsize, color=color,
                                  ffmpeg_fn=self._caption_fn)
    narration: >
      Four injection functions, four methods, each delegating to the
      corresponding module-level function with the bound injection. The
      thin delegation is intentional: all business logic is in the module-level
      functions, which are independently testable. The class provides the
      ergonomic interface: pipe.speech("Hello") rather than generate_speech(
      "Hello", tts_fn=some_fn) at every call site. This is the Section 5
      pattern: one class, bound mocks, thin wrappers.

  - type: code
    label: "Full pipeline"
    heading: "Using TalkingHeadPipeline End-to-End"
    code: |
      import tempfile, numpy as np
      from pathlib import Path
      from talking_head import TalkingHeadPipeline

      # Mock all stages
      def _mock_frames(n=5, height=64, width=64):
          import numpy as np
          return [np.zeros((height, width, 3), dtype=np.uint8) for _ in range(n)]

      pipe = TalkingHeadPipeline(
          tts_fn=lambda text, voice, rate, pitch: b'MP3:' + text[:8].encode(),
          capture_fn=lambda img, n: _mock_frames(n),
          mux_fn=lambda vp, ab, op: (Path(op).write_bytes(b'MUX' + bytes(len(ab))), Path(op))[1],
          caption_fn=lambda vp, t, op: (Path(op).write_bytes(b'CAP' + bytes(len(t))), Path(op))[1],
      )

      script = "Welcome to Day 75 — the Talking-Head Pipeline."
      audio  = pipe.speech(script, voice='en-US-GuyNeural', rate='+5%')
      frames = pipe.frames('face.png', n_frames=30)

      with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
          silent = f.name
      Path(silent).write_bytes(b'SILENT')  # placeholder (real: VideoProcessor)

      with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
          muxed = f.name
      with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
          final = f.name

      muxed_path   = pipe.mux(silent, audio, muxed)
      captioned    = pipe.caption(muxed_path, script[:40], final)
      print(captioned, captioned.stat().st_size)
    narration: >
      In production: the 'silent' placeholder is replaced by
      VideoProcessor.to_video(frames, 'silent.mp4', fps=30) from Day 74.
      Everything else stays the same. Swapping to real implementations means
      removing the four injection arguments from the TalkingHeadPipeline
      constructor — all call sites (pipe.speech, pipe.frames, pipe.mux,
      pipe.caption) remain unchanged. This is the same swap pattern used in
      Day 71 ImageSearchEngine and Day 72 AudioTranscriber.

  - type: exercise
    heading: "Exercise 5: TalkingHeadPipeline"
    prompt: >
      Implement TalkingHeadPipeline:
      __init__(tts_fn=None, capture_fn=None, mux_fn=None, caption_fn=None):
        store all four as self._tts_fn, self._capture_fn, self._mux_fn, self._caption_fn.
      speech(text, voice='en-US-AriaNeural', rate='+0%', pitch='+0Hz') -> bytes:
        return generate_speech(text, voice=voice, rate=rate, pitch=pitch, tts_fn=self._tts_fn).
      frames(image, n_frames) -> list:
        return image_to_frames(image, n_frames, capture_fn=self._capture_fn).
      mux(video_path, audio_bytes, output_path) -> Path:
        return mux_audio_video(video_path, audio_bytes, output_path, ffmpeg_fn=self._mux_fn).
      caption(video_path, text, output_path, fontsize=24, color='white') -> Path:
        return add_captions(video_path, text, output_path, fontsize=fontsize,
                            color=color, ffmpeg_fn=self._caption_fn).
    hint: >
      Each method is one return statement delegating to the module-level
      function with the corresponding self._xxx_fn bound injection.
    narration: >
      TalkingHeadPipeline completes Day 75. Combined with VideoProcessor (Day 74),
      you now have all the building blocks of the lesson-video pipeline that
      generates the audio narration, frames, and captions for every day in
      this course.

  - type: summary
    heading: "Lesson 5 Summary — Day 75 Complete"
    bullets:
      - "TalkingHeadPipeline binds tts_fn, capture_fn, mux_fn, caption_fn"
      - "Four methods: speech, frames, mux, caption — each one line"
      - "Full pipeline: speech → image_to_frames → to_video → mux → caption"
      - "In production: remove injection args, real edge-tts + OpenCV + FFmpeg run"
      - "Section 5 pattern: thin class wrappers over testable module functions"
      - "Tomorrow (Day 76): Multimodal Agents — vision + speech + text in one agent"
    narration: >
      Day 75 is complete. You have built the four-stage talking-head video
      pipeline from scratch: TTS audio, repeated face frames, FFmpeg mux,
      and caption burn-in. The pipeline is fully testable offline and ready
      to plug in a real lip-sync model as a drop-in replacement for
      image_to_frames. Section 5 continues tomorrow with multimodal agents.
"""

for i, content in enumerate([_LESSON_01, _LESSON_02, _LESSON_03,
                               _LESSON_04, _LESSON_05], start=1):
    (OUT / "lessons" / f"day_{DAY}_lesson_0{i}.yaml").write_text(content)

# ── shared helpers ────────────────────────────────────────────────────────────
_FRAMES_HELPER = """\
from pathlib import Path
import tempfile

def _make_mock_frames(n=5, height=32, width=32):
    import numpy as np
    return [np.zeros((height, width, 3), dtype=np.uint8) for _ in range(n)]
"""

_TTS_MOCK    = "_mock_tts_fn     = lambda text, voice, rate, pitch: b'MP3:' + text[:8].encode()\n"
_CAPTURE_MOCK = "_mock_capture_fn = lambda img, n: _make_mock_frames(n)\n"
_MUX_MOCK    = "_mock_mux_fn     = lambda video_path, audio_bytes, output_path: (Path(output_path).write_bytes(b'MUX' + bytes(len(audio_bytes))), Path(output_path))[1]\n"
_CAPTION_MOCK = "_mock_caption_fn = lambda video_path, text, output_path: (Path(output_path).write_bytes(b'CAP' + bytes(len(text))), Path(output_path))[1]\n"

# ── EX1: generate_speech ──────────────────────────────────────────────────────
_EX1_GIVEN = "from pathlib import Path\n" + _TTS_MOCK

_EX1_STUB = """\
def generate_speech(text: str, voice: str = 'en-US-AriaNeural',
                    rate: str = '+0%', pitch: str = '+0Hz',
                    tts_fn=None) -> bytes:
    \"\"\"Generate speech audio bytes from text.

    Args:
        text:   text to synthesise
        voice:  edge-tts ShortName
        rate:   speaking rate adjustment ('+10%', '-5%', ...)
        pitch:  pitch adjustment ('+5Hz', '-10Hz', ...)
        tts_fn: callable(text, voice, rate, pitch) -> bytes for testing
    \"\"\"
    raise NotImplementedError
"""

_EX1_SOLUTION = """\
def generate_speech(text, voice='en-US-AriaNeural',
                    rate='+0%', pitch='+0Hz', tts_fn=None):
    if tts_fn is not None:
        return tts_fn(text, voice, rate, pitch)
    import asyncio, edge_tts
    async def _run():
        comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        chunks = []
        async for chunk in comm.stream():
            if chunk['type'] == 'audio':
                chunks.append(chunk['data'])
        return b''.join(chunks)
    return asyncio.run(_run())
"""

_EX1_CHECKS = r"""
score, total = 0, 5
try:
    # returns bytes
    audio = generate_speech('Hello!', tts_fn=_mock_tts_fn)
    assert isinstance(audio, bytes)
    score += 1; print("✅ returns bytes")

    # non-empty output
    assert len(audio) > 0
    score += 1; print("✅ output is non-empty")

    # tts_fn receives all 4 args
    captured = {}
    def _cap(text, voice, rate, pitch):
        captured.update(text=text, voice=voice, rate=rate, pitch=pitch)
        return b'OK'
    generate_speech('Hi', voice='en-GB-LibbyNeural', rate='+10%', pitch='+5Hz',
                    tts_fn=_cap)
    assert captured.get('text') == 'Hi'
    assert captured.get('voice') == 'en-GB-LibbyNeural'
    score += 1; print("✅ tts_fn receives text and voice correctly")

    # rate and pitch forwarded
    assert captured.get('rate') == '+10%' and captured.get('pitch') == '+5Hz'
    score += 1; print("✅ rate and pitch forwarded to tts_fn")

    # different texts → different audio
    a1 = generate_speech('A', tts_fn=_mock_tts_fn)
    a2 = generate_speech('BCDEFGHIJ', tts_fn=_mock_tts_fn)
    assert a1 != a2
    score += 1; print("✅ different texts produce different audio bytes")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX1 = nb([
    md("# Day 075 — Exercise 1: generate_speech\n\n"
       "**What you'll build:** `generate_speech(text, voice, rate, pitch, tts_fn=None) -> bytes` — "
       "synthesise speech audio from text using edge-tts.\n\n"
       "**Why it matters:** Stage 1 of the talking-head pipeline — turns the lesson "
       "script into the audio track that drives everything else."),
    code(_EX1_GIVEN),
    md("## Task\n\n"
       "- **Mock:** `if tts_fn is not None: return tts_fn(text, voice, rate, pitch)`\n"
       "- **Real:** `import asyncio, edge_tts`; define `async def _run()` that creates "
       "`edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)`, streams chunks, "
       "collects `chunk['data']` where `chunk['type']=='audio'`, returns `b''.join(chunks)`\n"
       "- Return `asyncio.run(_run())`"),
    md("## Your Implementation"),
    code(_EX1_STUB),
    code(_EX1_SOLUTION),
    md("## Automated checks"),
    code(_EX1_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX1_SOLUTION + "```\n\n"
       "**Why pass all 4 args to tts_fn?** The mock receives `(text, voice, rate, pitch)` "
       "so it can be a drop-in for the real function. A mock that only uses `text` still "
       "accepts the other args — this makes the interface symmetric.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_01.ipynb", EX1)

# ── EX2: image_to_frames ──────────────────────────────────────────────────────
_EX2_GIVEN = _FRAMES_HELPER + _CAPTURE_MOCK

_EX2_STUB = """\
def image_to_frames(image, n_frames: int, capture_fn=None) -> list:
    \"\"\"Create n_frames identical BGR frames from a face image.

    Args:
        image:      PIL Image or path to image file
        n_frames:   number of frames to generate
        capture_fn: callable(image, n_frames) -> list[np.ndarray] for testing
    Returns:
        list of (H, W, 3) uint8 BGR numpy arrays, n_frames elements
    \"\"\"
    raise NotImplementedError
"""

_EX2_SOLUTION = """\
def image_to_frames(image, n_frames, capture_fn=None):
    if capture_fn is not None:
        return capture_fn(image, n_frames)
    import numpy as np
    from PIL import Image as PILImage
    if not isinstance(image, PILImage.Image):
        image = PILImage.open(str(image)).convert('RGB')
    arr = np.array(image)[:, :, ::-1].astype(np.uint8)
    return [arr.copy() for _ in range(n_frames)]
"""

_EX2_CHECKS = r"""
score, total = 0, 5
try:
    # returns a list
    frames = image_to_frames('face.png', 5, capture_fn=_mock_capture_fn)
    assert isinstance(frames, list)
    score += 1; print("✅ returns a list")

    # correct number of frames
    assert len(frames) == 5, f"expected 5 frames, got {len(frames)}"
    score += 1; print("✅ correct frame count (5)")

    # frames are (H, W, 3) uint8 numpy arrays
    assert frames[0].shape == (32, 32, 3)
    assert frames[0].dtype.name == 'uint8'
    score += 1; print("✅ frames are (32, 32, 3) uint8 numpy arrays")

    # capture_fn receives both image and n_frames
    captured = {}
    def _cap(img, n):
        captured['n'] = n
        return _make_mock_frames(n)
    image_to_frames('face.png', 7, capture_fn=_cap)
    assert captured.get('n') == 7
    score += 1; print("✅ capture_fn receives n_frames correctly")

    # different n_frames → different list lengths
    f3 = image_to_frames('face.png', 3, capture_fn=_mock_capture_fn)
    f8 = image_to_frames('face.png', 8, capture_fn=_mock_capture_fn)
    assert len(f3) == 3 and len(f8) == 8
    score += 1; print("✅ n_frames controls output list length")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX2 = nb([
    md("# Day 075 — Exercise 2: image_to_frames\n\n"
       "**What you'll build:** `image_to_frames(image, n_frames, capture_fn=None) -> list` — "
       "convert a face image into a list of identical BGR numpy frame arrays.\n\n"
       "**Why it matters:** Stage 2 of the pipeline — turns a static face photo into the "
       "frame sequence that VideoProcessor writes to a video file."),
    code(_EX2_GIVEN),
    md("## Task\n\n"
       "- **Mock:** `return capture_fn(image, n_frames)`\n"
       "- **Real:** lazy-import `numpy` and `PIL`; if `image` is not a PIL Image, "
       "open and convert to `'RGB'`; `arr = np.array(image)[:, :, ::-1].astype(np.uint8)` "
       "(RGB → BGR); return `[arr.copy() for _ in range(n_frames)]`\n\n"
       "**Key:** `arr.copy()` per frame — each frame must be an independent array."),
    md("## Your Implementation"),
    code(_EX2_STUB),
    code(_EX2_SOLUTION),
    md("## Automated checks"),
    code(_EX2_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX2_SOLUTION + "```\n\n"
       "**Why `[:, :, ::-1]`?** PIL produces RGB; OpenCV/VideoWriter expects BGR. "
       "Reversing the channel axis (axis 2) swaps R and B while keeping G. "
       "It is a zero-copy numpy view — no data is duplicated for the conversion.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_02.ipynb", EX2)

# ── EX3: mux_audio_video ─────────────────────────────────────────────────────
_EX3_GIVEN = (
    "from pathlib import Path\nimport tempfile, subprocess\n"
    + _TTS_MOCK
    + _MUX_MOCK
)

_EX3_STUB = """\
def mux_audio_video(video_path, audio_bytes: bytes,
                    output_path, ffmpeg_fn=None):
    \"\"\"Combine a silent video file with audio bytes into a new MP4.

    Args:
        video_path:  path to silent video file
        audio_bytes: MP3 audio bytes to add as soundtrack
        output_path: destination MP4 path
        ffmpeg_fn:   callable(video_path, audio_bytes, output_path) -> Path
    Returns:
        Path to the output video with audio
    \"\"\"
    raise NotImplementedError
"""

_EX3_SOLUTION = """\
def mux_audio_video(video_path, audio_bytes, output_path, ffmpeg_fn=None):
    if ffmpeg_fn is not None:
        return ffmpeg_fn(video_path, audio_bytes, output_path)
    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
        f.write(audio_bytes)
        audio_path = f.name
    try:
        out_path = Path(output_path)
        result = subprocess.run(
            ['ffmpeg', '-y', '-i', str(video_path), '-i', audio_path,
             '-c:v', 'copy', '-c:a', 'aac', '-shortest', str(out_path)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f'FFmpeg mux error: {result.stderr[-500:]}')
        return out_path
    finally:
        Path(audio_path).unlink(missing_ok=True)
"""

_EX3_CHECKS = r"""
score, total = 0, 5
try:
    audio = _mock_tts_fn('Hello world', 'v', '+0%', '+0Hz')

    # create a placeholder 'silent' video file
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
        silent = f.name
    Path(silent).write_bytes(b'SILENT_VIDEO')

    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
        out1 = f.name

    # returns Path
    result = mux_audio_video(silent, audio, out1, ffmpeg_fn=_mock_mux_fn)
    assert isinstance(result, Path), f"expected Path, got {type(result)}"
    score += 1; print("✅ returns Path")

    # file exists and non-empty
    assert result.exists() and result.stat().st_size > 0
    score += 1; print("✅ output file exists with non-zero size")

    # ffmpeg_fn receives correct arguments
    captured = {}
    def _cap_fn(vp, ab, op):
        captured.update(vp=str(vp), n_audio=len(ab))
        return Path(op)
    mux_audio_video(silent, audio, out1, ffmpeg_fn=_cap_fn)
    assert captured.get('vp') == str(silent)
    score += 1; print("✅ ffmpeg_fn receives video_path and audio_bytes")

    # audio bytes are forwarded (mock encodes length in output size)
    audio_short = _mock_tts_fn('Hi', 'v', '+0%', '+0Hz')
    audio_long  = _mock_tts_fn('Hello world!!', 'v', '+0%', '+0Hz')
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
        out2 = f.name
    r1 = mux_audio_video(silent, audio_short, out1, ffmpeg_fn=_mock_mux_fn)
    r2 = mux_audio_video(silent, audio_long,  out2, ffmpeg_fn=_mock_mux_fn)
    assert r1.stat().st_size != r2.stat().st_size
    score += 1; print("✅ audio_bytes incorporated (different sizes)")

    # output_path is respected
    assert str(result) == out1
    score += 1; print("✅ returned Path matches output_path")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX3 = nb([
    md("# Day 075 — Exercise 3: mux_audio_video\n\n"
       "**What you'll build:** `mux_audio_video(video_path, audio_bytes, output_path, ffmpeg_fn=None) -> Path` — "
       "combine a silent video file with audio bytes into a playable MP4.\n\n"
       "**Why it matters:** Stage 3 of the pipeline — this is what gives the talking-head "
       "its voice. FFmpeg's two-input mux combines the frame sequence with the TTS track."),
    code(_EX3_GIVEN),
    md("## Task\n\n"
       "- **Mock:** `return ffmpeg_fn(video_path, audio_bytes, output_path)`\n"
       "- **Real:** write `audio_bytes` to a `NamedTemporaryFile(.mp3)`; in `try/finally` "
       "run `subprocess.run(['ffmpeg','-y','-i',str(video_path),'-i',audio_path,"
       "'-c:v','copy','-c:a','aac','-shortest',str(out_path)], capture_output=True, text=True)`; "
       "raise `RuntimeError` if `returncode != 0`; `finally: Path(audio_path).unlink(missing_ok=True)`\n"
       "- Return `Path(output_path)`"),
    md("## Your Implementation"),
    code(_EX3_STUB),
    code(_EX3_SOLUTION),
    md("## Automated checks"),
    code(_EX3_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX3_SOLUTION + "```\n\n"
       "**Why `finally` for cleanup?** If FFmpeg raises or returns non-zero, "
       "the temp audio file must still be deleted. `finally` runs regardless "
       "of whether the `try` block succeeded or raised.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_03.ipynb", EX3)

# ── EX4: add_captions ─────────────────────────────────────────────────────────
_EX4_GIVEN = (
    "from pathlib import Path\nimport tempfile, subprocess\n"
    + _CAPTION_MOCK
)

_EX4_STUB = """\
def add_captions(video_path, text: str, output_path,
                 fontsize: int = 24, color: str = 'white',
                 ffmpeg_fn=None):
    \"\"\"Burn a caption onto a video using FFmpeg drawtext filter.

    Args:
        video_path:  source video
        text:        caption text (single line)
        output_path: destination path
        fontsize:    font size in pixels
        color:       text colour name ('white', 'yellow', 'black', ...)
        ffmpeg_fn:   callable(video_path, text, output_path) -> Path
    Returns:
        Path to captioned video
    \"\"\"
    raise NotImplementedError
"""

_EX4_SOLUTION = """\
def add_captions(video_path, text, output_path,
                 fontsize=24, color='white', ffmpeg_fn=None):
    if ffmpeg_fn is not None:
        return ffmpeg_fn(video_path, text, output_path)
    safe_text = text.replace("'", r"\\'").replace(':', r'\\:')
    out_path = Path(output_path)
    result = subprocess.run(
        ['ffmpeg', '-y', '-i', str(video_path),
         '-vf', (f"drawtext=text='{safe_text}':fontsize={fontsize}:"
                 f"fontcolor={color}:x=(w-text_w)/2:y=h-text_h-20"),
         str(out_path)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f'FFmpeg caption error: {result.stderr[-500:]}')
    return out_path
"""

_EX4_CHECKS = r"""
score, total = 0, 5
try:
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
        src = f.name
    Path(src).write_bytes(b'VIDEO')

    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
        out1 = f.name
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
        out2 = f.name

    # returns Path
    result = add_captions(src, 'Hello Day 75', out1, ffmpeg_fn=_mock_caption_fn)
    assert isinstance(result, Path)
    score += 1; print("✅ returns Path")

    # file exists and non-empty
    assert result.exists() and result.stat().st_size > 0
    score += 1; print("✅ output file exists with non-zero size")

    # ffmpeg_fn receives (video_path, text, output_path)
    captured = {}
    def _cap(vp, t, op):
        captured.update(text=t, op=op)
        return Path(op)
    add_captions(src, 'Day 75', out1, ffmpeg_fn=_cap)
    assert captured.get('text') == 'Day 75'
    score += 1; print("✅ text forwarded to ffmpeg_fn correctly")

    # output_path is respected
    assert str(result) == out1
    score += 1; print("✅ returned Path matches output_path")

    # different text lengths → different output sizes (text encoded in mock)
    r1 = add_captions(src, 'Hi', out1, ffmpeg_fn=_mock_caption_fn)
    r2 = add_captions(src, 'Hello World Pipeline', out2, ffmpeg_fn=_mock_caption_fn)
    assert r1.stat().st_size != r2.stat().st_size
    score += 1; print("✅ text incorporated (different lengths → different sizes)")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX4 = nb([
    md("# Day 075 — Exercise 4: add_captions\n\n"
       "**What you'll build:** `add_captions(video_path, text, output_path, fontsize, color, ffmpeg_fn=None) -> Path` — "
       "burn caption text onto a video using FFmpeg's `drawtext` filter.\n\n"
       "**Why it matters:** Stage 4 of the pipeline — captions make the video accessible "
       "and allow the lesson text to be read even without audio."),
    code(_EX4_GIVEN),
    md("## Task\n\n"
       "- **Mock:** `return ffmpeg_fn(video_path, text, output_path)`\n"
       "- **Real:** escape `text` (`'` → `\\'`, `:` → `\\:`); run "
       "`ffmpeg -y -i video_path -vf "
       "drawtext=text='{safe_text}':fontsize={fontsize}:fontcolor={color}:"
       "x=(w-text_w)/2:y=h-text_h-20 output_path`\n"
       "- Raise `RuntimeError` if `returncode != 0`; return `Path(output_path)`"),
    md("## Your Implementation"),
    code(_EX4_STUB),
    code(_EX4_SOLUTION),
    md("## Automated checks"),
    code(_EX4_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX4_SOLUTION + "```\n\n"
       "**drawtext positioning:** `x=(w-text_w)/2` centres horizontally "
       "(video width minus text width, halved). `y=h-text_h-20` places the "
       "text 20 pixels above the bottom edge. These expressions are evaluated "
       "at render time by FFmpeg against the actual frame dimensions.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_04.ipynb", EX4)

# ── EX5: TalkingHeadPipeline ──────────────────────────────────────────────────
_EX5_GIVEN = (
    _FRAMES_HELPER
    + _TTS_MOCK
    + _CAPTURE_MOCK
    + _MUX_MOCK
    + _CAPTION_MOCK
    + """\

def generate_speech(text, voice='en-US-AriaNeural', rate='+0%', pitch='+0Hz', tts_fn=None):
    if tts_fn is not None:
        return tts_fn(text, voice, rate, pitch)
    import asyncio, edge_tts
    async def _run():
        comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        chunks = []
        async for chunk in comm.stream():
            if chunk['type'] == 'audio': chunks.append(chunk['data'])
        return b''.join(chunks)
    return asyncio.run(_run())

def image_to_frames(image, n_frames, capture_fn=None):
    if capture_fn is not None:
        return capture_fn(image, n_frames)
    import numpy as np
    from PIL import Image as PILImage
    if not isinstance(image, PILImage.Image):
        image = PILImage.open(str(image)).convert('RGB')
    arr = np.array(image)[:, :, ::-1].astype(np.uint8)
    return [arr.copy() for _ in range(n_frames)]

def mux_audio_video(video_path, audio_bytes, output_path, ffmpeg_fn=None):
    if ffmpeg_fn is not None:
        return ffmpeg_fn(video_path, audio_bytes, output_path)
    import subprocess, tempfile
    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
        f.write(audio_bytes); audio_path = f.name
    try:
        out = Path(output_path)
        r = subprocess.run(['ffmpeg','-y','-i',str(video_path),'-i',audio_path,
                            '-c:v','copy','-c:a','aac','-shortest',str(out)],
                           capture_output=True, text=True)
        if r.returncode != 0: raise RuntimeError(r.stderr[-500:])
        return out
    finally:
        Path(audio_path).unlink(missing_ok=True)

def add_captions(video_path, text, output_path,
                 fontsize=24, color='white', ffmpeg_fn=None):
    if ffmpeg_fn is not None:
        return ffmpeg_fn(video_path, text, output_path)
    import subprocess
    safe = text.replace("'", r"\\'").replace(':', r'\\:')
    out = Path(output_path)
    r = subprocess.run(
        ['ffmpeg','-y','-i',str(video_path),'-vf',
         f"drawtext=text='{safe}':fontsize={fontsize}:"
         f"fontcolor={color}:x=(w-text_w)/2:y=h-text_h-20", str(out)],
        capture_output=True, text=True)
    if r.returncode != 0: raise RuntimeError(r.stderr[-500:])
    return out
"""
)

_EX5_STUB = """\
class TalkingHeadPipeline:
    \"\"\"Create talking-head videos from text and a face image.\"\"\"

    def __init__(self, tts_fn=None, capture_fn=None,
                 mux_fn=None, caption_fn=None) -> None:
        raise NotImplementedError

    def speech(self, text: str, voice: str = 'en-US-AriaNeural',
               rate: str = '+0%', pitch: str = '+0Hz') -> bytes:
        raise NotImplementedError

    def frames(self, image, n_frames: int) -> list:
        raise NotImplementedError

    def mux(self, video_path, audio_bytes: bytes, output_path):
        raise NotImplementedError

    def caption(self, video_path, text: str, output_path,
                fontsize: int = 24, color: str = 'white'):
        raise NotImplementedError
"""

_EX5_SOLUTION = """\
class TalkingHeadPipeline:
    def __init__(self, tts_fn=None, capture_fn=None,
                 mux_fn=None, caption_fn=None):
        self._tts_fn     = tts_fn
        self._capture_fn = capture_fn
        self._mux_fn     = mux_fn
        self._caption_fn = caption_fn

    def speech(self, text, voice='en-US-AriaNeural',
               rate='+0%', pitch='+0Hz'):
        return generate_speech(text, voice=voice, rate=rate, pitch=pitch,
                               tts_fn=self._tts_fn)

    def frames(self, image, n_frames):
        return image_to_frames(image, n_frames, capture_fn=self._capture_fn)

    def mux(self, video_path, audio_bytes, output_path):
        return mux_audio_video(video_path, audio_bytes, output_path,
                               ffmpeg_fn=self._mux_fn)

    def caption(self, video_path, text, output_path,
                fontsize=24, color='white'):
        return add_captions(video_path, text, output_path,
                            fontsize=fontsize, color=color,
                            ffmpeg_fn=self._caption_fn)
"""

_EX5_CHECKS = r"""
import tempfile
score, total = 0, 5
try:
    pipe = TalkingHeadPipeline(
        tts_fn=_mock_tts_fn,
        capture_fn=_mock_capture_fn,
        mux_fn=_mock_mux_fn,
        caption_fn=_mock_caption_fn,
    )

    # speech() delegates to generate_speech
    audio = pipe.speech('Day 75 is here!')
    assert isinstance(audio, bytes) and len(audio) > 0
    score += 1; print("✅ speech() returns non-empty bytes")

    # frames() delegates to image_to_frames
    frames = pipe.frames('face.png', 8)
    assert isinstance(frames, list) and len(frames) == 8
    assert frames[0].shape == (32, 32, 3)
    score += 1; print("✅ frames() returns correct list of numpy arrays")

    # mux() delegates to mux_audio_video
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
        silent = f.name
    Path(silent).write_bytes(b'SILENT')
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
        muxed = f.name
    m = pipe.mux(silent, audio, muxed)
    assert isinstance(m, Path) and m.exists()
    score += 1; print("✅ mux() returns existing Path")

    # caption() delegates to add_captions
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
        captioned = f.name
    c = pipe.caption(m, 'Day 75 complete!', captioned)
    assert isinstance(c, Path) and c.exists()
    score += 1; print("✅ caption() returns existing Path")

    # injection fns are bound at construction
    called = {}
    def _spy_tts(text, voice, rate, pitch):
        called['tts'] = True
        return b'MP3:spy'
    pipe2 = TalkingHeadPipeline(tts_fn=_spy_tts)
    pipe2.speech('test')
    assert called.get('tts') is True
    score += 1; print("✅ injection fn bound at construction, invoked on call")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX5 = nb([
    md("# Day 075 — Exercise 5: TalkingHeadPipeline\n\n"
       "**What you'll build:** `TalkingHeadPipeline` — full pipeline class binding "
       "all four injection functions at construction.\n\n"
       "**Why it matters:** The class is the ergonomic interface for the full pipeline: "
       "`pipe.speech(text)`, `pipe.frames(img, n)`, `pipe.mux(...)`, `pipe.caption(...)` "
       "reads more clearly than passing mock functions on every call."),
    code(_EX5_GIVEN),
    md("## Task\n\n"
       "Implement `TalkingHeadPipeline`:\n\n"
       "- `__init__`: store `tts_fn`, `capture_fn`, `mux_fn`, `caption_fn` as "
       "`self._xxx_fn`\n"
       "- `speech(text, voice, rate, pitch)`: `return generate_speech(..., tts_fn=self._tts_fn)`\n"
       "- `frames(image, n_frames)`: `return image_to_frames(..., capture_fn=self._capture_fn)`\n"
       "- `mux(video_path, audio_bytes, output_path)`: "
       "`return mux_audio_video(..., ffmpeg_fn=self._mux_fn)`\n"
       "- `caption(video_path, text, output_path, fontsize, color)`: "
       "`return add_captions(..., ffmpeg_fn=self._caption_fn)`"),
    md("## Your Implementation"),
    code(_EX5_STUB),
    code(_EX5_SOLUTION),
    md("## Automated checks"),
    code(_EX5_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX5_SOLUTION + "```\n\n"
       "**Why four methods, each one line?** All logic is in the module-level functions. "
       "The class is a binding layer, not a logic layer. A one-line method that calls a "
       "module function with a bound injection is the correct level of delegation — "
       "not a pass-through, not a reimplementation.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_05.ipynb", EX5)

# ── PROJECT NOTEBOOK ──────────────────────────────────────────────────────────
PROJECT = nb([
    md("# Day 075 — Project: Talking-Head Pipeline\n\n"
       "## What You're Building\n\n"
       "`talking_head.py` — a four-stage pipeline for talking-head video creation.\n\n"
       "## Setup\n\n"
       "```bash\n"
       "pip install edge-tts opencv-python-headless Pillow\n"
       "brew install ffmpeg   # macOS\n"
       "```\n\n"
       "## Design\n\n"
       "```\n"
       "generate_speech(text, voice, rate, pitch, tts_fn=None) -> bytes\n"
       "image_to_frames(image, n_frames, capture_fn=None) -> list[ndarray]\n"
       "mux_audio_video(video_path, audio_bytes, output_path, ffmpeg_fn=None) -> Path\n"
       "add_captions(video_path, text, output_path, fontsize, color, ffmpeg_fn=None) -> Path\n"
       "TalkingHeadPipeline(tts_fn, capture_fn, mux_fn, caption_fn)\n"
       "  .speech(text, voice, rate, pitch) -> bytes\n"
       "  .frames(image, n_frames) -> list\n"
       "  .mux(video_path, audio_bytes, output_path) -> Path\n"
       "  .caption(video_path, text, output_path, fontsize, color) -> Path\n"
       "```"),
    code("# Your implementation here — build TalkingHeadPipeline and write talking_head.py\n"),
])
save(OUT / "project" / "project.ipynb", PROJECT)

# ── SOLUTION NOTEBOOK ─────────────────────────────────────────────────────────
_SOL_CELL1 = (
    f"_SRC = {repr(_TALKING_HEAD_SRC)}\n"
    "from pathlib import Path\n"
    "Path('talking_head.py').write_text(_SRC, encoding='utf-8')\n"
    "print('talking_head.py written.')"
)

_SOL_CELL2 = """\
import tempfile
from pathlib import Path
from talking_head import (
    generate_speech, image_to_frames, mux_audio_video,
    add_captions, TalkingHeadPipeline,
)

def _make_mock_frames(n=5, height=32, width=32):
    import numpy as np
    return [np.zeros((height, width, 3), dtype=np.uint8) for _ in range(n)]

_mock_tts     = lambda text, voice, rate, pitch: b'MP3:' + text[:8].encode()
_mock_capture = lambda img, n: _make_mock_frames(n)
_mock_mux     = lambda vp, ab, op: (Path(op).write_bytes(b'MUX' + bytes(len(ab))), Path(op))[1]
_mock_caption = lambda vp, t, op: (Path(op).write_bytes(b'CAP' + bytes(len(t))), Path(op))[1]

# 1. generate_speech
audio = generate_speech('Hello Day 75!', tts_fn=_mock_tts)
assert isinstance(audio, bytes) and len(audio) > 0
print("\\u2705 generate_speech correct")

# 2. image_to_frames
frames = image_to_frames('face.png', 5, capture_fn=_mock_capture)
assert len(frames) == 5 and frames[0].shape == (32, 32, 3)
print("\\u2705 image_to_frames correct")

# 3. mux_audio_video
with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f: silent = f.name
Path(silent).write_bytes(b'SILENT')
with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f: muxed = f.name
m = mux_audio_video(silent, audio, muxed, ffmpeg_fn=_mock_mux)
assert isinstance(m, Path) and m.exists() and m.stat().st_size > 0
print("\\u2705 mux_audio_video correct")

# 4. add_captions
with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f: captioned = f.name
c = add_captions(silent, 'Day 75', captioned, ffmpeg_fn=_mock_caption)
assert isinstance(c, Path) and c.exists()
print("\\u2705 add_captions correct")

# 5. TalkingHeadPipeline
pipe = TalkingHeadPipeline(tts_fn=_mock_tts, capture_fn=_mock_capture,
                           mux_fn=_mock_mux, caption_fn=_mock_caption)
a = pipe.speech('Section 5 pipeline complete!')
f2 = pipe.frames('face.png', 10)
with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f: s2 = f.name
Path(s2).write_bytes(b'SILENT')
with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f: m2 = f.name
with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f: c2 = f.name
mx = pipe.mux(s2, a, m2)
cp = pipe.caption(mx, 'Day 75 done!', c2)
assert isinstance(a, bytes) and len(f2) == 10
assert isinstance(mx, Path) and mx.exists()
assert isinstance(cp, Path) and cp.exists()
print("\\u2705 TalkingHeadPipeline correct")
print("\\nTalking-Head Pipeline complete!")
"""

SOLUTION = nb([
    md("# Day 075 — Solution: Talking-Head Pipeline"),
    code(_SOL_CELL1),
    code(_SOL_CELL2),
])
save(OUT / "project" / "solution" / "solution.ipynb", SOLUTION)
(OUT / "project" / "solution" / "talking_head.py").write_text(_TALKING_HEAD_SRC)

print(f"Day {DAY} notebooks written to {OUT}")
print("  lessons/    day_075_lesson_01.yaml – lesson_05.yaml")
print("  exercises/  exercise_01 – exercise_05")
print("  project/    project.ipynb")
print("  project/solution/  solution.ipynb + talking_head.py")
