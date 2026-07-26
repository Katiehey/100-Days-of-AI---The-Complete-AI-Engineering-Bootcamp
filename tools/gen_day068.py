#!/usr/bin/env python3
"""gen_day068.py — generate Day 068: OCR & Document AI."""
from pathlib import Path
import json

ROOT    = Path(__file__).parent.parent
DAY     = "068"
SECTION = "05_vision_multimodal"
OUT     = ROOT / SECTION / f"day_{DAY}"

(OUT / "exercises").mkdir(parents=True, exist_ok=True)
(OUT / "lessons").mkdir(parents=True, exist_ok=True)
(OUT / "project" / "solution").mkdir(parents=True, exist_ok=True)

# ── deliverable: document_reader.py ──────────────────────────────────────────
_READER_SRC = '''\
"""document_reader.py — Day 068: OCR & Document AI.

Extracts text from images (via Tesseract OCR) and PDFs (via pypdf).
Also parses numeric values from OCR output using regex.

Setup:
    brew install tesseract        # macOS — installs the OCR engine
    pip install pytesseract pypdf  # Python bindings

Usage:
    from document_reader import DocumentReader
    from PIL import Image

    dr = DocumentReader()

    # Read an image
    img = Image.open("receipt.png")
    result = dr.read_image(img)
    print(result["text"])
    print(result["numbers"])

    # Read a PDF
    with open("invoice.pdf", "rb") as f:
        result = dr.read_pdf(f.read())
    for page in result["pages"]:
        print(page["text"])

Testing without Tesseract:
    mock = lambda img: "Hello World\\n$12.99"
    dr = DocumentReader(ocr_fn=mock)
"""
import re
import io
from PIL import Image, ImageEnhance, ImageFilter


def preprocess_for_ocr(img: Image.Image) -> Image.Image:
    """Improve image quality for OCR.

    Converts to grayscale, boosts contrast, and upscales small images.
    These steps significantly improve Tesseract accuracy on low-res or
    low-contrast scans.
    """
    out = img.convert("L")
    out = ImageEnhance.Contrast(out).enhance(2.0)
    w, h = out.size
    if w < 1000:
        scale = 1000 / w
        out = out.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
    return out


def ocr_image(img: Image.Image, ocr_fn=None,
              lang: str = "eng", config: str = "") -> str:
    """Extract text from a PIL Image using Tesseract OCR.

    Args:
        img:    PIL Image to OCR
        ocr_fn: callable(img) -> str for testing (bypasses Tesseract)
        lang:   Tesseract language code (default "eng")
        config: extra Tesseract config flags (e.g. "--psm 6")
    Returns:
        Extracted text string (may be empty)
    """
    if ocr_fn is not None:
        return ocr_fn(img)
    import pytesseract
    return pytesseract.image_to_string(img, lang=lang, config=config)


def extract_numbers(text: str) -> list:
    """Parse all numeric values from a text string.

    Handles integers, decimals, and currency amounts.
    Removes commas from numbers like "1,234.56" before parsing.

    Returns:
        Sorted list of float values found in text
    """
    pattern = r"\\b\\d{1,3}(?:,\\d{3})*(?:\\.\\d+)?|\\b\\d+(?:\\.\\d+)?\\b"
    raw = re.findall(pattern, text)
    result = []
    for s in raw:
        try:
            result.append(float(s.replace(",", "")))
        except ValueError:
            pass
    return sorted(result)


def extract_pdf_text(pdf_bytes: bytes) -> list:
    """Extract text from each page of a PDF.

    Uses pypdf for text-based PDFs. Returns an empty string for image-only
    (scanned) pages — use ocr_image on those pages instead.

    Args:
        pdf_bytes: raw PDF bytes (e.g. from open("f.pdf","rb").read())
    Returns:
        List of dicts: [{page: int (1-based), text: str, chars: int}]
    """
    import pypdf
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append({"page": i, "text": text, "chars": len(text)})
    return pages


class DocumentReader:
    """OCR and PDF text extractor.

    Pass ocr_fn for testing without a Tesseract installation::

        mock = lambda img: "Extracted text"
        dr = DocumentReader(ocr_fn=mock)
    """

    def __init__(self, ocr_fn=None) -> None:
        self._ocr_fn = ocr_fn

    def read_image(self, img: Image.Image,
                   preprocess: bool = True) -> dict:
        """OCR a PIL Image and return structured result.

        Args:
            img:        PIL Image to read
            preprocess: if True, apply grayscale + contrast + scale first
        Returns:
            {text: str, numbers: list[float], chars: int, preprocess: bool}
        """
        work = preprocess_for_ocr(img) if preprocess else img
        text = ocr_image(work, ocr_fn=self._ocr_fn)
        return {
            "text":       text,
            "numbers":    extract_numbers(text),
            "chars":      len(text),
            "preprocess": preprocess,
        }

    def read_pdf(self, pdf_bytes: bytes) -> dict:
        """Extract text from all pages of a PDF.

        Returns:
            {pages: list[{page, text, chars}], total_chars: int, page_count: int}
        """
        pages = extract_pdf_text(pdf_bytes)
        return {
            "pages":       pages,
            "total_chars": sum(p["chars"] for p in pages),
            "page_count":  len(pages),
        }

    def read(self, source, source_type: str = "image") -> dict:
        """Dispatch to read_image or read_pdf based on source_type.

        Args:
            source:      PIL Image for "image"; bytes for "pdf"
            source_type: "image" or "pdf"
        Returns:
            Same dict as read_image or read_pdf
        Raises:
            ValueError for unknown source_type
        """
        if source_type == "image":
            return self.read_image(source)
        if source_type == "pdf":
            return self.read_pdf(source)
        raise ValueError(
            f"Unknown source_type: {source_type!r}. Use 'image' or 'pdf'."
        )
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
day: "068"
lesson: 1
title: "How OCR Works"
slides:
  - type: title
    heading: "OCR & Document AI"
    subheading: "Day 68 — Turning images and PDFs into searchable text"
    narration: >
      Yesterday you gave images to a vision LLM and got text back. Today
      you use a different tool — Tesseract OCR — for the same task. They
      are complementary: Tesseract is fast, offline, and precise for clean
      printed text; vision LLMs handle context, handwriting, and noisy
      documents better. This day builds the toolkit to choose the right
      approach. You will also extract text from PDFs using pypdf, which
      you met on Day 56.

  - type: concept
    label: "What is OCR?"
    heading: "Optical Character Recognition"
    body: >
      OCR converts a raster image of text (pixels) into a machine-readable
      string. The image could be a scanned document, a photograph, or a
      screenshot.
    bullets:
      - "Input: image containing text (PNG, JPEG, TIFF, ...)"
      - "Output: UTF-8 string — same characters as visible in the image"
      - "Classic pipeline: binarise → segment → recognise → post-process"
      - "Modern engines (Tesseract 4+) use an LSTM-based recogniser"
    narration: >
      OCR was one of the first AI problems to reach production quality.
      Tesseract, originally developed at HP in the 1980s and open-sourced
      by Google in 2006, is now on version 5 with LSTM-based recognition.
      It ships with trained models for over 100 languages and runs entirely
      on-CPU — no GPU, no API key, no cost. For clean printed text it is
      highly accurate and very fast. For handwriting, complex layouts, or
      degraded images you need either preprocessing or a vision LLM.

  - type: how_it_works
    label: "Tesseract pipeline"
    heading: "Tesseract's OCR Pipeline"
    body: >
      Tesseract processes an image in four stages before producing text.
    bullets:
      - "1. Binarise — convert to black-and-white using adaptive thresholding"
      - "2. Deskew & segment — detect text blocks, columns, words, characters"
      - "3. Recognise — LSTM network predicts character sequence per text line"
      - "4. Post-process — language model corrects likely errors"
    narration: >
      Binarisation converts the greyscale image to pure black and white.
      Adaptive thresholding adjusts the cutoff locally so uneven lighting
      does not ruin the result. Segmentation uses heuristics to detect
      text blocks, split columns, find word boundaries, and isolate
      individual characters. The LSTM recogniser then reads each text
      line as a sequence prediction problem. The language model stage
      uses dictionaries and n-gram statistics to fix ambiguous characters
      — 'l' vs '1', '0' vs 'O'. You can skip the language model with
      --oem 3 --psm 6 flags if you are reading codes or numbers.

  - type: concept
    label: "pytesseract"
    heading: "pytesseract — Python Binding"
    body: >
      pytesseract is a thin Python wrapper around the Tesseract command-line
      binary. It handles the image → temp file → subprocess → stdout → string
      pipeline.
    bullets:
      - "pip install pytesseract  (Python package)"
      - "brew install tesseract   (macOS — the actual OCR binary)"
      - "image_to_string(img)     → extracted text"
      - "image_to_data(img)       → word-level bounding boxes + confidence"
    narration: >
      pytesseract is a wrapper, not a reimplementation. It serialises the PIL
      Image to a temporary TIFF or PNG, calls the Tesseract binary as a
      subprocess, captures stdout, and returns the string. This means Tesseract
      must be installed as a system binary — it is not bundled in the Python
      package. On macOS use brew install tesseract; on Ubuntu use
      apt-get install tesseract-ocr. The ocr_fn injection pattern you
      will use today means exercises run without Tesseract installed.

  - type: code
    label: "Basic usage"
    heading: "pytesseract.image_to_string"
    code: |
      import pytesseract
      from PIL import Image

      img = Image.open("document.png")

      # Basic OCR — returns a string
      text = pytesseract.image_to_string(img)
      print(text)

      # With language and page-segmentation hints
      text = pytesseract.image_to_string(
          img,
          lang='eng',
          config='--psm 6'   # treat image as uniform block of text
      )
    narration: >
      image_to_string is the main entry point. The lang parameter selects the
      recognition model — eng for English, fra for French, deu for German, etc.
      Multiple languages can be combined: lang='eng+fra'. The config parameter
      passes flags directly to Tesseract. --psm 6 means page segmentation mode 6
      — assume a single uniform block of text. The default is --psm 3 which runs
      automatic layout analysis. For receipts and invoices, --psm 6 is often more
      reliable because the layout is dense and varied.

  - type: exercise
    heading: "Exercise 1: OCR an Image"
    prompt: >
      Implement ocr_image(img, ocr_fn=None, lang='eng', config='') -> str.
      If ocr_fn is provided, call it with the image and return the result.
      Otherwise call pytesseract.image_to_string(img, lang=lang, config=config).
      All checks use a mock ocr_fn so Tesseract is not required.
    hint: >
      if ocr_fn is not None: return ocr_fn(img). Otherwise: import pytesseract
      inside the else branch; return pytesseract.image_to_string(img, lang=lang,
      config=config).
    narration: >
      The ocr_fn injection pattern follows the same contract as describe_fn in
      Day 67 — any callable that accepts the image and returns a string can act
      as the OCR engine. This makes every downstream function testable without
      Tesseract installed.

  - type: summary
    heading: "Lesson 1 Summary"
    bullets:
      - "Tesseract: binarise → segment → LSTM recognise → language-model post-process"
      - "pytesseract: Python wrapper — requires the Tesseract binary (brew install)"
      - "image_to_string(img, lang='eng', config='') → text string"
      - "--psm 6: treat as uniform text block (good for receipts)"
      - "ocr_fn=None injection: swap Tesseract for a mock in all tests"
    narration: >
      The OCR machinery is clear. Next: image preprocessing — small, dark, or
      blurry inputs hurt Tesseract accuracy significantly. Proper preprocessing
      can double the character accuracy on difficult images.
"""

_LESSON_02 = """\
day: "068"
lesson: 2
title: "Preprocessing for OCR"
slides:
  - type: title
    heading: "Preprocessing for OCR"
    subheading: "Grayscale, contrast, scale — three steps that matter most"
    narration: >
      Tesseract was designed for clean printed text on a white background.
      Real scanned documents are often slightly skewed, low-contrast, or
      small. Three preprocessing steps reliably improve OCR accuracy:
      convert to greyscale, boost contrast, and upscale small images.
      All three use Pillow tools you learned on Day 66.

  - type: concept
    label: "Why preprocess?"
    heading: "Why Preprocessing Matters"
    body: >
      Tesseract's accuracy depends heavily on image quality. Small changes
      to the input can shift accuracy from 60% to 98%.
    bullets:
      - "Low resolution: characters too small for the LSTM → missed/garbled"
      - "Low contrast: text blends into background → binarisation fails"
      - "Colour noise: colour channels add irrelevant variance → grayscale first"
      - "Skew: words curve or tilt → segmentation breaks word boundaries"
    narration: >
      Tesseract's binarisation step uses Otsu's global threshold, which
      works well when the text is clearly darker than the background. If
      contrast is low — light grey text on a white receipt, for example —
      the threshold ends up in the wrong place and many characters become
      noise. Boosting contrast before Tesseract gets the image essentially
      binarises it for the OCR engine. Resolution matters because the LSTM
      recogniser expects characters to span at least 20–30 pixels tall;
      anything smaller loses the distinguishing features of each character.

  - type: how_it_works
    label: "Preprocessing pipeline"
    heading: "The Three-Step Preprocessing Pipeline"
    body: >
      Three operations in order: colour → grayscale, then contrast boost,
      then resolution upscale if needed.
    narration: >
      Grayscale first — remove colour as a distraction. Then contrast
      enhancement — make text black and background white. Then scale —
      if the image is narrow (under 1000 pixels wide), upscale so characters
      have enough pixels. Each step uses Pillow, so there are no extra
      dependencies beyond what you installed on Day 66. The scale threshold
      of 1000 pixels is a practical rule of thumb; the exact number depends
      on your expected document types. For documents with small footnote text
      you may want 1500 or more.

  - type: code
    label: "Preprocessing code"
    heading: "preprocess_for_ocr Implementation"
    code: |
      from PIL import Image, ImageEnhance

      def preprocess_for_ocr(img: Image.Image) -> Image.Image:
          # Step 1: greyscale — one channel, no colour noise
          out = img.convert('L')

          # Step 2: boost contrast — dark text → black, background → white
          out = ImageEnhance.Contrast(out).enhance(2.0)

          # Step 3: upscale if too small — LSTM needs ≥20px tall chars
          w, h = out.size
          if w < 1000:
              scale = 1000 / w
              out = out.resize(
                  (int(w * scale), int(h * scale)),
                  Image.Resampling.LANCZOS
              )
          return out
    narration: >
      The contrast factor of 2.0 doubles the distance between each pixel
      and the midpoint grey. A pixel at 200 (light grey) becomes 200 + (200-128)
      × 1.0 ≈ 228 (near white). A pixel at 60 (dark grey) becomes 60 - (128-60)
      ≈ -8 → clamped to 0 (black). The ImageEnhance class handles clamping
      automatically — no overflow or wrapping. The LANCZOS resampling filter
      preserves sharp character edges during upscaling, which matters more here
      than for photos.

  - type: code
    label: "Before and after"
    heading: "Comparing OCR With and Without Preprocessing"
    code: |
      import pytesseract
      from PIL import Image

      img = Image.open("faded_receipt.png")   # small, low-contrast scan

      # Without preprocessing
      raw_text = pytesseract.image_to_string(img)

      # With preprocessing
      preprocessed = preprocess_for_ocr(img)
      clean_text   = pytesseract.image_to_string(preprocessed)

      print(f"Raw chars:   {len(raw_text.strip())}")
      print(f"Clean chars: {len(clean_text.strip())}")
      # clean_text typically has more characters and fewer garbage symbols
    narration: >
      You will not always see an improvement — on a high-quality scan the
      preprocessing makes no difference. But on a photograph of a document
      (uneven lighting, perspective distortion) or a compressed JPEG, the
      contrast boost and scale step frequently recover characters that the
      raw image misses. The preprocessing step is fast — a few milliseconds —
      so there is no cost to always applying it.

  - type: exercise
    heading: "Exercise 2: Preprocess for OCR"
    prompt: >
      Implement preprocess_for_ocr(img) -> Image.Image. Convert to grayscale
      ('L' mode), boost contrast by a factor of 2.0 with ImageEnhance.Contrast,
      then upscale to at least 1000 px wide using LANCZOS if the image is
      narrower. Return the processed Image. No OCR call — pure PIL.
    hint: >
      img.convert('L') → then ImageEnhance.Contrast(out).enhance(2.0) →
      then check w < 1000, compute scale = 1000/w, out.resize((int(w*scale),
      int(h*scale)), Image.Resampling.LANCZOS). Return out.
    narration: >
      This exercise is pure Pillow — no Tesseract needed. It reinforces
      the PIL patterns from Day 66 while building a production-quality
      preprocessing step that you will plug into the document reader pipeline
      in Exercise 5.

  - type: summary
    heading: "Lesson 2 Summary"
    bullets:
      - "Grayscale: img.convert('L') — removes colour, one channel"
      - "Contrast: ImageEnhance.Contrast(img).enhance(2.0) — make text black"
      - "Scale: resize to ≥1000 px wide with LANCZOS — LSTM needs ≥20 px chars"
      - "Order matters: colour first, then contrast, then scale"
      - "Always preprocess before Tesseract on real-world documents"
    narration: >
      The preprocessing pipeline is settled. Next: PDF text extraction —
      a different path where the text is already digital (no OCR needed),
      unless the PDF is a scanned image embedded in a PDF wrapper.
"""

_LESSON_03 = """\
day: "068"
lesson: 3
title: "PDF Text Extraction"
slides:
  - type: title
    heading: "PDF Text Extraction"
    subheading: "pypdf for text-based PDFs — Day 56 revisited"
    narration: >
      On Day 56 you used pypdf to extract text from uploaded PDF files.
      Today you revisit it in the context of document AI — extracting
      text per page, detecting scanned pages, and deciding whether to
      use pypdf or fallback to OCR. The two approaches are complementary:
      pypdf is instant for digital PDFs; Tesseract is needed for scanned pages.

  - type: concept
    label: "PDF types"
    heading: "Text-Based vs Scanned PDFs"
    body: >
      Not all PDFs are equal. The right extraction strategy depends on
      whether the text is stored digitally or embedded as an image.
    bullets:
      - "Text-based PDF: text is stored as Unicode strings in the PDF structure"
      - "Scanned PDF: pages are raster images; no machine-readable text"
      - "Hybrid: some pages digital, some scanned (common in mixed archives)"
      - "Detection: chars == 0 on a page → scanned (fallback to OCR)"
    narration: >
      When you save a Word document as PDF, the text is stored digitally —
      pypdf extracts it instantly with no OCR. When you scan a paper document
      and save it as PDF, the pages are raster images wrapped in a PDF container.
      pypdf's extract_text returns an empty string for those pages because there
      are no text objects in the PDF structure. The detection heuristic is simple:
      if chars == 0 after pypdf extraction, the page is probably scanned and
      needs OCR. In Day 69 you will combine vision LLM + Pydantic to handle
      scanned invoices end-to-end.

  - type: code
    label: "pypdf extraction"
    heading: "pypdf Page-by-Page Extraction"
    code: |
      import io
      import pypdf

      def extract_pdf_text(pdf_bytes: bytes) -> list:
          reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
          pages  = []
          for i, page in enumerate(reader.pages, start=1):
              text = page.extract_text() or ''
              pages.append({
                  'page':  i,
                  'text':  text,
                  'chars': len(text),
              })
          return pages

      # Usage
      with open('invoice.pdf', 'rb') as f:
          result = extract_pdf_text(f.read())

      for p in result:
          status = 'ok' if p['chars'] > 0 else 'SCANNED (no text)'
          print(f"Page {p['page']}: {p['chars']} chars — {status}")
    narration: >
      The `or ''` guard converts None (returned by pypdf when a page has no
      text objects) to an empty string. This is the same pattern from Day 56.
      enumerate starting at 1 makes the page numbers human-readable — matching
      what Adobe and most PDF viewers show. The page count comes from
      len(reader.pages) — no separate call needed.

  - type: how_it_works
    label: "Hybrid strategy"
    heading: "Hybrid PDF Strategy: pypdf First, OCR Fallback"
    body: >
      A production document reader tries pypdf first and falls back to
      OCR for pages with no extracted text.
    narration: >
      The hybrid strategy is: extract with pypdf, check chars per page,
      and for any page where chars == 0 (or fewer than some threshold),
      render the page as an image and run OCR. pypdf does not render pages
      to images — for that you need the pdf2image package (which wraps
      poppler). That is beyond today's scope but the architecture is clear:
      the page iterator is the same, and the decision at each page is just
      one if statement. Today's exercises focus on the pypdf path; the OCR
      fallback is exercise 5's pipeline.

  - type: code
    label: "Metadata"
    heading: "PDF Metadata and Page Count"
    code: |
      import io, pypdf

      def pdf_info(pdf_bytes: bytes) -> dict:
          reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
          meta   = reader.metadata or {}
          return {
              'page_count': len(reader.pages),
              'title':      meta.get('/Title', ''),
              'author':     meta.get('/Author', ''),
              'creator':    meta.get('/Creator', ''),
          }

      # with open('report.pdf', 'rb') as f:
      #     print(pdf_info(f.read()))
    narration: >
      PDF metadata is stored in the document's info dictionary. The keys
      use PDF name syntax with a leading slash. pypdf's metadata property
      returns a dict-like object; use .get with a default for optional fields.
      The page_count is the most reliable piece of metadata — it is always
      present. Title and author are often empty in machine-generated PDFs.

  - type: exercise
    heading: "Exercise 3: Extract PDF Text"
    prompt: >
      Implement extract_pdf_text(pdf_bytes: bytes) -> list[dict].
      Use pypdf.PdfReader(io.BytesIO(pdf_bytes)) to read the PDF.
      For each page (enumerate starting at 1), extract text with
      page.extract_text() — guard against None with 'or ""'.
      Return a list of dicts: [{page: int, text: str, chars: int}].
      Use the minimal_pdf fixture provided — no file system needed.
    hint: >
      import pypdf, io. reader = pypdf.PdfReader(io.BytesIO(pdf_bytes)).
      for i, page in enumerate(reader.pages, start=1): text = page.extract_text() or ''.
      append {'page': i, 'text': text, 'chars': len(text)}.
    narration: >
      pypdf was introduced on Day 56 — this exercise reinforces page-level
      iteration and the scanned-page detection pattern that the full document
      reader pipeline uses.

  - type: summary
    heading: "Lesson 3 Summary"
    bullets:
      - "Text-based PDF: extract_text() returns non-empty → use directly"
      - "Scanned PDF: extract_text() returns '' → needs OCR fallback"
      - "pypdf.PdfReader(io.BytesIO(pdf_bytes)) — no file needed"
      - "enumerate(reader.pages, start=1) — 1-based page numbers"
      - "page.extract_text() or '' — guard against None"
    narration: >
      PDF extraction is clean for digital documents. Next: parsing the
      output — extracting numeric values from OCR text, which is essential
      for receipt and invoice processing.
"""

_LESSON_04 = """\
day: "068"
lesson: 4
title: "Parsing OCR Output"
slides:
  - type: title
    heading: "Parsing OCR Output"
    subheading: "Regex numeric extraction — receipts and invoices"
    narration: >
      OCR gives you a raw string — a dump of everything the engine could
      read. For document AI you usually want structure: the total on a
      receipt, the line items on an invoice, the date on a contract. This
      lesson covers regex-based numeric extraction, the most common
      post-processing step for financial documents.

  - type: concept
    label: "OCR output noise"
    heading: "Why OCR Output Needs Parsing"
    body: >
      Raw OCR text is not clean. It contains layout artefacts, recognition
      errors, and mixed content. Parsing extracts the signal.
    bullets:
      - "Spurious whitespace: 'T o t a l' instead of 'Total'"
      - "Character substitutions: 'l' vs '1', 'O' vs '0', 'S' vs '5'"
      - "Layout artefacts: column separators, page numbers, headers"
      - "Mixed content: date strings, phone numbers, product codes, prices"
    narration: >
      Character substitutions are the most common source of errors in
      numeric extraction. The LSTM recogniser sometimes confuses lowercase L
      with 1, uppercase O with 0, or S with 5 — especially in fonts that
      look similar for these pairs. This is why domain-specific post-processing
      matters: if you know the field should be a price (positive float), you
      can filter out values that are clearly wrong.

  - type: how_it_works
    label: "Regex for numbers"
    heading: "Regex Pattern for Numeric Values"
    body: >
      A single regex pattern captures integers, decimals, and comma-separated
      thousands in one pass.
    narration: >
      The pattern has two alternatives joined by '|'. The first alternative
      matches comma-separated thousands notation like '1,234.56' using
      repetition groups. The second matches plain integers and decimals.
      The word-boundary anchors prevent matching partial numbers inside
      longer tokens. After extraction, commas are stripped and the value is
      cast to float. Sorting the result puts the values in ascending order,
      which is convenient for finding the minimum and maximum (often the
      individual items and the total on a receipt).

  - type: code
    label: "Number extraction"
    heading: "extract_numbers Implementation"
    code: |
      import re

      def extract_numbers(text: str) -> list:
          pattern = (
              r'\\b\\d{1,3}(?:,\\d{3})*(?:\\.\\d+)?'   # 1,234.56
              r'|\\b\\d+(?:\\.\\d+)?\\b'                # 123 or 12.5
          )
          raw = re.findall(pattern, text)
          result = []
          for s in raw:
              try:
                  result.append(float(s.replace(',', '')))
              except ValueError:
                  pass
          return sorted(result)

      sample = 'Subtotal 12.50\\nTax 1,00\\nTotal $13.50'
      print(extract_numbers(sample))
      # [1.0, 12.5, 13.5]  — 1,00 → 1.0 (misread comma)
    narration: >
      The try/except ValueError around each conversion handles OCR
      artefacts that look like numbers but are not valid floats after
      comma removal — things like a lone comma or a trailing dot.
      Sorting in ascending order is a stylistic choice — callers can
      reverse it if they need descending. Notice that '1,00' (common
      OCR misread of '1.00') becomes 1.0 after comma removal, which is
      the correct value for a dollar amount of one dollar. In a production
      system you would combine field detection (which label precedes the
      number?) with numeric parsing.

  - type: code
    label: "Applied parsing"
    heading: "Receipt Total Detection"
    code: |
      def find_total(text: str) -> float | None:
          '''Find the line marked Total/TOTAL and extract its amount.'''
          numbers_on_total_line = []
          for line in text.splitlines():
              if 'total' in line.lower():
                  nums = extract_numbers(line)
                  numbers_on_total_line.extend(nums)
          if not numbers_on_total_line:
              return None
          return max(numbers_on_total_line)   # largest number on the total line

      receipt_ocr = '''
      Item 1    $5.99
      Item 2    $3.50
      Subtotal  $9.49
      Tax       $0.76
      TOTAL     $10.25
      '''
      print(find_total(receipt_ocr))  # 10.25
    narration: >
      find_total shows the typical document AI pattern: filter lines by a
      keyword, extract numbers from those lines, pick the relevant one.
      Taking max on the total line works because the total is usually the
      largest number on that line and there is often only one. In practice
      you would also handle cases like 'Grand Total' vs 'Subtotal' using
      a priority list of keywords.

  - type: exercise
    heading: "Exercise 4: Extract Numbers from Text"
    prompt: >
      Implement extract_numbers(text: str) -> list[float].
      Use re.findall to capture comma-separated numbers (1,234.56) and
      plain decimals/integers. Strip commas from each match and cast to
      float. Skip values that fail to convert. Return the result sorted
      ascending. Pure Python — no PIL or Tesseract needed.
    hint: >
      pattern = r'\\b\\d{1,3}(?:,\\d{3})*(?:\\.\\d+)?|\\b\\d+(?:\\.\\d+)?\\b'
      re.findall(pattern, text) → list of strings. float(s.replace(',',''))
      in a try/except. sorted(result).
    narration: >
      Regex-based numeric extraction is pure Python — no imports beyond re.
      It is the parsing core of any receipt, invoice, or form reader built
      on OCR output.

  - type: summary
    heading: "Lesson 4 Summary"
    bullets:
      - "OCR output is noisy: substitutions, artefacts, mixed content"
      - "re.findall with alternation: 1,234.56 | 123 | 12.5"
      - "Strip commas before float() cast"
      - "try/except ValueError: skip tokens that look numeric but are not"
      - "sorted(): ascending order — max is the total, min is the smallest item"
    narration: >
      You have OCR, preprocessing, PDF extraction, and numeric parsing.
      Lesson 5 wires all four into a DocumentReader class — the same
      facade pattern you used for ChatStore in Section 4.
"""

_LESSON_05 = """\
day: "068"
lesson: 5
title: "Building a Document Reader"
slides:
  - type: title
    heading: "Building a Document Reader"
    subheading: "DocumentReader — one class, two sources, structured output"
    narration: >
      The final lesson assembles all four components into a DocumentReader
      class. You have seen this facade pattern before — ChatStore on Day 54,
      VisionAnalyzer on Day 67. The pattern is the same: one object wraps
      all dependencies, exposes a clean public interface, and accepts a mock
      injection for testing.

  - type: how_it_works
    label: "DocumentReader"
    heading: "DocumentReader Architecture"
    body: >
      Four components wired into one class:
      preprocess → OCR → extract_numbers → return structured dict.
    bullets:
      - "read_image(img) → {text, numbers, chars, preprocess}"
      - "read_pdf(pdf_bytes) → {pages: [{page, text, chars}], total_chars, page_count}"
      - "read(source, source_type) → dispatches to the right method"
      - "ocr_fn=None → Tesseract; pass mock for testing"
    narration: >
      The read method is a simple dispatcher — it delegates to read_image
      or read_pdf based on source_type. The dict return values are consistent
      enough that downstream code can inspect 'text' for an image result or
      iterate 'pages' for a PDF result. In a production document pipeline you
      would normalise these into a single schema — that is the Pydantic
      extraction work in Day 69.

  - type: code
    label: "DocumentReader"
    heading: "DocumentReader Class"
    code: |
      from document_reader import DocumentReader
      from PIL import Image

      # Testing mode — no Tesseract needed
      mock_ocr = lambda img: 'Invoice Total $42.00\\nTax $4.00'
      dr = DocumentReader(ocr_fn=mock_ocr)

      img = Image.new('RGB', (300, 100), 'white')
      result = dr.read_image(img)
      print(result['text'])
      print(result['numbers'])    # [4.0, 42.0]
      print(result['chars'])

      # Dispatch via read()
      result2 = dr.read(img, source_type='image')
      assert result2['text'] == result['text']
    narration: >
      The mock is a lambda that ignores its argument and returns a fixed
      string — the minimum interface required by ocr_fn. In production you
      replace it with the real Tesseract path by omitting ocr_fn (or passing
      None). The read method's source_type parameter means you can write a
      single pipeline step that accepts either source type and passes the
      right one to the right backend.

  - type: code
    label: "Full pipeline"
    heading: "Receipt OCR Pipeline End-to-End"
    code: |
      from PIL import Image, ImageDraw

      # Simulate a receipt image
      img = Image.new('RGB', (250, 120), 'white')
      draw = ImageDraw.Draw(img)
      draw.text((10, 10),  'Coffee     $3.50', fill='black')
      draw.text((10, 30),  'Sandwich   $7.25', fill='black')
      draw.text((10, 50),  'Subtotal  $10.75', fill='black')
      draw.text((10, 70),  'Tax        $0.86', fill='black')
      draw.text((10, 90),  'TOTAL     $11.61', fill='black')

      dr = DocumentReader()          # uses real Tesseract
      result = dr.read_image(img)

      print(result['text'])
      print('Numbers found:', result['numbers'])
      # Numbers found: [0.86, 3.5, 7.25, 10.75, 11.61]
    narration: >
      The full pipeline: create the image, call read_image (which preprocesses
      then OCRs), and inspect the structured output. The sorted numbers list
      makes it easy to find the total — max(result['numbers']) — or check
      that the sum of items roughly equals the total. In Day 69 you will push
      this further and use a vision LLM with a Pydantic schema to extract
      line items as structured JSON.

  - type: exercise
    heading: "Exercise 5: Document Reader Pipeline"
    prompt: >
      Implement read_document(source, source_type='image', ocr_fn=None) -> dict.
      For 'image': call preprocess_for_ocr(source), then ocr_image(preprocessed,
      ocr_fn), then extract_numbers(text). Return {text, numbers, chars}.
      For 'pdf': call extract_pdf_text(source). Return {pages, total_chars,
      page_count}. Raise ValueError for unknown source_type.
      All checks use mocks — no Tesseract or PDF file needed.
    hint: >
      if source_type == 'image': preprocess → ocr → numbers → return dict.
      elif source_type == 'pdf': extract_pdf_text → return dict.
      else: raise ValueError. Helper functions are provided in the given cell.
    narration: >
      The pipeline exercise ties Day 68 together: preprocessing, OCR, parsing,
      and PDF extraction in one function. The dict output is the input to Day 69's
      structured extraction step.

  - type: summary
    heading: "Lesson 5 Summary — Day 68 Complete"
    bullets:
      - "DocumentReader facade: ocr_fn=None injection, two source types"
      - "read_image: preprocess → OCR → numbers → {text, numbers, chars}"
      - "read_pdf: pypdf pages → {pages, total_chars, page_count}"
      - "read(source, source_type) dispatches to the right backend"
      - "Tomorrow (Day 69): vision LLM + Pydantic → structured JSON from images"
    narration: >
      Day 68 is complete. You have a working OCR pipeline and PDF extractor.
      The DocumentReader class handles both source types with a clean
      mock-injection interface. Tomorrow you combine the vision LLM from
      Day 67 with a Pydantic schema to extract structured data from images
      — turning a receipt photograph into a typed Python object with validated
      fields.
"""

for i, content in enumerate([_LESSON_01, _LESSON_02, _LESSON_03,
                               _LESSON_04, _LESSON_05], start=1):
    (OUT / "lessons" / f"day_{DAY}_lesson_0{i}.yaml").write_text(content)

# ── shared helper source for exercises ────────────────────────────────────────
_HELPER_SRC = """\
import io
import re
from PIL import Image, ImageEnhance

def preprocess_for_ocr(img):
    out = img.convert('L')
    out = ImageEnhance.Contrast(out).enhance(2.0)
    w, h = out.size
    if w < 1000:
        scale = 1000 / w
        out = out.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
    return out

def ocr_image(img, ocr_fn=None, lang='eng', config=''):
    if ocr_fn is not None:
        return ocr_fn(img)
    import pytesseract
    return pytesseract.image_to_string(img, lang=lang, config=config)

def extract_numbers(text):
    pattern = r'\\b\\d{1,3}(?:,\\d{3})*(?:\\.\\d+)?|\\b\\d+(?:\\.\\d+)?\\b'
    raw = re.findall(pattern, text)
    result = []
    for s in raw:
        try:
            result.append(float(s.replace(',', '')))
        except ValueError:
            pass
    return sorted(result)

def extract_pdf_text(pdf_bytes):
    import pypdf
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ''
        pages.append({'page': i, 'text': text, 'chars': len(text)})
    return pages
"""

# ── EXERCISE 1 — ocr_image ────────────────────────────────────────────────────
_EX1_GIVEN = """\
from PIL import Image, ImageDraw

_test_img = Image.new('RGB', (200, 50), color='white')
_draw = ImageDraw.Draw(_test_img)
_draw.text((10, 10), 'Hello OCR', fill='black')
"""

_EX1_STUB = """\
def ocr_image(img, ocr_fn=None, lang: str = 'eng', config: str = '') -> str:
    \"\"\"Extract text from a PIL Image using Tesseract OCR.

    Args:
        img:    PIL Image to OCR
        ocr_fn: callable(img) -> str  (for testing without Tesseract)
        lang:   Tesseract language code, default 'eng'
        config: extra Tesseract flags, e.g. '--psm 6'
    Returns:
        Extracted text string
    \"\"\"
    raise NotImplementedError
"""

_EX1_SOLUTION = """\
def ocr_image(img, ocr_fn=None, lang: str = 'eng', config: str = '') -> str:
    if ocr_fn is not None:
        return ocr_fn(img)
    import pytesseract
    return pytesseract.image_to_string(img, lang=lang, config=config)
"""

_EX1_CHECKS = """\
score, total = 0, 5
try:
    captured = {}
    def _mock(img_arg):
        captured['img'] = img_arg
        return 'Hello OCR'

    result = ocr_image(_test_img, ocr_fn=_mock)
    assert isinstance(result, str), f"Expected str, got {type(result)}"
    score += 1; print("\\u2705 returns a string")

    assert result == 'Hello OCR', f"Expected 'Hello OCR', got {result!r}"
    score += 1; print("\\u2705 returns the mock's text")

    assert captured.get('img') is _test_img, "mock should receive the img argument"
    score += 1; print("\\u2705 mock receives the image")

    # lang and config are passed through (mock ignores them but they don't raise)
    result2 = ocr_image(_test_img, ocr_fn=lambda i: 'test', lang='fra', config='--psm 6')
    assert result2 == 'test'
    score += 1; print("\\u2705 lang and config parameters accepted without error")

    # Default return is a string even for empty images
    result3 = ocr_image(Image.new('RGB',(50,20),'white'), ocr_fn=lambda i: '')
    assert isinstance(result3, str)
    score += 1; print("\\u2705 empty-response mock returns empty string")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX1 = nb([
    md("# Day 068 — Exercise 1: OCR an Image\n\n"
       "**What you'll build:** `ocr_image(img, ocr_fn=None, lang, config)` — "
       "extract text from a PIL Image using Tesseract, with mock injection for testing.\n\n"
       "**Why it matters:** This is the Tesseract equivalent of `describe_image` from "
       "Day 67. The `ocr_fn=None` pattern makes every downstream document function "
       "testable without a running Tesseract installation — the same contract as "
       "`describe_fn` for vision LLMs."),
    code(_EX1_GIVEN),
    md("## Task\n\nImplement `ocr_image(img, ocr_fn=None, lang='eng', config='') -> str`:\n\n"
       "- If `ocr_fn is not None`: call `ocr_fn(img)` and return the result\n"
       "- Otherwise: `import pytesseract` and call "
       "`pytesseract.image_to_string(img, lang=lang, config=config)`\n"
       "- Return the result string\n\n"
       "All checks use a mock `ocr_fn` — Tesseract is not required."),
    md("## Your Implementation"),
    code(_EX1_STUB),
    code(_EX1_SOLUTION),
    md("## Automated checks"),
    code(_EX1_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX1_SOLUTION + "```\n\n"
       "**Why import inside the else branch?** If Tesseract is not installed, "
       "importing pytesseract raises an ImportError only when you actually try to "
       "OCR without a mock. The mock path never triggers the import. This lets "
       "the module load cleanly in environments where Tesseract is not available, "
       "while still failing loudly when you try to use the real OCR path without it.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_01.ipynb", EX1)

# ── EXERCISE 2 — preprocess_for_ocr ──────────────────────────────────────────
_EX2_GIVEN = """\
from PIL import Image, ImageEnhance

_small_rgb  = Image.new('RGB',  (200, 80),  color=(180, 180, 200))   # small, grey
_large_rgb  = Image.new('RGB',  (1200, 400), color=(220, 210, 190))  # already large
"""

_EX2_STUB = """\
def preprocess_for_ocr(img) -> 'Image.Image':
    \"\"\"Improve image quality for Tesseract OCR.

    Steps (in order):
        1. Convert to greyscale ('L' mode)
        2. Boost contrast by factor 2.0 using ImageEnhance.Contrast
        3. Upscale to at least 1000 px wide using LANCZOS if narrower

    Args:
        img: PIL Image (any mode)
    Returns:
        Preprocessed PIL Image in 'L' mode
    \"\"\"
    raise NotImplementedError
"""

_EX2_SOLUTION = """\
def preprocess_for_ocr(img):
    out = img.convert('L')
    out = ImageEnhance.Contrast(out).enhance(2.0)
    w, h = out.size
    if w < 1000:
        scale = 1000 / w
        out = out.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
    return out
"""

_EX2_CHECKS = """\
score, total = 0, 5
try:
    result = preprocess_for_ocr(_small_rgb)
    assert hasattr(result, 'mode'), "Expected a PIL Image"
    score += 1; print("\\u2705 returns a PIL Image")

    assert result.mode == 'L', f"Expected 'L' mode, got {result.mode!r}"
    score += 1; print("\\u2705 output is grayscale ('L' mode)")

    w, h = result.size
    assert w >= 1000, f"Expected width >= 1000 px, got {w}"
    score += 1; print(f"\\u2705 small image upscaled to {w}x{h}")

    # Already-large image should not shrink
    large_result = preprocess_for_ocr(_large_rgb)
    lw, lh = large_result.size
    assert lw >= 1200, f"Large image should not shrink: got {lw}"
    score += 1; print(f"\\u2705 large image not shrunk (width {lw})")

    # RGBA input also works
    rgba = Image.new('RGBA', (300, 100), color=(200, 50, 50, 128))
    preproc = preprocess_for_ocr(rgba)
    assert preproc.mode == 'L'
    score += 1; print("\\u2705 RGBA input converted to L without error")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX2 = nb([
    md("# Day 068 — Exercise 2: Preprocess for OCR\n\n"
       "**What you'll build:** `preprocess_for_ocr(img) -> Image.Image` — "
       "three preprocessing steps that significantly improve Tesseract accuracy.\n\n"
       "**Why it matters:** Tesseract's LSTM recogniser needs high-contrast, "
       "sufficiently-sized characters. These three steps (grayscale → contrast → scale) "
       "are the most impactful preprocessing operations — often raising character "
       "accuracy from 60% to 98% on real-world document scans."),
    code(_EX2_GIVEN),
    md("## Task\n\nImplement `preprocess_for_ocr(img) -> Image.Image`:\n\n"
       "1. `out = img.convert('L')` — grayscale\n"
       "2. `out = ImageEnhance.Contrast(out).enhance(2.0)` — boost contrast\n"
       "3. If `out.size[0] < 1000`: upscale to 1000 px wide with "
       "`Image.Resampling.LANCZOS`\n"
       "4. Return `out`\n\n"
       "Pure PIL — no Tesseract, no mocks needed."),
    md("## Your Implementation"),
    code(_EX2_STUB),
    code(_EX2_SOLUTION),
    md("## Automated checks"),
    code(_EX2_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX2_SOLUTION + "```\n\n"
       "**Why check `w < 1000` not `w < 1000 or h < 1000`?** Width is the "
       "bottleneck because text lines run horizontally — a narrow image has "
       "narrow characters. Height scales with width proportionally so checking "
       "only width avoids distorting aspect ratios of tall narrow images.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_02.ipynb", EX2)

# ── EXERCISE 3 — extract_pdf_text ─────────────────────────────────────────────
# Build a minimal valid single-page PDF in memory for tests
_MINIMAL_PDF_CODE = """\
import io, struct

def _minimal_pdf(text: str) -> bytes:
    '''Generate a tiny single-page PDF with the given text (Helvetica 12pt).'''
    lines = text.splitlines()
    tf_lines = ''.join(f'({ln}) Tj T* ' for ln in lines)
    stream = (
        f'BT /F1 12 Tf 50 750 Td {tf_lines}ET'
    ).encode()
    slen = len(stream)

    objs = {
        1: b'<< /Type /Catalog /Pages 2 0 R >>',
        2: b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        3: b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /Contents 4 0 R >>',
        4: f'<< /Length {slen} >>\\nstream\\n'.encode() + stream + b'\\nendstream',
    }
    buf = io.BytesIO()
    buf.write(b'%PDF-1.4\\n')
    offsets = {}
    for num, obj_bytes in objs.items():
        offsets[num] = buf.tell()
        buf.write(f'{num} 0 obj\\n'.encode())
        buf.write(obj_bytes)
        buf.write(b'\\nendobj\\n')

    xref_pos = buf.tell()
    buf.write(b'xref\\n')
    buf.write(f'0 {len(objs)+1}\\n'.encode())
    buf.write(b'0000000000 65535 f \\n')
    for num in range(1, len(objs)+1):
        buf.write(f'{offsets[num]:010d} 00000 n \\n'.encode())
    buf.write(
        f'trailer << /Size {len(objs)+1} /Root 1 0 R >>\\n'
        f'startxref\\n{xref_pos}\\n%%EOF\\n'.encode()
    )
    return buf.getvalue()

_test_pdf = _minimal_pdf('Hello PDF\\nLine two')
"""

_EX3_GIVEN = "import io\nimport pypdf\n" + _MINIMAL_PDF_CODE

_EX3_STUB = """\
def extract_pdf_text(pdf_bytes: bytes) -> list:
    \"\"\"Extract text from each page of a PDF.

    Args:
        pdf_bytes: raw PDF bytes
    Returns:
        List of dicts: [{page: int (1-based), text: str, chars: int}]
    \"\"\"
    raise NotImplementedError
"""

_EX3_SOLUTION = """\
def extract_pdf_text(pdf_bytes: bytes) -> list:
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ''
        pages.append({'page': i, 'text': text, 'chars': len(text)})
    return pages
"""

_EX3_CHECKS = """\
score, total = 0, 5
try:
    result = extract_pdf_text(_test_pdf)
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    score += 1; print("\\u2705 returns a list")

    assert len(result) == 1, f"Expected 1 page, got {len(result)}"
    score += 1; print("\\u2705 returns one entry per page")

    page = result[0]
    assert 'page' in page and 'text' in page and 'chars' in page, (
        f"Missing keys: {set(page.keys())}")
    score += 1; print("\\u2705 each entry has 'page', 'text', 'chars' keys")

    assert page['page'] == 1, f"Page number should be 1-based, got {page['page']}"
    score += 1; print("\\u2705 page numbering is 1-based")

    assert isinstance(page['text'], str), "text should be a string"
    assert page['chars'] == len(page['text']), (
        f"chars {page['chars']} != len(text) {len(page['text'])}")
    score += 1; print("\\u2705 chars equals len(text)")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX3 = nb([
    md("# Day 068 — Exercise 3: Extract PDF Text\n\n"
       "**What you'll build:** `extract_pdf_text(pdf_bytes) -> list[dict]` — "
       "page-by-page text extraction from a PDF using pypdf.\n\n"
       "**Why it matters:** Text-based PDFs are the most common document type in "
       "business workflows. pypdf extracts text instantly — no OCR, no model, "
       "no network. The per-page structure lets you detect scanned pages "
       "(chars == 0) and route them to an OCR fallback."),
    code(_EX3_GIVEN),
    md("## Task\n\nImplement `extract_pdf_text(pdf_bytes: bytes) -> list[dict]`:\n\n"
       "1. `reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))`\n"
       "2. For each page: `text = page.extract_text() or ''`\n"
       "3. Append `{'page': i, 'text': text, 'chars': len(text)}` (1-based page numbers)\n"
       "4. Return the list\n\n"
       "A minimal in-memory PDF is provided — no file system needed."),
    md("## Your Implementation"),
    code(_EX3_STUB),
    code(_EX3_SOLUTION),
    md("## Automated checks"),
    code(_EX3_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX3_SOLUTION + "```\n\n"
       "**Why `or ''`?** `page.extract_text()` returns `None` for pages that "
       "contain no text objects (image-only / scanned pages). Without the guard, "
       "`len(None)` raises a `TypeError`. The `or ''` converts `None` to an empty "
       "string, and `chars == 0` signals a scanned page that needs OCR fallback.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_03.ipynb", EX3)

# ── EXERCISE 4 — extract_numbers ─────────────────────────────────────────────
_EX4_GIVEN = """\
import re
"""

_EX4_STUB = """\
def extract_numbers(text: str) -> list:
    \"\"\"Parse all numeric values from OCR text.

    Handles integers, decimals, and comma-separated thousands (1,234.56).
    Strips commas before casting to float. Skips tokens that fail conversion.

    Args:
        text: raw OCR output string
    Returns:
        Sorted list of float values found in text
    \"\"\"
    raise NotImplementedError
"""

_EX4_SOLUTION = """\
def extract_numbers(text: str) -> list:
    pattern = r'\\b\\d{1,3}(?:,\\d{3})*(?:\\.\\d+)?|\\b\\d+(?:\\.\\d+)?\\b'
    raw = re.findall(pattern, text)
    result = []
    for s in raw:
        try:
            result.append(float(s.replace(',', '')))
        except ValueError:
            pass
    return sorted(result)
"""

_EX4_CHECKS = """\
score, total = 0, 5
try:
    # Basic integer
    result = extract_numbers('Total 42')
    assert 42.0 in result, f"Expected 42.0 in {result}"
    score += 1; print("\\u2705 extracts integer")

    # Decimal
    result = extract_numbers('Price $3.99')
    assert 3.99 in result, f"Expected 3.99 in {result}"
    score += 1; print("\\u2705 extracts decimal")

    # Comma-separated thousands
    result = extract_numbers('Revenue: 1,234.56')
    assert 1234.56 in result, f"Expected 1234.56 in {result}"
    score += 1; print("\\u2705 handles comma-separated thousands (1,234.56)")

    # Multiple numbers, sorted ascending
    text = 'Item1 $5.99  Item2 $3.50  Total $9.49'
    result = extract_numbers(text)
    assert result == sorted(result), f"Result not sorted: {result}"
    assert len(result) >= 3, f"Expected at least 3 numbers, got {result}"
    score += 1; print(f"\\u2705 returns sorted list: {result}")

    # Empty string → empty list
    empty = extract_numbers('')
    assert empty == [], f"Expected [], got {empty}"
    score += 1; print("\\u2705 empty text returns empty list")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX4 = nb([
    md("# Day 068 — Exercise 4: Extract Numbers from Text\n\n"
       "**What you'll build:** `extract_numbers(text) -> list[float]` — "
       "regex-based numeric extraction from raw OCR output.\n\n"
       "**Why it matters:** After OCR you have a raw string. For receipts, "
       "invoices, or financial documents you need the numbers: prices, quantities, "
       "totals. This function turns messy OCR output into a clean sorted list of "
       "floats that a downstream rule or LLM can reason over."),
    code(_EX4_GIVEN),
    md("## Task\n\nImplement `extract_numbers(text: str) -> list[float]`:\n\n"
       "1. Use `re.findall` with pattern matching `1,234.56` and `123.45`\n"
       "2. For each match: strip commas, cast to `float`\n"
       "3. Skip values that raise `ValueError`\n"
       "4. Return `sorted(result)`\n\n"
       "Pattern hint: `r'\\b\\d{1,3}(?:,\\d{3})*(?:\\.\\d+)?|\\b\\d+(?:\\.\\d+)?\\b'`"),
    md("## Your Implementation"),
    code(_EX4_STUB),
    code(_EX4_SOLUTION),
    md("## Automated checks"),
    code(_EX4_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX4_SOLUTION + "```\n\n"
       "**Why alternation (`|`) in the pattern?** The first branch handles "
       "comma-separated thousands (`1,234.56`). Without it, `findall` would "
       "match `1`, `,` (non-matching), `234.56` — splitting the number. "
       "Putting the longer match first in the alternation ensures it takes "
       "precedence when both branches could match.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_04.ipynb", EX4)

# ── EXERCISE 5 — read_document ────────────────────────────────────────────────
_EX5_GIVEN = _HELPER_SRC + "\n" + _MINIMAL_PDF_CODE + """
from PIL import ImageDraw
_receipt_img = Image.new('RGB', (250, 60), 'white')
_d = ImageDraw.Draw(_receipt_img)
_d.text((10, 10), 'Item $5.99', fill='black')
_d.text((10, 30), 'Total $7.50', fill='black')
"""

_EX5_STUB = """\
def read_document(source, source_type: str = 'image',
                  ocr_fn=None) -> dict:
    \"\"\"Unified document reader: OCR images or extract PDF text.

    For 'image':
        1. preprocess_for_ocr(source)
        2. ocr_image(preprocessed, ocr_fn)
        3. extract_numbers(text)
        Return: {text: str, numbers: list[float], chars: int}

    For 'pdf':
        extract_pdf_text(source)
        Return: {pages: list[dict], total_chars: int, page_count: int}

    Raises:
        ValueError for unknown source_type
    \"\"\"
    raise NotImplementedError
"""

_EX5_SOLUTION = """\
def read_document(source, source_type: str = 'image',
                  ocr_fn=None) -> dict:
    if source_type == 'image':
        preprocessed = preprocess_for_ocr(source)
        text = ocr_image(preprocessed, ocr_fn=ocr_fn)
        numbers = extract_numbers(text)
        return {'text': text, 'numbers': numbers, 'chars': len(text)}
    if source_type == 'pdf':
        pages = extract_pdf_text(source)
        return {
            'pages':       pages,
            'total_chars': sum(p['chars'] for p in pages),
            'page_count':  len(pages),
        }
    raise ValueError(
        f"Unknown source_type: {source_type!r}. Use 'image' or 'pdf'."
    )
"""

_EX5_CHECKS = """\
score, total = 0, 5
try:
    _mock_ocr = lambda img: 'Item $5.99\\nTotal $7.50'

    # Image path
    result = read_document(_receipt_img, source_type='image', ocr_fn=_mock_ocr)
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert 'text' in result and 'numbers' in result and 'chars' in result, (
        f"Missing keys: {set(result.keys())}")
    score += 1; print("\\u2705 image result has text/numbers/chars keys")

    assert result['text'] == 'Item $5.99\\nTotal $7.50'
    score += 1; print("\\u2705 image text matches mock output")

    assert 5.99 in result['numbers'] and 7.5 in result['numbers'], (
        f"Expected 5.99 and 7.5 in numbers: {result['numbers']}")
    score += 1; print(f"\\u2705 numbers extracted: {result['numbers']}")

    # PDF path
    pdf_result = read_document(_test_pdf, source_type='pdf')
    assert 'pages' in pdf_result and 'total_chars' in pdf_result and 'page_count' in pdf_result, (
        f"Missing keys: {set(pdf_result.keys())}")
    assert pdf_result['page_count'] == 1
    score += 1; print("\\u2705 pdf result has pages/total_chars/page_count keys")

    # Unknown source_type raises ValueError
    raised = False
    try:
        read_document(_receipt_img, source_type='audio')
    except ValueError:
        raised = True
    assert raised, "Unknown source_type should raise ValueError"
    score += 1; print("\\u2705 unknown source_type raises ValueError")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX5 = nb([
    md("# Day 068 — Exercise 5: Document Reader Pipeline\n\n"
       "**What you'll build:** `read_document(source, source_type, ocr_fn)` — "
       "the unified pipeline that dispatches to image OCR or PDF text extraction "
       "and returns structured output.\n\n"
       "**Why it matters:** One function that handles any document source type "
       "is the clean interface your downstream pipeline needs. The dict output "
       "is the input for Day 69's structured extraction step — Pydantic schemas "
       "on top of OCR text."),
    code(_EX5_GIVEN),
    md("## Task\n\nImplement `read_document(source, source_type='image', ocr_fn=None) -> dict`:\n\n"
       "- `'image'` path: `preprocess_for_ocr` → `ocr_image(ocr_fn=ocr_fn)` → "
       "`extract_numbers` → return `{text, numbers, chars}`\n"
       "- `'pdf'` path: `extract_pdf_text` → return `{pages, total_chars, page_count}`\n"
       "- Unknown `source_type` → raise `ValueError`\n\n"
       "Helper functions are provided in the given cell. All checks use mocks."),
    md("## Your Implementation"),
    code(_EX5_STUB),
    code(_EX5_SOLUTION),
    md("## Automated checks"),
    code(_EX5_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX5_SOLUTION + "```\n\n"
       "**Why `chars: int` in the image result?** Downstream callers often want "
       "to know if the OCR returned any text at all — `chars == 0` means the "
       "image had no readable text and the result should not be passed to a parser. "
       "The same signal (`chars == 0`) is used in the PDF path at the page level "
       "to detect scanned pages that need an OCR fallback.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_05.ipynb", EX5)

# ── PROJECT NOTEBOOK ──────────────────────────────────────────────────────────
PROJECT = nb([
    md("# Day 068 — Project: Document Reader\n\n"
       "## What You're Building\n\n"
       "`document_reader.py` — a `DocumentReader` class for extracting text and "
       "structured data from images and PDFs.\n\n"
       "**Deliverable:** A class combining Tesseract OCR (images) and pypdf "
       "(PDFs) with a clean mock-injection interface for testing.\n\n"
       "## Setup\n\n"
       "```bash\n"
       "brew install tesseract      # OCR binary\n"
       "pip install pytesseract pypdf  # already installed\n"
       "```\n\n"
       "## Design\n\n"
       "```\n"
       "DocumentReader\n"
       "  .__init__(ocr_fn=None)\n"
       "  .read_image(img, preprocess=True) → {text, numbers, chars, preprocess}\n"
       "  .read_pdf(pdf_bytes)              → {pages, total_chars, page_count}\n"
       "  .read(source, source_type)        → dispatches above\n"
       "```\n\n"
       "## Usage (with real Tesseract)\n\n"
       "```python\n"
       "from document_reader import DocumentReader\n"
       "from PIL import Image\n\n"
       "dr = DocumentReader()\n"
       "img = Image.open('receipt.png')\n"
       "result = dr.read_image(img)\n"
       "print(result['text'])\n"
       "print('Total:', max(result['numbers']))\n"
       "```"),
    code("# Your implementation here\n"
         "# Build DocumentReader and write it to document_reader.py\n"),
])
save(OUT / "project" / "project.ipynb", PROJECT)

# ── SOLUTION NOTEBOOK ─────────────────────────────────────────────────────────
_SOL_CELL1 = (
    f"_READER_SRC = {repr(_READER_SRC)}\n"
    "from pathlib import Path\n"
    "Path('document_reader.py').write_text(_READER_SRC, encoding='utf-8')\n"
    "print('document_reader.py written.')"
)

_SOL_CELL2 = """\
import io
import re
from PIL import Image, ImageDraw
from document_reader import DocumentReader, preprocess_for_ocr, extract_numbers, extract_pdf_text

# Mock OCR — no Tesseract required
_mock_ocr = lambda img: 'Coffee $3.50\\nSandwich $7.25\\nTOTAL $10.75'

dr = DocumentReader(ocr_fn=_mock_ocr)
img = Image.new('RGB', (300, 100), 'white')

# 1. preprocess_for_ocr produces grayscale
preprocessed = preprocess_for_ocr(img)
assert preprocessed.mode == 'L'
print("\\u2705 preprocess_for_ocr returns L-mode image")

# 2. read_image returns text/numbers/chars
result = dr.read_image(img)
assert 'text' in result and 'numbers' in result and 'chars' in result
print("\\u2705 read_image returns {text, numbers, chars}")

# 3. numbers extracted
assert 3.5 in result['numbers']
assert 10.75 in result['numbers']
print(f"\\u2705 numbers: {result['numbers']}")

# 4. extract_numbers standalone
nums = extract_numbers('Price $1,234.56 and $99.99')
assert 1234.56 in nums and 99.99 in nums
print(f"\\u2705 extract_numbers handles comma-thousands: {nums}")

# 5. read dispatches correctly
result2 = dr.read(img, source_type='image')
assert result2['text'] == result['text']
print("\\u2705 dr.read() dispatches to read_image for source_type='image'")

# 6. unknown source_type raises ValueError
raised = False
try:
    dr.read(img, source_type='video')
except ValueError:
    raised = True
assert raised
print("\\u2705 unknown source_type raises ValueError")

# 7. read_pdf from in-memory PDF
def _minimal_pdf_bytes():
    # Tiny valid single-page PDF
    stream = b'BT /F1 12 Tf 50 750 Td (Hello PDF) Tj ET'
    slen = len(stream)
    objs = {
        1: b'<< /Type /Catalog /Pages 2 0 R >>',
        2: b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        3: b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /Contents 4 0 R >>',
        4: f'<< /Length {slen} >>\\nstream\\n'.encode() + stream + b'\\nendstream',
    }
    buf = io.BytesIO()
    buf.write(b'%PDF-1.4\\n')
    offs = {}
    for num, ob in objs.items():
        offs[num] = buf.tell()
        buf.write(f'{num} 0 obj\\n'.encode()); buf.write(ob); buf.write(b'\\nendobj\\n')
    xp = buf.tell()
    buf.write(b'xref\\n'); buf.write(f'0 {len(objs)+1}\\n'.encode())
    buf.write(b'0000000000 65535 f \\n')
    for n in range(1, len(objs)+1):
        buf.write(f'{offs[n]:010d} 00000 n \\n'.encode())
    buf.write(f'trailer << /Size {len(objs)+1} /Root 1 0 R >>\\nstartxref\\n{xp}\\n%%EOF\\n'.encode())
    return buf.getvalue()

pdf_bytes = _minimal_pdf_bytes()
pdf_result = dr.read_pdf(pdf_bytes)
assert pdf_result['page_count'] == 1
assert isinstance(pdf_result['pages'], list)
print("\\u2705 read_pdf extracts 1 page from in-memory PDF")

# 8. extract_pdf_text page numbering
pages = extract_pdf_text(pdf_bytes)
assert pages[0]['page'] == 1
print("\\u2705 extract_pdf_text uses 1-based page numbering")

print("\\nOCR & Document AI complete!")
"""

SOLUTION = nb([
    md("# Day 068 — Solution: Document Reader"),
    code(_SOL_CELL1),
    code(_SOL_CELL2),
])
save(OUT / "project" / "solution" / "solution.ipynb", SOLUTION)
(OUT / "project" / "solution" / "document_reader.py").write_text(_READER_SRC)

print(f"Day {DAY} notebooks written to {OUT}")
print("  lessons/    day_068_lesson_01.yaml – lesson_05.yaml")
print("  exercises/  exercise_01 – exercise_05")
print("  project/    project.ipynb")
print("  project/solution/  solution.ipynb + document_reader.py")
