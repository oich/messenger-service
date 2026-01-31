import logging
import sys
import time

from fastapi import FastAPI, Request
from starlette.types import ASGIApp, Receive, Scope, Send, Message

from app.config import LOG_LEVEL
from app.database import engine, SessionLocal, Base
from app import models
from app.routers import admin, auth, messages, rooms, users, notifications, health, sse
from app.services.user_provisioning import provision_bot_user
from app.services.matrix_client import matrix_client

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


class CORSAndLoggingMiddleware:
    """Combined CORS + request logging as pure ASGI middleware.

    SSE streaming paths (/api/v1/events/stream) are passed through
    with zero wrapping to avoid any response buffering.
    """

    CORS_HEADERS = [
        (b"access-control-allow-origin", b"*"),
        (b"access-control-allow-credentials", b"true"),
        (b"access-control-allow-methods", b"*"),
        (b"access-control-allow-headers", b"*"),
    ]

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        method = scope.get("method", "")

        # Handle CORS preflight
        if method == "OPTIONS":
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": self.CORS_HEADERS + [
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
                    headers.extend(self.CORS_HEADERS)
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
                headers.extend(self.CORS_HEADERS)
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
