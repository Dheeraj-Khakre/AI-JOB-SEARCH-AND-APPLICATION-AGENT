# Phase 7: LangGraph Agent Orchestration

Phase 7 adds a checkpointed workflow that composes the available Phase 5 and 6
agents. The graph currently supports job discovery, portal inspection, JD
analysis, candidate compatibility scoring, and an optional human-review pause.
Resume optimization, application automation, interview preparation, and
tracking remain separate future phases and are not simulated by this graph.

## Workflow state and graph

`JobSearchAppState` is defined in
[`backend/app/agents/job_search_state.py`](../backend/app/agents/job_search_state.py).
It tracks the workflow/session identifiers, selected job and profile, discovery
results, portal report, analyzed requirements, match result, approval status,
current agent, transition history, and bounded iteration count. Raw JD text may
be kept in local checkpoint state; candidate master facts and secrets are not
copied into workflow state or returned by the workflow API.

The graph in
[`backend/app/agents/job_search_orchestrator.py`](../backend/app/agents/job_search_orchestrator.py)
selects one of three entry routes:

- `discover`: searches connectors for an active job profile.
- `inspect`: inspects a target portal URL.
- `analyze`: analyzes supplied JD text or the description for a selected job.

Analysis can proceed to compatibility scoring when both a job and target profile
are specified. Search and analysis use the Phase 6 agents and save supported
results through the existing database models. Each node records the current
agent and transition history; the graph enforces a 12-agent iteration budget
and a LangGraph recursion limit.

## Checkpointing and human review

Workflow checkpoints are stored locally in
`<DATA_DIR>/db/workflow_checkpoints.sqlite3` using
`langgraph-checkpoint-sqlite`. Each workflow uses a UUID session ID as its
LangGraph `thread_id`, allowing status retrieval and resume across requests and
process restarts.

Set `require_human_approval` to pause the workflow after its analysis/scoring
result. The graph emits a `human_review_required` interrupt with a concise
summary and sets the status to `AWAITING_REVIEW`. `approve` or `reject` resumes
that thread. This is a review checkpoint only: it does not submit an application
and does not issue or replace the cryptographic, single-use submission approval
required by the application assistant.

## API

- `POST /api/v1/workflows/` — start a workflow; returns HTTP 202 and its current
  state, including any pending interrupt.
- `GET /api/v1/workflows/{session_id}` — retrieve checkpointed status.
- `POST /api/v1/workflows/{session_id}/resume` — resume a review checkpoint
  with `{"decision": "approve"}` or `{"decision": "reject"}`.

Example request:

```json
{
  "mode": "analyze",
  "raw_jd_text": "The job description text, at least 20 characters long.",
  "require_human_approval": true
}
```

The API response intentionally omits raw JD text and candidate master facts.
