# Market Signal Monitor
Market Signal Monitor is a real-time market news website that surfaces breaking financial and macro signals in a live React dashboard.

The project combines a Python backend and React frontend to ingest recent market-moving stories, rank and deduplicate them, and stream them to the UI over WebSocket as animated alert cards.

Features
Real-time market and news signal monitoring
Live WebSocket streaming from backend to frontend
Animated alert cards and rolling signal feed
Signal ranking and deduplication
Optional AI enrichment with Ollama
Mock-data mode for local UI testing
Stack
Frontend: React, Vite
Backend: Python, FastAPI, Uvicorn, WebSockets
Optional AI: Ollama
How It Works
The backend collects recent market-relevant news signals.
Signals are filtered, ranked, and deduplicated.
Fresh events are broadcast over /ws/alerts.
The frontend website listens in real time and renders them as live alert cards.
Local Development
Start the backend:

pip install -r backend/requirements.txt
cd backend
uvicorn alert_server:app --reload --host 127.0.0.1 --port 8000
Start the frontend:

cd frontend
npm install
npm run dev
Then open the local Vite URL in your browser, typically http://127.0.0.1:5173.

Optional AI Enrichment
If Ollama is enabled, the backend can add short summaries, sector tags, ticker extraction, and assistant-style responses based on the current signal set.

Production
For production, the frontend website should point to a deployed persistent backend service with WebSocket support. Do not rely on localhost in production.

Notes
USE_MOCK_DATA=true is useful for demos and frontend testing
This project is a prototype focused on modular architecture and real-time behavior
The UI is designed to feel like a live market/news signal desk
