from fastapi import HTTPException, Request
from fastapi.responses import ORJSONResponse


class AppError(HTTPException):
    def __init__(self, status_code: int, code: str, message: str, detail: dict | None = None):
        super().__init__(status_code=status_code, detail=detail or {})
        self.code = code
        self.message = message


async def app_error_handler(_: Request, exc: AppError) -> ORJSONResponse:
    retry_after = exc.detail.get("retry_after") if isinstance(exc.detail, dict) else None
    return ORJSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message, "detail": exc.detail},
        headers={"Retry-After": str(retry_after)} if retry_after is not None else None,
    )


async def http_error_handler(_: Request, exc: HTTPException) -> ORJSONResponse:
    detail = exc.detail if isinstance(exc.detail, dict) else {}
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return ORJSONResponse(
        status_code=exc.status_code,
        content={"code": detail.get("code", "HTTP_ERROR"), "message": message, "detail": detail},
    )
