# Sample End-to-End Run

Brownfield scenario: **daily click analytics**, run against this
repository's actual, currently-shipped application and test suite.

This is not a mocked or hypothetical trace. Requirements, design, and
implementation reflect this project's real, already-completed history
(cited below with their original decision text). **Tests, security,
compliance, release approval, release execution, and reliability
metrics were re-executed live** for this artifact set, running the
real functions in `orchestrator/` against the real `app/` code, and
produced the JSON files in [`artifacts/`](./artifacts).

Regenerate it yourself: the exact script used is
[`generate_sample_run.py`](../../../generate_sample_run.py) at the
project root.

---

## 1. Original Requirement

The requirement as written in
[`requirements/daily_clicks.txt`](../../../requirements/daily_clicks.txt):

> Extend GET /analytics/{short_code} with daily_counts.

## 2. Normalized Requirement (Requirements Stage Output)

The requirements agent turned that one line into explicit, testable
acceptance criteria and an explicit out-of-scope list -- rather than
guessing at what "extend with daily_counts" should mean:

**Acceptance criteria**
- Always include `daily_counts` as a list of `{"date": "YYYY-MM-DD", "count": integer}`
- Group clicks by UTC calendar date and sort dates ascending
- Record daily counts only from feature activation onward -- do not backfill
- Return `[]` when there are no daily records
- Preserve all existing response fields and lifetime click counts
- Preserve the existing 404 response for unknown short codes

**Out of scope**
- Dashboard, IP addresses/device details/referrers, date filters, automatic deletion

This is the actual, real ambiguous-to-normalized path: the original
ask for this feature was informal ("improve the analytics"), which the
requirements agent correctly returned as `NEEDS_CLARIFICATION` (see
[`docs/scenarios/ambiguous.md`](../../scenarios/ambiguous.md)) before
this specific, normalized requirement was written and approved.

## 3. Generated Tasks (Planner Output)

The real dependency graph for this run, from
[`workflow.json`](./artifacts/workflow.json):

| Task | Depends on |
|---|---|
| `requirements` | -- |
| `design` | `requirements` |
| `implement` | `design` |
| `tests` | `implement` |
| `security` | `implement` |
| `compliance` | `implement` |
| `docs` | `implement` |
| `release` | `tests`, `security`, `compliance`, `docs` |

## 4. Approval Pauses (Human Checkpoints)

Real, recorded decisions from this project's actual history plus this
run's live release approval:

| Stage | Actor | Outcome | Rationale (real, recorded) |
|---|---|---|---|
| requirements | `agent:requirements` → human | approved | "Human requirements review: approve. Lifetime clicks may exceed daily totals. Concurrency handling belongs in design and must prevent lost increments." |
| design | `agent:architect` → human | approved | "Design proposal generated; human review corrected SQLite concurrency assumptions before approval." |
| **release** (this run) | `human:release-reviewer` | **approved** | "Tests, security, and compliance gates passed. Approving release for this sample-run demonstration." |

The release approval above was produced by actually calling
`orchestrator.approvals.request_release_approval()` in this run -- it
is a real, executed function call, not a transcript.

## 5. Validation Results (Live, This Run)

Executed for real against the real `app/` code and `app/tests/` suite:

**Tests** -- `orchestrator.executor.execute_tests()`
- Result: `passed` (see `test_output` in [`workflow.json`](./artifacts/workflow.json))

**Security** -- `orchestrator.security_agent.run_security_review()`
([full report](./artifacts/security_report.json)):
```json
{
  "status": "passed",
  "findings": [],
  "controls_checked": [
    "tracked secret files", "private-key files", "eval and exec usage",
    "subprocess shell=True", "HTTP/HTTPS validation", "parameterized SQL",
    "SQLite foreign keys", "bounded lock wait", "controlled 503 response",
    "atomic counter transaction"
  ]
}
```

**Compliance** -- `orchestrator.compliance_agent.run_compliance_review()`
([full report](./artifacts/compliance_report.json)):
```json
{
  "status": "passed",
  "findings": [],
  "controls_checked": [
    "PII/tracking terms in application source",
    "PII-shaped database columns",
    "requirement out-of-scope violations"
  ]
}
```

**Documentation** -- represented by this repository's real, already-committed
output of this exact feature build: [`docs/architecture/overview.md`](../../architecture/overview.md),
[`docs/scenarios/brownfield-daily-analytics.md`](../../scenarios/brownfield-daily-analytics.md),
[`reports/engineering-summary.md`](../../../reports/engineering-summary.md).
(Not re-run here, to avoid overwriting those committed files with demo output.)

## 6. Final Release Decision (Live, This Run)

`orchestrator.release_agent.execute_release()` result
([full report](./artifacts/release_report.json)):

```json
{
  "status": "release_ready",
  "release_approval": "approved",
  "gates": {
    "tests": "passed",
    "security": "passed",
    "compliance": "passed",
    "docs": "passed"
  },
  "deployment_performed": false
}
```

## 7. Reliability Metrics (Live, This Run)

`orchestrator.metrics.generate_metrics_report()` result
([full report](./artifacts/metrics.json)):

| Metric | Value |
|---|---|
| Success rate | 100% (8/8 tasks) |
| Total attempts | 4 |
| Retries | 0 |
| Rollbacks | 0 |
| End-to-end latency | 0.688s |
| Audit events recorded | 18 |

No retries or rollbacks were needed for this run -- for a demonstration
of those specific mechanics under a deliberately-forced failure, see
[`docs/scenarios/audit-retry-demo.md`](../../scenarios/audit-retry-demo.md).

---

## What This Demonstrates

- A requirement was interpreted and normalized before any code was written
- Work was decomposed into an explicit, dependency-aware task graph
- Two independent human approval checkpoints exist and were exercised
- Three independent, deterministic validation gates (tests, security,
  compliance) all ran and are individually inspectable
- The release decision is a real artifact, not an assertion
- Every claim in this document is backed by a file in [`artifacts/`](./artifacts)
  you can open and check yourself
