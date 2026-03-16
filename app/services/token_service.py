"""Token blacklist management for logout functionality."""

import redis
from app.core.config import settings

# Connect to Redis
try:
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    redis_client.ping()  # Test connection
    USE_REDIS = True
except Exception as e:
    print(f"Redis connection failed: {e}. Falling back to in-memory storage.")
    USE_REDIS = False
    # In-memory fallback
    blacklisted_tokens = set()


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
