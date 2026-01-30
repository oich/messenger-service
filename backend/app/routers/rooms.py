"""Room listing, creation, and joining endpoints."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import UserMapping, RoomMapping, RoomType
from app.schemas.rooms import RoomCreate, RoomOut, RoomListOut
from app.services.matrix_client import matrix_client, MatrixClientError
from app.services.room_manager import (
    create_custom_room,
    get_or_create_general_room,
    get_or_create_dm_room,
    ensure_user_in_room,
)

logger = logging.getLogger("rooms")
router = APIRouter(prefix="/api/v1/rooms", tags=["rooms"])


@router.get("", response_model=RoomListOut)
async def list_rooms(
    current_user: UserMapping = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all rooms the user has access to."""
    if not current_user.matrix_access_token_encrypted:
        return RoomListOut(rooms=[])

    try:
        joined_room_ids = await matrix_client.list_joined_rooms(
            current_user.matrix_access_token_encrypted
        )
    except MatrixClientError:
        joined_room_ids = []

    rooms = []
    for room_id in joined_room_ids:
        mapping = (
            db.query(RoomMapping)
            .filter(RoomMapping.matrix_room_id == room_id)
            .first()
        )
        rooms.append(
            RoomOut(
                matrix_room_id=room_id,
                display_name=mapping.display_name if mapping else room_id,
                room_type=mapping.room_type if mapping else RoomType.general,
                entity_type=mapping.entity_type if mapping else None,
                entity_id=mapping.entity_id if mapping else None,
            )
        )

    return RoomListOut(rooms=rooms)


@router.post("", response_model=RoomOut, status_code=status.HTTP_201_CREATED)
async def create_room(
    room_data: RoomCreate,
    current_user: UserMapping = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new room."""
    if not current_user.matrix_access_token_encrypted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not provisioned on Matrix",
        )

    try:
        mapping = await create_custom_room(
            name=room_data.name,
            topic=room_data.topic,
            creator_token=current_user.matrix_access_token_encrypted,
            invite_user_ids=room_data.invite_users,
            tenant_id=current_user.tenant_id,
            db=db,
        )
    except MatrixClientError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to create room: {e}",
        )

    return RoomOut(
        matrix_room_id=mapping.matrix_room_id,
        display_name=mapping.display_name,
        room_type=mapping.room_type,
        entity_type=mapping.entity_type,
        entity_id=mapping.entity_id,
    )


@router.post("/{room_id}/join")
async def join_room(
    room_id: str,
    current_user: UserMapping = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Join a room."""
    if not current_user.matrix_access_token_encrypted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not provisioned on Matrix",
        )

    try:
        await matrix_client.join_room(
            current_user.matrix_access_token_encrypted, room_id
        )
    except MatrixClientError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to join room: {e}",
        )

    return {"status": "joined", "room_id": room_id}


@router.post("/dm/{target_user_id}", response_model=RoomOut)
async def create_dm(
    target_user_id: str,
    current_user: UserMapping = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create or get a DM room with another user."""
    if not current_user.matrix_access_token_encrypted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not provisioned on Matrix",
        )

    target_mapping = (
        db.query(UserMapping)
        .filter(UserMapping.hub_user_id == target_user_id)
        .first()
    )
    if not target_mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target user not found",
        )

    try:
        mapping = await get_or_create_dm_room(
            user1_mapping=current_user,
            user2_mapping=target_mapping,
            user1_token=current_user.matrix_access_token_encrypted,
            db=db,
        )
    except MatrixClientError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to create DM: {e}",
        )

    return RoomOut(
        matrix_room_id=mapping.matrix_room_id,
        display_name=target_mapping.display_name or target_user_id,
        room_type=RoomType.dm,
    )
