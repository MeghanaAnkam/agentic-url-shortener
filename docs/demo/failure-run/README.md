# Failure-Path Demonstration

This is not a happy-path-only system. This demonstration shows a
**genuinely broken candidate being caught and blocked**, using the
real `orchestrator.compliance_agent` and `orchestrator.approvals`
functions -- not a scripted transcript.

The broken code lives only in an isolated temp directory created for
this demonstration. **The application shipped in this repository was
never touched.**

Regenerate it yourself: the script is
[`generate_failure_demo.py`](../../../generate_failure_demo.py).

---

## 1. The Deliberately Broken Candidate

```python
# Deliberately broken candidate: this line would leak a visitor's IP
# address, which is explicitly out of scope for this project.
def log_visitor(request):
    ip_address = request.client.host
    return ip_address
```

This directly violates two things the approved requirement explicitly
rules out (see
[`requirements/daily_clicks.txt`](../../../requirements/daily_clicks.txt)):

> Out of scope:
> - Dashboard
> - **IP addresses, device details, or referrers**
> - Date filters
> - Automatic deletion

## 2. Real Compliance Check Result

`orchestrator.compliance_agent.run_compliance_review()` was run for
real against this broken candidate
([full report](./artifacts/compliance_report.json)):

```json
{
  "status": "failed",
  "findings": [
    "Possible PII/tracking term found in application source: 'ip_address'",
    "Possible PII/tracking term found in application source: 'client.host'",
    "Out-of-scope item 'IP addresses, device details, or referrers' (from daily_clicks.txt) appears implemented: found 'ip_address' in source.",
    "Out-of-scope item 'IP addresses, device details, or referrers' (from daily_clicks.txt) appears implemented: found 'client.host' in source."
  ]
}
```

Two independent checks caught this: the generic PII/tracking-term
scan, and the requirement-specific out-of-scope scan (which cites the
exact line in the requirement document that was violated).

## 3. Real Release-Approval Refusal

With `compliance` now `failed`, a real, unmodified call to
`orchestrator.approvals.request_release_approval()` was made. It
raised, rather than prompting a human for a decision at all:

```
ValueError: Release blocked. Incomplete tasks: ['compliance', 'security']
```

(`security` also appears because this isolated demo only exercised
the compliance gate; in a real run both would need to pass
independently -- neither gate can compensate for the other.)

This is the actual guard clause in `approvals.py`, not a check written
for this demo:

```python
incomplete = [
    task_id
    for task_id in required_tasks
    if statuses.get(task_id) != "passed"
]

if incomplete:
    raise ValueError(
        f"Release blocked. Incomplete tasks: {sorted(incomplete)}"
    )
```

A human is never even asked to approve or reject in this state -- the
system refuses to present the option.

## 4. Final State

From [`workflow.json`](./artifacts/workflow.json):

| Task | Status |
|---|---|
| requirements | passed |
| design | passed |
| implement | passed |
| tests | passed |
| security | pending |
| **compliance** | **failed** |
| docs | passed |
| **release** | **pending (never started)** |

`release_approval` remains `pending` -- not `rejected`, because a
rejection implies a human made a decision. Here, no decision was ever
offered, because the gates that must pass before a human is even asked
did not pass.

---

## What This Demonstrates

- Validation gates are not advisory -- a real failure genuinely blocks
  progress, verified by an actual raised exception, not a described
  behavior
- Two independent detection mechanisms (generic PII scan,
  requirement-specific scope scan) both caught the same violation
- The system fails closed: no human approval prompt appears until the
  automated gates pass, removing the chance of a rushed "approve
  anyway" click
- For the complementary case -- a real rollback of an already-applied
  change -- see
  [`docs/scenarios/audit-retry-demo.md`](../../scenarios/audit-retry-demo.md)
