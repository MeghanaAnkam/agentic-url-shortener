# ADR 1: SQLite for Storage

## Status

Accepted.

## Context

The system needs to persist short URLs, lifetime click counts, and
daily click counts, with correctness guarantees under concurrent
redirects (many visitors clicking the same short link at once).

## Decision

Use SQLite, with `BEGIN IMMEDIATE` transactions on the redirect path
and a bounded lock-wait timeout (`timeout=5`) that surfaces as an
HTTP 503 rather than blocking indefinitely or silently losing an
increment.

## Rationale

- The assignment scope is a 2-3 day prototype demonstrating
  engineering judgment, not a production deployment -- a
  zero-configuration embedded database keeps setup to one command
  (`pip install -r requirements.txt`) with nothing else to provision.
- SQLite's single-writer model is a real constraint, not a hidden one:
  it forces an explicit answer to "what happens under concurrent
  writes," which is answered here with `BEGIN IMMEDIATE` (fails fast
  and safely rather than corrupting a count) instead of leaving it
  undefined.
- The lifetime `clicks` counter and the corresponding `daily_clicks`
  row are updated in the same transaction, so the two can never drift
  out of sync from a partial write -- this property matters more than
  the storage engine reads.

## Consequences

- Write throughput is bounded by SQLite's single-writer limit; this is
  named explicitly in `README.md` under Limitations rather than
  discovered by a reader.
- A production deployment would need a database supporting concurrent
  writers (e.g., PostgreSQL); the schema (two tables, one foreign key)
  would carry over largely unchanged -- the transaction boundary is
  the part that would need re-verifying under a different engine's
  isolation guarantees.
