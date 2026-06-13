from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "Smart Receipt API"
    APP_ENV: str = "development"
    DATABASE_URL: str = "mysql+pymysql://username:password@localhost:3306/smart_receipt_db"
    GEMINI_API_KEY: str = ""
    UPLOAD_DIRECTORY: str = "uploads/receipts"
    FRONTEND_URL: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
