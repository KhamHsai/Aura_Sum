import re
from sqlalchemy.orm import Session
from app.models.category import Category
from app.schemas.category import CategoryCreate


class CategoryServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def get_categories(db: Session) -> list[Category]:
    """
    Retrieve all categories that are active and not soft-deleted,
    sorted by English name (name_en) in ascending order.
    """
    return (
        db.query(Category)
        .filter(Category.is_active == True, Category.deleted_at.is_(None))
        .order_by(Category.name_en.asc())
        .all()
    )

def get_category_by_id(db: Session, category_id: int) -> Category | None:
    """
    Retrieve a category by ID if it is active and not soft-deleted.
    """
    return (
        db.query(Category)
        .filter(
            Category.id == category_id,
            Category.is_active == True,
            Category.deleted_at.is_(None)
        )
        .first()
    )


def _make_code(name: str) -> str:
    """Generate a URL-safe code from a category name, e.g. 'Food & Dining' → 'food_dining'."""
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9]+', '_', slug)
    slug = slug.strip('_')
    return slug[:50] or 'category'


def create_category(db: Session, data: CategoryCreate) -> Category:
    """
    Create a new category from a user-typed name.
    If a category with the same name already exists (case-insensitive), return it instead.
    The name is stored as both name_en and name_th so it always displays correctly.
    """
    name = data.name.strip()
    name_lower = name.lower()

    # Idempotent — return existing if it matches
    existing = (
        db.query(Category)
        .filter(
            Category.is_active == True,
            Category.deleted_at.is_(None),
        )
        .all()
    )
    for cat in existing:
        if cat.name_en.lower() == name_lower or cat.name_th.lower() == name_lower:
            return cat

    # Generate a unique code
    base_code = _make_code(name)
    code = base_code
    counter = 1
    while db.query(Category).filter(Category.code == code).first():
        code = f"{base_code}_{counter}"
        counter += 1

    category = Category(
        code=code,
        name_en=name,
        name_th=name,
        is_active=True,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category