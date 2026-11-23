# Security policy

## Report a vulnerability
Do not open public issues containing exploit details or credentials. Use GitHub's private vulnerability reporting feature, if enabled, or contact the repository maintainer privately.

## Deployment guardrails
- Never commit `.env`, API keys, customer records or production logs.
- Bind the example container only to localhost; put a TLS reverse proxy and rate limits in front of production deployments.
- Rotate API keys and keep secrets in a secrets manager.
- Restrict egress using both `AIBAT_ALLOWED_HTTP_HOSTS` and network firewalls.
- Run untrusted workflows only after review; workflow files are treated as trusted operator configuration.
- Do not process regulated/customer data with external AI services without authorization and appropriate controls.
- Review provider data-retention terms before enabling optional AI actions.
- SQLite is suitable for a single-host deployment; use a server database and dedicated queue for distributed scale.
- HTTP actions are **at-least-once**: remote systems must support an idempotency key. A lease expiring after a successful remote call but before recording success may trigger a duplicate.
- DNS rebinding and time-of-check/time-of-use are not fully prevented by hostname resolution checks; enforce an outbound network policy at the infrastructure layer.
- Action output/audit entries may contain business information; restrict access, retention and backups.
