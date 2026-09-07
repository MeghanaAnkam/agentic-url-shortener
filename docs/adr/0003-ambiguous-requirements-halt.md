# ADR 3: Ambiguous Requirements Halt Execution

## Status

Accepted.

## Context

A vague requirement (e.g., "improve the analytics") could be handled
two ways: an agent could infer a reasonable scope and proceed, or it
could stop and ask. Proceeding on an inferred scope risks building the
wrong thing confidently; stopping costs a round-trip.

## Decision

`requirements_agent.py` returns a `NEEDS_CLARIFICATION` status instead
of proposing architecture when the request does not state a concrete,
testable outcome. The prompt explicitly instructs the model:

> "Improve analytics" does not confirm event tracking, database
> changes, dashboards, or new metrics. Ask what outcome the user
> wants before proposing architecture.

When this happens, the `requirements` task is marked `blocked`, not
`passed` or `failed` -- the workflow is correctly waiting on a human,
not stuck in error. See `docs/scenarios/ambiguous.md` for the
recorded example.

## Rationale

- Current system facts (e.g., "no dashboard exists today") are
  explicitly separated from requested changes in the prompt, so the
  model cannot silently reinterpret existing behavior as a feature
  request.
- The assignment names "identify ambiguity" as a distinct evaluated
  capability, separate from "interpret intent" -- treating every
  vague request as resolvable by inference would collapse that
  distinction.
- The cost asymmetry is real: a wrong guess here means the
  `design`, `implement`, `tests`, `security`, and `compliance` stages
  can all complete successfully against the wrong scope, and the
  mistake is only caught (if at all) at `release` -- far more
  expensive than one clarifying question up front.

## Consequences

- Genuinely ambiguous requests cost one round-trip before any design
  or code work begins.
- `update_requirement.py` handles the case where a requirement changes
  *after* clarification: it archives the prior workflow state and
  resets downstream tasks to `pending`, rather than trying to patch a
  partially-completed run against a new scope.
- This means the system can never demonstrate "it guessed correctly on
  a vague request" as a feature -- that outcome is intentionally
  unavailable, not merely untested.
