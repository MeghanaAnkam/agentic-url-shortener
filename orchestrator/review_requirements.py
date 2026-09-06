import sys
from pathlib import Path

from orchestrator.requirements_agent import analyze_requirement
from orchestrator.scheduler import ready_tasks
from orchestrator.storage import load_state, save_state


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Provide the workflow.json path.")

    checkpoint = Path(sys.argv[1])
    state = load_state(checkpoint)

    if "requirements" not in ready_tasks(state):
        raise SystemExit("Requirements task is not ready.")

    task = next(t for t in state.tasks if t.id == "requirements")
    task.status = "running"
    task.attempts += 1
    save_state(state, checkpoint)

    try:
        analysis = analyze_requirement(state.requirement)
    except Exception as error:
        task.status = "failed"
        state.decisions.append(
            f"Requirements analysis failed: {type(error).__name__}"
        )
        save_state(state, checkpoint)
        raise SystemExit("Analysis failed. Workflow saved as failed.")

    state.artifacts["requirements_analysis"] = analysis
    task.status = "blocked"
    state.decisions.append(
        "AI analysis saved. Human requirements review is required."
    )
    save_state(state, checkpoint)

    print(analysis)
    print("\nSaved. Design remains blocked pending human review.")


if __name__ == "__main__":
    main()