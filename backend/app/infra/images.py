"""Image uploads re-written without metadata (US-085, NFR-010). A phone camera writes where and when a
photo was taken into the file; the licensing record needs the picture, not the location of the operator's
kitchen. EXIF, XMP, IPTC and text chunks are dropped; the ICC profile is kept so colours stay right; the
EXIF orientation is applied to the pixels first so the picture does not turn on its side."""

from io import BytesIO
from typing import Any

from PIL import Image, ImageOps, JpegImagePlugin, UnidentifiedImageError

# Pillow refuses images past twice this and warns from it; 40 megapixels is generous for a phone photo
# and keeps the re-encode of a decompression bomb from taking the worker with it.
Image.MAX_IMAGE_PIXELS = 40_000_000

_FORMATS = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG"}


class ImageUnreadableError(Exception):
    """The bytes carry an image signature but Pillow cannot decode them (truncated, bomb, corrupt)."""


def is_image(ext: str) -> bool:
    return ext in _FORMATS


def strip_metadata(data: bytes, ext: str) -> bytes:
    """Return the image re-encoded with only its pixels and colour profile."""
    fmt = _FORMATS[ext]
    try:
        with Image.open(BytesIO(data)) as source:
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
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError) as exc:
        raise ImageUnreadableError(str(exc)) from exc


__all__ = ["ImageUnreadableError", "is_image", "strip_metadata"]
