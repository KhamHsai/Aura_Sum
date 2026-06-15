"""On-demand translation service for dynamic expense data.

Translates expense titles, notes, and item names between English and Thai.
Does NOT translate fixed frontend labels (Dashboard, Save, Delete, etc.).

Public API
----------
    translate_expense(db, user_id, expense_id, target_language) -> ExpenseTranslationResponse
    TranslationServiceError
"""

import json
import re

from pydantic import ValidationError
from sqlalchemy.orm import Session

from openai import OpenAI

from app.config import settings
from app.models.expense import Expense
from app.models.expense_item import ExpenseItem
from app.models.translation import Translation
from app.schemas.translation import (
    ExpenseTranslationRequest,
    ExpenseTranslationResponse,
    GeminiTranslatedItem,
    GeminiTranslationResult,
    TranslatedExpenseItem,
)


class TranslationServiceError(Exception):
    """Raised when translation cannot complete.

    status_code mirrors HTTP conventions so the route can forward it directly.
    """

    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


# ── Gemini client ──────────────────────────────────────────────────────────────

def _build_translation_client() -> OpenAI:
    """Build an OpenRouter client for translation.

    Keeps the same function name so tests can patch it independently.
    Raises TranslationServiceError when the API key is missing.
    """
    api_key = settings.OPENROUTER_API_KEY
    if not api_key:
        raise TranslationServiceError(
            "OpenRouter API key is not configured", status_code=503
        )
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )


# ── Gemini translation call ────────────────────────────────────────────────────

def _clean_json(text: str) -> str:
    """Strip whitespace and remove a single ```json … ``` fence if present."""
    text = text.strip()
    fenced = re.match(r"^```(?:json)?\s*([\s\S]*?)```$", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    return text


def translate_expense_text(
    source_language: str,
    target_language: str,
    title: str | None,
    notes: str | None,
    items: list[dict],
) -> GeminiTranslationResult:
    """Call Gemini to translate expense title, notes, and item names.

    Parameters
    ----------
    source_language : "en" or "th"
    target_language : "en" or "th"
    title           : expense title to translate, or None
    notes           : expense notes to translate, or None
    items           : list of dicts with keys item_id and source_name

    Returns
    -------
    GeminiTranslationResult — validated Pydantic object.

    Raises
    ------
    TranslationServiceError on any Gemini or validation failure.
    """
    client = _build_translation_client()

    lang_names = {"en": "English", "th": "Thai"}
    source_name = lang_names[source_language]
    target_name = lang_names[target_language]

    # Build the items list for the prompt — only item_id and source_name
    prompt_items = [
        {"item_id": item["item_id"], "source_name": item["source_name"]}
        for item in items
    ]

    prompt = f"""Translate the following expense data from {source_name} to {target_name}.

Rules:
- Translate only the provided text fields.
- Source language is {source_name}. Target language is {target_name}.
- Return JSON only. Do not include Markdown. Do not include code fences.
- Preserve meaning exactly. Do not add or remove information.
- Do not change numbers, currency codes, dates, IDs, or receipt codes.
- Use null when the source text is null.
- Keep the items array in the same order with the same item_id values.
- Return null for translated_name when source_name is null.

Input:
{{
  "title": {json.dumps(title)},
  "notes": {json.dumps(notes)},
  "items": {json.dumps(prompt_items)}
}}

Return exactly this JSON structure:
{{
  "translated_title": null,
  "translated_notes": null,
  "items": [
    {{
      "item_id": 1,
      "translated_name": null
    }}
  ]
}}"""

    try:
        response = client.chat.completions.create(
            model=settings.OPENROUTER_MODEL,
            messages=[
                {"role": "user", "content": prompt}
            ],
        )
    except TranslationServiceError:
        raise
    except Exception as exc:
        raise TranslationServiceError("AI translation failed", status_code=502) from exc

    response_text = response.choices[0].message.content if response.choices else None
    if not response_text or not response_text.strip():
        raise TranslationServiceError(
            "Gemini returned an empty response", status_code=502
        )

    cleaned = _clean_json(response_text)

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise TranslationServiceError(
            "Gemini returned invalid JSON", status_code=502
        ) from exc

    try:
        result = GeminiTranslationResult.model_validate(payload)
    except ValidationError as exc:
        raise TranslationServiceError(
            "Gemini translation validation failed", status_code=502
        ) from exc

    # Validate item IDs match exactly
    expected_ids = [item["item_id"] for item in items]
    try:
        result.validate_item_ids(expected_ids)
    except ValueError as exc:
        raise TranslationServiceError(
            f"Gemini translation validation failed: {exc}", status_code=502
        ) from exc

    return result


# ── Reuse helpers ──────────────────────────────────────────────────────────────

def _find_saved_translation(
    db: Session,
    source_text: str,
    source_language: str,
    target_language: str,
) -> str | None:
    """Look up a previously saved translation by source text and language pair.

    The Translation table does not have expense_id or field_name columns,
    so we use (source_text, source_language, target_language) as the lookup key.
    Returns the translated_text string, or None if not found.
    """
    row = (
        db.query(Translation)
        .filter(
            Translation.source_text == source_text,
            Translation.source_language == source_language,
            Translation.target_language == target_language,
            Translation.deleted_at.is_(None),
        )
        .first()
    )
    return row.translated_text if row else None


def _save_translation(
    db: Session,
    source_text: str,
    source_language: str,
    target_language: str,
    translated_text: str,
    expense_item_id: int | None = None,
) -> None:
    """Save or update a translation record.

    Uses (source_text, source_language, target_language) as uniqueness key.
    Updates translated_text in place if the record already exists.
    Does NOT commit — the caller is responsible for committing once at the end.
    """
    existing = (
        db.query(Translation)
        .filter(
            Translation.source_text == source_text,
            Translation.source_language == source_language,
            Translation.target_language == target_language,
            Translation.deleted_at.is_(None),
        )
        .first()
    )
    if existing:
        existing.translated_text = translated_text
    else:
        row = Translation(
            expense_item_id=expense_item_id,
            source_text=source_text,
            source_language=source_language,
            target_language=target_language,
            translated_text=translated_text,
            translation_source="gemini",
        )
        db.add(row)


# ── Source language helpers ────────────────────────────────────────────────────

def _resolve_source_language(expense: Expense, target_language: str) -> str:
    """Determine the source language from the expense, with a simple fallback.

    If language_detected is set and is 'en' or 'th', use it.
    Otherwise infer from the target: target th → source en, target en → source th.
    """
    detected = expense.language_detected
    if detected in ("en", "th"):
        return detected
    # Simple fallback: assume opposite of target
    return "en" if target_language == "th" else "th"


def _best_source_text_for_item(
    item: ExpenseItem, target_language: str
) -> str | None:
    """Pick the best source text for an item name given the translation direction.

    For target English: prefer name_th, then original_name, then name_en.
    For target Thai:    prefer name_en, then original_name, then name_th.
    """
    if target_language == "en":
        return item.name_th or item.original_name or item.name_en
    else:
        return item.name_en or item.original_name or item.name_th


# ── Main service function ──────────────────────────────────────────────────────

def translate_expense(
    db: Session,
    user_id: int,
    expense_id: int,
    target_language: str,
) -> ExpenseTranslationResponse:
    """Translate dynamic text fields of one owned expense on demand.

    Steps:
    1. Load expense (ownership + soft-delete check).
    2. Validate target language.
    3. Resolve source language; if same as target, return existing text.
    4. Load active items.
    5. Check existing saved translations (reuse when available).
    6. Call Gemini only for fields that still need translation.
    7. Save new translations + update item name columns in one transaction.
    8. Return ExpenseTranslationResponse.

    Raises TranslationServiceError for 404, 422, and 502 conditions.
    Does NOT raise HTTPException — that is the route's responsibility.
    """
    if target_language not in ("en", "th"):
        raise TranslationServiceError(
            "Unsupported target language. Use 'en' or 'th'.", status_code=422
        )

    # 1. Load the expense with ownership check
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
        raise TranslationServiceError("Expense not found", status_code=404)

    # 3. Resolve source language
    source_language = _resolve_source_language(expense, target_language)
    if source_language not in ("en", "th"):
        raise TranslationServiceError(
            "Expense language is unsupported for translation", status_code=422
        )

    # 4. Load active items
    active_items = (
        db.query(ExpenseItem)
        .filter(
            ExpenseItem.expense_id == expense_id,
            ExpenseItem.deleted_at.is_(None),
        )
        .order_by(ExpenseItem.id.asc())
        .all()
    )

    # 5a. Check existing title/notes translations
    translated_title: str | None = None
    translated_notes: str | None = None
    needs_title = False
    needs_notes = False

    if source_language == target_language:
        # Nothing to translate — return existing text as-is
        translated_title = expense.title
        translated_notes = expense.notes
    else:
        if expense.title:
            saved = _find_saved_translation(
                db, expense.title, source_language, target_language
            )
            if saved is not None:
                translated_title = saved
            else:
                needs_title = True
        if expense.notes:
            saved = _find_saved_translation(
                db, expense.notes, source_language, target_language
            )
            if saved is not None:
                translated_notes = saved
            else:
                needs_notes = True

    # 5b. Check existing item translations
    item_results: list[dict] = []
    items_needing_translation: list[dict] = []

    for item in active_items:
        already_translated: str | None = None

        if source_language == target_language:
            # No translation needed — use the existing target field
            already_translated = item.name_en if target_language == "en" else item.name_th
        else:
            if target_language == "en" and item.name_en:
                already_translated = item.name_en
            elif target_language == "th" and item.name_th:
                already_translated = item.name_th
            else:
                source_text = _best_source_text_for_item(item, target_language)
                if source_text:
                    saved = _find_saved_translation(
                        db, source_text, source_language, target_language
                    )
                    if saved is not None:
                        already_translated = saved
                else:
                    # No source text available — nothing to translate
                    already_translated = None

        item_results.append({
            "item": item,
            "translated_name": already_translated,
            "needs_translation": already_translated is None and source_language != target_language,
        })

        if already_translated is None and source_language != target_language:
            source_text = _best_source_text_for_item(item, target_language)
            items_needing_translation.append({
                "item_id": item.id,
                "source_name": source_text,
            })

    # Determine whether everything was already available
    gemini_needed = (
        needs_title
        or needs_notes
        or bool(items_needing_translation)
    ) and source_language != target_language

    reused_existing = not gemini_needed

    # 6. Call Gemini only when something is missing
    gemini_result: GeminiTranslationResult | None = None
    if gemini_needed:
        gemini_result = translate_expense_text(
            source_language=source_language,
            target_language=target_language,
            title=expense.title if needs_title else None,
            notes=expense.notes if needs_notes else None,
            items=items_needing_translation,
        )
        # Fill in translated title / notes from Gemini
        if needs_title:
            translated_title = gemini_result.translated_title
        if needs_notes:
            translated_notes = gemini_result.translated_notes

        # Map Gemini item results by item_id
        gemini_by_id: dict[int, GeminiTranslatedItem] = {
            g.item_id: g for g in gemini_result.items
        }
        for entry in item_results:
            if entry["needs_translation"]:
                item = entry["item"]
                g_item = gemini_by_id.get(item.id)
                if g_item:
                    entry["translated_name"] = g_item.translated_name

    # 7. Save results in one transaction
    try:
        if gemini_needed and gemini_result is not None:
            # Save title translation
            if needs_title and expense.title and translated_title is not None:
                _save_translation(
                    db,
                    expense.title,
                    source_language,
                    target_language,
                    translated_title,
                )

            # Save notes translation
            if needs_notes and expense.notes and translated_notes is not None:
                _save_translation(
                    db,
                    expense.notes,
                    source_language,
                    target_language,
                    translated_notes,
                )

            # Save item translations and update item name columns
            for entry in item_results:
                if entry["needs_translation"] and entry["translated_name"] is not None:
                    item = entry["item"]
                    source_text = _best_source_text_for_item(item, target_language)
                    if source_text:
                        _save_translation(
                            db,
                            source_text,
                            source_language,
                            target_language,
                            entry["translated_name"],
                            expense_item_id=item.id,
                        )
                    # Update the item's name column directly
                    if target_language == "en":
                        item.name_en = entry["translated_name"]
                    else:
                        item.name_th = entry["translated_name"]

        db.commit()

    except TranslationServiceError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    # 8. Build response
    translated_items = []
    for entry in item_results:
        item = entry["item"]
        # Refresh to pick up any name column updates
        db.refresh(item)
        translated_items.append(
            TranslatedExpenseItem(
                item_id=item.id,
                original_name=item.original_name,
                name_en=item.name_en,
                name_th=item.name_th,
                translated_name=entry["translated_name"],
            )
        )

    return ExpenseTranslationResponse(
        expense_id=expense.id,
        source_language=source_language,
        target_language=target_language,
        translated_title=translated_title,
        translated_notes=translated_notes,
        items=translated_items,
        reused_existing_translation=reused_existing,
    )
