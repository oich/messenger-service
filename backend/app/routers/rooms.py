"""Room listing, creation, and joining endpoints."""

import logging
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user, verify_service_token
from app.config import MESSENGER_FRONTEND_URL
from app.database import get_db
from app.models import UserMapping, RoomMapping, RoomType
from app.schemas.rooms import (
    RoomCreate,
    RoomOut,
    RoomListOut,
    EntityRoomCreate,
    EntityRoomOut,
)
from app.services.matrix_client import matrix_client, MatrixClientError
from app.services.room_manager import (
    create_custom_room,
    get_or_create_general_room,
    get_or_create_dm_room,
    get_or_create_entity_room,
    ensure_user_in_room,
)
from app.services.user_provisioning import provision_matrix_user

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
            current_user.get_matrix_access_token()
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
        display_name = mapping.display_name if mapping else room_id

        # For DM rooms, resolve pair key to the chat partner's display name
        if mapping and mapping.room_type == RoomType.dm and display_name and display_name.startswith("dm:"):
            display_name = _resolve_dm_display_name(
                display_name, current_user.matrix_user_id, db
            )

        rooms.append(
            RoomOut(
                matrix_room_id=room_id,
                display_name=display_name,
                room_type=mapping.room_type if mapping else RoomType.general,
                entity_type=mapping.entity_type if mapping else None,
                entity_id=mapping.entity_id if mapping else None,
                source_url=mapping.source_url if mapping else None,
            )
        )

    return RoomListOut(rooms=rooms)


def _resolve_dm_display_name(
    pair_key: str, current_matrix_id: str, db: Session
) -> str:
    """Resolve a DM pair key like 'dm:@user1:server:@user2:server' to the partner's display name."""
    parts = pair_key.split(":")
    if len(parts) < 5:
        return pair_key

    matrix_user_ids = [
        f"{parts[1]}:{parts[2]}",
        f"{parts[3]}:{parts[4]}",
    ]

    # Find the other user (not the current one)
    partner_matrix_id = None
    for mid in matrix_user_ids:
        if mid != current_matrix_id:
            partner_matrix_id = mid
            break

    if not partner_matrix_id:
        partner_matrix_id = matrix_user_ids[0]

    partner = (
        db.query(UserMapping)
        .filter(UserMapping.matrix_user_id == partner_matrix_id)
        .first()
    )
    if partner and partner.display_name:
        return partner.display_name
    if partner:
        return partner.hub_user_id
    # Fallback: extract username from Matrix ID (@user:server -> user)
    return partner_matrix_id.split(":")[0].lstrip("@")


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
            creator_token=current_user.get_matrix_access_token(),
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
            current_user.get_matrix_access_token(), room_id
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

    # Ensure target user is provisioned on Matrix
    if not target_mapping.matrix_access_token_encrypted:
        try:
            target_mapping = await provision_matrix_user(
                hub_user_id=target_mapping.hub_user_id,
                display_name=target_mapping.display_name or target_user_id,
                tenant_id=target_mapping.tenant_id,
                db=db,
            )
        except Exception:
            logger.warning("Could not provision target user %s", target_user_id)

    try:
        mapping = await get_or_create_dm_room(
            user1_mapping=current_user,
            user2_mapping=target_mapping,
            user1_token=current_user.get_matrix_access_token(),
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


@router.post("/{room_id}/invite")
async def invite_to_room(
    room_id: str,
    invite_data: dict,
    current_user: UserMapping = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Invite a user to a room by hub_user_id."""
    if not current_user.matrix_access_token_encrypted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not provisioned on Matrix",
        )

    hub_user_id = invite_data.get("hub_user_id")
    if not hub_user_id:
        raise HTTPException(status_code=400, detail="hub_user_id required")

    target = (
        db.query(UserMapping)
        .filter(UserMapping.hub_user_id == hub_user_id)
        .first()
    )
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    # Provision if needed
    if not target.matrix_access_token_encrypted:
        try:
            target = await provision_matrix_user(
                hub_user_id=target.hub_user_id,
                display_name=target.display_name or hub_user_id,
                tenant_id=target.tenant_id,
                db=db,
            )
        except Exception:
            raise HTTPException(status_code=502, detail="Could not provision user")

    try:
        await matrix_client.invite_user(
            current_user.get_matrix_access_token(),
            room_id,
            target.matrix_user_id,
        )
        # Auto-join so room appears in their list immediately
        if target.matrix_access_token_encrypted:
            await matrix_client.join_room(
                target.get_matrix_access_token(), room_id
            )
    except MatrixClientError as e:
        raise HTTPException(status_code=502, detail=f"Failed to invite: {e}")

    return {
        "status": "invited",
        "hub_user_id": hub_user_id,
        "display_name": target.display_name,
    }


@router.get("/{room_id}/members")
async def get_room_members(
    room_id: str,
    current_user: UserMapping = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get members of a room."""
    if not current_user.matrix_access_token_encrypted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not provisioned on Matrix",
        )

    try:
        members = await matrix_client.get_room_members(
            current_user.get_matrix_access_token(), room_id
        )
    except MatrixClientError as e:
        raise HTTPException(status_code=502, detail=f"Failed to get members: {e}")

    # Resolve display names from our DB
    result = []
    for matrix_user_id in members:
        user = (
            db.query(UserMapping)
            .filter(UserMapping.matrix_user_id == matrix_user_id)
            .first()
        )
        result.append({
            "matrix_user_id": matrix_user_id,
            "hub_user_id": user.hub_user_id if user else None,
            "display_name": (user.display_name if user else None)
                or matrix_user_id.split(":")[0].lstrip("@"),
        })

    return result


@router.post("/entity", response_model=EntityRoomOut)
async def get_or_create_entity_room_endpoint(
    room_data: EntityRoomCreate,
    db: Session = Depends(get_db),
    _token: str = Depends(verify_service_token),
):
    """Get or create a room for an entity owned by another satellite (e.g. a project).

    Requires X-Service-Token header matching MESSENGER_SERVICE_TOKEN. Idempotent:
    calling this again for the same (entity_type, entity_id) returns the same room.
    """
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
        mapping = await get_or_create_entity_room(
            entity_type=room_data.entity_type,
            entity_id=room_data.entity_id,
            display_name=room_data.display_name,
            admin_token=bot_token,
            db=db,
            tenant_id=room_data.tenant_id,
            source_url=room_data.source_url,
            update_display_name=room_data.update_display_name,
        )
    except MatrixClientError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to create entity room: {e}",
        )

    # Invite/join the requested users - get_or_create_entity_room only
    # ensures the bot is a member, but the room is private_chat, so without
    # this they could see the room in their list (if invited elsewhere) but
    # not actually read/send in it. Additive only: a user no longer in
    # hub_user_ids (e.g. unassigned from a project) is NOT removed - that
    # stays a deliberate manual action, not an automatic side effect.
    for hub_user_id in (room_data.hub_user_ids or []):
        user_mapping = (
            db.query(UserMapping)
            .filter(UserMapping.hub_user_id == hub_user_id)
            .first()
        )
        try:
            if not user_mapping:
                user_mapping = await provision_matrix_user(
                    hub_user_id=hub_user_id,
                    display_name=hub_user_id,
                    tenant_id=room_data.tenant_id,
                    db=db,
                )
            elif not user_mapping.matrix_access_token_encrypted:
                user_mapping = await provision_matrix_user(
                    hub_user_id=user_mapping.hub_user_id,
                    display_name=user_mapping.display_name or hub_user_id,
                    tenant_id=user_mapping.tenant_id,
                    db=db,
                )
            await ensure_user_in_room(user_mapping, mapping, bot_token)
        except MatrixClientError as e:
            logger.warning(
                "Could not add user %s to entity room %s: %s",
                hub_user_id, mapping.matrix_room_id, e,
            )

    deep_link_path = f"/room/{quote(mapping.matrix_room_id, safe='')}"
    deep_link_url = f"{MESSENGER_FRONTEND_URL}{deep_link_path}" if MESSENGER_FRONTEND_URL else None

    return EntityRoomOut(
        matrix_room_id=mapping.matrix_room_id,
        display_name=mapping.display_name,
        source_url=mapping.source_url,
        deep_link_path=deep_link_path,
        deep_link_url=deep_link_url,
    )
