# 📋 PATROL — TASK TRACKER
> **This file is the operational heartbeat. Update after EVERY completed task.**
> Format: ✅ DONE (date) | 🔄 IN PROGRESS | ⬜ PENDING | ❌ BLOCKED (reason)

---

## 🔍 RECOVERY AUDIT (2026-05-17)

Repository was partially generated then manually recovered. **Tracker previously overstated completion.**

| Area | Claimed | Actual on disk |
|------|---------|----------------|
| Phase 1 | 100% | ~35% — dirs exist via `.gitkeep`, most files missing |
| `schema.sql` | Pending | ✅ Complete (~500 lines) |
| `base_crawler.py` | Skeleton | ✅ Substantial abstract base |
| `main.py` | Done | ⚠️ Imports ~15 modules that do not exist — **won't boot** |
| Frontend | Next.js app | ⚠️ Types + constants only (`index.ts`, `constants.ts`) |
| Docs (11 files) | All done | 4 files: architecture, ai_pipeline, database_design, task_tracker |
| Docker/scripts | Done | `docker-compose.yml` only; no `docker/`, no `scripts/*.py` |
| `.env.example` | Done | Empty file |

**Next implementation order:** logging → DB connection/models → auth → queue stubs → bootable API → seed script → Dockerfiles.

---

## 📌 CONTINUATION PLAN (incremental)

### Sprint R1 — Bootable backend ✅ (2026-05-17)
1. ✅ `utils/logger.py` + `configs/logging_config.py`
2. ✅ `database/connection.py` + `database/models.py`
3. ✅ `queue/producer.py`, `websocket/manager.py`, `ai/model_loader.py` (stubs)
4. ✅ `main.py` — routers deferred; `from main import app` succeeds
5. ✅ `.env.example` populated

### Sprint R2 — Auth + Supabase ✅ (2026-05-17)
5. ✅ JWT auth + seed + Supabase MCP migrations
6. ✅ Frontend shell (login, dashboard, `.env.local`)

### Sprint R3 — Core API ✅ (2026-05-17)
7. ✅ Targets CRUD + evidence list + analytics dashboard API
8. ✅ Dashboard + evidence pages wired to live API

### Sprint R4 — Demo data + Targets UI 🔄 (2026-05-17) ← YOU ARE HERE
9. ✅ `scripts/seed_demo.py` + `/targets` page (list + add)
10. ⬜ Instagram crawler MVP
11. ⬜ Queue workers (when Redis enabled)

### Sprint R4+ — Crawler → AI → evidence (per original phases 3–5)

---

## 🎯 MVP PROGRESS OVERVIEW

```
Phase 1: Architecture & Scaffolding  ███████░░░░░░░░░░░░░  35% 🔄
Phase 2: Database & Auth             ████████████░░░░░░░░  60% 🔄
Phase 3: Platform Crawlers           █░░░░░░░░░░░░░░░░░░░   5% 🔄 (base only)
Phase 4: AI Engine                   ░░░░░░░░░░░░░░░░░░░░   0% ⬜
Phase 5: Evidence Engine             ░░░░░░░░░░░░░░░░░░░░   0% ⬜
Phase 6: Dashboard & WebSockets      ████░░░░░░░░░░░░░░░░  20% 🔄 (shell + live stats)
Phase 7: Reports & Exports           ░░░░░░░░░░░░░░░░░░░░   0% ⬜
Phase 8: Testing & Polish            ░░░░░░░░░░░░░░░░░░░░   0% ⬜

OVERALL MVP: █████░░░░░░░░░░░░░░░  ~12%
```

---

## PHASE 1: Architecture & Scaffolding 🔄 PARTIAL

### 1.1 Project Foundation
- ✅ BRAIN.md (2026-05-17 recovery audit)
- ✅ task_tracker.md (this file)
- 🔄 Directory structure (placeholder dirs + `.gitkeep` only)
- ✅ README.md
- ✅ .env.example (2026-05-17)
- ✅ docker-compose.yml (references missing Dockerfiles/workers)
- ⬜ backend/Dockerfile
- ⬜ frontend/Dockerfile

### 1.2 Backend Skeleton
- ✅ backend/main.py (imports OK; routes deferred until Sprint R2+)
- ✅ requirements.txt (repo root; not `backend/requirements.txt`)
- ✅ backend/configs/settings.py
- ✅ backend/configs/logging_config.py (2026-05-17)
- ✅ backend/utils/logger.py (2026-05-17)
- ✅ backend/crawlers/base_crawler.py

### 1.3 Frontend Skeleton
- ✅ frontend/package.json, next.config, tailwind, tsconfig (2026-05-17)
- ✅ src/app/login, dashboard, layout, globals.css
- ✅ src/lib/api.ts, auth.ts — wired to FastAPI
- ✅ src/components/layout (Sidebar, Header, AppShell)
- ✅ Types moved to frontend/src/types/

### 1.4 Documentation
- ✅ docs/architecture.md
- ✅ docs/ai_pipeline.md
- ✅ docs/database_design.md
- ⬜ docs/system_design.md, crawler_design.md, deployment_guide.md, api_reference.md, legal_considerations.md, roadmap.md, dashboard_architecture.md

### 1.5 DevOps
- ✅ docker-compose.yml
- ⬜ docker/*, scripts/setup.sh
- ✅ scripts/seed_db.py, scripts/seed_demo.py (2026-05-17)

---

## PHASE 2: Database & Authentication 🔄 IN PROGRESS

### 2.1 Database Schema
- ✅ backend/database/schema.sql (2026-05-17 — complete, 11 tables + views)
- ✅ backend/database/models.py (2026-05-17)
- ✅ backend/database/connection.py (2026-05-17)
- ⬜ backend/database/migrations/001_initial_schema.sql (optional; schema applied via docker init)

### 2.2 Authentication
- ✅ backend/auth/jwt_handler.py (2026-05-17)
- ✅ backend/auth/passwords.py (bcrypt)
- ✅ backend/auth/rbac.py
- ✅ backend/auth/middleware.py
- ✅ backend/api/routes/auth.py — POST /login, /refresh, /logout, GET /me
- ✅ backend/api/schemas/auth.py
- ✅ scripts/seed_db.py
- ✅ Supabase: `.cursor/mcp.json`, `supabase_migration.sql`, `apply_supabase_schema.py`

### 2.3 Queue Infrastructure
- ⬜ backend/queue/producer.py (Redis queue producer)
- ⬜ backend/queue/consumer.py (async worker loop)
- ⬜ backend/queue/tasks.py (task type definitions + handlers)
- ⬜ backend/queue/scheduler.py (APScheduler periodic crawl jobs)

### 2.4 Core API Schemas
- ✅ backend/api/schemas/common.py (2026-05-17)
- ✅ backend/api/schemas/target.py
- ✅ backend/api/schemas/evidence.py
- ✅ backend/api/schemas/analytics.py

### 2.5 Core API Routes
- ✅ backend/api/routes/targets.py — list, create, get, patch, delete
- ✅ backend/api/routes/evidence.py — list, get (filters)
- ✅ backend/api/routes/analytics.py — GET /dashboard
- ✅ Frontend dashboard + evidence pages use live API

---

## PHASE 3: Platform Crawlers ⬜ PENDING

### 3.1 Base Infrastructure
- 🔄 backend/crawlers/base_crawler.py (abstract base + Playwright session + retry; queue hooks pending)

### 3.2 Instagram Crawler
- ⬜ backend/crawlers/instagram/session_manager.py
  - Cookie-based session persistence
  - Session validity checker
  - Login flow (headless Playwright)
- ⬜ backend/crawlers/instagram/adapter.py
  - Main orchestrator, inherits BaseCrawler
  - Public post monitoring
  - Comment enumeration
- ⬜ backend/crawlers/instagram/parser.py
  - Extract: comment text, username, timestamp, profile URL, avatar
  - Handle pagination, load-more
- ⬜ backend/crawlers/instagram/comment_monitor.py
  - Polling loop (configurable interval)
  - New comment detection (diff from last crawl)
  - Push to queue on new content
- ⬜ backend/crawlers/instagram/screenshot.py
  - Playwright screenshot of comment in context
  - Crop to comment element
  - Save to storage/evidence/instagram/YYYY/MM/DD/

### 3.3 Twitter/X Crawler
- ⬜ backend/crawlers/twitter/session_manager.py
- ⬜ backend/crawlers/twitter/adapter.py (use Twitter API v2 free tier OR scraping)
- ⬜ backend/crawlers/twitter/parser.py
- ⬜ backend/crawlers/twitter/comment_monitor.py (reply monitoring)
- ⬜ backend/crawlers/twitter/screenshot.py

### 3.4 Facebook Crawler
- ⬜ backend/crawlers/facebook/session_manager.py
- ⬜ backend/crawlers/facebook/adapter.py
- ⬜ backend/crawlers/facebook/parser.py
- ⬜ backend/crawlers/facebook/comment_monitor.py
- ⬜ backend/crawlers/facebook/screenshot.py

### 3.5 Threads Crawler
- ⬜ backend/crawlers/threads/adapter.py (unofficial API approach)
- ⬜ backend/crawlers/threads/parser.py
- ⬜ backend/crawlers/threads/comment_monitor.py
- ⬜ backend/crawlers/threads/screenshot.py

### 3.6 Telegram Crawler
- ⬜ backend/crawlers/telegram/adapter.py (Telethon library)
- ⬜ backend/crawlers/telegram/parser.py
- ⬜ backend/crawlers/telegram/comment_monitor.py (channel message monitoring)
- ⬜ backend/crawlers/telegram/screenshot.py

### 3.7 WhatsApp Crawler
- ⬜ backend/crawlers/whatsapp/adapter.py (public channels only - WhatsApp Web)
- ⬜ backend/crawlers/whatsapp/parser.py
- ⬜ backend/crawlers/whatsapp/comment_monitor.py

### 3.8 Crawler Management API
- ⬜ backend/api/routes/crawlers.py
  - POST /crawlers/start/{platform}/{target_id}
  - POST /crawlers/stop/{platform}/{target_id}
  - GET /crawlers/status
  - GET /crawlers/logs

---

## PHASE 4: AI Abuse Detection Engine ⬜ PENDING

### 4.1 Model Infrastructure
- ⬜ backend/ai/model_loader.py
  - Lazy loading (load on first use, not import)
  - Model registry (name → model instance)
  - CPU/GPU auto-detection
  - Cache to ai_models/cache/

### 4.2 Language Detection
- ⬜ backend/ai/language_detector.py
  - Use `langdetect` + custom Hinglish heuristics
  - Returns: {"language": "hindi|english|hinglish", "confidence": 0.95}
  - Hinglish: Hindi words in Latin script (e.g., "teri maa ki")
  - Handle mixed scripts (Devanagari + Latin)

### 4.3 Abuse Classifier
- ⬜ backend/ai/classifier.py
  - Primary: `ai4bharat/IndicBERT` for Hindi/Hinglish
  - Secondary: `unitary/toxic-bert` for English
  - Output: {"is_abusive": bool, "confidence": 0.0-1.0, "categories": [...]}
  - Categories: abuse, sexual_harassment, rape_threat, stalking, hate_speech, threat, bullying

### 4.4 Keyword Engine
- ⬜ backend/ai/keyword_engine.py
  - Loads ai_models/configs/abuse_lexicon.json
  - Fast regex-based matching (pre-model filter)
  - Hindi/Hinglish/English keyword lists
  - Returns immediate HIGH flag for explicit content
- ⬜ ai_models/configs/abuse_lexicon.json (comprehensive word lists)

### 4.5 Severity Engine
- ⬜ backend/ai/severity_engine.py
  - Input: classifier confidence + keyword matches + context
  - Output: {"level": "LOW|MEDIUM|HIGH|CRITICAL", "score": 0-100}
  - CRITICAL: rape threats, death threats, doxxing
  - HIGH: sexual harassment, stalking patterns
  - MEDIUM: hate speech, targeted bullying
  - LOW: mild abuse, borderline content

### 4.6 Risk Scoring
- ⬜ backend/ai/risk_scoring.py
  - Composite score 0-100
  - Factors: severity + repeat_offender_bonus + verified_account + follower_count
  - Weighted formula documented in code

### 4.7 Entity Detection
- ⬜ backend/ai/entity_detector.py
  - NER using `ai4bharat/IndicNER` or spaCy
  - Extract: person names, locations, phone numbers, addresses
  - Flag personal information disclosure (doxxing detection)

### 4.8 AI Pipeline Integration
- ⬜ backend/ai/pipeline.py
  - Orchestrates: detect_language → keyword_check → classify → severity → risk → entities
  - Single entry point: `analyze_text(text: str, context: dict) → AnalysisResult`
  - Async-compatible

### 4.9 AI Model Download Script
- ⬜ scripts/download_models.py
  - Downloads all required HuggingFace models
  - Saves to ai_models/cache/
  - Progress bars, error handling

---

## PHASE 5: Evidence Engine ⬜ PENDING

### 5.1 Screenshot Engine
- ⬜ backend/evidence/screenshot_engine.py
  - Playwright browser pool (reuse contexts)
  - Capture comment in social media context
  - Element-level screenshot (crop to comment)
  - Full page fallback
  - Watermark with timestamp + evidence ID
  - Save: storage/evidence/{platform}/{YYYY}/{MM}/{DD}/{evidence_id}.png

### 5.2 Evidence Collector
- ⬜ backend/evidence/collector.py
  - Triggered after AI analysis flags content
  - Orchestrates: screenshot → metadata → DB insert → WebSocket broadcast
  - Evidence package: comment + screenshot + AI result + accused profile + timestamp

### 5.3 Metadata Builder
- ⬜ backend/evidence/metadata_builder.py
  - Builds structured evidence metadata
  - Generates unique evidence ID (UUID)
  - Creates chain-of-custody info

### 5.4 Storage Manager
- ⬜ backend/evidence/storage_manager.py
  - File path management
  - Directory auto-creation
  - File integrity checks (SHA256 hash)
  - Cleanup old temporary files

### 5.5 Evidence API
- 🔄 backend/api/routes/evidence.py
  - ✅ GET /evidence (paginated, filterable)
  - ✅ GET /evidence/{id}
  - ⬜ GET /evidence/{id}/screenshot
  - ⬜ DELETE /evidence/{id} (admin only)
  - ⬜ POST /evidence/{id}/escalate

---

## PHASE 6: Dashboard & WebSockets ⬜ PENDING

### 6.1 WebSocket Backend
- ⬜ backend/websocket/manager.py
  - ConnectionManager class
  - Connect/disconnect handling
  - Room-based broadcasting (by region, platform)
- ⬜ backend/websocket/events.py
  - Typed event classes (NewEvidenceEvent, CriticalAlertEvent, etc.)
  - JSON serialization
- ⬜ backend/websocket/broadcaster.py
  - Async broadcast to all connected clients
  - Filter by subscription (region/platform filters)
- ⬜ backend/api/routes/ws.py
  - WebSocket endpoint: /ws/dashboard

### 6.2 Analytics Backend
- 🔄 backend/analytics/aggregator.py (logic in routes/analytics.py for now)
  - Dashboard stats computation
  - Cached (Redis, 30s TTL)
  - Returns: total_incidents, active_targets, by_platform, by_severity, by_region
- ⬜ backend/analytics/trend_engine.py
  - Trending abuse keywords (last 24h)
  - Incident rate trends (hourly)
- ⬜ backend/api/routes/analytics.py
  - GET /analytics/dashboard
  - GET /analytics/trends
  - GET /analytics/regions
  - GET /analytics/platforms

### 6.3 Region Intelligence Backend
- ⬜ backend/region_engine/detector.py
- ⬜ backend/region_engine/scorer.py
- ⬜ backend/region_engine/geo_mapper.py
- ⬜ backend/region_engine/indian_regions.py (city→state→lat/lng mapping)
- ⬜ backend/api/routes/regions.py

### 6.4 Frontend Dashboard
- ⬜ frontend/src/app/layout.tsx (sidebar navigation)
- ⬜ frontend/src/app/dashboard/page.tsx
  - Stats cards (incidents, targets, offenders, evidence)
  - Live feed (WebSocket)
  - Platform breakdown chart
  - Severity distribution
  - Recent critical alerts

### 6.5 Frontend Components
- ⬜ frontend/src/components/ui/ (full design system)
  - Button, Card, Badge, Table, Input, Modal, Toast, Skeleton, SeverityBadge
- ⬜ frontend/src/components/feed/LiveFeed.tsx (WebSocket connected)
- ⬜ frontend/src/components/feed/EvidenceCard.tsx
- ⬜ frontend/src/components/charts/ThreatTimeline.tsx
- ⬜ frontend/src/components/charts/PlatformPieChart.tsx
- ⬜ frontend/src/components/maps/ThreatMap.tsx (Leaflet + OpenStreetMap)

### 6.6 Frontend Pages
- ⬜ frontend/src/app/monitoring/page.tsx
- ⬜ frontend/src/app/evidence/page.tsx
- ⬜ frontend/src/app/regions/page.tsx
- ⬜ frontend/src/app/offenders/page.tsx
- ⬜ frontend/src/app/analytics/page.tsx
- ⬜ frontend/src/app/settings/page.tsx

### 6.7 Frontend State & Hooks
- ⬜ frontend/src/hooks/useWebSocket.ts
- ⬜ frontend/src/hooks/useDashboard.ts
- ⬜ frontend/src/store/dashboardStore.ts (Zustand)
- ⬜ frontend/src/store/filterStore.ts
- ⬜ frontend/src/lib/api.ts (Axios instance)
- ⬜ frontend/src/lib/websocket.ts (WS client)

---

## PHASE 7: Reports & Exports ⬜ PENDING

### 7.1 Report Generation
- ⬜ backend/exports/excel_exporter.py
  - openpyxl-based Excel report
  - Sheets: Summary, Evidence List, Accused Profiles, Timeline
  - Embedded screenshots (as thumbnails)
  - Police-ready format
- ⬜ backend/exports/pdf_exporter.py
  - reportlab PDF
  - Official cyber intelligence report format
  - Evidence IDs, timestamps, chain of custody
  - Screenshots embedded
- ⬜ backend/exports/json_exporter.py
  - Machine-readable evidence dump
  - Full metadata included

### 7.2 Report API
- ⬜ backend/api/routes/reports.py
  - POST /reports/generate (async, returns job_id)
  - GET /reports/status/{job_id}
  - GET /reports/download/{job_id}
  - GET /reports/list

### 7.3 Frontend Reports Page
- ⬜ frontend/src/app/reports/page.tsx
  - Report builder UI (date range, filters, format)
  - Report list with download links
  - Preview thumbnails

---

## PHASE 8: Testing & Polish ⬜ PENDING

### 8.1 Unit Tests
- ⬜ tests/unit/test_ai_classifier.py
- ⬜ tests/unit/test_language_detector.py
- ⬜ tests/unit/test_severity_engine.py
- ⬜ tests/unit/test_risk_scoring.py
- ⬜ tests/unit/test_region_detector.py
- ⬜ tests/unit/test_keyword_engine.py

### 8.2 Integration Tests
- ⬜ tests/integration/test_auth_api.py
- ⬜ tests/integration/test_evidence_api.py
- ⬜ tests/integration/test_analytics_api.py
- ⬜ tests/integration/test_queue_pipeline.py

### 8.3 E2E Tests
- ⬜ tests/e2e/test_dashboard_flow.py
- ⬜ tests/e2e/test_evidence_capture.py

### 8.4 Demo Data
- ⬜ scripts/seed_db.py (realistic demo data for presentations)
  - 5 target accounts
  - 500+ sample comments (mix of languages + severity)
  - 50+ accused profiles
  - 20+ repeat offenders
  - Pre-computed analytics

### 8.5 Performance & Polish
- ⬜ Database query optimization (EXPLAIN ANALYZE all major queries)
- ⬜ Frontend Lighthouse score >85
- ⬜ API response times < 200ms (p95)
- ⬜ WebSocket reconnection logic
- ⬜ Error boundaries on all pages
- ⬜ Loading skeletons everywhere

---

## 📝 SPRINT LOG

### Sprint 1 (Phase 1) — COMPLETE ✅
**Goal:** Project foundation, all scaffolding, documentation
**Completed:**
- All directory structure
- BRAIN.md + task_tracker.md
- README.md
- docker-compose.yml
- Backend main.py + settings
- Frontend skeleton
- All documentation files

### Sprint R1 (Recovery) — COMPLETE ✅ (2026-05-17)
**Goal:** Bootable FastAPI + DB layer
**Done:** logger, connection, models, queue/redis stub, WS stub, main imports

### Sprint R2 (Phase 2) — CURRENT 🔄
**Goal:** Supabase + Auth
**Done:** Supabase settings/SSL, `.cursor/mcp.json`, auth module, `seed_db.py`, `apply_supabase_schema.py`
**Done (2026-05-17):** MCP migrations 001–005 applied; admin seeded (`admin@patrol.local`)

---

## 🚧 KNOWN BLOCKERS / DECISIONS PENDING

| # | Issue | Status | Decision |
|---|-------|--------|----------|
| 1 | Twitter API v2 free tier severely rate-limited | OPEN | Use scraping fallback with Playwright |
| 2 | WhatsApp has no public scraping API | OPEN | Limit to public WhatsApp Channels only |
| 3 | IndicBERT needs significant RAM (2GB+) | OPEN | Add CPU-only quantized version as fallback |
| 4 | Face recognition (future) needs GPU | DEFERRED | Phase 2+ roadmap only |

---

## 📊 FILE COUNT (actual, 2026-05-17)

| Area | On disk | Planned (BRAIN map) |
|------|---------|---------------------|
| Documentation | 4 + BRAIN + README | 11 |
| Backend Python | 5 modules | 50+ |
| Frontend TS | 2 files | 30+ |
| Tests / Docker / Scripts | 0 code | 20+ |

**Total: ~16 source files, ~130 planned**

---

## 🔖 QUICK REFERENCE COMMANDS

```bash
# Start everything
docker-compose up -d

# Backend only (dev)
cd backend && uvicorn main:app --reload --port 8000

# Frontend only (dev)
cd frontend && npm run dev

# Run DB migrations
cd backend && alembic upgrade head

# Seed demo data
python scripts/seed_db.py

# Download AI models
python scripts/download_models.py

# Run tests
pytest tests/ -v

# Check all services health
./scripts/health_check.sh
```