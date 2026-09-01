"""Device registration for push notifications (FCM)."""

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import DeviceToken, UserMapping

logger = logging.getLogger("devices")
router = APIRouter(prefix="/api/v1/devices", tags=["devices"])


class DeviceRegister(BaseModel):
    fcm_token: str
    platform: str = "android"


@router.post("/register")
def register_device(
    payload: DeviceRegister,
    current_user: UserMapping = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Register or refresh the FCM token for the current user's device."""
    existing = (
        db.query(DeviceToken)
        .filter(DeviceToken.fcm_token == payload.fcm_token)
        .first()
    )
    if existing:
        existing.hub_user_id = current_user.hub_user_id
        existing.platform = payload.platform
    else:
        db.add(DeviceToken(
            hub_user_id=current_user.hub_user_id,
            fcm_token=payload.fcm_token,
            platform=payload.platform,
        ))
    db.commit()
    return {"status": "registered"}


@router.delete("/register")
def unregister_device(
    fcm_token: str,
    current_user: UserMapping = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove a device token (e.g. on logout)."""
    db.query(DeviceToken).filter(
        DeviceToken.fcm_token == fcm_token,
        DeviceToken.hub_user_id == current_user.hub_user_id,
    ).delete()
    db.commit()
    return {"status": "unregistered"}
