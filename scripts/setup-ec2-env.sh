#!/usr/bin/env bash
# One-time (or repair) production .env on EC2.
# Run from repo root: bash scripts/setup-ec2-env.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ -f .env ]; then
  echo "==> .env already exists at $ROOT/.env"
  echo "    Edit with: nano .env"
  exit 0
fi

if [ ! -f .env.example ]; then
  echo "ERROR: .env.example not found"
  exit 1
fi

cp .env.example .env

# Production defaults (secrets must be filled manually or via GitHub Actions secrets)
sed -i 's/^ENVIRONMENT=development/ENVIRONMENT=production/' .env
sed -i 's/^CRAWLER_DEMO_MODE=true/CRAWLER_DEMO_MODE=false/' .env
sed -i 's|^ALLOWED_ORIGINS=.*|ALLOWED_ORIGINS=https://e-patrolling.vercel.app,http://localhost:3000|' .env

echo "==> Created $ROOT/.env from .env.example"
echo ""
echo "REQUIRED — edit these before starting the API:"
echo "  nano .env"
echo ""
echo "  1. DATABASE_URL=postgresql+asyncpg://postgres:PASSWORD@db....supabase.co:5432/postgres"
echo "  2. JWT_SECRET_KEY=<run: openssl rand -hex 32>"
echo "  3. SUPABASE keys (if used)"
echo ""
echo "Then:"
echo "  source .venv/bin/activate && pip install -r requirements.txt"
echo "  pm2 start ecosystem.config.cjs && pm2 save"
