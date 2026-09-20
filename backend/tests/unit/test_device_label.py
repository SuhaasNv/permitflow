"""Device labels from User-Agent strings (US-093): browser and device, never the header itself."""

import pytest

from app.domain.device_label import MAX_LABEL, UNKNOWN_DEVICE, device_label

CASES = [
    (
        "Mozilla/5.0 (iPad; CPU OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/17.4 Mobile/15E148 Safari/604.1",
        "Safari on iPad",
    ),
    (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "CriOS/128.0.0.0 Mobile/15E148 Safari/604.1",
        "Chrome on iPhone",
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36",
        "Chrome on Mac",
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0",
        "Edge on Windows",
    ),
    ("Mozilla/5.0 (X11; Linux x86_64; rv:129.0) Gecko/20100101 Firefox/129.0", "Firefox on Linux"),
    (
        "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) "
        "SamsungBrowser/25.0 Chrome/121.0.0.0 Mobile Safari/537.36",
        "Samsung Internet on Android",
    ),
    ("python-httpx/0.27.0", UNKNOWN_DEVICE),
    ("", UNKNOWN_DEVICE),
    (None, UNKNOWN_DEVICE),
    ("Mozilla/5.0 (Windows NT 10.0)", "Browser on Windows"),
    ("Chrome/128.0", "Chrome"),
]


@pytest.mark.parametrize(("ua", "expected"), CASES)
def test_device_label(ua: str | None, expected: str) -> None:
    label = device_label(ua)
    assert label == expected
    assert len(label) <= MAX_LABEL
    assert "Mozilla" not in label
