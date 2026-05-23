# EC2 + Vercel deployment checklist

## Symptoms you may see

| Symptom | Likely cause |
|--------|----------------|
| `[Errno 101] Network is unreachable` on login | EC2 cannot reach Supabase (no internet route / wrong `.env`) |
| Browser CORS error on `epatrol-api.duckdns.org` | `ALLOWED_ORIGINS` missing Vercel URL, or API returns 502/500 without reaching FastAPI |
| "Cannot reach API" on login page | Reverse proxy not running, wrong port, or security group blocks 443 |

## 1. Use the correct `.env` file

Settings loads **both** (backend overrides root):

1. `~/e-Patrolling/.env`
2. `~/e-Patrolling/backend/.env`

Put production secrets in **one** of these; if you only maintain `backend/.env`, that is now supported.

## 2. DATABASE_URL on EC2

Prefer the **direct** Supabase host (same as local dev):

```env
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@db.whzmtzatkxgiomwlwkgy.supabase.co:5432/postgres
DATABASE_SSL=true
```

If you use the **pooler** URI from the Supabase dashboard, use the full hostname and ensure the password is URL-encoded. A truncated line (`...postg` instead of `postgres`) will also break auth.

Test from EC2:

```bash
curl -sI https://whzmtzatkxgiomwlwkgy.supabase.co | head -1
nc -zv db.whzmtzatkxgiomwlwkgy.supabase.co 5432
```

If `nc` fails with "Network is unreachable", fix VPC routing first:

- Public subnet + Internet Gateway, **or**
- Private subnet + NAT Gateway
- Security group: allow **outbound** TCP 443 and 5432

## 3. CORS for Vercel

In `.env` on the server:

```env
ENVIRONMENT=production
ALLOWED_ORIGINS=https://e-patrolling.vercel.app,http://localhost:3000
```

Restart uvicorn after changing env vars.

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

## 5. Run as a service

```bash
cd ~/e-Patrolling
source venv/bin/activate
cd backend
uvicorn main:app --host 0.0.0.0 --port 5000
```

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
