# app/aggregator.py

from datetime import datetime, timedelta
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.dialects.mysql import insert
from app.database import SessionLocal
from app.sessions import sessions_manager
from app.models import (
    ActiveSession,
    StatsGlobal,
    StatsByServer,
    StatsByChannel,
    StatsByCountry,
    StatsByProtocol,
    StatsByUserAgent,
)
import logging

logger = logging.getLogger(__name__)


def get_minute_timestamp() -> datetime:
    """Get current time truncated to the minute"""
    now = datetime.utcnow()
    return now.replace(second=0, microsecond=0)


def run_aggregation() -> None:
    """
    Called every minute by scheduler.
    Collects stats and writes to database.
    """
    minute = get_minute_timestamp() - timedelta(minutes=1)  # Stats for previous minute

    try:
        stats = sessions_manager.get_and_reset_minute_stats()

        db = SessionLocal()
        try:
            # Write global stats
            write_global_stats(db, minute, stats["global"])

            # Write dimension stats
            write_dimension_stats(db, minute, StatsByServer, "server", stats["by_server"])
            write_dimension_stats(db, minute, StatsByChannel, "channel", stats["by_channel"])
            write_dimension_stats(db, minute, StatsByCountry, "country", stats["by_country"])
            write_dimension_stats(db, minute, StatsByProtocol, "protocol", stats["by_protocol"])
            write_dimension_stats(db, minute, StatsByUserAgent, "user_agent_class", stats["by_user_agent"])

            db.commit()
            logger.info(f"Aggregation complete for {minute}: {stats['global']['sessions_started']} started, {stats['global']['sessions_closed']} closed, {stats['global']['current_concurrent']} active")

        except Exception as e:
            db.rollback()
            logger.error(f"Aggregation failed: {e}")
            raise
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Aggregation error: {e}")


def write_global_stats(db: DBSession, minute: datetime, stats: dict) -> None:
    """Write global stats row"""
    bandwidth_bps = stats["total_bytes"] // 60 if stats["total_bytes"] else 0

    stmt = insert(StatsGlobal).values(
        minute=minute,
        sessions_started=stats["sessions_started"],
        sessions_closed=stats["sessions_closed"],
        total_bytes=stats["total_bytes"],
        bandwidth_bps=bandwidth_bps,
        watch_time_seconds=stats["watch_time_seconds"],
        unique_users=stats["unique_users"],
        peak_concurrent=stats["peak_concurrent"],
    )

    # Update if already exists (idempotent)
    stmt = stmt.on_duplicate_key_update(
        sessions_started=stmt.inserted.sessions_started,
        sessions_closed=stmt.inserted.sessions_closed,
        total_bytes=stmt.inserted.total_bytes,
        bandwidth_bps=stmt.inserted.bandwidth_bps,
        watch_time_seconds=stmt.inserted.watch_time_seconds,
        unique_users=stmt.inserted.unique_users,
        peak_concurrent=stmt.inserted.peak_concurrent,
    )

    db.execute(stmt)


def write_dimension_stats(db: DBSession, minute: datetime, model, dimension_column: str, stats_by_dimension: dict) -> None:
    """Write stats for a dimension (server, channel, country, etc.)"""

    for dimension_value, stats in stats_by_dimension.items():
        bandwidth_bps = stats["total_bytes"] // 60 if stats["total_bytes"] else 0

        values = {
            "minute": minute,
            dimension_column: dimension_value,
            "sessions_started": stats["sessions_started"],
            "sessions_closed": stats["sessions_closed"],
            "total_bytes": stats["total_bytes"],
            "bandwidth_bps": bandwidth_bps,
            "watch_time_seconds": stats["watch_time_seconds"],
            "unique_users": stats["unique_users"],
            "peak_concurrent": stats["peak_concurrent"],
        }

        stmt = insert(model).values(**values)

        stmt = stmt.on_duplicate_key_update(
            sessions_started=stmt.inserted.sessions_started,
            sessions_closed=stmt.inserted.sessions_closed,
            total_bytes=stmt.inserted.total_bytes,
            bandwidth_bps=stmt.inserted.bandwidth_bps,
            watch_time_seconds=stmt.inserted.watch_time_seconds,
            unique_users=stmt.inserted.unique_users,
            peak_concurrent=stmt.inserted.peak_concurrent,
        )

        db.execute(stmt)


def sync_active_sessions() -> None:
    """
    Persist active sessions to database.
    Called periodically for crash recovery.
    """
    sessions = sessions_manager.get_all_sessions()

    db = SessionLocal()
    try:
        # Clear old sessions and write current
        db.query(ActiveSession).delete()

        for session in sessions:
            db.add(ActiveSession(
                id=session.id,
                server=session.server,
                media=session.media,
                user_id=session.user_id,
                country=session.country,
                proto=session.proto,
                user_agent_class=session.user_agent_class,
                bytes=session.bytes,
                opened_at=session.opened_at,
                updated_at=datetime.utcnow(),
            ))

        db.commit()
        logger.debug(f"Synced {len(sessions)} active sessions to database")

    except Exception as e:
        db.rollback()
        logger.error(f"Session sync failed: {e}")
    finally:
        db.close()


def restore_active_sessions() -> None:
    """
    Load active sessions from database on startup.
    """
    db = SessionLocal()
    try:
        rows = db.query(ActiveSession).all()

        from app.sessions import Session
        sessions = [
            Session(
                id=row.id,
                server=row.server,
                media=row.media,
                user_id=row.user_id,
                country=row.country,
                proto=row.proto,
                user_agent_class=row.user_agent_class,
                bytes=row.bytes,
                opened_at=row.opened_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]

        sessions_manager.restore_sessions(sessions)
        logger.info(f"Restored {len(sessions)} active sessions from database")

    except Exception as e:
        logger.error(f"Session restore failed: {e}")
    finally:
        db.close()