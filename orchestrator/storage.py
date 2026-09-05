import json
from dataclasses import asdict
from pathlib import Path

from orchestrator.state import Task, WorkflowState


def save_state(state: WorkflowState, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(asdict(state), indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)


def load_state(path: Path) -> WorkflowState:
    data = json.loads(path.read_text(encoding="utf-8"))
    data["tasks"] = [Task(**task) for task in data["tasks"]]
    return WorkflowState(**data)