from fastapi.testclient import TestClient

from ai_business_automation.api import app
from ai_business_automation.config import get_settings


def test_api_auth_idempotency_and_job_status(settings):
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as client:
            assert client.get("/health").status_code == 200
            assert client.post("/v1/events/lead_intake", json={"data": {}}).status_code == 401
            headers = {"X-API-Key": settings.api_key, "Idempotency-Key": "one"}
            a = client.post("/v1/events/lead_intake", headers=headers,
                            json={"data": {"company": "Acme"}})
            b = client.post("/v1/events/lead_intake", headers=headers,
                            json={"data": {"company": "Other"}})
            assert a.status_code == 202
            assert a.json()["id"] == b.json()["id"]
            detail = client.get(f"/v1/jobs/{a.json()['id']}", headers=headers)
            assert detail.status_code == 200
            assert detail.json()["status"] == "queued"
            assert client.get("/v1/workflows", headers=headers).json()[0]["id"] == "lead_intake"
    finally:
        app.dependency_overrides.clear()
