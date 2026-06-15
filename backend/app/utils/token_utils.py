import uuid
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from app.config import settings

def create_access_token(user_id: int, expires_delta: Optional[timedelta] = None) -> str:
    """Create a short-lived JWT access token."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp())
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def create_refresh_token(user_id: int) -> str:
    """Create a longer-lived JWT refresh token with a unique jti."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "jti": uuid.uuid4().hex,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp())
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token. Returns payload dict or None if invalid."""
    if not token:
        return None
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.PyJWTError:
        return None

def hash_refresh_token(refresh_token: str) -> str:
    """Create a secure SHA-256 hash of a refresh token."""
    if not refresh_token or not refresh_token.strip():
        raise ValueError("Refresh token cannot be empty")
    return hashlib.sha256(refresh_token.encode("utf-8")).hexdigest().lower()
