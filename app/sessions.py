# app/sessions.py

from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from typing import Dict, Set
from app.classifier import classify_user_agent_cached


@dataclass
class Session:
    """Single active session"""
    id: str
    server: str
    media: str
    user_id: str
    country: str
    proto: str
    user_agent_class: str
    bytes: int
    opened_at: int  # Unix ms
    updated_at: datetime = field(default_factory=datetime.utcnow)


class ActiveSessionsManager:
    """
    In-memory active sessions tracking.
    Thread-safe for concurrent webhook requests.
    """

    def __init__(self):
        self._sessions: Dict[str, Session] = {}
        self._lock = Lock()

        # Per-minute tracking (reset each aggregation cycle)
        self._minute_started: int = 0
        self._minute_closed: int = 0
        self._minute_bytes: int = 0
        self._minute_watch_time_ms: int = 0
        self._minute_unique_users: Set[str] = set()
        self._minute_peak_concurrent: int = 0

        # Dimension-specific tracking for current minute
        self._minute_by_server: Dict[str, DimensionStats] = {}
        self._minute_by_channel: Dict[str, DimensionStats] = {}
        self._minute_by_country: Dict[str, DimensionStats] = {}
        self._minute_by_protocol: Dict[str, DimensionStats] = {}
        self._minute_by_user_agent: Dict[str, DimensionStats] = {}

    def session_started(self, event_data: dict) -> None:
        """Handle play_started event"""
        user_agent_class = classify_user_agent_cached(event_data.get("user_agent", ""))

        session = Session(
            id=event_data["id"],
            server=event_data["server"],
            media=event_data["media"],
            user_id=event_data.get("user_id") or event_data["id"],
            country=event_data.get("country") or "XX",
            proto=event_data.get("proto") or "unknown",
            user_agent_class=user_agent_class,
            bytes=event_data.get("bytes", 0),
            opened_at=event_data["opened_at"],
        )

        with self._lock:
            self._sessions[session.id] = session

            # Update minute counters
            self._minute_started += 1
            self._minute_unique_users.add(session.user_id)

            # Track peak concurrent
            current_concurrent = len(self._sessions)
            if current_concurrent > self._minute_peak_concurrent:
                self._minute_peak_concurrent = current_concurrent

            # Update dimension stats
            self._get_dimension_stats(self._minute_by_server, session.server).add_started(session.user_id)
            self._get_dimension_stats(self._minute_by_channel, session.media).add_started(session.user_id)
            self._get_dimension_stats(self._minute_by_country, session.country).add_started(session.user_id)
            self._get_dimension_stats(self._minute_by_protocol, session.proto).add_started(session.user_id)
            self._get_dimension_stats(self._minute_by_user_agent, user_agent_class).add_started(session.user_id)

    def session_closed(self, event_data: dict) -> None:
        """Handle play_closed event"""
        session_id = event_data["id"]

        with self._lock:
            session = self._sessions.pop(session_id, None)

            if session:
                # Calculate watch time and bytes for this session
                closed_at = event_data.get("closed_at", 0)
                watch_time_ms = closed_at - session.opened_at if closed_at else 0
                final_bytes = event_data.get("bytes", 0)
                bytes_delta = final_bytes - session.bytes

                # Update minute counters
                self._minute_closed += 1
                self._minute_bytes += bytes_delta
                self._minute_watch_time_ms += watch_time_ms
                self._minute_unique_users.add(session.user_id)

                # Update dimension stats
                self._get_dimension_stats(self._minute_by_server, session.server).add_closed(session.user_id, bytes_delta, watch_time_ms)
                self._get_dimension_stats(self._minute_by_channel, session.media).add_closed(session.user_id, bytes_delta, watch_time_ms)
                self._get_dimension_stats(self._minute_by_country, session.country).add_closed(session.user_id, bytes_delta, watch_time_ms)
                self._get_dimension_stats(self._minute_by_protocol, session.proto).add_closed(session.user_id, bytes_delta, watch_time_ms)
                self._get_dimension_stats(self._minute_by_user_agent, session.user_agent_class).add_closed(session.user_id, bytes_delta, watch_time_ms)
            else:
                # Session not found - still count the close event
                user_agent_class = classify_user_agent_cached(event_data.get("user_agent", ""))
                user_id = event_data.get("user_id") or event_data["id"]
                country = event_data.get("country") or "XX"
                proto = event_data.get("proto") or "unknown"

                self._minute_closed += 1
                self._minute_bytes += event_data.get("bytes", 0)
                self._minute_unique_users.add(user_id)

                # Update dimension stats
                self._get_dimension_stats(self._minute_by_server, event_data["server"]).add_closed(user_id, event_data.get("bytes", 0), 0)
                self._get_dimension_stats(self._minute_by_channel, event_data["media"]).add_closed(user_id, event_data.get("bytes", 0), 0)
                self._get_dimension_stats(self._minute_by_country, country).add_closed(user_id, event_data.get("bytes", 0), 0)
                self._get_dimension_stats(self._minute_by_protocol, proto).add_closed(user_id, event_data.get("bytes", 0), 0)
                self._get_dimension_stats(self._minute_by_user_agent, user_agent_class).add_closed(user_id, event_data.get("bytes", 0), 0)

    def get_and_reset_minute_stats(self) -> dict:
        """
        Get all stats for the current minute and reset counters.
        Called by aggregator every minute.
        """
        with self._lock:
            # Snapshot current concurrent counts by dimension
            concurrent_by_server: Dict[str, int] = {}
            concurrent_by_channel: Dict[str, int] = {}
            concurrent_by_country: Dict[str, int] = {}
            concurrent_by_protocol: Dict[str, int] = {}
            concurrent_by_user_agent: Dict[str, int] = {}

            for session in self._sessions.values():
                concurrent_by_server[session.server] = concurrent_by_server.get(session.server, 0) + 1
                concurrent_by_channel[session.media] = concurrent_by_channel.get(session.media, 0) + 1
                concurrent_by_country[session.country] = concurrent_by_country.get(session.country, 0) + 1
                concurrent_by_protocol[session.proto] = concurrent_by_protocol.get(session.proto, 0) + 1
                concurrent_by_user_agent[session.user_agent_class] = concurrent_by_user_agent.get(session.user_agent_class, 0) + 1

            stats = {
                "global": {
                    "sessions_started": self._minute_started,
                    "sessions_closed": self._minute_closed,
                    "total_bytes": self._minute_bytes,
                    "watch_time_seconds": self._minute_watch_time_ms // 1000,
                    "unique_users": len(self._minute_unique_users),
                    "peak_concurrent": self._minute_peak_concurrent,
                    "current_concurrent": len(self._sessions),
                },
                "by_server": self._finalize_dimension_stats(self._minute_by_server, concurrent_by_server),
                "by_channel": self._finalize_dimension_stats(self._minute_by_channel, concurrent_by_channel),
                "by_country": self._finalize_dimension_stats(self._minute_by_country, concurrent_by_country),
                "by_protocol": self._finalize_dimension_stats(self._minute_by_protocol, concurrent_by_protocol),
                "by_user_agent": self._finalize_dimension_stats(self._minute_by_user_agent, concurrent_by_user_agent),
            }

            # Reset minute counters
            self._minute_started = 0
            self._minute_closed = 0
            self._minute_bytes = 0
            self._minute_watch_time_ms = 0
            self._minute_unique_users.clear()
            self._minute_peak_concurrent = len(self._sessions)  # Start with current
            self._minute_by_server.clear()
            self._minute_by_channel.clear()
            self._minute_by_country.clear()
            self._minute_by_protocol.clear()
            self._minute_by_user_agent.clear()

            return stats

    def get_all_sessions(self) -> list[Session]:
        """Get all active sessions for DB persistence"""
        with self._lock:
            return list(self._sessions.values())

    def restore_sessions(self, sessions: list[Session]) -> None:
        """Restore sessions from DB on startup"""
        with self._lock:
            for session in sessions:
                self._sessions[session.id] = session
            self._minute_peak_concurrent = len(self._sessions)

    def _get_dimension_stats(self, dimension_dict: dict, key: str) -> "DimensionStats":
        if key not in dimension_dict:
            dimension_dict[key] = DimensionStats()
        return dimension_dict[key]

    def _finalize_dimension_stats(self, dimension_dict: Dict[str, "DimensionStats"], concurrent: Dict[str, int]) -> dict:
        result = {}
        all_keys = set(dimension_dict.keys()) | set(concurrent.keys())
        for key in all_keys:
            stats = dimension_dict.get(key, DimensionStats())
            result[key] = {
                "sessions_started": stats.started,
                "sessions_closed": stats.closed,
                "total_bytes": stats.bytes,
                "watch_time_seconds": stats.watch_time_ms // 1000,
                "unique_users": len(stats.unique_users),
                "peak_concurrent": max(stats.peak_concurrent, concurrent.get(key, 0)),
            }
        return result


class DimensionStats:
    """Stats accumulator for a single dimension value"""

    def __init__(self):
        self.started: int = 0
        self.closed: int = 0
        self.bytes: int = 0
        self.watch_time_ms: int = 0
        self.unique_users: Set[str] = set()
        self.peak_concurrent: int = 0

    def add_started(self, user_id: str) -> None:
        self.started += 1
        self.unique_users.add(user_id)

    def add_closed(self, user_id: str, bytes_delta: int, watch_time_ms: int) -> None:
        self.closed += 1
        self.bytes += bytes_delta
        self.watch_time_ms += watch_time_ms
        self.unique_users.add(user_id)


# Global singleton
sessions_manager = ActiveSessionsManager()