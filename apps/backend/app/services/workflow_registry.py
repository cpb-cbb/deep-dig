from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.errors import AppError
from app.schemas import WorkflowOut

ROOT = Path(__file__).resolve().parents[4]
WORKFLOW_DIR = ROOT / "packages" / "workflows" / "definitions"


@lru_cache(maxsize=1)
def load_workflows() -> dict[str, dict[str, Any]]:
    workflows: dict[str, dict[str, Any]] = {}
    for path in sorted(WORKFLOW_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        workflows[data["id"]] = data
    return workflows


def list_public_workflows() -> list[WorkflowOut]:
    return [
        WorkflowOut(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            version=data["version"],
            ui_config=data.get("ui_config", {}),
        )
        for data in load_workflows().values()
    ]


def get_workflow(workflow_id: str) -> dict[str, Any]:
    workflow = load_workflows().get(workflow_id)
    if workflow is None:
        raise AppError(404, "WORKFLOW_NOT_FOUND", "Workflow not found")
    return workflow
