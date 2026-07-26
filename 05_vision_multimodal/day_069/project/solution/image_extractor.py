"""image_extractor.py — Day 069: Multimodal Extraction.

Extracts structured data from images by combining a vision LLM (Ollama llava)
with a Pydantic v2 schema. Returns a validated Python object.

Setup:
    ollama pull llava    # vision model

Usage:
    from image_extractor import ImageExtractor
    from pydantic import BaseModel
    from PIL import Image

    class ProductInfo(BaseModel):
        name: str
        price: float
        category: str = ""

    extractor = ImageExtractor(schema_cls=ProductInfo)
    img = Image.open("product.jpg")
    result = extractor.extract(img)
    print(result.name, result.price)

Testing without Ollama:
    mock = lambda b64, prompt: '{"name": "Widget", "price": 9.99}'
    extractor = ImageExtractor(schema_cls=ProductInfo, describe_fn=mock)
"""
import io
import re
import json
import base64
from typing import Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def image_to_base64(img, format: str = "PNG") -> str:
    """Encode a PIL Image as a base64 string."""
    buf = io.BytesIO()
    out = img
    if format.upper() in ("JPEG", "JPG") and img.mode in ("RGBA", "P"):
        out = img.convert("RGB")
    out.save(buf, format=format)
    return base64.b64encode(buf.getvalue()).decode()


def build_extraction_prompt(schema_cls: Type[BaseModel]) -> str:
    """Build a vision LLM prompt for structured JSON extraction.

    Embeds the Pydantic model's JSON schema so the model knows exactly
    which fields to return and their types.
    """
    schema_json = json.dumps(schema_cls.model_json_schema(), indent=2)
    return (
        "Extract structured data from this image and return ONLY valid JSON "
        "matching this schema exactly. Do not include any explanation, "
        "markdown, or code blocks — just the raw JSON object.\n\n"
        f"Schema:\n{schema_json}\n\n"
        "Return ONLY the JSON object, nothing else."
    )


def strip_json_from_response(response: str) -> str:
    """Extract a JSON object from an LLM response string.

    Handles:
    - Plain JSON: {"key": "value"}
    - Markdown code block: ```json\n{...}\n```
    - JSON preceded by explanation text

    Raises:
        ValueError if no JSON object found in the response
    """
    # Try markdown code block first (```json ... ``` or ``` ... ```)
    block = re.search(r"```(?:json)?\s*([\s\S]*?)```", response)
    if block:
        return block.group(1).strip()

    # Fall back to first {...} span in the string
    obj = re.search(r"\{[\s\S]*\}", response)
    if obj:
        return obj.group(0).strip()

    raise ValueError(
        f"No JSON object found in LLM response: {response[:200]!r}"
    )


def extract_from_image(img_b64: str, schema_cls: Type[T],
                       describe_fn=None) -> dict:
    """Send an image to a vision LLM and parse its response as JSON.

    Args:
        img_b64:    base64-encoded image string
        schema_cls: Pydantic model class defining the target schema
        describe_fn: callable(img_b64, prompt) -> str for testing
    Returns:
        dict of extracted fields (not yet validated against schema)
    Raises:
        ValueError if the response contains no parseable JSON
        json.JSONDecodeError if the extracted JSON is malformed
    """
    prompt = build_extraction_prompt(schema_cls)
    if describe_fn is not None:
        response = describe_fn(img_b64, prompt)
    else:
        import ollama
        resp = ollama.chat(
            model="llava",
            messages=[{
                "role":    "user",
                "content": prompt,
                "images":  [img_b64],
            }],
        )
        response = resp["message"]["content"]
    raw = strip_json_from_response(response)
    return json.loads(raw)


def safe_extract(img_b64: str, schema_cls: Type[T],
                 describe_fn=None, retries: int = 2) -> dict | None:
    """Extract JSON from an image, retrying on parse failures.

    Args:
        img_b64:    base64-encoded image string
        schema_cls: Pydantic model class
        describe_fn: callable for testing
        retries:    number of extra attempts on failure (total = retries + 1)
    Returns:
        Extracted dict, or None if all attempts fail
    """
    for attempt in range(retries + 1):
        try:
            return extract_from_image(img_b64, schema_cls,
                                      describe_fn=describe_fn)
        except (ValueError, json.JSONDecodeError):
            if attempt == retries:
                return None
    return None


def validate_extraction(data: dict, schema_cls: Type[T]) -> tuple:
    """Validate an extracted dict against a Pydantic schema.

    Args:
        data:       dict from extract_from_image / safe_extract
        schema_cls: Pydantic model class
    Returns:
        (True, validated_model) on success
        (False, error_message_str) on validation failure
    """
    try:
        model = schema_cls.model_validate(data)
        return (True, model)
    except Exception as exc:
        return (False, str(exc))


class ImageExtractor:
    """Extract structured Pydantic objects from images using a vision LLM.

    Pass describe_fn for testing without Ollama::

        mock = lambda b64, prompt: '{"name": "Widget", "price": 9.99}'
        extractor = ImageExtractor(schema_cls=ProductInfo, describe_fn=mock)
    """

    def __init__(self, schema_cls: Type[T],
                 model: str = "llava",
                 describe_fn=None) -> None:
        self.schema_cls  = schema_cls
        self.model       = model
        self._describe_fn = describe_fn

    def extract(self, img, retries: int = 2) -> T:
        """Extract and validate structured data from a PIL Image.

        Encodes the image, calls the vision LLM, strips JSON from the
        response, parses, and validates against schema_cls.

        Args:
            img:     PIL Image
            retries: retry attempts on parse failure
        Returns:
            Validated Pydantic model instance
        Raises:
            ValueError if extraction fails after all retries
            pydantic.ValidationError if the extracted data does not
            match the schema after successful JSON parsing
        """
        img_b64 = image_to_base64(img)
        data = safe_extract(img_b64, self.schema_cls,
                            describe_fn=self._describe_fn,
                            retries=retries)
        if data is None:
            raise ValueError(
                f"Failed to extract valid JSON after {retries + 1} attempts"
            )
        return self.schema_cls.model_validate(data)
