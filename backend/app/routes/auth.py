from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.auth import RegisterRequest, LoginRequest, RefreshTokenRequest, LogoutRequest, TokenResponse
from app.schemas.user import UserResponse
from app.models.user import User
from app.dependencies.auth import get_current_user
from app.services.auth_service import (
    register_user,
    login_user,
    refresh_access_token,
    logout_user,
    AuthServiceError,
)

router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    try:
        return register_user(db, data)
    except AuthServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    try:
        return login_user(db, data)
    except AuthServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def refresh(data: RefreshTokenRequest, db: Session = Depends(get_db)):
    try:
        return refresh_access_token(db, data.refresh_token)
    except AuthServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(data: LogoutRequest, db: Session = Depends(get_db)):
    try:
        logout_user(db, data.refresh_token)
        return {"message": "Logged out successfully"}
    except AuthServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
