# Hostinger VPS + bojprtest.in/shakti deployment

Deploy **Shakti** to your Hostinger KVM VPS (`187.127.185.243`) with GitHub Actions. Instagram sessions in `storage/sessions/` are tracked in git and synced on every deploy.

## Architecture

| Component | Where |
|-----------|--------|
| API (FastAPI + crawlers) | VPS `:5000` via PM2 |
| Frontend (Next.js static) | `/var/www/shakti` via nginx |
| Postgres | Docker on VPS (`patrol_postgres`) or Supabase |
| Instagram session | `storage/sessions/*.json` in git |

**Recommended URL:** `https://shakti.bojprtest.in`  
Path-based `https://bojprtest.in/shakti/` is supported — set repo variable `NEXT_BASE_PATH=/shakti` and uncomment the path block in `deploy/nginx-shakti.conf`.

## 1. DNS (bojprtest.in account)

In the **other** Hostinger account that owns `bojprtest.in`:

1. DNS zone → add **A record**
   - Name: `shakti`
   - Points to: `187.127.185.243`
   - TTL: 300

Wait a few minutes, then verify: `ping shakti.bojprtest.in`

> `bojprtest.in/shakti/` on shared hosting shows the default Hostinger page until you either point the subdomain to the VPS (above) or upload a static build to `public_html/shakti/`. The automated workflow deploys to the **VPS**, not shared hosting FTP.

## 2. One-time VPS setup

SSH into the VPS (Hostinger hPanel → VPS → Manage → SSH):

```bash
ssh ubuntu@187.127.185.243
```

Clone the repo and bootstrap:

```bash
git clone https://github.com/YOUR_ORG/e-Patrolling.git /home/ubuntu/e-Patrolling
cd /home/ubuntu/e-Patrolling
sudo bash scripts/setup-hostinger-vps.sh
```

**Production `.env` (same Supabase DB as former EC2):**

From your PC:

```bash
scp deploy/env.production.hostinger ubuntu@187.127.185.243:~/e-Patrolling/.env
```

Or on the VPS, copy the example and paste your Supabase pooler URL + JWT:

```bash
cp deploy/env.production.hostinger.example .env
nano .env
```

`deploy/env.production.hostinger` is gitignored (contains secrets). The committed template is `deploy/env.production.hostinger.example`.

## 3. GitHub secrets (Settings → Secrets and variables → Actions)

| Secret | Value |
|--------|--------|
| `HOSTINGER_SSH_HOST` | `187.127.185.243` |
| `HOSTINGER_SSH_USER` | `ubuntu` or `root` |
| `HOSTINGER_SSH_KEY` | Private SSH key (PEM) for deploy |
| `HOSTINGER_JWT_SECRET` | Same as `.env` JWT_SECRET_KEY |
| `HOSTINGER_DATABASE_URL` | Same Supabase Session pooler URL as `deploy/env.production.hostinger` |
| `HOSTINGER_JWT_SECRET` | Same as `JWT_SECRET_KEY` in `.env` |

**Optional** (override git-tracked sessions):

| Secret | Value |
|--------|--------|
| `INSTAGRAM_STATE_B64` | `base64 -w0 storage/sessions/instagram_state.json` |
| `INSTAGRAM_META_B64` | `base64 -w0 storage/sessions/instagram_meta.json` |

## 4. GitHub variables (optional)

| Variable | Default | Purpose |
|----------|---------|---------|
| `HOSTINGER_DEPLOY_ENABLED` | `true` | Set `false` to skip Hostinger deploy |
| `DEPLOY_DOMAIN` | `shakti.bojprtest.in` | Public hostname |
| `PUBLIC_URL` | `https://shakti.bojprtest.in` | CORS + frontend API URL |
| `NEXT_BASE_PATH` | *(empty)* | Set `/shakti` for path-based deploy |

## 5. Instagram sessions in git

`storage/sessions/` is no longer gitignored. On push to `main`:

- **deploy-hostinger.yml** — full deploy including sessions
- **sync-instagram-sessions.yml** — fast session-only sync to VPS + EC2

Keep the repo **private**. Rotate Instagram if cookies leak.

## 6. Hostinger API + Cursor MCP

Do **not** commit API tokens. Set `HOSTINGER_API_TOKEN` in your OS environment or Cursor MCP user settings.

Copy `.cursor/mcp.hostinger.example.json` into Cursor Settings → MCP, and set the token there.

**Rotate your token** if it was shared in chat.

## 7. SSL (HTTPS)

After DNS works:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d shakti.bojprtest.in
```

Update `PUBLIC_URL` / CORS to `https://`.

## 8. Manual deploy test

On the VPS:

```bash
cd ~/e-Patrolling
bash scripts/deploy-hostinger-remote.sh
```

Health: `curl http://127.0.0.1:5000/health`  
Public: `https://shakti.bojprtest.in/admin`

## Workflows

| File | Trigger |
|------|---------|
| `.github/workflows/deploy-hostinger.yml` | Push to `main` |
| `.github/workflows/sync-instagram-sessions.yml` | Changes under `storage/sessions/` |
| `.github/workflows/deploy.yml` | Existing EC2 deploy (unchanged) |
