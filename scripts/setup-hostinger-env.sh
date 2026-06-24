#!/usr/bin/env bash
# Create production .env on Hostinger VPS.
# Run from repo root: bash scripts/setup-hostinger-env.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DEPLOY_DOMAIN="${DEPLOY_DOMAIN:-shakti.bojprtest.in}"
PUBLIC_URL="https://${DEPLOY_DOMAIN}"

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

sed -i 's/^ENVIRONMENT=development/ENVIRONMENT=production/' .env
sed -i 's/^CRAWLER_DEMO_MODE=true/CRAWLER_DEMO_MODE=false/' .env
sed -i 's/^REDIS_ENABLED=false/REDIS_ENABLED=false/' .env

# Local Postgres on VPS (docker)
if grep -q '^DATABASE_URL=' .env; then
  sed -i 's|^DATABASE_URL=.*|DATABASE_URL=postgresql+asyncpg://patrol:patrol_secret@127.0.0.1:5432/patrol_db|' .env
fi
sed -i 's/^DATABASE_FORCE_IPV4=.*/DATABASE_FORCE_IPV4=false/' .env

CORS="${PUBLIC_URL},https://bojprtest.in,https://www.bojprtest.in,http://localhost:3000"
if grep -q '^ALLOWED_ORIGINS=' .env; then
  sed -i "s|^ALLOWED_ORIGINS=.*|ALLOWED_ORIGINS=${CORS}|" .env
else
  echo "ALLOWED_ORIGINS=${CORS}" >> .env
fi

echo "NEXT_PUBLIC_API_URL=${PUBLIC_URL}" > frontend/.env.production.local
echo "NEXT_PUBLIC_WS_URL=wss://${DEPLOY_DOMAIN}" >> frontend/.env.production.local

echo "==> Created $ROOT/.env for Hostinger"
echo ""
echo "REQUIRED — edit before first deploy:"
echo "  nano .env"
echo "  1. JWT_SECRET_KEY  (openssl rand -hex 32)"
echo "  2. DATABASE_URL    (default: local Docker Postgres)"
echo "  3. Or use Supabase pooler URL if you prefer cloud DB"
echo ""
echo "Instagram session: storage/sessions/ is deployed from git or GitHub secrets."
