"""A small clamd client over TCP: the INSTREAM command (US-099, ADR-017). Standard library only.

The null-terminated `zINSTREAM` form: the file goes as length-prefixed chunks, a zero length ends it, and
clamd answers `stream: OK`, `stream: <signature> FOUND` or `<reason> ERROR`. Anything else, a refused
connection, a timeout or an early close is a `ScannerError`: the caller never treats it as clean.
"""

import socket
import struct
from dataclasses import dataclass

from app.core.settings import get_settings

CHUNK = 64 * 1024
_MAX_REPLY = 4096


class ScannerError(Exception):
    """clamd was unreachable, timed out or answered with an error."""


@dataclass(frozen=True)
class ScanResult:
    infected: bool
    signature: str | None = None


class ClamdClient:
    def __init__(self, host: str, port: int, timeout: float) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout

    def scan(self, data: bytes) -> ScanResult:
        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
                sock.settimeout(self.timeout)
                sock.sendall(b"zINSTREAM\0")
                for start in range(0, len(data), CHUNK):
                    chunk = data[start : start + CHUNK]
                    sock.sendall(struct.pack(">I", len(chunk)) + chunk)
                sock.sendall(struct.pack(">I", 0))
                reply = self._read_reply(sock)
        except (OSError, ValueError) as exc:  # includes timeouts and refused connections
            raise ScannerError(f"clamd connection failed: {type(exc).__name__}") from exc
        return _parse(reply)

    @staticmethod
    def _read_reply(sock: socket.socket) -> str:
        buf = b""
        while len(buf) < _MAX_REPLY:
            part = sock.recv(1024)
            if not part:
                break
            buf += part
            if b"\0" in buf or b"\n" in buf:
                break
        return buf.split(b"\0", 1)[0].decode("utf-8", "replace").strip()


def _parse(reply: str) -> ScanResult:
    if not reply or reply.endswith("ERROR"):
        raise ScannerError(f"clamd error: {reply[:120] or 'empty reply'}")
    if reply.endswith("FOUND"):
        signature = reply.removeprefix("stream:").removesuffix("FOUND").strip()
        return ScanResult(infected=True, signature=signature[:120] or "unknown")
    if reply.endswith("OK"):
        return ScanResult(infected=False)
    raise ScannerError(f"clamd unexpected reply: {reply[:120]}")


def client_from_settings() -> ClamdClient:
    s = get_settings()
    return ClamdClient(s.clamd_host, s.clamd_port, s.clamd_timeout_seconds)
