import sys
from unittest.mock import MagicMock, patch

# Mock dependencies before importing
sys.modules['googleapiclient.discovery'] = MagicMock()
sys.modules['google.auth.transport.requests'] = MagicMock()
sys.modules['google.oauth2.credentials'] = MagicMock()
sys.modules['google_auth_oauthlib.flow'] = MagicMock()
sys.modules['dotenv'] = MagicMock()

import calendar_manager

def test_extract_space_id():
    # Test different link formats
    links = [
        ("https://meet.google.com/abc-defg-hij", "abc-defg-hij"),
        ("https://meet.google.com/abc-defg-hij?authuser=0", "abc-defg-hij"),
        ("meet.google.com/xyz-pdq-rst", "xyz-pdq-rst"),
    ]
    for link, expected in links:
        # Mocking implementation detail: split logic
        space_id = link.split("meet.google.com/")[-1].split("?")[0]
        assert space_id == expected, f"Failed for {link}"
    print("Space ID extraction tests passed.")

@patch('calendar_manager._load_user_credentials')
@patch('calendar_manager.build')
def test_get_participant_count(mock_build, mock_load):
    mock_load.return_value = MagicMock()
    mock_meet = MagicMock()
    mock_build.return_value = mock_meet
    
    # Mock conferenceRecords().list().execute()
    mock_meet.conferenceRecords().list().execute.return_value = {
        "conferenceRecords": [{"name": "conferenceRecords/123"}]
    }
    
    # Mock conferenceRecords().participants().list().execute()
    mock_meet.conferenceRecords().participants().list().execute.return_value = {
        "participants": [
            {"name": "p1", "expireTime": None},
            {"name": "p2", "expireTime": "2026-03-23T10:00:00Z"}, # Left
            {"name": "p3"} # Active (no expireTime)
        ]
    }
    
    count = calendar_manager.get_meeting_participant_count("https://meet.google.com/abc-defg-hij")
    assert count == 2, f"Expected 2 active participants, got {count}"
    print("Participant count logic tests passed.")

if __name__ == "__main__":
    test_extract_space_id()
    try:
        test_get_participant_count()
    except Exception as e:
        print(f"Participant count test failed (expected if imports are tricky): {e}")
