# app/models.py

from sqlalchemy import (
    Column, String, Integer, BigInteger, DateTime, Index
)
from app.database import Base


class ActiveSession(Base):
    """In-memory primary, DB for persistence/recovery"""
    __tablename__ = "active_sessions"

    id = Column(String(36), primary_key=True)  # UUID from event
    server = Column(String(100), nullable=False)
    media = Column(String(100), nullable=False)
    user_id = Column(String(100), nullable=False)
    country = Column(String(10), nullable=False)
    proto = Column(String(20), nullable=False)
    user_agent_class = Column(String(20), nullable=False)
    bytes = Column(BigInteger, default=0)
    opened_at = Column(BigInteger, nullable=False)  # Unix ms
    updated_at = Column(DateTime, nullable=False)


class StatsGlobal(Base):
    """Global per-minute aggregates"""
    __tablename__ = "stats_global"

    minute = Column(DateTime, primary_key=True)
    sessions_started = Column(Integer, default=0)
    sessions_closed = Column(Integer, default=0)
    total_bytes = Column(BigInteger, default=0)
    bandwidth_bps = Column(BigInteger, default=0)
    watch_time_seconds = Column(BigInteger, default=0)
    unique_users = Column(Integer, default=0)
    peak_concurrent = Column(Integer, default=0)


class StatsByServer(Base):
    __tablename__ = "stats_by_server"

    minute = Column(DateTime, primary_key=True)
    server = Column(String(100), primary_key=True)
    sessions_started = Column(Integer, default=0)
    sessions_closed = Column(Integer, default=0)
    total_bytes = Column(BigInteger, default=0)
    bandwidth_bps = Column(BigInteger, default=0)
    watch_time_seconds = Column(BigInteger, default=0)
    unique_users = Column(Integer, default=0)
    peak_concurrent = Column(Integer, default=0)


class StatsByChannel(Base):
    __tablename__ = "stats_by_channel"

    minute = Column(DateTime, primary_key=True)
    channel = Column(String(100), primary_key=True)
    sessions_started = Column(Integer, default=0)
    sessions_closed = Column(Integer, default=0)
    total_bytes = Column(BigInteger, default=0)
    bandwidth_bps = Column(BigInteger, default=0)
    watch_time_seconds = Column(BigInteger, default=0)
    unique_users = Column(Integer, default=0)
    peak_concurrent = Column(Integer, default=0)


class StatsByCountry(Base):
    __tablename__ = "stats_by_country"

    minute = Column(DateTime, primary_key=True)
    country = Column(String(10), primary_key=True)
    sessions_started = Column(Integer, default=0)
    sessions_closed = Column(Integer, default=0)
    total_bytes = Column(BigInteger, default=0)
    bandwidth_bps = Column(BigInteger, default=0)
    watch_time_seconds = Column(BigInteger, default=0)
    unique_users = Column(Integer, default=0)
    peak_concurrent = Column(Integer, default=0)


class StatsByProtocol(Base):
    __tablename__ = "stats_by_protocol"

    minute = Column(DateTime, primary_key=True)
    protocol = Column(String(20), primary_key=True)
    sessions_started = Column(Integer, default=0)
    sessions_closed = Column(Integer, default=0)
    total_bytes = Column(BigInteger, default=0)
    bandwidth_bps = Column(BigInteger, default=0)
    watch_time_seconds = Column(BigInteger, default=0)
    unique_users = Column(Integer, default=0)
    peak_concurrent = Column(Integer, default=0)


class StatsByUserAgent(Base):
    __tablename__ = "stats_by_user_agent"

    minute = Column(DateTime, primary_key=True)
    user_agent_class = Column(String(20), primary_key=True)
    sessions_started = Column(Integer, default=0)
    sessions_closed = Column(Integer, default=0)
    total_bytes = Column(BigInteger, default=0)
    bandwidth_bps = Column(BigInteger, default=0)
    watch_time_seconds = Column(BigInteger, default=0)
    unique_users = Column(Integer, default=0)
    peak_concurrent = Column(Integer, default=0)