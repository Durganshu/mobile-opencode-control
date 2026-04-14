#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="$ROOT_DIR/.runtime"

OPENCODE_PID_FILE="$RUNTIME_DIR/opencode.pid"
OPENCODE_PORT_FILE="$RUNTIME_DIR/opencode.port"
OPENCODE_URL_FILE="$RUNTIME_DIR/opencode.url"
BACKEND_PID_FILE="$RUNTIME_DIR/backend.pid"
BACKEND_PORT_FILE="$RUNTIME_DIR/backend.port"
BACKEND_URL_FILE="$RUNTIME_DIR/backend.url"
FRONTEND_PID_FILE="$RUNTIME_DIR/frontend.pid"
FRONTEND_PORT_FILE="$RUNTIME_DIR/frontend.port"
FRONTEND_URL_FILE="$RUNTIME_DIR/frontend.url"

stop_matching_processes() {
  local name="$1"
  local pattern="$2"

  local pids
  pids="$(pgrep -f "$pattern" || true)"
  if [[ -z "$pids" ]]; then
    return 1
  fi

  while IFS= read -r pid; do
    [[ -z "$pid" ]] && continue
    kill "$pid" >/dev/null 2>&1 || true
  done <<< "$pids"

  sleep 1

  while IFS= read -r pid; do
    [[ -z "$pid" ]] && continue
    if kill -0 "$pid" >/dev/null 2>&1; then
      kill -9 "$pid" >/dev/null 2>&1 || true
    fi
  done <<< "$pids"

  return 0
}

stop_from_pid_file() {
  local name="$1"
  local pid_file="$2"

  if [[ ! -f "$pid_file" ]]; then
    return 1
  fi

  local pid
  pid="$(cat "$pid_file")"
  if [[ -z "$pid" ]]; then
    rm -f "$pid_file"
    return 1
  fi

  if ! kill -0 "$pid" >/dev/null 2>&1; then
    rm -f "$pid_file"
    return 1
  fi

  kill "$pid" >/dev/null 2>&1 || true
  sleep 1

  if kill -0 "$pid" >/dev/null 2>&1; then
    kill -9 "$pid" >/dev/null 2>&1 || true
  fi

  rm -f "$pid_file"
  return 0
}

stop_service() {
  local name="$1"
  local pid_file="$2"
  local pattern="$3"
  local stopped=1

  if stop_from_pid_file "$name" "$pid_file"; then
    stopped=0
  fi

  if stop_matching_processes "$name" "$pattern"; then
    stopped=0
  fi

  if [[ "$stopped" -eq 0 ]]; then
    echo "$name: stopped"
  else
    echo "$name: not running"
  fi
}

stop_service "frontend" "$FRONTEND_PID_FILE" "$ROOT_DIR/frontend/node_modules/.bin/vite --host 0.0.0.0 --port"
stop_service "backend" "$BACKEND_PID_FILE" "$ROOT_DIR/backend/run.py"
stop_service "opencode" "$OPENCODE_PID_FILE" "opencode serve --hostname 127.0.0.1 --port 4096"

rm -f "$OPENCODE_PORT_FILE" "$OPENCODE_URL_FILE" "$BACKEND_PORT_FILE" "$BACKEND_URL_FILE" "$FRONTEND_PORT_FILE" "$FRONTEND_URL_FILE"
