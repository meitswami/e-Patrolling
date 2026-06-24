#!/usr/bin/env bash
# Copy evidence/screenshot files from AWS EC2 to this Hostinger VPS.
# Database rows already live in Supabase — only files need copying.
#
# Usage (on Hostinger VPS as root):
#   export EC2_HOST=ec2-xx-xx-xx-xx.ap-northeast-1.compute.amazonaws.com
#   export EC2_KEY=/root/.ssh/ec2.pem
#   bash scripts/migrate-storage-from-ec2.sh
#
# Or from your PC (PowerShell) with OpenSSH rsync:
#   scp -i ec2.pem scripts/migrate-storage-from-ec2.sh root@187.127.185.243:/root/e-Patrolling/scripts/
#   ssh -i deploy.pem root@187.127.185.243 "EC2_HOST=... EC2_KEY=/root/.ssh/ec2.pem bash /root/e-Patrolling/scripts/migrate-storage-from-ec2.sh"
set -euo pipefail

ROOT="${ROOT:-/root/e-Patrolling}"
EC2_USER="${EC2_USER:-ubuntu}"
EC2_HOST="${EC2_HOST:?Set EC2_HOST (public DNS or IP of old EC2)}"
EC2_KEY="${EC2_KEY:-$HOME/.ssh/ec2.pem}"
# EC2 used relative EVIDENCE_STORAGE_PATH=./storage/evidence → backend/storage/evidence
EC2_STORAGE="${EC2_STORAGE:-~/e-Patrolling/backend/storage/}"
REMOTE="${EC2_USER}@${EC2_HOST}:${EC2_STORAGE}"

SSH_OPTS=(-o StrictHostKeyChecking=accept-new)
if [ -f "$EC2_KEY" ]; then
  SSH_OPTS+=(-i "$EC2_KEY")
fi

mkdir -p "$ROOT/storage/evidence" "$ROOT/storage/screenshots"

echo "==> Syncing storage from EC2 ($REMOTE) → $ROOT/storage/"
rsync -avz --progress -e "ssh ${SSH_OPTS[*]}" "$REMOTE" "$ROOT/storage/"

echo "==> File counts"
find "$ROOT/storage/evidence" -type f | wc -l | xargs echo "evidence files:"
du -sh "$ROOT/storage/evidence" "$ROOT/storage/screenshots"

echo "==> Restart backend"
cd "$ROOT" && pm2 restart backend

echo "Done. Test: curl -sI https://shakti.bojprtest.in/storage/evidence/instagram/..."
