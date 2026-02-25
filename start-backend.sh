#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
RELOAD=1
INSTALL_DEPS=1
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

usage() {
  cat <<'EOF'
Usage: ./start-backend.sh [options]

Options:
  --host <host>       Host to bind (default: 127.0.0.1)
  --port <port>       Port to bind (default: 8000)
  --frontend-port <port>
                     Frontend port allowed in CORS (default: 5173)
  --reload            Enable uvicorn reload (default)
  --no-reload         Disable uvicorn reload
  --skip-install      Skip dependency installation check
  -h, --help          Show this help

Environment overrides:
  HOST, PORT, FRONTEND_PORT
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
    --frontend-port)
      FRONTEND_PORT="${2:-}"
      shift 2
      ;;
    --reload)
      RELOAD=1
      shift
      ;;
    --no-reload)
      RELOAD=0
      shift
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

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required but not found." >&2
  exit 1
fi

cd "$BACKEND_DIR"

if [[ ! -d ".venv" ]]; then
  echo "Creating backend virtual environment (.venv)..."
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source ".venv/bin/activate"

if [[ "$INSTALL_DEPS" -eq 1 ]]; then
  if ! python -c "import fastapi, uvicorn, sqlalchemy, pgvector" >/dev/null 2>&1; then
    echo "Installing backend dependencies..."
    pip install -e ".[dev]"
  fi
fi

if [[ ! -f ".env" && -f ".env.example" ]]; then
  echo "Creating backend .env from .env.example"
  cp ".env.example" ".env"
fi

echo "Starting backend on http://${HOST}:${PORT}"
CORS_ORIGINS_JSON="[\"http://127.0.0.1:${FRONTEND_PORT}\",\"http://localhost:${FRONTEND_PORT}\"]"
echo "Allowing CORS origins: ${CORS_ORIGINS_JSON}"
if [[ "$RELOAD" -eq 1 ]]; then
  exec env DW_CORS_ORIGINS="$CORS_ORIGINS_JSON" uvicorn app.main:app --host "$HOST" --port "$PORT" --reload
else
  exec env DW_CORS_ORIGINS="$CORS_ORIGINS_JSON" uvicorn app.main:app --host "$HOST" --port "$PORT"
fi
