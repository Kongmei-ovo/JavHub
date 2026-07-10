#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_PATH="${JAVHUB_CONFIG_PATH:-${ROOT_DIR}/config.yaml}"
CONTAINER_NAME="${JAVHUB_FLARESOLVERR_CONTAINER:-javhub-flaresolverr-local}"
IMAGE="${JAVHUB_FLARESOLVERR_IMAGE:-ghcr.io/flaresolverr/flaresolverr:latest}"
MANAGED_LABEL_KEY="com.kongmei.javhub.local-flaresolverr"
MANAGED_LABEL="${MANAGED_LABEL_KEY}=true"
HEALTH_URL="http://127.0.0.1:8191/"
HEALTH_ATTEMPTS="${JAVHUB_FLARESOLVERR_HEALTH_ATTEMPTS:-60}"
HEALTH_INTERVAL="${JAVHUB_FLARESOLVERR_HEALTH_INTERVAL:-1}"

if [[ -x "${ROOT_DIR}/.venv/bin/python" ]]; then
  PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
else
  PYTHON_BIN="${PYTHON_BIN:-python3}"
fi

usage() {
  cat <<'USAGE'
Usage: scripts/local-flaresolverr.sh <ensure|restart|stop|status|doctor|logs> [--no-follow]
USAGE
}

configured_solver_url() {
  CONFIG_PATH="${CONFIG_PATH}" "${PYTHON_BIN}" <<'PY'
from pathlib import Path
import os

try:
    import yaml
    path = Path(os.environ["CONFIG_PATH"])
    data = yaml.safe_load(path.read_text()) if path.is_file() else {}
    print(str(((data or {}).get("stream") or {}).get("cf_solver_url") or "").strip(), end="")
except Exception:
    pass
PY
}

should_manage() {
  case "${JAVHUB_LOCAL_FLARESOLVERR:-auto}" in
    1|true|yes|on) return 0 ;;
    0|false|no|off) return 1 ;;
    auto|"") ;;
    *)
      echo "Invalid JAVHUB_LOCAL_FLARESOLVERR value: ${JAVHUB_LOCAL_FLARESOLVERR}" >&2
      return 2
      ;;
  esac

  local url
  url="$(configured_solver_url)"
  [[ "${url}" =~ ^https?://(127\.0\.0\.1|localhost):8191(/|$) ]]
}

print_skip_reason() {
  case "${JAVHUB_LOCAL_FLARESOLVERR:-auto}" in
    0|false|no|off) echo "local FlareSolverr: disabled by JAVHUB_LOCAL_FLARESOLVERR" ;;
    *) echo "local FlareSolverr: skipped (stream.cf_solver_url is not localhost:8191)" ;;
  esac
}

docker_daemon_ready() {
  command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1
}

ensure_docker_daemon() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "local FlareSolverr: docker CLI not found" >&2
    return 1
  fi
  if docker_daemon_ready; then
    return 0
  fi
  if [[ "$(uname -s)" == "Darwin" ]] && command -v colima >/dev/null 2>&1; then
    echo "local FlareSolverr: Docker daemon unavailable; starting Colima"
    colima start
  else
    echo "local FlareSolverr: Docker daemon unavailable" >&2
    return 1
  fi
  if ! docker_daemon_ready; then
    echo "local FlareSolverr: Docker daemon still unavailable after Colima start" >&2
    return 1
  fi
}

container_exists() {
  docker inspect "${CONTAINER_NAME}" >/dev/null 2>&1
}

container_is_owned() {
  [[ "$(docker inspect --format "{{ index .Config.Labels \"${MANAGED_LABEL_KEY}\" }}" "${CONTAINER_NAME}" 2>/dev/null || true)" == "true" ]]
}

require_owned_container() {
  if container_exists && ! container_is_owned; then
    echo "local FlareSolverr: container ${CONTAINER_NAME} exists but is not managed by JavHub" >&2
    return 1
  fi
}

container_is_running() {
  [[ "$(docker inspect --format '{{.State.Running}}' "${CONTAINER_NAME}" 2>/dev/null || true)" == "true" ]]
}

container_configuration_matches() {
  local configured_image published_port
  configured_image="$(docker inspect --format '{{.Config.Image}}' "${CONTAINER_NAME}" 2>/dev/null || true)"
  published_port="$(docker port "${CONTAINER_NAME}" 8191/tcp 2>/dev/null || true)"
  [[ "${configured_image}" == "${IMAGE}" && "${published_port}" == *"127.0.0.1:8191"* ]]
}

port_is_in_use() {
  command -v lsof >/dev/null 2>&1 && lsof -nP -iTCP:8191 -sTCP:LISTEN 2>/dev/null | awk 'NR > 1 { found=1 } END { exit found ? 0 : 1 }'
}

create_container() {
  if port_is_in_use; then
    echo "local FlareSolverr: port 8191 is already used by another process" >&2
    return 1
  fi
  docker run -d \
    --name "${CONTAINER_NAME}" \
    --label "${MANAGED_LABEL}" \
    --restart unless-stopped \
    -p "127.0.0.1:8191:8191" \
    -e "LOG_LEVEL=${FLARESOLVERR_LOG_LEVEL:-info}" \
    -e "TZ=${TZ:-Asia/Shanghai}" \
    "${IMAGE}" >/dev/null
}

health_is_ok() {
  command -v curl >/dev/null 2>&1 && curl -fsS --max-time 3 "${HEALTH_URL}" >/dev/null 2>&1
}

wait_for_health() {
  local attempt
  for ((attempt = 1; attempt <= HEALTH_ATTEMPTS; attempt++)); do
    if health_is_ok; then
      echo "FlareSolverr ${HEALTH_URL}: ok"
      return 0
    fi
    if [[ "${HEALTH_INTERVAL}" != "0" ]]; then
      sleep "${HEALTH_INTERVAL}"
    fi
  done
  echo "local FlareSolverr: health check timed out; run scripts/services.sh logs flaresolverr" >&2
  return 1
}

ensure_container() {
  ensure_docker_daemon
  require_owned_container
  if container_exists; then
    if ! container_configuration_matches; then
      docker rm -f "${CONTAINER_NAME}" >/dev/null
      create_container
    elif ! container_is_running; then
      docker start "${CONTAINER_NAME}" >/dev/null
    fi
  else
    create_container
  fi
  wait_for_health
}

ensure_command() {
  if ! should_manage; then
    local result=$?
    if [[ "${result}" == "2" ]]; then return 2; fi
    print_skip_reason
    return 0
  fi
  ensure_container
}

restart_command() {
  if ! should_manage; then print_skip_reason; return 0; fi
  ensure_docker_daemon
  require_owned_container
  if container_exists; then docker rm -f "${CONTAINER_NAME}" >/dev/null; fi
  create_container
  wait_for_health
}

stop_command() {
  if ! should_manage; then print_skip_reason; return 0; fi
  ensure_docker_daemon
  require_owned_container
  if container_exists; then
    docker rm -f "${CONTAINER_NAME}" >/dev/null
    echo "local FlareSolverr: stopped"
  else
    echo "local FlareSolverr: already stopped"
  fi
}

status_command() {
  if ! should_manage; then print_skip_reason; return 0; fi
  echo
  echo "Local FlareSolverr:"
  if ! docker_daemon_ready; then echo "docker daemon: unavailable"; return 1; fi
  if ! container_exists; then echo "container ${CONTAINER_NAME}: missing"; return 1; fi
  if ! container_is_owned; then echo "container ${CONTAINER_NAME}: not managed by JavHub"; return 1; fi
  if container_is_running; then echo "container ${CONTAINER_NAME}: running"; else echo "container ${CONTAINER_NAME}: stopped"; return 1; fi
  if health_is_ok; then echo "FlareSolverr ${HEALTH_URL}: ok"; else echo "FlareSolverr ${HEALTH_URL}: failed"; return 1; fi
}

doctor_command() {
  if ! should_manage; then print_skip_reason; return 0; fi
  local failed=0
  echo "Local FlareSolverr dependencies:"
  if command -v docker >/dev/null 2>&1; then echo "docker CLI: ok ($(command -v docker))"; else echo "docker CLI: missing"; failed=1; fi
  if [[ "$(uname -s)" == "Darwin" ]]; then
    if command -v colima >/dev/null 2>&1; then echo "colima: ok ($(command -v colima))"; else echo "colima: missing"; failed=1; fi
  fi
  if command -v curl >/dev/null 2>&1; then echo "curl: ok ($(command -v curl))"; else echo "curl: missing"; failed=1; fi
  return "${failed}"
}

logs_command() {
  local follow=1
  if [[ $# -gt 1 ]]; then usage >&2; return 2; fi
  if [[ $# -eq 1 ]]; then
    case "$1" in --no-follow) follow=0 ;; *) usage >&2; return 2 ;; esac
  fi
  if ! should_manage; then print_skip_reason; return 0; fi
  ensure_docker_daemon
  require_owned_container
  if ! container_exists; then echo "local FlareSolverr: container is missing" >&2; return 1; fi
  if [[ "${follow}" == "1" ]]; then docker logs --tail 120 --follow "${CONTAINER_NAME}"; else docker logs --tail 120 "${CONTAINER_NAME}"; fi
}

command="${1:-}"
shift || true
case "${command}" in
  ensure) [[ $# -eq 0 ]] || { usage >&2; exit 2; }; ensure_command ;;
  restart) [[ $# -eq 0 ]] || { usage >&2; exit 2; }; restart_command ;;
  stop) [[ $# -eq 0 ]] || { usage >&2; exit 2; }; stop_command ;;
  status) [[ $# -eq 0 ]] || { usage >&2; exit 2; }; status_command ;;
  doctor) [[ $# -eq 0 ]] || { usage >&2; exit 2; }; doctor_command ;;
  logs) logs_command "$@" ;;
  -h|--help|help|"") usage ;;
  *) echo "Unknown command: ${command}" >&2; usage >&2; exit 2 ;;
esac
