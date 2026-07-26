"""vision_analyzer.py — Day 067: Vision LLM image analyzer.

Wraps Ollama llava for image description, classification,
text extraction, and multi-task analysis.

Setup:
    ollama pull llava    # or: ollama pull llama3.2-vision

Usage:
    from vision_analyzer import VisionAnalyzer
    from PIL import Image

    va = VisionAnalyzer(model="llava")
    img = Image.open("photo.jpg")
    print(va.describe(img))
    print(va.extract_text(img))
    print(va.classify(img, ["indoor", "outdoor", "food"]))
    print(va.analyze(img, tasks=["describe", "objects"]))

Testing without Ollama:
    mock = lambda b64, prompt: "A red square image."
    va = VisionAnalyzer(describe_fn=mock)
"""
import io
import base64
from PIL import Image

_PROMPTS = {
    "describe": "Describe this image in 2-3 sentences.",
    "text":     (
        "Extract all visible text from this image exactly as it appears. "
        "If there is no text, reply with an empty string."
    ),
    "colors":   "List the 3 dominant colors visible in this image.",
    "objects":  "List the main objects visible in this image.",
}


def image_to_base64(img: Image.Image, format: str = "PNG") -> str:
    """Encode a PIL Image as a base64 string (no data URI prefix)."""
    buf = io.BytesIO()
    out = img
    if format.upper() in ("JPEG", "JPG") and img.mode in ("RGBA", "P"):
        out = img.convert("RGB")
    out.save(buf, format=format)
    return base64.b64encode(buf.getvalue()).decode()


class VisionAnalyzer:
    """Chainable vision LLM analyzer backed by Ollama.

    Pass describe_fn for testing without a running Ollama server::

        mock = lambda b64, prompt: "A test image."
        va = VisionAnalyzer(describe_fn=mock)
    """

    def __init__(self, model: str = "llava",
                 describe_fn=None) -> None:
        self.model = model
        self._describe_fn = describe_fn

    def _call(self, img_b64: str, prompt: str) -> str:
        if self._describe_fn is not None:
            return self._describe_fn(img_b64, prompt)
        import ollama
        resp = ollama.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt, "images": [img_b64]}],
        )
        return resp["message"]["content"]

    def describe(self, img: Image.Image,
                 prompt: str = "Describe this image in 2-3 sentences.") -> str:
        """Return a text description of the image."""
        return self._call(image_to_base64(img), prompt)

    def extract_text(self, img: Image.Image) -> str:
        """Extract visible text from the image (OCR via vision LLM)."""
        return self._call(image_to_base64(img), _PROMPTS["text"])

    def classify(self, img: Image.Image, labels: list) -> str:
        """Zero-shot classify the image into one of the given labels."""
        label_list = ", ".join(f'"{l}"' for l in labels)
        prompt = (
            f"Classify this image into exactly one of these categories: "
            f"{label_list}. Reply with only the category name."
        )
        response = self._call(image_to_base64(img), prompt)
        resp_lower = response.lower()
        for label in labels:
            if label.lower() in resp_lower:
                return label
        return labels[0]

    def analyze(self, img: Image.Image, tasks: list = None) -> dict:
        """Run multiple analyses on a single image.

        tasks: list of keys — 'describe', 'text', 'colors', 'objects'.
        Returns dict mapping task name to result string.
        """
        if tasks is None:
            tasks = ["describe"]
        img_b64 = image_to_base64(img)
        results = {}
        for task in tasks:
            if task not in _PROMPTS:
                raise ValueError(
                    f"Unknown task: {task!r}. Available: {list(_PROMPTS)}"
                )
            results[task] = self._call(img_b64, _PROMPTS[task])
        return results
