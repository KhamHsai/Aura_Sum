from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Absolute path to the backend/ directory (the folder that contains this file's parent)
_BASE_DIR: Path = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    APP_NAME: str = "Smart Receipt API"
    APP_ENV: str = "development"
    DATABASE_URL: str = "mysql+pymysql://username:password@localhost:3306/smart_receipt_db"
    TEST_DATABASE_URL: str = "mysql+pymysql://username:password@localhost:3306/smart_receipt_db_test"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "google/gemini-2.0-flash-exp:free"
    UPLOAD_DIRECTORY: str = "uploads/receipts"
    UPLOAD_DIR: str = "uploads/receipts"
    MAX_RECEIPT_FILE_SIZE_MB: int = 10
    FRONTEND_URL: str = ""

    # JWT configurations (JWT_SECRET_KEY has no default and must be provided in the environment)
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = SettingsConfigDict(
        env_file=str(_BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def upload_dir_absolute(self) -> Path:
        """Always return an absolute path for the upload directory.

        If UPLOAD_DIR is already absolute (starts with /), use it as-is.
        Otherwise resolve it relative to the backend/ root so the path is
        correct regardless of which directory uvicorn is launched from.
        """
        p = Path(self.UPLOAD_DIR)
        if p.is_absolute():
            return p
        return (_BASE_DIR / p).resolve()


settings = Settings()
