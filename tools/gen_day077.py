#!/usr/bin/env python3
"""gen_day077.py — generate Day 077: Real-Time Vision."""
from pathlib import Path
import json

ROOT    = Path(__file__).parent.parent
DAY     = "077"
SECTION = "05_vision_multimodal"
OUT     = ROOT / SECTION / f"day_{DAY}"

(OUT / "exercises").mkdir(parents=True, exist_ok=True)
(OUT / "lessons").mkdir(parents=True, exist_ok=True)
(OUT / "project" / "solution").mkdir(parents=True, exist_ok=True)

# ── deliverable: live_vision.py ───────────────────────────────────────────────
_LIVE_VISION_SRC = '''\
"""live_vision.py — Day 077: Real-Time Vision Agent.

Capture frames from a webcam or device, analyze them with a vision LLM,
and save results. All three capabilities are injectable for headless testing.

Functions:
    open_camera        — open a camera device as a VideoCapture object
    read_frame         — read one frame from an open capture
    frame_to_image     — convert BGR ndarray to PIL Image (RGB)
    analyze_frame      — vision LLM analysis of one frame
    save_frame         — write a frame to disk as PNG
    should_analyze     — rate-control predicate (every_n frames)
    capture_frames     — collect n_frames from camera into a list
    analyze_stream     — capture + analyze n_frames, return results
    LiveVisionAgent    — context-manager camera agent with vision

Setup:
    pip install pillow ollama opencv-python-headless
    ollama pull llava
"""
import io
import base64
from pathlib import Path


def open_camera(device=0, camera_fn=None):
    """Open a camera device and return a VideoCapture-compatible object.

    Args:
        device:    integer device index (0 = default webcam) or file path
        camera_fn: callable(device) -> cap for testing
    Returns:
        VideoCapture object with .isOpened(), .read(), .release()
    Raises:
        RuntimeError if the camera cannot be opened
    """
    if camera_fn is not None:
        return camera_fn(device)
    import cv2
    cap = cv2.VideoCapture(device)
    if not cap.isOpened():
        raise RuntimeError(f'Cannot open camera device {device}')
    return cap


def read_frame(cap):
    """Read one frame from an open capture.

    Args:
        cap: VideoCapture or compatible object
    Returns:
        (success: bool, frame: ndarray | None)
    """
    return cap.read()


def frame_to_image(frame):
    """Convert a BGR ndarray frame to a PIL Image in RGB mode.

    Args:
        frame: ndarray shape (H, W, 3) in BGR channel order (OpenCV convention)
    Returns:
        PIL Image in RGB mode
    """
    from PIL import Image
    rgb = frame[:, :, ::-1]
    return Image.fromarray(rgb)


def analyze_frame(frame, question, analyze_fn=None):
    """Analyze a camera frame with a vision LLM.

    Args:
        frame:      BGR ndarray
        question:   natural-language question about the frame
        analyze_fn: callable(pil_image, question) -> str for testing
    Returns:
        model answer string
    """
    image = frame_to_image(frame)
    if analyze_fn is not None:
        return analyze_fn(image, question)
    import ollama
    buf = io.BytesIO()
    image.save(buf, format='PNG')
    img_b64 = base64.b64encode(buf.getvalue()).decode()
    resp = ollama.chat(
        model='llava',
        messages=[{'role': 'user', 'content': question, 'images': [img_b64]}],
    )
    return resp['message']['content']


def save_frame(frame, path):
    """Save a BGR frame to disk as a PNG image.

    Args:
        frame: BGR ndarray
        path:  output path (str or Path)
    Returns:
        Path of the saved file
    """
    out = Path(path)
    frame_to_image(frame).save(out, format='PNG')
    return out


def should_analyze(frame_count, every_n):
    """Return True if this frame should be analyzed.

    Args:
        frame_count: zero-based frame counter
        every_n:     analyze every Nth frame (1 = every frame)
    Returns:
        bool
    """
    return frame_count % every_n == 0


def capture_frames(device=0, n_frames=5, every_n=1, camera_fn=None):
    """Capture n_frames frames from a camera, rate-controlled by every_n.

    Args:
        device:    camera device index
        n_frames:  how many frames to collect
        every_n:   collect every Nth frame read from the camera
        camera_fn: callable(device) -> cap for testing
    Returns:
        list of BGR ndarray frames
    """
    cap = open_camera(device=device, camera_fn=camera_fn)
    frames = []
    frame_count = 0
    try:
        while len(frames) < n_frames:
            ret, frame = read_frame(cap)
            if not ret:
                break
            if should_analyze(frame_count, every_n):
                frames.append(frame)
            frame_count += 1
    finally:
        cap.release()
    return frames


def analyze_stream(device=0, task='Describe what you see.', n_frames=5,
                   every_n=1, camera_fn=None, analyze_fn=None):
    """Capture frames and analyze each with a vision LLM.

    Args:
        device:     camera device index
        task:       question or instruction for the vision LLM
        n_frames:   number of frames to analyze
        every_n:    analyze every Nth frame (skip the rest)
        camera_fn:  callable(device) -> cap for testing
        analyze_fn: callable(pil_image, question) -> str for testing
    Returns:
        list of dicts: [{frame_idx: int, description: str}, ...]
    """
    cap = open_camera(device=device, camera_fn=camera_fn)
    results = []
    frame_count = 0
    analyzed = 0
    try:
        while analyzed < n_frames:
            ret, frame = read_frame(cap)
            if not ret:
                break
            if should_analyze(frame_count, every_n):
                description = analyze_frame(frame, task, analyze_fn=analyze_fn)
                results.append({'frame_idx': frame_count, 'description': description})
                analyzed += 1
            frame_count += 1
    finally:
        cap.release()
    return results


class LiveVisionAgent:
    """Context-manager camera agent with vision analysis.

    Opens a camera on enter, releases it on exit. Stores the last frame
    captured so analyze/describe/save can be called without re-reading.

    Example::

        with LiveVisionAgent(
            camera_fn=mock_camera,
            analyze_fn=mock_analyze,
        ) as agent:
            frame = agent.read()
            desc = agent.describe()
            agent.save(frame, 'frame.png')
    """

    def __init__(self, device=0, camera_fn=None, analyze_fn=None):
        self._device = device
        self._camera_fn = camera_fn
        self._analyze_fn = analyze_fn
        self._cap = None
        self._last_frame = None

    def open(self, device=None):
        """Open the camera. Called automatically by __enter__."""
        d = device if device is not None else self._device
        self._cap = open_camera(device=d, camera_fn=self._camera_fn)
        return self

    def read(self):
        """Read one frame; store as last frame. Returns ndarray or None."""
        if self._cap is None:
            raise RuntimeError('Camera not open: call open() first or use as context manager.')
        ret, frame = read_frame(self._cap)
        if ret:
            self._last_frame = frame
        return frame if ret else None

    def analyze(self, question, frame=None):
        """Analyze a frame (or last captured frame) with a vision LLM."""
        f = frame if frame is not None else self._last_frame
        if f is None:
            raise ValueError('No frame: call read() first or pass frame.')
        return analyze_frame(f, question, analyze_fn=self._analyze_fn)

    def describe(self, frame=None):
        """Describe what is visible in the frame."""
        return self.analyze('Describe what you see in detail.', frame=frame)

    def save(self, path, frame=None):
        """Save a frame (or last captured frame) to disk as PNG."""
        f = frame if frame is not None else self._last_frame
        if f is None:
            raise ValueError('No frame: call read() first or pass frame.')
        return save_frame(f, path)

    def close(self):
        """Release the camera resource."""
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *args):
        self.close()
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
day: "077"
lesson: 1
title: "Real-Time Vision — Webcam Capture"
slides:
  - type: title
    heading: "Real-Time Vision"
    subheading: "From static screenshots to live camera frames"
    narration: >
      Day 76 captured screenshots of whatever was already on screen. Day 77
      opens a camera device, reads a continuous stream of frames, and applies
      vision analysis to each one. The same injection pattern handles both:
      camera_fn replaces cv2.VideoCapture so the gate runs without a real camera.

  - type: concept
    label: "Webcam vs file"
    heading: "VideoCapture Device Index"
    body: >
      Day 74 opened video files. Day 77 opens a live camera using a device index.
    bullets:
      - "cv2.VideoCapture(0) — default webcam (device index 0)"
      - "cv2.VideoCapture(1) — second camera or external webcam"
      - "cv2.VideoCapture('file.mp4') — video file (Day 74 pattern)"
      - "Same interface: .isOpened(), .read(), .release()"
      - "Device index 0 is always the built-in or first camera"
      - ".isOpened() returns False if the device is not available"
    narration: >
      The same VideoCapture class works for both video files and live cameras.
      The only difference is the argument: a file path string opens a file,
      an integer opens a camera device. Device 0 is the default webcam on any
      platform. The cap object has identical .read() and .release() methods
      in both cases.

  - type: code
    label: "open_camera"
    heading: "open_camera Implementation"
    code: |
      def open_camera(device=0, camera_fn=None):
          if camera_fn is not None:
              return camera_fn(device)
          import cv2
          cap = cv2.VideoCapture(device)
          if not cap.isOpened():
              raise RuntimeError(f'Cannot open camera device {device}')
          return cap

      def read_frame(cap):
          return cap.read()
      # ret, frame = read_frame(cap)  -> (True, ndarray) or (False, None)
    narration: >
      open_camera delegates to camera_fn in test mode. In production it opens
      a real VideoCapture and raises RuntimeError if the device is unavailable.
      Importing cv2 inside the else branch avoids import errors in environments
      where opencv is not installed. read_frame is a one-line wrapper around
      cap.read() that makes the call unit-testable with a mock cap.

  - type: concept
    label: "Mock camera"
    heading: "Mock Camera for Headless Testing"
    body: >
      A mock cap object implements the same three-method interface as VideoCapture.
    bullets:
      - "isOpened() -> True: signals camera is ready"
      - "read() -> (True, frame_ndarray) or (False, None) at exhaustion"
      - "release(): no-op in the mock"
      - "camera_fn(device) -> mock_cap: returned by camera_fn injection"
      - "Each test call creates a fresh mock with its own frame list"
      - "Completely replaces cv2 — no display, no hardware required"
    narration: >
      The mock cap class stores a list of pre-built numpy arrays and returns
      them one at a time from read(). When the list is exhausted it returns
      (False, None), matching VideoCapture end-of-file behaviour. The mock
      is deterministic — same frames every test run.

  - type: exercise
    heading: "Exercise 1: open_camera and read_frame"
    prompt: >
      Implement open_camera(device=0, camera_fn=None) -> cap.
      If camera_fn is not None: return camera_fn(device).
      Otherwise: import cv2; cap = cv2.VideoCapture(device); if not
      cap.isOpened(): raise RuntimeError; return cap.
      Implement read_frame(cap) -> (bool, ndarray|None): return cap.read().
    hint: >
      open_camera: if camera_fn: return camera_fn(device).
      import cv2 inside else branch. cap = cv2.VideoCapture(device).
      if not cap.isOpened(): raise RuntimeError(f'Cannot open camera device {device}').
      read_frame: return cap.read().
    narration: >
      open_camera and read_frame are the foundation. Every other function
      in live_vision.py builds on these two.

  - type: summary
    heading: "Lesson 1 Summary"
    bullets:
      - "cv2.VideoCapture(0) opens default webcam; integer argument = device index"
      - "Same cap interface as file capture from Day 74: .isOpened/.read/.release"
      - "camera_fn(device) -> mock_cap: replaces VideoCapture for headless testing"
      - "Mock cap: isOpened()=True, read() returns frames one-by-one, release() no-op"
      - "read_frame(cap): one-line wrapper around cap.read()"
    narration: >
      Lesson 2 adds frame conversion and vision LLM analysis.
"""

_LESSON_02 = """\
day: "077"
lesson: 2
title: "Frame Analysis — BGR to PIL, Vision LLM"
slides:
  - type: title
    heading: "Frame Analysis"
    subheading: "BGR ndarray -> PIL Image -> vision LLM"
    narration: >
      A camera frame is a numpy ndarray in BGR channel order. To send it to
      a vision LLM via Ollama, it must first become a PIL Image in RGB order,
      then be base64-encoded. frame_to_image handles the conversion. analyze_frame
      chains conversion with the Day 76 vision LLM call.

  - type: code
    label: "frame_to_image"
    heading: "frame_to_image — BGR to PIL RGB"
    code: |
      from PIL import Image

      def frame_to_image(frame):
          rgb = frame[:, :, ::-1]   # BGR -> RGB (zero-copy axis reversal)
          return Image.fromarray(rgb)

      # frame[:, :, ::-1]
      #   first :  all rows
      #   second : all columns
      #   ::-1    reverse channel order: [B, G, R] -> [R, G, B]
    narration: >
      OpenCV stores frames in BGR order — a historical quirk from its early
      Windows days where bitmap pixels were stored B-G-R. PIL expects RGB.
      The zero-copy channel reversal frame[:, :, ::-1] reverses the third
      axis (channels) without copying memory. Image.fromarray then wraps the
      result. This is the same conversion introduced in Day 74 for displaying
      frames with matplotlib.

  - type: code
    label: "analyze_frame"
    heading: "analyze_frame — Frame to Vision LLM"
    code: |
      import io, base64

      def analyze_frame(frame, question, analyze_fn=None):
          image = frame_to_image(frame)
          if analyze_fn is not None:
              return analyze_fn(image, question)
          import ollama
          buf = io.BytesIO()
          image.save(buf, format='PNG')
          img_b64 = base64.b64encode(buf.getvalue()).decode()
          resp = ollama.chat(
              model='llava',
              messages=[{
                  'role': 'user',
                  'content': question,
                  'images': [img_b64],
              }],
          )
          return resp['message']['content']
    narration: >
      analyze_frame first converts the BGR frame to a PIL Image using
      frame_to_image, then follows the exact same base64-encode-and-chat
      pattern from Day 76's analyze_screenshot. The only difference is that
      the input is a BGR ndarray rather than a PIL Image. The analyze_fn
      injection receives the PIL Image (after conversion) so the mock does
      not need to handle BGR arrays.

  - type: concept
    label: "BGR convention"
    heading: "Why BGR? OpenCV History"
    body: >
      OpenCV stores frames as BGR arrays. Every frame operation must account
      for this.
    bullets:
      - "BGR = Blue-Green-Red channel order (OpenCV convention from Day 74)"
      - "PIL, matplotlib, and most deep learning frameworks expect RGB"
      - "frame[:, :, ::-1] reverses the channel axis: [B,G,R] -> [R,G,B]"
      - "Zero-copy: creates a view of the original array (no new memory)"
      - "Image.fromarray(rgb) wraps the RGB view as a PIL Image"
      - "analyze_fn receives PIL Image, not BGR ndarray (conversion done first)"
    narration: >
      The BGR/RGB mismatch is the most common source of colour errors when
      working with OpenCV. Always convert to RGB before passing to PIL,
      matplotlib, or Ollama. The channel reversal is zero-copy because numpy
      axis reversal creates a view rather than allocating new memory.

  - type: exercise
    heading: "Exercise 2: frame_to_image and analyze_frame"
    prompt: >
      Implement: (1) frame_to_image(frame) -> PIL.Image: reverse the channel
      axis with frame[:, :, ::-1] to get RGB, then return Image.fromarray(rgb).
      (2) analyze_frame(frame, question, analyze_fn=None) -> str: call
      frame_to_image(frame) to get image; if analyze_fn: return analyze_fn(image,
      question); else: BytesIO PNG encode -> base64 -> ollama.chat llava ->
      return resp['message']['content'].
    hint: >
      frame_to_image: from PIL import Image; rgb = frame[:, :, ::-1]; return
      Image.fromarray(rgb).
      analyze_frame: image = frame_to_image(frame); if analyze_fn: return
      analyze_fn(image, question); else: import io, base64, ollama; BytesIO +
      save PNG + b64encode + ollama.chat model='llava' + return content.
    narration: >
      frame_to_image is three lines. analyze_frame follows the exact same
      pattern as Day 76's analyze_screenshot with frame_to_image prepended.

  - type: summary
    heading: "Lesson 2 Summary"
    bullets:
      - "frame[:, :, ::-1]: reverse channel axis BGR->RGB (zero-copy view)"
      - "Image.fromarray(rgb): wrap RGB array as PIL Image"
      - "analyze_frame: frame_to_image first, then base64+ollama.chat llava"
      - "analyze_fn(pil_image, question) receives PIL Image, not BGR ndarray"
      - "Same base64+Ollama pattern as Day 76 analyze_screenshot"
    narration: >
      Lesson 3 adds rate control and frame persistence.
"""

_LESSON_03 = """\
day: "077"
lesson: 3
title: "Rate Control and Frame Persistence"
slides:
  - type: title
    heading: "Rate Control"
    subheading: "Analyze every Nth frame — vision LLMs are slow"
    narration: >
      A camera produces 30 frames per second. A vision LLM call takes 2 to 10
      seconds. Trying to analyze every frame would block the capture loop within
      one second. Rate control — analyzing only every Nth frame — decouples
      capture speed from analysis speed. The should_analyze predicate implements
      this with a single modulo check.

  - type: code
    label: "should_analyze"
    heading: "should_analyze — Rate Control Predicate"
    code: |
      def should_analyze(frame_count, every_n):
          return frame_count % every_n == 0

      # Examples:
      # every_n=1  -> analyze every frame (frame 0,1,2,3,...)
      # every_n=5  -> analyze frames 0, 5, 10, 15, ...
      # every_n=30 -> analyze ~1 frame per second at 30 FPS
      # frame_count=0, every_n=1 -> True (first frame is always analyzed)
    narration: >
      should_analyze uses modulo: frame_count % every_n == 0 is True when
      frame_count is a multiple of every_n. At every_n=1, every frame is
      analyzed. At every_n=30 with a 30 FPS camera, one frame per second is
      analyzed, giving the vision LLM several seconds to respond per frame.
      Starting at frame_count=0 means the very first frame is always included.

  - type: code
    label: "save_frame"
    heading: "save_frame — Persist a Frame as PNG"
    code: |
      from pathlib import Path

      def save_frame(frame, path):
          out = Path(path)
          frame_to_image(frame).save(out, format='PNG')
          return out

      # Never use cv2.imshow() — requires a display (headless fails)
      # Never use plt.show() — same problem
      # Save to disk with PIL: no display required
    narration: >
      save_frame converts the BGR frame to PIL RGB, then saves as PNG. This
      is intentionally the same as writing any PIL Image — no new API needed.
      The important constraint is that cv2.imshow() and plt.show() require a
      display server and fail in headless environments. Always save to disk
      or an in-memory buffer rather than showing interactively.

  - type: concept
    label: "Analysis cost"
    heading: "Balancing Capture Rate and Analysis Cost"
    body: >
      Typical vision LLM latency and frame rates determine the right every_n value.
    bullets:
      - "30 FPS camera: one new frame every 33 ms"
      - "llava analysis: 2-10 seconds per frame on a typical GPU"
      - "every_n=90 at 30 FPS: analyze ~1 frame every 3 seconds"
      - "every_n=1: analyze every frame — capture loop blocks immediately"
      - "For demos: every_n=30 or 60 is a practical starting point"
      - "For offline batch: every_n=1 fine (capture first, analyze later)"
    narration: >
      The right every_n value depends on hardware. On a fast GPU with a small
      llava variant, every_n=10 might be feasible. On a CPU, every_n=300
      might still cause a backlog. For real-time feel, a separate thread for
      analysis while capture continues is the production pattern (Day 83
      covers async agent loops). For Day 77, the simple blocking approach
      with every_n rate control is the right starting point.

  - type: exercise
    heading: "Exercise 3: should_analyze and save_frame"
    prompt: >
      Implement: (1) should_analyze(frame_count, every_n) -> bool:
      return frame_count % every_n == 0.
      (2) save_frame(frame, path) -> Path: convert frame to PIL image with
      frame_to_image(frame), call .save(out, format='PNG') on the result,
      return Path(path).
    hint: >
      should_analyze: return frame_count % every_n == 0.
      save_frame: out = Path(path); frame_to_image(frame).save(out, format='PNG');
      return out.
    narration: >
      Both functions are short. should_analyze is one line. save_frame is
      three lines following the same PIL save pattern from Day 66.

  - type: summary
    heading: "Lesson 3 Summary"
    bullets:
      - "should_analyze(frame_count, every_n): frame_count % every_n == 0"
      - "frame_count=0 at first frame: first frame is always analyzed"
      - "every_n=30 at 30 FPS: analyze ~1 frame per second"
      - "save_frame: frame_to_image + PIL .save(format='PNG')"
      - "Never cv2.imshow() or plt.show() in headless environments"
    narration: >
      Lesson 4 assembles rate control and analysis into capture_frames and
      analyze_stream.
"""

_LESSON_04 = """\
day: "077"
lesson: 4
title: "capture_frames and analyze_stream"
slides:
  - type: title
    heading: "Frame Pipelines"
    subheading: "capture_frames + analyze_stream — full loops"
    narration: >
      With open_camera, read_frame, frame_to_image, analyze_frame, and
      should_analyze all in place, the two pipeline functions are short
      assemblies of those pieces. capture_frames collects raw frames.
      analyze_stream combines capture with analysis.

  - type: code
    label: "capture_frames"
    heading: "capture_frames — Collect Raw Frames"
    code: |
      def capture_frames(device=0, n_frames=5, every_n=1, camera_fn=None):
          cap = open_camera(device=device, camera_fn=camera_fn)
          frames = []
          frame_count = 0
          try:
              while len(frames) < n_frames:
                  ret, frame = read_frame(cap)
                  if not ret:
                      break
                  if should_analyze(frame_count, every_n):
                      frames.append(frame)
                  frame_count += 1
          finally:
              cap.release()
          return frames
    narration: >
      capture_frames always calls cap.release() in a finally block, matching
      the pattern from Day 74's VideoCapture usage. The distinction from
      Day 74's extract_frames is the camera_fn injection — extract_frames
      injected at the capture level, here the injection replaces the entire
      VideoCapture with a mock cap. frame_count tracks all frames read; only
      the ones passing should_analyze are appended to the output list.

  - type: code
    label: "analyze_stream"
    heading: "analyze_stream — Capture and Analyze"
    code: |
      def analyze_stream(device=0, task='Describe what you see.', n_frames=5,
                         every_n=1, camera_fn=None, analyze_fn=None):
          cap = open_camera(device=device, camera_fn=camera_fn)
          results = []
          frame_count = 0
          analyzed = 0
          try:
              while analyzed < n_frames:
                  ret, frame = read_frame(cap)
                  if not ret:
                      break
                  if should_analyze(frame_count, every_n):
                      description = analyze_frame(frame, task, analyze_fn=analyze_fn)
                      results.append({'frame_idx': frame_count, 'description': description})
                      analyzed += 1
                  frame_count += 1
          finally:
              cap.release()
          return results
    narration: >
      analyze_stream adds an analyzed counter alongside frame_count: analyzed
      stops the outer loop at n_frames analyzed frames, frame_count tracks the
      total frames consumed from the camera. The result list contains
      {frame_idx, description} dicts. frame_idx is the raw camera frame number
      (reflecting every_n skipping), not the analyzed frame index.

  - type: concept
    label: "Two counters"
    heading: "Two Counters: frame_count and analyzed"
    body: >
      Separating the read counter from the analyzed counter enables rate control.
    bullets:
      - "frame_count: every frame read from camera, including skipped ones"
      - "analyzed: frames that passed should_analyze and were sent to the LLM"
      - "Loop stops when analyzed == n_frames (not frame_count)"
      - "frame_idx in result is frame_count value (camera-relative position)"
      - "With every_n=5: frames 0, 5, 10... are analyzed; frame_count=10 yields analyzed=3"
      - "finally: cap.release() runs even if analyze_frame raises an exception"
    narration: >
      The two-counter pattern is the clean way to implement rate control in
      a streaming loop. frame_count drives the every_n modulo check.
      analyzed drives the stopping condition. Storing frame_count in the result
      preserves the temporal position of each analyzed frame relative to
      the raw camera stream.

  - type: exercise
    heading: "Exercise 4: capture_frames and analyze_stream"
    prompt: >
      Implement: (1) capture_frames(device=0, n_frames=5, every_n=1,
      camera_fn=None) -> list: open_camera with camera_fn; try: loop while
      len(frames) < n_frames; read_frame; break if not ret; if should_analyze:
      append; frame_count += 1; finally: cap.release(); return frames.
      (2) analyze_stream(device=0, task='Describe what you see.', n_frames=5,
      every_n=1, camera_fn=None, analyze_fn=None) -> list[dict]: same loop
      structure; analyze_frame on passing frames; append {frame_idx, description};
      stop when analyzed == n_frames.
    hint: >
      capture_frames: cap = open_camera(device=device, camera_fn=camera_fn);
      frames=[]; frame_count=0; try: while len(frames)<n_frames: ret,frame=read_frame(cap);
      if not ret: break; if should_analyze(frame_count,every_n): frames.append(frame);
      frame_count+=1; finally: cap.release(); return frames.
      analyze_stream: same pattern + analyzed counter + analyze_frame call.
    narration: >
      The try/finally pattern guarantees cap.release() even when the vision
      LLM call raises an exception inside the loop.

  - type: summary
    heading: "Lesson 4 Summary"
    bullets:
      - "capture_frames: open, loop, should_analyze gate, collect, finally release"
      - "analyze_stream: adds analyze_frame + {frame_idx, description} result dicts"
      - "Two counters: frame_count (all reads) and analyzed (LLM calls made)"
      - "Loop condition: analyzed < n_frames (not frame_count)"
      - "frame_idx = frame_count at analysis time (camera-relative position)"
    narration: >
      Lesson 5 wraps everything into LiveVisionAgent with a context manager.
"""

_LESSON_05 = """\
day: "077"
lesson: 5
title: "LiveVisionAgent — Context Manager Camera Agent"
slides:
  - type: title
    heading: "LiveVisionAgent"
    subheading: "Context manager + stateful vision agent"
    narration: >
      LiveVisionAgent is the Section 5 class pattern applied to real-time
      vision: bind injections at construction, delegate to module-level
      functions, track last captured frame. The context manager interface
      ensures the camera is always released, even if an exception occurs
      inside the with block.

  - type: code
    label: "constructor and open"
    heading: "Constructor, open, and close"
    code: |
      class LiveVisionAgent:
          def __init__(self, device=0, camera_fn=None, analyze_fn=None):
              self._device = device
              self._camera_fn = camera_fn
              self._analyze_fn = analyze_fn
              self._cap = None
              self._last_frame = None

          def open(self, device=None):
              d = device if device is not None else self._device
              self._cap = open_camera(device=d, camera_fn=self._camera_fn)
              return self

          def close(self):
              if self._cap is not None:
                  self._cap.release()
                  self._cap = None

          def __enter__(self):
              self.open()
              return self

          def __exit__(self, *args):
              self.close()
    narration: >
      open() calls open_camera with the stored camera_fn injection and returns
      self, enabling method chaining. close() guards against double-release by
      checking _cap is not None before calling release. __enter__ calls open()
      and returns self so the with statement binds the agent. __exit__ calls
      close() regardless of whether an exception was raised.

  - type: code
    label: "read, analyze, describe, save"
    heading: "read, analyze, describe, save"
    code: |
          def read(self):
              if self._cap is None:
                  raise RuntimeError('Camera not open.')
              ret, frame = read_frame(self._cap)
              if ret:
                  self._last_frame = frame
              return frame if ret else None

          def analyze(self, question, frame=None):
              f = frame if frame is not None else self._last_frame
              if f is None:
                  raise ValueError('No frame: call read() first or pass frame.')
              return analyze_frame(f, question, analyze_fn=self._analyze_fn)

          def describe(self, frame=None):
              return self.analyze('Describe what you see in detail.', frame=frame)

          def save(self, path, frame=None):
              f = frame if frame is not None else self._last_frame
              if f is None:
                  raise ValueError('No frame: call read() first or pass frame.')
              return save_frame(f, path)
    narration: >
      read() stores the last successful frame in _last_frame. analyze() and
      save() use frame-or-last-frame with a ValueError guard, the same pattern
      as ScreenAgent from Day 76. describe() is a one-line convenience wrapper
      around analyze() with a fixed prompt. The analyze_fn injection is
      forwarded to analyze_frame so the class is fully testable without Ollama.

  - type: concept
    label: "Context manager"
    heading: "Python Context Manager Protocol"
    body: >
      The with statement guarantees cleanup even when exceptions occur.
    bullets:
      - "__enter__: runs on with-block entry, return value bound to 'as' target"
      - "__exit__(exc_type, exc_val, tb): runs on with-block exit, even on exception"
      - "Returning None (or False) from __exit__ lets exceptions propagate"
      - "Camera pattern: __enter__ opens, __exit__ calls release"
      - "Eliminates try/finally boilerplate in caller code"
      - "Used by open(), threading.Lock(), database connections, network sockets"
    narration: >
      Context managers are the standard Python idiom for resource management.
      The camera must be released after use — whether the code succeeds or
      raises an exception. __exit__ receives exception information and can
      suppress exceptions by returning True (rarely the right choice). Here
      we return nothing (implicitly None), so exceptions propagate normally
      and the camera is still released.

  - type: exercise
    heading: "Exercise 5: LiveVisionAgent"
    prompt: >
      Implement LiveVisionAgent(device=0, camera_fn=None, analyze_fn=None).
      __init__: store all 3 + _cap=None + _last_frame=None.
      open(device=None): d = device if device is not None else self._device;
      self._cap = open_camera(device=d, camera_fn=self._camera_fn); return self.
      read(): RuntimeError if cap None; read_frame(self._cap); store if ret;
      return frame or None.
      analyze(question, frame=None): frame-or-last guard (ValueError if None);
      analyze_frame(f, question, analyze_fn=self._analyze_fn).
      describe(frame=None): self.analyze('Describe what you see in detail.', frame=frame).
      save(path, frame=None): frame-or-last guard; save_frame(f, path).
      close(): if self._cap: release + set None.
      __enter__: self.open(); return self.
      __exit__(*args): self.close().
    hint: >
      Follow the same image-or-last pattern as ScreenAgent: f = frame if
      frame is not None else self._last_frame; raise ValueError if None.
      __enter__: self.open(); return self. __exit__: self.close().
      open returns self for chaining. close guards: if self._cap is not None.
    narration: >
      LiveVisionAgent is the last deliverable of Day 77. Combined with
      ScreenAgent from Day 76, you now have agents for both screenshot
      understanding and live camera vision.

  - type: summary
    heading: "Lesson 5 Summary — Day 77 Complete"
    bullets:
      - "LiveVisionAgent: device/camera_fn/analyze_fn at construction"
      - "open(): open_camera with stored injection; returns self for chaining"
      - "close(): cap.release() + set None (guards against double-release)"
      - "__enter__: open(); __exit__: close() — context manager protocol"
      - "read(): stores _last_frame; returns None if cap exhausted"
      - "analyze/describe/save: frame-or-last-frame with ValueError guard"
      - "Tomorrow (Day 78): Capstone — Media Studio combining all modalities"
    narration: >
      Day 77 complete. LiveVisionAgent combines all the pieces built over
      Days 66 through 77: PIL Image handling, vision LLM analysis, OpenCV
      frame capture, and the injectable class pattern. Day 78 assembles
      every Section 5 skill into one Media Studio application.
"""

for i, content in enumerate([_LESSON_01, _LESSON_02, _LESSON_03,
                               _LESSON_04, _LESSON_05], start=1):
    (OUT / "lessons" / f"day_{DAY}_lesson_0{i}.yaml").write_text(content)

# ── shared mock helpers ───────────────────────────────────────────────────────
_MOCK_HELPER = """\
import numpy as np
from PIL import Image as _PILImage

def _make_mock_frame(h=100, w=100, val=50):
    return np.full((h, w, 3), val, dtype=np.uint8)

class _MockCap:
    def __init__(self, n=5, h=100, w=100):
        self._frames = [_make_mock_frame(h, w) for _ in range(n)]
        self._idx = 0
    def isOpened(self):
        return True
    def read(self):
        if self._idx >= len(self._frames):
            return False, None
        f = self._frames[self._idx]; self._idx += 1
        return True, f
    def release(self):
        pass
    def get(self, prop):
        return 0.0

_mock_camera_fn = lambda device: _MockCap(n=5)
_mock_analyze_fn = lambda img, q: 'FRAME:' + q[:12]
"""

# ── pre-built solutions for later exercises ───────────────────────────────────
_OPEN_CAMERA_SOL = """\
def open_camera(device=0, camera_fn=None):
    if camera_fn is not None:
        return camera_fn(device)
    import cv2
    cap = cv2.VideoCapture(device)
    if not cap.isOpened():
        raise RuntimeError(f'Cannot open camera device {device}')
    return cap

def read_frame(cap):
    return cap.read()
"""

_FRAME_ANALYZE_SOL = """\
import io, base64

def frame_to_image(frame):
    from PIL import Image
    rgb = frame[:, :, ::-1]
    return Image.fromarray(rgb)

def analyze_frame(frame, question, analyze_fn=None):
    image = frame_to_image(frame)
    if analyze_fn is not None:
        return analyze_fn(image, question)
    import ollama
    buf = io.BytesIO()
    image.save(buf, format='PNG')
    img_b64 = base64.b64encode(buf.getvalue()).decode()
    resp = ollama.chat(
        model='llava',
        messages=[{'role': 'user', 'content': question, 'images': [img_b64]}],
    )
    return resp['message']['content']
"""

_RATE_SAVE_SOL = """\
from pathlib import Path

def should_analyze(frame_count, every_n):
    return frame_count % every_n == 0

def save_frame(frame, path):
    out = Path(path)
    frame_to_image(frame).save(out, format='PNG')
    return out
"""

_CAPTURE_SOL = """\
def capture_frames(device=0, n_frames=5, every_n=1, camera_fn=None):
    cap = open_camera(device=device, camera_fn=camera_fn)
    frames = []
    frame_count = 0
    try:
        while len(frames) < n_frames:
            ret, frame = read_frame(cap)
            if not ret:
                break
            if should_analyze(frame_count, every_n):
                frames.append(frame)
            frame_count += 1
    finally:
        cap.release()
    return frames

def analyze_stream(device=0, task='Describe what you see.', n_frames=5,
                   every_n=1, camera_fn=None, analyze_fn=None):
    cap = open_camera(device=device, camera_fn=camera_fn)
    results = []
    frame_count = 0
    analyzed = 0
    try:
        while analyzed < n_frames:
            ret, frame = read_frame(cap)
            if not ret:
                break
            if should_analyze(frame_count, every_n):
                description = analyze_frame(frame, task, analyze_fn=analyze_fn)
                results.append({'frame_idx': frame_count, 'description': description})
                analyzed += 1
            frame_count += 1
    finally:
        cap.release()
    return results
"""

_AGENT_SOL = """\
class LiveVisionAgent:
    def __init__(self, device=0, camera_fn=None, analyze_fn=None):
        self._device = device
        self._camera_fn = camera_fn
        self._analyze_fn = analyze_fn
        self._cap = None
        self._last_frame = None

    def open(self, device=None):
        d = device if device is not None else self._device
        self._cap = open_camera(device=d, camera_fn=self._camera_fn)
        return self

    def read(self):
        if self._cap is None:
            raise RuntimeError('Camera not open: call open() first or use as context manager.')
        ret, frame = read_frame(self._cap)
        if ret:
            self._last_frame = frame
        return frame if ret else None

    def analyze(self, question, frame=None):
        f = frame if frame is not None else self._last_frame
        if f is None:
            raise ValueError('No frame: call read() first or pass frame.')
        return analyze_frame(f, question, analyze_fn=self._analyze_fn)

    def describe(self, frame=None):
        return self.analyze('Describe what you see in detail.', frame=frame)

    def save(self, path, frame=None):
        f = frame if frame is not None else self._last_frame
        if f is None:
            raise ValueError('No frame: call read() first or pass frame.')
        return save_frame(f, path)

    def close(self):
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *args):
        self.close()
"""

# ── EX1: open_camera + read_frame ────────────────────────────────────────────
_EX1_STUB = """\
def open_camera(device=0, camera_fn=None):
    \"\"\"Open a camera device and return a VideoCapture-compatible object.\"\"\"
    raise NotImplementedError

def read_frame(cap):
    \"\"\"Read one frame. Returns (success: bool, frame: ndarray|None).\"\"\"
    raise NotImplementedError
"""

_EX1_CHECKS = r"""
score, total = 0, 4
try:
    cap = open_camera(device=0, camera_fn=_mock_camera_fn)
    assert cap is not None and cap.isOpened()
    score += 1; print("✅ open_camera returns cap via camera_fn")

    device_seen = []
    def _dfn(d): device_seen.append(d); return _MockCap(n=2)
    open_camera(device=99, camera_fn=_dfn)
    assert device_seen == [99], f"device not forwarded: {device_seen}"
    score += 1; print("✅ device argument forwarded to camera_fn")

    cap2 = _MockCap(n=2)
    ret, frame = read_frame(cap2)
    assert ret is True and frame is not None
    score += 1; print("✅ read_frame returns (True, frame) on valid cap")

    cap3 = _MockCap(n=1)
    read_frame(cap3)
    ret2, frame2 = read_frame(cap3)
    assert ret2 is False and frame2 is None
    score += 1; print("✅ read_frame returns (False, None) when exhausted")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX1 = nb([
    md("# Day 077 — Exercise 1: open_camera and read_frame\n\n"
       "**What you'll build:** The two camera primitives.\n\n"
       "**Why it matters:** Every function in `live_vision.py` builds on these. "
       "The `camera_fn` injection means the entire pipeline runs in a headless "
       "test environment without a real camera."),
    code(_MOCK_HELPER),
    md("## Task\n\n"
       "1. `open_camera(device=0, camera_fn=None) -> cap`\n"
       "   - If `camera_fn` is not None: `return camera_fn(device)`\n"
       "   - Else: `import cv2; cap = cv2.VideoCapture(device)`; "
       "raise `RuntimeError` if `not cap.isOpened()`; return cap\n\n"
       "2. `read_frame(cap) -> (bool, ndarray|None)`\n"
       "   - One line: `return cap.read()`"),
    md("## Your Implementation"),
    code(_EX1_STUB),
    code(_OPEN_CAMERA_SOL),
    md("## Automated checks"),
    code(_EX1_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _OPEN_CAMERA_SOL + "```\n\n"
       "**Why import cv2 inside the else branch?** Avoids import errors on "
       "machines without opencv installed. The module loads cleanly in any "
       "environment; cv2 is only imported when actually needed.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_01.ipynb", EX1)

# ── EX2: frame_to_image + analyze_frame ──────────────────────────────────────
_EX2_STUB = """\
import io, base64

def frame_to_image(frame):
    \"\"\"Convert BGR ndarray to PIL Image in RGB mode.\"\"\"
    raise NotImplementedError

def analyze_frame(frame, question, analyze_fn=None):
    \"\"\"Analyze a camera frame with a vision LLM.\"\"\"
    raise NotImplementedError
"""

_EX2_CHECKS = r"""
score, total = 0, 5
try:
    import numpy as np
    from PIL import Image as PILImage

    frame = _make_mock_frame(60, 80)  # (60, 80, 3) BGR
    img = frame_to_image(frame)
    assert isinstance(img, PILImage.Image), f"expected PIL Image, got {type(img)}"
    score += 1; print("✅ frame_to_image returns PIL Image")

    assert img.size == (80, 60), f"size mismatch: {img.size} (expected (80,60))"
    score += 1; print("✅ frame_to_image size correct (width, height)")

    # Check channel reversal: BGR(50,100,150) -> RGB(150,100,50)
    bgr_frame = np.full((10, 10, 3), 0, dtype=np.uint8)
    bgr_frame[:, :, 0] = 50   # B
    bgr_frame[:, :, 1] = 100  # G
    bgr_frame[:, :, 2] = 150  # R
    pil_img = frame_to_image(bgr_frame)
    r, g, b = pil_img.getpixel((0, 0))
    assert r == 150 and g == 100 and b == 50, f"channel flip wrong: R={r},G={g},B={b}"
    score += 1; print("✅ BGR->RGB channel reversal correct")

    result = analyze_frame(frame, 'Q?', analyze_fn=_mock_analyze_fn)
    assert isinstance(result, str)
    score += 1; print("✅ analyze_frame returns str via analyze_fn")

    received = {}
    def _afn(img, q): received.update(img=img, q=q); return 'OK'
    analyze_frame(frame, 'test?', analyze_fn=_afn)
    assert isinstance(received.get('img'), PILImage.Image), "analyze_fn should receive PIL Image"
    assert received.get('q') == 'test?'
    score += 1; print("✅ analyze_fn receives (PIL Image, question)")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX2 = nb([
    md("# Day 077 — Exercise 2: frame_to_image and analyze_frame\n\n"
       "**What you'll build:** Convert BGR frames to PIL Images and analyze "
       "them with a vision LLM.\n\n"
       "**Why it matters:** OpenCV stores frames in BGR order; PIL, Ollama, and "
       "all Section 5 tools expect RGB. `frame_to_image` bridges the two worlds. "
       "`analyze_frame` chains conversion with the Day 76 vision pipeline."),
    code(_MOCK_HELPER),
    md("## Task\n\n"
       "1. `frame_to_image(frame) -> PIL.Image`\n"
       "   - `rgb = frame[:, :, ::-1]` — reverse channel axis (BGR → RGB)\n"
       "   - `return Image.fromarray(rgb)` (from PIL import Image)\n\n"
       "2. `analyze_frame(frame, question, analyze_fn=None) -> str`\n"
       "   - `image = frame_to_image(frame)`\n"
       "   - If `analyze_fn`: `return analyze_fn(image, question)`\n"
       "   - Else: BytesIO + PNG save + base64 + `ollama.chat(model='llava', ...)` + "
       "return `resp['message']['content']`"),
    md("## Your Implementation"),
    code(_EX2_STUB),
    code(_FRAME_ANALYZE_SOL),
    md("## Automated checks"),
    code(_EX2_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _FRAME_ANALYZE_SOL + "```\n\n"
       "**Why does `analyze_fn` receive a PIL Image, not the BGR ndarray?** "
       "The conversion is an implementation detail. All mock functions and "
       "the real Ollama call work with PIL Images, so the mock doesn't need "
       "to know or care about BGR arrays.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_02.ipynb", EX2)

# ── EX3: should_analyze + save_frame ─────────────────────────────────────────
_EX3_GIVEN = _MOCK_HELPER + _FRAME_ANALYZE_SOL

_EX3_STUB = """\
from pathlib import Path

def should_analyze(frame_count, every_n):
    \"\"\"Return True if this frame should be analyzed (every_n rate control).\"\"\"
    raise NotImplementedError

def save_frame(frame, path):
    \"\"\"Save a BGR frame to disk as PNG. Returns Path.\"\"\"
    raise NotImplementedError
"""

_EX3_CHECKS = r"""
score, total = 0, 5
try:
    import tempfile, os

    assert should_analyze(0, 1) is True
    assert should_analyze(1, 1) is True
    score += 1; print("✅ every_n=1: all frames analyzed")

    assert should_analyze(0, 5) is True
    assert should_analyze(5, 5) is True
    assert should_analyze(10, 5) is True
    assert should_analyze(1, 5) is False
    assert should_analyze(4, 5) is False
    score += 1; print("✅ every_n=5: frames 0,5,10,... only")

    assert should_analyze(0, 30) is True
    assert should_analyze(29, 30) is False
    assert should_analyze(30, 30) is True
    score += 1; print("✅ every_n=30 correct")

    frame = _make_mock_frame(50, 50)
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        tmp = f.name
    try:
        result = save_frame(frame, tmp)
        assert str(result) == tmp, f"returned path mismatch: {result}"
        score += 1; print("✅ save_frame returns correct Path")
        assert os.path.getsize(tmp) > 0, "file is empty"
        score += 1; print("✅ save_frame writes non-empty PNG file")
    finally:
        os.unlink(tmp)

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX3 = nb([
    md("# Day 077 — Exercise 3: should_analyze and save_frame\n\n"
       "**What you'll build:** Rate control and frame persistence.\n\n"
       "**Why it matters:** Vision LLMs are slow (2-10 s/frame). Analyzing "
       "every camera frame at 30 FPS is impossible. `should_analyze` selects "
       "frames at a controlled rate. `save_frame` persists frames without any "
       "display — `cv2.imshow()` and `plt.show()` both require a display server."),
    code(_EX3_GIVEN),
    md("## Task\n\n"
       "1. `should_analyze(frame_count, every_n) -> bool`\n"
       "   - One line: `return frame_count % every_n == 0`\n\n"
       "2. `save_frame(frame, path) -> Path`\n"
       "   - `out = Path(path)`\n"
       "   - `frame_to_image(frame).save(out, format='PNG')`\n"
       "   - `return out`"),
    md("## Your Implementation"),
    code(_EX3_STUB),
    code(_RATE_SAVE_SOL),
    md("## Automated checks"),
    code(_EX3_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _RATE_SAVE_SOL + "```\n\n"
       "**Why not `cv2.imwrite`?** PIL is already established for all Section 5 "
       "image I/O. Using `frame_to_image + PIL.save` keeps the code consistent "
       "and avoids any display-related cv2 paths.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_03.ipynb", EX3)

# ── EX4: capture_frames + analyze_stream ─────────────────────────────────────
_EX4_GIVEN = _MOCK_HELPER + _OPEN_CAMERA_SOL + _FRAME_ANALYZE_SOL + _RATE_SAVE_SOL

_EX4_STUB = """\
def capture_frames(device=0, n_frames=5, every_n=1, camera_fn=None):
    \"\"\"Capture n_frames from a camera, rate-controlled by every_n.\"\"\"
    raise NotImplementedError

def analyze_stream(device=0, task='Describe what you see.', n_frames=5,
                   every_n=1, camera_fn=None, analyze_fn=None):
    \"\"\"Capture and analyze n_frames. Returns list of {frame_idx, description}.\"\"\"
    raise NotImplementedError
"""

_EX4_CHECKS = r"""
score, total = 0, 5
try:
    import numpy as np

    frames = capture_frames(n_frames=3, camera_fn=_mock_camera_fn)
    assert isinstance(frames, list) and len(frames) == 3
    score += 1; print("✅ capture_frames returns 3 frames")

    assert all(isinstance(f, np.ndarray) for f in frames)
    score += 1; print("✅ each frame is an ndarray")

    # every_n=2: frames 0, 2, 4 -> 3 frames from a 6-frame cap
    cap6 = _MockCap(n=6)
    frames2 = capture_frames(n_frames=3, every_n=2,
                              camera_fn=lambda d: _MockCap(n=6))
    assert len(frames2) == 3
    score += 1; print("✅ capture_frames respects every_n")

    results = analyze_stream(n_frames=2, camera_fn=_mock_camera_fn,
                              analyze_fn=_mock_analyze_fn)
    assert isinstance(results, list) and len(results) == 2
    score += 1; print("✅ analyze_stream returns 2 result dicts")

    assert all('frame_idx' in r and 'description' in r for r in results)
    score += 1; print("✅ each result has frame_idx and description")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX4 = nb([
    md("# Day 077 — Exercise 4: capture_frames and analyze_stream\n\n"
       "**What you'll build:** Full pipeline loops — capture and optionally analyze "
       "n frames from a camera with rate control.\n\n"
       "**Why it matters:** These are the batch interfaces. `capture_frames` collects "
       "raw frames for offline processing. `analyze_stream` is the real-time vision "
       "loop — capture + analyze in one call."),
    code(_EX4_GIVEN),
    md("## Task\n\n"
       "1. `capture_frames(device=0, n_frames=5, every_n=1, camera_fn=None) -> list`\n"
       "   - `cap = open_camera(device=device, camera_fn=camera_fn)`\n"
       "   - `frames=[]; frame_count=0`; `try`: loop `while len(frames) < n_frames`:\n"
       "     - `ret, frame = read_frame(cap)` → `break` if not ret\n"
       "     - `if should_analyze(frame_count, every_n): frames.append(frame)`\n"
       "     - `frame_count += 1`\n"
       "   - `finally: cap.release()`; `return frames`\n\n"
       "2. `analyze_stream(device=0, task=..., n_frames=5, every_n=1, camera_fn=None, analyze_fn=None) -> list[dict]`\n"
       "   - Same loop but with `analyzed` counter (stops at `n_frames` analyzed)\n"
       "   - Analyze passing frames: `analyze_frame(frame, task, analyze_fn=analyze_fn)`\n"
       "   - Append `{'frame_idx': frame_count, 'description': description}`"),
    md("## Your Implementation"),
    code(_EX4_STUB),
    code(_CAPTURE_SOL),
    md("## Automated checks"),
    code(_EX4_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _CAPTURE_SOL + "```\n\n"
       "**Why two counters in analyze_stream?** `frame_count` tracks all frames "
       "read (drives the every_n modulo check). `analyzed` tracks frames sent to "
       "the LLM (drives the stopping condition). Mixing them would break rate control.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_04.ipynb", EX4)

# ── EX5: LiveVisionAgent ──────────────────────────────────────────────────────
_EX5_GIVEN = (_MOCK_HELPER + _OPEN_CAMERA_SOL + _FRAME_ANALYZE_SOL
              + _RATE_SAVE_SOL + _CAPTURE_SOL)

_EX5_STUB = """\
class LiveVisionAgent:
    \"\"\"Context-manager camera agent with vision analysis.\"\"\"

    def __init__(self, device=0, camera_fn=None, analyze_fn=None):
        raise NotImplementedError

    def open(self, device=None):
        raise NotImplementedError

    def read(self):
        raise NotImplementedError

    def analyze(self, question, frame=None):
        raise NotImplementedError

    def describe(self, frame=None):
        raise NotImplementedError

    def save(self, path, frame=None):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError

    def __enter__(self):
        raise NotImplementedError

    def __exit__(self, *args):
        raise NotImplementedError
"""

_EX5_CHECKS = r"""
score, total = 0, 6
try:
    import numpy as np, tempfile, os

    agent = LiveVisionAgent(camera_fn=_mock_camera_fn, analyze_fn=_mock_analyze_fn)
    agent.open()
    assert agent._cap is not None
    score += 1; print("✅ open() sets _cap")

    frame = agent.read()
    assert isinstance(frame, np.ndarray)
    assert agent._last_frame is not None
    score += 1; print("✅ read() returns ndarray and stores _last_frame")

    desc = agent.describe()
    assert isinstance(desc, str)
    score += 1; print("✅ describe() returns str using stored frame")

    a = agent.analyze('What color?')
    assert isinstance(a, str)
    score += 1; print("✅ analyze() returns str")

    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        tmp = f.name
    try:
        p = agent.save(tmp)
        assert os.path.getsize(tmp) > 0
        score += 1; print("✅ save() writes non-empty PNG")
    finally:
        os.unlink(tmp)

    agent.close()
    assert agent._cap is None
    score += 1; print("✅ close() releases cap and sets None")

    # Context manager
    with LiveVisionAgent(camera_fn=_mock_camera_fn, analyze_fn=_mock_analyze_fn) as a2:
        f2 = a2.read()
        assert isinstance(f2, np.ndarray)
    assert a2._cap is None, "cap should be released after with block"
    print("✅ context manager: cap released on __exit__")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX5 = nb([
    md("# Day 077 — Exercise 5: LiveVisionAgent\n\n"
       "**What you'll build:** `LiveVisionAgent` — a context-manager camera agent "
       "that opens a camera, reads frames, and analyzes them with a vision LLM.\n\n"
       "**Why it matters:** The context manager (`with` statement) guarantees the "
       "camera is always released — even if an exception occurs inside the `with` block. "
       "This is the standard Python pattern for any resource that must be explicitly closed."),
    code(_EX5_GIVEN),
    md("## Task\n\n"
       "Implement `LiveVisionAgent(device=0, camera_fn=None, analyze_fn=None)`:\n\n"
       "- `__init__`: store device/camera_fn/analyze_fn; `_cap=None`, `_last_frame=None`\n"
       "- `open(device=None)`: `d = device if device is not None else self._device`; "
       "`self._cap = open_camera(d, camera_fn=self._camera_fn)`; `return self`\n"
       "- `read()`: RuntimeError if `_cap` is None; `ret, frame = read_frame(self._cap)`; "
       "store if ret; return frame or None\n"
       "- `analyze(question, frame=None)`: frame-or-last guard (ValueError); "
       "`analyze_frame(f, question, analyze_fn=self._analyze_fn)`\n"
       "- `describe(frame=None)`: `self.analyze('Describe what you see in detail.', frame=frame)`\n"
       "- `save(path, frame=None)`: frame-or-last guard; `save_frame(f, path)`\n"
       "- `close()`: `if self._cap: self._cap.release(); self._cap = None`\n"
       "- `__enter__`: `self.open(); return self`\n"
       "- `__exit__(*args)`: `self.close()`"),
    md("## Your Implementation"),
    code(_EX5_STUB),
    code(_AGENT_SOL),
    md("## Automated checks"),
    code(_EX5_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _AGENT_SOL + "```\n\n"
       "**Why `f = frame if frame is not None else self._last_frame`** instead of "
       "`frame or self._last_frame`? A valid frame ndarray is truthy, but an explicit "
       "`is not None` check is clearer about intent and handles edge cases like "
       "a zero-value frame array.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_05.ipynb", EX5)

# ── PROJECT NOTEBOOK ──────────────────────────────────────────────────────────
PROJECT = nb([
    md(f"# Day {DAY} — Project: Real-Time Vision Agent\n\n"
       "## Objective\n\n"
       "Build `live_vision.py` — a real-time vision agent that captures camera "
       "frames and analyzes them with a vision LLM.\n\n"
       "## Deliverable\n\n"
       "`live_vision.py` with:\n\n"
       "- `open_camera(device=0, camera_fn=None) -> cap`\n"
       "- `read_frame(cap) -> (bool, ndarray|None)`\n"
       "- `frame_to_image(frame) -> PIL.Image`\n"
       "- `analyze_frame(frame, question, analyze_fn=None) -> str`\n"
       "- `save_frame(frame, path) -> Path`\n"
       "- `should_analyze(frame_count, every_n) -> bool`\n"
       "- `capture_frames(device=0, n_frames=5, every_n=1, camera_fn=None) -> list`\n"
       "- `analyze_stream(device=0, task=..., n_frames=5, every_n=1, camera_fn=None, analyze_fn=None) -> list[dict]`\n"
       "- `LiveVisionAgent(device=0, camera_fn=None, analyze_fn=None)` with "
       "`open`, `read`, `analyze`, `describe`, `save`, `close`, `__enter__`, `__exit__`\n\n"
       "## Usage (with real webcam and Ollama)\n\n"
       "```python\n"
       "with LiveVisionAgent() as agent:\n"
       "    frame = agent.read()\n"
       "    print(agent.describe())\n"
       "    agent.save('frame.png')\n"
       "```"),
    code("# Your implementation here — build LiveVisionAgent and write live_vision.py\n"),
])
save(OUT / "project" / "project.ipynb", PROJECT)

# ── SOLUTION NOTEBOOK ─────────────────────────────────────────────────────────
_SOL_CELL1 = (
    f"_SRC = {repr(_LIVE_VISION_SRC)}\n"
    "from pathlib import Path\n"
    "Path('live_vision.py').write_text(_SRC, encoding='utf-8')\n"
    "print('live_vision.py written.')"
)

_SOL_CELL2 = r"""
import numpy as np
from pathlib import Path
from live_vision import (
    open_camera, read_frame, frame_to_image, analyze_frame,
    save_frame, should_analyze, capture_frames, analyze_stream,
    LiveVisionAgent,
)
from PIL import Image as PILImage

def _make_frame(h=100, w=100, val=50):
    return np.full((h, w, 3), val, dtype=np.uint8)

class _MockCap:
    def __init__(self, n=5):
        self._frames = [_make_frame() for _ in range(n)]
        self._idx = 0
    def isOpened(self): return True
    def read(self):
        if self._idx >= len(self._frames): return False, None
        f = self._frames[self._idx]; self._idx += 1
        return True, f
    def release(self): pass
    def get(self, p): return 0.0

_mock_camera_fn = lambda d: _MockCap(n=5)
_mock_analyze_fn = lambda img, q: 'FRAME:' + q[:12]

# 1. open_camera
cap = open_camera(device=0, camera_fn=_mock_camera_fn)
assert cap.isOpened()
print("✅ open_camera")

# 2. read_frame
ret, frame = read_frame(cap)
assert ret and isinstance(frame, np.ndarray)
print("✅ read_frame")

# 3. frame_to_image
img = frame_to_image(frame)
assert isinstance(img, PILImage.Image)
print("✅ frame_to_image")

# 4. analyze_frame
r = analyze_frame(frame, 'Q?', analyze_fn=_mock_analyze_fn)
assert isinstance(r, str)
print("✅ analyze_frame")

# 5. save_frame
import tempfile, os
with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
    tmp = f.name
try:
    p = save_frame(frame, tmp)
    assert os.path.getsize(tmp) > 0
    print("✅ save_frame")
finally:
    os.unlink(tmp)

# 6. should_analyze
assert should_analyze(0, 5) and should_analyze(5, 5)
assert not should_analyze(1, 5) and not should_analyze(4, 5)
print("✅ should_analyze")

# 7. capture_frames
frames = capture_frames(n_frames=3, camera_fn=_mock_camera_fn)
assert len(frames) == 3 and all(isinstance(f, np.ndarray) for f in frames)
print("✅ capture_frames")

# 8. analyze_stream
results = analyze_stream(n_frames=2, camera_fn=_mock_camera_fn, analyze_fn=_mock_analyze_fn)
assert len(results) == 2 and all('frame_idx' in r and 'description' in r for r in results)
print("✅ analyze_stream")

# 9. LiveVisionAgent
with LiveVisionAgent(camera_fn=_mock_camera_fn, analyze_fn=_mock_analyze_fn) as agent:
    f = agent.read()
    assert isinstance(f, np.ndarray)
    d = agent.describe()
    assert isinstance(d, str)
assert agent._cap is None
print("✅ LiveVisionAgent (context manager)")

print("\nReal-Time Vision Agent complete!")
"""

SOLUTION = nb([
    md(f"# Day {DAY} — Solution: Real-Time Vision Agent"),
    code(_SOL_CELL1),
    code(_SOL_CELL2),
])
save(OUT / "project" / "solution" / "solution.ipynb", SOLUTION)
(OUT / "project" / "solution" / "live_vision.py").write_text(_LIVE_VISION_SRC)

print(f"Day {DAY} notebooks written to {OUT}")
print("  lessons/    day_077_lesson_01.yaml – lesson_05.yaml")
print("  exercises/  exercise_01 – exercise_05")
print("  project/    project.ipynb")
print("  project/solution/  solution.ipynb + live_vision.py")
