"""Authenticated webhook ingestion and job status API."""

import hmac
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, status

from .config import Settings, get_settings
from .models import EventIn, JobOut
from .storage import Store
from .workflows import list_workflows, load_workflow


@asynccontextmanager
async def lifespan(app: FastAPI):
    override = app.dependency_overrides.get(get_settings)
    settings = override() if override else get_settings()
    Store(settings.database_path)
    yield


app = FastAPI(title="AI Business Automation Toolkit", version="0.1.0", lifespan=lifespan,
              docs_url=None, redoc_url=None, openapi_url=None)


def authorize(x_api_key: str | None = Header(default=None),
              settings: Settings = Depends(get_settings)) -> Settings:
    if not x_api_key or not hmac.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return settings


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/v1/workflows", dependencies=[Depends(authorize)])
def workflows(settings: Settings = Depends(get_settings)) -> list[dict]:
    return [{"id": w.id, "description": w.description} for w in list_workflows(settings.workflows_dir)]


@app.post("/v1/events/{workflow_id}", response_model=JobOut, status_code=202)
def accept_event(workflow_id: str, event: EventIn,
                 idempotency_key: str | None = Header(default=None, max_length=128),
                 settings: Settings = Depends(authorize)) -> dict:
    try:
        load_workflow(settings.workflows_dir, workflow_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Unknown workflow") from None
    except ValueError:
        raise HTTPException(status_code=422, detail="Workflow not available") from None
    # Namespace idempotency keys by workflow: the same key can be used for a different workflow.
    dedup_key = f"{workflow_id}:{idempotency_key}" if idempotency_key else None
    job = Store(settings.database_path).enqueue(workflow_id, event.data, dedup_key)
    return job


@app.get("/v1/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: uuid.UUID, settings: Settings = Depends(authorize)) -> dict:
    job = Store(settings.database_path).get(str(job_id))
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/v1/jobs/{job_id}/events")
def get_events(job_id: uuid.UUID, settings: Settings = Depends(authorize)) -> list[dict]:
    return Store(settings.database_path).events(str(job_id))
