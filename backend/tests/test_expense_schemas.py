"""Schema-only tests for Expense — no database connection required."""

from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas.expense import ExpenseCreate, ExpenseUpdate, ExpenseResponse
from app.schemas.expense_item import ExpenseItemCreate, ExpenseItemResponse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_create(**overrides) -> dict:
    base = dict(
        category_id=1,
        title="Lunch",
        receipt_date=date(2024, 6, 1),
        currency="THB",
        total_amount=Decimal("150.00"),
    )
    base.update(overrides)
    return base


def _make_expense_obj(**overrides):
    now = datetime(2024, 6, 1, 12, 0, 0)
    defaults = dict(
        id=1,
        user_id=5,
        category_id=1,
        title="Lunch",
        merchant_name="Noodle Shop",
        receipt_number=None,
        receipt_date=date(2024, 6, 1),
        payment_method=None,
        currency="THB",
        subtotal=Decimal("140.00"),
        tax_amount=Decimal("10.00"),
        discount_amount=Decimal("0"),
        total_amount=Decimal("150.00"),
        notes=None,
        is_confirmed=False,
        created_at=now,
        updated_at=now,
        deleted_at=now,  # should be excluded from response
        expense_items=[],
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


# ---------------------------------------------------------------------------
# ExpenseCreate
# ---------------------------------------------------------------------------

def test_valid_expense_creation():
    exp = ExpenseCreate(**_valid_create())
    assert exp.category_id == 1
    assert exp.currency == "THB"
    assert exp.items == []


def test_positive_category_id_required():
    with pytest.raises(ValidationError):
        ExpenseCreate(**_valid_create(category_id=0))

    with pytest.raises(ValidationError):
        ExpenseCreate(**_valid_create(category_id=-1))


def test_negative_subtotal_rejected():
    with pytest.raises(ValidationError):
        ExpenseCreate(**_valid_create(subtotal=Decimal("-1")))


def test_negative_tax_amount_rejected():
    with pytest.raises(ValidationError):
        ExpenseCreate(**_valid_create(tax_amount=Decimal("-0.01")))


def test_negative_total_amount_rejected():
    with pytest.raises(ValidationError):
        ExpenseCreate(**_valid_create(total_amount=Decimal("-10")))


def test_valid_three_letter_currency_accepted():
    exp = ExpenseCreate(**_valid_create(currency="USD"))
    assert exp.currency == "USD"


def test_lowercase_currency_normalized_to_uppercase():
    exp = ExpenseCreate(**_valid_create(currency="thb"))
    assert exp.currency == "THB"


def test_invalid_currency_length_rejected():
    with pytest.raises(ValidationError):
        ExpenseCreate(**_valid_create(currency="TH"))

    with pytest.raises(ValidationError):
        ExpenseCreate(**_valid_create(currency="USDD"))


def test_non_alphabetic_currency_rejected():
    with pytest.raises(ValidationError):
        ExpenseCreate(**_valid_create(currency="T2B"))

    with pytest.raises(ValidationError):
        ExpenseCreate(**_valid_create(currency="123"))


def test_whitespace_only_merchant_name_rejected():
    with pytest.raises(ValidationError):
        ExpenseCreate(**_valid_create(merchant_name="   "))


def test_no_items_defaults_to_empty_list():
    exp = ExpenseCreate(**_valid_create())
    assert exp.items == []


def test_valid_nested_items_accepted():
    items = [
        ExpenseItemCreate(original_name="Rice", quantity=Decimal("1"), total_price=Decimal("50")),
        ExpenseItemCreate(original_name="Water", quantity=Decimal("2"), total_price=Decimal("20")),
    ]
    exp = ExpenseCreate(**_valid_create(items=items))
    assert len(exp.items) == 2
    assert exp.items[0].original_name == "Rice"


def test_invalid_nested_item_rejected():
    bad_item = dict(original_name="", quantity=Decimal("1"), total_price=Decimal("10"))
    with pytest.raises(ValidationError):
        ExpenseCreate(**_valid_create(items=[bad_item]))


# ---------------------------------------------------------------------------
# ExpenseUpdate
# ---------------------------------------------------------------------------

def test_valid_partial_update():
    upd = ExpenseUpdate(total_amount=Decimal("200"))
    assert upd.total_amount == Decimal("200")
    assert upd.currency is None


def test_empty_update_accepted():
    upd = ExpenseUpdate()
    assert upd.category_id is None
    assert upd.total_amount is None


def test_update_currency_normalized():
    upd = ExpenseUpdate(currency="usd")
    assert upd.currency == "USD"


def test_update_invalid_currency_rejected():
    with pytest.raises(ValidationError):
        ExpenseUpdate(currency="12")


# ---------------------------------------------------------------------------
# ExpenseResponse
# ---------------------------------------------------------------------------

def test_response_loads_from_orm_like_object():
    obj = _make_expense_obj()
    resp = ExpenseResponse.model_validate(obj)
    assert resp.id == 1
    assert resp.user_id == 5
    assert resp.total_amount == Decimal("150.00")
    assert resp.currency == "THB"
    assert resp.items == []


def test_response_does_not_expose_deleted_at():
    obj = _make_expense_obj()
    resp = ExpenseResponse.model_validate(obj)
    assert not hasattr(resp, "deleted_at")
