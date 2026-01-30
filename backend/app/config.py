"""Centralized configuration from environment variables."""

import os


# Database
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set.")

# Security
SECRET_KEY = os.getenv("SECRET_KEY", "messenger-dev-secret-change-me")
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

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "info").strip().lower()
