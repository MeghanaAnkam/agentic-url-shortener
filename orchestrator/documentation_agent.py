import sys
from datetime import datetime, timezone
from pathlib import Path

from orchestrator.scheduler import ready_tasks
from orchestrator.state import WorkflowState
from orchestrator.storage import load_state, save_state


def write_document(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def generate_documentation(
    state: WorkflowState,
    checkpoint: Path,
    project_root: Path | None = None,
) -> list[Path]:
    if "docs" not in ready_tasks(state):
        raise ValueError(
            "Documentation cannot start: dependencies are not passed."
        )

    root = project_root or Path.cwd()
    task = next(item for item in state.tasks if item.id == "docs")

    task.status = "running"
    task.attempts += 1
    save_state(state, checkpoint)

    generated_at = datetime.now(timezone.utc).isoformat()

    architecture_path = root / "docs" / "architecture" / "overview.md"
    scenario_path = (
        root / "docs" / "scenarios" / "brownfield-daily-analytics.md"
    )
    summary_path = root / "reports" / "engineering-summary.md"

    architecture = f"""
# Architecture Overview

Generated: {generated_at}

## Components

- FastAPI URL-shortener application
- SQLite URL and daily-click storage
- Requirements agent
- Dependency-graph planner and scheduler
- Human design and release approval gates
- Candidate implementation agent
- Isolated validation runner
- Deterministic security agent
- Documentation and release-readiness stages
- Persistent JSON workflow checkpoints

## Workflow

    requirements
        -> design [human approval]
            -> implement
                -> tests
                -> security
                -> docs
                    -> release [human approval]

Tests, security, and documentation can execute independently after
implementation. Release waits for all three to pass.

## Safety Controls

- Human approval before implementation and release
- Bounded test retries
- Persistent failure states
- Candidate validation before application
- Original application backup
- Secret-file checks
- Controlled SQLite lock timeout
- Atomic lifetime and daily counter updates
- Safe stop when dependencies or approvals are missing

## Data Model

The urls table stores the original URL, short code, lifetime clicks,
and creation timestamp.

The daily_clicks table stores one counter for each short code and UTC
calendar date.
"""

    decisions = "\n".join(
        f"- {decision}" for decision in state.decisions
    )

    if not decisions:
        decisions = "- No decisions recorded."

    scenario = f"""
# Brownfield Scenario: Daily Click Analytics

Generated: {generated_at}

## Requirement

{state.requirement}

## Existing Behavior

The service already created short URLs, redirected requests, and
recorded lifetime click totals.

## Implemented Change

The analytics API now returns daily_counts grouped by UTC calendar
date and ordered ascending.

## Constraints

- Preserve lifetime clicks
- Do not backfill historical daily data
- Do not collect personal information
- Preserve unknown-code 404 behavior
- Return an empty list when no daily records exist

## Orchestration

1. The ambiguous request stopped for clarification.
2. The clarified requirement received human approval.
3. AI proposed an architecture.
4. Human review corrected SQLite concurrency assumptions.
5. Candidate code was generated separately.
6. Candidate tests passed before application.
7. Previous application code was backed up.
8. Test and security gates passed.

## Decision Lineage

{decisions}
"""

    task_lines = "\n".join(
        f"- {item.id}: {item.status} "
        f"(attempts: {item.attempts})"
        for item in state.tasks
    )

    summary = f"""
# Engineering Summary

Generated: {generated_at}

Run ID: {state.run_id}

## Outcome

The FastAPI and SQLite URL shortener was extended with UTC daily-click
analytics using a governed agentic workflow.

## Task Status Before Documentation Completion

{task_lines}

## Trade-offs

- SQLite is simple but allows only one writer at a time.
- A bounded lock wait returns 503 instead of losing updates.
- Lifetime clicks may exceed daily totals because there is no backfill.
- Deterministic checks control gates while AI remains advisory.

## Limitations

- SQLite is not intended for large distributed production traffic.
- Authentication and user ownership are not implemented.
- Rate limiting is not yet implemented.
- Gemini availability and quotas can affect AI stages.
- Dependency deprecation warnings remain.
- Public deployment is outside the current prototype.

## Rollback

Restore the backed-up application code while retaining the additive
daily-click table. Any tracking gap must be documented and never
fabricated.

## Human Ownership

Agents generate and validate work within defined boundaries. Humans
own requirement approval, design correction, release approval, and
final quality.
"""

    try:
        write_document(architecture_path, architecture)
        write_document(scenario_path, scenario)
        write_document(summary_path, summary)

        generated = [
            architecture_path,
            scenario_path,
            summary_path,
        ]

        for path in generated:
            if not path.exists() or path.stat().st_size < 100:
                raise ValueError(
                    f"Invalid documentation artifact: {path}"
                )

        task.status = "passed"

        state.artifacts["architecture_document"] = str(
            architecture_path
        )
        state.artifacts["brownfield_scenario"] = str(
            scenario_path
        )
        state.artifacts["engineering_summary"] = str(
            summary_path
        )

        state.decisions.append(
            "Documentation generated and validated deterministically."
        )

        save_state(state, checkpoint)
        return generated

    except Exception as error:
        task.status = "failed"

        state.decisions.append(
            f"Documentation failed safely: "
            f"{type(error).__name__}: {error}"
        )

        save_state(state, checkpoint)
        raise


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python -m orchestrator.documentation_agent "
            "runs/<run-id>/workflow.json"
        )

    checkpoint = Path(sys.argv[1])
    state = load_state(checkpoint)

    generated = generate_documentation(state, checkpoint)

    print("Documentation generated:")

    for path in generated:
        print(f"- {path}")


if __name__ == "__main__":
    main()