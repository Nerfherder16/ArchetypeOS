#!/usr/bin/env sh
set -e

# Apply database migrations before serving. `set -e` guarantees that a failed
# migration exits non-zero so the container never starts uvicorn — a broken
# schema is surfaced (health never responds), never masked.
alembic upgrade head

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
