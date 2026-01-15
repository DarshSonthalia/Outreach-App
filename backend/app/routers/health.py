"""
Health check router for monitoring system status.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.celery_app import celery_app
from celery.app.control import Inspect
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/")
def health_check():
    """Basic health check."""
    return {"ok": True}


@router.get("/db")
def database_health(db: Session = Depends(get_db)):
    """Check database connectivity."""
    try:
        # Simple query to test connection - use text() for SQLAlchemy 2.0
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}


@router.get("/celery")
def celery_health():
    """
    Check Celery worker status.
    Returns information about active workers and scheduled tasks.
    """
    try:
        i = Inspect(app=celery_app)
        
        # Get active workers
        active_workers = i.active()
        scheduled_tasks = i.scheduled()
        registered_tasks = i.registered()
        
        # Count workers
        worker_count = len(active_workers) if active_workers else 0
        
        # Count scheduled tasks across all workers
        total_scheduled = 0
        if scheduled_tasks:
            for worker_tasks in scheduled_tasks.values():
                total_scheduled += len(worker_tasks)
        
        # Get registered task names
        task_names = []
        if registered_tasks:
            for worker_name, tasks in registered_tasks.items():
                task_names.extend(tasks)
        
        status = "healthy" if worker_count > 0 else "no_workers"
        
        return {
            "status": status,
            "workers_active": worker_count,
            "tasks_scheduled": total_scheduled,
            "registered_tasks": len(set(task_names)),
            "worker_details": list(active_workers.keys()) if active_workers else []
        }
    except Exception as e:
        logger.error(f"Celery health check failed: {e}")
        return {
            "status": "error",
            "workers_active": 0,
            "error": str(e)
        }


@router.get("/beat")
def celery_beat_health():
    """
    Check Celery Beat scheduler status.
    """
    try:
        i = Inspect(app=celery_app)
        
        # Check if beat schedule is configured
        beat_schedule = celery_app.conf.beat_schedule
        
        return {
            "status": "configured",
            "scheduled_jobs": len(beat_schedule),
            "jobs": list(beat_schedule.keys())
        }
    except Exception as e:
        logger.error(f"Celery beat health check failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }
