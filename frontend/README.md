# FALCON Rescue Dashboard

React + Vite frontend for the existing FastAPI backend.

Backend: http://127.0.0.1:8000
WebSocket: ws://127.0.0.1:8000/ws

Run:
1. cd frontend
2. npm install
3. npm run dev

The video panel is intentionally a placeholder because the current backend has no video-stream endpoint. GPS is displayed only when real coordinates are supplied. The Falcon chat UI is prepared for a future POST /api/ask endpoint.
