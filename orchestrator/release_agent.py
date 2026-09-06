import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from orchestrator.scheduler import ready_tasks
from orchestrator.state import record_decision
from orchestrator.storage import load_state, save_state


def execute_release(state, checkpoint: Path) -> dict:
    if "release" not in ready_tasks(state):
        raise ValueError(
            "Release is blocked by prerequisites or human approval."
        )

    task = next(item for item in state.tasks if item.id == "release")
    task.status = "running"
    task.attempts += 1
    save_state(state, checkpoint)

    try:
        required = {"tests", "security", "compliance", "docs"}
        statuses = {
            item.id: item.status
            for item in state.tasks
            if item.id in required
        }

        if any(statuses.get(name) != "passed" for name in required):
            raise ValueError("A required release gate is not passed.")

        completed_at = datetime.now(timezone.utc).isoformat()

        report = {
            "run_id": state.run_id,
            "status": "release_ready",
            "completed_at": completed_at,
            "release_approval": state.release_approval,
            "gates": statuses,
            "deployment_performed": False,
            "artifacts": state.artifacts,
            "limitations": [
                "Local prototype only",
                "No production deployment performed",
                "SQLite supports limited write concurrency",
                "Authentication and rate limiting are not implemented",
            ],
        }

        report_path = checkpoint.parent / "release_report.json"
        report_path.write_text(
            json.dumps(report, indent=2),
            encoding="utf-8",
        )

        summary_path = Path("reports/release-readiness.md")
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(
            f"""# Release Readiness Report

Run ID: {state.run_id}

Status: Release ready

Completed: {completed_at}

## Gates

- Tests: {statuses["tests"]}
- Security: {statuses["security"]}
- Compliance: {statuses["compliance"]}
- Documentation: {statuses["docs"]}
- Human approval: {state.release_approval}

## Deployment

No production deployment was performed.

## Limitations

- Local prototype only
- SQLite has limited write concurrency
- Authentication is not implemented
- Rate limiting is not implemented
""",
            encoding="utf-8",
        )

        task.status = "passed"
        state.artifacts["release_report"] = str(report_path)
        state.artifacts["release_readiness"] = str(summary_path)
        record_decision(
            state,
            actor="agent:release",
            stage="release",
            action="prepare_release",
            outcome="release_ready",
            rationale=(
                "Release-readiness gates passed after human approval. "
                "No deployment was performed."
            ),
        )
        save_state(state, checkpoint)

        return report

    except Exception as error:
        task.status = "failed"
        record_decision(
            state,
            actor="agent:release",
            stage="release",
            action="prepare_release",
            outcome="failed",
            rationale=(
                f"Release failed safely: {type(error).__name__}: {error}"
            ),
        )
        save_state(state, checkpoint)
        raise


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python -m orchestrator.release_agent "
            "runs/<run-id>/workflow.json"
        )

    checkpoint = Path(sys.argv[1])
    state = load_state(checkpoint)
    report = execute_release(state, checkpoint)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
