import sys
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from app.config import settings

def create_database():
    try:
        url = make_url(settings.DATABASE_URL)
        db_name = url.database
        if not db_name:
            print("Error: Database name not specified in DATABASE_URL")
            sys.exit(1)

        server_url = url.set(database="")
        engine = create_engine(server_url)
        with engine.connect() as conn:
            # Execute database creation in autocommit mode
            conn = conn.execution_options(isolation_level="AUTOCOMMIT")
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
            print(f"Database '{db_name}' created or already exists.")
    except Exception as e:
        print(f"Error creating database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    create_database()
