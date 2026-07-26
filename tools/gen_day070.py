#!/usr/bin/env python3
"""gen_day070.py — generate Day 070: Image Generation."""
from pathlib import Path
import json

ROOT    = Path(__file__).parent.parent
DAY     = "070"
SECTION = "05_vision_multimodal"
OUT     = ROOT / SECTION / f"day_{DAY}"

(OUT / "exercises").mkdir(parents=True, exist_ok=True)
(OUT / "lessons").mkdir(parents=True, exist_ok=True)
(OUT / "project" / "solution").mkdir(parents=True, exist_ok=True)

# ── deliverable: image_generator.py ──────────────────────────────────────────
_GENERATOR_SRC = '''\
"""image_generator.py — Day 070: Image Generation.

Generates images from text prompts using a diffusion model.

Setup (real generation):
    pip install diffusers transformers accelerate torch
    # GPU recommended; CPU works but is very slow

Usage:
    from image_generator import ImageGenerator

    # Quick test (no GPU needed)
    mock = lambda prompt, **kw: Image.new("RGB", (kw.get("width",512), kw.get("height",512)), "steelblue")
    gen = ImageGenerator(generate_fn=mock)
    img = gen.generate("a cat on a moon")
    img.save("test.png")

    # Real generation (requires diffusers + downloaded model)
    gen = ImageGenerator(model_id="runwayml/stable-diffusion-v1-5")
    img = gen.generate("a cat on a moon")
"""
import math
from pathlib import Path
from PIL import Image

# Default style templates — positive/negative prompt pairs per style
STYLE_TEMPLATES = {
    "cinematic": {
        "positive": "cinematic lighting, film grain, anamorphic lens, dramatic shadows",
        "negative": "flat lighting, cartoon, illustration, bright colours",
    },
    "photorealistic": {
        "positive": "photorealistic, 8k uhd, high detail, DSLR, sharp focus",
        "negative": "painting, drawing, blur, watermark, cartoon",
    },
    "watercolor": {
        "positive": "watercolor painting, soft edges, artistic, pastel tones",
        "negative": "photorealistic, sharp, digital art, 3d render",
    },
    "anime": {
        "positive": "anime style, cel shaded, vibrant colours, clean lines",
        "negative": "photorealistic, watercolor, oil painting, sketch",
    },
}

# Common quality-boost tags to append to positive prompts
QUALITY_TAGS = ["masterpiece", "best quality", "highly detailed"]

# Common negative-quality tags to append to negative prompts
NEGATIVE_QUALITY_TAGS = ["blurry", "low quality", "watermark", "text", "cropped"]


def build_prompt(subject: str, style: str = "",
                 quality_tags: list = None,
                 negative_tags: list = None) -> dict:
    """Build a positive/negative prompt pair for image generation.

    Args:
        subject:       Main subject description
        style:         Visual style string (e.g. "oil painting, impressionist")
        quality_tags:  Extra positive quality tags (appended after subject+style)
        negative_tags: Tags describing what to avoid in the output
    Returns:
        dict with 'positive' (str) and 'negative' (str) keys
    """
    parts = [subject]
    if style:
        parts.append(style)
    if quality_tags:
        parts.extend(quality_tags)
    positive = ", ".join(p.strip() for p in parts if p.strip())
    negative = ", ".join(t.strip() for t in (negative_tags or []) if t.strip())
    return {"positive": positive, "negative": negative}


def apply_style_template(base_prompt: str, template_name: str,
                          templates: dict = None) -> dict:
    """Merge a base prompt with a named style template.

    Args:
        base_prompt:   Subject or scene description
        template_name: Key in STYLE_TEMPLATES (or custom templates dict)
        templates:     Custom template dict; defaults to STYLE_TEMPLATES
    Returns:
        dict with 'positive' (str) and 'negative' (str) keys
    Raises:
        ValueError for unknown template names
    """
    tmpl_dict = templates if templates is not None else STYLE_TEMPLATES
    tmpl = tmpl_dict.get(template_name)
    if tmpl is None:
        available = list(tmpl_dict.keys())
        raise ValueError(
            f"Unknown style template {template_name!r}. "
            f"Available: {available}"
        )
    pos = base_prompt + ", " + tmpl["positive"] if base_prompt.strip() else tmpl["positive"]
    return {"positive": pos, "negative": tmpl["negative"]}


def generate_image(prompt: str, negative: str = "",
                   generate_fn=None,
                   width: int = 512, height: int = 512,
                   steps: int = 20, guidance_scale: float = 7.5,
                   seed: int = 42) -> Image.Image:
    """Generate an image from a text prompt.

    Args:
        prompt:         Positive text prompt
        negative:       Negative text prompt (describe what to avoid)
        generate_fn:    callable(prompt, **kwargs) -> PIL.Image for testing
        width:          Output width in pixels (must be multiple of 8)
        height:         Output height in pixels (must be multiple of 8)
        steps:          Denoising steps (more steps = higher quality, slower)
        guidance_scale: CFG scale — how strongly the image follows the prompt
        seed:           Random seed for reproducibility
    Returns:
        PIL.Image.Image
    """
    if generate_fn is not None:
        return generate_fn(prompt, negative=negative, width=width,
                           height=height, steps=steps,
                           guidance_scale=guidance_scale, seed=seed)
    from diffusers import StableDiffusionPipeline
    import torch
    pipe = StableDiffusionPipeline.from_pretrained(
        "runwayml/stable-diffusion-v1-5",
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    )
    if torch.cuda.is_available():
        pipe = pipe.to("cuda")
    generator = torch.Generator().manual_seed(seed)
    result = pipe(
        prompt,
        negative_prompt=negative or None,
        width=width, height=height,
        num_inference_steps=steps,
        guidance_scale=guidance_scale,
        generator=generator,
    )
    return result.images[0]


def generate_variations(base_prompt: str, n_variations: int,
                         generate_fn=None, **kwargs) -> list:
    """Generate n_variations of the same prompt, each with a different seed.

    Args:
        base_prompt:  Text prompt
        n_variations: Number of images to generate
        generate_fn:  Callable for testing (see generate_image)
        **kwargs:     Forwarded to generate_image (width, height, steps, …)
    Returns:
        list of PIL.Image.Image, length == n_variations
    """
    images = []
    for i in range(n_variations):
        seed = i * 1000 + 42
        img = generate_image(base_prompt, generate_fn=generate_fn, seed=seed, **kwargs)
        images.append(img)
    return images


def create_image_grid(images: list, cols: int = 2) -> Image.Image:
    """Arrange a list of PIL Images in a rectangular grid.

    Args:
        images: list of PIL.Image.Image — all should have the same size
        cols:   number of columns in the grid
    Returns:
        Single PIL.Image.Image compositing all inputs
    Raises:
        ValueError if images is empty
    """
    if not images:
        raise ValueError("images list must not be empty")
    cols = max(1, min(cols, len(images)))
    rows = math.ceil(len(images) / cols)
    w, h = images[0].size
    grid = Image.new("RGB", (cols * w, rows * h), "white")
    for i, img in enumerate(images):
        col = i % cols
        row = i // cols
        if img.size != (w, h):
            img = img.resize((w, h), Image.Resampling.LANCZOS)
        grid.paste(img, (col * w, row * h))
    return grid


class ImageGenerator:
    """Generate images from text prompts using a diffusion model.

    Inject generate_fn for testing without a GPU or installed diffusers::

        mock = lambda p, **kw: Image.new("RGB", (kw.get("width", 512), kw.get("height", 512)), "steelblue")
        gen = ImageGenerator(generate_fn=mock)
    """

    def __init__(self, model_id: str = "runwayml/stable-diffusion-v1-5",
                 generate_fn=None) -> None:
        self._model_id  = model_id
        self._generate_fn = generate_fn

    def generate(self, prompt: str, negative: str = "",
                 width: int = 512, height: int = 512,
                 steps: int = 20, guidance_scale: float = 7.5,
                 seed: int = 42) -> Image.Image:
        """Generate a single image from a prompt."""
        return generate_image(
            prompt, negative=negative,
            generate_fn=self._generate_fn,
            width=width, height=height,
            steps=steps, guidance_scale=guidance_scale, seed=seed,
        )

    def batch(self, prompts: list, **kwargs) -> list:
        """Generate one image per prompt. Returns list[Image.Image]."""
        return [self.generate(p, **kwargs) for p in prompts]

    def grid(self, prompts: list, cols: int = 2, **kwargs) -> Image.Image:
        """Generate images for all prompts and stitch into a grid."""
        images = self.batch(prompts, **kwargs)
        return create_image_grid(images, cols=cols)
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
day: "070"
lesson: 1
title: "How Diffusion Models Work"
slides:
  - type: title
    heading: "Image Generation"
    subheading: "Day 70 — Diffusion models, prompts, and offline exercises"
    narration: >
      Day 69 extracted structured data from existing images. Today you create
      images from scratch using text prompts and diffusion models. You will
      learn how diffusion models work, how to engineer effective prompts, and
      how to build a generation pipeline with full mock injection so exercises
      run offline without a GPU.

  - type: concept
    label: "Diffusion models"
    heading: "How Diffusion Models Generate Images"
    body: >
      Diffusion models learn to reverse a noise process. Training adds random
      noise to real images step by step until only noise remains. The model
      learns to reverse that process — starting from pure noise and
      progressively denoising toward a clean image.
    bullets:
      - "Forward pass: clean image → add noise → pure noise (training only)"
      - "Reverse pass: pure noise → denoise step by step → clean image (inference)"
      - "Each denoising step uses the text prompt as a guide"
      - "More steps = higher quality but slower (20-50 steps typical)"
    narration: >
      At inference time, generation starts from a tensor of pure Gaussian noise
      and runs the denoising loop for N steps (typically 20-50). At each step,
      the model predicts the noise component and subtracts a fraction of it,
      guided by the text embedding. The result after all steps is a
      photorealistic image matching the prompt. This is why generation is slower
      than classification — it runs the neural network dozens of times.

  - type: concept
    label: "Key parameters"
    heading: "Key Generation Parameters"
    body: >
      Four parameters control generation quality and style. Understanding them
      lets you get consistent, high-quality outputs without trial and error.
    bullets:
      - "steps: denoising iterations — 20 for fast, 50 for high quality"
      - "guidance_scale: prompt adherence strength — 7.5 is standard (higher = more literal)"
      - "seed: random starting noise — same seed + same prompt = same image"
      - "width/height: output size — must be multiples of 8; 512x512 is standard"
    narration: >
      The guidance scale (also called CFG scale, from Classifier-Free Guidance)
      controls how strongly the denoising process follows the text embedding.
      At scale 1, the image is nearly random. At scale 7.5 it follows the
      prompt closely. Above 12-15, images become over-saturated and unnatural.
      The seed controls the initial noise tensor — pin it to reproduce results
      or vary it to explore the prompt's latent space.

  - type: how_it_works
    label: "Stable Diffusion"
    heading: "Stable Diffusion Architecture"
    body: >
      Stable Diffusion has three components: a text encoder, a U-Net denoiser,
      and a VAE decoder.
    bullets:
      - "Text encoder (CLIP): converts prompt to embedding vector"
      - "U-Net denoiser: predicts noise at each step, guided by text embedding"
      - "VAE decoder: converts low-res latent to full-resolution pixel image"
      - "Latent diffusion: noise process runs in latent space (64x64) not pixel space (512x512)"
    narration: >
      Stable Diffusion runs the denoising loop in a compressed latent space
      rather than full pixel space, which is why it's fast enough to run on
      consumer hardware. The VAE encodes a 512x512 image to a 64x64 latent,
      the denoising loop runs at 64x64, and the VAE decoder expands the final
      latent back to 512x512. The CLIP text encoder converts the prompt into a
      768-dimensional embedding vector that guides each denoising step.

  - type: code
    label: "generate_fn pattern"
    heading: "The generate_fn Injection Pattern"
    code: |
      from PIL import Image

      # Mock: returns a plain-colour image — no GPU, no diffusers
      def mock_gen(prompt, **kwargs):
          w = kwargs.get('width', 512)
          h = kwargs.get('height', 512)
          colour = (100, 149, 237)   # cornflower blue
          return Image.new('RGB', (w, h), colour)

      # All generation functions accept generate_fn=None
      # When None: calls the real diffusion pipeline
      # When a callable: calls the mock instead
      img = generate_image('a sunset over mountains',
                           generate_fn=mock_gen, width=256, height=256)
      print(img.size, img.mode)   # (256, 256) RGB
    narration: >
      The generate_fn=None injection pattern is the same approach used for
      describe_fn on Day 67 and ocr_fn on Day 68 — a callable that replaces
      the real model call in tests and headless CI. The mock returns a PIL
      Image of the right size and mode, exercising all the surrounding
      pipeline code without GPU or internet access.

  - type: exercise
    heading: "Exercise 1: Build Prompt"
    prompt: >
      Implement build_prompt(subject, style='', quality_tags=None, negative_tags=None) -> dict.
      Join subject, style, and quality_tags (skip empty) into a comma-separated
      positive string. Join negative_tags into a negative string. Return
      {'positive': str, 'negative': str}. Empty lists or None produce empty strings.
    hint: >
      parts = [subject]; if style: parts.append(style); if quality_tags: parts.extend(quality_tags).
      positive = ', '.join(p.strip() for p in parts if p.strip()).
      negative = ', '.join(t.strip() for t in (negative_tags or []) if t.strip()).
    narration: >
      A clean prompt-builder is the foundation of any image generation pipeline.
      Separating positive and negative into structured parts makes prompts easy
      to compose programmatically from templates and user input.

  - type: summary
    heading: "Lesson 1 Summary"
    bullets:
      - "Diffusion models: denoise from pure noise using text guidance"
      - "steps 20-50, guidance_scale 7-12, seed for reproducibility"
      - "Stable Diffusion: text encoder + U-Net denoiser + VAE decoder"
      - "Latent diffusion: runs at 64x64 in latent space, expands to 512x512"
      - "generate_fn=None injection: same pattern as describe_fn, ocr_fn"
    narration: >
      The theory is in place. Next: prompt engineering — how to write prompts
      that reliably produce high-quality images in specific styles.
"""

_LESSON_02 = """\
day: "070"
lesson: 2
title: "Prompt Engineering for Images"
slides:
  - type: title
    heading: "Prompt Engineering for Images"
    subheading: "Positive prompts, negative prompts, style templates"
    narration: >
      Image generation quality is highly sensitive to prompt wording. This
      lesson covers the structure of effective prompts: quality tokens that
      boost fidelity, negative prompts that prevent artefacts, and style
      templates that apply a consistent look across any subject.

  - type: concept
    label: "Prompt anatomy"
    heading: "Anatomy of an Image Generation Prompt"
    body: >
      An effective positive prompt has three layers: subject, style, and
      quality. Order matters — Stable Diffusion gives more weight to tokens
      earlier in the prompt.
    bullets:
      - "Subject: what to show — a golden retriever on a beach at sunset"
      - "Style: visual treatment — oil painting, impressionist, watercolor"
      - "Quality tokens: fidelity boosters — masterpiece, 8k, highly detailed"
      - "Rule of thumb: subject first, style second, quality last"
    narration: >
      Diffusion models use a transformer text encoder that attends to all
      tokens, but empirically tokens near the start of the prompt receive
      slightly higher attention weight. Putting the main subject first ensures
      the model centres the image on it. Style terms in the middle shape the
      visual treatment. Quality tokens at the end nudge the model toward its
      best-quality training examples.

  - type: concept
    label: "Negative prompts"
    heading: "Negative Prompts"
    body: >
      Negative prompts tell the model what to avoid. They are as important
      as positive prompts for consistent quality.
    bullets:
      - "Common negatives: blurry, low quality, watermark, text, cropped, ugly"
      - "Style negatives: cartoon (for photorealistic), realistic (for anime)"
      - "Anatomy negatives: extra fingers, deformed, disfigured"
      - "Negative prompt works via classifier-free guidance — opposite direction in latent space"
    narration: >
      During each denoising step, the U-Net is run twice — once conditioned
      on the positive prompt and once on the negative prompt. The final
      denoising direction is the positive direction minus the negative
      direction, scaled by guidance_scale. This means negative prompts
      actively steer the image away from unwanted concepts at every single
      denoising step, not just as a post-filter.

  - type: code
    label: "Style templates"
    heading: "Style Templates"
    code: |
      STYLE_TEMPLATES = {
          'cinematic': {
              'positive': 'cinematic lighting, film grain, dramatic shadows',
              'negative': 'flat lighting, cartoon, illustration',
          },
          'photorealistic': {
              'positive': 'photorealistic, 8k uhd, high detail, DSLR',
              'negative': 'painting, drawing, blur, watermark',
          },
          'watercolor': {
              'positive': 'watercolor painting, soft edges, artistic',
              'negative': 'photorealistic, sharp, digital art',
          },
      }

      def apply_style_template(base_prompt, template_name, templates=None):
          tmpl = (templates or STYLE_TEMPLATES)[template_name]
          pos = base_prompt + ', ' + tmpl['positive']
          return {'positive': pos, 'negative': tmpl['negative']}

      result = apply_style_template('a mountain lake', 'cinematic')
      print(result['positive'][:60])   # a mountain lake, cinematic lighting...
      print(result['negative'][:40])   # flat lighting, cartoon, illustration
    narration: >
      Templates separate reusable style DNA from the per-image subject.
      The same photorealistic template applied to a dozen different subjects
      produces a consistent visual look. Templates also make it easy to do
      A/B comparisons — generate the same subject with watercolor vs cinematic
      and show both to a user. The negative prompt from the template is
      essential: photorealistic negative prevents the model from adding
      painterly artefacts, which it would otherwise add because painting
      examples are plentiful in training data.

  - type: code
    label: "Prompt composition"
    heading: "Composing Prompts Programmatically"
    code: |
      def build_prompt(subject, style='', quality_tags=None, negative_tags=None):
          parts = [subject]
          if style: parts.append(style)
          if quality_tags: parts.extend(quality_tags)
          positive = ', '.join(p.strip() for p in parts if p.strip())
          negative = ', '.join(t.strip() for t in (negative_tags or []) if t.strip())
          return {'positive': positive, 'negative': negative}

      p = build_prompt(
          subject='a golden retriever on a beach at sunset',
          style='oil painting, impressionist',
          quality_tags=['masterpiece', 'best quality'],
          negative_tags=['blurry', 'low quality', 'watermark'],
      )
      print(p['positive'])
      # a golden retriever on a beach at sunset, oil painting,
      # impressionist, masterpiece, best quality
    narration: >
      Programmatic prompt construction makes it easy to vary individual
      components systematically — swap subjects while keeping style and quality
      constant, or compare styles on the same subject. It also prevents typos
      in repeated quality tokens and makes prompts easy to serialise to JSON
      for logging and reproducibility.

  - type: exercise
    heading: "Exercise 2: Apply Style Template"
    prompt: >
      Implement apply_style_template(base_prompt, template_name, templates=None) -> dict.
      Look up template_name in templates (or STYLE_TEMPLATES if None). Raise ValueError
      for unknown names with the message: f'Unknown style template {template_name!r}.
      Available: {list(tmpl_dict.keys())}'. Prepend base_prompt to the template's positive
      string with ', ' separator. Return the template's negative unchanged.
      Return {'positive': str, 'negative': str}.
    hint: >
      tmpl_dict = templates if templates is not None else STYLE_TEMPLATES.
      tmpl = tmpl_dict.get(template_name) — if None: raise ValueError.
      pos = base_prompt + ', ' + tmpl['positive'] if base_prompt.strip() else tmpl['positive'].
    narration: >
      Style templates are the fastest way to improve image quality
      programmatically. This function is the core of any template system
      that lets users pick a visual style from a menu.

  - type: summary
    heading: "Lesson 2 Summary"
    bullets:
      - "Prompt order: subject → style → quality tokens"
      - "Negative prompts steer every denoising step away from unwanted concepts"
      - "Common negatives: blurry, low quality, watermark, text, cropped"
      - "Style templates: reusable positive/negative pairs per visual style"
      - "Programmatic composition: build_prompt returns a dict with positive/negative"
    narration: >
      Prompt engineering is in place. Next: the core generation function and
      how all parameters wire together into a single generate_image call.
"""

_LESSON_03 = """\
day: "070"
lesson: 3
title: "The Generation Function"
slides:
  - type: title
    heading: "The Generation Function"
    subheading: "generate_image — parameters, mocking, reproducibility"
    narration: >
      Lessons 1 and 2 built the prompt layer. This lesson assembles
      generate_image — the single function that accepts a prompt and all
      generation parameters and returns a PIL Image. Like describe_image
      on Day 67, it accepts a generate_fn mock for headless testing.

  - type: how_it_works
    label: "generate_image"
    heading: "generate_image: Full Signature"
    body: >
      All generation parameters have sensible defaults. generate_fn is the
      test injection point — same pattern as describe_fn and ocr_fn.
    narration: >
      The function signature captures the five dimensions of a generation
      request: what to generate (prompt, negative), what size (width, height),
      how much quality (steps), how literally to follow the prompt
      (guidance_scale), and which starting noise to use (seed). All have
      defaults that work well for general use. The generate_fn parameter
      is the test injection point — when not None, the function is called
      instead of the real diffusion pipeline.

  - type: code
    label: "generate_image"
    heading: "generate_image Implementation"
    code: |
      from PIL import Image

      def generate_image(prompt, negative='', generate_fn=None,
                         width=512, height=512, steps=20,
                         guidance_scale=7.5, seed=42) -> Image.Image:
          if generate_fn is not None:
              return generate_fn(prompt, negative=negative, width=width,
                                 height=height, steps=steps,
                                 guidance_scale=guidance_scale, seed=seed)
          # Real diffusers implementation (lazy import)
          from diffusers import StableDiffusionPipeline
          import torch
          pipe = StableDiffusionPipeline.from_pretrained(
              'runwayml/stable-diffusion-v1-5',
              torch_dtype=torch.float32,
          )
          generator = torch.Generator().manual_seed(seed)
          result = pipe(prompt, negative_prompt=negative or None,
                        width=width, height=height,
                        num_inference_steps=steps,
                        guidance_scale=guidance_scale,
                        generator=generator)
          return result.images[0]
    narration: >
      The lazy import of diffusers and torch means the module imports cleanly
      even if those packages are not installed. The pipeline is only loaded
      when generate_fn is None and a real generation is requested. For
      exercises and tests, generate_fn is always provided, so the diffusers
      import never runs. This is the same deferred-import pattern used for
      ollama in Days 67-69.

  - type: code
    label: "Testing"
    heading: "Testing generate_image with a Mock"
    code: |
      def mock_gen(prompt, **kwargs):
          w = kwargs.get('width', 512)
          h = kwargs.get('height', 512)
          return Image.new('RGB', (w, h), 'steelblue')

      # Test size propagation
      img = generate_image('a cat', generate_fn=mock_gen,
                           width=256, height=128)
      assert img.size == (256, 128)    # width x height
      assert img.mode == 'RGB'

      # Test default size
      img2 = generate_image('a dog', generate_fn=mock_gen)
      assert img2.size == (512, 512)

      print('Tests passed')
    narration: >
      The mock captures all keyword arguments, including width and height,
      and returns an Image of the correct size. This tests the full call
      chain: generate_image receives the parameters, passes them to
      generate_fn, and returns the result. Every aspect of the function
      except the actual diffusion computation is exercised.

  - type: concept
    label: "Reproducibility"
    heading: "Seeds and Reproducibility"
    body: >
      The same prompt + seed always produces the same image. This is the
      key to iterative prompt refinement and variation generation.
    bullets:
      - "seed=42: same every run — use for testing and comparison"
      - "Different seeds, same prompt: explore the same concept differently"
      - "torch.Generator().manual_seed(seed): sets per-call random state"
      - "Save seed with image metadata for exact reproduction later"
    narration: >
      Seeds are the primary tool for systematic image exploration. To compare
      two prompts fairly — for example, to see if a style change improves
      quality — run both with the same seed. To generate a batch of variations
      on a theme — same prompt, different compositions — use different seeds.
      The generate_variations function in Exercise 4 automates this pattern:
      it generates N images of the same prompt with seeds 42, 1042, 2042, ...

  - type: exercise
    heading: "Exercise 3: Generate Image"
    prompt: >
      Implement generate_image(prompt, negative='', generate_fn=None, width=512,
      height=512, steps=20, guidance_scale=7.5, seed=42) -> Image.Image.
      If generate_fn is not None: return generate_fn(prompt, negative=negative,
      width=width, height=height, steps=steps, guidance_scale=guidance_scale,
      seed=seed). Otherwise, use diffusers.StableDiffusionPipeline (lazy import).
      The exercises all test with a mock, so the diffusers path is not required
      to be tested here.
    hint: >
      if generate_fn is not None: return generate_fn(prompt, negative=negative, width=width,
      height=height, steps=steps, guidance_scale=guidance_scale, seed=seed).
      The mock returns Image.new('RGB', (width, height), 'steelblue').
    narration: >
      generate_image is the hub of the whole pipeline. All higher-level
      functions call it. Getting the parameter forwarding right means every
      downstream function inherits correct behaviour automatically.

  - type: summary
    heading: "Lesson 3 Summary"
    bullets:
      - "generate_image: prompt + 6 params + generate_fn → PIL Image"
      - "generate_fn=None: lazy import diffusers, load pipeline on demand"
      - "Lazy import: module loads cleanly even without diffusers installed"
      - "Same seed + prompt = same image (reproducibility)"
      - "Mock captures kwargs, returns Image.new of correct size — tests all wiring"
    narration: >
      The core generation function is settled. Next: generating multiple
      images and creating a variation grid.
"""

_LESSON_04 = """\
day: "070"
lesson: 4
title: "Variations and Grids"
slides:
  - type: title
    heading: "Variations and Grids"
    subheading: "generate_variations, create_image_grid"
    narration: >
      A single image rarely captures the best interpretation of a prompt.
      Professional image generation workflows always generate multiple
      variations and compare them side by side. This lesson builds the
      two functions that enable this: generate_variations creates N images
      with different seeds, and create_image_grid stitches them into a
      single comparison image.

  - type: concept
    label: "Variations"
    heading: "Why Generate Multiple Variations"
    body: >
      Diffusion models are stochastic. The same prompt with different
      starting noise produces different compositions, lighting, and details.
    bullets:
      - "Variation 1 might have better composition, variation 3 better lighting"
      - "N=4 variations covers the most common distinct interpretations"
      - "Compare variations by generating with seeds 0, 1000, 2000, 3000"
      - "Pick the best one, refine its seed with prompt changes"
    narration: >
      Because generation starts from random noise, each run is like a random
      draw from a distribution of images that match the prompt. Some draws are
      excellent, some mediocre. Generating 4-8 variations lets you select the
      best composition before investing time in higher-quality settings (more
      steps, larger size). Using seeds 0, 1000, 2000, ... makes the variation
      set deterministic and reproducible.

  - type: code
    label: "generate_variations"
    heading: "generate_variations Implementation"
    code: |
      def generate_variations(base_prompt, n_variations,
                               generate_fn=None, **kwargs):
          images = []
          for i in range(n_variations):
              seed = i * 1000 + 42    # 42, 1042, 2042, ...
              img = generate_image(base_prompt, generate_fn=generate_fn,
                                   seed=seed, **kwargs)
              images.append(img)
          return images

      mock = lambda p, **kw: Image.new('RGB', (64, 64), 'steelblue')
      variations = generate_variations('a lighthouse', 4, generate_fn=mock)
      print(len(variations), variations[0].size)   # 4 (64, 64)
    narration: >
      The seed formula `i * 1000 + 42` ensures seeds are well-separated —
      seeds that are close together (0, 1, 2) often produce similar-looking
      images because the initial noise tensors are correlated. Seeds 1000 apart
      are reliably distinct. The `**kwargs` forwarding passes width, height,
      steps and guidance_scale through to generate_image, so all generation
      parameters can be controlled from the caller.

  - type: code
    label: "create_image_grid"
    heading: "create_image_grid Implementation"
    code: |
      import math
      from PIL import Image

      def create_image_grid(images, cols=2):
          if not images:
              raise ValueError('images list must not be empty')
          cols = max(1, min(cols, len(images)))
          rows = math.ceil(len(images) / cols)
          w, h = images[0].size
          grid = Image.new('RGB', (cols * w, rows * h), 'white')
          for i, img in enumerate(images):
              col = i % cols
              row = i // cols
              if img.size != (w, h):
                  img = img.resize((w, h), Image.Resampling.LANCZOS)
              grid.paste(img, (col * w, row * h))
          return grid

      # 4 images, 2 columns → 2x2 grid of (64,64) = (128, 128)
      imgs = [Image.new('RGB', (64, 64), c) for c in ['red','blue','green','yellow']]
      grid = create_image_grid(imgs, cols=2)
      print(grid.size)   # (128, 128)
    narration: >
      The grid function uses ceiling division for rows so odd numbers of images
      are handled: 3 images in 2 columns gives 2 rows (2+1). The `min(cols,
      len(images))` guard prevents cols being larger than the number of images,
      which would create an absurdly wide grid with empty columns. Images are
      resized to match the first image's dimensions if they differ — this
      handles the case where mock images have different sizes than real ones.

  - type: exercise
    heading: "Exercise 4: Variations and Grid"
    prompt: >
      Implement two functions:
      1. generate_variations(base_prompt, n_variations, generate_fn=None, **kwargs)
         -> list[Image.Image]. Use seed = i * 1000 + 42 for each variation.
         Forward kwargs to generate_image.
      2. create_image_grid(images, cols=2) -> Image.Image. Raise ValueError for
         empty list. Cap cols to len(images). Use math.ceil for rows. Build
         Image.new('RGB', (cols*w, rows*h), 'white'). Paste each image at its
         grid position (col*w, row*h). Resize mismatched images to (w, h).
    hint: >
      generate_variations: for i in range(n_variations): seed = i*1000+42; append generate_image(..., seed=seed, **kwargs).
      create_image_grid: cols = max(1, min(cols, len(images))); rows = math.ceil(len(images)/cols); w,h = images[0].size.
    narration: >
      generate_variations and create_image_grid together form the exploration
      loop: generate N → view grid → pick best seed → refine prompt. They are
      the practical foundation of any image generation UI or API.

  - type: summary
    heading: "Lesson 4 Summary"
    bullets:
      - "Generate 4-8 variations per prompt to cover distinct interpretations"
      - "Seeds i*1000+42: well-separated, deterministic, reproducible"
      - "create_image_grid: ceiling division for rows, min(cols, n) guard"
      - "Grid paste: position = (col*w, row*h)"
      - "Resize mismatched images to match first image size"
    narration: >
      Variation generation and grid display are complete. The final lesson
      wraps everything into an ImageGenerator class and connects to the
      full pipeline.
"""

_LESSON_05 = """\
day: "070"
lesson: 5
title: "ImageGenerator — Full Pipeline"
slides:
  - type: title
    heading: "ImageGenerator"
    subheading: "Full pipeline class — prompt to pixel"
    narration: >
      The individual functions are all in place. This lesson assembles
      them into an ImageGenerator class that binds the generate_fn at
      construction time, exposes generate, batch, and grid methods, and
      provides a clean interface for the final exercise and the project.

  - type: how_it_works
    label: "ImageGenerator"
    heading: "ImageGenerator Design"
    body: >
      Three methods, one per use case. generate is single-image, batch
      is multi-prompt, grid is batch + stitch.
    bullets:
      - "ImageGenerator(model_id='...', generate_fn=None)"
      - ".generate(prompt, ...) -> Image.Image — one prompt, one image"
      - ".batch(prompts, ...) -> list[Image.Image] — list of prompts"
      - ".grid(prompts, cols=2, ...) -> Image.Image — batch + stitch"
    narration: >
      The class binds generate_fn at construction time, same as VisionAnalyzer
      on Day 67 and ImageExtractor on Day 69. This makes the object reusable
      across many generate calls without passing the mock every time. The batch
      and grid methods are thin wrappers: batch calls generate per prompt, grid
      calls batch then create_image_grid. No logic is duplicated.

  - type: code
    label: "Usage"
    heading: "Using ImageGenerator"
    code: |
      from PIL import Image
      from image_generator import ImageGenerator

      # Testing mode — no GPU
      mock = lambda p, **kw: Image.new('RGB',
             (kw.get('width', 512), kw.get('height', 512)), 'steelblue')
      gen = ImageGenerator(generate_fn=mock)

      # Single image
      img = gen.generate('a sunset over mountains', width=256, height=256)
      print(img.size, img.mode)   # (256, 256) RGB

      # Batch
      prompts = ['a cat', 'a dog', 'a bird']
      imgs = gen.batch(prompts, width=128, height=128)
      print(len(imgs))   # 3

      # Grid
      grid = gen.grid(prompts, cols=3, width=128, height=128)
      print(grid.size)   # (384, 128) — 3 cols x 1 row
    narration: >
      The class interface is clean and consistent. A student building an image
      generation app swaps the mock for a real generate_fn by changing one
      argument in the constructor, not by modifying any route handler or
      business logic. This is the injection pattern paying off at the
      application level.

  - type: code
    label: "Real usage"
    heading: "Using the Real Diffusion Pipeline"
    code: |
      # Install first: pip install diffusers transformers accelerate torch
      # Then pull model: python -c "from diffusers import StableDiffusionPipeline; StableDiffusionPipeline.from_pretrained('runwayml/stable-diffusion-v1-5')"
      # GPU strongly recommended (CPU will take ~10-30 minutes per image)

      from image_generator import ImageGenerator, apply_style_template

      gen = ImageGenerator(model_id='runwayml/stable-diffusion-v1-5')

      # Apply a style template first
      p = apply_style_template('a golden retriever on a beach', 'photorealistic')

      # Generate one image
      img = gen.generate(p['positive'], negative=p['negative'],
                         steps=30, guidance_scale=7.5, seed=42)
      img.save('output.png')
      print('Saved output.png')
    narration: >
      The real pipeline requires GPU memory (4-8 GB for float16, 8-16 GB for
      float32). Smaller models like stabilityai/stable-diffusion-2-1 have
      the same API. On CPU, generation takes minutes per image — use the mock
      for development and switch to real generation only for final outputs
      or when GPU is available.

  - type: exercise
    heading: "Exercise 5: ImageGenerator Class"
    prompt: >
      Implement the ImageGenerator class:
      - __init__(self, model_id='runwayml/stable-diffusion-v1-5', generate_fn=None)
      - generate(self, prompt, negative='', width=512, height=512, steps=20,
          guidance_scale=7.5, seed=42) -> Image.Image
        Delegates to generate_image with self._generate_fn.
      - batch(self, prompts, **kwargs) -> list[Image.Image]
        Returns [self.generate(p, **kwargs) for p in prompts].
      - grid(self, prompts, cols=2, **kwargs) -> Image.Image
        Returns create_image_grid(self.batch(prompts, **kwargs), cols=cols).
    hint: >
      __init__: self._model_id = model_id; self._generate_fn = generate_fn.
      generate: return generate_image(prompt, ..., generate_fn=self._generate_fn, ...).
      batch: list comprehension over prompts. grid: batch then create_image_grid.
    narration: >
      ImageGenerator is the capstone of Day 70 — it wires all five exercises
      into a single reusable object that can be dropped into any app or
      notebook with one line of setup.

  - type: summary
    heading: "Lesson 5 Summary — Day 70 Complete"
    bullets:
      - "ImageGenerator: generate_fn bound at construction, three methods"
      - ".generate() delegates to generate_image with self._generate_fn"
      - ".batch() maps generate over a list of prompts"
      - ".grid() = batch + create_image_grid"
      - "Tomorrow (Day 71): Vision + RAG — search images by content"
    narration: >
      Day 70 is complete. You can build text-to-image prompts, generate
      images from code with a fully mockable pipeline, create variation
      batches, and stitch results into comparison grids — all without
      needing a GPU for development. Tomorrow is vision RAG, combining
      the image analysis skills from Days 66-67 with the vector search
      skills from Days 11-12.
"""

for i, content in enumerate([_LESSON_01, _LESSON_02, _LESSON_03,
                               _LESSON_04, _LESSON_05], start=1):
    (OUT / "lessons" / f"day_{DAY}_lesson_0{i}.yaml").write_text(content)

# ── shared helper source ───────────────────────────────────────────────────────
_HELPER_SRC = """\
import math
from PIL import Image

STYLE_TEMPLATES = {
    'cinematic': {
        'positive': 'cinematic lighting, film grain, dramatic shadows',
        'negative': 'flat lighting, cartoon, illustration',
    },
    'photorealistic': {
        'positive': 'photorealistic, 8k uhd, high detail, DSLR',
        'negative': 'painting, drawing, blur, watermark',
    },
    'watercolor': {
        'positive': 'watercolor painting, soft edges, artistic',
        'negative': 'photorealistic, sharp, digital art',
    },
    'anime': {
        'positive': 'anime style, cel shaded, vibrant colours',
        'negative': 'photorealistic, watercolor, oil painting',
    },
}

def build_prompt(subject, style='', quality_tags=None, negative_tags=None):
    parts = [subject]
    if style: parts.append(style)
    if quality_tags: parts.extend(quality_tags)
    positive = ', '.join(p.strip() for p in parts if p.strip())
    negative = ', '.join(t.strip() for t in (negative_tags or []) if t.strip())
    return {'positive': positive, 'negative': negative}

def apply_style_template(base_prompt, template_name, templates=None):
    tmpl_dict = templates if templates is not None else STYLE_TEMPLATES
    tmpl = tmpl_dict.get(template_name)
    if tmpl is None:
        raise ValueError(f'Unknown style template {template_name!r}. Available: {list(tmpl_dict.keys())}')
    pos = base_prompt + ', ' + tmpl['positive'] if base_prompt.strip() else tmpl['positive']
    return {'positive': pos, 'negative': tmpl['negative']}

def generate_image(prompt, negative='', generate_fn=None,
                   width=512, height=512, steps=20,
                   guidance_scale=7.5, seed=42):
    if generate_fn is not None:
        return generate_fn(prompt, negative=negative, width=width,
                           height=height, steps=steps,
                           guidance_scale=guidance_scale, seed=seed)
    from diffusers import StableDiffusionPipeline
    import torch
    pipe = StableDiffusionPipeline.from_pretrained(
        'runwayml/stable-diffusion-v1-5',
        torch_dtype=torch.float32,
    )
    generator = torch.Generator().manual_seed(seed)
    result = pipe(prompt, negative_prompt=negative or None,
                  width=width, height=height,
                  num_inference_steps=steps,
                  guidance_scale=guidance_scale,
                  generator=generator)
    return result.images[0]

def generate_variations(base_prompt, n_variations, generate_fn=None, **kwargs):
    images = []
    for i in range(n_variations):
        seed = i * 1000 + 42
        img = generate_image(base_prompt, generate_fn=generate_fn, seed=seed, **kwargs)
        images.append(img)
    return images

def create_image_grid(images, cols=2):
    if not images:
        raise ValueError('images list must not be empty')
    cols = max(1, min(cols, len(images)))
    rows = math.ceil(len(images) / cols)
    w, h = images[0].size
    grid = Image.new('RGB', (cols * w, rows * h), 'white')
    for i, img in enumerate(images):
        col = i % cols
        row = i // cols
        if img.size != (w, h):
            img = img.resize((w, h), Image.Resampling.LANCZOS)
        grid.paste(img, (col * w, row * h))
    return grid
"""

# standard mock for all exercises
_MOCK_DEF = """\
_mock_gen = lambda prompt, **kw: Image.new('RGB', (kw.get('width', 512), kw.get('height', 512)), 'steelblue')
"""

# ── EXERCISE 1 — build_prompt ─────────────────────────────────────────────────
_EX1_GIVEN = """\
from PIL import Image
"""

_EX1_STUB = """\
def build_prompt(subject: str, style: str = '',
                 quality_tags: list = None,
                 negative_tags: list = None) -> dict:
    \"\"\"Build a positive/negative prompt pair for image generation.

    Args:
        subject:       Main subject description
        style:         Visual style string appended after subject
        quality_tags:  Additional positive tags (e.g. masterpiece, 8k)
        negative_tags: Tags describing what to avoid
    Returns:
        {'positive': str, 'negative': str}
    \"\"\"
    raise NotImplementedError
"""

_EX1_SOLUTION = """\
def build_prompt(subject: str, style: str = '',
                 quality_tags: list = None,
                 negative_tags: list = None) -> dict:
    parts = [subject]
    if style:
        parts.append(style)
    if quality_tags:
        parts.extend(quality_tags)
    positive = ', '.join(p.strip() for p in parts if p.strip())
    negative = ', '.join(t.strip() for t in (negative_tags or []) if t.strip())
    return {'positive': positive, 'negative': negative}
"""

_EX1_CHECKS = """\
score, total = 0, 5
try:
    p = build_prompt('a cat on a moon')
    assert isinstance(p, dict) and 'positive' in p and 'negative' in p
    score += 1; print("\\u2705 returns dict with positive/negative keys")

    assert p['positive'] == 'a cat on a moon', f"Unexpected: {p['positive']!r}"
    assert p['negative'] == '', f"Unexpected: {p['negative']!r}"
    score += 1; print("\\u2705 subject-only prompt")

    p2 = build_prompt('a cat', style='oil painting',
                      quality_tags=['masterpiece', 'best quality'])
    assert 'a cat' in p2['positive']
    assert 'oil painting' in p2['positive']
    assert 'masterpiece' in p2['positive']
    score += 1; print("\\u2705 style and quality_tags included")

    p3 = build_prompt('a dog', negative_tags=['blurry', 'low quality'])
    assert p3['negative'] == 'blurry, low quality', f"Got: {p3['negative']!r}"
    score += 1; print("\\u2705 negative_tags joined correctly")

    p4 = build_prompt('a bird', quality_tags=None, negative_tags=None)
    assert p4['negative'] == ''
    p5 = build_prompt('', style='cinematic')
    assert 'cinematic' in p5['positive']
    score += 1; print("\\u2705 handles None tags and empty subject")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX1 = nb([
    md("# Day 070 — Exercise 1: Build Prompt\n\n"
       "**What you'll build:** `build_prompt(subject, style, quality_tags, negative_tags) -> dict` — "
       "construct a positive/negative prompt pair for image generation.\n\n"
       "**Why it matters:** Structured prompts are the foundation of reproducible image generation. "
       "Separating subject, style, quality, and negative into explicit parameters makes prompts "
       "easy to compose programmatically, version, and compare."),
    code(_EX1_GIVEN),
    md("## Task\n\nImplement `build_prompt`:\n\n"
       "1. Start with `parts = [subject]`\n"
       "2. Append `style` if non-empty\n"
       "3. Extend with `quality_tags` if provided\n"
       "4. `positive = ', '.join(p.strip() for p in parts if p.strip())`\n"
       "5. `negative = ', '.join(t.strip() for t in (negative_tags or []) if t.strip())`\n"
       "6. Return `{'positive': positive, 'negative': negative}`"),
    md("## Your Implementation"),
    code(_EX1_STUB),
    code(_EX1_SOLUTION),
    md("## Automated checks"),
    code(_EX1_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX1_SOLUTION + "```\n\n"
       "**Why filter `if p.strip()`?** An empty subject (or style) passed "
       "without a value would produce a leading comma. The filter removes "
       "blank/whitespace-only parts cleanly.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_01.ipynb", EX1)

# ── EXERCISE 2 — apply_style_template ────────────────────────────────────────
_EX2_GIVEN = """\
from PIL import Image

STYLE_TEMPLATES = {
    'cinematic': {
        'positive': 'cinematic lighting, film grain, dramatic shadows',
        'negative': 'flat lighting, cartoon, illustration',
    },
    'photorealistic': {
        'positive': 'photorealistic, 8k uhd, high detail, DSLR',
        'negative': 'painting, drawing, blur, watermark',
    },
    'watercolor': {
        'positive': 'watercolor painting, soft edges, artistic',
        'negative': 'photorealistic, sharp, digital art',
    },
    'anime': {
        'positive': 'anime style, cel shaded, vibrant colours',
        'negative': 'photorealistic, watercolor, oil painting',
    },
}
"""

_EX2_STUB = """\
def apply_style_template(base_prompt: str, template_name: str,
                          templates: dict = None) -> dict:
    \"\"\"Merge a base prompt with a named style template.

    Args:
        base_prompt:   Subject or scene description
        template_name: Key in STYLE_TEMPLATES (or custom templates dict)
        templates:     Custom template dict; defaults to STYLE_TEMPLATES
    Returns:
        {'positive': str, 'negative': str}
    Raises:
        ValueError for unknown template names
    \"\"\"
    raise NotImplementedError
"""

_EX2_SOLUTION = """\
def apply_style_template(base_prompt: str, template_name: str,
                          templates: dict = None) -> dict:
    tmpl_dict = templates if templates is not None else STYLE_TEMPLATES
    tmpl = tmpl_dict.get(template_name)
    if tmpl is None:
        raise ValueError(
            f'Unknown style template {template_name!r}. '
            f'Available: {list(tmpl_dict.keys())}'
        )
    pos = base_prompt + ', ' + tmpl['positive'] if base_prompt.strip() else tmpl['positive']
    return {'positive': pos, 'negative': tmpl['negative']}
"""

_EX2_CHECKS = """\
score, total = 0, 5
try:
    result = apply_style_template('a mountain lake', 'cinematic')
    assert isinstance(result, dict) and 'positive' in result and 'negative' in result
    score += 1; print("\\u2705 returns dict with positive/negative keys")

    assert result['positive'].startswith('a mountain lake, cinematic')
    score += 1; print("\\u2705 base_prompt prepended to template positive")

    assert result['negative'] == STYLE_TEMPLATES['cinematic']['negative']
    score += 1; print("\\u2705 negative is unmodified template negative")

    # Empty base_prompt: template positive only
    r2 = apply_style_template('', 'watercolor')
    assert r2['positive'] == STYLE_TEMPLATES['watercolor']['positive']
    score += 1; print("\\u2705 empty base_prompt returns template positive only")

    # Unknown template raises ValueError
    raised = False
    try:
        apply_style_template('test', 'unknown_style_xyz')
    except ValueError:
        raised = True
    assert raised, "Should raise ValueError for unknown template"
    score += 1; print("\\u2705 raises ValueError for unknown template name")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX2 = nb([
    md("# Day 070 — Exercise 2: Apply Style Template\n\n"
       "**What you'll build:** `apply_style_template(base_prompt, template_name, templates=None) -> dict` — "
       "merge a subject prompt with a named style template.\n\n"
       "**Why it matters:** Style templates separate reusable visual DNA (lighting, fidelity) "
       "from per-image subject matter. One template applied to many subjects produces "
       "a consistent visual style across an entire generation batch."),
    code(_EX2_GIVEN),
    md("## Task\n\nImplement `apply_style_template`:\n\n"
       "1. `tmpl_dict = templates if templates is not None else STYLE_TEMPLATES`\n"
       "2. `tmpl = tmpl_dict.get(template_name)` — if `None`, raise `ValueError`\n"
       "3. `pos = base_prompt + ', ' + tmpl['positive'] if base_prompt.strip() else tmpl['positive']`\n"
       "4. Return `{'positive': pos, 'negative': tmpl['negative']}`"),
    md("## Your Implementation"),
    code(_EX2_STUB),
    code(_EX2_SOLUTION),
    md("## Automated checks"),
    code(_EX2_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX2_SOLUTION + "```\n\n"
       "**Why `templates is not None` not `templates or STYLE_TEMPLATES`?** "
       "If someone passes an empty dict `{}` as templates, `templates or STYLE_TEMPLATES` "
       "would fall back to STYLE_TEMPLATES silently. `is not None` respects the "
       "caller's explicit choice (empty dict → raise ValueError for any lookup).\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_02.ipynb", EX2)

# ── EXERCISE 3 — generate_image ───────────────────────────────────────────────
_EX3_GIVEN = """\
from PIL import Image
""" + _MOCK_DEF

_EX3_STUB = """\
def generate_image(prompt: str, negative: str = '',
                   generate_fn=None,
                   width: int = 512, height: int = 512,
                   steps: int = 20, guidance_scale: float = 7.5,
                   seed: int = 42):
    \"\"\"Generate an image from a text prompt.

    Args:
        prompt:         Positive text prompt
        negative:       Negative text prompt
        generate_fn:    callable(prompt, **kwargs) -> PIL.Image for testing
        width:          Output width in pixels
        height:         Output height in pixels
        steps:          Denoising steps
        guidance_scale: CFG scale
        seed:           Random seed
    Returns:
        PIL.Image.Image
    \"\"\"
    raise NotImplementedError
"""

_EX3_SOLUTION = """\
def generate_image(prompt: str, negative: str = '',
                   generate_fn=None,
                   width: int = 512, height: int = 512,
                   steps: int = 20, guidance_scale: float = 7.5,
                   seed: int = 42):
    if generate_fn is not None:
        return generate_fn(prompt, negative=negative, width=width,
                           height=height, steps=steps,
                           guidance_scale=guidance_scale, seed=seed)
    from diffusers import StableDiffusionPipeline
    import torch
    pipe = StableDiffusionPipeline.from_pretrained(
        'runwayml/stable-diffusion-v1-5',
        torch_dtype=torch.float32,
    )
    generator = torch.Generator().manual_seed(seed)
    result = pipe(prompt, negative_prompt=negative or None,
                  width=width, height=height,
                  num_inference_steps=steps,
                  guidance_scale=guidance_scale,
                  generator=generator)
    return result.images[0]
"""

_EX3_CHECKS = """\
score, total = 0, 5
try:
    img = generate_image('a cat on a moon', generate_fn=_mock_gen)
    assert isinstance(img, Image.Image), f"Expected PIL Image, got {type(img)}"
    score += 1; print("\\u2705 returns PIL Image")

    assert img.size == (512, 512), f"Expected (512,512), got {img.size}"
    assert img.mode == 'RGB'
    score += 1; print("\\u2705 default size (512, 512) RGB")

    img2 = generate_image('a dog', generate_fn=_mock_gen, width=256, height=128)
    assert img2.size == (256, 128), f"Expected (256,128), got {img2.size}"
    score += 1; print("\\u2705 width/height propagated to generate_fn")

    # Verify generate_fn receives all params
    captured = {}
    def _capture(prompt, **kw):
        captured.update({'prompt': prompt, **kw})
        return Image.new('RGB', (kw.get('width', 64), kw.get('height', 64)), 'red')

    generate_image('sky', negative='clouds', generate_fn=_capture,
                   steps=30, guidance_scale=9.0, seed=99)
    assert captured.get('steps') == 30
    assert abs(captured.get('guidance_scale', 0) - 9.0) < 0.001
    assert captured.get('seed') == 99
    score += 1; print("\\u2705 all params forwarded to generate_fn")

    assert captured.get('negative') == 'clouds'
    score += 1; print("\\u2705 negative prompt forwarded")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX3 = nb([
    md("# Day 070 — Exercise 3: Generate Image\n\n"
       "**What you'll build:** `generate_image(prompt, negative, generate_fn, width, height, steps, guidance_scale, seed)` — "
       "the core generation function that forwards all parameters to the mock or real pipeline.\n\n"
       "**Why it matters:** All higher-level functions (`generate_variations`, `ImageGenerator.generate`) "
       "delegate to this one. Getting parameter forwarding right here means downstream "
       "functions automatically work correctly."),
    code(_EX3_GIVEN),
    md("## Task\n\nImplement `generate_image`:\n\n"
       "1. If `generate_fn is not None`: "
       "return `generate_fn(prompt, negative=negative, width=width, height=height, steps=steps, guidance_scale=guidance_scale, seed=seed)`\n"
       "2. Otherwise: use `diffusers.StableDiffusionPipeline` (lazy import — only needed for real generation)\n\n"
       "The checks always use `_mock_gen`, so the diffusers path is not required to work in exercises."),
    md("## Your Implementation"),
    code(_EX3_STUB),
    code(_EX3_SOLUTION),
    md("## Automated checks"),
    code(_EX3_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX3_SOLUTION + "```\n\n"
       "**Why lazy import diffusers?** Diffusers and torch are multi-gigabyte "
       "packages. By importing them only inside the `else` branch, the module "
       "loads cleanly in any environment. Students who have only PIL installed "
       "can still use all exercises via mock injection.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_03.ipynb", EX3)

# ── EXERCISE 4 — variations + grid ───────────────────────────────────────────
_EX4_GIVEN = """\
import math
from PIL import Image
""" + _MOCK_DEF + """\

def generate_image(prompt, negative='', generate_fn=None,
                   width=512, height=512, steps=20,
                   guidance_scale=7.5, seed=42):
    if generate_fn is not None:
        return generate_fn(prompt, negative=negative, width=width,
                           height=height, steps=steps,
                           guidance_scale=guidance_scale, seed=seed)
    raise RuntimeError('diffusers not available in exercises')
"""

_EX4_STUB = """\
def generate_variations(base_prompt: str, n_variations: int,
                         generate_fn=None, **kwargs) -> list:
    \"\"\"Generate n_variations images of the same prompt with different seeds.

    Uses seeds: 42, 1042, 2042, ... (i * 1000 + 42)
    Returns:
        list of PIL.Image.Image, length == n_variations
    \"\"\"
    raise NotImplementedError


def create_image_grid(images: list, cols: int = 2):
    \"\"\"Arrange images in a rectangular grid.

    Args:
        images: list of PIL.Image.Image
        cols:   number of columns (capped to len(images))
    Returns:
        Single PIL.Image.Image
    Raises:
        ValueError if images is empty
    \"\"\"
    raise NotImplementedError
"""

_EX4_SOLUTION = """\
def generate_variations(base_prompt: str, n_variations: int,
                         generate_fn=None, **kwargs) -> list:
    images = []
    for i in range(n_variations):
        seed = i * 1000 + 42
        img = generate_image(base_prompt, generate_fn=generate_fn,
                             seed=seed, **kwargs)
        images.append(img)
    return images


def create_image_grid(images: list, cols: int = 2):
    if not images:
        raise ValueError('images list must not be empty')
    cols = max(1, min(cols, len(images)))
    rows = math.ceil(len(images) / cols)
    w, h = images[0].size
    grid = Image.new('RGB', (cols * w, rows * h), 'white')
    for i, img in enumerate(images):
        col = i % cols
        row = i // cols
        if img.size != (w, h):
            img = img.resize((w, h), Image.Resampling.LANCZOS)
        grid.paste(img, (col * w, row * h))
    return grid
"""

_EX4_CHECKS = """\
score, total = 0, 5
try:
    # generate_variations returns correct count
    imgs = generate_variations('a cat', 4, generate_fn=_mock_gen,
                               width=64, height=64)
    assert len(imgs) == 4, f"Expected 4, got {len(imgs)}"
    score += 1; print("\\u2705 generate_variations returns 4 images")

    # All are PIL Images of correct size
    assert all(isinstance(i, Image.Image) and i.size == (64, 64) for i in imgs)
    score += 1; print("\\u2705 all images are PIL Images with correct size")

    # Deterministic seeds: second call produces same first image
    imgs2 = generate_variations('a cat', 1, generate_fn=_mock_gen, width=64, height=64)
    assert list(imgs[0].getdata()) == list(imgs2[0].getdata())
    score += 1; print("\\u2705 generate_variations is deterministic")

    # create_image_grid: 4 images, 2 cols → 2x2 grid
    tiles = [Image.new('RGB', (32, 32), c) for c in [(255,0,0),(0,255,0),(0,0,255),(255,255,0)]]
    grid = create_image_grid(tiles, cols=2)
    assert grid.size == (64, 64), f"Expected (64,64), got {grid.size}"
    score += 1; print("\\u2705 2x2 grid has correct dimensions")

    # create_image_grid: empty list raises ValueError
    raised = False
    try:
        create_image_grid([])
    except ValueError:
        raised = True
    assert raised
    score += 1; print("\\u2705 create_image_grid raises ValueError for empty list")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX4 = nb([
    md("# Day 070 — Exercise 4: Variations and Grid\n\n"
       "**What you'll build:** `generate_variations` (same prompt, N different seeds) and "
       "`create_image_grid` (stitch images into a rectangular grid).\n\n"
       "**Why it matters:** These two functions form the exploration loop in every image "
       "generation workflow: generate N → view grid → pick best → refine prompt."),
    code(_EX4_GIVEN),
    md("## Task\n\n"
       "**`generate_variations(base_prompt, n_variations, generate_fn=None, **kwargs)`:**\n"
       "- `for i in range(n_variations): seed = i * 1000 + 42`\n"
       "- Call `generate_image(base_prompt, generate_fn=generate_fn, seed=seed, **kwargs)`\n"
       "- Return the list of images\n\n"
       "**`create_image_grid(images, cols=2)`:**\n"
       "- Raise `ValueError` if `images` is empty\n"
       "- `cols = max(1, min(cols, len(images)))`\n"
       "- `rows = math.ceil(len(images) / cols)`\n"
       "- `w, h = images[0].size`; create `Image.new('RGB', (cols*w, rows*h), 'white')`\n"
       "- Paste each image at `(col*w, row*h)` where `col = i % cols`, `row = i // cols`"),
    md("## Your Implementation"),
    code(_EX4_STUB),
    code(_EX4_SOLUTION),
    md("## Automated checks"),
    code(_EX4_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX4_SOLUTION + "```\n\n"
       "**Why `i * 1000 + 42` for seeds?** Seeds 0, 1, 2 are often visually "
       "similar because the initial noise tensors are correlated. Seeds spaced "
       "1000 apart are reliably distinct, giving meaningfully different "
       "compositions for each variation.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_04.ipynb", EX4)

# ── EXERCISE 5 — ImageGenerator class ────────────────────────────────────────
_EX5_GIVEN = _HELPER_SRC + "\n" + _MOCK_DEF

_EX5_STUB = """\
class ImageGenerator:
    \"\"\"Generate images from text prompts using a diffusion model.

    Inject generate_fn for testing without GPU or diffusers installed::

        mock = lambda p, **kw: Image.new('RGB', (kw.get('width', 512), kw.get('height', 512)), 'steelblue')
        gen = ImageGenerator(generate_fn=mock)
    \"\"\"

    def __init__(self, model_id: str = 'runwayml/stable-diffusion-v1-5',
                 generate_fn=None) -> None:
        raise NotImplementedError

    def generate(self, prompt: str, negative: str = '',
                 width: int = 512, height: int = 512,
                 steps: int = 20, guidance_scale: float = 7.5,
                 seed: int = 42):
        \"\"\"Generate a single image from a prompt. Returns PIL.Image.Image.\"\"\"
        raise NotImplementedError

    def batch(self, prompts: list, **kwargs) -> list:
        \"\"\"Generate one image per prompt. Returns list[Image.Image].\"\"\"
        raise NotImplementedError

    def grid(self, prompts: list, cols: int = 2, **kwargs):
        \"\"\"Generate images for all prompts and stitch into a grid.\"\"\"
        raise NotImplementedError
"""

_EX5_SOLUTION = """\
class ImageGenerator:
    def __init__(self, model_id='runwayml/stable-diffusion-v1-5',
                 generate_fn=None) -> None:
        self._model_id   = model_id
        self._generate_fn = generate_fn

    def generate(self, prompt, negative='', width=512, height=512,
                 steps=20, guidance_scale=7.5, seed=42):
        return generate_image(
            prompt, negative=negative,
            generate_fn=self._generate_fn,
            width=width, height=height,
            steps=steps, guidance_scale=guidance_scale, seed=seed,
        )

    def batch(self, prompts, **kwargs):
        return [self.generate(p, **kwargs) for p in prompts]

    def grid(self, prompts, cols=2, **kwargs):
        return create_image_grid(self.batch(prompts, **kwargs), cols=cols)
"""

_EX5_CHECKS = """\
score, total = 0, 5
try:
    gen = ImageGenerator(generate_fn=_mock_gen)

    # generate returns PIL Image of correct size
    img = gen.generate('a sunset', width=128, height=64)
    assert isinstance(img, Image.Image) and img.size == (128, 64)
    score += 1; print("\\u2705 generate returns PIL Image of correct size")

    # batch returns list of correct length
    prompts = ['a cat', 'a dog', 'a bird']
    imgs = gen.batch(prompts, width=32, height=32)
    assert len(imgs) == 3 and all(isinstance(i, Image.Image) for i in imgs)
    score += 1; print("\\u2705 batch returns list of 3 PIL Images")

    # grid returns stitched image of correct dimensions
    grid = gen.grid(prompts, cols=3, width=32, height=32)
    assert grid.size == (96, 32), f"Expected (96,32), got {grid.size}"
    score += 1; print("\\u2705 grid (3 prompts, 3 cols) returns (96,32) image")

    # 2-col grid: 3 prompts → 2 rows
    grid2 = gen.grid(prompts, cols=2, width=32, height=32)
    assert grid2.size == (64, 64), f"Expected (64,64), got {grid2.size}"
    score += 1; print("\\u2705 grid (3 prompts, 2 cols) returns (64,64) image")

    # generate_fn is stored and forwarded
    captured = {}
    def _cap(prompt, **kw):
        captured['guidance_scale'] = kw.get('guidance_scale')
        return Image.new('RGB', (kw.get('width', 64), kw.get('height', 64)), 'red')
    gen2 = ImageGenerator(generate_fn=_cap)
    gen2.generate('test', guidance_scale=11.0)
    assert abs(captured.get('guidance_scale', 0) - 11.0) < 0.001
    score += 1; print("\\u2705 generate_fn and params forwarded correctly")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX5 = nb([
    md("# Day 070 — Exercise 5: ImageGenerator Class\n\n"
       "**What you'll build:** `ImageGenerator` — a class that binds `generate_fn` at "
       "construction time and exposes `generate`, `batch`, and `grid` methods.\n\n"
       "**Why it matters:** A class makes the generation pipeline reusable across "
       "many calls. Bind the mock at construction time for tests, swap in a real "
       "pipeline for production — no changes to callers."),
    code(_EX5_GIVEN),
    md("## Task\n\nImplement `ImageGenerator`:\n\n"
       "**`__init__(self, model_id, generate_fn=None)`:** store both as instance attributes.\n\n"
       "**`generate(self, prompt, negative='', width=512, height=512, steps=20, guidance_scale=7.5, seed=42)`:**\n"
       "Delegate to `generate_image(prompt, ..., generate_fn=self._generate_fn, ...)`. Return the result.\n\n"
       "**`batch(self, prompts, **kwargs)`:** "
       "`return [self.generate(p, **kwargs) for p in prompts]`\n\n"
       "**`grid(self, prompts, cols=2, **kwargs)`:** "
       "`return create_image_grid(self.batch(prompts, **kwargs), cols=cols)`"),
    md("## Your Implementation"),
    code(_EX5_STUB),
    code(_EX5_SOLUTION),
    md("## Automated checks"),
    code(_EX5_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX5_SOLUTION + "```\n\n"
       "**Why delegate `generate` to the module-level `generate_image`?** "
       "The class should not duplicate the conditional logic for real vs mock. "
       "By passing `self._generate_fn` to the module function, all the "
       "dispatch logic lives in one place. The class is a thin wrapper "
       "that holds state (the mock) and provides a convenient interface.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_05.ipynb", EX5)

# ── PROJECT NOTEBOOK ──────────────────────────────────────────────────────────
PROJECT = nb([
    md("# Day 070 — Project: Image Generator\n\n"
       "## What You're Building\n\n"
       "`image_generator.py` — an `ImageGenerator` class for text-to-image generation.\n\n"
       "**Deliverable:** A class and utility functions for building prompts, applying style "
       "templates, generating images (with mock injection for offline testing), and "
       "stitching variation batches into comparison grids.\n\n"
       "## Setup (for real generation)\n\n"
       "```bash\n"
       "pip install diffusers transformers accelerate torch\n"
       "```\n\n"
       "## Design\n\n"
       "```\n"
       "build_prompt(subject, style, quality_tags, negative_tags) -> dict\n"
       "apply_style_template(base_prompt, template_name) -> dict\n"
       "generate_image(prompt, negative, generate_fn, ...) -> Image.Image\n"
       "generate_variations(base_prompt, n, generate_fn) -> list[Image.Image]\n"
       "create_image_grid(images, cols) -> Image.Image\n\n"
       "ImageGenerator(model_id, generate_fn)\n"
       "  .generate(prompt, ...) -> Image.Image\n"
       "  .batch(prompts, ...) -> list[Image.Image]\n"
       "  .grid(prompts, cols, ...) -> Image.Image\n"
       "```\n\n"
       "## Usage (offline testing)\n\n"
       "```python\n"
       "from PIL import Image\n"
       "from image_generator import ImageGenerator, build_prompt, apply_style_template\n\n"
       "mock = lambda p, **kw: Image.new('RGB', (kw.get('width', 512), kw.get('height', 512)), 'steelblue')\n"
       "gen = ImageGenerator(generate_fn=mock)\n"
       "p = apply_style_template('a mountain lake at dawn', 'cinematic')\n"
       "img = gen.generate(p['positive'], negative=p['negative'])\n"
       "print(img.size)\n"
       "```"),
    code("# Your implementation here\n"
         "# Build ImageGenerator and write it to image_generator.py\n"),
])
save(OUT / "project" / "project.ipynb", PROJECT)

# ── SOLUTION NOTEBOOK ─────────────────────────────────────────────────────────
_SOL_CELL1 = (
    f"_GENERATOR_SRC = {repr(_GENERATOR_SRC)}\n"
    "from pathlib import Path\n"
    "Path('image_generator.py').write_text(_GENERATOR_SRC, encoding='utf-8')\n"
    "print('image_generator.py written.')"
)

_SOL_CELL2 = """\
import math
from PIL import Image
from image_generator import (
    STYLE_TEMPLATES, build_prompt, apply_style_template,
    generate_image, generate_variations, create_image_grid,
    ImageGenerator,
)

_mock = lambda p, **kw: Image.new('RGB', (kw.get('width', 512), kw.get('height', 512)), 'steelblue')
gen = ImageGenerator(generate_fn=_mock)

# 1. build_prompt
p = build_prompt('a cat', style='oil painting',
                 quality_tags=['masterpiece'], negative_tags=['blurry'])
assert p['positive'] == 'a cat, oil painting, masterpiece'
assert p['negative'] == 'blurry'
print("\\u2705 build_prompt correct")

# 2. apply_style_template
r = apply_style_template('a forest', 'cinematic')
assert r['positive'].startswith('a forest, cinematic')
assert r['negative'] == STYLE_TEMPLATES['cinematic']['negative']
print("\\u2705 apply_style_template correct")

# 3. generate_image
img = generate_image('a sunset', generate_fn=_mock, width=256, height=128)
assert img.size == (256, 128) and img.mode == 'RGB'
print("\\u2705 generate_image returns correct PIL Image")

# 4. generate_variations
imgs = generate_variations('a dog', 3, generate_fn=_mock, width=64, height=64)
assert len(imgs) == 3 and all(isinstance(i, Image.Image) for i in imgs)
print("\\u2705 generate_variations returns 3 images")

# 5. create_image_grid: 4 images, 2 cols → (128, 128)
tiles = [Image.new('RGB', (64, 64), 'steelblue') for _ in range(4)]
grid = create_image_grid(tiles, cols=2)
assert grid.size == (128, 128), f"Got {grid.size}"
print("\\u2705 create_image_grid 2x2 = (128,128)")

# 6. ImageGenerator.generate
img2 = gen.generate('a cloud', width=128, height=64)
assert img2.size == (128, 64)
print("\\u2705 ImageGenerator.generate correct")

# 7. ImageGenerator.batch
prompts = ['a cat', 'a dog']
batch = gen.batch(prompts, width=32, height=32)
assert len(batch) == 2 and batch[0].size == (32, 32)
print("\\u2705 ImageGenerator.batch correct")

# 8. ImageGenerator.grid
g = gen.grid(prompts, cols=2, width=32, height=32)
assert g.size == (64, 32), f"Got {g.size}"
print("\\u2705 ImageGenerator.grid correct")

print("\\nImage Generator complete!")
"""

SOLUTION = nb([
    md("# Day 070 — Solution: Image Generator"),
    code(_SOL_CELL1),
    code(_SOL_CELL2),
])
save(OUT / "project" / "solution" / "solution.ipynb", SOLUTION)
(OUT / "project" / "solution" / "image_generator.py").write_text(_GENERATOR_SRC)

print(f"Day {DAY} notebooks written to {OUT}")
print("  lessons/    day_070_lesson_01.yaml – lesson_05.yaml")
print("  exercises/  exercise_01 – exercise_05")
print("  project/    project.ipynb")
print("  project/solution/  solution.ipynb + image_generator.py")
