#!/usr/bin/env bash
# Quick production diagnostics on EC2. Run: bash scripts/ec2-check.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== .env ==="
if [ -f .env ]; then
  grep -E '^ENVIRONMENT=|^DATABASE_URL=|^ALLOWED_ORIGINS=' .env | sed 's/:[^@]*@/:***@/'
else
  echo "MISSING .env — copy from .env.example or scp from your PC"
fi

echo ""
echo "=== Python venv ==="
ls -la .venv/bin/uvicorn 2>/dev/null || echo "no .venv/bin/uvicorn"
ls -la venv/bin/uvicorn 2>/dev/null || echo "no venv/bin/uvicorn"

echo ""
echo "=== PM2 ==="
pm2 status backend 2>/dev/null || pm2 status

echo ""
echo "=== Port 5000 ==="
ss -tlnp 2>/dev/null | grep ':5000' || echo "nothing listening on 5000 (502 Bad Gateway cause)"

echo ""
echo "=== Health (local) ==="
curl -sS -m 5 http://127.0.0.1:5000/health || echo "health check FAILED"

echo ""
echo "=== PM2 logs (last 25 lines) ==="
pm2 logs backend --lines 25 --nostream 2>/dev/null || true
