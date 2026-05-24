from app.services.llm_gateway import LLMGateway


def test_openai_compatible_url_appends_chat_completions(monkeypatch):
    monkeypatch.setattr("app.services.llm_gateway.settings.llm_compat_base_url", "https://api.example.com/v1")

    assert LLMGateway()._chat_completions_url() == "https://api.example.com/v1/chat/completions"


def test_openai_compatible_url_accepts_full_chat_completions_path(monkeypatch):
    monkeypatch.setattr(
        "app.services.llm_gateway.settings.llm_compat_base_url",
        "https://api.example.com/v1/chat/completions",
    )

    assert LLMGateway()._chat_completions_url() == "https://api.example.com/v1/chat/completions"
