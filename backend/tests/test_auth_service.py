import pytest
import time
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.database import Base
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.schemas.auth import RegisterRequest, LoginRequest
from app.services.auth_service import (
    register_user,
    login_user,
    refresh_access_token,
    logout_user,
    get_user_by_id,
    AuthServiceError,
)
from app.utils.password_utils import verify_password
from app.utils.token_utils import hash_refresh_token, decode_token, create_access_token

# Setup test connection engine on TEST_DATABASE_URL
settings.JWT_SECRET_KEY = "test_jwt_secret_key_auth_services_testing_benz_2004"
settings.JWT_ALGORITHM = "HS256"

engine = create_engine(settings.TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db(db_session=None):
    session = TestingSessionLocal()
    # Explicitly clear tables before test runs to ensure isolation
    session.query(RefreshToken).delete()
    session.query(User).delete()
    session.commit()
    try:
        yield session
    finally:
        session.query(RefreshToken).delete()
        session.query(User).delete()
        session.commit()
        session.close()

# 1. Successful registration
def test_successful_registration(db):
    data = RegisterRequest(
        username="alice",
        email="alice@example.com",
        password="password123",
        full_name="Alice Smith",
        preferred_language="en"
    )
    user = register_user(db, data)
    assert user.id is not None
    assert user.username == "alice"
    assert user.email == "alice@example.com"
    assert user.preferred_language == "en"

# 2. Password is stored as a hash, not plain text
def test_password_is_hashed(db):
    data = RegisterRequest(
        username="alice",
        email="alice@example.com",
        password="password123"
    )
    user = register_user(db, data)
    assert user.password_hash != "password123"
    assert verify_password("password123", user.password_hash) is True

# 3. Duplicate email is rejected
def test_duplicate_email_rejected(db):
    data = RegisterRequest(username="alice", email="alice@example.com", password="password123")
    register_user(db, data)
    
    data2 = RegisterRequest(username="bob", email="alice@example.com", password="password123")
    with pytest.raises(AuthServiceError) as excinfo:
        register_user(db, data2)
    assert excinfo.value.status_code == 409
    assert "Email already exists" in excinfo.value.message

# 4. Duplicate username is rejected
def test_duplicate_username_rejected(db):
    data = RegisterRequest(username="alice", email="alice@example.com", password="password123")
    register_user(db, data)
    
    data2 = RegisterRequest(username="alice", email="bob@example.com", password="password123")
    with pytest.raises(AuthServiceError) as excinfo:
        register_user(db, data2)
    assert excinfo.value.status_code == 409
    assert "Username already exists" in excinfo.value.message

# 5. Successful login
def test_successful_login(db):
    reg_data = RegisterRequest(username="alice", email="alice@example.com", password="password123")
    register_user(db, reg_data)
    
    login_data = LoginRequest(email="alice@example.com", password="password123")
    tokens = login_user(db, login_data)
    
    assert tokens.access_token is not None
    assert tokens.refresh_token is not None
    assert tokens.token_type == "bearer"
    assert tokens.expires_in == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

# 6. Incorrect password is rejected
def test_incorrect_password_rejected(db):
    reg_data = RegisterRequest(username="alice", email="alice@example.com", password="password123")
    register_user(db, reg_data)
    
    login_data = LoginRequest(email="alice@example.com", password="wrongpassword")
    with pytest.raises(AuthServiceError) as excinfo:
        login_user(db, login_data)
    assert excinfo.value.status_code == 401
    assert "Invalid email or password" in excinfo.value.message

# 7. Unknown email uses the same invalid-credentials error
def test_unknown_email_rejected(db):
    login_data = LoginRequest(email="nonexistent@example.com", password="password123")
    with pytest.raises(AuthServiceError) as excinfo:
        login_user(db, login_data)
    assert excinfo.value.status_code == 401
    assert "Invalid email or password" in excinfo.value.message

# 8. Inactive user cannot log in
def test_inactive_user_login_fail(db):
    reg_data = RegisterRequest(username="alice", email="alice@example.com", password="password123")
    user = register_user(db, reg_data)
    user.is_active = False
    db.commit()
    
    login_data = LoginRequest(email="alice@example.com", password="password123")
    with pytest.raises(AuthServiceError) as excinfo:
        login_user(db, login_data)
    assert excinfo.value.status_code == 403
    assert "User account is inactive" in excinfo.value.message

# 9. Soft-deleted user cannot log in
def test_soft_deleted_user_login_fail(db):
    reg_data = RegisterRequest(username="alice", email="alice@example.com", password="password123")
    user = register_user(db, reg_data)
    user.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    
    login_data = LoginRequest(email="alice@example.com", password="password123")
    with pytest.raises(AuthServiceError) as excinfo:
        login_user(db, login_data)
    assert excinfo.value.status_code == 403
    assert "User account is unavailable" in excinfo.value.message

# 10. Login creates a refresh-token database record
def test_login_creates_refresh_token_record(db):
    reg_data = RegisterRequest(username="alice", email="alice@example.com", password="password123")
    user = register_user(db, reg_data)
    
    login_data = LoginRequest(email="alice@example.com", password="password123")
    tokens = login_user(db, login_data)
    
    db_token = db.query(RefreshToken).filter(RefreshToken.user_id == user.id).first()
    assert db_token is not None

# 11. Stored refresh token is hashed, not raw
def test_refresh_token_stored_is_hashed(db):
    reg_data = RegisterRequest(username="alice", email="alice@example.com", password="password123")
    register_user(db, reg_data)
    
    login_data = LoginRequest(email="alice@example.com", password="password123")
    tokens = login_user(db, login_data)
    
    expected_hash = hash_refresh_token(tokens.refresh_token)
    db_token = db.query(RefreshToken).filter(RefreshToken.token_hash == expected_hash).first()
    assert db_token is not None
    # Verify we did not save the raw token
    assert db_token.token_hash != tokens.refresh_token

# 12. Successful access-token refresh
def test_successful_token_refresh(db):
    reg_data = RegisterRequest(username="alice", email="alice@example.com", password="password123")
    register_user(db, reg_data)
    
    login_data = LoginRequest(email="alice@example.com", password="password123")
    tokens = login_user(db, login_data)
    
    refreshed = refresh_access_token(db, tokens.refresh_token)
    assert refreshed.access_token is not None
    assert refreshed.refresh_token == tokens.refresh_token

# 13. Access token cannot be used as a refresh token
def test_access_token_rejected_as_refresh_token(db):
    reg_data = RegisterRequest(username="alice", email="alice@example.com", password="password123")
    register_user(db, reg_data)
    
    login_data = LoginRequest(email="alice@example.com", password="password123")
    tokens = login_user(db, login_data)
    
    with pytest.raises(AuthServiceError) as excinfo:
        refresh_access_token(db, tokens.access_token)
    assert excinfo.value.status_code == 401

# 14. Invalid refresh token is rejected
def test_invalid_refresh_token_rejected(db):
    with pytest.raises(AuthServiceError) as excinfo:
        refresh_access_token(db, "invalid_token")
    assert excinfo.value.status_code == 401

# 15. Revoked refresh token is rejected
def test_revoked_refresh_token_rejected(db):
    reg_data = RegisterRequest(username="alice", email="alice@example.com", password="password123")
    register_user(db, reg_data)
    
    login_data = LoginRequest(email="alice@example.com", password="password123")
    tokens = login_user(db, login_data)
    
    logout_user(db, tokens.refresh_token)
    
    with pytest.raises(AuthServiceError) as excinfo:
        refresh_access_token(db, tokens.refresh_token)
    assert excinfo.value.status_code == 401

# 16. Expired refresh token is rejected
def test_expired_refresh_token_rejected(db):
    reg_data = RegisterRequest(username="alice", email="alice@example.com", password="password123")
    user = register_user(db, reg_data)
    
    login_data = LoginRequest(email="alice@example.com", password="password123")
    tokens = login_user(db, login_data)
    
    # Manually expire database record
    expected_hash = hash_refresh_token(tokens.refresh_token)
    db_token = db.query(RefreshToken).filter(RefreshToken.token_hash == expected_hash).first()
    db_token.expires_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)
    db.commit()
    
    with pytest.raises(AuthServiceError) as excinfo:
        refresh_access_token(db, tokens.refresh_token)
    assert excinfo.value.status_code == 401

# 17. Successful logout sets revoked_at
def test_logout_sets_revoked_at(db):
    reg_data = RegisterRequest(username="alice", email="alice@example.com", password="password123")
    register_user(db, reg_data)
    
    login_data = LoginRequest(email="alice@example.com", password="password123")
    tokens = login_user(db, login_data)
    
    status = logout_user(db, tokens.refresh_token)
    assert status is True
    
    expected_hash = hash_refresh_token(tokens.refresh_token)
    db_token = db.query(RefreshToken).filter(RefreshToken.token_hash == expected_hash).first()
    assert db_token.revoked_at is not None

# 18. Repeated logout remains safe
def test_repeated_logout_is_safe(db):
    reg_data = RegisterRequest(username="alice", email="alice@example.com", password="password123")
    register_user(db, reg_data)
    
    login_data = LoginRequest(email="alice@example.com", password="password123")
    tokens = login_user(db, login_data)
    
    assert logout_user(db, tokens.refresh_token) is True
    assert logout_user(db, tokens.refresh_token) is True

# 19. get_user_by_id returns an active user
def test_get_user_by_id_active(db):
    reg_data = RegisterRequest(username="alice", email="alice@example.com", password="password123")
    user = register_user(db, reg_data)
    
    fetched = get_user_by_id(db, user.id)
    assert fetched is not None
    assert fetched.id == user.id

# 20. get_user_by_id does not return inactive or deleted users
def test_get_user_by_id_inactive_or_deleted(db):
    reg_data = RegisterRequest(username="alice", email="alice@example.com", password="password123")
    user1 = register_user(db, reg_data)
    user1.is_active = False
    db.commit()
    
    assert get_user_by_id(db, user1.id) is None
    
    reg_data2 = RegisterRequest(username="bob", email="bob@example.com", password="password123")
    user2 = register_user(db, reg_data2)
    user2.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    
    assert get_user_by_id(db, user2.id) is None
