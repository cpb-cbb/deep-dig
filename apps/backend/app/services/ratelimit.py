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


JOB_SUBMIT_USER_RULE = RateLimitRule(
    "job_submit_user", settings.job_submit_user_limit_per_minute, 60
)
JOB_SUBMIT_IP_RULE = RateLimitRule(
    "job_submit_ip", settings.job_submit_ip_limit_per_minute, 60
)
JOB_READ_USER_RULE = RateLimitRule(
    "job_read_user", settings.job_read_user_limit_per_minute, 60
)
JOB_READ_IP_RULE = RateLimitRule(
    "job_read_ip", settings.job_read_ip_limit_per_minute, 60
)
JOB_ACTION_USER_RULE = RateLimitRule(
    "job_action_user", settings.job_action_user_limit_per_minute, 60
)
JOB_ACTION_IP_RULE = RateLimitRule(
    "job_action_ip", settings.job_action_ip_limit_per_minute, 60
)


async def check_rate_limit(identifier: str, rule: RateLimitRule) -> None:
    await check_rate_limits([(identifier, rule)])


async def check_rate_limits(entries: list[tuple[str, RateLimitRule]]) -> None:
    redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    try:
        for identifier, rule in entries:
            key = f"ratelimit:{rule.name}:{identifier}"
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, rule.window_seconds)
            if count > rule.limit:
                ttl = await redis.ttl(key)
                raise AppError(
                    429,
                    "RATE_LIMITED",
                    "Too many requests",
                    {"retry_after": max(ttl, 1)},
                )
    finally:
        await redis.close()
