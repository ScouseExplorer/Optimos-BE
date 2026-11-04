from types import SimpleNamespace

import pytest

from app.core.runtime_validation import assert_runtime_settings_safe, redis_required, validate_runtime_settings


def _base_settings(**overrides):
    defaults = {
        "ENVIRONMENT": "development",
        "SECRET_KEY": "your-secret-key-here-change-in-production",
        "ACCESS_TOKEN_EXPIRE_MINUTES": 30,
        "RATE_LIMIT_WINDOW_SECONDS": 60,
        "RATE_LIMIT_DEFAULT_REQUESTS": 120,
        "RATE_LIMIT_AUTH_REQUESTS": 20,
        "RATE_LIMIT_AI_REQUESTS": 40,
        "RATE_LIMIT_ADMIN_REQUESTS": 30,
        "AUTO_CREATE_TABLES": False,
        "DATABASE_URL": "sqlite:///./optimos.db",
        "LOG_LEVEL": "INFO",
        "MICROSERVICE_TIMEOUT_SECONDS": 10.0,
        "AI_SERVICE_URL": None,
        "POST_ANALYSIS_SERVICE_URL": None,
        "STRIPE_SECRET_KEY": "sk_test_x",
        "STRIPE_WEBHOOK_SECRET": "whsec_test",
        "STRIPE_CREDIT_PRICE_ID": "price_credit",
        "STRIPE_PRO_PRICE_ID": "price_pro",
        "STRIPE_ENTERPRISE_PRICE_ID": "price_enterprise",
        "STRIPE_SUCCESS_URL": "https://app.example.com/billing/success",
        "STRIPE_CANCEL_URL": "https://app.example.com/billing/cancel",
        "ALLOW_SELF_SERVICE_TIER_CHANGE": False,
        "REDIS_ENABLED": True,
        "REDIS_URL": "redis://localhost:6379/0",
        "RESEND_API_KEY": "re_test",
        "EMAIL_FROM": "Optimos <test@example.com>",
        "FRONTEND_URL": "https://app.example.com",
        "EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS": 24,
        "PASSWORD_RESET_TOKEN_EXPIRE_MINUTES": 60,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_development_allows_default_secret_marker():
    settings = _base_settings()
    errors = validate_runtime_settings(settings)
    assert errors == []


def test_production_rejects_default_secret():
    settings = _base_settings(ENVIRONMENT="production")
    errors = validate_runtime_settings(settings)
    assert any("SECRET_KEY" in e for e in errors)


def test_production_rejects_sqlite_database():
    settings = _base_settings(
        ENVIRONMENT="production",
        SECRET_KEY="this-is-a-long-safe-secret-key-for-prod-123",
    )
    errors = validate_runtime_settings(settings)
    assert any("DATABASE_URL" in e for e in errors)


def test_negative_rate_limit_rejected_in_all_envs():
    settings = _base_settings(RATE_LIMIT_DEFAULT_REQUESTS=0)
    errors = validate_runtime_settings(settings)
    assert any("RATE_LIMIT_DEFAULT_REQUESTS" in e for e in errors)


def test_production_requires_redis_enabled():
    settings = _base_settings(
        ENVIRONMENT="production",
        SECRET_KEY="this-is-a-long-safe-secret-key-for-prod-123",
        DATABASE_URL="postgresql://u:p@db/optimos",
        REDIS_ENABLED=False,
        REDIS_URL="redis://redis:6379/0",
    )
    errors = validate_runtime_settings(settings)
    assert any("REDIS_ENABLED" in e for e in errors)


def test_production_with_redis_enabled_has_no_redis_error():
    settings = _base_settings(
        ENVIRONMENT="production",
        SECRET_KEY="this-is-a-long-safe-secret-key-for-prod-123",
        DATABASE_URL="postgresql://u:p@db/optimos",
        REDIS_ENABLED=True,
        REDIS_URL="redis://redis:6379/0",
    )
    assert validate_runtime_settings(settings) == []


def test_production_requires_stripe_billing_configuration():
    settings = _base_settings(
        ENVIRONMENT="production",
        SECRET_KEY="this-is-a-long-safe-secret-key-for-prod-123",
        DATABASE_URL="postgresql://db/optimos",
        STRIPE_SECRET_KEY=None,
        STRIPE_WEBHOOK_SECRET=None,
        STRIPE_PRO_PRICE_ID=None,
        STRIPE_ENTERPRISE_PRICE_ID=None,
        STRIPE_CREDIT_PRICE_ID=None,
    )
    errors = validate_runtime_settings(settings)
    assert any("STRIPE_SECRET_KEY" in error for error in errors)
    assert any("STRIPE_WEBHOOK_SECRET" in error for error in errors)
    assert any("STRIPE_PRO_PRICE_ID" in error for error in errors)


def test_production_rejects_self_service_paid_tier_changes():
    settings = _base_settings(
        ENVIRONMENT="production",
        SECRET_KEY="this-is-a-long-safe-secret-key-for-prod-123",
        DATABASE_URL="postgresql://db/optimos",
        ALLOW_SELF_SERVICE_TIER_CHANGE=True,
    )
    assert any(
        "ALLOW_SELF_SERVICE_TIER_CHANGE" in error
        for error in validate_runtime_settings(settings)
    )


def test_production_requires_email_delivery_configuration():
    settings = _base_settings(
        ENVIRONMENT="production",
        SECRET_KEY="this-is-a-long-safe-secret-key-for-prod-123",
        DATABASE_URL="postgresql://db/optimos",
        RESEND_API_KEY=None,
        EMAIL_FROM=None,
        FRONTEND_URL="http://localhost:3000",
    )
    errors = validate_runtime_settings(settings)
    assert any("RESEND_API_KEY" in error for error in errors)
    assert any("EMAIL_FROM" in error for error in errors)
    assert any("FRONTEND_URL" in error for error in errors)


def test_redis_required_only_for_prod_like_envs():
    assert redis_required(_base_settings(ENVIRONMENT="production"))
    assert redis_required(_base_settings(ENVIRONMENT="staging"))
    assert not redis_required(_base_settings(ENVIRONMENT="development"))


def _unreachable_redis(monkeypatch, environment):
    import redis as redis_lib
    from app.services import rate_limit_service

    def boom(*args, **kwargs):
        raise redis_lib.ConnectionError("down")

    monkeypatch.setattr(rate_limit_service.redis, "from_url", boom)
    monkeypatch.setattr(rate_limit_service.settings, "REDIS_ENABLED", True)
    monkeypatch.setattr(rate_limit_service.settings, "ENVIRONMENT", environment)
    return rate_limit_service


def test_rate_limiter_fails_fast_in_production_when_redis_down(monkeypatch):
    svc = _unreachable_redis(monkeypatch, "production")
    with pytest.raises(RuntimeError, match="Redis is required"):
        svc._get_redis_client()


def test_rate_limiter_degrades_in_development_when_redis_down(monkeypatch):
    svc = _unreachable_redis(monkeypatch, "development")
    assert svc._get_redis_client() is None


def test_token_service_fails_fast_in_production_when_redis_down(monkeypatch):
    import importlib
    import sys

    import redis as redis_lib
    from app.core.config import settings

    def boom(*args, **kwargs):
        raise redis_lib.ConnectionError("down")

    original = sys.modules.get("app.services.token_service")
    monkeypatch.setattr(redis_lib, "from_url", boom)
    monkeypatch.setattr(settings, "REDIS_ENABLED", True)
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    sys.modules.pop("app.services.token_service", None)
    try:
        with pytest.raises(RuntimeError, match="Redis is required"):
            importlib.import_module("app.services.token_service")
    finally:
        if original is not None:
            sys.modules["app.services.token_service"] = original


def test_assert_runtime_raises_on_invalid_prod_config():
    settings = _base_settings(ENVIRONMENT="prod")
    with pytest.raises(RuntimeError):
        assert_runtime_settings_safe(settings)
