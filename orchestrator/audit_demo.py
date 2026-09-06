import time
from pathlib import Path
from tempfile import TemporaryDirectory

from orchestrator.metrics import generate_metrics_report
from orchestrator.planner import create_plan
from orchestrator.rollback_candidate import execute_rollback
from orchestrator.scheduler import ready_tasks
from orchestrator.state import WorkflowState, record_decision
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


def simulate_apply_and_rollback(state, checkpoint, demo_project: Path) -> None:
    """
    Demonstrates the rollback control path using isolated demo files,
    never touching the real app/main.py. Simulates: a candidate was
    applied, a problem was found, and a human rolled it back.
    """
    (demo_project / "app").mkdir(parents=True, exist_ok=True)

    backup = demo_project / "main_before_apply.py"
    target = demo_project / "app" / "main.py"

    backup.write_text("DEMO VERSION 1 (known good)\n", encoding="utf-8")
    target.write_text("DEMO VERSION 2 (bad candidate)\n", encoding="utf-8")

    state.artifacts["pre_apply_backup"] = str(backup)

    execute_rollback(
        state,
        checkpoint,
        project=demo_project,
        reason=(
            "Controlled audit demonstration: reverting a simulated "
            "bad candidate to exercise the rollback control path."
        ),
    )


def main():
    state = WorkflowState(
        requirement=(
            "Demonstrate audit events, bounded retry, rollback, "
            "recovery, approvals, synchronization, and reliability "
            "metrics."
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
    record_decision(
        state,
        actor="human:design-reviewer",
        stage="design",
        action="review_design",
        outcome="approved",
        rationale="Human approved deterministic audit demonstration design.",
    )
    save_state(state, checkpoint)

    transition(state, checkpoint, "implement", "running")
    transition(state, checkpoint, "implement", "passed")

    # Controlled apply-then-rollback, using isolated demo files.
    with TemporaryDirectory() as demo_directory:
        simulate_apply_and_rollback(
            state, checkpoint, Path(demo_directory)
        )

        # Human-approved corrected re-implementation after rollback.
        task_by_id(state, "implement").status = "pending"
        save_state(state, checkpoint)

        transition(state, checkpoint, "implement", "running")
        transition(state, checkpoint, "implement", "passed")

    # Controlled first-attempt test failure.
    transition(state, checkpoint, "tests", "running")
    transition(state, checkpoint, "tests", "failed")

    record_decision(
        state,
        actor="system:test-runner",
        stage="tests",
        action="run_tests",
        outcome="failed",
        rationale="Controlled test failure recorded; bounded retry authorized.",
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
    record_decision(
        state,
        actor="human:release-reviewer",
        stage="release",
        action="review_release",
        outcome="approved",
        rationale="Human approved local release-readiness demonstration.",
    )
    save_state(state, checkpoint)

    transition(state, checkpoint, "release", "running")
    transition(state, checkpoint, "release", "passed")

    metrics = generate_metrics_report(state, checkpoint)

    print("Audit demo completed")
    print("Checkpoint:", checkpoint)
    print("Events:", len(state.events))
    print("Retries:", metrics["retry_count"])
    print("Rollbacks:", metrics["rollback_count"])
    print("MTTR seconds:", metrics["mttr_seconds"])
    print(
        "End-to-end latency:",
        metrics["end_to_end_latency_seconds"],
    )


if __name__ == "__main__":
    main()