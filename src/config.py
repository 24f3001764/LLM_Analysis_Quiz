from pydantic import Field, validator
from pydantic_settings import BaseSettings
from typing import Optional, List, Union, Dict, Any
import os
import json
from pathlib import Path
from urllib.parse import urlparse

class Settings(BaseSettings):
    # Pydantic v2 config
    model_config = {
        "extra": "allow",  # Allow extra environment variables
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "validate_default": True,
        "validate_assignment": True
    }
    
    # Application Metadata
    APP_NAME: str = "LLM Analysis Quiz"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # API Keys
    OPENAI_API_KEY: str = ""
    SECRET_KEY: str = "your-secret-key-change-in-production"
    QUIZ_SECRET: str = "default-quiz-secret"
    API_KEY: str = ""
    
    # API Configuration
    API_PREFIX: str = "/api"
    
    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1
    RELOAD: bool = False
    
    # Timeout Configuration (in seconds)
    REQUEST_TIMEOUT: int = 180  # 3 minutes
    BROWSER_TIMEOUT: int = 30
    API_TIMEOUT: int = 30
    
    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    LOGS_DIR: Path = BASE_DIR / "logs"
    DOWNLOADS_DIR: Path = BASE_DIR / "downloads"
    TEMP_DIR: Path = BASE_DIR / "temp"
    
    # Browser Configuration
    HEADLESS_BROWSER: bool = True
    BROWSER_LAUNCH_ARGS: List[str] = [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-accelerated-2d-canvas",
        "--no-first-run",
        "--no-zygote",
        "--single-process",
        "--disable-gpu",
        "--disable-software-rasterizer",
        "--disable-blink-features=AutomationControlled"
    ]
    
    # Quiz Configuration
    MAX_QUESTIONS: int = int(os.getenv("MAX_QUESTIONS", "50"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY: int = int(os.getenv("RETRY_DELAY", "5"))  # seconds
    
    # File Handling
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_FILE_TYPES: List[str] = [
        "text/plain",
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/json",
        "image/jpeg",
        "image/png",
        "image/gif"
    ]
    
    # Security
    CORS_ORIGINS: List[str] = Field(default=["*"], env="CORS_ORIGINS")
    ALLOWED_HOSTS: List[str] = Field(default=["*"], env="ALLOWED_HOSTS")
    RATE_LIMIT: str = Field(default="100/minute", env="RATE_LIMIT")
    
    # Logging Configuration
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_MAX_SIZE: int = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT: int = 5
    
    # Create necessary directories
    @validator('LOGS_DIR', 'DOWNLOADS_DIR', 'TEMP_DIR', pre=True)
    def create_dirs(cls, v):
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    # Validate CORS origins
    @validator('CORS_ORIGINS', pre=True)
    def validate_cors_origins(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [v]
        return v
    
    # Model configuration is now handled by model_config at the class level
    
    @property
    def downloads_path(self) -> Path:
        """Get the absolute path to the downloads directory."""
        path = Path(self.downloads_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path.absolute()

# Global settings instance
settings = Settings()

# Export settings
__all__ = ["settings"]
