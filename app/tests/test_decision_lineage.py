from orchestrator.state import WorkflowState, record_decision
from orchestrator.storage import load_state, save_state


def test_structured_decision_survives_checkpoint(tmp_path):
    state = WorkflowState(requirement="Test decision lineage")

    decision = record_decision(
        state,
        actor="human:reviewer",
        stage="design",
        action="review_design",
        outcome="approved",
        rationale="Transaction boundaries are acceptable.",
        artifact_hashes={"design": "abc123"},
    )

    checkpoint = tmp_path / "workflow.json"
    save_state(state, checkpoint)
    restored = load_state(checkpoint)

    assert len(restored.decisions) == 1
    assert restored.decisions[0].id == decision.id
    assert restored.decisions[0].actor == "human:reviewer"
    assert restored.decisions[0].stage == "design"
    assert restored.decisions[0].outcome == "approved"
    assert restored.decisions[0].artifact_hashes == {
        "design": "abc123"
    }


def test_old_string_decisions_are_migrated(tmp_path):
    checkpoint = tmp_path / "legacy.json"
    checkpoint.write_text(
        """
        {
          "requirement": "Legacy workflow",
          "tasks": [],
          "decisions": ["Human approved design."],
          "artifacts": {}
        }
        """,
        encoding="utf-8",
    )

    restored = load_state(checkpoint)

    assert restored.decisions[0].actor == "legacy"
    assert restored.decisions[0].rationale == "Human approved design."