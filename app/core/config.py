from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Dict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
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
    AUTO_CREATE_TABLES: bool = False
    
    # Redis
    REDIS_ENABLED: bool = True
    REDIS_URL: str = "redis://localhost:6379/0"

    # Logging
    LOG_LEVEL: str = "INFO"

    # Rate limits (requests per window)
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    RATE_LIMIT_DEFAULT_REQUESTS: int = 120
    RATE_LIMIT_AUTH_REQUESTS: int = 20
    RATE_LIMIT_AI_REQUESTS: int = 40
    RATE_LIMIT_ADMIN_REQUESTS: int = 30

    # Microservice integration URLs
    AI_SERVICE_URL: str | None = None
    POST_ANALYSIS_SERVICE_URL: str | None = None
    BILLING_SERVICE_URL: str | None = None
    BILLING_WEBHOOK_TOKEN: str | None = None
    STRIPE_SECRET_KEY: str | None = None
    STRIPE_WEBHOOK_SECRET: str | None = None
    STRIPE_SUCCESS_URL: str | None = None
    STRIPE_CANCEL_URL: str | None = None
    MICROSERVICE_TIMEOUT_SECONDS: float = 10.0

    # Account verification and password recovery email delivery
    RESEND_API_KEY: str | None = None
    EMAIL_FROM: str | None = None
    FRONTEND_URL: str = "http://localhost:3000"
    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 60
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()
