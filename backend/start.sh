#!/bin/bash
set -e

# Add shared packages to Python path if available
if [ -d /opt/hub_sync_client ] || [ -d /opt/hub_messenger_client ] || [ -d /opt/satellite_api_client ]; then
  export PYTHONPATH="/opt:${PYTHONPATH:-}"
fi

# Auto-Migration wenn aktiviert (Standard: an)
AUTO_FLAG="${AUTO_MIGRATE:-1}"
case "$(printf "%s" "$AUTO_FLAG" | tr '[:upper:]' '[:lower:]')" in
  1|true|yes)
    echo "[start] Running Alembic migrations..."
    alembic upgrade head 2>&1 || {
        echo "[start] Alembic upgrade failed — stamping head for fresh DB..."
        alembic stamp head 2>&1 || true
    }
    echo "[start] Alembic migrations done."
    ;;
  *)
    echo "[start] AUTO_MIGRATE disabled. Skipping migrations."
    ;;
esac

echo "[start] Starting Messenger Service Backend..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers "${UVICORN_WORKERS:-1}"
