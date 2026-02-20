"""
Tests for the background task scheduler.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.tasks.scheduler import (
    get_scheduler,
    list_scheduled_jobs,
    start_scheduler,
    stop_scheduler,
    trigger_job,
)


@pytest.fixture
async def clean_scheduler():
    """Ensure scheduler is clean before/after tests."""
    await stop_scheduler()
    yield
    await stop_scheduler()


class TestSchedulerLifecycle:
    """Test scheduler startup and shutdown."""

    @pytest.mark.asyncio
    async def test_start_scheduler(self, clean_scheduler):
        """Test starting the scheduler."""
        scheduler = await start_scheduler()

        assert scheduler is not None
        assert scheduler.running
        assert len(scheduler.get_jobs()) > 0

        await stop_scheduler()

    @pytest.mark.asyncio
    async def test_stop_scheduler(self, clean_scheduler):
        """Test stopping the scheduler."""
        await start_scheduler()
        await stop_scheduler()

        scheduler = get_scheduler()
        assert scheduler is None

    @pytest.mark.asyncio
    async def test_start_scheduler_already_running(self, clean_scheduler):
        """Test starting scheduler when already running."""
        await start_scheduler()
        scheduler1 = get_scheduler()

        await start_scheduler()
        scheduler2 = get_scheduler()

        assert scheduler1 is scheduler2
        await stop_scheduler()

    @pytest.mark.asyncio
    async def test_stop_scheduler_not_running(self, clean_scheduler):
        """Test stopping scheduler when not running."""
        # Should not raise an error
        await stop_scheduler()

        scheduler = get_scheduler()
        assert scheduler is None


class TestScheduledJobs:
    """Test scheduled job registration."""

    @pytest.mark.asyncio
    async def test_jobs_registered(self, clean_scheduler):
        """Test that all expected jobs are registered."""
        await start_scheduler()
        scheduler = get_scheduler()

        jobs = scheduler.get_jobs()
        job_ids = {job.id for job in jobs}

        expected_jobs = {
            "update_stock_prices",
            "refresh_fundamentals",
            "refresh_news",
            "cleanup_old_data",
            "update_usage_stats",
            "analyze_news_sentiment",
        }

        assert expected_jobs.issubset(job_ids)
        await stop_scheduler()

    @pytest.mark.asyncio
    async def test_job_attributes(self, clean_scheduler):
        """Test that jobs have correct attributes."""
        await start_scheduler()
        scheduler = get_scheduler()

        price_job = scheduler.get_job("update_stock_prices")
        assert price_job is not None
        assert price_job.name == "Update Stock Prices"

        await stop_scheduler()


class TestListJobs:
    """Test listing scheduled jobs."""

    @pytest.mark.asyncio
    async def test_list_jobs_no_scheduler(self, clean_scheduler):
        """Test listing jobs when scheduler is not running."""
        jobs = await list_scheduled_jobs()

        assert jobs == []

    @pytest.mark.asyncio
    async def test_list_jobs_with_scheduler(self, clean_scheduler):
        """Test listing jobs when scheduler is running."""
        await start_scheduler()
        jobs = await list_scheduled_jobs()

        assert len(jobs) > 0

        # Check job structure
        job = jobs[0]
        assert "id" in job
        assert "name" in job
        assert "next_run_time" in job
        assert "trigger" in job

        await stop_scheduler()


class TestTriggerJob:
    """Test manual job triggering."""

    @pytest.mark.asyncio
    async def test_trigger_job_no_scheduler(self, clean_scheduler):
        """Test triggering job when scheduler is not running."""
        success = await trigger_job("update_stock_prices")

        assert success is False

    @pytest.mark.asyncio
    async def test_trigger_job_invalid_id(self, clean_scheduler):
        """Test triggering a job with invalid ID."""
        await start_scheduler()
        success = await trigger_job("invalid_job_id")

        assert success is False
        await stop_scheduler()

    @pytest.mark.asyncio
    async def test_trigger_job_valid_id(self, clean_scheduler):
        """Test triggering a valid job."""
        await start_scheduler()

        # Mock the job function to avoid actual execution
        with patch("app.tasks.scheduler.update_stock_prices", new_callable=AsyncMock):
            success = await trigger_job("update_stock_prices")

        assert success is True
        await stop_scheduler()


class TestJobFunctions:
    """Test individual job functions."""

    @pytest.mark.asyncio
    async def test_update_stock_prices_job(self, clean_scheduler):
        """Test the stock price update job function."""
        # Mock the service function that's imported in the scheduler
        with patch("app.services.data.price_service.update_prices_for_watched_stocks", return_value=10):
            from app.tasks.scheduler import update_stock_prices

            await update_stock_prices()

    @pytest.mark.asyncio
    async def test_cleanup_old_data_job(self, clean_scheduler):
        """Test the cleanup job function."""
        # Mock the service functions that are imported in the scheduler
        with patch("app.services.maintenance.cleanup_old_sessions", return_value=5):
            with patch("app.services.maintenance.cleanup_old_logs", return_value=10):
                from app.tasks.scheduler import cleanup_old_data

                await cleanup_old_data()


@pytest.mark.asyncio
async def test_multiple_scheduler_lifecycle_cycles(clean_scheduler):
    """Test multiple start/stop cycles."""
    for _ in range(3):
        scheduler = await start_scheduler()
        assert scheduler.running

        await stop_scheduler()
        assert get_scheduler() is None
