"""Server-Sent Events endpoint for real-time push."""

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.auth import get_current_user
from app.models import UserMapping
from app.services.sse_broker import broker, sse_event_stream

logger = logging.getLogger("sse")
router = APIRouter(prefix="/api/v1/events", tags=["sse"])


@router.get("/stream")
async def event_stream(
    current_user: UserMapping = Depends(get_current_user),
):
    """SSE stream of real-time events for the authenticated user."""
    q = broker.subscribe(current_user.hub_user_id)
    return StreamingResponse(
        sse_event_stream(current_user.hub_user_id, q),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
