# 🧠 PATROL — PROJECT BRAIN
> **READ THIS FIRST. ALWAYS. BEFORE TOUCHING ANY FILE.**
> This is the single source of truth for any AI agent (Claude, Codex, Cursor, GPT-4, Gemini) continuing this project.
> Last Updated: 2026-05-17 — Recovery audit (partial scaffold; see task_tracker)

---

## ⚡ TL;DR FOR AI AGENTS

**What is this?** PATROL = Predictive Abuse Tracking & Regional Observation Layer
An enterprise-grade, AI-powered cyber intelligence platform that monitors social media for abuse/harassment targeting women influencers — for use by Cyber Cells, Law Enforcement, and Women Safety Organizations.

**Stack:** FastAPI (Python) + Next.js (TypeScript) + **Supabase (PostgreSQL)** + Redis + Playwright + HuggingFace NLP

**Current Status:** MVP ~60% — 4-platform patrol, evidence escalate/delete, CI, abuse lexicon JSON, admin settings (2026-05-17)

**Where to continue:** Read `docs/task_tracker.md` → **Recovery Audit** → first `⬜ PENDING` task.

**Important:** Many paths in the module map below are *planned*, not on disk. Do not assume files exist — check the repo first.

**Critical rule:** After completing any task, update `docs/task_tracker.md` and `BRAIN.md` status section.

---

## 📁 PROJECT MAP (File & Module Graph)

```
PATROL/
├── BRAIN.md                    ← YOU ARE HERE (read every session)
├── README.md                   ← Public-facing overview
├── .env.example                ← All env vars documented
├── docker-compose.yml          ← Orchestrates all services
│
├── backend/                    ← Python FastAPI application
│   ├── main.py                 ← App entry point, mounts all routers
│   ├── requirements.txt        ← Python dependencies
│   ├── Dockerfile
│   │
│   ├── configs/                ← All configuration
│   │   ├── settings.py         ← Pydantic Settings (env-based config)
│   │   └── logging_config.py   ← Structured logging setup
│   │
│   ├── database/               ← DB layer
│   │   ├── connection.py       ← AsyncPG connection pool
│   │   ├── models.py           ← SQLAlchemy ORM models
│   │   ├── schema.sql          ← Raw SQL schema (source of truth)
│   │   └── migrations/         ← Alembic migration files
│   │
│   ├── auth/                   ← JWT Authentication + RBAC
│   │   ├── jwt_handler.py      ← Token create/verify
│   │   ├── rbac.py             ← Role-based access (admin/analyst/viewer)
│   │   └── middleware.py       ← Auth middleware
│   │
│   ├── api/                    ← HTTP API layer
│   │   ├── routes/
│   │   │   ├── targets.py      ← CRUD for monitored accounts
│   │   │   ├── evidence.py     ← Evidence retrieval + export
│   │   │   ├── analytics.py    ← Dashboard stats endpoints
│   │   │   ├── reports.py      ← Report generation triggers
│   │   │   ├── search.py       ← Full-text search
│   │   │   ├── regions.py      ← Region intelligence endpoints
│   │   │   ├── offenders.py    ← Repeat offender tracking
│   │   │   └── auth.py         ← Login/refresh/logout
│   │   ├── middleware/
│   │   │   ├── rate_limit.py   ← SlowAPI rate limiting
│   │   │   ├── audit_log.py    ← Every request logged
│   │   │   └── cors.py         ← CORS config
│   │   └── schemas/
│   │       ├── target.py       ← Pydantic request/response models
│   │       ├── evidence.py
│   │       ├── analytics.py
│   │       └── common.py       ← Shared schemas (pagination etc.)
│   │
│   ├── crawlers/               ← Platform data collectors (Playwright)
│   │   ├── base_crawler.py     ← Abstract base class all crawlers inherit
│   │   ├── instagram/
│   │   │   ├── adapter.py      ← Main crawler orchestrator
│   │   │   ├── parser.py       ← HTML/JSON → structured data
│   │   │   ├── screenshot.py   ← Playwright screenshot capture
│   │   │   ├── session_manager.py  ← Cookie/session persistence
│   │   │   └── comment_monitor.py  ← Live comment polling loop
│   │   ├── facebook/           ← Same structure as instagram/
│   │   ├── twitter/            ← Same structure
│   │   ├── threads/            ← Same structure
│   │   ├── telegram/           ← Same structure
│   │   └── whatsapp/           ← Public channels only
│   │
│   ├── ai/                     ← NLP / Abuse Detection Engine
│   │   ├── classifier.py       ← Main abuse classifier (IndicBERT + MiniLM)
│   │   ├── language_detector.py ← Detects Hindi/English/Hinglish
│   │   ├── severity_engine.py  ← Maps scores to LOW/MEDIUM/HIGH/CRITICAL
│   │   ├── risk_scoring.py     ← Composite risk score (0-100)
│   │   ├── entity_detector.py  ← NER: extracts names, locations, threats
│   │   ├── keyword_engine.py   ← Fast keyword matching (abuse lexicon)
│   │   └── model_loader.py     ← Lazy model loading + caching
│   │
│   ├── evidence/               ← Evidence collection & storage
│   │   ├── collector.py        ← Orchestrates evidence creation
│   │   ├── screenshot_engine.py ← Playwright screenshot logic
│   │   ├── storage_manager.py  ← File paths: storage/evidence/platform/Y/M/D/
│   │   └── metadata_builder.py ← Builds evidence metadata package
│   │
│   ├── region_engine/          ← Geographic intelligence
│   │   ├── detector.py         ← Infers region from bio/hashtags/lang
│   │   ├── scorer.py           ← Confidence scoring for region
│   │   ├── geo_mapper.py       ← Maps regions to lat/lng for maps
│   │   └── indian_regions.py   ← India-specific region data
│   │
│   ├── queue/                  ← Async task queue
│   │   ├── producer.py         ← Pushes jobs to Redis
│   │   ├── consumer.py         ← Workers that process jobs
│   │   ├── tasks.py            ← Task definitions
│   │   └── scheduler.py        ← Periodic crawl scheduling
│   │
│   ├── monitoring/             ← System health monitoring
│   │   ├── health_check.py     ← /health endpoint logic
│   │   └── metrics.py          ← Prometheus metrics
│   │
│   ├── analytics/              ← Data aggregation for dashboard
│   │   ├── aggregator.py       ← Computes dashboard stats
│   │   ├── trend_engine.py     ← Trending keywords/patterns
│   │   └── platform_stats.py   ← Per-platform analytics
│   │
│   ├── websocket/              ← Real-time push to frontend
│   │   ├── manager.py          ← Connection manager
│   │   ├── events.py           ← Event types (new_evidence, alert, etc.)
│   │   └── broadcaster.py      ← Broadcasts to connected clients
│   │
│   ├── exports/                ← Report generation
│   │   ├── excel_exporter.py   ← openpyxl Excel reports
│   │   ├── pdf_exporter.py     ← reportlab PDF reports
│   │   └── json_exporter.py    ← JSON evidence dumps
│   │
│   ├── services/               ← Business logic layer
│   │   ├── target_service.py   ← Target account management
│   │   ├── evidence_service.py ← Evidence CRUD + queries
│   │   ├── offender_service.py ← Repeat offender logic
│   │   └── alert_service.py    ← Alert creation + escalation
│   │
│   └── utils/
│       ├── text_cleaner.py     ← Unicode normalization, emoji handling
│       ├── url_validator.py    ← Platform URL validation
│       ├── rate_limiter.py     ← Request throttling utilities
│       └── logger.py           ← Structured logger factory
│
├── frontend/                   ← Next.js 14 App Router application
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   │
│   └── src/
│       ├── app/                ← Next.js App Router pages
│       │   ├── layout.tsx      ← Root layout (sidebar + navbar)
│       │   ├── page.tsx        ← Redirects to /dashboard
│       │   ├── dashboard/      ← Overview page (metrics + live feed)
│       │   ├── monitoring/     ← Live monitoring control center
│       │   ├── evidence/       ← Evidence gallery + details
│       │   ├── regions/        ← Region intelligence + map
│       │   ├── offenders/      ← Repeat offender profiles
│       │   ├── analytics/      ← Charts, heatmaps, trends
│       │   ├── reports/        ← Report generation + download
│       │   └── settings/       ← System config, targets, users
│       │
│       ├── components/
│       │   ├── ui/             ← Base design system components
│       │   │   ├── Button.tsx, Card.tsx, Badge.tsx, Table.tsx
│       │   │   ├── Input.tsx, Modal.tsx, Toast.tsx, Skeleton.tsx
│       │   │   └── SeverityBadge.tsx  ← LOW/MEDIUM/HIGH/CRITICAL visual
│       │   ├── charts/         ← Recharts wrappers
│       │   │   ├── ThreatTimeline.tsx
│       │   │   ├── PlatformPieChart.tsx
│       │   │   ├── RegionHeatmap.tsx
│       │   │   └── SeverityBarChart.tsx
│       │   ├── maps/           ← OpenStreetMap / Leaflet integration
│       │   │   ├── ThreatMap.tsx        ← Main map component
│       │   │   ├── IncidentMarker.tsx
│       │   │   └── RegionFilterPanel.tsx
│       │   ├── feed/           ← Live intelligence feed
│       │   │   ├── LiveFeed.tsx          ← WebSocket-connected feed
│       │   │   ├── EvidenceCard.tsx      ← Individual incident card
│       │   │   └── ThreatAlert.tsx       ← Critical alert popup
│       │   └── alerts/
│       │       ├── AlertBanner.tsx
│       │       └── SoundNotification.tsx
│       │
│       ├── lib/
│       │   ├── api.ts          ← Axios instance + interceptors
│       │   ├── websocket.ts    ← WebSocket client manager
│       │   ├── constants.ts    ← Platform names, severity colors, etc.
│       │   └── utils.ts        ← formatDate, truncate, etc.
│       │
│       ├── hooks/
│       │   ├── useWebSocket.ts ← Real-time connection hook
│       │   ├── useDashboard.ts ← Dashboard data fetching (SWR)
│       │   ├── useEvidence.ts  ← Evidence queries + filters
│       │   └── useRegion.ts    ← Region filter state
│       │
│       ├── types/
│       │   ├── evidence.ts     ← TypeScript interfaces matching DB models
│       │   ├── analytics.ts
│       │   ├── platform.ts
│       │   └── api.ts          ← API response types
│       │
│       └── store/
│           ├── dashboardStore.ts  ← Zustand store for dashboard state
│           ├── filterStore.ts     ← Global filters (region/platform/severity)
│           └── alertStore.ts      ← Active alerts state
│
├── docs/                       ← All documentation
│   ├── BRAIN.md                ← Symlink to root BRAIN.md
│   ├── task_tracker.md         ← PHASE/TASK status (UPDATE AFTER EACH TASK)
│   ├── architecture.md         ← System architecture + decisions
│   ├── system_design.md        ← High-level design + diagrams
│   ├── crawler_design.md       ← Crawler architecture details
│   ├── ai_pipeline.md          ← AI/NLP pipeline documentation
│   ├── dashboard_architecture.md ← Frontend architecture
│   ├── database_design.md      ← Schema + ER diagram
│   ├── deployment_guide.md     ← Docker + production deployment
│   ├── api_reference.md        ← All API endpoints documented
│   ├── legal_considerations.md ← Legal/ethical guidelines
│   └── roadmap.md              ← Future features roadmap
│
├── docker/
│   ├── backend.Dockerfile
│   ├── frontend.Dockerfile
│   └── nginx.conf              ← Reverse proxy config
│
├── scripts/
│   ├── setup.sh                ← One-command local setup
│   ├── seed_db.py              ← Seed demo data for dashboard
│   ├── download_models.py      ← Download HuggingFace models
│   └── health_check.sh         ← Verify all services running
│
├── tests/
│   ├── unit/                   ← Unit tests (pytest)
│   ├── integration/            ← API integration tests
│   └── e2e/                    ← Playwright E2E tests
│
└── storage/
    ├── evidence/               ← Screenshots: platform/year/month/day/
    ├── screenshots/            ← Raw crawler screenshots
    ├── exports/                ← Generated reports
    └── logs/                   ← Application logs
```

---

## 🗄️ DATABASE SCHEMA SUMMARY

Tables (PostgreSQL):
| Table | Purpose |
|-------|---------|
| `users` | Admin/analyst accounts with roles |
| `target_accounts` | Women influencers/public figures being monitored |
| `crawled_comments` | All collected comments/posts from platforms |
| `ai_results` | AI classification output per comment |
| `evidence_reports` | Packaged evidence (comment + screenshot + metadata) |
| `accused_profiles` | Unique offender profiles (aggregated) |
| `repeat_offenders` | Profiles with ≥3 abusive incidents |
| `monitoring_logs` | Crawler run logs, errors, stats |
| `region_scores` | Inferred region + confidence per accused profile |
| `dashboard_events` | Pre-aggregated stats for fast dashboard queries |

---

## 🤖 AI PIPELINE SUMMARY

```
Raw Text Input
    ↓
language_detector.py → detects: "hindi" | "english" | "hinglish"
    ↓
keyword_engine.py → fast blocklist check (instant flag for obvious abuse)
    ↓
classifier.py → IndicBERT (Hindi) or MiniLM (EN/Hinglish) inference
    ↓
severity_engine.py → maps confidence → LOW / MEDIUM / HIGH / CRITICAL
    ↓
risk_scoring.py → composite score (0-100) considering: repeat? verified? threat?
    ↓
entity_detector.py → extracts: person names, locations, threat keywords
    ↓
Evidence Package Created
```

**Models Used (all free/local):**
- `ai4bharat/IndicBERT` — Hindi abuse detection
- `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` — Multilingual
- `unitary/toxic-bert` — English toxicity (optional fallback)
- Custom keyword lexicon: `ai_models/configs/abuse_lexicon.json`

---

## 🔌 REAL-TIME ARCHITECTURE

```
[Playwright Crawler] → [Redis Queue] → [AI Worker] → [PostgreSQL]
                                                          ↓
[Next.js Dashboard] ← [WebSocket] ← [FastAPI WS Manager] ← [DB Change Listener]
```

WebSocket events:
- `new_evidence` — new abusive content detected
- `critical_alert` — CRITICAL severity incident
- `stats_update` — dashboard numbers updated
- `offender_flagged` — new repeat offender identified

---

## 🌐 API BASE STRUCTURE

Base URL: `http://localhost:8000/api/v1`

| Module | Prefix | Key Endpoints |
|--------|--------|---------------|
| Auth | `/auth` | POST /login, POST /refresh |
| Targets | `/targets` | CRUD monitored accounts |
| Evidence | `/evidence` | GET list, GET detail, GET screenshot |
| Analytics | `/analytics` | GET dashboard stats, trends |
| Reports | `/reports` | POST generate, GET download |
| Search | `/search` | GET with query params |
| Regions | `/regions` | GET intelligence, GET map data |
| Offenders | `/offenders` | GET profiles, GET timeline |

---

## 🎨 FRONTEND DESIGN SYSTEM

**Theme:** Dark cyber/SOC aesthetic (NOT purple gradient cliché)
- Background: `#0a0e1a` (deep navy-black)
- Surface: `#111827` (dark card)
- Accent: `#00ff88` (neon green — "active monitoring")
- Danger: `#ff3b30` (red — critical alerts)
- Warning: `#ff9f0a` (amber — high severity)
- Text: `#e2e8f0` (light gray)
- Font Display: `JetBrains Mono` (intelligence/terminal feel)
- Font Body: `Inter` (readable)

**Key UI Patterns:**
- Blinking red dot for CRITICAL alerts
- Platform color badges (Instagram pink, Twitter blue, etc.)
- Evidence cards with screenshot thumbnails
- Real-time counter animations
- Region filter as sticky sidebar panel

---

## 🔧 ENVIRONMENT VARIABLES (see .env.example)

```bash
# Supabase Database (Session pooler URI from dashboard)
DATABASE_URL=postgresql+asyncpg://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
SUPABASE_URL=https://[ref].supabase.co
SUPABASE_PROJECT_REF=[ref]
DATABASE_SSL=true

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=<generate with: openssl rand -hex 32>
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=480

# AI Models
MODEL_CACHE_DIR=./ai_models/cache
USE_GPU=false  # CPU-only for local MVP

# Storage
EVIDENCE_STORAGE_PATH=./storage/evidence
SCREENSHOTS_PATH=./storage/screenshots

# Map (OpenStreetMap - FREE, no key needed)
MAP_PROVIDER=openstreetmap

# Crawler
CRAWLER_HEADLESS=true
CRAWLER_TIMEOUT_MS=30000
MAX_CONCURRENT_BROWSERS=3
```

---

## 🚦 CURRENT BUILD STATUS

| Phase | Status | Notes |
|-------|--------|-------|
| 1 Architecture & Scaffolding | 🔄 ~35% | Docs + core files exist; most dirs are `.gitkeep` only |
| 2 Database & Auth | 🔄 ~50% | Supabase + schema; auth routes; seed script; MCP configured |
| 3–8 | ⬜ | See task_tracker |

**On disk today:** `BRAIN.md`, `README.md`, `requirements.txt`, `docker-compose.yml`, `.env.example` (empty), `backend/main.py`, `settings.py`, `base_crawler.py`, `schema.sql`, `frontend/index.ts` + `constants.ts`, 4 docs under `docs/`, `ai/prompts/master_prompt.md`.

**See `docs/task_tracker.md` for granular task status and continuation plan.**

---

## ⚠️ CRITICAL RULES FOR AI AGENTS

1. **Read BRAIN.md + task_tracker.md FIRST** — don't start coding blind
2. **Update task_tracker.md** after completing any task (mark ✅ DONE with date)
3. **Update BRAIN.md** if you add new files not in the module map
4. **Never hardcode secrets** — use `.env` + `configs/settings.py`
5. **All DB queries async** — use `asyncpg` / SQLAlchemy async session
6. **All crawlers inherit** `base_crawler.py` — don't duplicate logic
7. **AI models load lazily** — don't load at import time (memory!)
8. **Evidence always has screenshot** — no evidence record without screenshot attempt
9. **WebSocket events use typed EventEmitter pattern** — see `websocket/events.py`
10. **Frontend uses SWR for data fetching** — not raw useEffect fetches

---

## 🗄️ SUPABASE SETUP

1. Create a Supabase project (dev/staging — not production data).
2. Copy **Session pooler** URI into `.env` as `DATABASE_URL` (use `postgresql+asyncpg://` prefix).
3. Set `SUPABASE_PROJECT_REF` and `SUPABASE_URL` in `.env`.
4. **Cursor MCP:** `.cursor/mcp.json` points to `https://mcp.supabase.com/mcp?project_ref=...`
   - Restart Cursor → Settings → Tools & MCP → authorize Supabase (browser OAuth).
   - Set OS env `SUPABASE_PROJECT_REF` or edit MCP URL with your ref.
5. Apply schema: MCP `apply_migration` **or** `python scripts/apply_supabase_schema.py`
6. Seed admin: `python scripts/seed_db.py`

---

## 📞 CONTINUING THIS PROJECT (AI AGENT CHECKLIST)

When you start a new session on this project:

```
1. cat BRAIN.md                    → understand project
2. cat docs/task_tracker.md        → find what's pending
3. cat docs/[relevant_doc].md      → deep dive specific area
4. Look at existing files in module → understand patterns
5. Build the next pending task
6. Update task_tracker.md
7. Update BRAIN.md if new files added
```

**Never start coding without completing steps 1-4.**