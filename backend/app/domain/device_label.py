"""A short, human device label from a User-Agent string (US-093). Pure. The raw header is never stored:
the label names the browser and the kind of device, enough for "signed in on Safari on iPad" and
nothing that identifies the person or the machine (NFR-019)."""

UNKNOWN_DEVICE = "Unknown device"
MAX_LABEL = 60

# Order matters: the first match wins, and the specific tokens come before the generic ones.
_DEVICES: tuple[tuple[str, str], ...] = (
    ("ipad", "iPad"),
    ("iphone", "iPhone"),
    ("android", "Android"),
    ("windows", "Windows"),
    ("cros", "Chromebook"),
    ("macintosh", "Mac"),
    ("mac os", "Mac"),
    ("linux", "Linux"),
)
_BROWSERS: tuple[tuple[str, str], ...] = (
    ("edg/", "Edge"),
    ("edga/", "Edge"),
    ("edgios/", "Edge"),
    ("opr/", "Opera"),
    ("samsungbrowser/", "Samsung Internet"),
    ("firefox/", "Firefox"),
    ("fxios/", "Firefox"),
    ("crios/", "Chrome"),
    ("chrome/", "Chrome"),
    ("safari/", "Safari"),
)


def device_label(user_agent: str | None) -> str:
    """`Safari on iPad`, `Chrome on Mac`, `Firefox on Windows`; the device alone or the browser alone
    when only one is recognisable; `Unknown device` otherwise (scripts, test clients)."""
    ua = (user_agent or "").lower()
    if not ua.strip():
        return UNKNOWN_DEVICE
    # Newer iPads announce themselves as a Mac with touch support; the "Mobile" token still marks them.
    device = next((name for token, name in _DEVICES if token in ua), None)
    browser = next((name for token, name in _BROWSERS if token in ua), None)
    if device and browser:
        return f"{browser} on {device}"[:MAX_LABEL]
    if device:
        return f"Browser on {device}"[:MAX_LABEL]
    if browser:
        return browser[:MAX_LABEL]
    return UNKNOWN_DEVICE


__all__ = ["MAX_LABEL", "UNKNOWN_DEVICE", "device_label"]
