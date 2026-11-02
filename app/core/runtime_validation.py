from app.core.config import Settings
from urllib.parse import urlparse


INSECURE_SECRET_MARKERS = {
    "your-secret-key-here-change-in-production",
    "your-super-secret-key-change-this",
    "your-super-secret-key-change-this-in-production",
}


def _is_prod_like(environment: str) -> bool:
    return environment.strip().lower() in {"production", "prod", "staging"}


def redis_required(settings: Settings) -> bool:
    """Production/staging must use Redis; in-memory fallback is dev/test only."""
    return _is_prod_like(settings.ENVIRONMENT)


def validate_runtime_settings(settings: Settings) -> list[str]:
    errors: list[str] = []
    env = settings.ENVIRONMENT.strip().lower()

    if settings.ACCESS_TOKEN_EXPIRE_MINUTES <= 0:
        errors.append("ACCESS_TOKEN_EXPIRE_MINUTES must be > 0")

    if settings.RATE_LIMIT_WINDOW_SECONDS <= 0:
        errors.append("RATE_LIMIT_WINDOW_SECONDS must be > 0")

    if settings.RATE_LIMIT_DEFAULT_REQUESTS <= 0:
        errors.append("RATE_LIMIT_DEFAULT_REQUESTS must be > 0")

    if settings.RATE_LIMIT_AUTH_REQUESTS <= 0:
        errors.append("RATE_LIMIT_AUTH_REQUESTS must be > 0")

    if settings.RATE_LIMIT_AI_REQUESTS <= 0:
        errors.append("RATE_LIMIT_AI_REQUESTS must be > 0")

    if settings.RATE_LIMIT_ADMIN_REQUESTS <= 0:
        errors.append("RATE_LIMIT_ADMIN_REQUESTS must be > 0")

    if settings.MICROSERVICE_TIMEOUT_SECONDS <= 0:
        errors.append("MICROSERVICE_TIMEOUT_SECONDS must be > 0")

    for field_name in [
        "AI_SERVICE_URL",
        "POST_ANALYSIS_SERVICE_URL",
        "BILLING_SERVICE_URL",
    ]:
        value = getattr(settings, field_name)
        if not value:
            continue
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            errors.append(f"{field_name} must be a valid http/https URL")

    if _is_prod_like(env):
        if settings.SECRET_KEY in INSECURE_SECRET_MARKERS or len(settings.SECRET_KEY) < 32:
            errors.append("SECRET_KEY is insecure for production/staging")

        if settings.AUTO_CREATE_TABLES:
            errors.append("AUTO_CREATE_TABLES must be false for production/staging")

        if settings.DATABASE_URL.strip().lower().startswith("sqlite"):
            errors.append("DATABASE_URL cannot use SQLite for production/staging")

        if not getattr(settings, "REDIS_ENABLED", True):
            errors.append(
                "REDIS_ENABLED must be true for production/staging "
                "(rate limits and token revocation must be shared across instances)"
            )

        if not getattr(settings, "REDIS_URL", "redis://"):
            errors.append("REDIS_URL must be set for production/staging")

        if settings.LOG_LEVEL.strip().upper() == "DEBUG":
            errors.append("LOG_LEVEL cannot be DEBUG for production/staging")

        if not settings.RESEND_API_KEY:
            errors.append("RESEND_API_KEY must be set for production/staging")

        if not settings.EMAIL_FROM:
            errors.append("EMAIL_FROM must be set for production/staging")

        frontend_url = urlparse(settings.FRONTEND_URL)
        if (
            frontend_url.scheme != "https"
            or not frontend_url.netloc
            or frontend_url.hostname in {"localhost", "127.0.0.1", "::1"}
        ):
            errors.append("FRONTEND_URL must be a public HTTPS URL for production/staging")

    if settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS <= 0:
        errors.append("EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS must be > 0")

    if settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES <= 0:
        errors.append("PASSWORD_RESET_TOKEN_EXPIRE_MINUTES must be > 0")

    frontend_url = urlparse(settings.FRONTEND_URL)
    if frontend_url.scheme not in {"http", "https"} or not frontend_url.netloc:
        errors.append("FRONTEND_URL must be a valid http/https URL")

    return errors


def assert_runtime_settings_safe(settings: Settings) -> None:
    errors = validate_runtime_settings(settings)
    if errors:
        raise RuntimeError("Invalid runtime configuration: " + "; ".join(errors))
