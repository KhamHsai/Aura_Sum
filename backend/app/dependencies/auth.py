from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.services.auth_service import get_user_by_id
from app.utils.token_utils import decode_token

# Initialize OAuth2 Password Bearer pointing to login route
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Retrieve and validate the current authenticated user from JWT Bearer token."""
    unauthorized_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Decode and validate token
    payload = decode_token(token)
    if not payload:
        raise unauthorized_exception

    # Assert correct type of token is used
    if payload.get("type") != "access":
        raise unauthorized_exception

    # Retrieve subject claim containing user ID
    sub = payload.get("sub")
    if not sub:
        raise unauthorized_exception

    try:
        user_id = int(sub)
    except ValueError:
        raise unauthorized_exception

    # Query active user
    user = get_user_by_id(db, user_id)
    if not user:
        raise unauthorized_exception

    return user
