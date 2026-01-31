#!/bin/bash
set -e

echo "Running database migrations..."
alembic upgrade head 2>&1 || {
    echo "Alembic upgrade failed — stamping head for fresh DB..."
    alembic stamp head 2>&1 || true
}

echo "Starting Messenger Service Backend..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
