# NewsUTD Market Signal Monitor

A real-time prototype that monitors market-relevant News activity, ranks candidate stories, and emits animated alert cards into a React dashboard.
This enhanced branch keeps the original LLM flow and adds a NewsUTD home page, Pydantic-driven typing, PostgreSQL cache support, and pandas analytics summaries.

## What It Does

- Pulls posts from selected market-focused news with PRAW
- Falls back to market/news feeds when News data is unavailable
- Keeps only recent items from a rolling 24-hour window
- Scores posts by engagement and market relevance
- Deduplicates by post ID before emitting signal events
- Streams live updates over WebSocket
- Supports a live editable subNews watchlist
- Renders News-style animated alert cards in the frontend
- Optionally enriches posts with Ollama-generated summaries, sectors, tickers, and confidence
- Adds a NewsUTD landing page (`/`) while keeping the dashboard at `/monitor`
- Adds pandas analytics endpoint at `GET /api/analytics/summary`
- Adds optional PostgreSQL cache fallback for recent signal posts

## Architecture

```text
market-signal-monitor/
  backend/
    alert_server.py
    analytics.py
    postgres_cache.py
    News_scraper.py
    schemas.py
    settings.py
    signal_engine.py
    ollama_enricher.py
    market_data.py
    market_data_server.py
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
        HomePage.jsx
      hooks/
      styles/
      assets/
  start-market-signal-monitor.ps1
```

## Backend Features

- `alert_server.py` runs a FastAPI app with REST endpoints plus `/ws/alerts`
- `News_scraper.py` fetches, normalizes, filters, and ranks News/news items
- `signal_engine.py` emits deduplicated signal events from ranked posts
- `ollama_enricher.py` adds optional AI summaries and classifications
- `settings.py` provides typed env configuration using Pydantic
- `schemas.py` defines typed API payloads and cache serialization models
- `postgres_cache.py` stores normalized posts in PostgreSQL for fallback reads
- `postgres_cache.py` also stores market mover sets in PostgreSQL for market widget fallback
- `analytics.py` builds pandas-based signal summary aggregates
- Watchlists can be updated at runtime through `POST /api/watchlist`
- Latest snapshots are available through `GET /api/signals/latest`
- Analytics summary is available through `GET /api/analytics/summary`
- Health/status is available through `GET /health`

## Frontend Features

- React + Vite dashboard UI
- NewsUTD landing page with live backend overview cards
- Live WebSocket stream with reconnect and heartbeat handling
- Animated active alert card plus historical feed
- Watchlist editing from the sidebar
- Time-range filters
- Optional assistant panel backed by the backend chat endpoint

## Quick Start

### 1. Backend Setup

Create and activate a virtual environment, then install dependencies:

```bash
pip install -r backend/requirements.txt
```

Copy the backend env template:

```bash
cp backend/.env.example backend/.env
```

Start the backend:

```bash
cd backend
uvicorn alert_server:app --reload --host 127.0.0.1 --port 8000
```

### 2. Frontend Setup

Install dependencies:

```bash
cd frontend
npm install
```

Optional: create a frontend env file if you want to override backend URLs:

```bash
cp .env.example .env
```

Start the frontend:

```bash
npm run dev
```

Open the Vite URL, typically `http://127.0.0.1:5173`.
NewsUTD home loads at `/` and the live monitor stays at `/monitor`.

## One-Command Local Launch

The repo also includes a helper script that opens backend and frontend shells and starts both services:

```powershell
.\start-market-signal-monitor.ps1
```

This expects a local virtual environment at `.venv`.

## Environment Variables

### Backend

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

### Frontend

```bash
VITE_API_BASE_URL=https://your-backend-domain
VITE_WS_URL=wss://your-backend-domain/ws/alerts
VITE_WATCHLIST_URL=https://your-backend-domain/api/watchlist
```

If frontend env vars are omitted in local development, the app will automatically target `127.0.0.1:8000`.

## API Surface

### REST

- `GET /health`
- `GET /api/signals/latest`
- `GET /api/analytics/summary`
- `POST /api/watchlist`
- `GET /api/market-movers`
- `POST /api/assistant/chat`

### WebSocket

- `GET /ws/alerts`

The socket sends:

- `hello`
- `posts_snapshot`
- `signal`
- `watchlist_updated`
- `pong`

## Scoring and Signal Flow

- News posts are filtered to a rolling 24-hour window
- Candidate posts are ranked by a weighted engagement score
- The current backend uses a News engagement weighting of `signal_score = (upvotes * 0.55) + (comments * 0.45)`
- Ranked posts are deduplicated by News post ID before signals are emitted
- The signal engine keeps a processed-ID cache so the same post is not repeatedly re-emitted

## Optional Ollama Enrichment

You can enable a local Ollama layer for post enrichment and assistant replies.

1. Install and start Ollama.
2. Pull a model, for example:

```bash
ollama pull llama3.2:latest
```

3. Enable these backend settings in `backend/.env`:

```bash
OLLAMA_ENABLED=true
OLLAMA_MODEL=llama3.2:latest
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_TIMEOUT_SECONDS=20
OLLAMA_CHAT_TIMEOUT_SECONDS=8
OLLAMA_MIN_CONFIDENCE=0.55
```

When enabled, the backend can add:

- short AI summary
- sector classification
- extracted ticker symbols
- market relevance flag
- relevance confidence
- assistant chat responses grounded in the current signal set

If Ollama is unavailable, the app falls back to the normal non-AI signal flow.

## Production Deployment

The frontend must point at a deployed persistent backend service. Do not rely on localhost in production.

Frontend env example:

```bash
VITE_API_BASE_URL=https://your-backend-domain
VITE_WS_URL=wss://your-backend-domain/ws/alerts
VITE_WATCHLIST_URL=https://your-backend-domain/api/watchlist
```

Backend deployment requirements:

- deploy as a long-running service, not serverless
- expose `/ws/alerts` with WebSocket support
- set `CORS_ALLOW_ORIGINS` to your deployed frontend origin list
- provide New credentials or enable mock mode for demo-only environments

Suitable platforms include Render, Railway, Fly.io, and DigitalOcean.

## Notes

- `USE_MOCK_DATA=true
- The frontend stores the active watchlist and filters in local storage
- This is a prototype focused on modular architecture and real-time behavior rather than production-scale ingestion
