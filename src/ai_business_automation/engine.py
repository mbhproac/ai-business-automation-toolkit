"""Action executor: deterministic templates, host allowlisting and optional AI."""

import asyncio
import ipaddress
import json
import logging
import socket
from string import Template
from urllib.parse import urlsplit

import httpx

from .config import Settings
from .models import Workflow
from .storage import Store
from .workflows import load_workflow

logger = logging.getLogger(__name__)


def render(template: str, payload: dict) -> str:
    # Only `${field}` substitution; no eval, arbitrary code or nested object inspection.
    safe = {key: str(value) for key, value in payload.items() if isinstance(value, (str, int, float, bool))}
    return Template(template).safe_substitute(safe)


def validate_destination(url: str, allowed_hosts: set[str]) -> str:
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    if (
        parsed.scheme != "https" or not host or host not in allowed_hosts
        or parsed.username or parsed.password or parsed.port not in (None, 443)
    ):
        raise ValueError("Outbound destination must be an allowlisted HTTPS host")
    # Fail closed for IP literals and locally/reserved-resolving hostnames.
    try:
        ips = {ipaddress.ip_address(host)}
    except ValueError:
        ips = {
            ipaddress.ip_address(info[4][0])
            for info in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        }
    if not ips or any(not ip.is_global for ip in ips):
        raise ValueError("Outbound destination resolves to restricted network")
    return url


async def execute_action(action, payload: dict, settings: Settings) -> str:
    if action.type == "record":
        return render(action.message or "Event recorded", payload)
    if action.type == "http_post":
        url = validate_destination(action.url, settings.http_hosts)
        # Disallow redirects to prevent redirect-based network pivoting.
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds, follow_redirects=False,
                                     trust_env=False) as client:
            response = await client.post(url, json={"event": payload, "action": action.name})
            response.raise_for_status()
        return f"HTTP {response.status_code}"
    if action.type == "ai_summarize":
        # Optional provider-independent AI action: configured via OpenAI-compatible API.
        # Never send data without explicitly supplying a model, endpoint and API key.
        import os

        token = os.environ.get("AIBAT_AI_API_KEY")
        endpoint = os.environ.get("AIBAT_AI_ENDPOINT")
        model = os.environ.get("AIBAT_AI_MODEL")
        if not all([token, endpoint, model]):
            raise RuntimeError("AI requires AIBAT_AI_API_KEY, AIBAT_AI_ENDPOINT, AIBAT_AI_MODEL")
        validate_destination(endpoint, settings.http_hosts)
        prompt = render(action.prompt, payload)
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds,
                                     follow_redirects=False, trust_env=False) as client:
            response = await client.post(
                endpoint,
                headers={"Authorization": f"Bearer {token}"},
                json={"model": model, "messages": [{"role": "user", "content": prompt}]},
            )
            response.raise_for_status()
            result = response.json()["choices"][0]["message"]["content"]
        return str(result)[:1000]
    raise ValueError("Unknown action")


async def process_job(store: Store, settings: Settings, job: dict) -> None:
    try:
        workflow: Workflow = load_workflow(settings.workflows_dir, job["workflow_id"])
        payload = json.loads(job["payload"])
        # Track successful action steps to avoid replaying them across normal retries.
        completed = {e["detail"] for e in store.events(job["id"]) if e["kind"] == "action_done"}
        for index, action in enumerate(workflow.actions):
            marker = f"{index}:{action.name}"
            if marker in completed:
                continue
            result = await execute_action(action, payload, settings)
            store.event(job["id"], "action_result", result)
            store.event(job["id"], "action_done", marker)
        store.complete(job["id"])
        store.event(job["id"], "completed", "Workflow succeeded")
    except Exception as exc:
        # Never write request bodies, API keys, prompt contents or remote response bodies to logs.
        logger.warning("Job %s failed: %s", job["id"], type(exc).__name__)
        store.failed(job["id"], type(exc).__name__, settings.max_retries)
        store.event(job["id"], "attempt_failed", type(exc).__name__)


async def run_worker(settings: Settings, once: bool = False) -> None:
    store = Store(settings.database_path)
    while True:
        job = store.claim(settings.worker_lease_seconds)
        if job:
            await process_job(store, settings, job)
        if once:
            return
        if not job:
            await asyncio.sleep(settings.worker_poll_seconds)
