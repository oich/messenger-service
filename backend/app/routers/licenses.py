"""License information endpoints for Python and system packages."""
import json
import os

from fastapi import APIRouter

router = APIRouter(tags=["Licenses"])

_PYTHON_LICENSE_FILE = "/opt/licenses-python.json"
_SYSTEM_LICENSE_FILE = "/opt/licenses-system.json"


def _read_license_file(path: str) -> list:
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


@router.get("/python")
def get_python_licenses():
    """Return license information for installed Python packages."""
    return _read_license_file(_PYTHON_LICENSE_FILE)


@router.get("/system")
def get_system_licenses():
    """Return license information for installed system (apt) packages."""
    return _read_license_file(_SYSTEM_LICENSE_FILE)
