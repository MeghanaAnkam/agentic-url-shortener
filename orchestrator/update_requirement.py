import sys
from pathlib import Path
from uuid import uuid4

from orchestrator.storage import load_state, save_state


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Provide the workflow.json path.")

    checkpoint = Path(sys.argv[1])
    state = load_state(checkpoint)

    project = Path(__file__).resolve().parents[1]
    updated = (
        project / "requirements" / "daily_clicks.txt"
    ).read_text(encoding="utf-8").strip()

    if not updated:
        raise SystemExit("Requirement file is empty.")

    if updated == state.requirement:
        raise SystemExit("No requirement changes found.")

    # This update command supports only the current early stage.
    if any(
        task.status == "running"
        or (task.id != "requirements" and task.status != "pending")
        for task in state.tasks
    ):
        raise SystemExit("Later work has started. Impact review required.")

    archive = checkpoint.with_name(f"previous-{uuid4().hex}.json")
    save_state(state, archive)

    state.requirement = updated
    state.artifacts.clear()
    state.design_approval = "pending"
    state.release_approval = "pending"

    for task in state.tasks:
        task.status = "pending"
        task.attempts = 0

    state.decisions.append(
        f"Requirement updated; old outputs and approvals invalidated. "
        f"Previous state: {archive.name}"
    )
    save_state(state, checkpoint)
    print("Requirement updated. Previous workflow archived.")


if __name__ == "__main__":
    main()