import pytest

from app.domain.uploads import UploadRejected, check_magic_bytes, check_name_and_type, extension_of


def test_extension_and_type() -> None:
    assert extension_of("Dir/My File.PDF") == ".pdf"
    assert check_name_and_type("a.jpeg", "image/jpeg") == ".jpeg"
    assert check_name_and_type("a.txt", "application/octet-stream") == ".txt"
    with pytest.raises(UploadRejected):
        check_name_and_type("a.exe", "application/octet-stream")
    with pytest.raises(UploadRejected):
        check_name_and_type("a.pdf", "image/png")
    with pytest.raises(UploadRejected):
        check_name_and_type("noext", None)


def test_magic_bytes() -> None:
    check_magic_bytes(".pdf", b"%PDF-1.7")
    check_magic_bytes(".png", b"\x89PNG\r\n\x1a\n....")
    check_magic_bytes(".jpg", b"\xff\xd8\xff\xe0")
    check_magic_bytes(".txt", b"hello\n")
    with pytest.raises(UploadRejected):
        check_magic_bytes(".pdf", b"PK\x03\x04")
    with pytest.raises(UploadRejected):
        check_magic_bytes(".txt", b"\x00\x01binary")
