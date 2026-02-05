"""Manage Matrix rooms: tenant spaces, entity rooms, DMs."""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.config import MATRIX_SERVER_NAME
from app.models import RoomMapping, RoomType, UserMapping
from app.services.matrix_client import matrix_client, MatrixClientError

logger = logging.getLogger("room_manager")


async def _ensure_bot_in_room(bot_token: str, room_id: str) -> None:
    """Ensure the bot is a member of the room so it can send messages.

    For public rooms, the bot can join directly.
    For private rooms, this may fail if the bot is not invited.
    """
    try:
        await matrix_client.join_room(bot_token, room_id)
    except MatrixClientError as e:
        # Log but don't fail - the bot may already be a member
        logger.debug("Bot join attempt for room %s: %s", room_id, e)


async def get_or_create_general_room(
    tenant_id: int,
    admin_token: str,
    db: Session,
) -> RoomMapping:
    """Get or create the tenant's general chat room."""
    mapping = (
        db.query(RoomMapping)
        .filter(
            RoomMapping.tenant_id == tenant_id,
            RoomMapping.room_type == RoomType.general,
        )
        .first()
    )
    if mapping:
        # Ensure bot can send to this room (may have been created before bot provisioning)
        await _ensure_bot_in_room(admin_token, mapping.matrix_room_id)
        return mapping

    room_id = await matrix_client.create_room(
        access_token=admin_token,
        name="Allgemein",
        topic="Allgemeiner Chat-Kanal",
        preset="public_chat",
    )

    mapping = RoomMapping(
        matrix_room_id=room_id,
        room_type=RoomType.general,
        display_name="Allgemein",
        tenant_id=tenant_id,
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return mapping


async def get_or_create_service_room(
    service_name: str,
    display_name: str,
    admin_token: str,
    db: Session,
    tenant_id: Optional[int] = None,
) -> RoomMapping:
    """Get or create a dedicated room for a satellite service (e.g., machine-monitoring)."""
    mapping = (
        db.query(RoomMapping)
        .filter(
            RoomMapping.room_type == RoomType.service,
            RoomMapping.entity_type == service_name,
        )
        .first()
    )
    if mapping:
        # Ensure bot can send to this room (may have been created before bot provisioning)
        await _ensure_bot_in_room(admin_token, mapping.matrix_room_id)
        return mapping

    # Get all non-bot users to invite them
    all_users = db.query(UserMapping).filter(UserMapping.is_bot == False).all()
    invite_user_ids = [u.matrix_user_id for u in all_users if u.matrix_user_id]

    room_id = await matrix_client.create_room(
        access_token=admin_token,
        name=display_name,
        topic=f"Benachrichtigungen von {display_name}",
        preset="public_chat",
        invite=invite_user_ids if invite_user_ids else None,
    )

    # Auto-join all invited users so the room appears in their list
    for user in all_users:
        if user.matrix_access_token_encrypted:
            try:
                await matrix_client.join_room(
                    user.get_matrix_access_token(), room_id
                )
            except MatrixClientError:
                logger.debug(
                    "User %s could not auto-join service room %s",
                    user.matrix_user_id, room_id,
                )

    mapping = RoomMapping(
        matrix_room_id=room_id,
        room_type=RoomType.service,
        display_name=display_name,
        tenant_id=tenant_id,
        entity_type=service_name,  # Use entity_type to store service name
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return mapping


async def get_or_create_notification_dm_room(
    bot_user_id: str,
    target_user_mapping: UserMapping,
    bot_token: str,
    db: Session,
) -> RoomMapping:
    """Get or create a DM room between the notification bot and a target user.

    This is used for sending direct notification messages to specific users.
    """
    # Create a unique key for this bot-user pair
    pair_key = f"notification_dm:{bot_user_id}:{target_user_mapping.matrix_user_id}"

    mapping = (
        db.query(RoomMapping)
        .filter(
            RoomMapping.room_type == RoomType.dm,
            RoomMapping.display_name == pair_key,
        )
        .first()
    )
    if mapping:
        await _ensure_bot_in_room(bot_token, mapping.matrix_room_id)
        return mapping

    # Create new DM room with the target user invited
    room_id = await matrix_client.create_room(
        access_token=bot_token,
        name=f"Benachrichtigungen fuer {target_user_mapping.display_name or target_user_mapping.hub_user_id}",
        invite=[target_user_mapping.matrix_user_id],
        is_direct=True,
        preset="private_chat",
    )

    # Auto-join the target user so they see the room
    if target_user_mapping.matrix_access_token_encrypted:
        try:
            await matrix_client.join_room(
                target_user_mapping.get_matrix_access_token(), room_id
            )
        except MatrixClientError:
            logger.warning(
                "User %s could not auto-join notification DM room %s",
                target_user_mapping.matrix_user_id,
                room_id,
            )

    mapping = RoomMapping(
        matrix_room_id=room_id,
        room_type=RoomType.dm,
        display_name=pair_key,
        tenant_id=target_user_mapping.tenant_id,
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return mapping


async def get_or_create_entity_room(
    entity_type: str,
    entity_id: int,
    display_name: str,
    admin_token: str,
    db: Session,
    tenant_id: Optional[int] = None,
) -> RoomMapping:
    """Get or create a room for a specific entity (machine, project, etc.)."""
    mapping = (
        db.query(RoomMapping)
        .filter(
            RoomMapping.entity_type == entity_type,
            RoomMapping.entity_id == entity_id,
            RoomMapping.room_type == RoomType.entity,
        )
        .first()
    )
    if mapping:
        # Ensure bot can send to this room (may have been created before bot provisioning)
        await _ensure_bot_in_room(admin_token, mapping.matrix_room_id)
        return mapping

    room_id = await matrix_client.create_room(
        access_token=admin_token,
        name=display_name,
        topic=f"{entity_type} #{entity_id}",
        preset="private_chat",
    )

    mapping = RoomMapping(
        matrix_room_id=room_id,
        room_type=RoomType.entity,
        display_name=display_name,
        tenant_id=tenant_id,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return mapping


async def get_or_create_dm_room(
    user1_mapping: UserMapping,
    user2_mapping: UserMapping,
    user1_token: str,
    db: Session,
) -> RoomMapping:
    """Get or create a DM room between two users."""
    # Check both directions
    pair_key_1 = f"dm:{user1_mapping.matrix_user_id}:{user2_mapping.matrix_user_id}"
    pair_key_2 = f"dm:{user2_mapping.matrix_user_id}:{user1_mapping.matrix_user_id}"

    mapping = (
        db.query(RoomMapping)
        .filter(
            RoomMapping.room_type == RoomType.dm,
            RoomMapping.display_name.in_([pair_key_1, pair_key_2]),
        )
        .first()
    )
    if mapping:
        # Ensure both users are joined (they may have been only invited)
        room_id = mapping.matrix_room_id
        for user_mapping, token in [
            (user1_mapping, user1_token),
            (user2_mapping, user2_mapping.get_matrix_access_token() if user2_mapping.matrix_access_token_encrypted else None),
        ]:
            if not token:
                continue
            try:
                await matrix_client.join_room(token, room_id)
            except MatrixClientError:
                # Try invite first, then join
                try:
                    await matrix_client.invite_user(user1_token, room_id, user_mapping.matrix_user_id)
                    await matrix_client.join_room(token, room_id)
                except MatrixClientError:
                    logger.warning(
                        "User %s could not join existing DM room %s",
                        user_mapping.matrix_user_id,
                        room_id,
                    )
        return mapping

    room_id = await matrix_client.create_room(
        access_token=user1_token,
        name=f"DM: {user1_mapping.display_name} & {user2_mapping.display_name}",
        invite=[user2_mapping.matrix_user_id],
        is_direct=True,
    )

    # Auto-join recipient so the room appears in their joined_rooms
    if user2_mapping.matrix_access_token_encrypted:
        try:
            await matrix_client.join_room(
                user2_mapping.get_matrix_access_token(), room_id
            )
        except MatrixClientError:
            logger.warning(
                "User %s could not auto-join DM room %s",
                user2_mapping.matrix_user_id,
                room_id,
            )

    mapping = RoomMapping(
        matrix_room_id=room_id,
        room_type=RoomType.dm,
        display_name=pair_key_1,
        tenant_id=user1_mapping.tenant_id,
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return mapping


async def create_custom_room(
    name: str,
    topic: Optional[str],
    creator_token: str,
    invite_user_ids: Optional[list[str]],
    tenant_id: Optional[int],
    db: Session,
) -> RoomMapping:
    """Create a custom room and auto-join invited users."""
    room_id = await matrix_client.create_room(
        access_token=creator_token,
        name=name,
        topic=topic,
        invite=invite_user_ids,
        preset="private_chat",
    )

    # Auto-join invited users so the room appears in their room list
    if invite_user_ids:
        for matrix_user_id in invite_user_ids:
            user_mapping = (
                db.query(UserMapping)
                .filter(UserMapping.matrix_user_id == matrix_user_id)
                .first()
            )
            if user_mapping and user_mapping.matrix_access_token_encrypted:
                try:
                    await matrix_client.join_room(
                        user_mapping.get_matrix_access_token(), room_id
                    )
                except MatrixClientError:
                    logger.warning(
                        "User %s could not auto-join room %s",
                        matrix_user_id, room_id,
                    )

    mapping = RoomMapping(
        matrix_room_id=room_id,
        room_type=RoomType.general,
        display_name=name,
        tenant_id=tenant_id,
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return mapping


async def ensure_user_in_room(
    user_mapping: UserMapping,
    room_mapping: RoomMapping,
    admin_token: str,
) -> None:
    """Ensure a user is in a room (invite + auto-join)."""
    try:
        await matrix_client.invite_user(
            admin_token, room_mapping.matrix_room_id, user_mapping.matrix_user_id
        )
    except MatrixClientError:
        pass  # May already be invited or joined

    if user_mapping.matrix_access_token_encrypted:
        try:
            await matrix_client.join_room(
                user_mapping.get_matrix_access_token(),
                room_mapping.matrix_room_id,
            )
        except MatrixClientError:
            logger.warning(
                "User %s could not join room %s",
                user_mapping.matrix_user_id,
                room_mapping.matrix_room_id,
            )
