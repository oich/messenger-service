"""Hub SSO login endpoint.

When a user logs in via Hub, this endpoint:
1. Validates the Hub JWT
2. Provisions a Matrix user if needed
3. Returns a messenger-service access token + Matrix user info
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.hub_sso import is_sso_enabled, validate_hub_token
from app.schemas.users import TokenResponse
from app.security import create_access_token
from app.services.user_provisioning import provision_matrix_user

logger = logging.getLogger("auth")
router = APIRouter(prefix="/auth", tags=["auth"])


class HubLoginRequest:
    """Extracted from the Authorization header."""
    pass


@router.post("/hub-login", response_model=TokenResponse)
async def hub_login(
    hub_token: str,
    db: Session = Depends(get_db),
):
    """Login via Hub SSO token. Provisions Matrix user if needed."""
    if not is_sso_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Hub SSO is not configured",
        )

    hub_info = validate_hub_token(hub_token)
    if not hub_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Hub token",
        )

    # Provision Matrix user
    mapping = await provision_matrix_user(
        hub_user_id=hub_info["username"],
        display_name=hub_info.get("display_name", hub_info["username"]),
        tenant_id=hub_info.get("tenant_id"),
        db=db,
    )

    # Create local access token
    access_token = create_access_token(data={"sub": mapping.hub_user_id})

    return TokenResponse(
        access_token=access_token,
        matrix_user_id=mapping.matrix_user_id,
        display_name=mapping.display_name,
    )
