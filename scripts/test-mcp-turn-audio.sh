#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_LOG="/tmp/dw-mcp-turn-audio-backend.log"
FRONTEND_LOG="/tmp/dw-mcp-turn-audio-frontend.log"
RESULT_FILE="/tmp/codex_mcp_turn_audio_test.txt"
BACKEND_PID=""
FRONTEND_PID=""
BACKEND_SERVER_PID=""
FRONTEND_SERVER_PID=""

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
  terminate_pid "$BACKEND_SERVER_PID"
  terminate_pid "$FRONTEND_SERVER_PID"
  terminate_pid "$BACKEND_PID"
  terminate_pid "$FRONTEND_PID"
  if [[ $exit_code -ne 0 ]]; then
    echo "MCP turn-audio test failed. Logs:"
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

require_cmd curl
require_cmd codex
require_cmd rg
require_cmd lsof

if ! codex mcp list | rg -q "chrome-devtools"; then
  echo "chrome-devtools MCP server is not configured in codex." >&2
  echo "Install it first, then rerun: npm run test:mcp:turn-audio" >&2
  exit 1
fi

rm -f "$RESULT_FILE"

echo "Starting backend..."
"$ROOT_DIR/start-backend.sh" --no-reload --skip-install >"$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!

echo "Starting frontend..."
"$ROOT_DIR/start-frontend.sh" --skip-install >"$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!

wait_for_url "http://127.0.0.1:8000/api/v1/health" "backend API"
wait_for_url "http://127.0.0.1:5173/" "frontend app"

BACKEND_SERVER_PID="$(lsof -tiTCP:8000 -sTCP:LISTEN | head -n 1 || true)"
FRONTEND_SERVER_PID="$(lsof -tiTCP:5173 -sTCP:LISTEN | head -n 1 || true)"

TS="$(date +%s)"
HOST_EMAIL="host.turn.audio.${TS}@example.com"
PASSWORD="Password123!"
STORY_TITLE="MCP Turn Audio ${TS}"
PLAYER_INPUT="I quietly study the obsidian gate for hidden runes and echoes."

PROMPT=$(cat <<EOF
Use the chrome-devtools MCP server only.
Validate turn audio replay and export flow on http://127.0.0.1:5173/.

Host credentials:
- email: ${HOST_EMAIL}
- password: ${PASSWORD}

Flow:
1) Register the host account.
2) Create story '${STORY_TITLE}'.
3) In 'Generate GM response', enter '${PLAYER_INPUT}' and click 'Generate GM Response'.
4) Verify timeline includes both a 'player action' card and a 'gm prompt' card with the same Turn tag.
5) Verify 'Turn Audio Timeline' is visible with at least one waveform track and one transcript timestamp row.
6) Click 'Play Turn Audio' and confirm visible status text contains either 'Playing clip' or 'Finished turn playback'.
7) Click 'Export Turn Pack' and confirm visible status text contains 'Exported turn pack'.

End with exactly one line:
RESULT: PASS - <reason>
or
RESULT: FAIL - <reason>
EOF
)

echo "Running Codex MCP turn-audio validation..."
codex exec --full-auto -C "$ROOT_DIR" "$PROMPT" --output-last-message "$RESULT_FILE"

if [[ ! -s "$RESULT_FILE" ]]; then
  echo "MCP turn-audio test did not produce a result file." >&2
  exit 1
fi

RESULT_LINE="$(tail -n 1 "$RESULT_FILE" | tr -d '\r')"
echo "$RESULT_LINE"

if [[ "$RESULT_LINE" != RESULT:\ PASS* ]]; then
  echo "MCP turn-audio validation returned non-pass result." >&2
  exit 1
fi

echo "MCP turn-audio validation passed."
