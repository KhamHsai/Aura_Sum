from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.category import CategoryCreate, CategoryResponse
from app.models.user import User
from app.dependencies.auth import get_current_user
from app.services.category_service import get_categories, get_category_by_id, create_category, CategoryServiceError

router = APIRouter(
    prefix="/api/categories",
    tags=["Categories"],
)

@router.get("", response_model=list[CategoryResponse], status_code=status.HTTP_200_OK)
def list_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all active and non-deleted categories.
    Requires authentication.
    """
    return get_categories(db)

@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category_route(
    data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new category. If a category with the same name already exists,
    returns it instead (idempotent).
    Requires authentication.
    """
    try:
        return create_category(db, data)
    except CategoryServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

@router.get("/{category_id}", response_model=CategoryResponse, status_code=status.HTTP_200_OK)
def get_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific category by ID if active and non-deleted.
    Requires authentication.
    """
    category = get_category_by_id(db, category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    return category