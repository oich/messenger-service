"""User listing endpoint for DM user discovery."""

import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import UserMapping

logger = logging.getLogger("users")
router = APIRouter(prefix="/api/v1/users", tags=["users"])


class UserOut(BaseModel):
    hub_user_id: str
    display_name: Optional[str] = None

    class Config:
        from_attributes = True


class UserMeOut(UserOut):
    matrix_user_id: Optional[str] = None
    role: str = "user"
    external_client_enabled: bool = False


@router.get("/me", response_model=UserMeOut)
async def get_me(
    current_user: UserMapping = Depends(get_current_user),
):
    """Return the current authenticated user's info."""
    return current_user


class ExternalClientInfo(BaseModel):
    homeserver: str
    user_id: str
    username: str
    password: str


@router.get("/me/external-client", response_model=ExternalClientInfo)
async def get_external_client_info(
    request: Request,
    current_user: UserMapping = Depends(get_current_user),
):
    """Return Matrix login credentials for external clients (if enabled by admin)."""
    if not current_user.external_client_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="External client access is not enabled for your account",
        )
    if not current_user.matrix_password:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Matrix password available — contact your admin",
        )

    # Build homeserver URL from the incoming request host
    host = request.headers.get("x-forwarded-host") or request.headers.get("host", "localhost")
    # Strip port if present, use Matrix port 8448
    hostname = host.split(":")[0]
    homeserver_url = f"https://{hostname}:8448"

    localpart = current_user.matrix_user_id.split(":")[0].lstrip("@")

    return ExternalClientInfo(
        homeserver=homeserver_url,
        user_id=current_user.matrix_user_id,
        username=localpart,
        password=current_user.matrix_password,
    )


@router.get("", response_model=List[UserOut])
async def list_users(
    q: Optional[str] = Query(None, description="Search by display name"),
    current_user: UserMapping = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List users available for DM, excluding bots and the current user."""
    query = db.query(UserMapping).filter(
        UserMapping.is_bot == False,
        UserMapping.hub_user_id != current_user.hub_user_id,
    )

    if current_user.tenant_id is not None:
        query = query.filter(UserMapping.tenant_id == current_user.tenant_id)

    if q:
        query = query.filter(UserMapping.display_name.ilike(f"%{q}%"))

    query = query.order_by(UserMapping.display_name)

    return query.all()
