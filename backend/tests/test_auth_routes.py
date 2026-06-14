import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.database import get_db
from app.main import app
from app.models.user import User
from app.models.refresh_token import RefreshToken

# Override settings to ensure correct test keys
settings.JWT_SECRET_KEY = "test_jwt_secret_key_auth_routes_testing_benz_2004"
settings.JWT_ALGORITHM = "HS256"

# Setup testing session factory
engine = create_engine(settings.TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Override get_db in FastAPI app
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

# 1. Successful registration returns 201
# 2. Registration response does not contain password_hash
def test_successful_registration():
    response = client.post(
        "/api/auth/register",
        json={
            "username": "alice",
            "email": "alice@example.com",
            "password": "password123",
            "full_name": "Alice Smith"
        }
    )
    assert response.status_code == 201
    res_data = response.json()
    assert res_data["username"] == "alice"
    assert res_data["email"] == "alice@example.com"
    assert "password_hash" not in res_data
    assert "id" in res_data

# 3. Invalid registration input returns 422
def test_invalid_registration_input():
    response = client.post(
        "/api/auth/register",
        json={
            "username": "al",  # too short
            "email": "invalid-email",
            "password": "short"
        }
    )
    assert response.status_code == 422

# 4. Duplicate email returns 409
def test_duplicate_email_registration():
    # Register first user
    client.post(
        "/api/auth/register",
        json={"username": "alice", "email": "alice@example.com", "password": "password123"}
    )
    # Register second user with same email
    response = client.post(
        "/api/auth/register",
        json={"username": "bob", "email": "alice@example.com", "password": "password123"}
    )
    assert response.status_code == 409
    assert "Email already exists" in response.json()["detail"]

# 5. Duplicate username returns 409
def test_duplicate_username_registration():
    # Register first user
    client.post(
        "/api/auth/register",
        json={"username": "alice", "email": "alice@example.com", "password": "password123"}
    )
    # Register second user with same username
    response = client.post(
        "/api/auth/register",
        json={"username": "alice", "email": "bob@example.com", "password": "password123"}
    )
    assert response.status_code == 409
    assert "Username already exists" in response.json()["detail"]

# 6. Successful login returns 200
# 7. Login response includes access token
# 8. Login response includes refresh token
def test_successful_login():
    client.post(
        "/api/auth/register",
        json={"username": "alice", "email": "alice@example.com", "password": "password123"}
    )
    
    response = client.post(
        "/api/auth/login",
        json={"email": "alice@example.com", "password": "password123"}
    )
    assert response.status_code == 200
    res_data = response.json()
    assert "access_token" in res_data
    assert "refresh_token" in res_data
    assert res_data["token_type"] == "bearer"
    assert "expires_in" in res_data

# 9. Wrong password returns 401
def test_login_wrong_password():
    client.post(
        "/api/auth/register",
        json={"username": "alice", "email": "alice@example.com", "password": "password123"}
    )
    response = client.post(
        "/api/auth/login",
        json={"email": "alice@example.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]

# 10. Unknown email returns 401
def test_login_unknown_email():
    response = client.post(
        "/api/auth/login",
        json={"email": "unknown@example.com", "password": "password123"}
    )
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]

# 11. Successful token refresh returns 200
def test_successful_token_refresh():
    client.post(
        "/api/auth/register",
        json={"username": "alice", "email": "alice@example.com", "password": "password123"}
    )
    login_res = client.post(
        "/api/auth/login",
        json={"email": "alice@example.com", "password": "password123"}
    )
    refresh_token = login_res.json()["refresh_token"]
    
    response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    assert response.status_code == 200
    res_data = response.json()
    assert "access_token" in res_data
    assert res_data["refresh_token"] == refresh_token

# 12. Access token cannot be used in the refresh endpoint
def test_access_token_in_refresh_fails():
    client.post(
        "/api/auth/register",
        json={"username": "alice", "email": "alice@example.com", "password": "password123"}
    )
    login_res = client.post(
        "/api/auth/login",
        json={"email": "alice@example.com", "password": "password123"}
    )
    access_token = login_res.json()["access_token"]
    
    response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": access_token}
    )
    assert response.status_code == 401
    assert "Invalid or expired refresh token" in response.json()["detail"]

# 13. Invalid refresh token returns 401
def test_invalid_refresh_token_fails():
    response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": "invalid_refresh_token"}
    )
    assert response.status_code == 401
    assert "Invalid or expired refresh token" in response.json()["detail"]

# 14. Successful logout returns 200
# 15. Logout response contains the success message
def test_successful_logout():
    client.post(
        "/api/auth/register",
        json={"username": "alice", "email": "alice@example.com", "password": "password123"}
    )
    login_res = client.post(
        "/api/auth/login",
        json={"email": "alice@example.com", "password": "password123"}
    )
    refresh_token = login_res.json()["refresh_token"]
    
    response = client.post(
        "/api/auth/logout",
        json={"refresh_token": refresh_token}
    )
    assert response.status_code == 200
    assert response.json() == {"message": "Logged out successfully"}

# 16. Revoked refresh token cannot refresh again
def test_revoked_token_cannot_refresh():
    client.post(
        "/api/auth/register",
        json={"username": "alice", "email": "alice@example.com", "password": "password123"}
    )
    login_res = client.post(
        "/api/auth/login",
        json={"email": "alice@example.com", "password": "password123"}
    )
    refresh_token = login_res.json()["refresh_token"]
    
    # Logout
    client.post("/api/auth/logout", json={"refresh_token": refresh_token})
    
    # Try refresh
    response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    assert response.status_code == 401
    assert "Invalid or expired refresh token" in response.json()["detail"]

# 17. Repeated logout remains safe
def test_repeated_logout_safe():
    client.post(
        "/api/auth/register",
        json={"username": "alice", "email": "alice@example.com", "password": "password123"}
    )
    login_res = client.post(
        "/api/auth/login",
        json={"email": "alice@example.com", "password": "password123"}
    )
    refresh_token = login_res.json()["refresh_token"]
    
    res1 = client.post("/api/auth/logout", json={"refresh_token": refresh_token})
    assert res1.status_code == 200
    
    res2 = client.post("/api/auth/logout", json={"refresh_token": refresh_token})
    assert res2.status_code == 200
