from pathlib import Path

import orchestrator.run_pipeline as run_pipeline_module
from orchestrator.planner import create_plan
from orchestrator.run_pipeline import run_pipeline
from orchestrator.state import WorkflowState
from orchestrator.storage import load_state, save_state


def make_state_at_checkpoint(tmp_path):
    project = tmp_path / "project"
    project.mkdir()

    state = WorkflowState(requirement="Test pipeline driver")
    create_plan(state)

    checkpoint = project / "runs" / "workflow.json"
    save_state(state, checkpoint)

    return checkpoint


def test_pipeline_stops_after_requirements_for_human_review(
    tmp_path, monkeypatch
):
    checkpoint = make_state_at_checkpoint(tmp_path)

    calls = []

    def fake_run_cli_stage(module, *args):
        calls.append(module)
        state = load_state(checkpoint)
        task = next(t for t in state.tasks if t.id == "requirements")
        task.status = "blocked"
        state.artifacts["requirements_analysis"] = "FAKE ANALYSIS"
        save_state(state, checkpoint)

    monkeypatch.setattr(
        run_pipeline_module, "run_cli_stage", fake_run_cli_stage
    )

    run_pipeline(checkpoint)

    assert calls == ["review_requirements"]

    restored = load_state(checkpoint)
    requirements_task = next(
        t for t in restored.tasks if t.id == "requirements"
    )
    # Still blocked -- the pipeline must not auto-approve requirements.
    assert requirements_task.status == "blocked"


def test_pipeline_drives_full_workflow_with_fakes(tmp_path, monkeypatch):
    checkpoint = make_state_at_checkpoint(tmp_path)

    # Start from an already-approved requirement, so this test focuses
    # on design -> implement -> parallel gates -> release.
    state = load_state(checkpoint)
    requirements_task = next(
        t for t in state.tasks if t.id == "requirements"
    )
    requirements_task.status = "passed"
    save_state(state, checkpoint)

    call_order = []

    def fake_run_cli_stage(module, *args):
        call_order.append(module)
        state = load_state(checkpoint)

        if module == "design_agent":
            task = next(t for t in state.tasks if t.id == "design")
            task.status = "passed"
            state.artifacts["design"] = "FAKE DESIGN"
            state.artifacts["design_source"] = "FAKE SOURCE"

        elif module == "implementation_agent":
            task = next(t for t in state.tasks if t.id == "implement")
            task.status = "blocked"
            candidate = checkpoint.parent / "candidate_main.py"
            candidate.write_text("# fake candidate\n", encoding="utf-8")
            state.artifacts["candidate_main"] = str(candidate)

        elif module == "validate_candidate":
            pass  # Assume validation succeeds; nothing to update.

        elif module == "apply_candidate":
            task = next(t for t in state.tasks if t.id == "implement")
            task.status = "passed"

        else:
            raise AssertionError(f"Unexpected CLI stage: {module}")

        save_state(state, checkpoint)

    def fake_request_design_approval(state, checkpoint):
        call_order.append("approve_design")
        state.design_approval = "approved"
        save_state(state, checkpoint)

    def fake_request_release_approval(state, checkpoint):
        call_order.append("approve_release")
        state.release_approval = "approved"
        save_state(state, checkpoint)

    def fake_execute_tests(state, checkpoint):
        call_order.append("tests")
        state = load_state(checkpoint)
        task = next(t for t in state.tasks if t.id == "tests")
        task.status = "passed"
        save_state(state, checkpoint)

    def fake_run_security_review(state, checkpoint):
        call_order.append("security")
        state = load_state(checkpoint)
        task = next(t for t in state.tasks if t.id == "security")
        task.status = "passed"
        save_state(state, checkpoint)

    def fake_run_compliance_review(state, checkpoint, project):
        call_order.append("compliance")
        state = load_state(checkpoint)
        task = next(t for t in state.tasks if t.id == "compliance")
        task.status = "passed"
        save_state(state, checkpoint)

    def fake_generate_documentation(state, checkpoint, project_root=None):
        call_order.append("docs")
        state = load_state(checkpoint)
        task = next(t for t in state.tasks if t.id == "docs")
        task.status = "passed"
        save_state(state, checkpoint)

    def fake_execute_release(state, checkpoint):
        call_order.append("release")
        state = load_state(checkpoint)
        task = next(t for t in state.tasks if t.id == "release")
        task.status = "passed"
        save_state(state, checkpoint)

    monkeypatch.setattr(
        run_pipeline_module, "run_cli_stage", fake_run_cli_stage
    )
    monkeypatch.setattr(
        run_pipeline_module,
        "request_design_approval",
        fake_request_design_approval,
    )
    monkeypatch.setattr(
        run_pipeline_module,
        "request_release_approval",
        fake_request_release_approval,
    )
    monkeypatch.setattr(
        run_pipeline_module, "execute_tests", fake_execute_tests
    )
    monkeypatch.setattr(
        run_pipeline_module,
        "run_security_review",
        fake_run_security_review,
    )
    monkeypatch.setattr(
        run_pipeline_module,
        "run_compliance_review",
        fake_run_compliance_review,
    )
    monkeypatch.setattr(
        run_pipeline_module,
        "generate_documentation",
        fake_generate_documentation,
    )
    monkeypatch.setattr(
        run_pipeline_module, "execute_release", fake_execute_release
    )

    run_pipeline(checkpoint)

    restored = load_state(checkpoint)

    for task in restored.tasks:
        assert task.status == "passed", f"{task.id} did not complete"

    assert restored.design_approval == "approved"
    assert restored.release_approval == "approved"

    # Design and implementation must happen before any of the
    # independent tests/security/compliance/docs branches, and release
    # must be last.
    assert call_order.index("design_agent") < call_order.index(
        "approve_design"
    )
    assert call_order.index("approve_design") < call_order.index(
        "implementation_agent"
    )
    assert call_order.index("apply_candidate") < call_order.index(
        "tests"
    )
    assert call_order[-2:] == ["approve_release", "release"]


def test_pipeline_stops_cleanly_when_release_is_rejected(
    tmp_path, monkeypatch
):
    checkpoint = make_state_at_checkpoint(tmp_path)
    state = load_state(checkpoint)

    for task in state.tasks:
        if task.id != "release":
            task.status = "passed"

    save_state(state, checkpoint)

    def fake_request_release_approval(state, checkpoint):
        state.release_approval = "rejected"
        save_state(state, checkpoint)

    release_called = []

    def fake_execute_release(state, checkpoint):
        release_called.append(True)

    monkeypatch.setattr(
        run_pipeline_module,
        "request_release_approval",
        fake_request_release_approval,
    )
    monkeypatch.setattr(
        run_pipeline_module, "execute_release", fake_execute_release
    )

    run_pipeline(checkpoint)

    assert release_called == []

    restored = load_state(checkpoint)
    assert restored.release_approval == "rejected"
    release_task = next(t for t in restored.tasks if t.id == "release")
    assert release_task.status == "pending"