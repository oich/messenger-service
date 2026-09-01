from sqlalchemy import Column, Integer, String, DateTime, func

from app.database import Base


class DeviceToken(Base):
    """FCM device token for push notifications (e.g. the Android mobile client)."""

    __tablename__ = "messenger_device_tokens"

    id = Column(Integer, primary_key=True, index=True)
    hub_user_id = Column(String(255), nullable=False, index=True)
    fcm_token = Column(String(500), nullable=False, unique=True)
    platform = Column(String(20), nullable=False, default="android")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
