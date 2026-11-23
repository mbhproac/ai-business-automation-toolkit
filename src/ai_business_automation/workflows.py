"""Load validated workflow JSON at startup / per call."""

import json
from pathlib import Path

from .models import Workflow


def load_workflow(workflows_dir: Path, workflow_id: str) -> Workflow:
    # The ID is validated independently from untrusted URL route parameters.
    if not workflow_id or not workflow_id.replace("_", "").replace("-", "").isalnum():
        raise ValueError("Invalid workflow ID")
    path = workflows_dir / f"{workflow_id}.json"
    if not path.is_file():
        raise FileNotFoundError(workflow_id)
    wf = Workflow.model_validate(json.loads(path.read_text(encoding="utf-8")))
    if wf.id != workflow_id:
        raise ValueError("Workflow filename and ID do not match")
    if not wf.enabled:
        raise ValueError("Workflow disabled")
    return wf


def list_workflows(workflows_dir: Path) -> list[Workflow]:
    return [
        load_workflow(workflows_dir, path.stem)
        for path in sorted(workflows_dir.glob("*.json"))
        if _is_enabled(path)
    ]


def _is_enabled(path: Path) -> bool:
    return bool(json.loads(path.read_text(encoding="utf-8")).get("enabled", True))
