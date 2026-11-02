"""Token blacklist management for logout functionality."""

import logging

import redis
from app.core.config import settings
from app.core.runtime_validation import redis_required

logger = logging.getLogger(__name__)

# In-memory fallback (development/test only; never allowed in production/staging)
blacklisted_tokens = set()

# Connect to Redis when enabled; production/staging fail fast if it is unavailable.
if settings.REDIS_ENABLED:
    try:
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        redis_client.ping()  # Test connection
        USE_REDIS = True
    except Exception as e:
        if redis_required(settings):
            raise RuntimeError(
                f"Redis is required for token revocation in production/staging but is unavailable: {e}"
            ) from e
        logger.warning("Redis unavailable (%s); token revocation falls back to per-process memory", e)
        USE_REDIS = False
else:
    if redis_required(settings):
        raise RuntimeError("Redis is required for token revocation in production/staging")
    USE_REDIS = False


def blacklist_token(token: str, expiration_seconds: int = 3600) -> None:
    """Add token to blacklist (logout). 
    
    Token will automatically expire from Redis after expiration_seconds.
    For in-memory fallback, tokens never expire.
    """
    if USE_REDIS:
        # Store token in Redis with expiration
        redis_client.setex(f"blacklist:{token}", expiration_seconds, "1")
    else:
        # In-memory fallback
        blacklisted_tokens.add(token)


def is_token_blacklisted(token: str) -> bool:
    """Check if token is blacklisted."""
    if USE_REDIS:
        return redis_client.exists(f"blacklist:{token}") > 0
    else:
        # In-memory fallback
        return token in blacklisted_tokens


def clear_blacklist() -> None:
    """Clear all blacklisted tokens (for testing/maintenance)."""
    if USE_REDIS:
        # Delete all blacklist keys
        keys = redis_client.keys("blacklist:*")
        if keys:
            redis_client.delete(*keys)
    else:
        # In-memory fallback
        blacklisted_tokens.clear()
