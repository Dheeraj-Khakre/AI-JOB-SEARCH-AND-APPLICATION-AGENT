"""Checkpointed LangGraph workflow endpoints."""

from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from langgraph.types import Command
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.job_search_orchestrator import (
    GRAPH_RECURSION_LIMIT,
    WorkflowStateError,
    get_workflow_graph,
)
from app.core.exceptions import PortalConnectorError
from app.db.session import get_db
from app.schemas.workflow import WorkflowResponse, WorkflowResumeRequest, WorkflowStartRequest

router = APIRouter(prefix="/workflows", tags=["Agent Workflows"])

VISIBLE_STATE_KEYS = {
    "agent_history",
    "analyzed_jd",
    "approval_status",
    "approval_summary",
    "compatibility_score",
    "current_portal_report",
    "current_agent",
    "discovered_jobs",
    "iteration_count",
    "match_result",
    "selected_job_id",
    "tailored_resume_data",
    "grounding_verified",
    "active_resume_version_id",
    "generated_pdf_path",
    "generated_docx_path",
    "workflow_status"
}


def _graph_config(session_id: UUID, db: AsyncSession) -> dict[str, Any]:
    return {
        "configurable": {
            "thread_id": str(session_id),
            "db_session": db
        },
        "recursion_limit": GRAPH_RECURSION_LIMIT
    }


def _interrupt_payload(snapshot) -> dict[str, Any] | None:
    for task in getattr(snapshot, "tasks", ()):
        for interrupt in getattr(task, "interrupts", ()):
            value = getattr(interrupt, "value", None)
            if isinstance(value, dict):
                return value
    return None


def _response(session_id: UUID, snapshot) -> WorkflowResponse:
    state = snapshot.values or {}
    visible_state = {key: state[key] for key in VISIBLE_STATE_KEYS if key in state}
    return WorkflowResponse(
        session_id=session_id,
        workflow_status=state.get("workflow_status", "RUNNING"),
        current_agent=state.get("current_agent"),
        iteration_count=state.get("iteration_count", 0),
        state=visible_state,
        pending_interrupt=_interrupt_payload(snapshot)
    )


async def _load_snapshot(graph, session_id: UUID, db: AsyncSession):
    config = _graph_config(session_id, db)
    snapshot = await graph.aget_state(config)
    if not snapshot.values:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow session '{session_id}' was not found."
        )
    return config, snapshot


@router.post("/", response_model=WorkflowResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_workflow(
    request: WorkflowStartRequest,
    db: AsyncSession = Depends(get_db)
):
    session_id = request.session_id or uuid4()
    graph = await get_workflow_graph()
    config = _graph_config(session_id, db)

    existing = await graph.aget_state(config)
    if existing.values:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Workflow session '{session_id}' already exists."
        )

    initial_state = request.model_dump(exclude_none=True, mode="python")
    initial_state["session_id"] = str(session_id)
    if request.target_url:
        initial_state["target_url"] = str(request.target_url)

    try:
        await graph.ainvoke(initial_state, config)
    except PortalConnectorError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=exc.message) from exc
    except WorkflowStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.message
        ) from exc

    snapshot = await graph.aget_state(config)
    return _response(session_id, snapshot)


@router.get("/{session_id}", response_model=WorkflowResponse)
async def get_workflow_status(
    session_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    graph = await get_workflow_graph()
    _, snapshot = await _load_snapshot(graph, session_id, db)
    return _response(session_id, snapshot)


@router.post("/{session_id}/resume", response_model=WorkflowResponse)
async def resume_workflow(
    session_id: UUID,
    request: WorkflowResumeRequest,
    db: AsyncSession = Depends(get_db)
):
    graph = await get_workflow_graph()
    config, snapshot = await _load_snapshot(graph, session_id, db)
    if (
        snapshot.values.get("approval_status") != "AWAITING_REVIEW"
        or not _interrupt_payload(snapshot)
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This workflow is not waiting for human review."
        )

    try:
        await graph.ainvoke(Command(resume={"decision": request.decision}), config)
    except WorkflowStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.message
        ) from exc

    snapshot = await graph.aget_state(config)
    return _response(session_id, snapshot)
