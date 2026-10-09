# Security checks and remaining limits

| Asset / threat | Control | Evidence | Remaining limit |
| --- | --- | --- | --- |
| Provider credential leakage | SecretStr, ignored environment, no auth headers in recordings, redacted errors, credential-echo rejection | Fake canary tests cover prompt, DB, recordings, logs, failure responses, and rendered UI; Git history scan | Trusted local operator and provider receive runtime access; not a managed secret service |
| Document prompt injection | Instructions/data separated; no model execution, browsing, approval, or DB tools | Attack is supplied only as user data; a fabricated approved field fails the contract | Generated wording can still be influenced; review remains necessary |
| Unsupported or stale approval | Exact revision, source checks, explicit semantic confirmation, expected dataset inside transaction | Revision/reset, source-race, authority-removal, and version-change tests | Semantic confirmation is a human decision, not automatic proof |
| Consumption / availability | Input limits, one application-process request, persisted attempts, local rate limit, overall deadline, bounded retries | Budget survives reopen; delayed-response and retry-delay tests | Limits are per local database/process, not an account-wide distributed quota |
| SQL / local exposure | Parameterized queries, foreign keys, short connections/transactions, DB mode 0600, localhost binding, CORS/XSRF, host allowlist | Workflow/persistence tests, config, and container recreation checks | No verified login, organization isolation, encrypted storage, or public deployment |
| Build and delivery | Explicit COPY/package allowlists, ignored secrets/state, digest-pinned bases, pinned actions, read-only CI | Fake environment excluded from image; package replay smoke test; Gitleaks and dependency audit | Dependency checks are point-in-time; maintain and re-evaluate before production deployment |

Inputs are fictional. No external document URLs are fetched, and source/model passages are
rendered as plain text. Explanations and raw model responses are review evidence, not instructions
to execute. Tests use isolated fake credentials; no test response is substituted for real replay.
