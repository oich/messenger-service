"""Cross-App Notification API.

Other satellites call this endpoint with a service token to send
notifications into Matrix rooms.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import verify_service_token as _verify_service_token
from app.database import get_db
from app.models import NotificationLog, UserMapping
from app.schemas.notifications import NotificationSend, NotificationOut
from app.services.notification_router import route_notification
from app.services.push_notifier import push_to_room_members
from app.services.sse_broker import broker

logger = logging.getLogger("notifications")
router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


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

    try:
        bot_token = bot.get_matrix_access_token()
    except ValueError as e:
        logger.error("Failed to decrypt bot token: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Notification bot token decryption failed. Re-provision the bot.",
        )

    try:
        log_entry = await route_notification(
            notification=notification,
            bot_token=bot_token,
            db=db,
        )
    except Exception as e:
        logger.exception("Failed to route notification")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to route notification: {str(e)[:200]}",
        )

    # Push to SSE subscribers. A DM is only relevant to its one recipient -
    # broadcasting it to every connected user made every other logged-in
    # user's notification bell show a "notification" entry for DMs that
    # weren't theirs (clicking it either opened someone else's private room
    # or did nothing, since they aren't a member of it).
    try:
        event_data = {
            "type": "notification",
            "source_app": notification.source_app,
            "event_type": notification.event_type,
            "title": notification.title,
            "body": notification.body,
            "priority": notification.priority,
            "room_id": log_entry.matrix_room_id,
        }
        if notification.target_type == "dm" and notification.target_user:
            await broker.publish_to_user(notification.target_user, event_data)
        else:
            await broker.broadcast(event_data)
    except Exception as e:
        logger.warning("SSE broadcast failed (non-fatal): %s", e)

    if log_entry.matrix_room_id:
        try:
            await push_to_room_members(
                log_entry.matrix_room_id, bot_token,
                notification.title, notification.body or "", db,
            )
        except Exception as e:
            logger.warning("FCM push failed (non-fatal): %s", e)

    return NotificationOut.model_validate(log_entry)


@router.get("/log", response_model=list[NotificationOut])
async def get_notification_log(
    db: Session = Depends(get_db),
    _token: str = Depends(_verify_service_token),
    source_app: Optional[str] = Query(None, description="Filter by source app"),
    limit: int = Query(100, ge=1, le=500, description="Max number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """Get notification log entries.

    Requires X-Service-Token header matching MESSENGER_SERVICE_TOKEN.
    Returns notification history filtered by source_app if provided.
    """
    query = db.query(NotificationLog).order_by(NotificationLog.created_at.desc())

    if source_app:
        query = query.filter(NotificationLog.source_app == source_app)

    logs = query.offset(offset).limit(limit).all()
    return [NotificationOut.model_validate(log) for log in logs]
