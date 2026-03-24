import os
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

from google import genai
from google.genai import types

from calendar_manager import create_meet_event
from env import load_application_dotenv
from notification_manager import send_agent_email

EventEmitter = Optional[Callable[[str, str, str, Dict[str, Any]], None]]

_CALENDAR_DECL: Dict[str, Any] = {
    "name": "Calendar",
    "description": "Create a Google Calendar event that generates a Google Meet link.",
    "parameters": {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "description": "Meeting summary/title."},
            "start_time_iso": {
                "type": "string",
                "description": "ISO 8601 UTC timestamp with explicit offset (example: 2026-01-01T14:00:00+00:00).",
            },
            "duration_minutes": {"type": "integer", "description": "Duration of the meeting in minutes."},
            "attendees_list": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of attendee emails.",
            },
        },
        "required": ["summary", "start_time_iso", "duration_minutes", "attendees_list"],
    },
}

_SEND_EMAIL_DECL: Dict[str, Any] = {
    "name": "send_notification_email",
    "description": "Send a professional email notification (HTML + plain text) with meeting details.",
    "parameters": {
        "type": "object",
        "properties": {
            "recipient_email": {"type": "string", "description": "Email address of the recipient."},
            "subject": {"type": "string", "description": "Clear subject line (e.g. meeting title + date)."},
            "body_text": {
                "type": "string",
                "description": (
                    "YOU must write the entire email body as plain text: a full professional letter (not a short note). "
                    "Minimum several paragraphs: greeting; purpose and context from the user's task; date/time (human-readable and UTC), "
                    "duration, and the Google Meet link on its own line; what the recipient should do next; polite closing and signature. "
                    "Use a calm, businesslike tone. Do not send a one- or two-sentence body."
                ),
            },
            "meet_link": {
                "type": "string",
                "description": "Google Meet URL from the Calendar tool (if known).",
            },
            "scheduled_time_iso": {
                "type": "string",
                "description": "Meeting start in ISO 8601 UTC (optional, improves the template).",
            },
            "duration_minutes": {"type": "integer", "description": "Meeting length in minutes (optional)."},
            "meeting_title": {"type": "string", "description": "Short meeting title for the email header (optional)."},
        },
        "required": ["recipient_email", "subject", "body_text"],
    },
}


def _emit(event_type: str, title: str, detail: str, data: Optional[Dict[str, Any]], emit_event: EventEmitter) -> None:
    if emit_event is not None:
        emit_event(event_type, title, detail, data or {})


def _struct_to_dict(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    try:
        return dict(value)
    except Exception:
        pass
    try:
        from google.protobuf.json_format import MessageToDict

        return MessageToDict(value)
    except Exception:
        return value


def _execute_tool(function_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    if function_name == "Calendar":
        missing = [
            k
            for k in ("summary", "start_time_iso", "duration_minutes", "attendees_list")
            if k not in args
        ]
        if missing:
            return {
                "status": "error",
                "message": f"Calendar tool missing required fields: {', '.join(missing)}",
            }
        return create_meet_event(
            summary=args["summary"],
            start_time_iso=args["start_time_iso"],
            duration_minutes=int(args["duration_minutes"]),
            attendees_list=list(args["attendees_list"]),
        )
    if function_name == "send_notification_email":
        missing = [k for k in ("recipient_email", "subject", "body_text") if k not in args]
        if missing:
            return {
                "status": "error",
                "message": f"send_notification_email missing required fields: {', '.join(missing)}",
            }
        raw_duration = args.get("duration_minutes")
        duration: Optional[int] = None
        if raw_duration is not None:
            try:
                duration = int(raw_duration)
            except (TypeError, ValueError):
                duration = None
        return send_agent_email(
            recipient_email=args["recipient_email"],
            subject=args["subject"],
            body_text=args["body_text"],
            meet_link=args.get("meet_link"),
            scheduled_time_iso=args.get("scheduled_time_iso"),
            duration_minutes=duration,
            meeting_title=args.get("meeting_title"),
        )
    return {"status": "error", "message": f"Unknown function: {function_name}"}


def _resolve_tool_name(function_call: Any, args: Dict[str, Any]) -> str:
    """Gemini may omit `function_call.name`; infer from args when needed."""
    raw = (getattr(function_call, "name", None) or "").strip()
    if raw:
        return raw
    if not isinstance(args, dict):
        return "Calendar"
    if args.get("recipient_email") or (args.get("body_text") and args.get("subject")):
        return "send_notification_email"
    if args.get("summary") or args.get("start_time_iso") or args.get("attendees_list"):
        return "Calendar"
    return "Calendar"


def _normalize_tool_result(tool_name: str, result: Any) -> Dict[str, Any]:
    if isinstance(result, dict):
        if result.get("status") == "error":
            message = result.get("message") or result.get("error") or f"{tool_name} failed."
            return {"status": "error", "message": str(message)}
        return result
    return {"status": "error", "message": f"{tool_name} failed with invalid response format."}


def _build_system_instruction(user_local_time: Optional[str] = None) -> str:
    now_utc = datetime.now(timezone.utc)
    tomorrow_utc = now_utc + timedelta(days=1)
    today_iso = now_utc.isoformat()
    tomorrow_date_iso = tomorrow_utc.date().isoformat()
    
    local_info = ""
    if user_local_time:
        local_info = f"\nUser's local time: {user_local_time}"

    return f"""
You are an autonomous backend agent.
You must complete the user's request by calling tools (function calling) until the request is fulfilled.

Current date/time (UTC): {today_iso}
Tomorrow's date (UTC): {tomorrow_date_iso}{local_info}

Tool usage rules:
1. For any meeting booking request, call `Calendar` first.
   - IMPORTANT: Interpret relative times (like "in 10 minutes" or "at 2 PM") relative to the User's local time if provided, but ALWAYS convert the final result to UTC for the tool call.
   - summary: a short descriptive title that includes the attendee email(s)
   - start_time_iso: ISO 8601 timestamp in UTC with an explicit offset (e.g. "+00:00")
   - duration_minutes: if not provided by the user, default to 30
   - attendees_list: list of attendee emails
2. After the meeting is successfully created, call `send_notification_email`.
   YOU write the full email copy in `body_text` (the system only adds light formatting). Requirements for `body_text`:
   - It must read like a real business email: multiple paragraphs (typically 4–8), not a stub or bullet fragment.
   - Include: greeting (e.g. Dear / Hello + context); why this meeting exists and how it relates to the user's request;
     when it happens in plain language AND the exact UTC time; duration; the Google Meet link on its own line;
     optional agenda or preparation; closing line and sign-off (e.g. "Best regards").
   - Tone: professional, clear, and helpful—similar to a calendar invite email from a colleague.
   - Also pass structured fields for the layout card: recipient_email, subject, meet_link, scheduled_time_iso, duration_minutes, meeting_title.

Extra constraints:
- Always use UTC for the computed times.
- If the user says "tomorrow at 2 PM" interpret it as {tomorrow_date_iso} 14:00 UTC.
- Do not invent emails; use the email(s) from the prompt.
- If Calendar returns an error (for example slot busy), ask the user for another time option.
- If notification sending fails, end gracefully and clearly report the email failure.
""".strip()


def _build_genai_client() -> genai.Client:
    load_application_dotenv()
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set in environment.")
    return genai.Client(api_key=api_key)


def _build_generate_config(user_local_time: Optional[str] = None) -> types.GenerateContentConfig:
    tools = types.Tool(function_declarations=[_CALENDAR_DECL, _SEND_EMAIL_DECL])
    return types.GenerateContentConfig(
        tools=[tools],
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(mode="AUTO"),
        ),
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        system_instruction=_build_system_instruction(user_local_time),
    )


def _response_text(response: types.GenerateContentResponse) -> str:
    if getattr(response, "text", None):
        return response.text or ""
    return ""


def _collect_function_calls(response: types.GenerateContentResponse) -> List[types.FunctionCall]:
    out: List[types.FunctionCall] = []
    try:
        cand = response.candidates[0]
        content = cand.content
        if not content or not content.parts:
            return out
        for part in content.parts:
            if part.function_call is not None:
                out.append(part.function_call)
    except (IndexError, TypeError, AttributeError):
        return out
    return out


def run_agent_session(
    user_prompt: str,
    *,
    user_local_time: Optional[str] = None,
    max_steps: int = 10,
    emit_event: EventEmitter = None,
) -> Dict[str, Any]:
    _emit("run_started", "Run started", "Agent execution has started.", {"prompt": user_prompt}, emit_event)
    client = _build_genai_client()
    model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-3.1-pro-preview")
    config = _build_generate_config(user_local_time)

    contents: List[types.Content] = [
        types.Content(role="user", parts=[types.Part(text=user_prompt)]),
    ]

    _emit(
        "model_thinking",
        "Model analyzing request",
        "Gemini is decomposing the task into tool calls.",
        {"task_preview": user_prompt[:500], "step": "initial_reasoning"},
        emit_event,
    )
    response = client.models.generate_content(model=model_name, contents=contents, config=config)
    artifacts: Dict[str, Any] = {}

    steps = 0
    while steps < max_steps:
        steps += 1
        function_calls = _collect_function_calls(response)
        if not function_calls:
            break

        try:
            model_content = response.candidates[0].content
        except (IndexError, AttributeError):
            break
        if not model_content:
            break
        contents.append(model_content)
        response_parts: List[types.Part] = []

        for function_call in function_calls:
            args = _struct_to_dict(function_call.args) or {}
            fn_name = _resolve_tool_name(function_call, args)
            _emit(
                "tool_requested",
                f"{fn_name} requested",
                f"Agent is calling {fn_name}.",
                {"tool_name": fn_name, "args": args},
                emit_event,
            )

            result = _normalize_tool_result(fn_name, _execute_tool(fn_name, args))
            if result.get("status") == "success":
                if "meetLink" in result:
                    artifacts["meetLink"] = result["meetLink"]
                if "messageId" in result:
                    artifacts["messageId"] = result["messageId"]
                if "startTime" in result:
                    artifacts["startTime"] = result["startTime"]
                if "endTime" in result:
                    artifacts["endTime"] = result["endTime"]
                _emit(
                    "tool_succeeded",
                    f"{fn_name} succeeded",
                    f"{fn_name} completed successfully.",
                    {"tool_name": fn_name, "result": result},
                    emit_event,
                )
            else:
                _emit(
                    "tool_failed",
                    f"{fn_name} failed",
                    result.get("message", f"{fn_name} failed."),
                    {"tool_name": fn_name, "result": result},
                    emit_event,
                )

            fr = types.FunctionResponse(name=fn_name, response=result)
            call_id = getattr(function_call, "id", None)
            if call_id:
                fr.id = call_id
            response_parts.append(types.Part(function_response=fr))

        contents.append(types.Content(role="user", parts=response_parts))
        _emit(
            "model_thinking",
            "Model continuing",
            "Gemini is reviewing tool results and planning next steps.",
            {
                "step": "after_tools",
                "known_artifacts": list(artifacts.keys()),
                "task_preview": user_prompt[:500],
            },
            emit_event,
        )
        response = client.models.generate_content(model=model_name, contents=contents, config=config)

    final_message = _response_text(response) or "The agent completed without a final response."
    _emit("completed", "Run completed", final_message, {"artifacts": artifacts}, emit_event)
    return {"status": "completed", "final_message": final_message, "artifacts": artifacts}


def run_autonomous_agent(user_prompt: str, *, max_steps: int = 10) -> str:
    return run_agent_session(user_prompt, max_steps=max_steps)["final_message"]
