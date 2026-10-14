"""US-099: the clamd INSTREAM client against a fake clamd on a local socket (standard library only)."""

import socket
import struct
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager

import pytest

from app.infra.clamd import CHUNK, ClamdClient, ScannerError

Handler = Callable[[socket.socket, bytes], None]


def _read_stream(conn: socket.socket) -> tuple[bytes, list[int]]:
    """What a real clamd reads: the command, then length-prefixed chunks up to a zero length."""
    f = conn.makefile("rb")
    command = b""
    while not command.endswith(b"\0"):
        command += f.read(1)
    body, sizes = b"", []
    while True:
        (size,) = struct.unpack(">I", f.read(4))
        if size == 0:
            break
        sizes.append(size)
        body += f.read(size)
    assert command == b"zINSTREAM\0"
    return body, sizes


@contextmanager
def fake_clamd(
    reply: bytes | None, *, hang: bool = False
) -> Iterator[tuple[int, list[bytes], list[list[int]]]]:
    """A one-connection-at-a-time fake. `reply` is sent after the stream; `hang` never answers."""
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(4)
    server.settimeout(5)
    received: list[bytes] = []
    chunks: list[list[int]] = []
    stop = threading.Event()

    def serve() -> None:
        while not stop.is_set():
            try:
                conn, _ = server.accept()
            except OSError:
                return
            with conn:
                try:
                    body, sizes = _read_stream(conn)
                except (OSError, struct.error):
                    continue
                received.append(body)
                chunks.append(sizes)
                if hang:
                    stop.wait(3)
                elif reply is not None:
                    conn.sendall(reply)

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    try:
        yield server.getsockname()[1], received, chunks
    finally:
        stop.set()
        server.close()
        thread.join(5)


def test_clean_file_and_the_stream_framing() -> None:
    data = b"x" * (CHUNK * 2 + 10)
    with fake_clamd(b"stream: OK\0") as (port, received, chunks):
        result = ClamdClient("127.0.0.1", port, 3).scan(data)
    assert result.infected is False and result.signature is None
    assert received == [data]  # the whole file arrived intact
    assert chunks == [[CHUNK, CHUNK, 10]]  # in chunks of at most 64 KiB


def test_infected_file_names_the_signature() -> None:
    with fake_clamd(b"stream: Eicar-Signature FOUND\0") as (port, _, _):
        result = ClamdClient("127.0.0.1", port, 3).scan(b"eicar")
    assert result.infected is True and result.signature == "Eicar-Signature"


def test_an_empty_file_is_still_sent_and_answered() -> None:
    with fake_clamd(b"stream: OK\0") as (port, received, chunks):
        assert ClamdClient("127.0.0.1", port, 3).scan(b"").infected is False
    assert received == [b""] and chunks == [[]]


@pytest.mark.parametrize(
    "reply",
    [b"INSTREAM size limit exceeded. ERROR\0", b"\0", b"something odd\0", b"stream: OK but not\0"],
)
def test_an_error_or_unexpected_reply_is_a_scanner_error(reply: bytes) -> None:
    with fake_clamd(reply) as (port, _, _), pytest.raises(ScannerError):
        ClamdClient("127.0.0.1", port, 3).scan(b"data")


def test_a_closed_connection_without_a_reply_is_a_scanner_error() -> None:
    with fake_clamd(None) as (port, _, _), pytest.raises(ScannerError):
        ClamdClient("127.0.0.1", port, 3).scan(b"data")


def test_a_clamd_that_never_answers_times_out() -> None:
    with fake_clamd(None, hang=True) as (port, _, _), pytest.raises(ScannerError):
        ClamdClient("127.0.0.1", port, 0.4).scan(b"data")


def test_a_refused_connection_is_a_scanner_error() -> None:
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()  # nothing listens here now
    with pytest.raises(ScannerError):
        ClamdClient("127.0.0.1", port, 1).scan(b"data")


def _ping_server(reply: bytes) -> tuple[socket.socket, list[bytes]]:
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    server.settimeout(5)
    seen: list[bytes] = []

    def serve() -> None:
        conn, _ = server.accept()
        with conn:
            seen.append(conn.recv(16))
            conn.sendall(reply)

    threading.Thread(target=serve, daemon=True).start()
    return server, seen


def test_ping_sends_zping_and_accepts_pong() -> None:
    server, seen = _ping_server(b"PONG\0")
    ClamdClient("127.0.0.1", server.getsockname()[1], 3).ping()
    server.close()
    assert seen == [b"zPING\0"]


def test_ping_with_another_reply_or_no_listener_is_a_scanner_error() -> None:
    server, _ = _ping_server(b"nope\0")
    port = server.getsockname()[1]
    with pytest.raises(ScannerError):
        ClamdClient("127.0.0.1", port, 3).ping()
    server.close()  # nothing listens here now
    with pytest.raises(ScannerError):
        ClamdClient("127.0.0.1", port, 1).ping()
