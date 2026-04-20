# NewsUTD Market Signal Monitor

NewsUTD is a real-time market signal dashboard that combines live social/news narrative flow, typed backend services, local AI interpretation, and a modern React monitor UI.

This version keeps the original LLM-assisted workflow and adds:

- NewsUTD home experience (`/`) plus live monitor (`/monitor`)
- Pydantic settings and response schemas
- PostgreSQL cache fallback for signal and market data
- pandas analytics summaries for fast signal rollups

## Stack

- Backend: FastAPI, Uvicorn, Pydantic, pandas, psycopg
- Frontend: React 18 + Vite
- Realtime: WebSocket alert stream (`/ws/alerts`)
- Optional AI: Ollama enrichment and chat assistant
- Optional market source: Yahoo Finance quote snapshot fallback pipeline
- Optional cache: PostgreSQL (`POSTGRES_CACHE_ENABLED=true`)

## Project Layout

```text
market-signal-monitor/
  backend/
    alert_server.py
    analytics.py
    market_data.py
    market_data_server.py
    ollama_enricher.py
    postgres_cache.py
    reddit_scraper.py
    schemas.py
    settings.py
    signal_engine.py
    requirements.txt
    .env.example
  frontend/
    index.html
    package.json
    vite.config.js
    .env.example
    src/
      App.jsx
      DashboardApp.jsx
      main.jsx
      components/
      hooks/
      styles/
      assets/
  .vscode/
  start-market-signal-monitor.ps1
  run-newsutd.ps1
  vercel.json
```

## Backend Highlights

- `alert_server.py`
  - Primary API service and WebSocket broadcaster
  - Maintains watchlist state, signal stream, health, and assistant routes
  - Handles reset/stream sequencing and snapshot synchronization
- `signal_engine.py`
  - Scores/deduplicates incoming posts before emission
  - Maintains processed-ID cache to prevent duplicate signals
- `settings.py`
  - Central typed environment loading (Pydantic)
- `schemas.py`
  - Typed payload models for endpoints, watchlist updates, and cached objects
- `analytics.py`
  - pandas aggregation pipeline for signal summary metrics
- `postgres_cache.py`
  - Postgres-backed fallback cache for posts and market movers
- `market_data.py` + `market_data_server.py`
  - Market pulse fetch and normalization pipeline with cache-source awareness
- `ollama_enricher.py`
  - Optional local LLM classification/summarization for signals and assistant chat

## Frontend Highlights

- `/` Home screen with NewsUTD branding and system status cues
- `/monitor` dashboard with:
  - Live signal feed and active alert
  - Watchlist controls and filters
  - Market pulse panel (live/cached status)
  - Signal AI quick chat panel with constrained scroll region
- Responsive layout and dark SaaS styling consistency across pages

## Local Setup

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

## One-command run (Windows PowerShell)

```powershell
.\start-market-signal-monitor.ps1
```

## Environment Variables

## Backend (`backend/.env`)

```bash
# Social/news signal ingestion
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

# Local LLM
OLLAMA_ENABLED=false
OLLAMA_MODEL=llama3.2:latest
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_TIMEOUT_SECONDS=20
OLLAMA_CHAT_TIMEOUT_SECONDS=8
OLLAMA_MIN_CONFIDENCE=0.55
MARKET_CHAT_TIMEOUT_SECONDS=1.5

# Postgres cache
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

If omitted locally, frontend falls back to `127.0.0.1:8000`.

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

## Vercel (frontend)

The repository includes a root `vercel.json` configured to:

- build frontend with Vite from `frontend/`
- publish `frontend/dist`
- rewrite all routes to `index.html` for SPA routing (`/monitor` works)

Deploy backend separately on a persistent service (Render/Railway/Fly.io/etc.) and set frontend `VITE_*` URLs to that backend.

## Notes

- Use `USE_MOCK_DATA=true` for UI demos without external credentials.
- PostgreSQL cache can serve stale-but-recent data during source/API interruptions.
- This project is optimized for fast prototyping, narrative detection, and real-time operator workflows.
