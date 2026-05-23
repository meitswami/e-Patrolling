#!/usr/bin/env bash
# Show which DB host is configured (passwords masked). Run on EC2 after editing .env.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
for f in "$ROOT/.env" "$ROOT/backend/.env"; do
  if [ -f "$f" ]; then
    echo "=== $f ==="
    grep '^DATABASE_URL=' "$f" | sed -E 's#(postgresql(\+asyncpg)?://[^:@]+):[^@]*@#\1:***@#'
    grep '^DATABASE_FORCE_IPV4=' "$f" 2>/dev/null || true
  fi
done
