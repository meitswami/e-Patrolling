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
export NEXT_PUBLIC_API_URL="${PUBLIC_URL:-http://187.127.185.243}"
export NEXT_PUBLIC_WS_URL="${WS_URL:-ws://187.127.185.243}"
export NEXT_BASE_PATH="${NEXT_BASE_PATH:-}"
npm ci
npm run build
mkdir -p /var/www/shakti
rsync -a --delete out/ /var/www/shakti/

cd "$ROOT"
cp deploy/nginx-shakti.conf /etc/nginx/sites-available/shakti
ln -sf /etc/nginx/sites-available/shakti /etc/nginx/sites-enabled/shakti

cat > /etc/nginx/sites-available/shakti-ip <<'NGINX'
server {
    listen 80 default_server;
    server_name 187.127.185.243 _;
    client_max_body_size 25M;

    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 300s;
    }

    location /ws/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    location /health {
        proxy_pass http://127.0.0.1:5000;
    }

    location / {
        root /var/www/shakti;
        try_files $uri $uri/ $uri.html /index.html;
    }
}
NGINX
ln -sf /etc/nginx/sites-available/shakti-ip /etc/nginx/sites-enabled/shakti-ip
rm -f /etc/nginx/sites-enabled/default
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
