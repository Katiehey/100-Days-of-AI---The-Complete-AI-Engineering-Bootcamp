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
    mock = lambda img: "Hello World\n$12.99"
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
    pattern = r"\b\d{1,3}(?:,\d{3})*(?:\.\d+)?|\b\d+(?:\.\d+)?\b"
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
