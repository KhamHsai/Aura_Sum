"""Schema-only tests for ExpenseItem — no database connection required."""

from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas.expense_item import ExpenseItemCreate, ExpenseItemUpdate, ExpenseItemResponse


# ---------------------------------------------------------------------------
# ExpenseItemCreate
# ---------------------------------------------------------------------------

def test_valid_item_creation():
    item = ExpenseItemCreate(
        original_name="Coffee",
        quantity=Decimal("2"),
        total_price=Decimal("150.00"),
    )
    assert item.original_name == "Coffee"
    assert item.quantity == Decimal("2")
    assert item.total_price == Decimal("150.00")
    assert item.discount_amount == Decimal("0")


def test_empty_name_rejected():
    with pytest.raises(ValidationError):
        ExpenseItemCreate(original_name="", quantity=Decimal("1"), total_price=Decimal("10"))


def test_whitespace_only_name_rejected():
    with pytest.raises(ValidationError):
        ExpenseItemCreate(original_name="   ", quantity=Decimal("1"), total_price=Decimal("10"))


def test_name_is_stripped():
    item = ExpenseItemCreate(original_name="  Cake  ", quantity=Decimal("1"), total_price=Decimal("50"))
    assert item.original_name == "Cake"


def test_quantity_zero_rejected():
    with pytest.raises(ValidationError):
        ExpenseItemCreate(original_name="Tea", quantity=Decimal("0"), total_price=Decimal("10"))


def test_negative_quantity_rejected():
    with pytest.raises(ValidationError):
        ExpenseItemCreate(original_name="Tea", quantity=Decimal("-1"), total_price=Decimal("10"))


def test_negative_unit_price_rejected():
    with pytest.raises(ValidationError):
        ExpenseItemCreate(
            original_name="Tea",
            quantity=Decimal("1"),
            unit_price=Decimal("-5"),
            total_price=Decimal("10"),
        )


def test_negative_total_price_rejected():
    with pytest.raises(ValidationError):
        ExpenseItemCreate(original_name="Tea", quantity=Decimal("1"), total_price=Decimal("-1"))


def test_zero_unit_price_accepted():
    item = ExpenseItemCreate(
        original_name="Promo item",
        quantity=Decimal("1"),
        unit_price=Decimal("0"),
        total_price=Decimal("0"),
    )
    assert item.unit_price == Decimal("0")


# ---------------------------------------------------------------------------
# ExpenseItemUpdate
# ---------------------------------------------------------------------------

def test_valid_partial_update():
    upd = ExpenseItemUpdate(quantity=Decimal("3"))
    assert upd.quantity == Decimal("3")
    assert upd.original_name is None


def test_empty_update_accepted():
    upd = ExpenseItemUpdate()
    assert upd.original_name is None
    assert upd.quantity is None
    assert upd.total_price is None


def test_update_whitespace_name_rejected():
    with pytest.raises(ValidationError):
        ExpenseItemUpdate(original_name="   ")


# ---------------------------------------------------------------------------
# ExpenseItemResponse
# ---------------------------------------------------------------------------

def _make_item_obj(**overrides):
    now = datetime(2024, 6, 1, 12, 0, 0)
    defaults = dict(
        id=1,
        expense_id=10,
        category_id=None,
        original_name="Pad Thai",
        name_en="Pad Thai",
        name_th=None,
        quantity=Decimal("1"),
        unit=None,
        unit_price=Decimal("80.00"),
        discount_amount=Decimal("0"),
        total_price=Decimal("80.00"),
        created_at=now,
        updated_at=now,
        deleted_at=now,  # should be excluded from response
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_response_loads_from_orm_like_object():
    obj = _make_item_obj()
    resp = ExpenseItemResponse.model_validate(obj)
    assert resp.id == 1
    assert resp.original_name == "Pad Thai"
    assert resp.total_price == Decimal("80.00")


def test_response_does_not_expose_deleted_at():
    obj = _make_item_obj()
    resp = ExpenseItemResponse.model_validate(obj)
    assert not hasattr(resp, "deleted_at")
