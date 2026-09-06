from pathlib import Path

from orchestrator.planner import create_plan
from orchestrator.state import WorkflowState
from orchestrator.storage import save_state


def main():
    project = Path(__file__).resolve().parents[1]
    requirement_file = project / "requirements" / "daily_clicks.txt"
    requirement = requirement_file.read_text(encoding="utf-8").strip()

    if not requirement:
        raise SystemExit("The requirement file is empty.")

    state = WorkflowState(requirement=requirement)
    create_plan(state)

    checkpoint = project / "runs" / state.run_id / "workflow.json"
    save_state(state, checkpoint)

    print("Workflow created:", state.run_id)
    print("Saved to:", checkpoint)
    print("Requirements are pending review. No code was changed.")


if __name__ == "__main__":
    main()