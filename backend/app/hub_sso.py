"""Hub SSO integration for messenger-service satellite.

When HUB_SECRET_KEY is set, validates JWT tokens issued by the AESystek Hub.
When absent, SSO is disabled and the satellite operates standalone.
"""

import logging
import os
from typing import Optional

from jose import JWTError, jwt

from app.config import HUB_SECRET_KEY

logger = logging.getLogger("hub_sso")

HUB_ALGORITHM = "HS256"

# Mindest-Rolle, die der Hub-User fuer DIESEN Satelliten braucht (muss mit der
# App.required_role im Hub-App-Registry uebereinstimmen - siehe
# hub-backend/app/services/app_registry_service.py). Ohne diesen Check
# akzeptierte der Satellit jedes gueltig signierte Hub-JWT unabhaengig von der
# App-Berechtigung im Hub (/permissions). None/unset = keine Einschraenkung.
HUB_MIN_ROLE: Optional[str] = os.getenv("HUB_MIN_ROLE") or None

ROLE_HIERARCHY = {
    "super_admin": 0,
    "admin": 1,
    "manager": 2,
    "user": 3,
    "terminal": 4,
    "viewer": 5,
}


def _meets_min_role(role: str) -> bool:
    if not HUB_MIN_ROLE:
        return True
    if role in ("admin", "super_admin"):
        return True
    return ROLE_HIERARCHY.get(role, 99) <= ROLE_HIERARCHY.get(HUB_MIN_ROLE, 99)


HUB_ROLE_MAP = {
    "super_admin": "admin",
    "admin": "admin",
    "manager": "user",
    "user": "user",
    "terminal": "user",
    "viewer": "viewer",
}


def is_sso_enabled() -> bool:
    return bool(HUB_SECRET_KEY)


def _role_for(payload: dict) -> str:
    """Rolle aus dem Token. Service-to-service-Tokens tragen keinen role-Claim,
    sind aber nur mit HUB_SECRET_KEY signierbar (vertrauenswuerdiger interner
    Aufrufer) -> admin. Formate: "satellite-service" (hub_sync_client),
    "service:<slug>" (satellite_api_client), "<app>-service" (service_token.py).
    """
    role = payload.get("role")
    if role:
        return role
    sub = str(payload.get("sub") or "")
    if sub == "satellite-service" or sub.startswith("service:") or sub.endswith("-service"):
        return "admin"
    return "viewer"


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
    role = _role_for(payload)
    if not _meets_min_role(role):
        logger.warning("Hub token role '%s' insufficient for HUB_MIN_ROLE '%s'", role, HUB_MIN_ROLE)
        return None
    return {
        "username": username,
        "role": role,
        "tenant_id": payload.get("tenant_id"),
        "display_name": payload.get("display_name", username),
    }


def map_hub_role(hub_role: str) -> str:
    return HUB_ROLE_MAP.get(hub_role, "viewer")
