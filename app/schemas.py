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

    # User info
    user_id: str
    user_name: str
    ip: str
    country: str
    user_agent: str

    # Stream details
    proto: str
    bytes: int
    token: str
    source_id: str
    query_string: str

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