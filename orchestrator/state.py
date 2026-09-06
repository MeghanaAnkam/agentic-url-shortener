from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4


TaskStatus = Literal[
    "pending",
    "running",
    "passed",
    "failed",
    "blocked",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Task:
    id: str
    description: str
    depends_on: list[str] = field(default_factory=list)
    status: TaskStatus = "pending"
    attempts: int = 0
    started_at: str | None = None
    completed_at: str | None = None


@dataclass
class Decision:
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=utc_now)
    actor: str = "system"
    stage: str = "workflow"
    action: str = ""
    outcome: str = ""
    rationale: str = ""
    artifact_hashes: dict[str, str] = field(default_factory=dict)
    supersedes: str | None = None


@dataclass
class WorkflowState:
    requirement: str
    run_id: str = field(default_factory=lambda: str(uuid4()))
    tasks: list[Task] = field(default_factory=list)
    decisions: list[Decision] = field(default_factory=list)
    artifacts: dict[str, str] = field(default_factory=dict)
    design_approval: Literal[
        "pending", "approved", "rejected"
    ] = "pending"
    release_approval: Literal[
        "pending", "approved", "rejected"
    ] = "pending"
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    events: list[dict[str, Any]] = field(default_factory=list)


def record_decision(
    state: WorkflowState,
    *,
    actor: str,
    stage: str,
    action: str,
    outcome: str,
    rationale: str,
    artifact_hashes: dict[str, str] | None = None,
    supersedes: str | None = None,
) -> Decision:
    decision = Decision(
        actor=actor,
        stage=stage,
        action=action,
        outcome=outcome,
        rationale=rationale,
        artifact_hashes=artifact_hashes or {},
        supersedes=supersedes,
    )
    state.decisions.append(decision)
    return decision