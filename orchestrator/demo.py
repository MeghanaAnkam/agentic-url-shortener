"""
One-command demonstration entry point.

    python -m orchestrator.demo

Runs a complete, self-contained, deterministic pass through the
orchestration pipeline -- no Gemini API key required -- exercising:

  - the full 8-stage dependency graph (requirements -> ... -> release)
  - a real bounded test retry
  - a real rollback (isolated demo files, never touching app/main.py)
  - real audit events and reliability metrics

This is the same logic as `orchestrator.audit_demo`, exposed under a
predictable, discoverable name for anyone opening this repo for the
first time. For a genuine, non-simulated pass against the real
application (requires a Gemini API key), see `run_pipeline.py`
instead:

    python -m orchestrator.run_pipeline runs/<run-id>/workflow.json

For a demonstration of a real validation failure genuinely blocking
release, see `generate_failure_demo.py` at the project root and
`docs/demo/failure-run/`.
"""
from orchestrator.audit_demo import main as run_audit_demo


def main() -> None:
    print("Running the full orchestration pipeline end to end.")
    print("No Gemini API key is required for this demonstration.\n")
    run_audit_demo()
    print(
        "\nSee docs/scenarios/audit-retry-demo.md and "
        "reports/reliability-metrics.md for the full write-up."
    )


if __name__ == "__main__":
    main()
