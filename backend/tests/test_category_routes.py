import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.database import get_db
from app.main import app
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.models.category import Category

settings.JWT_SECRET_KEY = "test_jwt_secret_key_category_routes_testing_benz_2004"
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
    db.query(Category).delete()
    db.commit()
    try:
        yield
    finally:
        db = TestingSessionLocal()
        db.query(RefreshToken).delete()
        db.query(User).delete()
        db.query(Category).delete()
        db.commit()
        db.close()

# Helper to register and login a user, yielding the access token
def get_auth_token():
    client.post(
        "/api/auth/register",
        json={
            "username": "bob",
            "email": "bob@example.com",
            "password": "password123",
            "full_name": "Bob Vance"
        }
    )
    login_res = client.post(
        "/api/auth/login",
        json={"email": "bob@example.com", "password": "password123"}
    )
    return login_res.json()["access_token"]

# 1. Authenticated user can list categories, returns 200, returns array with expected fields
def test_authenticated_user_can_list_categories():
    db = TestingSessionLocal()
    c1 = Category(code="FOOD", name_en="Food", name_th="อาหาร", is_active=True)
    c2 = Category(code="TRANS", name_en="Transportation", name_th="การเดินทาง", is_active=True)
    db.add_all([c1, c2])
    db.commit()
    db.close()

    token = get_auth_token()
    response = client.get(
        "/api/categories",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    res_data = response.json()
    assert isinstance(res_data, list)
    assert len(res_data) == 2
    
    # Verify expected fields and correct sorting (Food before Transportation)
    assert res_data[0]["code"] == "FOOD"
    assert res_data[0]["name_en"] == "Food"
    assert "deleted_at" not in res_data[0]
    assert "id" in res_data[0]
    assert "created_at" in res_data[0]

# 2. Missing access token returns 401
def test_missing_access_token_returns_401():
    response = client.get("/api/categories")
    assert response.status_code == 401

# 3. Invalid access token returns 401
def test_invalid_access_token_returns_401():
    response = client.get(
        "/api/categories",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401

# 4. Authenticated user can get one category
def test_authenticated_user_can_get_one_category():
    db = TestingSessionLocal()
    c = Category(code="FOOD", name_en="Food", name_th="อาหาร", is_active=True)
    db.add(c)
    db.commit()
    category_id = c.id
    db.close()

    token = get_auth_token()
    response = client.get(
        f"/api/categories/{category_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["id"] == category_id
    assert res_data["code"] == "FOOD"
    assert res_data["name_en"] == "Food"

# 5. Unknown category ID returns 404
def test_unknown_category_id_returns_404():
    token = get_auth_token()
    response = client.get(
        "/api/categories/999999",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Category not found"

# 6. Inactive category returns 404
def test_inactive_category_returns_404():
    db = TestingSessionLocal()
    c = Category(code="INACTIVE", name_en="Inactive", name_th="ไม่ใช้งาน", is_active=False)
    db.add(c)
    db.commit()
    category_id = c.id
    db.close()

    token = get_auth_token()
    response = client.get(
        f"/api/categories/{category_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404

# 7. Soft-deleted category returns 404
def test_soft_deleted_category_returns_404():
    db = TestingSessionLocal()
    c = Category(
        code="DELETED",
        name_en="Deleted",
        name_th="ลบแล้ว",
        is_active=True,
        deleted_at=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    db.add(c)
    db.commit()
    category_id = c.id
    db.close()

    token = get_auth_token()
    response = client.get(
        f"/api/categories/{category_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404
