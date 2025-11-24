# app/main.py

from contextlib import asynccontextmanager
from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler
from app.config import settings
from app.database import init_db
from app.webhook import router as webhook_router
from app.aggregator import run_aggregation, sync_active_sessions, restore_active_sessions
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Scheduler instance
scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""

    # Startup
    logger.info("Starting Stream Stats API...")

    # Initialize database tables
    init_db()
    logger.info("Database initialized")

    # Restore active sessions from DB
    restore_active_sessions()

    # Schedule aggregation job (every minute at :00)
    scheduler.add_job(
        run_aggregation,
        trigger="cron",
        second=0,
        id="aggregation",
        replace_existing=True,
    )

    # Schedule session sync job (every N seconds)
    scheduler.add_job(
        sync_active_sessions,
        trigger="interval",
        seconds=settings.session_sync_interval_seconds,
        id="session_sync",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started")

    logger.info(f"Stream Stats API ready - listening for webhooks")

    yield

    # Shutdown
    logger.info("Shutting down...")

    scheduler.shutdown(wait=True)
    logger.info("Scheduler stopped")

    # Final session sync before exit
    sync_active_sessions()
    logger.info("Final session sync complete")


app = FastAPI(
    title="Stream Stats API",
    description="Receives streaming events and aggregates statistics",
    version="1.0.0",
    lifespan=lifespan,
)

# Register routes
app.include_router(webhook_router)