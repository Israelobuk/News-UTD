"""Shared market data fetcher for live mover charts."""

from __future__ import annotations

import json
import math
import os
import random
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import ProxyHandler, Request, build_opener

from postgres_cache import PostgresMarketCache

MARKET_UNIVERSE_SYMBOLS = [
    symbol.strip().upper()
    for symbol in os.getenv(
        "MARKET_UNIVERSE_SYMBOLS",
        (
            "NVDA,TSLA,AAPL,MSFT,AMZN,META,GOOGL,AMD,NFLX,PLTR,SMCI,AVGO,INTC,TSM,ARM,"
            "COIN,MSTR,HOOD,RDDT,UBER,CRM,ORCL,ADBE,PYPL,SQ,JPM,BAC,GS,XOM,CVX,SLB,"
            "LLY,NVO,MRNA,RIVN,SOFI,SNOW,PANW,CRWD,SERV,TTD,SHOP"
        ),
    ).split(",")
    if symbol.strip()
]
POPULAR_MARKET_SYMBOLS = [
    symbol.strip().upper()
    for symbol in os.getenv(
        "POPULAR_MARKET_SYMBOLS",
        "NVDA,MSFT,AAPL,AMZN,META,GOOGL,TSLA,AMD,PLTR,AVGO,TSM,COIN,MSTR,JPM,XOM,LLY",
    ).split(",")
    if symbol.strip()
]
MARKET_DATA_TTL_SECONDS = int(os.getenv("MARKET_DATA_TTL_SECONDS", "120"))
MIN_WINDOW_POINTS = int(os.getenv("MARKET_MIN_WINDOW_POINTS", "24"))
MIN_WINDOW_SPAN_SECONDS = int(os.getenv("MARKET_MIN_WINDOW_SPAN_SECONDS", str(4 * 60 * 60)))
TRAILING_SESSION_POINTS = int(os.getenv("MARKET_TRAILING_SESSION_POINTS", "78"))
MARKET_DISPLAY_LIMIT = int(os.getenv("MARKET_DISPLAY_LIMIT", "9"))
VOLATILITY_POOL_SIZE = int(os.getenv("MARKET_VOLATILITY_POOL_SIZE", "18"))
MARKET_CACHE_MAX_AGE_SECONDS = int(os.getenv("MARKET_CACHE_MAX_AGE_SECONDS", str(6 * 60 * 60)))

_market_cache: dict[str, object] = {
    "fetched_at": 0.0,
    "data": {"popular": [], "volatile": [], "pullbacks": []},
}
_market_http = build_opener(ProxyHandler({}))
_market_cache_source = "live"
_market_postgres_cache: PostgresMarketCache | None = None
_market_postgres_init_attempted = False


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _set_market_cache_source(source: str) -> None:
    global _market_cache_source
    _market_cache_source = str(source or "live").strip().lower() or "live"


def get_market_cache_source() -> str:
    return _market_cache_source


def _has_market_rows(data: dict[str, list[dict]]) -> bool:
    return bool(data.get("popular") or data.get("volatile") or data.get("pullbacks"))


def _clone_market_sets(data: dict[str, list[dict]]) -> dict[str, list[dict]]:
    return {
        "popular": list(data.get("popular", [])),
        "volatile": list(data.get("volatile", [])),
        "pullbacks": list(data.get("pullbacks", [])),
    }


def _initialize_postgres_market_cache_if_needed() -> None:
    global _market_postgres_cache, _market_postgres_init_attempted
    if _market_postgres_init_attempted:
        return

    _market_postgres_init_attempted = True
    dsn = os.getenv("POSTGRES_CACHE_DSN", "").strip()
    enabled = _parse_bool(os.getenv("POSTGRES_CACHE_ENABLED"), default=bool(dsn))
    if not enabled or not dsn:
        return

    cache = PostgresMarketCache(dsn, max_age_seconds=MARKET_CACHE_MAX_AGE_SECONDS)
    if cache.initialize():
        _market_postgres_cache = cache


def compress_points(points: list[float], target_size: int = 72) -> list[float]:
    if len(points) <= target_size:
        return points

    compressed: list[float] = []
    for index in range(target_size):
        position = round(index * (len(points) - 1) / (target_size - 1))
        compressed.append(points[position])
    return compressed


def select_chart_points(all_pairs: list[tuple[int, float]]) -> list[float]:
    if not all_pairs:
        return []

    cutoff = int(time.time()) - 86400
    recent_pairs = [
        (timestamp, close)
        for timestamp, close in all_pairs
        if timestamp >= cutoff
    ]

    if recent_pairs:
        recent_span = recent_pairs[-1][0] - recent_pairs[0][0]
        if len(recent_pairs) >= MIN_WINDOW_POINTS and recent_span >= MIN_WINDOW_SPAN_SECONDS:
            return [close for _, close in recent_pairs]

    trailing_pairs = all_pairs[-TRAILING_SESSION_POINTS:]
    return [close for _, close in trailing_pairs]


def _to_finite_float(value: object) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def _fetch_quote_snapshot(symbols: list[str], user_agent: str) -> dict[str, dict[str, float]]:
    if not symbols:
        return {}

    symbols_param = ",".join(symbols)
    url = (
        "https://query1.finance.yahoo.com/v7/finance/quote"
        f"?symbols={quote(symbols_param)}"
    )
    request = Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "application/json",
        },
    )

    try:
        with _market_http.open(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return {}

    rows = ((payload.get("quoteResponse") or {}).get("result") or [])
    snapshot: dict[str, dict[str, float]] = {}
    for row in rows:
        symbol = str(row.get("symbol", "")).strip().upper()
        if not symbol:
            continue

        last_price = _to_finite_float(row.get("regularMarketPrice"))
        previous_close = _to_finite_float(row.get("regularMarketPreviousClose"))
        change_percent = _to_finite_float(row.get("regularMarketChangePercent"))

        snapshot[symbol] = {
            "last_price": last_price,
            "previous_close": previous_close,
            "change_percent": change_percent,
        }

    return snapshot


def build_market_entry(
    symbol: str,
    points: list[float],
    previous_close: float,
    last_price: float,
    change_percent_override: float | None = None,
) -> dict:
    point_min = min(points)
    point_max = max(points)
    if change_percent_override is not None:
        change_percent = change_percent_override
    else:
        change_percent = ((float(last_price) - float(previous_close)) / float(previous_close)) * 100
    volatility_percent = ((float(point_max) - float(point_min)) / float(previous_close)) * 100

    return {
        "ticker": symbol,
        "change": round(change_percent, 2),
        "volatility": round(volatility_percent, 2),
        "points": compress_points(points, 72),
        "previous_close": round(float(previous_close), 4),
        "last_price": round(float(last_price), 4),
    }


def fetch_market_sets() -> dict[str, list[dict]]:
    _initialize_postgres_market_cache_if_needed()

    cached_data = _market_cache.get("data", {"popular": [], "volatile": [], "pullbacks": []})
    cached_at = float(_market_cache.get("fetched_at", 0.0))
    if (
        isinstance(cached_data, dict)
        and _has_market_rows(cached_data)
        and (time.time() - cached_at) < MARKET_DATA_TTL_SECONDS
    ):
        _set_market_cache_source("memory")
        return _clone_market_sets(cached_data)

    results: list[dict] = []
    user_agent = os.getenv("REDDIT_USER_AGENT", "market-signal-monitor/0.1")
    quote_snapshot = _fetch_quote_snapshot(MARKET_UNIVERSE_SYMBOLS, user_agent)

    for symbol in MARKET_UNIVERSE_SYMBOLS:
        url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol)}"
            "?interval=5m&range=2d&includePrePost=true"
        )
        request = Request(
            url,
            headers={
                "User-Agent": user_agent,
                "Accept": "application/json",
            },
        )

        try:
            with _market_http.open(request, timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
            continue

        chart_result = (payload.get("chart") or {}).get("result") or []
        if not chart_result:
            continue

        chart = chart_result[0]
        meta = chart.get("meta") or {}
        timestamps = chart.get("timestamp") or []
        quotes = ((chart.get("indicators") or {}).get("quote") or [{}])[0]
        closes = quotes.get("close") or []
        all_pairs = [
            (int(timestamp), float(close))
            for timestamp, close in zip(timestamps, closes)
            if timestamp is not None and close is not None
        ]
        points = select_chart_points(all_pairs)
        if len(points) < 2:
            continue

        quote_row = quote_snapshot.get(symbol, {})
        quote_previous_close = quote_row.get("previous_close")
        quote_last_price = quote_row.get("last_price")
        quote_change_percent = quote_row.get("change_percent")

        previous_close = (
            quote_previous_close
            if quote_previous_close is not None
            else _to_finite_float(meta.get("regularMarketPreviousClose"))
        )
        if previous_close is None:
            previous_close = _to_finite_float(meta.get("chartPreviousClose"))
        if previous_close is None:
            previous_close = _to_finite_float(meta.get("previousClose"))
        if previous_close is None and points:
            previous_close = _to_finite_float(points[0])

        last_price = (
            quote_last_price
            if quote_last_price is not None
            else _to_finite_float(meta.get("regularMarketPrice"))
        )
        if last_price is None and points:
            last_price = _to_finite_float(points[-1])

        if previous_close is None or previous_close <= 0 or last_price is None:
            continue

        results.append(
            build_market_entry(
                symbol,
                points,
                float(previous_close),
                float(last_price),
                change_percent_override=(
                    float(quote_change_percent)
                    if quote_change_percent is not None
                    else None
                ),
            )
        )

    if results:
        entries_by_symbol = {str(item.get("ticker", "")): item for item in results}
        popular = [
            entries_by_symbol[symbol]
            for symbol in POPULAR_MARKET_SYMBOLS
            if symbol in entries_by_symbol
        ][:MARKET_DISPLAY_LIMIT]

        volatile_ranked = sorted(
            results,
            key=lambda item: (float(item.get("volatility", 0)), abs(float(item.get("change", 0)))),
            reverse=True,
        )
        volatile_pool = volatile_ranked[: max(MARKET_DISPLAY_LIMIT, VOLATILITY_POOL_SIZE)]
        randomizer = random.Random(int(time.time() // MARKET_DATA_TTL_SECONDS))
        randomizer.shuffle(volatile_pool)
        volatile = volatile_pool[:MARKET_DISPLAY_LIMIT]

        pullback_candidates = [
            item for item in results if float(item.get("change", 0)) < 0
        ]
        pullbacks = sorted(
            pullback_candidates if pullback_candidates else results,
            key=lambda item: (float(item.get("change", 0)), -float(item.get("volatility", 0))),
        )[:MARKET_DISPLAY_LIMIT]

        next_data = {
            "popular": popular,
            "volatile": volatile,
            "pullbacks": pullbacks,
        }
        _market_cache["fetched_at"] = time.time()
        _market_cache["data"] = next_data
        _set_market_cache_source("live")
        if _market_postgres_cache is not None:
            _market_postgres_cache.cache_sets(next_data)
        return next_data

    if isinstance(cached_data, dict) and _has_market_rows(cached_data):
        _set_market_cache_source("memory")
        return _clone_market_sets(cached_data)

    if _market_postgres_cache is not None:
        postgres_data = _market_postgres_cache.fetch_sets()
        if _has_market_rows(postgres_data):
            _market_cache["fetched_at"] = time.time()
            _market_cache["data"] = _clone_market_sets(postgres_data)
            _set_market_cache_source("postgres")
            return _clone_market_sets(postgres_data)

    _set_market_cache_source("unavailable")
    return {"popular": [], "volatile": [], "pullbacks": []}


def fetch_market_movers() -> list[dict]:
    return fetch_market_sets().get("popular", [])
