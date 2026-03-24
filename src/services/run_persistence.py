"""SQLite persistence for run history (survives API restarts)."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

def _parse_ts(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _serialize_event(event: Any) -> Dict[str, Any]:
    return {
        "id": event.id,
        "type": event.type,
        "title": event.title,
        "detail": event.detail,
        "data": event.data,
        "timestamp": event.timestamp.isoformat(),
    }


def _deserialize_event(payload: Dict[str, Any], RunEventRecord: Any) -> Any:
    return RunEventRecord(
        id=int(payload["id"]),
        type=str(payload["type"]),
        title=str(payload["title"]),
        detail=str(payload["detail"]),
        data=dict(payload.get("data") or {}),
        timestamp=_parse_ts(str(payload["timestamp"])),
    )


def _serialize_record(record: Any) -> Dict[str, Any]:
    return {
        "id": record.id,
        "prompt": record.prompt,
        "status": record.status,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
        "final_message": record.final_message,
        "clarification_prompt": record.clarification_prompt,
        "clarification_options": list(record.clarification_options),
        "artifacts": dict(record.artifacts),
        "event_counter": record.event_counter,
        "events": [_serialize_event(event) for event in record.events],
    }


def _deserialize_record(payload: Dict[str, Any], RunEventRecord: Any, RunRecord: Any) -> Any:
    return RunRecord(
        id=str(payload["id"]),
        prompt=str(payload["prompt"]),
        status=str(payload["status"]),
        created_at=_parse_ts(str(payload["created_at"])),
        updated_at=_parse_ts(str(payload["updated_at"])),
        final_message=payload.get("final_message"),
        clarification_prompt=payload.get("clarification_prompt"),
        clarification_options=list(payload.get("clarification_options") or []),
        artifacts=dict(payload.get("artifacts") or {}),
        events=[_deserialize_event(item, RunEventRecord) for item in payload.get("events") or []],
        event_counter=int(payload.get("event_counter") or 0),
    )


def load_runs_from_sqlite(path: Path) -> Dict[str, Any]:
    from services.run_store import RunEventRecord, RunRecord

    if not path.exists():
        return {}
    conn = sqlite3.connect(path)
    try:
        cur = conn.execute("SELECT payload FROM runs")
        rows = cur.fetchall()
    finally:
        conn.close()
    out: Dict[str, Any] = {}
    for (raw,) in rows:
        payload = json.loads(raw)
        record = _deserialize_record(payload, RunEventRecord, RunRecord)
        out[record.id] = record
    return out


def persist_runs_to_sqlite(path: Path, runs: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, payload TEXT NOT NULL)",
        )
        conn.execute("DELETE FROM runs")
        for rid, record in runs.items():
            payload = json.dumps(_serialize_record(record), separators=(",", ":"))
            conn.execute(
                "INSERT INTO runs (id, payload) VALUES (?, ?)",
                (rid, payload),
            )
        conn.commit()
    finally:
        conn.close()
