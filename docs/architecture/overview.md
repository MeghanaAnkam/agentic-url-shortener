# Architecture Overview

Generated: 2026-09-06T04:36:02.699924+00:00

## Components

- FastAPI URL-shortener application
- SQLite URL and daily-click storage
- Requirements agent
- Dependency-graph planner and scheduler
- Human design and release approval gates
- Candidate implementation agent
- Isolated validation runner
- Deterministic security agent
- Deterministic compliance agent
- Documentation and release-readiness stages
- Persistent JSON workflow checkpoints

## Workflow

    requirements
        -> design [human approval]
            -> implement
                -> tests
                -> security
                -> compliance
                -> docs
                    -> release [human approval]

Tests, security, compliance, and documentation can execute
independently after implementation. Release waits for all four to
pass.

## Safety Controls

- Human approval before implementation and release
- Bounded test retries
- Persistent failure states
- Candidate validation before application
- Original application backup
- Secret-file checks
- Compliance review for PII, tracking terms, and scope violations
- Controlled SQLite lock timeout
- Atomic lifetime and daily counter updates
- Safe stop when dependencies or approvals are missing
- Rollback of applied candidates to the pre-apply backup

## Data Model

The urls table stores the original URL, short code, lifetime clicks,
and creation timestamp.

The daily_clicks table stores one counter for each short code and UTC
calendar date.
