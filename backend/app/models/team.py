from sqlalchemy import Column, Integer, String, DateTime, JSON, func

from app.database import Base


class Team(Base):
    """A fixed, named group of Hub users, defined once and reusable across
    rooms/projects (e.g. "Konstruktion", "Schicht A") - lets a user bulk-invite
    a whole team into any chat instead of inviting members one by one.
    """

    __tablename__ = "messenger_teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    # Generic JSON (not JSONB) so this also works on the SQLite test DB.
    member_hub_user_ids = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
