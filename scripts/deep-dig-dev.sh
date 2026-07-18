#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="$ROOT_DIR/.dev"
PID_DIR="$STATE_DIR/pids"
LOG_DIR="$STATE_DIR/logs"

API_HOST="${API_HOST:-127.0.0.1}"
API_PORT="${API_PORT:-8001}"
REDIS_HOST="${REDIS_HOST:-127.0.0.1}"
REDIS_PORT="${REDIS_PORT:-6379}"
AUTH_MODE="env"
LLM_MODE="env"

usage() {
  cat <<'EOF'
Usage:
  scripts/deep-dig-dev.sh start [--auth env|real|dev] [--llm env|real|fake]
  scripts/deep-dig-dev.sh stop
  scripts/deep-dig-dev.sh restart [same options as start]
  scripts/deep-dig-dev.sh status
  scripts/deep-dig-dev.sh logs [api|worker|redis]

Modes:
  --auth env   read DEV_AUTH_ENABLED from apps/backend/.env
  --auth real  force DEV_AUTH_ENABLED=false
  --auth dev   force DEV_AUTH_ENABLED=true
  --llm env    read LLM_PROVIDER from apps/backend/.env
  --llm real   do not override LLM_PROVIDER
  --llm fake   force LLM_PROVIDER=fake
EOF
}

ensure_dirs() {
  mkdir -p "$PID_DIR" "$LOG_DIR"
}

pid_file() {
  echo "$PID_DIR/$1.pid"
}

meta_file() {
  echo "$PID_DIR/$1.meta"
}

is_pid_running() {
  local pid="${1:-}"
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

read_pid() {
  local file
  file="$(pid_file "$1")"
  [[ -f "$file" ]] && cat "$file"
}

port_open() {
  nc -z "$1" "$2" >/dev/null 2>&1
}

declare -a backend_env_args=()

build_backend_env() {
  backend_env_args=()
  case "$AUTH_MODE" in
    env) ;;
    real) backend_env_args+=("DEV_AUTH_ENABLED=false") ;;
    dev) backend_env_args+=("DEV_AUTH_ENABLED=true") ;;
    *) echo "Unknown auth mode: $AUTH_MODE" >&2; exit 2 ;;
  esac

  case "$LLM_MODE" in
    env|real) ;;
    fake) backend_env_args+=("LLM_PROVIDER=fake") ;;
    *) echo "Unknown LLM mode: $LLM_MODE" >&2; exit 2 ;;
  esac
}

start_process() {
  local name="$1"
  local cwd="$2"
  shift 2
  local existing
  existing="$(read_pid "$name" || true)"
  if is_pid_running "$existing"; then
    echo "$name already running (pid $existing)"
    return
  fi

  echo "Starting $name..."
  (
    cd "$cwd"
    nohup "$@" >"$LOG_DIR/$name.log" 2>&1 &
    echo $! >"$(pid_file "$name")"
  )
  echo "$name pid $(cat "$(pid_file "$name")")"
}

start_redis() {
  if port_open "$REDIS_HOST" "$REDIS_PORT"; then
    echo "redis already available on $REDIS_HOST:$REDIS_PORT"
    echo "external" >"$(meta_file redis)"
    return
  fi
  if ! command -v redis-server >/dev/null 2>&1; then
    echo "redis-server not found; start Redis manually on $REDIS_HOST:$REDIS_PORT" >&2
    exit 1
  fi
  echo "managed" >"$(meta_file redis)"
  start_process redis "$ROOT_DIR" redis-server --port "$REDIS_PORT" --bind "$REDIS_HOST"
}

start_api() {
  if port_open "$API_HOST" "$API_PORT"; then
    local existing
    existing="$(read_pid api || true)"
    if is_pid_running "$existing"; then
      echo "api already running (pid $existing)"
      return
    fi
    echo "api port $API_HOST:$API_PORT is already in use; not starting another API process" >&2
    return
  fi
  build_backend_env
  start_process api "$ROOT_DIR/apps/backend" env ${backend_env_args[@]+"${backend_env_args[@]}"} uv run uvicorn app.main:app --host "$API_HOST" --port "$API_PORT"
}

start_worker() {
  build_backend_env
  start_process worker "$ROOT_DIR/apps/backend" env ${backend_env_args[@]+"${backend_env_args[@]}"} uv run arq app.workers.arq_worker.WorkerSettings
}

stop_process() {
  local name="$1"
  local pid
  pid="$(read_pid "$name" || true)"
  if ! is_pid_running "$pid"; then
    echo "$name not running"
    rm -f "$(pid_file "$name")"
    return
  fi

  echo "Stopping $name (pid $pid)..."
  kill "$pid" 2>/dev/null || true
  for _ in {1..30}; do
    if ! is_pid_running "$pid"; then
      rm -f "$(pid_file "$name")"
      echo "$name stopped"
      return
    fi
    sleep 0.2
  done
  echo "$name did not stop gracefully; sending SIGKILL"
  kill -9 "$pid" 2>/dev/null || true
  rm -f "$(pid_file "$name")"
}

stop_all() {
  stop_process worker
  stop_process api
  if [[ "$(cat "$(meta_file redis)" 2>/dev/null || true)" == "managed" ]]; then
    stop_process redis
  else
    echo "redis was external or not started by this script; leaving it running"
    rm -f "$(pid_file redis)" "$(meta_file redis)"
  fi
}

status_one() {
  local name="$1"
  local pid
  pid="$(read_pid "$name" || true)"
  if is_pid_running "$pid"; then
    echo "$name: running (pid $pid)"
  else
    echo "$name: stopped"
  fi
}

status_all() {
  status_one redis
  status_one api
  status_one worker
  if port_open "$API_HOST" "$API_PORT"; then
    echo "api port: open at http://$API_HOST:$API_PORT"
  else
    echo "api port: closed at http://$API_HOST:$API_PORT"
  fi
  if port_open "$REDIS_HOST" "$REDIS_PORT"; then
    echo "redis port: open at $REDIS_HOST:$REDIS_PORT"
  else
    echo "redis port: closed at $REDIS_HOST:$REDIS_PORT"
  fi
}

show_logs() {
  local name="${1:-api}"
  local file="$LOG_DIR/$name.log"
  if [[ ! -f "$file" ]]; then
    echo "No log file for $name at $file" >&2
    exit 1
  fi
  tail -n 120 -f "$file"
}

parse_start_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --)
        shift
        ;;
      --auth)
        AUTH_MODE="${2:-}"
        shift 2
        ;;
      --llm)
        LLM_MODE="${2:-}"
        shift 2
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        echo "Unknown option: $1" >&2
        usage
        exit 2
        ;;
    esac
  done
}

main() {
  ensure_dirs
  local command="${1:-}"
  shift || true
  case "$command" in
    start)
      parse_start_args "$@"
      start_redis
      start_api
      start_worker
      status_all
      ;;
    stop)
      stop_all
      ;;
    restart)
      stop_all
      parse_start_args "$@"
      start_redis
      start_api
      start_worker
      status_all
      ;;
    status)
      status_all
      ;;
    logs)
      show_logs "${1:-api}"
      ;;
    -h|--help|"")
      usage
      ;;
    *)
      echo "Unknown command: $command" >&2
      usage
      exit 2
      ;;
  esac
}

main "$@"
