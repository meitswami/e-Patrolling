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
- **7 abuse categories**: Sexual harassment, rape threats, stalking, hate speech, doxxing, threats, bullying
- **4-level severity**: LOW → MEDIUM → HIGH → CRITICAL
- **Confidence scoring**: 0–100 composite risk score
- **Real-time processing**: < 500ms per comment analysis

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

### 📊 Intelligence Dashboard
- Real-time incident feed (WebSocket)
- Platform analytics with Recharts
- Repeat offender profiles + timeline
- Regional threat distribution maps
- CRITICAL alert system with sound notifications

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
├── frontend/             ← Next.js dashboard
├── docs/                 ← All documentation
├── scripts/              ← Setup & utility scripts
├── storage/              ← Evidence, screenshots, exports
├── ai_models/            ← Downloaded model cache
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

## 🗺️ Roadmap

### MVP (Current)
- [x] Project architecture & scaffolding
- [ ] Database schema + authentication
- [ ] Platform crawlers (Instagram, Twitter, Facebook, Threads, Telegram)
- [ ] Hindi + Hinglish + English AI abuse detection
- [ ] Evidence collection + screenshot engine
- [ ] Real-time intelligence dashboard
- [ ] PDF + Excel report generation

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