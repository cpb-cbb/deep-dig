from fastapi import APIRouter, Depends, File, UploadFile

from app.auth.jwt import AuthUser, verify_auth
from app.config import settings
from app.errors import AppError
from app.schemas import ParsedFileOut
from app.services.pdf_parser import parse_pdf_bytes

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/parse", response_model=list[ParsedFileOut])
def parse_files(
    files: list[UploadFile] = File(...),
    auth: AuthUser = Depends(verify_auth),
) -> list[dict[str, object]]:
    if len(files) > settings.free_batch_limit:
        raise AppError(400, "BATCH_LIMIT_EXCEEDED", "Too many files in a single request")
    results: list[dict[str, object]] = []
    for upload in files:
        if not upload.filename or not upload.filename.lower().endswith(".pdf"):
            raise AppError(400, "NOT_PDF", f"Only .pdf files are supported: {upload.filename}")
        data = upload.file.read()
        if len(data) > settings.upload_max_bytes:
            raise AppError(
                413, "PAYLOAD_TOO_LARGE", f"File exceeds the maximum upload size: {upload.filename}"
            )
        results.append(parse_pdf_bytes(data, upload.filename))
    return results
