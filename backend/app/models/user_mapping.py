from sqlalchemy import Column, Integer, String, Boolean, DateTime, func

from app.database import Base


class UserMapping(Base):
    __tablename__ = "messenger_user_mappings"

    id = Column(Integer, primary_key=True, index=True)
    hub_user_id = Column(String(255), unique=True, nullable=False, index=True)
    matrix_user_id = Column(String(255), unique=True, nullable=False)
    matrix_access_token_encrypted = Column(String(1024), nullable=True)
    tenant_id = Column(Integer, nullable=True)
    display_name = Column(String(255), nullable=True)
    is_bot = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
