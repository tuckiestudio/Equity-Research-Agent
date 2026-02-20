from __future__ import annotations
from typing import Optional, Any
"""
Background job management API endpoints.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.models.user import User
from app.tasks.scheduler import get_scheduler, list_scheduled_jobs, trigger_job

router = APIRouter(prefix="/jobs", tags=["background-jobs"])


# --- Response Schemas ---

class JobInfo(BaseModel):
    """Information about a scheduled job."""

    id: str
    name: str
    next_run_time: Optional[str]
    trigger: str


class JobsListResponse(BaseModel):
    """Response containing list of scheduled jobs."""

    jobs: list[JobInfo]
    scheduler_running: bool


class JobTriggerResponse(BaseModel):
    """Response after triggering a job."""

    success: bool
    message: str


# --- Admin Check Helper ---

def is_admin_user(user: User) -> bool:
    """Check if user has admin privileges via is_admin flag."""
    return getattr(user, "is_admin", False)


# --- Endpoints ---

@router.get("/list", response_model=JobsListResponse)
async def list_jobs(
    current_user: User = Depends(get_current_user),
) -> JobsListResponse:
    """
    List all scheduled background jobs.

    This endpoint shows all configured background jobs, their schedules,
    and next run times. Useful for monitoring and debugging.
    """
    jobs = await list_scheduled_jobs()
    scheduler = get_scheduler()

    return JobsListResponse(
        jobs=[JobInfo(**job) for job in jobs],
        scheduler_running=scheduler is not None and scheduler.running,
    )


@router.post("/trigger/{job_id}", response_model=JobTriggerResponse)
async def trigger_job_endpoint(
    job_id: str,
    current_user: User = Depends(get_current_user),
) -> JobTriggerResponse:
    """
    Manually trigger a scheduled background job.

    This is useful for:
    - Testing job logic
    - Forcing immediate updates
    - Recovering from missed runs

    Available job IDs:
    - update_stock_prices: Update stock prices for all tracked stocks
    - refresh_fundamentals: Refresh fundamentals data
    - refresh_news: Fetch latest news
    - cleanup_old_data: Clean up old data
    - update_usage_stats: Update usage statistics
    - analyze_news_sentiment: Analyze news sentiment
    """
    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=403,
            detail="Only administrators can manually trigger jobs"
        )

    success = await trigger_job(job_id)

    if success:
        return JobTriggerResponse(
            success=True,
            message=f"Job '{job_id}' triggered successfully"
        )
    else:
        return JobTriggerResponse(
            success=False,
            message=f"Failed to trigger job '{job_id}'. Check if the job exists."
        )


@router.get("/status")
async def get_scheduler_status(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get the current status of the background task scheduler.

    Returns information about scheduler state, running jobs, etc.
    """
    scheduler = get_scheduler()

    if scheduler is None:
        return {
            "running": False,
            "state": "NOT_INITIALIZED",
            "job_count": 0
        }

    jobs = scheduler.get_jobs()

    return {
        "running": scheduler.running,
        "state": "RUNNING" if scheduler.running else "STOPPED",
        "job_count": len(jobs),
        "jobs": [
            {
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            }
            for job in jobs
        ]
    }


@router.post("/restart")
async def restart_scheduler(
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """
    Restart the background task scheduler.

    This can be useful if the scheduler has stopped or needs to be
    reconfigured with new job schedules.
    """
    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=403,
            detail="Only administrators can restart the scheduler"
        )

    from app.tasks.scheduler import start_scheduler, stop_scheduler

    await stop_scheduler()
    await start_scheduler()

    return {"message": "Scheduler restarted successfully"}
