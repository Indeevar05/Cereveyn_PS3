import os
from pathlib import Path

from env import load_application_dotenv, project_root
from services.run_service import RunService
from services.run_store import RunStore


def _runs_db_path() -> Path:
    load_application_dotenv()
    raw = os.getenv("CEREVYN_RUNS_DB", "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return project_root() / "data" / "cerevyn_runs.sqlite"


run_store = RunStore(persist_path=_runs_db_path())
run_service = RunService(store=run_store)
google_oauth_states: set[str] = set()
