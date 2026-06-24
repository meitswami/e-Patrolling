#!/usr/bin/env bash
set -euo pipefail
ROOT="/root/e-Patrolling"
cd "$ROOT"

mkdir -p storage/sessions storage/logs storage/evidence storage/screenshots
chmod 700 storage/sessions

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -U pip -q
pip install -r requirements.txt -q

export PLAYWRIGHT_HOST_PLATFORM_OVERRIDE=ubuntu24.04-x64
python -m playwright install --with-deps chromium

cd "$ROOT/frontend"
cp next.config.hostinger.js next.config.js
SHAKTI_DOMAIN="${DEPLOY_DOMAIN:-shakti.bojprtest.in}"
PUBLIC_URL="${PUBLIC_URL:-https://${SHAKTI_DOMAIN}}"
export NEXT_PUBLIC_API_URL="$PUBLIC_URL"
export NEXT_PUBLIC_WS_URL="wss://${SHAKTI_DOMAIN}"
export NEXT_BASE_PATH="${NEXT_BASE_PATH:-}"
npm ci
npm run build
mkdir -p /var/www/shakti
rsync -a --delete out/ /var/www/shakti/

cd "$ROOT"
cp deploy/nginx-shakti.conf /etc/nginx/sites-available/shakti
ln -sf /etc/nginx/sites-available/shakti /etc/nginx/sites-enabled/01-shakti
# Do not bind Shakti to raw IP — other projects use subdomain vhosts under /var/www/
nginx -t
systemctl reload nginx

chmod +x scripts/start-backend.sh
pm2 delete backend 2>/dev/null || true
pm2 start ecosystem.config.cjs
pm2 save
pm2 startup systemd -u root --hp /root >/dev/null 2>&1 || true

echo "Waiting for backend..."
for i in $(seq 1 24); do
  if curl -sf http://127.0.0.1:5000/health >/dev/null; then
    curl -s http://127.0.0.1:5000/health
    echo ""
    echo "DEPLOY_OK"
    exit 0
  fi
  sleep 5
done
pm2 logs backend --lines 40 --nostream
exit 1
