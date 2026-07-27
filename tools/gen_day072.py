#!/usr/bin/env python3
"""gen_day072.py — generate Day 072: Speech-to-Text."""
from pathlib import Path
import json

ROOT    = Path(__file__).parent.parent
DAY     = "072"
SECTION = "05_vision_multimodal"
OUT     = ROOT / SECTION / f"day_{DAY}"

(OUT / "exercises").mkdir(parents=True, exist_ok=True)
(OUT / "lessons").mkdir(parents=True, exist_ok=True)
(OUT / "project" / "solution").mkdir(parents=True, exist_ok=True)

# ── deliverable: audio_transcriber.py ────────────────────────────────────────
_TRANSCRIBER_SRC = '''\
"""audio_transcriber.py — Day 072: Speech-to-Text.

Transcribes audio files using the openai-whisper local package.
openai-whisper is the LOCAL package — it runs entirely on your machine.
No API key, no network calls after the model is downloaded.

Setup:
    pip install openai-whisper
    brew install ffmpeg      # macOS
    # Ubuntu: apt install ffmpeg

Usage:
    from audio_transcriber import AudioTranscriber

    # Real transcription
    tr = AudioTranscriber(model='base')
    result = tr.transcribe('recording.mp3')
    print(result['text'])

    # Testing — no audio file needed
    mock = lambda src: {'text': ' Hello.', 'language': 'en', 'segments': [
        {'id': 0, 'start': 0.0, 'end': 1.0, 'text': ' Hello.',
         'avg_logprob': -0.2, 'no_speech_prob': 0.01}]}
    tr = AudioTranscriber(transcribe_fn=mock)
    print(tr.get_text(b'fake audio'))   # Hello.
"""
import os
import tempfile
from typing import Callable, Optional, Union


def _format_time(seconds: float) -> str:
    """Convert seconds to HH:MM:SS string."""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def format_transcript(result: dict, include_timestamps: bool = False) -> str:
    """Format a whisper result dict as a readable string.

    Args:
        result:             Whisper result dict (keys: text, segments, language)
        include_timestamps: If True, prefix each segment with [HH:MM:SS]
    Returns:
        Formatted transcript string
    """
    if not include_timestamps:
        return result.get("text", "").strip()
    lines = []
    for seg in result.get("segments", []):
        ts = _format_time(seg.get("start", 0.0))
        lines.append(f"[{ts}] {seg.get('text', '').strip()}")
    return "\\n".join(lines)


def extract_segments(result: dict) -> list:
    """Extract time-stamped segments from a whisper result.

    Returns:
        list of dicts: {start: float, end: float, text: str, confidence: float}
        confidence is derived from avg_logprob ∈ (-∞, 0]: 0.0 = poor, 1.0 = perfect
    """
    out = []
    for seg in result.get("segments", []):
        logprob = seg.get("avg_logprob", -1.0)
        confidence = min(1.0, max(0.0, 1.0 + logprob))
        out.append({
            "start":      float(seg.get("start", 0.0)),
            "end":        float(seg.get("end", 0.0)),
            "text":       seg.get("text", "").strip(),
            "confidence": round(confidence, 4),
        })
    return out


def transcribe_audio(source, transcribe_fn: Optional[Callable] = None,
                     model: str = "base") -> dict:
    """Transcribe an audio source using openai-whisper.

    Args:
        source:        File path (str/Path), bytes, or numpy float32 array
        transcribe_fn: callable(source) -> dict for testing (no whisper needed)
        model:         Whisper model size: tiny, base, small, medium, large
    Returns:
        dict with keys: text (str), language (str), segments (list)
    """
    if transcribe_fn is not None:
        return transcribe_fn(source)
    import whisper as _whisper
    mdl = _whisper.load_model(model)
    if isinstance(source, (bytes, bytearray)):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(source)
            tmp = f.name
        try:
            return mdl.transcribe(tmp)
        finally:
            os.unlink(tmp)
    return mdl.transcribe(str(source))


def search_transcript(result: dict, query: str,
                      case_sensitive: bool = False) -> list:
    """Find segments whose text contains the query string.

    Args:
        result:         Whisper result dict
        query:          Search string
        case_sensitive: If False, comparison is case-insensitive
    Returns:
        list of matching segment dicts (same format as extract_segments)
    """
    segments = extract_segments(result)
    if not case_sensitive:
        q = query.lower()
        return [s for s in segments if q in s["text"].lower()]
    return [s for s in segments if query in s["text"]]


class AudioTranscriber:
    """Transcribe audio files using openai-whisper.

    Inject transcribe_fn for testing without whisper or audio files::

        mock = lambda src: {'text': ' Hello.', 'language': 'en',
                            'segments': [{'id':0,'start':0.0,'end':1.0,
                             'text':' Hello.','avg_logprob':-0.2,'no_speech_prob':0.01}]}
        tr = AudioTranscriber(transcribe_fn=mock)
    """

    def __init__(self, model: str = "base",
                 transcribe_fn: Optional[Callable] = None) -> None:
        self._model        = model
        self._transcribe_fn = transcribe_fn

    def transcribe(self, source) -> dict:
        """Transcribe audio. Returns full whisper result dict."""
        return transcribe_audio(source,
                                transcribe_fn=self._transcribe_fn,
                                model=self._model)

    def get_text(self, source) -> str:
        """Return plain transcript text (stripped)."""
        return format_transcript(self.transcribe(source))

    def get_segments(self, source) -> list:
        """Return list of time-stamped segment dicts."""
        return extract_segments(self.transcribe(source))

    def search(self, source, query: str,
               case_sensitive: bool = False) -> list:
        """Search for a query in the transcript segments."""
        return search_transcript(self.transcribe(source), query,
                                 case_sensitive=case_sensitive)
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
day: "072"
lesson: 1
title: "openai-whisper — Local Speech-to-Text"
slides:
  - type: title
    heading: "Speech-to-Text"
    subheading: "Day 72 — openai-whisper, the local package"
    narration: >
      Section 5 has covered vision, extraction, generation, and visual
      search. Today adds the audio dimension: converting spoken words to
      text. You will use openai-whisper — not the OpenAI API, but the
      open-source local package that runs entirely on your machine.
      No API key, no cost, no internet after the model is downloaded.

  - type: concept
    label: "What is Whisper"
    heading: "openai-whisper: The Local Package"
    body: >
      OpenAI released the Whisper model weights as open-source in 2022.
      The openai-whisper pip package loads those weights locally.
      This is completely different from the OpenAI Whisper API.
    bullets:
      - "pip install openai-whisper — installs the local package"
      - "brew install ffmpeg — required for audio file loading (macOS)"
      - "import whisper — the module name after pip install"
      - "No API key. Model files download once (~74MB for base)"
    narration: >
      The distinction between the local package and the API matters:
      the API sends your audio to OpenAI's servers and charges per minute.
      The local package downloads the model weights once and runs them
      on your CPU or GPU. For a course with a zero-cost constraint, the
      local package is the only option. The quality is identical — it's
      the same model. The local package also guarantees privacy since audio
      never leaves your machine.

  - type: concept
    label: "Model sizes"
    heading: "Whisper Model Sizes"
    body: >
      Whisper comes in five sizes. Each is a trade-off between speed,
      accuracy, and memory.
    bullets:
      - "tiny: 39M params, fastest, lowest accuracy (good for testing)"
      - "base: 74M params, fast, good accuracy (recommended for development)"
      - "small: 244M params, slower, better accuracy"
      - "medium: 769M params, slow, high accuracy"
      - "large: 1.5B params, slowest, best accuracy (needs 10GB+ GPU)"
    narration: >
      For exercises and development, base is the right choice: small enough
      to download quickly, fast enough to iterate, accurate enough for
      clear speech. For production, small or medium often hits the sweet
      spot of speed and accuracy. Large is for professional transcription
      services where accuracy is paramount and latency is not a concern.
      All sizes are multilingual — Whisper was trained on 680,000 hours of
      audio in 99 languages.

  - type: how_it_works
    label: "Whisper output"
    heading: "What Whisper Returns"
    body: >
      model.transcribe(audio) returns a dict with three key fields.
    bullets:
      - "text: the full transcript as one string (may have leading space)"
      - "language: detected language code like en, fr, de, zh"
      - "segments: list of dicts with start, end, text, avg_logprob"
      - "avg_logprob: average log probability — negative value, closer to 0 = more confident"
    narration: >
      The segments list is Whisper's most powerful output. Each segment
      is a time-stamped chunk of speech with start and end in seconds.
      avg_logprob is the average log probability of the tokens in the
      segment — a confidence proxy. Values close to 0 mean high confidence,
      values below -1 suggest noise, music, or unclear speech.
      no_speech_prob is the probability that the segment contains no
      speech at all — useful for filtering silence or music.

  - type: code
    label: "Quick start"
    heading: "Using Whisper Locally"
    code: |
      # Real usage (requires pip install openai-whisper + ffmpeg)
      import whisper
      model = whisper.load_model('base')
      result = model.transcribe('recording.mp3')
      print(result['text'])        # full transcript
      print(result['language'])    # 'en'
      for seg in result['segments']:
          print(seg['start'], seg['end'], seg['text'])

      # Testing — inject a mock so no whisper or audio needed
      _MOCK = {
          'text': ' Hello world. Testing one two three.',
          'language': 'en',
          'segments': [
              {'id': 0, 'start': 0.0, 'end': 2.5, 'text': ' Hello world.',
               'avg_logprob': -0.25, 'no_speech_prob': 0.01},
              {'id': 1, 'start': 2.5, 'end': 6.0, 'text': ' Testing one two three.',
               'avg_logprob': -0.20, 'no_speech_prob': 0.01},
          ],
      }
      mock_transcribe = lambda src: _MOCK
    narration: >
      The mock pattern for transcription is simpler than for vision because
      the transcription function only has one injection point (transcribe_fn)
      rather than two (describe_fn + embed_fn). The mock takes the audio
      source and returns a dict that looks exactly like whisper output.
      All downstream functions work on the dict, so the mock exercises the
      entire formatting and segment extraction pipeline without loading any
      model or audio file.

  - type: exercise
    heading: "Exercise 1: format_transcript"
    prompt: >
      Implement _format_time(seconds) -> str: convert float seconds to HH:MM:SS string.
      Use divmod(int(seconds), 60) twice (seconds→m+s, then m→h+m).
      Format as f'{h:02d}:{m:02d}:{s:02d}'.
      Then implement format_transcript(result, include_timestamps=False) -> str:
      if include_timestamps is False, return result.get('text', '').strip().
      If include_timestamps is True, iterate result.get('segments', []),
      format each as '[HH:MM:SS] {text}', join with newline.
    hint: >
      _format_time: m, s = divmod(int(seconds), 60); h, m = divmod(m, 60); return f'{h:02d}:{m:02d}:{s:02d}'.
      format_transcript: if not include_timestamps: return result.get('text','').strip().
      else: lines = [f'[{_format_time(seg[start])}] {seg[text].strip()}' for seg in ...].
    narration: >
      format_transcript with timestamps is the foundation of subtitle
      generation — the same output format used by tools that add captions
      to videos. Without timestamps it is the plain-text transcript used
      for search indexing and summarization.

  - type: summary
    heading: "Lesson 1 Summary"
    bullets:
      - "openai-whisper: pip install + ffmpeg, local model, no API key"
      - "Five sizes: tiny/base/small/medium/large (base for development)"
      - "Output: text (str), language (str), segments (list with timestamps)"
      - "avg_logprob: confidence proxy — closer to 0 = more confident"
      - "transcribe_fn=None injection: mock returns the same dict structure"
    narration: >
      The foundation is set. Next: working with the segments list to
      extract time-stamped content and compute confidence scores.
"""

_LESSON_02 = """\
day: "072"
lesson: 2
title: "Segments and Confidence"
slides:
  - type: title
    heading: "Segments and Confidence"
    subheading: "extract_segments — timestamps and quality scores"
    narration: >
      The full transcript text is useful for reading, but the segments
      list is where the real power of Whisper lives. Each segment has
      a start and end time, text content, and a log-probability score
      that measures transcription confidence. This lesson builds
      extract_segments to convert Whisper's raw segment dicts into a
      clean, consistent format.

  - type: concept
    label: "avg_logprob"
    heading: "Understanding avg_logprob (Confidence)"
    body: >
      avg_logprob is the average log probability of the tokens in the
      segment. It is always zero or negative.
    bullets:
      - "avg_logprob = 0.0: every token perfectly predicted (rare)"
      - "avg_logprob = -0.2 to -0.5: typical clear speech"
      - "avg_logprob = -0.8 to -1.0: noisy audio or strong accent"
      - "avg_logprob < -1.0: likely silence, music, or background noise"
    narration: >
      Log probabilities come from the softmax output of the language model
      decoder. A token with probability 0.8 has log probability -0.22.
      The average across all tokens in a segment gives a quality signal.
      To convert to a 0-1 confidence score, use min(1.0, max(0.0, 1.0 + logprob)).
      At logprob = 0 this gives 1.0, at logprob = -1 this gives 0.0, and
      at logprob = -2 this clamps to 0.0. The formula maps the practical
      range of -1 to 0 linearly onto 0 to 1.

  - type: code
    label: "extract_segments"
    heading: "extract_segments Implementation"
    code: |
      def extract_segments(result):
          out = []
          for seg in result.get('segments', []):
              logprob = seg.get('avg_logprob', -1.0)
              confidence = min(1.0, max(0.0, 1.0 + logprob))
              out.append({
                  'start':      float(seg.get('start', 0.0)),
                  'end':        float(seg.get('end', 0.0)),
                  'text':       seg.get('text', '').strip(),
                  'confidence': round(confidence, 4),
              })
          return out

      # Example
      segs = extract_segments(_MOCK_RESULT)
      for s in segs:
          print(f"{s['start']:.1f}s-{s['end']:.1f}s  {s['confidence']:.2f}  {s['text']}")
      # 0.0s-2.5s  0.75  Hello world.
      # 2.5s-6.0s  0.80  Testing one two three.
    narration: >
      The output format is explicit and consistent. start and end are
      always float (not int), text is stripped of leading and trailing
      whitespace, and confidence is rounded to 4 decimal places. The
      .get() calls with defaults ensure the function handles incomplete
      segment dicts without raising KeyError — important when mocking.

  - type: concept
    label: "Use cases"
    heading: "What to Do with Segments"
    body: >
      Timestamped segments unlock several applications that plain text
      transcription cannot support.
    bullets:
      - "Subtitle generation: segments map directly to SRT/VTT format"
      - "Jump-to-moment: click a word to jump to that point in audio/video"
      - "Quality filtering: discard segments with confidence below threshold"
      - "Speaker diarization: combine with speaker model for who-said-what"
    narration: >
      SRT subtitle format is: segment index, time range (HH:MM:SS,ms), text.
      Whisper's segments are the most direct input to subtitle generators.
      Quality filtering is valuable for podcast transcripts where music
      intros produce spurious low-confidence segments. The no_speech_prob
      field (0-1) is Whisper's own estimate of whether the segment contains
      any speech — filter out segments where no_speech_prob > 0.6.

  - type: exercise
    heading: "Exercise 2: extract_segments"
    prompt: >
      Implement extract_segments(result) -> list[dict].
      For each segment in result.get('segments', []):
      - logprob = seg.get('avg_logprob', -1.0)
      - confidence = min(1.0, max(0.0, 1.0 + logprob))
      - append {start: float(...), end: float(...),
                text: seg.get('text','').strip(),
                confidence: round(confidence, 4)}
      Return the list.
    hint: >
      for seg in result.get('segments', []):
      logprob = seg.get('avg_logprob', -1.0); confidence = min(1.0, max(0.0, 1.0 + logprob));
      out.append({'start': float(seg.get('start',0.0)), ...}).
    narration: >
      extract_segments is the key processing step between raw Whisper
      output and every downstream application: subtitles, segment
      search, confidence filtering, and the AudioTranscriber class.

  - type: summary
    heading: "Lesson 2 Summary"
    bullets:
      - "avg_logprob in (-inf, 0]: 0 = perfect, -1 = poor, below -1 = likely noise"
      - "confidence = min(1.0, max(0.0, 1.0 + logprob)) maps (-1,0) onto (0,1)"
      - "extract_segments output: {start, end, text, confidence} per segment"
      - "no_speech_prob > 0.6 = likely silence or music (filter out)"
      - "Segments enable subtitles, jump-to-moment, quality filtering"
    narration: >
      Segments are extracted and confidence scores are computed. Next:
      the core transcription function with mock injection.
"""

_LESSON_03 = """\
day: "072"
lesson: 3
title: "The transcribe_audio Function"
slides:
  - type: title
    heading: "transcribe_audio"
    subheading: "Core transcription with transcribe_fn=None injection"
    narration: >
      Lessons 1 and 2 covered the output of Whisper — how to format text
      and extract segments. This lesson builds the function that produces
      that output: transcribe_audio, with the same fn=None injection pattern
      used throughout Section 5.

  - type: concept
    label: "Input types"
    heading: "Audio Input Types"
    body: >
      transcribe_audio accepts three types of audio input, each handled
      differently when calling the real whisper model.
    bullets:
      - "str or Path: file path — pass directly to model.transcribe"
      - "bytes: audio bytes — write to temp file, transcribe, delete"
      - "numpy float32 array: pre-loaded audio — pass directly"
    narration: >
      File paths are the most common case — point at an MP3, WAV, or M4A.
      Bytes input is useful when audio arrives over an HTTP upload (Day 56
      pattern: UploadFile → bytes). Numpy arrays are useful when audio has
      already been loaded and processed — for example after sample rate
      conversion. The bytes case requires a temp file because whisper calls
      ffmpeg on the file path internally. The temp file is always deleted
      after transcription to avoid disk accumulation.

  - type: code
    label: "transcribe_audio"
    heading: "transcribe_audio Implementation"
    code: |
      import os, tempfile

      def transcribe_audio(source, transcribe_fn=None, model='base'):
          if transcribe_fn is not None:
              return transcribe_fn(source)
          import whisper as _whisper
          mdl = _whisper.load_model(model)
          if isinstance(source, (bytes, bytearray)):
              with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                  f.write(source)
                  tmp = f.name
              try:
                  return mdl.transcribe(tmp)
              finally:
                  os.unlink(tmp)
          return mdl.transcribe(str(source))

      # Testing — mock ignores source, returns fixed dict
      result = transcribe_audio(b'fake audio', transcribe_fn=mock_transcribe)
      print(result['text'])       # Hello world. Testing one two three.
      print(result['language'])   # en
    narration: >
      The lazy import of whisper inside the else branch means the module
      can be imported without whisper installed — exercises use the mock
      path exclusively. The try/finally around the temp file ensures cleanup
      even if transcription raises an exception. The model is loaded fresh
      every call in this implementation — a production version would cache
      the loaded model as a class attribute to avoid the model-loading
      overhead on every call.

  - type: concept
    label: "Model caching"
    heading: "Caching the Loaded Model"
    body: >
      whisper.load_model loads model weights from disk on every call —
      several seconds of overhead. In the AudioTranscriber class, cache
      the model after the first load.
    narration: >
      This is the same lazy-initialisation pattern used for ChromaDB
      clients on Day 12 and for Stable Diffusion pipelines on Day 70.
      At construction time, set self._model_obj = None. In the generate
      or transcribe method, check if None and load if so. This means the
      first call pays the load cost and all subsequent calls are fast.
      For the AudioTranscriber class in Exercise 5, the transcribe_fn
      injection bypasses this entirely — the model is never loaded
      when testing.

  - type: exercise
    heading: "Exercise 3: transcribe_audio"
    prompt: >
      Implement transcribe_audio(source, transcribe_fn=None, model='base') -> dict.
      If transcribe_fn is not None: return transcribe_fn(source).
      Otherwise: lazy import whisper, load_model(model), then:
      - if source is bytes/bytearray: write to NamedTemporaryFile(suffix='.wav', delete=False),
        transcribe, unlink in finally.
      - else: return mdl.transcribe(str(source)).
      The checks all use transcribe_fn, so the whisper path is not tested.
    hint: >
      if transcribe_fn is not None: return transcribe_fn(source).
      import whisper as _whisper; mdl = _whisper.load_model(model).
      if isinstance(source, (bytes, bytearray)): tempfile + try/finally.
    narration: >
      transcribe_audio is the hub of the AudioTranscriber pipeline.
      All class methods ultimately call this function. Getting the
      injection pattern right means every downstream method is
      automatically testable.

  - type: summary
    heading: "Lesson 3 Summary"
    bullets:
      - "transcribe_audio: file path / bytes / ndarray → whisper result dict"
      - "bytes: write to NamedTemporaryFile, transcribe, unlink in finally"
      - "str source: mdl.transcribe(str(source))"
      - "lazy import: module loads cleanly without whisper installed"
      - "Production: cache the loaded model object to avoid reload overhead"
    narration: >
      The core transcription function is done. Next: search within a
      transcript to find relevant segments.
"""

_LESSON_04 = """\
day: "072"
lesson: 4
title: "Searching Transcripts"
slides:
  - type: title
    heading: "Searching Transcripts"
    subheading: "search_transcript — find moments in audio"
    narration: >
      A full transcript string is useful for reading, but finding a specific
      moment requires segment-level search. This lesson builds search_transcript,
      which returns segments whose text contains a query string. The result
      enables jump-to-moment navigation: tell the user exactly when a topic
      was mentioned in a recording.

  - type: how_it_works
    label: "search_transcript"
    heading: "search_transcript Design"
    body: >
      Two steps: extract segments, then filter by query string.
      Returns the matching segments in extract_segments format.
    bullets:
      - "extract_segments(result) → list of {start, end, text, confidence}"
      - "for case_insensitive: q = query.lower(); filter text.lower()"
      - "for case_sensitive: filter text directly"
      - "Returns: list of matching segment dicts (empty if no match)"
    narration: >
      search_transcript builds on extract_segments rather than the raw
      result dict, so the output is always in the clean format with
      start/end floats and stripped text. Case-insensitive is the
      default because users rarely know the exact capitalisation of a
      spoken word. The function returns a list of matching segments
      with their timestamps — the caller can format them as jump links,
      render them highlighted, or count occurrences.

  - type: code
    label: "search_transcript"
    heading: "search_transcript Implementation"
    code: |
      def search_transcript(result, query, case_sensitive=False):
          segments = extract_segments(result)
          if not case_sensitive:
              q = query.lower()
              return [s for s in segments if q in s['text'].lower()]
          return [s for s in segments if query in s['text']]

      # Example: find 'test' in the transcript
      hits = search_transcript(_MOCK_RESULT, 'test')
      for h in hits:
          print(f"Found at {h['start']:.1f}s: {h['text']!r}")
      # Found at 2.5s: 'Testing one two three.'
    narration: >
      The list comprehension is idiomatic Python for a filter operation.
      Using case-insensitive comparison by default means searching for
      'testing' finds 'Testing' and 'TESTING'. The query string is
      lowercased once outside the comprehension rather than inside — a
      small efficiency improvement for large transcripts with many segments.

  - type: concept
    label: "Applications"
    heading: "Practical Applications of Transcript Search"
    body: >
      Search-in-transcript is the core of several real-world AI features.
    bullets:
      - "Meeting notes: find all segments where a topic was discussed"
      - "Podcast indexing: jump to the exact moment a keyword appears"
      - "Call analytics: count how many calls mention a specific product"
      - "Lecture navigation: click a topic to jump to when it was explained"
    narration: >
      Combined with a video player, segment timestamps become chapter markers.
      Combined with a vector index (Day 71), segment text becomes a RAG
      knowledge base over audio content. Combined with an LLM summarizer
      (Day 7), the extracted segments can be summarized into bullet points.
      These combinations are not hypothetical — they are the basis of tools
      like Otter.ai, Descript, and YouTube's chapter feature.

  - type: exercise
    heading: "Exercise 4: search_transcript"
    prompt: >
      Implement search_transcript(result, query, case_sensitive=False) -> list[dict].
      Call extract_segments(result) to get all segments.
      If not case_sensitive: q = query.lower(), filter segments where q in s['text'].lower().
      If case_sensitive: filter segments where query in s['text'].
      Return the filtered list.
    hint: >
      segments = extract_segments(result).
      if not case_sensitive: q = query.lower(); return [s for s in segments if q in s['text'].lower()].
      else: return [s for s in segments if query in s['text']].
    narration: >
      search_transcript is two list comprehensions behind a flag. Its
      value is that it composes extract_segments (already tested) with
      a filter, producing a new clean abstraction: find moments in audio.

  - type: summary
    heading: "Lesson 4 Summary"
    bullets:
      - "search_transcript: extract_segments → filter by query"
      - "case_insensitive default: query.lower() in s['text'].lower()"
      - "Returns list of matching segment dicts in extract_segments format"
      - "Applications: meeting notes, podcast indexing, call analytics"
      - "Combines with RAG (Day 71) and summarization (Day 7)"
    narration: >
      All individual functions are complete. The final lesson assembles
      them into the AudioTranscriber class.
"""

_LESSON_05 = """\
day: "072"
lesson: 5
title: "AudioTranscriber — Full Pipeline"
slides:
  - type: title
    heading: "AudioTranscriber"
    subheading: "Full pipeline class — audio to insight"
    narration: >
      Lessons 1-4 built and tested every building block. This lesson
      assembles them into AudioTranscriber — a class that binds the
      model name and transcribe_fn at construction time and exposes
      transcribe, get_text, get_segments, and search.

  - type: how_it_works
    label: "AudioTranscriber"
    heading: "AudioTranscriber Design"
    body: >
      Four public methods, each calling transcribe once and then
      processing the result.
    bullets:
      - "AudioTranscriber(model='base', transcribe_fn=None)"
      - ".transcribe(source) -> dict — full whisper result"
      - ".get_text(source) -> str — plain transcript"
      - ".get_segments(source) -> list[dict] — timestamped segments"
      - ".search(source, query, case_sensitive=False) -> list[dict]"
    narration: >
      The pattern is exactly the same as VisionAnalyzer (Day 67),
      ImageExtractor (Day 69), ImageGenerator (Day 70), and
      ImageSearchEngine (Day 71): store the mock function at construction
      time, delegate each method to the corresponding module-level function.
      get_text calls format_transcript, get_segments calls extract_segments,
      search calls search_transcript. transcribe calls transcribe_audio.
      No logic is duplicated in the class.

  - type: code
    label: "Implementation"
    heading: "AudioTranscriber Implementation"
    code: |
      class AudioTranscriber:
          def __init__(self, model='base', transcribe_fn=None):
              self._model         = model
              self._transcribe_fn = transcribe_fn

          def transcribe(self, source):
              return transcribe_audio(source,
                                      transcribe_fn=self._transcribe_fn,
                                      model=self._model)

          def get_text(self, source):
              return format_transcript(self.transcribe(source))

          def get_segments(self, source):
              return extract_segments(self.transcribe(source))

          def search(self, source, query, case_sensitive=False):
              return search_transcript(self.transcribe(source), query,
                                       case_sensitive=case_sensitive)
    narration: >
      Every method calls self.transcribe first, then processes the result.
      This means for get_text, get_segments, and search, the audio is
      transcribed fresh each call. A production AudioTranscriber would
      cache results keyed by file hash to avoid re-transcribing the same
      file. For the course, the sequential version is correct and clear.
      Caching would be appropriate in a web app where many users might
      query the same podcast episode.

  - type: code
    label: "Usage"
    heading: "Full Pipeline Usage"
    code: |
      from audio_transcriber import AudioTranscriber

      # Testing mode — no whisper, no audio file
      mock = lambda src: {
          'text': ' The meeting started at nine AM. Budget was discussed.',
          'language': 'en',
          'segments': [
              {'id': 0, 'start': 0.0, 'end': 4.0,
               'text': ' The meeting started at nine AM.',
               'avg_logprob': -0.25, 'no_speech_prob': 0.01},
              {'id': 1, 'start': 4.0, 'end': 8.5,
               'text': ' Budget was discussed.',
               'avg_logprob': -0.30, 'no_speech_prob': 0.01},
          ],
      }
      tr = AudioTranscriber(transcribe_fn=mock)
      print(tr.get_text(b'audio'))   # The meeting started at nine AM. Budget was discussed.
      segs = tr.get_segments(b'audio')
      for s in segs:
          print(f"{s['start']:.0f}s  {s['confidence']:.2f}  {s['text']}")
      hits = tr.search(b'audio', 'budget')
      print(hits[0]['start'], hits[0]['text'])   # 4.0  Budget was discussed.
    narration: >
      The mock lambda returns a fixed dict regardless of source. Every
      method works: get_text strips the text, get_segments extracts with
      confidence scores, search finds the budget segment at 4.0 seconds.
      Swapping to real transcription means changing one line — the
      constructor argument.

  - type: exercise
    heading: "Exercise 5: AudioTranscriber Class"
    prompt: >
      Implement AudioTranscriber:
      __init__(model='base', transcribe_fn=None): store model and transcribe_fn.
      transcribe(source) -> dict: calls transcribe_audio(source, transcribe_fn=self._transcribe_fn, model=self._model).
      get_text(source) -> str: format_transcript(self.transcribe(source)).
      get_segments(source) -> list[dict]: extract_segments(self.transcribe(source)).
      search(source, query, case_sensitive=False) -> list[dict]:
        search_transcript(self.transcribe(source), query, case_sensitive).
    hint: >
      Every method calls self.transcribe(source) first, then the corresponding
      module function on the result.
    narration: >
      AudioTranscriber is the Day 72 deliverable. It packages a local
      Whisper pipeline into a single object that can transcribe any audio
      source, return plain text, extract timestamped segments, or search
      for specific spoken words — all switchable to mock mode with one
      constructor argument.

  - type: summary
    heading: "Lesson 5 Summary — Day 72 Complete"
    bullets:
      - "AudioTranscriber: model + transcribe_fn at construction"
      - ".transcribe delegates to transcribe_audio"
      - ".get_text = format_transcript(transcribe)"
      - ".get_segments = extract_segments(transcribe)"
      - ".search = search_transcript(transcribe, query)"
      - "Tomorrow (Day 73): Text-to-Speech Deep Dive (voices, SSML, podcast generator)"
    narration: >
      Day 72 is complete. You can transcribe audio files locally with
      Whisper, extract timestamped segments, score confidence, and search
      for spoken words — all with a single AudioTranscriber object that
      works in tests without any audio files or installed models.
      Tomorrow is the reverse direction: text to speech, building a
      podcast generator from written content.
"""

for i, content in enumerate([_LESSON_01, _LESSON_02, _LESSON_03,
                               _LESSON_04, _LESSON_05], start=1):
    (OUT / "lessons" / f"day_{DAY}_lesson_0{i}.yaml").write_text(content)

# ── shared helpers ────────────────────────────────────────────────────────────
_HELPER_SRC = """\
import os, tempfile

def _format_time(seconds):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f'{h:02d}:{m:02d}:{s:02d}'

def format_transcript(result, include_timestamps=False):
    if not include_timestamps:
        return result.get('text', '').strip()
    lines = []
    for seg in result.get('segments', []):
        ts = _format_time(seg.get('start', 0.0))
        lines.append(f'[{ts}] {seg.get(\"text\", \"\").strip()}')
    return '\\n'.join(lines)

def extract_segments(result):
    out = []
    for seg in result.get('segments', []):
        logprob = seg.get('avg_logprob', -1.0)
        confidence = min(1.0, max(0.0, 1.0 + logprob))
        out.append({'start': float(seg.get('start', 0.0)),
                    'end':   float(seg.get('end', 0.0)),
                    'text':  seg.get('text', '').strip(),
                    'confidence': round(confidence, 4)})
    return out

def transcribe_audio(source, transcribe_fn=None, model='base'):
    if transcribe_fn is not None:
        return transcribe_fn(source)
    import whisper as _whisper
    mdl = _whisper.load_model(model)
    if isinstance(source, (bytes, bytearray)):
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            f.write(source); tmp = f.name
        try:
            return mdl.transcribe(tmp)
        finally:
            os.unlink(tmp)
    return mdl.transcribe(str(source))

def search_transcript(result, query, case_sensitive=False):
    segments = extract_segments(result)
    if not case_sensitive:
        q = query.lower()
        return [s for s in segments if q in s['text'].lower()]
    return [s for s in segments if query in s['text']]
"""

_MOCK_SRC = """\
_MOCK_RESULT = {
    'text': ' Hello world. This is a test of speech recognition.',
    'language': 'en',
    'segments': [
        {'id': 0, 'start': 0.0, 'end': 3.2, 'text': ' Hello world.',
         'avg_logprob': -0.25, 'no_speech_prob': 0.01},
        {'id': 1, 'start': 3.2, 'end': 7.8,
         'text': ' This is a test of speech recognition.',
         'avg_logprob': -0.30, 'no_speech_prob': 0.02},
    ],
}
_mock_transcribe = lambda source: _MOCK_RESULT
"""

# ── EXERCISE 1 — format_transcript ────────────────────────────────────────────
_EX1_GIVEN = _MOCK_SRC

_EX1_STUB = """\
def _format_time(seconds: float) -> str:
    \"\"\"Convert float seconds to HH:MM:SS string (e.g. 65.0 -> '00:01:05').\"\"\"
    raise NotImplementedError


def format_transcript(result: dict, include_timestamps: bool = False) -> str:
    \"\"\"Format a whisper result as a readable string.

    Args:
        result:             Whisper result dict (text, segments, language)
        include_timestamps: If True, prefix each segment with [HH:MM:SS]
    Returns:
        Formatted transcript string
    \"\"\"
    raise NotImplementedError
"""

_EX1_SOLUTION = """\
def _format_time(seconds):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f'{h:02d}:{m:02d}:{s:02d}'


def format_transcript(result, include_timestamps=False):
    if not include_timestamps:
        return result.get('text', '').strip()
    lines = []
    for seg in result.get('segments', []):
        ts = _format_time(seg.get('start', 0.0))
        lines.append(f'[{ts}] {seg.get(\"text\", \"\").strip()}')
    return '\\n'.join(lines)
"""

_EX1_CHECKS = r"""
score, total = 0, 5
try:
    # _format_time
    assert _format_time(0.0)   == '00:00:00', f"Got {_format_time(0.0)!r}"
    assert _format_time(65.0)  == '00:01:05', f"Got {_format_time(65.0)!r}"
    assert _format_time(3661.0)== '01:01:01', f"Got {_format_time(3661.0)!r}"
    score += 1; print("✅ _format_time: 0s, 65s, 3661s correct")

    # format_transcript without timestamps
    t = format_transcript(_MOCK_RESULT)
    assert isinstance(t, str) and len(t) > 0
    assert t == t.strip(), "Should be stripped"
    score += 1; print("✅ format_transcript returns stripped string")

    # without timestamps: should not contain [
    assert '[' not in t, "Should not contain timestamps"
    score += 1; print("✅ format_transcript (no timestamps) has no brackets")

    # with timestamps: contains HH:MM:SS
    ts_text = format_transcript(_MOCK_RESULT, include_timestamps=True)
    assert '[00:00:00]' in ts_text, f"Expected [00:00:00] in {ts_text!r}"
    assert '[00:00:03]' in ts_text, f"Expected [00:00:03] in {ts_text!r}"
    score += 1; print("✅ format_transcript with timestamps contains [HH:MM:SS]")

    # each segment on its own line
    lines = ts_text.strip().split('\n')
    assert len(lines) == 2, f"Expected 2 lines, got {len(lines)}"
    score += 1; print("✅ format_transcript with timestamps: one line per segment")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX1 = nb([
    md("# Day 072 — Exercise 1: format_transcript\n\n"
       "**What you'll build:** `_format_time(seconds)` and "
       "`format_transcript(result, include_timestamps=False)` — "
       "convert a Whisper result dict to a readable string, with optional "
       "timestamped segments.\n\n"
       "**Why it matters:** The transcript format is the foundation of subtitle "
       "generation, speaker notes, and text search indexing."),
    code(_EX1_GIVEN),
    md("## Task\n\n"
       "**`_format_time(seconds) -> str`:**\n"
       "- `m, s = divmod(int(seconds), 60); h, m = divmod(m, 60)`\n"
       "- Return `f'{h:02d}:{m:02d}:{s:02d}'`\n\n"
       "**`format_transcript(result, include_timestamps=False) -> str`:**\n"
       "- Without timestamps: `return result.get('text', '').strip()`\n"
       "- With timestamps: for each segment in `result.get('segments', [])`, "
       "format `[HH:MM:SS] text`, join with `\\n`"),
    md("## Your Implementation"),
    code(_EX1_STUB),
    code(_EX1_SOLUTION),
    md("## Automated checks"),
    code(_EX1_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX1_SOLUTION + "```\n\n"
       "**Why two divmod calls?** `divmod(seconds, 60)` gives minutes + seconds. "
       "Then `divmod(minutes, 60)` gives hours + minutes. This handles any "
       "duration without manual arithmetic.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_01.ipynb", EX1)

# ── EXERCISE 2 — extract_segments ─────────────────────────────────────────────
_EX2_GIVEN = _MOCK_SRC

_EX2_STUB = """\
def extract_segments(result: dict) -> list:
    \"\"\"Extract time-stamped segments from a whisper result.

    Returns:
        list of dicts: {start: float, end: float, text: str, confidence: float}
        confidence = min(1.0, max(0.0, 1.0 + avg_logprob))
    \"\"\"
    raise NotImplementedError
"""

_EX2_SOLUTION = """\
def extract_segments(result):
    out = []
    for seg in result.get('segments', []):
        logprob = seg.get('avg_logprob', -1.0)
        confidence = min(1.0, max(0.0, 1.0 + logprob))
        out.append({
            'start':      float(seg.get('start', 0.0)),
            'end':        float(seg.get('end', 0.0)),
            'text':       seg.get('text', '').strip(),
            'confidence': round(confidence, 4),
        })
    return out
"""

_EX2_CHECKS = r"""
score, total = 0, 5
try:
    segs = extract_segments(_MOCK_RESULT)

    # returns a list
    assert isinstance(segs, list) and len(segs) == 2
    score += 1; print("✅ returns list with correct item count")

    # required keys
    assert all('start' in s and 'end' in s and 'text' in s and 'confidence' in s
               for s in segs)
    score += 1; print("✅ all required keys present")

    # start/end are floats
    assert isinstance(segs[0]['start'], float) and isinstance(segs[0]['end'], float)
    assert segs[0]['start'] == 0.0 and abs(segs[0]['end'] - 3.2) < 0.001
    score += 1; print("✅ start/end are correct floats")

    # text is stripped
    assert segs[0]['text'] == 'Hello world.', f"Got {segs[0]['text']!r}"
    score += 1; print("✅ text is stripped")

    # confidence: avg_logprob=-0.25 -> confidence=0.75
    assert abs(segs[0]['confidence'] - 0.75) < 0.001, f"Got {segs[0]['confidence']}"
    # confidence clamped: logprob=-2.0 -> 0.0
    low_seg = {'start': 0.0, 'end': 1.0, 'text': 'noise', 'avg_logprob': -2.0, 'no_speech_prob': 0.9}
    low_result = {'text': 'noise', 'language': 'en', 'segments': [low_seg]}
    low = extract_segments(low_result)
    assert low[0]['confidence'] == 0.0, f"Expected 0.0, got {low[0]['confidence']}"
    score += 1; print("✅ confidence: 1+logprob correct; clamped to 0.0 for logprob<=-1")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX2 = nb([
    md("# Day 072 — Exercise 2: extract_segments\n\n"
       "**What you'll build:** `extract_segments(result) -> list[dict]` — "
       "convert Whisper's raw segment list to clean dicts with "
       "`{start, end, text, confidence}`.\n\n"
       "**Why it matters:** Timestamped segments are the basis of subtitles, "
       "jump-to-moment navigation, quality filtering, and segment search."),
    code(_EX2_GIVEN),
    md("## Task\n\n"
       "Implement `extract_segments(result) -> list[dict]`:\n\n"
       "For each `seg` in `result.get('segments', [])`:\n"
       "- `logprob = seg.get('avg_logprob', -1.0)`\n"
       "- `confidence = min(1.0, max(0.0, 1.0 + logprob))`\n"
       "- Append `{'start': float(seg.get('start', 0.0)), 'end': float(seg.get('end', 0.0)), "
       "'text': seg.get('text', '').strip(), 'confidence': round(confidence, 4)}`"),
    md("## Your Implementation"),
    code(_EX2_STUB),
    code(_EX2_SOLUTION),
    md("## Automated checks"),
    code(_EX2_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX2_SOLUTION + "```\n\n"
       "**Why `min(1.0, max(0.0, ...))`?** avg_logprob can be anywhere in "
       "(-inf, 0]. Values below -1 produce negative confidence — we clamp "
       "to 0.0. Values very close to 0 produce values above 1 only if logprob > 0, "
       "which Whisper never produces, but clamping to 1.0 is defensive.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_02.ipynb", EX2)

# ── EXERCISE 3 — transcribe_audio ────────────────────────────────────────────
_EX3_GIVEN = "import os, tempfile\n" + _MOCK_SRC

_EX3_STUB = """\
def transcribe_audio(source, transcribe_fn=None, model: str = 'base') -> dict:
    \"\"\"Transcribe an audio source using openai-whisper.

    Args:
        source:        File path (str/Path), bytes, or numpy array
        transcribe_fn: callable(source) -> dict for testing
        model:         Whisper model size: tiny, base, small, medium, large
    Returns:
        dict with keys: text (str), language (str), segments (list)
    \"\"\"
    raise NotImplementedError
"""

_EX3_SOLUTION = """\
def transcribe_audio(source, transcribe_fn=None, model='base'):
    if transcribe_fn is not None:
        return transcribe_fn(source)
    import whisper as _whisper
    mdl = _whisper.load_model(model)
    if isinstance(source, (bytes, bytearray)):
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            f.write(source)
            tmp = f.name
        try:
            return mdl.transcribe(tmp)
        finally:
            os.unlink(tmp)
    return mdl.transcribe(str(source))
"""

_EX3_CHECKS = r"""
score, total = 0, 5
try:
    # returns dict with correct keys
    result = transcribe_audio(b'fake audio', transcribe_fn=_mock_transcribe)
    assert isinstance(result, dict)
    assert 'text' in result and 'language' in result and 'segments' in result
    score += 1; print("✅ returns dict with text/language/segments")

    # text is non-empty
    assert isinstance(result['text'], str) and len(result['text']) > 0
    score += 1; print("✅ text is non-empty string")

    # language is a string
    assert isinstance(result['language'], str)
    score += 1; print("✅ language is a string")

    # transcribe_fn called with the source
    captured = {}
    def _cap(src):
        captured['src'] = src
        return _MOCK_RESULT
    transcribe_audio(b'test bytes', transcribe_fn=_cap)
    assert captured.get('src') == b'test bytes'
    score += 1; print("✅ transcribe_fn receives the source argument")

    # path source also works via mock
    result2 = transcribe_audio('fake/path.mp3', transcribe_fn=_mock_transcribe)
    assert result2['language'] == 'en'
    score += 1; print("✅ string path source forwarded correctly")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX3 = nb([
    md("# Day 072 — Exercise 3: transcribe_audio\n\n"
       "**What you'll build:** `transcribe_audio(source, transcribe_fn=None, model='base') -> dict` — "
       "the core transcription function with `transcribe_fn=None` mock injection.\n\n"
       "**Why it matters:** This is the hub of the AudioTranscriber pipeline. "
       "All class methods call it. Getting the injection pattern right makes "
       "every downstream method automatically testable."),
    code(_EX3_GIVEN),
    md("## Task\n\n"
       "Implement `transcribe_audio`:\n\n"
       "1. If `transcribe_fn is not None`: `return transcribe_fn(source)`\n"
       "2. `import whisper as _whisper; mdl = _whisper.load_model(model)`\n"
       "3. If `isinstance(source, (bytes, bytearray))`: write to "
       "`NamedTemporaryFile(suffix='.wav', delete=False)`, call `mdl.transcribe(tmp)` "
       "in a try/finally that unlinks the temp file\n"
       "4. Else: `return mdl.transcribe(str(source))`\n\n"
       "The checks all use `transcribe_fn`, so the whisper path is not tested here."),
    md("## Your Implementation"),
    code(_EX3_STUB),
    code(_EX3_SOLUTION),
    md("## Automated checks"),
    code(_EX3_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX3_SOLUTION + "```\n\n"
       "**Why `try/finally` for the temp file?** If `mdl.transcribe` raises an "
       "exception (bad audio, model error), the temp file would be left on disk "
       "without the `finally`. Always clean up temporary files regardless of "
       "whether the operation succeeds.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_03.ipynb", EX3)

# ── EXERCISE 4 — search_transcript ────────────────────────────────────────────
_EX4_GIVEN = _HELPER_SRC + "\n" + _MOCK_SRC

_EX4_STUB = """\
def search_transcript(result: dict, query: str,
                      case_sensitive: bool = False) -> list:
    \"\"\"Find segments whose text contains the query string.

    Args:
        result:         Whisper result dict
        query:          Search string
        case_sensitive: Default False (case-insensitive comparison)
    Returns:
        list of matching segment dicts in extract_segments format
    \"\"\"
    raise NotImplementedError
"""

_EX4_SOLUTION = """\
def search_transcript(result, query, case_sensitive=False):
    segments = extract_segments(result)
    if not case_sensitive:
        q = query.lower()
        return [s for s in segments if q in s['text'].lower()]
    return [s for s in segments if query in s['text']]
"""

_EX4_CHECKS = r"""
score, total = 0, 5
try:
    # case-insensitive hit
    hits = search_transcript(_MOCK_RESULT, 'hello')
    assert len(hits) == 1 and hits[0]['text'] == 'Hello world.'
    score += 1; print("✅ case-insensitive search finds 'hello' in 'Hello world.'")

    # case-insensitive miss
    no_hits = search_transcript(_MOCK_RESULT, 'elephant')
    assert no_hits == []
    score += 1; print("✅ no match returns empty list")

    # case-sensitive hit
    cs_hits = search_transcript(_MOCK_RESULT, 'Hello', case_sensitive=True)
    assert len(cs_hits) == 1
    score += 1; print("✅ case-sensitive match works")

    # case-sensitive miss (wrong case)
    cs_miss = search_transcript(_MOCK_RESULT, 'hello', case_sensitive=True)
    assert cs_miss == [], f"Expected [], got {cs_miss}"
    score += 1; print("✅ case-sensitive: wrong case produces no match")

    # result has correct format (from extract_segments)
    hits2 = search_transcript(_MOCK_RESULT, 'test')
    assert len(hits2) == 1
    assert all(k in hits2[0] for k in ('start', 'end', 'text', 'confidence'))
    assert hits2[0]['start'] == 3.2
    score += 1; print("✅ results in extract_segments format with correct timestamps")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX4 = nb([
    md("# Day 072 — Exercise 4: search_transcript\n\n"
       "**What you'll build:** `search_transcript(result, query, case_sensitive=False) -> list[dict]` — "
       "find segments containing a query string, enabling jump-to-moment navigation.\n\n"
       "**Why it matters:** Segment-level search is the core of podcast indexing, "
       "meeting search, and lecture navigation. Finding the exact timestamp "
       "when a topic was mentioned is not possible with plain text transcription."),
    code(_EX4_GIVEN),
    md("## Task\n\n"
       "Implement `search_transcript`:\n\n"
       "1. `segments = extract_segments(result)`\n"
       "2. If `not case_sensitive`: `q = query.lower()`, filter `[s for s in segments if q in s['text'].lower()]`\n"
       "3. Else: filter `[s for s in segments if query in s['text']]`"),
    md("## Your Implementation"),
    code(_EX4_STUB),
    code(_EX4_SOLUTION),
    md("## Automated checks"),
    code(_EX4_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX4_SOLUTION + "```\n\n"
       "**Why call `extract_segments` rather than filtering `result['segments']`?** "
       "Two reasons: (1) the returned dicts have consistent, clean keys (stripped text, "
       "float start/end, confidence); (2) if `extract_segments` logic changes later, "
       "`search_transcript` inherits the change automatically.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_04.ipynb", EX4)

# ── EXERCISE 5 — AudioTranscriber ────────────────────────────────────────────
_EX5_GIVEN = _HELPER_SRC + "\n" + _MOCK_SRC

_EX5_STUB = """\
class AudioTranscriber:
    \"\"\"Transcribe audio using openai-whisper with mock injection support.\"\"\"

    def __init__(self, model: str = 'base',
                 transcribe_fn=None) -> None:
        raise NotImplementedError

    def transcribe(self, source) -> dict:
        \"\"\"Transcribe audio. Returns full whisper result dict.\"\"\"
        raise NotImplementedError

    def get_text(self, source) -> str:
        \"\"\"Return plain transcript text (stripped).\"\"\"
        raise NotImplementedError

    def get_segments(self, source) -> list:
        \"\"\"Return list of time-stamped segment dicts.\"\"\"
        raise NotImplementedError

    def search(self, source, query: str,
               case_sensitive: bool = False) -> list:
        \"\"\"Search for a query in the transcript segments.\"\"\"
        raise NotImplementedError
"""

_EX5_SOLUTION = """\
class AudioTranscriber:
    def __init__(self, model='base', transcribe_fn=None):
        self._model         = model
        self._transcribe_fn = transcribe_fn

    def transcribe(self, source):
        return transcribe_audio(source,
                                transcribe_fn=self._transcribe_fn,
                                model=self._model)

    def get_text(self, source):
        return format_transcript(self.transcribe(source))

    def get_segments(self, source):
        return extract_segments(self.transcribe(source))

    def search(self, source, query, case_sensitive=False):
        return search_transcript(self.transcribe(source), query,
                                 case_sensitive=case_sensitive)
"""

_EX5_CHECKS = r"""
score, total = 0, 5
try:
    tr = AudioTranscriber(transcribe_fn=_mock_transcribe)

    # transcribe returns the mock result dict
    result = tr.transcribe(b'audio bytes')
    assert isinstance(result, dict) and 'text' in result and 'segments' in result
    score += 1; print("✅ transcribe returns whisper result dict")

    # get_text returns stripped string
    text = tr.get_text(b'audio bytes')
    assert isinstance(text, str) and text == text.strip() and len(text) > 0
    score += 1; print("✅ get_text returns stripped transcript string")

    # get_segments returns list of dicts with required keys
    segs = tr.get_segments(b'audio bytes')
    assert isinstance(segs, list) and len(segs) == 2
    assert all('start' in s and 'confidence' in s for s in segs)
    score += 1; print("✅ get_segments returns list of segment dicts")

    # search finds matches
    hits = tr.search(b'audio bytes', 'hello')
    assert len(hits) == 1 and hits[0]['text'] == 'Hello world.'
    score += 1; print("✅ search finds matching segments")

    # transcribe_fn is stored and reused
    calls = [0]
    def _count(src):
        calls[0] += 1
        return _MOCK_RESULT
    tr2 = AudioTranscriber(transcribe_fn=_count)
    tr2.get_text(b'a'); tr2.get_segments(b'b')
    assert calls[0] == 2, f"Expected 2 calls, got {calls[0]}"
    score += 1; print("✅ transcribe_fn called once per method call")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX5 = nb([
    md("# Day 072 — Exercise 5: AudioTranscriber Class\n\n"
       "**What you'll build:** `AudioTranscriber` — a class that wraps the "
       "full Whisper pipeline with `transcribe`, `get_text`, `get_segments`, "
       "and `search` methods.\n\n"
       "**Why it matters:** The class is the deliverable that slots into any "
       "app. One constructor call to configure, then call `.get_text` for "
       "plain transcription or `.search` for moment-finding."),
    code(_EX5_GIVEN),
    md("## Task\n\nImplement `AudioTranscriber`:\n\n"
       "- `__init__(model='base', transcribe_fn=None)`: store both as instance attributes\n"
       "- `transcribe(source) -> dict`: `transcribe_audio(source, transcribe_fn=self._transcribe_fn, model=self._model)`\n"
       "- `get_text(source) -> str`: `format_transcript(self.transcribe(source))`\n"
       "- `get_segments(source) -> list[dict]`: `extract_segments(self.transcribe(source))`\n"
       "- `search(source, query, case_sensitive=False) -> list[dict]`: "
       "`search_transcript(self.transcribe(source), query, case_sensitive)`"),
    md("## Your Implementation"),
    code(_EX5_STUB),
    code(_EX5_SOLUTION),
    md("## Automated checks"),
    code(_EX5_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX5_SOLUTION + "```\n\n"
       "**Why does each method call `self.transcribe` rather than caching "
       "the result?** In exercises, the source is always `b'fake audio'` — "
       "the mock is instant so re-transcribing is fine. In production, you "
       "would cache the result keyed by `hash(source)` to avoid loading the "
       "model twice for the same file.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_05.ipynb", EX5)

# ── PROJECT NOTEBOOK ──────────────────────────────────────────────────────────
PROJECT = nb([
    md("# Day 072 — Project: Audio Transcriber\n\n"
       "## What You're Building\n\n"
       "`audio_transcriber.py` — an `AudioTranscriber` class for local speech-to-text.\n\n"
       "**Deliverable:** A class and utility functions that transcribe audio files "
       "using the openai-whisper local package, extract timestamped segments, "
       "compute confidence scores, and search for spoken content.\n\n"
       "## Setup\n\n"
       "```bash\n"
       "pip install openai-whisper\n"
       "brew install ffmpeg          # macOS\n"
       "ollama pull llama3.2         # not needed for this day\n"
       "# Download the base model (74MB):\n"
       "python -c \"import whisper; whisper.load_model('base')\"\n"
       "```\n\n"
       "## Design\n\n"
       "```\n"
       "_format_time(seconds) -> str\n"
       "format_transcript(result, include_timestamps=False) -> str\n"
       "extract_segments(result) -> list[{start, end, text, confidence}]\n"
       "transcribe_audio(source, transcribe_fn=None, model='base') -> dict\n"
       "search_transcript(result, query, case_sensitive=False) -> list[dict]\n"
       "AudioTranscriber(model='base', transcribe_fn=None)\n"
       "  .transcribe(source) -> dict\n"
       "  .get_text(source) -> str\n"
       "  .get_segments(source) -> list[dict]\n"
       "  .search(source, query) -> list[dict]\n"
       "```"),
    code("# Your implementation here — build AudioTranscriber and write audio_transcriber.py\n"),
])
save(OUT / "project" / "project.ipynb", PROJECT)

# ── SOLUTION NOTEBOOK ─────────────────────────────────────────────────────────
_SOL_CELL1 = (
    f"_TRANSCRIBER_SRC = {repr(_TRANSCRIBER_SRC)}\n"
    "from pathlib import Path\n"
    "Path('audio_transcriber.py').write_text(_TRANSCRIBER_SRC, encoding='utf-8')\n"
    "print('audio_transcriber.py written.')"
)

_SOL_CELL2 = """\
from audio_transcriber import (
    _format_time, format_transcript, extract_segments,
    transcribe_audio, search_transcript, AudioTranscriber,
)

_MOCK = {
    'text': ' Hello world. Testing one two three.',
    'language': 'en',
    'segments': [
        {'id': 0, 'start': 0.0, 'end': 2.5, 'text': ' Hello world.',
         'avg_logprob': -0.25, 'no_speech_prob': 0.01},
        {'id': 1, 'start': 2.5, 'end': 6.0, 'text': ' Testing one two three.',
         'avg_logprob': -0.20, 'no_speech_prob': 0.01},
    ],
}
_mock_fn = lambda src: _MOCK

# 1. _format_time
assert _format_time(0.0)   == '00:00:00'
assert _format_time(65.0)  == '00:01:05'
assert _format_time(3661.0)== '01:01:01'
print("\\u2705 _format_time correct")

# 2. format_transcript
t = format_transcript(_MOCK)
assert t == 'Hello world. Testing one two three.'
ts = format_transcript(_MOCK, include_timestamps=True)
assert '[00:00:00]' in ts and '[00:00:02]' in ts
print("\\u2705 format_transcript correct")

# 3. extract_segments
segs = extract_segments(_MOCK)
assert len(segs) == 2
assert segs[0] == {'start': 0.0, 'end': 2.5, 'text': 'Hello world.', 'confidence': 0.75}
print("\\u2705 extract_segments correct")

# 4. transcribe_audio
result = transcribe_audio(b'fake', transcribe_fn=_mock_fn)
assert result['language'] == 'en' and len(result['text']) > 0
print("\\u2705 transcribe_audio correct")

# 5. search_transcript
hits = search_transcript(_MOCK, 'hello')
assert len(hits) == 1 and hits[0]['start'] == 0.0
no_hits = search_transcript(_MOCK, 'HELLO', case_sensitive=True)
assert no_hits == []
print("\\u2705 search_transcript correct")

# 6. AudioTranscriber
tr = AudioTranscriber(transcribe_fn=_mock_fn)
assert tr.get_text(b'a') == 'Hello world. Testing one two three.'
s = tr.get_segments(b'a')
assert len(s) == 2 and s[0]['confidence'] == 0.75
h = tr.search(b'a', 'testing')
assert len(h) == 1 and abs(h[0]['start'] - 2.5) < 0.001
print("\\u2705 AudioTranscriber correct")

print("\\nAudio Transcriber complete!")
"""

SOLUTION = nb([
    md("# Day 072 — Solution: Audio Transcriber"),
    code(_SOL_CELL1),
    code(_SOL_CELL2),
])
save(OUT / "project" / "solution" / "solution.ipynb", SOLUTION)
(OUT / "project" / "solution" / "audio_transcriber.py").write_text(_TRANSCRIBER_SRC)

print(f"Day {DAY} notebooks written to {OUT}")
print("  lessons/    day_072_lesson_01.yaml – lesson_05.yaml")
print("  exercises/  exercise_01 – exercise_05")
print("  project/    project.ipynb")
print("  project/solution/  solution.ipynb + audio_transcriber.py")
