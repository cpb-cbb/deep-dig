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
        ui_config=data.get("ui_config", {}),
    )
