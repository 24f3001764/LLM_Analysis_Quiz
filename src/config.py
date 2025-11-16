from pydantic import BaseSettings, Field
from typing import Optional
import os
from pathlib import Path

class Settings(BaseSettings):
    # API Configuration
    APP_NAME: str = "LLM Analysis Quiz"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    QUIZ_SECRET: str = os.getenv("QUIZ_SECRET", "default-quiz-secret")
    
    # Server Configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    WORKERS: int = int(os.getenv("WORKERS", "1"))
    
    # Timeout Configuration (in seconds)
    REQUEST_TIMEOUT: int = 180  # 3 minutes
    BROWSER_TIMEOUT: int = 30
    
    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    LOGS_DIR: Path = BASE_DIR / "logs"
    
    # Ensure logs directory exists
    if not LOGS_DIR.exists():
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # CORS
    CORS_ORIGINS: list = ["*"]  # In production, replace with specific origins
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create settings instance
settings = Settings()

# Export settings
__all__ = ["settings"]
