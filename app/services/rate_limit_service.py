from __future__ import annotations

import logging
from collections import defaultdict
from math import floor
from time import time
from typing import Dict, List

import redis

from app.core.config import settings
from app.core.runtime_validation import redis_required

logger = logging.getLogger(__name__)


# Fallback store when Redis is unavailable.
_in_memory_tracker: Dict[str, List[float]] = defaultdict(list)


def _get_redis_client() -> redis.Redis | None:
    if not settings.REDIS_ENABLED:
        if redis_required(settings):
            raise RuntimeError("Redis is required for rate limiting in production/staging")
        return None

    try:
        client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        client.ping()
        return client
    except Exception as exc:
        if redis_required(settings):
            raise RuntimeError(
                f"Redis is required for rate limiting in production/staging but is unavailable: {exc}"
            ) from exc
        logger.warning("Redis unavailable (%s); rate limiting falls back to per-process memory", exc)
        return None


_redis_client = _get_redis_client()


class RateLimitDecision:
    def __init__(self, allowed: int, remaining: int, window: int, retry_after: int, limited: bool):
        self.allowed = allowed
        self.remaining = remaining
        self.window = window
        self.retry_after = retry_after
        self.limited = limited


class RateLimitService:
    @staticmethod
    def evaluate(client_key: str, group: str, allowed: int, window_seconds: int) -> RateLimitDecision:
        now = time()
        if _redis_client is not None:
            return RateLimitService._evaluate_with_redis(
                client_key=client_key,
                group=group,
                allowed=allowed,
                window_seconds=window_seconds,
                now=now,
            )

        return RateLimitService._evaluate_in_memory(
            client_key=client_key,
            group=group,
            allowed=allowed,
            window_seconds=window_seconds,
            now=now,
        )

    @staticmethod
    def _evaluate_with_redis(
        client_key: str,
        group: str,
        allowed: int,
        window_seconds: int,
        now: float,
    ) -> RateLimitDecision:
        bucket = floor(now / window_seconds)
        key = f"rate_limit:{group}:{client_key}:{bucket}"

        pipe = _redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, window_seconds)
        result = pipe.execute()

        current_count = int(result[0])
        remaining = max(0, allowed - current_count)
        retry_after = max(1, window_seconds - int(now % window_seconds))
        limited = current_count > allowed

        return RateLimitDecision(
            allowed=allowed,
            remaining=remaining,
            window=window_seconds,
            retry_after=retry_after,
            limited=limited,
        )

    @staticmethod
    def _evaluate_in_memory(
        client_key: str,
        group: str,
        allowed: int,
        window_seconds: int,
        now: float,
    ) -> RateLimitDecision:
        key = f"{group}:{client_key}"
        _in_memory_tracker[key] = [ts for ts in _in_memory_tracker[key] if now - ts < window_seconds]
        _in_memory_tracker[key].append(now)

        current_count = len(_in_memory_tracker[key])
        remaining = max(0, allowed - current_count)
        limited = current_count > allowed

        return RateLimitDecision(
            allowed=allowed,
            remaining=remaining,
            window=window_seconds,
            retry_after=window_seconds,
            limited=limited,
        )
