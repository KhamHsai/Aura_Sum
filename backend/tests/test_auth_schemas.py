import pytest
from datetime import datetime
from pydantic import ValidationError
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    LogoutRequest,
)
from app.schemas.user import UserResponse, UserUpdate

# 1. Valid registration data
def test_valid_registration():
    data = {
        "username": "  alice  ",
        "email": "  ALICE@example.com  ",
        "password": "supersecurepassword123",
        "full_name": "  Alice Smith  ",
        "preferred_language": "th"
    }
    req = RegisterRequest(**data)
    assert req.username == "alice"  # should be trimmed
    assert req.email == "alice@example.com"  # should be trimmed & lowercase
    assert req.password == "supersecurepassword123"
    assert req.full_name == "Alice Smith"  # should be trimmed
    assert req.preferred_language == "th"

# 2. Username too short
def test_username_too_short():
    with pytest.raises(ValidationError) as excinfo:
        RegisterRequest(
            username="ab",
            email="alice@example.com",
            password="supersecurepassword123"
        )
    assert "username" in str(excinfo.value)

# 3. Invalid email
def test_invalid_email():
    with pytest.raises(ValidationError) as excinfo:
        RegisterRequest(
            username="alice",
            email="not-an-email",
            password="supersecurepassword123"
        )
    assert "email" in str(excinfo.value)

# 4. Password too short
def test_password_too_short():
    with pytest.raises(ValidationError) as excinfo:
        RegisterRequest(
            username="alice",
            email="alice@example.com",
            password="short"
        )
    assert "password" in str(excinfo.value)

# 5. Unsupported preferred language
def test_unsupported_language():
    with pytest.raises(ValidationError) as excinfo:
        RegisterRequest(
            username="alice",
            email="alice@example.com",
            password="supersecurepassword123",
            preferred_language="fr"
        )
    assert "preferred_language" in str(excinfo.value)

# 6. Valid login data
def test_valid_login():
    data = {
        "email": "  BOB@example.com  ",
        "password": "somepassword"
    }
    req = LoginRequest(**data)
    assert req.email == "bob@example.com"
    assert req.password == "somepassword"

# 7. Empty refresh token
def test_empty_refresh_token():
    with pytest.raises(ValidationError):
        RefreshTokenRequest(refresh_token="")
    with pytest.raises(ValidationError):
        LogoutRequest(refresh_token="")

# 8. Safe UserResponse fields
def test_user_response_fields():
    # Setup dummy model-like class or dict
    class MockUser:
        id = 1
        username = "alice"
        email = "alice@example.com"
        full_name = "Alice Smith"
        preferred_language = "en"
        role = "user"
        is_active = True
        created_at = datetime(2026, 1, 1, 12, 0, 0)
        updated_at = datetime(2026, 1, 1, 12, 0, 0)
        password_hash = "secret_hash"
        deleted_at = None

    user_obj = MockUser()
    resp = UserResponse.model_validate(user_obj)
    
    # Assert fields are present
    assert resp.id == 1
    assert resp.username == "alice"
    assert resp.email == "alice@example.com"
    assert resp.full_name == "Alice Smith"
    
    # Verify sensitive attributes are not exposed (they aren't part of the schema fields)
    assert not hasattr(resp, "password_hash")
    assert not hasattr(resp, "deleted_at")

# 9. Valid partial UserUpdate
def test_user_update_partial():
    # Only updating full_name
    update1 = UserUpdate(full_name="  New Name  ")
    assert update1.full_name == "New Name"
    assert update1.username is None
    
    # Invalid username length on update
    with pytest.raises(ValidationError):
        UserUpdate(username="a")
