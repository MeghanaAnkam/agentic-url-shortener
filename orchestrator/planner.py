from orchestrator.state import Task, WorkflowState


def create_plan(state: WorkflowState) -> None:
    if state.tasks:
        raise ValueError("This workflow already has a plan.")

    state.tasks = [
        Task("requirements", "Clarify requirement and acceptance criteria"),
        Task("design", "Design APIs and database", ["requirements"]),
        Task("implement", "Build the approved design", ["design"]),
        Task("tests", "Run automated tests", ["implement"]),
        Task("security", "Check security risks", ["implement"]),
        Task("compliance", "Check data-privacy and scope compliance", ["implement"]),
        Task("docs", "Update setup and API documentation", ["implement"]),
        Task(
            "release",
            "Prepare release-readiness report",
            ["tests", "security", "compliance", "docs"],
        ),
    ]


if __name__ == "__main__":
    state = WorkflowState(requirement="Build a URL shortener")
    create_plan(state)

    for task in state.tasks:
        dependencies = ", ".join(task.depends_on) or "none"
        print(f"{task.id}: waits for [{dependencies}]")