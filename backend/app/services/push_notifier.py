"""Send Firebase Cloud Messaging push notifications to room members.

Complements the SSE broker: SSE only reaches clients with an open connection
(app in the foreground), FCM push reaches the mobile app while backgrounded
or closed. Disabled unless FCM_ENABLED + FIREBASE_CREDENTIALS_JSON are set.
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.config import FCM_ENABLED, FIREBASE_CREDENTIALS_JSON
from app.models import DeviceToken, UserMapping
from app.services.matrix_client import matrix_client, MatrixClientError

logger = logging.getLogger("push_notifier")

_firebase_app = None
_firebase_init_failed = False


def _get_firebase_app():
    """Lazily initialize the firebase-admin app from the configured credentials."""
    global _firebase_app, _firebase_init_failed
    if _firebase_app is not None or _firebase_init_failed:
        return _firebase_app
    if not FCM_ENABLED or not FIREBASE_CREDENTIALS_JSON:
        _firebase_init_failed = True
        return None
    try:
        import firebase_admin
        from firebase_admin import credentials

        cred = credentials.Certificate(FIREBASE_CREDENTIALS_JSON)
        _firebase_app = firebase_admin.initialize_app(cred)
        return _firebase_app
    except Exception:
        logger.exception("Failed to initialize firebase-admin - push notifications disabled")
        _firebase_init_failed = True
        return None


async def push_to_room_members(
    room_id: str,
    bot_token: str,
    title: str,
    body: str,
    db: Session,
    exclude_matrix_user_id: Optional[str] = None,
) -> None:
    """Send an FCM push to every registered device of every member of a room.

    Resolves actual Matrix room membership (not a blind broadcast) so users
    who are not in the room never receive a push for it.
    """
    if not FCM_ENABLED:
        return
    app = _get_firebase_app()
    if app is None:
        return

    try:
        member_matrix_ids = await matrix_client.get_room_members(bot_token, room_id)
    except MatrixClientError:
        logger.warning("Could not resolve members for room %s - skipping push", room_id)
        return

    if exclude_matrix_user_id:
        member_matrix_ids = [m for m in member_matrix_ids if m != exclude_matrix_user_id]
    if not member_matrix_ids:
        return

    hub_user_ids = [
        row.hub_user_id
        for row in db.query(UserMapping)
        .filter(UserMapping.matrix_user_id.in_(member_matrix_ids), UserMapping.is_bot == False)
        .all()
    ]
    if not hub_user_ids:
        return

    tokens = [
        row.fcm_token
        for row in db.query(DeviceToken)
        .filter(DeviceToken.hub_user_id.in_(hub_user_ids))
        .all()
    ]
    if not tokens:
        return

    from firebase_admin import messaging

    message = messaging.MulticastMessage(
        notification=messaging.Notification(title=title, body=body),
        data={"matrix_room_id": room_id},
        tokens=tokens,
    )
    try:
        response = messaging.send_each_for_multicast(message, app=app)
        logger.info(
            "FCM push to room %s: %d/%d sent",
            room_id, response.success_count, len(tokens),
        )
        _prune_invalid_tokens(tokens, response, db)
    except Exception:
        logger.exception("FCM push failed for room %s", room_id)


def _prune_invalid_tokens(tokens: list[str], response, db: Session) -> None:
    """Remove device tokens that Firebase reports as unregistered/invalid."""
    invalid = [
        tokens[i] for i, r in enumerate(response.responses)
        if not r.success and r.exception is not None
        and getattr(r.exception, "code", "") in ("NOT_FOUND", "UNREGISTERED")
    ]
    if not invalid:
        return
    db.query(DeviceToken).filter(DeviceToken.fcm_token.in_(invalid)).delete(synchronize_session=False)
    db.commit()
