"""Per-user room read markers, used to derive cross-satellite unread
indicators (e.g. an envelope icon on a project card in another satellite,
which has no live SSE connection of its own to know about new messages).
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import RoomRead


def mark_room_read(hub_user_id: str, room_id: str, db: Session) -> None:
    row = (
        db.query(RoomRead)
        .filter(RoomRead.hub_user_id == hub_user_id, RoomRead.matrix_room_id == room_id)
        .first()
    )
    now = datetime.now(timezone.utc)
    if row:
        row.last_read_at = now
    else:
        db.add(RoomRead(hub_user_id=hub_user_id, matrix_room_id=room_id, last_read_at=now))
    db.commit()
