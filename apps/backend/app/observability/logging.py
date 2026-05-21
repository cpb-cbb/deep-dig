import logging

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

from app.config import settings


def configure_observability() -> None:
    logging.basicConfig(
        level=logging.INFO if settings.env != "development" else logging.DEBUG,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.env,
            release=settings.app_version,
            integrations=[FastApiIntegration()],
            traces_sample_rate=0.1 if settings.env == "production" else 1.0,
        )
