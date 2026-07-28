#!/usr/bin/env python3
"""gen_day078.py — generate Day 078: Capstone — Media Studio."""
from pathlib import Path
import json

ROOT    = Path(__file__).parent.parent
DAY     = "078"
SECTION = "05_vision_multimodal"
OUT     = ROOT / SECTION / f"day_{DAY}"

(OUT / "exercises").mkdir(parents=True, exist_ok=True)
(OUT / "lessons").mkdir(parents=True, exist_ok=True)
(OUT / "project" / "solution").mkdir(parents=True, exist_ok=True)

# ── deliverable: media_studio.py ──────────────────────────────────────────────
_MEDIA_STUDIO_SRC = '''\
"""media_studio.py — Day 078: Capstone — Multimodal Media Studio.

Combines Section 5 skills into a unified media processing interface:
  detect_media_type  — identify file type from extension
  describe_media     — image -> text description (llava via Ollama)
  transcribe_media   — audio -> text transcript (Whisper)
  synthesize_speech  — text -> audio MP3 bytes (edge-tts)
  narrate_image      — image -> description -> audio
  process_media      — auto-detect type and dispatch
  MediaStudio        — stateful class with all capabilities + batch

Setup:
    pip install pillow ollama openai-whisper edge-tts
    ollama pull llava
"""
import io
import base64
import asyncio
from pathlib import Path

MEDIA_EXTENSIONS = {
    'image': {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tiff'},
    'audio': {'.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac'},
    'video': {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv'},
}


def detect_media_type(path):
    """Return media type string from file extension.

    Args:
        path: file path (str or Path)
    Returns:
        'image', 'audio', 'video', or 'unknown'
    """
    ext = Path(path).suffix.lower()
    for media_type, extensions in MEDIA_EXTENSIONS.items():
        if ext in extensions:
            return media_type
    return 'unknown'


def describe_media(source, describe_fn=None):
    """Describe an image using a vision LLM.

    Args:
        source:     PIL Image or file path (str/Path)
        describe_fn: callable(pil_image, prompt) -> str for testing
    Returns:
        description string
    """
    from PIL import Image
    if isinstance(source, (str, Path)):
        image = Image.open(source) if describe_fn is None else source
    else:
        image = source
    prompt = 'Describe this image in detail, including all visible content.'
    if describe_fn is not None:
        return describe_fn(image, prompt)
    import ollama
    buf = io.BytesIO()
    image.save(buf, format='PNG')
    img_b64 = base64.b64encode(buf.getvalue()).decode()
    resp = ollama.chat(
        model='llava',
        messages=[{'role': 'user', 'content': prompt, 'images': [img_b64]}],
    )
    return resp['message']['content']


def transcribe_media(source, transcribe_fn=None):
    """Transcribe audio to text using Whisper.

    Args:
        source:        audio bytes or file path (str/Path)
        transcribe_fn: callable(source) -> dict for testing
    Returns:
        dict with keys: text (str), segments (list of {start, end, text})
    """
    if transcribe_fn is not None:
        return transcribe_fn(source)
    import whisper, os, tempfile
    model = whisper.load_model('base')
    if isinstance(source, bytes):
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            f.write(source)
            tmp = f.name
        try:
            raw = model.transcribe(tmp)
        finally:
            os.unlink(tmp)
    else:
        raw = model.transcribe(str(source))
    segments = [
        {'start': s['start'], 'end': s['end'], 'text': s['text'].strip()}
        for s in raw.get('segments', [])
    ]
    return {'text': raw.get('text', '').strip(), 'segments': segments}


def synthesize_speech(text, voice='en-US-AriaNeural', rate='+0%', pitch='+0Hz',
                      tts_fn=None):
    """Convert text to speech and return MP3 bytes.

    Args:
        text:   text to synthesize
        voice:  edge-tts voice ShortName (e.g. 'en-US-AriaNeural')
        rate:   speed adjustment ('+0%', '+20%', '-20%')
        pitch:  pitch adjustment ('+0Hz', '+5Hz', '-5Hz')
        tts_fn: callable(text, voice, rate, pitch) -> bytes for testing
    Returns:
        MP3 bytes
    """
    if tts_fn is not None:
        return tts_fn(text, voice, rate, pitch)
    import edge_tts
    async def _run():
        chunks = []
        async for chunk in edge_tts.Communicate(
                text, voice, rate=rate, pitch=pitch).stream():
            if chunk['type'] == 'audio':
                chunks.append(chunk['data'])
        return b''.join(chunks)
    return asyncio.run(_run())


def narrate_image(source, voice='en-US-AriaNeural', describe_fn=None, tts_fn=None):
    """Describe an image then convert the description to speech.

    Args:
        source:     PIL Image or file path
        voice:      edge-tts voice ShortName
        describe_fn: callable(pil_image, prompt) -> str for testing
        tts_fn:      callable(text, voice, rate, pitch) -> bytes for testing
    Returns:
        dict with keys: description (str), audio (bytes)
    """
    description = describe_media(source, describe_fn=describe_fn)
    audio = synthesize_speech(description, voice=voice, tts_fn=tts_fn)
    return {'description': description, 'audio': audio}


def process_media(source, describe_fn=None, transcribe_fn=None, tts_fn=None):
    """Auto-detect media type and process the file.

    - image  -> describe_media -> str description
    - audio  -> transcribe_media -> {text, segments}
    - other  -> {note: '...'}

    Returns:
        dict with keys: type (str), source (str), result
    """
    media_type = detect_media_type(source)
    if media_type == 'image':
        result = describe_media(source, describe_fn=describe_fn)
    elif media_type == 'audio':
        result = transcribe_media(source, transcribe_fn=transcribe_fn)
    else:
        result = {'note': f'Media type {media_type!r} detected but not processed'}
    return {'type': media_type, 'source': str(source), 'result': result}


class MediaStudio:
    """Multimodal media processing studio.

    Combines image description, audio transcription, and text-to-speech
    synthesis into a single injectable interface.

    Example::

        studio = MediaStudio(
            describe_fn=lambda img, q: 'Mock description',
            transcribe_fn=lambda src: {'text': 'Mock transcript', 'segments': []},
            tts_fn=lambda text, v, r, p: b'AUDIO',
        )
        desc    = studio.describe(image)
        text    = studio.transcribe(audio_bytes)['text']
        audio   = studio.speak('Hello world')
        result  = studio.narrate(image)
        results = studio.batch(['image.png', 'audio.wav'])
    """

    def __init__(self, describe_fn=None, transcribe_fn=None, tts_fn=None):
        self._describe_fn = describe_fn
        self._transcribe_fn = transcribe_fn
        self._tts_fn = tts_fn

    def describe(self, source):
        """Describe an image (PIL Image or path)."""
        return describe_media(source, describe_fn=self._describe_fn)

    def transcribe(self, source):
        """Transcribe audio (bytes or path). Returns {text, segments}."""
        return transcribe_media(source, transcribe_fn=self._transcribe_fn)

    def speak(self, text, voice='en-US-AriaNeural', rate='+0%', pitch='+0Hz'):
        """Convert text to speech. Returns MP3 bytes."""
        return synthesize_speech(text, voice=voice, rate=rate, pitch=pitch,
                                 tts_fn=self._tts_fn)

    def narrate(self, source, voice='en-US-AriaNeural'):
        """Describe an image and speak the description."""
        return narrate_image(source, voice=voice,
                             describe_fn=self._describe_fn, tts_fn=self._tts_fn)

    def process(self, source):
        """Auto-detect media type and process the file."""
        return process_media(source, describe_fn=self._describe_fn,
                             transcribe_fn=self._transcribe_fn, tts_fn=self._tts_fn)

    def batch(self, sources):
        """Process a list of media sources. Returns list of result dicts."""
        return [self.process(s) for s in sources]
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
day: "078"
lesson: 1
title: "Media Studio — Capstone Architecture"
slides:
  - type: title
    heading: "Media Studio"
    subheading: "Section 5 Capstone — one studio for every modality"
    narration: >
      Days 66 through 77 built thirteen individual tools: image processing,
      vision LLM, OCR, structured extraction, image generation, visual search,
      speech-to-text, text-to-speech, video processing, talking-head pipeline,
      screenshot agents, and real-time camera vision. Day 78 assembles three
      of the most composable into a Media Studio that can describe images,
      transcribe audio, synthesize speech, and chain them into cross-modal
      pipelines like image narration.

  - type: concept
    label: "Three pipelines"
    heading: "Three Core Pipelines"
    body: >
      MediaStudio combines three direction-orthogonal pipelines.
    bullets:
      - "Vision: image -> text (describe_media using llava)"
      - "Speech-to-Text: audio -> text (transcribe_media using Whisper)"
      - "Text-to-Speech: text -> audio (synthesize_speech using edge-tts)"
      - "Cross-modal: image -> describe -> speak = narrate_image"
      - "All three introduced in Days 67/72/73 — MediaStudio composes them"
    narration: >
      The three pipelines are direction-orthogonal. Vision goes image-to-text.
      Speech recognition goes audio-to-text. TTS goes text-to-audio. Each
      direction is reversible across different modalities. Chaining vision
      and TTS produces image narration — a talking description of any image.
      The MediaStudio class is the composition layer.

  - type: concept
    label: "Three injections"
    heading: "Three Injection Points"
    body: >
      MediaStudio has one injection per pipeline, keeping mock setup minimal.
    bullets:
      - "describe_fn(pil_image, prompt) -> str: replaces llava (Day 67 pattern)"
      - "transcribe_fn(source) -> dict: replaces Whisper (Day 72 pattern)"
      - "tts_fn(text, voice, rate, pitch) -> bytes: replaces edge-tts (Day 73 pattern)"
      - "All three None: production mode (real models)"
      - "All three mocked: gate runs offline with no models"
    narration: >
      Each injection follows the exact pattern established in its original day.
      describe_fn matches the Day 76/77 analyze_fn signature: PIL Image plus
      prompt string. transcribe_fn matches Day 72's transcribe_fn: receives
      source (bytes or path), returns the same dict structure. tts_fn matches
      Day 73's tts_fn: four positional args (text, voice, rate, pitch).

  - type: concept
    label: "Media type detection"
    heading: "MEDIA_EXTENSIONS and detect_media_type"
    body: >
      A module-level dict maps type names to sets of extensions.
    bullets:
      - "MEDIA_EXTENSIONS: {'image': {'.jpg','.png',...}, 'audio': {...}, 'video': {...}}"
      - "detect_media_type(path): Path(path).suffix.lower() -> look up in dict"
      - "Loop over dict items; return key when ext is in value set"
      - "Return 'unknown' if no match"
      - "Case-insensitive: .PNG and .png both return 'image'"
      - "Only extension checked — no file magic bytes (no file needs to exist)"
    narration: >
      detect_media_type uses only the file extension — the file does not need
      to exist. This means process_media can dispatch correctly even before
      opening the file, and tests can use fictitious paths like 'test.mp3'
      without creating real audio files. The module-level dict is the single
      source of truth for supported extensions.

  - type: exercise
    heading: "Exercise 1: MEDIA_EXTENSIONS and detect_media_type"
    prompt: >
      Define MEDIA_EXTENSIONS = {'image': {'.jpg','.jpeg','.png','.bmp','.gif',
      '.webp','.tiff'}, 'audio': {'.mp3','.wav','.ogg','.flac','.m4a','.aac'},
      'video': {'.mp4','.avi','.mov','.mkv','.webm','.flv'}}.
      Implement detect_media_type(path) -> str: ext = Path(path).suffix.lower();
      loop over MEDIA_EXTENSIONS.items(); return media_type if ext in extensions;
      return 'unknown'.
    hint: >
      from pathlib import Path. ext = Path(path).suffix.lower().
      for media_type, extensions in MEDIA_EXTENSIONS.items():
          if ext in extensions: return media_type.
      return 'unknown'.
    narration: >
      detect_media_type is the routing function for the whole studio. Getting
      it right means process_media dispatches correctly to the right pipeline.

  - type: summary
    heading: "Lesson 1 Summary"
    bullets:
      - "MediaStudio: 3 pipelines (vision/STT/TTS) + cross-modal composition"
      - "3 injections: describe_fn, transcribe_fn, tts_fn — all 4-positional from Day 73"
      - "MEDIA_EXTENSIONS: module-level dict, type name -> extension set"
      - "detect_media_type: suffix.lower() + dict loop -> 'image'/'audio'/'video'/'unknown'"
      - "Extension-only check: file does not need to exist"
    narration: >
      Lesson 2 implements describe_media — image description with a vision LLM.
"""

_LESSON_02 = """\
day: "078"
lesson: 2
title: "describe_media — Image to Text"
slides:
  - type: title
    heading: "describe_media"
    subheading: "PIL Image or file path -> vision LLM description"
    narration: >
      describe_media is the vision pipeline of the Media Studio. It accepts
      either a PIL Image object or a file path, converts to base64, and calls
      llava via Ollama. The describe_fn injection follows the same pattern
      as analyze_fn from Days 76 and 77.

  - type: code
    label: "describe_media"
    heading: "describe_media Implementation"
    code: |
      import io, base64
      from pathlib import Path

      def describe_media(source, describe_fn=None):
          from PIL import Image
          if isinstance(source, (str, Path)):
              image = Image.open(source) if describe_fn is None else source
          else:
              image = source           # PIL Image passed directly
          prompt = 'Describe this image in detail, including all visible content.'
          if describe_fn is not None:
              return describe_fn(image, prompt)
          import ollama
          buf = io.BytesIO()
          image.save(buf, format='PNG')
          img_b64 = base64.b64encode(buf.getvalue()).decode()
          resp = ollama.chat(
              model='llava',
              messages=[{'role': 'user', 'content': prompt, 'images': [img_b64]}],
          )
          return resp['message']['content']
    narration: >
      describe_media handles both input forms: a PIL Image object from memory
      (for programmatic pipelines) or a file path string (for processing files
      on disk). The isinstance check dispatches correctly. Image.open is lazy
      — it loads on demand when image.save() is called. The describe_fn
      receives the PIL Image rather than the base64 string, making mocks
      simpler and more flexible.

  - type: concept
    label: "Dual input"
    heading: "Dual Input: PIL Image and File Path"
    body: >
      Accepting both forms makes describe_media usable in all contexts.
    bullets:
      - "PIL Image: received from camera (Day 77), screenshot (Day 76), generation (Day 70)"
      - "File path: received from disk, uploaded file, output of save_frame"
      - "isinstance(source, (str, Path)): check for either string or Path object"
      - "Image.open is lazy: file is read on first pixel access or .save()"
      - "describe_fn(pil_image, prompt): always receives PIL Image regardless of input form"
      - "Same describe_fn(pil_image, question) signature as analyze_fn in Day 76/77"
    narration: >
      The dual input form is a common pattern when a function needs to work
      in both interactive (PIL Image in memory) and batch (file path from disk)
      contexts. Always normalising to PIL Image before calling the injection
      means the mock is always a simple lambda that receives PIL Image, never
      needing to handle file I/O.

  - type: exercise
    heading: "Exercise 2: describe_media"
    prompt: >
      Implement describe_media(source, describe_fn=None) -> str.
      from PIL import Image. If isinstance(source, (str, Path)): image =
      Image.open(source); else: image = source.
      prompt = 'Describe this image in detail, including all visible content.'
      If describe_fn is not None: return describe_fn(image, prompt).
      Else: BytesIO + image.save PNG + base64.b64encode + ollama.chat model='llava'
      + return resp['message']['content'].
    hint: >
      from PIL import Image; isinstance check on (str, Path); Image.open for paths.
      prompt = 'Describe this image in detail, including all visible content.'
      if describe_fn: return describe_fn(image, prompt).
      else: io.BytesIO + save + b64encode + ollama.chat llava.
    narration: >
      describe_media is three logical blocks: input normalisation, mock path,
      real path. Follow the same base64+Ollama pattern used in Days 67, 76, 77.

  - type: summary
    heading: "Lesson 2 Summary"
    bullets:
      - "isinstance(source, (str, Path)): route file path vs PIL Image"
      - "Image.open(source): lazy load — decoded on first pixel access"
      - "describe_fn(pil_image, prompt): always receives PIL Image"
      - "Real path: BytesIO PNG -> base64 -> ollama.chat llava"
      - "Fixed prompt: 'Describe this image in detail, including all visible content.'"
    narration: >
      Lesson 3 adds transcribe_media — the audio-to-text pipeline using Whisper.
"""

_LESSON_03 = """\
day: "078"
lesson: 3
title: "transcribe_media — Audio to Text"
slides:
  - type: title
    heading: "transcribe_media"
    subheading: "Audio bytes or file path -> Whisper transcript"
    narration: >
      transcribe_media brings the Day 72 Whisper integration into the Media
      Studio. Like describe_media, it handles two input forms: raw audio bytes
      (for programmatic pipelines) and file paths (for files on disk). The
      transcribe_fn injection replaces the entire Whisper call for testing.

  - type: code
    label: "transcribe_media"
    heading: "transcribe_media Implementation"
    code: |
      def transcribe_media(source, transcribe_fn=None):
          if transcribe_fn is not None:
              return transcribe_fn(source)
          import whisper, os, tempfile
          model = whisper.load_model('base')
          if isinstance(source, bytes):
              with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                  f.write(source)
                  tmp = f.name
              try:
                  raw = model.transcribe(tmp)
              finally:
                  os.unlink(tmp)
          else:
              raw = model.transcribe(str(source))
          segments = [
              {'start': s['start'], 'end': s['end'], 'text': s['text'].strip()}
              for s in raw.get('segments', [])
          ]
          return {'text': raw.get('text', '').strip(), 'segments': segments}
    narration: >
      transcribe_fn receives source directly — mock functions can accept either
      bytes or path without caring which. The real path uses the same
      NamedTemporaryFile pattern from Day 72: write bytes to temp WAV, transcribe,
      unlink in finally. The result normalises the Whisper output to a consistent
      dict: text (stripped string) and segments (list of start/end/text dicts).

  - type: concept
    label: "Result normalisation"
    heading: "Normalising Whisper Output"
    body: >
      Whisper returns a rich dict. transcribe_media extracts the essential fields.
    bullets:
      - "raw['text']: full transcript string — strip() removes leading/trailing whitespace"
      - "raw['segments']: list of dicts with many fields — keep start, end, text only"
      - "s['text'].strip(): remove leading space that Whisper prepends to each segment"
      - "raw.get('text', ''): guard against missing key in mock or edge cases"
      - "Return: {'text': str, 'segments': [{start, end, text}, ...]}"
      - "Mock must return the same dict structure for downstream code to work"
    narration: >
      Whisper segments have many fields: avg_logprob, no_speech_prob, tokens,
      temperature, and more. transcribe_media keeps only start, end, and text
      — the fields callers actually use. The mock must return the same structure:
      a dict with 'text' string and 'segments' list. This contract is what
      allows the mock and the real model to be swapped without changing callers.

  - type: exercise
    heading: "Exercise 3: transcribe_media"
    prompt: >
      Implement transcribe_media(source, transcribe_fn=None) -> dict.
      If transcribe_fn is not None: return transcribe_fn(source).
      Else: import whisper, os, tempfile; model = whisper.load_model('base').
      If isinstance(source, bytes): NamedTemporaryFile(suffix='.wav', delete=False),
      write source, try: raw=model.transcribe(tmp); finally: os.unlink(tmp).
      Else: raw = model.transcribe(str(source)).
      segments = [{start,end,text.strip()} for s in raw.get('segments',[])].
      Return {'text': raw.get('text','').strip(), 'segments': segments}.
    hint: >
      if transcribe_fn: return transcribe_fn(source).
      import whisper, os, tempfile; model = whisper.load_model('base').
      if isinstance(source, bytes): NamedTemporaryFile + try/finally unlink.
      else: raw = model.transcribe(str(source)).
      Extract segments: [{'start':s['start'],'end':s['end'],'text':s['text'].strip()}...].
      return {'text': raw.get('text','').strip(), 'segments': segments}.
    narration: >
      transcribe_media is structurally similar to Day 72's transcribe_audio.
      The main difference is the normalised output dict and the dual input form.

  - type: summary
    heading: "Lesson 3 Summary"
    bullets:
      - "transcribe_fn(source) receives source directly (bytes or path)"
      - "bytes path: NamedTemporaryFile(suffix='.wav', delete=False) + try/finally unlink"
      - "path: model.transcribe(str(source)) — str() handles Path objects"
      - "Normalised output: {'text': stripped str, 'segments': [{start,end,text}]}"
      - "s['text'].strip(): Whisper prepends a space to each segment text"
    narration: >
      Lesson 4 adds synthesize_speech and narrate_image — the TTS and
      cross-modal composition pipelines.
"""

_LESSON_04 = """\
day: "078"
lesson: 4
title: "synthesize_speech and narrate_image"
slides:
  - type: title
    heading: "TTS and Cross-Modal"
    subheading: "synthesize_speech + narrate_image"
    narration: >
      synthesize_speech brings the Day 73 edge-tts integration into the Media
      Studio. narrate_image chains vision and TTS: describe the image with
      llava, then speak the description with edge-tts. This is the first
      cross-modal pipeline in the course — image input, audio output.

  - type: code
    label: "synthesize_speech"
    heading: "synthesize_speech Implementation"
    code: |
      import asyncio

      def synthesize_speech(text, voice='en-US-AriaNeural', rate='+0%',
                            pitch='+0Hz', tts_fn=None):
          if tts_fn is not None:
              return tts_fn(text, voice, rate, pitch)
          import edge_tts
          async def _run():
              chunks = []
              async for chunk in edge_tts.Communicate(
                      text, voice, rate=rate, pitch=pitch).stream():
                  if chunk['type'] == 'audio':
                      chunks.append(chunk['data'])
              return b''.join(chunks)
          return asyncio.run(_run())
    narration: >
      synthesize_speech is the same Day 73 pattern: async edge-tts stream
      wrapped in asyncio.run. The tts_fn injection receives all four positional
      args: text, voice, rate, pitch. This is the same contract as Day 73's
      tts_fn mock. The function is synchronous from the caller's perspective —
      asyncio.run handles the event loop.

  - type: code
    label: "narrate_image"
    heading: "narrate_image — Cross-Modal Pipeline"
    code: |
      def narrate_image(source, voice='en-US-AriaNeural',
                        describe_fn=None, tts_fn=None):
          description = describe_media(source, describe_fn=describe_fn)
          audio = synthesize_speech(description, voice=voice, tts_fn=tts_fn)
          return {'description': description, 'audio': audio}
    narration: >
      narrate_image is five lines: call describe_media to get a text description,
      call synthesize_speech to turn that text to audio, return both in a dict.
      The describe_fn and tts_fn injections are forwarded to the respective
      module-level functions. The return dict matches the TalkingHeadPipeline
      pattern from Day 75: a result dict that includes both the intermediate
      description and the final audio, making debugging easier.

  - type: concept
    label: "Cross-modal"
    heading: "Cross-Modal Pipeline Design"
    body: >
      Cross-modal pipelines connect two modalities through a text bridge.
    bullets:
      - "Image -> text bridge (llava description) -> audio = image narration"
      - "Text bridge: the description string links the two modalities"
      - "Result dict includes description: intermediate output for debugging"
      - "Each stage independently injectable: can mock vision but use real TTS"
      - "Pattern extends: video -> frames -> describe each -> script -> podcast"
      - "Text is the universal interchange format between modalities"
    narration: >
      Text is the natural bridge between modalities. Every Day 66-77 tool
      either produces text (vision, OCR, STT) or consumes text (TTS, prompts).
      Cross-modal pipelines are just vision or audio tools on either side of
      a text bridge. narrate_image is the simplest cross-modal pipeline:
      one vision call and one TTS call. More complex chains (video narration,
      document reading) extend this pattern.

  - type: exercise
    heading: "Exercise 4: synthesize_speech and narrate_image"
    prompt: >
      Implement: (1) synthesize_speech(text, voice='en-US-AriaNeural',
      rate='+0%', pitch='+0Hz', tts_fn=None) -> bytes: if tts_fn: return
      tts_fn(text, voice, rate, pitch); else: import asyncio, edge_tts;
      async def _run(): collect audio chunks from edge_tts.Communicate.stream();
      return asyncio.run(_run()).
      (2) narrate_image(source, voice='en-US-AriaNeural', describe_fn=None,
      tts_fn=None) -> dict: description = describe_media(source, describe_fn);
      audio = synthesize_speech(description, voice=voice, tts_fn=tts_fn);
      return {'description': description, 'audio': audio}.
    hint: >
      synthesize_speech: if tts_fn: return tts_fn(text, voice, rate, pitch).
      import asyncio, edge_tts; async def _run(): chunks=[]; async for chunk
      in edge_tts.Communicate(text, voice, rate=rate, pitch=pitch).stream():
      if chunk['type']=='audio': chunks.append(chunk['data']); return b''.join(chunks).
      return asyncio.run(_run()).
      narrate_image: two calls + return dict.
    narration: >
      synthesize_speech re-uses the Day 73 async pattern. narrate_image is
      a three-line function: describe, synthesize, return dict.

  - type: summary
    heading: "Lesson 4 Summary"
    bullets:
      - "synthesize_speech: tts_fn(text, voice, rate, pitch) injection (Day 73 contract)"
      - "Real path: asyncio.run(edge_tts async stream) -> bytes"
      - "narrate_image: describe_media -> synthesize_speech -> {description, audio}"
      - "Cross-modal: text is the bridge between image and audio modalities"
      - "Result dict includes intermediate description for debugging"
    narration: >
      Lesson 5 assembles everything into the MediaStudio class with process_media
      and batch processing.
"""

_LESSON_05 = """\
day: "078"
lesson: 5
title: "MediaStudio — Unified Interface and Batch Processing"
slides:
  - type: title
    heading: "MediaStudio"
    subheading: "Section 5 complete — one class, all modalities"
    narration: >
      MediaStudio is the Section 5 capstone class. It binds three injections
      at construction, delegates every operation to a module-level function,
      and adds two higher-level methods: process (auto-detect and dispatch)
      and batch (process a list of sources). The class is the same pattern
      used throughout Section 5: bind at construction, delegate, no logic
      duplicated in the class body.

  - type: code
    label: "MediaStudio"
    heading: "MediaStudio Class"
    code: |
      class MediaStudio:
          def __init__(self, describe_fn=None, transcribe_fn=None, tts_fn=None):
              self._describe_fn = describe_fn
              self._transcribe_fn = transcribe_fn
              self._tts_fn = tts_fn

          def describe(self, source):
              return describe_media(source, describe_fn=self._describe_fn)

          def transcribe(self, source):
              return transcribe_media(source, transcribe_fn=self._transcribe_fn)

          def speak(self, text, voice='en-US-AriaNeural', rate='+0%', pitch='+0Hz'):
              return synthesize_speech(text, voice=voice, rate=rate, pitch=pitch,
                                       tts_fn=self._tts_fn)

          def narrate(self, source, voice='en-US-AriaNeural'):
              return narrate_image(source, voice=voice,
                                   describe_fn=self._describe_fn, tts_fn=self._tts_fn)

          def process(self, source):
              return process_media(source, describe_fn=self._describe_fn,
                                   transcribe_fn=self._transcribe_fn, tts_fn=self._tts_fn)

          def batch(self, sources):
              return [self.process(s) for s in sources]
    narration: >
      Every method is one line that delegates to the module-level function,
      forwarding the stored injections. speak exposes voice, rate, and pitch
      parameters for prosody control (Day 73). narrate chains describe and TTS
      using both the describe_fn and tts_fn. process delegates to process_media
      which calls detect_media_type to choose the right pipeline. batch is a
      list comprehension over process.

  - type: code
    label: "process_media"
    heading: "process_media — Auto-Dispatch"
    code: |
      def process_media(source, describe_fn=None, transcribe_fn=None, tts_fn=None):
          media_type = detect_media_type(source)
          if media_type == 'image':
              result = describe_media(source, describe_fn=describe_fn)
          elif media_type == 'audio':
              result = transcribe_media(source, transcribe_fn=transcribe_fn)
          else:
              result = {'note': f'Media type {media_type!r} detected but not processed'}
          return {'type': media_type, 'source': str(source), 'result': result}
    narration: >
      process_media is the routing layer. detect_media_type returns the type
      string, which drives the dispatch. Image sources are described, audio
      sources are transcribed, and unknown or video sources get a note dict
      rather than an error. The return dict always has the same three keys:
      type, source, and result — making batch results consistent regardless
      of media type.

  - type: concept
    label: "Section 5 pattern"
    heading: "The Section 5 Class Pattern"
    body: >
      Every Section 5 class follows the same three-part structure.
    bullets:
      - "Construction: bind injections, initialise internal state"
      - "Delegation: each method calls the module-level function + stored fn"
      - "No logic in class body: class is a convenient binding layer only"
      - "Tested at two levels: module functions (individual) + class (integration)"
      - "Section 5 classes: ImageProcessor, VisionAnalyzer, DocumentReader, ImageExtractor,"
      - "ImageGenerator, ImageSearchEngine, AudioTranscriber, PodcastGenerator,"
      - "VideoProcessor, TalkingHeadPipeline, ScreenAgent, LiveVisionAgent, MediaStudio"
    narration: >
      Day 78 is the 13th Section 5 class and the last of the section. Each one
      follows the same pattern, making them predictable to use and easy to test.
      The module-level functions can be used directly for simple pipelines.
      The class adds convenience for longer sessions that need consistent
      injection bindings across many calls.

  - type: exercise
    heading: "Exercise 5: MediaStudio + process_media"
    prompt: >
      Implement process_media(source, describe_fn=None, transcribe_fn=None,
      tts_fn=None) -> dict: detect_media_type(source) -> media_type; if 'image':
      describe_media; elif 'audio': transcribe_media; else: {'note':...};
      return {'type':media_type, 'source':str(source), 'result':result}.
      Implement MediaStudio(describe_fn=None, transcribe_fn=None, tts_fn=None):
      store all 3; describe/transcribe/speak/narrate/process/batch methods
      each delegate to module-level function with stored injections.
    hint: >
      process_media: media_type=detect_media_type(source); if/elif/else dispatch;
      return {'type':media_type,'source':str(source),'result':result}.
      MediaStudio: store injections; each method = one delegation line;
      batch: [self.process(s) for s in sources].
    narration: >
      MediaStudio is the final class of Section 5. Section 6 — AI Agents —
      begins on Day 79 and uses many of the tools built here.

  - type: summary
    heading: "Lesson 5 Summary — Section 5 Complete"
    bullets:
      - "process_media: detect_media_type -> dispatch -> {type, source, result}"
      - "Unknown/video types: {'note': ...} result dict, not an error"
      - "MediaStudio: 3 injections; describe/transcribe/speak/narrate/process/batch"
      - "batch: [self.process(s) for s in sources] list comprehension"
      - "Section 5 pattern: bind at construction, delegate in methods, no class logic"
      - "Section 5 complete (Days 66-78) — 13 classes, all injectable, all gate-green"
    narration: >
      Section 5 is complete. Thirteen days built a full vision and multimodal
      stack: image processing, vision LLM, OCR, structured extraction, image
      generation, visual search, speech-to-text, TTS, video, talking-head,
      screenshot agents, live camera, and now the Media Studio capstone.
      Section 6 begins Day 79 with AI Agent fundamentals.
"""

for i, content in enumerate([_LESSON_01, _LESSON_02, _LESSON_03,
                               _LESSON_04, _LESSON_05], start=1):
    (OUT / "lessons" / f"day_{DAY}_lesson_0{i}.yaml").write_text(content)

# ── shared mock helpers ───────────────────────────────────────────────────────
_MOCK_HELPER = """\
from PIL import Image as _PILImage

def _make_mock_image(w=100, h=100, color=(100, 150, 200)):
    return _PILImage.new('RGB', (w, h), color=color)

_mock_describe_fn   = lambda img, q: 'A test image with a solid color background.'
_mock_transcribe_fn = lambda src: {'text': 'Hello world.', 'segments': [
    {'start': 0.0, 'end': 1.0, 'text': 'Hello world.'}]}
_mock_tts_fn        = lambda text, voice, rate, pitch: b'AUDIO:' + text[:8].encode()
"""

# ── pre-built solutions for later exercises ───────────────────────────────────
_DETECT_SOL = """\
from pathlib import Path

MEDIA_EXTENSIONS = {
    'image': {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tiff'},
    'audio': {'.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac'},
    'video': {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv'},
}

def detect_media_type(path):
    ext = Path(path).suffix.lower()
    for media_type, extensions in MEDIA_EXTENSIONS.items():
        if ext in extensions:
            return media_type
    return 'unknown'
"""

_DESCRIBE_SOL = """\
import io, base64

def describe_media(source, describe_fn=None):
    from PIL import Image
    if isinstance(source, (str, Path)):
        image = Image.open(source) if describe_fn is None else source
    else:
        image = source
    prompt = 'Describe this image in detail, including all visible content.'
    if describe_fn is not None:
        return describe_fn(image, prompt)
    import ollama
    buf = io.BytesIO()
    image.save(buf, format='PNG')
    img_b64 = base64.b64encode(buf.getvalue()).decode()
    resp = ollama.chat(
        model='llava',
        messages=[{'role': 'user', 'content': prompt, 'images': [img_b64]}],
    )
    return resp['message']['content']
"""

_TRANSCRIBE_SOL = """\
def transcribe_media(source, transcribe_fn=None):
    if transcribe_fn is not None:
        return transcribe_fn(source)
    import whisper, os, tempfile
    model = whisper.load_model('base')
    if isinstance(source, bytes):
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            f.write(source)
            tmp = f.name
        try:
            raw = model.transcribe(tmp)
        finally:
            os.unlink(tmp)
    else:
        raw = model.transcribe(str(source))
    segments = [
        {'start': s['start'], 'end': s['end'], 'text': s['text'].strip()}
        for s in raw.get('segments', [])
    ]
    return {'text': raw.get('text', '').strip(), 'segments': segments}
"""

_TTS_NARRATE_SOL = """\
import asyncio

def synthesize_speech(text, voice='en-US-AriaNeural', rate='+0%', pitch='+0Hz',
                      tts_fn=None):
    if tts_fn is not None:
        return tts_fn(text, voice, rate, pitch)
    import edge_tts
    async def _run():
        chunks = []
        async for chunk in edge_tts.Communicate(
                text, voice, rate=rate, pitch=pitch).stream():
            if chunk['type'] == 'audio':
                chunks.append(chunk['data'])
        return b''.join(chunks)
    return asyncio.run(_run())

def narrate_image(source, voice='en-US-AriaNeural', describe_fn=None, tts_fn=None):
    description = describe_media(source, describe_fn=describe_fn)
    audio = synthesize_speech(description, voice=voice, tts_fn=tts_fn)
    return {'description': description, 'audio': audio}
"""

_PROCESS_STUDIO_SOL = """\
def process_media(source, describe_fn=None, transcribe_fn=None, tts_fn=None):
    media_type = detect_media_type(source)
    if media_type == 'image':
        result = describe_media(source, describe_fn=describe_fn)
    elif media_type == 'audio':
        result = transcribe_media(source, transcribe_fn=transcribe_fn)
    else:
        result = {'note': f'Media type {media_type!r} detected but not processed'}
    return {'type': media_type, 'source': str(source), 'result': result}

class MediaStudio:
    def __init__(self, describe_fn=None, transcribe_fn=None, tts_fn=None):
        self._describe_fn = describe_fn
        self._transcribe_fn = transcribe_fn
        self._tts_fn = tts_fn

    def describe(self, source):
        return describe_media(source, describe_fn=self._describe_fn)

    def transcribe(self, source):
        return transcribe_media(source, transcribe_fn=self._transcribe_fn)

    def speak(self, text, voice='en-US-AriaNeural', rate='+0%', pitch='+0Hz'):
        return synthesize_speech(text, voice=voice, rate=rate, pitch=pitch,
                                 tts_fn=self._tts_fn)

    def narrate(self, source, voice='en-US-AriaNeural'):
        return narrate_image(source, voice=voice,
                             describe_fn=self._describe_fn, tts_fn=self._tts_fn)

    def process(self, source):
        return process_media(source, describe_fn=self._describe_fn,
                             transcribe_fn=self._transcribe_fn, tts_fn=self._tts_fn)

    def batch(self, sources):
        return [self.process(s) for s in sources]
"""

# ── EX1: MEDIA_EXTENSIONS + detect_media_type ────────────────────────────────
_EX1_STUB = """\
from pathlib import Path

MEDIA_EXTENSIONS = {}  # fill in the three types

def detect_media_type(path):
    \"\"\"Return 'image', 'audio', 'video', or 'unknown' from file extension.\"\"\"
    raise NotImplementedError
"""

_EX1_CHECKS = r"""
score, total = 0, 5
try:
    assert detect_media_type('photo.png') == 'image'
    assert detect_media_type('photo.jpg') == 'image'
    assert detect_media_type('photo.JPEG') == 'image'   # case-insensitive
    score += 1; print("✅ image extensions detected")

    assert detect_media_type('recording.mp3') == 'audio'
    assert detect_media_type('recording.wav') == 'audio'
    assert detect_media_type('recording.WAV') == 'audio'
    score += 1; print("✅ audio extensions detected")

    assert detect_media_type('clip.mp4') == 'video'
    assert detect_media_type('clip.avi') == 'video'
    score += 1; print("✅ video extensions detected")

    assert detect_media_type('notes.txt') == 'unknown'
    assert detect_media_type('data.csv') == 'unknown'
    score += 1; print("✅ unknown extensions return 'unknown'")

    assert all(k in MEDIA_EXTENSIONS for k in ('image', 'audio', 'video'))
    assert '.png' in MEDIA_EXTENSIONS['image']
    assert '.mp3' in MEDIA_EXTENSIONS['audio']
    assert '.mp4' in MEDIA_EXTENSIONS['video']
    score += 1; print("✅ MEDIA_EXTENSIONS has correct structure")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX1 = nb([
    md("# Day 078 — Exercise 1: MEDIA_EXTENSIONS and detect_media_type\n\n"
       "**What you'll build:** The routing layer for the entire Media Studio.\n\n"
       "**Why it matters:** `process_media` auto-dispatches to the right pipeline "
       "based on file type. `detect_media_type` uses only the extension — "
       "the file does not need to exist."),
    code(_MOCK_HELPER),
    md("## Task\n\n"
       "1. Define `MEDIA_EXTENSIONS` dict:\n"
       "   - `'image'`: `{'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tiff'}`\n"
       "   - `'audio'`: `{'.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac'}`\n"
       "   - `'video'`: `{'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv'}`\n\n"
       "2. `detect_media_type(path) -> str`\n"
       "   - `ext = Path(path).suffix.lower()`\n"
       "   - Loop over `MEDIA_EXTENSIONS.items()`; return type if ext in set\n"
       "   - Return `'unknown'` if no match"),
    md("## Your Implementation"),
    code(_EX1_STUB),
    code(_DETECT_SOL),
    md("## Automated checks"),
    code(_EX1_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _DETECT_SOL + "```\n\n"
       "**Why `.suffix.lower()`?** Python's `Path.suffix` preserves case. "
       "A user uploading `Photo.JPEG` would fail without the `.lower()` call.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_01.ipynb", EX1)

# ── EX2: describe_media ───────────────────────────────────────────────────────
_EX2_STUB = """\
import io, base64
from pathlib import Path

def describe_media(source, describe_fn=None):
    \"\"\"Describe an image (PIL Image or path) using a vision LLM.\"\"\"
    raise NotImplementedError
"""

_EX2_CHECKS = r"""
score, total = 0, 4
try:
    from PIL import Image as PILImage
    import tempfile, os

    img = _make_mock_image()
    result = describe_media(img, describe_fn=_mock_describe_fn)
    assert isinstance(result, str) and len(result) > 0
    score += 1; print("✅ describe_media returns str for PIL Image input")

    received = {}
    def _dfn(i, q): received.update(img=i, q=q); return 'DESC'
    describe_media(img, describe_fn=_dfn)
    assert isinstance(received.get('img'), PILImage.Image)
    assert isinstance(received.get('q'), str) and len(received['q']) > 10
    score += 1; print("✅ describe_fn receives (PIL Image, prompt_str)")

    # File path input
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        img.save(f, format='PNG')
        tmp = f.name
    try:
        path_result = describe_media(tmp, describe_fn=_mock_describe_fn)
        assert isinstance(path_result, str)
        score += 1; print("✅ describe_media accepts file path")
    finally:
        os.unlink(tmp)

    # Both forms produce same result with same mock
    img2 = _make_mock_image()
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        img2.save(f, format='PNG')
        tmp2 = f.name
    try:
        r1 = describe_media(img2, describe_fn=_mock_describe_fn)
        r2 = describe_media(tmp2, describe_fn=_mock_describe_fn)
        assert r1 == r2
        score += 1; print("✅ PIL Image and file path produce same mock result")
    finally:
        os.unlink(tmp2)

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX2 = nb([
    md("# Day 078 — Exercise 2: describe_media\n\n"
       "**What you'll build:** The image description pipeline — accepts PIL Image "
       "or file path, returns a vision LLM description.\n\n"
       "**Why it matters:** `describe_media` is the vision pipeline of the studio. "
       "Supporting both input forms means it works in programmatic pipelines "
       "(PIL Images from camera/generation) and batch file processing."),
    code(_MOCK_HELPER + _DETECT_SOL),
    md("## Task\n\n"
       "`describe_media(source, describe_fn=None) -> str`\n\n"
       "1. `from PIL import Image`\n"
       "2. `if isinstance(source, (str, Path)): image = Image.open(source)` "
       "else: `image = source`\n"
       "3. `prompt = 'Describe this image in detail, including all visible content.'`\n"
       "4. If `describe_fn`: `return describe_fn(image, prompt)`\n"
       "5. Else: BytesIO + `image.save(buf, format='PNG')` + base64 + "
       "`ollama.chat(model='llava', ...)` + return `resp['message']['content']`"),
    md("## Your Implementation"),
    code(_EX2_STUB),
    code(_DESCRIBE_SOL),
    md("## Automated checks"),
    code(_EX2_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _DESCRIBE_SOL + "```\n\n"
       "**Why does `describe_fn` receive PIL Image, not base64?** The conversion "
       "to base64 is an implementation detail of the Ollama call. Mocks are simpler "
       "and more versatile when they receive a PIL Image — they can inspect size, "
       "mode, and pixels if needed.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_02.ipynb", EX2)

# ── EX3: transcribe_media ─────────────────────────────────────────────────────
_EX3_GIVEN = _MOCK_HELPER + _DETECT_SOL + _DESCRIBE_SOL

_EX3_STUB = """\
def transcribe_media(source, transcribe_fn=None):
    \"\"\"Transcribe audio (bytes or path) using Whisper.
    Returns dict with keys: text (str), segments (list).
    \"\"\"
    raise NotImplementedError
"""

_EX3_CHECKS = r"""
score, total = 0, 4
try:
    result = transcribe_media(b'MOCK_AUDIO', transcribe_fn=_mock_transcribe_fn)
    assert isinstance(result, dict)
    score += 1; print("✅ transcribe_media returns dict")

    assert 'text' in result and 'segments' in result
    score += 1; print("✅ result has 'text' and 'segments' keys")

    assert isinstance(result['text'], str)
    assert isinstance(result['segments'], list)
    score += 1; print("✅ text is str, segments is list")

    called = []
    def _tfn(src): called.append(src); return {'text': 'hi', 'segments': []}
    transcribe_media('test.wav', transcribe_fn=_tfn)
    assert called[0] == 'test.wav', f"transcribe_fn not called with source: {called}"
    score += 1; print("✅ transcribe_fn receives source directly")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX3 = nb([
    md("# Day 078 — Exercise 3: transcribe_media\n\n"
       "**What you'll build:** The audio transcription pipeline — accepts bytes "
       "or file path, returns a normalised transcript dict.\n\n"
       "**Why it matters:** `transcribe_media` brings the Day 72 Whisper integration "
       "into the studio. The dual input form handles both uploaded audio bytes and "
       "on-disk audio files."),
    code(_EX3_GIVEN),
    md("## Task\n\n"
       "`transcribe_media(source, transcribe_fn=None) -> dict`\n\n"
       "1. If `transcribe_fn`: `return transcribe_fn(source)`\n"
       "2. `import whisper, os, tempfile; model = whisper.load_model('base')`\n"
       "3. If `isinstance(source, bytes)`: write to `NamedTemporaryFile(suffix='.wav', "
       "delete=False)`, `try: raw=model.transcribe(tmp); finally: os.unlink(tmp)`\n"
       "4. Else: `raw = model.transcribe(str(source))`\n"
       "5. `segments = [{'start':s['start'],'end':s['end'],'text':s['text'].strip()} "
       "for s in raw.get('segments',[])]`\n"
       "6. Return `{'text': raw.get('text','').strip(), 'segments': segments}`"),
    md("## Your Implementation"),
    code(_EX3_STUB),
    code(_TRANSCRIBE_SOL),
    md("## Automated checks"),
    code(_EX3_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _TRANSCRIBE_SOL + "```\n\n"
       "**Why `transcribe_fn(source)` not `transcribe_fn(source, model)`?** "
       "The mock doesn't need the model — it returns a fixed dict. The injection "
       "replaces the entire transcription operation, not just one part of it.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_03.ipynb", EX3)

# ── EX4: synthesize_speech + narrate_image ────────────────────────────────────
_EX4_GIVEN = _MOCK_HELPER + _DETECT_SOL + _DESCRIBE_SOL + _TRANSCRIBE_SOL

_EX4_STUB = """\
import asyncio

def synthesize_speech(text, voice='en-US-AriaNeural', rate='+0%', pitch='+0Hz',
                      tts_fn=None):
    \"\"\"Convert text to speech. Returns MP3 bytes.\"\"\"
    raise NotImplementedError

def narrate_image(source, voice='en-US-AriaNeural', describe_fn=None, tts_fn=None):
    \"\"\"Describe an image then speak the description.
    Returns dict with keys: description (str), audio (bytes).
    \"\"\"
    raise NotImplementedError
"""

_EX4_CHECKS = r"""
score, total = 0, 5
try:
    audio = synthesize_speech('Hello', tts_fn=_mock_tts_fn)
    assert isinstance(audio, bytes) and len(audio) > 0
    score += 1; print("✅ synthesize_speech returns bytes")

    calls = []
    def _tfn(text, voice, rate, pitch): calls.append((text,voice,rate,pitch)); return b'A'
    synthesize_speech('Test text', voice='en-GB-RyanNeural',
                      rate='+10%', pitch='+5Hz', tts_fn=_tfn)
    assert calls[0] == ('Test text', 'en-GB-RyanNeural', '+10%', '+5Hz')
    score += 1; print("✅ tts_fn receives (text, voice, rate, pitch)")

    img = _make_mock_image()
    result = narrate_image(img, describe_fn=_mock_describe_fn, tts_fn=_mock_tts_fn)
    assert isinstance(result, dict)
    score += 1; print("✅ narrate_image returns dict")

    assert 'description' in result and 'audio' in result
    score += 1; print("✅ result has 'description' and 'audio'")

    assert isinstance(result['description'], str) and isinstance(result['audio'], bytes)
    score += 1; print("✅ description is str, audio is bytes")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX4 = nb([
    md("# Day 078 — Exercise 4: synthesize_speech and narrate_image\n\n"
       "**What you'll build:** The TTS pipeline and the first cross-modal pipeline "
       "(image → describe → speak).\n\n"
       "**Why it matters:** `narrate_image` is a two-stage pipeline that produces "
       "audio narration of any image. Text is the bridge: vision produces it, "
       "TTS consumes it."),
    code(_EX4_GIVEN),
    md("## Task\n\n"
       "1. `synthesize_speech(text, voice='en-US-AriaNeural', rate='+0%', "
       "pitch='+0Hz', tts_fn=None) -> bytes`\n"
       "   - If `tts_fn`: `return tts_fn(text, voice, rate, pitch)`\n"
       "   - Else: `import edge_tts; async def _run(): collect audio chunks; "
       "return b''.join(chunks); return asyncio.run(_run())`\n\n"
       "2. `narrate_image(source, voice='en-US-AriaNeural', describe_fn=None, "
       "tts_fn=None) -> dict`\n"
       "   - `description = describe_media(source, describe_fn=describe_fn)`\n"
       "   - `audio = synthesize_speech(description, voice=voice, tts_fn=tts_fn)`\n"
       "   - `return {'description': description, 'audio': audio}`"),
    md("## Your Implementation"),
    code(_EX4_STUB),
    code(_TTS_NARRATE_SOL),
    md("## Automated checks"),
    code(_EX4_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _TTS_NARRATE_SOL + "```\n\n"
       "**Why return both `description` and `audio` in narrate_image?** "
       "The text description is useful on its own — callers can display it, "
       "log it, or store it. Returning only the audio would discard "
       "intermediate output that took a full LLM call to produce.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_04.ipynb", EX4)

# ── EX5: process_media + MediaStudio ─────────────────────────────────────────
_EX5_GIVEN = (_MOCK_HELPER + _DETECT_SOL + _DESCRIBE_SOL
              + _TRANSCRIBE_SOL + _TTS_NARRATE_SOL)

_EX5_STUB = """\
def process_media(source, describe_fn=None, transcribe_fn=None, tts_fn=None):
    \"\"\"Auto-detect media type and process. Returns {type, source, result}.\"\"\"
    raise NotImplementedError

class MediaStudio:
    \"\"\"Multimodal media processing studio.\"\"\"

    def __init__(self, describe_fn=None, transcribe_fn=None, tts_fn=None):
        raise NotImplementedError

    def describe(self, source):
        raise NotImplementedError

    def transcribe(self, source):
        raise NotImplementedError

    def speak(self, text, voice='en-US-AriaNeural', rate='+0%', pitch='+0Hz'):
        raise NotImplementedError

    def narrate(self, source, voice='en-US-AriaNeural'):
        raise NotImplementedError

    def process(self, source):
        raise NotImplementedError

    def batch(self, sources):
        raise NotImplementedError
"""

_EX5_CHECKS = r"""
score, total = 0, 6
try:
    from PIL import Image as PILImage
    import tempfile, os

    # process_media with image
    img = _make_mock_image()
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        img.save(f, format='PNG'); tmp_img = f.name
    try:
        r = process_media(tmp_img, describe_fn=_mock_describe_fn)
        assert r['type'] == 'image' and isinstance(r['result'], str)
        score += 1; print("✅ process_media dispatches image to describe_media")
    finally:
        os.unlink(tmp_img)

    # process_media with audio (file need not exist — mock)
    r2 = process_media('test.mp3', transcribe_fn=_mock_transcribe_fn)
    assert r2['type'] == 'audio' and isinstance(r2['result'], dict)
    score += 1; print("✅ process_media dispatches audio to transcribe_media")

    # process_media with unknown
    r3 = process_media('data.csv')
    assert r3['type'] == 'unknown' and 'note' in r3['result']
    score += 1; print("✅ process_media handles unknown type gracefully")

    # MediaStudio describe
    studio = MediaStudio(describe_fn=_mock_describe_fn,
                         transcribe_fn=_mock_transcribe_fn,
                         tts_fn=_mock_tts_fn)
    d = studio.describe(PILImage.new('RGB', (10, 10)))
    assert isinstance(d, str)
    score += 1; print("✅ MediaStudio.describe returns str")

    t = studio.transcribe(b'audio')
    assert isinstance(t, dict) and 'text' in t
    score += 1; print("✅ MediaStudio.transcribe returns {text, segments}")

    results = studio.batch(['photo.png', 'clip.mp4', 'notes.txt'])
    assert len(results) == 3 and all('type' in r for r in results)
    score += 1; print("✅ MediaStudio.batch returns list of 3 result dicts")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX5 = nb([
    md("# Day 078 — Exercise 5: process_media and MediaStudio\n\n"
       "**What you'll build:** The routing layer and the capstone class.\n\n"
       "**Why it matters:** `process_media` makes the studio file-type-aware. "
       "`MediaStudio` is the Section 5 capstone class — 13 injectable classes, "
       "all following the same bind-at-construction pattern."),
    code(_EX5_GIVEN),
    md("## Task\n\n"
       "1. `process_media(source, describe_fn=None, transcribe_fn=None, tts_fn=None) -> dict`\n"
       "   - `media_type = detect_media_type(source)`\n"
       "   - `if image`: `result = describe_media(source, describe_fn=describe_fn)`\n"
       "   - `elif audio`: `result = transcribe_media(source, transcribe_fn=transcribe_fn)`\n"
       "   - `else`: `result = {'note': f'Media type {media_type!r} detected but not processed'}`\n"
       "   - Return `{'type': media_type, 'source': str(source), 'result': result}`\n\n"
       "2. `MediaStudio(describe_fn=None, transcribe_fn=None, tts_fn=None)`\n"
       "   - Store all 3 injections\n"
       "   - `describe/transcribe/speak/narrate/process`: one delegation line each\n"
       "   - `batch(sources)`: `[self.process(s) for s in sources]`"),
    md("## Your Implementation"),
    code(_EX5_STUB),
    code(_PROCESS_STUDIO_SOL),
    md("## Automated checks"),
    code(_EX5_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _PROCESS_STUDIO_SOL + "```\n\n"
       "**Why `{'note': ...}` instead of `raise ValueError` for unknown types?** "
       "In a batch pipeline, one unsupported file should not crash the whole job. "
       "Returning a descriptive dict lets the caller decide how to handle it.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_05.ipynb", EX5)

# ── PROJECT NOTEBOOK ──────────────────────────────────────────────────────────
PROJECT = nb([
    md(f"# Day {DAY} — Project: Multimodal Media Studio\n\n"
       "## Objective\n\n"
       "Build `media_studio.py` — a Media Studio that combines vision description, "
       "audio transcription, and text-to-speech synthesis into a unified interface.\n\n"
       "## Deliverable\n\n"
       "`media_studio.py` with:\n\n"
       "- `MEDIA_EXTENSIONS`: dict of type → extension set\n"
       "- `detect_media_type(path) -> str`\n"
       "- `describe_media(source, describe_fn=None) -> str`\n"
       "- `transcribe_media(source, transcribe_fn=None) -> dict`\n"
       "- `synthesize_speech(text, ..., tts_fn=None) -> bytes`\n"
       "- `narrate_image(source, ..., describe_fn=None, tts_fn=None) -> dict`\n"
       "- `process_media(source, ...) -> dict`\n"
       "- `MediaStudio(describe_fn=None, transcribe_fn=None, tts_fn=None)` "
       "with `describe/transcribe/speak/narrate/process/batch`\n\n"
       "## Usage (with Ollama + Whisper + edge-tts installed)\n\n"
       "```python\n"
       "from media_studio import MediaStudio\n"
       "studio = MediaStudio()\n"
       "desc = studio.describe('photo.png')\n"
       "audio = studio.speak(desc)\n"
       "Path('narration.mp3').write_bytes(audio)\n"
       "```"),
    code("# Your implementation here — build MediaStudio and write media_studio.py\n"),
])
save(OUT / "project" / "project.ipynb", PROJECT)

# ── SOLUTION NOTEBOOK ─────────────────────────────────────────────────────────
_SOL_CELL1 = (
    f"_SRC = {repr(_MEDIA_STUDIO_SRC)}\n"
    "from pathlib import Path\n"
    "Path('media_studio.py').write_text(_SRC, encoding='utf-8')\n"
    "print('media_studio.py written.')"
)

_SOL_CELL2 = r"""
from pathlib import Path
from PIL import Image as PILImage
from media_studio import (
    MEDIA_EXTENSIONS, detect_media_type, describe_media, transcribe_media,
    synthesize_speech, narrate_image, process_media, MediaStudio,
)
import tempfile, os

_mock_describe_fn   = lambda img, q: 'A solid color test image.'
_mock_transcribe_fn = lambda src: {'text': 'Hello world.', 'segments': []}
_mock_tts_fn        = lambda t, v, r, p: b'AUDIO:' + t[:8].encode()

# 1. detect_media_type
assert detect_media_type('photo.png') == 'image'
assert detect_media_type('audio.mp3') == 'audio'
assert detect_media_type('clip.mp4')  == 'video'
assert detect_media_type('data.txt')  == 'unknown'
print("✅ detect_media_type")

# 2. describe_media
img = PILImage.new('RGB', (50, 50), color=(100,100,100))
d = describe_media(img, describe_fn=_mock_describe_fn)
assert isinstance(d, str) and len(d) > 0
print("✅ describe_media (PIL Image)")

with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
    img.save(f, format='PNG'); tmp_img = f.name
try:
    d2 = describe_media(tmp_img, describe_fn=_mock_describe_fn)
    assert isinstance(d2, str)
    print("✅ describe_media (file path)")
finally:
    os.unlink(tmp_img)

# 3. transcribe_media
t = transcribe_media(b'AUDIO', transcribe_fn=_mock_transcribe_fn)
assert isinstance(t, dict) and 'text' in t and 'segments' in t
print("✅ transcribe_media")

# 4. synthesize_speech
audio = synthesize_speech('Hello', tts_fn=_mock_tts_fn)
assert isinstance(audio, bytes) and len(audio) > 0
print("✅ synthesize_speech")

# 5. narrate_image
n = narrate_image(img, describe_fn=_mock_describe_fn, tts_fn=_mock_tts_fn)
assert 'description' in n and 'audio' in n
assert isinstance(n['description'], str) and isinstance(n['audio'], bytes)
print("✅ narrate_image")

# 6. process_media
with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
    img.save(f, format='PNG'); tmp2 = f.name
try:
    r = process_media(tmp2, describe_fn=_mock_describe_fn)
    assert r['type'] == 'image' and isinstance(r['result'], str)
    print("✅ process_media (image)")
finally:
    os.unlink(tmp2)

r2 = process_media('test.mp3', transcribe_fn=_mock_transcribe_fn)
assert r2['type'] == 'audio' and 'text' in r2['result']
print("✅ process_media (audio)")

r3 = process_media('data.txt')
assert r3['type'] == 'unknown' and 'note' in r3['result']
print("✅ process_media (unknown)")

# 7. MediaStudio
studio = MediaStudio(describe_fn=_mock_describe_fn,
                     transcribe_fn=_mock_transcribe_fn,
                     tts_fn=_mock_tts_fn)
assert isinstance(studio.describe(img), str)
assert isinstance(studio.transcribe(b'A')['text'], str)
assert isinstance(studio.speak('Hello'), bytes)
narr = studio.narrate(img)
assert 'description' in narr and 'audio' in narr
results = studio.batch(['x.png', 'y.mp3', 'z.txt'])
assert len(results) == 3
print("✅ MediaStudio (describe/transcribe/speak/narrate/batch)")

print("\nMedia Studio complete! Section 5 done.")
"""

SOLUTION = nb([
    md(f"# Day {DAY} — Solution: Multimodal Media Studio"),
    code(_SOL_CELL1),
    code(_SOL_CELL2),
])
save(OUT / "project" / "solution" / "solution.ipynb", SOLUTION)
(OUT / "project" / "solution" / "media_studio.py").write_text(_MEDIA_STUDIO_SRC)

print(f"Day {DAY} notebooks written to {OUT}")
print("  lessons/    day_078_lesson_01.yaml – lesson_05.yaml")
print("  exercises/  exercise_01 – exercise_05")
print("  project/    project.ipynb")
print("  project/solution/  solution.ipynb + media_studio.py")
