from pathlib import Path

from orchestrator.planner import create_plan
from orchestrator.security_agent import (
    find_dangerous_python_calls,
    find_tracked_secrets,
    run_security_review,
    verify_application_controls,
)
from orchestrator.state import WorkflowState
from orchestrator.storage import load_state, save_state


def test_security_check_detects_tracked_env():
    findings = find_tracked_secrets(
        [".env", "app/main.py"]
    )

    assert findings == ["Sensitive file is tracked: .env"]


def test_security_check_detects_private_key():
    findings = find_tracked_secrets(
        ["certificates/server.pem"]
    )

    assert findings == [
        "Private-key file is tracked: certificates/server.pem"
    ]


def test_repository_has_no_dangerous_python_calls():
    findings = find_dangerous_python_calls(Path.cwd())

    assert findings == []


def test_application_security_controls_exist():
    findings = verify_application_controls(Path.cwd())

    assert findings == []


def test_run_security_review_records_structured_decision(tmp_path):
    state = WorkflowState(requirement="Test security decision recording")
    create_plan(state)

    for task in state.tasks:
        if task.id == "implement":
            task.status = "passed"

    checkpoint = tmp_path / "workflow.json"
    save_state(state, checkpoint)

    report = run_security_review(state, checkpoint)

    restored = load_state(checkpoint)
    security_decisions = [
        decision
        for decision in restored.decisions
        if decision.action == "run_security_review"
    ]
    assert len(security_decisions) == 1
    assert security_decisions[0].outcome == report["status"]
    assert security_decisions[0].actor == "system:security-checker"
