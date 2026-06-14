"""make_expenses_category_id_nullable

Allow expenses.category_id to be NULL so that AI-extracted expenses
can be saved even when no category name matches an active category.

Revision ID: a1b2c3d4e5f6
Revises: cbb57baabb25
Create Date: 2026-06-14 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'cbb57baabb25'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Change expenses.category_id from NOT NULL to NULL.

    The column type, foreign key, and index are preserved exactly.
    Safe to run even if the column is already nullable (MySQL MODIFY
    is idempotent for this change).
    """
    op.alter_column(
        'expenses',
        'category_id',
        existing_type=mysql.INTEGER(unsigned=True),
        nullable=True,
        existing_nullable=False,
    )


def downgrade() -> None:
    """Change expenses.category_id back from NULL to NOT NULL.

    Before making the column NOT NULL again, we must ensure no rows
    have category_id = NULL.  We look for an active 'Other' category
    (code = 'other') and use it as the fallback.

    If no valid fallback category exists, we raise an error rather than
    silently assigning an unrelated category or leaving the migration
    in a broken state.
    """
    # Get a connection from Alembic's current migration context.
    connection = op.get_bind()

    # Look for the 'Other' category — active and not soft-deleted.
    result = connection.execute(
        sa.text(
            "SELECT id FROM categories "
            "WHERE code = 'other' "
            "AND is_active = 1 "
            "AND deleted_at IS NULL "
            "LIMIT 1"
        )
    )
    row = result.fetchone()

    # Count how many expenses currently have no category.
    null_count_result = connection.execute(
        sa.text("SELECT COUNT(*) FROM expenses WHERE category_id IS NULL")
    )
    null_count = null_count_result.scalar()

    if null_count > 0:
        # We have rows to fix — we need a valid fallback category.
        if row is None:
            raise RuntimeError(
                "Downgrade aborted: expenses.category_id has "
                f"{null_count} NULL row(s), but no active 'Other' "
                "category (code='other') exists to use as a fallback. "
                "Either seed the 'Other' category first or manually "
                "assign a category to those expenses before downgrading."
            )

        fallback_id = row[0]
        # Assign the fallback category to every uncategorised expense.
        connection.execute(
            sa.text(
                "UPDATE expenses "
                "SET category_id = :fallback_id "
                "WHERE category_id IS NULL"
            ),
            {"fallback_id": fallback_id},
        )

    # Now it is safe to make the column NOT NULL again.
    op.alter_column(
        'expenses',
        'category_id',
        existing_type=mysql.INTEGER(unsigned=True),
        nullable=False,
        existing_nullable=True,
    )
