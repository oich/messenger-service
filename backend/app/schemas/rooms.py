from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel

from app.models.room import RoomType


class RoomCreate(BaseModel):
    name: str
    room_type: RoomType = RoomType.general
    topic: Optional[str] = None
    invite_users: Optional[List[str]] = None
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None


class RoomOut(BaseModel):
    matrix_room_id: str
    display_name: Optional[str] = None
    room_type: RoomType
    topic: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    unread_count: int = 0
    last_message: Optional[str] = None
    last_message_ts: Optional[datetime] = None


class RoomListOut(BaseModel):
    rooms: List[RoomOut]


class EntityRoomCreate(BaseModel):
    """Request to get-or-create a room for an entity in another satellite (e.g. a project)."""

    entity_type: str
    entity_id: int
    display_name: str
    tenant_id: Optional[int] = None


class EntityRoomOut(BaseModel):
    matrix_room_id: str
    display_name: Optional[str] = None
    deep_link_path: str
    deep_link_url: Optional[str] = None
