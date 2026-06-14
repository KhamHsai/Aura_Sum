from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from app.utils.password_utils import hash_password, verify_password
from app.utils.token_utils import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_refresh_token,
)
from app.config import settings

class AuthServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)

def register_user(db: Session, data: RegisterRequest) -> User:
    """Register a new user account."""
    # Normalize email and username
    normalized_email = data.email.strip().lower()
    normalized_username = data.username.strip()

    # Check whether the email already exists (including soft-deleted users)
    existing_email = db.query(User).filter(User.email == normalized_email).first()
    if existing_email:
        raise AuthServiceError("Email already exists", 409)

    # Check whether the username already exists (including soft-deleted users)
    existing_username = db.query(User).filter(User.username == normalized_username).first()
    if existing_username:
        raise AuthServiceError("Username already exists", 409)

    # Hash password and create User model
    hashed_pwd = hash_password(data.password)
    user = User(
        username=normalized_username,
        email=normalized_email,
        password_hash=hashed_pwd,
        full_name=data.full_name.strip() if data.full_name else None,
        preferred_language=data.preferred_language,
        role="user",
        is_active=True
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except Exception as e:
        db.rollback()
        raise e

def login_user(db: Session, data: LoginRequest) -> TokenResponse:
    """Authenticate credentials and generate JWT tokens."""
    normalized_email = data.email.strip().lower()
    user = db.query(User).filter(User.email == normalized_email).first()

    # 1. Reject if user does not exist
    if not user:
        raise AuthServiceError("Invalid email or password", 401)

    # 2. Reject if soft-deleted
    if user.deleted_at is not None:
        raise AuthServiceError("User account is unavailable", 403)

    # 3. Reject if inactive
    if not user.is_active:
        raise AuthServiceError("User account is inactive", 403)

    # 4. Verify password
    if not verify_password(data.password, user.password_hash):
        raise AuthServiceError("Invalid email or password", 401)

    # 5. Create tokens
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    # 6. Decode refresh token to extract jti and exp
    decoded_refresh = decode_token(refresh_token)
    if not decoded_refresh:
        raise AuthServiceError("Failed to generate token payload", 500)

    jti = decoded_refresh.get("jti")
    exp_timestamp = decoded_refresh.get("exp")
    expires_at = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc).replace(tzinfo=None)

    # 7. Hash the raw refresh token
    token_hash = hash_refresh_token(refresh_token)

    # 8. Save only the hashed refresh token in database
    db_refresh_token = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at
    )

    # 9. Update last login timestamp
    user.last_login_at = datetime.now(timezone.utc).replace(tzinfo=None)

    try:
        db.add(db_refresh_token)
        db.commit()
    except Exception as e:
        db.rollback()
        raise e

    expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=expires_in
    )

def refresh_access_token(db: Session, refresh_token: str) -> TokenResponse:
    """Create a new access token using a valid refresh token."""
    decoded = decode_token(refresh_token)
    if not decoded or decoded.get("type") != "refresh":
        raise AuthServiceError("Invalid or expired refresh token", 401)

    sub = decoded.get("sub")
    jti = decoded.get("jti")
    if not sub or not jti:
        raise AuthServiceError("Invalid or expired refresh token", 401)

    try:
        user_id = int(sub)
    except ValueError:
        raise AuthServiceError("Invalid or expired refresh token", 401)

    token_hash = hash_refresh_token(refresh_token)

    # Query refresh token from database
    db_token = db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.token_hash == token_hash
    ).first()

    if not db_token or db_token.revoked_at is not None:
        raise AuthServiceError("Invalid or expired refresh token", 401)

    # Check database expiration time
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    if db_token.expires_at < now_utc:
        raise AuthServiceError("Invalid or expired refresh token", 401)

    # Verify associated user status
    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.deleted_at is not None:
        raise AuthServiceError("Invalid or expired refresh token", 401)

    if not user.is_active:
        raise AuthServiceError("Invalid or expired refresh token", 401)

    # Generate new access token
    access_token = create_access_token(user.id)
    expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=expires_in
    )

def logout_user(db: Session, refresh_token: str) -> bool:
    """Revoke a refresh token by setting revoked_at."""
    if not refresh_token or not refresh_token.strip():
        raise ValueError("Refresh token cannot be empty")

    token_hash = hash_refresh_token(refresh_token)
    db_token = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()

    if not db_token:
        raise AuthServiceError("Invalid or expired refresh token", 401)

    if db_token.revoked_at is not None:
        return True

    db_token.revoked_at = datetime.now(timezone.utc).replace(tzinfo=None)

    try:
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        raise e

def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Retrieve an active, non-deleted user by ID."""
    return db.query(User).filter(
        User.id == user_id,
        User.deleted_at.is_(None),
        User.is_active.is_(True)
    ).first()
