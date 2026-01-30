import enum

from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, func

from app.database import Base


class NotificationStatus(str, enum.Enum):
    pending = "pending"
    sent = "sent"
    failed = "failed"


class NotificationLog(Base):
    __tablename__ = "messenger_notification_log"

    id = Column(Integer, primary_key=True, index=True)
    source_app = Column(String(100), nullable=False)
    event_type = Column(String(100), nullable=False)
    title = Column(String(500), nullable=False)
    body = Column(Text, nullable=True)
    target_type = Column(String(50), nullable=True)
    entity_type = Column(String(100), nullable=True)
    entity_id = Column(Integer, nullable=True)
    priority = Column(String(20), default="normal")
    matrix_room_id = Column(String(255), nullable=True)
    matrix_event_id = Column(String(255), nullable=True)
    status = Column(Enum(NotificationStatus), default=NotificationStatus.pending)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
