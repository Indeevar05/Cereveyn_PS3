# Cerevyn SaaS Platform

**Cerevyn** is an enterprise-grade, autonomous multi-step AI assistant built on a modern SaaS architecture. Leveraging **Google GenAI (Gemini)** for intelligent function calling and **FastAPI** for high-performance backend routing, Cerevyn seamlessly handles natural-language tasks, event scheduling, and automated communication workflows.

---

## 🏗️ SaaS Level Architecture

Cerevyn is designed with a scalable, modular architecture that ensures robust performance and seamless user experiences:

### 1. Advanced DOM Control & Dynamic UI
The sophisticated **React + Vite** frontend architecture **takes full control of the DOM** to deliver a premium, responsive Dashboard. 
- **Real-Time Rendering:** Dynamically updates the UI with live execution timelines, status badges, and human-in-the-loop prompts.
- **Seamless State Management:** Ensures smooth transitions and instant updates without page reloads, providing a desktop-app-like experience in the browser.

### 2. Comprehensive Process Capture
The API layer robustly **captures the entire agent execution process**:
- **Execution Telemetry:** Every step of the agent's thought process, tool requests, and human interactions are captured and persistently stored.
- **SQLite Persistence:** Run history survives API restarts and scales effortlessly (`data/cerevyn_runs.sqlite`), allowing for detailed auditing and process playback.
- **Background Processing:** Agent loops run asynchronously, ensuring the main thread remains unblocked for high-throughput API requests.

### 3. Intelligent Email Messaging
Cerevyn integrates deep **AWS SES** capabilities for enterprise email delivery:
- **Automated Dispatches:** Automatically dispatches professional email messages and Google Meet invites exactly when the agent determines it is necessary.
- **Rich Multipart Messaging:** Delivers AI-generated, highly contextual plain-text bodies wrapped in a beautifully formatted HTML styling, complete with meeting summary cards and footers.

---

## 🚀 Quick Start Guide

### Prerequisites
- Python **3.10+**
- Node.js **18+**
- API Keys: **Gemini API**, **Google OAuth** (Calendar/Meet), and **AWS SES**.

### Backend Setup
```bash
cd /path/to/Cerevyn
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env        # Configure GEMINI_API_KEY and AWS credentials
```

**Run the API Server:**
```bash
PYTHONPATH=src uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```
*Health Check: `GET http://127.0.0.1:8000/health`*

### Frontend Setup
```bash
cd frontend
cp .env.example .env.local   # Configure VITE_API_BASE_URL
npm install
npm run dev
```
*The Dashboard will be available at `http://127.0.0.1:5173`.*

---

## ⚙️ Core Configuration

Control the SaaS environment via `.env` files:

| Environment Variable | Description |
|----------------------|-------------|
| `GEMINI_API_KEY` | **Required.** Authenticates the core LLM engine. |
| `GEMINI_MODEL_NAME` | Specifies the model version (defaults to `gemini-3.1-pro-preview`). |
| `CLIENT_ID` & `SECRET` | Google OAuth credentials for Google Calendar and Meet integrations. |
| `CEREVYN_RUNS_DB` | Absolute path for SQLite persistence tracking. |
| `AWS_SES_SENDER_EMAIL`| Authorized email address for outbound automated communications. |

---

## 🧪 Testing

Run continuous integration tests easily:
```bash
pytest
```

## 📄 License & Status
Internal SaaS Project (PS3-style autonomous agent). 
*Designed for high availability, robust process capturing, and intelligent DOM UI control.*
