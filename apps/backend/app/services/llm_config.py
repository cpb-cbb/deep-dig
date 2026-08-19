from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.errors import AppError
from app.models import UserSettings
from app.schemas import LLMSettingsOut, LLMSettingsPatch

LLMProvider = Literal["auto", "openrouter", "anthropic", "openai_compatible", "fake"]


@dataclass(frozen=True)
class ResolvedLLMConfig:
    provider: LLMProvider
    base_url: str
    api_key: str
    model: str
    temperature: float
    source: Literal["environment", "custom"]


def _environment_key(value: str) -> str:
    cleaned = value.strip()
    return "" if cleaned.lower() in {"replace-me", "change-me", "your-api-key"} else cleaned


def _fernet() -> Fernet:
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.auth_secret.encode()).digest())
    return Fernet(key)


def encrypt_api_key(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt_api_key(value: str | None) -> str:
    if not value:
        return ""
    try:
        return _fernet().decrypt(value.encode()).decode()
    except InvalidToken as exc:
        raise AppError(
            500,
            "LLM_SETTINGS_DECRYPT_FAILED",
            "Stored API key cannot be decrypted; save the provider settings again",
        ) from exc


def environment_llm_config(provider: LLMProvider | None = None) -> ResolvedLLMConfig:
    selected = provider or settings.llm_provider
    compat_key = _environment_key(settings.llm_compat_api_key)
    openrouter_key = _environment_key(settings.llm_openrouter_key)
    anthropic_key = _environment_key(settings.llm_anthropic_key)
    if selected == "auto":
        if compat_key:
            selected = "openai_compatible"
        elif openrouter_key:
            selected = "openrouter"
        elif anthropic_key:
            selected = "anthropic"
        else:
            return ResolvedLLMConfig(
                provider="auto",
                base_url="",
                api_key="",
                model="",
                temperature=settings.llm_temperature,
                source="environment",
            )

    if selected == "openai_compatible":
        return ResolvedLLMConfig(
            provider=selected,
            base_url=settings.llm_compat_base_url,
            api_key=compat_key,
            model=settings.llm_compat_model,
            temperature=settings.llm_temperature,
            source="environment",
        )
    if selected == "openrouter":
        return ResolvedLLMConfig(
            provider=selected,
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_key,
            model=settings.llm_openrouter_model,
            temperature=settings.llm_temperature,
            source="environment",
        )
    if selected == "anthropic":
        return ResolvedLLMConfig(
            provider=selected,
            base_url="https://api.anthropic.com/v1",
            api_key=anthropic_key,
            model=settings.llm_anthropic_model,
            temperature=settings.llm_temperature,
            source="environment",
        )
    return ResolvedLLMConfig(
        provider="fake",
        base_url="",
        api_key="",
        model="fake",
        temperature=settings.llm_temperature,
        source="environment",
    )


def resolve_llm_config(user_settings: UserSettings | None) -> ResolvedLLMConfig:
    if user_settings is None or user_settings.llm_provider is None:
        return environment_llm_config()

    provider = user_settings.llm_provider
    if provider not in {"auto", "openrouter", "anthropic", "openai_compatible", "fake"}:
        raise AppError(500, "LLM_SETTINGS_INVALID", "Stored LLM provider is invalid")
    base = environment_llm_config(provider)
    return ResolvedLLMConfig(
        provider=provider,
        base_url=user_settings.llm_base_url or base.base_url,
        api_key=decrypt_api_key(user_settings.llm_api_key_encrypted) or base.api_key,
        model=user_settings.llm_model or base.model,
        temperature=(
            user_settings.llm_temperature
            if user_settings.llm_temperature is not None
            else base.temperature
        ),
        source="custom",
    )


async def get_user_llm_config(db: AsyncSession, user_id: UUID) -> ResolvedLLMConfig:
    value = await db.scalar(select(UserSettings).where(UserSettings.user_id == user_id))
    return resolve_llm_config(value)


def llm_settings_out(config: ResolvedLLMConfig) -> LLMSettingsOut:
    return LLMSettingsOut(
        source=config.source,
        provider=config.provider,
        base_url=config.base_url,
        model=config.model,
        temperature=config.temperature,
        api_key_configured=bool(config.api_key),
    )


def llm_settings_view(user_settings: UserSettings | None) -> LLMSettingsOut:
    if user_settings is None or user_settings.llm_provider is None:
        return llm_settings_out(environment_llm_config())
    provider = user_settings.llm_provider
    if provider not in {"openrouter", "anthropic", "openai_compatible", "fake"}:
        raise AppError(500, "LLM_SETTINGS_INVALID", "Stored LLM provider is invalid")
    base = environment_llm_config(provider)
    return LLMSettingsOut(
        source="custom",
        provider=provider,
        base_url=user_settings.llm_base_url or base.base_url,
        model=user_settings.llm_model or base.model,
        temperature=(
            user_settings.llm_temperature
            if user_settings.llm_temperature is not None
            else base.temperature
        ),
        api_key_configured=bool(user_settings.llm_api_key_encrypted or base.api_key),
    )


def apply_llm_settings(user_settings: UserSettings, payload: LLMSettingsPatch) -> None:
    if payload.mode == "environment":
        user_settings.llm_provider = None
        user_settings.llm_base_url = None
        user_settings.llm_model = None
        user_settings.llm_api_key_encrypted = None
        user_settings.llm_temperature = None
        return

    if payload.provider is None:
        raise AppError(422, "LLM_PROVIDER_REQUIRED", "Choose a provider for custom settings")
    base_url = (payload.base_url or "").strip()
    if payload.provider == "openai_compatible" and not base_url:
        raise AppError(422, "LLM_BASE_URL_REQUIRED", "Base URL is required")
    if base_url and not base_url.startswith(("http://", "https://")):
        raise AppError(
            422,
            "LLM_BASE_URL_INVALID",
            "Base URL must start with http:// or https://",
        )

    user_settings.llm_provider = payload.provider
    user_settings.llm_base_url = (payload.base_url or "").strip() or None
    user_settings.llm_model = (payload.model or "").strip() or None
    user_settings.llm_temperature = payload.temperature
    if payload.clear_api_key:
        user_settings.llm_api_key_encrypted = None
    if payload.api_key and payload.api_key.strip():
        user_settings.llm_api_key_encrypted = encrypt_api_key(payload.api_key.strip())
