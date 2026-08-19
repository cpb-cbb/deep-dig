from uuid import uuid4

from app.models import UserSettings
from app.schemas import LLMSettingsPatch
from app.services.llm_config import (
    apply_llm_settings,
    environment_llm_config,
    llm_settings_out,
    resolve_llm_config,
)


def test_custom_llm_settings_encrypt_key_and_resolve_runtime_config(monkeypatch):
    monkeypatch.setattr("app.services.llm_config.settings.auth_secret", "test-secret")
    monkeypatch.setattr("app.services.llm_config.settings.llm_compat_api_key", "")
    values = UserSettings(user_id=uuid4())

    apply_llm_settings(
        values,
        LLMSettingsPatch(
            mode="custom",
            provider="openai_compatible",
            base_url="https://llm.example/v1",
            model="example-model",
            temperature=0.35,
            api_key="secret-provider-key",
        ),
    )

    assert values.llm_api_key_encrypted
    assert "secret-provider-key" not in values.llm_api_key_encrypted
    resolved = resolve_llm_config(values)
    assert resolved.source == "custom"
    assert resolved.base_url == "https://llm.example/v1"
    assert resolved.model == "example-model"
    assert resolved.temperature == 0.35
    assert resolved.api_key == "secret-provider-key"
    assert llm_settings_out(resolved).api_key_configured is True
    assert "api_key" not in llm_settings_out(resolved).model_dump()


def test_environment_mode_clears_all_database_overrides(monkeypatch):
    monkeypatch.setattr("app.services.llm_config.settings.llm_provider", "fake")
    values = UserSettings(
        user_id=uuid4(),
        llm_provider="openrouter",
        llm_base_url="https://custom.example/v1",
        llm_model="custom-model",
        llm_api_key_encrypted="encrypted-value",
        llm_temperature=0.7,
    )

    apply_llm_settings(values, LLMSettingsPatch(mode="environment"))

    assert values.llm_provider is None
    assert values.llm_api_key_encrypted is None
    assert resolve_llm_config(values) == environment_llm_config()
