import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from orchestrator.state import Decision, Task, WorkflowState


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def previous_task_statuses(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    return {
        task["id"]: task["status"]
        for task in data.get("tasks", [])
        if "id" in task and "status" in task
    }


def record_task_transitions(
    state: WorkflowState,
    previous_statuses: dict[str, str],
    timestamp: str,
) -> None:
    for task in state.tasks:
        previous = previous_statuses.get(task.id)

        if previous == task.status:
            continue

        if task.status == "running" and previous != "running":
            task.started_at = timestamp
            task.completed_at = None

        if task.status in {"passed", "failed", "blocked"}:
            task.completed_at = timestamp

        state.events.append(
            {
                "timestamp": timestamp,
                "event_type": "task_transition",
                "task_id": task.id,
                "from_status": previous,
                "to_status": task.status,
                "attempt": task.attempts,
            }
        )


def save_state(state: WorkflowState, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    timestamp = utc_now()
    previous_statuses = previous_task_statuses(path)

    record_task_transitions(
        state,
        previous_statuses,
        timestamp,
    )

    state.updated_at = timestamp

    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(asdict(state), indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)


def load_state(path: Path) -> WorkflowState:
    data = json.loads(path.read_text(encoding="utf-8"))

    data["tasks"] = [
        Task(**task)
        for task in data.get("tasks", [])
    ]

    restored_decisions = []

    for item in data.get("decisions", []):
        if isinstance(item, str):
            restored_decisions.append(
                Decision(
                    actor="legacy",
                    stage="unknown",
                    action="legacy_decision",
                    outcome="recorded",
                    rationale=item,
                )
            )
        elif isinstance(item, dict):
            restored_decisions.append(Decision(**item))
        else:
            raise ValueError(
                f"Unsupported decision format: {type(item).__name__}"
            )

    data["decisions"] = restored_decisions

    return WorkflowState(**data)