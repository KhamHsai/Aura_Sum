import pytest
import time
from datetime import timedelta
import jwt
from app.config import settings
from app.utils.token_utils import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_refresh_token,
)

# Enforce a specific test key for local test isolation if not already present
settings.JWT_SECRET_KEY = "test_key_for_jwt_token_utilities_testing_only"
settings.JWT_ALGORITHM = "HS256"

# 1. Access token creation returns a string
def test_create_access_token_returns_string():
    token = create_access_token(user_id=123)
    assert isinstance(token, str)

# 2. Access token decodes successfully
def test_access_token_decodes_successfully():
    token = create_access_token(user_id=123)
    payload = decode_token(token)
    assert payload is not None

# 3. Access token payload contains the correct sub
def test_access_token_contains_correct_sub():
    token = create_access_token(user_id=123)
    payload = decode_token(token)
    assert payload["sub"] == "123"

# 4. Access token payload contains type = access
def test_access_token_contains_type_access():
    token = create_access_token(user_id=123)
    payload = decode_token(token)
    assert payload["type"] == "access"

# 5. Refresh token creation returns a string
def test_create_refresh_token_returns_string():
    token = create_refresh_token(user_id=123)
    assert isinstance(token, str)

# 6. Refresh token payload contains type = refresh
def test_refresh_token_contains_type_refresh():
    token = create_refresh_token(user_id=123)
    payload = decode_token(token)
    assert payload["type"] == "refresh"

# 7. Refresh token payload contains a non-empty jti
def test_refresh_token_contains_non_empty_jti():
    token = create_refresh_token(user_id=123)
    payload = decode_token(token)
    assert "jti" in payload
    assert isinstance(payload["jti"], str)
    assert len(payload["jti"]) > 0

# 8. Two refresh tokens have different jti values
def test_different_refresh_tokens_have_different_jti():
    token1 = create_refresh_token(user_id=123)
    token2 = create_refresh_token(user_id=123)
    payload1 = decode_token(token1)
    payload2 = decode_token(token2)
    assert payload1["jti"] != payload2["jti"]

# 9. Invalid token returns None
def test_invalid_token_returns_none():
    assert decode_token("invalid.token.format") is None
    assert decode_token("invalid_token") is None

# 10. Empty token returns None
def test_empty_token_returns_none():
    assert decode_token("") is None
    assert decode_token(None) is None

# 11. Expired token returns None
def test_expired_token_returns_none():
    # Create an access token that expired 10 minutes ago
    expired_delta = timedelta(minutes=-10)
    token = create_access_token(user_id=123, expires_delta=expired_delta)
    assert decode_token(token) is None

# 12. Refresh-token hashing returns a string
def test_hash_refresh_token_returns_string():
    hashed = hash_refresh_token("some_refresh_token_string")
    assert isinstance(hashed, str)
    assert len(hashed) == 64  # SHA-256 is 64 hex characters

# 13. The same refresh token creates the same hash
def test_same_refresh_token_produces_same_hash():
    token = "some_refresh_token_string"
    hash1 = hash_refresh_token(token)
    hash2 = hash_refresh_token(token)
    assert hash1 == hash2

# 14. Different refresh tokens create different hashes
def test_different_refresh_tokens_produce_different_hashes():
    hash1 = hash_refresh_token("token_one")
    hash2 = hash_refresh_token("token_two")
    assert hash1 != hash2

# 15. Empty refresh-token hashing is rejected
def test_empty_refresh_token_hashing_fails():
    with pytest.raises(ValueError):
        hash_refresh_token("")
    with pytest.raises(ValueError):
        hash_refresh_token("   ")
    with pytest.raises(ValueError):
        hash_refresh_token(None)
