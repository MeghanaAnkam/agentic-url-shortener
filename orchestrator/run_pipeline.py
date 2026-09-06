import subprocess
import sys
from pathlib import Path

from orchestrator.approvals import (
    request_design_approval,
    request_release_approval,
)
from orchestrator.compliance_agent import run_compliance_review
from orchestrator.documentation_agent import generate_documentation
from orchestrator.executor import execute_tests, retry_tests
from orchestrator.release_agent import execute_release
from orchestrator.scheduler import ready_tasks
from orchestrator.security_agent import run_security_review
from orchestrator.storage import load_state


PROJECT_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FOR_RELEASE = {"tests", "security", "compliance", "docs"}

# Fixed order for single-task dispatch. When several tasks are
# simultaneously ready (e.g. tests/security/compliance/docs once
# implementation passes), ready_tasks() has already proven none of
# them depends on another -- this list only decides which one *this*
# driver reaches for first. A driver with a thread pool could run
# them concurrently instead; this one runs them one at a time so a
# beginner can follow exactly what happened and in what order.
DISPATCH_PRIORITY = [
    "requirements",
    "design",
    "implement",
    "tests",
    "security",
    "compliance",
    "docs",
    "release",
]


def release_awaiting_approval(state) -> bool:
    """
    ready_tasks() only lists "release" once release_approval is
    already "approved" -- it does not announce that release is ready
    *to be* approved. So the pipeline checks that condition itself:
    all required gates passed, release still pending, and no approval
    decision recorded yet.
    """
    release_task = next(t for t in state.tasks if t.id == "release")

    if release_task.status != "pending" or state.release_approval != "pending":
        return False

    statuses = {
        task.id: task.status
        for task in state.tasks
        if task.id in REQUIRED_FOR_RELEASE
    }

    return all(
        statuses.get(name) == "passed" for name in REQUIRED_FOR_RELEASE
    )


def run_cli_stage(module: str, *args: str) -> None:
    """
    Run a stage whose logic lives only inside its own main() function
    (requirements review, design, implementation, validation, apply),
    the same way a human would from the terminal:
    python -m orchestrator.<module> <args>

    These stages are left untouched and untested-against here on
    purpose -- they already have their own tests, and calling them
    exactly as a human would avoids introducing a second code path
    that could drift from the real one.
    """
    command = [sys.executable, "-m", f"orchestrator.{module}", *args]
    result = subprocess.run(command, cwd=PROJECT_ROOT)

    if result.returncode != 0:
        raise RuntimeError(
            f"{module} exited with status {result.returncode}"
        )


def run_pipeline(checkpoint: Path) -> None:
    """
    Advances a workflow checkpoint as far as it can go without
    inventing a human decision. Requirements, design, and release
    still ask a real question and wait for a real answer -- this only
    removes the need to remember which script to run next, and lets
    the independent tests/security/compliance/docs branches proceed
    without waiting on each other.
    """
    checkpoint = Path(checkpoint).resolve()

    while True:
        state = load_state(checkpoint)

        if release_awaiting_approval(state):
            print(
                "\n[pipeline] All release gates passed. Requesting "
                "your release approval..."
            )
            try:
                request_release_approval(state, checkpoint)
            except Exception as error:
                print(
                    f"\n[pipeline] Stopped: "
                    f"{type(error).__name__}: {error}"
                )
                return
            continue

        ready = ready_tasks(state)

        if not ready:
            print("\n[pipeline] Nothing is ready to run right now.")
            print(f"[pipeline] Checkpoint: {checkpoint}")
            return

        task_id = next(t for t in DISPATCH_PRIORITY if t in ready)
        print(f"\n[pipeline] Advancing: {task_id}")

        try:
            if task_id == "requirements":
                run_cli_stage("review_requirements", str(checkpoint))
                print(
                    "\n[pipeline] Human requirements review is "
                    "required.\nRun: python -m "
                    f"orchestrator.approve_requirements {checkpoint}"
                )
                return

            elif task_id == "design":
                run_cli_stage("design_agent", str(checkpoint))
                state = load_state(checkpoint)
                request_design_approval(state, checkpoint)

            elif task_id == "implement":
                run_cli_stage("implementation_agent", str(checkpoint))
                state = load_state(checkpoint)
                candidate = state.artifacts.get("candidate_main")

                if not candidate:
                    print(
                        "[pipeline] No candidate was produced. Stopping."
                    )
                    return

                run_cli_stage("validate_candidate", candidate)
                run_cli_stage("apply_candidate", str(checkpoint))

            elif task_id == "tests":
                execute_tests(state, checkpoint)
                state = load_state(checkpoint)
                test_task = next(
                    t for t in state.tasks if t.id == "tests"
                )

                if test_task.status == "failed":
                    print(
                        "[pipeline] Tests failed; attempting one "
                        "bounded retry..."
                    )
                    try:
                        retry_tests(state, checkpoint)
                    except ValueError as retry_error:
                        print(f"[pipeline] {retry_error}")

            elif task_id == "security":
                run_security_review(state, checkpoint)

            elif task_id == "compliance":
                run_compliance_review(state, checkpoint, PROJECT_ROOT)

            elif task_id == "docs":
                generate_documentation(state, checkpoint, PROJECT_ROOT)

            elif task_id == "release":
                # By the time "release" appears in ready_tasks(), the
                # approval above has already been recorded.
                execute_release(state, checkpoint)

        except Exception as error:
            print(
                f"\n[pipeline] Stopped: {type(error).__name__}: {error}"
            )
            return


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python -m orchestrator.run_pipeline "
            "runs/<run-id>/workflow.json"
        )

    run_pipeline(Path(sys.argv[1]))


if __name__ == "__main__":
    main()