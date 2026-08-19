from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
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
        _validate_definition(data, path)
        workflow_id = data["id"]
        if workflow_id in workflows:
            raise RuntimeError(f"Duplicate workflow id {workflow_id!r}")
        workflows[workflow_id] = data
    if not workflows:
        raise RuntimeError(f"No workflow definitions found in {WORKFLOW_DIR}")
    return workflows


def list_public_workflows() -> list[WorkflowOut]:
    ordered = sorted(
        load_workflows().values(), key=lambda data: data.get("ui_config", {}).get("order", 100)
    )
    return [_public_workflow(data) for data in ordered]


def get_workflow(workflow_id: str) -> dict[str, Any]:
    workflow = load_workflows().get(workflow_id)
    if workflow is None:
        raise AppError(404, "WORKFLOW_NOT_FOUND", "Workflow not found")
    return workflow


def workflow_snapshot(workflow: dict[str, Any]) -> dict[str, Any]:
    return deepcopy(workflow)


def workflow_schema_hash(workflow: dict[str, Any]) -> str:
    canonical = json.dumps(workflow, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_workflow_config(workflow: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    normalized = _validate_value(config, workflow.get("config_schema", {}), "config", errors)
    if isinstance(normalized, dict):
        _validate_semantics(workflow, normalized, errors)
    if errors:
        raise AppError(
            422,
            "INVALID_WORKFLOW_CONFIG",
            "Workflow configuration is invalid",
            {"errors": errors},
        )
    return normalized if isinstance(normalized, dict) else {}


def _public_workflow(data: dict[str, Any]) -> WorkflowOut:
    return WorkflowOut(
        id=data["id"],
        name=data["name"],
        description=data["description"],
        version=data["version"],
        domain=data["domain"],
        task_type=data["task_type"],
        result_type=data["result_type"],
        config_schema=data.get("config_schema", {}),
        output_schema=data.get("output_schema", {}),
        ui_schema=data.get("ui_schema", {}),
        ui_config=data.get("ui_config", {}),
    )


def _validate_definition(data: Any, path: Path) -> None:
    if not isinstance(data, dict):
        raise RuntimeError(f"Workflow definition {path} must be an object")
    required = {
        "id",
        "name",
        "description",
        "version",
        "domain",
        "task_type",
        "result_type",
        "config_schema",
        "output_schema",
        "steps",
    }
    missing = sorted(required - data.keys())
    if missing:
        raise RuntimeError(f"Workflow definition {path} is missing: {', '.join(missing)}")
    if path.stem != data["id"]:
        raise RuntimeError(f"Workflow id in {path} must match its filename")
    if not isinstance(data["steps"], list) or not data["steps"]:
        raise RuntimeError(f"Workflow definition {path} must contain at least one step")


def _validate_value(value: Any, schema: dict[str, Any], path: str, errors: list[str]) -> Any:
    expected = schema.get("type")
    if expected == "object":
        if not isinstance(value, dict):
            errors.append(f"{path} must be an object")
            return value
        properties = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}.{key} is required")
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in properties:
                    errors.append(f"{path}.{key} is not supported")
        return {
            key: _validate_value(item, properties.get(key, {}), f"{path}.{key}", errors)
            for key, item in value.items()
            if key in properties or schema.get("additionalProperties", True)
        }
    if expected == "array":
        if not isinstance(value, list):
            errors.append(f"{path} must be an array")
            return value
        _check_size(value, schema, path, errors)
        normalized = [
            _validate_value(item, schema.get("items", {}), f"{path}[{index}]", errors)
            for index, item in enumerate(value)
        ]
        if schema.get("uniqueItems") and len(
            {json.dumps(item, sort_keys=True) for item in normalized}
        ) != len(normalized):
            errors.append(f"{path} must not contain duplicate values")
        return normalized
    if expected == "string":
        if not isinstance(value, str):
            errors.append(f"{path} must be a string")
            return value
        normalized = value.strip()
        _check_size(normalized, schema, path, errors)
        if "enum" in schema and normalized not in schema["enum"]:
            errors.append(f"{path} must be one of: {', '.join(schema['enum'])}")
        return normalized
    if expected == "boolean":
        if not isinstance(value, bool):
            errors.append(f"{path} must be a boolean")
        return value
    if expected == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            errors.append(f"{path} must be a number")
        return value
    return value


def _check_size(value: Any, schema: dict[str, Any], path: str, errors: list[str]) -> None:
    minimum = schema.get("minLength", schema.get("minItems"))
    maximum = schema.get("maxLength", schema.get("maxItems"))
    if minimum is not None and len(value) < minimum:
        errors.append(f"{path} must contain at least {minimum} item(s) or character(s)")
    if maximum is not None and len(value) > maximum:
        errors.append(f"{path} must contain at most {maximum} item(s) or character(s)")


def _validate_semantics(
    workflow: dict[str, Any], config: dict[str, Any], errors: list[str]
) -> None:
    if workflow.get("result_type") != "records":
        return
    fields = config.get("fields", [])
    keys = [field.get("key") for field in fields if isinstance(field, dict)]
    duplicate_keys = sorted({key for key in keys if key and keys.count(key) > 1})
    if duplicate_keys:
        errors.append(f"config.fields contains duplicate keys: {', '.join(duplicate_keys)}")
    for index, key in enumerate(keys):
        if isinstance(key, str) and not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", key):
            errors.append(
                f"config.fields[{index}].key must start with a letter and contain only letters, numbers, or underscores"
            )
