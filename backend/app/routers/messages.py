"""Message send/receive/history endpoints."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import UserMapping
from app.schemas.messages import MessageSend, MessageOut, MessageHistory
from app.services.matrix_client import matrix_client, MatrixClientError
from app.services.sse_broker import broker

logger = logging.getLogger("messages")
router = APIRouter(prefix="/api/v1/messages", tags=["messages"])


@router.post("/send", response_model=MessageOut)
async def send_message(
    msg: MessageSend,
    current_user: UserMapping = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Send a message to a room."""
    if not current_user.matrix_access_token_encrypted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not provisioned on Matrix",
        )

    try:
        event_id = await matrix_client.send_message(
            access_token=current_user.matrix_access_token_encrypted,
            room_id=msg.room_id,
            body=msg.body,
            msg_type=msg.msg_type,
        )
    except MatrixClientError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to send message: {e}",
        )

    message_out = MessageOut(
        event_id=event_id,
        room_id=msg.room_id,
        sender=current_user.matrix_user_id,
        sender_display_name=current_user.display_name,
        body=msg.body,
        msg_type=msg.msg_type,
        timestamp=datetime.now(timezone.utc),
    )

    # Notify SSE subscribers
    await broker.broadcast({
        "type": "new_message",
        "room_id": msg.room_id,
        "event_id": event_id,
        "sender": current_user.matrix_user_id,
        "sender_display_name": current_user.display_name,
        "body": msg.body,
    })

    return message_out


@router.get("/history/{room_id}", response_model=MessageHistory)
async def get_history(
    room_id: str,
    limit: int = Query(50, ge=1, le=200),
    from_token: str = Query(None),
    current_user: UserMapping = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get message history for a room."""
    if not current_user.matrix_access_token_encrypted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not provisioned on Matrix",
        )

    try:
        result = await matrix_client.get_room_messages(
            access_token=current_user.matrix_access_token_encrypted,
            room_id=room_id,
            limit=limit,
            from_token=from_token,
        )
    except MatrixClientError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to get messages: {e}",
        )

    messages = []
    for event in result.get("chunk", []):
        if event.get("type") != "m.room.message":
            continue
        content = event.get("content", {})
        messages.append(
            MessageOut(
                event_id=event["event_id"],
                room_id=room_id,
                sender=event.get("sender", ""),
                sender_display_name=None,
                body=content.get("body", ""),
                msg_type=content.get("msgtype", "m.text"),
                timestamp=datetime.fromtimestamp(
                    event.get("origin_server_ts", 0) / 1000,
                    tz=timezone.utc,
                ),
            )
        )

    return MessageHistory(
        messages=messages,
        end_token=result.get("end"),
        has_more=len(messages) == limit,
    )
