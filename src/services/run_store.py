from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional
from uuid import uuid4

from schemas.runs import RunEventModel, RunStateModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def make_json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): make_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [make_json_safe(item) for item in value]
    if hasattr(value, "items"):
        try:
            return {str(key): make_json_safe(item) for key, item in value.items()}
        except Exception:
            pass
    if hasattr(value, "__iter__") and not isinstance(value, (bytes, bytearray)):
        try:
            return [make_json_safe(item) for item in value]
        except Exception:
            pass
    return str(value)


@dataclass
class RunEventRecord:
    id: int
    type: str
    title: str
    detail: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=utc_now)


@dataclass
class RunRecord:
    id: str
    prompt: str
    status: str
    created_at: datetime
    updated_at: datetime
    final_message: Optional[str] = None
    clarification_prompt: Optional[str] = None
    clarification_options: List[str] = field(default_factory=list)
    artifacts: Dict[str, Any] = field(default_factory=dict)
    events: List[RunEventRecord] = field(default_factory=list)
    event_counter: int = 0


class RunStore:
    def __init__(self, *, persist_path: Optional[Path] = None) -> None:
        self._lock = Lock()
        self._persist_path = persist_path
        self._runs: Dict[str, RunRecord] = {}
        if self._persist_path:
            from services.run_persistence import load_runs_from_sqlite

            self._runs = load_runs_from_sqlite(self._persist_path)

    def _persist_unlocked(self) -> None:
        if not self._persist_path:
            return
        from services.run_persistence import persist_runs_to_sqlite

        persist_runs_to_sqlite(self._persist_path, self._runs)

    def create_run(self, prompt: str, status: str = "running") -> RunRecord:
        with self._lock:
            now = utc_now()
            record = RunRecord(
                id=uuid4().hex,
                prompt=prompt,
                status=status,
                created_at=now,
                updated_at=now,
            )
            self._runs[record.id] = record
            self._persist_unlocked()
            return record

    def list_runs(self) -> List[RunStateModel]:
        with self._lock:
            runs = sorted(self._runs.values(), key=lambda item: item.updated_at, reverse=True)
            return [self._to_model(record) for record in runs]

    def get_run_record(self, run_id: str) -> RunRecord:
        with self._lock:
            if run_id not in self._runs:
                raise KeyError(run_id)
            return self._runs[run_id]

    def get_run(self, run_id: str) -> RunStateModel:
        with self._lock:
            if run_id not in self._runs:
                raise KeyError(run_id)
            return self._to_model(self._runs[run_id])

    def append_event(
        self,
        run_id: str,
        event_type: str,
        title: str,
        detail: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> RunEventModel:
        with self._lock:
            record = self._runs[run_id]
            record.event_counter += 1
            event = RunEventRecord(
                id=record.event_counter,
                type=event_type,
                title=title,
                detail=detail,
                data=make_json_safe(data or {}),
            )
            record.events.append(event)
            record.updated_at = utc_now()
            self._persist_unlocked()
            return self._event_to_model(event)

    def list_events(self, run_id: str, since: int = 0) -> List[RunEventModel]:
        with self._lock:
            record = self._runs[run_id]
            return [
                self._event_to_model(event)
                for event in record.events
                if event.id > since
            ]

    def update_status(self, run_id: str, status: str) -> None:
        with self._lock:
            record = self._runs[run_id]
            record.status = status
            record.updated_at = utc_now()
            self._persist_unlocked()

    def set_waiting(
        self,
        run_id: str,
        prompt: str,
        options: Optional[List[str]] = None,
    ) -> None:
        with self._lock:
            record = self._runs[run_id]
            record.status = "waiting_for_user"
            record.clarification_prompt = prompt
            record.clarification_options = list(options or [])
            record.updated_at = utc_now()
            self._persist_unlocked()

    def clear_waiting(self, run_id: str) -> None:
        with self._lock:
            record = self._runs[run_id]
            record.clarification_prompt = None
            record.clarification_options = []
            record.updated_at = utc_now()
            self._persist_unlocked()

    def merge_artifacts(self, run_id: str, artifacts: Dict[str, Any]) -> None:
        with self._lock:
            record = self._runs[run_id]
            record.artifacts.update(make_json_safe(artifacts))
            record.updated_at = utc_now()
            self._persist_unlocked()

    def set_final_message(self, run_id: str, message: str, status: str) -> None:
        with self._lock:
            record = self._runs[run_id]
            record.final_message = message
            record.status = status
            record.updated_at = utc_now()
            self._persist_unlocked()

    def delete_run(self, run_id: str) -> None:
        with self._lock:
            if run_id in self._runs:
                del self._runs[run_id]
                self._persist_unlocked()

    def _event_to_model(self, event: RunEventRecord) -> RunEventModel:
        return RunEventModel(
            id=event.id,
            type=event.type,
            title=event.title,
            detail=event.detail,
            data=event.data,
            timestamp=event.timestamp,
        )

    def _to_model(self, record: RunRecord) -> RunStateModel:
        return RunStateModel(
            id=record.id,
            prompt=record.prompt,
            status=record.status,
            final_message=record.final_message,
            clarification_prompt=record.clarification_prompt,
            clarification_options=list(record.clarification_options),
            artifacts=dict(record.artifacts),
            events=[self._event_to_model(event) for event in record.events],
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
