#!/usr/bin/env bash
# One-time bootstrap for Hostinger KVM VPS (Ubuntu).
# Run as root or with sudo on a fresh VPS:
#   curl -fsSL https://raw.githubusercontent.com/YOUR_ORG/e-Patrolling/main/scripts/setup-hostinger-vps.sh | bash
# Or from a cloned repo:
#   sudo bash scripts/setup-hostinger-vps.sh
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Run with sudo: sudo bash scripts/setup-hostinger-vps.sh"
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
APP_USER="${APP_USER:-ubuntu}"
APP_DIR="${APP_DIR:-/home/${APP_USER}/e-Patrolling}"
DEPLOY_DOMAIN="${DEPLOY_DOMAIN:-shakti.bojprtest.in}"

echo "==> Installing system packages"
apt-get update -qq
apt-get install -y -qq \
  git curl ca-certificates nginx \
  python3 python3-venv python3-pip \
  build-essential libpq-dev \
  docker.io docker-compose-plugin

systemctl enable --now docker nginx

if ! id "$APP_USER" &>/dev/null; then
  useradd -m -s /bin/bash "$APP_USER"
fi
usermod -aG docker "$APP_USER" || true

echo "==> Installing Node.js 20"
if ! command -v node &>/dev/null || [ "$(node -p 'process.versions.node.split(".")[0]')" -lt 18 ]; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y -qq nodejs
fi

echo "==> Installing PM2"
npm install -g pm2

echo "==> Postgres via Docker (local patrol_db)"
if ! docker ps --format '{{.Names}}' | grep -q '^patrol_postgres$'; then
  mkdir -p "$APP_DIR"
  if [ -f "$APP_DIR/docker-compose.yml" ]; then
    cd "$APP_DIR"
    docker compose up -d postgres
  else
    docker run -d --name patrol_postgres --restart unless-stopped \
      -e POSTGRES_USER=patrol \
      -e POSTGRES_PASSWORD=patrol_secret \
      -e POSTGRES_DB=patrol_db \
      -p 127.0.0.1:5432:5432 \
      -v patrol_postgres_data:/var/lib/postgresql/data \
      postgres:15-alpine
  fi
fi

echo "==> Nginx site for ${DEPLOY_DOMAIN}"
if [ -f "$APP_DIR/deploy/nginx-shakti.conf" ]; then
  cp "$APP_DIR/deploy/nginx-shakti.conf" /etc/nginx/sites-available/shakti
else
  echo "WARN: clone repo first, then re-run to install nginx config"
fi
ln -sf /etc/nginx/sites-available/shakti /etc/nginx/sites-enabled/shakti
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

mkdir -p /var/www/shakti
chown -R "${APP_USER}:${APP_USER}" /var/www/shakti

echo ""
echo "Bootstrap complete."
echo "Next steps:"
echo "  1. DNS: A record ${DEPLOY_DOMAIN} → $(curl -4 -s ifconfig.me || hostname -I | awk '{print $1}')"
echo "  2. Add GitHub deploy key / SSH key for ${APP_USER}"
echo "  3. Clone repo: sudo -u ${APP_USER} git clone <repo-url> ${APP_DIR}"
echo "  4. bash scripts/setup-hostinger-env.sh && nano ${APP_DIR}/.env"
echo "  5. Push to main — GitHub Actions deploy-hostinger.yml runs automatically"
