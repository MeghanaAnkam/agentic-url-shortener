# Agentic URL Shortener

A production-minded URL-shortener prototype demonstrating controlled
AI-agent execution across the software-development lifecycle.

## Features

- Create short URLs
- Validate HTTP and HTTPS URLs
- Redirect using HTTP 307
- Lifetime click analytics
- Daily click counts grouped by UTC date
- SQLite transaction safety
- Explicit dependency graph
- Human design and release approvals
- Bounded retries and safe-stop behavior
- Candidate isolation and validation
- Security-review gate
- Compliance-review gate (data-privacy and scope checks)
- Documentation generation
- Audit events and reliability metrics
- Greenfield, brownfield, and ambiguous scenarios

## Architecture

The application uses FastAPI and SQLite.

The orchestration lifecycle is:

    requirements
        -> design [human approval]
            -> implementation
                -> tests
                -> security
                -> compliance
                -> documentation
                    -> release [human approval]

Tests, security, compliance, and documentation can run independently
after implementation. Release requires all four and explicit human
approval.

See `docs/architecture/overview.md` for details.

## Project Structure

    app/                 FastAPI application and tests
    orchestrator/        Workflow agents, gates, storage, and metrics
    docs/architecture/   Architecture documentation
    docs/scenarios/      Greenfield, brownfield, and ambiguous scenarios
    requirements/        Normalized engineering requirements
    reports/             Engineering and release-readiness reports
    runs/                Local runtime evidence; ignored by Git

## Setup

### 1. Create the environment

    python3 -m venv .venv
    source .venv/bin/activate

### 2. Install dependencies

    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt

### 3. Configure Gemini

Copy `.env.example` to `.env` and add a private Gemini API key.

Never commit `.env`.

### 4. Start the API

    python -m uvicorn app.main:app --reload

Open:

    http://127.0.0.1:8000/docs

## API Examples

### Create a short URL

    curl -X POST http://127.0.0.1:8000/shorten \
      -H "Content-Type: application/json" \
      -d '{"original_url":"https://www.example.com"}'

### Redirect

    http://127.0.0.1:8000/{short_code}

### Analytics

    http://127.0.0.1:8000/analytics/{short_code}

Example response:

```json
{
  "short_code": "example",
  "original_url": "https://www.example.com",
  "clicks": 5,
  "created_at": "2026-09-05T05:47:20+00:00",
  "daily_counts": [
    {
      "date": "2026-09-06",
      "count": 1
    }
  ]
}
```

## Running the Full Pipeline

Each stage can still be run individually (see the scripts in
`orchestrator/`), but `run_pipeline.py` drives the whole workflow
forward automatically wherever no human decision is required, and
pauses cleanly at requirements review, design approval, and release
approval:

    python -m orchestrator.run_pipeline runs/<run-id>/workflow.json

Run it again after each approval to continue from where it stopped.
It never auto-approves anything; it only removes the need to
remember which script to run next.

## Testing

Run:

    python -m pytest app/tests -q

Current verified result:

    65 passed

Two dependency deprecation warnings remain and are documented as a
known limitation.

## Demonstrated Scenarios

- Greenfield URL-shortener construction
- Brownfield daily-analytics enhancement
- Ambiguous analytics request with safe clarification stop
- Controlled audit, retry, and recovery demonstration
- Test-improvement: closing a release-gate coverage gap

See `docs/scenarios/`.

## Reliability Evidence

The audit demonstration recorded:

- 8 completed tasks
- 10 total attempts
- 2 bounded retries (one test retry, one post-rollback re-implementation)
- 1 rollback
- ~0.03-second MTTR
- ~0.4-second end-to-end latency
- 32 audit events

These values come from a labelled local demonstration, not production
traffic.

## Security Controls

- HTTP/HTTPS validation
- Parameterized SQL
- SQLite foreign-key enforcement
- Atomic analytics increments
- Bounded database lock wait
- Controlled 503 response
- Tracked-secret checks
- Dangerous Python-call checks
- Human design and release approvals

## Compliance Controls

- PII and tracking-term scan of application source
- PII-shaped database column scan
- Requirement out-of-scope violation detection
- Release blocked until compliance passes

## Limitations

- SQLite permits limited write concurrency.
- Authentication and user ownership are not implemented.
- Rate limiting is not implemented.
- The prototype is not publicly deployed.
- Gemini availability depends on hosted API limits.
- Test dependency deprecation warnings remain.

## Governance Principle

Agents execute within defined autonomy boundaries. Humans own
requirements approval, design correction, release approval, and final
quality decisions.

## Important Security Note

Never commit `.env`, API keys, database files, private keys, or runtime
artifacts.
