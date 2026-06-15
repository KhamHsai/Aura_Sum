import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models.category import Category
from app.services.category_service import get_categories, get_category_by_id

engine = create_engine(settings.TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    session = TestingSessionLocal()
    session.query(Category).delete()
    session.commit()
    try:
        yield session
    finally:
        session.query(Category).delete()
        session.commit()
        session.close()

# 1. Empty category table returns an empty list
def test_get_categories_empty(db):
    results = get_categories(db)
    assert results == []

# 2. get_categories() returns only active, non-deleted categories, sorted by name_en
def test_get_categories_filtering_and_sorting(db):
    # Seed categories
    c1 = Category(code="C1", name_en="Transportation", name_th="การเดินทาง", is_active=True)
    c2 = Category(code="C2", name_en="Food", name_th="อาหาร", is_active=True)
    c3 = Category(code="C3", name_en="Utilities", name_th="สาธารณูปโภค", is_active=False)  # Inactive
    c4 = Category(code="C4", name_en="Entertainment", name_th="บันเทิง", is_active=True, deleted_at=datetime.now(timezone.utc).replace(tzinfo=None))  # Soft-deleted

    db.add_all([c1, c2, c3, c4])
    db.commit()

    results = get_categories(db)
    assert len(results) == 2
    # Check ordering (Food, then Transportation)
    assert results[0].name_en == "Food"
    assert results[1].name_en == "Transportation"

# 3. get_category_by_id() returns active and non-deleted categories
def test_get_category_by_id_active(db):
    cat = Category(code="FOOD", name_en="Food", name_th="อาหาร", is_active=True)
    db.add(cat)
    db.commit()

    fetched = get_category_by_id(db, cat.id)
    assert fetched is not None
    assert fetched.id == cat.id
    assert fetched.name_en == "Food"

# 4. get_category_by_id() returns None for unknown, inactive, or soft-deleted categories
def test_get_category_by_id_inactive_or_deleted(db):
    c_inactive = Category(code="UTIL", name_en="Utilities", name_th="สาธารณูปโภค", is_active=False)
    c_deleted = Category(code="ENT", name_en="Entertainment", name_th="บันเทิง", is_active=True, deleted_at=datetime.now(timezone.utc).replace(tzinfo=None))
    db.add_all([c_inactive, c_deleted])
    db.commit()

    # Unknown ID
    assert get_category_by_id(db, 999999) is None
    # Inactive
    assert get_category_by_id(db, c_inactive.id) is None
    # Deleted
    assert get_category_by_id(db, c_deleted.id) is None
