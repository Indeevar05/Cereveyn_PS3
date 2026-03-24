import pytest


@pytest.fixture(autouse=True)
def reset_notification_ses_client():
    """`notification_manager` caches a global SES client; reset between tests for isolated mocks."""
    import notification_manager

    notification_manager.ses_client = None
    yield
    notification_manager.ses_client = None
