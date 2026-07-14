from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    MONGODB_URL: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str

    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int
    
    # API
    API_BASE_URL: str = "http://localhost:8000"


    # Google OAuth
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str

    # Gemini OCR API
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL_NAME: str = "gemini-3.5-flash"

    # Resend Email
    RESEND_API_KEY: str
    RESEND_SENDER_EMAIL: str
    RESEND_SENDER_NAME: str

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()
