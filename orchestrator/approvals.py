from pathlib import Path

from orchestrator.state import WorkflowState, record_decision
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
    record_decision(
        state,
        actor="human:design-reviewer",
        stage="design",
        action="review_design",
        outcome=state.design_approval,
        rationale="Local human design review completed.",
    )
    save_state(state, checkpoint)
    print("Design approval:", state.design_approval)

def request_release_approval(
    state: WorkflowState,
    checkpoint: Path,
) -> None:
    required_tasks = {"tests", "security", "compliance", "docs"}

    statuses = {
        task.id: task.status
        for task in state.tasks
        if task.id in required_tasks
    }

    incomplete = [
        task_id
        for task_id in required_tasks
        if statuses.get(task_id) != "passed"
    ]

    if incomplete:
        raise ValueError(
            f"Release blocked. Incomplete tasks: {sorted(incomplete)}"
        )

    print("\nRELEASE READINESS REVIEW")
    print("Run ID:", state.run_id)
    print("Requirement:", state.requirement)

    print("\nRequired gates:")
    for task_id in sorted(required_tasks):
        print(f"- {task_id}: {statuses[task_id]}")

    answer = input(
        "\nType approve or reject: "
    ).strip().lower()

    if answer not in {"approve", "reject"}:
        raise ValueError(
            "Invalid response. No approval recorded."
        )

    rationale = input(
        "Enter your decision rationale: "
    ).strip()

    if not rationale:
        raise ValueError(
            "Rationale is required. No approval recorded."
        )

    state.release_approval = (
        "approved" if answer == "approve" else "rejected"
    )

    record_decision(
        state,
        actor="human:release-reviewer",
        stage="release",
        action="review_release",
        outcome=state.release_approval,
        rationale=rationale,
    )

    save_state(state, checkpoint)

    print("Release approval:", state.release_approval)
    print("No deployment was performed.")
