import tempfile
from pathlib import Path

from services.run_store import RunStore


def test_run_store_round_trip_sqlite():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "runs.sqlite"
        store = RunStore(persist_path=path)
        record = store.create_run(prompt="hello", status="running")
        store.append_event(record.id, "run_started", "t", "d", {})
        store.set_final_message(record.id, "done", "completed")

        store2 = RunStore(persist_path=path)
        loaded = store2.get_run(record.id)
        assert loaded.prompt == "hello"
        assert loaded.status == "completed"
        assert loaded.final_message == "done"
        assert len(loaded.events) >= 1