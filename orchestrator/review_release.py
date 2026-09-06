import sys
from pathlib import Path

from orchestrator.approvals import request_release_approval
from orchestrator.scheduler import ready_tasks
from orchestrator.storage import load_state


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python -m orchestrator.review_release "
            "runs/<run-id>/workflow.json"
        )

    checkpoint = Path(sys.argv[1])
    state = load_state(checkpoint)

    request_release_approval(state, checkpoint)

    updated_state = load_state(checkpoint)

    print("Ready tasks:", ready_tasks(updated_state))


if __name__ == "__main__":
    main()