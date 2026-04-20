"""Optional PostgreSQL-backed cache for NewsUTD signal posts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Sequence

from reddit_scraper import RedditPost
from schemas import SerializedPost

try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:  # pragma: no cover - optional runtime dependency
    psycopg = None
    dict_row = None


class PostgresSignalCache:
    """Caches normalized posts in PostgreSQL for resilient fallback reads."""

    def __init__(self, dsn: str, max_rows: int = 5000) -> None:
        self.dsn = str(dsn or "").strip()
        self.max_rows = max(500, int(max_rows))
        self._last_error = ""

    @property
    def enabled(self) -> bool:
        return bool(self.dsn and psycopg is not None and dict_row is not None)

    @property
    def last_error(self) -> str:
        return self._last_error

    def initialize(self) -> bool:
        if not self.enabled:
            if not self.dsn:
                self._last_error = "POSTGRES_CACHE_DSN is not set."
            elif psycopg is None:
                self._last_error = "psycopg is not installed."
            return False

        try:
            with self._connect() as conn, conn.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS newsutd_post_cache (
                        post_id TEXT PRIMARY KEY,
                        subreddit TEXT NOT NULL,
                        signal_score DOUBLE PRECISION NOT NULL DEFAULT 0,
                        created_utc DOUBLE PRECISION NOT NULL DEFAULT 0,
                        seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        payload JSONB NOT NULL
                    );
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_newsutd_post_cache_seen_at
                    ON newsutd_post_cache (seen_at DESC);
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_newsutd_post_cache_subreddit
                    ON newsutd_post_cache (subreddit);
                    """
                )
            self._last_error = ""
            return True
        except Exception as exc:  # pragma: no cover - depends on local db
            self._last_error = str(exc)
            return False

    def cache_posts(self, posts: Sequence[RedditPost]) -> int:
        if not self.enabled or not posts:
            return 0

        records = [SerializedPost.from_post(post).model_dump() for post in posts]
        rows = [
            (
                record["id"],
                record["subreddit"],
                float(record.get("signal_score", 0.0)),
                float(record.get("created_utc", 0.0)),
                json.dumps(record),
            )
            for record in records
        ]

        try:
            with self._connect() as conn, conn.cursor() as cursor:
                cursor.executemany(
                    """
                    INSERT INTO newsutd_post_cache (
                        post_id,
                        subreddit,
                        signal_score,
                        created_utc,
                        payload,
                        seen_at
                    )
                    VALUES (%s, %s, %s, %s, %s::jsonb, NOW())
                    ON CONFLICT (post_id) DO UPDATE
                    SET subreddit = EXCLUDED.subreddit,
                        signal_score = EXCLUDED.signal_score,
                        created_utc = EXCLUDED.created_utc,
                        payload = EXCLUDED.payload,
                        seen_at = NOW();
                    """,
                    rows,
                )
                cursor.execute(
                    """
                    DELETE FROM newsutd_post_cache
                    WHERE post_id IN (
                        SELECT post_id
                        FROM newsutd_post_cache
                        ORDER BY seen_at DESC
                        OFFSET %s
                    );
                    """,
                    (self.max_rows,),
                )
            self._last_error = ""
            return len(rows)
        except Exception as exc:  # pragma: no cover - depends on local db
            self._last_error = str(exc)
            return 0

    def fetch_posts(self, subreddits: Sequence[str], limit: int = 120) -> list[RedditPost]:
        if not self.enabled:
            return []

        cleaned_subreddits = [
            str(item or "").strip().lower()
            for item in subreddits
            if str(item or "").strip()
        ]
        read_limit = max(20, int(limit))

        try:
            with self._connect() as conn, conn.cursor() as cursor:
                if cleaned_subreddits:
                    cursor.execute(
                        """
                        SELECT payload
                        FROM newsutd_post_cache
                        WHERE subreddit = ANY(%s)
                        ORDER BY signal_score DESC, created_utc DESC, seen_at DESC
                        LIMIT %s;
                        """,
                        (cleaned_subreddits, read_limit),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT payload
                        FROM newsutd_post_cache
                        ORDER BY signal_score DESC, created_utc DESC, seen_at DESC
                        LIMIT %s;
                        """,
                        (read_limit,),
                    )
                rows = cursor.fetchall()
            parsed_posts: list[RedditPost] = []
            for row in rows:
                post = self._row_to_post(row)
                if post is not None:
                    parsed_posts.append(post)
            self._last_error = ""
            return parsed_posts
        except Exception as exc:  # pragma: no cover - depends on local db
            self._last_error = str(exc)
            return []

    def _connect(self):
        return psycopg.connect(self.dsn, autocommit=True, row_factory=dict_row)

    @staticmethod
    def _row_to_post(row: dict) -> RedditPost | None:
        payload = row.get("payload", {})
        if not isinstance(payload, dict):
            return None
        try:
            return SerializedPost.model_validate(payload).to_post()
        except Exception:
            return None


class PostgresMarketCache:
    """Caches market movers sets in PostgreSQL for resilient market widget reads."""

    CACHE_KEY = "market_sets_v1"

    def __init__(self, dsn: str, max_age_seconds: int = 6 * 60 * 60) -> None:
        self.dsn = str(dsn or "").strip()
        self.max_age_seconds = max(60, int(max_age_seconds))
        self._last_error = ""

    @property
    def enabled(self) -> bool:
        return bool(self.dsn and psycopg is not None and dict_row is not None)

    @property
    def last_error(self) -> str:
        return self._last_error

    def initialize(self) -> bool:
        if not self.enabled:
            if not self.dsn:
                self._last_error = "POSTGRES_CACHE_DSN is not set."
            elif psycopg is None:
                self._last_error = "psycopg is not installed."
            return False

        try:
            with self._connect() as conn, conn.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS newsutd_market_cache (
                        cache_key TEXT PRIMARY KEY,
                        fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        payload JSONB NOT NULL
                    );
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_newsutd_market_cache_fetched_at
                    ON newsutd_market_cache (fetched_at DESC);
                    """
                )
            self._last_error = ""
            return True
        except Exception as exc:  # pragma: no cover - depends on local db
            self._last_error = str(exc)
            return False

    def cache_sets(self, market_sets: dict) -> bool:
        if not self.enabled:
            return False

        payload = self._normalize_payload(market_sets)
        if not self._has_any_rows(payload):
            return False

        try:
            with self._connect() as conn, conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO newsutd_market_cache (cache_key, fetched_at, payload)
                    VALUES (%s, NOW(), %s::jsonb)
                    ON CONFLICT (cache_key) DO UPDATE
                    SET fetched_at = NOW(),
                        payload = EXCLUDED.payload;
                    """,
                    (self.CACHE_KEY, json.dumps(payload)),
                )
            self._last_error = ""
            return True
        except Exception as exc:  # pragma: no cover - depends on local db
            self._last_error = str(exc)
            return False

    def fetch_sets(self) -> dict[str, list[dict]]:
        if not self.enabled:
            return {"popular": [], "volatile": [], "pullbacks": []}

        try:
            with self._connect() as conn, conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT payload, fetched_at
                    FROM newsutd_market_cache
                    WHERE cache_key = %s
                    LIMIT 1;
                    """,
                    (self.CACHE_KEY,),
                )
                row = cursor.fetchone()

            if not row:
                return {"popular": [], "volatile": [], "pullbacks": []}

            fetched_at = row.get("fetched_at")
            if isinstance(fetched_at, datetime):
                age_seconds = (datetime.now(timezone.utc) - fetched_at).total_seconds()
                if age_seconds > self.max_age_seconds:
                    return {"popular": [], "volatile": [], "pullbacks": []}

            payload = self._normalize_payload(row.get("payload", {}))
            self._last_error = ""
            return payload
        except Exception as exc:  # pragma: no cover - depends on local db
            self._last_error = str(exc)
            return {"popular": [], "volatile": [], "pullbacks": []}

    def _connect(self):
        return psycopg.connect(self.dsn, autocommit=True, row_factory=dict_row)

    @staticmethod
    def _normalize_payload(raw: dict | None) -> dict[str, list[dict]]:
        payload = raw if isinstance(raw, dict) else {}
        return {
            "popular": list(payload.get("popular", [])) if isinstance(payload.get("popular", []), list) else [],
            "volatile": list(payload.get("volatile", [])) if isinstance(payload.get("volatile", []), list) else [],
            "pullbacks": list(payload.get("pullbacks", [])) if isinstance(payload.get("pullbacks", []), list) else [],
        }

    @staticmethod
    def _has_any_rows(payload: dict[str, list[dict]]) -> bool:
        return bool(payload.get("popular") or payload.get("volatile") or payload.get("pullbacks"))
