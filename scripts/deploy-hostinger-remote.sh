#!/usr/bin/env bash
# Remote deploy steps for Hostinger VPS (invoked by GitHub Actions over SSH).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DEPLOY_DOMAIN="${DEPLOY_DOMAIN:-shakti.bojprtest.in}"
PUBLIC_URL="${PUBLIC_URL:-https://${DEPLOY_DOMAIN}}"
NEXT_BASE_PATH="${NEXT_BASE_PATH:-}"
FRONTEND_OUT="${FRONTEND_OUT:-/var/www/shakti}"

echo "==> Pull latest code"
git fetch origin main
git reset --hard origin/main

echo "==> Restore Instagram session (git + optional secrets)"
mkdir -p storage/sessions storage/logs storage/evidence storage/screenshots
chmod 700 storage/sessions

if [ -n "${INSTAGRAM_STATE_B64:-}" ]; then
  echo "$INSTAGRAM_STATE_B64" | base64 -d > storage/sessions/instagram_state.json
fi
if [ -n "${INSTAGRAM_META_B64:-}" ]; then
  echo "$INSTAGRAM_META_B64" | base64 -d > storage/sessions/instagram_meta.json
fi

if [ -f storage/sessions/instagram_state.json ]; then
  echo "Instagram session present ($(wc -c < storage/sessions/instagram_state.json) bytes)"
else
  echo "WARN: No instagram_state.json — connect Instagram in Settings after deploy"
fi

echo "==> Python backend"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -U pip -q
pip install -r requirements.txt -q

export PLAYWRIGHT_HOST_PLATFORM_OVERRIDE=ubuntu24.04-x64
python -m playwright install --with-deps chromium 2>/dev/null || {
  sudo python -m playwright install-deps chromium 2>/dev/null || true
  python -m playwright install chromium 2>/dev/null || true
}

if [ ! -f .env ]; then
  bash scripts/setup-hostinger-env.sh
fi

# Production toggles
if grep -q '^ENVIRONMENT=development' .env; then
  sed -i 's/^ENVIRONMENT=development/ENVIRONMENT=production/' .env
fi
if grep -q '^CRAWLER_DEMO_MODE=true' .env; then
  sed -i 's/^CRAWLER_DEMO_MODE=true/CRAWLER_DEMO_MODE=false/' .env
fi

CORS="${PUBLIC_URL},https://bojprtest.in,https://www.bojprtest.in,https://e-patrolling.vercel.app,http://localhost:3000"
if grep -q '^ALLOWED_ORIGINS=' .env; then
  sed -i "s|^ALLOWED_ORIGINS=.*|ALLOWED_ORIGINS=${CORS}|" .env
fi

for key in PRELOAD_AI_MODELS USE_ML_CLASSIFIER USE_INDICBERT; do
  if grep -q "^${key}=true" .env; then
    sed -i "s/^${key}=true/${key}=false/" .env
  fi
done

if [ -n "${HOSTINGER_DATABASE_URL:-}" ]; then
  if grep -q '^DATABASE_URL=' .env; then
    sed -i "s|^DATABASE_URL=.*|DATABASE_URL=${HOSTINGER_DATABASE_URL}|" .env
  else
    echo "DATABASE_URL=${HOSTINGER_DATABASE_URL}" >> .env
  fi
fi
if [ -n "${HOSTINGER_JWT_SECRET:-}" ]; then
  if grep -q '^JWT_SECRET_KEY=' .env; then
    sed -i "s|^JWT_SECRET_KEY=.*|JWT_SECRET_KEY=${HOSTINGER_JWT_SECRET}|" .env
  else
    echo "JWT_SECRET_KEY=${HOSTINGER_JWT_SECRET}" >> .env
  fi
fi

if grep -qE 'YOUR_SUPABASE_PASSWORD|YOUR-PASSWORD|change_me_use_openssl' .env; then
  echo "ERROR: .env still has placeholder DATABASE_URL or JWT_SECRET_KEY."
  echo "Copy production env: scp deploy/env.production.hostinger ubuntu@HOST:~/e-Patrolling/.env"
  echo "Or set GitHub secrets: HOSTINGER_DATABASE_URL, HOSTINGER_JWT_SECRET"
  exit 1
fi

echo "==> Ensure Postgres is running"
if docker ps --format '{{.Names}}' | grep -q '^patrol_postgres$'; then
  echo "patrol_postgres container OK"
elif docker ps -a --format '{{.Names}}' | grep -q '^patrol_postgres$'; then
  docker start patrol_postgres
else
  docker compose up -d postgres 2>/dev/null || true
fi

echo "==> Frontend static export"
cd "$ROOT/frontend"
cp next.config.hostinger.js next.config.js
export NEXT_PUBLIC_API_URL="${PUBLIC_URL}"
export NEXT_PUBLIC_WS_URL="wss://${DEPLOY_DOMAIN}"
export NEXT_BASE_PATH="${NEXT_BASE_PATH}"
npm ci --prefer-offline
npm run build
sudo mkdir -p "$FRONTEND_OUT"
sudo rsync -a --delete out/ "${FRONTEND_OUT}/"
cd "$ROOT"

echo "==> Nginx"
if [ -f deploy/nginx-shakti.conf ]; then
  sudo cp deploy/nginx-shakti.conf /etc/nginx/sites-available/shakti
  sudo ln -sf /etc/nginx/sites-available/shakti /etc/nginx/sites-enabled/shakti
  sudo nginx -t
  sudo systemctl reload nginx
fi

chmod +x scripts/start-backend.sh
pm2 delete backend 2>/dev/null || true
pm2 start ecosystem.config.cjs
pm2 save

echo "==> Health check"
ok=0
for i in $(seq 1 18); do
  if curl -sf http://127.0.0.1:5000/health >/dev/null; then
    ok=1
    curl -s http://127.0.0.1:5000/health
    echo ""
    break
  fi
  echo "Waiting for backend... attempt $i/18"
  sleep 5
done
if [ "$ok" -ne 1 ]; then
  pm2 logs backend --lines 50 --nostream
  exit 1
fi

echo "Deploy finished OK — ${PUBLIC_URL}"
