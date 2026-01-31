"""Admin endpoints for messenger management (admin-only)."""

import logging
import secrets
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func

from app.auth import get_admin_user
from app.config import MATRIX_SERVER_NAME
from app.database import get_db
from app.models import UserMapping, RoomMapping, RoomType
from app.services.sse_broker import broker
from app.services.matrix_client import matrix_client, MatrixClientError

logger = logging.getLogger("admin")

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# ── Schemas ─────────────────────────────────────────────────────────

class AdminUserOut(BaseModel):
    hub_user_id: str
    display_name: Optional[str] = None
    role: str
    matrix_user_id: str
    provisioned: bool
    external_client_enabled: bool = False
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class AdminUserUpdate(BaseModel):
    display_name: str


class AdminRoomOut(BaseModel):
    matrix_room_id: str
    display_name: Optional[str] = None
    room_type: str
    member_count: int = 0

    class Config:
        from_attributes = True


class SystemStats(BaseModel):
    total_users: int
    provisioned_users: int
    rooms_by_type: dict
    sse_connections: int
    conduit_status: str


# ── User management ────────────────────────────────────────────────

@router.get("/users", response_model=List[AdminUserOut])
async def admin_list_users(
    admin: UserMapping = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """List all users with provisioning status."""
    users = db.query(UserMapping).order_by(UserMapping.created_at.desc()).all()
    return [
        AdminUserOut(
            hub_user_id=u.hub_user_id,
            display_name=u.display_name,
            role=u.role or "user",
            matrix_user_id=u.matrix_user_id,
            provisioned=bool(u.matrix_access_token_encrypted),
            external_client_enabled=bool(u.external_client_enabled),
            created_at=u.created_at.isoformat() if u.created_at else None,
        )
        for u in users
    ]


@router.patch("/users/{hub_user_id}")
async def admin_update_user(
    hub_user_id: str,
    body: AdminUserUpdate,
    admin: UserMapping = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Update a user's display name."""
    mapping = (
        db.query(UserMapping)
        .filter(UserMapping.hub_user_id == hub_user_id)
        .first()
    )
    if not mapping:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    mapping.display_name = body.display_name
    db.commit()
    db.refresh(mapping)
    return {"ok": True, "display_name": mapping.display_name}


class ExternalAccessToggle(BaseModel):
    enabled: bool


@router.post("/users/{hub_user_id}/external-access")
async def admin_toggle_external_access(
    hub_user_id: str,
    body: ExternalAccessToggle,
    admin: UserMapping = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Enable or disable external Matrix client access for a user.

    When enabling, ensures the user has a stored Matrix password
    (re-provisions with a new password if needed).
    """
    mapping = (
        db.query(UserMapping)
        .filter(UserMapping.hub_user_id == hub_user_id)
        .first()
    )
    if not mapping:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not mapping.matrix_access_token_encrypted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not yet provisioned on Matrix",
        )

    if body.enabled and not mapping.matrix_password:
        # User was provisioned before password storage was added.
        # Generate a new password and re-login to get a fresh token.
        new_password = secrets.token_urlsafe(24)
        localpart = mapping.matrix_user_id.split(":")[0].lstrip("@")
        try:
            # Re-register sets a new password on Conduit (m.login.dummy auth)
            result = await matrix_client.register_user(
                username=localpart,
                password=new_password,
                admin=False,
            )
            new_token = result.get("access_token", "")
            if new_token:
                mapping.matrix_access_token_encrypted = new_token
            mapping.matrix_password = new_password
        except MatrixClientError as e:
            logger.error("Failed to re-provision password for %s: %s", hub_user_id, e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not generate Matrix password for this user",
            )

    mapping.external_client_enabled = body.enabled
    db.commit()
    db.refresh(mapping)
    return {"ok": True, "external_client_enabled": mapping.external_client_enabled}


# ── Room management ────────────────────────────────────────────────

@router.get("/rooms", response_model=List[AdminRoomOut])
async def admin_list_rooms(
    admin: UserMapping = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """List all rooms with member counts."""
    rooms = db.query(RoomMapping).order_by(RoomMapping.created_at.desc()).all()
    result = []
    for room in rooms:
        member_count = 0
        try:
            # Use bot or admin token to query members
            bot = (
                db.query(UserMapping)
                .filter(UserMapping.is_bot == True)
                .first()
            )
            if bot and bot.matrix_access_token_encrypted:
                members = await matrix_client.get_room_members(
                    bot.matrix_access_token_encrypted, room.matrix_room_id
                )
                member_count = len(members)
        except Exception:
            pass
        result.append(
            AdminRoomOut(
                matrix_room_id=room.matrix_room_id,
                display_name=room.display_name,
                room_type=room.room_type.value if room.room_type else "general",
                member_count=member_count,
            )
        )
    return result


@router.delete("/rooms/{room_id}")
async def admin_delete_room(
    room_id: str,
    admin: UserMapping = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Delete a room mapping from the database."""
    mapping = (
        db.query(RoomMapping)
        .filter(RoomMapping.matrix_room_id == room_id)
        .first()
    )
    if not mapping:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    db.delete(mapping)
    db.commit()
    return {"ok": True, "deleted": room_id}


# ── System stats ───────────────────────────────────────────────────

@router.get("/stats", response_model=SystemStats)
async def admin_stats(
    admin: UserMapping = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """System overview statistics."""
    total_users = db.query(sa_func.count(UserMapping.id)).scalar()
    provisioned_users = (
        db.query(sa_func.count(UserMapping.id))
        .filter(UserMapping.matrix_access_token_encrypted.isnot(None))
        .scalar()
    )

    # Rooms by type
    room_counts = (
        db.query(RoomMapping.room_type, sa_func.count(RoomMapping.id))
        .group_by(RoomMapping.room_type)
        .all()
    )
    rooms_by_type = {
        (rt.value if rt else "unknown"): count
        for rt, count in room_counts
    }

    # SSE connections
    sse_connections = sum(len(queues) for queues in broker._subscribers.values())

    # Conduit status
    conduit_status = "offline"
    try:
        versions = await matrix_client.server_versions()
        if versions:
            conduit_status = "online"
    except Exception:
        pass

    return SystemStats(
        total_users=total_users,
        provisioned_users=provisioned_users,
        rooms_by_type=rooms_by_type,
        sse_connections=sse_connections,
        conduit_status=conduit_status,
    )
