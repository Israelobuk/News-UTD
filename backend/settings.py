"""Environment-backed runtime settings for Market Signal Monitor."""

from __future__ import annotations

import os

from pydantic import BaseModel, Field


DEFAULT_SUBREDDITS = ["stocks", "investing", "economics", "cryptocurrency"]
DEFAULT_CORS_ALLOW_ORIGINS = [
    "https://newsutd.vercel.app",
    "http://127.0.0.1:5173",
    "http://localhost:5173",
]


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


class BackendSettings(BaseModel):
    """Strongly typed app settings loaded from environment variables."""

    app_name: str = "NewsUTD Market Signal Monitor"
    subreddits: list[str] = Field(default_factory=lambda: list(DEFAULT_SUBREDDITS))
    posts_per_subreddit: int = 200
    top_posts_limit: int = 20
    max_processed_posts: int = 10000
    poll_seconds: float = 5.0
    use_mock_data: bool = False
    reddit_fetch_cache_seconds: float = 20.0
    ollama_enabled: bool = False
    ollama_model: str = "llama3.1:8b"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_timeout_seconds: float = 20.0
    ollama_chat_timeout_seconds: float = 8.0
    market_chat_timeout_seconds: float = 1.5
    ollama_min_confidence: float = 0.55
    cors_allow_origins: list[str] = Field(default_factory=lambda: list(DEFAULT_CORS_ALLOW_ORIGINS))
    postgres_cache_enabled: bool = False
    postgres_cache_dsn: str = ""
    postgres_cache_max_rows: int = 5000
    postgres_cache_read_limit: int = 120
    pandas_group_limit: int = 6

    @classmethod
    def from_env(cls) -> "BackendSettings":
        raw_subreddits = [
            item.strip()
            for item in os.getenv("SUBREDDITS", ",".join(DEFAULT_SUBREDDITS)).split(",")
            if item.strip()
        ]
        raw_origins = [
            origin.strip()
            for origin in os.getenv(
                "CORS_ALLOW_ORIGINS",
                ",".join(DEFAULT_CORS_ALLOW_ORIGINS),
            ).split(",")
            if origin.strip()
        ]
        if "*" in raw_origins:
            merged_origins = ["*"]
        else:
            merged_origins = list(dict.fromkeys([*raw_origins, *DEFAULT_CORS_ALLOW_ORIGINS]))
        postgres_cache_dsn = os.getenv("POSTGRES_CACHE_DSN", "").strip()
        postgres_cache_enabled = _parse_bool(
            os.getenv("POSTGRES_CACHE_ENABLED"),
            default=bool(postgres_cache_dsn),
        )
        return cls(
            app_name=os.getenv("APP_NAME", "NewsUTD Market Signal Monitor").strip()
            or "NewsUTD Market Signal Monitor",
            subreddits=raw_subreddits or list(DEFAULT_SUBREDDITS),
            posts_per_subreddit=int(os.getenv("POSTS_PER_SUBREDDIT", "200")),
            top_posts_limit=int(os.getenv("TOP_POSTS_LIMIT", "20")),
            max_processed_posts=int(os.getenv("MAX_PROCESSED_POSTS", "10000")),
            poll_seconds=float(os.getenv("POLL_SECONDS", "5")),
            use_mock_data=_parse_bool(os.getenv("USE_MOCK_DATA"), default=False),
            reddit_fetch_cache_seconds=float(os.getenv("REDDIT_FETCH_CACHE_SECONDS", "20")),
            ollama_enabled=_parse_bool(os.getenv("OLLAMA_ENABLED"), default=False),
            ollama_model=os.getenv("OLLAMA_MODEL", "llama3.1:8b").strip() or "llama3.1:8b",
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").strip()
            or "http://127.0.0.1:11434",
            ollama_timeout_seconds=float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "20")),
            ollama_chat_timeout_seconds=float(os.getenv("OLLAMA_CHAT_TIMEOUT_SECONDS", "8")),
            market_chat_timeout_seconds=float(os.getenv("MARKET_CHAT_TIMEOUT_SECONDS", "1.5")),
            ollama_min_confidence=float(os.getenv("OLLAMA_MIN_CONFIDENCE", "0.55")),
            cors_allow_origins=merged_origins,
            postgres_cache_enabled=postgres_cache_enabled,
            postgres_cache_dsn=postgres_cache_dsn,
            postgres_cache_max_rows=max(500, int(os.getenv("POSTGRES_CACHE_MAX_ROWS", "5000"))),
            postgres_cache_read_limit=max(20, int(os.getenv("POSTGRES_CACHE_READ_LIMIT", "120"))),
            pandas_group_limit=max(3, int(os.getenv("PANDAS_GROUP_LIMIT", "6"))),
        )
