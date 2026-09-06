from pathlib import Path

import pytest

from orchestrator.planner import create_plan
from orchestrator.rollback_candidate import execute_rollback
from orchestrator.state import WorkflowState
from orchestrator.storage import load_state, save_state


def make_applied_state(tmp_path):
    """
    Build a workflow state that looks like implementation was already
    generated, validated, and applied -- i.e. exactly the situation
    rollback_candidate.py is meant to reverse.
    """
    project = tmp_path / "project"
    (project / "app").mkdir(parents=True)

    original_code = "ORIGINAL VERSION\n"
    new_code = "NEW (BAD) VERSION\n"

    target = project / "app" / "main.py"
    target.write_text(new_code, encoding="utf-8")

    backup = project / "main_before_apply.py"
    backup.write_text(original_code, encoding="utf-8")

    state = WorkflowState(requirement="Test rollback")
    create_plan(state)

    implement_task = next(t for t in state.tasks if t.id == "implement")
    implement_task.status = "passed"
    state.artifacts["pre_apply_backup"] = str(backup)

    checkpoint = project / "runs" / "workflow.json"
    save_state(state, checkpoint)

    return state, checkpoint, project, target, original_code, new_code


def test_rollback_restores_original_file(tmp_path):
    state, checkpoint, project, target, original_code, new_code = (
        make_applied_state(tmp_path)
    )

    assert target.read_text(encoding="utf-8") == new_code

    execute_rollback(state, checkpoint, project, reason="Bad candidate")

    assert target.read_text(encoding="utf-8") == original_code


def test_rollback_records_event_and_decision(tmp_path):
    state, checkpoint, project, target, original_code, new_code = (
        make_applied_state(tmp_path)
    )

    execute_rollback(state, checkpoint, project, reason="Bad candidate")

    restored = load_state(checkpoint)

    rollback_events = [
        event
        for event in restored.events
        if event.get("event_type") == "rollback"
    ]
    assert len(rollback_events) == 1
    assert rollback_events[0]["reason"] == "Bad candidate"

    implement_task = next(
        t for t in restored.tasks if t.id == "implement"
    )
    assert implement_task.status == "failed"
    assert restored.release_approval == "pending"
    assert any("Rollback executed" in d for d in restored.decisions)


def test_rollback_requires_applied_implementation(tmp_path):
    state, checkpoint, project, target, original_code, new_code = (
        make_applied_state(tmp_path)
    )

    implement_task = next(t for t in state.tasks if t.id == "implement")
    implement_task.status = "pending"

    with pytest.raises(ValueError, match="Nothing to roll back"):
        execute_rollback(state, checkpoint, project, reason="test")


def test_rollback_requires_a_reason(tmp_path):
    state, checkpoint, project, target, original_code, new_code = (
        make_applied_state(tmp_path)
    )

    with pytest.raises(ValueError, match="reason is required"):
        execute_rollback(state, checkpoint, project, reason="")