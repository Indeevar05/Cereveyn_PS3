"""Load repository `.env` from a stable path so `GEMINI_API_KEY` works regardless of process cwd."""

from pathlib import Path

from dotenv import load_dotenv

# src/env.py -> project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_application_dotenv() -> None:
    load_dotenv(_PROJECT_ROOT / ".env", override=False)


def project_root() -> Path:
    return _PROJECT_ROOT
