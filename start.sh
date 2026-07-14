#!/bin/sh
set -e

if [ "${RUN_MIGRATIONS_ON_START:-true}" = "true" ]; then
  echo "Applying database migrations..."
  alembic upgrade head
fi

echo "Starting FastAPI server..."
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --proxy-headers \
  --forwarded-allow-ips="*"
