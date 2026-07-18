from __future__ import annotations

from collections.abc import Callable

from mcp.server.auth.provider import AccessToken

from deep_dig_mcp.backend_client import DeepDigBackendClient
from deep_dig_mcp.errors import BackendApiError
from deep_dig_mcp.settings import Settings


BackendClientFactory = Callable[[str], DeepDigBackendClient]


class BackendTokenVerifier:
    """Validate MCP bearer tokens through the backend account boundary."""

    def __init__(
        self,
        settings: Settings,
        client_factory: BackendClientFactory | None = None,
    ) -> None:
        self.settings = settings
        self.client_factory = client_factory or self._build_client

    async def verify_token(self, token: str) -> AccessToken | None:
        if not token:
            return None
        try:
            user = await self.client_factory(token).get_me()
        except BackendApiError:
            return None
        subject = str(user.get("id") or "")
        if not subject:
            return None
        return AccessToken(
            token=token,
            client_id="deep-dig-mcp-client",
            scopes=["deep-dig"],
            subject=subject,
        )

    def _build_client(self, token: str) -> DeepDigBackendClient:
        return DeepDigBackendClient(
            base_url=self.settings.api_base_url,
            token=token,
            timeout_seconds=self.settings.request_timeout_seconds,
        )
