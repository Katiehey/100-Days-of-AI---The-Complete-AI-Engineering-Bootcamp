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
