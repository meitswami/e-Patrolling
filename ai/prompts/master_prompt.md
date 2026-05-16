You are a Senior AI Architect, Principal Engineer, OSINT Specialist, Cyber Intelligence System Designer, NLP Engineer, Full Stack Engineer, DevOps Architect, and Security Engineer.

Your task is to build a COMPLETE ENTERPRISE-GRADE MVP platform called:

# PATROL

## Full Form:
Predictive Abuse Tracking & Regional Observation Layer

Tagline:
AI-Powered Regional Social Media Harassment Intelligence System

========================================================
PROJECT OVERVIEW
========================================================

PATROL is an AI-powered cyber intelligence and social media monitoring platform designed to detect, monitor, analyze, and generate evidence for abusive, threatening, harassing, stalking, or targeted harmful activity against women influencers/public figures across multiple social media platforms.

The system must support:
- Real-time monitoring
- AI-based abuse detection
- Hindi + Hinglish + English analysis
- Regional intelligence filtering
- Evidence collection
- Screenshot capture
- Repeat offender tracking
- Dashboard analytics
- Exportable cyber intelligence reports

The system should feel like a real cyber intelligence command center suitable for:
- Cyber Cells
- Law Enforcement
- Women Safety Organizations
- OSINT Teams
- Threat Intelligence Operations

========================================================
IMPORTANT DEVELOPMENT RULES
========================================================

This is NOT a simple scraper project.

This MUST be built as:
- A scalable intelligence platform
- Clean enterprise architecture
- Proper documentation
- Production-ready structure
- Modular platform adapters
- AI-ready pipelines
- Secure backend
- Real-time analytics system

Everything must be highly structured and professionally organized.

========================================================
SUPPORTED MVP PLATFORMS
========================================================

The MVP must support:

1. Instagram
2. Facebook
3. Twitter/X
4. Threads
5. Telegram
6. WhatsApp Channels/Public Groups (if feasible)

IMPORTANT:
- Public data only
- No illegal/private scraping
- Respect platform limitations
- Build modular adapters

========================================================
PRIMARY MVP GOALS
========================================================

The MVP demonstration must show:

- Multi-platform monitoring
- Live comment/reply monitoring
- Hindi abuse detection
- English abuse detection
- Hinglish abuse detection
- Screenshot evidence generation
- Live dashboard
- Region-based filtering
- Risk scoring
- Repeat offender detection
- Exportable reports
- Real-time analytics
- Live intelligence feed

========================================================
TECH STACK
========================================================

BACKEND:
- Python FastAPI
- Async architecture
- WebSockets

FRONTEND:
- Next.js
- TypeScript
- TailwindCSS

DATABASE:
- PostgreSQL

QUEUE:
- RabbitMQ OR Redis Queue

SEARCH:
- Elasticsearch OR PostgreSQL Full Text Search

CRAWLING:
- Playwright
- Browser context reuse
- Async workers

AI/NLP:
- HuggingFace Transformers
- IndicBERT
- multilingual MiniLM
- sentence-transformers
- Detoxify (optional)

REPORTS:
- openpyxl
- reportlab

DEVOPS:
- Docker
- Docker Compose

========================================================
PROJECT STRUCTURE
========================================================

Generate COMPLETE folder structure.

Required:

/backend
/frontend
/storage
/docs
/tests
/docker
/scripts
/deployment
/ai_models

========================================================
BACKEND REQUIREMENTS
========================================================

Create modular backend architecture.

Required modules:

backend/
├── api/
├── crawlers/
├── ai/
├── evidence/
├── monitoring/
├── analytics/
├── websocket/
├── database/
├── auth/
├── queue/
├── services/
├── exports/
├── region_engine/
├── utils/
├── configs/

========================================================
PLATFORM CRAWLERS
========================================================

Each platform must have dedicated crawler modules.

Folder example:

backend/crawlers/instagram/
- adapter.py
- parser.py
- screenshot.py
- session_manager.py
- comment_monitor.py

Repeat same structure for:
- Facebook
- Twitter/X
- Threads
- Telegram
- WhatsApp

========================================================
CRAWLER FEATURES
========================================================

Support:
- Login/session persistence
- Comment extraction
- Reply monitoring
- Retry handling
- Screenshot capture
- Queue integration
- Rate limit handling

Use:
- Playwright
- Async browser contexts

Avoid Selenium.

========================================================
AI ABUSE DETECTION ENGINE
========================================================

This is the CORE engine.

Must support:
- Hindi
- Hinglish
- English

Detect:
- Abuse
- Sexual harassment
- Rape threats
- Obscene comments
- Stalking
- Targeted bullying
- Hate speech
- Threats
- Repeat harassment

========================================================
AI MODULES
========================================================

Create:
backend/ai/

Modules:
- classifier.py
- language_detector.py
- severity_engine.py
- risk_scoring.py
- entity_detector.py
- keyword_engine.py

========================================================
ABUSE CLASSIFICATION LEVELS
========================================================

Generate:
- confidence score
- toxicity score
- severity score

Levels:
- LOW
- MEDIUM
- HIGH
- CRITICAL

========================================================
EVIDENCE COLLECTION ENGINE
========================================================

When abusive content is detected:

Automatically store:
- Comment
- Accused profile
- Target profile
- Platform
- Timestamp
- URL
- Screenshot
- AI result
- Threat level

========================================================
SCREENSHOT ENGINE
========================================================

Use Playwright screenshots.

Store inside:

storage/evidence/
platform/year/month/day/

========================================================
REAL-TIME PIPELINE
========================================================

Architecture:

Crawler
→ Queue
→ AI Engine
→ Evidence Engine
→ Database
→ Dashboard
→ Real-time Alerts

========================================================
DATABASE DESIGN
========================================================

Use PostgreSQL.

Create proper:
- migrations
- schema.sql
- indexes
- relations

Required tables:
- target_accounts
- crawled_comments
- ai_results
- evidence_reports
- accused_profiles
- repeat_offenders
- monitoring_logs
- region_scores
- dashboard_events

========================================================
REGION DETECTION ENGINE
========================================================

Implement intelligent region inference.

Detect region using:
- Bio keywords
- Geotags
- Hashtags
- Captions
- Language
- Social graph

Generate:
- region confidence score

Example:
Jaipur → 92%

========================================================
REAL-TIME ADMIN INTELLIGENCE DASHBOARD
========================================================

Build an ADVANCED CYBER INTELLIGENCE ADMIN PANEL.

The dashboard must feel like:
- SOC dashboard
- Threat intelligence center
- OSINT investigation platform

========================================================
ADMIN DASHBOARD FEATURES
========================================================

Dashboard pages:
- Overview
- Live Monitoring
- Evidence Feed
- Region Intelligence
- Repeat Offenders
- Platform Analytics
- Reports
- Settings

========================================================
LIVE ANALYTICS
========================================================

Display:
- Total monitored accounts
- Live abusive comments
- High-risk threats
- Repeat offenders
- Region-wise incidents
- Platform-wise incidents
- AI confidence metrics
- Trending abuse keywords
- Evidence count
- Confirmed offenders

========================================================
REAL-TIME LIVE FEED
========================================================

Display:
- Latest abusive comments
- Screenshot previews
- Target account
- Accused account
- Platform
- Timestamp
- Severity score

Auto-refresh using:
- WebSockets
- Socket.IO

========================================================
MAP INTEGRATION
========================================================

Integrate:
- Google Maps API OR OpenStreetMap

Features:
- Region search
- Auto-complete
- Geo filtering
- Threat heatmaps
- Incident clustering
- Region drill-down

========================================================
REGION FILTERING LOGIC
========================================================

When admin selects:
- Jaipur
- Rajasthan
- Delhi
etc.

The system must:
- Filter dashboard live
- Prioritize crawler monitoring
- Update analytics dynamically
- Show region-specific evidence

========================================================
INTELLIGENCE FILTERS
========================================================

Admin filters:
- Region
- Platform
- Threat level
- Language
- Gender
- Verified users
- Repeat offenders
- Time range

========================================================
REAL-TIME ALERT SYSTEM
========================================================

Implement:
- Critical alerts
- Flash indicators
- Sound notifications
- Escalation flags

========================================================
VISUAL ANALYTICS
========================================================

Use:
- Recharts
- D3.js (optional)

Include:
- Heatmaps
- Live timelines
- Threat graphs
- Region analytics
- Platform analytics

========================================================
REPORTING ENGINE
========================================================

Generate:
- Excel reports
- PDF reports
- JSON exports

Include:
- Screenshots
- Metadata
- Threat classification
- Evidence IDs

========================================================
SEARCH ENGINE
========================================================

Support searching by:
- Username
- Platform
- Abuse keyword
- Threat level
- Region

========================================================
SECURITY REQUIREMENTS
========================================================

Implement:
- JWT Authentication
- RBAC
- Secure environment configs
- API rate limiting
- Audit logging

========================================================
FREE / LOCAL MVP REQUIREMENTS
========================================================

IMPORTANT:
Everything must run locally for MVP.

Prefer:
- Open-source tools
- Free AI models
- Dockerized setup
- CPU-compatible fallback

Avoid:
- Expensive APIs
- Paid enterprise services

========================================================
DEVOPS REQUIREMENTS
========================================================

Provide:
- Docker Compose
- Health checks
- Logging system
- Environment configs
- Monitoring setup

========================================================
DOCUMENTATION REQUIREMENTS
========================================================

Create COMPLETE documentation.

Required docs:

/docs
- architecture.md
- system_design.md
- crawler_design.md
- ai_pipeline.md
- dashboard_architecture.md
- database_design.md
- deployment_guide.md
- api_reference.md
- legal_considerations.md
- roadmap.md
- task_tracker.md

========================================================
README REQUIREMENTS
========================================================

Create enterprise-grade README including:
- Project overview
- Features
- Architecture
- Installation
- Docker setup
- Development setup
- AI pipeline
- Dashboard overview
- Platform limitations
- Future roadmap

========================================================
TASK TRACKING
========================================================

Create:
docs/task_tracker.md

Track:
- Completed tasks
- Pending tasks
- Current sprint
- MVP progress
- Future enhancements

========================================================
FUTURE ROADMAP SUPPORT
========================================================

Design architecture for future support:
- Face recognition
- Cross-platform identity mapping
- AI clustering
- FIR draft generation
- Cyber cell workflows
- Mobile apps
- Multi-region deployment
- Real-time escalation

========================================================
CODING STANDARDS
========================================================

Use:
- Clean architecture
- SOLID principles
- Modular services
- Async-first design
- Type hints
- Structured logging

========================================================
VISUAL DOCUMENTATION
========================================================

Generate:
- Mermaid diagrams
- System diagrams
- Flowcharts
- Pipeline diagrams

========================================================
IMPLEMENTATION STRATEGY
========================================================

DO NOT generate entire project at once.

Follow PHASE-WISE development.

PHASE 1:
- Architecture
- Folder structure
- Backend skeleton
- Frontend skeleton
- Docker setup
- Documentation

PHASE 2:
- Database
- Queue pipeline
- Authentication

PHASE 3:
- Platform crawlers

PHASE 4:
- AI abuse detection engine

PHASE 5:
- Evidence engine
- Screenshot engine

PHASE 6:
- Dashboard
- WebSockets
- Real-time analytics

PHASE 7:
- Reports
- Export system

PHASE 8:
- Testing
- Optimization
- Final documentation

========================================================
IMPORTANT OUTPUT RULES
========================================================

Always:
- Explain architecture decisions
- Create files properly
- Maintain documentation
- Update task tracker
- Keep code modular
- Use scalable design

Never:
- Generate messy code
- Hardcode secrets
- Skip documentation
- Mix unrelated modules

========================================================
FINAL OBJECTIVE
========================================================

Build a PROFESSIONAL AI-powered cyber intelligence MVP platform that looks and behaves like a real-world threat intelligence and social media harassment monitoring system suitable for demonstrations to:
- Cyber Cells
- Police Departments
- Women Safety Initiatives
- OSINT Teams
- Intelligence Agencies

Begin now with:

1. Complete architecture planning
2. Folder structure generation
3. Tech stack explanation
4. Development roadmap
5. Backend initialization
6. Frontend initialization
7. Docker setup
8. Documentation generation

Then proceed phase-by-phase systematically.