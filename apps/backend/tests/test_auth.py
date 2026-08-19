from pydantic import ValidationError
import pytest

from app.auth.passwords import hash_password, normalize_username, verify_password
from app.schemas import RegisterRequest


def test_password_hash_is_salted_and_verifiable():
    first = hash_password("correct horse battery staple")
    second = hash_password("correct horse battery staple")

    assert first != second
    assert "correct horse battery staple" not in first
    assert verify_password("correct horse battery staple", first) is True
    assert verify_password("wrong password", first) is False
    assert verify_password("anything", "malformed") is False


def test_username_normalization_and_registration_validation():
    assert normalize_username("  Alice.Example  ") == "alice.example"
    assert RegisterRequest(username="alice-1", password="long-enough").username == "alice-1"
    with pytest.raises(ValidationError):
        RegisterRequest(username="invalid name", password="long-enough")
    with pytest.raises(ValidationError):
        RegisterRequest(username="alice", password="short")
