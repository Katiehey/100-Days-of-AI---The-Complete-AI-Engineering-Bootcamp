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
    return "\n".join(lines)


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
