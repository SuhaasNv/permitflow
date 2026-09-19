"""Upload validation rules (SEC-005): extension + MIME allowlist, size cap, magic bytes."""

from dataclasses import dataclass

# ruff: noqa: N818 - raised as a value object and translated to BadRequest by the service

ALLOWED: dict[str, tuple[str, ...]] = {
    ".pdf": ("application/pdf",),
    ".png": ("image/png",),
    ".jpg": ("image/jpeg",),
    ".jpeg": ("image/jpeg",),
    ".txt": ("text/plain",),
}
ALLOWED_LABEL = "PDF, PNG, JPG or TXT"


@dataclass(frozen=True)
class UploadRejected(Exception):
    reason: str
    message: str


def extension_of(filename: str) -> str:
    name = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    if "." not in name:
        return ""
    return "." + name.rsplit(".", 1)[-1].lower()


def check_name_and_type(filename: str, content_type: str | None) -> str:
    """Return the normalised extension or raise UploadRejected."""
    ext = extension_of(filename)
    if ext not in ALLOWED:
        raise UploadRejected("unsupported_format", f"Only {ALLOWED_LABEL} files are accepted.")
    declared = (content_type or "").split(";")[0].strip().lower()
    if declared and declared not in ALLOWED[ext] and declared != "application/octet-stream":
        raise UploadRejected("unsupported_format", f"Only {ALLOWED_LABEL} files are accepted.")
    return ext


def check_magic_bytes(ext: str, head: bytes) -> None:
    """The first bytes must match the extension; a renamed .docx is rejected here."""
    ok = {
        ".pdf": head.startswith(b"%PDF-"),
        ".png": head.startswith(b"\x89PNG\r\n\x1a\n"),
        ".jpg": head.startswith(b"\xff\xd8\xff"),
        ".jpeg": head.startswith(b"\xff\xd8\xff"),
        ".txt": _looks_like_text(head),
    }[ext]
    if not ok:
        raise UploadRejected(
            "content_mismatch", "The file content does not match its type. Save it again and retry."
        )


def _looks_like_text(head: bytes) -> bool:
    if not head:
        return True
    if b"\x00" in head:
        return False
    try:
        head.decode("utf-8")
    except UnicodeDecodeError as exc:
        # The sample is a fixed-length prefix: a multibyte character cut at its end is not a bad file.
        return exc.start >= len(head) - 3
    return True


def canonical_content_type(ext: str) -> str:
    return ALLOWED[ext][0]


def too_large_message(limit_bytes: int) -> str:
    return f"The file is larger than {limit_bytes // (1024 * 1024)} MB."
