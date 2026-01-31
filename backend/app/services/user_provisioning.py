"""Auto-provision Matrix users for Hub users."""

import logging
import secrets

from sqlalchemy.orm import Session

from app.config import MATRIX_SERVER_NAME
from app.models import UserMapping
from app.services.matrix_client import matrix_client, MatrixClientError

logger = logging.getLogger("user_provisioning")


async def provision_matrix_user(
    hub_user_id: str,
    display_name: str,
    tenant_id: int | None,
    db: Session,
) -> UserMapping:
    """Ensure a Matrix user exists for the given Hub user.

    If no mapping exists, registers the user on Conduit and stores the mapping.
    Returns the UserMapping with a valid matrix_access_token_encrypted.
    """
    mapping = (
        db.query(UserMapping)
        .filter(UserMapping.hub_user_id == hub_user_id)
        .first()
    )

    if mapping and mapping.matrix_access_token_encrypted:
        return mapping

    matrix_localpart = hub_user_id.lower().replace(" ", "_")
    matrix_user_id = f"@{matrix_localpart}:{MATRIX_SERVER_NAME}"
    password = secrets.token_urlsafe(32)

    try:
        result = await matrix_client.register_user(
            username=matrix_localpart,
            password=password,
            admin=False,
        )
        access_token = result.get("access_token", "")
    except MatrixClientError as e:
        logger.error("Failed to provision Matrix user %s: %s", hub_user_id, e)
        raise

    # Set display name
    if access_token and display_name:
        try:
            await matrix_client.set_display_name(access_token, matrix_user_id, display_name)
        except MatrixClientError:
            logger.warning("Failed to set display name for %s", matrix_user_id)

    if mapping is None:
        mapping = UserMapping(
            hub_user_id=hub_user_id,
            matrix_user_id=matrix_user_id,
            matrix_access_token_encrypted=access_token,
            matrix_password=password,
            tenant_id=tenant_id,
            display_name=display_name,
            is_bot=False,
        )
        db.add(mapping)
    else:
        mapping.matrix_access_token_encrypted = access_token
        mapping.matrix_user_id = matrix_user_id
        mapping.matrix_password = password
        if display_name:
            mapping.display_name = display_name
        if tenant_id:
            mapping.tenant_id = tenant_id

    db.commit()
    db.refresh(mapping)
    return mapping


async def provision_bot_user(
    bot_name: str,
    display_name: str,
    db: Session,
) -> UserMapping:
    """Provision a bot user for automated notifications."""
    mapping = (
        db.query(UserMapping)
        .filter(UserMapping.hub_user_id == bot_name, UserMapping.is_bot == True)
        .first()
    )

    if mapping and mapping.matrix_access_token_encrypted:
        return mapping

    matrix_localpart = f"bot_{bot_name}"
    matrix_user_id = f"@{matrix_localpart}:{MATRIX_SERVER_NAME}"
    password = secrets.token_urlsafe(32)

    try:
        result = await matrix_client.register_user(
            username=matrix_localpart,
            password=password,
            admin=False,
        )
        access_token = result.get("access_token", "")
    except MatrixClientError as e:
        logger.error("Failed to provision bot user %s: %s", bot_name, e)
        raise

    if access_token and display_name:
        try:
            await matrix_client.set_display_name(access_token, matrix_user_id, display_name)
        except MatrixClientError:
            pass

    if mapping is None:
        mapping = UserMapping(
            hub_user_id=bot_name,
            matrix_user_id=matrix_user_id,
            matrix_access_token_encrypted=access_token,
            tenant_id=None,
            display_name=display_name,
            is_bot=True,
        )
        db.add(mapping)
    else:
        mapping.matrix_access_token_encrypted = access_token

    db.commit()
    db.refresh(mapping)
    return mapping
