# NewsUTD: Market Signal Monitor

NewsUTD is a real-time market intelligence platform built to catch narrative shifts before price fully reacts.

It ingests live social/news flow, ranks what matters, streams alerts over WebSockets, and gives operators an AI-assisted control surface for fast decision support.

## Why This Matters

Markets move on narrative velocity, not just raw headlines.

NewsUTD is designed to answer one question quickly:

**What is changing right now, and how confident should we be?**

This project focuses on:

- Faster signal detection from noisy sources
- Clear prioritization of what to watch next
- Resilient operation during API/source interruptions
- A production-lean architecture that can evolve into a full intelligence product

## What NewsUTD Does

- Streams live signal events to a React dashboard in near real time
- Scores and ranks incoming items by market relevance and engagement
- Keeps an active watchlist of themes/sectors and updates state live
- Exposes analytics summaries using pandas for quick signal rollups
- Uses PostgreSQL cache fallback when live sources degrade
- Preserves LLM-based interpretation (optional Ollama enrichment + assistant chat)
- Provides a landing/home experience (`/`) and a live monitor workspace (`/monitor`)

## Core Architecture

```text
market-signal-monitor/
  backend/
    alert_server.py          # FastAPI app + websocket broadcaster + orchestration
    signal_engine.py         # ranking + dedupe + signal emission
    reddit_scraper.py        # source ingestion + normalization + filtering
    ollama_enricher.py       # optional local LLM enrichment and chat context
    analytics.py             # pandas summaries and grouped metrics
    postgres_cache.py        # Postgres fallback cache for posts + market movers
    market_data.py           # market pulse retrieval + normalization
    market_data_server.py    # market data API surface
    settings.py              # Pydantic environment/config loader
    schemas.py               # Pydantic API and serialization models
  frontend/
    src/
      App.jsx
      DashboardApp.jsx
      components/
      hooks/
      styles/
  start-market-signal-monitor.ps1
  run-newsutd.ps1
  vercel.json
```

## Tech Stack

- **Backend:** FastAPI, Uvicorn, Pydantic, pandas, psycopg
- **Frontend:** React 18, Vite
- **Realtime:** WebSocket stream at `/ws/alerts`
- **Data resilience:** PostgreSQL caching/fallback
- **AI layer (optional):** Ollama for classification/summarization/chat

## Product Highlights

1. **Realtime Signal Flow**
- Live snapshots + incremental signal events
- Reset/stream behavior tuned for cleaner sequencing
- Deduplicated emission to avoid noisy repeats

2. **NewsUTD UX**
- Distinct home page branding and system overview
- Focused monitoring workspace for active signal operations
- Improved layout consistency and dark SaaS visual system

3. **AI Assistant Dock**
- Context-grounded responses from current signal state
- Better message usability and contained scroll behavior in chat

4. **Market Pulse Reliability**
- Live + cached source status awareness
- Failover-friendly handling for market data interruptions

5. **Typed, Safer Backend**
- Pydantic settings and schemas across key API flows
- Cleaner contracts between ingestion, caching, analytics, and UI

## Run Locally

## 1) Backend

```bash
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
cd backend
uvicorn alert_server:app --reload --host 127.0.0.1 --port 8000
```

## 2) Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open `http://127.0.0.1:5173`

- Home: `/`
- Monitor: `/monitor`

## One-command startup (PowerShell)

```powershell
.\start-market-signal-monitor.ps1
```

## Environment Variables

## Backend (`backend/.env`)

```bash
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USER_AGENT=market-signal-monitor/0.1 by local_user

SUBREDDITS=stocks,investing,economics,cryptocurrency
POSTS_PER_SUBREDDIT=200
TOP_POSTS_LIMIT=20
MAX_PROCESSED_POSTS=10000
POLL_SECONDS=8
REDDIT_FETCH_CACHE_SECONDS=20
USE_MOCK_DATA=false

OLLAMA_ENABLED=false
OLLAMA_MODEL=llama3.2:latest
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_TIMEOUT_SECONDS=20
OLLAMA_CHAT_TIMEOUT_SECONDS=8
OLLAMA_MIN_CONFIDENCE=0.55
MARKET_CHAT_TIMEOUT_SECONDS=1.5

POSTGRES_CACHE_ENABLED=false
POSTGRES_CACHE_DSN=postgresql://postgres:postgres@127.0.0.1:5432/newsutd_cache
POSTGRES_CACHE_MAX_ROWS=5000
POSTGRES_CACHE_READ_LIMIT=120
MARKET_CACHE_MAX_AGE_SECONDS=21600
PANDAS_GROUP_LIMIT=6

CORS_ALLOW_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
```

## Frontend (`frontend/.env`)

```bash
VITE_API_BASE_URL=https://your-backend-domain
VITE_WS_URL=wss://your-backend-domain/ws/alerts
VITE_WATCHLIST_URL=https://your-backend-domain/api/watchlist
```

If omitted locally, frontend auto-targets `127.0.0.1:8000`.

## API Surface

## REST

- `GET /health`
- `GET /api/signals/latest`
- `GET /api/analytics/summary`
- `POST /api/watchlist`
- `GET /api/subreddits/search?q=stocks`
- `GET /api/market-movers`
- `POST /api/assistant/chat`

## WebSocket

- `GET /ws/alerts`

Events:

- `hello`
- `posts_snapshot`
- `signal`
- `watchlist_updated`
- `pong`

## Deployment Notes

`vercel.json` is configured for frontend SPA deployment:

- Build: `frontend` with Vite
- Output: `frontend/dist`
- Route rewrites to `index.html` so `/monitor` works

Deploy backend on a persistent service (Render, Railway, Fly.io, DigitalOcean, etc.) and point frontend `VITE_*` variables to that backend URL.

## Current Focus

NewsUTD is currently optimized for high-speed prototyping and operator workflows:

- capture narrative momentum quickly
- maintain resilient signal continuity
- keep AI context actionable, not verbose

If you are extending this project, the best next upgrades are multi-source ingestion expansion, historical signal storage, and strategy-grade alerting rules.
