import ast
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from orchestrator.scheduler import ready_tasks
from orchestrator.state import WorkflowState, record_decision
from orchestrator.storage import load_state, save_state


BLOCKED_NAMES = {".env", "urls.db"}
BLOCKED_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def find_tracked_secrets(files: list[str]) -> list[str]:
    findings = []

    for filename in files:
        path = Path(filename)

        if path.name in BLOCKED_NAMES:
            findings.append(f"Sensitive file is tracked: {filename}")

        if path.suffix.lower() in BLOCKED_SUFFIXES:
            findings.append(f"Private-key file is tracked: {filename}")

    return findings


def find_dangerous_python_calls(root: Path) -> list[str]:
    findings = []

    for folder_name in ("app", "orchestrator"):
        folder = root / folder_name

        if not folder.exists():
            continue

        for path in folder.rglob("*.py"):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except (OSError, SyntaxError) as error:
                findings.append(f"Cannot safely parse {path}: {error}")
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        if node.func.id in {"eval", "exec"}:
                            findings.append(
                                f"Dangerous {node.func.id}() call in "
                                f"{path}:{node.lineno}"
                            )

                    for keyword in node.keywords:
                        if (
                            keyword.arg == "shell"
                            and isinstance(keyword.value, ast.Constant)
                            and keyword.value.value is True
                        ):
                            findings.append(
                                f"shell=True found in {path}:{node.lineno}"
                            )

    return findings


def verify_application_controls(root: Path) -> list[str]:
    findings = []
    main_path = root / "app" / "main.py"

    if not main_path.exists():
        return ["app/main.py is missing"]

    source = main_path.read_text(encoding="utf-8")

    required_controls = {
        "HTTP/HTTPS URL validation": '("http", "https")',
        "parameterized SQL": "?",
        "SQLite foreign keys": "PRAGMA foreign_keys = ON",
        "bounded database wait": "timeout=5",
        "controlled busy response": "status_code=503",
        "atomic write transaction": "BEGIN IMMEDIATE",
    }

    for control, marker in required_controls.items():
        if marker not in source:
            findings.append(f"Required control missing: {control}")

    return findings


def run_security_review(
    state: WorkflowState,
    checkpoint: Path,
) -> dict:
    if "security" not in ready_tasks(state):
        raise ValueError(
            "Security review cannot start: dependencies are not passed."
        )

    task = next(task for task in state.tasks if task.id == "security")
    task.status = "running"
    task.attempts += 1
    save_state(state, checkpoint)

    root = Path.cwd()

    try:
        findings = []
        findings.extend(find_tracked_secrets(tracked_files()))
        findings.extend(find_dangerous_python_calls(root))
        findings.extend(verify_application_controls(root))

        status = "passed" if not findings else "failed"

        report = {
            "run_id": state.run_id,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "findings": findings,
            "controls_checked": [
                "tracked secret files",
                "private-key files",
                "eval and exec usage",
                "subprocess shell=True",
                "HTTP/HTTPS validation",
                "parameterized SQL",
                "SQLite foreign keys",
                "bounded lock wait",
                "controlled 503 response",
                "atomic counter transaction",
            ],
        }

        report_path = checkpoint.parent / "security_report.json"
        report_path.write_text(
            json.dumps(report, indent=2),
            encoding="utf-8",
        )

        task.status = status
        state.artifacts["security_report"] = str(report_path)
        record_decision(
            state,
            actor="system:security-checker",
            stage="security",
            action="run_security_review",
            outcome=status,
            rationale=f"Deterministic security review completed: {status}.",
        )
        save_state(state, checkpoint)

        return report

    except Exception as error:
        task.status = "failed"
        record_decision(
            state,
            actor="system:security-checker",
            stage="security",
            action="run_security_review",
            outcome="failed",
            rationale=(
                f"Security review failed safely: "
                f"{type(error).__name__}: {error}"
            ),
        )
        save_state(state, checkpoint)
        raise


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python -m orchestrator.security_agent "
            "runs/<run-id>/workflow.json"
        )

    checkpoint = Path(sys.argv[1])
    state = load_state(checkpoint)
    report = run_security_review(state, checkpoint)

    print(json.dumps(report, indent=2))

    if report["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
