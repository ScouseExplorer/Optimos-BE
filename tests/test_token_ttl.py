from datetime import timedelta

from jose import jwt

from app.core.config import settings
from app.core.security import (
    MAX_TOKEN_LIFETIME_SECONDS,
    create_access_token,
    get_token_remaining_ttl,
)


def test_ttl_reflects_remaining_lifetime():
    token = create_access_token({"sub": "1"}, expires_delta=timedelta(minutes=10))
    assert 590 <= get_token_remaining_ttl(token) <= 600


def test_ttl_of_expired_token_is_minimum():
    token = create_access_token({"sub": "1"}, expires_delta=timedelta(minutes=-10))
    assert get_token_remaining_ttl(token) == 1


def test_ttl_of_unverifiable_token_is_minimum():
    forged = jwt.encode({"sub": "1", "exp": 4102444800}, "another-secret", algorithm=settings.ALGORITHM)
    assert get_token_remaining_ttl(forged) == 1
    assert get_token_remaining_ttl("not-a-jwt") == 1


def test_ttl_of_signed_token_without_exp_uses_max_lifetime():
    token = jwt.encode({"sub": "1"}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    assert get_token_remaining_ttl(token) == MAX_TOKEN_LIFETIME_SECONDS
