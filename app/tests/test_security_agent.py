from pathlib import Path

from orchestrator.security_agent import (
    find_dangerous_python_calls,
    find_tracked_secrets,
    verify_application_controls,
)


def test_security_check_detects_tracked_env():
    findings = find_tracked_secrets(
        [".env", "app/main.py"]
    )

    assert findings == ["Sensitive file is tracked: .env"]


def test_security_check_detects_private_key():
    findings = find_tracked_secrets(
        ["certificates/server.pem"]
    )

    assert findings == [
        "Private-key file is tracked: certificates/server.pem"
    ]


def test_repository_has_no_dangerous_python_calls():
    findings = find_dangerous_python_calls(Path.cwd())

    assert findings == []


def test_application_security_controls_exist():
    findings = verify_application_controls(Path.cwd())

    assert findings == []