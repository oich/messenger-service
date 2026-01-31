"""User listing endpoint for DM user discovery."""

import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, Query
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


@router.get("/me", response_model=UserMeOut)
async def get_me(
    current_user: UserMapping = Depends(get_current_user),
):
    """Return the current authenticated user's info."""
    return current_user


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
