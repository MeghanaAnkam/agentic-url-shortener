import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

from orchestrator.storage import load_state, save_state


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def execute_rollback(
    state,
    checkpoint: Path,
    project: Path,
    reason: str,
) -> None:
    """
    Restore app/main.py from the backup that apply_candidate.py made,
    and record a rollback event so it shows up in the audit trail
    and reliability metrics.
    """
    task = next(t for t in state.tasks if t.id == "implement")

    if task.status != "passed":
        raise ValueError(
            "Nothing to roll back: no applied implementation found."
        )

    backup_path = state.artifacts.get("pre_apply_backup")
    if not backup_path:
        raise ValueError("No backup was recorded for this workflow.")

    backup = Path(backup_path)
    target = project / "app" / "main.py"

    if not backup.is_file():
        raise ValueError(f"Backup file is missing: {backup}")

    if not reason:
        raise ValueError("A rollback reason is required.")

    current_code = target.read_bytes()
    backup_code = backup.read_bytes()

    # Write the restore atomically, the same safe way apply_candidate does.
    temporary = target.with_name("main.py.rollback-tmp")
    with temporary.open("wb") as file:
        file.write(backup_code)
    temporary.replace(target)

    task.status = "failed"
    state.release_approval = "pending"

    state.artifacts["rolled_back_from_sha256"] = digest(current_code)
    state.artifacts["rolled_back_to_sha256"] = digest(backup_code)

    state.events.append(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "rollback",
            "task_id": "implement",
            "reason": reason,
        }
    )

    state.decisions.append(
        f"Rollback executed: app/main.py restored from {backup}. "
        f"Reason: {reason}"
    )

    save_state(state, checkpoint)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python -m orchestrator.rollback_candidate "
            "runs/<run-id>/workflow.json"
        )

    project = Path(__file__).resolve().parents[1]
    checkpoint = Path(sys.argv[1]).resolve()
    state = load_state(checkpoint)

    task = next(t for t in state.tasks if t.id == "implement")
    backup_path = state.artifacts.get("pre_apply_backup")

    if task.status != "passed" or not backup_path:
        raise SystemExit("Nothing to roll back for this workflow.")

    print("\nROLLBACK REQUEST")
    print("Run ID:", state.run_id)
    print("This will restore app/main.py from:", backup_path)
    print(
        "The daily_clicks table and any data already collected will "
        "NOT be deleted; only application code is restored."
    )

    answer = input(
        "\nType 'rollback' to confirm, anything else to cancel: "
    ).strip().lower()

    if answer != "rollback":
        raise SystemExit("Rollback cancelled. No files were changed.")

    reason = input("Enter the rollback reason: ").strip()

    try:
        execute_rollback(state, checkpoint, project, reason)
    except ValueError as error:
        raise SystemExit(str(error))

    print("\nRollback complete. app/main.py has been restored.")
    print(
        "Note: daily-click tracking may show a gap for the period the "
        "rolled-back code was live. This gap is expected and must be "
        "documented, not fabricated."
    )


if __name__ == "__main__":
    main()