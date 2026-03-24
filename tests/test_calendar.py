from datetime import datetime, timezone


def test_create_meet_event_success(mocker):
    from calendar_manager import create_meet_event

    mock_execute_return = {"hangoutLink": "http://mock.google.com/meet/xyz"}

    mock_insert = mocker.MagicMock()
    mock_insert.execute.return_value = mock_execute_return

    mock_events = mocker.MagicMock()
    mock_events.insert.return_value = mock_insert

    mock_google_calendar_api = mocker.MagicMock()
    mock_google_calendar_api.events.return_value = mock_events

    mocker.patch("calendar_manager.google_calendar_api", mock_google_calendar_api)

    start_time = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc).isoformat()
    payload = create_meet_event(
        summary="Test Meeting",
        start_time_iso=start_time,
        duration_minutes=30,
        attendees_list=["a@example.com"],
    )

    assert payload == {"status": "success", "meetLink": "http://mock.google.com/meet/xyz"}

