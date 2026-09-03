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
    source_url: Optional[str] = None
    unread_count: int = 0
    last_message: Optional[str] = None
    last_message_ts: Optional[datetime] = None
    is_archived: bool = False


class RoomListOut(BaseModel):
    rooms: List[RoomOut]
    # Count of archived rooms hidden from `rooms` (list_rooms only includes
    # them when include_archived=true) - lets the UI show "Archiv (N)".
    archived_count: int = 0


class EntityRoomCreate(BaseModel):
    """Request to get-or-create a room for an entity in another satellite (e.g. a project)."""

    entity_type: str
    entity_id: int
    display_name: str
    tenant_id: Optional[int] = None
    # Hub usernames to invite/join so they can actually see and send messages
    # (the room is private_chat, so creating it alone is not enough; only the
    # bot would be a member). Typically the requesting user plus the entity's
    # assigned team (e.g. a project's assigned employees with a Hub login).
    hub_user_ids: Optional[List[str]] = None
    # Deep link back into the source app's own view of this entity, shown in
    # the messenger UI. Only set by the "primary" source app - a secondary
    # satellite linking to the same entity (e.g. engineering-app to a
    # fertigungs-app project) should leave this unset.
    source_url: Optional[str] = None
    # Whether this caller's display_name should overwrite an already-existing
    # room's name. Default False (safe): only a caller that knows it holds
    # the authoritative name (e.g. fertigungs-app, which has the customer
    # number) should pass True.
    update_display_name: bool = False


class EntityRoomOut(BaseModel):
    matrix_room_id: str
    display_name: Optional[str] = None
    source_url: Optional[str] = None
    deep_link_path: str
    deep_link_url: Optional[str] = None


class EntityRef(BaseModel):
    entity_type: str
    entity_id: int


class UnreadStatusRequest(BaseModel):
    """Cross-satellite read/unread lookup for a batch of entities (e.g. every
    project shown on a Gantt page), relative to one Hub user."""

    hub_user_id: str
    entities: List[EntityRef]


class UnreadStatusItem(BaseModel):
    entity_type: str
    entity_id: int
    has_messages: bool = False
    unread: bool = False


class UnreadStatusResponse(BaseModel):
    items: List[UnreadStatusItem]
