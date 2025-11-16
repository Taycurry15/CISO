"""
Celery Application Configuration
Handles background tasks for CMMC Compliance Platform
"""

import os
from celery import Celery
from celery.schedules import crontab

# Read configuration from environment
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")

# Initialize Celery app
app = Celery(
    "cmmc_platform",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["api.tasks"]
)

# Celery configuration
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    task_soft_time_limit=3300,  # 55 minutes soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    result_expires=86400,  # Results expire after 24 hours
)

# Periodic tasks schedule
app.conf.beat_schedule = {
    # Run scheduled integrations every hour
    "check-scheduled-integrations": {
        "task": "api.tasks.check_scheduled_integrations",
        "schedule": crontab(minute=0),  # Every hour
    },
    # Calculate SPRS scores daily
    "calculate-daily-sprs": {
        "task": "api.tasks.calculate_daily_sprs",
        "schedule": crontab(hour=2, minute=0),  # 2 AM daily
    },
    # Check for overdue POA&Ms daily
    "check-overdue-poams": {
        "task": "api.tasks.check_overdue_poams",
        "schedule": crontab(hour=9, minute=0),  # 9 AM daily
    },
    # Generate weekly compliance reports
    "generate-weekly-reports": {
        "task": "api.tasks.generate_weekly_reports",
        "schedule": crontab(day_of_week=1, hour=8, minute=0),  # Monday 8 AM
    },
    # Clean up old integration logs
    "cleanup-integration-logs": {
        "task": "api.tasks.cleanup_integration_logs",
        "schedule": crontab(day_of_week=0, hour=3, minute=0),  # Sunday 3 AM
    },
}

if __name__ == "__main__":
    app.start()
