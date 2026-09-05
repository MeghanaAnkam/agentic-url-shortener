from pathlib import Path

from orchestrator.state import WorkflowState
from orchestrator.storage import save_state


def request_design_approval(
    state: WorkflowState,
    checkpoint: Path,
) -> None:
    design = next(t for t in state.tasks if t.id == "design")

    if design.status != "passed":
        raise ValueError("Design must be completed before approval.")

    proposal = state.artifacts.get("design")
    if not proposal:
        raise ValueError("No design document available to review.")

    print("\nRequirement:", state.requirement)
    print("\nDesign to review:\n", proposal)

    answer = input("\nType approve or reject: ").strip().lower()

    if answer not in {"approve", "reject"}:
        raise ValueError("Invalid response. No approval recorded.")

    state.design_approval = (
        "approved" if answer == "approve" else "rejected"
    )
    state.decisions.append(
        f"Local human review: design {state.design_approval}."
    )
    save_state(state, checkpoint)
    print("Design approval:", state.design_approval)