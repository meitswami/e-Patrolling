# PATROL — System Architecture

> Predictive Abuse Tracking & Regional Observation Layer  
> See [BRAIN.md](../BRAIN.md) for the full module map and [task_tracker.md](./task_tracker.md) for build status.

---

## High-Level Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    PATROL Platform                          │
│                                                             │
│  ┌──────────┐    ┌──────────┐    ┌──────────────────────┐  │
│  │ Crawlers │───▶│  Queue   │───▶│    AI Pipeline       │  │
│  │Playwright│    │  Redis   │    │LanguageDetect→Classify│  │
│  └──────────┘    └──────────┘    │ →Severity→RiskScore  │  │
│                                  └──────────┬───────────┘  │
│                                             │              │
│  ┌──────────────┐              ┌────────────▼───────────┐  │
│  │   Evidence   │◀─────────────│      PostgreSQL         │  │
│  │  Engine      │              │   (Source of Truth)     │  │
│  │ Screenshots  │              └────────────┬───────────┘  │
│  └──────────────┘                           │              │
│                                             │              │
│  ┌──────────────────────────────────────────▼───────────┐  │
│  │              FastAPI Backend (backend/)                 │  │
│  │         REST API + WebSocket Server                   │  │
│  └──────────────────────────────────────────┬───────────┘  │
│                                             │              │
│  ┌──────────────────────────────────────────▼───────────┐  │
│  │           Next.js Intelligence Dashboard (frontend/)  │  │
│  │    Live Feed · Maps · Charts · Evidence Gallery       │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Repository Layout

| Path | Role |
|------|------|
| `backend/main.py` | FastAPI entry point |
| `backend/configs/` | Settings, logging |
| `backend/database/` | `schema.sql`, migrations |
| `backend/crawlers/` | Platform crawlers (Playwright) |
| `backend/api/` | HTTP routes and middleware |
| `frontend/` | Next.js dashboard (types, constants, components) |
| `ai/` | Prompts, memory, workflows (orchestration assets) |
| `docs/` | Design and pipeline documentation |
| `scripts/` | Setup, seed, and utility scripts |
| `docker-compose.yml` | Local multi-service stack |

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Backend** | Python 3.11 + FastAPI | Async REST API + WebSockets |
| **Frontend** | Next.js 14 + TypeScript | Intelligence dashboard |
| **Database** | PostgreSQL 15 | Primary data store |
| **Cache/Queue** | Redis 7 | Task queue + API cache |
| **Crawling** | Playwright (async) | Browser automation |
| **AI** | HuggingFace (IndicBERT, MiniLM, toxic-bert) | Multilingual abuse detection |
| **Maps** | Leaflet + OpenStreetMap | Regional threat maps |
| **DevOps** | Docker Compose | Local orchestration |

---

## Design Decisions

1. **PostgreSQL as source of truth** — `backend/database/schema.sql` defines the canonical schema; production changes go through `migrations/`.
2. **Async-first backend** — asyncpg, asyncio crawlers, and async FastAPI handlers end-to-end.
3. **Queue-decoupled AI** — crawlers enqueue work; AI workers consume from Redis so API latency stays independent of model inference.
4. **Evidence chain-of-custody** — screenshots and metadata stored under `storage/` with hashed integrity checks (see [database_design.md](./database_design.md)).
5. **Config via environment** — no secrets in code; see root `.env.example` and `backend/configs/settings.py`.

---

## Related Docs

- [ai_pipeline.md](./ai_pipeline.md) — NLP pipeline and model flow
- [database_design.md](./database_design.md) — ER model and tables
- [task_tracker.md](./task_tracker.md) — Phase and task status
