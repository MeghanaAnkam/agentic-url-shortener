from orchestrator.state import WorkflowState


def ready_tasks(state: WorkflowState) -> list[str]:
    passed = {
        task.id
        for task in state.tasks
        if task.status == "passed"
    }

    ready = []

    for task in state.tasks:
        if task.status != "pending":
            continue

        if not all(dep in passed for dep in task.depends_on):
            continue

        if task.id == "implement":
            if state.design_approval != "approved":
                continue

        if task.id == "release":
            if state.release_approval != "approved":
                continue

        ready.append(task.id)

    return ready