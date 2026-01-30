import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app import models, security
from app.config import SECRET_KEY, ALGORITHM
from app.database import get_db

logger = logging.getLogger("auth")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


async def _get_or_create_hub_shadow_user(hub_info: dict, db: Session) -> models.UserMapping:
    """Find or create a user mapping for a Hub SSO login.

    Automatically provisions the user on Matrix if not yet provisioned.
    """
    from app.hub_sso import map_hub_role
    from app.services.user_provisioning import provision_matrix_user

    username = hub_info["username"]
    mapping = (
        db.query(models.UserMapping)
        .filter(models.UserMapping.hub_user_id == username)
        .first()
    )
    if mapping is None:
        # No mapping at all – provision on Matrix directly
        try:
            mapping = await provision_matrix_user(
                hub_user_id=username,
                display_name=hub_info.get("display_name", username),
                tenant_id=hub_info.get("tenant_id"),
                db=db,
            )
        except Exception:
            logger.warning("Matrix provisioning failed for new user %s, creating shadow user", username)
            matrix_user_id = f"@{username}:hub.local"
            mapping = models.UserMapping(
                hub_user_id=username,
                matrix_user_id=matrix_user_id,
                tenant_id=hub_info.get("tenant_id"),
                display_name=hub_info.get("display_name", username),
                is_bot=False,
            )
            db.add(mapping)
            db.commit()
            db.refresh(mapping)
    else:
        changed = False
        if hub_info.get("display_name") and mapping.display_name != hub_info["display_name"]:
            mapping.display_name = hub_info["display_name"]
            changed = True
        if hub_info.get("tenant_id") and mapping.tenant_id != hub_info["tenant_id"]:
            mapping.tenant_id = hub_info["tenant_id"]
            changed = True
        if changed:
            db.commit()
            db.refresh(mapping)

        # Provision on Matrix if not yet done
        if not mapping.matrix_access_token_encrypted:
            try:
                mapping = await provision_matrix_user(
                    hub_user_id=username,
                    display_name=mapping.display_name,
                    tenant_id=mapping.tenant_id,
                    db=db,
                )
            except Exception:
                logger.warning("Matrix provisioning failed for existing user %s", username)

    return mapping


async def get_current_user(
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme),
) -> models.UserMapping:
    """Authenticate via Hub SSO token or local JWT."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    # 1. Try Hub SSO token
    from app.hub_sso import is_sso_enabled, validate_hub_token

    if is_sso_enabled():
        hub_info = validate_hub_token(token)
        if hub_info:
            return await _get_or_create_hub_shadow_user(hub_info, db)

    # 2. Fallback to local JWT
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    mapping = (
        db.query(models.UserMapping)
        .filter(models.UserMapping.hub_user_id == username)
        .first()
    )
    if mapping is None:
        raise credentials_exception

    # Auto-provision existing local JWT users on Matrix if needed
    if not mapping.matrix_access_token_encrypted:
        try:
            from app.services.user_provisioning import provision_matrix_user
            mapping = await provision_matrix_user(
                hub_user_id=username,
                display_name=mapping.display_name,
                tenant_id=mapping.tenant_id,
                db=db,
            )
        except Exception:
            logger.warning("Matrix provisioning failed for local user %s", username)

    return mapping
