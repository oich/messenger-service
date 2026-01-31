import logging
import sys
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import LOG_LEVEL
from app.database import engine, SessionLocal, Base
from app import models
from app.routers import auth, messages, rooms, users, notifications, health, sse
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LogRequestsMiddleware:
    """Pure ASGI middleware for request logging.

    Unlike @app.middleware("http") / BaseHTTPMiddleware, this does NOT
    buffer streaming responses, so SSE connections work correctly.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        # Skip logging for SSE streaming endpoints (don't interfere at all)
        if path.startswith("/api/v1/events"):
            await self.app(scope, receive, send)
            return

        start_time = time.time()
        status_code = None

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 0)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            duration = time.time() - start_time
            method = scope.get("method", "?")
            logger.exception(
                "Unhandled exception during '%s %s' after %.4fs",
                method, path, duration,
            )
            raise
        else:
            duration = time.time() - start_time
            method = scope.get("method", "?")
            logger.info(
                "'%s %s' - Status: %s - Duration: %.4fs",
                method, path, status_code, duration,
            )


app.add_middleware(LogRequestsMiddleware)


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
app.include_router(auth.router)
app.include_router(messages.router)
app.include_router(rooms.router)
app.include_router(users.router)
app.include_router(notifications.router)
app.include_router(sse.router)


@app.get("/")
def read_root():
    return {"message": "Messenger Service API"}
