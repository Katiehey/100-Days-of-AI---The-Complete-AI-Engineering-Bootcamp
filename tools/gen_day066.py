#!/usr/bin/env python3
"""gen_day066.py — generate Day 066: Images in Python."""
from pathlib import Path
import json

ROOT    = Path(__file__).parent.parent
DAY     = "066"
SECTION = "05_vision_multimodal"
OUT     = ROOT / SECTION / f"day_{DAY}"

(OUT / "exercises").mkdir(parents=True, exist_ok=True)
(OUT / "lessons").mkdir(parents=True, exist_ok=True)
(OUT / "project" / "solution").mkdir(parents=True, exist_ok=True)

# ── deliverable: image_utils.py ───────────────────────────────────────────────
_UTILS_SRC = '''\
"""image_utils.py — Day 066: Chainable image-processing utility.

Usage:
    from image_utils import ImageProcessor
    img = (ImageProcessor.new(800, 600, color=(200, 220, 240))
           .resize(400, 300)
           .apply_filter("sharpen")
           .save("output.png"))
"""
import io
from pathlib import Path
from PIL import Image, ImageFilter, ImageEnhance

_FILTERS = {
    "blur":         ImageFilter.BLUR,
    "sharpen":      ImageFilter.SHARPEN,
    "edge_enhance": ImageFilter.EDGE_ENHANCE,
    "contour":      ImageFilter.CONTOUR,
}


class ImageProcessor:
    """Chainable image processing pipeline.

    Every mutating method returns self so calls can be chained.
    """

    def __init__(self, img: Image.Image) -> None:
        self._img = img.copy()

    @classmethod
    def from_file(cls, path: str) -> "ImageProcessor":
        return cls(Image.open(path))

    @classmethod
    def new(cls, width: int, height: int,
            color: tuple = (255, 255, 255)) -> "ImageProcessor":
        return cls(Image.new("RGB", (width, height), color=color))

    @property
    def image(self) -> Image.Image:
        return self._img.copy()

    @property
    def size(self) -> tuple:
        return self._img.size

    @property
    def mode(self) -> str:
        return self._img.mode

    def resize(self, width: int, height: int) -> "ImageProcessor":
        self._img = self._img.resize((width, height), Image.Resampling.LANCZOS)
        return self

    def crop_center(self, width: int, height: int) -> "ImageProcessor":
        iw, ih = self._img.size
        left = (iw - width) // 2
        top  = (ih - height) // 2
        self._img = self._img.crop((left, top, left + width, top + height))
        return self

    def to_grayscale(self) -> "ImageProcessor":
        self._img = self._img.convert("L")
        return self

    def convert_mode(self, mode: str) -> "ImageProcessor":
        self._img = self._img.convert(mode)
        return self

    def apply_filter(self, filter_name: str) -> "ImageProcessor":
        f = _FILTERS.get(filter_name.lower())
        if f is None:
            raise ValueError(
                f"Unknown filter: {filter_name!r}. Available: {list(_FILTERS)}"
            )
        self._img = self._img.filter(f)
        return self

    def adjust_brightness(self, factor: float) -> "ImageProcessor":
        self._img = ImageEnhance.Brightness(self._img).enhance(factor)
        return self

    def adjust_contrast(self, factor: float) -> "ImageProcessor":
        self._img = ImageEnhance.Contrast(self._img).enhance(factor)
        return self

    def save(self, path: str, **kwargs) -> str:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        out = self._img
        if p.suffix.lower() in (".jpg", ".jpeg") and self._img.mode in ("RGBA", "P"):
            out = self._img.convert("RGB")
        out.save(path, **kwargs)
        return path

    def to_bytes(self, format: str = "PNG") -> bytes:
        buf = io.BytesIO()
        out = self._img
        if format.upper() in ("JPEG", "JPG") and self._img.mode in ("RGBA", "P"):
            out = self._img.convert("RGB")
        out.save(buf, format=format)
        return buf.getvalue()
'''

# ── notebook helpers ───────────────────────────────────────────────────────────
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
day: "066"
lesson: 1
title: "Images in Python — PIL/Pillow"
slides:
  - type: title
    heading: "Images in Python"
    subheading: "Section 5, Day 66 — PIL/Pillow Fundamentals"
    narration: >
      Welcome to Section 5 — Vision and Multimodal. Over the next 13 days you
      will give your AI apps eyes and ears, working with images, audio, and
      video. Day 66 is the foundation: reading, creating, and inspecting
      images entirely in Python using the Pillow library.

  - type: concept
    label: "What is a digital image?"
    heading: "Pixels, Channels, and Modes"
    body: >
      An image is a rectangular grid of pixels. Each pixel stores one number
      per channel. The mode string describes the channel layout.
    bullets:
      - "RGB — 3 channels (red, green, blue); standard for photos"
      - "RGBA — 4 channels; RGB plus transparency (alpha)"
      - "L — 1 channel (luminance); grayscale"
      - "Each channel is an integer 0–255 (8-bit per channel)"
    narration: >
      Before writing any code, understand what a digital image actually is.
      It is a rectangular grid — width times height pixels. Each pixel stores
      one number per channel. RGB images have three channels: red, green, and
      blue. RGBA adds a fourth transparency channel. L mode stores a single
      luminance value per pixel — that is grayscale. The mode is something you
      will query constantly in Pillow, so get familiar with it now.

  - type: how_it_works
    label: "Pillow"
    heading: "The Pillow Library"
    body: >
      Pillow is the maintained fork of PIL. Install as pillow, import as PIL.
      It is the de-facto standard for image I/O in Python — used by OpenCV
      Python bindings, torchvision, scikit-image, and many others.
    narration: >
      Pillow ships on pip as the package named pillow, but you import it as
      PIL. It is the lingua franca of Python imaging. OpenCV's Python
      bindings, scikit-image, and torchvision all either accept Pillow images
      or export to them. Once you know Pillow you can work with any image
      library. You already have it installed in this course environment.

  - type: code
    label: "Creating images"
    heading: "Image.new and Image.fromarray"
    code: |
      from PIL import Image
      import numpy as np

      # Solid-colour synthetic image — no file needed
      img = Image.new('RGB', (200, 100), color=(255, 128, 0))
      print(img.size)   # (200, 100) — width, height
      print(img.mode)   # 'RGB'

      # From a NumPy array — shape is (height, width, channels)
      arr = np.random.randint(0, 255, (100, 200, 3), dtype=np.uint8)
      img2 = Image.fromarray(arr)
      print(img2.size)  # (200, 100) — PIL flips to (width, height)
    narration: >
      Image.new takes a mode string, a width-height tuple, and a colour. Note
      that PIL size is always width-comma-height — not height-comma-width like
      NumPy arrays. NumPy uses row-major order so the shape is height, width,
      channels. When you convert between PIL and NumPy, this axis swap is the
      number one cause of accidentally transposed images. Keep it front of
      mind.

  - type: code
    label: "I/O"
    heading: "Image.open, Image.save, and BytesIO"
    code: |
      import io
      from PIL import Image

      img = Image.new('RGB', (100, 100), color=(0, 128, 255))

      # Save to / load from disk
      img.save('test.png')
      loaded = Image.open('test.png')
      print(loaded.size, loaded.mode)  # (100, 100) RGB

      # Save to / load from memory — no disk I/O
      buf = io.BytesIO()
      img.save(buf, format='PNG')
      buf.seek(0)            # rewind before reading back!
      reloaded = Image.open(buf)
      print(reloaded.size)   # (100, 100)
    narration: >
      Image.save and Image.open both accept a file path or a BytesIO buffer.
      When saving to a buffer, call buf.seek zero before reading it back —
      writing advances the pointer to the end of the data. The in-memory
      BytesIO pattern is essential for notebooks and APIs: you pass bytes
      without touching the filesystem. You will use this pattern constantly in
      the rest of this section.

  - type: exercise
    heading: "Exercise 1: Get Image Info"
    prompt: >
      Implement get_image_info(img) returning a dict with keys 'width',
      'height', 'mode', and 'num_channels'. Use a lookup for known modes
      (RGB=3, RGBA=4, L=1) and len(img.getbands()) for anything else.
    hint: >
      img.size returns (width, height). img.mode is a string like 'RGB'.
      img.getbands() returns a tuple of band names.
    narration: >
      For your first exercise you will inspect an image and return structured
      metadata. Every image pipeline starts with understanding what you are
      working with — size, mode, channel count. This kind of info function
      appears in every computer vision system and will be useful when you pass
      images to vision models later in this section.

  - type: summary
    heading: "Lesson 1 Summary"
    bullets:
      - "Image = pixel grid; each pixel has N values (one per channel)"
      - "PIL modes: RGB (3ch), RGBA (4ch), L (1ch grayscale)"
      - "Image.new — create synthetic images; no file required"
      - "PIL size = (width, height); NumPy shape = (height, width, channels)"
      - "BytesIO — in-memory I/O; always seek(0) before reading"
    narration: >
      The foundations are in place. You understand the pixel-channel-mode
      model, you can create images without touching the filesystem, and you
      know the size versus shape difference between PIL and NumPy. Next: how
      image formats differ and when to choose each one.
"""

_LESSON_02 = """\
day: "066"
lesson: 2
title: "Image Formats and I/O"
slides:
  - type: title
    heading: "Image Formats and I/O"
    subheading: "PNG, JPEG, BMP — and the BytesIO pattern"
    narration: >
      Images can be stored in many formats. Choosing the wrong one costs
      quality or storage. This lesson covers the three formats you will
      encounter most: PNG, JPEG, and BMP — and the in-memory I/O pattern
      that lets you work with images as bytes rather than files.

  - type: concept
    label: "Raster formats"
    heading: "PNG vs JPEG vs BMP"
    body: >
      The three most common raster formats differ in compression strategy
      and intended use.
    bullets:
      - "PNG — lossless compression; supports transparency (RGBA); ideal for
        screenshots and diagrams"
      - "JPEG — lossy compression; no alpha; small files; ideal for photos"
      - "BMP — uncompressed; exact pixel values; large files; legacy format"
    narration: >
      PNG uses lossless compression — every pixel is stored exactly. It
      supports RGBA transparency. Use PNG for diagrams, screenshots, and
      anything where you need exact pixel values. JPEG uses lossy
      compression — it throws away information to make files much smaller.
      It does not support transparency. Use JPEG for photographs. BMP is
      uncompressed — it stores every byte of every pixel. The files are
      large, but there is no compression artefact. You will mostly encounter
      BMP in legacy pipelines or as an intermediate format.

  - type: how_it_works
    label: "BytesIO pattern"
    heading: "In-Memory I/O with BytesIO"
    body: >
      io.BytesIO wraps a byte buffer as a file-like object. PIL can save to
      and load from it. No file is ever written to disk.
    narration: >
      The BytesIO pattern is the backbone of image processing in APIs and
      notebooks. Instead of writing a file to disk and reading it back, you
      pass a buffer. This works because PIL treats BytesIO identically to a
      real file. Three steps: create an empty buffer, save into it, seek back
      to zero. From that point, you can pass the buffer to anything that
      accepts a file-like object — or call getvalue to get raw bytes.

  - type: code
    label: "Format conversion"
    heading: "Saving Different Formats"
    code: |
      import io
      from PIL import Image

      rgb = Image.new('RGB', (100, 100), color=(200, 100, 50))

      # Save as different formats to BytesIO
      def to_bytes(img, fmt):
          buf = io.BytesIO()
          img.save(buf, format=fmt)
          return buf.getvalue()

      png_data  = to_bytes(rgb, 'PNG')
      jpeg_data = to_bytes(rgb, 'JPEG')
      print(f"PNG : {len(png_data):,} bytes")
      print(f"JPEG: {len(jpeg_data):,} bytes")  # typically much smaller

      # RGBA → JPEG requires mode conversion (JPEG has no alpha)
      rgba = rgb.convert('RGBA')
      jpeg_safe = to_bytes(rgba.convert('RGB'), 'JPEG')
    narration: >
      The to_bytes helper is a pattern you will use throughout this section.
      Create a BytesIO buffer, save into it with a format string, and call
      getvalue to get the raw bytes. Notice that JPEG is typically much
      smaller than PNG for photographic content. Also notice the RGBA to JPEG
      issue: JPEG has no alpha channel, so you must convert RGBA to RGB
      before saving as JPEG — Pillow will raise an error otherwise.

  - type: code
    label: "Round-trip"
    heading: "Bytes → Image Round-trip"
    code: |
      import io
      from PIL import Image

      original = Image.new('RGB', (64, 64), color=(0, 200, 100))

      # Encode to bytes
      buf = io.BytesIO()
      original.save(buf, format='PNG')
      raw_bytes = buf.getvalue()

      # Decode back from bytes
      buf2 = io.BytesIO(raw_bytes)
      restored = Image.open(buf2)
      restored.load()          # force decoding before buffer goes away
      print(restored.size, restored.mode)   # (64, 64) RGB
    narration: >
      To decode bytes back to a PIL Image, wrap them in a new BytesIO and
      call Image.open. One critical detail: call restored.load() to force
      Pillow to actually decode the image data before you close or reuse the
      buffer. Pillow is lazy — it defers decoding until you access pixel
      data. If the buffer gets garbage-collected first, you get a broken
      image. Calling load makes the decode immediate and safe.

  - type: exercise
    heading: "Exercise 2: Image to Bytes"
    prompt: >
      Implement image_to_bytes(img, format='PNG') -> bytes. Save the PIL
      Image to a BytesIO buffer and return the bytes. For JPEG output,
      automatically convert RGBA or P mode images to RGB first.
    hint: >
      Create io.BytesIO(), call img.save(buf, format=format), then return
      buf.getvalue(). Check img.mode before saving as JPEG.
    narration: >
      This exercise locks in the BytesIO pattern. Converting an image to bytes
      is the gateway to every downstream operation: sending images over HTTP,
      encoding as base64 for a vision model, or storing in a database. The
      RGBA-to-RGB handling before JPEG is real production code — you will hit
      this exact error when users upload transparent PNGs and you try to save
      thumbnails as JPEG.

  - type: summary
    heading: "Lesson 2 Summary"
    bullets:
      - "PNG: lossless, supports RGBA; JPEG: lossy, photos only, no alpha"
      - "io.BytesIO — file-like object; wraps bytes as a virtual file"
      - "img.save(buf, format='PNG') → buf.getvalue() → bytes"
      - "Always seek(0) before reading from a buffer"
      - "JPEG does not support RGBA — convert to RGB first"
    narration: >
      You now have the I/O toolkit. BytesIO is the most important pattern in
      this lesson — use it every time you want images as bytes rather than
      files. Next lesson: how to change image geometry — resize, crop, and the
      cover-and-crop pattern used by profile photos and card headers.
"""

_LESSON_03 = """\
day: "066"
lesson: 3
title: "Resize, Crop, and Geometry"
slides:
  - type: title
    heading: "Resize, Crop, and Geometry"
    subheading: "LANCZOS resampling, crop boxes, and the thumbnail pattern"
    narration: >
      Geometric transforms are the most common image operations in production.
      You resize thumbnails, crop profile photos to squares, and create
      consistent-size inputs for machine learning models. This lesson covers
      resize, crop, and thumbnail — and when to use each one.

  - type: concept
    label: "Geometric transforms"
    heading: "Resize vs Crop vs Thumbnail"
    body: >
      Three operations change image dimensions. They differ in how they
      preserve content and aspect ratio.
    bullets:
      - "resize — scale to exact (w, h); may distort aspect ratio"
      - "crop — cut a rectangular sub-region; no scaling"
      - "thumbnail — scale DOWN to fit within a box; preserves aspect ratio;
        modifies in place"
    narration: >
      Resize gives you exact output dimensions but may squish or stretch the
      image if you do not match the aspect ratio. Crop cuts a rectangular
      region — no scaling, just selecting pixels. Thumbnail is a convenience
      method that scales an image down to fit within a bounding box while
      preserving the aspect ratio. It only shrinks — it will not enlarge an
      image. Choose based on what matters: exact dimensions or preserved
      proportions.

  - type: how_it_works
    label: "Resampling"
    heading: "LANCZOS Resampling"
    body: >
      When resizing, Pillow must combine or invent pixel values. The
      resampling filter controls quality. LANCZOS (also called Sinc) produces
      the sharpest results for photos and is the recommended default.
    narration: >
      Resampling is how Pillow maps old pixels to new pixels when the
      dimensions change. NEAREST is the fastest — it just picks the closest
      pixel — but produces blocky results. BILINEAR blends neighbouring
      pixels. LANCZOS uses a much wider kernel and produces sharp, high
      quality results at the cost of slightly more CPU time. For thumbnails
      and profile images, always use LANCZOS. The constant lives at
      Image.Resampling.LANCZOS in Pillow 9 and later.

  - type: code
    label: "Resize and crop"
    heading: "img.resize and img.crop"
    code: |
      from PIL import Image

      img = Image.new('RGB', (400, 300), color=(100, 150, 200))

      # Exact resize
      small = img.resize((200, 150), Image.Resampling.LANCZOS)
      print(small.size)   # (200, 150)

      # Crop a sub-region: box = (left, top, right, bottom)
      crop = img.crop((100, 75, 300, 225))
      print(crop.size)    # (200, 150) — right-left, bottom-top

      # Center crop helper
      def crop_center(img, w, h):
          iw, ih = img.size
          left = (iw - w) // 2
          top  = (ih - h) // 2
          return img.crop((left, top, left + w, top + h))

      square = crop_center(img, 200, 200)
      print(square.size)  # (200, 200)
    narration: >
      resize takes a width-height tuple and a resampling filter. crop takes a
      box tuple: left, top, right, bottom. Note that right and bottom are
      exclusive — they are the pixel coordinate just past the last included
      pixel. The center-crop pattern is extremely common: compute the left and
      top offsets by halving the difference between original and target
      dimensions, then add the crop width and height to get right and bottom.

  - type: code
    label: "Thumbnail"
    heading: "img.thumbnail — Aspect-Ratio-Safe Downscale"
    code: |
      from PIL import Image

      img = Image.new('RGB', (1200, 800), color=(200, 100, 50))

      # thumbnail modifies in place — make a copy first if needed
      thumb = img.copy()
      thumb.thumbnail((300, 300), Image.Resampling.LANCZOS)
      print(thumb.size)  # (300, 200) — fits within 300x300, aspect preserved

      # Fits within the box but may not fill it exactly
      tall = Image.new('RGB', (100, 400))
      tall.thumbnail((200, 200))
      print(tall.size)   # (50, 200) — limited by height
    narration: >
      thumbnail is a convenience for making preview images. It scales the
      image down to fit within the given bounding box while preserving the
      aspect ratio. It never upscales. One important gotcha: thumbnail
      modifies the image in place. If you need the original later, copy it
      first. The output may not fill the full bounding box — it only
      guarantees that both dimensions are at most the given limits.

  - type: exercise
    heading: "Exercise 3: Resize Image"
    prompt: >
      Implement resize_image(img, width, height) -> Image.Image. Resize the
      image to the exact given dimensions using LANCZOS resampling. Return a
      new Image; leave the original unchanged.
    hint: >
      Call img.resize((width, height), Image.Resampling.LANCZOS). PIL resize
      always returns a new Image object.
    narration: >
      Resize is the most common single-image operation — profile photos,
      ML model inputs, thumbnails — all require exact dimensions. Using
      LANCZOS is the default recommendation for quality. This function will
      be a building block in the image pipeline exercise.

  - type: summary
    heading: "Lesson 3 Summary"
    bullets:
      - "resize — exact dimensions; use LANCZOS for quality"
      - "crop — cut a box (left, top, right, bottom); exclusive right/bottom"
      - "thumbnail — aspect-ratio-safe downscale; modifies in place"
      - "Center crop: left = (iw - w)//2, top = (ih - h)//2"
      - "Image.Resampling.LANCZOS — the quality default (Pillow 9+)"
    narration: >
      Geometric transforms sorted. You now have resize, crop, and thumbnail.
      Next lesson: convolution filters and enhancement — how to blur, sharpen,
      and adjust brightness and contrast.
"""

_LESSON_04 = """\
day: "066"
lesson: 4
title: "Filters and Image Enhancement"
slides:
  - type: title
    heading: "Filters and Image Enhancement"
    subheading: "ImageFilter, ImageEnhance — blur, sharpen, brightness"
    narration: >
      Pillow provides two ways to change an image's appearance without
      changing its size: convolution filters, which process pixel
      neighbourhoods, and enhancement adjusters, which scale a property like
      brightness or contrast globally. This lesson covers both.

  - type: concept
    label: "Convolution filters"
    heading: "What is a Convolution Filter?"
    body: >
      A convolution filter replaces each pixel with a weighted average of its
      neighbours. The weights (the kernel) determine the effect.
    bullets:
      - "BLUR — averages a wide neighbourhood; smooths noise"
      - "SHARPEN — amplifies differences between a pixel and its neighbours"
      - "EDGE_ENHANCE — highlights edges between regions"
      - "CONTOUR — finds contours; output is mostly grey with dark edges"
    narration: >
      A convolution filter slides a small grid of weights — called a kernel —
      across every pixel in the image. For each pixel, it multiplies the
      weights by the pixel values in the neighbourhood and sums them. A blur
      kernel has equal positive weights — averaging the neighbourhood. A
      sharpen kernel has a large positive center and negative neighbours —
      amplifying local differences. Edge filters have weights that respond
      strongly to intensity gradients. Pillow's ImageFilter module provides
      pre-built kernels for common effects.

  - type: how_it_works
    label: "ImageFilter"
    heading: "PIL.ImageFilter"
    body: >
      Apply a filter with img.filter(ImageFilter.NAME). It returns a new
      Image. The original is not modified.
    narration: >
      The filter method takes a filter object and returns a new Image. All of
      the standard filters are attributes of ImageFilter: BLUR, SHARPEN,
      SMOOTH, EDGE_ENHANCE, EDGE_ENHANCE_MORE, CONTOUR, EMBOSS, FIND_EDGES.
      You can also create custom filters with ImageFilter.Kernel for full
      control over the convolution weights — useful when you need a specific
      effect that the presets do not cover.

  - type: code
    label: "Applying filters"
    heading: "img.filter — Applying Convolution Filters"
    code: |
      from PIL import Image, ImageFilter
      import numpy as np

      # Create a noisy image — blur will visibly smooth it
      rng = np.random.default_rng(42)
      arr = rng.integers(0, 256, (100, 100, 3), dtype=np.uint8)
      img = Image.fromarray(arr)

      blurred   = img.filter(ImageFilter.BLUR)
      sharpened = img.filter(ImageFilter.SHARPEN)
      edges     = img.filter(ImageFilter.EDGE_ENHANCE)

      print(blurred.size, blurred.mode)  # same size, same mode
      # filter() always returns a new Image — original unchanged
      print(img is blurred)  # False
    narration: >
      img.filter always returns a new Image. The filter is applied to every
      pixel and the result is a new object — the original is never touched.
      Note that most filters require RGB or L mode. If you have an RGBA image
      and a filter raises an error, convert to RGB first with img.convert
      RGB. The gradient image in this example makes filter effects visible
      — on a solid-colour image, most filters produce little change because
      there are no gradients to blur or sharpen.

  - type: how_it_works
    label: "ImageEnhance"
    heading: "PIL.ImageEnhance — Brightness, Contrast, Colour"
    body: >
      ImageEnhance adjusters scale a global property. factor=1.0 is
      unchanged. factor=0 gives a degenerate image (black, grey, etc.).
    narration: >
      While filters operate on pixel neighbourhoods, ImageEnhance adjusters
      scale a single global property. Brightness multiplies every pixel value
      by the factor. Contrast stretches the histogram. Color adjusts
      saturation — factor 0 gives greyscale, factor 2 gives vivid colours.
      Sharpness is similar to the SHARPEN filter but adjustable on a
      continuous scale. All four follow the same API: pass the image to the
      enhancer constructor, then call enhance with a float factor.

  - type: code
    label: "Enhancement"
    heading: "ImageEnhance.Brightness and Contrast"
    code: |
      from PIL import Image, ImageEnhance

      img = Image.new('RGB', (100, 100), color=(100, 100, 100))

      bright = ImageEnhance.Brightness(img).enhance(2.0)  # 2x brighter
      dark   = ImageEnhance.Brightness(img).enhance(0.5)  # half as bright
      vivid  = ImageEnhance.Color(img).enhance(2.0)       # 2x saturation

      # Values are clamped to 0–255 automatically
      import numpy as np
      arr = np.array(bright)
      print(arr.mean())  # ≈ 200 (min(100*2, 255) = 200)
    narration: >
      The pattern is the same for all four enhancers. Construct with the
      image, call enhance with a float. The result is a new Image. Values are
      automatically clamped to the valid range — you cannot accidentally
      overflow to negative pixel values. Chaining multiple enhancers is
      common: first adjust brightness, then contrast, then sharpness.

  - type: exercise
    heading: "Exercise 4: Apply Filter"
    prompt: >
      Implement apply_filter(img, filter_name) -> Image.Image using the
      provided _FILTERS dict. Look up the filter by name (case-insensitive).
      Raise ValueError for unknown names. Return the filtered image.
    hint: >
      _FILTERS.get(filter_name.lower()) gives None for unknown names. Check
      for None and raise ValueError. Otherwise call img.filter(f).
    narration: >
      Wrapping filter lookup in a string-keyed function is the right
      engineering pattern — callers pass a name, not an ImageFilter constant.
      This makes filters configurable from JSON or user input. The ValueError
      gives a clear message instead of a confusing AttributeError, and the
      lower() call makes the API case-insensitive.

  - type: summary
    heading: "Lesson 4 Summary"
    bullets:
      - "ImageFilter — convolution-based: BLUR, SHARPEN, EDGE_ENHANCE, CONTOUR"
      - "img.filter(f) — returns a new Image; original unchanged"
      - "ImageEnhance — global adjusters: Brightness, Contrast, Color, Sharpness"
      - "ImageEnhance.Brightness(img).enhance(factor) — factor=1 unchanged"
      - "Values always clamped to 0–255"
    narration: >
      Filters and enhancement complete. You now have the core toolkit: create,
      load, save, resize, crop, filter, and enhance. The final lesson pulls
      all of these together into a composable pipeline.
"""

_LESSON_05 = """\
day: "066"
lesson: 5
title: "Building an Image Pipeline"
slides:
  - type: title
    heading: "Building an Image Pipeline"
    subheading: "Composable transforms, ImageDraw, and the ImageProcessor pattern"
    narration: >
      Individual operations are useful, but production image processing always
      involves chains of transforms: resize, then sharpen, then save. This
      lesson shows how to compose operations into a reusable pipeline using the
      chainable method pattern.

  - type: concept
    label: "Composition"
    heading: "Why Chain Image Transforms?"
    body: >
      A pipeline is a sequence of pure transforms applied in order. Chainable
      APIs return self after each step, enabling concise multi-step processing.
    narration: >
      Every real image processing system applies multiple transforms. A
      profile photo pipeline might resize to 512 by 512, sharpen to
      compensate for LANCZOS softening, then save as JPEG. Chaining is the
      idiomatic Python pattern for this: each method mutates the object and
      returns self, so you can write one expression per pipeline. The
      alternative — assigning a new variable after every step — produces
      cluttered code and makes it hard to see the transform sequence at a
      glance.

  - type: how_it_works
    label: "Chainable methods"
    heading: "The return-self Pattern"
    body: >
      Each transform method mutates self._img and returns self. The caller
      can chain calls or use the result as a regular method call.
    narration: >
      The chainable pattern is straightforward: instead of returning a new
      object or returning None, each method returns self. This means the call
      result is the same object, and you can immediately call another method
      on it. The only trade-off is that methods mutate the object rather than
      returning copies — so if you need the intermediate state, call image to
      get a copy before the next transform.

  - type: code
    label: "Chained pipeline"
    heading: "ImageProcessor — Chainable API"
    code: |
      from image_utils import ImageProcessor

      # Single expression, six operations
      result = (
          ImageProcessor.new(800, 600, color=(50, 100, 150))
          .resize(400, 300)
          .crop_center(300, 300)
          .apply_filter("sharpen")
          .adjust_brightness(1.1)
          .adjust_contrast(1.2)
      )
      print(result.size)   # (300, 300)
      print(result.mode)   # 'RGB'
      raw_bytes = result.to_bytes("PNG")
    narration: >
      The ImageProcessor class you build today implements this pattern. Each
      method returns self. You create a 800 by 600 image, resize it to half
      size, crop a 300 by 300 square from the center, sharpen to counteract
      LANCZOS blurring, and brighten and increase contrast slightly — all in
      one expression. The result is still an ImageProcessor, so you can call
      to_bytes or save on it.

  - type: code
    label: "ImageDraw"
    heading: "ImageDraw — Annotating Images"
    code: |
      from PIL import Image, ImageDraw

      img = Image.new('RGB', (200, 100), color=(240, 240, 240))
      draw = ImageDraw.Draw(img)

      # Draw rectangle and text
      draw.rectangle([(10, 10), (190, 90)], outline=(200, 50, 50), width=3)
      draw.text((20, 40), "Hello, Pillow!", fill=(50, 50, 200))

      # Draw a circle (ellipse with equal axes)
      draw.ellipse([(80, 30), (120, 70)], fill=(0, 200, 100))

      img.save("annotated.png")
    narration: >
      ImageDraw lets you draw shapes and text directly onto an image. Create
      a Draw object from an Image, and any drawing calls modify the underlying
      image. This is useful for adding bounding boxes from object detection,
      overlaying text labels, watermarking, or building charts entirely in
      Pillow. In Day 68 you will use ImageDraw to create test images with text
      that you then feed to OCR.

  - type: exercise
    heading: "Exercise 5: Image Pipeline"
    prompt: >
      Implement image_pipeline(img, steps) -> Image.Image. Each step is a
      (op_name, params_dict) tuple. Support: 'resize' (width, height),
      'crop' (width, height — center crop), 'grayscale' (no params),
      'filter' (name), 'brightness' (factor), 'contrast' (factor).
      Raise ValueError for unknown ops. Return the processed image.
    hint: >
      Start with result = img.copy(). For each op, update result. For 'crop',
      use the same left/top calculation as crop_center. For 'filter', look up
      in _FILTERS. For 'brightness' and 'contrast', use ImageEnhance.
    narration: >
      This final exercise ties the whole day together. You will implement a
      mini-pipeline that chains all the operations you learned — resize, crop,
      grayscale, filter, brightness, contrast. The steps-list design makes the
      pipeline data-driven: you can specify a sequence in JSON and feed it
      directly to image_pipeline without any code changes.

  - type: summary
    heading: "Lesson 5 Summary — Day 66 Complete"
    bullets:
      - "Chain transforms by returning self from each mutating method"
      - "ImageDraw — annotate images with shapes and text"
      - "Data-driven pipelines: steps list specifies operations as data"
      - "Tomorrow: pass images to a vision LLM via Ollama (Day 67)"
    narration: >
      Day 66 is complete. You can create, load, save, resize, crop, filter,
      enhance, and pipeline images entirely in Python. The BytesIO and
      programmatic-image patterns will carry forward through every day in this
      section. Tomorrow you will pass these images to a vision language model
      and get text descriptions back — the foundation of multimodal AI.
"""

for i, content in enumerate([_LESSON_01, _LESSON_02, _LESSON_03,
                               _LESSON_04, _LESSON_05], start=1):
    (OUT / "lessons" / f"day_{DAY}_lesson_0{i}.yaml").write_text(content)

# ── EXERCISE 1 — get_image_info ───────────────────────────────────────────────
_EX1_GIVEN = """\
from PIL import Image
import numpy as np

# Test images for the checks
_rgb  = Image.new('RGB',  (200, 100), color=(255, 128, 0))
_rgba = Image.new('RGBA', (50, 50),   color=(0, 0, 0, 128))
_gray = Image.new('L',    (64, 32),   color=128)
"""

_EX1_STUB = """\
def get_image_info(img: Image.Image) -> dict:
    \"\"\"Return metadata about a PIL Image.

    Returns a dict with keys:
        width:        int — image width in pixels
        height:       int — image height in pixels
        mode:         str — color mode ('RGB', 'L', 'RGBA', etc.)
        num_channels: int — number of channels

    For num_channels, use the lookup RGB=3, RGBA=4, L=1.
    For any other mode, use len(img.getbands()).
    \"\"\"
    raise NotImplementedError
"""

_EX1_SOLUTION = """\
def get_image_info(img: Image.Image) -> dict:
    w, h = img.size
    channel_map = {'RGB': 3, 'RGBA': 4, 'L': 1}
    n = channel_map.get(img.mode, len(img.getbands()))
    return {'width': w, 'height': h, 'mode': img.mode, 'num_channels': n}
"""

_EX1_CHECKS = """\
score, total = 0, 5
try:
    info = get_image_info(_rgb)
    assert isinstance(info, dict)
    for k in ('width', 'height', 'mode', 'num_channels'):
        assert k in info, f"Missing key: {k!r}"
    score += 1; print("\\u2705 returns dict with all 4 keys")

    assert info['width'] == 200 and info['height'] == 100, (
        f"Expected 200x100, got {info['width']}x{info['height']}")
    score += 1; print("\\u2705 width and height correct for 200x100 image")

    assert info['mode'] == 'RGB', f"Expected 'RGB', got {info['mode']!r}"
    score += 1; print("\\u2705 mode is 'RGB'")

    assert info['num_channels'] == 3, f"Expected 3, got {info['num_channels']}"
    score += 1; print("\\u2705 num_channels == 3 for RGB")

    info_rgba = get_image_info(_rgba)
    info_gray = get_image_info(_gray)
    assert info_rgba['num_channels'] == 4, f"RGBA should have 4 channels"
    assert info_gray['num_channels'] == 1, f"L should have 1 channel"
    assert info_gray['width'] == 64 and info_gray['height'] == 32
    score += 1; print("\\u2705 RGBA=4 channels, L=1 channel, sizes correct")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX1 = nb([
    md("# Day 066 — Exercise 1: Get Image Info\n\n"
       "**What you'll build:** `get_image_info(img)` — inspect a PIL Image and "
       "return its key metadata as a dict.\n\n"
       "**Why it matters:** Before processing any image, you need to know what "
       "you're working with. Size, mode, and channel count determine every "
       "downstream decision — how to resize, whether to convert mode, how much "
       "memory to expect."),
    code(_EX1_GIVEN),
    md("## Task\n\nImplement `get_image_info(img) -> dict` with keys:\n\n"
       "| Key | Type | Description |\n"
       "|-----|------|-------------|\n"
       "| `width` | int | image width in pixels |\n"
       "| `height` | int | image height in pixels |\n"
       "| `mode` | str | color mode string |\n"
       "| `num_channels` | int | number of channels |\n\n"
       "For `num_channels`: use lookup `{'RGB': 3, 'RGBA': 4, 'L': 1}`, "
       "fall back to `len(img.getbands())`."),
    md("## Your Implementation"),
    code(_EX1_STUB),
    code(_EX1_SOLUTION),
    md("## Automated checks"),
    code(_EX1_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX1_SOLUTION + "```\n\n"
       "**Why a lookup dict for channels?** `img.getbands()` works for all modes "
       "but the lookup is faster and more explicit for the three modes you will "
       "encounter 99% of the time. The fallback handles uncommon modes (like 'HSV' "
       "or 'LAB') gracefully without extra branches.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_01.ipynb", EX1)

# ── EXERCISE 2 — image_to_bytes ───────────────────────────────────────────────
_EX2_GIVEN = """\
import io
from PIL import Image

# Test images
_rgb  = Image.new('RGB',  (100, 80), color=(50, 100, 200))
_rgba = Image.new('RGBA', (60, 60),  color=(0, 200, 100, 128))
"""

_EX2_STUB = """\
def image_to_bytes(img: Image.Image, format: str = 'PNG') -> bytes:
    \"\"\"Serialize a PIL Image to bytes in the given format.

    For JPEG output, RGBA and P mode images are automatically converted to
    RGB before saving (JPEG does not support alpha channels).

    Args:
        img:    PIL Image to encode
        format: format string — 'PNG', 'JPEG', 'BMP', etc.
    Returns: raw bytes of the encoded image
    \"\"\"
    raise NotImplementedError
"""

_EX2_SOLUTION = """\
def image_to_bytes(img: Image.Image, format: str = 'PNG') -> bytes:
    buf = io.BytesIO()
    out = img
    if format.upper() in ('JPEG', 'JPG') and img.mode in ('RGBA', 'P'):
        out = img.convert('RGB')
    out.save(buf, format=format)
    return buf.getvalue()
"""

_EX2_CHECKS = """\
score, total = 0, 5
try:
    result = image_to_bytes(_rgb, 'PNG')
    assert isinstance(result, bytes), f"Expected bytes, got {type(result)}"
    score += 1; print("\\u2705 returns bytes")

    assert len(result) > 0, "bytes should not be empty"
    score += 1; print("\\u2705 bytes are non-empty")

    # PNG magic bytes: \\x89PNG
    assert result[:4] == b'\\x89PNG', (
        f"Expected PNG magic bytes, got {result[:4]!r}")
    score += 1; print("\\u2705 PNG output has correct magic bytes (\\\\x89PNG)")

    jpeg_bytes = image_to_bytes(_rgb, 'JPEG')
    assert jpeg_bytes[:2] == b'\\xff\\xd8', (
        f"Expected JPEG SOI marker, got {jpeg_bytes[:2]!r}")
    score += 1; print("\\u2705 JPEG output has correct SOI marker (\\\\xff\\\\xd8)")

    # RGBA -> JPEG should work without error (auto-convert to RGB)
    jpeg_from_rgba = image_to_bytes(_rgba, 'JPEG')
    assert len(jpeg_from_rgba) > 0
    score += 1; print("\\u2705 RGBA image converts to JPEG without error")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX2 = nb([
    md("# Day 066 — Exercise 2: Image to Bytes\n\n"
       "**What you'll build:** `image_to_bytes(img, format)` — serialize a PIL "
       "Image to raw bytes using BytesIO.\n\n"
       "**Why it matters:** Converting images to bytes is the gateway to every "
       "downstream operation — sending images over HTTP, encoding as base64 for a "
       "vision model, or storing in a database. The RGBA→RGB handling before JPEG "
       "is real production code you will hit every time users upload transparent "
       "PNGs."),
    code(_EX2_GIVEN),
    md("## Task\n\nImplement `image_to_bytes(img, format='PNG') -> bytes`:\n\n"
       "1. Create `io.BytesIO()`\n"
       "2. If `format` is `'JPEG'` or `'JPG'` and `img.mode` is `'RGBA'` or `'P'`, "
       "convert to `'RGB'` first\n"
       "3. Call `.save(buf, format=format)`\n"
       "4. Return `buf.getvalue()`\n\n"
       "**Magic bytes reference:**\n"
       "- PNG: starts with `b'\\x89PNG'`\n"
       "- JPEG: starts with `b'\\xff\\xd8'` (SOI marker)"),
    md("## Your Implementation"),
    code(_EX2_STUB),
    code(_EX2_SOLUTION),
    md("## Automated checks"),
    code(_EX2_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX2_SOLUTION + "```\n\n"
       "**Why check magic bytes?** Magic bytes are the first few bytes of a file "
       "that identify its format — independent of the file extension. Checking them "
       "in tests proves the encoding actually happened, not just that bytes were "
       "returned. PNG's magic is `\\x89PNG\\r\\n\\x1a\\n`. JPEG's is `\\xff\\xd8` "
       "(Start of Image marker).\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_02.ipynb", EX2)

# ── EXERCISE 3 — resize_image ─────────────────────────────────────────────────
_EX3_GIVEN = """\
from PIL import Image
import numpy as np

_src = Image.new('RGB', (400, 200), color=(100, 150, 200))
"""

_EX3_STUB = """\
def resize_image(img: Image.Image, width: int, height: int) -> Image.Image:
    \"\"\"Resize an image to exact dimensions using LANCZOS resampling.

    Args:
        img:    source PIL Image
        width:  target width in pixels
        height: target height in pixels
    Returns:
        New resized Image. The original is not modified.
    \"\"\"
    raise NotImplementedError
"""

_EX3_SOLUTION = """\
def resize_image(img: Image.Image, width: int, height: int) -> Image.Image:
    return img.resize((width, height), Image.Resampling.LANCZOS)
"""

_EX3_CHECKS = """\
score, total = 0, 5
try:
    result = resize_image(_src, 200, 100)
    assert isinstance(result, Image.Image), (
        f"Expected PIL Image, got {type(result)}")
    score += 1; print("\\u2705 returns a PIL Image")

    assert result.size[0] == 200, f"Expected width 200, got {result.size[0]}"
    score += 1; print("\\u2705 output width is correct")

    assert result.size[1] == 100, f"Expected height 100, got {result.size[1]}"
    score += 1; print("\\u2705 output height is correct")

    # Upscale
    upscaled = resize_image(_src, 800, 400)
    assert upscaled.size == (800, 400), f"Upscale failed: {upscaled.size}"
    score += 1; print("\\u2705 upscaling to 800x400 works")

    # Original unchanged
    assert _src.size == (400, 200), "Original size should not change"
    score += 1; print("\\u2705 original image is not modified")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX3 = nb([
    md("# Day 066 — Exercise 3: Resize Image\n\n"
       "**What you'll build:** `resize_image(img, width, height)` — exact-dimension "
       "resize using LANCZOS resampling.\n\n"
       "**Why it matters:** Most ML models require fixed-size inputs. LANCZOS is the "
       "quality default — it produces sharper results than BILINEAR or NEAREST by "
       "using a wider convolution kernel."),
    code(_EX3_GIVEN),
    md("## Task\n\nImplement `resize_image(img, width, height) -> Image.Image`:\n\n"
       "- Use `img.resize((width, height), Image.Resampling.LANCZOS)`\n"
       "- Return the new image (PIL resize always returns a new object)\n"
       "- Do not modify the original image\n\n"
       "`Image.Resampling.LANCZOS` is available in Pillow 9+. "
       "The deprecated alias `Image.LANCZOS` also works but is not recommended."),
    md("## Your Implementation"),
    code(_EX3_STUB),
    code(_EX3_SOLUTION),
    md("## Automated checks"),
    code(_EX3_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX3_SOLUTION + "```\n\n"
       "**Why LANCZOS?** It uses a sinc-based kernel wider than BILINEAR's "
       "2-pixel window. For downscaling, LANCZOS avoids the aliasing artefacts "
       "that BILINEAR and NEAREST produce. The extra computation is negligible "
       "for single-image operations — it matters for batch processing of thousands "
       "of images.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_03.ipynb", EX3)

# ── EXERCISE 4 — apply_filter ─────────────────────────────────────────────────
_EX4_GIVEN = """\
import numpy as np
from PIL import Image, ImageFilter

_FILTERS = {
    'blur':         ImageFilter.BLUR,
    'sharpen':      ImageFilter.SHARPEN,
    'edge_enhance': ImageFilter.EDGE_ENHANCE,
    'contour':      ImageFilter.CONTOUR,
}

# Noisy image — blur will measurably change pixel values
_rng = np.random.default_rng(42)
_arr = _rng.integers(0, 256, (100, 100, 3), dtype=np.uint8)
_gradient = Image.fromarray(_arr)
"""

_EX4_STUB = """\
def apply_filter(img: Image.Image, filter_name: str) -> Image.Image:
    \"\"\"Apply a named convolution filter to an image.

    Looks up filter_name (case-insensitive) in _FILTERS.

    Args:
        img:         source PIL Image
        filter_name: one of 'blur', 'sharpen', 'edge_enhance', 'contour'
    Returns:
        New filtered Image (original unchanged)
    Raises:
        ValueError: if filter_name is not in _FILTERS
    \"\"\"
    raise NotImplementedError
"""

_EX4_SOLUTION = """\
def apply_filter(img: Image.Image, filter_name: str) -> Image.Image:
    f = _FILTERS.get(filter_name.lower())
    if f is None:
        raise ValueError(
            f"Unknown filter: {filter_name!r}. Available: {list(_FILTERS)}"
        )
    return img.filter(f)
"""

_EX4_CHECKS = """\
score, total = 0, 5
try:
    result = apply_filter(_gradient, 'blur')
    assert isinstance(result, Image.Image), (
        f"Expected PIL Image, got {type(result)}")
    score += 1; print("\\u2705 returns a PIL Image")

    assert result.size == _gradient.size, (
        f"Size changed: {result.size} != {_gradient.size}")
    score += 1; print("\\u2705 output size matches input size")

    # blur should change pixel values on a gradient image
    import numpy as np
    orig_arr   = np.array(_gradient)
    result_arr = np.array(result)
    assert not np.array_equal(orig_arr, result_arr), (
        "Blur should change pixel values on a gradient image")
    score += 1; print("\\u2705 blur changes pixel values")

    # Case-insensitive lookup
    result2 = apply_filter(_gradient, 'SHARPEN')
    assert isinstance(result2, Image.Image)
    score += 1; print("\\u2705 filter_name lookup is case-insensitive")

    # Unknown filter raises ValueError
    raised = False
    try:
        apply_filter(_gradient, 'teleport')
    except ValueError:
        raised = True
    assert raised, "Unknown filter should raise ValueError"
    score += 1; print("\\u2705 unknown filter name raises ValueError")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX4 = nb([
    md("# Day 066 — Exercise 4: Apply Filter\n\n"
       "**What you'll build:** `apply_filter(img, filter_name)` — apply a named "
       "convolution filter using the `_FILTERS` lookup dict.\n\n"
       "**Why it matters:** String-keyed filter dispatch makes filters "
       "configurable from user input or JSON without importing ImageFilter "
       "constants everywhere. The ValueError gives a clear message instead of "
       "a confusing `KeyError` or `NoneType` error."),
    code(_EX4_GIVEN),
    md("## Task\n\nImplement `apply_filter(img, filter_name) -> Image.Image`:\n\n"
       "1. Look up `filter_name.lower()` in `_FILTERS`\n"
       "2. If not found, raise `ValueError` with a helpful message\n"
       "3. Call `img.filter(f)` and return the result\n\n"
       "Available filters: `'blur'`, `'sharpen'`, `'edge_enhance'`, `'contour'`"),
    md("## Your Implementation"),
    code(_EX4_STUB),
    code(_EX4_SOLUTION),
    md("## Automated checks"),
    code(_EX4_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX4_SOLUTION + "```\n\n"
       "**Why a gradient image in the tests?** On a solid-colour image, blur "
       "has no visible effect — every pixel neighbourhood has the same value, so "
       "the average equals the original. A gradient gives each pixel a different "
       "neighbourhood, so blur produces measurably different output. Always design "
       "test images that make the expected behaviour observable.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_04.ipynb", EX4)

# ── EXERCISE 5 — image_pipeline ───────────────────────────────────────────────
_EX5_GIVEN = """\
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance

_FILTERS = {
    'blur':         ImageFilter.BLUR,
    'sharpen':      ImageFilter.SHARPEN,
    'edge_enhance': ImageFilter.EDGE_ENHANCE,
}

_src = Image.new('RGB', (200, 150), color=(80, 120, 180))
"""

_EX5_STUB = """\
def image_pipeline(img: Image.Image, steps: list) -> Image.Image:
    \"\"\"Apply a sequence of image processing steps in order.

    Each step is a (operation_name, params_dict) tuple.

    Supported operations:
        ('resize',     {'width': int, 'height': int})
        ('crop',       {'width': int, 'height': int})   # center crop
        ('grayscale',  {})
        ('filter',     {'name': str})                   # key in _FILTERS
        ('brightness', {'factor': float})               # 1.0 = unchanged
        ('contrast',   {'factor': float})               # 1.0 = unchanged

    Args:
        img:   starting PIL Image (not modified)
        steps: list of (op_name, params) tuples
    Returns:
        Processed Image
    Raises:
        ValueError for unknown operations
    \"\"\"
    raise NotImplementedError
"""

_EX5_SOLUTION = """\
def image_pipeline(img: Image.Image, steps: list) -> Image.Image:
    result = img.copy()
    for op, params in steps:
        if op == 'resize':
            result = result.resize(
                (params['width'], params['height']), Image.Resampling.LANCZOS)
        elif op == 'crop':
            w, h = params['width'], params['height']
            iw, ih = result.size
            left, top = (iw - w) // 2, (ih - h) // 2
            result = result.crop((left, top, left + w, top + h))
        elif op == 'grayscale':
            result = result.convert('L')
        elif op == 'filter':
            f = _FILTERS.get(params['name'].lower())
            if f is None:
                raise ValueError(f"Unknown filter: {params['name']!r}")
            result = result.filter(f)
        elif op == 'brightness':
            result = ImageEnhance.Brightness(result).enhance(params['factor'])
        elif op == 'contrast':
            result = ImageEnhance.Contrast(result).enhance(params['factor'])
        else:
            raise ValueError(f"Unknown operation: {op!r}")
    return result
"""

_EX5_CHECKS = """\
score, total = 0, 5
try:
    # Empty pipeline — result identical to input
    result = image_pipeline(_src, [])
    assert list(result.getdata()) == list(_src.getdata()), (
        "Empty pipeline should return a copy with identical pixels")
    score += 1; print("\\u2705 empty steps returns identical image")

    # Single resize step
    result = image_pipeline(_src, [('resize', {'width': 100, 'height': 75})])
    assert result.size == (100, 75), f"Expected (100, 75), got {result.size}"
    score += 1; print("\\u2705 resize step works")

    # Multi-step: resize + grayscale
    result = image_pipeline(_src, [
        ('resize',    {'width': 60, 'height': 60}),
        ('grayscale', {}),
    ])
    assert result.size == (60, 60) and result.mode == 'L', (
        f"Expected (60, 60) L, got {result.size} {result.mode}")
    score += 1; print("\\u2705 resize + grayscale pipeline works")

    # Brightness step changes pixel values
    import numpy as np
    bright = image_pipeline(_src, [('brightness', {'factor': 2.0})])
    arr_src   = np.array(_src, dtype=float)
    arr_bright = np.array(bright, dtype=float)
    assert arr_bright.mean() > arr_src.mean(), (
        "brightness factor=2.0 should increase mean pixel value")
    score += 1; print("\\u2705 brightness step increases pixel values")

    # Unknown operation raises ValueError
    raised = False
    try:
        image_pipeline(_src, [('teleport', {})])
    except ValueError:
        raised = True
    assert raised, "Unknown op should raise ValueError"
    score += 1; print("\\u2705 unknown operation raises ValueError")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX5 = nb([
    md("# Day 066 — Exercise 5: Image Pipeline\n\n"
       "**What you'll build:** `image_pipeline(img, steps)` — apply a "
       "sequence of named operations to an image.\n\n"
       "**Why it matters:** A steps-list design makes image pipelines "
       "data-driven — you can specify the sequence in JSON or a config file. "
       "This pattern is used by image processing APIs, ML preprocessing "
       "scripts, and thumbnail generators everywhere."),
    code(_EX5_GIVEN),
    md("## Task\n\nImplement `image_pipeline(img, steps) -> Image.Image`:\n\n"
       "- Start with `result = img.copy()` (don't modify the original)\n"
       "- Iterate `steps`, each a `(op_name, params_dict)` tuple\n"
       "- Apply each operation to `result`\n"
       "- Raise `ValueError` for unknown ops\n\n"
       "| Op | params | Operation |\n"
       "|----|--------|-----------|\n"
       "| `'resize'` | `{width, height}` | `resize` with LANCZOS |\n"
       "| `'crop'` | `{width, height}` | center crop |\n"
       "| `'grayscale'` | `{}` | convert to L mode |\n"
       "| `'filter'` | `{name}` | look up in `_FILTERS` |\n"
       "| `'brightness'` | `{factor}` | `ImageEnhance.Brightness` |\n"
       "| `'contrast'` | `{factor}` | `ImageEnhance.Contrast` |"),
    md("## Your Implementation"),
    code(_EX5_STUB),
    code(_EX5_SOLUTION),
    md("## Automated checks"),
    code(_EX5_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX5_SOLUTION + "```\n\n"
       "**Why `img.copy()` at the start?** If `steps` is empty the caller gets "
       "back a copy, not the same object. This prevents accidental mutation of "
       "the original when the caller passes the result to another pipeline. "
       "The copy cost is negligible — it's the safe default.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_05.ipynb", EX5)

# ── PROJECT NOTEBOOK ──────────────────────────────────────────────────────────
PROJECT = nb([
    md("# Day 066 — Project: Image-Processing Utility\n\n"
       "## What You're Building\n\n"
       "`image_utils.py` — a chainable image processor built on Pillow.\n\n"
       "**Deliverable:** `image_utils.py` containing an `ImageProcessor` class "
       "with chainable methods for resize, crop, grayscale, filter, brightness, "
       "contrast, and I/O. You run it, it produces a working utility you can "
       "import in any project. That's the deliverable.\n\n"
       "## Design\n\n"
       "```\n"
       "ImageProcessor\n"
       "  .new(w, h, color)      → create blank RGB image\n"
       "  .from_file(path)       → load from disk\n"
       "  .resize(w, h)          → LANCZOS resize  ← returns self\n"
       "  .crop_center(w, h)     → center crop     ← returns self\n"
       "  .to_grayscale()        → convert to L    ← returns self\n"
       "  .apply_filter(name)    → named filter    ← returns self\n"
       "  .adjust_brightness(f)  → scale brightness← returns self\n"
       "  .adjust_contrast(f)    → scale contrast  ← returns self\n"
       "  .save(path)            → write to disk; returns path\n"
       "  .to_bytes(format)      → encode to bytes; returns bytes\n"
       "```\n\n"
       "## Implementation\n\n"
       "Build `ImageProcessor` in `image_utils.py`. Use the exercises as building "
       "blocks — you have already implemented each operation individually."),
    code("# Your implementation here\n"
         "# Build ImageProcessor and write it to image_utils.py\n"),
])
save(OUT / "project" / "project.ipynb", PROJECT)

# ── SOLUTION NOTEBOOK ─────────────────────────────────────────────────────────
_SOL_CELL1 = (
    f"_UTILS_SRC = {repr(_UTILS_SRC)}\n"
    "from pathlib import Path\n"
    "Path('image_utils.py').write_text(_UTILS_SRC, encoding='utf-8')\n"
    "print('image_utils.py written.')"
)

_SOL_CELL2 = """\
import os
import tempfile
from pathlib import Path
from PIL import Image
import numpy as np
from image_utils import ImageProcessor

# 1. Create image
p = ImageProcessor.new(200, 150, color=(100, 150, 200))
assert p.size == (200, 150), f"Expected (200, 150), got {p.size}"
assert p.mode == 'RGB'
print("\\u2705 ImageProcessor.new creates correct image")

# 2. Resize (chainable)
p.resize(100, 75)
assert p.size == (100, 75), f"Expected (100, 75), got {p.size}"
print("\\u2705 resize works")

# 3. Crop center
p2 = ImageProcessor.new(200, 200, color=(255, 0, 0))
p2.crop_center(100, 100)
assert p2.size == (100, 100), f"Expected (100, 100), got {p2.size}"
print("\\u2705 crop_center works")

# 4. Grayscale
p3 = ImageProcessor.new(100, 100, color=(200, 100, 50))
p3.to_grayscale()
assert p3.mode == 'L', f"Expected L mode, got {p3.mode}"
print("\\u2705 to_grayscale works")

# 5. Filter
p4 = ImageProcessor.new(100, 100, color=(200, 100, 50))
p4.apply_filter('blur')
assert p4.size == (100, 100)
print("\\u2705 apply_filter works")

# 6. Unknown filter raises ValueError
raised = False
try:
    ImageProcessor.new(50, 50).apply_filter('teleport')
except ValueError:
    raised = True
assert raised
print("\\u2705 unknown filter raises ValueError")

# 7. Chain operations
p5 = (
    ImageProcessor.new(400, 300, color=(50, 100, 150))
    .resize(200, 150)
    .apply_filter('sharpen')
    .adjust_brightness(1.1)
    .adjust_contrast(1.2)
)
assert p5.size == (200, 150), f"Expected (200, 150), got {p5.size}"
print("\\u2705 method chaining works")

# 8. to_bytes returns valid PNG
raw = ImageProcessor.new(50, 50).to_bytes('PNG')
assert raw[:4] == b'\\x89PNG', f"Not a PNG: {raw[:4]!r}"
print("\\u2705 to_bytes returns valid PNG")

# 9. to_bytes JPEG — RGBA auto-converts
rgba_proc = ImageProcessor(Image.new('RGBA', (50, 50), (0, 200, 100, 128)))
jpeg_raw = rgba_proc.to_bytes('JPEG')
assert jpeg_raw[:2] == b'\\xff\\xd8'
print("\\u2705 RGBA image converts to JPEG bytes without error")

# 10. save to disk
with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
    tmp_path = f.name
try:
    ImageProcessor.new(50, 50, color=(0, 255, 0)).save(tmp_path)
    assert Path(tmp_path).stat().st_size > 0
    print("\\u2705 save to disk works")
finally:
    os.unlink(tmp_path)

print("\\nImages in Python complete!")
"""

SOLUTION = nb([
    md("# Day 066 — Solution: Image-Processing Utility"),
    code(_SOL_CELL1),
    code(_SOL_CELL2),
])
save(OUT / "project" / "solution" / "solution.ipynb", SOLUTION)
(OUT / "project" / "solution" / "image_utils.py").write_text(_UTILS_SRC)

print(f"Day {DAY} notebooks written to {OUT}")
print("  lessons/    day_066_lesson_01.yaml – lesson_05.yaml")
print("  exercises/  exercise_01 – exercise_05")
print("  project/    project.ipynb")
print("  project/solution/  solution.ipynb + image_utils.py")
