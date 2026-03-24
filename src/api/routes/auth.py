from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse

from api.dependencies import google_oauth_states
from calendar_manager import (
    disconnect_google_oauth,
    exchange_google_oauth_code,
    get_google_authorization_url,
    get_google_calendar_auth_status,
)
from schemas.auth import GoogleAuthStatusResponse, GoogleAuthUrlResponse

router = APIRouter(prefix="/auth/google", tags=["auth"])


@router.get("/status", response_model=GoogleAuthStatusResponse)
def google_auth_status() -> GoogleAuthStatusResponse:
    return GoogleAuthStatusResponse(**get_google_calendar_auth_status())


@router.get("/url", response_model=GoogleAuthUrlResponse)
def google_auth_url() -> GoogleAuthUrlResponse:
    state = uuid4().hex
    auth_url, returned_state = get_google_authorization_url(state=state)
    google_oauth_states.add(returned_state)
    return GoogleAuthUrlResponse(authorizationUrl=auth_url, state=returned_state)


@router.get("/start")
def google_auth_start():
    payload = google_auth_url()
    return RedirectResponse(payload.authorizationUrl)


@router.get("/callback", response_class=HTMLResponse)
def google_auth_callback(
    code: str = Query(...),
    state: str = Query(...),
):
    if state not in google_oauth_states:
        raise HTTPException(status_code=400, detail="Invalid OAuth state.")

    google_oauth_states.discard(state)
    exchange_google_oauth_code(code, state=state)
    return HTMLResponse(
        """
        <html>
          <head><title>Google Calendar connected</title></head>
          <body style="font-family: sans-serif; background: #020617; color: #e2e8f0; padding: 40px;">
            <h2>Google Calendar connected</h2>
            <p>You can close this window and return to Cerevyn.</p>
            <script>
              if (window.opener) {
                window.opener.postMessage({ type: 'google-auth-success' }, '*');
              }
            </script>
          </body>
        </html>
        """
    )


@router.post("/disconnect", response_model=GoogleAuthStatusResponse)
def google_auth_disconnect() -> GoogleAuthStatusResponse:
    disconnect_google_oauth()
    return GoogleAuthStatusResponse(**get_google_calendar_auth_status())
