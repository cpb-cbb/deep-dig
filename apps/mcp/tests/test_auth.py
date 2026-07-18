from __future__ import annotations

import pytest

from conftest import FakeBackend
from deep_dig_mcp.auth import BackendTokenVerifier
from deep_dig_mcp.errors import BackendApiError
from deep_dig_mcp.settings import Settings


@pytest.mark.asyncio
async def test_token_verifier_preserves_backend_user_identity(
    runtime_settings: Settings,
) -> None:
    verifier = BackendTokenVerifier(runtime_settings, client_factory=lambda _token: FakeBackend())
    access = await verifier.verify_token("user-token")
    assert access is not None
    assert access.token == "user-token"
    assert access.subject == "00000000-0000-0000-0000-000000000001"


@pytest.mark.asyncio
async def test_token_verifier_rejects_backend_auth_failure(runtime_settings: Settings) -> None:
    class RejectingBackend:
        async def get_me(self) -> dict:
            raise BackendApiError("AUTH_INVALID", "Invalid token")

    verifier = BackendTokenVerifier(
        runtime_settings, client_factory=lambda _token: RejectingBackend()
    )
    assert await verifier.verify_token("invalid-token") is None
