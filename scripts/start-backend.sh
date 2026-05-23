#!/usr/bin/env bash
# Start PATROL API on EC2 (used by PM2 ecosystem.config.cjs).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ -f "$ROOT/.venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
elif [ -f "$ROOT/venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source "$ROOT/venv/bin/activate"
else
  echo "ERROR: No Python venv at $ROOT/.venv or $ROOT/venv" >&2
  echo "Run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt" >&2
  exit 1
fi

if ! command -v uvicorn >/dev/null 2>&1; then
  echo "ERROR: uvicorn not installed in venv" >&2
  exit 1
fi

cd "$ROOT/backend"
exec uvicorn main:app --host 0.0.0.0 --port 5000
