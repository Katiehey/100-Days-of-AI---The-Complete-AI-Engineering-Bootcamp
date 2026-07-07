"""
Render slide PNGs from a YAML lesson outline.
Called by lesson_build.py — not usually run directly.

Usage (standalone):
    conda activate ai-course
    python 00_pipeline/slide_gen.py 00_pipeline/lessons/day_001_lesson_01.yaml
"""

import os
import sys
import textwrap

import yaml
from PIL import Image, ImageDraw, ImageFont

# ── Canvas ───────────────────────────────────────────────────────────────────
W, H = 1280, 720

# ── Colour palette (dark theme) ──────────────────────────────────────────────
C_BG        = (15,  23,  42)    # #0f172a  background
C_SURFACE   = (30,  41,  59)    # #1e293b  code block surface
C_BORDER    = (51,  65,  85)    # #334155  subtle border
C_ACCENT    = (99,  102, 241)   # #6366f1  indigo — labels, underlines
C_PRIMARY   = (241, 245, 249)   # #f1f5f9  main text
C_SECONDARY = (148, 163, 184)   # #94a3b8  body / subdued
C_DIM       = (71,  85,  105)   # #475569  branding / hints
C_AMBER     = (245, 158, 11)    # #f59e0b  exercise
C_EMERALD   = (16,  185, 129)   # #10b981  solution

# ── Fonts ────────────────────────────────────────────────────────────────────
_FONT_REG  = "/System/Library/Fonts/Helvetica.ttc"
_FONT_MONO = "/System/Library/Fonts/Menlo.ttc"

# PiP safe zone — keep content away from bottom-right corner
_CONTENT_MAX_X = 960   # PiP starts at x=1060
_CONTENT_MAX_Y = 640


def _f(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default(size=size)


def _reg(size: int)  -> ImageFont.FreeTypeFont: return _f(_FONT_REG,  size)
def _mono(size: int) -> ImageFont.FreeTypeFont: return _f(_FONT_MONO, size)


# ── Drawing helpers ───────────────────────────────────────────────────────────

def _base() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img  = Image.new("RGB", (W, H), C_BG)
    draw = ImageDraw.Draw(img)
    return img, draw


def _label(draw: ImageDraw.ImageDraw, text: str,
           color: tuple = C_ACCENT, y: int = 38) -> None:
    draw.text((60, y), text.upper(), font=_reg(15), fill=color)


def _heading(draw: ImageDraw.ImageDraw, text: str,
             y: int = 72, color: tuple = C_PRIMARY, size: int = 44) -> int:
    """Draw heading + accent underline. Returns y after underline."""
    font = _reg(size)
    draw.text((60, y), text, font=font, fill=color)
    bbox   = font.getbbox(text)
    line_y = y + bbox[3] + 10
    draw.rectangle([60, line_y, min(60 + bbox[2], _CONTENT_MAX_X), line_y + 3],
                   fill=C_ACCENT)
    return line_y + 24


def _wrap_text(text: str, size: int, max_px: int = 900) -> list[str]:
    """Wrap text so each line fits within max_px pixels."""
    font   = _reg(size)
    words  = text.split()
    lines, current = [], ""
    for word in words:
        test = f"{current} {word}".strip()
        if font.getlength(test) <= max_px:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _body(draw: ImageDraw.ImageDraw, text: str, y: int,
          size: int = 23, color: tuple = C_SECONDARY,
          max_px: int = 900, line_gap: int = 10) -> int:
    font = _reg(size)
    for para in text.split("\n"):
        for line in (_wrap_text(para.strip(), size, max_px) if para.strip() else [""]):
            draw.text((60, y), line, font=font, fill=color)
            y += size + line_gap
        y += 6
    return y


def _bullets(draw: ImageDraw.ImageDraw, items: list[str], y: int,
             size: int = 22, color: tuple = C_PRIMARY) -> int:
    font = _reg(size)
    for item in items:
        draw.text((60, y), "·", font=_reg(size + 2), fill=C_ACCENT)
        for i, line in enumerate(_wrap_text(item, size, max_px=840)):
            draw.text((88, y), line, font=font, fill=color)
            y += size + 8
        y += 6
    return y


def _code_block(draw: ImageDraw.ImageDraw, code: str, y: int,
                x: int = 60, size: int = 17) -> int:
    font    = _mono(size)
    lines   = code.rstrip().split("\n")
    pad     = 18
    line_h  = size + 8
    block_w = _CONTENT_MAX_X - x
    block_h = len(lines) * line_h + pad * 2

    draw.rectangle([x, y, x + block_w, y + block_h],
                   fill=C_SURFACE, outline=C_BORDER, width=1)
    cy = y + pad
    for line in lines:
        draw.text((x + pad, cy), line, font=font, fill=C_PRIMARY)
        cy += line_h
    return y + block_h + 20


def _branding(draw: ImageDraw.ImageDraw, day: str, lesson: str) -> None:
    draw.text((60, H - 34),
              f"100 Days of AI  ·  Day {day}  ·  Lesson {lesson}",
              font=_reg(14), fill=C_DIM)


# ── Slide renderers ───────────────────────────────────────────────────────────

def _slide_title(meta: dict, slide: dict) -> Image.Image:
    img, draw = _base()
    day, les  = meta["day"], meta["lesson"]

    tag_font  = _reg(17)
    head_font = _reg(52)
    sub_font  = _reg(28)

    heading    = slide.get("heading",    meta.get("title", ""))
    subheading = slide.get("subheading", "")

    y = 240
    draw.text((60, y), f"DAY {day}  ·  LESSON {les}",
              font=tag_font, fill=C_ACCENT)
    y += 36
    draw.text((60, y), heading, font=head_font, fill=C_PRIMARY)
    y += 64
    if subheading:
        draw.text((60, y), subheading, font=sub_font, fill=C_SECONDARY)

    _branding(draw, day, les)
    return img


def _slide_concept(meta: dict, slide: dict) -> Image.Image:
    img, draw = _base()
    _label(draw, slide.get("label", "Concept"))
    y = _heading(draw, slide["heading"])
    y += 20
    if "body" in slide:
        y = _body(draw, slide["body"], y)
        y += 10
    if "bullets" in slide:
        _bullets(draw, slide["bullets"], y)
    _branding(draw, meta["day"], meta["lesson"])
    return img


def _slide_how(meta: dict, slide: dict) -> Image.Image:
    slide = {**slide, "label": slide.get("label", "How It Works")}
    return _slide_concept(meta, slide)


def _slide_code(meta: dict, slide: dict) -> Image.Image:
    img, draw = _base()
    _label(draw, slide.get("label", "Code"))
    y = _heading(draw, slide["heading"])
    y += 20
    if "body" in slide:
        y = _body(draw, slide["body"], y, size=21)
        y += 14
    if "code" in slide:
        _code_block(draw, slide["code"], y)
    _branding(draw, meta["day"], meta["lesson"])
    return img


def _slide_exercise(meta: dict, slide: dict) -> Image.Image:
    img, draw = _base()
    _label(draw, "Exercise", color=C_AMBER)
    y = _heading(draw, slide.get("heading", "Your Turn"), color=C_AMBER)
    y += 20
    if "prompt" in slide:
        y = _body(draw, slide["prompt"], y, size=23, color=C_PRIMARY)
        y += 14
    if "hint" in slide:
        _body(draw, f"Hint: {slide['hint']}", y, size=19, color=C_DIM)
    _branding(draw, meta["day"], meta["lesson"])
    return img


def _slide_solution(meta: dict, slide: dict) -> Image.Image:
    img, draw = _base()
    _label(draw, "Solution", color=C_EMERALD)
    y = _heading(draw, slide.get("heading", "Solution"), color=C_EMERALD)
    y += 20
    if "body" in slide:
        y = _body(draw, slide["body"], y, size=21, color=C_SECONDARY)
        y += 14
    if "code" in slide:
        _code_block(draw, slide["code"], y)
    _branding(draw, meta["day"], meta["lesson"])
    return img


def _slide_summary(meta: dict, slide: dict) -> Image.Image:
    img, draw = _base()
    _label(draw, "Summary")
    y = _heading(draw, slide.get("heading", "Key Takeaways"))
    y += 20
    if "bullets" in slide:
        _bullets(draw, slide["bullets"], y, size=23)
    _branding(draw, meta["day"], meta["lesson"])
    return img


def _slide_project(meta: dict, slide: dict) -> Image.Image:
    img, draw = _base()
    C_PROJECT = (168, 85, 247)   # #a855f7  purple

    _label(draw, f"Day {meta['day']} Project", color=C_PROJECT)
    y = _heading(draw, slide.get("heading", "Day Project"), color=C_PROJECT)
    y += 20

    if "description" in slide:
        y = _body(draw, slide["description"], y, size=23, color=C_PRIMARY)
        y += 14

    if "requirements" in slide:
        _label(draw, "Requirements", color=C_PROJECT, y=y)
        y += 26
        _bullets(draw, slide["requirements"], y, size=21, color=C_SECONDARY)

    # Bottom instruction strip
    strip_y = H - 80
    draw.rectangle([0, strip_y, W, strip_y + 1], fill=C_PROJECT)
    draw.text((60, strip_y + 12),
              f"Open: 00_warmup/day_{meta['day']}/project/project.ipynb  ·  "
              f"Solution unlocked after you finish",
              font=_reg(15), fill=C_DIM)

    _branding(draw, meta["day"], meta["lesson"])
    return img


_RENDERERS = {
    "title":        _slide_title,
    "concept":      _slide_concept,
    "how_it_works": _slide_how,
    "code":         _slide_code,
    "exercise":     _slide_exercise,
    "solution":     _slide_solution,
    "summary":      _slide_summary,
    "project":      _slide_project,
}


# ── Public API ────────────────────────────────────────────────────────────────

def generate_slides(yaml_path: str, output_dir: str) -> list[str]:
    """Generate slide PNGs. Returns ordered list of PNG file paths."""
    with open(yaml_path, encoding="utf-8") as f:
        lesson = yaml.safe_load(f)

    meta = {
        "day":    str(lesson["day"]).zfill(3),
        "lesson": str(lesson["lesson"]).zfill(2),
        "title":  lesson["title"],
    }
    os.makedirs(output_dir, exist_ok=True)

    paths = []
    for i, slide in enumerate(lesson["slides"], 1):
        stype    = slide.get("type", "concept")
        renderer = _RENDERERS.get(stype, _slide_concept)
        img      = renderer(meta, slide)
        path     = os.path.join(output_dir, f"slide_{i:03d}.png")
        img.save(path)
        print(f"  {i:03d} [{stype:12s}]  {path}")
        paths.append(path)

    return paths


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    _yaml  = sys.argv[1]
    _stem  = os.path.splitext(os.path.basename(_yaml))[0]
    _out   = os.path.join(os.path.dirname(_yaml), "..", "slides", _stem)
    _out   = os.path.abspath(_out)

    print(f"Generating slides → {_out}\n")
    _paths = generate_slides(_yaml, _out)
    print(f"\nDone. {len(_paths)} slides.")
