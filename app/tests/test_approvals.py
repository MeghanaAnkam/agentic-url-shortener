import pytest

from orchestrator.approvals import request_design_approval
from orchestrator.planner import create_plan
from orchestrator.state import WorkflowState
from orchestrator.storage import load_state


@pytest.mark.parametrize(
    "answer, expected",
    [("approve", "approved"), ("reject", "rejected")],
)
def test_design_approval(tmp_path, monkeypatch, answer, expected):
    state = WorkflowState(requirement="Build a URL shortener")
    create_plan(state)

    design = next(t for t in state.tasks if t.id == "design")
    design.status = "passed"
    state.artifacts["design"] = "Use FastAPI and SQLite."

    monkeypatch.setattr("builtins.input", lambda _: answer)
    checkpoint = tmp_path / "workflow.json"

    request_design_approval(state, checkpoint)

    restored = load_state(checkpoint)
    assert restored.design_approval == expected
    assert restored.release_approval == "pending"


def test_invalid_input_does_not_approve(tmp_path, monkeypatch):
    state = WorkflowState(requirement="Build a URL shortener")
    create_plan(state)

    design = next(t for t in state.tasks if t.id == "design")
    design.status = "passed"
    state.artifacts["design"] = "Use FastAPI and SQLite."

    monkeypatch.setattr("builtins.input", lambda _: "maybe")
    checkpoint = tmp_path / "workflow.json"

    with pytest.raises(ValueError, match="Invalid response"):
        request_design_approval(state, checkpoint)

    assert state.design_approval == "pending"
    assert not checkpoint.exists()