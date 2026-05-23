# EC2 + Vercel deployment checklist

## Symptoms you may see

| Symptom | Likely cause |
|--------|----------------|
| `[Errno 101] Network is unreachable` on login | **`db.*.supabase.co` is IPv6-only**; most EC2 VPCs have no IPv6 egress. Use **Session pooler** URI (IPv4), not direct `db.` host |
| `nc -4` → *No address associated with hostname* | Normal for direct `db.` host — no IPv4. Use pooler host **from dashboard** (may be `aws-1-REGION`, not `aws-0`) |
| `Tenant or user not found` | Pooler hostname wrong for your project — copy **exact** Session pooler host from Dashboard → Connect |
| Browser CORS error on `epatrol-api.duckdns.org` | `ALLOWED_ORIGINS` missing Vercel URL, or API returns 502/500 without reaching FastAPI |
| **502 Bad Gateway** on login | nginx OK but **nothing on port 5000** — PM2/uvicorn crashed; run `bash scripts/ec2-check.sh` and `pm2 logs backend` |
| "Cannot reach API" on login page | Reverse proxy not running, wrong port, or security group blocks 443 |

## 1. Create `.env` on EC2 (required)

`.env` is **not** in git. If `grep .env` says *No such file*, the API has no database URL, JWT secret, or CORS config.

```bash
cd ~/e-Patrolling
bash scripts/setup-ec2-env.sh
nano .env   # set DATABASE_URL and JWT_SECRET_KEY (see below)
```

Settings loads **both** (backend overrides root):

1. `~/e-Patrolling/.env` ← **use this on EC2**
2. `~/e-Patrolling/backend/.env`

Copy values from your **local** machine’s working `.env` (same Supabase project), or from Supabase Dashboard → Database → connection string (add `+asyncpg` after `postgresql`).

## 2. DATABASE_URL on EC2 — use the pooler (not `db.*.supabase.co`)

Supabase **direct** host `db.<project>.supabase.co` resolves to **IPv6 only**. Typical EC2 VPCs cannot reach it (`errno 101` or `nc -4` → *No address associated with hostname*).

### Fix (recommended)

1. Supabase Dashboard → your project → **Connect** → **ORMs** or **Connection string**
2. Copy **Session pooler** (port **5432**) — not “Direct connection”
3. Change the prefix to `postgresql+asyncpg://`
4. Username is **`postgres.whzmtzatkxgiomwlwkgy`** (not plain `postgres`)

Example (replace host + password from dashboard — **do not guess** `aws-0` vs `aws-1`):

```env
DATABASE_URL=postgresql+asyncpg://postgres.whzmtzatkxgiomwlwkgy:YOUR_PASSWORD@aws-1-ap-south-1.pooler.supabase.com:5432/postgres
DATABASE_SSL=true
DATABASE_FORCE_IPV4=false
ENVIRONMENT=production
```

Test from EC2 (use **your** pooler host from the dashboard):

```bash
nc -4 -zv aws-1-ap-south-1.pooler.supabase.com 5432
curl -s http://127.0.0.1:5000/health
```

Expect `"database":"connected"`.

### Alternatives

- Enable **IPv6 egress** on the VPC (subnet IPv6 + route `::/0`), then direct `db.` URL can work
- Paid **IPv4 add-on** on Supabase Pro for direct connection IPv4

If pooler `nc -4` fails with "Network is unreachable", fix VPC outbound routing first:

- Public subnet + Internet Gateway, **or**
- Private subnet + NAT Gateway
- Security group: allow **outbound** TCP 443 and 5432

## 3. CORS for Vercel

In `~/e-Patrolling/.env` (or `backend/.env`):

```env
ENVIRONMENT=production
ALLOWED_ORIGINS=https://e-patrolling.vercel.app,http://localhost:3000
```

The app also merges `CORS_EXTRA_ORIGINS` (includes `https://e-patrolling.vercel.app`) and, when `ENVIRONMENT=production`, allows `https://*.vercel.app` via regex.

**GitHub Actions deploy** (`ecosystem.config.cjs` + updated workflow) sets PM2 correctly and patches `.env` if `ALLOWED_ORIGINS` is missing.

Restart after manual env changes:

```bash
cd ~/e-Patrolling && pm2 restart backend
```

Verify CORS from the server:

```bash
curl -s -D - -o /dev/null -X OPTIONS "http://127.0.0.1:5000/api/v1/auth/login" \
  -H "Origin: https://e-patrolling.vercel.app" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type"
```

You must see `access-control-allow-origin: https://e-patrolling.vercel.app`.

If OPTIONS works on `:5000` but the browser still fails on `https://epatrol-api.duckdns.org`, nginx is not proxying OPTIONS to uvicorn (see `deploy/nginx-patrol-api.conf`).

## 4. Expose the API (DuckDNS + HTTPS)

Uvicorn on port 5000 is not enough for `https://epatrol-api.duckdns.org`. Use nginx or Caddy:

```nginx
server {
    listen 443 ssl;
    server_name epatrol-api.duckdns.org;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Open EC2 security group: **443** (and **80** for Let's Encrypt).

## 5. Run as a service (PM2)

```bash
cd ~/e-Patrolling
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
chmod +x scripts/start-backend.sh scripts/ec2-check.sh
pm2 delete backend 2>/dev/null || true
pm2 start ecosystem.config.cjs
pm2 save
bash scripts/ec2-check.sh
```

If `ec2-check` shows *nothing listening on 5000*, read `pm2 logs backend` — often missing `.venv/bin/uvicorn` (old deploy used `venv/` only).

**Common deploy mistake:** using `venv` instead of `.venv`, or wrong uvicorn path — the API never starts and the browser shows a CORS error (nginx 502 has no CORS headers).

Verify:

```bash
curl -s http://127.0.0.1:5000/health | jq
```

Expect `"database": "connected"` before testing login from Vercel.

## 6. Vercel frontend

Set in Vercel project → Environment variables:

- `NEXT_PUBLIC_API_URL=https://epatrol-api.duckdns.org`
- `NEXT_PUBLIC_WS_URL=wss://epatrol-api.duckdns.org`

Redeploy after changing.

## 7. Seed admin user (once DB works)

```bash
cd ~/e-Patrolling
source venv/bin/activate
python scripts/seed_db.py
```

Default: `admin@patrol.dev` / `Patrol@2024!` (match `ADMIN_EMAIL` / `ADMIN_PASSWORD` in `.env`).
