"""Service layer for expense management."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.expense import Expense
from app.models.expense_item import ExpenseItem
from app.schemas.expense import ExpenseCreate, ExpenseResponse, ExpenseUpdate
from app.schemas.expense_item import ExpenseItemResponse


class ExpenseServiceError(Exception):
    """Raised when business validation fails in the expense service."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _get_valid_category(db: Session, category_id: int, error_message: str) -> Category:
    """Return a category that exists, is active, and is not soft-deleted."""
    category = (
        db.query(Category)
        .filter(
            Category.id == category_id,
            Category.is_active == True,
            Category.deleted_at.is_(None),
        )
        .first()
    )
    if not category:
        raise ExpenseServiceError(error_message, status_code=404)
    return category


def create_expense(db: Session, user_id: int, data: ExpenseCreate) -> ExpenseResponse:
    """
    Create one expense and its optional items for the authenticated user.

    Validates categories, writes everything in one transaction,
    and rolls back fully if anything fails.
    Returns an ExpenseResponse built while the session is still open.
    """
    # 1. Validate the main expense category
    _get_valid_category(db, data.category_id, "Category not found")

    # 2. Validate each item category before touching the database
    for item_data in data.items:
        if item_data.category_id is not None:
            _get_valid_category(db, item_data.category_id, "Item category not found")

    try:
        # 3. Create the Expense — user_id always comes from the auth layer
        expense = Expense(
            user_id=user_id,
            category_id=data.category_id,
            title=data.title,
            merchant_name=data.merchant_name,
            receipt_number=data.receipt_number,
            receipt_date=data.receipt_date,
            payment_method=data.payment_method,
            currency=data.currency,
            subtotal=data.subtotal,
            tax_amount=data.tax_amount,
            discount_amount=data.discount_amount,
            total_amount=data.total_amount,
            notes=data.notes,
            input_method="manual",  # only supported value for user-created expenses
        )

        # 4. Flush to get expense.id without committing yet
        db.add(expense)
        db.flush()

        # 5. Create each ExpenseItem using the flushed expense.id, collecting them
        created_items: list[ExpenseItem] = []
        for item_data in data.items:
            item = ExpenseItem(
                expense_id=expense.id,
                category_id=item_data.category_id,
                original_name=item_data.original_name,
                name_en=item_data.name_en,
                name_th=item_data.name_th,
                quantity=item_data.quantity,
                unit=item_data.unit,
                unit_price=item_data.unit_price,
                discount_amount=item_data.discount_amount,
                total_price=item_data.total_price,
            )
            db.add(item)
            created_items.append(item)

        # 6. Flush items to get their IDs, then commit once
        db.flush()
        db.commit()

        # 7. Refresh expense and all items to load server-generated fields
        #    (created_at, updated_at) while the session is still open.
        db.refresh(expense)
        for item in created_items:
            db.refresh(item)

        # 8. Build the Pydantic response from the in-memory objects while the
        #    session is still open — avoids lazy-load issues after session closes.
        item_responses = [ExpenseItemResponse.model_validate(item) for item in created_items]
        response = ExpenseResponse(
            id=expense.id,
            user_id=expense.user_id,
            category_id=expense.category_id,
            title=expense.title,
            merchant_name=expense.merchant_name,
            receipt_number=expense.receipt_number,
            receipt_date=expense.receipt_date,
            payment_method=expense.payment_method,
            currency=expense.currency,
            subtotal=expense.subtotal,
            tax_amount=expense.tax_amount,
            discount_amount=expense.discount_amount,
            total_amount=expense.total_amount,
            notes=expense.notes,
            is_confirmed=expense.is_confirmed,
            created_at=expense.created_at,
            updated_at=expense.updated_at,
            items=item_responses,
        )
        return response

    except ExpenseServiceError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_non_deleted_items(db: Session, expense_id: int) -> list[ExpenseItem]:
    """Return non-deleted items for an expense, ordered by id ascending."""
    return (
        db.query(ExpenseItem)
        .filter(
            ExpenseItem.expense_id == expense_id,
            ExpenseItem.deleted_at.is_(None),
        )
        .order_by(ExpenseItem.id.asc())
        .all()
    )


def _build_expense_response(expense: Expense, items: list[ExpenseItem]) -> ExpenseResponse:
    """Build an ExpenseResponse from ORM objects while the session is open."""
    item_responses = [ExpenseItemResponse.model_validate(item) for item in items]
    return ExpenseResponse(
        id=expense.id,
        user_id=expense.user_id,
        category_id=expense.category_id,
        title=expense.title,
        merchant_name=expense.merchant_name,
        receipt_number=expense.receipt_number,
        receipt_date=expense.receipt_date,
        payment_method=expense.payment_method,
        currency=expense.currency,
        subtotal=expense.subtotal,
        tax_amount=expense.tax_amount,
        discount_amount=expense.discount_amount,
        total_amount=expense.total_amount,
        notes=expense.notes,
        is_confirmed=expense.is_confirmed,
        created_at=expense.created_at,
        updated_at=expense.updated_at,
        items=item_responses,
    )


# ── Read functions ─────────────────────────────────────────────────────────────

def get_user_expenses(db: Session, user_id: int) -> list[ExpenseResponse]:
    """
    Return all non-deleted expenses belonging to one user, newest first.

    Each expense includes only its non-deleted items.
    Returns an empty list when the user has no expenses.
    """
    expenses = (
        db.query(Expense)
        .filter(
            Expense.user_id == user_id,
            Expense.deleted_at.is_(None),
        )
        .order_by(Expense.created_at.desc(), Expense.id.desc())
        .all()
    )

    result = []
    for expense in expenses:
        items = _get_non_deleted_items(db, expense.id)
        result.append(_build_expense_response(expense, items))
    return result


def get_user_expense_by_id(
    db: Session,
    user_id: int,
    expense_id: int,
) -> ExpenseResponse | None:
    """
    Return one owned, non-deleted expense with its non-deleted items.

    Returns None when the expense does not exist, belongs to another user,
    or has been soft-deleted — so the caller can safely return 404 without
    revealing whether another user's expense exists.
    """
    expense = (
        db.query(Expense)
        .filter(
            Expense.id == expense_id,
            Expense.user_id == user_id,
            Expense.deleted_at.is_(None),
        )
        .first()
    )

    if expense is None:
        return None

    items = _get_non_deleted_items(db, expense.id)
    return _build_expense_response(expense, items)


# ── Update ─────────────────────────────────────────────────────────────────────

def update_user_expense(
    db: Session,
    user_id: int,
    expense_id: int,
    data: ExpenseUpdate,
) -> ExpenseResponse | None:
    """
    Partially update one owned, non-deleted expense.

    Only fields present in the request body are written.
    Items are replaced only when the 'items' key was provided.
    Returns None when the expense is unavailable; the route converts this to 404.
    """
    expense = (
        db.query(Expense)
        .filter(
            Expense.id == expense_id,
            Expense.user_id == user_id,
            Expense.deleted_at.is_(None),
        )
        .first()
    )
    if expense is None:
        return None

    updates = data.model_dump(exclude_unset=True)

    # Validate new category before touching anything
    if "category_id" in updates:
        _get_valid_category(db, updates["category_id"], "Category not found")

    # Validate all new item categories before touching anything
    new_items_data = updates.pop("items", None)  # None means not provided
    if new_items_data is not None:
        for item_dict in new_items_data:
            cat_id = item_dict.get("category_id")
            if cat_id is not None:
                _get_valid_category(db, cat_id, "Item category not found")

    # Simple-field editable names that the client is allowed to change
    _EDITABLE = {
        "category_id", "title", "merchant_name", "receipt_number", "receipt_date",
        "payment_method", "currency", "subtotal", "tax_amount", "discount_amount",
        "total_amount", "notes",
    }

    try:
        # Apply simple field updates
        for field, value in updates.items():
            if field in _EDITABLE:
                setattr(expense, field, value)

        # Replace items only when the key was present in the request
        if new_items_data is not None:
            now = datetime.now(timezone.utc).replace(tzinfo=None)

            # Soft-delete all existing active items
            active_items = _get_non_deleted_items(db, expense.id)
            for item in active_items:
                item.deleted_at = now

            # Create all new item records
            created_items: list[ExpenseItem] = []
            for item_dict in new_items_data:
                item = ExpenseItem(
                    expense_id=expense.id,
                    category_id=item_dict.get("category_id"),
                    original_name=item_dict["original_name"],
                    name_en=item_dict.get("name_en"),
                    name_th=item_dict.get("name_th"),
                    quantity=item_dict["quantity"],
                    unit=item_dict.get("unit"),
                    unit_price=item_dict.get("unit_price"),
                    discount_amount=item_dict.get("discount_amount", 0),
                    total_price=item_dict["total_price"],
                )
                db.add(item)
                created_items.append(item)

            db.flush()
            for item in created_items:
                db.refresh(item)

        db.flush()
        db.commit()
        db.refresh(expense)

        items = _get_non_deleted_items(db, expense.id)
        return _build_expense_response(expense, items)

    except ExpenseServiceError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise


# ── Delete ─────────────────────────────────────────────────────────────────────

def delete_user_expense(
    db: Session,
    user_id: int,
    expense_id: int,
) -> bool:
    """
    Soft-delete an owned expense and all its active items.

    Returns False when the expense is unavailable (missing, wrong owner, already deleted).
    Does not permanently delete rows or touch receipt files.
    """
    expense = (
        db.query(Expense)
        .filter(
            Expense.id == expense_id,
            Expense.user_id == user_id,
            Expense.deleted_at.is_(None),
        )
        .first()
    )
    if expense is None:
        return False

    try:
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        expense.deleted_at = now

        active_items = _get_non_deleted_items(db, expense.id)
        for item in active_items:
            item.deleted_at = now

        db.commit()
        return True

    except Exception:
        db.rollback()
        raise
