"""Pandas analytics helpers for NewsUTD signal summaries."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from reddit_scraper import RedditPost

try:
    import pandas as pd
except Exception:  # pragma: no cover - optional dependency fallback
    pd = None


def build_signal_summary(posts: Sequence[RedditPost], group_limit: int = 6) -> dict:
    """Build aggregate signal analytics from the latest post set."""
    now_iso = datetime.now(timezone.utc).isoformat()
    capped_limit = max(3, int(group_limit))
    if not posts:
        return {
            "generated_at": now_iso,
            "totals": {
                "posts": 0,
                "average_signal_score": 0.0,
                "total_upvotes": 0,
                "total_comments": 0,
                "total_engagement": 0,
            },
            "by_subreddit": [],
            "by_sector": [],
            "top_tickers": [],
        }

    if pd is None:
        return _build_without_pandas(posts, capped_limit, now_iso)

    rows = [
        {
            "post_id": post.post_id,
            "subreddit": post.subreddit or "unknown",
            "sector": post.ai_sector or "unclassified",
            "signal_score": float(post.signal_score),
            "upvotes": int(post.score),
            "comments": int(post.comment_count),
            "engagement": int(post.score) + int(post.comment_count),
            "created_utc": float(post.created_utc),
            "tickers": list(post.ai_tickers),
        }
        for post in posts
    ]
    frame = pd.DataFrame(rows)

    totals = {
        "posts": int(frame["post_id"].count()),
        "average_signal_score": round(float(frame["signal_score"].mean()), 2),
        "total_upvotes": int(frame["upvotes"].sum()),
        "total_comments": int(frame["comments"].sum()),
        "total_engagement": int(frame["engagement"].sum()),
    }

    by_subreddit = (
        frame.groupby("subreddit", as_index=False)
        .agg(
            posts=("post_id", "count"),
            average_signal_score=("signal_score", "mean"),
            total_engagement=("engagement", "sum"),
        )
        .sort_values(by=["posts", "total_engagement"], ascending=False)
        .head(capped_limit)
    )
    by_subreddit["average_signal_score"] = by_subreddit["average_signal_score"].round(2)

    by_sector = (
        frame.groupby("sector", as_index=False)
        .agg(
            posts=("post_id", "count"),
            average_signal_score=("signal_score", "mean"),
            total_engagement=("engagement", "sum"),
        )
        .sort_values(by=["posts", "total_engagement"], ascending=False)
        .head(capped_limit)
    )
    by_sector["average_signal_score"] = by_sector["average_signal_score"].round(2)

    ticker_series = frame[["tickers"]].explode("tickers")
    ticker_series = ticker_series[ticker_series["tickers"].notna()]
    if not ticker_series.empty:
        top_tickers = (
            ticker_series["tickers"]
            .astype(str)
            .str.upper()
            .value_counts()
            .head(capped_limit)
            .reset_index()
        )
        top_tickers.columns = ["ticker", "mentions"]
        top_ticker_rows = top_tickers.to_dict(orient="records")
    else:
        top_ticker_rows = []

    return {
        "generated_at": now_iso,
        "totals": totals,
        "by_subreddit": [
            {
                "label": str(item["subreddit"]),
                "posts": int(item["posts"]),
                "average_signal_score": float(item["average_signal_score"]),
                "total_engagement": int(item["total_engagement"]),
            }
            for item in by_subreddit.to_dict(orient="records")
        ],
        "by_sector": [
            {
                "label": str(item["sector"]),
                "posts": int(item["posts"]),
                "average_signal_score": float(item["average_signal_score"]),
                "total_engagement": int(item["total_engagement"]),
            }
            for item in by_sector.to_dict(orient="records")
        ],
        "top_tickers": [
            {
                "ticker": str(item["ticker"]),
                "mentions": int(item["mentions"]),
            }
            for item in top_ticker_rows
        ],
    }


def _build_without_pandas(posts: Sequence[RedditPost], group_limit: int, now_iso: str) -> dict:
    subreddit_groups: dict[str, dict] = {}
    sector_groups: dict[str, dict] = {}
    ticker_counts: dict[str, int] = {}
    total_score = 0.0
    total_upvotes = 0
    total_comments = 0

    for post in posts:
        total_score += float(post.signal_score)
        total_upvotes += int(post.score)
        total_comments += int(post.comment_count)
        engagement = int(post.score) + int(post.comment_count)

        subreddit_key = post.subreddit or "unknown"
        sector_key = post.ai_sector or "unclassified"
        _accumulate_group(subreddit_groups, subreddit_key, float(post.signal_score), engagement)
        _accumulate_group(sector_groups, sector_key, float(post.signal_score), engagement)

        for ticker in post.ai_tickers:
            ticker_key = str(ticker or "").strip().upper()
            if ticker_key:
                ticker_counts[ticker_key] = ticker_counts.get(ticker_key, 0) + 1

    by_subreddit = _finalize_groups(subreddit_groups, group_limit)
    by_sector = _finalize_groups(sector_groups, group_limit)
    top_tickers = [
        {"ticker": ticker, "mentions": mentions}
        for ticker, mentions in sorted(
            ticker_counts.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:group_limit]
    ]

    return {
        "generated_at": now_iso,
        "totals": {
            "posts": len(posts),
            "average_signal_score": round(total_score / len(posts), 2),
            "total_upvotes": total_upvotes,
            "total_comments": total_comments,
            "total_engagement": total_upvotes + total_comments,
        },
        "by_subreddit": by_subreddit,
        "by_sector": by_sector,
        "top_tickers": top_tickers,
    }


def _accumulate_group(bucket: dict[str, dict], key: str, signal_score: float, engagement: int) -> None:
    if key not in bucket:
        bucket[key] = {"label": key, "posts": 0, "score_sum": 0.0, "total_engagement": 0}
    bucket[key]["posts"] += 1
    bucket[key]["score_sum"] += signal_score
    bucket[key]["total_engagement"] += engagement


def _finalize_groups(bucket: dict[str, dict], limit: int) -> list[dict]:
    rows = []
    for value in bucket.values():
        posts = max(1, int(value["posts"]))
        rows.append(
            {
                "label": str(value["label"]),
                "posts": posts,
                "average_signal_score": round(float(value["score_sum"]) / posts, 2),
                "total_engagement": int(value["total_engagement"]),
            }
        )
    rows.sort(key=lambda item: (item["posts"], item["total_engagement"]), reverse=True)
    return rows[:limit]
