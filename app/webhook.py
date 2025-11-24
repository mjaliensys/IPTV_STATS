# app/webhook.py

from fastapi import APIRouter, Request
from typing import List, Union
from app.schemas import StreamEvent, WebhookResponse
from app.sessions import sessions_manager
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/api/webhook", response_model=WebhookResponse)
async def receive_webhook(request: Request) -> WebhookResponse:
    """
    Receive streaming events from servers.
    Accepts single event or array of events.
    """
    body = await request.json()

    # Normalize to list
    if isinstance(body, dict):
        events = [body]
    elif isinstance(body, list):
        events = body
    else:
        return WebhookResponse(status="error", processed=0, errors=1)

    processed = 0
    errors = 0

    for event_data in events:
        try:
            # Validate event
            event = StreamEvent(**event_data)

            # Route to appropriate handler
            if event.event == "play_started":
                sessions_manager.session_started(event_data)
            elif event.event == "play_closed":
                sessions_manager.session_closed(event_data)

            processed += 1

        except Exception as e:
            errors += 1
            logger.warning(f"Failed to process event: {e}")

    return WebhookResponse(
        status="ok" if errors == 0 else "partial",
        processed=processed,
        errors=errors,
    )


@router.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {"status": "healthy"}


@router.get("/stats/active")
async def active_sessions_count():
    """Quick endpoint to check current active sessions"""
    sessions = sessions_manager.get_all_sessions()
    return {
        "active_sessions": len(sessions),
        "by_server": count_by_attribute(sessions, "server"),
        "by_channel": count_by_attribute(sessions, "media"),
    }


def count_by_attribute(sessions: list, attr: str) -> dict:
    """Helper to count sessions by attribute"""
    counts = {}
    for session in sessions:
        key = getattr(session, attr)
        counts[key] = counts.get(key, 0) + 1
    return counts