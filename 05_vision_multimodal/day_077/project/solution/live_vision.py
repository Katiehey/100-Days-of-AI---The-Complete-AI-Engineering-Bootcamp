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
