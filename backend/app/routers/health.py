import logging

from fastapi import APIRouter

from app.services.matrix_client import matrix_client, MatrixClientError

logger = logging.getLogger("health")
router = APIRouter(tags=["health"])


@router.get("/api/v1/health")
async def health_check():
    conduit_ok = False
    try:
        versions = await matrix_client.server_versions()
        conduit_ok = bool(versions.get("versions"))
    except MatrixClientError:
        pass
    except Exception:
        pass

    return {
        "status": "ok" if conduit_ok else "degraded",
        "service": "messenger-service",
        "conduit": "connected" if conduit_ok else "unreachable",
    }
