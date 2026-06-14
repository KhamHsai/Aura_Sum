import pytest
from app.utils.password_utils import hash_password, verify_password

# 1. Hashing returns a string
def test_hash_returns_string():
    hashed = hash_password("secret_pass")
    assert isinstance(hashed, str)

# 2. Hashing does not return the original password
def test_hash_not_equal_to_plain():
    plain = "secret_pass"
    hashed = hash_password(plain)
    assert hashed != plain

# 3. Correct password verification returns True
def test_correct_verification():
    plain = "secret_pass"
    hashed = hash_password(plain)
    assert verify_password(plain, hashed) is True

# 4. Incorrect password verification returns False
def test_incorrect_verification():
    plain = "secret_pass"
    hashed = hash_password(plain)
    assert verify_password("wrong_pass", hashed) is False

# 5. Hashing the same password twice creates different hashes (because of random salt)
def test_different_hashes_for_same_password():
    plain = "secret_pass"
    hash1 = hash_password(plain)
    hash2 = hash_password(plain)
    assert hash1 != hash2

# 6. Both different hashes still verify the same password
def test_both_hashes_verify_correctly():
    plain = "secret_pass"
    hash1 = hash_password(plain)
    hash2 = hash_password(plain)
    assert verify_password(plain, hash1) is True
    assert verify_password(plain, hash2) is True

# 7. Empty password hashing is rejected
def test_empty_password_hashing_raises_value_error():
    with pytest.raises(ValueError):
        hash_password("")
    with pytest.raises(ValueError):
        hash_password(None)

# 8. Invalid or empty stored hash returns False or is handled safely
def test_invalid_or_empty_hash():
    # Empty inputs should return False
    assert verify_password("secret_pass", "") is False
    assert verify_password("", "some_hash") is False
    # Invalid format hash should return False instead of raising exceptions
    assert verify_password("secret_pass", "invalid_hash_format") is False
