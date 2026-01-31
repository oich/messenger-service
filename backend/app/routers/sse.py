"""Server-Sent Events endpoint for real-time push."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import UserMapping
from app.services.sse_broker import broker, sse_event_stream

logger = logging.getLogger("sse")
router = APIRouter(prefix="/api/v1/events", tags=["sse"])


async def _get_sse_user(
    request: Request,
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db),
) -> UserMapping:
    """Authenticate SSE connections via query param or Authorization header.

    EventSource API cannot set custom headers, so the token is passed
    as a query parameter (?token=...). We also support the standard
    Authorization header as fallback.
    """
    from app.hub_sso import is_sso_enabled, validate_hub_token
    from app.auth import _get_or_create_hub_shadow_user
    from app.config import SECRET_KEY, ALGORITHM
    from jose import JWTError, jwt

    # Try query param first, then Authorization header
    auth_token = token
    if not auth_token:
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            auth_token = auth_header[7:]

    if not auth_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    # Try Hub SSO
    if is_sso_enabled():
        hub_info = validate_hub_token(auth_token)
        if hub_info:
            return await _get_or_create_hub_shadow_user(hub_info, db)

    # Fallback to local JWT
    try:
        payload = jwt.decode(auth_token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    mapping = (
        db.query(UserMapping)
        .filter(UserMapping.hub_user_id == username)
        .first()
    )
    if not mapping:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return mapping


@router.get("/stream")
async def event_stream(
    current_user: UserMapping = Depends(_get_sse_user),
):
    """SSE stream of real-time events for the authenticated user."""
    logger.info("SSE: User %s connected (matrix: %s)", current_user.hub_user_id, current_user.matrix_user_id)
    q = broker.subscribe(current_user.hub_user_id)
    return StreamingResponse(
        sse_event_stream(current_user.hub_user_id, q),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
