# Idempotency and Rerun Behavior

## Purpose

The workflow is designed to be safely resumed after a human approval, transient failure, validation failure, or process restart.

A rerun should continue from persisted workflow state rather than blindly repeat completed work.

## Workflow Resume Behavior

The full pipeline is invoked with:

```bash
python -m orchestrator.run_pipeline runs/<run-id>/workflow.json
```

The workflow state stored for the run is treated as the source of truth.

On each invocation, the driver evaluates the current task states and advances only work that is eligible to run.

Human approval gates are never bypassed automatically.

Typical execution therefore looks like:

```text
Run #1
Requirement analysis
        ↓
Requirements approval required
        ↓
STOP

Human approves requirements

Run #2
Resume existing workflow
        ↓
Design
        ↓
Design approval required
        ↓
STOP

Human approves design

Run #3
Resume existing workflow
        ↓
Implementation
        ↓
Tests / Security / Compliance / Documentation
        ↓
Release approval required
        ↓
STOP

Human approves release

Run #4
Resume existing workflow
        ↓
Release completed
```

## Idempotency Strategy

Idempotency means that repeating an orchestration command should converge toward the same intended workflow state instead of creating duplicate work or silently repeating side effects.

The prototype applies this principle through several controls.

### Persisted task state

Completed tasks remain completed when the same workflow is resumed.

The scheduler uses persisted state and dependency information to determine which tasks are ready.

### Explicit approval state

Requirements, design, and release decisions are persisted.

Restarting the pipeline does not automatically recreate or bypass those decisions.

### Candidate isolation

Generated implementation changes are written as candidates before they affect the live application.

Validation occurs against the candidate before application.

### Hash-pinned application

Validated source content is identified by its hash.

If the underlying source changes between validation and application, application refuses rather than silently applying a stale candidate.

### Backup before mutation

Before a validated candidate replaces the live source, the existing source is backed up.

This provides a deterministic recovery point for rollback.

### Bounded retries

Retries are explicit and limited.

A failed test execution receives at most the configured retry allowance rather than entering an unlimited retry loop.

## Requirement Changes

A requirement change is intentionally **not** treated as a simple resume.

Changing an approved requirement can invalidate assumptions made by downstream stages.

When requirements change:

1. the previous workflow state is preserved for auditability;
2. downstream artifacts and approvals are invalidated;
3. affected tasks return to pending state;
4. the dependency graph is executed again against the new requirement.

This prevents stale design or implementation decisions from silently surviving a change in scope.

## Side-Effect Safety

Operations are divided into two broad categories.

| Operation                    | Rerun behavior                                 |
| ---------------------------- | ---------------------------------------------- |
| Read workflow state          | Safe to repeat                                 |
| Compute ready tasks          | Safe to repeat                                 |
| Run deterministic validation | Safe to repeat                                 |
| Generate candidate artifact  | Regenerated or replaced as candidate state     |
| Record approval              | Persisted decision                             |
| Apply candidate              | Guarded by validation/hash checks and backup   |
| Rollback                     | Explicit human-confirmed recovery action       |
| Release                      | Requires completed gates and explicit approval |

## Current Prototype Boundary

The prototype demonstrates resumability and guarded side effects within a local workflow.

It does not implement a distributed idempotency-key service, transactional message queue, or multi-node workflow coordinator.

A production implementation would add stable operation IDs and durable transactional storage for externally visible side effects.
