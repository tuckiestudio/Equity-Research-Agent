# Background Jobs System - Documentation

## Overview

The Equity Research Agent uses APScheduler to manage background jobs for periodic tasks like price updates, data refreshes, and maintenance operations.

## Architecture

### Scheduler Setup

The background task scheduler is implemented in `/app/tasks/scheduler.py` and uses APScheduler with AsyncIO support:

- **Scheduler Type**: `AsyncIOScheduler`
- **Timezone**: UTC
- **Job Coalescing**: Enabled (combines missed runs into one)
- **Max Instances**: 1 (prevents overlapping job executions)
- **Misfire Grace Time**: 3600 seconds (allows jobs to run up to 1 hour late)

### Lifecycle Management

The scheduler is integrated into the FastAPI application lifespan in `app/main.py`:

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup
    await start_scheduler()

    yield

    # Shutdown
    await stop_scheduler()
```

## Scheduled Jobs

### Price Updates

| Job ID | Schedule | Description |
|--------|----------|-------------|
| `update_stock_prices` | Every 5 minutes (Mon-Fri, 9 AM - 4 PM UTC) | Update stock prices for all tracked stocks |

### Data Refresh

| Job ID | Schedule | Description |
|--------|----------|-------------|
| `refresh_fundamentals` | Daily at 6 AM UTC | Refresh fundamentals data for all tracked stocks |
| `refresh_news` | Every hour | Fetch latest news for all tracked stocks |

### Maintenance

| Job ID | Schedule | Description |
|--------|----------|-------------|
| `cleanup_old_data` | Daily at 3 AM UTC | Clean up old session and log data |
| `update_usage_stats` | Every hour | Update usage statistics for monitoring |

### AI/Analysis

| Job ID | Schedule | Description |
|--------|----------|-------------|
| `analyze_news_sentiment` | Every 2 hours | Analyze sentiment of newly fetched news |

## API Endpoints

### List All Jobs

```bash
GET /api/v1/jobs/list
Authorization: Bearer <token>
```

Response:
```json
{
  "jobs": [
    {
      "id": "update_stock_prices",
      "name": "Update Stock Prices",
      "next_run_time": "2024-01-15T14:05:00+00:00",
      "trigger": "cron[day_of_week='mon-fri', hour='9-16', minute='*/5']"
    }
  ],
  "scheduler_running": true
}
```

### Get Scheduler Status

```bash
GET /api/v1/jobs/status
Authorization: Bearer <token>
```

Response:
```json
{
  "running": true,
  "state": "RUNNING",
  "job_count": 7,
  "jobs": [...]
}
```

### Trigger Job Manually (Admin Only)

```bash
POST /api/v1/jobs/trigger/{job_id}
Authorization: Bearer <admin_token>
```

Available job IDs:
- `update_stock_prices`
- `refresh_fundamentals`
- `refresh_news`
- `cleanup_old_data`
- `update_usage_stats`
- `analyze_news_sentiment`

### Restart Scheduler (Admin Only)

```bash
POST /api/v1/jobs/restart
Authorization: Bearer <admin_token>
```

## Implementation Guide

### Creating a New Scheduled Job

1. **Define the job function** in `app/tasks/scheduler.py`:

```python
async def my_new_job() -> None:
    """Description of what this job does."""
    logger.info("Starting my new job")

    try:
        async with async_session_maker() as db:
            # Your job logic here
            pass
    except Exception as e:
        logger.error(f"Error in my_new_job: {e}")
```

2. **Register the job** in `_register_scheduled_jobs()`:

```python
# Add to the function
scheduler.add_job(
    my_new_job,
    trigger=CronTrigger(
        hour="*/2",  # Every 2 hours
    ),
    id="my_new_job",
    name="My New Job",
    replace_existing=True,
)
```

3. **Add to the jobs list** for the admin endpoint documentation

### Job Scheduling Options

#### Interval Trigger (Run every X time units)

```python
from apscheduler.triggers.interval import IntervalTrigger

# Every 30 minutes
trigger=IntervalTrigger(minutes=30)

# Every 2 hours
trigger=IntervalTrigger(hours=2)

# Every day
trigger=IntervalTrigger(days=1)
```

#### Cron Trigger (Run at specific times)

```python
from apscheduler.triggers.cron import CronTrigger

# Daily at 6 AM
trigger=CronTrigger(hour=6, minute=0)

# Every 5 minutes during market hours
trigger=CronTrigger(
    day_of_week="mon-fri",
    hour="9-16",
    minute="*/5"
)

# Every Monday at 9 AM
trigger=CronTrigger(
    day_of_week="mon",
    hour=9,
    minute=0
)
```

### Job Best Practices

1. **Error Handling**: Always wrap job logic in try-except blocks
2. **Logging**: Log job start, completion, and any errors
3. **Database Sessions**: Use `async_session_maker()` to create new sessions
4. **Idempotency**: Jobs should be safe to run multiple times
5. **Timeouts**: Consider adding timeouts for long-running operations

### Example: Complete Job Implementation

```python
async def sync_user_portfolios() -> None:
    """
    Sync user portfolios with external data sources.

    This job runs every 6 hours to ensure portfolio data is up-to-date
    with any changes from external brokers or data sources.
    """
    logger.info("Starting portfolio sync job")

    try:
        async with async_session_maker() as db:
            from app.services.portfolio.sync import sync_all_portfolios

            synced_count = await sync_all_portfolios(db)
            logger.info(f"Synced {synced_count} portfolios")

    except Exception as e:
        logger.error(f"Error syncing portfolios: {e}", exc_info=True)

# Register in _register_scheduled_jobs()
scheduler.add_job(
    sync_user_portfolios,
    trigger=IntervalTrigger(hours=6),
    id="sync_portfolios",
    name="Sync User Portfolios",
    replace_existing=True,
)
```

## Service Placeholders

The following service modules have been created with placeholder implementations:

### `app/services/data/price_service.py`
- `update_prices_for_watched_stocks()` - Update prices for tracked stocks

### `app/services/data/fundamentals_service.py`
- `refresh_all_fundamentals()` - Refresh fundamentals data

### `app/services/news/news_service.py`
- `fetch_latest_news_for_all_stocks()` - Fetch latest news

### `app/services/maintenance.py`
- `cleanup_old_sessions()` - Clean up old session data
- `cleanup_old_logs()` - Clean up old log data

### `app/services/analytics.py`
- `update_hourly_usage_stats()` - Update usage statistics

### `app/services/ai/sentiment_service.py`
- `analyze_unprocessed_news()` - Analyze news sentiment

## TODO: Implementation Tasks

To complete the background jobs system, implement the following:

1. **Price Service** (`app/services/data/price_service.py`)
   - [ ] Get all tickers from portfolios and watch lists
   - [ ] Fetch current prices from price provider
   - [ ] Update price_history table
   - [ ] Handle rate limiting and errors

2. **Fundamentals Service** (`app/services/data/fundamentals_service.py`)
   - [ ] Get all tickers from portfolios
   - [ ] Fetch fundamentals from fundamentals provider
   - [ ] Update stocks table with latest data
   - [ ] Handle missing data and errors

3. **News Service** (`app/services/news/news_service.py`)
   - [ ] Get all tickers from portfolios
   - [ ] Fetch latest news from news provider
   - [ ] Store in news_articles table
   - [ ] Deduplicate articles

4. **Maintenance Service** (`app/services/maintenance.py`)
   - [ ] Implement session cleanup (older than 30 days)
   - [ ] Implement log cleanup (older than 90 days)
   - [ ] Add other cleanup tasks as needed

5. **Analytics Service** (`app/services/analytics.py`)
   - [ ] Track API calls per user
   - [ ] Track feature usage
   - [ ] Generate usage reports

6. **Sentiment Service** (`app/services/ai/sentiment_service.py`)
   - [ ] Get news articles without sentiment
   - [ ] Call AI service for analysis
   - [ ] Update articles with sentiment scores

## Monitoring and Debugging

### View Scheduled Jobs

```bash
curl -X GET http://localhost:8000/api/v1/jobs/list \
  -H "Authorization: Bearer <token>"
```

### Trigger Job Manually

```bash
curl -X POST http://localhost:8000/api/v1/jobs/trigger/update_stock_prices \
  -H "Authorization: Bearer <admin_token>"
```

### Check Application Logs

Background job activity is logged to the application logger:

```
INFO:app.tasks.scheduler:Starting stock price update job
INFO:app.tasks.scheduler:Updated prices for 25 stocks
```

### Common Issues

**Job not running:**
- Check if scheduler is running: `GET /api/v1/jobs/status`
- Check application logs for startup errors
- Verify cron schedule is correct for your timezone

**Job failing silently:**
- Check application logs for errors
- Verify database connections are working
- Ensure external API credentials are valid

**Jobs running too slowly:**
- Consider reducing job frequency
- Add database indexes for better performance
- Implement batching for large datasets

## Configuration

### Environment Variables

No additional environment variables are required for basic scheduler operation.

For advanced configuration, you can add to `app/core/config.py`:

```python
# Scheduler settings
SCHEDULER_ENABLED: bool = True
SCHEDULER_TIMEZONE: str = "UTC"
SCHEDULER_MAX_INSTANCES: int = 1
```

### Customizing Job Schedules

To customize job schedules, modify the trigger settings in `_register_scheduled_jobs()` in `app/tasks/scheduler.py`.

For example, to change price updates to every 10 minutes:

```python
scheduler.add_job(
    update_stock_prices,
    trigger=CronTrigger(
        day_of_week="mon-fri",
        hour="9-16",
        minute="*/10",  # Changed from */5 to */10
    ),
    id="update_stock_prices",
    name="Update Stock Prices",
    replace_existing=True,
)
```

## Testing

### Test Job Functions

```python
import pytest
from app.tasks.scheduler import update_stock_prices

@pytest.mark.asyncio
async def test_update_stock_prices():
    """Test the stock price update job."""
    await update_stock_prices()
    # Add assertions
```

### Test Scheduler Integration

```python
from app.tasks.scheduler import start_scheduler, stop_scheduler, get_scheduler

@pytest.mark.asyncio
async def test_scheduler_lifecycle():
    """Test scheduler start/stop."""
    scheduler = await start_scheduler()
    assert scheduler is not None
    assert scheduler.running

    await stop_scheduler()
    assert get_scheduler() is None
```

## Future Enhancements

- [ ] Add job execution history tracking
- [ ] Implement job priorities
- [ ] Add job execution time monitoring
- [ ] Support for distributed job execution (Celery/RQ)
- [ ] Webhook notifications on job failures
- [ ] Dynamic job scheduling via API
- [ ] Job dependency management
- [ ] Retry logic for failed jobs
