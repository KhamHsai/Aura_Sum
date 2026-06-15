import pytest
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.database import get_db
from app.main import app
from app.models.user import User
from app.models.refresh_token import RefreshToken

# Setup testing session factory and client
settings.JWT_SECRET_KEY = "test_jwt_secret_key_current_user_testing_benz_2004"
settings.JWT_ALGORITHM = "HS256"

engine = create_engine(settings.TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(scope="function", autouse=True)
def clean_db():
    db = TestingSessionLocal()
    db.query(RefreshToken).delete()
    db.query(User).delete()
    db.commit()
    try:
        yield
    finally:
        db.query(RefreshToken).delete()
        db.query(User).delete()
        db.commit()
        db.close()

# Helper to register and login a user, yielding the user object and login response
def setup_user_and_tokens():
    client.post(
        "/api/auth/register",
        json={
            "username": "alice",
            "email": "alice@example.com",
            "password": "password123",
            "full_name": "Alice Smith"
        }
    )
    login_res = client.post(
        "/api/auth/login",
        json={"email": "alice@example.com", "password": "password123"}
    )
    return login_res.json()

# 1. Valid access token returns 200
# 2. /api/auth/me returns the correct user ID
# 3. /api/auth/me returns the correct email and username
# 4. Response does not contain password_hash
def test_valid_access_token_returns_me():
    tokens = setup_user_and_tokens()
    access_token = tokens["access_token"]
    
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["username"] == "alice"
    assert res_data["email"] == "alice@example.com"
    assert "password_hash" not in res_data
    assert "id" in res_data

# 5. Missing Authorization header returns 401
def test_missing_auth_header_fails():
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert "WWW-Authenticate" in response.headers
    assert "Bearer" in response.headers["WWW-Authenticate"]

# 6. Invalid token returns 401
# 14. Error response includes WWW-Authenticate: Bearer
def test_invalid_token_fails():
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid_token_value_xyz"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"
    assert response.headers.get("WWW-Authenticate") == "Bearer"

# 7. Expired access token returns 401
def test_expired_access_token_fails():
    now = datetime.now(timezone.utc)
    expire = now - timedelta(minutes=10)
    payload = {
        "sub": "1",
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp())
    }
    expired_token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert response.status_code == 401

# 8. Refresh token used on /api/auth/me returns 401
def test_refresh_token_on_me_fails():
    tokens = setup_user_and_tokens()
    refresh_token = tokens["refresh_token"]
    
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {refresh_token}"}
    )
    assert response.status_code == 401

# 9. Token with missing sub returns 401
def test_missing_sub_fails():
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=30)
    payload = {
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp())
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401

# 10. Token with invalid non-integer sub returns 401
def test_invalid_sub_format_fails():
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=30)
    payload = {
        "sub": "not_an_int",
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp())
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401

# 11. Token for an unknown user returns 401
def test_unknown_user_token_fails():
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=30)
    payload = {
        "sub": "99999",  # non-existent ID
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp())
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401

# 12. Inactive user returns 401
def test_inactive_user_token_fails(db_session=None):
    tokens = setup_user_and_tokens()
    access_token = tokens["access_token"]
    
    db = TestingSessionLocal()
    user = db.query(User).filter(User.username == "alice").first()
    user.is_active = False
    db.commit()
    db.close()
    
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 401

# 13. Soft-deleted user returns 401
def test_soft_deleted_user_token_fails():
    tokens = setup_user_and_tokens()
    access_token = tokens["access_token"]
    
    db = TestingSessionLocal()
    user = db.query(User).filter(User.username == "alice").first()
    user.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.close()
    
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 401
