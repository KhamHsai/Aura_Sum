"""Protected routes for expense management."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.expense import ExpenseCreate, ExpenseResponse, ExpenseUpdate
from app.schemas.receipt import ReceiptFileResponse
from app.schemas.translation import ExpenseTranslationRequest, ExpenseTranslationResponse
from app.services.expense_service import (
    ExpenseServiceError,
    create_expense,
    confirm_user_expense,
    delete_user_expense,
    get_user_expense_by_id,
    get_user_expenses,
    link_receipt_to_expense,
    unlink_receipt_from_expense,
    update_user_expense,
)
from app.services.translation_service import TranslationServiceError, translate_expense

router = APIRouter(
    prefix="/api/expenses",
    tags=["Expenses"],
)


@router.post(
    "",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Expense",
)
def create_expense_route(
    data: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExpenseResponse:
    """Create a new expense with optional line items for the authenticated user."""
    try:
        return create_expense(db, current_user.id, data)
    except ExpenseServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


@router.get(
    "",
    response_model=list[ExpenseResponse],
    status_code=status.HTTP_200_OK,
    summary="List My Expenses",
)
def list_expenses_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ExpenseResponse]:
    """Return all non-deleted expenses belonging to the authenticated user, newest first."""
    return get_user_expenses(db, current_user.id)


@router.get(
    "/{expense_id}",
    response_model=ExpenseResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Expense Details",
)
def get_expense_route(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExpenseResponse:
    """Return one owned, non-deleted expense with its items. Returns 404 for missing, soft-deleted, or another user's expense."""
    expense = get_user_expense_by_id(db, current_user.id, expense_id)
    if expense is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    return expense


@router.put(
    "/{expense_id}",
    response_model=ExpenseResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Expense",
)
def update_expense_route(
    expense_id: int,
    data: ExpenseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExpenseResponse:
    """Partially update an owned, non-deleted expense. Items are replaced only when provided."""
    try:
        result = update_user_expense(db, current_user.id, expense_id, data)
    except ExpenseServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    return result


@router.delete(
    "/{expense_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Expense",
)
def delete_expense_route(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Soft-delete an owned expense and its active items. Returns 404 for missing or another user's expense."""
    deleted = delete_user_expense(db, current_user.id, expense_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    return {"message": "Expense deleted successfully"}


@router.post(
    "/{expense_id}/confirm",
    response_model=ExpenseResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm Expense",
)
def confirm_expense_route(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExpenseResponse:
    """Confirm an AI-extracted draft expense after the user has reviewed it."""
    try:
        return confirm_user_expense(db, current_user.id, expense_id)
    except ExpenseServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


@router.post(
    "/{expense_id}/receipts/{receipt_id}",
    response_model=ReceiptFileResponse,
    status_code=status.HTTP_200_OK,
    summary="Link Receipt to Expense",
)
def link_receipt_route(
    expense_id: int,
    receipt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReceiptFileResponse:
    """Link an owned receipt file to an owned expense."""
    try:
        receipt = link_receipt_to_expense(db, current_user.id, expense_id, receipt_id)
        return ReceiptFileResponse.model_validate(receipt)
    except ExpenseServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


@router.post(
    "/{expense_id}/translate",
    response_model=ExpenseTranslationResponse,
    status_code=status.HTTP_200_OK,
    summary="Translate Expense",
)
def translate_expense_route(
    expense_id: int,
    data: ExpenseTranslationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExpenseTranslationResponse:
    """Translate dynamic expense text (title, notes, item names) between English and Thai.

    Only live user data is translated. Fixed frontend labels are not handled here.
    Existing saved translations are reused to avoid unnecessary Gemini calls.
    """
    try:
        return translate_expense(db, current_user.id, expense_id, data.target_language)
    except TranslationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


@router.delete(
    "/{expense_id}/receipts/{receipt_id}",
    response_model=ReceiptFileResponse,
    status_code=status.HTTP_200_OK,
    summary="Unlink Receipt from Expense",
)
def unlink_receipt_route(
    expense_id: int,
    receipt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReceiptFileResponse:
    """Remove the link between an owned receipt file and an owned expense."""
    try:
        receipt = unlink_receipt_from_expense(db, current_user.id, expense_id, receipt_id)
        return ReceiptFileResponse.model_validate(receipt)
    except ExpenseServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
