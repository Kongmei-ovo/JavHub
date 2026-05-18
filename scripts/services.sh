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

usage() {
  cat <<'USAGE'
Usage: scripts/services.sh <command> [service]

Commands:
  ensure              Install/update LaunchAgents and start missing services.
  start               Install/update LaunchAgents and start all services.
  restart [service]   Restart all services or one: javinfo, backend, frontend.
  stop [service]      Stop all services or one: javinfo, backend, frontend.
  status              Print launchd and port status.
  logs <service>      Tail logs for: javinfo, backend, frontend.
  rebuild-javinfo     Rebuild JavInfoApi binary and restart javinfo.
  render-plists       Write LaunchAgent plists without starting services.

Environment:
  JAVINFO_DIR         Defaults to /Users/kongmei/Code/JavInfoApi.
USAGE
}

xml_escape() {
  "${ROOT_DIR}/.venv/bin/python" -c 'import html, sys; print(html.escape(sys.stdin.read().rstrip("\n"), quote=True), end="")'
}

javinfo_source_proxy_url() {
  ROOT_DIR="${ROOT_DIR}" "${ROOT_DIR}/.venv/bin/python" <<'PY'
from pathlib import Path
import os
import sys

try:
    import yaml
except Exception:
    sys.exit(0)

config_path = Path(os.environ["ROOT_DIR"]) / "config.yaml"
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
    <string>/opt/homebrew/bin/npm</string>
    <string>run</string>
    <string>dev</string>
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

  plutil -lint "${JAVINFO_PLIST}" "${BACKEND_PLIST}" "${FRONTEND_PLIST}" >/dev/null
}

is_loaded() {
  launchctl print "gui/${UID_VALUE}/$1" >/dev/null 2>&1
}

is_running() {
  launchctl print "gui/${UID_VALUE}/$1" 2>/dev/null | grep -q "state = running"
}

plist_for_label() {
  case "$1" in
    "${JAVINFO_LABEL}") echo "${JAVINFO_PLIST}" ;;
    "${BACKEND_LABEL}") echo "${BACKEND_PLIST}" ;;
    "${FRONTEND_LABEL}") echo "${FRONTEND_PLIST}" ;;
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

stop_label() {
  local label="$1"
  local plist
  plist="$(plist_for_label "${label}")"
  launchctl bootout "gui/${UID_VALUE}" "${plist}" 2>/dev/null || true
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

ensure_services() {
  write_plists
  while IFS= read -r label; do
    bootstrap_label "${label}"
    if ! is_running "${label}"; then
      launchctl kickstart "gui/${UID_VALUE}/${label}" >/dev/null 2>&1 || true
    fi
  done < <(all_labels)
}

status() {
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
}

tail_logs() {
  case "${1:-}" in
    javinfo)
      tail -n 120 -f "${JAVINFO_DIR}/javinfoapi.launchd.log" "${JAVINFO_DIR}/javinfoapi.launchd.err.log"
      ;;
    backend)
      tail -n 120 -f "${ROOT_DIR}/backend/javhub-backend.launchd.log" "${ROOT_DIR}/backend/javhub-backend.launchd.err.log"
      ;;
    frontend)
      tail -n 120 -f "${ROOT_DIR}/javhub-frontend.launchd.log" "${ROOT_DIR}/javhub-frontend.launchd.err.log"
      ;;
    *)
      echo "Usage: scripts/services.sh logs <javinfo|backend|frontend>" >&2
      return 2
      ;;
  esac
}

restart_services() {
  write_plists
  if [[ $# -eq 0 ]]; then
    while IFS= read -r label; do
      kickstart_label "${label}"
    done < <(all_labels)
    return
  fi
  kickstart_label "$(label_for_service "$1")"
}

stop_services() {
  if [[ $# -eq 0 ]]; then
    while IFS= read -r label; do
      stop_label "${label}"
    done < <(all_labels)
    return
  fi
  stop_label "$(label_for_service "$1")"
}

rebuild_javinfo() {
  (cd "${JAVINFO_DIR}" && go build -o JavInfoApi ./cmd/javinfoapi)
  write_plists
  stop_label "${JAVINFO_LABEL}"
  bootstrap_label "${JAVINFO_LABEL}"
  kickstart_label "${JAVINFO_LABEL}"
}

command="${1:-}"
shift || true

case "${command}" in
  ensure|start) ensure_services ;;
  render-plists) write_plists ;;
  restart) restart_services "$@" ;;
  stop) stop_services "$@" ;;
  status) status ;;
  logs) tail_logs "${1:-}" ;;
  rebuild-javinfo) rebuild_javinfo ;;
  -h|--help|help|"") usage ;;
  *)
    echo "Unknown command: ${command}" >&2
    usage >&2
    exit 2
    ;;
esac
