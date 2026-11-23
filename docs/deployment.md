# Deployment & publication

## Local installation
```bash
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -e '.[dev]'
cp .env.example .env    # Windows: copy .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
# Put the generated token in AIBAT_API_KEY in .env
pytest -q
uvicorn ai_business_automation.api:app --host 127.0.0.1 --port 8000
# In a second terminal (same environment):
aibat worker
```

## Docker Compose
```bash
cp .env.example .env
# Edit .env, supply a long random API key
# Docker Compose mounts workflows read-only and persists SQLite in a named volume.
docker compose up --build -d
curl http://127.0.0.1:8000/health
```

## Publish on GitHub (public)
1. Inspect all files and confirm that no secrets, customer names, proprietary documents or client information are present.
2. Create a **public**, empty GitHub repository named `ai-business-automation-toolkit` (do not initialize with a README or license).
3. From this project folder, run:
```bash
git init -b main
git add .
git commit -m "feat: initial secure automation toolkit"
git remote add origin https://github.com/YOUR_USERNAME/ai-business-automation-toolkit.git
git push -u origin main
```
4. In GitHub Settings, enable Dependabot alerts, secret scanning, private vulnerability reporting and branch protection. Verify the CI workflow passes.
5. Configure repository description, topics (`python`, `automation`, `webhooks`, `fastapi`, `workflows`), license and optional social preview.

**Do not push `.env`, internal workflow secrets, production databases or clients' source data.**

## Production readiness checklist
- TLS reverse proxy, request body limit and API rate limiting at edge
- Restrict network access and outbound egress; audit allowlist hosts
- Per-deployment secrets management and regular key rotation
- Backups and restore drill for SQLite volume
- Monitoring, alerts, job age tracking and log collection
- AI provider/privacy approval before enabling AI steps
- Run a staging deployment and verify external integrations are idempotent
- For multi-node/high-volume operation, replace SQLite with PostgreSQL + a distributed queue
