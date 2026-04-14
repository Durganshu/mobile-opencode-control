# AGENTS.md

## Quick Start

```bash
# One-command start/stop via helper scripts (recommended)
./scripts/start-app.sh
./scripts/stop-app.sh
```

## Dev Commands

- **Backend**: `source .venv/bin/activate && python backend/run.py`
- **Frontend**: `npm --prefix frontend run dev`
- **OpenCode server**: `opencode serve --hostname 127.0.0.1 --port 4096 --cors http://localhost:5173`

## Service Order (required)

1. OpenCode server first (needs available port)
2. Backend (Flask on localhost:8080)
3. Frontend (Vite on localhost:5173)

Backend `/api/health` checks OpenCode proxy - if OpenCode isn't running, health check fails.

## Env Setup

```bash
cp .env.example .env
```

## Key Paths

- Frontend proxied API: `/api` → `http://localhost:8080`
- SQLite DB: `backend/data/app.db`
- OpenCode runtime metadata: `.runtime/opencode.port`, `.runtime/opencode.url`

## Tech Stack

- Frontend: Vite + React 18 + TypeScript
- Backend: Flask + Flask-SQLAlchemy + SQLite (default)
- DB override: Set `DATABASE_URL` in `.env` for PostgreSQL