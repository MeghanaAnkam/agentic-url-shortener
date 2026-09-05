from pathlib import Path

from orchestrator.scheduler import ready_tasks
from orchestrator.state import WorkflowState
from orchestrator.storage import save_state
from orchestrator.test_runner import run_api_tests


def execute_tests(state: WorkflowState, checkpoint: Path) -> None:
    if "tests" not in ready_tasks(state):
        raise ValueError("Tests cannot start: dependencies are not passed.")

    task = next(t for t in state.tasks if t.id == "tests")
    task.status = "running"
    task.attempts += 1
    save_state(state, checkpoint)

    try:
        report = run_api_tests()
    except Exception as error:
        task.status = "failed"
        state.artifacts["test_output"] = (
            f"Runner error: {type(error).__name__}: {error}"
        )
        save_state(state, checkpoint)
        raise

    task.status = report["status"]
    state.artifacts["test_output"] = report["output"]
    save_state(state, checkpoint)

def retry_tests(state: WorkflowState, checkpoint: Path) -> None:
    task = next(t for t in state.tasks if t.id == "tests")

    if task.status != "failed":
        raise ValueError("Only a failed test task can be retried.")

    if task.attempts >= 2:
        task.status = "blocked"
        state.decisions.append(
            "Test attempt limit reached. Human review required."
        )
        save_state(state, checkpoint)
        raise ValueError("Retry limit reached. Human review required.")

    task.status = "pending"
    save_state(state, checkpoint)
    execute_tests(state, checkpoint)