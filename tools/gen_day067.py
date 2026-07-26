#!/usr/bin/env python3
"""gen_day067.py — generate Day 067: Vision LLM (Ollama llava)."""
from pathlib import Path
import json

ROOT    = Path(__file__).parent.parent
DAY     = "067"
SECTION = "05_vision_multimodal"
OUT     = ROOT / SECTION / f"day_{DAY}"

(OUT / "exercises").mkdir(parents=True, exist_ok=True)
(OUT / "lessons").mkdir(parents=True, exist_ok=True)
(OUT / "project" / "solution").mkdir(parents=True, exist_ok=True)

# ── deliverable: vision_analyzer.py ──────────────────────────────────────────
_ANALYZER_SRC = '''\
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
        label_list = ", ".join(f\'"{l}"\' for l in labels)
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

        tasks: list of keys — \'describe\', \'text\', \'colors\', \'objects\'.
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
day: "067"
lesson: 1
title: "Multimodal LLMs"
slides:
  - type: title
    heading: "Vision LLMs"
    subheading: "Day 67 — Giving language models eyes"
    narration: >
      Yesterday you learned to manipulate images with Pillow. Today you give
      those images to a language model and get text back. A vision LLM accepts
      both text and images as input, opening up a huge new class of tasks:
      describe a photo, read a receipt, classify a product image, or extract
      structured data from a screenshot.

  - type: concept
    label: "Multimodal models"
    heading: "What Makes a Model Vision-Capable?"
    body: >
      A multimodal LLM processes multiple modalities — text and images — in
      a single forward pass. The image is encoded by a vision encoder, then
      its features are projected into the same embedding space as tokens.
    bullets:
      - "Vision encoder (e.g. CLIP) converts image to a feature vector"
      - "Projector maps image features into the LLM token space"
      - "LLM processes combined image tokens + text tokens together"
      - "Output: text that is grounded in the visual content"
    narration: >
      Traditional LLMs only process tokens — pieces of text. A multimodal
      model adds a vision encoder that converts an image into a sequence of
      feature vectors. A learned projection layer maps those features into
      the same embedding space as text tokens. The language model then
      attends over both image features and text tokens simultaneously,
      producing output that is grounded in the visual content. Models like
      llava use CLIP as their vision encoder and LLaMA as the text backbone.

  - type: concept
    label: "What vision LLMs can do"
    heading: "Vision LLM Capabilities"
    body: >
      Vision LLMs can answer natural language questions about images with no
      task-specific fine-tuning — zero-shot.
    bullets:
      - "Caption: describe what is in the image"
      - "Classification: which category does this image belong to?"
      - "OCR: what text is visible in this image?"
      - "VQA: answer any question about the image content"
      - "Structured extraction: describe then parse into schema (Day 69)"
    narration: >
      Zero-shot means you do not need labelled training data for your specific
      task. You describe the task in the prompt, show the model an image, and
      it applies its broad visual understanding. Captioning, classification,
      OCR, and visual question answering all work this way. In Day 69 you will
      take this further and combine a vision LLM with a Pydantic schema to
      extract structured JSON from images — product photos, receipts, invoices.

  - type: how_it_works
    label: "Ollama vision"
    heading: "Running Vision Models with Ollama"
    body: >
      Ollama supports vision models the same way it supports text models.
      Pull the model once, then pass images in the messages list.
    narration: >
      Ollama added vision model support by extending the chat message format.
      The existing messages list already supports role and content. For vision,
      you add an images key containing a list of base64-encoded image strings.
      The model key is just the name of the vision model you pulled — llava,
      llava-phi3, llama3.2-vision, or others. No extra packages needed beyond
      the ollama Python library you already have.

  - type: code
    label: "Ollama vision API"
    heading: "ollama.chat with images"
    code: |
      import ollama

      # Pass images as base64 strings in the message
      resp = ollama.chat(
          model='llava',
          messages=[{
              'role':    'user',
              'content': 'What do you see in this image?',
              'images':  ['<base64_string_here>'],   # list of base64 strings
          }]
      )
      print(resp['message']['content'])
    narration: >
      The Ollama vision API is an extension of the standard chat API you
      learned in Day 3. The only difference is the images key in the message
      dict. It takes a list of base64-encoded image strings — not file paths,
      not URLs, just raw base64 data. The response format is identical to a
      text-only chat call: the answer is at resp['message']['content']. You
      can combine text and images in any message, and add multi-turn history
      exactly as you would for a text-only conversation.

  - type: exercise
    heading: "Exercise 1: Image to Base64"
    prompt: >
      Implement image_to_base64(img, format='PNG') -> str. Encode a PIL Image
      as a base64 string using BytesIO. For JPEG format, convert RGBA and P
      mode images to RGB first. Return the base64 string without a data URI prefix.
    hint: >
      io.BytesIO() → img.save(buf, format=format) → base64.b64encode(buf.getvalue()).decode()
    narration: >
      The first exercise converts a PIL Image into the format that Ollama
      expects — a base64 string. This is the encoding bridge between Pillow
      and any vision API. Once you implement this, you will reuse it in every
      subsequent exercise today and in Days 69 and 76.

  - type: summary
    heading: "Lesson 1 Summary"
    bullets:
      - "Vision LLMs = text LLM + vision encoder + projector"
      - "Zero-shot: describe the task in a prompt, no labelled data needed"
      - "Ollama vision: same chat API, add images key with base64 list"
      - "Response format unchanged: resp['message']['content']"
    narration: >
      You understand how vision LLMs work and how Ollama exposes them. Next
      lesson: why images are encoded as base64 and how the encoding pipeline
      works end to end.
"""

_LESSON_02 = """\
day: "067"
lesson: 2
title: "Image Encoding for LLMs"
slides:
  - type: title
    heading: "Image Encoding for LLMs"
    subheading: "PIL → BytesIO → base64 → Ollama"
    narration: >
      Vision LLM APIs do not accept file paths or URLs — they expect images
      as base64-encoded strings embedded directly in the request body. This
      lesson covers why, and shows you the encoding pipeline that converts
      a PIL Image into what Ollama needs.

  - type: concept
    label: "Why base64?"
    heading: "Binary in Text Protocols"
    body: >
      HTTP request bodies and JSON values are text. Base64 encodes binary
      data (image bytes) as printable ASCII characters that can be safely
      embedded in any text field.
    bullets:
      - "Base64 maps every 3 bytes to 4 ASCII characters"
      - "Overhead: ~33% larger than the original binary"
      - "Result is pure ASCII — safe in JSON, HTTP, SQL"
      - "Decoding is exact — no information lost"
    narration: >
      Images are binary data — sequences of bytes that include values from 0
      to 255. JSON is a text format that cannot represent arbitrary binary
      bytes directly. Base64 solves this by encoding every three bytes as
      four printable ASCII characters. The overhead is about one third larger
      than the original, but the result is a plain string you can embed in
      any JSON field. Ollama's messages API is JSON-based, so base64 is the
      correct encoding for the images list.

  - type: how_it_works
    label: "Encoding pipeline"
    heading: "PIL → BytesIO → base64 → str"
    body: >
      Four steps: create a BytesIO buffer, save the PIL Image into it,
      read the bytes, encode as base64.
    narration: >
      The full pipeline has four steps. First, create an io.BytesIO buffer —
      an in-memory file-like object that accepts writes and reads. Second,
      call img.save on the buffer, specifying a format. Third, call
      buf.getvalue to get the raw bytes — no seek needed when using getvalue
      rather than reading. Fourth, call base64.b64encode on the bytes and
      decode the result to a Python str. The decode call converts the bytes
      object returned by b64encode to a regular string for JSON serialisation.

  - type: code
    label: "Encoding"
    heading: "PIL Image to Base64 String"
    code: |
      import io, base64
      from PIL import Image

      img = Image.new('RGB', (100, 100), color=(255, 0, 0))  # red square

      # Step 1-3: save to bytes
      buf = io.BytesIO()
      img.save(buf, format='PNG')
      raw_bytes = buf.getvalue()     # no seek() needed with getvalue()

      # Step 4: base64 encode
      b64_str = base64.b64encode(raw_bytes).decode()
      print(f"Original bytes: {len(raw_bytes):,}")
      print(f"Base64 chars:   {len(b64_str):,}")  # ~33% larger
      print(f"First 20 chars: {b64_str[:20]!r}")
    narration: >
      Notice that we call buf.getvalue() rather than buf.read(). getvalue
      returns all bytes written to the buffer regardless of the current
      read position — it does not require seek zero first. buf.read, by
      contrast, reads from the current position, so after a write you would
      need to seek zero. Use getvalue when you only want the full bytes and
      do not need to read the buffer incrementally.

  - type: code
    label: "Decoding"
    heading: "Base64 → PIL Image (Round-trip)"
    code: |
      import io, base64
      from PIL import Image

      # Decode back to PIL Image
      def base64_to_image(b64_str: str) -> Image.Image:
          raw = base64.b64decode(b64_str)
          return Image.open(io.BytesIO(raw))

      # Round-trip test
      img = Image.new('RGB', (64, 64), color=(0, 200, 100))
      b64 = base64.b64encode(
          (lambda b: (img.save(b, format='PNG'), b)[1])(io.BytesIO()).getvalue()
      ).decode()

      restored = base64_to_image(b64)
      print(restored.size, restored.mode)  # (64, 64) RGB
    narration: >
      Decoding is the reverse: pass the base64 string to base64.b64decode to
      get raw bytes, then wrap in BytesIO and call Image.open. The round-trip
      is lossless for PNG. For JPEG it is lossy — the decoded image will have
      slight compression artefacts. For sending to a vision model, PNG is
      safer because the model sees the exact pixels you intended.

  - type: exercise
    heading: "Exercise 2: Describe Image"
    prompt: >
      Implement describe_image(img_b64, prompt, describe_fn=None) -> str.
      If describe_fn is provided, call describe_fn(img_b64, prompt) and
      return the result. Otherwise call ollama.chat with model='llava' and
      the images parameter. All checks use a mock describe_fn so no Ollama
      server is needed.
    hint: >
      Check if describe_fn is not None first. For the Ollama path, the message
      dict needs role, content (the prompt), and images (list with img_b64).
      Return resp['message']['content'].
    narration: >
      This exercise implements the core describe_image function that all
      subsequent exercises build on. The describe_fn injection pattern is
      the same one you used throughout Section 4 with process_fn — it keeps
      the function testable without a running model server.

  - type: summary
    heading: "Lesson 2 Summary"
    bullets:
      - "Base64 encodes binary (images) as ASCII text for JSON / HTTP"
      - "~33% size overhead; lossless; always decodable back to exact bytes"
      - "io.BytesIO + img.save + buf.getvalue() → base64.b64encode().decode()"
      - "Use getvalue() (no seek needed) or seek(0) + read()"
      - "PNG is lossless; JPEG is lossy — use PNG when pixel accuracy matters"
    narration: >
      The encoding pipeline is settled. PIL to base64 is a two-liner you will
      reuse in Days 69, 71, and 76. Next: calling Ollama with an image and
      exploring the full range of analysis patterns.
"""

_LESSON_03 = """\
day: "067"
lesson: 3
title: "Ollama Vision API"
slides:
  - type: title
    heading: "Ollama Vision API"
    subheading: "llava, llama3.2-vision, and the images parameter"
    narration: >
      Now that you can encode images as base64, let's use them. This lesson
      walks through the Ollama vision API in detail — which models are
      available, how the messages format works with images, and how to
      handle the response.

  - type: how_it_works
    label: "Vision models"
    heading: "Available Vision Models in Ollama"
    body: >
      Ollama supports several vision models. Pull one before starting.
    bullets:
      - "'ollama pull llava' — LLaVA 7B or 13B; strong general vision"
      - "'ollama pull llava-phi3' — smaller, faster; good for descriptions"
      - "'ollama pull llama3.2-vision' — Meta's Llama 3.2 with vision"
      - "Check installed models: 'ollama list'"
    narration: >
      LLaVA — Large Language and Vision Assistant — is the most widely tested
      option. It uses CLIP for image encoding and LLaMA for text generation.
      Pull it with ollama pull llava before running any vision exercises for
      real. The exercises use a mock function so you can complete them even
      if llava is not available, but for the project you will want the real
      model. Check what is installed with ollama list in your terminal.

  - type: code
    label: "Full example"
    heading: "Complete Ollama Vision Call"
    code: |
      import base64, io, ollama
      from PIL import Image

      def ask_image(img: Image.Image, question: str,
                    model: str = 'llava') -> str:
          buf = io.BytesIO()
          img.save(buf, format='PNG')
          b64 = base64.b64encode(buf.getvalue()).decode()

          resp = ollama.chat(
              model=model,
              messages=[{
                  'role':    'user',
                  'content': question,
                  'images':  [b64],
              }]
          )
          return resp['message']['content']

      # Usage (requires ollama serve + ollama pull llava)
      img = Image.new('RGB', (200, 100), color=(255, 0, 0))
      # answer = ask_image(img, 'What colour is this image?')
    narration: >
      The ask_image helper shows the complete end-to-end pattern. Encode the
      image from a PIL Image, build the message dict with role, content, and
      images, call ollama.chat, and extract the content from the response.
      This is five lines of functional code — everything else in the day's
      exercises is just wrapping this pattern in different ways.

  - type: how_it_works
    label: "Multi-turn vision"
    heading: "Multi-turn Vision Conversations"
    body: >
      You can include images in any message in the conversation history. The
      model maintains context across turns, including visual context.
    narration: >
      Vision models support multi-turn conversations. You can ask a follow-up
      question about an image in the second turn without re-sending the image,
      because the model already encoded it in the first turn. You can also send
      different images in different turns. This enables conversational image
      analysis — ask for a description, then ask a follow-up about a specific
      detail, then ask to classify based on what was described.

  - type: code
    label: "Multi-turn"
    heading: "Multi-turn Vision Conversation"
    code: |
      import base64, io, ollama
      from PIL import Image

      def encode(img):
          buf = io.BytesIO()
          img.save(buf, format='PNG')
          return base64.b64encode(buf.getvalue()).decode()

      img = Image.new('RGB', (100, 100), color=(255, 128, 0))
      b64 = encode(img)

      history = [
          {'role': 'user',      'content': 'Describe this image.', 'images': [b64]},
          {'role': 'assistant', 'content': 'A solid orange square.'},
          {'role': 'user',      'content': 'What mood does it evoke?'},
          # No 'images' key needed in follow-up turns
      ]
      # resp = ollama.chat(model='llava', messages=history)
    narration: >
      Follow-up turns do not need to re-send the images key — the model's
      attention already processed the image in turn one. Only include images
      in the message where you are introducing new visual content. This keeps
      the request small and lets you ask multiple questions about the same
      image efficiently.

  - type: exercise
    heading: "Exercise 3: Classify Image"
    prompt: >
      Implement classify_image(img_b64, labels, describe_fn=None) -> str.
      Build a prompt asking the model to classify the image into one of the
      given labels. Call describe_image to get the response. Parse the
      response to find which label appears; fall back to labels[0] if none
      found. All checks use a mock that returns one of the labels.
    hint: >
      Build a prompt like: "Classify this image into one of: 'cat', 'dog'.
      Reply with only the category name." Call describe_image with that
      prompt and your describe_fn. Search response.lower() for each label.
    narration: >
      Zero-shot image classification is a powerful technique. Instead of
      training a classifier on thousands of labelled examples, you just
      describe the categories in the prompt. The vision LLM applies its
      broad visual knowledge to pick the most appropriate category.

  - type: summary
    heading: "Lesson 3 Summary"
    bullets:
      - "Ollama vision models: llava, llava-phi3, llama3.2-vision"
      - "images key in message dict: list of base64 strings"
      - "Response unchanged: resp['message']['content']"
      - "Multi-turn: include images only where new visual content is introduced"
      - "Zero-shot classification: labels in the prompt, no training data"
    narration: >
      The API is clear. Next lesson: the four main vision analysis patterns —
      describe, OCR, classify, and structured extraction.
"""

_LESSON_04 = """\
day: "067"
lesson: 4
title: "Vision Analysis Patterns"
slides:
  - type: title
    heading: "Vision Analysis Patterns"
    subheading: "Describe, OCR, classify, extract — four prompt templates"
    narration: >
      Vision LLMs are general purpose, but your prompts determine the output.
      Four patterns cover most real-world use cases: description, OCR,
      classification, and structured extraction. Each has its own prompt
      strategy.

  - type: concept
    label: "Four patterns"
    heading: "The Four Core Vision Analysis Patterns"
    body: >
      Each pattern maps to a prompt strategy that reliably elicits the
      expected output shape from a vision LLM.
    bullets:
      - "Describe: open-ended caption — 'Describe this image in 2-3 sentences.'"
      - "OCR: text extraction — 'Extract all visible text exactly as it appears.'"
      - "Classify: constrained choice — 'Reply with only one of: cat, dog, other.'"
      - "Extract (Day 69): schema-guided — 'Output JSON with keys: name, price, ...'"
    narration: >
      Description uses an open-ended prompt with a length constraint — two to
      three sentences keeps it focused without being too terse. OCR needs the
      word "exactly" and "as it appears" to stop the model from paraphrasing
      or correcting spelling. Classification uses a hard constraint — reply
      with only the category name — to prevent verbose responses that are hard
      to parse. Structured extraction combines a schema with explicit JSON
      instruction; that is Day 69.

  - type: how_it_works
    label: "OCR prompting"
    heading: "OCR via Vision LLM"
    body: >
      Vision LLMs can read text in images when prompted correctly. They work
      best on clean, high-contrast text but can handle varied fonts and angles.
    narration: >
      OCR via vision LLM is not as precise as dedicated OCR tools like
      Tesseract for highly stylised or dense document text, but it handles
      context better — it understands that "Qty 2" on a receipt means
      quantity, not a word starting with Q. The key prompt instruction is to
      extract text "exactly as it appears" — without that constraint, the
      model might correct typos, expand abbreviations, or reformat numbers.
      In Day 68 you will use pytesseract for traditional OCR and compare the
      two approaches.

  - type: code
    label: "Analysis patterns"
    heading: "Four Prompt Templates"
    code: |
      _PROMPTS = {
          'describe': 'Describe this image in 2-3 sentences.',
          'text':     ('Extract all visible text from this image exactly '
                       'as it appears. If there is no text, reply with '
                       'an empty string.'),
          'colors':   'List the 3 dominant colors in this image.',
          'objects':  'List the main objects visible in this image.',
      }

      def analyze(img_b64: str, task: str,
                  describe_fn=None) -> str:
          prompt = _PROMPTS.get(task)
          if prompt is None:
              raise ValueError(f"Unknown task: {task!r}")
          return describe_image(img_b64, prompt, describe_fn=describe_fn)
    narration: >
      A _PROMPTS dict keyed by task name is the cleanest pattern. New tasks
      are added by inserting one entry — the dispatch logic never changes.
      Each prompt is engineered for its specific output: the describe prompt
      has a length limit, the text prompt has the "exactly as it appears"
      constraint, and the classification prompt in the previous lesson has
      "reply with only the category name." These constraints are the
      difference between a prompt that works reliably and one that produces
      varied, hard-to-parse output.

  - type: code
    label: "Prompt engineering"
    heading: "Prompts that Produce Parseable Output"
    code: |
      # BAD: vague, produces verbose response
      bad_classify = "What is in this image?"

      # GOOD: constrained, produces one of the known labels
      def classify_prompt(labels: list[str]) -> str:
          label_list = ', '.join(f'"{l}"' for l in labels)
          return (
              f"Classify this image into exactly one of: {label_list}. "
              f"Reply with only the category name, nothing else."
          )

      # BAD: may paraphrase text
      bad_ocr = "What text is in this image?"

      # GOOD: exact extraction
      good_ocr = ("Extract all visible text exactly as it appears. "
                  "If there is no text, reply with an empty string.")
    narration: >
      The difference between a good and bad vision prompt is usually
      constraint. "What is in this image" could return a paragraph; "reply
      with only the category name" forces a single word you can compare to
      your labels list. "What text is in this image" allows paraphrasing;
      "exactly as it appears" forces literal transcription. Every prompt
      template you write should ask: what exact output shape do I need, and
      what constraints enforce it?

  - type: exercise
    heading: "Exercise 4: Extract Text from Image"
    prompt: >
      Implement extract_text_from_image(img_b64, describe_fn=None) -> str.
      Build an OCR prompt and call describe_image. The prompt should instruct
      the model to extract text "exactly as it appears" and to return an
      empty string if there is no text. The check captures the prompt
      to verify the OCR intent is present.
    hint: >
      Use a prompt containing both "text" (or "extract") and "exactly" to
      pass the prompt inspection check. Call describe_image with describe_fn.
    narration: >
      Extract text from an image is the simplest vision analysis wrapper —
      it calls describe_image with one specific OCR prompt. In Day 68 you
      will compare this approach with pytesseract for structured documents.
      Vision LLMs often perform better on noisy or context-rich images;
      Tesseract is more reliable for dense, well-structured documents.

  - type: summary
    heading: "Lesson 4 Summary"
    bullets:
      - "Describe: open prompt with length limit — '2-3 sentences'"
      - "OCR: 'exactly as it appears' + 'empty string if no text'"
      - "Classify: 'reply with only the category name' — parseable output"
      - "Structured extraction (Day 69): combine with Pydantic schema"
      - "_PROMPTS dict + task key = clean, extensible dispatch"
    narration: >
      Prompt engineering for vision follows the same rules as text: constrain
      the output shape, be explicit about edge cases, and test with a mock
      before running the real model. Next lesson: wiring all four patterns into
      a composable VisionAnalyzer.
"""

_LESSON_05 = """\
day: "067"
lesson: 5
title: "Building a Vision Pipeline"
slides:
  - type: title
    heading: "Building a Vision Pipeline"
    subheading: "VisionAnalyzer — encode once, query many"
    narration: >
      The final lesson puts everything together. You will build a
      VisionAnalyzer class that encodes an image once and runs multiple
      analyses on it efficiently — the same pattern used in production image
      pipelines.

  - type: concept
    label: "Encode once"
    heading: "Encode Once, Query Many Times"
    body: >
      Base64 encoding is a CPU-bound operation. For multiple analyses of the
      same image, encode once and reuse the base64 string for every query.
    narration: >
      In the analysis pipeline exercise, you encode the image once at the
      start and reuse the base64 string for every task. This avoids
      redundant encoding — if you run three analyses on a 1 megapixel image,
      you only call BytesIO and b64encode once. In production with large
      images or batch processing, this matters. It is also cleaner code:
      the encoding happens at the pipeline boundary, and the inner functions
      work with already-encoded strings.

  - type: how_it_works
    label: "VisionAnalyzer"
    heading: "The VisionAnalyzer Class"
    body: >
      A class that wraps the Ollama vision model, accepts a mock describe_fn
      for testing, and exposes describe, extract_text, classify, and analyze.
    narration: >
      The VisionAnalyzer class follows the same mock-injection pattern as
      the process_fn in Days 52 through 65. A single describe_fn parameter
      controls whether the class calls Ollama or uses a mock. The class's
      public methods — describe, extract_text, classify, analyze — all
      delegate to a private _call method that handles the mock-vs-real
      branching in one place. No duplicated if-else logic.

  - type: code
    label: "VisionAnalyzer"
    heading: "VisionAnalyzer Class Structure"
    code: |
      from vision_analyzer import VisionAnalyzer
      from PIL import Image

      # Production: calls Ollama llava
      va = VisionAnalyzer(model='llava')

      # Testing: no Ollama needed
      mock_fn = lambda b64, prompt: "A bright orange circle."
      va_test = VisionAnalyzer(describe_fn=mock_fn)

      img = Image.new('RGB', (200, 200), color=(255, 128, 0))

      # Single analysis
      desc = va_test.describe(img)
      text = va_test.extract_text(img)
      cat  = va_test.classify(img, ['circle', 'square', 'triangle'])

      # Multi-task: encode once, run multiple analyses
      results = va_test.analyze(img, tasks=['describe', 'objects'])
      print(results.keys())  # dict_keys(['describe', 'objects'])
    narration: >
      The mock function takes img_b64 and prompt and returns a string. That
      is the entire interface. In tests you pass a lambda; in production you
      let the default None trigger the Ollama path. The analyze method encodes
      the image once, then iterates the tasks list — no repeated encoding.
      This is a clean separation: encoding at the boundary, querying inside.

  - type: code
    label: "Error handling"
    heading: "Defensive VisionAnalyzer"
    code: |
      class VisionAnalyzer:
          def analyze(self, img, tasks=None):
              if tasks is None:
                  tasks = ['describe']
              img_b64 = image_to_base64(img)
              results = {}
              for task in tasks:
                  if task not in _PROMPTS:
                      raise ValueError(
                          f"Unknown task: {task!r}. "
                          f"Available: {list(_PROMPTS)}"
                      )
                  results[task] = self._call(img_b64, _PROMPTS[task])
              return results

      # Unknown task → clear ValueError with available options
      try:
          va_test.analyze(img, tasks=['describe', 'mood'])
      except ValueError as e:
          print(e)  # Unknown task: 'mood'. Available: ['describe', ...]
    narration: >
      Always validate task names before making the network call — fail fast
      with a clear error rather than sending a malformed request and getting
      an opaque HTTP 400 back. The ValueError message includes the available
      options, so the caller immediately knows what to change. This defensive
      pattern applies to any dict-dispatch system.

  - type: exercise
    heading: "Exercise 5: Analyze Image Pipeline"
    prompt: >
      Implement analyze_image_pipeline(img, tasks, describe_fn=None) -> dict.
      Encode the image to base64 once at the start. For each task in tasks,
      look up the prompt in a _TASKS_PROMPTS dict, call describe_image, and
      collect results. Raise ValueError for unknown tasks. Return a dict
      mapping task name to result string.
    hint: >
      _TASKS_PROMPTS is provided in the given cell. img_b64 = image_to_base64(img).
      For each task: if task not in _TASKS_PROMPTS, raise ValueError.
      Otherwise call describe_image(img_b64, prompt, describe_fn).
    narration: >
      The pipeline exercise ties Day 67 together: encode once, dispatch on
      task name, query the model, collect results. The dict output is easy
      to serialize to JSON, log, or pass to a downstream function that
      combines the analyses into a structured summary.

  - type: summary
    heading: "Lesson 5 Summary — Day 67 Complete"
    bullets:
      - "Encode once per image, reuse base64 string across multiple calls"
      - "VisionAnalyzer: mock-injection pattern; describe_fn=None → Ollama"
      - "Four patterns: describe, OCR, classify, extract (Day 69)"
      - "Validate task names before calling the model — fail fast"
      - "Tomorrow (Day 68): pytesseract OCR + document AI"
    narration: >
      Day 67 is complete. You can encode PIL Images for a vision LLM, call
      Ollama llava, and apply four analysis patterns. The encode-once pattern
      and mock-injection architecture will appear in Days 69, 71, and 76.
      Tomorrow: traditional OCR with pytesseract — a complement to vision
      LLMs for structured text extraction from documents.
"""

for i, content in enumerate([_LESSON_01, _LESSON_02, _LESSON_03,
                               _LESSON_04, _LESSON_05], start=1):
    (OUT / "lessons" / f"day_{DAY}_lesson_0{i}.yaml").write_text(content)

# ── helper source shared across exercises ─────────────────────────────────────
_HELPER_SRC = """\
import io
import base64
from PIL import Image

def image_to_base64(img: Image.Image, format: str = 'PNG') -> str:
    buf = io.BytesIO()
    out = img
    if format.upper() in ('JPEG', 'JPG') and img.mode in ('RGBA', 'P'):
        out = img.convert('RGB')
    out.save(buf, format=format)
    return base64.b64encode(buf.getvalue()).decode()
"""

# ── EXERCISE 1 — image_to_base64 ──────────────────────────────────────────────
_EX1_GIVEN = """\
import io
import base64
from PIL import Image

_rgb  = Image.new('RGB',  (100, 80), color=(255, 0, 0))
_rgba = Image.new('RGBA', (50, 50),  color=(0, 200, 100, 128))
"""

_EX1_STUB = """\
def image_to_base64(img: Image.Image, format: str = 'PNG') -> str:
    \"\"\"Encode a PIL Image as a base64 string.

    For JPEG format, automatically converts RGBA and P mode images to RGB.

    Args:
        img:    PIL Image to encode
        format: image format ('PNG', 'JPEG', etc.)
    Returns:
        Base64-encoded string — no data URI prefix (just the raw base64 data)
    \"\"\"
    raise NotImplementedError
"""

_EX1_SOLUTION = """\
def image_to_base64(img: Image.Image, format: str = 'PNG') -> str:
    buf = io.BytesIO()
    out = img
    if format.upper() in ('JPEG', 'JPG') and img.mode in ('RGBA', 'P'):
        out = img.convert('RGB')
    out.save(buf, format=format)
    return base64.b64encode(buf.getvalue()).decode()
"""

_EX1_CHECKS = """\
score, total = 0, 5
try:
    result = image_to_base64(_rgb)
    assert isinstance(result, str), f"Expected str, got {type(result)}"
    score += 1; print("\\u2705 returns a string")

    assert len(result) > 0, "base64 string should not be empty"
    score += 1; print("\\u2705 non-empty base64 string")

    # Decode and verify it is a valid PNG
    raw = base64.b64decode(result)
    assert raw[:4] == b'\\x89PNG', f"Not PNG: {raw[:4]!r}"
    score += 1; print("\\u2705 decoded bytes are valid PNG")

    # JPEG encoding works
    jpeg_b64 = image_to_base64(_rgb, 'JPEG')
    assert isinstance(jpeg_b64, str) and len(jpeg_b64) > 0
    jpeg_raw = base64.b64decode(jpeg_b64)
    assert jpeg_raw[:2] == b'\\xff\\xd8', f"Not JPEG: {jpeg_raw[:2]!r}"
    score += 1; print("\\u2705 JPEG encoding produces valid JPEG bytes")

    # RGBA → JPEG auto-converts without error
    rgba_b64 = image_to_base64(_rgba, 'JPEG')
    assert isinstance(rgba_b64, str) and len(rgba_b64) > 0
    score += 1; print("\\u2705 RGBA image encodes to JPEG without error")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX1 = nb([
    md("# Day 067 — Exercise 1: Image to Base64\n\n"
       "**What you'll build:** `image_to_base64(img, format)` — encode a PIL "
       "Image as a base64 string ready for the Ollama vision API.\n\n"
       "**Why it matters:** Every vision LLM API accepts images as base64 strings "
       "embedded in JSON. This function is the encoding bridge between Pillow and "
       "Ollama (and any other vision API). You will reuse it in every subsequent "
       "exercise today and in Days 69, 71, and 76."),
    code(_EX1_GIVEN),
    md("## Task\n\nImplement `image_to_base64(img, format='PNG') -> str`:\n\n"
       "1. Create `io.BytesIO()`\n"
       "2. If `format` is `'JPEG'`/`'JPG'` and `img.mode` is `'RGBA'` or `'P'`, "
       "convert to `'RGB'` first\n"
       "3. Call `out.save(buf, format=format)`\n"
       "4. Return `base64.b64encode(buf.getvalue()).decode()`"),
    md("## Your Implementation"),
    code(_EX1_STUB),
    code(_EX1_SOLUTION),
    md("## Automated checks"),
    code(_EX1_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX1_SOLUTION + "```\n\n"
       "**Why `buf.getvalue()` not `buf.read()`?** `getvalue()` returns the entire "
       "buffer contents regardless of the current position — no `seek(0)` needed. "
       "`buf.read()` reads from the current position; after a write the position "
       "is at the end, so `read()` would return empty bytes without a preceding "
       "`seek(0)`. `getvalue()` is the correct choice when you only need the full "
       "byte string.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_01.ipynb", EX1)

# ── EXERCISE 2 — describe_image ───────────────────────────────────────────────
_EX2_GIVEN = _HELPER_SRC + """
_test_img = Image.new('RGB', (100, 100), color=(255, 0, 0))
_test_b64 = image_to_base64(_test_img)
"""

_EX2_STUB = """\
def describe_image(img_b64: str, prompt: str = 'Describe this image.',
                   describe_fn=None) -> str:
    \"\"\"Send an image to a vision LLM and return its text response.

    Args:
        img_b64:     base64-encoded image string
        prompt:      question or instruction for the model
        describe_fn: optional callable(img_b64: str, prompt: str) -> str
                     If provided, calls this instead of Ollama (for testing).
                     If None, calls ollama.chat(model='llava', ...).
    Returns:
        Model response text
    \"\"\"
    raise NotImplementedError
"""

_EX2_SOLUTION = """\
def describe_image(img_b64: str, prompt: str = 'Describe this image.',
                   describe_fn=None) -> str:
    if describe_fn is not None:
        return describe_fn(img_b64, prompt)
    import ollama
    resp = ollama.chat(
        model='llava',
        messages=[{'role': 'user', 'content': prompt, 'images': [img_b64]}]
    )
    return resp['message']['content']
"""

_EX2_CHECKS = """\
score, total = 0, 5
try:
    captured = {}
    def _mock(b64, p):
        captured['b64']    = b64
        captured['prompt'] = p
        return f"Mock: saw image of length {len(b64)} with prompt '{p}'"

    result = describe_image(_test_b64, 'What colour is this?', describe_fn=_mock)
    assert isinstance(result, str), f"Expected str, got {type(result)}"
    score += 1; print("\\u2705 returns a string")

    assert len(result) > 0, "result should not be empty"
    score += 1; print("\\u2705 non-empty result")

    assert captured.get('b64') == _test_b64, (
        "describe_fn should receive the img_b64 argument")
    score += 1; print("\\u2705 mock receives the correct img_b64")

    assert captured.get('prompt') == 'What colour is this?', (
        f"Expected prompt 'What colour is this?', got {captured.get('prompt')!r}")
    score += 1; print("\\u2705 mock receives the correct prompt")

    # Default prompt
    result2 = describe_image(_test_b64, describe_fn=lambda b, p: p)
    assert result2 == 'Describe this image.', (
        f"Default prompt mismatch: {result2!r}")
    score += 1; print("\\u2705 default prompt is 'Describe this image.'")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX2 = nb([
    md("# Day 067 — Exercise 2: Describe Image\n\n"
       "**What you'll build:** `describe_image(img_b64, prompt, describe_fn=None)` "
       "— the core vision LLM call, with mock injection for testing.\n\n"
       "**Why it matters:** This is the foundation all other exercises build on. "
       "The `describe_fn` injection pattern makes every downstream function "
       "testable without a running Ollama server — the same technique used with "
       "`process_fn` in Section 4."),
    code(_EX2_GIVEN),
    md("## Task\n\nImplement `describe_image(img_b64, prompt, describe_fn=None) -> str`:\n\n"
       "- If `describe_fn is not None`: call `describe_fn(img_b64, prompt)` and return\n"
       "- Otherwise: call `ollama.chat(model='llava', messages=[{...}])` with the "
       "`images` key set to `[img_b64]`\n"
       "- Return `resp['message']['content']`\n\n"
       "All checks use a mock `describe_fn` — no Ollama server required."),
    md("## Your Implementation"),
    code(_EX2_STUB),
    code(_EX2_SOLUTION),
    md("## Automated checks"),
    code(_EX2_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX2_SOLUTION + "```\n\n"
       "**The mock-injection pattern:** checking `describe_fn is not None` first "
       "means any callable can override the Ollama path — a lambda, a class method, "
       "or a pre-recorded fixture. The production path (None → Ollama) is never "
       "reached in tests. This is identical to `process_fn` in Section 4 and "
       "will appear again in Days 69, 71, and 76.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_02.ipynb", EX2)

# ── EXERCISE 3 — classify_image ───────────────────────────────────────────────
_EX3_GIVEN = _HELPER_SRC + """
import ollama  # imported so the stub compiles; not called in checks

def describe_image(img_b64: str, prompt: str = 'Describe this image.',
                   describe_fn=None) -> str:
    if describe_fn is not None:
        return describe_fn(img_b64, prompt)
    resp = ollama.chat(
        model='llava',
        messages=[{'role': 'user', 'content': prompt, 'images': [img_b64]}]
    )
    return resp['message']['content']

_test_img = Image.new('RGB', (100, 100), color=(50, 200, 50))
_test_b64 = image_to_base64(_test_img)
"""

_EX3_STUB = """\
def classify_image(img_b64: str, labels: list,
                   describe_fn=None) -> str:
    \"\"\"Classify an image into one of the given labels using a vision LLM.

    Builds a classification prompt that asks the model to pick one label.
    Parses the response to find which label appears (case-insensitive).
    Falls back to labels[0] if no label found in the response.

    Args:
        img_b64:     base64-encoded image string
        labels:      list of category strings, e.g. ['cat', 'dog', 'other']
        describe_fn: callable(img_b64, prompt) -> str for testing
    Returns:
        One of the strings from labels
    \"\"\"
    raise NotImplementedError
"""

_EX3_SOLUTION = """\
def classify_image(img_b64: str, labels: list,
                   describe_fn=None) -> str:
    label_list = ', '.join(f'\"{l}\"' for l in labels)
    prompt = (
        f'Classify this image into exactly one of these categories: '
        f'{label_list}. Reply with only the category name, nothing else.'
    )
    response = describe_image(img_b64, prompt, describe_fn=describe_fn)
    resp_lower = response.lower()
    for label in labels:
        if label.lower() in resp_lower:
            return label
    return labels[0]
"""

_EX3_CHECKS = """\
score, total = 0, 5
try:
    labels = ['red', 'green', 'blue']

    # Mock returns 'green' — should match the second label
    result = classify_image(_test_b64, labels,
                            describe_fn=lambda b, p: 'green')
    assert isinstance(result, str), f"Expected str, got {type(result)}"
    score += 1; print("\\u2705 returns a string")

    assert result == 'green', f"Expected 'green', got {result!r}"
    score += 1; print("\\u2705 correctly identifies 'green' from mock response")

    # Labels are passed to the mock's prompt
    captured_prompt = {}
    def _mock_capture(b, p):
        captured_prompt['p'] = p
        return 'red'
    classify_image(_test_b64, labels, describe_fn=_mock_capture)
    assert all(l in captured_prompt['p'] for l in labels), (
        f"All labels should appear in the prompt: {captured_prompt['p']!r}")
    score += 1; print("\\u2705 all labels appear in the classification prompt")

    # Fallback to labels[0] when no label found in response
    fallback = classify_image(_test_b64, labels,
                               describe_fn=lambda b, p: 'I cannot determine')
    assert fallback == labels[0], f"Expected fallback {labels[0]!r}, got {fallback!r}"
    score += 1; print("\\u2705 falls back to labels[0] when no match found")

    # Works with 2-label binary classification
    two = classify_image(_test_b64, ['indoor', 'outdoor'],
                          describe_fn=lambda b, p: 'outdoor')
    assert two == 'outdoor'
    score += 1; print("\\u2705 2-label classification works")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX3 = nb([
    md("# Day 067 — Exercise 3: Classify Image\n\n"
       "**What you'll build:** `classify_image(img_b64, labels, describe_fn=None)` "
       "— zero-shot image classification by prompting a vision LLM.\n\n"
       "**Why it matters:** Zero-shot classification needs no labelled training data. "
       "You describe the categories in the prompt and the model applies its visual "
       "knowledge. This pattern is used for product categorisation, content moderation, "
       "and medical image triage."),
    code(_EX3_GIVEN),
    md("## Task\n\nImplement `classify_image(img_b64, labels, describe_fn=None) -> str`:\n\n"
       "1. Build a prompt listing all labels and asking for exactly one\n"
       "2. Call `describe_image(img_b64, prompt, describe_fn=describe_fn)`\n"
       "3. Search `response.lower()` for each `label.lower()` — return first match\n"
       "4. Fall back to `labels[0]` if no label found in the response"),
    md("## Your Implementation"),
    code(_EX3_STUB),
    code(_EX3_SOLUTION),
    md("## Automated checks"),
    code(_EX3_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX3_SOLUTION + "```\n\n"
       "**Why case-insensitive matching and a fallback?** Vision LLMs may return "
       "\"Green\" or \"GREEN\" rather than the exact string you provided. The "
       "`.lower()` comparison handles this. The `labels[0]` fallback ensures the "
       "function always returns a valid label — the caller can then check if the "
       "confidence is meaningful (e.g., flag items where the fallback was used).\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_03.ipynb", EX3)

# ── EXERCISE 4 — extract_text_from_image ─────────────────────────────────────
_EX4_GIVEN = _HELPER_SRC + """
import ollama

def describe_image(img_b64: str, prompt: str = 'Describe this image.',
                   describe_fn=None) -> str:
    if describe_fn is not None:
        return describe_fn(img_b64, prompt)
    resp = ollama.chat(
        model='llava',
        messages=[{'role': 'user', 'content': prompt, 'images': [img_b64]}]
    )
    return resp['message']['content']

from PIL import ImageDraw
_text_img = Image.new('RGB', (200, 60), color='white')
_draw = ImageDraw.Draw(_text_img)
_draw.text((10, 15), 'Hello World', fill='black')
_text_b64 = image_to_base64(_text_img)
"""

_EX4_STUB = """\
def extract_text_from_image(img_b64: str, describe_fn=None) -> str:
    \"\"\"Extract visible text from an image using a vision LLM.

    Uses an OCR-focused prompt that instructs the model to transcribe
    text exactly as it appears, without paraphrasing or correcting.

    Args:
        img_b64:     base64-encoded image string
        describe_fn: callable(img_b64, prompt) -> str for testing
    Returns:
        Extracted text string (may be empty if no text in image)
    \"\"\"
    raise NotImplementedError
"""

_EX4_SOLUTION = """\
def extract_text_from_image(img_b64: str, describe_fn=None) -> str:
    prompt = (
        'Extract all visible text from this image exactly as it appears. '
        'If there is no text, reply with an empty string.'
    )
    return describe_image(img_b64, prompt, describe_fn=describe_fn)
"""

_EX4_CHECKS = """\
score, total = 0, 5
try:
    result = extract_text_from_image(_text_b64,
                                      describe_fn=lambda b, p: 'Hello World')
    assert isinstance(result, str), f"Expected str, got {type(result)}"
    score += 1; print("\\u2705 returns a string")

    assert result == 'Hello World', f"Expected 'Hello World', got {result!r}"
    score += 1; print("\\u2705 returns the mock's response text")

    # Prompt must contain OCR intent keywords
    captured = {}
    def _mock_capture(b, p):
        captured['prompt'] = p
        return ''
    extract_text_from_image(_text_b64, describe_fn=_mock_capture)
    prompt_lower = captured.get('prompt', '').lower()
    assert 'text' in prompt_lower or 'extract' in prompt_lower, (
        f"Prompt should mention 'text' or 'extract': {captured.get('prompt')!r}")
    score += 1; print("\\u2705 prompt contains OCR intent keyword")

    # Prompt contains 'exactly' to enforce literal transcription
    assert 'exactly' in prompt_lower or 'literal' in prompt_lower or 'appears' in prompt_lower, (
        f"Prompt should contain 'exactly' or 'appears': {captured.get('prompt')!r}")
    score += 1; print("\\u2705 prompt enforces exact transcription")

    # Empty string returned for image with no text
    empty = extract_text_from_image(_text_b64,
                                     describe_fn=lambda b, p: '')
    assert isinstance(empty, str), "Should return empty string for no-text image"
    score += 1; print("\\u2705 handles empty-text response gracefully")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX4 = nb([
    md("# Day 067 — Exercise 4: Extract Text from Image\n\n"
       "**What you'll build:** `extract_text_from_image(img_b64, describe_fn=None)` "
       "— OCR via a vision LLM using a carefully crafted prompt.\n\n"
       "**Why it matters:** Vision LLMs read text in context — they understand that "
       "\"Qty\" on a receipt means quantity. The key is the prompt: "
       "\"exactly as it appears\" stops the model from paraphrasing. "
       "Tomorrow (Day 68) you will compare this with pytesseract for structured documents."),
    code(_EX4_GIVEN),
    md("## Task\n\nImplement `extract_text_from_image(img_b64, describe_fn=None) -> str`:\n\n"
       "- Build an OCR prompt containing `'exactly'` and `'text'`\n"
       "- The prompt should handle the no-text case (instruct the model to return "
       "an empty string)\n"
       "- Call `describe_image(img_b64, prompt, describe_fn=describe_fn)`\n"
       "- Return the result directly"),
    md("## Your Implementation"),
    code(_EX4_STUB),
    code(_EX4_SOLUTION),
    md("## Automated checks"),
    code(_EX4_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX4_SOLUTION + "```\n\n"
       "**Why `'exactly as it appears'`?** Without this constraint, vision LLMs "
       "often paraphrase — they might correct a typo, expand an abbreviation, "
       "or reformat a date. For OCR you want the literal characters. "
       "Telling the model to return an empty string for no-text images prevents "
       "responses like 'I do not see any text in this image.' which would require "
       "post-processing to detect.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_04.ipynb", EX4)

# ── EXERCISE 5 — analyze_image_pipeline ──────────────────────────────────────
_EX5_GIVEN = _HELPER_SRC + """
import ollama

_TASKS_PROMPTS = {
    'describe': 'Describe this image in 2-3 sentences.',
    'text':     ('Extract all visible text from this image exactly as it '
                 'appears. If there is no text, reply with an empty string.'),
    'colors':   'List the 3 dominant colors visible in this image.',
    'objects':  'List the main objects visible in this image.',
}

def describe_image(img_b64: str, prompt: str = 'Describe this image.',
                   describe_fn=None) -> str:
    if describe_fn is not None:
        return describe_fn(img_b64, prompt)
    resp = ollama.chat(
        model='llava',
        messages=[{'role': 'user', 'content': prompt, 'images': [img_b64]}]
    )
    return resp['message']['content']

_test_img = Image.new('RGB', (150, 150), color=(0, 100, 200))
"""

_EX5_STUB = """\
def analyze_image_pipeline(img, tasks: list,
                            describe_fn=None) -> dict:
    \"\"\"Run multiple vision analyses on a single image.

    Encodes the image once, then runs each task from _TASKS_PROMPTS.

    Args:
        img:         PIL Image to analyze
        tasks:       list of task names — keys from _TASKS_PROMPTS
        describe_fn: callable(img_b64, prompt) -> str for testing
    Returns:
        dict mapping each task name to its result string
    Raises:
        ValueError for any unknown task name
    \"\"\"
    raise NotImplementedError
"""

_EX5_SOLUTION = """\
def analyze_image_pipeline(img, tasks: list,
                            describe_fn=None) -> dict:
    img_b64 = image_to_base64(img)
    results = {}
    for task in tasks:
        if task not in _TASKS_PROMPTS:
            raise ValueError(
                f'Unknown task: {task!r}. Available: {list(_TASKS_PROMPTS)}'
            )
        results[task] = describe_image(
            img_b64, _TASKS_PROMPTS[task], describe_fn=describe_fn
        )
    return results
"""

_EX5_CHECKS = """\
score, total = 0, 5
try:
    _mock = lambda b, p: f'result for: {p[:20]}'

    # Returns dict
    result = analyze_image_pipeline(_test_img, ['describe'], describe_fn=_mock)
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    score += 1; print("\\u2705 returns a dict")

    # Keys match requested tasks
    assert set(result.keys()) == {'describe'}, (
        f"Expected keys {{'describe'}}, got {set(result.keys())}")
    score += 1; print("\\u2705 dict keys match the requested tasks")

    # Multi-task
    multi = analyze_image_pipeline(_test_img, ['describe', 'colors'],
                                    describe_fn=_mock)
    assert set(multi.keys()) == {'describe', 'colors'}
    assert all(isinstance(v, str) for v in multi.values())
    score += 1; print("\\u2705 multi-task pipeline returns all requested tasks")

    # Empty tasks list → empty dict
    empty = analyze_image_pipeline(_test_img, [], describe_fn=_mock)
    assert empty == {}, f"Empty tasks should return empty dict, got {empty}"
    score += 1; print("\\u2705 empty tasks list returns empty dict")

    # Unknown task raises ValueError
    raised = False
    try:
        analyze_image_pipeline(_test_img, ['describe', 'mood'], describe_fn=_mock)
    except ValueError:
        raised = True
    assert raised, "Unknown task should raise ValueError"
    score += 1; print("\\u2705 unknown task raises ValueError")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX5 = nb([
    md("# Day 067 — Exercise 5: Analyze Image Pipeline\n\n"
       "**What you'll build:** `analyze_image_pipeline(img, tasks, describe_fn=None)` "
       "— encode once, run multiple vision analyses, return a results dict.\n\n"
       "**Why it matters:** Encoding is CPU-bound — doing it once for multiple "
       "analyses is more efficient than re-encoding per task. The dict output "
       "serialises cleanly to JSON, logs easily, and is straightforward to pass "
       "downstream for structured processing."),
    code(_EX5_GIVEN),
    md("## Task\n\nImplement `analyze_image_pipeline(img, tasks, describe_fn=None) -> dict`:\n\n"
       "1. Encode the image **once**: `img_b64 = image_to_base64(img)`\n"
       "2. For each task in `tasks`:\n"
       "   - Raise `ValueError` if the task is not in `_TASKS_PROMPTS`\n"
       "   - Call `describe_image(img_b64, _TASKS_PROMPTS[task], describe_fn=describe_fn)`\n"
       "   - Store the result in `results[task]`\n"
       "3. Return the `results` dict"),
    md("## Your Implementation"),
    code(_EX5_STUB),
    code(_EX5_SOLUTION),
    md("## Automated checks"),
    code(_EX5_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX5_SOLUTION + "```\n\n"
       "**Why encode once?** PIL save + base64 encode touches CPU for every byte of "
       "the image. For a 1 megapixel image (~3 MB uncompressed), encoding twice "
       "doubles that work. More importantly, `image_to_base64` called inside the "
       "loop would produce the same base64 every time — wasted work. Encode at "
       "the pipeline boundary, pass the string inward.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_05.ipynb", EX5)

# ── PROJECT NOTEBOOK ──────────────────────────────────────────────────────────
PROJECT = nb([
    md("# Day 067 — Project: Vision Analyzer\n\n"
       "## What You're Building\n\n"
       "`vision_analyzer.py` — a `VisionAnalyzer` class backed by Ollama llava.\n\n"
       "**Deliverable:** A class that accepts any PIL Image and returns text "
       "descriptions, extracted text, zero-shot classifications, and multi-task "
       "analysis results. Works offline with a `describe_fn` mock; works with a "
       "real image when Ollama is running.\n\n"
       "## Setup\n\n"
       "```bash\n"
       "# Pull the vision model (one-time)\n"
       "ollama pull llava\n"
       "# or: ollama pull llama3.2-vision\n"
       "```\n\n"
       "## Design\n\n"
       "```\n"
       "VisionAnalyzer\n"
       "  .__init__(model='llava', describe_fn=None)\n"
       "  .describe(img, prompt=...)     → str\n"
       "  .extract_text(img)             → str\n"
       "  .classify(img, labels)         → str  (one of labels)\n"
       "  .analyze(img, tasks=['...'])   → dict  (task → result)\n"
       "```\n\n"
       "## Usage (with real Ollama)\n\n"
       "```python\n"
       "from vision_analyzer import VisionAnalyzer\n"
       "from PIL import Image\n\n"
       "va = VisionAnalyzer(model='llava')\n"
       "img = Image.open('your_photo.jpg')\n"
       "print(va.describe(img))\n"
       "print(va.classify(img, ['indoor', 'outdoor', 'food']))\n"
       "print(va.analyze(img, tasks=['describe', 'objects']))\n"
       "```"),
    code("# Your implementation here\n"
         "# Build VisionAnalyzer and write it to vision_analyzer.py\n"),
])
save(OUT / "project" / "project.ipynb", PROJECT)

# ── SOLUTION NOTEBOOK ─────────────────────────────────────────────────────────
_SOL_CELL1 = (
    f"_ANALYZER_SRC = {repr(_ANALYZER_SRC)}\n"
    "from pathlib import Path\n"
    "Path('vision_analyzer.py').write_text(_ANALYZER_SRC, encoding='utf-8')\n"
    "print('vision_analyzer.py written.')"
)

_SOL_CELL2 = """\
from PIL import Image
import base64, io
from vision_analyzer import VisionAnalyzer, image_to_base64

# Mock: no Ollama required
_mock_fn = lambda b64, prompt: f"[mock] {prompt[:40]}"

va = VisionAnalyzer(describe_fn=_mock_fn)
img = Image.new('RGB', (200, 150), color=(100, 50, 200))

# 1. describe
desc = va.describe(img)
assert isinstance(desc, str) and len(desc) > 0
print("\\u2705 describe returns non-empty string")

# 2. describe with custom prompt
custom = va.describe(img, prompt='How many colours?')
assert 'How many colours?' in custom
print("\\u2705 custom prompt passed to mock")

# 3. extract_text
text = va.extract_text(img)
assert isinstance(text, str)
print("\\u2705 extract_text returns string")

# 4. classify — mock returns the first label's name
labels = ['purple', 'red', 'blue']
cat = va.classify(img, labels)
assert isinstance(cat, str) and cat in labels
print(f"\\u2705 classify returns one of the labels: {cat!r}")

# 5. analyze single task
results = va.analyze(img, tasks=['describe'])
assert isinstance(results, dict) and 'describe' in results
print("\\u2705 analyze single task returns dict with 'describe' key")

# 6. analyze multi-task
multi = va.analyze(img, tasks=['describe', 'colors'])
assert set(multi.keys()) == {'describe', 'colors'}
print("\\u2705 analyze multi-task returns all requested keys")

# 7. analyze unknown task raises ValueError
raised = False
try:
    va.analyze(img, tasks=['teleport'])
except ValueError:
    raised = True
assert raised
print("\\u2705 unknown task raises ValueError")

# 8. image_to_base64 produces valid PNG base64
b64 = image_to_base64(img)
raw = base64.b64decode(b64)
assert raw[:4] == b'\\x89PNG'
print("\\u2705 image_to_base64 produces valid PNG base64")

print("\\nVision LLM complete!")
"""

SOLUTION = nb([
    md("# Day 067 — Solution: Vision Analyzer"),
    code(_SOL_CELL1),
    code(_SOL_CELL2),
])
save(OUT / "project" / "solution" / "solution.ipynb", SOLUTION)
(OUT / "project" / "solution" / "vision_analyzer.py").write_text(_ANALYZER_SRC)

print(f"Day {DAY} notebooks written to {OUT}")
print("  lessons/    day_067_lesson_01.yaml – lesson_05.yaml")
print("  exercises/  exercise_01 – exercise_05")
print("  project/    project.ipynb")
print("  project/solution/  solution.ipynb + vision_analyzer.py")
