import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials as UserCredentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google_auth_oauthlib.flow import Flow

# Lazy-initialized so unit tests can patch it without needing real credentials.
google_calendar_api = None
GOOGLE_CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar"]
# Meet REST API: spaces.create — https://developers.google.com/workspace/meet/api/reference/rest/v2/spaces/create
GOOGLE_MEET_SCOPES = [
    "https://www.googleapis.com/auth/meetings.space.created"
]
GOOGLE_OAUTH_SCOPES = GOOGLE_CALENDAR_SCOPES + GOOGLE_MEET_SCOPES


def _get_token_path() -> Path:
    token_path = os.getenv("GOOGLE_OAUTH_TOKEN_JSON", ".tokens/google_calendar_token.json").strip()
    return Path(token_path)


def _save_user_credentials(creds: UserCredentials) -> None:
    token_path = _get_token_path()
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json(), encoding="utf-8")


def _get_oauth_redirect_uri() -> str:
    return os.getenv(
        "GOOGLE_OAUTH_REDIRECT_URI",
        "http://127.0.0.1:8000/auth/google/callback",
    ).strip()


def _build_oauth_client_config() -> dict:
    client_id = os.getenv("CLIENT_ID", "").strip()
    client_secret = os.getenv("CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise ValueError("CLIENT_ID and CLIENT_SECRET must be set for Google OAuth.")
    return {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [_get_oauth_redirect_uri()],
        }
    }


def create_google_oauth_flow(*, state: Optional[str] = None) -> Flow:
    # Web server uses client_secret; disable PKCE so a new Flow on the callback
    # does not need the code_verifier from the authorization request (see
    # google_auth_oauthlib Flow.authorization_url / fetch_token).
    flow = Flow.from_client_config(
        _build_oauth_client_config(),
        scopes=GOOGLE_OAUTH_SCOPES,
        state=state,
        autogenerate_code_verifier=False,
    )
    flow.redirect_uri = _get_oauth_redirect_uri()
    return flow


def get_google_authorization_url(*, state: Optional[str] = None) -> tuple[str, str]:
    flow = create_google_oauth_flow(state=state)
    auth_url, returned_state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return auth_url, returned_state


def exchange_google_oauth_code(code: str, *, state: Optional[str] = None) -> dict:
    global google_calendar_api
    flow = create_google_oauth_flow(state=state)
    flow.fetch_token(code=code)
    _save_user_credentials(flow.credentials)
    google_calendar_api = None
    return {"status": "connected", "redirectUri": _get_oauth_redirect_uri()}


def disconnect_google_oauth() -> None:
    global google_calendar_api
    token_path = _get_token_path()
    if token_path.exists():
        token_path.unlink()
    google_calendar_api = None


def get_google_calendar_auth_status() -> dict:
    load_dotenv()
    service_account_path = os.getenv("GOOGLE_CALENDAR_CREDENTIALS_JSON", "").strip()
    token_path = _get_token_path()
    if service_account_path:
        return {"connected": True, "authMode": "service_account", "redirectUri": _get_oauth_redirect_uri()}
    if token_path.exists():
        return {"connected": True, "authMode": "oauth", "redirectUri": _get_oauth_redirect_uri()}
    return {"connected": False, "authMode": "oauth", "redirectUri": _get_oauth_redirect_uri()}


def _load_user_credentials() -> Optional[UserCredentials]:
    load_dotenv()
    token_path = _get_token_path()
    if not token_path.exists():
        return None

    creds = UserCredentials.from_authorized_user_file(str(token_path), scopes=GOOGLE_OAUTH_SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _save_user_credentials(creds)

    if creds.valid:
        return creds
    return None


def _get_calendar_api():
    global google_calendar_api
    if google_calendar_api is not None:
        return google_calendar_api

    load_dotenv()
    credentials_json_path = os.getenv("GOOGLE_CALENDAR_CREDENTIALS_JSON", "").strip()
    if credentials_json_path:
        creds = ServiceAccountCredentials.from_service_account_file(
            credentials_json_path,
            scopes=GOOGLE_OAUTH_SCOPES,
        )
        google_calendar_api = build("calendar", "v3", credentials=creds)
        return google_calendar_api

    creds = _load_user_credentials()
    if creds is None:
        raise ValueError(
            "Google Calendar is not connected. Complete OAuth setup at /auth/google/start first."
        )

    google_calendar_api = build("calendar", "v3", credentials=creds)
    return google_calendar_api


def _rfc3339_utc(dt: datetime) -> str:
    """UTC instant as RFC3339 with Z suffix.

    Avoids ``dateTime`` + ``timeZone`` combinations that some Calendar API
    validations reject when combined with ``conferenceData``.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _http_error_detail(exc: HttpError) -> str:
    try:
        if exc.content:
            payload = json.loads(exc.content.decode())
            err = payload.get("error") or {}
            errs = err.get("errors") or []
            if errs:
                return "; ".join(
                    f"{e.get('domain', '')}:{e.get('reason', '')} {e.get('message', '')}".strip()
                    for e in errs
                )
            if err.get("message"):
                return str(err["message"])
    except Exception:
        pass
    return str(exc)


def _extract_meet_link(calendar_event_response: dict) -> Optional[str]:
    # Newer APIs may return conferenceData.entryPoints; older may still return hangoutLink.
    if isinstance(calendar_event_response, dict):
        hangout_link = calendar_event_response.get("hangoutLink")
        if hangout_link:
            return hangout_link

        conference_data = calendar_event_response.get("conferenceData") or {}
        entry_points = conference_data.get("entryPoints") or []
        for entry_point in entry_points:
            if entry_point.get("entryPointType") == "video":
                return entry_point.get("uri")
    return None


def _try_create_meet_space_link() -> Optional[str]:
    """Create a Meet join URL using Meet REST API ``spaces.create`` (needs OAuth + Meet scope)."""
    load_dotenv()
    if os.getenv("GOOGLE_CALENDAR_CREDENTIALS_JSON", "").strip():
        return None
    try:
        creds = _load_user_credentials()
        if creds is None:
            return None
        meet = build("meet", "v2", credentials=creds, static_discovery=False)
        space = meet.spaces().create(body={}).execute()
        return space.get("meetingUri")
    except Exception:
        return None


def create_meet_event(
    summary: str,
    start_time_iso: str,
    duration_minutes: int,
    attendees_list: List[str],
):
    """
    Create a Google Calendar event and resolve a Meet join URL.

    Prefer a Meet link from Calendar ``conferenceData``; if missing, call the
    Meet REST API ``spaces.create`` (requires ``meetings.space.created`` scope).
    """
    api = _get_calendar_api()

    start_dt = datetime.fromisoformat(start_time_iso)
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=timezone.utc)
    end_dt = start_dt + timedelta(minutes=duration_minutes)

    def _event_body(with_conference: bool) -> dict:
        body: dict = {
            "summary": summary,
            "attendees": [{"email": email} for email in attendees_list],
            "start": {"dateTime": _rfc3339_utc(start_dt)},
            "end": {"dateTime": _rfc3339_utc(end_dt)},
        }
        if with_conference:
            body["conferenceData"] = {
                "createRequest": {
                    "requestId": uuid.uuid4().hex,
                    "conferenceSolutionKey": {"type": "hangoutMeet"},
                }
            }
        return body

    try:
        # conferenceDataVersion is an insert query parameter, not an Event field.
        response = (
            api.events()
            .insert(
                calendarId="primary",
                body=_event_body(with_conference=True),
                conferenceDataVersion=1,
                sendUpdates="all",
            )
            .execute()
        )
        calendar_link = _extract_meet_link(response)
        meet_link = calendar_link
        if not meet_link:
            meet_link = _try_create_meet_space_link()
        payload: dict = {
            "status": "success",
            "meetLink": meet_link,
            "startTime": _rfc3339_utc(start_dt),
            "endTime": _rfc3339_utc(end_dt),
        }
        if meet_link and not calendar_link:
            payload["message"] = "Meet link created via Google Meet API (Calendar had no conference link)."
        return payload
    except HttpError as exc:
        status = getattr(exc, "status_code", None) or getattr(getattr(exc, "resp", None), "status", None)
        if status == 409:
            return {"status": "error", "message": "Calendar slot busy. Please provide a new meeting time."}
        # Some accounts/API combinations reject conferenceData with 400; book without Meet.
        if status == 400:
            try:
                response = (
                    api.events()
                    .insert(
                        calendarId="primary",
                        body=_event_body(with_conference=False),
                        sendUpdates="all",
                    )
                    .execute()
                )
                calendar_link = _extract_meet_link(response)
                meet_link = calendar_link
                if not meet_link:
                    meet_link = _try_create_meet_space_link()
                if meet_link:
                    return {
                        "status": "success",
                        "meetLink": meet_link,
                        "startTime": _rfc3339_utc(start_dt),
                        "endTime": _rfc3339_utc(end_dt),
                        **(
                            {"message": "Meet link created via Google Meet API."}
                            if not calendar_link
                            else {}
                        ),
                    }
                return {
                    "status": "success",
                    "meetLink": None,
                    "message": (
                        "Calendar event created, but no Meet link could be added "
                        "(conference creation was rejected and Meet API did not return a link)."
                    ),
                }
            except HttpError as exc_plain:
                return {
                    "status": "error",
                    "message": f"Calendar API error: {_http_error_detail(exc_plain)}",
                }
        return {"status": "error", "message": f"Calendar API error: {_http_error_detail(exc)}"}
    except Exception as exc:
        return {"status": "error", "message": f"Calendar error: {str(exc)}"}


def get_meeting_participant_count(meet_link: str) -> int:
    """
    Check the number of active participants in a Google Meet space.
    Extracted from the meet_link (e.g. https://meet.google.com/abc-defg-hij).
    """
    if not meet_link or "meet.google.com/" not in meet_link:
        return 0

    space_id = meet_link.split("meet.google.com/")[-1].split("?")[0]
    if not space_id:
        return 0

    try:
        creds = _load_user_credentials()
        if creds is None:
            return 0
        
        # Use Meet REST API v2
        meet = build("meet", "v2", credentials=creds, static_discovery=False)
        
        # List conference records for this space. 
        # Filter for active conferences.
        response = (
            meet.conferenceRecords()
            .list(filter=f"space.name='spaces/{space_id}' AND active=true")
            .execute()
        )
        
        conference_records = response.get("conferenceRecords", [])
        if not conference_records:
            return 0
            
        # If there's an active conference, check participant count.
        # For simplicity, if an active conference exists, we can try to list participants.
        # But even just the presence of an active conference record often means people are there.
        # Let's try to get more detail if possible.
        conf_name = conference_records[0].get("name")
        participants_resp = meet.conferenceRecords().participants().list(parent=conf_name).execute()
        
        # Filter for participants that have not left.
        active_participants = [
            p for p in participants_resp.get("participants", [])
            if not p.get("expireTime")
        ]
        
        return len(active_participants)
    except Exception:
        # Fallback: if we can't get participant details but have an active conference, assume > 0
        try:
            if conference_records:
                return 1
        except NameError:
            pass
        return 0
