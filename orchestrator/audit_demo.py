import time
from pathlib import Path

from orchestrator.metrics import generate_metrics_report
from orchestrator.planner import create_plan
from orchestrator.scheduler import ready_tasks
from orchestrator.state import WorkflowState
from orchestrator.storage import save_state


def task_by_id(state, task_id):
    return next(task for task in state.tasks if task.id == task_id)


def transition(state, checkpoint, task_id, status):
    task = task_by_id(state, task_id)

    if status == "running":
        if task_id not in ready_tasks(state):
            raise ValueError(f"{task_id} is not ready")

        task.attempts += 1

    task.status = status
    save_state(state, checkpoint)
    time.sleep(0.02)


def main():
    state = WorkflowState(
        requirement=(
            "Demonstrate audit events, bounded retry, recovery, "
            "approvals, synchronization, and reliability metrics."
        )
    )

    create_plan(state)

    run_folder = Path("runs") / f"audit-demo-{state.run_id}"
    checkpoint = run_folder / "workflow.json"

    save_state(state, checkpoint)

    transition(state, checkpoint, "requirements", "running")
    transition(state, checkpoint, "requirements", "passed")

    transition(state, checkpoint, "design", "running")
    transition(state, checkpoint, "design", "passed")

    state.design_approval = "approved"
    state.decisions.append(
        "Human approved deterministic audit demonstration design."
    )
    save_state(state, checkpoint)

    transition(state, checkpoint, "implement", "running")
    transition(state, checkpoint, "implement", "passed")

    # Controlled first-attempt failure.
    transition(state, checkpoint, "tests", "running")
    transition(state, checkpoint, "tests", "failed")

    state.decisions.append(
        "Controlled test failure recorded; bounded retry authorized."
    )

    task_by_id(state, "tests").status = "pending"
    save_state(state, checkpoint)

    transition(state, checkpoint, "tests", "running")
    transition(state, checkpoint, "tests", "passed")

    transition(state, checkpoint, "security", "running")
    transition(state, checkpoint, "security", "passed")

    transition(state, checkpoint, "docs", "running")
    transition(state, checkpoint, "docs", "passed")

    state.release_approval = "approved"
    state.decisions.append(
        "Human approved local release-readiness demonstration."
    )
    save_state(state, checkpoint)

    transition(state, checkpoint, "release", "running")
    transition(state, checkpoint, "release", "passed")

    metrics = generate_metrics_report(state, checkpoint)

    print("Audit demo completed")
    print("Checkpoint:", checkpoint)
    print("Events:", len(state.events))
    print("Retries:", metrics["retry_count"])
    print("MTTR seconds:", metrics["mttr_seconds"])
    print(
        "End-to-end latency:",
        metrics["end_to_end_latency_seconds"],
    )


if __name__ == "__main__":
    main()
    