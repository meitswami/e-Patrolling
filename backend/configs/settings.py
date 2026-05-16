"""
PATROL — Application Settings
==============================
All configuration via environment variables.
Uses Pydantic Settings for validation and type safety.

Usage:
    from configs.settings import settings
    print(settings.DATABASE_URL)
"""

from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

# Repo root (SocialMediaMonitoringTool/) — two levels up from backend/configs/
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Defaults are set for local development.
    """

    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Environment ──────────────────────────────────────────
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = False

    # ── Database ─────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://patrol:patrol_secret@localhost:5432/patrol_db"

    # ── Redis ─────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: Optional[str] = None

    # ── JWT ───────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "change_this_in_production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480

    # ── CORS ─────────────────────────────────────────────────
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:80",
        "http://127.0.0.1:3000",
    ]

    # ── AI Models ─────────────────────────────────────────────
    MODEL_CACHE_DIR: Path = _PROJECT_ROOT / "ai_models" / "cache"
    USE_GPU: bool = False
    PRELOAD_AI_MODELS: bool = False  # Lazy load for faster startup

    # HuggingFace model identifiers
    INDICBERT_MODEL: str = "ai4bharat/IndicBERT"
    MINILM_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    TOXIC_BERT_MODEL: str = "unitary/toxic-bert"

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
    MAX_CONCURRENT_BROWSERS: int = 3
    CRAWL_INTERVAL_SECONDS: int = 300  # 5 minutes between crawl cycles

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
    ADMIN_EMAIL: str = "admin@patrol.local"
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


# Singleton — import this everywhere
settings = Settings()