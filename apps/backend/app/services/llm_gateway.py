from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.config import settings
from app.errors import AppError


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

    async def call(self, system_prompt: str, user_prompt: str, model: str = "anthropic/claude-3.5-haiku", **kwargs: Any) -> LLMResult:
        if settings.llm_provider == "fake":
            return self._call_fake(system_prompt, user_prompt)
        if settings.llm_provider in {"auto", "openrouter"} and settings.llm_openrouter_key:
            return await self._call_openrouter(system_prompt, user_prompt, model, **kwargs)
        if settings.llm_provider in {"auto", "anthropic"} and settings.llm_anthropic_key:
            return await self._call_anthropic(system_prompt, user_prompt, model, **kwargs)
        raise AppError(503, "LLM_NOT_CONFIGURED", "No LLM provider key configured")

    def _call_fake(self, system_prompt: str, user_prompt: str) -> LLMResult:
        if "isExperimental" in system_prompt:
            text = '{"isExperimental": true, "sampleNames": ["Demo Sample"], "reason": "Fake development response"}'
        elif "JSON" in system_prompt or "JSON" in user_prompt:
            text = '{"investigated_systems": [{"system_name": "Demo Sample", "properties": [{"name": "Yield Strength", "value": "500", "unit": "MPa", "remark": "fake", "source": "Table 1", "method": "tensile test"}]}]}'
        else:
            text = "# SAMPLE: Demo Sample\n- Yield Strength | 500 | MPa | fake development response | Table 1 | tensile test"
        return LLMResult(text=text, raw={"provider": "fake"}, tokens_in=len(user_prompt.split()), tokens_out=len(text.split()), cost_usd=0.0)

    async def _call_openrouter(self, system_prompt: str, user_prompt: str, model: str, **kwargs: Any) -> LLMResult:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": kwargs.get("temperature", 0),
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.llm_openrouter_key}"},
                json=payload,
            )
            if response.status_code == 429:
                raise AppError(429, "LLM_RATE_LIMITED", "LLM provider rate limited the request")
            response.raise_for_status()
            data = response.json()
        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return LLMResult(text=text, raw=data, tokens_in=usage.get("prompt_tokens", 0), tokens_out=usage.get("completion_tokens", 0))

    async def _call_anthropic(self, system_prompt: str, user_prompt: str, model: str, **kwargs: Any) -> LLMResult:
        anthropic_model = kwargs.get("anthropic_model", "claude-3-5-haiku-latest")
        payload = {
            "model": anthropic_model,
            "max_tokens": kwargs.get("max_tokens", 4096),
            "temperature": kwargs.get("temperature", 0),
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.llm_anthropic_key,
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
        return LLMResult(text=text, raw=data, tokens_in=usage.get("input_tokens", 0), tokens_out=usage.get("output_tokens", 0))


llm_gateway = LLMGateway()
