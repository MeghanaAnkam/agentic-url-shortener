import sys
from pathlib import Path

from orchestrator.scheduler import ready_tasks
from orchestrator.state import record_decision
from orchestrator.storage import load_state, save_state


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Provide the workflow.json path.")

    checkpoint = Path(sys.argv[1])
    state = load_state(checkpoint)
    task = next(t for t in state.tasks if t.id == "requirements")

    analysis = state.artifacts.get("requirements_analysis")
    if task.status != "blocked" or not analysis:
        raise SystemExit("No requirements analysis awaiting review.")

    print("\nREQUIREMENT:\n", state.requirement)
    print("\nAI REVIEW:\n", analysis)

    note = input("\nYour review decision/rationale: ").strip()
    if not note:
        raise SystemExit("Review rationale is required.")

    answer = input("\nType approve or reject: ").strip().lower()
    if answer not in {"approve", "reject"}:
        raise SystemExit("Invalid response. Nothing changed.")

    task.status = "passed" if answer == "approve" else "blocked"
    record_decision(
    state,
    actor="human:requirements-reviewer",
    stage="requirements",
    action="review_requirement",
    outcome="approved" if answer == "approve" else "rejected",
    rationale=note,
)
    save_state(state, checkpoint)

    print("Decision saved.")
    print("Ready tasks:", ready_tasks(state))


if __name__ == "__main__":
    main()