"""Image uploads re-written without metadata (US-085, NFR-010). A phone camera writes where and when a
photo was taken into the file; the licensing record needs the picture, not the location of the operator's
kitchen. EXIF, XMP, IPTC and text chunks are dropped; the ICC profile is kept so colours stay right; the
EXIF orientation is applied to the pixels first so the picture does not turn on its side."""

import warnings
from io import BytesIO
from typing import Any

from PIL import Image, ImageOps, JpegImagePlugin, UnidentifiedImageError

# 40 megapixels is generous for a phone photo (a 12 MP camera is a third of it). Pillow's own setting
# only warns at this figure and refuses at twice it, and the warning let an 80-megapixel PNG of a few
# hundred kilobytes decode to 600 MB in the worker (review finding, 21 Sep): the size in the header is
# checked here before a single pixel is decoded, and the warning is an error as a second fence.
MAX_PIXELS = 40_000_000
Image.MAX_IMAGE_PIXELS = MAX_PIXELS

_FORMATS = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG"}


class ImageUnreadableError(Exception):
    """The bytes carry an image signature but Pillow cannot decode them (truncated, bomb, corrupt)."""


def is_image(ext: str) -> bool:
    return ext in _FORMATS


def strip_metadata(data: bytes, ext: str) -> bytes:
    """Return the image re-encoded with only its pixels and colour profile."""
    fmt = _FORMATS[ext]
    try:
        # The filter is scoped here, not module-wide: a test runner or a library resets global filters.
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            source = Image.open(BytesIO(data))
        with source:
            width, height = source.size
            if width * height > MAX_PIXELS:
                raise ImageUnreadableError(f"{width}x{height} is more than {MAX_PIXELS} pixels")
            source.load()
            icc = source.info.get("icc_profile")
            image = ImageOps.exif_transpose(source) or source
            # Pillow writes what it finds in `info` (comment, XMP, EXIF) unless told otherwise.
            image.info = {}
            out = BytesIO()
            if fmt == "JPEG":
                if image.mode not in ("RGB", "L", "CMYK"):
                    image = image.convert("RGB")
                # The source's quantisation tables and subsampling are reused, so a phone photo is not
                # degraded a second time by the re-encode.
                options: dict[str, Any] = {}
                tables = getattr(source, "quantization", None)
                if tables:
                    options["qtables"] = tables
                sampling = JpegImagePlugin.get_sampling(source)
                if sampling >= 0:
                    options["subsampling"] = sampling
                image.save(out, "JPEG", icc_profile=icc, **options)
            else:
                image.save(out, "PNG", icc_profile=icc, optimize=False)
            return out.getvalue()
    except (
        UnidentifiedImageError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        OSError,
        ValueError,
    ) as exc:
        raise ImageUnreadableError(str(exc)) from exc


__all__ = ["MAX_PIXELS", "ImageUnreadableError", "is_image", "strip_metadata"]
