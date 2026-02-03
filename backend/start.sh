#!/bin/bash
set -e

# Add shared packages to Python path if available
if [ -d /opt/hub_sync_client ] || [ -d /opt/hub_messenger_client ] || [ -d /opt/satellite_api_client ]; then
  export PYTHONPATH="/opt:${PYTHONPATH:-}"
fi

echo "Running database migrations..."
alembic upgrade head 2>&1 || {
    echo "Alembic upgrade failed — stamping head for fresh DB..."
    alembic stamp head 2>&1 || true
}

echo "Starting Messenger Service Backend..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
