from pathlib import Path

import pytest

from orchestrator.compliance_agent import (
    find_out_of_scope_violations,
    find_pii_terms,
    find_schema_pii_columns,
    run_compliance_review,
)
from orchestrator.planner import create_plan
from orchestrator.state import WorkflowState
from orchestrator.storage import load_state, save_state


CLEAN_SOURCE = """
def get_analytics(short_code):
    return {"short_code": short_code, "clicks": 5}
"""

PII_TERM_SOURCE = """
def log_request(request):
    ip = request.client.host
    return ip
"""

PII_SCHEMA_SOURCE = '''
SCHEMA = """
CREATE TABLE visits (
    short_code TEXT,
    ip_address TEXT,
    email TEXT
)
"""
'''


def test_find_pii_terms_detects_banned_terms():
    findings = find_pii_terms(PII_TERM_SOURCE)
    assert any("client.host" in f for f in findings)


def test_find_pii_terms_clean_source_has_no_findings():
    assert find_pii_terms(CLEAN_SOURCE) == []


def test_find_schema_pii_columns_detects_pii_columns():
    findings = find_schema_pii_columns(PII_SCHEMA_SOURCE)
    assert any("ip_address" in f for f in findings)
    assert any("email" in f for f in findings)


def test_find_schema_pii_columns_clean_source_has_no_findings():
    assert find_schema_pii_columns(CLEAN_SOURCE) == []


def test_find_out_of_scope_violations_detects_dashboard(tmp_path):
    requirement_file = tmp_path / "requirement.txt"
    requirement_file.write_text(
        "Some requirement.\n\nOut of scope:\n- Dashboard\n",
        encoding="utf-8",
    )

    source = "@app.get('/dashboard')\ndef dashboard():\n    return {}\n"

    findings = find_out_of_scope_violations(source, [requirement_file])
    assert any("Dashboard" in f for f in findings)


def test_find_out_of_scope_violations_clean_source_has_no_findings(
    tmp_path,
):
    requirement_file = tmp_path / "requirement.txt"
    requirement_file.write_text(
        "Some requirement.\n\nOut of scope:\n- Dashboard\n",
        encoding="utf-8",
    )

    findings = find_out_of_scope_violations(CLEAN_SOURCE, [requirement_file])
    assert findings == []


def make_ready_state(tmp_path):
    project = tmp_path / "project"
    (project / "app").mkdir(parents=True)
    (project / "requirements").mkdir(parents=True)

    (project / "requirements" / "req.txt").write_text(
        "Some requirement.\n\nOut of scope:\n- Dashboard\n",
        encoding="utf-8",
    )

    state = WorkflowState(requirement="Test compliance")
    create_plan(state)

    for task in state.tasks:
        if task.id == "implement":
            task.status = "passed"

    checkpoint = project / "runs" / "workflow.json"
    save_state(state, checkpoint)

    return state, checkpoint, project


def test_run_compliance_review_passes_on_clean_source(tmp_path):
    state, checkpoint, project = make_ready_state(tmp_path)
    (project / "app" / "main.py").write_text(CLEAN_SOURCE, encoding="utf-8")

    report = run_compliance_review(state, checkpoint, project)

    assert report["status"] == "passed"
    assert report["findings"] == []

    restored = load_state(checkpoint)
    task = next(t for t in restored.tasks if t.id == "compliance")
    assert task.status == "passed"


def test_run_compliance_review_fails_on_pii_terms(tmp_path):
    state, checkpoint, project = make_ready_state(tmp_path)
    (project / "app" / "main.py").write_text(
        PII_TERM_SOURCE, encoding="utf-8"
    )

    report = run_compliance_review(state, checkpoint, project)

    assert report["status"] == "failed"
    assert len(report["findings"]) > 0

    restored = load_state(checkpoint)
    task = next(t for t in restored.tasks if t.id == "compliance")
    assert task.status == "failed"


def test_run_compliance_review_requires_dependencies(tmp_path):
    state, checkpoint, project = make_ready_state(tmp_path)

    task = next(t for t in state.tasks if t.id == "implement")
    task.status = "pending"

    (project / "app" / "main.py").write_text(CLEAN_SOURCE, encoding="utf-8")

    with pytest.raises(ValueError, match="dependencies are not passed"):
        run_compliance_review(state, checkpoint, project)