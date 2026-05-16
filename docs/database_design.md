# PATROL — Database Design
> **For AI Agents:** Complete schema reference. Read before writing any DB query or migration.

## Schema Overview (Mermaid ER Diagram)

```mermaid
erDiagram
    users {
        uuid id PK
        varchar email UK
        varchar name
        varchar password_hash
        user_role role
        boolean is_active
        timestamp last_login_at
        timestamp created_at
    }

    target_accounts {
        uuid id PK
        varchar username
        varchar display_name
        platform_type platform
        text profile_url
        boolean is_active
        boolean monitoring_enabled
        varchar inferred_region
        float region_confidence
        uuid added_by FK
        timestamp last_crawled_at
    }

    accused_profiles {
        uuid id PK
        platform_type platform
        varchar username
        integer total_incidents
        integer critical_count
        float avg_severity_score
        integer max_risk_score
        offender_status status
        boolean is_repeat_offender
        varchar inferred_region
    }

    crawled_comments {
        uuid id PK
        varchar content_hash UK
        platform_type platform
        text post_url
        text text
        language_type language
        uuid target_id FK
        uuid accused_id FK
        boolean is_processed
        timestamp crawled_at
    }

    ai_results {
        uuid id PK
        uuid comment_id FK
        boolean is_abusive
        boolean is_rape_threat
        float confidence_score
        integer risk_score
        severity_level severity_level
        language_type detected_language
        text[] matched_keywords
        jsonb detected_entities
    }

    evidence_reports {
        uuid id PK
        varchar evidence_id UK
        uuid comment_id FK
        uuid ai_result_id FK
        uuid target_id FK
        uuid accused_id FK
        platform_type platform
        text comment_text
        severity_level severity_level
        integer risk_score
        text screenshot_path
        varchar screenshot_hash
        boolean is_escalated
    }

    repeat_offenders {
        uuid id PK
        uuid accused_id FK
        integer total_offenses
        integer targets_harassed
        platform_type[] platforms_used
        offender_status status
        integer priority_score
    }

    region_scores {
        uuid id PK
        uuid accused_id FK
        varchar city
        varchar state
        varchar country
        float latitude
        float longitude
        float confidence
        jsonb detection_signals
    }

    monitoring_logs {
        uuid id PK
        uuid target_id FK
        platform_type platform
        integer comments_found
        integer abusive_detected
        boolean success
        timestamp started_at
    }

    users ||--o{ target_accounts : "added_by"
    target_accounts ||--o{ crawled_comments : "target_id"
    accused_profiles ||--o{ crawled_comments : "accused_id"
    crawled_comments ||--|| ai_results : "comment_id"
    crawled_comments ||--o| evidence_reports : "comment_id"
    ai_results ||--o| evidence_reports : "ai_result_id"
    target_accounts ||--o{ evidence_reports : "target_id"
    accused_profiles ||--o{ evidence_reports : "accused_id"
    accused_profiles ||--o| repeat_offenders : "accused_id"
    accused_profiles ||--o{ region_scores : "accused_id"
    target_accounts ||--o{ monitoring_logs : "target_id"
```

---

## Table Reference

### `users`
Admin and analyst accounts. Passwords stored as bcrypt hashes (never plaintext).
- Roles: ADMIN (full), ANALYST (read+write), VIEWER (read-only)
- JWT tokens reference `users.id`

### `target_accounts`
Women influencers/public figures being monitored.
- One row per (username, platform) combination
- `monitoring_enabled` = false pauses crawling without deleting
- `last_crawled_at` updated after each crawler run

### `accused_profiles`
Unique offender profiles normalized across all incidents.
- One row per (username, platform) — not per incident
- `total_incidents`, `avg_severity_score`, `max_risk_score` updated via trigger or service
- `is_repeat_offender` = true when total_incidents >= 3

### `crawled_comments`
Raw data from all platform crawls. Deduplicated by `content_hash` (SHA256 of platform+comment_id+text).
- `is_processed` = false until AI pipeline runs
- Full-text search via `pg_trgm` index on `text`
- JSON `raw_data` stores platform-specific fields

### `ai_results`
One-to-one with `crawled_comments`. Created by AI pipeline.
- Separate boolean per abuse category (easy filtering)
- `matched_keywords` array stores which lexicon words triggered
- `detected_entities` JSONB: `{persons: [], locations: [], phones: []}`

### `evidence_reports`
Legal evidence packages. Created when AI detects abuse.
- `evidence_id` = human-readable ID (e.g., `EVD-2024-001234`)
- `screenshot_path` = relative path in storage directory
- `screenshot_hash` = SHA256 of screenshot file (integrity)
- `chain_of_custody` JSONB records all access/actions

### `repeat_offenders`
Populated when accused_profiles.total_incidents >= 3.
- `priority_score` computed from: total_offenses × severity_weights
- Used for dashboard "Repeat Offenders" page

### `monitoring_logs`
Audit trail for every crawler run. Never deleted.

### `region_scores`
Geographic inference per accused profile.
- `detection_signals` JSONB example:
  ```json
  {
    "bio_keywords": ["Jaipur", "राजस्थान"],
    "hashtags": ["#Jaipur"],
    "language_region": "Rajasthani Hindi",
    "confidence_factors": {...}
  }
  ```

---

## Key Queries

### Dashboard Stats
```sql
SELECT
    (SELECT COUNT(*) FROM target_accounts WHERE is_active = TRUE) AS active_targets,
    (SELECT COUNT(*) FROM evidence_reports 
     WHERE created_at > NOW() - INTERVAL '24 hours') AS evidence_24h,
    (SELECT COUNT(*) FROM evidence_reports 
     WHERE severity_level = 'CRITICAL') AS critical_total,
    (SELECT COUNT(*) FROM repeat_offenders 
     WHERE status = 'CONFIRMED') AS repeat_offenders;
```

### Recent Evidence Feed (Dashboard Live Feed)
```sql
SELECT er.*, ta.username AS target_username, ap.username AS accused_username
FROM evidence_reports er
JOIN target_accounts ta ON er.target_id = ta.id
JOIN accused_profiles ap ON er.accused_id = ap.id
WHERE er.severity_level IN ('HIGH', 'CRITICAL')
ORDER BY er.created_at DESC
LIMIT 50;
```

### Region Threat Map Data
```sql
SELECT 
    rs.state, rs.city, rs.latitude, rs.longitude,
    COUNT(er.id) AS incident_count,
    COUNT(CASE WHEN er.severity_level = 'CRITICAL' THEN 1 END) AS critical_count
FROM region_scores rs
JOIN accused_profiles ap ON rs.accused_id = ap.id
JOIN evidence_reports er ON er.accused_id = ap.id
WHERE rs.latitude IS NOT NULL
GROUP BY rs.state, rs.city, rs.latitude, rs.longitude
ORDER BY incident_count DESC;
```

### Unprocessed Comments (AI Worker Query)
```sql
SELECT id, text, platform, target_id, accused_id
FROM crawled_comments
WHERE is_processed = FALSE
ORDER BY crawled_at ASC
LIMIT 100
FOR UPDATE SKIP LOCKED;  -- Critical: prevents duplicate processing
```

### Repeat Offender Detection
```sql
UPDATE accused_profiles
SET is_repeat_offender = TRUE
WHERE total_incidents >= 3
  AND is_repeat_offender = FALSE
RETURNING id, username, platform, total_incidents;
```

---

## Indexes Summary

| Table | Index | Type | Purpose |
|-------|-------|------|---------|
| `crawled_comments` | `text` | GIN trgm | Full-text search |
| `crawled_comments` | `text` | GIN FTS | PostgreSQL text search |
| `ai_results` | `risk_score DESC` | BTree | Dashboard top threats |
| `evidence_reports` | `created_at DESC` | BTree | Chronological feed |
| `accused_profiles` | `max_risk_score DESC` | BTree | Top offender ranking |

---

## Migration Strategy

- Migrations in `backend/database/migrations/`
- Naming: `001_initial_schema.sql`, `002_add_doxxing_flag.sql`, etc.
- Apply with: `alembic upgrade head`
- Never edit `schema.sql` directly after first deployment — create migrations

---

## Connection Pool Config

```python
# database/connection.py

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=10,           # 10 persistent connections
    max_overflow=20,        # 20 additional overflow connections
    pool_timeout=30,        # Wait max 30s for connection
    pool_recycle=3600,      # Recycle connections hourly
    echo=settings.DEBUG,    # Log SQL in debug mode
)
```