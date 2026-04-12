from pydantic_settings import BaseSettings
from typing import List, Dict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Optimos API"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    
    # Security
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Test User
    TEST_USER: Dict[str, str] = {
        "username": "testuser",
        "password": "testpass123"
    }
    
    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/optimos"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Email Configuration
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = "your-email@gmail.com"
    SMTP_PASSWORD: str = "your-app-password"
    SMTP_FROM_EMAIL: str = "noreply@optimos.com"
    SMTP_FROM_NAME: str = "Optimos"
    
    # Email Links (for verification/reset links in emails)
    FRONTEND_URL: str = "http://localhost:3000"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
