from fastapi import APIRouter

from app.schemas import WorkflowOut
from app.services.workflow_registry import get_workflow, list_public_workflows

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.get("", response_model=list[WorkflowOut])
async def list_workflows() -> list[WorkflowOut]:
    return list_public_workflows()


@router.get("/{workflow_id}", response_model=WorkflowOut)
async def workflow_detail(workflow_id: str) -> WorkflowOut:
    data = get_workflow(workflow_id)
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
