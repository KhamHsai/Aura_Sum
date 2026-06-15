"""Pydantic schemas for on-demand expense translation.

Only dynamic user data is translated here — expense titles, notes, and item names.
Fixed frontend labels (Dashboard, Save, Delete, etc.) are not handled by this endpoint.
"""

from typing import Literal

from pydantic import BaseModel, field_validator


class ExpenseTranslationRequest(BaseModel):
    """Request body for POST /api/expenses/{expense_id}/translate."""

    target_language: Literal["en", "th"]

    @field_validator("target_language", mode="before")
    @classmethod
    def normalise_language(cls, v: object) -> str:
        """Accept 'EN' and 'TH' in addition to lowercase."""
        if isinstance(v, str):
            return v.strip().lower()
        return v  # let Literal validation fail with a clear message


class TranslatedExpenseItem(BaseModel):
    """One translated item in the translation response."""

    item_id: int
    original_name: str | None = None
    name_en: str | None = None
    name_th: str | None = None
    translated_name: str | None = None


class ExpenseTranslationResponse(BaseModel):
    """Response body for POST /api/expenses/{expense_id}/translate."""

    expense_id: int
    source_language: Literal["en", "th"]
    target_language: Literal["en", "th"]
    translated_notes: str | None = None
    items: list[TranslatedExpenseItem] = []
    reused_existing_translation: bool = False


# ── Internal schemas for AI translation output ───────────────────────────

class GeminiTranslatedItem(BaseModel):
    """One item as returned by the AI in the translation response."""

    item_id: int
    translated_name: str | None = None


class GeminiTranslationResult(BaseModel):
    """Full AI translation output — validated before any database write.

    item_ids_expected must be supplied by the caller so the validator can
    confirm no extra or missing IDs are present.
    """

    translated_notes: str | None = None
    items: list[GeminiTranslatedItem] = []

    def validate_item_ids(self, expected_ids: list[int]) -> None:
        """Raise ValueError when returned item IDs do not match expected IDs exactly."""
        returned_ids = [item.item_id for item in self.items]
        extra = set(returned_ids) - set(expected_ids)
        if extra:
            raise ValueError(f"AI returned unexpected item IDs: {extra}")
        missing = set(expected_ids) - set(returned_ids)
        if missing:
            raise ValueError(f"AI did not return translations for item IDs: {missing}")
