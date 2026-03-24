# Cerevyn

Autonomous multi-step assistant: natural-language tasks, **Google GenAI (Gemini)** function calling, **Google Calendar / Meet** for events, and **AWS SES** for email. A **FastAPI** backend and **React** dashboard track runs, tool calls, and human-in-the-loop clarifications.

## Features

- **Agent loop** — Gemini calls tools (`Calendar`, `send_notification_email`) until the task completes or needs user input.
- **Run history** — Stored in **SQLite** (`data/cerevyn_runs.sqlite` by default) so runs survive API restarts.
- **Dashboard** — React + Vite + Tailwind: run list, execution timeline (with auto-scroll), results, Google OAuth status, light/dark theme.
- **Email** — SES sends multipart HTML + plain text; the model writes the main message body; the template adds a summary card and footer.

## Requirements

- Python **3.10+**
- Node **18+** (for the frontend)
- API keys: **Gemini**, optional **Google OAuth** (Calendar/Meet), optional **AWS SES** for email

## Quick start

### 1. Backend

```bash
cd /path/to/Cerevyn
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env        # fill GEMINI_API_KEY and any optional services
```

Run the API (from repo root, `PYTHONPATH` must include `src`):

```bash
PYTHONPATH=src uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

Health: `GET http://127.0.0.1:8000/health`

### 2. Frontend

```bash
cd frontend
cp .env.example .env.local   # optional: set VITE_API_BASE_URL
npm install
npm run dev
```

Open the URL Vite prints (e.g. `http://127.0.0.1:5173`). CORS allows `localhost` / `127.0.0.1` on port 5173.

### 3. Tests

```bash
pytest
```

(`pythonpath` for tests is set in `pyproject.toml`.)

## Configuration

| Variable | Purpose |
|----------|---------|
| `GEMINI_API_KEY` | Required for the agent. |
| `GEMINI_MODEL_NAME` | Model id (default in code if unset). |
| `CLIENT_ID`, `CLIENT_SECRET`, `GOOGLE_OAUTH_REDIRECT_URI` | Google OAuth for Calendar/Meet; redirect must match the GCP console. |
| `GOOGLE_OAUTH_TOKEN_JSON` | Where OAuth tokens are stored (default under `.tokens/`). |
| `CEREVYN_RUNS_DB` | Optional absolute path to SQLite DB; default `data/cerevyn_runs.sqlite`. |
| `AWS_*`, `AWS_SES_SENDER_EMAIL` | SES for outbound mail. |

Frontend: `VITE_API_BASE_URL` (see `frontend/.env.example`) points the SPA at the API.

## Project layout

```
Cerevyn/
├── src/                    # Python package (on PYTHONPATH)
│   ├── api/                # FastAPI app, routes (runs, auth)
│   ├── services/           # Run store, SQLite persistence, run service
│   ├── agent_core.py       # Gemini loop + tool execution
│   ├── calendar_manager.py # Calendar + Meet + OAuth
│   └── notification_manager.py
├── tests/
├── frontend/               # React SPA
├── data/                   # SQLite DB (gitignored; .gitkeep kept)
└── pyproject.toml
```

## Architecture (short)

1. **POST /runs** creates a run; optional clarification if the prompt is ambiguous.
2. A **background thread** runs `run_agent_session`: Gemini ↔ tools; events appended to the run.
3. **GET /runs**, **GET /runs/{id}**, **GET /runs/{id}/events** sync the UI.

## API overview

- `GET /health` — Liveness.
- `GET /runs`, `POST /runs` — List / start runs.
- `GET /runs/{id}`, `GET /runs/{id}/events` — Run state and incremental events.
- `POST /runs/{id}/respond` — User reply when status is `waiting_for_user`.
- Google OAuth routes under `/auth/google/...` (see `src/api/routes/auth.py`).

## License / status

Internal / project work (PS3-style agent). Adjust `pyproject.toml` metadata if you publish.
