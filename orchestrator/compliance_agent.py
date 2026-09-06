import ast
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from orchestrator.scheduler import ready_tasks
from orchestrator.state import WorkflowState, record_decision
from orchestrator.storage import load_state, save_state


# Terms that would signal personal-data collection if they showed up
# in the application source or database schema. This is intentionally
# a data-privacy check, distinct from security_agent.py's code-safety
# checks (eval/exec, secrets, SQL injection, etc.).
BANNED_PII_TERMS = [
    "ip_address",
    "ip address",
    "client.host",
    "x-forwarded-for",
    "user_agent",
    "user-agent",
    "useragent",
    "referrer",
    "referer",
    "device_id",
    "device id",
    "fingerprint",
    "geolocation",
    "latitude",
    "longitude",
    "email",
    "phone_number",
    "phone number",
    "ssn",
    "social_security",
]

# Maps an "Out of scope" bullet (as written in requirements/*.txt,
# lowercased) to the source-code markers that would indicate someone
# built it anyway. This ties the compliance gate directly to the
# approved requirement document instead of a generic hardcoded policy.
OUT_OF_SCOPE_MARKERS = {
    "dashboard": ["/dashboard", "dashboard"],
    "ip addresses, device details, or referrers": list(BANNED_PII_TERMS),
    "date filters": ["start_date", "end_date", "from_date", "to_date"],
    "automatic deletion": ["delete from", "os.remove", "unlink("],
}


def find_pii_terms(source: str) -> list[str]:
    lowered = source.lower()
    return [
        f"Possible PII/tracking term found in application source: '{term}'"
        for term in BANNED_PII_TERMS
        if term in lowered
    ]


def find_schema_pii_columns(source: str) -> list[str]:
    """
    Looks specifically inside CREATE TABLE string literals for
    PII-shaped column names, so a docstring or comment mentioning
    "email" elsewhere doesn't produce a false positive here.
    """
    findings: list[str] = []

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ["Cannot parse source for schema inspection."]

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if "create table" in node.value.lower():
                lowered_schema = node.value.lower()
                for term in BANNED_PII_TERMS:
                    column_like = term.replace(" ", "_").replace("-", "_")
                    if column_like in lowered_schema:
                        findings.append(
                            f"Possible PII-shaped column in schema: '{term}'"
                        )

    return findings


def find_out_of_scope_violations(
    source: str, requirement_files: list[Path]
) -> list[str]:
    findings: list[str] = []
    lowered_source = source.lower()

    for requirement_file in requirement_files:
        text = requirement_file.read_text(encoding="utf-8")
        lowered_text = text.lower()

        if "out of scope" not in lowered_text:
            continue

        section = text[lowered_text.index("out of scope"):]

        for line in section.splitlines()[1:]:
            item = line.strip().lstrip("-").strip().rstrip(".")
            if not item:
                continue

            markers = OUT_OF_SCOPE_MARKERS.get(item.lower())
            if not markers:
                continue

            for marker in markers:
                if marker.lower() in lowered_source:
                    findings.append(
                        f"Out-of-scope item '{item}' "
                        f"(from {requirement_file.name}) appears "
                        f"implemented: found '{marker}' in source."
                    )

    return findings


def run_compliance_review(
    state: WorkflowState,
    checkpoint: Path,
    project: Path,
) -> dict:
    if "compliance" not in ready_tasks(state):
        raise ValueError(
            "Compliance review cannot start: dependencies are not passed."
        )

    task = next(t for t in state.tasks if t.id == "compliance")
    task.status = "running"
    task.attempts += 1
    save_state(state, checkpoint)

    try:
        source = (project / "app" / "main.py").read_text(encoding="utf-8")
        requirement_files = sorted(
            (project / "requirements").glob("*.txt")
        )

        findings = []
        findings.extend(find_pii_terms(source))
        findings.extend(find_schema_pii_columns(source))
        findings.extend(
            find_out_of_scope_violations(source, requirement_files)
        )

        status = "passed" if not findings else "failed"

        report = {
            "run_id": state.run_id,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "findings": findings,
            "controls_checked": [
                "PII/tracking terms in application source",
                "PII-shaped database columns",
                "requirement out-of-scope violations",
            ],
        }

        report_path = checkpoint.parent / "compliance_report.json"
        report_path.write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )

        task.status = status
        state.artifacts["compliance_report"] = str(report_path)

        record_decision(
            state,
            actor="system:compliance-checker",
            stage="compliance",
            action="run_compliance_review",
            outcome=status,
            rationale=f"Deterministic compliance review completed: {status}.",
        )
        save_state(state, checkpoint)

        return report

    except Exception as error:
        task.status = "failed"
        record_decision(
            state,
            actor="system:compliance-checker",
            stage="compliance",
            action="run_compliance_review",
            outcome="failed",
            rationale=(
                f"Compliance review failed safely: "
                f"{type(error).__name__}: {error}"
            ),
        )
        save_state(state, checkpoint)
        raise


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python -m orchestrator.compliance_agent "
            "runs/<run-id>/workflow.json"
        )

    project = Path(__file__).resolve().parents[1]
    checkpoint = Path(sys.argv[1])
    state = load_state(checkpoint)

    report = run_compliance_review(state, checkpoint, project)

    print(json.dumps(report, indent=2))

    if report["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()