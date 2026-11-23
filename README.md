# AI Business Automation Toolkit

Python toolkit for webhook-driven business workflows with secure ingestion, durable execution, retries, an audit trail and optional AI enrichment.

**Status:** usable single-host reference implementation (v0.1.0). Production-oriented engineering practices are included, but external deployment controls and integration-specific tests are required before serving real customer data.

## Features

- FastAPI endpoint for receiving structured business events
- Strong API-key check, idempotent event ingestion and persistent SQLite queue
- Independent worker with leases, bounded retries and action-level audit trail
- Declarative JSON workflows (no dynamic Python execution)
- `record`, allowlisted HTTPS `http_post`, and opt-in OpenAI-compatible `ai_summarize` actions
- CLI, Docker Compose, pytest suite and GitHub Actions CI

## Quick start

Requires Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
pip install -e '.[dev]'
cp .env.example .env  # Windows: copy .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
# Replace AIBAT_API_KEY in .env with the generated secret
uvicorn ai_business_automation.api:app --host 127.0.0.1 --port 8000
```

Start a worker in another terminal:

```bash
aibat worker
```

Send a sample business lead:

```bash
curl -X POST http://127.0.0.1:8000/v1/events/lead_intake \
  -H "X-API-Key: YOUR_SECRET" \
  -H "Idempotency-Key: sample-lead-001" \
  -H "Content-Type: application/json" \
  -d '{"data":{"company":"Example Corp","contact":"Sam","interest":"monthly accounting"}}'
```

Get `id` from the response, then:

```bash
curl -H "X-API-Key: YOUR_SECRET" http://127.0.0.1:8000/v1/jobs/JOB_UUID
curl -H "X-API-Key: YOUR_SECRET" http://127.0.0.1:8000/v1/jobs/JOB_UUID/events
```

## Example business automations

- **Lead intake:** record and route an inbound CRM lead (`workflows/lead_intake.json`)
- **Customer follow-ups:** add a reviewed HTTPS action to an allowlisted CRM endpoint
- **Invoice administration:** integrate an accounting system's webhook without publishing customer data
- **AI summaries:** enable the opt-in AI workflow only after configuring a compliant provider and data controls

Workflows are JSON configuration files stored in `workflows/`. Each workflow must have an `id` equal to the filename. The example AI workflow ends in `.example.json` and is not activated by default. To activate, rename to `ai_lead_summary.json`, set `enabled` to true, provide the AI environment variables, and allowlist its endpoint host.

### HTTP action example

```json
{"id":"lead_intake","description":"Notify CRM","actions":[{"type":"http_post","name":"notify_crm","url":"https://crm.example.com/hooks/lead"}]}
```

Set `AIBAT_ALLOWED_HTTP_HOSTS=crm.example.com`. Actions send the event under an `event` key. The HTTP action is at-least-once; see [Security](SECURITY.md) for duplicate-delivery and network risks.

## Commands

```bash
aibat workflows
aibat submit lead_intake examples/lead_received.json
aibat worker --once
pytest -q
```

## Documentation

- [Architecture and delivery guarantees](docs/architecture.md)
- [Deployment and public GitHub publication](docs/deployment.md)
- [Security and privacy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)

## License

MIT. See [LICENSE](LICENSE).
