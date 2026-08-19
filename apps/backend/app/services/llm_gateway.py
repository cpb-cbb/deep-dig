from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.config import settings
from app.errors import AppError
from app.services.llm_config import ResolvedLLMConfig, environment_llm_config


@dataclass(frozen=True)
class LLMResult:
    text: str
    raw: dict[str, Any]
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0


class LLMGateway:
    def __init__(self) -> None:
        self.timeout = httpx.Timeout(120.0)

    async def call(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        config: ResolvedLLMConfig | None = None,
        **kwargs: Any,
    ) -> LLMResult:
        active = config or environment_llm_config()
        if active.provider == "fake":
            return self._call_fake(system_prompt, user_prompt)
        if not active.api_key:
            raise AppError(503, "LLM_NOT_CONFIGURED", "No LLM provider key configured")
        selected_model = model or active.model
        if active.provider == "openai_compatible":
            return await self._call_openai_compatible(
                active, system_prompt, user_prompt, selected_model, **kwargs
            )
        if active.provider == "openrouter":
            return await self._call_openrouter(
                active, system_prompt, user_prompt, selected_model, **kwargs
            )
        if active.provider == "anthropic":
            return await self._call_anthropic(
                active, system_prompt, user_prompt, selected_model, **kwargs
            )
        raise AppError(503, "LLM_NOT_CONFIGURED", "No LLM provider key configured")

    def _call_fake(self, system_prompt: str, user_prompt: str) -> LLMResult:
        if '"records"' in user_prompt and "Field definitions" in user_prompt:
            text = '{"records": [], "warnings": ["Fake provider returned no records"]}'
        elif '"entities"' in user_prompt and "Allowed entity types" in user_prompt:
            text = '{"entities": [], "relations": [], "warnings": ["Fake provider returned no entities"]}'
        elif '"samples"' in user_prompt and "Requested properties" in user_prompt:
            text = '{"samples": []}'
        elif "isExperimental" in system_prompt:
            text = '{"isExperimental": true, "sampleNames": ["Demo Sample"], "reason": "Fake development response"}'
        elif "JSON" in system_prompt or "JSON" in user_prompt:
            text = '{"investigated_systems": [{"system_name": "Demo Sample", "properties": [{"name": "Yield Strength", "value": "500", "unit": "MPa", "remark": "fake", "source": "Table 1", "method": "tensile test"}]}]}'
        else:
            text = "# SAMPLE: Demo Sample\n- Yield Strength | 500 | MPa | fake development response | Table 1 | tensile test"
        return LLMResult(
            text=text,
            raw={"provider": "fake"},
            tokens_in=len(user_prompt.split()),
            tokens_out=len(text.split()),
            cost_usd=0.0,
        )

    def _chat_completions_url(self, base_url: str | None = None) -> str:
        base_url = (base_url or settings.llm_compat_base_url).rstrip("/")
        if base_url.endswith("/chat/completions"):
            return base_url
        return f"{base_url}/chat/completions"

    async def _call_openai_compatible(
        self,
        config: ResolvedLLMConfig,
        system_prompt: str,
        user_prompt: str,
        model: str,
        **kwargs: Any,
    ) -> LLMResult:
        payload = {
            "model": kwargs.get("model") or model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": kwargs.get("temperature", config.temperature),
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                self._chat_completions_url(config.base_url),
                headers={"Authorization": f"Bearer {config.api_key}"},
                json=payload,
            )
            if response.status_code == 429:
                raise AppError(429, "LLM_RATE_LIMITED", "LLM provider rate limited the request")
            response.raise_for_status()
            data = response.json()
        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return LLMResult(
            text=text,
            raw=data,
            tokens_in=usage.get("prompt_tokens", 0),
            tokens_out=usage.get("completion_tokens", 0),
        )

    async def _call_openrouter(
        self,
        config: ResolvedLLMConfig,
        system_prompt: str,
        user_prompt: str,
        model: str,
        **kwargs: Any,
    ) -> LLMResult:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": kwargs.get("temperature", config.temperature),
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                self._chat_completions_url(config.base_url),
                headers={"Authorization": f"Bearer {config.api_key}"},
                json=payload,
            )
            if response.status_code == 429:
                raise AppError(429, "LLM_RATE_LIMITED", "LLM provider rate limited the request")
            response.raise_for_status()
            data = response.json()
        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return LLMResult(
            text=text,
            raw=data,
            tokens_in=usage.get("prompt_tokens", 0),
            tokens_out=usage.get("completion_tokens", 0),
        )

    async def _call_anthropic(
        self,
        config: ResolvedLLMConfig,
        system_prompt: str,
        user_prompt: str,
        model: str,
        **kwargs: Any,
    ) -> LLMResult:
        base_url = config.base_url.rstrip("/")
        messages_url = base_url if base_url.endswith("/messages") else f"{base_url}/messages"
        payload = {
            "model": kwargs.get("anthropic_model") or model,
            "max_tokens": kwargs.get("max_tokens", 4096),
            "temperature": kwargs.get("temperature", config.temperature),
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                messages_url,
                headers={
                    "x-api-key": config.api_key,
                    "anthropic-version": "2023-06-01",
                },
                json=payload,
            )
            if response.status_code == 429:
                raise AppError(429, "LLM_RATE_LIMITED", "LLM provider rate limited the request")
            response.raise_for_status()
            data = response.json()
        text = "".join(block.get("text", "") for block in data.get("content", []))
        usage = data.get("usage", {})
        return LLMResult(
            text=text,
            raw=data,
            tokens_in=usage.get("input_tokens", 0),
            tokens_out=usage.get("output_tokens", 0),
        )


llm_gateway = LLMGateway()
