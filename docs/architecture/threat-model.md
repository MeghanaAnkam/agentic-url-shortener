# Threat Model

## Scope

This threat model covers both:

1. the URL-shortener application; and
2. the agentic software-engineering orchestration layer.

The goal is not to claim production-grade security, but to identify important failure modes and show where deterministic controls constrain agent behavior.

## Trust Boundaries

```text
Human Operator
      |
      v
Agentic Orchestrator
      |
      +--------> Hosted LLM API
      |
      +--------> Candidate Workspace
      |
      +--------> Deterministic Validation
                    |
                    +-- Tests
                    +-- Security checks
                    +-- Compliance checks
      |
      v
Live Application
      |
      v
SQLite Database
```

The LLM is treated as an untrusted probabilistic component.

Security-sensitive decisions are therefore enforced outside the model whenever practical.

## Threats and Mitigations

| Threat                                    | Risk                               | Current mitigation                                                                         |
| ----------------------------------------- | ---------------------------------- | ------------------------------------------------------------------------------------------ |
| Malicious or malformed URL input          | Invalid application state or abuse | HTTP/HTTPS URL validation                                                                  |
| SQL injection                             | Database compromise                | Parameterized SQL                                                                          |
| Concurrent analytics writes               | Lost or inconsistent counters      | Transaction handling, atomic increments, bounded lock wait                                 |
| Secret committed to source                | Credential exposure                | Tracked-secret checks and `.gitignore` guidance                                            |
| Private key committed                     | Credential compromise              | Security validation blocks tracked secrets/private-key material                            |
| Dangerous generated Python                | Arbitrary execution                | Deterministic checks for dangerous calls such as `eval`, `exec`, and unsafe subprocess use |
| AI modifies live code directly            | Unreviewed production mutation     | Candidate isolation                                                                        |
| Source changes after validation           | Applying stale/unreviewed code     | Hash-pinned validation and apply                                                           |
| Bad generated change                      | Application regression             | Test gate before release                                                                   |
| Policy/privacy regression                 | PII or out-of-scope behavior       | Compliance gate                                                                            |
| Agent bypasses human review               | Excessive autonomy                 | Explicit requirements/design/release approvals                                             |
| Infinite corrective loop                  | Resource exhaustion                | Bounded retry policy                                                                       |
| Ambiguous requirement                     | Silent scope invention             | `NEEDS_CLARIFICATION` safe-stop                                                            |
| Failed applied candidate                  | Broken application state           | Backup and rollback                                                                        |
| Prompt injection against model            | Agent may propose unsafe output    | Model output remains candidate data; deterministic gates execute outside the model         |
| Hosted-model outage                       | Workflow interruption              | Model fallback and safe failure                                                            |
| API-key leakage through runtime artifacts | Credential exposure                | `.env` excluded from version control; runtime artifacts excluded                           |

## Agent-Specific Threat Principle

The orchestration system does not assume that the model will always follow instructions.

The model may propose designs or implementation changes, but deterministic code controls whether those outputs may advance.

For example:

```text
LLM proposes implementation
          |
          v
      Candidate
          |
          v
Tests + Security + Compliance
          |
      PASS?
      /   \
    no     yes
    |       |
 BLOCK    Human release approval
```

The LLM therefore cannot directly declare its own output safe.

## Residual Risks

The current prototype does not address all production threats.

Important remaining risks include:

* authentication and authorization;
* per-user URL ownership;
* abuse and spam prevention;
* rate limiting;
* distributed database concurrency;
* hardened execution sandboxing;
* dependency vulnerability scanning;
* network isolation for generated-code execution;
* production secret-management infrastructure;
* denial-of-service protection.

These are documented as prototype boundaries rather than hidden assumptions.

## Security Design Principle

**Probabilistic components propose; deterministic controls decide whether the proposal may advance.**
