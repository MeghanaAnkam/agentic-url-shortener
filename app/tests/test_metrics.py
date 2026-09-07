from orchestrator.metrics import (
    calculate_metrics,
    calculate_mttr,
    generate_metrics_report,
)
from orchestrator.state import Task, WorkflowState
from orchestrator.storage import load_state, save_state


def test_metrics_calculate_success_and_retries():
    state = WorkflowState(requirement="Metrics test")
    state.tasks = [
        Task(
            id="one",
            description="Passed task",
            status="passed",
            attempts=2,
        ),
        Task(
            id="two",
            description="Failed task",
            status="failed",
            attempts=1,
        ),
    ]

    metrics = calculate_metrics(state)

    assert metrics["total_tasks"] == 2
    assert metrics["passed_tasks"] == 1
    assert metrics["failed_tasks"] == 1
    assert metrics["success_rate_percent"] == 50.0
    assert metrics["retry_count"] == 1


def test_mttr_is_calculated_from_failure_and_recovery():
    events = [
        {
            "timestamp": "2026-09-06T05:00:00+00:00",
            "event_type": "task_transition",
            "task_id": "tests",
            "to_status": "failed",
        },
        {
            "timestamp": "2026-09-06T05:00:30+00:00",
            "event_type": "task_transition",
            "task_id": "tests",
            "to_status": "passed",
        },
    ]

    assert calculate_mttr(events) == 30.0


def test_metrics_report_missing_history_honestly():
    state = WorkflowState(requirement="Old workflow")
    state.tasks = [
        Task(
            id="requirements",
            description="Requirement",
            status="passed",
            attempts=1,
        )
    ]

    metrics = calculate_metrics(state)

    assert metrics["event_count"] == 0
    assert metrics["historical_timing_complete"] is False
    assert metrics["mttr_seconds"] is None


def test_generate_metrics_report_records_structured_decision(tmp_path):
    state = WorkflowState(requirement="Metrics decision test")
    state.tasks = [
        Task(
            id="one",
            description="Passed task",
            status="passed",
            attempts=1,
        ),
    ]

    checkpoint = tmp_path / "workflow.json"
    save_state(state, checkpoint)

    generate_metrics_report(state, checkpoint)

    restored = load_state(checkpoint)
    metrics_decisions = [
        decision
        for decision in restored.decisions
        if decision.action == "generate_metrics_report"
    ]
    assert len(metrics_decisions) == 1
    assert metrics_decisions[0].actor == "system:metrics-generator"
