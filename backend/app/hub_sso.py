"""Hub SSO integration for messenger-service satellite.

When HUB_SECRET_KEY is set, validates JWT tokens issued by the AESystek Hub.
When absent, SSO is disabled and the satellite operates standalone.
"""

import logging
from typing import Optional

from jose import JWTError, jwt

from app.config import HUB_SECRET_KEY

logger = logging.getLogger("hub_sso")

HUB_ALGORITHM = "HS256"

HUB_ROLE_MAP = {
    "super_admin": "admin",
    "admin": "admin",
    "manager": "user",
    "user": "user",
    "viewer": "viewer",
}


def is_sso_enabled() -> bool:
    return bool(HUB_SECRET_KEY)


def validate_hub_token(token: str) -> Optional[dict]:
    if not HUB_SECRET_KEY:
        return None
    try:
        payload = jwt.decode(
            token,
            HUB_SECRET_KEY,
            algorithms=[HUB_ALGORITHM],
            options={"verify_aud": False},
        )
    except JWTError as e:
        logger.debug("Hub token validation failed: %s", e)
        return None
    if payload.get("iss") != "aesystek-hub":
        return None
    username = payload.get("sub")
    if not username:
        return None
    return {
        "username": username,
        "role": payload.get("role", "viewer"),
        "tenant_id": payload.get("tenant_id"),
        "display_name": payload.get("display_name", username),
    }


def map_hub_role(hub_role: str) -> str:
    return HUB_ROLE_MAP.get(hub_role, "viewer")
