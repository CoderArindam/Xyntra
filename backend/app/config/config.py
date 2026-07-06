from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    SMTP_EMAIL: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    
    FRONTEND_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # AI Configuration
    AI_ENABLED: bool = False
    AI_PROVIDER: str = "openai"
    AI_MODEL: str = "gpt-4o"
    AI_TIMEOUT: int = 60
    AI_MAX_RETRIES: int = 3
    AI_TEMPERATURE: float = 0.0
    AI_MAX_TOKENS: int = 2000
    AI_LOG_LEVEL: str = "INFO"

    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    AZURE_OPENAI_KEY: Optional[str] = None
    PUTER_API_KEY: Optional[str] = None
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()

print("SMTP EMAIL LOADED:", settings.SMTP_EMAIL)
print("SMTP PASSWORD LOADED:", bool(settings.SMTP_PASSWORD))