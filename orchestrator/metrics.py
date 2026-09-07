import json
import sys
from datetime import datetime
from pathlib import Path

from orchestrator.state import record_decision
from orchestrator.storage import load_state, save_state


def seconds_between(start: str | None, end: str | None):
    if not start or not end:
        return None

    return round(
        (
            datetime.fromisoformat(end)
            - datetime.fromisoformat(start)
        ).total_seconds(),
        3,
    )


def calculate_mttr(events: list[dict]):
    failures = {}
    recovery_times = []

    for event in events:
        if event.get("event_type") != "task_transition":
            continue

        task_id = event.get("task_id")
        status = event.get("to_status")
        timestamp = event.get("timestamp")

        if status == "failed":
            failures[task_id] = timestamp

        if status == "passed" and task_id in failures:
            recovery = seconds_between(
                failures[task_id],
                timestamp,
            )

            if recovery is not None:
                recovery_times.append(recovery)

            del failures[task_id]

    if not recovery_times:
        return None

    return round(
        sum(recovery_times) / len(recovery_times),
        3,
    )


def calculate_metrics(state) -> dict:
    total_tasks = len(state.tasks)
    passed_tasks = sum(
        task.status == "passed"
        for task in state.tasks
    )
    failed_tasks = sum(
        task.status == "failed"
        for task in state.tasks
    )
    blocked_tasks = sum(
        task.status == "blocked"
        for task in state.tasks
    )

    total_attempts = sum(
        task.attempts
        for task in state.tasks
    )

    retry_count = sum(
        max(task.attempts - 1, 0)
        for task in state.tasks
    )

    rollback_count = sum(
        event.get("event_type") == "rollback"
        for event in state.events
    )

    safe_stop_count = sum(
        event.get("to_status") == "blocked"
        for event in state.events
    )

    success_rate = (
        round((passed_tasks / total_tasks) * 100, 2)
        if total_tasks
        else 0.0
    )

    retry_frequency = (
        round((retry_count / total_attempts) * 100, 2)
        if total_attempts
        else 0.0
    )

    task_latencies = {
        task.id: seconds_between(
            task.started_at,
            task.completed_at,
        )
        for task in state.tasks
    }

    return {
        "run_id": state.run_id,
        "total_tasks": total_tasks,
        "passed_tasks": passed_tasks,
        "failed_tasks": failed_tasks,
        "blocked_tasks": blocked_tasks,
        "success_rate_percent": success_rate,
        "total_attempts": total_attempts,
        "retry_count": retry_count,
        "retry_frequency_percent": retry_frequency,
        "rollback_count": rollback_count,
        "safe_stop_count": safe_stop_count,
        "mttr_seconds": calculate_mttr(state.events),
        "end_to_end_latency_seconds": seconds_between(
            state.created_at,
            state.updated_at,
        ),
        "task_latency_seconds": task_latencies,
        "event_count": len(state.events),
        "historical_timing_complete": bool(state.events),
    }


def generate_metrics_report(
    state,
    checkpoint: Path,
) -> dict:
    metrics = calculate_metrics(state)

    json_path = checkpoint.parent / "metrics.json"
    json_path.write_text(
        json.dumps(metrics, indent=2),
        encoding="utf-8",
    )

    markdown_path = Path("reports/reliability-metrics.md")
    markdown_path.parent.mkdir(parents=True, exist_ok=True)

    markdown_path.write_text(
        f"""# Reliability Metrics

Run ID: {state.run_id}

## Results

- Success rate: {metrics["success_rate_percent"]}%
- Passed tasks: {metrics["passed_tasks"]}/{metrics["total_tasks"]}
- Total attempts: {metrics["total_attempts"]}
- Retries: {metrics["retry_count"]}
- Retry frequency: {metrics["retry_frequency_percent"]}%
- Rollbacks: {metrics["rollback_count"]}
- Safe stops: {metrics["safe_stop_count"]}
- MTTR: {metrics["mttr_seconds"]}
- End-to-end latency: {metrics["end_to_end_latency_seconds"]} seconds
- Audit events: {metrics["event_count"]}

## Timing Limitation

Historical timing complete: {metrics["historical_timing_complete"]}

This workflow started before event timestamps were introduced. Therefore,
historical per-stage latency and MTTR may be unavailable. A fresh workflow
must be used to demonstrate complete event timing.
""",
        encoding="utf-8",
    )

    state.artifacts["metrics_json"] = str(json_path)
    state.artifacts["reliability_metrics"] = str(markdown_path)
    record_decision(
        state,
        actor="system:metrics-generator",
        stage="release",
        action="generate_metrics_report",
        outcome="passed",
        rationale=(
            "Reliability metrics generated. Historical timing "
            "limitations were reported without fabricating missing "
            "data."
        ),
    )

    save_state(state, checkpoint)
    return metrics


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python -m orchestrator.metrics "
            "runs/<run-id>/workflow.json"
        )

    checkpoint = Path(sys.argv[1])
    state = load_state(checkpoint)
    metrics = generate_metrics_report(state, checkpoint)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
