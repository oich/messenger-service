import logging
import sys
import time

from fastapi import FastAPI, Request
from starlette.types import ASGIApp, Receive, Scope, Send, Message

from app.config import LOG_LEVEL, ALLOWED_ORIGINS, IS_PRODUCTION
from app.database import engine, SessionLocal, Base
from app import models
from app.models.user_mapping import UserMapping
from app.routers import admin, auth, messages, rooms, users, notifications, health, sse
from app.services.user_provisioning import provision_bot_user
from app.services.matrix_client import matrix_client
from app.services.encryption import migrate_encrypt_if_needed

# Logging
_level_map = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}
_level = _level_map.get(LOG_LEVEL, logging.INFO)
logging.basicConfig(
    stream=sys.stdout,
    level=_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger("messenger_api")
logger.setLevel(_level)
logger.propagate = True

app = FastAPI(
    title="Messenger Service API",
    description="Cross-App Messaging and Notifications via Matrix/Conduit",
    version="1.0.0",
)


def _get_cors_origins() -> list[str]:
    """Get allowed CORS origins from environment or use secure defaults."""
    if ALLOWED_ORIGINS:
        return [o.strip() for o in ALLOWED_ORIGINS.split(",") if o.strip()]

    if IS_PRODUCTION:
        logger.warning(
            "ALLOWED_ORIGINS not set in production! "
            "Set ALLOWED_ORIGINS environment variable (comma-separated list of allowed origins)."
        )
        return []

    # Development mode - allow common local origins
    return [
        "http://localhost",
        "https://localhost",
        "http://localhost:443",
        "https://localhost:443",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8085",
        "https://localhost:8085",
        "http://127.0.0.1",
        "https://127.0.0.1",
        "http://127.0.0.1:443",
        "https://127.0.0.1:443",
    ]


class CORSAndLoggingMiddleware:
    """Combined CORS + request logging as pure ASGI middleware.

    SSE streaming paths (/api/v1/events/stream) are passed through
    with zero wrapping to avoid any response buffering.

    Uses CORS whitelist in production, allows all in development.
    """

    def __init__(self, app: ASGIApp):
        self.app = app
        self._allowed_origins = _get_cors_origins()
        self._allow_all = not self._allowed_origins and not IS_PRODUCTION
        logger.info(
            "CORS allowed origins: %s",
            self._allowed_origins if self._allowed_origins else "(all origins in dev mode)"
        )

    def _get_cors_headers(self, request_origin: str = "") -> list[tuple[bytes, bytes]]:
        """Build CORS headers based on the request origin."""
        # Determine allowed origin
        if self._allow_all:
            origin = b"*"
        elif request_origin in self._allowed_origins:
            origin = request_origin.encode("utf-8")
        elif self._allowed_origins:
            origin = self._allowed_origins[0].encode("utf-8")
        else:
            origin = b""

        return [
            (b"access-control-allow-origin", origin),
            (b"access-control-allow-credentials", b"true"),
            (b"access-control-allow-methods", b"GET, POST, PUT, DELETE, PATCH, OPTIONS"),
            (b"access-control-allow-headers", b"Authorization, Content-Type, X-Requested-With"),
        ]

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        method = scope.get("method", "")

        # Extract request origin for CORS
        request_origin = ""
        for header_name, header_value in scope.get("headers", []):
            if header_name == b"origin":
                request_origin = header_value.decode("utf-8", errors="replace")
                break

        cors_headers = self._get_cors_headers(request_origin)

        # Handle CORS preflight
        if method == "OPTIONS":
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": cors_headers + [
                    (b"access-control-max-age", b"600"),
                    (b"content-length", b"0"),
                ],
            })
            await send({"type": "http.response.body", "body": b""})
            return

        # SSE stream: pass through completely — no wrapping, no logging
        if path == "/api/v1/events/stream":
            async def sse_send(message: Message):
                if message["type"] == "http.response.start":
                    headers = list(message.get("headers", []))
                    headers.extend(cors_headers)
                    message = {**message, "headers": headers}
                await send(message)

            await self.app(scope, receive, sse_send)
            return

        # All other requests: add CORS headers + log
        start_time = time.time()
        status_code = None

        async def send_wrapper(message: Message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 0)
                headers = list(message.get("headers", []))
                headers.extend(cors_headers)
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            duration = time.time() - start_time
            logger.exception(
                "Unhandled exception during '%s %s' after %.4fs",
                method, path, duration,
            )
            raise
        else:
            duration = time.time() - start_time
            logger.info(
                "'%s %s' - Status: %s - Duration: %.4fs",
                method, path, status_code, duration,
            )


app.add_middleware(CORSAndLoggingMiddleware)


@app.on_event("startup")
async def on_startup():
    # Create all tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified.")

    # Auto-migrate plaintext tokens to encrypted format
    db = SessionLocal()
    try:
        _migrate_plaintext_tokens(db)
    except Exception as e:
        logger.warning("Token migration failed (non-fatal): %s", e)
    finally:
        db.close()

    # Provision notification bot
    db = SessionLocal()
    try:
        try:
            await provision_bot_user(
                bot_name="notification_bot",
                display_name="Notification Bot",
                db=db,
            )
            logger.info("Notification bot provisioned.")
        except Exception as e:
            logger.warning(
                "Could not provision notification bot (Conduit may not be ready): %s", e
            )
    finally:
        db.close()


def _migrate_plaintext_tokens(db) -> None:
    """Migrate plaintext Matrix tokens to encrypted format.

    This runs automatically on startup to ensure all tokens are encrypted.
    Tokens are detected as plaintext if they don't have the encryption prefix.
    """
    from app.services.encryption import is_encrypted, encrypt_token

    users = db.query(UserMapping).all()
    migrated_count = 0

    for user in users:
        updated = False

        # Migrate access token
        if user.matrix_access_token_encrypted and not is_encrypted(user.matrix_access_token_encrypted):
            user.matrix_access_token_encrypted = encrypt_token(user.matrix_access_token_encrypted)
            updated = True

        # Migrate password
        if user.matrix_password and not is_encrypted(user.matrix_password):
            user.matrix_password = encrypt_token(user.matrix_password)
            updated = True

        if updated:
            migrated_count += 1

    if migrated_count > 0:
        db.commit()
        logger.info("Migrated %d user(s) to encrypted token storage.", migrated_count)
    else:
        logger.debug("No plaintext tokens found to migrate.")


@app.on_event("shutdown")
async def on_shutdown():
    await matrix_client.close()


# Register routers
app.include_router(health.router)
app.include_router(admin.router)
app.include_router(auth.router)
app.include_router(messages.router)
app.include_router(rooms.router)
app.include_router(users.router)
app.include_router(notifications.router)
app.include_router(sse.router)


@app.get("/")
def read_root():
    return {"message": "Messenger Service API"}
