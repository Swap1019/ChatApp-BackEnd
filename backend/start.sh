#!/bin/sh
set -eu

# Start local Redis inside the same container
redis-server --save "" --appendonly no --bind 127.0.0.1 --port 6379 --daemonize yes

# Start Celery worker
celery -A backend worker --loglevel=INFO &
CELERY_PID=$!

# Start Django ASGI app
gunicorn backend.asgi:application \
  -k uvicorn_worker.UvicornWorker \
  -w 1 \
  -b 0.0.0.0:8000 \
  --timeout 120 \
  --log-level info &
GUNICORN_PID=$!

cleanup() {
  kill -TERM "$GUNICORN_PID" "$CELERY_PID" 2>/dev/null || true
  wait "$GUNICORN_PID" 2>/dev/null || true
  wait "$CELERY_PID" 2>/dev/null || true
}

trap cleanup INT TERM

# Wait until one process exits
while kill -0 "$GUNICORN_PID" 2>/dev/null && kill -0 "$CELERY_PID" 2>/dev/null; do
  sleep 1
done

EXIT_CODE=0
if ! kill -0 "$GUNICORN_PID" 2>/dev/null; then
  wait "$GUNICORN_PID" || EXIT_CODE=$?
else
  wait "$CELERY_PID" || EXIT_CODE=$?
fi

cleanup
exit "$EXIT_CODE"
