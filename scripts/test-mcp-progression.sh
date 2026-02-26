#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_LOG="/tmp/dw-mcp-backend.log"
FRONTEND_LOG="/tmp/dw-mcp-frontend.log"
RESULT_FILE="/tmp/codex_mcp_progression_test.txt"
BACKEND_PID=""
FRONTEND_PID=""
BACKEND_PORT="${MCP_BACKEND_PORT:-}"
FRONTEND_PORT="${MCP_FRONTEND_PORT:-}"
APP_URL=""
API_BASE_URL=""

terminate_pid() {
  local pid="$1"
  if [[ -z "$pid" ]]; then
    return 0
  fi
  if ! kill -0 "$pid" >/dev/null 2>&1; then
    return 0
  fi

  kill "$pid" >/dev/null 2>&1 || true

  local i
  for ((i = 1; i <= 20; i += 1)); do
    if ! kill -0 "$pid" >/dev/null 2>&1; then
      break
    fi
    sleep 0.25
  done

  if kill -0 "$pid" >/dev/null 2>&1; then
    kill -9 "$pid" >/dev/null 2>&1 || true
  fi

  wait "$pid" >/dev/null 2>&1 || true
}

cleanup() {
  local exit_code=$?
  terminate_pid "$BACKEND_PID"
  terminate_pid "$FRONTEND_PID"
  if [[ $exit_code -ne 0 ]]; then
    echo "MCP test failed. Logs:"
    echo "  backend:  $BACKEND_LOG"
    echo "  frontend: $FRONTEND_LOG"
    echo "  result:   $RESULT_FILE"
  fi
}

trap cleanup EXIT INT TERM

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Required command not found: $1" >&2
    exit 1
  fi
}

wait_for_url() {
  local url="$1"
  local name="$2"
  local retries="${3:-60}"
  local delay="${4:-1}"

  local i
  for ((i = 1; i <= retries; i += 1)); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep "$delay"
  done

  echo "Timed out waiting for $name at $url" >&2
  return 1
}

find_free_port() {
  python3 - <<'PY'
import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind(("127.0.0.1", 0))
print(sock.getsockname()[1])
sock.close()
PY
}

require_cmd curl
require_cmd codex
require_cmd rg
require_cmd python3

if ! codex mcp list | rg -q "chrome-devtools"; then
  echo "chrome-devtools MCP server is not configured in codex." >&2
  echo "Install it first, then rerun: npm run test:mcp" >&2
  exit 1
fi

if [[ -z "$BACKEND_PORT" ]]; then
  BACKEND_PORT="$(find_free_port)"
fi
if [[ -z "$FRONTEND_PORT" ]]; then
  FRONTEND_PORT="$(find_free_port)"
fi
while [[ "$BACKEND_PORT" == "$FRONTEND_PORT" ]]; do
  FRONTEND_PORT="$(find_free_port)"
done

APP_URL="http://127.0.0.1:${FRONTEND_PORT}"
API_BASE_URL="http://127.0.0.1:${BACKEND_PORT}/api/v1"

rm -f "$RESULT_FILE"

echo "Starting backend..."
"$ROOT_DIR/start-backend.sh" --no-reload --skip-install --port "$BACKEND_PORT" --frontend-port "$FRONTEND_PORT" >"$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!

echo "Starting frontend..."
"$ROOT_DIR/start-frontend.sh" --skip-install --port "$FRONTEND_PORT" --api-base-url "$API_BASE_URL" >"$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!

wait_for_url "http://127.0.0.1:${BACKEND_PORT}/api/v1/health" "backend API"
wait_for_url "${APP_URL}/" "frontend app"

TS="$(date +%s)"
HOST_EMAIL="host.mcp.${TS}@example.com"
PLAYER_EMAIL="player.mcp.${TS}@example.com"
PASSWORD="Password123!"
STORY_TITLE="MCP Progression ${TS}"
REASON="MCP_quest_reward"

PROMPT=$(cat <<EOF
Use the chrome-devtools MCP server only.
Validate multiplayer progression end-to-end on ${APP_URL}/.

Host credentials:
- email: ${HOST_EMAIL}
- password: ${PASSWORD}

Player credentials:
- email: ${PLAYER_EMAIL}
- password: ${PASSWORD}

Flow:
1) On host page: register, create story '${STORY_TITLE}', create 4-player session, start it, and capture join token.
2) Open a second page in isolated context named 'playerctx' with the join token URL, register player, and click Join Session.
3) Verify multiplayer join succeeded on host page by confirming ACTIVE • 1/4 players and player email visible.
4) On host page, award 350 XP to the player with reason '${REASON}'.
5) Verify host progression row for player shows Level 2 and 350 XP.
6) On player isolated page, verify My Progression shows Level 2 and 350 XP.

End with exactly one line:
RESULT: PASS - <reason>
or
RESULT: FAIL - <reason>
EOF
)

echo "Running Codex MCP validation..."
codex exec --full-auto -C "$ROOT_DIR" "$PROMPT" --output-last-message "$RESULT_FILE"

if [[ ! -s "$RESULT_FILE" ]]; then
  echo "MCP test did not produce a result file." >&2
  exit 1
fi

RESULT_LINE="$(tail -n 1 "$RESULT_FILE" | tr -d '\r')"
echo "$RESULT_LINE"

if [[ "$RESULT_LINE" != RESULT:\ PASS* ]]; then
  echo "MCP validation returned non-pass result." >&2
  exit 1
fi

echo "MCP progression validation passed."
