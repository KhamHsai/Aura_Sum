from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

# Initialize PasswordHash context with Argon2 hasher
password_hash_context = PasswordHash((Argon2Hasher(),))

def hash_password(plain_password: str) -> str:
    """Securely hash a plain text password using Argon2."""
    if not plain_password:
        raise ValueError("Password cannot be empty")
    return password_hash_context.hash(plain_password)

def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a plain text password against a stored hash."""
    if not plain_password or not password_hash:
        return False
    try:
        return password_hash_context.verify(plain_password, password_hash)
    except Exception:
        # Prevent exposing internal hashing library errors to the user
        return False
