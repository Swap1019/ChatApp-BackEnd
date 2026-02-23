#!/bin/sh
set -eu

# Start local Redis inside the same container
redis-server --save "" --appendonly no --bind 127.0.0.1 --port 6379 --daemonize yes

# Start Django ASGI app
gunicorn backend.asgi:application \
  -k uvicorn_worker.UvicornWorker \
  -w 1 \
  -b 0.0.0.0:8000 \
  --timeout 120 \
  --log-level info &
GUNICORN_PID=$!

cleanup() {
  kill -TERM "$GUNICORN_PID" 2>/dev/null || true
  wait "$GUNICORN_PID" 2>/dev/null || true
}

trap cleanup INT TERM

# Wait until process exits
while kill -0 "$GUNICORN_PID" 2>/dev/null; do
  sleep 1
done

EXIT_CODE=0
wait "$GUNICORN_PID" || EXIT_CODE=$?

cleanup
exit "$EXIT_CODE"
