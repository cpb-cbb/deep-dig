from unittest.mock import AsyncMock

import pytest

from app.errors import AppError
from app.services import ratelimit


class FakeRedis:
    def __init__(self) -> None:
        self.counts: dict[str, int] = {}
        self.expirations: dict[str, int] = {}
        self.closed = False

    async def incr(self, key: str) -> int:
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    async def expire(self, key: str, seconds: int) -> None:
        self.expirations[key] = seconds

    async def ttl(self, key: str) -> int:
        return self.expirations.get(key, 1)

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_rate_limits_apply_each_rule_and_close_redis(monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr(ratelimit, "create_pool", AsyncMock(return_value=redis))
    user_rule = ratelimit.RateLimitRule("submit_user_test", 2, 60)
    ip_rule = ratelimit.RateLimitRule("submit_ip_test", 3, 60)

    await ratelimit.check_rate_limits([("user-1", user_rule), ("127.0.0.1", ip_rule)])

    assert redis.counts["ratelimit:submit_user_test:user-1"] == 1
    assert redis.counts["ratelimit:submit_ip_test:127.0.0.1"] == 1
    assert redis.closed is True


@pytest.mark.asyncio
async def test_rate_limit_rejects_requests_over_the_limit(monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr(ratelimit, "create_pool", AsyncMock(return_value=redis))
    rule = ratelimit.RateLimitRule("submit_user_test", 1, 60)

    await ratelimit.check_rate_limit("user-1", rule)
    with pytest.raises(AppError) as exc_info:
        await ratelimit.check_rate_limit("user-1", rule)

    assert exc_info.value.status_code == 429
    assert exc_info.value.code == "RATE_LIMITED"
    assert exc_info.value.detail["retry_after"] == 60
