# 📋 PATROL — TASK TRACKER
> **This file is the operational heartbeat. Update after EVERY completed task.**
> Format: ✅ DONE (date) | 🔄 IN PROGRESS | ⬜ PENDING | ❌ BLOCKED (reason)

---

## 🎯 MVP PROGRESS OVERVIEW

```
Phase 1: Architecture & Scaffolding  ████████████████████ 100% ✅
Phase 2: Database & Auth             ████░░░░░░░░░░░░░░░░  20% 🔄
Phase 3: Platform Crawlers           ░░░░░░░░░░░░░░░░░░░░   0% ⬜
Phase 4: AI Engine                   ░░░░░░░░░░░░░░░░░░░░   0% ⬜
Phase 5: Evidence Engine             ░░░░░░░░░░░░░░░░░░░░   0% ⬜
Phase 6: Dashboard & WebSockets      ░░░░░░░░░░░░░░░░░░░░   0% ⬜
Phase 7: Reports & Exports           ░░░░░░░░░░░░░░░░░░░░   0% ⬜
Phase 8: Testing & Polish            ░░░░░░░░░░░░░░░░░░░░   0% ⬜

OVERALL MVP: ████░░░░░░░░░░░░░░░░  ~12%
```

---

## PHASE 1: Architecture & Scaffolding ✅ COMPLETE

### 1.1 Project Foundation
- ✅ BRAIN.md created (AI agent guide)
- ✅ task_tracker.md created (this file)
- ✅ Directory structure created (all 50+ folders)
- ✅ README.md created
- ✅ .env.example created
- ✅ docker-compose.yml created
- ✅ backend/Dockerfile created
- ✅ frontend/Dockerfile created

### 1.2 Backend Skeleton
- ✅ backend/main.py (FastAPI app entry point)
- ✅ backend/requirements.txt
- ✅ backend/configs/settings.py (Pydantic settings)
- ✅ backend/configs/logging_config.py
- ✅ backend/utils/logger.py
- ✅ backend/crawlers/base_crawler.py (abstract base)

### 1.3 Frontend Skeleton
- ✅ frontend/package.json
- ✅ frontend/next.config.js
- ✅ frontend/tailwind.config.js
- ✅ frontend/tsconfig.json
- ✅ frontend/src/app/layout.tsx (root layout)
- ✅ frontend/src/lib/constants.ts
- ✅ frontend/src/types/ (all TypeScript interfaces)

### 1.4 Documentation
- ✅ docs/architecture.md
- ✅ docs/system_design.md
- ✅ docs/ai_pipeline.md
- ✅ docs/database_design.md
- ✅ docs/crawler_design.md
- ✅ docs/deployment_guide.md
- ✅ docs/api_reference.md
- ✅ docs/legal_considerations.md
- ✅ docs/roadmap.md
- ✅ docs/dashboard_architecture.md

### 1.5 DevOps
- ✅ docker-compose.yml (all services)
- ✅ docker/backend.Dockerfile
- ✅ docker/frontend.Dockerfile
- ✅ docker/nginx.conf
- ✅ scripts/setup.sh
- ✅ scripts/seed_db.py (demo data)

---

## PHASE 2: Database & Authentication 🔄 IN PROGRESS

### 2.1 Database Schema ⬜ NEXT TO BUILD
- ⬜ backend/database/schema.sql (complete PostgreSQL schema)
  - Tables: users, target_accounts, crawled_comments, ai_results,
    evidence_reports, accused_profiles, repeat_offenders,
    monitoring_logs, region_scores, dashboard_events
  - All indexes, foreign keys, constraints
- ⬜ backend/database/models.py (SQLAlchemy ORM models matching schema)
- ⬜ backend/database/connection.py (async connection pool)
- ⬜ backend/database/migrations/001_initial_schema.sql

### 2.2 Authentication
- ⬜ backend/auth/jwt_handler.py
  - create_access_token(), verify_token(), refresh_token()
  - HS256 algorithm, configurable expiry
- ⬜ backend/auth/rbac.py
  - Roles: ADMIN, ANALYST, VIEWER
  - Permission decorators
- ⬜ backend/auth/middleware.py
  - FastAPI dependency injection for protected routes
- ⬜ backend/api/routes/auth.py
  - POST /login, POST /refresh, POST /logout, GET /me
- ⬜ backend/api/schemas/auth.py (LoginRequest, TokenResponse, UserResponse)

### 2.3 Queue Infrastructure
- ⬜ backend/queue/producer.py (Redis queue producer)
- ⬜ backend/queue/consumer.py (async worker loop)
- ⬜ backend/queue/tasks.py (task type definitions + handlers)
- ⬜ backend/queue/scheduler.py (APScheduler periodic crawl jobs)

### 2.4 Core API Schemas
- ⬜ backend/api/schemas/target.py
- ⬜ backend/api/schemas/evidence.py
- ⬜ backend/api/schemas/analytics.py
- ⬜ backend/api/schemas/common.py (PaginatedResponse, FilterParams)

---

## PHASE 3: Platform Crawlers ⬜ PENDING

### 3.1 Base Infrastructure
- ⬜ backend/crawlers/base_crawler.py (expand with full interface)
  - Abstract methods: start(), stop(), crawl_comments(), take_screenshot()
  - Built-in retry logic (exponential backoff)
  - Rate limiting per platform
  - Queue integration hooks
  - Session management base

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
- ⬜ backend/api/routes/evidence.py
  - GET /evidence (paginated, filterable)
  - GET /evidence/{id}
  - GET /evidence/{id}/screenshot
  - DELETE /evidence/{id} (admin only)
  - POST /evidence/{id}/escalate

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
- ⬜ backend/analytics/aggregator.py
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

### Sprint 2 (Phase 2) — CURRENT 🔄
**Goal:** Working database + auth + queue
**Target:** `backend/database/schema.sql` → `models.py` → `connection.py` → auth module → queue

---

## 🚧 KNOWN BLOCKERS / DECISIONS PENDING

| # | Issue | Status | Decision |
|---|-------|--------|----------|
| 1 | Twitter API v2 free tier severely rate-limited | OPEN | Use scraping fallback with Playwright |
| 2 | WhatsApp has no public scraping API | OPEN | Limit to public WhatsApp Channels only |
| 3 | IndicBERT needs significant RAM (2GB+) | OPEN | Add CPU-only quantized version as fallback |
| 4 | Face recognition (future) needs GPU | DEFERRED | Phase 2+ roadmap only |

---

## 📊 FILE COUNT

| Area | Files Created | Files Pending |
|------|--------------|---------------|
| Documentation | 11 | 0 |
| Backend Core | 8 | 45+ |
| Backend Crawlers | 1 (base) | 25 |
| AI Engine | 0 | 8 |
| Frontend | 6 | 30+ |
| Tests | 0 | 15 |
| DevOps | 5 | 2 |

**Total: ~31 created, ~125 pending**

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