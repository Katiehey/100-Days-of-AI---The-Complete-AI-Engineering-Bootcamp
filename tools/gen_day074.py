#!/usr/bin/env python3
"""gen_day074.py — generate Day 074: Video Basics."""
from pathlib import Path
import json

ROOT    = Path(__file__).parent.parent
DAY     = "074"
SECTION = "05_vision_multimodal"
OUT     = ROOT / SECTION / f"day_{DAY}"

(OUT / "exercises").mkdir(parents=True, exist_ok=True)
(OUT / "lessons").mkdir(parents=True, exist_ok=True)
(OUT / "project" / "solution").mkdir(parents=True, exist_ok=True)

# ── deliverable: video_processor.py ──────────────────────────────────────────
_VIDEO_SRC = '''\
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
day: "074"
lesson: 1
title: "Video Fundamentals and OpenCV VideoCapture"
slides:
  - type: title
    heading: "Video Basics"
    subheading: "Day 74 — frames, FFmpeg, VideoProcessor"
    narration: >
      Day 74 opens Section 5's final module before the capstone. Video is the
      richest media format: it combines images, audio, and time. Today you will
      process video files in pure Python: extract metadata, pull frames as
      numpy arrays, write new video files, and call FFmpeg from code. All
      exercises are offline — no video file needed.

  - type: concept
    label: "Video structure"
    heading: "What Is a Video File?"
    body: >
      A video container (MP4, AVI, MKV) stores video frames, an audio track,
      and metadata. Inside, frames are stored as compressed images in a codec
      format (H.264, HEVC, VP9).
    bullets:
      - "Frame: one still image — a numpy array (H, W, 3), dtype uint8"
      - "FPS: frames per second — how many frames cover one second of playback"
      - "Resolution: width x height in pixels (e.g. 1920x1080)"
      - "Codec: compression algorithm — H.264 for web, MJPG for editing"
      - "Duration = frame_count / fps (in seconds)"
    narration: >
      At the lowest level, a video is just a list of images played quickly
      enough to create the illusion of motion. The threshold is roughly 24 FPS
      (cinema standard) or 30 FPS (broadcast TV). Each image is stored as a
      numpy array with three colour channels. OpenCV uses BGR channel order
      (Blue-Green-Red) rather than the RGB you get from PIL or matplotlib. This
      is a historical quirk from early machine vision hardware. Internally,
      frames are compressed frame-to-frame using I-frames (full images) and
      P-frames (only the differences from the previous frame). Codecs like
      H.264 achieve 50x or more compression compared to raw pixel data.

  - type: concept
    label: "BGR order"
    heading: "OpenCV BGR vs PIL RGB"
    body: >
      OpenCV reads and writes frames in BGR (Blue-Green-Red) channel order.
      PIL and matplotlib use RGB. Convert between them for display or PIL ops.
    bullets:
      - "cv2.VideoCapture reads frames as (H, W, 3) uint8 BGR numpy arrays"
      - "BGR to RGB: frame_rgb = frame[:, :, ::-1]"
      - "BGR to PIL: Image.fromarray(frame[:, :, ::-1])"
      - "BGR to RGB with OpenCV: cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)"
      - "Saving via PIL/matplotlib: convert to RGB first"
    narration: >
      When you do frame[:, :, ::-1] you are reversing the third axis — swapping
      channel 0 (blue) with channel 2 (red) while keeping channel 1 (green)
      unchanged. This is a zero-copy slice operation in numpy — no data is
      copied. The most common bug when mixing OpenCV and matplotlib is
      forgetting this conversion: matplotlib assumes RGB, so a BGR frame
      rendered with imshow will have the red and blue channels swapped.
      In this course we save frames as files rather than displaying them, so
      this conversion is needed when saving to PNG via PIL.

  - type: code
    label: "VideoCapture API"
    heading: "OpenCV VideoCapture — Metadata"
    code: |
      import cv2

      # Open a video file
      cap = cv2.VideoCapture('input.mp4')

      if not cap.isOpened():
          raise ValueError('Cannot open video')

      # Read metadata properties
      fps         = cap.get(cv2.CAP_PROP_FPS)
      frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
      width       = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
      height      = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
      duration    = frame_count / fps if fps > 0 else 0.0

      print(f'{fps} fps  {width}x{height}  {frame_count} frames  {duration:.2f}s')

      cap.release()   # always release the capture object
    narration: >
      VideoCapture is the entry point for all video reading in OpenCV.
      The .get() method reads properties identified by integer constants
      starting with CAP_PROP. The important ones are FPS, FRAME_COUNT,
      FRAME_WIDTH, and FRAME_HEIGHT. Frame count multiplied by width
      multiplied by height multiplied by 3 (channels) multiplied by 1 byte
      gives the raw uncompressed size — dividing by the actual file size tells
      you the compression ratio. Always call cap.release() to close the file
      handle and free resources, even if an exception might occur — use
      try/finally or a context manager wrapper.

  - type: exercise
    heading: "Exercise 1: get_video_info"
    prompt: >
      Implement get_video_info(source, info_fn=None) -> dict.
      If info_fn is not None: return info_fn(source).
      Otherwise (lazy import cv2): open VideoCapture(str(source)), check isOpened(),
      read fps, frame_count (int), width (int), height (int), release cap,
      compute duration_sec = round(frame_count / fps, 3) if fps > 0 else 0.0.
      Return dict with keys fps, frame_count, width, height, duration_sec.
    hint: >
      if info_fn is not None: return info_fn(source).
      import cv2; cap = cv2.VideoCapture(str(source)).
      fps = cap.get(cv2.CAP_PROP_FPS); frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)).
      width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)).
      cap.release(). duration = round(frame_count/fps,3) if fps>0 else 0.0. return {...}.
    narration: >
      get_video_info is the foundation of the VideoProcessor. All higher-level
      operations that need FPS or resolution call this first.

  - type: summary
    heading: "Lesson 1 Summary"
    bullets:
      - "Video = frames (numpy arrays) + audio track + metadata in a container"
      - "Frame shape: (H, W, 3) uint8, BGR channel order"
      - "BGR to RGB: frame[:, :, ::-1] — numpy channel-reverse, zero-copy"
      - "VideoCapture: .get(CAP_PROP_FPS/FRAME_COUNT/FRAME_WIDTH/FRAME_HEIGHT)"
      - "Always cap.release() to close file handle"
      - "info_fn=None injection: mock returns metadata dict, no OpenCV needed"
    narration: >
      The video metadata foundation is laid. Next: extracting the actual
      frame pixel data.
"""

_LESSON_02 = """\
day: "074"
lesson: 2
title: "Frame Extraction"
slides:
  - type: title
    heading: "Frame Extraction"
    subheading: "extract_frames — step, max_frames, numpy arrays"
    narration: >
      Extracting frames is the most common video processing operation. A one-
      hour video at 30 FPS contains 108,000 frames. Extracting every frame
      fills gigabytes of RAM. Step and max_frames parameters let you sample
      efficiently — taking every 10th frame for a timelapse, or capping at 100
      frames for a quick preview.

  - type: how_it_works
    label: "Frame loop"
    heading: "The cap.read() Frame Loop"
    body: >
      cap.read() returns (ret, frame) — ret is False when the video ends
      or a read error occurs. The standard frame loop checks ret first.
    bullets:
      - "cap.read() -> (ret: bool, frame: np.ndarray | None)"
      - "ret=False means end of file or error — stop the loop"
      - "frame is (H, W, 3) uint8 BGR numpy array when ret=True"
      - "step: only keep frames where idx % step == 0"
      - "max_frames: break early when enough frames collected"
    narration: >
      The two-return-value pattern (ret, frame) is OpenCV's way of combining
      the end-of-stream signal with the frame data into a single call. The
      name ret is short for return code — True means success, False means
      the video has ended or the source is unavailable. The frame when ret is
      False is typically None, so always check ret before using the frame.
      The step parameter is applied with the modulo operator: idx % step == 0
      selects frames at indices 0, step, 2*step, and so on. Combined with
      max_frames, you get a streaming take(max) + stride sampler.

  - type: code
    label: "extract_frames"
    heading: "extract_frames Implementation"
    code: |
      import cv2

      def extract_frames(source, step=1, max_frames=None, capture_fn=None):
          if capture_fn is not None:
              all_frames = capture_fn(source)
              stepped    = all_frames[::step]
              return stepped[:max_frames] if max_frames is not None else stepped
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

      # Testing with mock
      import numpy as np
      mock_frames = [np.zeros((64,64,3), dtype=np.uint8)] * 10
      frames = extract_frames('video.mp4', step=2, max_frames=3,
                               capture_fn=lambda src: mock_frames)
      print(len(frames))   # 3 (10 frames // step=2 = 5, capped at max=3)
    narration: >
      The mock path slices the full frame list using Python list slicing:
      all_frames[::step] produces every nth element, then [:max_frames]
      caps the result. The real path applies step during reading with
      the modulo check, which is more memory-efficient for large videos
      because intermediate frames are never stored in memory. Both paths
      return the same result for the same video and parameters.

  - type: concept
    label: "Frame shapes"
    heading: "Working With Frame Numpy Arrays"
    body: >
      Each frame is a numpy array. PIL, matplotlib, and numpy operations all
      apply directly. Save frames as PNG with PIL to inspect them without
      a display.
    bullets:
      - "frame.shape -> (height, width, 3) — note: height first, width second"
      - "frame.dtype -> uint8 (values 0-255 per channel)"
      - "PIL from BGR frame: Image.fromarray(frame[:, :, ::-1])"
      - "Save frame as PNG: Image.fromarray(frame[:,:,::-1]).save('frame.png')"
      - "Frame from PIL: np.array(pil_img)[:, :, ::-1] (RGB to BGR)"
    narration: >
      The height-first, width-second shape order in numpy conflicts with
      OpenCV's (width, height) pair in VideoWriter — this is the most common
      source of shape errors. Always extract h, w = frame.shape[:2] from the
      actual frame array and pass (w, h) to VideoWriter. The [:2] slice drops
      the channel count, leaving just the spatial dimensions. When you see a
      weirdly colored image in saved output, check the BGR/RGB conversion first.

  - type: exercise
    heading: "Exercise 2: extract_frames"
    prompt: >
      Implement extract_frames(source, step=1, max_frames=None, capture_fn=None) -> list.
      If capture_fn is not None: all_frames = capture_fn(source); stepped = all_frames[::step];
      return stepped[:max_frames] if max_frames is not None else stepped.
      Otherwise (lazy import cv2): VideoCapture loop with idx counter,
      keep frames where idx % step == 0, break when max_frames reached or ret=False,
      cap.release(), return frames list.
    hint: >
      Mock path: all_frames = capture_fn(source); stepped = all_frames[::step];
      return stepped[:max_frames] if max_frames else stepped.
      Real path: import cv2; cap = VideoCapture; idx=0; while True: ret,frame=cap.read();
      if not ret: break; if idx%step==0: frames.append(frame); if max_frames and len>=max_frames: break;
      idx+=1; cap.release(); return frames.
    narration: >
      extract_frames is the workhorse of any video analysis pipeline — whether
      for frame-by-frame vision analysis, generating thumbnails, or building
      training data.

  - type: summary
    heading: "Lesson 2 Summary"
    bullets:
      - "cap.read() -> (ret, frame): check ret before using frame"
      - "step parameter: idx % step == 0 selects every nth frame"
      - "max_frames: break early to avoid reading the whole file"
      - "frame.shape = (H, W, 3) — height first, width second"
      - "BGR to PIL: Image.fromarray(frame[:, :, ::-1])"
      - "Mock path: slice capture_fn result with [::step][:max_frames]"
    narration: >
      Frame extraction is complete. Next: writing frames back to a video file.
"""

_LESSON_03 = """\
day: "074"
lesson: 3
title: "Writing Video with VideoWriter"
slides:
  - type: title
    heading: "Writing Video Files"
    subheading: "frames_to_video — VideoWriter, fourcc, fps"
    narration: >
      The reverse of extraction: taking a list of numpy frame arrays and
      writing them to a video file. VideoWriter requires three parameters to
      match the frames exactly: codec, fps, and frame size. Getting any one
      wrong produces a corrupt or empty file.

  - type: concept
    label: "VideoWriter"
    heading: "VideoWriter and fourcc Codes"
    body: >
      VideoWriter encodes frames into a video file. The fourcc parameter
      selects the codec. The frame size must match the actual frame dimensions.
    bullets:
      - "fourcc = four-character code identifying the codec"
      - "mp4v: MPEG-4 video, used in .mp4 files — good default"
      - "XVID: Xvid codec, used in .avi files"
      - "MJPG: Motion JPEG, each frame a JPEG — large but compatible"
      - "cv2.VideoWriter_fourcc(*'mp4v') converts the string to an integer code"
    narration: >
      The fourcc code was introduced in the early days of video on Windows to
      label codecs in AVI files. It is literally four ASCII characters packed
      into a 32-bit integer. The asterisk unpacking (*'mp4v') expands the
      string into four character arguments: cv2.VideoWriter_fourcc('m', 'p',
      '4', 'v'). The codec must match the output file extension: mp4v for
      .mp4 files, XVID for .avi. If the codec is unavailable on the system,
      OpenCV silently falls back or produces an empty file. MJPG is the most
      compatible fallback since it requires no external codec.

  - type: code
    label: "VideoWriter usage"
    heading: "VideoWriter: Frame Size and Write Loop"
    code: |
      import cv2
      from pathlib import Path

      def frames_to_video(frames, output_path, fps=30.0,
                          fourcc='mp4v', writer_fn=None):
          if writer_fn is not None:
              return writer_fn(frames, output_path, fps)
          frames       = list(frames)
          if not frames:
              raise ValueError('frames list is empty')
          h, w         = frames[0].shape[:2]   # height, width from frame
          fourcc_code  = cv2.VideoWriter_fourcc(*fourcc)
          out_path     = Path(output_path)
          writer       = cv2.VideoWriter(str(out_path), fourcc_code, fps, (w, h))
          for frame in frames:
              writer.write(frame)
          writer.release()
          return out_path

      # Key: VideoWriter takes (width, height), NOT (height, width)
      # h, w = frame.shape[:2]  -> shape is (H, W, channels), so [:2] = (H, W)
      # (w, h)                  -> VideoWriter wants (W, H) = (width, height)
    narration: >
      The h, w = frames[0].shape[:2] line unpacks height and width from the
      first frame's shape tuple — numpy shape is always height-first, which
      is the opposite of how VideoWriter expects them. Passing (w, h) to
      VideoWriter gives (width, height) in OpenCV's expected order. If you
      accidentally pass (h, w) (height, width), OpenCV will write a transposed
      video — frames will be squeezed into the wrong aspect ratio. The
      writer.release() call is mandatory: it flushes the codec buffer and
      writes the file footer. Without it, many video players cannot open the
      file.

  - type: exercise
    heading: "Exercise 3: frames_to_video"
    prompt: >
      Implement frames_to_video(frames, output_path, fps=30.0, fourcc='mp4v', writer_fn=None) -> Path.
      If writer_fn is not None: return writer_fn(frames, output_path, fps).
      Otherwise (lazy import cv2): list(frames), raise ValueError if empty,
      h,w = frames[0].shape[:2], fourcc_code = cv2.VideoWriter_fourcc(*fourcc),
      out_path = Path(output_path), writer = cv2.VideoWriter(str(out_path), fourcc_code, fps, (w,h)),
      loop writing frames, writer.release(), return out_path.
    hint: >
      if writer_fn is not None: return writer_fn(frames, output_path, fps).
      import cv2; frames=list(frames); if not frames: raise ValueError('frames list is empty').
      h,w=frames[0].shape[:2]; code=cv2.VideoWriter_fourcc(*fourcc).
      writer=cv2.VideoWriter(str(Path(output_path)),code,fps,(w,h)).
      for f in frames: writer.write(f). writer.release(). return Path(output_path).
    narration: >
      frames_to_video completes the read-process-write loop: extract frames
      from a source video, transform each frame (resize, annotate, filter),
      write to a new video file.

  - type: summary
    heading: "Lesson 3 Summary"
    bullets:
      - "fourcc: four-char codec code — mp4v for .mp4, XVID for .avi"
      - "cv2.VideoWriter_fourcc(*fourcc) packs 4 chars into codec int"
      - "VideoWriter size is (width, height) — reverse of numpy shape"
      - "h,w = frames[0].shape[:2] then pass (w,h) to VideoWriter"
      - "writer.release() mandatory — flushes codec buffer, writes footer"
      - "writer_fn=None injection: mock writes placeholder bytes, returns Path"
    narration: >
      Reading and writing video is done. Next: FFmpeg for format conversion
      and audio extraction.
"""

_LESSON_04 = """\
day: "074"
lesson: 4
title: "FFmpeg from Python"
slides:
  - type: title
    heading: "FFmpeg from Python"
    subheading: "subprocess.run — format conversion, audio extraction"
    narration: >
      FFmpeg is the Swiss Army knife of media processing: it converts between
      formats, extracts audio tracks, resizes video, and hundreds of other
      operations. Calling it from Python with subprocess.run wraps all of this
      power with testable injection and clean output capture.

  - type: concept
    label: "FFmpeg basics"
    heading: "FFmpeg Command Structure"
    body: >
      Every FFmpeg command follows the same pattern: input flags, input file,
      filter/codec flags, output file. The -y flag overwrites output without
      prompting.
    bullets:
      - "ffmpeg -y -i input.mp4 output.avi — convert format"
      - "ffmpeg -y -i input.mp4 -vn output.mp3 — extract audio (-vn = no video)"
      - "ffmpeg -y -i in.mp4 -vf scale=640:-1 out.mp4 — resize to 640 wide"
      - "ffmpeg -y -i in.mp4 -ss 10 -t 30 clip.mp4 — 30s clip starting at 10s"
      - "-y: overwrite output without asking (essential for automation)"
    narration: >
      The -i flag specifies the input file. Everything before the first -i is
      global options (like -y). Everything between -i and the output file is
      output options: codec (-c:v), audio codec (-c:a), no video (-vn),
      video filters (-vf), duration (-t), start time (-ss). The output file
      is always the last argument. FFmpeg infers the output format from the
      file extension. The -y flag is essential when running FFmpeg from code
      because without it, FFmpeg blocks waiting for a y/n prompt when the
      output file already exists.

  - type: code
    label: "run_ffmpeg"
    heading: "run_ffmpeg Implementation"
    code: |
      import subprocess

      def run_ffmpeg(args, ffmpeg_fn=None):
          if ffmpeg_fn is not None:
              return ffmpeg_fn(args)
          result = subprocess.run(
              ['ffmpeg', '-y'] + list(args),
              capture_output=True, text=True,
          )
          return {
              'returncode': result.returncode,
              'stdout':     result.stdout,
              'stderr':     result.stderr,
          }

      # Format conversion
      r = run_ffmpeg(['-i', 'input.mp4', 'output.avi'])
      print(r['returncode'])   # 0 = success, non-zero = error

      # Extract audio
      r = run_ffmpeg(['-i', 'video.mp4', '-vn', 'audio.mp3'])

      # Resize to 640px wide (keep aspect ratio)
      r = run_ffmpeg(['-i', 'video.mp4', '-vf', 'scale=640:-1', 'small.mp4'])
    narration: >
      subprocess.run blocks until the command finishes, then returns a
      CompletedProcess object. capture_output=True redirects both stdout and
      stderr to the result object — without it, FFmpeg's verbose progress
      output floods the terminal. text=True decodes bytes to str using the
      system locale. returncode 0 means success; any other value means an
      error. FFmpeg always writes progress to stderr (not stdout), so check
      result.stderr for error messages. The injection pattern
      ffmpeg_fn=lambda args: dict(returncode=0,...) lets you test all calling
      code without FFmpeg installed.

  - type: concept
    label: "FFmpeg stderr"
    heading: "Reading FFmpeg Output"
    body: >
      FFmpeg writes its progress and error messages to stderr, not stdout.
      Always check result.stderr for diagnostics when returncode is non-zero.
    bullets:
      - "returncode 0: success"
      - "returncode non-zero: check result.stderr for the error message"
      - "FFmpeg always logs to stderr — stdout is typically empty"
      - "stderr on success: codec info, frame count, duration summary"
      - "stderr on failure: 'No such file or directory' or 'codec not found'"
    narration: >
      The reason FFmpeg uses stderr for progress is that stdout is reserved
      for piped binary output — if you pipe FFmpeg output to another program,
      stdout carries the video data and stderr carries human-readable progress.
      When calling from Python, capture_output=True captures both. A
      returncode of 0 with a non-empty stderr is normal: FFmpeg prints
      verbose codec information even on successful runs. Only a non-zero
      returncode indicates failure. Check result.stderr.split(newline)[-5:]
      to see the last few lines for a quick diagnosis.

  - type: exercise
    heading: "Exercise 4: run_ffmpeg"
    prompt: >
      Implement run_ffmpeg(args, ffmpeg_fn=None) -> dict.
      If ffmpeg_fn is not None: return ffmpeg_fn(args).
      Otherwise: import subprocess; result = subprocess.run(
      ['ffmpeg', '-y'] + list(args), capture_output=True, text=True).
      Return {'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}.
    hint: >
      if ffmpeg_fn is not None: return ffmpeg_fn(args).
      import subprocess; result = subprocess.run(['ffmpeg','-y']+list(args), capture_output=True, text=True).
      return {'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}.
    narration: >
      run_ffmpeg wraps FFmpeg's entire capability behind one testable function.
      Any video conversion, audio extraction, or filter operation becomes a
      single function call.

  - type: summary
    heading: "Lesson 4 Summary"
    bullets:
      - "FFmpeg: -y (overwrite), -i (input), output flags, output file"
      - "subprocess.run(['ffmpeg','-y']+args, capture_output=True, text=True)"
      - "returncode 0 = success; non-zero = check stderr for error"
      - "FFmpeg writes progress to stderr — stdout is binary pipe"
      - "Common ops: format convert, -vn audio extract, -vf scale=W:-1 resize"
      - "ffmpeg_fn=None injection: lambda args: dict(returncode=0,...)"
    narration: >
      All four core functions are built. The final lesson assembles them into
      VideoProcessor.
"""

_LESSON_05 = """\
day: "074"
lesson: 5
title: "VideoProcessor — Full Pipeline"
slides:
  - type: title
    heading: "VideoProcessor"
    subheading: "Full pipeline class — info, frames, to_video, run_ffmpeg"
    narration: >
      VideoProcessor wraps all four Day 74 functions behind a single class
      that binds injection functions at construction time. This is the same
      pattern as ImageSearchEngine (Day 71), AudioTranscriber (Day 72), and
      PodcastGenerator (Day 73): one class, bound mocks, clean interface.

  - type: how_it_works
    label: "VideoProcessor"
    heading: "VideoProcessor Design"
    body: >
      Four injection functions bound at __init__. Four methods, each delegating
      to the corresponding module-level function.
    bullets:
      - "VideoProcessor(info_fn, capture_fn, writer_fn, ffmpeg_fn)"
      - ".info(source) -> dict — delegates to get_video_info"
      - ".frames(source, step, max_frames) -> list — delegates to extract_frames"
      - ".to_video(frames, output_path, fps, fourcc) -> Path"
      - ".run_ffmpeg(args) -> dict — delegates to run_ffmpeg"
    narration: >
      All four injection parameters default to None. Passing only the ones
      needed for a particular test is fine — the rest fall through to the
      real implementations. The class binds them once at construction rather
      than passing them on every call, so calling code reads naturally:
      proc.frames(source, step=5) rather than extract_frames(source, 5,
      capture_fn=mock_fn). This is the same reason PodcastGenerator binds
      tts_fn and voice_map at construction.

  - type: code
    label: "Implementation"
    heading: "VideoProcessor Implementation"
    code: |
      class VideoProcessor:
          def __init__(self, info_fn=None, capture_fn=None,
                       writer_fn=None, ffmpeg_fn=None):
              self._info_fn    = info_fn
              self._capture_fn = capture_fn
              self._writer_fn  = writer_fn
              self._ffmpeg_fn  = ffmpeg_fn

          def info(self, source):
              return get_video_info(source, info_fn=self._info_fn)

          def frames(self, source, step=1, max_frames=None):
              return extract_frames(source, step=step,
                                    max_frames=max_frames,
                                    capture_fn=self._capture_fn)

          def to_video(self, frames, output_path, fps=30.0, fourcc='mp4v'):
              return frames_to_video(frames, output_path, fps=fps,
                                     fourcc=fourcc,
                                     writer_fn=self._writer_fn)

          def run_ffmpeg(self, args):
              return run_ffmpeg(args, ffmpeg_fn=self._ffmpeg_fn)
    narration: >
      Each method is a single line that forwards to the module-level function
      with the bound injection function. This thin delegation is intentional:
      the business logic lives in the module-level functions, which are
      independently testable. The class is an ergonomic wrapper that makes
      calls shorter and groups related operations. If you want to add a
      batch_frames method or a transcode convenience method, add them here
      without touching the underlying functions.

  - type: code
    label: "Full pipeline"
    heading: "Full Video Processing Pipeline"
    code: |
      import numpy as np
      import tempfile
      from pathlib import Path
      from video_processor import VideoProcessor

      # Mock functions — no video file or FFmpeg needed
      _FRAMES = [np.zeros((64, 64, 3), dtype=np.uint8) for _ in range(20)]
      _mock_info    = lambda src: {'fps': 30.0, 'frame_count': 20,
                                   'width': 64, 'height': 64, 'duration_sec': 0.667}
      _mock_capture = lambda src: _FRAMES
      _mock_writer  = lambda frms, path, fps: (Path(path).write_bytes(b'V'), Path(path))[1]
      _mock_ffmpeg  = lambda args: {'returncode': 0, 'stdout': '', 'stderr': ''}

      proc = VideoProcessor(info_fn=_mock_info, capture_fn=_mock_capture,
                            writer_fn=_mock_writer, ffmpeg_fn=_mock_ffmpeg)

      meta   = proc.info('source.mp4')
      frames = proc.frames('source.mp4', step=2, max_frames=5)
      print(meta['fps'], len(frames))   # 30.0  5

      with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
          out = proc.to_video(frames, f.name)
      print(out, Path(out).stat().st_size)

      res = proc.run_ffmpeg(['-i', 'source.mp4', '-vn', 'audio.mp3'])
      print(res['returncode'])   # 0
    narration: >
      This is the full video pipeline in 15 lines. With real implementations
      (no mock functions), the same code extracts frames from a real video,
      applies any transformation to the numpy arrays, writes a new video, and
      runs FFmpeg to extract the audio track. Swapping from mock to real
      means removing the injection arguments from the VideoProcessor constructor
      — all call sites remain unchanged.

  - type: exercise
    heading: "Exercise 5: VideoProcessor Class"
    prompt: >
      Implement VideoProcessor:
      __init__(info_fn=None, capture_fn=None, writer_fn=None, ffmpeg_fn=None):
        store all four as self._info_fn, self._capture_fn, self._writer_fn, self._ffmpeg_fn.
      info(source) -> dict: return get_video_info(source, info_fn=self._info_fn).
      frames(source, step=1, max_frames=None) -> list:
        return extract_frames(source, step=step, max_frames=max_frames, capture_fn=self._capture_fn).
      to_video(frames, output_path, fps=30.0, fourcc='mp4v') -> Path:
        return frames_to_video(frames, output_path, fps=fps, fourcc=fourcc, writer_fn=self._writer_fn).
      run_ffmpeg(args) -> dict: return run_ffmpeg(args, ffmpeg_fn=self._ffmpeg_fn).
    hint: >
      Each method is one return statement delegating to the module-level function
      with the corresponding self._xxx_fn bound injection function.
    narration: >
      VideoProcessor is the Day 74 deliverable. Combined with the vision
      pipeline from Day 67 and the audio transcriber from Day 72, you can
      now process all three modalities of video: video frames (Day 74),
      audio track (Day 72), and visual content (Day 67).

  - type: summary
    heading: "Lesson 5 Summary — Day 74 Complete"
    bullets:
      - "VideoProcessor binds info_fn, capture_fn, writer_fn, ffmpeg_fn at construction"
      - "Four methods each delegate to module-level function + bound injection fn"
      - "Full pipeline: info → frames → transform numpy arrays → to_video → run_ffmpeg"
      - "BGR numpy arrays as the common currency between OpenCV and PIL/numpy ops"
      - "Tomorrow (Day 75): Talking-Head Pipeline — lip sync, Wav2Lip, compositing"
    narration: >
      Day 74 is complete. You can read video metadata, extract frames as numpy
      arrays, write processed frames to a new video, and run FFmpeg conversions
      from Python — all testable without a video file or FFmpeg installed.
"""

for i, content in enumerate([_LESSON_01, _LESSON_02, _LESSON_03,
                               _LESSON_04, _LESSON_05], start=1):
    (OUT / "lessons" / f"day_{DAY}_lesson_0{i}.yaml").write_text(content)

# ── shared helpers ────────────────────────────────────────────────────────────
_NUMPY_HELPER = """\
from pathlib import Path

def _make_test_frames(n=10, height=32, width=32):
    import numpy as np
    frames = []
    for i in range(n):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:, :, 0] = int(255 * i / max(n - 1, 1))
        frames.append(frame)
    return frames
"""

_MOCK_SRC = """\
_MOCK_META = {
    'fps': 30.0, 'frame_count': 10, 'width': 32, 'height': 32, 'duration_sec': 0.333,
}
_mock_info_fn    = lambda source: dict(_MOCK_META)
_mock_capture_fn = lambda source: _make_test_frames(10)
_mock_writer_fn  = lambda frames, path, fps: (Path(path).write_bytes(b'VIDEO' + bytes(len(frames))), Path(path))[1]
_mock_ffmpeg_fn  = lambda args: {'returncode': 0, 'stdout': '', 'stderr': ''}
"""

# ── EX1: get_video_info ───────────────────────────────────────────────────────
_EX1_STUB = """\
def get_video_info(source, info_fn=None) -> dict:
    \"\"\"Return video metadata: fps, frame_count, width, height, duration_sec.

    Args:
        source:  path to video file (str or Path)
        info_fn: callable(source) -> dict for testing (no OpenCV needed)
    \"\"\"
    raise NotImplementedError
"""

_EX1_SOLUTION = """\
def get_video_info(source, info_fn=None):
    if info_fn is not None:
        return info_fn(source)
    import cv2
    cap = cv2.VideoCapture(str(source))
    if not cap.isOpened():
        raise ValueError(f'Cannot open video: {source}')
    fps         = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width       = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height      = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    duration = round(frame_count / fps, 3) if fps > 0 else 0.0
    return {
        'fps': fps, 'frame_count': frame_count,
        'width': width, 'height': height, 'duration_sec': duration,
    }
"""

_EX1_CHECKS = r"""
score, total = 0, 5
try:
    meta = get_video_info('video.mp4', info_fn=_mock_info_fn)

    # returns a dict
    assert isinstance(meta, dict)
    score += 1; print("✅ returns a dict")

    # required keys present
    for k in ('fps', 'frame_count', 'width', 'height', 'duration_sec'):
        assert k in meta, f"missing key '{k}'"
    score += 1; print("✅ all required keys present")

    # fps is float
    assert isinstance(meta['fps'], float) and meta['fps'] > 0
    score += 1; print("✅ fps is positive float")

    # frame_count and dimensions are int
    assert isinstance(meta['frame_count'], int)
    assert isinstance(meta['width'], int) and isinstance(meta['height'], int)
    score += 1; print("✅ frame_count, width, height are int")

    # duration_sec is float and approximately correct
    expected = round(meta['frame_count'] / meta['fps'], 3)
    assert abs(meta['duration_sec'] - expected) < 0.01, \
        f"duration_sec {meta['duration_sec']} != expected {expected}"
    score += 1; print("✅ duration_sec = frame_count / fps (correct)")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX1 = nb([
    md("# Day 074 — Exercise 1: get_video_info\n\n"
       "**What you'll build:** `get_video_info(source, info_fn=None) -> dict` — "
       "extract video metadata using OpenCV VideoCapture.\n\n"
       "**Why it matters:** fps, frame_count, width, and height are needed by "
       "every downstream operation: frame extraction, VideoWriter, and "
       "duration-based sampling."),
    code(_NUMPY_HELPER),
    code(_MOCK_SRC),
    md("## Task\n\n"
       "Return a dict with `fps`, `frame_count`, `width`, `height`, `duration_sec`.\n\n"
       "- Mock: `if info_fn is not None: return info_fn(source)`\n"
       "- Real: `import cv2`, `VideoCapture`, `.get(CAP_PROP_*)`, `.release()`\n"
       "- `duration_sec = round(frame_count / fps, 3) if fps > 0 else 0.0`"),
    md("## Your Implementation"),
    code(_EX1_STUB),
    code(_EX1_SOLUTION),
    md("## Automated checks"),
    code(_EX1_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX1_SOLUTION + "```\n\n"
       "**Why `int(cap.get(...))`?** The `cap.get()` method always returns a "
       "float, even for integer-valued properties. `int()` converts to the "
       "expected Python type for frame count and pixel dimensions.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_01.ipynb", EX1)

# ── EX2: extract_frames ───────────────────────────────────────────────────────
_EX2_STUB = """\
def extract_frames(source, step: int = 1, max_frames=None,
                   capture_fn=None) -> list:
    \"\"\"Extract frames from a video as a list of numpy arrays (BGR, uint8).

    Args:
        source:     video file path
        step:       keep every nth frame (1=all, 2=every other, ...)
        max_frames: maximum frames to return (None=all)
        capture_fn: callable(source) -> list[np.ndarray] for testing
    \"\"\"
    raise NotImplementedError
"""

_EX2_SOLUTION = """\
def extract_frames(source, step=1, max_frames=None, capture_fn=None):
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
"""

_EX2_CHECKS = r"""
score, total = 0, 5
try:
    # basic extraction — all frames
    frames = extract_frames('video.mp4', capture_fn=_mock_capture_fn)
    assert isinstance(frames, list) and len(frames) == 10
    score += 1; print("✅ extracts all 10 frames when step=1")

    # frame is numpy array with correct shape
    assert frames[0].shape == (32, 32, 3)
    assert frames[0].dtype.name == 'uint8'
    score += 1; print("✅ frames are (32, 32, 3) uint8 numpy arrays")

    # step parameter
    stepped = extract_frames('video.mp4', step=3, capture_fn=_mock_capture_fn)
    assert len(stepped) == 4, f"step=3 on 10 frames should give 4, got {len(stepped)}"
    score += 1; print("✅ step=3 selects correct frames (indices 0,3,6,9)")

    # max_frames cap
    capped = extract_frames('video.mp4', max_frames=3, capture_fn=_mock_capture_fn)
    assert len(capped) == 3, f"max_frames=3 should give 3, got {len(capped)}"
    score += 1; print("✅ max_frames=3 caps result at 3 frames")

    # step + max_frames combined
    combo = extract_frames('video.mp4', step=2, max_frames=3,
                           capture_fn=_mock_capture_fn)
    assert len(combo) <= 3
    score += 1; print("✅ step and max_frames work together")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX2 = nb([
    md("# Day 074 — Exercise 2: extract_frames\n\n"
       "**What you'll build:** `extract_frames(source, step, max_frames, capture_fn) -> list[np.ndarray]` — "
       "extract frames as numpy arrays with step and count control.\n\n"
       "**Why it matters:** A 2-hour movie at 30 FPS has 216,000 frames. "
       "`step` and `max_frames` make frame extraction feasible for any video length."),
    code(_NUMPY_HELPER),
    code(_MOCK_SRC),
    md("## Task\n\n"
       "**Mock path:** `all_frames = capture_fn(source); stepped = all_frames[::step]; "
       "return stepped[:max_frames] if max_frames is not None else stepped`\n\n"
       "**Real path:** `import cv2`, `VideoCapture` loop with `idx % step == 0` filter "
       "and `max_frames` early break."),
    md("## Your Implementation"),
    code(_EX2_STUB),
    code(_EX2_SOLUTION),
    md("## Automated checks"),
    code(_EX2_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX2_SOLUTION + "```\n\n"
       "**Why `max_frames is not None`** rather than `if max_frames`? "
       "Because `max_frames=0` would be falsy but is a valid (if unusual) limit "
       "meaning return zero frames. The explicit `is not None` check is safer.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_02.ipynb", EX2)

# ── EX3: frames_to_video ─────────────────────────────────────────────────────
_EX3_GIVEN = _NUMPY_HELPER + _MOCK_SRC

_EX3_STUB = """\
def frames_to_video(frames: list, output_path,
                    fps: float = 30.0, fourcc: str = 'mp4v',
                    writer_fn=None):
    \"\"\"Write frames to a video file.

    Args:
        frames:      list of (H, W, 3) uint8 numpy arrays (BGR)
        output_path: destination file path
        fps:         output frame rate
        fourcc:      codec code ('mp4v' for .mp4, 'XVID' for .avi)
        writer_fn:   callable(frames, output_path, fps) -> Path for testing
    Returns:
        Path to written file
    \"\"\"
    raise NotImplementedError
"""

_EX3_SOLUTION = """\
def frames_to_video(frames, output_path, fps=30.0, fourcc='mp4v', writer_fn=None):
    if writer_fn is not None:
        return writer_fn(frames, output_path, fps)
    import cv2
    frames = list(frames)
    if not frames:
        raise ValueError('frames list is empty')
    h, w        = frames[0].shape[:2]
    fourcc_code = cv2.VideoWriter_fourcc(*fourcc)
    out_path    = Path(output_path)
    writer      = cv2.VideoWriter(str(out_path), fourcc_code, fps, (w, h))
    for frame in frames:
        writer.write(frame)
    writer.release()
    return out_path
"""

_EX3_CHECKS = r"""
import tempfile
score, total = 0, 5
try:
    test_frames = _make_test_frames(6)

    # returns Path
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
        tmp = f.name
    out = frames_to_video(test_frames, tmp, writer_fn=_mock_writer_fn)
    assert isinstance(out, Path), f"expected Path, got {type(out)}"
    score += 1; print("✅ returns Path object")

    # file exists and has content
    assert out.exists() and out.stat().st_size > 0
    score += 1; print("✅ output file exists with non-zero size")

    # fps is forwarded to writer_fn
    captured_fps = {}
    def _cap_writer(frames, path, fps):
        captured_fps['fps'] = fps
        return Path(path)
    frames_to_video(test_frames, tmp, fps=24.0, writer_fn=_cap_writer)
    assert captured_fps.get('fps') == 24.0
    score += 1; print("✅ fps forwarded to writer_fn")

    # frames list forwarded correctly
    captured_frames = {}
    def _cap_frames(frames, path, fps):
        captured_frames['n'] = len(frames)
        return Path(path)
    frames_to_video(test_frames, tmp, writer_fn=_cap_frames)
    assert captured_frames.get('n') == 6
    score += 1; print("✅ correct number of frames forwarded")

    # different frame counts → different file sizes (mock encodes count)
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
        tmp2 = f.name
    out1 = frames_to_video(_make_test_frames(3), tmp, writer_fn=_mock_writer_fn)
    out2 = frames_to_video(_make_test_frames(8), tmp2, writer_fn=_mock_writer_fn)
    assert out1.stat().st_size != out2.stat().st_size
    score += 1; print("✅ different frame counts produce different file sizes")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX3 = nb([
    md("# Day 074 — Exercise 3: frames_to_video\n\n"
       "**What you'll build:** `frames_to_video(frames, output_path, fps, fourcc, writer_fn) -> Path` — "
       "write a list of numpy frame arrays to a video file.\n\n"
       "**Why it matters:** Completing the read→process→write loop — every "
       "video processing pipeline ends by writing the result to disk."),
    code(_EX3_GIVEN),
    md("## Task\n\n"
       "- **Mock:** `return writer_fn(frames, output_path, fps)`\n"
       "- **Real:** `import cv2`, `list(frames)`, raise `ValueError` if empty, "
       "`h,w = frames[0].shape[:2]`, `VideoWriter_fourcc(*fourcc)`, "
       "`VideoWriter(str(path), code, fps, (w,h))`, write loop, `release()`, return `Path`\n\n"
       "**Key gotcha:** VideoWriter takes `(width, height)` — "
       "numpy shape is `(height, width, channels)` so pass `(w, h)` not `(h, w)`."),
    md("## Your Implementation"),
    code(_EX3_STUB),
    code(_EX3_SOLUTION),
    md("## Automated checks"),
    code(_EX3_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX3_SOLUTION + "```\n\n"
       "**Why `list(frames)`?** The caller might pass a generator or iterator. "
       "Converting to list once means we can safely read `frames[0]` for "
       "shape and iterate in the write loop.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_03.ipynb", EX3)

# ── EX4: run_ffmpeg ───────────────────────────────────────────────────────────
_EX4_GIVEN = "from pathlib import Path\n" + _MOCK_SRC.replace(
    "_make_test_frames(10)", "[]")  # ffmpeg exercise doesn't need frame helper

_EX4_STUB = """\
def run_ffmpeg(args: list, ffmpeg_fn=None) -> dict:
    \"\"\"Run an FFmpeg command and return the result dict.

    Args:
        args:      FFmpeg arguments (everything after 'ffmpeg -y')
        ffmpeg_fn: callable(args) -> dict for testing
    Returns:
        {'returncode': int, 'stdout': str, 'stderr': str}
    \"\"\"
    raise NotImplementedError
"""

_EX4_SOLUTION = """\
def run_ffmpeg(args, ffmpeg_fn=None):
    if ffmpeg_fn is not None:
        return ffmpeg_fn(args)
    import subprocess
    result = subprocess.run(
        ['ffmpeg', '-y'] + list(args),
        capture_output=True, text=True,
    )
    return {
        'returncode': result.returncode,
        'stdout':     result.stdout,
        'stderr':     result.stderr,
    }
"""

_EX4_CHECKS = r"""
score, total = 0, 5
try:
    # returns a dict
    result = run_ffmpeg(['-i', 'input.mp4', 'output.avi'], ffmpeg_fn=_mock_ffmpeg_fn)
    assert isinstance(result, dict)
    score += 1; print("✅ returns a dict")

    # required keys present
    for k in ('returncode', 'stdout', 'stderr'):
        assert k in result, f"missing key '{k}'"
    score += 1; print("✅ all required keys present (returncode, stdout, stderr)")

    # returncode is int
    assert isinstance(result['returncode'], int)
    score += 1; print("✅ returncode is int")

    # ffmpeg_fn receives args
    captured = {}
    def _cap(args): captured['args'] = list(args); return {'returncode': 0, 'stdout': '', 'stderr': ''}
    run_ffmpeg(['-i', 'a.mp4', '-vn', 'b.mp3'], ffmpeg_fn=_cap)
    assert captured.get('args') == ['-i', 'a.mp4', '-vn', 'b.mp3']
    score += 1; print("✅ args forwarded to ffmpeg_fn unchanged")

    # mock returns success code 0
    r2 = run_ffmpeg(['any', 'args'], ffmpeg_fn=_mock_ffmpeg_fn)
    assert r2['returncode'] == 0
    score += 1; print("✅ mock ffmpeg_fn returns returncode 0")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX4 = nb([
    md("# Day 074 — Exercise 4: run_ffmpeg\n\n"
       "**What you'll build:** `run_ffmpeg(args, ffmpeg_fn=None) -> dict` — "
       "shell out to FFmpeg with injection support for testing.\n\n"
       "**Why it matters:** FFmpeg handles every media format conversion, "
       "audio extraction, and filter operation that OpenCV cannot. "
       "`run_ffmpeg` is the bridge from Python to the full FFmpeg ecosystem."),
    code("from pathlib import Path\n"
         "_mock_ffmpeg_fn = lambda args: {'returncode': 0, 'stdout': '', 'stderr': ''}"),
    md("## Task\n\n"
       "- **Mock:** `if ffmpeg_fn is not None: return ffmpeg_fn(args)`\n"
       "- **Real:** `import subprocess; result = subprocess.run(['ffmpeg', '-y'] + list(args), "
       "capture_output=True, text=True)`\n"
       "- Return `{'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}`"),
    md("## Your Implementation"),
    code(_EX4_STUB),
    code(_EX4_SOLUTION),
    md("## Automated checks"),
    code(_EX4_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX4_SOLUTION + "```\n\n"
       "**Why `-y` before the args?** The `-y` flag must come before the "
       "input/output arguments. Prepending it in the base command ensures "
       "callers never need to remember to include it. FFmpeg will overwrite "
       "existing output files without prompting — essential for automation.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_04.ipynb", EX4)

# ── EX5: VideoProcessor ───────────────────────────────────────────────────────
_EX5_GIVEN = _NUMPY_HELPER + _MOCK_SRC + """\

def get_video_info(source, info_fn=None):
    if info_fn is not None:
        return info_fn(source)
    import cv2
    cap = cv2.VideoCapture(str(source))
    if not cap.isOpened():
        raise ValueError(f'Cannot open video: {source}')
    fps         = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width       = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height      = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    duration = round(frame_count / fps, 3) if fps > 0 else 0.0
    return {'fps': fps, 'frame_count': frame_count,
            'width': width, 'height': height, 'duration_sec': duration}

def extract_frames(source, step=1, max_frames=None, capture_fn=None):
    if capture_fn is not None:
        all_frames = capture_fn(source)
        stepped    = all_frames[::step]
        return stepped[:max_frames] if max_frames is not None else stepped
    import cv2
    cap = cv2.VideoCapture(str(source)); frames = []; idx = 0
    while True:
        ret, frame = cap.read()
        if not ret: break
        if idx % step == 0:
            frames.append(frame)
            if max_frames is not None and len(frames) >= max_frames: break
        idx += 1
    cap.release(); return frames

def frames_to_video(frames, output_path, fps=30.0, fourcc='mp4v', writer_fn=None):
    if writer_fn is not None:
        return writer_fn(frames, output_path, fps)
    import cv2; frames = list(frames)
    if not frames: raise ValueError('frames list is empty')
    h, w = frames[0].shape[:2]; code = cv2.VideoWriter_fourcc(*fourcc)
    writer = cv2.VideoWriter(str(Path(output_path)), code, fps, (w, h))
    for f in frames: writer.write(f)
    writer.release(); return Path(output_path)

def run_ffmpeg(args, ffmpeg_fn=None):
    if ffmpeg_fn is not None:
        return ffmpeg_fn(args)
    import subprocess
    r = subprocess.run(['ffmpeg', '-y'] + list(args), capture_output=True, text=True)
    return {'returncode': r.returncode, 'stdout': r.stdout, 'stderr': r.stderr}
"""

_EX5_STUB = """\
class VideoProcessor:
    \"\"\"Process video files using OpenCV and FFmpeg.

    Inject fn parameters for testing without video files or FFmpeg.
    \"\"\"

    def __init__(self, info_fn=None, capture_fn=None,
                 writer_fn=None, ffmpeg_fn=None) -> None:
        raise NotImplementedError

    def info(self, source) -> dict:
        \"\"\"Return video metadata dict.\"\"\"
        raise NotImplementedError

    def frames(self, source, step: int = 1, max_frames=None) -> list:
        \"\"\"Extract frames as a list of numpy arrays.\"\"\"
        raise NotImplementedError

    def to_video(self, frames: list, output_path,
                 fps: float = 30.0, fourcc: str = 'mp4v'):
        \"\"\"Write frames to a video file. Returns Path.\"\"\"
        raise NotImplementedError

    def run_ffmpeg(self, args: list) -> dict:
        \"\"\"Run an FFmpeg command. Returns result dict.\"\"\"
        raise NotImplementedError
"""

_EX5_SOLUTION = """\
class VideoProcessor:
    def __init__(self, info_fn=None, capture_fn=None,
                 writer_fn=None, ffmpeg_fn=None):
        self._info_fn    = info_fn
        self._capture_fn = capture_fn
        self._writer_fn  = writer_fn
        self._ffmpeg_fn  = ffmpeg_fn

    def info(self, source):
        return get_video_info(source, info_fn=self._info_fn)

    def frames(self, source, step=1, max_frames=None):
        return extract_frames(source, step=step,
                              max_frames=max_frames,
                              capture_fn=self._capture_fn)

    def to_video(self, frames, output_path, fps=30.0, fourcc='mp4v'):
        return frames_to_video(frames, output_path, fps=fps,
                               fourcc=fourcc, writer_fn=self._writer_fn)

    def run_ffmpeg(self, args):
        return run_ffmpeg(args, ffmpeg_fn=self._ffmpeg_fn)
"""

_EX5_CHECKS = r"""
import tempfile
score, total = 0, 5
try:
    proc = VideoProcessor(
        info_fn=_mock_info_fn,
        capture_fn=_mock_capture_fn,
        writer_fn=_mock_writer_fn,
        ffmpeg_fn=_mock_ffmpeg_fn,
    )

    # info delegates to get_video_info
    meta = proc.info('video.mp4')
    assert isinstance(meta, dict) and 'fps' in meta and 'frame_count' in meta
    score += 1; print("✅ info() returns metadata dict")

    # frames delegates to extract_frames
    frames = proc.frames('video.mp4', step=2, max_frames=4)
    assert isinstance(frames, list) and len(frames) <= 4
    assert frames[0].shape == (32, 32, 3)
    score += 1; print("✅ frames() returns correct list of numpy arrays")

    # to_video delegates to frames_to_video
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
        tmp = f.name
    out = proc.to_video(_make_test_frames(5), tmp)
    assert isinstance(out, Path) and out.exists()
    score += 1; print("✅ to_video() returns existing Path")

    # run_ffmpeg delegates correctly
    res = proc.run_ffmpeg(['-i', 'in.mp4', 'out.avi'])
    assert res.get('returncode') == 0
    score += 1; print("✅ run_ffmpeg() returns result dict with returncode 0")

    # injection fns bound at construction (not passed per call)
    captured = {}
    def _cap_capture(src): captured['called'] = True; return _make_test_frames(5)
    proc2 = VideoProcessor(capture_fn=_cap_capture)
    proc2.frames('x.mp4')
    assert captured.get('called') is True
    score += 1; print("✅ injection fn bound at construction, used on each call")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX5 = nb([
    md("# Day 074 — Exercise 5: VideoProcessor\n\n"
       "**What you'll build:** `VideoProcessor` — full pipeline class binding "
       "all four injection functions at construction.\n\n"
       "**Why it matters:** The class makes the full pipeline ergonomic: "
       "`proc.frames(src, step=5)` reads more clearly than "
       "`extract_frames(src, 5, capture_fn=mock)` at every call site."),
    code(_EX5_GIVEN),
    md("## Task\n\n"
       "Implement `VideoProcessor`:\n\n"
       "- `__init__`: store `info_fn`, `capture_fn`, `writer_fn`, `ffmpeg_fn` as "
       "`self._xxx_fn`\n"
       "- `info(source)`: `return get_video_info(source, info_fn=self._info_fn)`\n"
       "- `frames(source, step=1, max_frames=None)`: delegate to `extract_frames` "
       "with `capture_fn=self._capture_fn`\n"
       "- `to_video(frames, output_path, fps=30.0, fourcc='mp4v')`: delegate to "
       "`frames_to_video` with `writer_fn=self._writer_fn`\n"
       "- `run_ffmpeg(args)`: delegate to `run_ffmpeg` with `ffmpeg_fn=self._ffmpeg_fn`"),
    md("## Your Implementation"),
    code(_EX5_STUB),
    code(_EX5_SOLUTION),
    md("## Automated checks"),
    code(_EX5_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX5_SOLUTION + "```\n\n"
       "**Why store as `self._xxx_fn`** (underscore prefix)? Underscore "
       "signals implementation detail — callers use `.info()`, `.frames()` etc, "
       "not the raw injection functions. Same convention as `_describe_fn` in "
       "Day 67's `VisionAnalyzer`.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_05.ipynb", EX5)

# ── PROJECT NOTEBOOK ──────────────────────────────────────────────────────────
PROJECT = nb([
    md("# Day 074 — Project: Video Processor\n\n"
       "## What You're Building\n\n"
       "`video_processor.py` — a `VideoProcessor` class for frame-level video processing.\n\n"
       "## Setup\n\n"
       "```bash\n"
       "pip install opencv-python-headless\n"
       "brew install ffmpeg   # macOS\n"
       "```\n\n"
       "## Design\n\n"
       "```\n"
       "get_video_info(source, info_fn=None) -> dict\n"
       "extract_frames(source, step, max_frames, capture_fn=None) -> list[ndarray]\n"
       "frames_to_video(frames, output_path, fps, fourcc, writer_fn=None) -> Path\n"
       "run_ffmpeg(args, ffmpeg_fn=None) -> dict\n"
       "VideoProcessor(info_fn, capture_fn, writer_fn, ffmpeg_fn)\n"
       "  .info(source) -> dict\n"
       "  .frames(source, step, max_frames) -> list\n"
       "  .to_video(frames, output_path, fps, fourcc) -> Path\n"
       "  .run_ffmpeg(args) -> dict\n"
       "```"),
    code("# Your implementation here — build VideoProcessor and write video_processor.py\n"),
])
save(OUT / "project" / "project.ipynb", PROJECT)

# ── SOLUTION NOTEBOOK ─────────────────────────────────────────────────────────
_SOL_CELL1 = (
    f"_VIDEO_SRC = {repr(_VIDEO_SRC)}\n"
    "from pathlib import Path\n"
    "Path('video_processor.py').write_text(_VIDEO_SRC, encoding='utf-8')\n"
    "print('video_processor.py written.')"
)

_SOL_CELL2 = """\
import tempfile, numpy as np
from pathlib import Path
from video_processor import (
    get_video_info, extract_frames, frames_to_video, run_ffmpeg, VideoProcessor,
)

_FRAMES = [np.zeros((32, 32, 3), dtype=np.uint8) for _ in range(10)]
_mock_info    = lambda src: {'fps': 30.0, 'frame_count': 10, 'width': 32, 'height': 32, 'duration_sec': 0.333}
_mock_capture = lambda src: _FRAMES
_mock_writer  = lambda frames, path, fps: (Path(path).write_bytes(b'V' * len(frames)), Path(path))[1]
_mock_ffmpeg  = lambda args: {'returncode': 0, 'stdout': '', 'stderr': ''}

# 1. get_video_info
meta = get_video_info('x.mp4', info_fn=_mock_info)
assert set(meta) >= {'fps', 'frame_count', 'width', 'height', 'duration_sec'}
assert isinstance(meta['frame_count'], int)
print("\\u2705 get_video_info correct")

# 2. extract_frames
frames = extract_frames('x.mp4', step=2, max_frames=4, capture_fn=_mock_capture)
assert len(frames) <= 4 and frames[0].shape == (32, 32, 3)
print("\\u2705 extract_frames correct")

# 3. frames_to_video
with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
    tmp = f.name
out = frames_to_video(_FRAMES[:5], tmp, writer_fn=_mock_writer)
assert isinstance(out, Path) and out.exists() and out.stat().st_size > 0
print("\\u2705 frames_to_video correct")

# 4. run_ffmpeg
res = run_ffmpeg(['-i', 'in.mp4', 'out.avi'], ffmpeg_fn=_mock_ffmpeg)
assert res['returncode'] == 0 and 'stdout' in res and 'stderr' in res
print("\\u2705 run_ffmpeg correct")

# 5. VideoProcessor
proc = VideoProcessor(info_fn=_mock_info, capture_fn=_mock_capture,
                      writer_fn=_mock_writer, ffmpeg_fn=_mock_ffmpeg)
meta2  = proc.info('v.mp4')
frms   = proc.frames('v.mp4', step=3, max_frames=3)
out2   = proc.to_video(frms, tmp)
res2   = proc.run_ffmpeg(['-vn', 'out.mp3'])
assert isinstance(meta2, dict) and len(frms) <= 3
assert isinstance(out2, Path) and res2['returncode'] == 0
print("\\u2705 VideoProcessor correct")
print("\\nVideo Processor complete!")
"""

SOLUTION = nb([
    md("# Day 074 — Solution: Video Processor"),
    code(_SOL_CELL1),
    code(_SOL_CELL2),
])
save(OUT / "project" / "solution" / "solution.ipynb", SOLUTION)
(OUT / "project" / "solution" / "video_processor.py").write_text(_VIDEO_SRC)

print(f"Day {DAY} notebooks written to {OUT}")
print("  lessons/    day_074_lesson_01.yaml – lesson_05.yaml")
print("  exercises/  exercise_01 – exercise_05")
print("  project/    project.ipynb")
print("  project/solution/  solution.ipynb + video_processor.py")
