from fastapi.testclient import TestClient

from api.main import app
from api.routes.runs import get_run_service
from services.run_service import RunService
from services.run_store import RunStore


def build_client(service: RunService) -> TestClient:
    app.dependency_overrides[get_run_service] = lambda: service
    return TestClient(app)


def teardown_client() -> None:
    app.dependency_overrides.clear()


def test_create_run_waits_for_human_input():
    service = RunService(store=RunStore())
    client = build_client(service)
    try:
        response = client.post("/runs", json={"prompt": "Book meeting at 1pm tomorrow."})
        assert response.status_code == 200

        payload = response.json()["run"]
        assert payload["status"] == "waiting_for_user"
        assert "email" in payload["clarification_prompt"].lower()

        events_response = client.get(f"/runs/{payload['id']}/events")
        assert events_response.status_code == 200
        events = events_response.json()["events"]
        assert any(event["type"] == "waiting_for_user" for event in events)
    finally:
        teardown_client()


def test_create_run_with_attendee_email_skips_clarification():
    """Prompts that already include an attendee email go straight to execution (no wait for email)."""
    service = RunService(store=RunStore())

    def complete_sync(run_id: str, prompt: str) -> None:
        service.store.set_final_message(run_id, "Meeting booked successfully.", "completed")

    service._start_background_execution = complete_sync  # type: ignore[method-assign]
    client = build_client(service)
    try:
        response = client.post(
            "/runs",
            json={
                "prompt": "Book meeting with vemalivardhan@gmail.com tomorrow at 2pm and send the invite.",
            },
        )
        assert response.status_code == 200
        payload = response.json()["run"]
        assert payload["status"] == "completed"
        assert payload["final_message"] == "Meeting booked successfully."
        assert payload["clarification_prompt"] is None
    finally:
        teardown_client()


def test_respond_to_run_resumes_and_completes():
    service = RunService(store=RunStore())

    def complete_immediately(run_id: str, prompt: str) -> None:
        service.store.append_event(
            run_id,
            "completed",
            "Run completed",
            "The task finished after the clarification.",
            {"prompt": prompt},
        )
        service.store.merge_artifacts(run_id, {"meetLink": "http://mock.google.com/meet/xyz"})
        service.store.set_final_message(run_id, "Meeting booked successfully.", "completed")

    service._start_background_execution = complete_immediately  # type: ignore[method-assign]
    client = build_client(service)

    try:
        initial = client.post("/runs", json={"prompt": "Book meeting at 1pm tomorrow."})
        run_id = initial.json()["run"]["id"]

        response = client.post(f"/runs/{run_id}/respond", json={"response_text": "boss@example.com"})
        assert response.status_code == 200

        payload = response.json()["run"]
        assert payload["status"] == "completed"
        assert payload["final_message"] == "Meeting booked successfully."
        assert payload["artifacts"]["meetLink"] == "http://mock.google.com/meet/xyz"
    finally:
        teardown_client()
