from __future__ import annotations

from dataclasses import dataclass

from arq import create_pool
from arq.connections import RedisSettings

from app.config import settings
from app.errors import AppError


@dataclass(frozen=True)
class RateLimitRule:
    name: str
    limit: int
    window_seconds: int


USER_API_RULE = RateLimitRule("user_api", 30, 60)
IP_API_RULE = RateLimitRule("ip_api", 60, 60)


async def check_rate_limit(identifier: str, rule: RateLimitRule) -> None:
    redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    key = f"ratelimit:{rule.name}:{identifier}"
    try:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, rule.window_seconds)
        if count > rule.limit:
            ttl = await redis.ttl(key)
            raise AppError(429, "RATE_LIMITED", "Too many requests", {"retry_after": max(ttl, 1)})
    finally:
        await redis.close()
