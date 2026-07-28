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
