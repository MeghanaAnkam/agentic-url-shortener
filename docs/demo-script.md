# Agentic URL Shortener Demo Script

## 1. Introduction

This prototype demonstrates an agentic software-engineering system that
converts requirements into reviewed, tested, secure, and release-ready
engineering outcomes.

Agents operate within controlled boundaries. Humans own requirement,
design, and release decisions.

## 2. Working Application

Start the API:

    python -m uvicorn app.main:app --reload

Open:

    http://127.0.0.1:8000/docs

Demonstrate:

1. Health check
2. Create a short URL
3. Redirect through the short URL
4. View lifetime and UTC daily analytics

## 3. Ambiguous Requirement

Show the input:

    Improve the analytics in my URL shortener.

Explain that the requirements agent returned NEEDS_CLARIFICATION and
prevented downstream implementation.

## 4. Brownfield Requirement

Show the clarified daily-count requirement and explain:

- Existing API compatibility was preserved.
- Historical daily data was not fabricated.
- Personal information was not collected.
- Database design required human approval.

## 5. Orchestration Graph

Explain:

    requirements
        -> design [approval]
            -> implementation
                -> tests
                -> security
                -> compliance
                -> documentation
                    -> release [approval]

Tests, security, compliance, and documentation form parallel
branches that synchronize before release.

## 6. Human Governance

Show that implementation was blocked until design approval.

Show that release remained blocked until:

- Tests passed
- Security passed
- Documentation passed
- Human release approval was recorded

No production deployment was performed.

## 7. Reliability and Recovery

Show the audit demonstration:

- 24 audit events
- 8 total attempts
- 1 bounded retry
- 12.5% retry frequency
- 0.051-second MTTR
- 0.4-second end-to-end latency
- 100% final task success

Clearly state that the failure was intentionally simulated for a
controlled observability demonstration.

## 8. Security

Explain the deterministic checks:

- Secret and private-key files
- Dangerous eval/exec usage
- subprocess shell=True
- URL validation
- Parameterized SQL
- Foreign-key enforcement
- Atomic counter updates
- Controlled database lock timeout

## 8b. Compliance

Explain the deterministic compliance checks, which are distinct from
security (code safety) -- these check data-privacy and scope:

- PII and tracking-term scan of the application source
- PII-shaped database column scan
- Requirement out-of-scope violation detection (e.g. dashboard,
  device tracking, date filters, automatic deletion)

Release is blocked until compliance passes, the same as security.

## 9. Engineering Judgment

Important human corrections included:

- SQLite has one writer at a time, not row-level write locking.
- Lifetime and daily counters must update atomically.
- Only lock-related database errors become 503 responses.
- Historical analytics must never be fabricated.
- Generated code must be validated before application.

## 10. Limitations

- SQLite is not intended for distributed high-volume production.
- Authentication is not implemented.
- Rate limiting is not implemented.
- Gemini availability depends on API quotas.
- Two test dependency deprecation warnings remain.

## 11. Closing

The system demonstrates agents executing multi-step engineering work
while humans retain control over scope, architecture, and release.