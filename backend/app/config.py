"""Centralized configuration from environment variables."""

import logging
import os
import warnings

logger = logging.getLogger(__name__)

# Environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
IS_PRODUCTION = ENVIRONMENT in ("production", "prod")

# Database
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set.")

# Security - SECRET_KEY validation
_DEFAULT_SECRET = "messenger-dev-secret-change-me"
SECRET_KEY = os.getenv("SECRET_KEY", "")

if not SECRET_KEY:
    if IS_PRODUCTION:
        raise RuntimeError(
            "SECRET_KEY environment variable MUST be set in production! "
            "Generate one with: openssl rand -hex 32"
        )
    logger.warning("SECRET_KEY not set - using insecure default for development")
    warnings.warn("SECRET_KEY not set - using insecure default!", UserWarning)
    SECRET_KEY = _DEFAULT_SECRET
elif SECRET_KEY == _DEFAULT_SECRET:
    logger.warning("SECRET_KEY is set to the default value - change it for production!")

# Encryption key for sensitive data (Matrix tokens, passwords)
# Must be a 32-byte key encoded as hex (64 characters) or base64
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "")
if not ENCRYPTION_KEY:
    if IS_PRODUCTION:
        raise RuntimeError(
            "ENCRYPTION_KEY environment variable MUST be set in production! "
            "Generate one with: openssl rand -hex 32"
        )
    # Development default - DO NOT USE IN PRODUCTION
    logger.warning("ENCRYPTION_KEY not set - using insecure default for development")
    ENCRYPTION_KEY = "0" * 64  # 32 bytes of zeros in hex - insecure!

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "40320"))

# Hub SSO
HUB_SECRET_KEY = os.getenv("HUB_SECRET_KEY")

# Matrix / Conduit
MATRIX_HOMESERVER_URL = os.getenv("MATRIX_HOMESERVER_URL", "http://conduit:6167")
MATRIX_SERVER_NAME = os.getenv("MATRIX_SERVER_NAME", "hub.local")
MATRIX_ADMIN_USER = os.getenv("MATRIX_ADMIN_USER", "@admin:hub.local")
MATRIX_ADMIN_PASSWORD = os.getenv("MATRIX_ADMIN_PASSWORD", "admin-secret")
MATRIX_AS_TOKEN = os.getenv("MATRIX_AS_TOKEN", "messenger-as-token-change-me")
MATRIX_HS_TOKEN = os.getenv("MATRIX_HS_TOKEN", "messenger-hs-token-change-me")

# Cross-App Notification
MESSENGER_SERVICE_TOKEN = os.getenv("MESSENGER_SERVICE_TOKEN", "messenger-service-token-change-me")

# CORS - use whitelist in production
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "info").strip().lower()
