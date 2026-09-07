# ADR 2: Human Approval Gates at Design and Release

## Status

Accepted.

## Context

The assignment requires "controlled autonomy": agents execute
multi-step work, but humans provide oversight, approvals, and final
quality control. The orchestrator has to decide, for each of its 8
stages, which ones an agent may complete unattended and which ones
require an explicit human decision before the workflow can proceed.

## Decision

Two stages require a human decision the workflow cannot bypass:

- **Design approval** -- gates `implement`. No candidate code is ever
  generated from an unapproved design.
- **Release approval** -- gates `release`, and additionally requires
  `tests`, `security`, `compliance`, and `docs` to all be `passed`
  first (`orchestrator/approvals.py`).

Requirements review is a third human checkpoint, but is intentionally
handled differently: it can return the workflow to `NEEDS_CLARIFICATION`
without any downstream artifact existing yet, so there is nothing at
that point for an agent to have gotten wrong -- only a human decision
about scope.

## Rationale

- **Design** is the point where architecture and scope commitments are
  made (e.g., the SQLite concurrency correction recorded in
  `docs/scenarios/brownfield-daily-analytics.md`'s decision lineage)
  -- mistakes here are expensive to unwind once code exists.
- **Release** is the last point before the change is considered
  ready; by construction it is gated on the deterministic checks
  passing first, so the human is confirming a fully-validated state,
  not substituting their judgment for the checks.
- Both approval functions require a **recorded rationale**, not just
  an approve/reject click (`request_release_approval` raises
  `ValueError` if the rationale is blank) -- the decision has to be
  defensible after the fact, not just logged as a timestamp.
- Stages that are deterministic and reversible (tests, security,
  compliance, docs) do **not** get a human gate of their own; adding
  one for every stage would make "controlled autonomy" indistinguishable
  from "no autonomy."

## Consequences

- The workflow cannot be fully automated end-to-end without a human
  present at exactly two points, by design.
- `run_pipeline.py` reflects this deliberately: it drives every other
  stage forward automatically and only pauses at these two gates
  (plus the human-only script for requirements clarification), rather
  than trying to script around them.
- If a future stage were added that could cause irreversible external
  effects (e.g., an actual deployment step), this ADR's own logic
  implies it should get the same treatment: a required, rationale-backed
  human decision, not a silent pass-through.
