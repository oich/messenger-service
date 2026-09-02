import enum

from sqlalchemy import Column, Integer, String, DateTime, Enum, func

from app.database import Base


class RoomType(str, enum.Enum):
    general = "general"
    dm = "dm"
    entity = "entity"
    space = "space"
    service = "service"  # Dedicated rooms for satellite services (e.g., machine-monitoring)


class RoomMapping(Base):
    __tablename__ = "messenger_room_mappings"

    id = Column(Integer, primary_key=True, index=True)
    matrix_room_id = Column(String(255), unique=True, nullable=False, index=True)
    room_type = Column(Enum(RoomType), nullable=False, default=RoomType.general)
    display_name = Column(String(255), nullable=True)
    tenant_id = Column(Integer, nullable=True)
    entity_type = Column(String(100), nullable=True)
    entity_id = Column(Integer, nullable=True)
    # Deep link back into the source app's entity view (e.g. the fertigungs-app
    # project). Lets the messenger UI offer a "back to source" link without
    # needing to know each app's URL scheme.
    source_url = Column(String(1000), nullable=True)
    # Bumped on every message/upload into this room - compared against a
    # user's RoomRead.last_read_at to derive unread indicators cross-satellite.
    last_message_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
