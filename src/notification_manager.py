import html
import os
import re
from typing import Optional, Tuple

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Lazy-initialized so unit tests can patch it without needing AWS credentials.
ses_client = None

_MEET_LINK_RE = re.compile(r"https?://[^\s]+meet[^\s]*", re.IGNORECASE)


def _get_ses_client():
    global ses_client
    if ses_client is not None:
        return ses_client

    load_dotenv()
    region = os.getenv("AWS_REGION", "").strip()
    if region:
        ses_client = boto3.client("ses", region_name=region)
    else:
        ses_client = boto3.client("ses")
    return ses_client


def extract_meet_link(body_text: str) -> Optional[str]:
    match = _MEET_LINK_RE.search(body_text or "")
    return match.group(0).rstrip(").,;") if match else None


def _plain_email_to_html_paragraphs(body: str) -> str:
    """Turn AI plain-text email into HTML paragraphs (double newline = paragraph)."""
    esc = html.escape
    text = (body or "").strip()
    if not text:
        return ""
    parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not parts:
        inner = esc(text).replace("\n", "<br />")
        return f'<p style="margin:0 0 16px 0;line-height:1.65;font-size:15px;color:#24292f;">{inner}</p>'
    chunks = []
    for para in parts:
        inner = esc(para).replace("\n", "<br />")
        chunks.append(
            f'<p style="margin:0 0 16px 0;line-height:1.65;font-size:15px;color:#24292f;">{inner}</p>'
        )
    return "".join(chunks)


def build_meeting_email_bodies(
    *,
    recipient_email: str,
    subject: str,
    body_text: str,
    meet_link: Optional[str] = None,
    scheduled_time_iso: Optional[str] = None,
    duration_minutes: Optional[int] = None,
    meeting_title: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Plain-text + HTML: the AI-written body_text is the main message; we add a summary card and footer.
    """
    esc = html.escape
    link = (meet_link or "").strip() or extract_meet_link(body_text)
    title = (meeting_title or "").strip() or "Meeting scheduled"
    safe_body = (body_text or "").strip()
    if not safe_body:
        safe_body = "(No message body was provided.)"

    # Plain text: AI letter first, then optional quick-reference (does not replace the AI copy).
    ref_lines: list[str] = []
    if title or scheduled_time_iso or duration_minutes is not None or link:
        ref_lines.extend(["", "--- Quick reference ---", f"Title: {title}"])
        if scheduled_time_iso:
            ref_lines.append(f"When (UTC): {scheduled_time_iso}")
        if duration_minutes is not None:
            ref_lines.append(f"Duration: {duration_minutes} minutes")
        if link:
            ref_lines.append(f"Meet: {link}")
    ref_lines.extend(
        [
            "",
            "---",
            "This notification was sent by Cerevyn on behalf of the organizer.",
            f"Recipient: {recipient_email}",
        ]
    )
    plain = safe_body + "\n".join(ref_lines)

    meta_rows = ""
    if scheduled_time_iso:
        meta_rows += (
            "<tr><td style='padding:6px 10px;color:#57606a;width:32%;'>Time (UTC)</td>"
            f"<td style='padding:6px 10px;'>{esc(scheduled_time_iso)}</td></tr>"
        )
    if duration_minutes is not None:
        meta_rows += (
            "<tr><td style='padding:6px 10px;color:#57606a;'>Duration</td>"
            f"<td style='padding:6px 10px;'>{duration_minutes} minutes</td></tr>"
        )
    if link:
        meta_rows += (
            "<tr><td style='padding:6px 10px;color:#57606a;vertical-align:top;'>Meet</td>"
            f"<td style='padding:6px 10px;word-break:break-all;'>"
            f'<a href="{esc(link)}" style="color:#0969da;">{esc(link)}</a></td></tr>'
        )

    summary_table = ""
    if meta_rows:
        summary_table = f"""
      <table role="presentation" cellspacing="0" cellpadding="0" width="100%" style="border-collapse:collapse;background:#f6f8fa;border:1px solid #d0d7de;border-radius:6px;margin:0 0 20px 0;">
        <tr><td colspan="2" style="padding:8px 10px;font-size:12px;font-weight:600;color:#57606a;text-transform:uppercase;letter-spacing:0.04em;">Meeting summary</td></tr>
        <tr><td style="padding:6px 10px;color:#57606a;border-top:1px solid #d0d7de;">Title</td><td style="padding:6px 10px;border-top:1px solid #d0d7de;">{esc(title)}</td></tr>
        {meta_rows}
      </table>"""

    body_html = _plain_email_to_html_paragraphs(safe_body)

    html_out = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8" /><meta name="viewport" content="width=device-width" /></head>
<body style="margin:0;padding:24px;background:#f6f8fa;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;color:#24292f;font-size:14px;line-height:1.5;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:600px;margin:0 auto;background:#ffffff;border:1px solid #d0d7de;border-radius:8px;">
    <tr><td style="padding:28px 28px 24px 28px;">
      <p style="margin:0 0 6px 0;font-size:11px;font-weight:600;color:#57606a;text-transform:uppercase;letter-spacing:0.06em;">Meeting notification</p>
      <h1 style="margin:0 0 20px 0;font-size:18px;font-weight:600;color:#24292f;line-height:1.35;">{esc(title)}</h1>
      {summary_table}
      <div style="margin:0 0 8px 0;font-size:12px;font-weight:600;color:#57606a;">Message</div>
      <div style="border-left:3px solid #0969da;padding-left:16px;margin-bottom:24px;">
        {body_html}
      </div>
      <p style="margin:0;font-size:12px;color:#57606a;line-height:1.5;">
        If you did not expect this invitation, contact the organizer. Keep meeting links private.
      </p>
    </td></tr>
  </table>
  <p style="text-align:center;color:#8c959f;font-size:11px;margin-top:14px;max-width:600px;margin-left:auto;margin-right:auto;">{esc(subject)}</p>
</body>
</html>"""

    return plain, html_out


def send_agent_email(
    recipient_email: str,
    subject: str,
    body_text: str,
    *,
    meet_link: Optional[str] = None,
    scheduled_time_iso: Optional[str] = None,
    duration_minutes: Optional[int] = None,
    meeting_title: Optional[str] = None,
):
    """
    Send multipart (plain + HTML) SES email with a structured meeting notification layout.
    """
    load_dotenv()
    sender_email = os.getenv("AWS_SES_SENDER_EMAIL", "").strip()
    if not sender_email:
        raise ValueError("AWS_SES_SENDER_EMAIL is not set in environment.")

    plain, html_body = build_meeting_email_bodies(
        recipient_email=recipient_email,
        subject=subject,
        body_text=body_text,
        meet_link=meet_link,
        scheduled_time_iso=scheduled_time_iso,
        duration_minutes=duration_minutes,
        meeting_title=meeting_title,
    )

    client = _get_ses_client()

    try:
        response = client.send_email(
            Source=sender_email,
            Destination={"ToAddresses": [recipient_email]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {
                    "Text": {"Data": plain, "Charset": "UTF-8"},
                    "Html": {"Data": html_body, "Charset": "UTF-8"},
                },
            },
        )
        message_id: Optional[str] = response.get("MessageId")
        return {"status": "success", "messageId": message_id}
    except ClientError as exc:
        error_code = (
            exc.response.get("Error", {}).get("Code")
            if getattr(exc, "response", None)
            else None
        )
        if error_code == "LimitExceededException":
            return {
                "status": "error",
                "message": "Notification limit exceeded. Please retry shortly.",
            }
        return {"status": "error", "message": f"Notification API error: {str(exc)}"}
    except Exception as exc:
        return {"status": "error", "message": f"Notification error: {str(exc)}"}
