# Architecture

```text
Client --(X-API-Key / Idempotency-Key)--> FastAPI --(atomic insert)--> SQLite jobs
                                                                  |
                                                     worker --(lease/claim)
                                                                  |
                                            validated JSON workflow actions
                                              |          |         |
                                           record      HTTPS      AI*
                                              |          |         |
                                          audit events / job status
```

*AI is optional and disabled until explicitly configured.*

## Delivery semantics
- Ingestion is at-least-once without an idempotency key; the same key within a workflow returns the existing job.
- A single worker claims jobs transactionally. Multiple local workers use SQLite transactions; network filesystem shares are not supported.
- Individual action completion is recorded. A crash in the gap between outbound side effects and audit write can replay that action.
- Exponential retries use a bounded delay; failed jobs remain inspectable.
- Retention, dead-letter requeue, dashboards, per-customer tenancy and distributed scheduling are future extensions.

## Threat model
Trusted administrators control workflow definitions. Untrusted callers must present the API key and can only submit event data. Templating does not evaluate code. HTTPS host validation checks DNS and blocks local addresses, but infrastructure egress controls are still required. Do not expose the API without TLS, network access policy and rate limiting.
