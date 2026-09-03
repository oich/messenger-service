"""Feedback (bug/feature request) -> Hub Messenger DM to admins + GitHub issue.

Thin per-app wiring around the shared hub_feedback_kit router factory.

messenger-service's user model (UserMapping) has no 'username' field - the
Hub username lives in hub_user_id already (no 'hub_' prefix to strip, unlike
other satellites' locally-synced users), so admin usernames can be used
as-is for the Messenger DM target.
"""

from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.models import UserMapping
from hub_feedback_kit import build_feedback_router


def _list_admin_usernames(db: Session) -> list[str]:
    return [
        m.hub_user_id
        for m in db.query(UserMapping).filter(UserMapping.role == "admin").all()
    ]


router = build_feedback_router(
    source_app="messenger-service",
    get_db=get_db,
    get_current_user=get_current_user,
    list_admin_usernames=_list_admin_usernames,
)
