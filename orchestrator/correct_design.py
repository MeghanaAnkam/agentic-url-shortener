import sys
from pathlib import Path

from orchestrator.state import record_decision
from orchestrator.storage import load_state, save_state


def main():
    checkpoint = Path(sys.argv[1])
    state = load_state(checkpoint)

    if "design" not in state.artifacts:
        raise SystemExit("No design proposal found.")

    if any(
        task.status != "pending"
        for task in state.tasks
        if task.id in {"implement", "tests", "security", "docs", "release"}
    ):
        raise SystemExit("Later work has started. Impact review required.")

    corrections = """
REVIEW CORRECTIONS — these supersede conflicting proposal text:

- Local SQLite version is 3.50.4; UPSERT is supported.
- SQLite allows one writer at a time, not row-level write locks.
- Use a bounded lock wait and return a controlled 503 on lock
  timeout; do not redirect after a failed counting transaction.
- Verify the short code exists before incrementing either counter.
- Increment lifetime and daily counts in the same transaction.
  Roll back both if either operation fails.
- Capture UTC date once at redirect-handler entry.
- Enable foreign keys on every database connection.
- Explicitly close connections after use.
- Read lifetime and daily analytics from one consistent snapshot.
- Query daily rows directly in date order; no JOIN is necessary.
- The composite primary key supports lookup by short_code;
  omit the redundant separate short_code index.
- Create the new table before serving the upgraded application.
  Preserve all existing links and counts; do not backfill.
- Rollback restores previous application code and retains the
  daily table. Daily tracking pauses during rollback; document
  that gap instead of inventing missing history.
- Test concurrent increments using counter differences, not
  equality between lifetime clicks and daily totals.
- Test unknown links, old links, empty lists, ordering, UTC
  midnight, lock timeout, and failure between counter updates.
"""

    if "design_before_review" in state.artifacts:
        raise SystemExit("Corrections already recorded.")

    state.artifacts["design_before_review"] = state.artifacts["design"]
    state.artifacts["design"] += "\n" + corrections
    state.design_approval = "pending"
    state.release_approval = "pending"
    record_decision(
        state,
        actor="human:design-reviewer",
        stage="design",
        action="correct_design",
        outcome="corrections_recorded",
        rationale=(
            "Human corrections supersede conflicting design text. "
            "Design approval remains pending."
        ),
    )
    save_state(state, checkpoint)
    print("Corrected design saved. Application code unchanged.")


if __name__ == "__main__":
    main()