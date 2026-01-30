#!/bin/bash
set -e

echo "Starting Messenger Service Backend..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
