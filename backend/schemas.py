"""Pydantic models used across API payloads and cached signal data."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from reddit_scraper import RedditPost


class WatchlistPayload(BaseModel):
    subreddits: list[str]

    @field_validator("subreddits")
    @classmethod
    def _normalize_subreddits(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for value in values:
            cleaned = str(value or "").strip().replace("r/", "").lower()
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            normalized.append(cleaned)
            if len(normalized) >= 20:
                break
        return normalized


class AssistantMessagePayload(BaseModel):
    role: str
    content: str


class AssistantChatPayload(BaseModel):
    message: str
    history: list[AssistantMessagePayload] = Field(default_factory=list)


class SerializedPost(BaseModel):
    id: str
    title: str
    body_text: str = ""
    subreddit: str
    author: str
    username: str
    upvotes: int = 0
    comments: int = 0
    comment_count: int = 0
    thumbnail_url: str | None = None
    image: str | None = None
    article_link: str = ""
    permalink: str = ""
    post_url: str = ""
    created_utc: float = 0.0
    timestamp: str = ""
    signal_score: float = 0.0
    ai_summary: str = ""
    ai_sector: str = ""
    ai_reason: str = ""
    ai_confidence: float = 0.0
    ai_market_relevant: bool = True
    ai_tickers: list[str] = Field(default_factory=list)

    @classmethod
    def from_post(cls, post: RedditPost) -> "SerializedPost":
        return cls(
            id=post.post_id,
            title=post.title,
            body_text=post.body_text,
            subreddit=post.subreddit,
            author=post.username,
            username=post.username,
            upvotes=post.score,
            comments=post.comment_count,
            comment_count=post.comment_count,
            thumbnail_url=post.thumbnail_url,
            image=post.thumbnail_url,
            article_link=post.article_link,
            permalink=post.permalink,
            post_url=post.post_url,
            created_utc=post.created_utc,
            timestamp=post.created_at_iso,
            signal_score=round(post.signal_score, 2),
            ai_summary=post.ai_summary,
            ai_sector=post.ai_sector,
            ai_reason=post.ai_reason,
            ai_confidence=round(post.ai_confidence, 3),
            ai_market_relevant=post.ai_market_relevant,
            ai_tickers=list(post.ai_tickers),
        )

    def to_post(self) -> RedditPost:
        return RedditPost(
            post_id=self.id,
            title=self.title,
            body_text=self.body_text,
            subreddit=self.subreddit,
            username=self.author or self.username or "unknown",
            score=int(self.upvotes),
            comment_count=int(self.comment_count or self.comments),
            thumbnail_url=self.thumbnail_url or self.image,
            article_link=self.article_link,
            permalink=self.permalink,
            post_url=self.post_url,
            created_utc=float(self.created_utc),
            created_at_iso=self.timestamp,
            signal_score=float(self.signal_score),
            ai_summary=self.ai_summary,
            ai_sector=self.ai_sector,
            ai_reason=self.ai_reason,
            ai_confidence=float(self.ai_confidence),
            ai_market_relevant=bool(self.ai_market_relevant),
            ai_tickers=tuple(self.ai_tickers),
        )


class LatestSignalsResponse(BaseModel):
    posts: list[SerializedPost]
    error: str = ""
    subreddits: list[str] = Field(default_factory=list)
    cache_source: str = "live"


class HealthResponse(BaseModel):
    app_name: str
    status: str
    use_mock_data: bool
    ollama_enabled: bool
    ollama_model: str
    reddit_error: str
    subreddits: list[str]
    top_posts_limit: int
    connected_clients: int
    posts_cached: int
    cache_source: str
    postgres_cache_enabled: bool


class AnalyticsGroupRow(BaseModel):
    label: str
    posts: int
    average_signal_score: float
    total_engagement: int


class AnalyticsTickerRow(BaseModel):
    ticker: str
    mentions: int


class AnalyticsSummaryResponse(BaseModel):
    tracked_subreddits: list[str] = Field(default_factory=list)
    generated_at: str
    cache_source: str
    totals: dict[str, Any]
    by_subreddit: list[AnalyticsGroupRow]
    by_sector: list[AnalyticsGroupRow]
    top_tickers: list[AnalyticsTickerRow]
