"""Tests for expense_service.create_expense (uses smart_receipt_db_test)."""

from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.category import Category
from app.models.expense import Expense
from app.models.expense_item import ExpenseItem
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.expense import ExpenseCreate
from app.schemas.expense_item import ExpenseItemCreate
from app.services.expense_service import ExpenseServiceError, create_expense
from app.utils.password_utils import hash_password

# ── Test DB ───────────────────────────────────────────────────────────────────
settings.JWT_SECRET_KEY = "test_jwt_secret_key_expense_service_testing_benz_2004"
settings.JWT_ALGORITHM = "HS256"

engine = create_engine(settings.TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_category(db, *, name_en="Food", name_th="อาหาร", code="FOOD",
                  is_active=True, deleted_at=None) -> Category:
    cat = Category(
        code=code,
        name_en=name_en,
        name_th=name_th,
        is_active=is_active,
        deleted_at=deleted_at,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


def make_user(db, *, username="tester", email="tester@example.com") -> User:
    user = User(
        username=username,
        email=email,
        password_hash=hash_password("password123"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def base_data(category_id: int, **overrides) -> ExpenseCreate:
    defaults = dict(
        category_id=category_id,
        title="Lunch",
        receipt_date=date(2025, 6, 1),
        total_amount=Decimal("100.00"),
        currency="THB",
        items=[],
    )
    defaults.update(overrides)
    return ExpenseCreate(**defaults)


def item_data(**overrides) -> ExpenseItemCreate:
    defaults = dict(
        original_name="Coffee",
        quantity=Decimal("1"),
        total_price=Decimal("50.00"),
    )
    defaults.update(overrides)
    return ExpenseItemCreate(**defaults)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clean_db():
    from app.models.receipt_file import ReceiptFile
    db = TestingSessionLocal()
    db.query(ExpenseItem).delete()
    db.query(Expense).delete()
    db.query(Category).delete()
    db.query(RefreshToken).delete()
    db.query(ReceiptFile).delete()
    db.query(User).delete()
    db.commit()
    yield
    db.query(ExpenseItem).delete()
    db.query(Expense).delete()
    db.query(Category).delete()
    db.query(RefreshToken).delete()
    db.query(ReceiptFile).delete()
    db.query(User).delete()
    db.commit()
    db.close()


@pytest.fixture()
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def user(db):
    return make_user(db)


@pytest.fixture()
def category(db):
    return make_category(db)


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_successful_expense_creation(db, user, category):
    data = base_data(category.id)
    expense = create_expense(db, user.id, data)
    assert expense.id is not None


def test_expense_belongs_to_correct_user(db, user, category):
    data = base_data(category.id)
    expense = create_expense(db, user.id, data)
    assert expense.user_id == user.id


def test_main_category_is_stored_correctly(db, user, category):
    data = base_data(category.id)
    expense = create_expense(db, user.id, data)
    assert expense.category_id == category.id


def test_money_fields_are_stored_correctly(db, user, category):
    data = base_data(
        category.id,
        subtotal=Decimal("90.00"),
        tax_amount=Decimal("7.00"),
        discount_amount=Decimal("2.00"),
        total_amount=Decimal("95.00"),
    )
    expense = create_expense(db, user.id, data)
    assert expense.total_amount == Decimal("95.00")
    assert expense.subtotal == Decimal("90.00")
    assert expense.tax_amount == Decimal("7.00")
    assert expense.discount_amount == Decimal("2.00")


def test_currency_stored_uppercase(db, user, category):
    data = base_data(category.id, currency="usd")
    expense = create_expense(db, user.id, data)
    assert expense.currency == "USD"


def test_expense_with_no_items_is_created(db, user, category):
    data = base_data(category.id, items=[])
    expense = create_expense(db, user.id, data)
    assert expense.id is not None
    assert expense.items == []


def test_expense_with_one_item_is_created(db, user, category):
    data = base_data(category.id, items=[item_data()])
    expense = create_expense(db, user.id, data)
    assert len(expense.items) == 1


def test_expense_with_multiple_items_is_created(db, user, category):
    items = [item_data(original_name=f"Item {i}") for i in range(3)]
    data = base_data(category.id, items=items)
    expense = create_expense(db, user.id, data)
    assert len(expense.items) == 3


def test_created_items_use_correct_expense_id(db, user, category):
    data = base_data(category.id, items=[item_data(), item_data(original_name="Tea")])
    expense = create_expense(db, user.id, data)
    for item in expense.items:
        assert item.expense_id == expense.id


def test_invalid_main_category_is_rejected(db, user):
    data = base_data(category_id=999999)
    with pytest.raises(ExpenseServiceError) as exc_info:
        create_expense(db, user.id, data)
    assert exc_info.value.status_code == 404


def test_inactive_main_category_is_rejected(db, user, db2=None):
    db_session = TestingSessionLocal()
    cat = make_category(db_session, code="INACTIVE", name_en="Inactive Cat",
                        name_th="ไม่ใช้งาน", is_active=False)
    data = base_data(category_id=cat.id)
    with pytest.raises(ExpenseServiceError) as exc_info:
        create_expense(db_session, user.id, data)
    assert exc_info.value.status_code == 404
    db_session.close()


def test_soft_deleted_main_category_is_rejected(db, user):
    cat = make_category(db, code="DELETED", name_en="Deleted Cat",
                        name_th="ลบแล้ว", deleted_at=datetime(2024, 1, 1))
    data = base_data(category_id=cat.id)
    with pytest.raises(ExpenseServiceError) as exc_info:
        create_expense(db, user.id, data)
    assert exc_info.value.status_code == 404


def test_invalid_item_category_is_rejected(db, user, category):
    items = [item_data(category_id=999999)]
    data = base_data(category.id, items=items)
    with pytest.raises(ExpenseServiceError) as exc_info:
        create_expense(db, user.id, data)
    assert exc_info.value.status_code == 404


def test_inactive_item_category_is_rejected(db, user, category):
    item_cat = make_category(db, code="ITEM_INACTIVE", name_en="Item Inactive",
                             name_th="ไม่ใช้งาน", is_active=False)
    items = [item_data(category_id=item_cat.id)]
    data = base_data(category.id, items=items)
    with pytest.raises(ExpenseServiceError) as exc_info:
        create_expense(db, user.id, data)
    assert exc_info.value.status_code == 404


def test_soft_deleted_item_category_is_rejected(db, user, category):
    item_cat = make_category(db, code="ITEM_DELETED", name_en="Item Deleted",
                             name_th="ลบแล้ว", deleted_at=datetime(2024, 1, 1))
    items = [item_data(category_id=item_cat.id)]
    data = base_data(category.id, items=items)
    with pytest.raises(ExpenseServiceError) as exc_info:
        create_expense(db, user.id, data)
    assert exc_info.value.status_code == 404


def test_if_one_item_fails_no_expense_remains(db, user, category):
    """Force an item creation failure by passing an invalid category_id."""
    items = [item_data(), item_data(category_id=999999)]
    data = base_data(category.id, items=items)
    with pytest.raises(ExpenseServiceError):
        create_expense(db, user.id, data)
    count = db.query(Expense).filter(Expense.user_id == user.id).count()
    assert count == 0


def test_if_one_item_fails_no_partial_items_remain(db, user, category):
    items = [item_data(), item_data(category_id=999999)]
    data = base_data(category.id, items=items)
    with pytest.raises(ExpenseServiceError):
        create_expense(db, user.id, data)
    count = db.query(ExpenseItem).count()
    assert count == 0


def test_internal_ai_fields_cannot_be_set_through_expense_create(db, user, category):
    """ExpenseCreate schema must not expose ai_* or internal fields."""
    fields = ExpenseCreate.model_fields
    for forbidden in ("ai_confidence", "ai_status", "ai_raw_response",
                      "language_detected", "deleted_at", "user_id"):
        assert forbidden not in fields, f"ExpenseCreate must not have field: {forbidden}"


def test_returned_expense_includes_nested_items(db, user, category):
    data = base_data(category.id, items=[item_data(), item_data(original_name="Tea")])
    expense = create_expense(db, user.id, data)
    assert len(expense.items) == 2
    assert expense.items[0].original_name in ("Coffee", "Tea")


def test_user_id_always_comes_from_service_argument(db, user, category):
    """user_id must come from the service argument, not from ExpenseCreate."""
    assert "user_id" not in ExpenseCreate.model_fields
    data = base_data(category.id)
    expense = create_expense(db, user.id, data)
    assert expense.user_id == user.id


# ── Import new service functions ──────────────────────────────────────────────
from app.services.expense_service import get_user_expenses, get_user_expense_by_id
from datetime import datetime as dt


# ── Helpers for read tests ────────────────────────────────────────────────────

def make_expense(db, user_id: int, category_id: int, *,
                 title: str = "Test Expense",
                 receipt_date=date(2025, 6, 1),
                 total_amount: Decimal = Decimal("100.00"),
                 deleted_at=None) -> Expense:
    """Directly insert an expense row for read-test setup."""
    expense = Expense(
        user_id=user_id,
        category_id=category_id,
        title=title,
        receipt_date=receipt_date,
        total_amount=total_amount,
        currency="THB",
        input_method="manual",
        deleted_at=deleted_at,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


def make_item(db, expense_id: int, *,
              original_name: str = "Coffee",
              total_price: Decimal = Decimal("50.00"),
              deleted_at=None) -> ExpenseItem:
    """Directly insert an expense item row for read-test setup."""
    item = ExpenseItem(
        expense_id=expense_id,
        original_name=original_name,
        quantity=Decimal("1"),
        total_price=total_price,
        deleted_at=deleted_at,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


# ── get_user_expenses tests ───────────────────────────────────────────────────

def test_get_user_expenses_returns_own_expenses(db, user, category):
    make_expense(db, user.id, category.id, title="Mine")
    results = get_user_expenses(db, user.id)
    assert len(results) == 1
    assert results[0].title == "Mine"
    assert results[0].user_id == user.id


def test_get_user_expenses_excludes_other_users_expenses(db, category):
    user_a = make_user(db, username="user_a", email="a@example.com")
    user_b = make_user(db, username="user_b", email="b@example.com")
    make_expense(db, user_a.id, category.id, title="A's expense")
    make_expense(db, user_b.id, category.id, title="B's expense")
    results = get_user_expenses(db, user_a.id)
    assert len(results) == 1
    assert results[0].user_id == user_a.id


def test_get_user_expenses_excludes_soft_deleted_expenses(db, user, category):
    make_expense(db, user.id, category.id, title="Active")
    make_expense(db, user.id, category.id, title="Deleted", deleted_at=dt(2024, 1, 1))
    results = get_user_expenses(db, user.id)
    assert len(results) == 1
    assert results[0].title == "Active"


def test_get_user_expenses_empty_table_returns_empty_list(db, user):
    results = get_user_expenses(db, user.id)
    assert results == []


def test_get_user_expenses_user_with_no_expenses_returns_empty_list(db, category):
    user_a = make_user(db, username="user_a2", email="a2@example.com")
    user_b = make_user(db, username="user_b2", email="b2@example.com")
    make_expense(db, user_b.id, category.id, title="Only B has one")
    results = get_user_expenses(db, user_a.id)
    assert results == []


def test_get_user_expenses_ordered_newest_first(db, user, category):
    from datetime import datetime as dt2
    import time
    e1 = make_expense(db, user.id, category.id, title="First")
    time.sleep(0.05)  # ensure distinct created_at
    e2 = make_expense(db, user.id, category.id, title="Second")
    results = get_user_expenses(db, user.id)
    assert results[0].id == e2.id
    assert results[1].id == e1.id


def test_get_user_expenses_stable_ordering_by_id_when_dates_equal(db, user, category):
    """When created_at is the same, ordering falls back to id descending."""
    e1 = make_expense(db, user.id, category.id, title="Earlier ID")
    e2 = make_expense(db, user.id, category.id, title="Later ID")
    results = get_user_expenses(db, user.id)
    # Either created_at or id desc — later id should come first
    assert results[0].id == e2.id


def test_get_user_expenses_includes_nested_items(db, user, category):
    expense = make_expense(db, user.id, category.id)
    make_item(db, expense.id, original_name="Coffee")
    make_item(db, expense.id, original_name="Tea")
    results = get_user_expenses(db, user.id)
    assert len(results[0].items) == 2


def test_get_user_expenses_excludes_soft_deleted_items(db, user, category):
    expense = make_expense(db, user.id, category.id)
    make_item(db, expense.id, original_name="Active item")
    make_item(db, expense.id, original_name="Deleted item", deleted_at=dt(2024, 1, 1))
    results = get_user_expenses(db, user.id)
    assert len(results[0].items) == 1
    assert results[0].items[0].original_name == "Active item"


def test_get_user_expenses_item_order_is_stable(db, user, category):
    expense = make_expense(db, user.id, category.id)
    i1 = make_item(db, expense.id, original_name="A")
    i2 = make_item(db, expense.id, original_name="B")
    results = get_user_expenses(db, user.id)
    ids = [item.id for item in results[0].items]
    assert ids == sorted(ids)


# ── get_user_expense_by_id tests ──────────────────────────────────────────────

def test_get_user_expense_by_id_returns_owned_expense(db, user, category):
    expense = make_expense(db, user.id, category.id)
    result = get_user_expense_by_id(db, user.id, expense.id)
    assert result is not None
    assert result.id == expense.id


def test_get_user_expense_by_id_includes_nested_items(db, user, category):
    expense = make_expense(db, user.id, category.id)
    make_item(db, expense.id, original_name="Burger")
    result = get_user_expense_by_id(db, user.id, expense.id)
    assert len(result.items) == 1
    assert result.items[0].original_name == "Burger"


def test_get_user_expense_by_id_unknown_id_returns_none(db, user):
    result = get_user_expense_by_id(db, user.id, 999999)
    assert result is None


def test_get_user_expense_by_id_another_users_expense_returns_none(db, category):
    user_a = make_user(db, username="owner_a", email="owner_a@example.com")
    user_b = make_user(db, username="viewer_b", email="viewer_b@example.com")
    expense = make_expense(db, user_a.id, category.id)
    result = get_user_expense_by_id(db, user_b.id, expense.id)
    assert result is None


def test_get_user_expense_by_id_soft_deleted_returns_none(db, user, category):
    expense = make_expense(db, user.id, category.id, deleted_at=dt(2024, 1, 1))
    result = get_user_expense_by_id(db, user.id, expense.id)
    assert result is None


def test_get_user_expense_by_id_excludes_soft_deleted_items(db, user, category):
    expense = make_expense(db, user.id, category.id)
    make_item(db, expense.id, original_name="Keep")
    make_item(db, expense.id, original_name="Remove", deleted_at=dt(2024, 1, 1))
    result = get_user_expense_by_id(db, user.id, expense.id)
    assert len(result.items) == 1
    assert result.items[0].original_name == "Keep"


def test_get_user_expense_by_id_does_not_expose_internal_ai_fields(db, user, category):
    expense = make_expense(db, user.id, category.id)
    result = get_user_expense_by_id(db, user.id, expense.id)
    result_dict = result.model_dump()
    for field in ("ai_confidence", "ai_status", "ai_raw_response", "language_detected"):
        assert field not in result_dict, f"Response must not expose: {field}"


def test_get_user_expense_by_id_does_not_expose_deleted_at(db, user, category):
    expense = make_expense(db, user.id, category.id)
    result = get_user_expense_by_id(db, user.id, expense.id)
    assert "deleted_at" not in result.model_dump()


# ── Import update / delete service functions ──────────────────────────────────
from app.services.expense_service import update_user_expense, delete_user_expense
from app.schemas.expense import ExpenseUpdate, ExpenseResponse as ExpenseResponseSchema


def update_data(**kwargs) -> ExpenseUpdate:
    """Build an ExpenseUpdate with only the supplied fields set."""
    return ExpenseUpdate(**kwargs)


# ── update_user_expense tests ─────────────────────────────────────────────────

def test_update_simple_fields_succeeds(db, user, category):
    expense = make_expense(db, user.id, category.id, title="Old Title")
    result = update_user_expense(db, user.id, expense.id, update_data(title="New Title"))
    assert result is not None
    assert result.title == "New Title"


def test_update_returns_expense_response(db, user, category):
    expense = make_expense(db, user.id, category.id)
    result = update_user_expense(db, user.id, expense.id, update_data(title="Updated"))
    assert isinstance(result, ExpenseResponseSchema)


def test_missing_fields_remain_unchanged(db, user, category):
    expense = make_expense(db, user.id, category.id, title="Keep Me",
                           total_amount=Decimal("200.00"))
    # Update only notes — title and total_amount must be unchanged
    result = update_user_expense(db, user.id, expense.id, update_data(notes="Added note"))
    assert result.title == "Keep Me"
    assert result.total_amount == Decimal("200.00")


def test_empty_update_is_accepted_and_changes_nothing(db, user, category):
    expense = make_expense(db, user.id, category.id, title="Unchanged",
                           total_amount=Decimal("50.00"))
    result = update_user_expense(db, user.id, expense.id, ExpenseUpdate())
    assert result is not None
    assert result.title == "Unchanged"
    assert result.total_amount == Decimal("50.00")


def test_update_category_to_another_valid_category(db, user, category):
    new_cat = make_category(db, code="TRAVEL", name_en="Travel", name_th="ท่องเที่ยว")
    expense = make_expense(db, user.id, category.id)
    result = update_user_expense(db, user.id, expense.id,
                                 update_data(category_id=new_cat.id))
    assert result.category_id == new_cat.id


def test_update_invalid_category_is_rejected(db, user, category):
    expense = make_expense(db, user.id, category.id)
    with pytest.raises(ExpenseServiceError) as exc_info:
        update_user_expense(db, user.id, expense.id,
                            update_data(category_id=999999))
    assert exc_info.value.status_code == 404


def test_update_inactive_category_is_rejected(db, user, category):
    inactive = make_category(db, code="INACT_U", name_en="Inactive",
                             name_th="ไม่ใช้งาน", is_active=False)
    expense = make_expense(db, user.id, category.id)
    with pytest.raises(ExpenseServiceError) as exc_info:
        update_user_expense(db, user.id, expense.id,
                            update_data(category_id=inactive.id))
    assert exc_info.value.status_code == 404


def test_update_soft_deleted_category_is_rejected(db, user, category):
    deleted_cat = make_category(db, code="DEL_U", name_en="Deleted",
                                name_th="ลบแล้ว", deleted_at=datetime(2024, 1, 1))
    expense = make_expense(db, user.id, category.id)
    with pytest.raises(ExpenseServiceError) as exc_info:
        update_user_expense(db, user.id, expense.id,
                            update_data(category_id=deleted_cat.id))
    assert exc_info.value.status_code == 404


def test_update_another_users_expense_returns_none(db, category):
    user_a = make_user(db, username="upd_a", email="upd_a@example.com")
    user_b = make_user(db, username="upd_b", email="upd_b@example.com")
    expense = make_expense(db, user_a.id, category.id)
    result = update_user_expense(db, user_b.id, expense.id,
                                 update_data(title="Stolen"))
    assert result is None


def test_update_soft_deleted_expense_returns_none(db, user, category):
    expense = make_expense(db, user.id, category.id,
                           deleted_at=datetime(2024, 1, 1))
    result = update_user_expense(db, user.id, expense.id,
                                 update_data(title="Ghost"))
    assert result is None


def test_update_unknown_expense_returns_none(db, user):
    result = update_user_expense(db, user.id, 999999, update_data(title="Nothing"))
    assert result is None


def test_update_without_items_preserves_current_items(db, user, category):
    expense = make_expense(db, user.id, category.id)
    make_item(db, expense.id, original_name="Coffee")
    result = update_user_expense(db, user.id, expense.id,
                                 update_data(title="New Title"))
    assert len(result.items) == 1
    assert result.items[0].original_name == "Coffee"


def test_update_with_empty_items_soft_deletes_all_active_items(db, user, category):
    expense = make_expense(db, user.id, category.id)
    make_item(db, expense.id, original_name="Coffee")
    make_item(db, expense.id, original_name="Tea")
    result = update_user_expense(db, user.id, expense.id,
                                 update_data(items=[]))
    assert result.items == []


def test_update_with_items_replaces_old_active_items(db, user, category):
    expense = make_expense(db, user.id, category.id)
    make_item(db, expense.id, original_name="Old Item")
    new_items = [item_data(original_name="New Item")]
    result = update_user_expense(db, user.id, expense.id,
                                 update_data(items=new_items))
    assert len(result.items) == 1
    assert result.items[0].original_name == "New Item"


def test_old_item_rows_remain_as_soft_deleted(db, user, category):
    expense = make_expense(db, user.id, category.id)
    old_item = make_item(db, expense.id, original_name="Old")
    update_user_expense(db, user.id, expense.id, update_data(items=[]))
    row = db.query(ExpenseItem).filter(ExpenseItem.id == old_item.id).first()
    assert row is not None
    assert row.deleted_at is not None


def test_new_items_use_correct_expense_id(db, user, category):
    expense = make_expense(db, user.id, category.id)
    new_items = [item_data(original_name="New")]
    result = update_user_expense(db, user.id, expense.id,
                                 update_data(items=new_items))
    assert result.items[0].expense_id == expense.id


def test_update_invalid_new_item_category_rejects_full_update(db, user, category):
    expense = make_expense(db, user.id, category.id, title="Original")
    bad_items = [item_data(category_id=999999)]
    with pytest.raises(ExpenseServiceError):
        update_user_expense(db, user.id, expense.id,
                            update_data(title="Should not save", items=bad_items))
    # Title must not have changed
    db_expense = db.query(Expense).filter(Expense.id == expense.id).first()
    assert db_expense.title == "Original"


def test_failed_item_replacement_rolls_back_field_changes(db, user, category):
    expense = make_expense(db, user.id, category.id, title="Before")
    bad_items = [item_data(category_id=999999)]
    with pytest.raises(ExpenseServiceError):
        update_user_expense(db, user.id, expense.id,
                            update_data(title="After", items=bad_items))
    db.expire(expense)
    db.refresh(expense)
    assert expense.title == "Before"


def test_failed_item_replacement_keeps_old_items_active(db, user, category):
    expense = make_expense(db, user.id, category.id)
    make_item(db, expense.id, original_name="Survivor")
    bad_items = [item_data(category_id=999999)]
    with pytest.raises(ExpenseServiceError):
        update_user_expense(db, user.id, expense.id, update_data(items=bad_items))
    items = db.query(ExpenseItem).filter(
        ExpenseItem.expense_id == expense.id,
        ExpenseItem.deleted_at.is_(None),
    ).all()
    assert len(items) == 1
    assert items[0].original_name == "Survivor"


def test_current_user_remains_owner_after_update(db, user, category):
    expense = make_expense(db, user.id, category.id)
    result = update_user_expense(db, user.id, expense.id,
                                 update_data(title="Changed"))
    assert result.user_id == user.id


# ── delete_user_expense tests ──────────────────────────────────────────────────

def test_successful_delete_sets_expense_deleted_at(db, user, category):
    expense = make_expense(db, user.id, category.id)
    result = delete_user_expense(db, user.id, expense.id)
    assert result is True
    db.expire(expense)
    db.refresh(expense)
    assert expense.deleted_at is not None


def test_successful_delete_soft_deletes_all_active_items(db, user, category):
    expense = make_expense(db, user.id, category.id)
    make_item(db, expense.id, original_name="Item 1")
    make_item(db, expense.id, original_name="Item 2")
    delete_user_expense(db, user.id, expense.id)
    active = db.query(ExpenseItem).filter(
        ExpenseItem.expense_id == expense.id,
        ExpenseItem.deleted_at.is_(None),
    ).all()
    assert active == []


def test_expense_and_items_use_consistent_delete_timestamp(db, user, category):
    expense = make_expense(db, user.id, category.id)
    item = make_item(db, expense.id, original_name="Coffee")
    delete_user_expense(db, user.id, expense.id)
    db.expire(expense)
    db.refresh(expense)
    db.expire(item)
    db.refresh(item)
    assert expense.deleted_at == item.deleted_at


def test_deleted_expense_row_remains_in_database(db, user, category):
    expense = make_expense(db, user.id, category.id)
    expense_id = expense.id
    delete_user_expense(db, user.id, expense.id)
    row = db.query(Expense).filter(Expense.id == expense_id).first()
    assert row is not None


def test_deleted_item_rows_remain_in_database(db, user, category):
    expense = make_expense(db, user.id, category.id)
    item = make_item(db, expense.id, original_name="Leftover")
    item_id = item.id
    delete_user_expense(db, user.id, expense.id)
    row = db.query(ExpenseItem).filter(ExpenseItem.id == item_id).first()
    assert row is not None


def test_unknown_expense_delete_returns_false(db, user):
    result = delete_user_expense(db, user.id, 999999)
    assert result is False


def test_another_users_expense_delete_returns_false(db, category):
    user_a = make_user(db, username="del_a", email="del_a@example.com")
    user_b = make_user(db, username="del_b", email="del_b@example.com")
    expense = make_expense(db, user_a.id, category.id)
    result = delete_user_expense(db, user_b.id, expense.id)
    assert result is False


def test_already_deleted_expense_delete_returns_false(db, user, category):
    expense = make_expense(db, user.id, category.id,
                           deleted_at=datetime(2024, 1, 1))
    result = delete_user_expense(db, user.id, expense.id)
    assert result is False


def test_delete_does_not_touch_receipt_files(db, user, category):
    """Deleting an expense must not affect ReceiptFile rows."""
    from app.models.receipt_file import ReceiptFile
    expense = make_expense(db, user.id, category.id)
    # Attach a dummy receipt file via ORM (no real file required for this check)
    receipt = ReceiptFile(
        user_id=user.id,
        expense_id=expense.id,
        original_filename="test.jpg",
        stored_filename="test.jpg",
        file_path="/uploads/test.jpg",
        file_size=1000,
        mime_type="image/jpeg",
    )
    db.add(receipt)
    db.commit()
    db.refresh(receipt)
    receipt_id = receipt.id

    delete_user_expense(db, user.id, expense.id)

    # The receipt row must still exist and be unmodified
    row = db.query(ReceiptFile).filter(ReceiptFile.id == receipt_id).first()
    assert row is not None
    assert row.deleted_at is None


def test_delete_response_does_not_expose_internal_fields(db, user, category):
    """The function returns True/False, not an ORM object — no internal fields exposed."""
    expense = make_expense(db, user.id, category.id)
    result = delete_user_expense(db, user.id, expense.id)
    assert isinstance(result, bool)


# ═══════════════════════════════════════════════════════════════════════════════
# Receipt-link service tests
# ═══════════════════════════════════════════════════════════════════════════════

import tempfile
import os
from app.models.receipt_file import ReceiptFile
from app.services.expense_service import link_receipt_to_expense, unlink_receipt_from_expense


def make_receipt(db, user_id: int, *, expense_id=None, deleted_at=None,
                 stored_filename=None) -> ReceiptFile:
    """Insert a ReceiptFile row directly for test setup."""
    if stored_filename is None:
        import uuid
        stored_filename = f"{uuid.uuid4().hex}.jpg"
    receipt = ReceiptFile(
        user_id=user_id,
        expense_id=expense_id,
        original_filename="receipt.jpg",
        stored_filename=stored_filename,
        file_path=f"/uploads/{stored_filename}",
        mime_type="image/jpeg",
        file_size=1000,
        upload_status="uploaded",
        deleted_at=deleted_at,
    )
    db.add(receipt)
    db.commit()
    db.refresh(receipt)
    return receipt


# ── link_receipt_to_expense ───────────────────────────────────────────────────

def test_link_receipt_succeeds(db, user, category):
    expense = make_expense(db, user.id, category.id)
    receipt = make_receipt(db, user.id)
    result = link_receipt_to_expense(db, user.id, expense.id, receipt.id)
    assert result is not None


def test_link_stores_correct_expense_id(db, user, category):
    expense = make_expense(db, user.id, category.id)
    receipt = make_receipt(db, user.id)
    result = link_receipt_to_expense(db, user.id, expense.id, receipt.id)
    assert result.expense_id == expense.id


def test_link_same_expense_is_idempotent(db, user, category):
    expense = make_expense(db, user.id, category.id)
    receipt = make_receipt(db, user.id, expense_id=expense.id)
    # Already linked — should succeed without error
    result = link_receipt_to_expense(db, user.id, expense.id, receipt.id)
    assert result.expense_id == expense.id


def test_link_receipt_already_linked_elsewhere_raises_409(db, user, category):
    expense_a = make_expense(db, user.id, category.id, title="A")
    expense_b = make_expense(db, user.id, category.id, title="B")
    receipt = make_receipt(db, user.id, expense_id=expense_a.id)
    with pytest.raises(ExpenseServiceError) as exc_info:
        link_receipt_to_expense(db, user.id, expense_b.id, receipt.id)
    assert exc_info.value.status_code == 409


def test_link_unknown_expense_raises_404(db, user, category):
    receipt = make_receipt(db, user.id)
    with pytest.raises(ExpenseServiceError) as exc_info:
        link_receipt_to_expense(db, user.id, 999999, receipt.id)
    assert exc_info.value.status_code == 404


def test_link_unknown_receipt_raises_404(db, user, category):
    expense = make_expense(db, user.id, category.id)
    with pytest.raises(ExpenseServiceError) as exc_info:
        link_receipt_to_expense(db, user.id, expense.id, 999999)
    assert exc_info.value.status_code == 404


def test_link_another_users_expense_raises_404(db, category):
    user_a = make_user(db, username="lnk_a", email="lnk_a@example.com")
    user_b = make_user(db, username="lnk_b", email="lnk_b@example.com")
    expense = make_expense(db, user_a.id, category.id)
    receipt = make_receipt(db, user_b.id)
    with pytest.raises(ExpenseServiceError) as exc_info:
        link_receipt_to_expense(db, user_b.id, expense.id, receipt.id)
    assert exc_info.value.status_code == 404


def test_link_another_users_receipt_raises_404(db, category):
    user_a = make_user(db, username="lnk_c", email="lnk_c@example.com")
    user_b = make_user(db, username="lnk_d", email="lnk_d@example.com")
    expense = make_expense(db, user_a.id, category.id)
    receipt = make_receipt(db, user_b.id)
    with pytest.raises(ExpenseServiceError) as exc_info:
        link_receipt_to_expense(db, user_a.id, expense.id, receipt.id)
    assert exc_info.value.status_code == 404


def test_link_soft_deleted_expense_raises_404(db, user, category):
    expense = make_expense(db, user.id, category.id, deleted_at=dt(2024, 1, 1))
    receipt = make_receipt(db, user.id)
    with pytest.raises(ExpenseServiceError) as exc_info:
        link_receipt_to_expense(db, user.id, expense.id, receipt.id)
    assert exc_info.value.status_code == 404


def test_link_soft_deleted_receipt_raises_404(db, user, category):
    expense = make_expense(db, user.id, category.id)
    receipt = make_receipt(db, user.id, deleted_at=dt(2024, 1, 1))
    with pytest.raises(ExpenseServiceError) as exc_info:
        link_receipt_to_expense(db, user.id, expense.id, receipt.id)
    assert exc_info.value.status_code == 404


# ── unlink_receipt_from_expense ───────────────────────────────────────────────

def test_unlink_receipt_succeeds(db, user, category):
    expense = make_expense(db, user.id, category.id)
    receipt = make_receipt(db, user.id, expense_id=expense.id)
    result = unlink_receipt_from_expense(db, user.id, expense.id, receipt.id)
    assert result.expense_id is None


def test_unlink_preserves_receipt_row(db, user, category):
    expense = make_expense(db, user.id, category.id)
    receipt = make_receipt(db, user.id, expense_id=expense.id)
    receipt_id = receipt.id
    unlink_receipt_from_expense(db, user.id, expense.id, receipt.id)
    row = db.query(ReceiptFile).filter(ReceiptFile.id == receipt_id).first()
    assert row is not None
    assert row.deleted_at is None


def test_unlink_preserves_physical_file(db, user, category):
    """Unlink must not delete the physical file — only the DB reference changes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        fake_path = os.path.join(tmpdir, "receipt.jpg")
        with open(fake_path, "wb") as f:
            f.write(b"fake image data")

        expense = make_expense(db, user.id, category.id)
        receipt = make_receipt(db, user.id, expense_id=expense.id)
        # Override file_path to the temp file so we can check it afterward
        receipt.file_path = fake_path
        db.commit()

        unlink_receipt_from_expense(db, user.id, expense.id, receipt.id)

        assert os.path.exists(fake_path), "Physical file must not be deleted on unlink"


def test_unlink_wrong_expense_raises_409(db, user, category):
    expense_a = make_expense(db, user.id, category.id, title="A")
    expense_b = make_expense(db, user.id, category.id, title="B")
    receipt = make_receipt(db, user.id, expense_id=expense_a.id)
    with pytest.raises(ExpenseServiceError) as exc_info:
        unlink_receipt_from_expense(db, user.id, expense_b.id, receipt.id)
    assert exc_info.value.status_code == 409


def test_unlink_unlinked_receipt_raises_409(db, user, category):
    expense = make_expense(db, user.id, category.id)
    receipt = make_receipt(db, user.id)  # expense_id is None
    with pytest.raises(ExpenseServiceError) as exc_info:
        unlink_receipt_from_expense(db, user.id, expense.id, receipt.id)
    assert exc_info.value.status_code == 409


def test_unlink_unknown_expense_raises_404(db, user, category):
    receipt = make_receipt(db, user.id)
    with pytest.raises(ExpenseServiceError) as exc_info:
        unlink_receipt_from_expense(db, user.id, 999999, receipt.id)
    assert exc_info.value.status_code == 404


def test_unlink_unknown_receipt_raises_404(db, user, category):
    expense = make_expense(db, user.id, category.id)
    with pytest.raises(ExpenseServiceError) as exc_info:
        unlink_receipt_from_expense(db, user.id, expense.id, 999999)
    assert exc_info.value.status_code == 404


def test_unlink_another_users_records_raises_404(db, category):
    user_a = make_user(db, username="ulnk_a", email="ulnk_a@example.com")
    user_b = make_user(db, username="ulnk_b", email="ulnk_b@example.com")
    expense = make_expense(db, user_a.id, category.id)
    receipt = make_receipt(db, user_a.id, expense_id=expense.id)
    with pytest.raises(ExpenseServiceError) as exc_info:
        unlink_receipt_from_expense(db, user_b.id, expense.id, receipt.id)
    assert exc_info.value.status_code == 404


def test_link_db_failure_rolls_back(db, user, category):
    """Simulate a DB failure: receipt.expense_id must stay None after rollback."""
    from unittest.mock import patch
    expense = make_expense(db, user.id, category.id)
    receipt = make_receipt(db, user.id)

    original_commit = db.commit

    def fail_once():
        db.commit = original_commit  # restore before raising
        raise RuntimeError("Simulated DB failure")

    db.commit = fail_once

    with pytest.raises(RuntimeError):
        link_receipt_to_expense(db, user.id, expense.id, receipt.id)

    db.expire(receipt)
    db.refresh(receipt)
    assert receipt.expense_id is None


def test_unlink_db_failure_rolls_back(db, user, category):
    """Simulate a DB failure: receipt.expense_id must stay set after rollback."""
    from unittest.mock import patch
    expense = make_expense(db, user.id, category.id)
    receipt = make_receipt(db, user.id, expense_id=expense.id)

    original_commit = db.commit

    def fail_once():
        db.commit = original_commit
        raise RuntimeError("Simulated DB failure")

    db.commit = fail_once

    with pytest.raises(RuntimeError):
        unlink_receipt_from_expense(db, user.id, expense.id, receipt.id)

    db.expire(receipt)
    db.refresh(receipt)
    assert receipt.expense_id == expense.id


# ═══════════════════════════════════════════════════════════════════════════════
# confirm_user_expense tests
# ═══════════════════════════════════════════════════════════════════════════════

from app.services.expense_service import confirm_user_expense
from app.models.receipt_file import ReceiptFile as ReceiptFileModel


def make_ai_expense(
    db,
    user_id: int,
    category_id: int | None,
    *,
    title: str = "Lunch at Cafe",
    total_amount: Decimal = Decimal("99.00"),
    is_confirmed: bool = False,
    deleted_at=None,
) -> Expense:
    """Insert a minimal AI-extracted draft expense for confirm tests."""
    expense = Expense(
        user_id=user_id,
        category_id=category_id,
        title=title,
        receipt_date=date(2025, 6, 1),
        total_amount=total_amount,
        currency="THB",
        input_method="ai",
        ai_status="completed",
        is_confirmed=is_confirmed,
        deleted_at=deleted_at,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


# ── 1. Successful confirmation ────────────────────────────────────────────────

def test_confirm_returns_expense_response(db, user, category):
    expense = make_ai_expense(db, user.id, category.id)
    result = confirm_user_expense(db, user.id, expense.id)
    assert isinstance(result, ExpenseResponseSchema)


def test_confirm_is_confirmed_becomes_true(db, user, category):
    expense = make_ai_expense(db, user.id, category.id)
    result = confirm_user_expense(db, user.id, expense.id)
    assert result.is_confirmed is True


def test_confirm_is_confirmed_persisted_in_db(db, user, category):
    expense = make_ai_expense(db, user.id, category.id)
    confirm_user_expense(db, user.id, expense.id)
    db.expire(expense)
    db.refresh(expense)
    assert expense.is_confirmed is True


def test_confirm_ai_status_remains_completed(db, user, category):
    expense = make_ai_expense(db, user.id, category.id)
    confirm_user_expense(db, user.id, expense.id)
    db.expire(expense)
    db.refresh(expense)
    assert expense.ai_status == "completed"


def test_confirm_items_remain_unchanged(db, user, category):
    expense = make_ai_expense(db, user.id, category.id)
    make_item(db, expense.id, original_name="Pad Thai")
    result = confirm_user_expense(db, user.id, expense.id)
    assert len(result.items) == 1
    assert result.items[0].original_name == "Pad Thai"


def test_confirm_receipt_link_remains_unchanged(db, user, category):
    expense = make_ai_expense(db, user.id, category.id)
    receipt = ReceiptFileModel(
        user_id=user.id,
        expense_id=expense.id,
        original_filename="r.jpg",
        stored_filename="r.jpg",
        file_path="/uploads/r.jpg",
        file_size=500,
        mime_type="image/jpeg",
    )
    db.add(receipt)
    db.commit()
    db.refresh(receipt)
    confirm_user_expense(db, user.id, expense.id)
    db.expire(receipt)
    db.refresh(receipt)
    assert receipt.expense_id == expense.id


def test_confirm_ownership_does_not_change(db, user, category):
    expense = make_ai_expense(db, user.id, category.id)
    result = confirm_user_expense(db, user.id, expense.id)
    assert result.user_id == user.id


def test_confirm_no_unrelated_fields_change(db, user, category):
    expense = make_ai_expense(db, user.id, category.id, title="Original Title",
                               total_amount=Decimal("55.50"))
    result = confirm_user_expense(db, user.id, expense.id)
    assert result.title == "Original Title"
    assert result.total_amount == Decimal("55.50")
    assert result.category_id == category.id


def test_confirm_internal_fields_not_in_response(db, user, category):
    expense = make_ai_expense(db, user.id, category.id)
    result = confirm_user_expense(db, user.id, expense.id)
    result_dict = result.model_dump()
    for field in ("ai_confidence", "ai_status", "ai_raw_response",
                  "language_detected", "deleted_at"):
        assert field not in result_dict, f"Response must not expose: {field}"


# ── 2. Ownership / not-found errors ──────────────────────────────────────────

def test_confirm_unknown_expense_raises_404(db, user, category):
    with pytest.raises(ExpenseServiceError) as exc_info:
        confirm_user_expense(db, user.id, 999999)
    assert exc_info.value.status_code == 404


def test_confirm_other_users_expense_raises_404(db, category):
    user_a = make_user(db, username="conf_a", email="conf_a@example.com")
    user_b = make_user(db, username="conf_b", email="conf_b@example.com")
    expense = make_ai_expense(db, user_a.id, category.id)
    with pytest.raises(ExpenseServiceError) as exc_info:
        confirm_user_expense(db, user_b.id, expense.id)
    assert exc_info.value.status_code == 404


def test_confirm_soft_deleted_expense_raises_404(db, user, category):
    expense = make_ai_expense(db, user.id, category.id,
                               deleted_at=datetime(2024, 1, 1))
    with pytest.raises(ExpenseServiceError) as exc_info:
        confirm_user_expense(db, user.id, expense.id)
    assert exc_info.value.status_code == 404


# ── 3. AI-only restriction ────────────────────────────────────────────────────

def test_confirm_manual_expense_raises_409(db, user, category):
    expense = make_expense(db, user.id, category.id)  # input_method="manual"
    with pytest.raises(ExpenseServiceError) as exc_info:
        confirm_user_expense(db, user.id, expense.id)
    assert exc_info.value.status_code == 409
    assert "AI-extracted" in exc_info.value.message


# ── 4. Already confirmed ──────────────────────────────────────────────────────

def test_confirm_already_confirmed_raises_409(db, user, category):
    expense = make_ai_expense(db, user.id, category.id, is_confirmed=True)
    with pytest.raises(ExpenseServiceError) as exc_info:
        confirm_user_expense(db, user.id, expense.id)
    assert exc_info.value.status_code == 409
    assert "already confirmed" in exc_info.value.message


def test_confirm_already_confirmed_does_not_write_to_db(db, user, category):
    expense = make_ai_expense(db, user.id, category.id, is_confirmed=True)
    original_updated_at = expense.updated_at
    with pytest.raises(ExpenseServiceError):
        confirm_user_expense(db, user.id, expense.id)
    db.expire(expense)
    db.refresh(expense)
    # updated_at must not have changed
    assert expense.updated_at == original_updated_at


# ── 5. Required-field validation ──────────────────────────────────────────────

def test_confirm_missing_category_raises_422(db, user, category):
    expense = make_ai_expense(db, user.id, category_id=None)
    with pytest.raises(ExpenseServiceError) as exc_info:
        confirm_user_expense(db, user.id, expense.id)
    assert exc_info.value.status_code == 422
    assert "category" in exc_info.value.message.lower()


def test_confirm_invalid_category_raises_422(db, user):
    # "Invalid category" = category exists but is inactive (soft-delete or is_active=False).
    # The inactive variant represents the category becoming invalid after extraction.
    inactive = make_category(db, code="CONF_INVAL", name_en="Invalid",
                              name_th="ไม่ถูกต้อง", is_active=False)
    expense = make_ai_expense(db, user.id, inactive.id)
    with pytest.raises(ExpenseServiceError) as exc_info:
        confirm_user_expense(db, user.id, expense.id)
    assert exc_info.value.status_code == 422


def test_confirm_inactive_category_raises_422(db, user):
    inactive = make_category(db, code="CONF_INACT", name_en="Inactive",
                              name_th="ไม่ใช้งาน", is_active=False)
    expense = make_ai_expense(db, user.id, inactive.id)
    with pytest.raises(ExpenseServiceError) as exc_info:
        confirm_user_expense(db, user.id, expense.id)
    assert exc_info.value.status_code == 422


def test_confirm_soft_deleted_category_raises_422(db, user):
    deleted_cat = make_category(db, code="CONF_DEL", name_en="Deleted",
                                 name_th="ลบแล้ว", deleted_at=datetime(2024, 1, 1))
    expense = make_ai_expense(db, user.id, deleted_cat.id)
    with pytest.raises(ExpenseServiceError) as exc_info:
        confirm_user_expense(db, user.id, expense.id)
    assert exc_info.value.status_code == 422


def test_confirm_blank_title_raises_422(db, user, category):
    expense = make_ai_expense(db, user.id, category.id, title="   ")
    with pytest.raises(ExpenseServiceError) as exc_info:
        confirm_user_expense(db, user.id, expense.id)
    assert exc_info.value.status_code == 422
    assert "title" in exc_info.value.message.lower()


def test_confirm_negative_total_raises_422(db, user, category):
    expense = make_ai_expense(db, user.id, category.id,
                               total_amount=Decimal("-1.00"))
    with pytest.raises(ExpenseServiceError) as exc_info:
        confirm_user_expense(db, user.id, expense.id)
    assert exc_info.value.status_code == 422
    assert "total amount" in exc_info.value.message.lower()


def test_confirm_zero_total_is_accepted(db, user, category):
    expense = make_ai_expense(db, user.id, category.id,
                               total_amount=Decimal("0.00"))
    result = confirm_user_expense(db, user.id, expense.id)
    assert result.is_confirmed is True
    assert result.total_amount == Decimal("0.00")


# ── 6. Validation does not leave side effects ────────────────────────────────

def test_failed_validation_does_not_confirm(db, user):
    expense = make_ai_expense(db, user.id, category_id=None)  # will fail at category
    with pytest.raises(ExpenseServiceError):
        confirm_user_expense(db, user.id, expense.id)
    db.expire(expense)
    db.refresh(expense)
    assert expense.is_confirmed is False


# ── 7. DB failure rolls back ──────────────────────────────────────────────────

def test_confirm_db_failure_rolls_back(db, user, category):
    expense = make_ai_expense(db, user.id, category.id)
    original_commit = db.commit

    def fail_once():
        db.commit = original_commit
        raise RuntimeError("Simulated DB failure")

    db.commit = fail_once

    with pytest.raises(RuntimeError):
        confirm_user_expense(db, user.id, expense.id)

    db.expire(expense)
    db.refresh(expense)
    assert expense.is_confirmed is False
