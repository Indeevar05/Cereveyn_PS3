from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


RunStatus = Literal["running", "waiting_for_user", "completed", "failed"]
RunEventType = Literal[
    "run_started",
    "model_thinking",
    "tool_requested",
    "tool_succeeded",
    "tool_failed",
    "waiting_for_user",
    "completed",
    "failed",
]


class RunEventModel(BaseModel):
    id: int
    type: RunEventType
    title: str
    detail: str
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime


class RunStateModel(BaseModel):
    id: str
    prompt: str
    status: RunStatus
    final_message: Optional[str] = None
    clarification_prompt: Optional[str] = None
    clarification_options: List[str] = Field(default_factory=list)
    artifacts: Dict[str, Any] = Field(default_factory=dict)
    events: List[RunEventModel] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class CreateRunRequest(BaseModel):
    prompt: str = Field(min_length=1)
    user_local_time: Optional[str] = None


class CreateRunResponse(BaseModel):
    run: RunStateModel


class ListRunsResponse(BaseModel):
    runs: List[RunStateModel]


class RunEventsResponse(BaseModel):
    events: List[RunEventModel]
    next_cursor: int


class HumanResponseRequest(BaseModel):
    response_text: str = Field(min_length=1)
    user_local_time: Optional[str] = None


class HumanResponseResponse(BaseModel):
    run: RunStateModel
