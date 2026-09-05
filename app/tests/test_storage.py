from orchestrator.planner import create_plan
from orchestrator.state import WorkflowState
from orchestrator.storage import load_state, save_state


def test_save_and_restore_workflow(tmp_path):
    state = WorkflowState(requirement="Build a URL shortener")
    create_plan(state)
    state.tasks[0].status = "passed"
    state.design_approval = "approved"

    path = tmp_path / "workflow.json"
    save_state(state, path)
    restored = load_state(path)

    assert restored == state
    assert restored.release_approval == "pending"