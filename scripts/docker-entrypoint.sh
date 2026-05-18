#!/bin/sh
set -eu

uvicorn main:app --host 127.0.0.1 --port 8000 &
backend_pid="$!"

nginx -g "daemon off;" &
nginx_pid="$!"

shutdown() {
  kill -TERM "$backend_pid" "$nginx_pid" 2>/dev/null || true
  wait "$backend_pid" 2>/dev/null || true
  wait "$nginx_pid" 2>/dev/null || true
}

trap 'shutdown; exit 0' INT TERM

while true; do
  if ! kill -0 "$backend_pid" 2>/dev/null; then
    set +e
    wait "$backend_pid"
    status="$?"
    set -e
    kill -TERM "$nginx_pid" 2>/dev/null || true
    wait "$nginx_pid" 2>/dev/null || true
    exit "$status"
  fi

  if ! kill -0 "$nginx_pid" 2>/dev/null; then
    set +e
    wait "$nginx_pid"
    status="$?"
    set -e
    kill -TERM "$backend_pid" 2>/dev/null || true
    wait "$backend_pid" 2>/dev/null || true
    exit "$status"
  fi

  sleep 1
done
