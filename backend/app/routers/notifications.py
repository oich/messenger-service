"""Cross-App Notification API.

Other satellites call this endpoint with a service token to send
notifications into Matrix rooms.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session

from app.config import MESSENGER_SERVICE_TOKEN
from app.database import get_db
from app.models import UserMapping
from app.schemas.notifications import NotificationSend, NotificationOut
from app.services.notification_router import route_notification
from app.services.sse_broker import broker

logger = logging.getLogger("notifications")
router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


def _verify_service_token(x_service_token: str = Header(...)) -> str:
    """Verify the cross-app service token."""
    if x_service_token != MESSENGER_SERVICE_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid service token",
        )
    return x_service_token


@router.post("/send", response_model=NotificationOut)
async def send_notification(
    notification: NotificationSend,
    db: Session = Depends(get_db),
    _token: str = Depends(_verify_service_token),
):
    """Send a cross-app notification.

    Requires X-Service-Token header matching MESSENGER_SERVICE_TOKEN.
    Routes the notification to the appropriate Matrix room via a bot user.
    """
    # Get or create bot user token
    bot = (
        db.query(UserMapping)
        .filter(UserMapping.hub_user_id == "notification_bot", UserMapping.is_bot == True)
        .first()
    )

    if not bot or not bot.matrix_access_token_encrypted:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Notification bot not provisioned. Run startup provisioning first.",
        )

    log_entry = await route_notification(
        notification=notification,
        bot_token=bot.matrix_access_token_encrypted,
        db=db,
    )

    # Broadcast to SSE subscribers
    await broker.broadcast({
        "type": "notification",
        "source_app": notification.source_app,
        "event_type": notification.event_type,
        "title": notification.title,
        "body": notification.body,
        "priority": notification.priority,
        "room_id": log_entry.matrix_room_id,
    })

    return NotificationOut.model_validate(log_entry)
