"""
Celery configuration for background tasks
"""
from celery import Celery
from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "fastapi_template",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.email_tasks", "app.tasks.file_tasks", "app.tasks.notification_tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Optional: Configure periodic tasks
celery_app.conf.beat_schedule = {
    # Example: Clean up old files every day
    "cleanup-old-files": {
        "task": "app.tasks.file_tasks.cleanup_old_files",
        "schedule": 86400.0,  # Daily
    },
}
