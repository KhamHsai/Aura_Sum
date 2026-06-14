from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "Smart Receipt API"
    APP_ENV: str = "development"
    DATABASE_URL: str = "mysql+pymysql://username:password@localhost:3306/smart_receipt_db"
    TEST_DATABASE_URL: str = "mysql+pymysql://username:password@localhost:3306/smart_receipt_db_test"
    GEMINI_API_KEY: str = ""
    UPLOAD_DIRECTORY: str = "uploads/receipts"
    FRONTEND_URL: str = ""

    # JWT configurations (JWT_SECRET_KEY has no default and must be provided in the environment)
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
