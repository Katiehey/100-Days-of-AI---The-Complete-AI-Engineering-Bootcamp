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
    safe_text = text.replace("'", r"\'").replace(':', r'\:')
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
