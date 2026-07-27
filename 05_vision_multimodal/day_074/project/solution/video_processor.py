"""video_processor.py — Day 074: Video Basics.

Process video files in Python using OpenCV and FFmpeg.

Setup:
    pip install opencv-python-headless
    brew install ffmpeg   # macOS

Usage:
    from video_processor import VideoProcessor

    # Testing — no video file or FFmpeg needed
    import numpy as np
    def _mock_info(source):
        return {'fps': 30.0, 'frame_count': 10, 'width': 64, 'height': 64, 'duration_sec': 0.333}
    def _mock_capture(source):
        return [np.zeros((64, 64, 3), dtype=np.uint8) for _ in range(10)]

    proc = VideoProcessor(info_fn=_mock_info, capture_fn=_mock_capture)
    meta  = proc.info('video.mp4')
    frames = proc.frames('video.mp4', step=2, max_frames=4)
    print(meta['fps'], len(frames))   # 30.0  5 (10 frames step=2)
"""
import subprocess
from pathlib import Path
from typing import Callable, Optional


def get_video_info(source, info_fn: Optional[Callable] = None) -> dict:
    """Return video metadata: fps, frame_count, width, height, duration_sec.

    Args:
        source:  path to video file (str or Path)
        info_fn: callable(source) -> dict for testing (no OpenCV needed)
    """
    if info_fn is not None:
        return info_fn(source)
    import cv2
    cap = cv2.VideoCapture(str(source))
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {source}")
    fps         = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width       = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height      = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    duration = round(frame_count / fps, 3) if fps > 0 else 0.0
    return {
        "fps":         fps,
        "frame_count": frame_count,
        "width":       width,
        "height":      height,
        "duration_sec": duration,
    }


def extract_frames(source, step: int = 1, max_frames: Optional[int] = None,
                   capture_fn: Optional[Callable] = None) -> list:
    """Extract frames from a video as a list of numpy arrays (BGR, uint8).

    Args:
        source:     path to video file
        step:       take every nth frame (1 = every frame, 2 = every other, ...)
        max_frames: maximum frames to return (None = all)
        capture_fn: callable(source) -> list[np.ndarray] for testing
    Returns:
        list of numpy arrays, shape (H, W, 3), dtype uint8, BGR
    """
    if capture_fn is not None:
        all_frames = capture_fn(source)
        stepped    = all_frames[::step]
        return stepped[:max_frames] if max_frames is not None else stepped
    import cv2
    cap    = cv2.VideoCapture(str(source))
    frames = []
    idx    = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if idx % step == 0:
            frames.append(frame)
            if max_frames is not None and len(frames) >= max_frames:
                break
        idx += 1
    cap.release()
    return frames


def frames_to_video(frames: list, output_path,
                    fps: float = 30.0, fourcc: str = "mp4v",
                    writer_fn: Optional[Callable] = None):
    """Write a list of frames to a video file.

    Args:
        frames:      list of numpy arrays (H, W, 3) BGR uint8
        output_path: destination file path
        fps:         output frame rate
        fourcc:      four-character codec code (mp4v for MP4, XVID for AVI)
        writer_fn:   callable(frames, output_path, fps) -> Path for testing
    Returns:
        Path to the written video file
    """
    if writer_fn is not None:
        return writer_fn(frames, output_path, fps)
    import cv2
    frames = list(frames)
    if not frames:
        raise ValueError("frames list is empty")
    h, w         = frames[0].shape[:2]
    fourcc_code  = cv2.VideoWriter_fourcc(*fourcc)
    out_path     = Path(output_path)
    writer       = cv2.VideoWriter(str(out_path), fourcc_code, fps, (w, h))
    for frame in frames:
        writer.write(frame)
    writer.release()
    return out_path


def run_ffmpeg(args: list, ffmpeg_fn: Optional[Callable] = None) -> dict:
    """Run an FFmpeg command and return the result dict.

    Args:
        args:      FFmpeg arguments (everything after 'ffmpeg -y')
        ffmpeg_fn: callable(args) -> dict for testing (no FFmpeg binary needed)
    Returns:
        {returncode: int, stdout: str, stderr: str}
    """
    if ffmpeg_fn is not None:
        return ffmpeg_fn(args)
    result = subprocess.run(
        ["ffmpeg", "-y"] + list(args),
        capture_output=True, text=True,
    )
    return {
        "returncode": result.returncode,
        "stdout":     result.stdout,
        "stderr":     result.stderr,
    }


class VideoProcessor:
    """Process video files using OpenCV and FFmpeg.

    Inject fn parameters for testing without video files or FFmpeg::

        proc = VideoProcessor(
            info_fn=lambda src: {...},
            capture_fn=lambda src: [frame1, frame2, ...],
        )
    """

    def __init__(self, info_fn: Optional[Callable] = None,
                 capture_fn: Optional[Callable] = None,
                 writer_fn: Optional[Callable] = None,
                 ffmpeg_fn: Optional[Callable] = None) -> None:
        self._info_fn    = info_fn
        self._capture_fn = capture_fn
        self._writer_fn  = writer_fn
        self._ffmpeg_fn  = ffmpeg_fn

    def info(self, source) -> dict:
        """Return video metadata dict."""
        return get_video_info(source, info_fn=self._info_fn)

    def frames(self, source, step: int = 1,
                max_frames: Optional[int] = None) -> list:
        """Extract frames as a list of numpy arrays."""
        return extract_frames(source, step=step, max_frames=max_frames,
                              capture_fn=self._capture_fn)

    def to_video(self, frames: list, output_path,
                 fps: float = 30.0, fourcc: str = "mp4v"):
        """Write frames to a video file. Returns Path."""
        return frames_to_video(frames, output_path, fps=fps,
                               fourcc=fourcc, writer_fn=self._writer_fn)

    def run_ffmpeg(self, args: list) -> dict:
        """Run an FFmpeg command. Returns result dict."""
        return run_ffmpeg(args, ffmpeg_fn=self._ffmpeg_fn)
