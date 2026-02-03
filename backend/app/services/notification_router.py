"""Route cross-app notifications to Matrix rooms."""

import logging

from sqlalchemy.orm import Session

from app.models import NotificationLog, NotificationStatus, RoomMapping, RoomType, UserMapping
from app.schemas.notifications import NotificationSend
from app.services.matrix_client import matrix_client, MatrixClientError
from app.services.room_manager import get_or_create_entity_room, get_or_create_general_room, get_or_create_service_room

logger = logging.getLogger("notification_router")


async def route_notification(
    notification: NotificationSend,
    bot_token: str,
    db: Session,
) -> NotificationLog:
    """Route a notification to the appropriate Matrix room and log it."""
    log_entry = NotificationLog(
        source_app=notification.source_app,
        event_type=notification.event_type,
        title=notification.title,
        body=notification.body,
        target_type=notification.target_type,
        entity_type=notification.entity_type,
        entity_id=notification.entity_id,
        priority=notification.priority,
        status=NotificationStatus.pending,
    )
    db.add(log_entry)
    db.flush()

    try:
        room_mapping = await _resolve_target_room(notification, bot_token, db)
        if not room_mapping:
            log_entry.status = NotificationStatus.failed
            log_entry.error_message = "Could not resolve target room"
            db.commit()
            return log_entry

        log_entry.matrix_room_id = room_mapping.matrix_room_id

        # Format message
        priority_prefix = "🔴 " if notification.priority == "urgent" else ""
        formatted_body = (
            f"{priority_prefix}**[{notification.source_app}]** {notification.title}"
        )
        if notification.body:
            formatted_body += f"\n\n{notification.body}"

        event_id = await matrix_client.send_message(
            access_token=bot_token,
            room_id=room_mapping.matrix_room_id,
            body=formatted_body,
            msg_type="m.text",
        )

        log_entry.matrix_event_id = event_id
        log_entry.status = NotificationStatus.sent

    except MatrixClientError as e:
        logger.error("Failed to send notification: %s", e)
        log_entry.status = NotificationStatus.failed
        log_entry.error_message = str(e)
    except Exception as e:
        logger.exception("Unexpected error routing notification")
        log_entry.status = NotificationStatus.failed
        log_entry.error_message = str(e)

    db.commit()
    db.refresh(log_entry)
    return log_entry


SERVICE_DISPLAY_NAMES = {
    "machine-monitoring": "Maschinenüberwachung",
}


async def _resolve_target_room(
    notification: NotificationSend,
    bot_token: str,
    db: Session,
) -> RoomMapping | None:
    """Determine which Matrix room should receive the notification."""
    if notification.target_type == "service_room":
        service_name = notification.source_app
        display_name = SERVICE_DISPLAY_NAMES.get(service_name, service_name)
        return await get_or_create_service_room(
            service_name=service_name,
            display_name=display_name,
            admin_token=bot_token,
            db=db,
        )

    if notification.target_type == "entity_room" and notification.entity_type and notification.entity_id:
        display_name = f"{notification.entity_type} #{notification.entity_id}"
        return await get_or_create_entity_room(
            entity_type=notification.entity_type,
            entity_id=notification.entity_id,
            display_name=display_name,
            admin_token=bot_token,
            db=db,
        )

    if notification.target_type == "dm" and notification.target_user:
        # Find the user's DM room or a room they're in
        user_mapping = (
            db.query(UserMapping)
            .filter(UserMapping.hub_user_id == notification.target_user)
            .first()
        )
        if user_mapping:
            # Find existing DM room
            dm_room = (
                db.query(RoomMapping)
                .filter(
                    RoomMapping.room_type == RoomType.dm,
                    RoomMapping.display_name.contains(user_mapping.matrix_user_id),
                )
                .first()
            )
            if dm_room:
                return dm_room

    # Default: general room (tenant_id=1 as default)
    return await get_or_create_general_room(
        tenant_id=1,
        admin_token=bot_token,
        db=db,
    )
