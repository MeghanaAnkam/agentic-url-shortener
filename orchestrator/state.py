from dataclasses import dataclass, field
from typing import Literal
from uuid import uuid4


TaskStatus = Literal["pending", "running", "passed", "failed", "blocked"]


@dataclass
class Task:
    id: str
    description: str
    depends_on: list[str] = field(default_factory=list)
    status: TaskStatus = "pending"
    attempts: int = 0


@dataclass
class WorkflowState:
    requirement: str
    run_id: str = field(default_factory=lambda: str(uuid4()))
    tasks: list[Task] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    artifacts: dict[str, str] = field(default_factory=dict)
    design_approval: Literal["pending", "approved", "rejected"] = "pending"
    release_approval: Literal["pending", "approved", "rejected"] = "pending"