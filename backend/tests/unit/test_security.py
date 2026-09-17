import uuid

import pytest

from app.core.errors import Unauthorized
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hash_roundtrip() -> None:
    h = hash_password("s3cret")
    assert h.startswith("$argon2")
    assert verify_password("s3cret", h)
    assert not verify_password("other", h)
    assert not verify_password("s3cret", "garbage")


def test_token_roundtrip() -> None:
    uid = uuid.uuid4()
    token, _ = create_access_token(uid, "officer")
    payload = decode_access_token(token)
    assert payload["sub"] == str(uid)
    assert payload["role"] == "officer"


def test_tampered_token_rejected() -> None:
    token, _ = create_access_token(uuid.uuid4(), "operator")
    with pytest.raises(Unauthorized):
        decode_access_token(token[:-2] + "xx")
