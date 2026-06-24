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

TEMPLATE="$ROOT/deploy/env.production.hostinger.example"
if [ ! -f "$TEMPLATE" ]; then
  echo "ERROR: $TEMPLATE not found"
  exit 1
fi

cp "$TEMPLATE" .env

# Apply runtime domain (subdomain or path deploy)
CORS="${PUBLIC_URL},https://bojprtest.in,https://www.bojprtest.in,https://e-patrolling.vercel.app,http://localhost:3000"
sed -i "s|^ALLOWED_ORIGINS=.*|ALLOWED_ORIGINS=${CORS}|" .env
sed -i "s|^NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=${PUBLIC_URL}|" .env
sed -i "s|^NEXT_PUBLIC_WS_URL=.*|NEXT_PUBLIC_WS_URL=wss://${DEPLOY_DOMAIN}|" .env

echo "NEXT_PUBLIC_API_URL=${PUBLIC_URL}" > frontend/.env.production.local
echo "NEXT_PUBLIC_WS_URL=wss://${DEPLOY_DOMAIN}" >> frontend/.env.production.local

echo "==> Created $ROOT/.env from deploy/env.production.hostinger.example"
echo ""
echo "REQUIRED — set real secrets before starting the API:"
echo "  nano .env"
echo "  1. DATABASE_URL  (Supabase Session pooler — copy from deploy/env.production.hostinger)"
echo "  2. JWT_SECRET_KEY  (openssl rand -hex 32)"
echo ""
echo "Or copy your full production file from your PC:"
echo "  scp deploy/env.production.hostinger ubuntu@187.127.185.243:~/e-Patrolling/.env"
