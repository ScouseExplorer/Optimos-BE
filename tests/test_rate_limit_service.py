from app.services import rate_limit_service
from app.services.rate_limit_service import RateLimitService


def test_in_memory_rate_limiter_blocks_after_limit(monkeypatch):
    monkeypatch.setattr(rate_limit_service, "_redis_client", None)
    rate_limit_service._in_memory_tracker.clear()

    allowed = 3
    decisions = []
    for _ in range(4):
        decisions.append(
            RateLimitService.evaluate(
                client_key="127.0.0.1",
                group="auth",
                allowed=allowed,
                window_seconds=60,
            )
        )

    assert decisions[0].limited is False
    assert decisions[1].limited is False
    assert decisions[2].limited is False
    assert decisions[3].limited is True
    assert decisions[3].remaining == 0


def test_rate_limiter_response_metadata_present(monkeypatch):
    monkeypatch.setattr(rate_limit_service, "_redis_client", None)
    rate_limit_service._in_memory_tracker.clear()

    decision = RateLimitService.evaluate(
        client_key="10.0.0.1",
        group="ai",
        allowed=5,
        window_seconds=30,
    )

    assert decision.allowed == 5
    assert decision.window == 30
    assert decision.retry_after >= 1
