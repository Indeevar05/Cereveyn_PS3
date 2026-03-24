import os

import pytest
from googleapiclient.errors import HttpError
from httplib2 import Response


def _require_live_key():
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not gemini_key:
        pytest.skip("GEMINI_API_KEY is not set; skipping live Gemini robustness test.")


def test_calendar_conflict_prompts_for_new_time(mocker):
    _require_live_key()

    from agent_core import run_autonomous_agent

    # Calendar insert fails with a 409 conflict.
    mock_insert = mocker.MagicMock()
    mock_insert.execute.side_effect = HttpError(Response({"status": "409"}), b"Conflict")
    mock_events = mocker.MagicMock()
    mock_events.insert.return_value = mock_insert
    mock_google_calendar_api = mocker.MagicMock()
    mock_google_calendar_api.events.return_value = mock_events
    mocker.patch("calendar_manager.google_calendar_api", mock_google_calendar_api)

    # SES mocked to ensure no real calls happen.
    mock_send_email = mocker.MagicMock(return_value={"MessageId": "mock-id"})
    mock_ses_client = mocker.MagicMock(send_email=mock_send_email)
    mocker.patch("notification_manager.boto3.client", return_value=mock_ses_client)
    mocker.patch.dict(os.environ, {"AWS_SES_SENDER_EMAIL": "sender@example.com"}, clear=False)

    # Include an attendee email so the model reaches Calendar (then sees the conflict).
    final_text = run_autonomous_agent(
        "Book meeting with attendee@example.com at 1pm tomorrow."
    )
    final_lower = (final_text or "").lower()

    assert "time" in final_lower or "slot" in final_lower
    assert "new" in final_lower or "another" in final_lower or "provide" in final_lower


def test_ses_failure_reported_gracefully(mocker):
    _require_live_key()

    from agent_core import run_autonomous_agent

    meeting_link = "http://mock.google.com/meet/xyz"

    # Calendar path succeeds.
    mock_insert = mocker.MagicMock()
    mock_insert.execute.return_value = {"hangoutLink": meeting_link}
    mock_events = mocker.MagicMock()
    mock_events.insert.return_value = mock_insert
    mock_google_calendar_api = mocker.MagicMock()
    mock_google_calendar_api.events.return_value = mock_events
    mocker.patch("calendar_manager.google_calendar_api", mock_google_calendar_api)

    # SES fails generically.
    mock_send_email = mocker.MagicMock(side_effect=Exception("SES transport unavailable"))
    mock_ses_client = mocker.MagicMock(send_email=mock_send_email)
    mocker.patch("notification_manager.boto3.client", return_value=mock_ses_client)
    mocker.patch.dict(os.environ, {"AWS_SES_SENDER_EMAIL": "sender@example.com"}, clear=False)

    final_text = run_autonomous_agent(
        "Book meeting with boss@example.com for tomorrow at 2 PM and email them."
    )
    final_lower = (final_text or "").lower()

    assert "email" in final_lower or "notification" in final_lower
    assert (
        "fail" in final_lower
        or "error" in final_lower
        or "unable" in final_lower
        or "unavailable" in final_lower
    )

