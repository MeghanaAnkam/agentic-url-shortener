from pathlib import Path
from tempfile import TemporaryDirectory

from orchestrator.approvals import request_design_approval
from orchestrator.planner import create_plan
from orchestrator.scheduler import ready_tasks
from orchestrator.state import WorkflowState
from orchestrator.storage import load_state


def main():
    state = WorkflowState(requirement="Build a URL shortener")
    create_plan(state)

    # Demo setup only—not work performed by AI agents.
    for task in state.tasks:
        if task.id in {"requirements", "design"}:
            task.status = "passed"

    state.artifacts["design"] = (
        "LOCAL DEMO DESIGN:\n"
        "- FastAPI endpoints: shorten, redirect, analytics.\n"
        "- SQLite stores links and click counts.\n"
        "- Accept only HTTP/HTTPS URLs.\n"
        "- No public deployment in this demo."
    )

    print("Ready before approval:", ready_tasks(state))

    with TemporaryDirectory() as directory:
        checkpoint = Path(directory) / "workflow.json"
        request_design_approval(state, checkpoint)

        restored = load_state(checkpoint)
        print("Ready after review:", ready_tasks(restored))


if __name__ == "__main__":
    main()