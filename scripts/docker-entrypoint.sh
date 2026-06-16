#!/bin/sh
set -eu

initialize_config() {
  config_path="${JAVHUB_CONFIG_PATH:-/config/config.yaml}"
  config_example="${JAVHUB_CONFIG_EXAMPLE:-/app/config.yaml.example}"
  export JAVHUB_CONFIG_PATH="$config_path"

  if [ -d "$config_path" ]; then
    echo "JAVHUB_CONFIG_PATH '$config_path' is a directory; expected a YAML file." >&2
    echo "Remove the directory or mount a config directory such as './config:/config'." >&2
    return 1
  fi

  if [ ! -e "$config_path" ]; then
    if [ ! -f "$config_example" ]; then
      echo "Config file '$config_path' is missing and example '$config_example' was not found." >&2
      return 1
    fi

    mkdir -p "$(dirname "$config_path")"
    cp "$config_example" "$config_path"
    echo "Created default config at '$config_path'."
  fi
}

initialize_config

if [ "${JAVHUB_ENTRYPOINT_INIT_ONLY:-}" = "1" ]; then
  exit 0
fi

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
