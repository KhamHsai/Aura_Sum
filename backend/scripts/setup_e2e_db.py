"""
Setup script for the E2E test database.

Usage:
    python scripts/setup_e2e_db.py

This script:
1. Checks that the database name ends with _e2e or _test (safety guard).
2. Clears E2E test users and their owned data (cascades via FK constraints).
3. Reports readiness.

The script does NOT run Alembic migrations — run:
    alembic upgrade head
separately with E2E_DATABASE_URL set.

Environment variable: E2E_DATABASE_URL
Example:
    E2E_DATABASE_URL=mysql+pymysql://root:@localhost:3306/smart_receipt_db_e2e
    python scripts/setup_e2e_db.py
"""

import os
import sys

# ── Safety guard ──────────────────────────────────────────────────────────────

def get_and_validate_db_url() -> str:
    url = os.environ.get("E2E_DATABASE_URL", "")
    if not url:
        print("ERROR: E2E_DATABASE_URL environment variable is not set.")
        print("Set it to a database whose name ends with '_e2e' or '_test'.")
        sys.exit(1)

    # Extract the database name from the URL
    # Expected format: dialect://user:pass@host:port/dbname
    db_name = url.rsplit("/", 1)[-1].split("?")[0]

    if not (db_name.endswith("_e2e") or db_name.endswith("_test")):
        print(f"SAFETY CHECK FAILED: Database '{db_name}' does not end with '_e2e' or '_test'.")
        print("Refusing to clean up a non-test database.")
        sys.exit(2)

    print(f"Safety check passed — database: '{db_name}'")
    return url


def clear_e2e_test_data(url: str) -> None:
    """Delete all rows created by E2E test users (email contains 'e2e-user-')."""
    from sqlalchemy import create_engine, text

    engine = create_engine(url)
    with engine.begin() as conn:
        # Find E2E user IDs
        result = conn.execute(
            text("SELECT id FROM users WHERE email LIKE 'e2e-user-%@example.com'")
        )
        user_ids = [row[0] for row in result]

        if not user_ids:
            print("No E2E test users found — database is already clean.")
            return

        print(f"Cleaning up {len(user_ids)} E2E test user(s): {user_ids}")

        ids_placeholder = ", ".join(str(uid) for uid in user_ids)

        # Delete in dependency order to respect FK constraints
        # (Alembic migrations should have set up ON DELETE CASCADE,
        #  but we do it explicitly here to be safe)
        conn.execute(text(f"DELETE FROM translations WHERE expense_id IN (SELECT id FROM expenses WHERE user_id IN ({ids_placeholder}))"))
        conn.execute(text(f"DELETE FROM expense_items WHERE expense_id IN (SELECT id FROM expenses WHERE user_id IN ({ids_placeholder}))"))
        conn.execute(text(f"DELETE FROM receipt_files WHERE user_id IN ({ids_placeholder})"))
        conn.execute(text(f"DELETE FROM expenses WHERE user_id IN ({ids_placeholder})"))
        conn.execute(text(f"DELETE FROM refresh_tokens WHERE user_id IN ({ids_placeholder})"))
        conn.execute(text(f"DELETE FROM users WHERE id IN ({ids_placeholder})"))

        print("E2E test data cleared successfully.")


if __name__ == "__main__":
    db_url = get_and_validate_db_url()
    clear_e2e_test_data(db_url)
    print("E2E database is ready.")
