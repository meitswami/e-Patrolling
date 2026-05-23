# 🛡️ PATROL
## Predictive Abuse Tracking & Regional Observation Layer

> **AI-Powered Regional Social Media Harassment Intelligence System**
> Built for Cyber Cells · Law Enforcement · Women Safety Organizations · OSINT Teams

[![Phase](https://img.shields.io/badge/Phase-1%20Complete-green)]()
[![Stack](https://img.shields.io/badge/Stack-FastAPI%20%2B%20Next.js%20%2B%20PostgreSQL-blue)]()
[![AI](https://img.shields.io/badge/AI-IndicBERT%20%2B%20MiniLM-purple)]()
[![License](https://img.shields.io/badge/License-Restricted-red)]()

---

## 🎯 What is PATROL?

PATROL is an enterprise-grade cyber intelligence platform that monitors social media platforms for harassment, abuse, and targeted threats against women influencers and public figures.

It combines **real-time social media crawling**, **multilingual AI abuse detection** (Hindi + Hinglish + English), and a **SOC-grade intelligence dashboard** to help organizations detect, document, and report online harassment.

### Designed For:
- 🚔 **Cyber Cells & Police Departments** — Evidence collection + FIR-ready reports
- 👮 **Law Enforcement Agencies** — Regional threat intelligence
- 🏛️ **Women Safety Organizations** — Monitoring + escalation workflows
- 🔍 **OSINT Teams** — Deep social media investigation
- 🛡️ **Threat Intelligence Operations** — Pattern analysis + repeat offender tracking

---

## ✨ Key Features

### 🤖 AI-Powered Detection
- **Multilingual NLP**: Hindi, English, Hinglish (Latin-script Hindi)
- **Keyword lexicon + optional ML**: Fast pattern matching by default (`USE_ML_CLASSIFIER=false`); IndicBERT / MiniLM when enabled in Settings
- **Abuse categories** (stored per comment & evidence):
  - `sexual_harassment` · `rape_threat` · `stalking` · `hate_speech` · `threat` · `bullying`
  - Combined labels supported (e.g. `hate_speech + bullying` for *fake bc*)
- **Hinglish / romanized slur detection**: `bc`, `bsdk`, `mc`, `fake bc`, sexual solicitation (`S*X` → normalized), and more via `ai_models/configs/abuse_lexicon.json`
- **Investigator explanations**: Auto-generated “what this means” panels — term meaning (e.g. *bc* = behenchod) and **what the offender implies**, driven by `ai_models/configs/abuse_term_glossary.json`
- **4-level severity**: LOW → MEDIUM → HIGH → CRITICAL
- **Confidence scoring**: 0–100 composite risk score
- **Reclassify crawl window**: Re-run classifier on comments from a crawl log after lexicon updates (`POST /api/v1/crawlers/logs/{log_id}/reclassify`)

### 📡 Multi-Platform Monitoring
| Platform | Comments | Replies | DM Channels | Public Groups |
|----------|----------|---------|-------------|---------------|
| Instagram | ✅ | ✅ | ❌ | ❌ |
| Twitter/X | ✅ | ✅ | ❌ | ❌ |
| Facebook | ✅ | ✅ | ❌ | ✅ |
| Threads | ✅ | ✅ | ❌ | ❌ |
| Telegram | ✅ | ✅ | ❌ | ✅ |
| WhatsApp | ❌ | ❌ | ✅ | ✅ |

### 🗺️ Regional Intelligence
- Geographic inference from bio/hashtags/language
- India-specific region mapping (city → district → state)
- Confidence-scored region attribution
- Leaflet/OpenStreetMap threat heatmaps
- Real-time region filtering

### 📸 Evidence Engine
- Automated screenshot capture (Playwright)
- Evidence packages with chain-of-custody metadata
- SHA-256 file integrity verification
- Organized storage: `platform/year/month/day/`
- Screenshot watermarking with timestamp + evidence ID
- **Evidence Feed** with category badges, bold abusive comment text, lexicon-highlight styling, and contextual explanation blocks
- **Backfill abuse categories** (one-click): Updates `abuse_categories`, lexicon flags, and explanations on all stored evidence (`POST /api/v1/evidence/backfill-categories`, Analyst/Admin)

### 📡 Instagram & Historical Crawling (Live Mode)
- **Live mode only** — no demo/synthetic crawl path in production UI
- **Session-based Instagram auth**: Connect via visible browser login; session saved to `storage/sessions/instagram_state.json` (no password stored in Settings when using connect flow)
- **Historical post crawl**: Opens posts one-by-one, expands “View more comments”, scrolls for full threads
- **Incremental / resumable checkpoints** per target (`target_crawl_checkpoints` migration `003_target_crawl_checkpoints.sql`) — stops at last-seen comment to avoid re-processing
- **Reset crawl state**: Clear checkpoints and optionally forget stored comments (`POST /api/v1/targets/reset-crawl-state`, `reset-crawl-state-all`)
- Tunable via `.env`: `HISTORICAL_CRAWL_MAX_POSTS`, `HISTORICAL_CRAWL_MAX_COMMENTS_PER_POST`, `HISTORICAL_CRAWL_COMMENT_EXPAND_ROUNDS`, etc.

### 🖥️ Operations & Monitoring UI
- **Live Monitoring**: Crawl logs with human-readable timestamps (date · time · duration)
- **Crawl log results**: Abusive evidence captured per run with categories, explanations, and screenshot proof
- **Clear old crawl errors** from the monitoring dashboard
- **Settings**: Instagram Connect / Verify / Disconnect; ML classifier toggles; hydration-safe role display

### 📊 Intelligence Dashboard
- Real-time incident feed (WebSocket)
- Platform analytics with Recharts
- Repeat offender profiles + timeline (dossier includes abuse categories & explanations)
- Regional threat distribution maps
- CRITICAL alert system with sound notifications
- **Abuse UX**: `Abusive` + category chips; **bold** comment text; stronger red styling for **lexicon** matches

### 📄 Export & Reporting
- **Excel reports**: Multi-sheet with screenshots (openpyxl)
- **PDF reports**: Police-ready format (reportlab)
- **JSON exports**: Machine-readable evidence packages

---

## 🏗️ Architecture

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
│  │              FastAPI Backend                          │  │
│  │         REST API + WebSocket Server                   │  │
│  └──────────────────────────────────────────┬───────────┘  │
│                                             │              │
│  ┌──────────────────────────────────────────▼───────────┐  │
│  │           Next.js Intelligence Dashboard              │  │
│  │    Live Feed · Maps · Charts · Evidence Gallery       │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Backend** | Python 3.11 + FastAPI | Async REST API + WebSockets |
| **Frontend** | Next.js 14 + TypeScript | Intelligence Dashboard |
| **Database** | PostgreSQL 15 | Primary data store |
| **Cache/Queue** | Redis 7 | Task queue + API cache |
| **Search** | PostgreSQL FTS | Comment/evidence search |
| **Crawling** | Playwright (async) | Browser automation |
| **AI - Hindi** | IndicBERT (HuggingFace) | Hindi abuse detection |
| **AI - Multi** | multilingual-MiniLM | Multilingual embeddings |
| **AI - English** | toxic-bert | English toxicity |
| **Reports** | openpyxl + reportlab | Excel + PDF generation |
| **Maps** | Leaflet + OpenStreetMap | Free map integration |
| **Charts** | Recharts | Dashboard visualizations |
| **Styling** | TailwindCSS | UI design system |
| **State** | Zustand + SWR | Frontend state management |
| **DevOps** | Docker + Docker Compose | Container orchestration |

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- 8GB RAM minimum (for AI models)
- 20GB disk space

### 1. Clone & Configure
```bash
git clone <repo-url> patrol
cd patrol
cp .env.example .env
# Edit .env with your settings
```

### 2. Download AI Models
```bash
python scripts/download_models.py
```

### 3. Start All Services
```bash
docker-compose up -d
```

### 4. Initialize Database
```bash
docker-compose exec backend python -m alembic upgrade head
```

### 5. Seed Demo Data
```bash
docker-compose exec backend python /scripts/seed_db.py
```

### 6. Access Dashboard
```
Dashboard:  http://localhost:3000
API Docs:   http://localhost:8000/docs
```

### 7. Instagram session (live crawl)
1. Open **Settings** → **Connect Instagram** (browser login).
2. **Verify session** after login.
3. Add targets and run crawl from **Live Monitoring** or **Targets**.

### 8. Abuse categories on existing evidence
After upgrading or changing the lexicon, open **Evidence Feed** → **Backfill abuse categories** (Analyst/Admin), or call:
```bash
curl -X POST http://localhost:8000/api/v1/evidence/backfill-categories \
  -H "Authorization: Bearer <token>"
```

**Default credentials:**
```
Email:    admin@patrol.local
Password: Patrol@2024!
```

---

## 📁 Project Structure

See `BRAIN.md` for complete module-level documentation with all file relationships.

```
PATROL/
├── BRAIN.md              ← AI Agent Guide (read first!)
├── docker-compose.yml
├── .env.example
├── backend/              ← FastAPI Python backend
│   ├── ai/               ← Classifier, lexicon, abuse categories & explanations
│   ├── crawlers/         ← Instagram historical crawl, pipeline, checkpoints
│   └── database/migrations/  ← incl. 003_target_crawl_checkpoints.sql
├── frontend/             ← Next.js dashboard
│   └── src/components/abuse/  ← Category badges, explanation panel, bold comment text
├── docs/                 ← All documentation
├── scripts/              ← Setup & utility scripts (e.g. start-backend.ps1)
├── storage/              ← Evidence, screenshots, Instagram sessions
├── ai_models/configs/    ← abuse_lexicon.json, abuse_term_glossary.json
└── tests/                ← Unit, integration, E2E
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [BRAIN.md](./BRAIN.md) | Complete project guide (start here) |
| [task_tracker.md](./docs/task_tracker.md) | Build progress + pending tasks |
| [architecture.md](./docs/architecture.md) | System architecture + decisions |
| [ai_pipeline.md](./docs/ai_pipeline.md) | AI/NLP pipeline documentation |
| [database_design.md](./docs/database_design.md) | Schema + ER diagram |
| [api_reference.md](./docs/api_reference.md) | All API endpoints |
| [crawler_design.md](./docs/crawler_design.md) | Platform crawler design |
| [deployment_guide.md](./docs/deployment_guide.md) | Production deployment |
| [legal_considerations.md](./docs/legal_considerations.md) | Legal & ethical guidelines |
| [roadmap.md](./docs/roadmap.md) | Future feature roadmap |

---

## 🔌 Notable API Endpoints (Live Ops)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/settings/crawler/connect-instagram` | Browser login → save session |
| `POST` | `/api/v1/settings/crawler/verify-instagram-session` | Validate saved session |
| `POST` | `/api/v1/crawlers/logs/{log_id}/reclassify` | Re-run abuse classifier on crawl window |
| `POST` | `/api/v1/evidence/backfill-categories` | Backfill categories + explanations on all evidence |
| `POST` | `/api/v1/targets/reset-crawl-state` | Clear checkpoints / optional forget comments |
| `GET` | `/api/v1/crawlers/logs/{log_id}/results` | Evidence from a crawl run (categories + explanations) |

---

## 🗺️ Roadmap

### MVP (Current)
- [x] Project architecture & scaffolding
- [x] Database schema + authentication
- [x] Instagram live crawler + session auth + historical crawl with checkpoints
- [x] Hindi + Hinglish + English abuse detection (lexicon + optional ML)
- [x] Abuse category labels + investigator explanations + Evidence Feed UX
- [x] Evidence collection + screenshot engine
- [x] Real-time intelligence dashboard + Live Monitoring logs
- [ ] Platform crawlers (Twitter, Facebook, Threads, Telegram) — beyond Instagram patrol
- [ ] PDF + Excel report generation (partial / in progress)

### Phase 2 (Post-MVP)
- [ ] Face recognition for accused profiles
- [ ] Cross-platform identity mapping
- [ ] FIR draft auto-generation
- [ ] Cyber cell workflow integration
- [ ] Mobile app (React Native)
- [ ] AI clustering of related incidents

### Phase 3 (Enterprise)
- [ ] Multi-tenant (multiple organizations)
- [ ] Dedicated cyber cell portal
- [ ] Real-time escalation workflows
- [ ] Court-admissible evidence packages
- [ ] National threat intelligence aggregation

---

## ⚖️ Legal & Ethical

PATROL is designed for **legitimate law enforcement and safety operations only**.

- Monitors **public data only** — no private messages
- Complies with platform Terms of Service where possible
- Evidence collected for **legal reporting purposes**
- Data minimization principles applied
- Audit logs maintained for all actions

See [legal_considerations.md](./docs/legal_considerations.md) for full guidelines.

---

## 👥 For AI Agents Continuing This Project

**Read `BRAIN.md` before any session.** It contains:
- Complete file map with module relationships
- Database schema summary
- API structure
- AI pipeline explanation
- Environment variables
- What's built vs. what's pending

Then check `docs/task_tracker.md` for the next task to build.

---

*Built for those who protect the digital safety of women.*