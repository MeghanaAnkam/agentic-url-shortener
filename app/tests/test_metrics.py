from orchestrator.metrics import calculate_metrics, calculate_mttr
from orchestrator.state import Task, WorkflowState


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