import logging
import sys
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

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


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    try:
        response = await call_next(request)
        return response
    except Exception:
        duration = time.time() - start_time
        logger.exception(
            "Unhandled exception during '%s %s' after %.4fs",
            request.method,
            request.url.path,
            duration,
        )
        raise
    finally:
        if "response" in locals():
            duration = time.time() - start_time
            logger.info(
                "'%s %s' - Status: %s - Duration: %.4fs",
                request.method,
                request.url.path,
                response.status_code,
                duration,
            )


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
