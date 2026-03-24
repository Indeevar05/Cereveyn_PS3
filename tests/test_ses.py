import os


def test_send_agent_email_success_includes_meet_link(mocker):
    from notification_manager import send_agent_email

    meeting_link = "http://mock.google.com/meet/xyz"
    body_text = f"Here is your meeting link: {meeting_link}"

    mock_send_email = mocker.MagicMock(return_value={"MessageId": "mock-id"})
    mock_ses_client = mocker.MagicMock()
    mock_ses_client.send_email = mock_send_email

    mocker.patch("notification_manager.boto3.client", return_value=mock_ses_client)
    mocker.patch.dict(
        os.environ,
        {
            "AWS_REGION": "us-east-1",
            "AWS_SES_SENDER_EMAIL": "sender@example.com",
        },
        clear=False,
    )

    payload = send_agent_email(
        recipient_email="rcpt@example.com",
        subject="Team meeting",
        body_text=body_text,
    )

    assert payload == {"status": "success", "messageId": "mock-id"}

    _, kwargs = mock_send_email.call_args
    sent_body_text = kwargs["Message"]["Body"]["Text"]["Data"]
    sent_html = kwargs["Message"]["Body"]["Html"]["Data"]
    assert meeting_link in sent_body_text
    assert meeting_link in sent_html
    assert "<html" in sent_html.lower()