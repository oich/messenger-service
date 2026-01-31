"""Message send/receive/history endpoints."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import MATRIX_HOMESERVER_URL
from app.database import get_db
from app.models import UserMapping, RoomMapping
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

    # Notify room members via SSE
    await _notify_room_members(
        room_id=msg.room_id,
        event_id=event_id,
        sender=current_user.matrix_user_id,
        sender_display_name=current_user.display_name,
        body=msg.body,
        msg_type=msg.msg_type,
        db=db,
    )

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

    # Build a cache of sender matrix_id -> display_name
    sender_ids = set()
    for event in result.get("chunk", []):
        if event.get("type") == "m.room.message":
            sender_ids.add(event.get("sender", ""))
    sender_ids.discard("")

    display_name_map = {}
    if sender_ids:
        user_mappings = (
            db.query(UserMapping)
            .filter(UserMapping.matrix_user_id.in_(list(sender_ids)))
            .all()
        )
        for um in user_mappings:
            display_name_map[um.matrix_user_id] = um.display_name or um.hub_user_id

    messages = []
    for event in result.get("chunk", []):
        if event.get("type") != "m.room.message":
            continue
        content = event.get("content", {})
        file_info = content.get("info", {})
        file_url = content.get("url")
        filename = content.get("filename") or content.get("body", "")
        sender = event.get("sender", "")
        messages.append(
            MessageOut(
                event_id=event["event_id"],
                room_id=room_id,
                sender=sender,
                sender_display_name=display_name_map.get(sender),
                body=content.get("body", ""),
                msg_type=content.get("msgtype", "m.text"),
                timestamp=datetime.fromtimestamp(
                    event.get("origin_server_ts", 0) / 1000,
                    tz=timezone.utc,
                ),
                file_url=file_url,
                filename=filename if file_url else None,
                file_size=file_info.get("size") if file_url else None,
            )
        )

    return MessageHistory(
        messages=messages,
        end_token=result.get("end"),
        has_more=len(messages) == limit,
    )


@router.post("/upload", response_model=MessageOut)
async def upload_file(
    room_id: str = Form(...),
    file: UploadFile = File(...),
    body: str = Form(""),
    current_user: UserMapping = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a file and send it as a message to a room."""
    if not current_user.matrix_access_token_encrypted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not provisioned on Matrix",
        )

    file_data = await file.read()
    content_type = file.content_type or "application/octet-stream"
    filename = file.filename or "file"
    file_size = len(file_data)

    try:
        mxc_uri = await matrix_client.upload_file(
            access_token=current_user.matrix_access_token_encrypted,
            file_data=file_data,
            content_type=content_type,
            filename=filename,
        )
    except MatrixClientError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to upload file: {e}",
        )

    # Determine message type based on content type
    if content_type.startswith("image/"):
        msg_type = "m.image"
    elif content_type.startswith("audio/"):
        msg_type = "m.audio"
    elif content_type.startswith("video/"):
        msg_type = "m.video"
    else:
        msg_type = "m.file"

    event_content = {
        "msgtype": msg_type,
        "body": body or filename,
        "filename": filename,
        "url": mxc_uri,
        "info": {
            "mimetype": content_type,
            "size": file_size,
        },
    }

    try:
        event_id = await matrix_client.send_message_event(
            access_token=current_user.matrix_access_token_encrypted,
            room_id=room_id,
            content=event_content,
        )
    except MatrixClientError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to send file message: {e}",
        )

    message_out = MessageOut(
        event_id=event_id,
        room_id=room_id,
        sender=current_user.matrix_user_id,
        sender_display_name=current_user.display_name,
        body=body or filename,
        msg_type=msg_type,
        timestamp=datetime.now(timezone.utc),
        file_url=mxc_uri,
        filename=filename,
        file_size=file_size,
    )

    await _notify_room_members(
        room_id=room_id,
        event_id=event_id,
        sender=current_user.matrix_user_id,
        sender_display_name=current_user.display_name,
        body=body or filename,
        msg_type=msg_type,
        db=db,
        file_url=mxc_uri,
        filename=filename,
        file_size=file_size,
    )

    return message_out


async def _notify_room_members(
    room_id: str,
    event_id: str,
    sender: str,
    sender_display_name: str | None,
    body: str,
    msg_type: str,
    db: Session,
    file_url: str | None = None,
    filename: str | None = None,
    file_size: int | None = None,
) -> None:
    """Send SSE notification to all members of a room."""
    event_data = {
        "type": "new_message",
        "room_id": room_id,
        "event_id": event_id,
        "sender": sender,
        "sender_display_name": sender_display_name,
        "body": body,
        "msg_type": msg_type,
    }
    if file_url:
        event_data["file_url"] = file_url
        event_data["filename"] = filename
        event_data["file_size"] = file_size

    # Find room members via RoomMapping + UserMapping
    room_mapping = (
        db.query(RoomMapping)
        .filter(RoomMapping.matrix_room_id == room_id)
        .first()
    )
    if not room_mapping:
        # Unknown room — fallback to broadcast
        logger.info("SSE: Unknown room %s, broadcasting to all", room_id)
        await broker.broadcast(event_data)
        return

    # For DM rooms, extract participant user IDs from the display_name key
    if room_mapping.room_type == "dm" and room_mapping.display_name:
        # display_name format: "dm:@user1:server:@user2:server"
        parts = room_mapping.display_name.split(":")
        # Reconstruct matrix user IDs from the pair key
        matrix_user_ids = []
        if len(parts) >= 5:
            matrix_user_ids.append(f"{parts[1]}:{parts[2]}")
            matrix_user_ids.append(f"{parts[3]}:{parts[4]}")
        if matrix_user_ids:
            users = (
                db.query(UserMapping)
                .filter(UserMapping.matrix_user_id.in_(matrix_user_ids))
                .all()
            )
            logger.info(
                "SSE: DM room %s — notifying %d users: %s",
                room_id,
                len(users),
                [u.hub_user_id for u in users],
            )
            for user in users:
                await broker.publish_to_user(user.hub_user_id, event_data)
            return

    # For non-DM rooms, broadcast to all (room membership tracking not available)
    logger.info("SSE: Non-DM room %s, broadcasting to all", room_id)
    await broker.broadcast(event_data)


@router.get("/media/{server_name}/{media_id}")
async def get_media(
    server_name: str,
    media_id: str,
    current_user: UserMapping = Depends(get_current_user),
):
    """Proxy media download from Matrix content repository."""
    import httpx

    download_url = (
        f"{MATRIX_HOMESERVER_URL}/_matrix/media/v3/download/{server_name}/{media_id}"
    )
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(download_url)
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail="Media not found")
            content_type = resp.headers.get("content-type", "application/octet-stream")
            return StreamingResponse(
                iter([resp.content]),
                media_type=content_type,
                headers={
                    "Content-Disposition": resp.headers.get(
                        "content-disposition", "inline"
                    ),
                    "Cache-Control": "public, max-age=86400",
                },
            )
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Failed to fetch media")
