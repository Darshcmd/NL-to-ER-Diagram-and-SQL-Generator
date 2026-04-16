from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings from environment variables."""

    gemini_api_key: Optional[str] = None
    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"
    debug: bool = False

    class Config:
        env_file = (".env", "backend/.env")
        case_sensitive = False


settings = Settings()
