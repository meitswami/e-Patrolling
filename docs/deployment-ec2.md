# EC2 + Vercel deployment checklist

## Symptoms you may see

| Symptom | Likely cause |
|--------|----------------|
| `[Errno 101] Network is unreachable` on login | EC2 tries **IPv6** to Supabase (no IPv6 egress); HTTPS works but port 5432 on AAAA fails — set `DATABASE_FORCE_IPV4=true` (default) or test `nc -4 -zv db....supabase.co 5432` |
| Browser CORS error on `epatrol-api.duckdns.org` | `ALLOWED_ORIGINS` missing Vercel URL, or API returns 502/500 without reaching FastAPI |
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

## 2. DATABASE_URL on EC2

Prefer the **direct** Supabase host (same as local dev):

```env
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@db.whzmtzatkxgiomwlwkgy.supabase.co:5432/postgres
DATABASE_SSL=true
```

If you use the **pooler** URI from the Supabase dashboard, use the full hostname and ensure the password is URL-encoded. A truncated line (`...postg` instead of `postgres`) will also break auth.

Test from EC2:

```bash
curl -sI https://supabase.com | head -1
nc -4 -zv db.whzmtzatkxgiomwlwkgy.supabase.co 5432   # MUST use -4 on many EC2 VPCs
nc -zv db.whzmtzatkxgiomwlwkgy.supabase.co 5432      # may try IPv6 and fail with errno 101
```

If `nc -4` works but `nc` without `-4` fails → IPv6 routing issue (common). The app uses `DATABASE_FORCE_IPV4=true` to connect via IPv4 only.

If both fail with "Network is unreachable", fix VPC routing first:

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
source .venv/bin/activate
pip install -r requirements.txt
pm2 start ecosystem.config.cjs
pm2 save
pm2 logs backend
```

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
