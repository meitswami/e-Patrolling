"""
PATROL — Application Settings
==============================
All configuration via environment variables.
Uses Pydantic Settings for validation and type safety.

Usage:
    from configs.settings import settings
    print(settings.DATABASE_URL)
"""

import json
from pathlib import Path
from typing import Annotated, List, Optional

from pydantic import BeforeValidator, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Repo root (SocialMediaMonitoringTool/) — two levels up from backend/configs/
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _parse_allowed_origins(value: object) -> List[str]:
    """Accept JSON array or comma-separated URLs (Render-friendly)."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            raise ValueError(
                "ALLOWED_ORIGINS cannot be empty. Example: "
                '["https://your-app.vercel.app"] or https://your-app.vercel.app'
            )
        if raw.startswith("["):
            parsed = json.loads(raw)
            if not isinstance(parsed, list):
                raise ValueError("ALLOWED_ORIGINS JSON must be an array of strings")
            return [str(item).strip() for item in parsed if str(item).strip()]
        return [part.strip() for part in raw.split(",") if part.strip()]
    raise TypeError(f"ALLOWED_ORIGINS must be a string or list, got {type(value).__name__}")


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Defaults are set for local development.
    """

    model_config = SettingsConfigDict(
        # Root .env first; backend/.env overrides (common on EC2 when cwd is backend/)
        env_file=(
            str(_PROJECT_ROOT / ".env"),
            str(_PROJECT_ROOT / "backend" / ".env"),
        ),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Environment ──────────────────────────────────────────
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = False

    # ── Portable Windows build ────────────────────────────────
    PATROL_PORTABLE: bool = False
    PORTABLE_PORT: int = 8765
    STATIC_UI_PATH: Optional[Path] = None

    # ── Database (Supabase PostgreSQL) ───────────────────────
    # Dashboard → Project Settings → Database → Connection string (URI)
    # Use Session pooler (port 6543) for serverless; Direct (5432) for long-lived API.
    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:password@db.whzmtzatkxgiomwlwkgy.supabase.co:5432/postgres"
    )

    # Supabase project (for MCP + client SDK)
    SUPABASE_URL: Optional[str] = None
    SUPABASE_PROJECT_REF: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    DATABASE_SSL: bool = True
    DATABASE_SSL_VERIFY: bool = False  # Set True in production; False fixes Windows dev cert issues
    # If hostname has an IPv4 A record, use it (does not help db.*.supabase.co — use pooler on EC2).
    DATABASE_FORCE_IPV4: bool = True

    # ── Redis (optional until crawlers/queue are built) ─────────
    REDIS_ENABLED: bool = False
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: Optional[str] = None

    # ── JWT ───────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "change_this_in_production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480

    # ── CORS ─────────────────────────────────────────────────
    # NoDecode: Render env UI often uses plain URLs, not JSON arrays.
    ALLOWED_ORIGINS: Annotated[
        List[str],
        NoDecode,
        BeforeValidator(_parse_allowed_origins),
    ] = [
        "http://localhost:3000",
        "http://localhost:80",
        "http://127.0.0.1:3000",
    ]
    # Also allow Vercel preview/production URLs (*.vercel.app) when set (recommended for EC2).
    CORS_ORIGIN_REGEX: Optional[str] = r"https://([a-z0-9-]+\.)*vercel\.app"
    # Merged into CORS middleware — ensures production frontend works even if .env omits ALLOWED_ORIGINS.
    CORS_EXTRA_ORIGINS: Annotated[
        List[str],
        NoDecode,
        BeforeValidator(_parse_allowed_origins),
    ] = ["https://e-patrolling.vercel.app"]

    # ── AI Models ─────────────────────────────────────────────
    MODEL_CACHE_DIR: Path = _PROJECT_ROOT / "ai_models" / "cache"
    USE_GPU: bool = False
    PRELOAD_AI_MODELS: bool = False  # Lazy load for faster startup
    USE_ML_CLASSIFIER: bool = False  # Set true to enable local HF model (downloads on first run)
    USE_MULTILINGUAL_TOXIC: bool = True  # When ML on: textdetox/bert-multilingual-toxicity-classifier (hi+en)
    USE_INDICBERT: bool = False  # Hindi/Hinglish DeBERTa abuse model (large download)
    INDIC_ABUSE_MODEL: str = "Hate-speech-CNERG/indic-abusive-allInOne-MuRIL"
    CAPTURE_EVIDENCE_SCREENSHOTS: bool = True  # Master toggle for evidence PNGs
    EVIDENCE_SCREENSHOT_MODE: str = "both"  # pillow | playwright | both

    # HuggingFace model identifiers
    INDICBERT_MODEL: str = "ai4bharat/indic-bert"
    MINILM_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    TOXIC_BERT_MODEL: str = "unitary/toxic-bert"
    MULTILINGUAL_TOXIC_MODEL: str = "textdetox/bert-multilingual-toxicity-classifier"
    HUGGINGFACE_API_TOKEN: Optional[str] = None
    USE_HF_INFERENCE_API: bool = False

    # AI thresholds
    ABUSE_CONFIDENCE_THRESHOLD: float = 0.65
    CRITICAL_CONFIDENCE_THRESHOLD: float = 0.90

    # ── Storage ───────────────────────────────────────────────
    EVIDENCE_STORAGE_PATH: Path = _PROJECT_ROOT / "storage" / "evidence"
    SCREENSHOTS_PATH: Path = _PROJECT_ROOT / "storage" / "screenshots"
    EXPORTS_PATH: Path = _PROJECT_ROOT / "storage" / "exports"
    LOGS_PATH: Path = _PROJECT_ROOT / "storage" / "logs"

    # ── Crawler ───────────────────────────────────────────────
    CRAWLER_HEADLESS: bool = True
    CRAWLER_TIMEOUT_MS: int = 30000
    CRAWLER_DEMO_MODE: bool = False  # Live-only; synthetic demo mode removed
    CRAWLER_SCHEDULER_ENABLED: bool = True  # APScheduler crawl-all on startup
    MAX_CONCURRENT_BROWSERS: int = 3
    CRAWL_INTERVAL_SECONDS: int = 300  # 5 minutes between crawl cycles; 0 = disabled
    # Historical crawl: scroll profile for older posts, then comments per post
    HISTORICAL_CRAWL_MAX_POSTS: int = 12
    HISTORICAL_CRAWL_MAX_COMMENTS_PER_POST: int = 80
    HISTORICAL_CRAWL_PROFILE_SCROLLS: int = 8
    # Comment loading: higher = more complete but slower (clicks "View more" repeatedly)
    HISTORICAL_CRAWL_COMMENT_EXPAND_ROUNDS: int = 15
    HISTORICAL_CRAWL_COMMENT_SCROLL_ROUNDS: int = 10
    HISTORICAL_CRAWL_POST_DELAY_SEC: float = 2.0
    HISTORICAL_CRAWL_PROFILE_SCROLL_DELAY_SEC: float = 1.5
    WEEKLY_REPORT_EXPORT_ENABLED: bool = True
    WEEKLY_REPORT_DAY: str = "mon"
    WEEKLY_REPORT_HOUR: int = 6

    # Platform credentials (optional — public crawling if empty)
    INSTAGRAM_USERNAME: Optional[str] = None
    INSTAGRAM_PASSWORD: Optional[str] = None
    TWITTER_BEARER_TOKEN: Optional[str] = None
    FACEBOOK_ACCESS_TOKEN: Optional[str] = None
    TELEGRAM_API_ID: Optional[str] = None
    TELEGRAM_API_HASH: Optional[str] = None
    TELEGRAM_PHONE: Optional[str] = None

    # ── Rate Limiting ─────────────────────────────────────────
    API_RATE_LIMIT_PER_MINUTE: int = 60
    CRAWLER_RATE_LIMIT_PER_PLATFORM: int = 10

    # ── Map ───────────────────────────────────────────────────
    MAP_PROVIDER: str = "openstreetmap"
    GOOGLE_MAPS_API_KEY: Optional[str] = None

    # ── First Admin ───────────────────────────────────────────
    ADMIN_EMAIL: str = "admin@patrol.dev"
    ADMIN_PASSWORD: str = "Patrol@2024!"
    ADMIN_NAME: str = "System Administrator"

    # ── Alerts ───────────────────────────────────────────────
    ALERT_EMAIL_ENABLED: bool = False
    ALERT_EMAIL_HOST: Optional[str] = None
    ALERT_EMAIL_PORT: int = 587
    ALERT_EMAIL_USER: Optional[str] = None
    ALERT_EMAIL_PASS: Optional[str] = None
    ALERT_EMAIL_TO: Optional[str] = None

    @field_validator("MODEL_CACHE_DIR", "EVIDENCE_STORAGE_PATH", "SCREENSHOTS_PATH",
                     "EXPORTS_PATH", "LOGS_PATH", mode="before")
    @classmethod
    def create_dirs(cls, v: str) -> Path:
        """Auto-create storage directories if they don't exist."""
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    @property
    def uses_supabase(self) -> bool:
        return (
            self.SUPABASE_URL is not None
            or self.SUPABASE_PROJECT_REF is not None
            or "supabase.co" in self.DATABASE_URL
            or "supabase.com" in self.DATABASE_URL
        )

    @property
    def effective_cors_origins(self) -> List[str]:
        """ALLOWED_ORIGINS + CORS_EXTRA_ORIGINS (deduped)."""
        merged: List[str] = []
        for origin in [*self.ALLOWED_ORIGINS, *self.CORS_EXTRA_ORIGINS]:
            o = origin.strip()
            if o and o not in merged:
                merged.append(o)
        return merged

    @property
    def database_url_direct(self) -> str:
        """DSN for asyncpg/psql (without SQLAlchemy driver prefix)."""
        url = self.DATABASE_URL
        if url.startswith("postgresql+asyncpg://"):
            return url.replace("postgresql+asyncpg://", "postgresql://", 1)
        return url


# Singleton — import this everywhere
settings = Settings()