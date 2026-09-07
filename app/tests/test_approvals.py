import pytest

from orchestrator.approvals import (
    request_design_approval,
    request_release_approval,
)
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

    design_events = [
        event
        for event in restored.events
        if event.get("event_type") == "design_approval"
    ]
    assert len(design_events) == 1
    assert design_events[0]["outcome"] == expected


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


def make_state_with_gates(tmp_path, *, security="passed", compliance="passed"):
    """
    Builds a workflow where tests/docs are always passed, and
    security/compliance can be set to any status -- used to prove
    release approval is genuinely blocked by either gate, not just
    by an unfinished task list.
    """
    state = WorkflowState(requirement="Build a URL shortener")
    create_plan(state)

    for task in state.tasks:
        if task.id == "tests":
            task.status = "passed"
        elif task.id == "docs":
            task.status = "passed"
        elif task.id == "security":
            task.status = security
        elif task.id == "compliance":
            task.status = compliance

    checkpoint = tmp_path / "workflow.json"
    return state, checkpoint


def test_release_approval_blocked_by_failed_security(tmp_path):
    state, checkpoint = make_state_with_gates(tmp_path, security="failed")

    with pytest.raises(ValueError, match="security"):
        request_release_approval(state, checkpoint)

    assert state.release_approval == "pending"
    assert not checkpoint.exists()


def test_release_approval_blocked_by_failed_compliance(tmp_path):
    state, checkpoint = make_state_with_gates(
        tmp_path, compliance="failed"
    )

    with pytest.raises(ValueError, match="compliance"):
        request_release_approval(state, checkpoint)

    assert state.release_approval == "pending"
    assert not checkpoint.exists()


def test_release_approval_blocked_by_incomplete_gates(tmp_path):
    state, checkpoint = make_state_with_gates(
        tmp_path, security="pending", compliance="pending"
    )

    with pytest.raises(ValueError, match="Incomplete tasks"):
        request_release_approval(state, checkpoint)


@pytest.mark.parametrize(
    "answer, expected",
    [("approve", "approved"), ("reject", "rejected")],
)
def test_release_approval_records_decision_once_gates_pass(
    tmp_path, monkeypatch, answer, expected
):
    state, checkpoint = make_state_with_gates(tmp_path)

    responses = iter([answer, "Reviewed and decided."])
    monkeypatch.setattr("builtins.input", lambda _: next(responses))

    request_release_approval(state, checkpoint)

    restored = load_state(checkpoint)
    assert restored.release_approval == expected

    release_decisions = [
        decision
        for decision in restored.decisions
        if decision.action == "review_release"
    ]
    assert len(release_decisions) == 1
    assert release_decisions[0].outcome == expected
    assert release_decisions[0].rationale == "Reviewed and decided."

    release_events = [
        event
        for event in restored.events
        if event.get("event_type") == "release_approval"
    ]
    assert len(release_events) == 1
    assert release_events[0]["outcome"] == expected


def test_release_approval_requires_rationale(tmp_path, monkeypatch):
    state, checkpoint = make_state_with_gates(tmp_path)

    responses = iter(["approve", ""])
    monkeypatch.setattr("builtins.input", lambda _: next(responses))

    with pytest.raises(ValueError, match="Rationale is required"):
        request_release_approval(state, checkpoint)

    assert state.release_approval == "pending"


def test_release_approval_rejects_invalid_answer(tmp_path, monkeypatch):
    state, checkpoint = make_state_with_gates(tmp_path)

    monkeypatch.setattr("builtins.input", lambda _: "maybe")

    with pytest.raises(ValueError, match="Invalid response"):
        request_release_approval(state, checkpoint)

    assert state.release_approval == "pending"
