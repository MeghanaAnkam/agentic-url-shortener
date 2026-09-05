import pytest
import orchestrator.executor as executor

from orchestrator.planner import create_plan
from orchestrator.state import WorkflowState
from orchestrator.storage import load_state


def test_executor_blocks_when_dependencies_are_pending(tmp_path, monkeypatch):
    state = WorkflowState(requirement="Build a URL shortener")
    create_plan(state)

    def forbidden_run():
        pytest.fail("Tests must not run before dependencies pass.")

    monkeypatch.setattr(executor, "run_api_tests", forbidden_run)
    checkpoint = tmp_path / "workflow.json"

    with pytest.raises(ValueError):
        executor.execute_tests(state, checkpoint)

    assert not checkpoint.exists()
    task = next(t for t in state.tasks if t.id == "tests")
    assert task.attempts == 0


@pytest.mark.parametrize("result", ["passed", "failed"])
def test_executor_saves_result(tmp_path, monkeypatch, result):
    state = WorkflowState(requirement="Build a URL shortener")
    create_plan(state)

    # Simulate completed upstream work for this isolated test.
    for task in state.tasks:
        if task.id in {"requirements", "design", "implement"}:
            task.status = "passed"

    checkpoint = tmp_path / "workflow.json"

    def fake_run():
        saved = load_state(checkpoint)
        task = next(t for t in saved.tasks if t.id == "tests")
        assert task.status == "running"
        assert task.attempts == 1
        return {"status": result, "output": "Simulated test output"}

    monkeypatch.setattr(executor, "run_api_tests", fake_run)
    executor.execute_tests(state, checkpoint)

    restored = load_state(checkpoint)
    task = next(t for t in restored.tasks if t.id == "tests")

    assert task.status == result
    assert task.attempts == 1
    assert restored.artifacts["test_output"] == "Simulated test output"


def test_runner_error_saves_failed_state(tmp_path, monkeypatch):
    state = WorkflowState(requirement="Build a URL shortener")
    create_plan(state)

    for task in state.tasks:
        if task.id in {"requirements", "design", "implement"}:
            task.status = "passed"

    def broken_runner():
        raise RuntimeError("Unexpected runner failure")

    monkeypatch.setattr(executor, "run_api_tests", broken_runner)
    checkpoint = tmp_path / "workflow.json"

    with pytest.raises(RuntimeError):
        executor.execute_tests(state, checkpoint)

    restored = load_state(checkpoint)
    task = next(t for t in restored.tasks if t.id == "tests")

    assert task.status == "failed"
    assert task.attempts == 1
    assert "Unexpected runner failure" in restored.artifacts["test_output"]

def test_retry_limit(tmp_path, monkeypatch):
    state = WorkflowState(requirement="Build a URL shortener")
    create_plan(state)

    for task in state.tasks:
        if task.id in {"requirements", "design", "implement"}:
            task.status = "passed"

    calls = []

    def failing_runner():
        calls.append("called")
        return {"status": "failed", "output": "Simulated failure"}

    monkeypatch.setattr(executor, "run_api_tests", failing_runner)
    checkpoint = tmp_path / "workflow.json"

    # Original attempt.
    executor.execute_tests(state, checkpoint)

    # One permitted retry.
    executor.retry_tests(state, checkpoint)

    # A third attempt must be refused.
    with pytest.raises(ValueError, match="Retry limit"):
        executor.retry_tests(state, checkpoint)

    restored = load_state(checkpoint)
    task = next(t for t in restored.tasks if t.id == "tests")

    assert len(calls) == 2
    assert task.attempts == 2
    assert task.status == "blocked"
    assert "Human review required" in restored.decisions[-1]