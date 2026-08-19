import pytest

from app.errors import AppError
from app.services.workflow_registry import (
    get_workflow,
    list_public_workflows,
    validate_workflow_config,
    workflow_schema_hash,
    workflow_snapshot,
)


def test_registry_loads_all_builtin_workflows_without_exposing_prompts():
    workflows = list_public_workflows()

    assert {workflow.id for workflow in workflows} == {
        "material_extraction",
        "custom_record_extraction",
        "entity_relation_extraction",
    }
    assert all(workflow.config_schema for workflow in workflows)
    assert all(workflow.output_schema for workflow in workflows)
    assert "steps" not in workflows[0].model_dump()


def test_custom_record_config_is_normalized_and_validated():
    workflow = get_workflow("custom_record_extraction")

    config = validate_workflow_config(
        workflow,
        {
            "fields": [
                {
                    "key": " effective_date ",
                    "label": " Effective date ",
                    "type": "date",
                    "description": " Date the agreement starts ",
                }
            ]
        },
    )

    assert config["fields"][0]["key"] == "effective_date"
    assert config["fields"][0]["label"] == "Effective date"


def test_custom_record_config_rejects_duplicate_or_unsafe_keys():
    workflow = get_workflow("custom_record_extraction")
    field = {
        "key": "not-safe-key",
        "label": "Field",
        "type": "text",
        "description": "Description",
    }

    with pytest.raises(AppError) as raised:
        validate_workflow_config(workflow, {"fields": [field, field]})

    assert raised.value.code == "INVALID_WORKFLOW_CONFIG"


def test_workflow_snapshot_is_detached_and_hash_is_stable():
    workflow = get_workflow("material_extraction")
    snapshot = workflow_snapshot(workflow)
    original_hash = workflow_schema_hash(workflow)

    snapshot["version"] = "changed"

    assert workflow["version"] == "2.0.0"
    assert workflow_schema_hash(workflow) == original_hash
