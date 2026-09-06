import hashlib
import json
import sys
from pathlib import Path

from orchestrator.storage import load_state, save_state


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Provide the workflow.json path.")

    project = Path(__file__).resolve().parents[1]
    checkpoint = Path(sys.argv[1]).resolve()
    state = load_state(checkpoint)

    task = next(t for t in state.tasks if t.id == "implement")
    design = next(t for t in state.tasks if t.id == "design")

    if (
        state.design_approval != "approved"
        or design.status != "passed"
        or task.status != "blocked"
    ):
        raise SystemExit("Approved design and reviewed candidate required.")

    target = project / "app/main.py"
    test_target = project / "app/tests/test_daily_counts.py"
    candidate = checkpoint.parent / "candidate_main.py"
    daily_tests = checkpoint.parent / "test_daily_counts.py"
    api_tests = project / "app/tests/test_api.py"

    report = json.loads(
        (checkpoint.parent / "validation.json").read_text()
    )
    if report["status"] != "passed" or report["exit_code"] != 0:
        raise SystemExit("Passing validation required.")

    code = candidate.read_bytes()
    tests = daily_tests.read_bytes()
    original = target.read_bytes()

    checks = [
        (code, report["candidate_sha256"]),
        (tests, report["daily_tests_sha256"]),
        (api_tests.read_bytes(), report["api_tests_sha256"]),
    ]
    if any(digest(data) != expected for data, expected in checks):
        raise SystemExit("Files changed since validation. Revalidate first.")

    if target.read_text() != state.artifacts["design_source"]:
        raise SystemExit("Working application changed. Review required.")

    backup = checkpoint.parent / "main_before_apply.py"
    if backup.exists() or test_target.exists():
        raise SystemExit("Backup or destination tests already exist.")

    # Recheck immediately before writing.
    if target.read_bytes() != original:
        raise SystemExit("Working application changed during checks.")

    with backup.open("xb") as file:
        file.write(original)

    temporary = target.with_name("main.py.apply-tmp")
    try:
        with temporary.open("xb") as file:
            file.write(code)
        with test_target.open("xb") as file:
            file.write(tests)
        temporary.replace(target)
    except Exception:
        raise SystemExit(
            "Apply interrupted. Inspect files before retrying; "
            f"original code is backed up at {backup}"
        )

    task.status = "passed"
    state.release_approval = "pending"
    state.artifacts["applied_candidate_sha256"] = digest(code)
    state.artifacts["pre_apply_backup"] = str(backup)
    state.artifacts["candidate_validation"] = json.dumps(report)
    state.decisions.append(
        "Validated candidate and feature tests applied locally. "
        "Release remains unapproved."
    )
    save_state(state, checkpoint)
    print("Candidate applied. Original code backed up.")
    print("No database migration or release was executed.")


if __name__ == "__main__":
    main()