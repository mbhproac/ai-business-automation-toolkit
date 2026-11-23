"""Command line interface."""

import asyncio
import json
from pathlib import Path

import typer

from .config import get_settings
from .engine import run_worker
from .storage import Store
from .workflows import list_workflows

app = typer.Typer(help="Business event automation, locally or via API")


@app.command()
def worker(once: bool = typer.Option(False, help="Process one available job then exit")) -> None:
    asyncio.run(run_worker(get_settings(), once=once))


@app.command()
def workflows() -> None:
    for wf in list_workflows(get_settings().workflows_dir):
        typer.echo(f"{wf.id}: {wf.description}")


@app.command()
def submit(workflow_id: str, input_file: Path,
           idempotency_key: str | None = None) -> None:
    data = json.loads(input_file.read_text(encoding="utf-8"))
    job = Store(get_settings().database_path).enqueue(
        workflow_id, data, f"{workflow_id}:{idempotency_key}" if idempotency_key else None
    )
    typer.echo(job["id"])


if __name__ == "__main__":
    app()
