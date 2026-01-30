from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class NotificationSend(BaseModel):
    source_app: str
    event_type: str
    title: str
    body: Optional[str] = None
    target_type: str = "general"  # general, entity_room, dm
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    target_user: Optional[str] = None  # for DM notifications
    priority: str = "normal"  # normal, urgent


class NotificationOut(BaseModel):
    id: int
    source_app: str
    event_type: str
    title: str
    body: Optional[str] = None
    priority: str
    status: str
    matrix_room_id: Optional[str] = None
    matrix_event_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
