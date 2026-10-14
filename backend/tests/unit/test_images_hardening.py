"""US-098: image decode memory. At most N images are decoded at once and a waiter times out cleanly; the
in-place orientation turn gives the same pixels as the copying one; the pixel cap still refuses an oversized
image before a single pixel is decoded."""

import threading
import time
from io import BytesIO

import pytest
from PIL import Image, ImageOps, PngImagePlugin

from app.infra import images
from app.infra.images import ImageBusyError, ImageUnreadableError, strip_metadata


def _png(width: int = 7, height: int = 4, orientation: int | None = None) -> bytes:
    image = Image.new("RGB", (width, height))
    image.putdata(
        [(x * 30 % 256, y * 60 % 256, (x + y) * 10 % 256) for y in range(height) for x in range(width)]
    )
    exif = Image.Exif()
    if orientation is not None:
        exif[0x0112] = orientation
    out = BytesIO()
    image.save(out, "PNG", exif=exif)
    return out.getvalue()


def test_at_most_the_configured_number_of_images_are_decoded_at_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(images, "_SLOTS", threading.BoundedSemaphore(2))
    lock = threading.Lock()
    running = 0
    peak = 0

    def slow(data: bytes, fmt: str) -> bytes:
        nonlocal running, peak
        with lock:
            running += 1
            peak = max(peak, running)
        time.sleep(0.05)
        with lock:
            running -= 1
        return data

    monkeypatch.setattr(images, "_strip", slow)
    threads = [threading.Thread(target=strip_metadata, args=(b"x", ".png")) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert peak == 2


def test_a_caller_that_cannot_get_a_slot_times_out_with_a_clean_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    slots = threading.BoundedSemaphore(1)
    monkeypatch.setattr(images, "_SLOTS", slots)
    monkeypatch.setattr(images, "WAIT_SECONDS", 0.05)
    slots.acquire()
    started = time.monotonic()
    with pytest.raises(ImageBusyError):
        strip_metadata(_png(), ".png")
    assert time.monotonic() - started < 2
    slots.release()
    assert Image.open(BytesIO(strip_metadata(_png(), ".png"))).size == (7, 4)  # the slot is usable again


def test_a_failed_decode_gives_its_slot_back(monkeypatch: pytest.MonkeyPatch) -> None:
    slots = threading.BoundedSemaphore(1)
    monkeypatch.setattr(images, "_SLOTS", slots)
    monkeypatch.setattr(images, "WAIT_SECONDS", 0.05)
    with pytest.raises(ImageUnreadableError):
        strip_metadata(b"\x89PNG\r\n\x1a\n" + b"\x00" * 40, ".png")
    assert slots.acquire(blocking=False)


@pytest.mark.parametrize("orientation", range(1, 9))
def test_in_place_orientation_gives_the_same_pixels_as_the_copying_turn(orientation: int) -> None:
    original = _png(orientation=orientation)
    expected = ImageOps.exif_transpose(Image.open(BytesIO(original)))
    assert expected is not None
    stored = Image.open(BytesIO(strip_metadata(original, ".png")))
    assert stored.size == expected.size
    assert list(stored.convert("RGB").getdata()) == list(expected.convert("RGB").getdata())
    assert 0x0112 not in stored.getexif()


def test_the_pixel_cap_refuses_an_oversized_image_before_any_pixel_is_decoded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    out = BytesIO()
    Image.new("1", (6800, 6700)).save(out, "PNG", optimize=True)  # 45.6 MP > MAX_PIXELS, a few KB on the wire
    assert 6800 * 6700 > images.MAX_PIXELS

    def decoded(*_: object, **__: object) -> None:
        raise AssertionError("pixels were decoded")

    monkeypatch.setattr(PngImagePlugin.PngImageFile, "load", decoded)
    with pytest.raises(ImageUnreadableError, match="exceeds limit|more than"):
        strip_metadata(out.getvalue(), ".png")
