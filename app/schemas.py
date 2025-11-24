# app/schemas.py

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class StreamEvent(BaseModel):
    """Incoming event from streaming server"""

    # Event identification
    time: datetime
    event: Literal["play_started", "play_closed"]
    id: str  # Session UUID

    # Source
    server: str
    media: str  # Channel name

    # User info (optional - may not be present)
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    ip: Optional[str] = None
    country: Optional[str] = "XX"
    user_agent: Optional[str] = ""

    # Stream details (optional)
    proto: Optional[str] = "unknown"
    bytes: int = 0
    token: Optional[str] = None
    source_id: Optional[str] = None
    query_string: Optional[str] = None

    # Timing
    opened_at: int  # Unix ms

    # play_closed only
    closed_at: Optional[int] = None  # Unix ms
    reason: Optional[str] = None

    # Erlang internals (captured but not used)
    pid: Optional[str] = None
    module: Optional[str] = None
    line: Optional[int] = None

    class Config:
        extra = "ignore"  # Ignore unexpected fields


class WebhookResponse(BaseModel):
    status: str
    processed: int
    errors: int = 0