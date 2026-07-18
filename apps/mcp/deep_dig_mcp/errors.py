from __future__ import annotations

from typing import Any


class DeepDigMcpError(Exception):
    """Expected user-facing error with a stable machine-readable code."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        detail: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail or {}

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "detail": self.detail}


class BackendApiError(DeepDigMcpError):
    pass
