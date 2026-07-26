#!/usr/bin/env python3
"""gen_day069.py — generate Day 069: Multimodal Extraction."""
from pathlib import Path
import json

ROOT    = Path(__file__).parent.parent
DAY     = "069"
SECTION = "05_vision_multimodal"
OUT     = ROOT / SECTION / f"day_{DAY}"

(OUT / "exercises").mkdir(parents=True, exist_ok=True)
(OUT / "lessons").mkdir(parents=True, exist_ok=True)
(OUT / "project" / "solution").mkdir(parents=True, exist_ok=True)

# ── deliverable: image_extractor.py ──────────────────────────────────────────
_EXTRACTOR_SRC = '''\
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
    mock = lambda b64, prompt: \'{"name": "Widget", "price": 9.99}\'
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
        "markdown, or code blocks — just the raw JSON object.\\n\\n"
        f"Schema:\\n{schema_json}\\n\\n"
        "Return ONLY the JSON object, nothing else."
    )


def strip_json_from_response(response: str) -> str:
    """Extract a JSON object from an LLM response string.

    Handles:
    - Plain JSON: {"key": "value"}
    - Markdown code block: ```json\\n{...}\\n```
    - JSON preceded by explanation text

    Raises:
        ValueError if no JSON object found in the response
    """
    # Try markdown code block first (```json ... ``` or ``` ... ```)
    block = re.search(r"```(?:json)?\\s*([\\s\\S]*?)```", response)
    if block:
        return block.group(1).strip()

    # Fall back to first {...} span in the string
    obj = re.search(r"\\{[\\s\\S]*\\}", response)
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

        mock = lambda b64, prompt: \'{"name": "Widget", "price": 9.99}\'
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
day: "069"
lesson: 1
title: "Schema-Guided Vision Extraction"
slides:
  - type: title
    heading: "Multimodal Extraction"
    subheading: "Day 69 — Vision LLM + Pydantic = structured data from images"
    narration: >
      Days 67 and 68 gave you two tools for reading images: a vision LLM that
      returns free-form text, and OCR that returns a raw character stream.
      Today you combine them into something more powerful: schema-guided
      extraction. You describe the data you want as a Pydantic model, embed
      the schema in the prompt, and the vision LLM returns a JSON object you
      can validate and use directly in your application code.

  - type: concept
    label: "Schema-guided extraction"
    heading: "What is Schema-Guided Extraction?"
    body: >
      You give the LLM both an image and a precise schema. The LLM acts as
      a structured reading machine — extracting only the fields you asked for
      in the exact format you specified.
    bullets:
      - "Input: image + Pydantic model class"
      - "Output: validated Python object with correct types"
      - "Zero-shot: no training data, no fine-tuning"
      - "Fields: str, float, int, list, nested models — anything Pydantic supports"
    narration: >
      Schema-guided extraction is the bridge between vision LLMs and typed
      application code. On Day 4 you used Pydantic to validate structured
      output from a text LLM. Today the source is an image — a receipt, an
      invoice, a product label, a screenshot — and the extraction engine is
      a vision model. The schema constrains what the model returns, and
      Pydantic validation ensures the types are correct before your code
      uses the data.

  - type: how_it_works
    label: "The pipeline"
    heading: "The Extraction Pipeline"
    body: >
      Four steps: encode the image, build a schema-aware prompt, call the
      vision LLM, parse and validate the JSON response.
    bullets:
      - "1. Encode: PIL Image → base64 (image_to_base64 from Day 67)"
      - "2. Prompt: embed model_json_schema() in the instruction"
      - "3. Call: vision LLM returns a JSON string (ideally)"
      - "4. Parse + validate: json.loads → model_validate → typed object"
    narration: >
      Each step has a failure mode. Encoding fails for corrupted images.
      The LLM sometimes returns JSON wrapped in markdown code blocks or
      preceded by explanation text. json.loads fails on malformed JSON.
      model_validate fails when the LLM omits required fields or returns
      the wrong type. In lesson 4 you will add a retry layer that handles
      these failures systematically.

  - type: concept
    label: "Why embed the schema?"
    heading: "Why Embed model_json_schema in the Prompt?"
    body: >
      JSON Schema is the LLM-friendly format for describing structured data.
      Pydantic generates it automatically — you never write it by hand.
    bullets:
      - "model_json_schema() returns a dict describing all fields + types"
      - "json.dumps(schema, indent=2) makes it readable in the prompt"
      - "The LLM has seen thousands of JSON Schema examples in training"
      - "It knows: 'type: number' means a float, 'type: string' means a str"
    narration: >
      JSON Schema is a standard format for describing the structure of a JSON
      document. Pydantic v2 generates it from your model class automatically
      — call model_json_schema() to get the dict, then json.dumps to convert
      it to a string you can embed in the prompt. Vision LLMs have seen large
      quantities of JSON Schema in their training data, so the format is
      natural to them. The combination of a clear instruction and an explicit
      schema dramatically increases the probability of a valid JSON response.

  - type: code
    label: "Schema in prompt"
    heading: "Embedding a Pydantic Schema in the Prompt"
    code: |
      import json
      from pydantic import BaseModel

      class Receipt(BaseModel):
          merchant: str
          total:    float
          date:     str = ""

      schema_dict = Receipt.model_json_schema()
      schema_json = json.dumps(schema_dict, indent=2)

      prompt = (
          "Extract structured data from this image and return ONLY valid JSON "
          "matching this schema exactly:\\n\\n"
          f"Schema:\\n{schema_json}\\n\\n"
          "Return ONLY the JSON object, nothing else."
      )
      print(prompt[:300])
    narration: >
      The prompt has three parts: the extraction instruction, the schema
      block, and the output constraint. The output constraint — "Return ONLY
      the JSON object, nothing else" — is the most important. Without it,
      models often prefix their response with "Here is the extracted data:"
      or wrap it in a markdown code block. Both make json.loads fail. The
      constraint reduces that noise, and the strip_json_from_response function
      in lesson 2 handles the cases that slip through.

  - type: exercise
    heading: "Exercise 1: Build Extraction Prompt"
    prompt: >
      Implement build_extraction_prompt(schema_cls) -> str.
      Call schema_cls.model_json_schema() to get the schema dict.
      Embed it in a prompt that instructs the model to return ONLY valid JSON.
      The prompt must contain the word 'JSON' and all field names from the schema.
    hint: >
      json.dumps(schema_cls.model_json_schema(), indent=2) gives the schema as
      a string. Build a prompt containing that string plus a clear instruction
      to return only the JSON object.
    narration: >
      The extraction prompt is the single most important input to the pipeline.
      A well-crafted prompt reliably produces parseable JSON. A vague prompt
      produces explanation text around the JSON, requiring more post-processing.

  - type: summary
    heading: "Lesson 1 Summary"
    bullets:
      - "Schema-guided extraction: image + Pydantic model → validated typed object"
      - "model_json_schema() → JSON Schema dict; json.dumps → prompt-ready string"
      - "Four steps: encode → prompt → call → parse+validate"
      - "Output constraint: 'Return ONLY the JSON object' reduces noise"
      - "Failures: markdown wrapping, extra text, wrong types, missing fields"
    narration: >
      The pipeline is clear. Next: handling the most common LLM failure — wrapping
      JSON in markdown code blocks or adding explanation text before the JSON.
"""

_LESSON_02 = """\
day: "069"
lesson: 2
title: "Parsing LLM JSON Responses"
slides:
  - type: title
    heading: "Parsing LLM JSON Responses"
    subheading: "Stripping markdown, finding JSON, handling noise"
    narration: >
      Even with the best prompt, vision LLMs sometimes return JSON wrapped
      in markdown code blocks or preceded by explanation text. This lesson
      builds the strip_json_from_response function that handles all common
      response formats and delivers the clean JSON string that json.loads needs.

  - type: concept
    label: "LLM response noise"
    heading: "Common LLM Response Patterns"
    body: >
      Three formats appear in practice. Your parser needs to handle all three.
    bullets:
      - "Plain JSON: bare JSON object — ideal, but models often add noise"
      - "Markdown block: object wrapped in code fences — very common"
      - "Prefixed JSON: natural-language preamble before the object — also common"
    narration: >
      Instruction-tuned models like Llama tend to wrap code in markdown fences
      because they were trained to do that in chat contexts. A prompt saying
      "return ONLY the JSON" reduces this, but does not eliminate it. Chat
      models may add a natural-language preamble. The strip function uses
      regex to handle both cases: first try to match a markdown code block,
      then fall back to finding any bare JSON object in the string.

  - type: code
    label: "Stripping JSON"
    heading: "strip_json_from_response Implementation"
    code: |
      import re, json

      def strip_json_from_response(response: str) -> str:
          # 1. Try markdown code block (```json ... ``` or ``` ... ```)
          block = re.search(r'```(?:json)?\\s*([\\s\\S]*?)```', response)
          if block:
              return block.group(1).strip()

          # 2. Fall back: first {...} span in the string
          obj = re.search(r'\\{[\\s\\S]*\\}', response)
          if obj:
              return obj.group(0).strip()

          raise ValueError(
              f"No JSON object found: {response[:200]!r}"
          )

      # Test with each format
      print(strip_json_from_response('{"a": 1}'))             # plain
      print(strip_json_from_response('```json\\n{"a": 1}\\n```'))  # code block
      print(strip_json_from_response('Here: {"a": 1}'))       # prefixed
    narration: >
      The regex `(?:json)?` makes the language tag optional — code blocks
      are written both as ```json and as ```. The `[\\s\\S]*?` inside the block
      is a non-greedy match for any character including newlines — essential
      because the JSON may span multiple lines. The fallback `{[\\s\\S]*}` is
      greedy and will match the outermost braces in the string, which is what
      you want for nested objects. If neither pattern matches, raise a
      ValueError so the caller can retry.

  - type: how_it_works
    label: "Parse then validate"
    heading: "Strip → json.loads → model_validate"
    body: >
      Three steps convert the raw LLM response into a validated Pydantic object.
    narration: >
      After stripping, json.loads converts the string to a Python dict —
      this raises JSONDecodeError if the JSON is syntactically invalid. Then
      model_validate converts the dict to a Pydantic model instance —
      this raises ValidationError if the data does not match the schema
      (wrong type, missing required field, constraint violation). Separating
      these two steps makes it easy to distinguish syntax errors (retry the
      LLM call) from semantic errors (the model extracted the wrong data).

  - type: code
    label: "Full parse step"
    heading: "Full Parse Step: strip → loads → validate"
    code: |
      import json
      from pydantic import BaseModel, ValidationError

      class Receipt(BaseModel):
          merchant: str
          total:    float

      def parse_response(response: str, schema_cls):
          raw  = strip_json_from_response(response)   # handles markdown/noise
          data = json.loads(raw)                       # raises JSONDecodeError
          return schema_cls.model_validate(data)       # raises ValidationError

      # Happy path
      r = parse_response('{"merchant": "ACME", "total": 42.0}', Receipt)
      print(r.merchant, r.total)   # ACME 42.0

      # Type coercion: Pydantic converts "42.0" string → float
      r2 = parse_response('{"merchant": "ACME", "total": "42.0"}', Receipt)
      print(r2.total, type(r2.total))   # 42.0 <class 'float'>
    narration: >
      Pydantic v2 performs type coercion by default — the string "42.0" is
      automatically converted to the float 42.0 when the field is declared
      as `float`. This is very useful for vision LLM output because models
      sometimes return numeric values as quoted strings. The coercion handles
      this silently. A missing required field, however, raises a ValidationError
      that you need to handle — either by retrying the LLM or by falling back
      to a default.

  - type: exercise
    heading: "Exercise 2: Strip JSON from LLM Response"
    prompt: >
      Implement strip_json_from_response(response: str) -> str.
      First try to match a markdown code block (```json...``` or ```...```).
      If found, return the content inside the block stripped of whitespace.
      Otherwise, use a regex to find the first {...} object in the string.
      If nothing found, raise ValueError. Return the stripped JSON string only.
    hint: >
      re.search(r'```(?:json)?\\s*([\\s\\S]*?)```', response) for code blocks.
      re.search(r'\\{[\\s\\S]*\\}', response) for bare JSON objects.
      Raise ValueError if neither matches.
    narration: >
      This function is the noise filter between the raw LLM output and your
      JSON parser. Getting it right means all downstream functions can assume
      they receive clean JSON strings.

  - type: summary
    heading: "Lesson 2 Summary"
    bullets:
      - "Three LLM output patterns: plain JSON, markdown block, prefixed JSON"
      - "```(?:json)?\\\\s*([\\\\s\\\\S]*?)``` — matches code blocks with optional 'json' tag"
      - "\\\\{[\\\\s\\\\S]*\\\\} — matches outermost braces (greedy, handles nested)"
      - "Try code block first; fall back to bare object; raise ValueError if none"
      - "strip → json.loads → model_validate: three distinct failure points"
    narration: >
      The JSON stripping function is settled. Next: assembling the full
      extraction function that takes image bytes and a schema class and
      returns the parsed dict.
"""

_LESSON_03 = """\
day: "069"
lesson: 3
title: "The Extraction Function"
slides:
  - type: title
    heading: "The Extraction Function"
    subheading: "describe_fn injection + JSON pipeline end to end"
    narration: >
      Lessons 1 and 2 built the two components: the schema-aware prompt and
      the JSON stripper. This lesson wires them into extract_from_image —
      the core function that takes an image base64 string and a Pydantic
      class and returns a dict. Like describe_image on Day 67, it accepts
      a describe_fn mock for headless testing.

  - type: how_it_works
    label: "extract_from_image"
    heading: "extract_from_image: Full Pipeline"
    body: >
      Three operations: build prompt → call LLM → strip + parse JSON.
    narration: >
      The function accepts an already-encoded base64 string, not a PIL Image,
      because encoding is the caller's responsibility — following the encode-once
      pattern from Day 67. The describe_fn parameter follows the same contract
      as in Days 67 and 68: a callable(img_b64, prompt) -> str that returns the
      raw LLM response string. When describe_fn is None, the function calls
      Ollama llava directly.

  - type: code
    label: "extract_from_image"
    heading: "extract_from_image Implementation"
    code: |
      import json

      def extract_from_image(img_b64, schema_cls, describe_fn=None) -> dict:
          prompt = build_extraction_prompt(schema_cls)

          if describe_fn is not None:
              response = describe_fn(img_b64, prompt)
          else:
              import ollama
              resp = ollama.chat(
                  model='llava',
                  messages=[{
                      'role':    'user',
                      'content': prompt,
                      'images':  [img_b64],
                  }],
              )
              response = resp['message']['content']

          raw  = strip_json_from_response(response)
          return json.loads(raw)
    narration: >
      The function does not validate against the schema — it returns a raw dict.
      This is a deliberate choice: you may want to inspect the raw dict before
      validation, or handle validation errors differently from parse errors.
      The caller decides what to do with the dict — call model_validate if they
      want a typed object, or pass it to safe_extract's retry wrapper.

  - type: code
    label: "Testing"
    heading: "Testing with a Mock describe_fn"
    code: |
      from pydantic import BaseModel

      class ProductInfo(BaseModel):
          name:     str
          price:    float
          category: str = ""

      # Mock returns valid JSON — no Ollama needed
      mock = lambda b64, prompt: '{"name": "Headphones", "price": 49.99}'

      result = extract_from_image("fake_b64==", ProductInfo, describe_fn=mock)
      print(result)          # {'name': 'Headphones', 'price': 49.99}
      print(type(result))    # <class 'dict'>

      # Now validate
      obj = ProductInfo.model_validate(result)
      print(obj.name, obj.price)   # Headphones 49.99
    narration: >
      Notice that the mock's return value is a JSON string — the same format
      the real LLM would return. The test exercises the full strip → loads
      pipeline, not just the business logic. If the mock returned a dict
      directly, the test would bypass the JSON parsing step and miss any bugs
      in strip_json_from_response or json.loads.

  - type: code
    label: "Error cases"
    heading: "Handling Parse Failures"
    code: |
      # JSON syntax error → JSONDecodeError
      bad_mock = lambda b64, p: '{"name": "Broken", "price": }'
      try:
          extract_from_image("b64==", ProductInfo, describe_fn=bad_mock)
      except json.JSONDecodeError as e:
          print(f"Syntax error: {e}")

      # No JSON at all → ValueError from strip_json_from_response
      no_json_mock = lambda b64, p: "I cannot see any structured data."
      try:
          extract_from_image("b64==", ProductInfo, describe_fn=no_json_mock)
      except ValueError as e:
          print(f"No JSON found: {e}")
    narration: >
      Two failure modes. JSONDecodeError means the model returned something
      that looks like JSON but has syntax errors — a missing comma, an unquoted
      key, a trailing comma. ValueError means the model did not return any JSON
      at all. Both are retryable — asking the model again with the same image
      often produces a valid response on the second or third attempt.

  - type: exercise
    heading: "Exercise 3: Extract from Image"
    prompt: >
      Implement extract_from_image(img_b64, schema_cls, describe_fn=None) -> dict.
      Build the extraction prompt using build_extraction_prompt. Call describe_fn
      if provided, otherwise call ollama.chat with model='llava'. Strip JSON from
      the response with strip_json_from_response. Return json.loads(raw). Do not
      validate against the schema — return a plain dict.
    hint: >
      Call build_extraction_prompt(schema_cls) → prompt. If describe_fn is not None:
      response = describe_fn(img_b64, prompt). Then raw = strip_json_from_response(response).
      Return json.loads(raw). The mock in checks returns a valid JSON string.
    narration: >
      extract_from_image is the core of the extraction pipeline. Every function
      in today's day builds on it — safe_extract adds retries, validate_extraction
      adds Pydantic validation, and extract_pipeline combines all three.

  - type: summary
    heading: "Lesson 3 Summary"
    bullets:
      - "extract_from_image: build prompt → call LLM → strip → json.loads → dict"
      - "Returns a raw dict, not a validated model — caller decides how to use it"
      - "Two failure types: JSONDecodeError (syntax) and ValueError (no JSON)"
      - "Mock returns a JSON string — tests the full parse pipeline"
      - "describe_fn=None injection: same pattern as Day 67 describe_image"
    narration: >
      The core extraction function is complete. Next: retry logic that calls
      extract_from_image multiple times when it fails, plus Pydantic validation
      to check that the extracted data matches the schema.
"""

_LESSON_04 = """\
day: "069"
lesson: 4
title: "Retry and Validation"
slides:
  - type: title
    heading: "Retry and Validation"
    subheading: "safe_extract, validate_extraction — making the pipeline robust"
    narration: >
      Real vision LLMs are non-deterministic. A prompt that fails once may
      succeed on the second attempt. And even when JSON parsing succeeds,
      the extracted data may not match your schema. This lesson adds the
      retry wrapper and validation function that make the pipeline production-ready.

  - type: concept
    label: "Why retry?"
    heading: "Why Non-Deterministic LLMs Need Retries"
    body: >
      Temperature > 0 means the model samples different tokens each run.
      A prompt that fails once (bad JSON) often succeeds the next time.
    bullets:
      - "Temperature > 0 → different output each call (stochastic sampling)"
      - "JSON parse failure on run 1 ≠ JSON parse failure on run 2"
      - "Retry is free: one extra API call costs pennies or nothing (Ollama)"
      - "Retry cap: 2-3 retries is enough; beyond that, the prompt is probably wrong"
    narration: >
      With Ollama running locally there is no marginal cost to retrying.
      With a paid API you pay per token, but 2-3 retries is still reasonable
      insurance against a single bad run. The retry count should be small —
      if the model consistently fails to produce valid JSON after 3 attempts,
      the problem is with your prompt or your schema, not with random sampling.
      Fix the prompt rather than increasing retries.

  - type: code
    label: "safe_extract"
    heading: "safe_extract: Retry Wrapper"
    code: |
      import json

      def safe_extract(img_b64, schema_cls, describe_fn=None,
                       retries=2) -> dict | None:
          for attempt in range(retries + 1):
              try:
                  return extract_from_image(
                      img_b64, schema_cls, describe_fn=describe_fn
                  )
              except (ValueError, json.JSONDecodeError):
                  if attempt == retries:
                      return None   # exhausted all attempts
          return None

      # With always-failing mock: returns None after 3 attempts
      def _bad(b64, p): return "I cannot determine the values."
      result = safe_extract("b64==", Receipt, describe_fn=_bad, retries=2)
      print(result)   # None

      # With good mock: succeeds on first attempt
      def _good(b64, p): return '{"merchant": "ACME", "total": 42.0}'
      result = safe_extract("b64==", Receipt, describe_fn=_good)
      print(result)   # {'merchant': 'ACME', 'total': 42.0}
    narration: >
      The for loop runs up to retries + 1 times. The try/except catches
      both ValueError (no JSON found) and JSONDecodeError (malformed JSON)
      — the two parse failures from extract_from_image. On the last attempt
      it returns None rather than raising, so the caller can decide what to
      do: log a warning, use a default, or surface an error to the user.
      None is a clear signal — distinct from an empty dict, which might be
      a valid schema response.

  - type: how_it_works
    label: "validate_extraction"
    heading: "validate_extraction: Schema Conformance Check"
    body: >
      Validates an extracted dict against the Pydantic schema, returning a
      (success, result) tuple — the same tuple pattern as Days 51 and 55.
    narration: >
      After safe_extract returns a dict, validate_extraction runs
      model_validate to check that all required fields are present with
      the correct types. It returns a tuple: (True, validated_model) on
      success, or (False, error_message_string) on failure. The tuple
      pattern lets the caller branch cleanly without a try/except at the
      call site — check tuple[0], then use tuple[1] as either the model
      or the error message.

  - type: code
    label: "validate_extraction"
    heading: "validate_extraction Implementation"
    code: |
      from pydantic import BaseModel

      def validate_extraction(data: dict, schema_cls) -> tuple:
          try:
              model = schema_cls.model_validate(data)
              return (True, model)
          except Exception as exc:
              return (False, str(exc))

      class Receipt(BaseModel):
          merchant: str
          total:    float

      ok, result = validate_extraction({'merchant': 'ACME', 'total': 42.0},
                                       Receipt)
      print(ok, result.merchant)    # True ACME

      ok2, err = validate_extraction({'merchant': 'ACME'}, Receipt)
      print(ok2, err)   # False 'total' is required...
    narration: >
      Using bare Exception rather than pydantic.ValidationError means the
      function handles any validation error — type errors, constraint
      violations, and unexpected exceptions alike. The error message string
      is human-readable, suitable for logging or displaying in a UI. The
      (True, model) / (False, error_str) tuple is easier to use than
      try/except at every call site.

  - type: exercise
    heading: "Exercise 4: Validate Extraction"
    prompt: >
      Implement validate_extraction(data: dict, schema_cls) -> tuple.
      Try schema_cls.model_validate(data). On success return (True, model).
      On any exception return (False, str(exc)).
      Also implement safe_extract(img_b64, schema_cls, describe_fn=None,
      retries=2) -> dict | None. Loop up to retries+1 times. On the last
      attempt return None instead of raising. Catch ValueError and
      json.JSONDecodeError.
    hint: >
      validate_extraction: try model_validate, except Exception as exc: return (False, str(exc)).
      safe_extract: for attempt in range(retries+1): try extract_from_image, except ... if attempt==retries return None.
    narration: >
      Both functions complete the robustness layer of the extraction pipeline.
      validate_extraction gives the caller a clean way to check schema
      conformance without catching Pydantic exceptions everywhere.

  - type: summary
    heading: "Lesson 4 Summary"
    bullets:
      - "Temperature > 0: same prompt may fail once but succeed next attempt"
      - "safe_extract: loop retries+1 times; return None on exhaustion"
      - "Catch ValueError (no JSON) and JSONDecodeError (bad JSON)"
      - "validate_extraction: (True, model) or (False, error_str) tuple"
      - "Use model_validate (not model_validate_json) on a dict"
    narration: >
      Retry and validation are in place. The final lesson assembles everything
      into an ImageExtractor class and a convenience pipeline function.
"""

_LESSON_05 = """\
day: "069"
lesson: 5
title: "ImageExtractor — End-to-End Pipeline"
slides:
  - type: title
    heading: "ImageExtractor"
    subheading: "PIL Image → validated Pydantic object in one call"
    narration: >
      All the pieces are ready. The final lesson puts them together in
      an ImageExtractor class that accepts a PIL Image and a Pydantic
      schema class and returns a validated typed object — the cleanest
      possible interface for schema-guided image extraction.

  - type: how_it_works
    label: "ImageExtractor"
    heading: "ImageExtractor Design"
    body: >
      One class, one method: extract(img) → validated Pydantic model.
      The schema class is bound at construction time.
    bullets:
      - "ImageExtractor(schema_cls, model='llava', describe_fn=None)"
      - ".extract(img, retries=2) → validated model instance"
      - "Raises ValueError if all retries fail"
      - "Raises ValidationError if JSON parsed but schema mismatch"
    narration: >
      Binding the schema_cls at construction time means you can create
      separate extractor instances for different document types — a
      ReceiptExtractor, a ProductExtractor, an InvoiceExtractor —
      and reuse them across many images. The describe_fn injection is
      still available for testing. The extractor encodes the image once
      and calls safe_extract, which handles retries internally.

  - type: code
    label: "Usage"
    heading: "Using ImageExtractor"
    code: |
      from pydantic import BaseModel
      from image_extractor import ImageExtractor
      from PIL import Image

      class Receipt(BaseModel):
          merchant: str
          total:    float
          items:    list[str] = []

      # Testing — no Ollama needed
      mock = lambda b64, p: '{"merchant": "ACME", "total": 42.0, "items": ["Coffee", "Bagel"]}'
      extractor = ImageExtractor(schema_cls=Receipt, describe_fn=mock)

      img = Image.new('RGB', (400, 200), 'white')
      result = extractor.extract(img)

      print(result.merchant)   # ACME
      print(result.total)      # 42.0
      print(result.items)      # ['Coffee', 'Bagel']
      print(type(result))      # <class '__main__.Receipt'>
    narration: >
      The result is a fully typed Python object — not a dict, not a JSON
      string. You can access fields with dot notation, use them in type-checked
      code, serialise them back to JSON with model_dump, or store them in a
      database. This is the difference between "the LLM returned some text
      about the receipt" and "the receipt's total is 42.0 as a Python float."

  - type: code
    label: "Real schemas"
    heading: "Real-World Schema Examples"
    code: |
      from pydantic import BaseModel, Field
      from typing import Optional

      class ReceiptItem(BaseModel):
          name:  str
          price: float

      class Receipt(BaseModel):
          merchant: str
          date:     str = ""
          items:    list[ReceiptItem] = []
          subtotal: float = 0.0
          tax:      float = 0.0
          total:    float

      class ProductLabel(BaseModel):
          name:        str
          brand:       str = ""
          price:       Optional[float] = None
          barcode:     str = ""
          description: str = ""

      class BusinessCard(BaseModel):
          name:    str
          title:   str = ""
          email:   str = ""
          phone:   str = ""
          company: str = ""
    narration: >
      The schema can be as simple or as detailed as you need. Optional fields
      with defaults give the LLM flexibility — it only needs to fill in the
      fields it can see. Required fields (no default) force the LLM to extract
      them or produce a ValidationError. Nested models like ReceiptItem work
      because model_json_schema generates a $defs section and the LLM has
      seen this pattern many times. The more constrained your schema, the
      more precisely you need to word the extraction prompt.

  - type: exercise
    heading: "Exercise 5: Extract Pipeline"
    prompt: >
      Implement extract_pipeline(img, schema_cls, describe_fn=None) -> BaseModel.
      Encode the PIL Image with image_to_base64. Call safe_extract to get a dict
      (retries=2). If None, raise ValueError. Call validate_extraction to get
      (ok, result). If not ok, raise ValueError(result). Return the validated model.
      A complete pipeline: encode → extract → validate → return typed object.
    hint: >
      img_b64 = image_to_base64(img). data = safe_extract(img_b64, schema_cls,
      describe_fn=describe_fn, retries=2). if data is None: raise ValueError.
      ok, result = validate_extraction(data, schema_cls). if not ok: raise ValueError(result).
      return result.
    narration: >
      extract_pipeline is the one-liner interface over the whole extraction
      stack. It enforces the complete happy-path and raises ValueError for
      any failure, giving callers a single exception type to handle.

  - type: summary
    heading: "Lesson 5 Summary — Day 69 Complete"
    bullets:
      - "ImageExtractor binds schema_cls at construction — reusable across images"
      - ".extract(img) → encode → safe_extract → validate → typed object"
      - "Raises ValueError if extraction fails; ValidationError if schema mismatch"
      - "Real schemas: nested models, Optional fields, list fields all supported"
      - "Tomorrow (Day 70): AI image generation with mock-based exercises"
    narration: >
      Day 69 is complete. You can extract structured typed data from any image
      using a vision LLM and a Pydantic schema. The pipeline handles markdown
      noise, retries on parse failure, and validates types — all the robustness
      you need for production document AI. Tomorrow is image generation.
"""

for i, content in enumerate([_LESSON_01, _LESSON_02, _LESSON_03,
                               _LESSON_04, _LESSON_05], start=1):
    (OUT / "lessons" / f"day_{DAY}_lesson_0{i}.yaml").write_text(content)

# ── shared helper source ───────────────────────────────────────────────────────
_HELPER_SRC = """\
import io
import re
import json
import base64
from pydantic import BaseModel

def image_to_base64(img, format='PNG'):
    buf = io.BytesIO()
    out = img
    if format.upper() in ('JPEG', 'JPG') and img.mode in ('RGBA', 'P'):
        out = img.convert('RGB')
    out.save(buf, format=format)
    return base64.b64encode(buf.getvalue()).decode()

def build_extraction_prompt(schema_cls):
    schema_json = json.dumps(schema_cls.model_json_schema(), indent=2)
    return (
        'Extract structured data from this image and return ONLY valid JSON '
        'matching this schema exactly. Do not include any explanation, '
        'markdown, or code blocks.\\n\\n'
        f'Schema:\\n{schema_json}\\n\\n'
        'Return ONLY the JSON object, nothing else.'
    )

def strip_json_from_response(response):
    block = re.search(r'```(?:json)?\\s*([\\s\\S]*?)```', response)
    if block:
        return block.group(1).strip()
    obj = re.search(r'\\{[\\s\\S]*\\}', response)
    if obj:
        return obj.group(0).strip()
    raise ValueError(f'No JSON found: {response[:200]!r}')

def extract_from_image(img_b64, schema_cls, describe_fn=None):
    prompt = build_extraction_prompt(schema_cls)
    if describe_fn is not None:
        response = describe_fn(img_b64, prompt)
    else:
        import ollama
        resp = ollama.chat(
            model='llava',
            messages=[{'role': 'user', 'content': prompt, 'images': [img_b64]}]
        )
        response = resp['message']['content']
    raw = strip_json_from_response(response)
    return json.loads(raw)

def safe_extract(img_b64, schema_cls, describe_fn=None, retries=2):
    for attempt in range(retries + 1):
        try:
            return extract_from_image(img_b64, schema_cls, describe_fn=describe_fn)
        except (ValueError, json.JSONDecodeError):
            if attempt == retries:
                return None
    return None

def validate_extraction(data, schema_cls):
    try:
        model = schema_cls.model_validate(data)
        return (True, model)
    except Exception as exc:
        return (False, str(exc))
"""

# ── test schemas ──────────────────────────────────────────────────────────────
_TEST_SCHEMA_SRC = """\
from pydantic import BaseModel

class _TestItem(BaseModel):
    name:  str
    value: float

class _TestSchema(BaseModel):
    title:   str
    amount:  float
    items:   list[_TestItem] = []
    note:    str = ''
"""

# ── EXERCISE 1 — build_extraction_prompt ─────────────────────────────────────
_EX1_GIVEN = """\
import json
from pydantic import BaseModel

class ProductInfo(BaseModel):
    name:     str
    price:    float
    category: str = ''
"""

_EX1_STUB = """\
def build_extraction_prompt(schema_cls) -> str:
    \"\"\"Build a vision LLM prompt for structured JSON extraction.

    Embeds the Pydantic model's JSON schema in the instruction.
    The prompt must instruct the model to return ONLY a JSON object
    matching the schema.

    Args:
        schema_cls: Pydantic BaseModel subclass
    Returns:
        Prompt string containing the JSON schema and extraction instruction
    \"\"\"
    raise NotImplementedError
"""

_EX1_SOLUTION = """\
def build_extraction_prompt(schema_cls) -> str:
    schema_json = json.dumps(schema_cls.model_json_schema(), indent=2)
    return (
        'Extract structured data from this image and return ONLY valid JSON '
        'matching this schema exactly. Do not include any explanation, '
        'markdown, or code blocks.\\n\\n'
        f'Schema:\\n{schema_json}\\n\\n'
        'Return ONLY the JSON object, nothing else.'
    )
"""

_EX1_CHECKS = """\
score, total = 0, 5
try:
    prompt = build_extraction_prompt(ProductInfo)
    assert isinstance(prompt, str), f"Expected str, got {type(prompt)}"
    score += 1; print("\\u2705 returns a string")

    assert 'JSON' in prompt or 'json' in prompt, "Prompt should mention JSON"
    score += 1; print("\\u2705 prompt mentions JSON")

    # Schema field names should appear in the prompt
    assert 'name' in prompt, "Field 'name' should appear in prompt"
    assert 'price' in prompt, "Field 'price' should appear in prompt"
    score += 1; print("\\u2705 field names (name, price) appear in prompt")

    # The embedded schema should be parseable JSON
    import re
    json_block = re.search(r'\\{[\\s\\S]*\\}', prompt)
    assert json_block, "Prompt should contain a JSON schema block"
    parsed = json.loads(json_block.group(0))
    assert isinstance(parsed, dict)
    score += 1; print("\\u2705 embedded schema block is valid JSON")

    # Works with a different schema
    class _Other(BaseModel):
        merchant: str
        total: float
    p2 = build_extraction_prompt(_Other)
    assert 'merchant' in p2 and 'total' in p2
    score += 1; print("\\u2705 works with a different schema class")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX1 = nb([
    md("# Day 069 — Exercise 1: Build Extraction Prompt\n\n"
       "**What you'll build:** `build_extraction_prompt(schema_cls) -> str` — "
       "generate a vision LLM prompt that embeds the Pydantic model's JSON schema.\n\n"
       "**Why it matters:** The prompt is the single most important input to the "
       "extraction pipeline. Embedding the schema as JSON gives the model precise "
       "field names and types to target — dramatically improving the likelihood of "
       "a parseable, schema-conforming response."),
    code(_EX1_GIVEN),
    md("## Task\n\nImplement `build_extraction_prompt(schema_cls) -> str`:\n\n"
       "1. `schema_json = json.dumps(schema_cls.model_json_schema(), indent=2)`\n"
       "2. Build a prompt string that:\n"
       "   - Instructs the model to return ONLY valid JSON\n"
       "   - Embeds `schema_json` in a labeled `Schema:` block\n"
       "   - Ends with a constraint like \"Return ONLY the JSON object\"\n\n"
       "The checks verify that field names appear in the prompt and the embedded "
       "schema is valid JSON."),
    md("## Your Implementation"),
    code(_EX1_STUB),
    code(_EX1_SOLUTION),
    md("## Automated checks"),
    code(_EX1_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX1_SOLUTION + "```\n\n"
       "**Why `model_json_schema()` and not `model_fields`?** JSON Schema is "
       "the standard format LLMs understand — it has type information, required "
       "flags, and default values, all in a format the model has seen many times "
       "during training. `model_fields` is a Pydantic-internal dict that the "
       "model has not seen in training data.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_01.ipynb", EX1)

# ── EXERCISE 2 — strip_json_from_response ────────────────────────────────────
_EX2_GIVEN = """\
import re
import json
"""

_EX2_STUB = """\
def strip_json_from_response(response: str) -> str:
    \"\"\"Extract a JSON object from a raw LLM response string.

    Handles three formats:
        1. Markdown code block: ```json\\n{...}\\n```  (or ``` without 'json')
        2. Prefixed JSON:       'Here is the data: {...}'
        3. Plain JSON:          '{...}'

    Args:
        response: raw LLM output string
    Returns:
        Stripped JSON string ready for json.loads
    Raises:
        ValueError if no JSON object found in the response
    \"\"\"
    raise NotImplementedError
"""

_EX2_SOLUTION = """\
def strip_json_from_response(response: str) -> str:
    block = re.search(r'`{3}(?:json)?\\s*([\\s\\S]*?)`{3}', response)
    if block:
        return block.group(1).strip()
    obj = re.search(r'\\{[\\s\\S]*\\}', response)
    if obj:
        return obj.group(0).strip()
    raise ValueError(f'No JSON found: {response[:200]!r}')
"""

_EX2_CHECKS = """\
score, total = 0, 5
try:
    # Plain JSON
    r1 = strip_json_from_response('{"name": "Widget", "price": 9.99}')
    assert json.loads(r1) == {"name": "Widget", "price": 9.99}
    score += 1; print("\\u2705 plain JSON")

    # Markdown code block with language tag
    r2 = strip_json_from_response('```json\\n{"name": "Widget", "price": 9.99}\\n```')
    assert json.loads(r2) == {"name": "Widget", "price": 9.99}
    score += 1; print("\\u2705 markdown code block (```json)")

    # Markdown code block without language tag
    r3 = strip_json_from_response('```\\n{"name": "Widget"}\\n```')
    assert json.loads(r3) == {"name": "Widget"}
    score += 1; print("\\u2705 markdown code block (no language tag)")

    # Prefixed with explanation text
    r4 = strip_json_from_response('Here is the data:\\n{"name": "Widget", "price": 9.99}')
    assert json.loads(r4)['name'] == 'Widget'
    score += 1; print("\\u2705 prefixed JSON (explanation text before)")

    # No JSON → ValueError
    raised = False
    try:
        strip_json_from_response("I cannot determine the values from this image.")
    except ValueError:
        raised = True
    assert raised, "Should raise ValueError when no JSON found"
    score += 1; print("\\u2705 raises ValueError when no JSON object found")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX2 = nb([
    md("# Day 069 — Exercise 2: Strip JSON from LLM Response\n\n"
       "**What you'll build:** `strip_json_from_response(response) -> str` — "
       "extract the raw JSON string from any LLM response format.\n\n"
       "**Why it matters:** Vision LLMs often wrap their JSON output in markdown "
       "code blocks (` ```json...``` `) or precede it with explanation text. "
       "This function is the noise filter that delivers a clean JSON string to "
       "`json.loads` regardless of the model's formatting habits."),
    code(_EX2_GIVEN),
    md("## Task\n\nImplement `strip_json_from_response(response: str) -> str`:\n\n"
       "1. Try `re.search(r'```(?:json)?\\\\s*([\\\\s\\\\S]*?)```', response)` — "
       "markdown code block\n"
       "2. If found: return `block.group(1).strip()`\n"
       "3. Otherwise: try `re.search(r'\\\\{[\\\\s\\\\S]*\\\\}', response)` — bare JSON\n"
       "4. If found: return `obj.group(0).strip()`\n"
       "5. If nothing found: `raise ValueError(f'No JSON found: {response[:200]!r}')`"),
    md("## Your Implementation"),
    code(_EX2_STUB),
    code(_EX2_SOLUTION),
    md("## Automated checks"),
    code(_EX2_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX2_SOLUTION + "```\n\n"
       "**Why code blocks first?** If the response is ```` ```json\\n{...}\\n``` ````, "
       "the bare JSON regex `{[\\\\s\\\\S]*}` would also match — but it would include "
       "the backticks as surrounding text. Trying code blocks first and returning "
       "the capture group gives the clean inner content without backticks.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_02.ipynb", EX2)

# ── EXERCISE 3 — extract_from_image ──────────────────────────────────────────
_EX3_GIVEN = """\
import re
import json
from pydantic import BaseModel

def build_extraction_prompt(schema_cls):
    schema_json = json.dumps(schema_cls.model_json_schema(), indent=2)
    return (
        'Extract structured data from this image and return ONLY valid JSON '
        'matching this schema exactly.\\n\\nSchema:\\n' + schema_json +
        '\\n\\nReturn ONLY the JSON object, nothing else.'
    )

def strip_json_from_response(response):
    block = re.search(r'```(?:json)?\\s*([\\s\\S]*?)```', response)
    if block:
        return block.group(1).strip()
    obj = re.search(r'\\{[\\s\\S]*\\}', response)
    if obj:
        return obj.group(0).strip()
    raise ValueError(f'No JSON found: {response[:200]!r}')

class ProductInfo(BaseModel):
    name:     str
    price:    float
    category: str = ''
"""

_EX3_STUB = """\
def extract_from_image(img_b64: str, schema_cls,
                       describe_fn=None) -> dict:
    \"\"\"Send an image to a vision LLM and parse the response as JSON.

    Args:
        img_b64:     base64-encoded image string
        schema_cls:  Pydantic model class defining the extraction schema
        describe_fn: callable(img_b64, prompt) -> str for testing
    Returns:
        dict of extracted fields (not yet Pydantic-validated)
    Raises:
        ValueError if no JSON found in the response
        json.JSONDecodeError if the extracted string is malformed JSON
    \"\"\"
    raise NotImplementedError
"""

_EX3_SOLUTION = """\
def extract_from_image(img_b64: str, schema_cls,
                       describe_fn=None) -> dict:
    prompt = build_extraction_prompt(schema_cls)
    if describe_fn is not None:
        response = describe_fn(img_b64, prompt)
    else:
        import ollama
        resp = ollama.chat(
            model='llava',
            messages=[{'role': 'user', 'content': prompt, 'images': [img_b64]}]
        )
        response = resp['message']['content']
    raw = strip_json_from_response(response)
    return json.loads(raw)
"""

_EX3_CHECKS = """\
score, total = 0, 5
try:
    captured = {}
    def _mock(b64, p):
        captured['b64']    = b64
        captured['prompt'] = p
        return '{"name": "Headphones", "price": 49.99}'

    result = extract_from_image('test_b64==', ProductInfo, describe_fn=_mock)
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    score += 1; print("\\u2705 returns a dict")

    assert result == {'name': 'Headphones', 'price': 49.99}, (
        f"Unexpected result: {result}")
    score += 1; print("\\u2705 dict matches mock JSON")

    assert captured['b64'] == 'test_b64==', "img_b64 should be passed to describe_fn"
    score += 1; print("\\u2705 mock receives the img_b64 argument")

    # Prompt contains schema fields
    assert 'name' in captured['prompt'] and 'price' in captured['prompt'], (
        f"Schema fields missing from prompt: {captured['prompt'][:200]!r}")
    score += 1; print("\\u2705 prompt contains schema field names")

    # Mock returning markdown block also works
    r2 = extract_from_image('b64', ProductInfo,
                             describe_fn=lambda b, p: '```json\\n{"name":"Test","price":1.0}\\n```')
    assert r2['name'] == 'Test'
    score += 1; print("\\u2705 handles markdown-wrapped JSON response")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX3 = nb([
    md("# Day 069 — Exercise 3: Extract from Image\n\n"
       "**What you'll build:** `extract_from_image(img_b64, schema_cls, describe_fn=None) -> dict` "
       "— the core extraction function combining prompt generation, LLM call, and JSON parsing.\n\n"
       "**Why it matters:** This is the central function of the multimodal extraction pipeline. "
       "All other functions (`safe_extract`, `extract_pipeline`, `ImageExtractor.extract`) "
       "delegate to it. Getting the mock interface right ensures every downstream function "
       "is testable without Ollama."),
    code(_EX3_GIVEN),
    md("## Task\n\nImplement `extract_from_image(img_b64, schema_cls, describe_fn=None) -> dict`:\n\n"
       "1. `prompt = build_extraction_prompt(schema_cls)`\n"
       "2. If `describe_fn is not None`: `response = describe_fn(img_b64, prompt)`\n"
       "3. Otherwise: call `ollama.chat(model='llava', messages=[{...}])`\n"
       "4. `raw = strip_json_from_response(response)`\n"
       "5. `return json.loads(raw)`\n\n"
       "Return a plain dict — do not validate against the schema here."),
    md("## Your Implementation"),
    code(_EX3_STUB),
    code(_EX3_SOLUTION),
    md("## Automated checks"),
    code(_EX3_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX3_SOLUTION + "```\n\n"
       "**Why return a dict and not a model?** Keeping parse and validate as "
       "separate steps makes error handling cleaner: JSONDecodeError = bad syntax "
       "(retry the call), ValidationError = bad data (schema mismatch, possibly "
       "unretryable). If extraction and validation were combined, you could not "
       "distinguish the two failure modes.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_03.ipynb", EX3)

# ── EXERCISE 4 — safe_extract + validate_extraction ──────────────────────────
_EX4_GIVEN = _HELPER_SRC + "\n" + _TEST_SCHEMA_SRC + """
from PIL import Image
_img = Image.new('RGB', (200, 100), 'white')
_img_b64 = image_to_base64(_img)
"""

_EX4_STUB = """\
def safe_extract(img_b64: str, schema_cls,
                 describe_fn=None, retries: int = 2):
    \"\"\"Extract JSON from an image with retry on parse failure.

    Args:
        img_b64:    base64-encoded image string
        schema_cls: Pydantic model class
        describe_fn: callable for testing
        retries:    number of extra attempts (total = retries + 1)
    Returns:
        dict on success, None if all attempts fail
    \"\"\"
    raise NotImplementedError


def validate_extraction(data: dict, schema_cls) -> tuple:
    \"\"\"Validate extracted data against a Pydantic schema.

    Args:
        data:       dict from extract_from_image or safe_extract
        schema_cls: Pydantic model class
    Returns:
        (True, validated_model) on success
        (False, error_message_str) on failure
    \"\"\"
    raise NotImplementedError
"""

_EX4_SOLUTION = """\
def safe_extract(img_b64: str, schema_cls,
                 describe_fn=None, retries: int = 2):
    for attempt in range(retries + 1):
        try:
            return extract_from_image(img_b64, schema_cls,
                                      describe_fn=describe_fn)
        except (ValueError, json.JSONDecodeError):
            if attempt == retries:
                return None
    return None


def validate_extraction(data: dict, schema_cls) -> tuple:
    try:
        model = schema_cls.model_validate(data)
        return (True, model)
    except Exception as exc:
        return (False, str(exc))
"""

_EX4_CHECKS = """\
score, total = 0, 5
try:
    # safe_extract: good mock → returns dict
    _good = lambda b, p: '{"title": "Test", "amount": 42.0}'
    result = safe_extract(_img_b64, _TestSchema, describe_fn=_good)
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert result['title'] == 'Test' and result['amount'] == 42.0
    score += 1; print("\\u2705 safe_extract returns dict on success")

    # safe_extract: always-failing mock → returns None after retries
    _bad = lambda b, p: "no json here"
    result_none = safe_extract(_img_b64, _TestSchema, describe_fn=_bad, retries=1)
    assert result_none is None, f"Expected None, got {result_none}"
    score += 1; print("\\u2705 safe_extract returns None after exhausting retries")

    # validate_extraction: valid data → (True, model)
    ok, model = validate_extraction({'title': 'Test', 'amount': 9.99}, _TestSchema)
    assert ok is True, f"Expected True, got {ok}"
    assert model.title == 'Test' and model.amount == 9.99
    score += 1; print("\\u2705 validate_extraction returns (True, model) for valid data")

    # validate_extraction: missing required field → (False, error_str)
    ok2, err = validate_extraction({'title': 'Test'}, _TestSchema)
    assert ok2 is False, f"Expected False, got {ok2}"
    assert isinstance(err, str) and len(err) > 0
    score += 1; print("\\u2705 validate_extraction returns (False, error_str) for invalid data")

    # validate_extraction: type coercion works (str "9.99" → float 9.99)
    ok3, model3 = validate_extraction({'title': 'Coerce', 'amount': '9.99'}, _TestSchema)
    assert ok3 is True and abs(model3.amount - 9.99) < 0.001
    score += 1; print("\\u2705 validate_extraction coerces str to float")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX4 = nb([
    md("# Day 069 — Exercise 4: Retry + Validation\n\n"
       "**What you'll build:** `safe_extract` (retry wrapper) and "
       "`validate_extraction` (Pydantic conformance check).\n\n"
       "**Why it matters:** Production vision LLM calls are non-deterministic — "
       "a prompt that fails once often succeeds on the next attempt. "
       "`safe_extract` handles this gracefully, and `validate_extraction` gives "
       "callers a clean (ok, result) tuple instead of forcing them to catch "
       "Pydantic exceptions everywhere."),
    code(_EX4_GIVEN),
    md("## Task\n\nImplement both functions:\n\n"
       "**`safe_extract(img_b64, schema_cls, describe_fn=None, retries=2)`:**\n"
       "- `for attempt in range(retries + 1):`\n"
       "- `try: return extract_from_image(...)`\n"
       "- `except (ValueError, json.JSONDecodeError): if attempt == retries: return None`\n\n"
       "**`validate_extraction(data, schema_cls) -> tuple`:**\n"
       "- `try: return (True, schema_cls.model_validate(data))`\n"
       "- `except Exception as exc: return (False, str(exc))`"),
    md("## Your Implementation"),
    code(_EX4_STUB),
    code(_EX4_SOLUTION),
    md("## Automated checks"),
    code(_EX4_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX4_SOLUTION + "```\n\n"
       "**Why return `None` not raise on exhaustion?** `None` is a clear "
       "sentinel that the pipeline failed — different from an empty dict, "
       "which is a valid (though unusual) schema response. The caller decides "
       "whether to log, use a default, or surface an error, without being "
       "forced to wrap `safe_extract` in another try/except.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_04.ipynb", EX4)

# ── EXERCISE 5 — extract_pipeline ─────────────────────────────────────────────
_EX5_GIVEN = _HELPER_SRC + "\n" + _TEST_SCHEMA_SRC + """
from PIL import Image
_img = Image.new('RGB', (200, 100), 'white')
"""

_EX5_STUB = """\
def extract_pipeline(img, schema_cls, describe_fn=None):
    \"\"\"Full extraction pipeline: PIL Image → validated Pydantic model.

    Steps:
        1. image_to_base64(img)
        2. safe_extract(img_b64, schema_cls, describe_fn, retries=2)
        3. If None: raise ValueError('Extraction failed after retries')
        4. validate_extraction(data, schema_cls)
        5. If not ok: raise ValueError(error_message)
        6. Return the validated model instance

    Args:
        img:         PIL Image
        schema_cls:  Pydantic model class
        describe_fn: callable(img_b64, prompt) -> str for testing
    Returns:
        Validated Pydantic model instance
    Raises:
        ValueError if extraction or validation fails
    \"\"\"
    raise NotImplementedError
"""

_EX5_SOLUTION = """\
def extract_pipeline(img, schema_cls, describe_fn=None):
    img_b64 = image_to_base64(img)
    data = safe_extract(img_b64, schema_cls, describe_fn=describe_fn, retries=2)
    if data is None:
        raise ValueError('Extraction failed after retries')
    ok, result = validate_extraction(data, schema_cls)
    if not ok:
        raise ValueError(result)
    return result
"""

_EX5_CHECKS = """\
score, total = 0, 5
try:
    _mock = lambda b, p: '{"title": "Invoice", "amount": 99.50}'

    # Happy path: returns validated model
    result = extract_pipeline(_img, _TestSchema, describe_fn=_mock)
    assert hasattr(result, 'title') and hasattr(result, 'amount'), (
        f"Expected model with title/amount, got {type(result)}")
    score += 1; print("\\u2705 returns a validated Pydantic model")

    assert result.title == 'Invoice' and abs(result.amount - 99.50) < 0.001
    score += 1; print(f"\\u2705 model fields correct: title={result.title!r}, amount={result.amount}")

    # Extraction failure → ValueError
    raised = False
    try:
        extract_pipeline(_img, _TestSchema, describe_fn=lambda b, p: 'no json here')
    except ValueError:
        raised = True
    assert raised, "Should raise ValueError when extraction fails"
    score += 1; print("\\u2705 raises ValueError when extraction fails")

    # Validation failure → ValueError (missing required 'amount' field)
    raised2 = False
    try:
        extract_pipeline(_img, _TestSchema,
                          describe_fn=lambda b, p: '{"title": "OnlyTitle"}')
    except ValueError:
        raised2 = True
    assert raised2, "Should raise ValueError when validation fails"
    score += 1; print("\\u2705 raises ValueError when validation fails (missing required field)")

    # Type coercion: '99.50' string → float 99.50
    result2 = extract_pipeline(_img, _TestSchema,
                                describe_fn=lambda b, p: '{"title": "T", "amount": "99.50"}')
    assert abs(result2.amount - 99.50) < 0.001
    score += 1; print("\\u2705 Pydantic coerces string amounts to float")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX5 = nb([
    md("# Day 069 — Exercise 5: Extract Pipeline\n\n"
       "**What you'll build:** `extract_pipeline(img, schema_cls, describe_fn=None)` "
       "— the complete end-to-end pipeline from PIL Image to validated Pydantic model.\n\n"
       "**Why it matters:** This is the final integration layer. It encodes the image, "
       "calls the vision LLM with retries, validates the result, and returns a typed "
       "Python object — or raises a clear `ValueError` at any failure point. "
       "The `ImageExtractor` class is a thin wrapper over this function."),
    code(_EX5_GIVEN),
    md("## Task\n\nImplement `extract_pipeline(img, schema_cls, describe_fn=None)`:\n\n"
       "1. `img_b64 = image_to_base64(img)`\n"
       "2. `data = safe_extract(img_b64, schema_cls, describe_fn=describe_fn, retries=2)`\n"
       "3. If `data is None`: `raise ValueError('Extraction failed after retries')`\n"
       "4. `ok, result = validate_extraction(data, schema_cls)`\n"
       "5. If `not ok`: `raise ValueError(result)`\n"
       "6. `return result`"),
    md("## Your Implementation"),
    code(_EX5_STUB),
    code(_EX5_SOLUTION),
    md("## Automated checks"),
    code(_EX5_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX5_SOLUTION + "```\n\n"
       "**Why `raise ValueError(result)` when validation fails?** The `result` "
       "from `validate_extraction` on failure is the error message string. "
       "Passing it to `ValueError` means the caller's exception message includes "
       "Pydantic's description of what was wrong — which field is missing, which "
       "type was wrong. This is more useful than a generic 'validation failed' message.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_05.ipynb", EX5)

# ── PROJECT NOTEBOOK ──────────────────────────────────────────────────────────
PROJECT = nb([
    md("# Day 069 — Project: Image Extractor\n\n"
       "## What You're Building\n\n"
       "`image_extractor.py` — an `ImageExtractor` class for schema-guided "
       "structured extraction from images using a vision LLM.\n\n"
       "**Deliverable:** A class that accepts a Pydantic model class at "
       "construction time and returns validated typed objects from any image.\n\n"
       "## Setup\n\n"
       "```bash\n"
       "ollama pull llava      # vision model\n"
       "```\n\n"
       "## Design\n\n"
       "```\n"
       "ImageExtractor(schema_cls, model='llava', describe_fn=None)\n"
       "  .extract(img, retries=2) → validated Pydantic model instance\n"
       "```\n\n"
       "## Usage (with real Ollama)\n\n"
       "```python\n"
       "from image_extractor import ImageExtractor\n"
       "from pydantic import BaseModel\n"
       "from PIL import Image\n\n"
       "class Receipt(BaseModel):\n"
       "    merchant: str\n"
       "    total:    float\n"
       "    items:    list[str] = []\n\n"
       "extractor = ImageExtractor(schema_cls=Receipt)\n"
       "img = Image.open('receipt.jpg')\n"
       "result = extractor.extract(img)\n"
       "print(result.merchant, result.total)\n"
       "```"),
    code("# Your implementation here\n"
         "# Build ImageExtractor and write it to image_extractor.py\n"),
])
save(OUT / "project" / "project.ipynb", PROJECT)

# ── SOLUTION NOTEBOOK ─────────────────────────────────────────────────────────
_SOL_CELL1 = (
    f"_EXTRACTOR_SRC = {repr(_EXTRACTOR_SRC)}\n"
    "from pathlib import Path\n"
    "Path('image_extractor.py').write_text(_EXTRACTOR_SRC, encoding='utf-8')\n"
    "print('image_extractor.py written.')"
)

_SOL_CELL2 = """\
import json, re, base64, io
from PIL import Image
from pydantic import BaseModel
from image_extractor import (
    ImageExtractor, image_to_base64, build_extraction_prompt,
    strip_json_from_response, extract_from_image, safe_extract,
    validate_extraction,
)

class ProductInfo(BaseModel):
    name:     str
    price:    float
    category: str = ''

_mock = lambda b64, prompt: '{"name": "Headphones", "price": 49.99, "category": "Electronics"}'
extractor = ImageExtractor(schema_cls=ProductInfo, describe_fn=_mock)
img = Image.new('RGB', (300, 150), 'white')

# 1. build_extraction_prompt embeds schema fields
prompt = build_extraction_prompt(ProductInfo)
assert 'name' in prompt and 'price' in prompt
print("\\u2705 build_extraction_prompt contains field names")

# 2. strip_json_from_response handles markdown
raw = strip_json_from_response('```json\\n{"a": 1}\\n```')
assert json.loads(raw) == {"a": 1}
print("\\u2705 strip_json_from_response handles markdown code block")

# 3. extract_from_image returns dict
d = extract_from_image(image_to_base64(img), ProductInfo, describe_fn=_mock)
assert isinstance(d, dict) and d['name'] == 'Headphones'
print("\\u2705 extract_from_image returns dict")

# 4. safe_extract returns dict on success
d2 = safe_extract(image_to_base64(img), ProductInfo, describe_fn=_mock)
assert d2 is not None and d2['price'] == 49.99
print("\\u2705 safe_extract returns dict on success")

# 5. safe_extract returns None on failure
d3 = safe_extract(image_to_base64(img), ProductInfo,
                   describe_fn=lambda b, p: 'no json', retries=1)
assert d3 is None
print("\\u2705 safe_extract returns None after exhausted retries")

# 6. validate_extraction success
ok, model = validate_extraction({'name': 'Widget', 'price': 9.99}, ProductInfo)
assert ok and model.name == 'Widget'
print("\\u2705 validate_extraction success: (True, model)")

# 7. validate_extraction failure
ok2, err = validate_extraction({'price': 9.99}, ProductInfo)
assert not ok2 and isinstance(err, str)
print("\\u2705 validate_extraction failure: (False, error_str)")

# 8. ImageExtractor.extract returns typed model
result = extractor.extract(img)
assert isinstance(result, ProductInfo)
assert result.name == 'Headphones' and result.price == 49.99
print(f"\\u2705 ImageExtractor.extract returns {type(result).__name__}: {result.name} ${result.price}")

print("\\nMultimodal Extraction complete!")
"""

SOLUTION = nb([
    md("# Day 069 — Solution: Image Extractor"),
    code(_SOL_CELL1),
    code(_SOL_CELL2),
])
save(OUT / "project" / "solution" / "solution.ipynb", SOLUTION)
(OUT / "project" / "solution" / "image_extractor.py").write_text(_EXTRACTOR_SRC)

print(f"Day {DAY} notebooks written to {OUT}")
print("  lessons/    day_069_lesson_01.yaml – lesson_05.yaml")
print("  exercises/  exercise_01 – exercise_05")
print("  project/    project.ipynb")
print("  project/solution/  solution.ipynb + image_extractor.py")
