#!/usr/bin/env bash
# Rebuild Shakti frontend for production subdomain (run on VPS after DNS + SSL).
set -euo pipefail
ROOT="/root/e-Patrolling"
DOMAIN="${SHAKTI_DOMAIN:-shakti.meitcybersolutions.com}"
PUBLIC_URL="https://${DOMAIN}"

cd "$ROOT/frontend"
cp next.config.hostinger.js next.config.js
export NEXT_PUBLIC_API_URL="$PUBLIC_URL"
export NEXT_PUBLIC_WS_URL="wss://${DOMAIN}"
export NEXT_BASE_PATH="${NEXT_BASE_PATH:-}"
npm ci --prefer-offline
npm run build
rsync -a --delete out/ /var/www/shakti/
echo "Frontend deployed to /var/www/shakti with API_URL=$PUBLIC_URL"
