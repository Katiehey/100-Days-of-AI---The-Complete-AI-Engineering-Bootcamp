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
