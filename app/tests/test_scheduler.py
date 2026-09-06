from orchestrator.planner import create_plan
from orchestrator.scheduler import ready_tasks
from orchestrator.state import WorkflowState


def make_state():
    state = WorkflowState(requirement="Build a URL shortener")
    create_plan(state)
    return state


def test_only_requirements_ready_initially():
    assert ready_tasks(make_state()) == ["requirements"]


def test_parallel_tasks_ready_after_implementation():
    state = make_state()

    for task in state.tasks:
        if task.id in {"requirements", "design", "implement"}:
            task.status = "passed"

    assert set(ready_tasks(state)) == {
        "tests",
        "security",
        "compliance",
        "docs",
    }


def test_release_waits_for_security():
    state = make_state()

    for task in state.tasks:
        if task.id not in {"security", "release"}:
            task.status = "passed"

    assert "release" not in ready_tasks(state)

    security = next(t for t in state.tasks if t.id == "security")
    security.status = "passed"

        # Passing checks alone does not authorize release.
    assert ready_tasks(state) == []

    state.release_approval = "approved"
    assert ready_tasks(state) == ["release"]


def test_release_waits_for_compliance():
    state = make_state()

    for task in state.tasks:
        if task.id not in {"compliance", "release"}:
            task.status = "passed"

    assert "release" not in ready_tasks(state)

    compliance = next(t for t in state.tasks if t.id == "compliance")
    compliance.status = "passed"

    # Passing checks alone does not authorize release.
    assert ready_tasks(state) == []

    state.release_approval = "approved"
    assert ready_tasks(state) == ["release"]


def test_implementation_requires_design_approval():
    state = make_state()

    for task in state.tasks:
        if task.id in {"requirements", "design"}:
            task.status = "passed"

    assert ready_tasks(state) == []

    state.design_approval = "rejected"
    assert ready_tasks(state) == []

    state.design_approval = "approved"
    assert ready_tasks(state) == ["implement"]

def test_design_approval_does_not_approve_release():
    state = make_state()
    state.design_approval = "approved"

    for task in state.tasks:
        if task.id != "release":
            task.status = "passed"

    assert ready_tasks(state) == []

    state.release_approval = "rejected"
    assert ready_tasks(state) == []

    state.release_approval = "approved"
    assert ready_tasks(state) == ["release"]
