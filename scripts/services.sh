#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
JAVINFO_DIR="${JAVINFO_DIR:-/Users/kongmei/Code/JavInfoApi}"
LAUNCH_AGENTS_DIR="${HOME}/Library/LaunchAgents"
UID_VALUE="$(id -u)"

JAVINFO_LABEL="com.kongmei.javinfoapi"
BACKEND_LABEL="com.kongmei.javhub.backend"
FRONTEND_LABEL="com.kongmei.javhub.frontend"

JAVINFO_PLIST="${LAUNCH_AGENTS_DIR}/${JAVINFO_LABEL}.plist"
BACKEND_PLIST="${LAUNCH_AGENTS_DIR}/${BACKEND_LABEL}.plist"
FRONTEND_PLIST="${LAUNCH_AGENTS_DIR}/${FRONTEND_LABEL}.plist"
FRONTEND_DIST_DIR="${JAVHUB_FRONTEND_DIST:-${ROOT_DIR}/frontend/dist}"

if [[ -x "${ROOT_DIR}/.venv/bin/python" ]]; then
  PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
else
  PYTHON_BIN="${PYTHON_BIN:-python3}"
fi

if [[ -n "${NPM_BIN:-}" ]]; then
  FRONTEND_NPM_BIN="${NPM_BIN}"
elif command -v npm >/dev/null 2>&1; then
  FRONTEND_NPM_BIN="$(command -v npm)"
else
  FRONTEND_NPM_BIN="npm"
fi

usage() {
  cat <<'USAGE'
Usage: scripts/services.sh <command> [service]

Commands:
  ensure                                Install/update LaunchAgents and start missing services.
  start                                 Install/update LaunchAgents and start all services.
  doctor                                Check local service dependencies without changing state.
  restart [<javinfo|backend|frontend>]  Restart all services or one service.
  stop [<javinfo|backend|frontend>]     Stop all services or one service.
  status                                Print launchd and port status.
  logs <javinfo|backend|frontend> [--no-follow]
                                        Show service logs, following by default.
  rebuild-javinfo                       Rebuild JavInfoApi binary and restart javinfo.
  render-plists                         Write LaunchAgent plists without starting services.

Environment:
  JAVINFO_DIR         Defaults to /Users/kongmei/Code/JavInfoApi.
  JAVHUB_CONFIG_PATH  Defaults to config.yaml in the JavHub checkout.
USAGE
}

xml_escape() {
  "${PYTHON_BIN}" -c 'import html, sys; print(html.escape(sys.stdin.read().rstrip("\n"), quote=True), end="")'
}

javinfo_source_proxy_url() {
  ROOT_DIR="${ROOT_DIR}" "${PYTHON_BIN}" <<'PY'
from pathlib import Path
import os
import sys

try:
    import yaml
except Exception:
    sys.exit(0)

config_path = Path(os.environ.get("JAVHUB_CONFIG_PATH") or Path(os.environ["ROOT_DIR"]) / "config.yaml")
try:
    data = yaml.safe_load(config_path.read_text()) or {}
except Exception:
    sys.exit(0)

proxy = data.get("proxy") or {}
if not proxy.get("enabled"):
    sys.exit(0)

for key in ("http_url", "https_url"):
    value = str(proxy.get(key) or "").strip()
    if value:
        print(value, end="")
        break
PY
}

write_plists() {
  mkdir -p "${LAUNCH_AGENTS_DIR}"
  local javinfo_source_proxy_url_value javinfo_source_proxy_env
  JAVINFO_PLIST_CHANGED=0
  BACKEND_PLIST_CHANGED=0
  FRONTEND_PLIST_CHANGED=0
  local javinfo_before backend_before frontend_before
  local javinfo_had_plist=0 backend_had_plist=0 frontend_had_plist=0
  javinfo_before="$(mktemp)"
  backend_before="$(mktemp)"
  frontend_before="$(mktemp)"
  if [[ -f "${JAVINFO_PLIST}" ]]; then
    javinfo_had_plist=1
    cp "${JAVINFO_PLIST}" "${javinfo_before}"
  fi
  if [[ -f "${BACKEND_PLIST}" ]]; then
    backend_had_plist=1
    cp "${BACKEND_PLIST}" "${backend_before}"
  fi
  if [[ -f "${FRONTEND_PLIST}" ]]; then
    frontend_had_plist=1
    cp "${FRONTEND_PLIST}" "${frontend_before}"
  fi
  javinfo_source_proxy_url_value="$(javinfo_source_proxy_url)"
  javinfo_source_proxy_env=""
  if [[ -n "${javinfo_source_proxy_url_value}" ]]; then
    local escaped_proxy_url
    escaped_proxy_url="$(printf '%s' "${javinfo_source_proxy_url_value}" | xml_escape)"
    javinfo_source_proxy_env="    <key>JAVINFO_SOURCE_PROXY_URL</key>
    <string>${escaped_proxy_url}</string>"
  fi

  cat > "${JAVINFO_PLIST}" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${JAVINFO_LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${JAVINFO_DIR}/JavInfoApi</string>
  </array>
  <key>WorkingDirectory</key>
  <string>${JAVINFO_DIR}</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    <key>SERVER_PORT</key>
    <string>8080</string>
${javinfo_source_proxy_env}
  </dict>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>${JAVINFO_DIR}/javinfoapi.launchd.log</string>
  <key>StandardErrorPath</key>
  <string>${JAVINFO_DIR}/javinfoapi.launchd.err.log</string>
</dict>
</plist>
EOF

  cat > "${BACKEND_PLIST}" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${BACKEND_LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${ROOT_DIR}/.venv/bin/uvicorn</string>
    <string>main:app</string>
    <string>--host</string>
    <string>0.0.0.0</string>
    <string>--port</string>
    <string>18090</string>
  </array>
  <key>WorkingDirectory</key>
  <string>${ROOT_DIR}/backend</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>${ROOT_DIR}/.venv/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    <key>PYTHONUNBUFFERED</key>
    <string>1</string>
    <key>JAVHUB_DB_HOST</key>
    <string>${JAVHUB_DB_HOST:-localhost}</string>
    <key>JAVHUB_DB_PORT</key>
    <string>${JAVHUB_DB_PORT:-5432}</string>
    <key>JAVHUB_DB_USER</key>
    <string>${JAVHUB_DB_USER:-kongmei}</string>
    <key>JAVHUB_DB_PASSWORD</key>
    <string>${JAVHUB_DB_PASSWORD:-}</string>
    <key>JAVHUB_DB_NAME</key>
    <string>${JAVHUB_DB_NAME:-javhub}</string>
    <key>JAVHUB_CACHE_BACKEND</key>
    <string>${JAVHUB_CACHE_BACKEND:-redis}</string>
    <key>JAVHUB_REDIS_URL</key>
    <string>${JAVHUB_REDIS_URL:-redis://127.0.0.1:6379/0}</string>
    <key>JAVHUB_REDIS_PREFIX</key>
    <string>${JAVHUB_REDIS_PREFIX:-javhub-cache}</string>
  </dict>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>${ROOT_DIR}/backend/javhub-backend.launchd.log</string>
  <key>StandardErrorPath</key>
  <string>${ROOT_DIR}/backend/javhub-backend.launchd.err.log</string>
</dict>
</plist>
EOF

  cat > "${FRONTEND_PLIST}" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${FRONTEND_LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${FRONTEND_NPM_BIN}</string>
    <string>run</string>
    <string>preview</string>
    <string>--</string>
    <string>--host</string>
    <string>0.0.0.0</string>
    <string>--port</string>
    <string>5174</string>
  </array>
  <key>WorkingDirectory</key>
  <string>${ROOT_DIR}/frontend</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
  </dict>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>${ROOT_DIR}/javhub-frontend.launchd.log</string>
  <key>StandardErrorPath</key>
  <string>${ROOT_DIR}/javhub-frontend.launchd.err.log</string>
</dict>
</plist>
EOF

  if command -v plutil >/dev/null 2>&1; then
    plutil -lint "${JAVINFO_PLIST}" "${BACKEND_PLIST}" "${FRONTEND_PLIST}" >/dev/null
  fi

  if [[ "${javinfo_had_plist}" == "1" ]] && ! cmp -s "${javinfo_before}" "${JAVINFO_PLIST}"; then
    JAVINFO_PLIST_CHANGED=1
  fi
  if [[ "${backend_had_plist}" == "1" ]] && ! cmp -s "${backend_before}" "${BACKEND_PLIST}"; then
    BACKEND_PLIST_CHANGED=1
  fi
  if [[ "${frontend_had_plist}" == "1" ]] && ! cmp -s "${frontend_before}" "${FRONTEND_PLIST}"; then
    FRONTEND_PLIST_CHANGED=1
  fi
  rm -f "${javinfo_before}" "${backend_before}" "${frontend_before}"
}

build_frontend() {
  if [[ "${JAVHUB_SKIP_FRONTEND_BUILD:-0}" == "1" ]]; then
    return
  fi
  (cd "${ROOT_DIR}/frontend" && "${FRONTEND_NPM_BIN}" run build)
}

is_loaded() {
  launchctl print "gui/${UID_VALUE}/$1" >/dev/null 2>&1
}

is_running() {
  local output
  output="$(launchctl print "gui/${UID_VALUE}/$1" 2>/dev/null || true)"
  [[ "${output}" == *"state = running"* ]]
}

plist_for_label() {
  case "$1" in
    "${JAVINFO_LABEL}") echo "${JAVINFO_PLIST}" ;;
    "${BACKEND_LABEL}") echo "${BACKEND_PLIST}" ;;
    "${FRONTEND_LABEL}") echo "${FRONTEND_PLIST}" ;;
    *) return 1 ;;
  esac
}

plist_changed_for_label() {
  case "$1" in
    "${JAVINFO_LABEL}") [[ "${JAVINFO_PLIST_CHANGED:-0}" == "1" ]] ;;
    "${BACKEND_LABEL}") [[ "${BACKEND_PLIST_CHANGED:-0}" == "1" ]] ;;
    "${FRONTEND_LABEL}") [[ "${FRONTEND_PLIST_CHANGED:-0}" == "1" ]] ;;
    *) return 1 ;;
  esac
}

bootstrap_label() {
  local label="$1"
  local plist
  plist="$(plist_for_label "${label}")"
  if ! is_loaded "${label}"; then
    launchctl bootstrap "gui/${UID_VALUE}" "${plist}" 2>/dev/null || true
  fi
}

kickstart_label() {
  local label="$1"
  bootstrap_label "${label}"
  launchctl kickstart -k "gui/${UID_VALUE}/${label}" >/dev/null
}

restart_label() {
  local label="$1"
  local plist
  plist="$(plist_for_label "${label}")"
  stop_label "${label}"
  prepare_port_for_label_start "${label}" || return 1
  launchctl bootstrap "gui/${UID_VALUE}" "${plist}" 2>/dev/null || true
  launchctl kickstart -k "gui/${UID_VALUE}/${label}" >/dev/null
}

restart_and_check_label() {
  local label="$1"
  local name url

  name="$(service_name_for_label "${label}")"
  url="$(health_url_for_label "${label}")"
  if restart_label "${label}" && wait_for_label_http_health "${label}"; then
    echo "${name} ${url}: ok after restart"
    if [[ "${label}" == "${BACKEND_LABEL}" ]] && ! print_backend_readiness_summary; then
      print_service_log_paths "${name}"
      return 1
    fi
    if label_needs_restart_stability_check "${label}" && ! check_label_restart_stability "${label}"; then
      print_label_unstable "${label}" "after restart"
      print_service_log_paths "${name}"
      return 1
    fi
    return 0
  fi

  echo "${name} ${url}: failed after restart"
  print_service_log_paths "${name}"
  return 1
}

stop_label() {
  local label="$1"
  local plist
  plist="$(plist_for_label "${label}")"
  launchctl bootout "gui/${UID_VALUE}" "${plist}" 2>/dev/null || true
}

stop_and_check_label() {
  local label="$1"
  local name port listener_pids

  name="$(service_name_for_label "${label}")"
  port="$(port_for_label "${label}")"
  stop_label "${label}"
  if wait_for_port_to_release "${port}"; then
    echo "${name} port ${port}: stopped"
    return 0
  fi

  listener_pids="$(listener_pids_for_port "${port}")"
  echo "${name} port ${port}: still has listener pid(s) ${listener_pids} after stop"
  print_pid_commands "${listener_pids}"
  return 1
}

label_for_service() {
  case "${1:-}" in
    javinfo) echo "${JAVINFO_LABEL}" ;;
    backend) echo "${BACKEND_LABEL}" ;;
    frontend) echo "${FRONTEND_LABEL}" ;;
    "") return 1 ;;
    *) echo "Unknown service: $1" >&2; return 2 ;;
  esac
}

all_labels() {
  printf '%s\n%s\n%s\n' "${JAVINFO_LABEL}" "${BACKEND_LABEL}" "${FRONTEND_LABEL}"
}

service_name_for_label() {
  case "$1" in
    "${JAVINFO_LABEL}") echo "javinfo" ;;
    "${BACKEND_LABEL}") echo "backend" ;;
    "${FRONTEND_LABEL}") echo "frontend" ;;
    *) return 1 ;;
  esac
}

port_for_label() {
  case "$1" in
    "${JAVINFO_LABEL}") echo "8080" ;;
    "${BACKEND_LABEL}") echo "18090" ;;
    "${FRONTEND_LABEL}") echo "5174" ;;
    *) return 1 ;;
  esac
}

launchd_pid_for_label() {
  local label="$1"
  launchctl print "gui/${UID_VALUE}/${label}" 2>/dev/null | awk '/pid =/ { print $3; exit }'
}

launchd_state_for_label() {
  local label="$1"
  launchctl print "gui/${UID_VALUE}/${label}" 2>/dev/null | awk -F'= ' '/state =/ { print $2; exit }'
}

label_launchd_is_running() {
  local label="$1"
  [[ "$(launchd_state_for_label "${label}")" == "running" ]]
}

print_launchd_not_running() {
  local name="$1"
  local label="$2"
  local state

  state="$(launchd_state_for_label "${label}")"
  if [[ -n "${state}" ]]; then
    echo "${name} launchd: not running (state = ${state})"
  else
    echo "${name} launchd: not running (state unavailable)"
  fi
}

listener_pids_for_port() {
  local port="$1"
  lsof -nP -iTCP:"${port}" -sTCP:LISTEN 2>/dev/null | awk '
    NR > 1 && $2 ~ /^[0-9]+$/ && !seen[$2]++ {
      if (pids) {
        pids = pids "," $2
      } else {
        pids = $2
      }
    }
    END { print pids }
  ' || true
}

wait_for_label_listener_if_loaded() {
  local label="$1"
  local port
  local attempt

  port="$(port_for_label "${label}")"
  if [[ -n "$(listener_pids_for_port "${port}")" ]]; then
    return 0
  fi
  if ! is_loaded "${label}"; then
    return 1
  fi

  for attempt in {1..10}; do
    sleep 0.2
    if [[ -n "$(listener_pids_for_port "${port}")" ]]; then
      return 0
    fi
  done

  return 1
}

pid_is_self_or_descendant_of() {
  local pid="$1"
  local ancestor_pid="$2"
  local parent_pid
  local depth=0

  if [[ "${pid}" == "${ancestor_pid}" ]]; then
    return 0
  fi

  while [[ -n "${pid}" && "${pid}" != "0" && "${pid}" != "1" && "${depth}" -lt 32 ]]; do
    parent_pid="$(ps -o ppid= -p "${pid}" 2>/dev/null | awk '{ print $1; exit }')"
    if [[ -z "${parent_pid}" ]]; then
      return 1
    fi
    if [[ "${parent_pid}" == "${ancestor_pid}" ]]; then
      return 0
    fi
    pid="${parent_pid}"
    depth=$((depth + 1))
  done

  return 1
}

listener_pids_owned_by_launchd_pid() {
  local listener_pids="$1"
  local launchd_pid="$2"
  local pid
  local found=0

  IFS=',' read -r -a pids <<< "${listener_pids}"
  for pid in "${pids[@]}"; do
    if [[ -z "${pid}" ]]; then
      continue
    fi
    found=1
    if ! pid_is_self_or_descendant_of "${pid}" "${launchd_pid}"; then
      return 1
    fi
  done

  [[ "${found}" == "1" ]]
}

label_port_has_owned_listener() {
  local label="$1"
  local port launchd_pid listener_pids

  port="$(port_for_label "${label}")"
  launchd_pid="$(launchd_pid_for_label "${label}")"
  listener_pids="$(listener_pids_for_port "${port}")"

  if [[ -z "${listener_pids}" || -z "${launchd_pid}" ]]; then
    return 1
  fi

  case ",${listener_pids}," in
    *",${launchd_pid},"*) return 0 ;;
  esac

  listener_pids_owned_by_launchd_pid "${listener_pids}" "${launchd_pid}"
}

pid_command() {
  local pid="$1"
  ps -o command= -p "${pid}" 2>/dev/null || true
}

print_pid_commands() {
  local pid_list="$1"
  local pid command

  IFS=',' read -r -a pids <<< "${pid_list}"
  for pid in "${pids[@]}"; do
    if [[ -z "${pid}" ]]; then
      continue
    fi
    command="$(pid_command "${pid}")"
    if [[ -n "${command}" ]]; then
      echo "  pid ${pid} command: ${command}"
    else
      echo "  pid ${pid} command: unavailable"
    fi
  done
}

listener_pid_matches_label() {
  local label="$1"
  local pid="$2"
  local command
  command="$(pid_command "${pid}")"

  case "${label}" in
    "${JAVINFO_LABEL}")
      [[ "${command}" == *"${JAVINFO_DIR}/JavInfoApi"* ]]
      ;;
    "${BACKEND_LABEL}")
      [[ "${command}" == *"${ROOT_DIR}/.venv/bin/uvicorn"* && "${command}" == *"main:app"* && "${command}" == *"--port 18090"* ]]
      ;;
    "${FRONTEND_LABEL}")
      [[ "${command}" == *"${ROOT_DIR}/frontend"* && "${command}" == *"--port 5174"* ]]
      ;;
    *)
      return 1
      ;;
  esac
}

join_by_comma() {
  local IFS=,
  echo "$*"
}

wait_for_port_to_release() {
  local port="$1"
  local attempt

  for attempt in {1..50}; do
    if [[ -z "$(listener_pids_for_port "${port}")" ]]; then
      return 0
    fi
    sleep 0.1
  done

  return 1
}

prepare_port_for_label_start() {
  local label="$1"
  local name port launchd_pid listener_pids
  local pid stale_pids blocked_pids stale_summary blocked_summary
  local -a stale_pid_array=()
  local -a blocked_pid_array=()

  name="$(service_name_for_label "${label}")"
  port="$(port_for_label "${label}")"
  launchd_pid="$(launchd_pid_for_label "${label}")"
  listener_pids="$(listener_pids_for_port "${port}")"

  if [[ -z "${listener_pids}" ]]; then
    return 0
  fi

  IFS=',' read -r -a pids <<< "${listener_pids}"
  for pid in "${pids[@]}"; do
    if [[ -z "${pid}" ]]; then
      continue
    fi
    if [[ -n "${launchd_pid}" ]] && pid_is_self_or_descendant_of "${pid}" "${launchd_pid}"; then
      continue
    fi
    if listener_pid_matches_label "${label}" "${pid}"; then
      stale_pid_array+=("${pid}")
    else
      blocked_pid_array+=("${pid}")
    fi
  done

  if [[ "${#blocked_pid_array[@]}" -gt 0 ]]; then
    blocked_summary="$(join_by_comma "${blocked_pid_array[@]}")"
    echo "${name} port ${port}: blocked by non-JavHub listener pid(s) ${blocked_summary}; not starting"
    print_pid_commands "${blocked_summary}"
    return 1
  fi

  if [[ "${#stale_pid_array[@]}" -eq 0 ]]; then
    return 0
  fi

  stale_summary="$(join_by_comma "${stale_pid_array[@]}")"
  "${JAVHUB_KILL_BIN:-kill}" -TERM "${stale_pid_array[@]}" 2>/dev/null || true

  if wait_for_port_to_release "${port}"; then
    echo "${name} port ${port}: reclaimed stale listener pid(s) ${stale_summary}"
    return 0
  fi

  echo "${name} port ${port}: stale listener pid(s) ${stale_summary} did not release after TERM; not starting"
  return 1
}

print_port_diagnostic() {
  local name="$1"
  local label="$2"
  local port="$3"
  local launchd_pid listener_pids

  launchd_pid="$(launchd_pid_for_label "${label}")"
  listener_pids="$(listener_pids_for_port "${port}")"

  if [[ -z "${listener_pids}" ]]; then
    echo "${name} port ${port}: no listener"
    return 1
  fi

  if [[ -z "${launchd_pid}" ]]; then
    echo "${name} port ${port}: listener pid(s) ${listener_pids}; launchd pid unavailable"
    return 1
  fi

  case ",${listener_pids}," in
    *",${launchd_pid},"*) echo "${name} port ${port}: ok (pid ${launchd_pid})" ;;
    *)
      if listener_pids_owned_by_launchd_pid "${listener_pids}" "${launchd_pid}"; then
        echo "${name} port ${port}: ok (listener pid(s) ${listener_pids} owned by launchd pid ${launchd_pid})"
      else
        echo "${name} port ${port}: listener pid(s) ${listener_pids} differ from launchd pid ${launchd_pid}"
        print_pid_commands "${listener_pids}"
        return 1
      fi
      ;;
  esac

  return 0
}

print_port_diagnostics() {
  local failed=0
  local label

  echo
  echo "Port diagnostics:"
  while IFS= read -r label; do
    wait_for_label_listener_if_loaded "${label}" >/dev/null 2>&1 || true
  done < <(all_labels)
  print_port_diagnostic "javinfo" "${JAVINFO_LABEL}" "8080" || failed=1
  print_port_diagnostic "backend" "${BACKEND_LABEL}" "18090" || failed=1
  print_port_diagnostic "frontend" "${FRONTEND_LABEL}" "5174" || failed=1

  return "${failed}"
}

check_label_restart_stability() {
  local label="$1"
  local name port url delay
  local failed=0

  name="$(service_name_for_label "${label}")"
  port="$(port_for_label "${label}")"
  url="$(health_url_for_label "${label}")"
  delay="${JAVHUB_RESTART_STABILITY_DELAY:-1}"

  if [[ "${delay}" != "0" ]]; then
    sleep "${delay}"
  fi

  if ! label_launchd_is_running "${label}"; then
    print_launchd_not_running "${name}" "${label}"
    failed=1
  fi

  if ! label_port_has_owned_listener "${label}"; then
    print_port_diagnostic "${name}" "${label}" "${port}" || true
    failed=1
  fi

  if ! label_http_is_healthy "${label}"; then
    echo "${name} ${url}: failed during stability check"
    failed=1
  fi

  return "${failed}"
}

label_needs_restart_stability_check() {
  [[ "$1" == "${BACKEND_LABEL}" || "$1" == "${FRONTEND_LABEL}" ]]
}

print_label_unstable() {
  local label="$1"
  local context="${2:-}"
  local name url suffix

  name="$(service_name_for_label "${label}")"
  url="$(health_url_for_label "${label}")"
  suffix=""
  if [[ -n "${context}" ]]; then
    suffix=" ${context}"
  fi
  echo "${name} ${url}: unstable${suffix}"
}

health_url_for_label() {
  case "$1" in
    "${JAVINFO_LABEL}") echo "http://127.0.0.1:8080/health" ;;
    "${BACKEND_LABEL}") echo "http://127.0.0.1:18090/health" ;;
    "${FRONTEND_LABEL}") echo "http://127.0.0.1:5174" ;;
    *) return 1 ;;
  esac
}

http_url_is_healthy() {
  local url="$1"

  command -v curl >/dev/null 2>&1 || return 2
  curl -fsS --max-time 2 "${url}" >/dev/null 2>&1
}

label_http_is_healthy() {
  local label="$1"
  local url
  url="$(health_url_for_label "${label}")"
  http_url_is_healthy "${url}"
}

wait_for_label_http_health() {
  local label="$1"
  local attempt

  for attempt in {1..30}; do
    if label_http_is_healthy "${label}"; then
      return 0
    fi
    sleep 0.5
  done

  return 1
}

print_http_check() {
  local name="$1"
  local url="$2"

  if ! command -v curl >/dev/null 2>&1; then
    echo "${name} ${url}: skipped (curl not found)"
    return
  fi

  if curl -fsS --max-time 2 "${url}" >/dev/null 2>&1; then
    echo "${name} ${url}: ok"
  else
    echo "${name} ${url}: failed"
    return 1
  fi
}

print_http_health_summary() {
  local failed=0

  echo
  echo "HTTP health:"
  print_http_check "javinfo" "http://127.0.0.1:8080/health" || failed=1
  print_http_check "backend" "http://127.0.0.1:18090/health" || failed=1
  print_http_check "frontend" "http://127.0.0.1:5174" || failed=1

  return "${failed}"
}

print_backend_readiness_summary() {
  local url="http://127.0.0.1:18090/health/readiness"
  local payload

  echo
  echo "Backend readiness:"
  if ! command -v curl >/dev/null 2>&1; then
    echo "backend readiness ${url}: skipped (curl not found)"
    return 0
  fi

  if ! payload="$(curl -fsS --max-time 3 "${url}" 2>/dev/null)"; then
    echo "backend readiness ${url}: failed"
    return 1
  fi

  READINESS_PAYLOAD="${payload}" "${PYTHON_BIN}" <<'PY'
import json
import os
import sys


def text(value):
    return str(value or "").strip()


def line(label, ok, context, error):
    state = "ok" if ok else "failed"
    suffix = f" ({context})" if context else ""
    message = f" {error}" if error else ""
    print(f"{label}: {state}{suffix}{message}")


try:
    payload = json.loads(os.environ.get("READINESS_PAYLOAD", ""))
except Exception as exc:
    print(f"backend readiness: failed to parse JSON ({exc})")
    sys.exit(1)

status = text(payload.get("status")) or "unknown"
print(f"backend readiness: {status}")
has_detail = any(isinstance(payload.get(key), dict) for key in ("database", "javinfo", "cache"))
if not has_detail:
    sys.exit(0 if status == "ok" else 1)

database = payload.get("database") if isinstance(payload.get("database"), dict) else {}
db_context = ":".join(
    part for part in (text(database.get("host")), text(database.get("port"))) if part
)
db_name = text(database.get("database"))
if db_name:
    db_context = f"{db_context}/{db_name}" if db_context else db_name
line("database", bool(database.get("connectable")), db_context, text(database.get("error")))

javinfo = payload.get("javinfo") if isinstance(payload.get("javinfo"), dict) else {}
line("javinfo", bool(javinfo.get("reachable")), text(javinfo.get("api_url")), text(javinfo.get("error")))

cache = payload.get("cache") if isinstance(payload.get("cache"), dict) else {}
line("cache", not bool(text(cache.get("error"))), text(cache.get("backend")), text(cache.get("error")))

sys.exit(0 if status == "ok" else 1)
PY
}

backend_readiness_is_ok() {
  local url="http://127.0.0.1:18090/health/readiness"
  local payload

  command -v curl >/dev/null 2>&1 || return 0
  payload="$(curl -fsS --max-time 3 "${url}" 2>/dev/null)" || return 1
  READINESS_PAYLOAD="${payload}" "${PYTHON_BIN}" <<'PY'
import json
import os
import sys

try:
    payload = json.loads(os.environ.get("READINESS_PAYLOAD", ""))
except Exception:
    sys.exit(1)

sys.exit(0 if str(payload.get("status") or "").strip() == "ok" else 1)
PY
}

recover_unhealthy_http_services() {
  local failed=0
  local label name url

  echo
  echo "HTTP health:"
  while IFS= read -r label; do
    name="$(service_name_for_label "${label}")"
    url="$(health_url_for_label "${label}")"
    if label_http_is_healthy "${label}"; then
      echo "${name} ${url}: ok"
      continue
    fi

    echo "${name} ${url}: failed; restarting ${name}"
    if [[ "${label}" == "${FRONTEND_LABEL}" ]]; then
      build_frontend
    fi
    if restart_label "${label}" && wait_for_label_http_health "${label}"; then
      echo "${name} ${url}: recovered"
      if label_needs_restart_stability_check "${label}" && ! check_label_restart_stability "${label}"; then
        print_label_unstable "${label}" "after restart"
        print_service_log_paths "${name}"
        failed=1
      fi
    else
      echo "${name} ${url}: still failed after restart"
      print_service_log_paths "${name}"
      failed=1
    fi
  done < <(all_labels)

  return "${failed}"
}

recover_backend_readiness() {
  local failed=0

  if backend_readiness_is_ok; then
    if ! print_backend_readiness_summary; then
      failed=1
    elif ! check_label_restart_stability "${BACKEND_LABEL}"; then
      print_label_unstable "${BACKEND_LABEL}"
      print_service_log_paths "backend"
      failed=1
    fi
    return "${failed}"
  fi

  echo
  echo "Backend readiness:"
  echo "backend readiness: degraded; restarting backend"
  if restart_label "${BACKEND_LABEL}" && wait_for_label_http_health "${BACKEND_LABEL}"; then
    if ! print_backend_readiness_summary; then
      print_service_log_paths "backend"
      failed=1
    elif ! check_label_restart_stability "${BACKEND_LABEL}"; then
      print_label_unstable "${BACKEND_LABEL}" "after restart"
      print_service_log_paths "backend"
      failed=1
    fi
  else
    echo "backend readiness: failed after restart"
    print_service_log_paths "backend"
    failed=1
  fi

  return "${failed}"
}

tail_service_logs() {
  local name="$1"
  local stdout_path="$2"
  local stderr_path="$3"
  local follow="${4:-1}"

  mkdir -p "$(dirname "${stdout_path}")" "$(dirname "${stderr_path}")"
  touch "${stdout_path}" "${stderr_path}"
  echo "${name} stdout: ${stdout_path}"
  echo "${name} stderr: ${stderr_path}"
  if [[ "${follow}" == "1" ]]; then
    tail -n 120 -f "${stdout_path}" "${stderr_path}"
  else
    tail -n 120 "${stdout_path}" "${stderr_path}"
  fi
}

print_service_log_paths() {
  case "$1" in
    javinfo)
      echo "javinfo stdout: ${JAVINFO_DIR}/javinfoapi.launchd.log"
      echo "javinfo stderr: ${JAVINFO_DIR}/javinfoapi.launchd.err.log"
      ;;
    backend)
      echo "backend stdout: ${ROOT_DIR}/backend/javhub-backend.launchd.log"
      echo "backend stderr: ${ROOT_DIR}/backend/javhub-backend.launchd.err.log"
      ;;
    frontend)
      echo "frontend stdout: ${ROOT_DIR}/javhub-frontend.launchd.log"
      echo "frontend stderr: ${ROOT_DIR}/javhub-frontend.launchd.err.log"
      ;;
  esac
}

DOCTOR_QUIET=0

doctor_print() {
  if [[ "${DOCTOR_QUIET}" != "1" ]]; then
    echo "$1"
  fi
}

doctor_command_check() {
  local name="$1"
  local command_name="$2"

  if command -v "${command_name}" >/dev/null 2>&1; then
    doctor_print "${name}: ok ($(command -v "${command_name}"))"
    return 0
  fi

  doctor_print "${name}: missing"
  return 1
}

doctor_path_or_command_check() {
  local name="$1"
  local command_path="$2"

  if [[ "${command_path}" == */* ]]; then
    doctor_executable_check "${name}" "${command_path}"
    return
  fi

  doctor_command_check "${name}" "${command_path}"
}

doctor_executable_check() {
  local name="$1"
  local path="$2"

  if [[ -x "${path}" ]]; then
    doctor_print "${name}: ok (${path})"
    return 0
  fi

  doctor_print "${name}: missing (${path})"
  return 1
}

doctor_directory_check() {
  local name="$1"
  local path="$2"

  if [[ -d "${path}" ]]; then
    doctor_print "${name}: ok (${path})"
    return 0
  fi

  doctor_print "${name}: missing (${path})"
  return 1
}

doctor_file_check() {
  local name="$1"
  local path="$2"

  if [[ -f "${path}" ]]; then
    doctor_print "${name}: ok (${path})"
    return 0
  fi

  doctor_print "${name}: missing (${path})"
  return 1
}

doctor_checks() {
  local failed=0

  doctor_command_check "launchctl" "launchctl" || failed=1
  doctor_command_check "lsof" "lsof" || failed=1
  doctor_command_check "curl" "curl" || failed=1
  doctor_path_or_command_check "frontend npm" "${FRONTEND_NPM_BIN}" || failed=1
  doctor_executable_check "backend uvicorn" "${ROOT_DIR}/.venv/bin/uvicorn" || failed=1
  doctor_directory_check "frontend directory" "${ROOT_DIR}/frontend" || failed=1
  doctor_file_check "frontend build" "${FRONTEND_DIST_DIR}/index.html" || failed=1
  doctor_executable_check "javinfo binary" "${JAVINFO_DIR}/JavInfoApi" || failed=1

  return "${failed}"
}

ensure_preflight_checks() {
  local failed=0

  doctor_command_check "launchctl" "launchctl" || failed=1
  doctor_command_check "lsof" "lsof" || failed=1
  doctor_command_check "curl" "curl" || failed=1
  doctor_path_or_command_check "frontend npm" "${FRONTEND_NPM_BIN}" || failed=1
  doctor_executable_check "backend uvicorn" "${ROOT_DIR}/.venv/bin/uvicorn" || failed=1
  doctor_directory_check "frontend directory" "${ROOT_DIR}/frontend" || failed=1
  doctor_executable_check "javinfo binary" "${JAVINFO_DIR}/JavInfoApi" || failed=1

  return "${failed}"
}

doctor() {
  DOCTOR_QUIET=0
  echo "Dependency check:"
  doctor_checks
}

ensure_dependency_preflight() {
  DOCTOR_QUIET=1
  if ensure_preflight_checks; then
    DOCTOR_QUIET=0
    return 0
  fi

  DOCTOR_QUIET=0
  echo "Dependency check:"
  ensure_preflight_checks || true
  return 1
}

ensure_services() {
  ensure_dependency_preflight
  local failed=0
  write_plists
  while IFS= read -r label; do
    if is_loaded "${label}" && plist_changed_for_label "${label}"; then
      if [[ "${label}" == "${FRONTEND_LABEL}" ]]; then
        build_frontend
      fi
      restart_and_check_label "${label}" || failed=1
      continue
    fi
    bootstrap_label "${label}"
    if is_running "${label}"; then
      local port launchd_pid listener_pids
      port="$(port_for_label "${label}")"
      launchd_pid="$(launchd_pid_for_label "${label}")"
      listener_pids="$(listener_pids_for_port "${port}")"
      if [[ -n "${listener_pids}" && -n "${launchd_pid}" ]] && ! listener_pids_owned_by_launchd_pid "${listener_pids}" "${launchd_pid}"; then
        if prepare_port_for_label_start "${label}"; then
          launchctl kickstart -k "gui/${UID_VALUE}/${label}" >/dev/null 2>&1 || true
        else
          failed=1
        fi
      fi
    else
      if ! prepare_port_for_label_start "${label}"; then
        failed=1
        continue
      fi
      if [[ "${label}" == "${FRONTEND_LABEL}" ]]; then
        build_frontend
      fi
      launchctl kickstart "gui/${UID_VALUE}/${label}" >/dev/null 2>&1 || true
      wait_for_label_http_health "${label}" >/dev/null 2>&1 || true
    fi
  done < <(all_labels)
  recover_unhealthy_http_services || failed=1
  recover_backend_readiness || failed=1
  return "${failed}"
}

status() {
  local failed=0

  while IFS= read -r label; do
    if is_loaded "${label}"; then
      launchctl print "gui/${UID_VALUE}/${label}" 2>/dev/null | awk -v label="${label}" '
        /state =|pid =|runs =|last exit code =|program =/ { print label ": " $0 }
      '
    else
      echo "${label}: not loaded"
    fi
  done < <(all_labels)

  echo
  lsof -nP -iTCP:8080 -sTCP:LISTEN 2>/dev/null || true
  lsof -nP -iTCP:18090 -sTCP:LISTEN 2>/dev/null || true
  lsof -nP -iTCP:5174 -sTCP:LISTEN 2>/dev/null || true

  print_port_diagnostics || failed=1
  print_http_health_summary || failed=1
  print_backend_readiness_summary || failed=1

  return "${failed}"
}

tail_logs() {
  local service="${1:-}"
  local follow=1

  if [[ $# -gt 2 ]]; then
    echo "Usage: scripts/services.sh logs <javinfo|backend|frontend> [--no-follow]" >&2
    return 2
  fi

  if [[ $# -eq 2 ]]; then
    case "$2" in
      --no-follow) follow=0 ;;
      *)
        echo "Usage: scripts/services.sh logs <javinfo|backend|frontend> [--no-follow]" >&2
        return 2
        ;;
    esac
  fi

  case "${service}" in
    javinfo)
      tail_service_logs "javinfo" "${JAVINFO_DIR}/javinfoapi.launchd.log" "${JAVINFO_DIR}/javinfoapi.launchd.err.log" "${follow}"
      ;;
    backend)
      tail_service_logs "backend" "${ROOT_DIR}/backend/javhub-backend.launchd.log" "${ROOT_DIR}/backend/javhub-backend.launchd.err.log" "${follow}"
      ;;
    frontend)
      tail_service_logs "frontend" "${ROOT_DIR}/javhub-frontend.launchd.log" "${ROOT_DIR}/javhub-frontend.launchd.err.log" "${follow}"
      ;;
    *)
      echo "Usage: scripts/services.sh logs <javinfo|backend|frontend> [--no-follow]" >&2
      return 2
      ;;
  esac
}

restart_services() {
  if [[ $# -gt 1 ]]; then
    echo "Usage: scripts/services.sh restart [javinfo|backend|frontend]" >&2
    return 2
  fi
  if [[ $# -eq 0 ]]; then
    local failed=0
    write_plists
    build_frontend
    while IFS= read -r label; do
      restart_and_check_label "${label}" || failed=1
    done < <(all_labels)
    return "${failed}"
  fi
  local label
  label="$(label_for_service "$1")" || return $?
  write_plists
  if [[ "${label}" == "${FRONTEND_LABEL}" ]]; then
    build_frontend
  fi
  restart_and_check_label "${label}"
}

stop_services() {
  if [[ $# -gt 1 ]]; then
    echo "Usage: scripts/services.sh stop [javinfo|backend|frontend]" >&2
    return 2
  fi
  if [[ $# -eq 0 ]]; then
    local failed=0
    while IFS= read -r label; do
      stop_and_check_label "${label}" || failed=1
    done < <(all_labels)
    return "${failed}"
  fi
  local label
  label="$(label_for_service "$1")" || return $?
  stop_and_check_label "${label}"
}

rebuild_javinfo() {
  if [[ $# -gt 0 ]]; then
    echo "Usage: scripts/services.sh rebuild-javinfo" >&2
    return 2
  fi

  (cd "${JAVINFO_DIR}" && go build -o JavInfoApi ./cmd/javinfoapi)
  write_plists
  restart_and_check_label "${JAVINFO_LABEL}"
}

command="${1:-}"
shift || true

case "${command}" in
  ensure|start) ensure_services ;;
  doctor) doctor ;;
  render-plists) write_plists ;;
  restart) restart_services "$@" ;;
  stop) stop_services "$@" ;;
  status) status ;;
  logs) tail_logs "$@" ;;
  rebuild-javinfo) rebuild_javinfo "$@" ;;
  -h|--help|help|"") usage ;;
  *)
    echo "Unknown command: ${command}" >&2
    usage >&2
    exit 2
    ;;
esac
