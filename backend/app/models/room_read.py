from sqlalchemy import Column, Integer, String, DateTime, UniqueConstraint, func

from app.database import Base


class RoomRead(Base):
    """Per-user read marker for a room, used to compute unread indicators
    for other satellites (e.g. an envelope icon on a project card) that have
    no live SSE connection of their own to the messenger.
    """

    __tablename__ = "messenger_room_reads"

    id = Column(Integer, primary_key=True, index=True)
    hub_user_id = Column(String(255), nullable=False, index=True)
    matrix_room_id = Column(String(255), nullable=False, index=True)
    last_read_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("hub_user_id", "matrix_room_id", name="_room_read_uc"),
    )
