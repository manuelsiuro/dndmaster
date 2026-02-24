#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-5173}"
INSTALL_DEPS=1
API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8000/api/v1}"

usage() {
  cat <<'EOF'
Usage: ./start-frontend.sh [options]

Options:
  --host <host>       Host to bind (default: 127.0.0.1)
  --port <port>       Port to bind (default: 5173)
  --api-base-url <url>
                     API base URL passed to Vite (default: http://127.0.0.1:8000/api/v1)
  --skip-install      Skip npm install check
  -h, --help          Show this help

Environment overrides:
  HOST, PORT, API_BASE_URL
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      HOST="${2:-}"
      shift 2
      ;;
    --port)
      PORT="${2:-}"
      shift 2
      ;;
    --api-base-url)
      API_BASE_URL="${2:-}"
      shift 2
      ;;
    --skip-install)
      INSTALL_DEPS=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if ! command -v npm >/dev/null 2>&1; then
  echo "npm is required but not found." >&2
  exit 1
fi

cd "$FRONTEND_DIR"

if [[ "$INSTALL_DEPS" -eq 1 ]]; then
  if [[ ! -d "node_modules" || ! -x "node_modules/.bin/vite" ]]; then
    echo "Installing frontend dependencies..."
    npm install
  fi
fi

if [[ ! -f ".env" && -f ".env.example" ]]; then
  echo "Creating frontend .env from .env.example"
  cp ".env.example" ".env"
fi

echo "Starting frontend on http://${HOST}:${PORT}"
echo "Using API base: ${API_BASE_URL}"
exec env VITE_API_BASE_URL="$API_BASE_URL" npm run dev -- --host "$HOST" --port "$PORT" --strictPort
