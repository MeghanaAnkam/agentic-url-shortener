"""
Generates a genuine failure-path artifact: a real compliance violation
that genuinely blocks release, using the real orchestrator functions
against an isolated project containing a deliberately broken candidate.

The application shipped in this repository is never touched -- the
broken code lives only in a temporary directory created and destroyed
by this script.
"""
import json
import shutil
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, ".")

from orchestrator.planner import create_plan
from orchestrator.state import WorkflowState
from orchestrator.storage import save_state, load_state
from orchestrator import compliance_agent, approvals

PROJECT = Path(".").resolve()
OUT_DIR = PROJECT / "docs" / "demo" / "failure-run"
ARTIFACTS = OUT_DIR / "artifacts"
ARTIFACTS.mkdir(parents=True, exist_ok=True)

BROKEN_CANDIDATE = '''\
# Deliberately broken candidate: this line would leak a visitor's IP
# address, which is explicitly out of scope for this project.
def log_visitor(request):
    ip_address = request.client.host
    return ip_address
'''

with TemporaryDirectory() as directory:
    broken_project = Path(directory)
    (broken_project / "app").mkdir()
    (broken_project / "requirements").mkdir()

    (broken_project / "app" / "main.py").write_text(
        BROKEN_CANDIDATE, encoding="utf-8"
    )
    shutil.copy2(
        PROJECT / "requirements" / "daily_clicks.txt",
        broken_project / "requirements" / "daily_clicks.txt",
    )

    requirement = (
        broken_project / "requirements" / "daily_clicks.txt"
    ).read_text(encoding="utf-8").strip()

    checkpoint = ARTIFACTS / "workflow.json"

    state = WorkflowState(requirement=requirement)
    create_plan(state)

    for task_id in ("requirements", "design", "implement", "tests", "docs"):
        task = next(t for t in state.tasks if t.id == task_id)
        task.status = "passed"

    state.design_approval = "approved"
    save_state(state, checkpoint)

    # Real compliance check against the real, deliberately broken
    # candidate.
    report = compliance_agent.run_compliance_review(
        state, checkpoint, broken_project
    )
    state = load_state(checkpoint)

    print("Compliance status:", report["status"])
    print("Findings:", json.dumps(report["findings"], indent=2))

    # Real attempt to request release approval -- must be genuinely
    # refused, not merely described as refused.
    try:
        approvals.request_release_approval(state, checkpoint)
        raise SystemExit("ERROR: release approval should have been blocked!")
    except ValueError as error:
        block_message = str(error)
        print("\nRelease approval correctly refused:")
        print(" ", block_message)

    state = load_state(checkpoint)

    (ARTIFACTS / "release_block_message.txt").write_text(
        block_message + "\n", encoding="utf-8"
    )

    print("\nFinal task statuses:")
    for t in state.tasks:
        print(f"  {t.id}: {t.status}")
    print("Release approval:", state.release_approval)
