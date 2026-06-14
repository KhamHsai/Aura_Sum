from sqlalchemy.orm import Session
from app.models.category import Category

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
