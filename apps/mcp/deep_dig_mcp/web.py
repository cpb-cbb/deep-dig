from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import Annotated

import uvicorn
from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from deep_dig_mcp.errors import DeepDigMcpError
from deep_dig_mcp.service import DeepDigService
from deep_dig_mcp.settings import Settings


PACKAGE_DIR = Path(__file__).parent


class ExtractionRequest(BaseModel):
    document_id: str
    properties: list[str] = Field(min_length=1, max_length=100)
    allow_low_quality: bool = False


def create_app(service: DeepDigService | None = None) -> FastAPI:
    runtime = service or DeepDigService()
    app = FastAPI(title="Deep Dig Local", version="0.1.0")
    templates = Jinja2Templates(directory=PACKAGE_DIR / "templates")
    app.mount("/static", StaticFiles(directory=PACKAGE_DIR / "static"), name="static")

    @app.exception_handler(DeepDigMcpError)
    async def handle_deep_dig_error(_request: Request, exc: DeepDigMcpError) -> JSONResponse:
        return JSONResponse(
            status_code=_status_for_error(exc.code), content={"ok": False, "error": exc.as_dict()}
        )

    @app.get("/", include_in_schema=False)
    async def index(request: Request):
        return templates.TemplateResponse(request=request, name="index.html")

    @app.get("/health")
    async def health() -> dict:
        info = runtime.parser_info()
        return {"ok": True, "parser": info.model_dump(mode="json", by_alias=True)}

    @app.post("/api/documents/parse")
    async def parse_uploaded_document(
        document: Annotated[UploadFile, File(description="A local digital PDF")],
    ) -> dict:
        original_name = Path(document.filename or "document.pdf").name
        runtime.settings.upload_dir.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        total = 0
        try:
            with tempfile.NamedTemporaryFile(
                "wb",
                suffix=Path(original_name).suffix,
                dir=runtime.settings.upload_dir,
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
                while chunk := await document.read(1024 * 1024):
                    total += len(chunk)
                    if total > runtime.settings.max_file_bytes:
                        raise DeepDigMcpError(
                            "FILE_TOO_LARGE",
                            f"Document exceeds the {runtime.settings.max_file_bytes}-byte local limit",
                        )
                    temporary.write(chunk)
            result = await asyncio.to_thread(
                runtime.parse_document,
                temporary_path,
                allowed_roots=[runtime.settings.upload_dir],
                display_name=original_name,
            )
            return {"ok": True, "document": result.model_dump(mode="json", by_alias=True)}
        finally:
            await document.close()
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    @app.post("/api/extractions")
    async def submit_extraction(payload: ExtractionRequest) -> dict:
        result = await runtime.submit_material_extraction(
            payload.document_id,
            payload.properties,
            allow_low_quality=payload.allow_low_quality,
        )
        return {"ok": True, "submission": result.model_dump(mode="json", by_alias=True)}

    @app.get("/api/extractions/{job_id}")
    async def get_extraction(job_id: str) -> dict:
        result = await runtime.get_extraction(job_id)
        return {"ok": True, "extraction": result.model_dump(mode="json", by_alias=True)}

    @app.post("/api/extractions/{job_id}/export")
    async def export_extraction(job_id: str) -> FileResponse:
        output_path = await runtime.export_extraction_xlsx(job_id)
        return FileResponse(
            output_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=Path(output_path).name,
        )

    return app


def _status_for_error(code: str) -> int:
    if code in {"DOCUMENT_NOT_FOUND", "DOCUMENT_NOT_CACHED", "INPUT_ROOT_NOT_FOUND"}:
        return 404
    if code in {"BACKEND_UNREACHABLE"}:
        return 502
    if code in {"API_TOKEN_REQUIRED"}:
        return 503
    return 400


def main() -> None:
    settings = Settings()
    uvicorn.run(
        create_app(DeepDigService(settings)),
        host=settings.web_host,
        port=settings.web_port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
