import os
from datetime import datetime, timedelta, timezone

import pytest
from google.genai import types

import agent_core
from agent_core import run_autonomous_agent


@pytest.mark.parametrize(
    "attendee_email",
    [
        "boss@example.com",
        "vemalivardhan@gmail.com",
    ],
)
def test_agent_book_meeting_and_email_integration(mocker, attendee_email):
    """End-to-end tool loop with Gemini responses mocked (stable, no API key)."""
    meeting_link = "http://mock.google.com/meet/xyz"
    exec_order = []

    mock_execute = mocker.MagicMock(
        side_effect=lambda: (exec_order.append("calendar"), {"hangoutLink": meeting_link})[1]
    )

    mock_insert = mocker.MagicMock()
    mock_insert.execute = mock_execute

    mock_events = mocker.MagicMock()
    mock_events.insert = mocker.MagicMock(return_value=mock_insert)

    mock_google_calendar_api = mocker.MagicMock()
    mock_google_calendar_api.events = mocker.MagicMock(return_value=mock_events)

    mocker.patch("calendar_manager.google_calendar_api", mock_google_calendar_api)

    mock_send_email = mocker.MagicMock(
        side_effect=lambda **kwargs: (exec_order.append("ses"), {"MessageId": "mock-id"})[1]
    )
    mock_ses_client = mocker.MagicMock(send_email=mock_send_email)
    mocker.patch("notification_manager.boto3.client", return_value=mock_ses_client)

    mocker.patch.dict(
        os.environ,
        {"AWS_SES_SENDER_EMAIL": "sender@example.com"},
        clear=False,
    )

    user_prompt = f"Book meeting with {attendee_email} for tomorrow at 2 PM and email them."

    now_utc = datetime.now(timezone.utc)
    tomorrow_date = (now_utc + timedelta(days=1)).date()
    expected_dt = datetime(
        tomorrow_date.year,
        tomorrow_date.month,
        tomorrow_date.day,
        14,
        0,
        0,
        tzinfo=timezone.utc,
    )
    start_iso = expected_dt.isoformat()

    class FakeModels:
        def __init__(self) -> None:
            self._step = 0

        def generate_content(self, model, contents, config):
            self._step += 1
            if self._step == 1:
                return types.GenerateContentResponse(
                    candidates=[
                        types.Candidate(
                            content=types.Content(
                                role="model",
                                parts=[
                                    types.Part(
                                        function_call=types.FunctionCall(
                                            name="Calendar",
                                            id="call-cal",
                                            args={
                                                "summary": f"Meeting with {attendee_email}",
                                                "start_time_iso": start_iso,
                                                "duration_minutes": 30,
                                                "attendees_list": [attendee_email],
                                            },
                                        )
                                    )
                                ],
                            ),
                            finish_reason=types.FinishReason.STOP,
                        )
                    ]
                )
            if self._step == 2:
                return types.GenerateContentResponse(
                    candidates=[
                        types.Candidate(
                            content=types.Content(
                                role="model",
                                parts=[
                                    types.Part(
                                        function_call=types.FunctionCall(
                                            name="send_notification_email",
                                            id="call-email",
                                            args={
                                                "recipient_email": attendee_email,
                                                "subject": "Team meeting",
                                                "body_text": f"Join here: {meeting_link}",
                                            },
                                        )
                                    )
                                ],
                            ),
                            finish_reason=types.FinishReason.STOP,
                        )
                    ]
                )
            return types.GenerateContentResponse(
                candidates=[
                    types.Candidate(
                        content=types.Content(
                            role="model",
                            parts=[types.Part(text="Meeting booked and notification sent.")],
                        ),
                        finish_reason=types.FinishReason.STOP,
                    )
                ]
            )

    class FakeClient:
        def __init__(self) -> None:
            self.models = FakeModels()

    mocker.patch.object(agent_core, "_build_genai_client", return_value=FakeClient())

    run_autonomous_agent(user_prompt)

    assert "calendar" in exec_order
    assert "ses" in exec_order
    assert exec_order.index("calendar") < exec_order.index("ses")

    assert mock_events.insert.called
    assert mock_insert.execute.called
    _, insert_kwargs = mock_events.insert.call_args_list[-1]
    event_body = insert_kwargs["body"]

    assert attendee_email.lower() in (event_body["summary"] or "").lower()
    assert event_body["attendees"][0]["email"] == attendee_email

    start_dt_actual = datetime.fromisoformat(event_body["start"]["dateTime"])
    assert start_dt_actual.year == expected_dt.year
    assert start_dt_actual.month == expected_dt.month
    assert start_dt_actual.day == expected_dt.day
    assert start_dt_actual.hour == 14
    assert start_dt_actual.minute == 0

    _, ses_kwargs = mock_send_email.call_args_list[-1]
    sent_body_text = ses_kwargs["Message"]["Body"]["Text"]["Data"]
    assert meeting_link in sent_body_text
    assert ses_kwargs["Destination"]["ToAddresses"] == [attendee_email]
