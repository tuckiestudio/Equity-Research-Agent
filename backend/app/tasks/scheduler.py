"""
Background task scheduler using APScheduler.

This module handles all scheduled background jobs for the application,
including price updates, data refreshes, and maintenance tasks.
"""
from __future__ import annotations

import logging
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.db.session import async_session_factory

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler: Optional[AsyncIOScheduler] = None


def get_scheduler() -> Optional[AsyncIOScheduler]:
    """Get the global scheduler instance."""
    return scheduler


async def start_scheduler() -> AsyncIOScheduler:
    """
    Start the background task scheduler.

    This should be called during application startup.
    """
    global scheduler

    if scheduler is not None:
        logger.warning("Scheduler already started")
        return scheduler

    logger.info("Starting background task scheduler")

    # Create scheduler with asyncio job store
    scheduler = AsyncIOScheduler(
        timezone="UTC",
        job_defaults={
            "coalesce": True,  # Combine missed jobs into one
            "max_instances": 1,  # Only run one instance of each job
            "misfire_grace_time": 3600,  # Allow jobs to run up to 1 hour late
        },
    )

    # Add scheduled jobs
    await _register_scheduled_jobs()

    # Start the scheduler
    scheduler.start()
    logger.info("Background task scheduler started successfully")

    return scheduler


async def stop_scheduler() -> None:
    """
    Stop the background task scheduler.

    This should be called during application shutdown.
    """
    global scheduler

    if scheduler is None:
        logger.warning("Scheduler not running")
        return

    logger.info("Stopping background task scheduler")
    scheduler.shutdown(wait=True)
    scheduler = None
    logger.info("Background task scheduler stopped")


async def _register_scheduled_jobs() -> None:
    """Register all scheduled background jobs."""

    # === Price Update Jobs ===

    # Update stock prices every 5 minutes during market hours
    scheduler.add_job(
        update_stock_prices,
        trigger=CronTrigger(
            day_of_week="mon-fri",
            hour="9-16",  # 9 AM to 4 PM UTC (adjust for your market timezone)
            minute="*/5",  # Every 5 minutes
        ),
        id="update_stock_prices",
        name="Update Stock Prices",
        replace_existing=True,
    )

    # === Data Refresh Jobs ===

    # Refresh fundamentals data daily at 6 AM
    scheduler.add_job(
        refresh_fundamentals_data,
        trigger=CronTrigger(
            hour=6,
            minute=0,
        ),
        id="refresh_fundamentals",
        name="Refresh Fundamentals Data",
        replace_existing=True,
    )

    # Refresh news data every hour
    scheduler.add_job(
        refresh_news_data,
        trigger=IntervalTrigger(hours=1),
        id="refresh_news",
        name="Refresh News Data",
        replace_existing=True,
    )

    # === Maintenance Jobs ===

    # Clean up old session data daily at 3 AM
    scheduler.add_job(
        cleanup_old_data,
        trigger=CronTrigger(
            hour=3,
            minute=0,
        ),
        id="cleanup_old_data",
        name="Clean Up Old Data",
        replace_existing=True,
    )

    # Update usage statistics hourly
    scheduler.add_job(
        update_usage_statistics,
        trigger=IntervalTrigger(hours=1),
        id="update_usage_stats",
        name="Update Usage Statistics",
        replace_existing=True,
    )

    # === AI/Analysis Jobs ===

    # Generate sentiment analysis for new news every 2 hours
    scheduler.add_job(
        analyze_news_sentiment,
        trigger=IntervalTrigger(hours=2),
        id="analyze_news_sentiment",
        name="Analyze News Sentiment",
        replace_existing=True,
    )

    logger.info(f"Registered {len(scheduler.get_jobs())} scheduled jobs")


# === Background Job Functions ===

async def update_stock_prices() -> None:
    """
    Update stock prices for all tracked stocks.

    This job runs every 5 minutes during market hours.
    """
    logger.info("Starting stock price update job")

    try:
        async with async_session_factory() as db:
            # Import here to avoid circular imports
            from app.services.data.price_service import update_prices_for_watched_stocks

            updated_count = await update_prices_for_watched_stocks(db)
            logger.info(f"Updated prices for {updated_count} stocks")

    except Exception as e:
        logger.error(f"Error updating stock prices: {e}")


async def refresh_fundamentals_data() -> None:
    """
    Refresh fundamentals data for all tracked stocks.

    This job runs once daily at 6 AM.
    """
    logger.info("Starting fundamentals data refresh job")

    try:
        async with async_session_factory() as db:
            from app.services.data.fundamentals_service import refresh_all_fundamentals

            refreshed_count = await refresh_all_fundamentals(db)
            logger.info(f"Refreshed fundamentals for {refreshed_count} stocks")

    except Exception as e:
        logger.error(f"Error refreshing fundamentals: {e}")


async def refresh_news_data() -> None:
    """
    Refresh news data for all tracked stocks.

    This job runs every hour.
    """
    logger.info("Starting news data refresh job")

    try:
        async with async_session_factory() as db:
            from app.services.news.news_service import fetch_latest_news_for_all_stocks

            fetched_count = await fetch_latest_news_for_all_stocks(db)
            logger.info(f"Fetched news for {fetched_count} stocks")

    except Exception as e:
        logger.error(f"Error refreshing news: {e}")


async def cleanup_old_data() -> None:
    """
    Clean up old data that's no longer needed.

    This job runs once daily at 3 AM.
    """
    logger.info("Starting data cleanup job")

    try:
        async with async_session_factory() as db:
            from app.services.maintenance import cleanup_old_logs, cleanup_old_sessions

            sessions_deleted = await cleanup_old_sessions(db)
            logs_deleted = await cleanup_old_logs(db)

            logger.info(f"Deleted {sessions_deleted} old sessions and {logs_deleted} old logs")

    except Exception as e:
        logger.error(f"Error during cleanup: {e}")


async def update_usage_statistics() -> None:
    """
    Update usage statistics for monitoring and billing.

    This job runs every hour.
    """
    logger.info("Starting usage statistics update job")

    try:
        async with async_session_factory() as db:
            from app.services.analytics import update_hourly_usage_stats

            await update_hourly_usage_stats(db)
            logger.info("Updated usage statistics")

    except Exception as e:
        logger.error(f"Error updating usage statistics: {e}")


async def analyze_news_sentiment() -> None:
    """
    Analyze sentiment of newly fetched news articles.

    This job runs every 2 hours.
    """
    logger.info("Starting news sentiment analysis job")

    try:
        async with async_session_factory() as db:
            from app.services.ai.sentiment_service import analyze_unprocessed_news

            analyzed_count = await analyze_unprocessed_news(db)
            logger.info(f"Analyzed sentiment for {analyzed_count} news articles")

    except Exception as e:
        logger.error(f"Error analyzing news sentiment: {e}")


# === Manual Job Triggering ===

async def trigger_job(job_id: str) -> bool:
    """
    Manually trigger a scheduled job.

    Args:
        job_id: The ID of the job to trigger

    Returns:
        True if job was triggered, False if not found
    """
    if scheduler is None:
        logger.error("Scheduler not running")
        return False

    job = scheduler.get_job(job_id)
    if job is None:
        logger.error(f"Job {job_id} not found")
        return False

    job.modify(next_run_time=None)  # Trigger immediately
    logger.info(f"Manually triggered job: {job_id}")
    return True


async def list_scheduled_jobs() -> list[dict]:
    """
    Get information about all scheduled jobs.

    Returns:
        List of job information dictionaries
    """
    if scheduler is None:
        return []

    jobs = []
    for job in scheduler.get_jobs():
        jobs.append(
            {
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger),
            }
        )

    return jobs
