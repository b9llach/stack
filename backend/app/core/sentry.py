"""
Sentry error tracking integration
"""
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

from app.core.config import settings


def init_sentry():
    """Initialize Sentry error tracking"""
    if not settings.SENTRY_ENABLED or not settings.SENTRY_DSN:
        return

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.SENTRY_ENVIRONMENT,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
            RedisIntegration(),
            CeleryIntegration(),
        ],
        # Send default PII (personally identifiable information)
        send_default_pii=False,
        # Set traces sample rate
        profiles_sample_rate=1.0,
    )


def capture_exception(exception: Exception, context: dict = None):
    """
    Capture exception to Sentry

    Args:
        exception: Exception to capture
        context: Additional context dict
    """
    if settings.SENTRY_ENABLED:
        with sentry_sdk.push_scope() as scope:
            if context:
                for key, value in context.items():
                    scope.set_context(key, value)
            sentry_sdk.capture_exception(exception)
