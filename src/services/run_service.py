from __future__ import annotations

import re
from threading import Thread
from typing import List, Optional, Tuple

from agent_core import run_agent_session
from calendar_manager import get_meeting_participant_count
from schemas.runs import RunStateModel
from services.run_store import RunStore

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
MULTI_TIME_RE = re.compile(
    r"\b(\d{1,2}(?::\d{2})?\s?(?:am|pm))\b.*\bor\b.*\b(\d{1,2}(?::\d{2})?\s?(?:am|pm))\b",
    re.IGNORECASE,
)


class RunService:
    def __init__(self, store: Optional[RunStore] = None) -> None:
        self.store = store or RunStore()

    def list_runs(self) -> List[RunStateModel]:
        return self.store.list_runs()

    def get_run(self, run_id: str) -> RunStateModel:
        return self.store.get_run(run_id)

    def delete_run(self, run_id: str) -> None:
        self.store.delete_run(run_id)

    def get_events(self, run_id: str, since: int = 0):
        return self.store.list_events(run_id, since=since)

    def start_run(self, prompt: str, user_local_time: Optional[str] = None) -> RunStateModel:
        record = self.store.create_run(prompt=prompt, status="running")
        self.store.append_event(
            record.id,
            "run_started",
            "Request received",
            "The web app accepted the task and is preparing the agent run.",
            {"prompt": prompt},
        )
        clarification = self._get_initial_clarification(prompt)
        if clarification is not None:
            question, options = clarification
            self.store.set_waiting(record.id, question, options)
            self.store.append_event(
                record.id,
                "waiting_for_user",
                "Need clarification",
                question,
                {"options": options},
            )
            return self.store.get_run(record.id)

        self._start_background_execution(record.id, prompt, user_local_time)
        return self.store.get_run(record.id)

    def respond_to_run(self, run_id: str, response_text: str, user_local_time: Optional[str] = None) -> RunStateModel:
        current = self.store.get_run(run_id)
        merged_prompt = f"{current.prompt}\n\nUser clarification: {response_text}"
        self.store.clear_waiting(run_id)
        self.store.update_status(run_id, "running")
        self.store.append_event(
            run_id,
            "model_thinking",
            "Clarification received",
            "The agent is resuming with the user's clarification.",
            {"response_text": response_text},
        )
        self._start_background_execution(run_id, merged_prompt, user_local_time)
        return self.store.get_run(run_id)

    def _start_background_execution(self, run_id: str, prompt: str, user_local_time: Optional[str] = None) -> None:
        worker = Thread(target=self._execute_run, args=(run_id, prompt, user_local_time), daemon=True)
        worker.start()

    def _execute_run(self, run_id: str, prompt: str, user_local_time: Optional[str] = None) -> None:
        try:
            result = run_agent_session(
                prompt, user_local_time=user_local_time, emit_event=lambda *args: self.store.append_event(run_id, *args)
            )
            final_message = result.get("final_message", "")
            artifacts = result.get("artifacts", {})
            if artifacts:
                self.store.merge_artifacts(run_id, artifacts)

            follow_up = self._get_follow_up_clarification(final_message)
            if follow_up is not None:
                question, options = follow_up
                self.store.set_final_message(run_id, final_message, "waiting_for_user")
                self.store.set_waiting(run_id, question, options)
                self.store.append_event(
                    run_id,
                    "waiting_for_user",
                    "Awaiting user input",
                    question,
                    {"options": options},
                )
                return

            self.store.set_final_message(run_id, final_message, "completed")
        except Exception as exc:
            message = f"Agent execution failed: {exc}"
            self.store.append_event(run_id, "failed", "Run failed", message, {})
            self.store.set_final_message(run_id, message, "failed")

    def _get_initial_clarification(self, prompt: str) -> Optional[Tuple[str, List[str]]]:
        lower_prompt = prompt.lower()
        time_options = MULTI_TIME_RE.search(lower_prompt)
        if time_options:
            option_a, option_b = time_options.group(1), time_options.group(2)
            return (
                f"I found two possible meeting times: {option_a} or {option_b}. Which do you prefer?",
                [option_a, option_b],
            )

        if "meeting" in lower_prompt and not EMAIL_RE.search(prompt):
            return (
                "Who should receive the invite and notification email? Please provide an attendee email address.",
                [],
            )
        return None

    def _get_follow_up_clarification(self, final_message: str) -> Optional[Tuple[str, List[str]]]:
        lower_message = final_message.lower()
        if "provide a new meeting time" in lower_message or "provide a new time" in lower_message:
            return ("The requested slot is busy. What new time would you like instead?", [])
        if "which do you prefer" in lower_message:
            return (final_message, [])
        return None

    def get_run_meeting_status(self, run_id: str) -> dict:
        run = self.store.get_run(run_id)
        meet_link = run.artifacts.get("meetLink")
        if not meet_link:
            return {"participants": 0, "hasMeetLink": False}
        
        count = get_meeting_participant_count(meet_link)
        return {
            "participants": count,
            "hasMeetLink": True,
            "meetLink": meet_link
        }
