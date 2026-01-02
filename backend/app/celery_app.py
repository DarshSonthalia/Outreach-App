"""
Celery application configuration.
"""
from celery import Celery
from app.config import settings

celery_app = Celery(
    "outreach_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.workers.campaign_worker",
        "app.workers.reply_worker",
        "app.workers.safety_worker",
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
    worker_prefetch_multiplier=1,  # Process one task at a time
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    # Process due campaign sends every minute
    "process-campaign-sends": {
        "task": "app.workers.campaign_worker.process_due_sends",
        "schedule": 60.0,  # Every minute
    },
    # Poll for replies every 2 minutes
    "poll-inbox-replies": {
        "task": "app.workers.reply_worker.poll_all_mailboxes",
        "schedule": 120.0,  # Every 2 minutes
    },
    # Safety check every 5 minutes
    "safety-snapshot": {
        "task": "app.workers.safety_worker.update_risk_snapshots",
        "schedule": 300.0,  # Every 5 minutes
    },
}
