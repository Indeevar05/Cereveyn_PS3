from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import run_service
from schemas.runs import (
    CreateRunRequest,
    CreateRunResponse,
    HumanResponseRequest,
    HumanResponseResponse,
    ListRunsResponse,
    RunEventsResponse,
    RunStateModel,
)
from services.run_service import RunService

router = APIRouter(prefix="/runs", tags=["runs"])


def get_run_service() -> RunService:
    return run_service


@router.get("", response_model=ListRunsResponse)
def list_runs(service: RunService = Depends(get_run_service)) -> ListRunsResponse:
    return ListRunsResponse(runs=service.list_runs())


@router.post("", response_model=CreateRunResponse)
def create_run(
    request: CreateRunRequest,
    service: RunService = Depends(get_run_service),
) -> CreateRunResponse:
    return CreateRunResponse(run=service.start_run(request.prompt, request.user_local_time))


@router.get("/{run_id}", response_model=RunStateModel)
def get_run(run_id: str, service: RunService = Depends(get_run_service)) -> RunStateModel:
    try:
        return service.get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc


@router.get("/{run_id}/events", response_model=RunEventsResponse)
def get_run_events(
    run_id: str,
    since: int = Query(default=0, ge=0),
    service: RunService = Depends(get_run_service),
) -> RunEventsResponse:
    try:
        events = service.get_events(run_id, since=since)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc
    next_cursor = events[-1].id if events else since
    return RunEventsResponse(events=events, next_cursor=next_cursor)


@router.post("/{run_id}/respond", response_model=HumanResponseResponse)
def respond_to_run(
    run_id: str,
    request: HumanResponseRequest,
    service: RunService = Depends(get_run_service),
) -> HumanResponseResponse:
    try:
        run = service.respond_to_run(run_id, request.response_text, request.user_local_time)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc
    return HumanResponseResponse(run=run)


@router.delete("/{run_id}", status_code=204)
def delete_run(run_id: str, service: RunService = Depends(get_run_service)) -> None:
    service.delete_run(run_id)


@router.get("/{run_id}/meeting-status")
def get_meeting_status(run_id: str, service: RunService = Depends(get_run_service)):
    try:
        return service.get_run_meeting_status(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc
