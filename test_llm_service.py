from llm_service import generate_text, get_llm_model


def test_llm_service_uses_fallback_without_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "")

    assert get_llm_model() is None
    assert generate_text("Say hello", fallback="fallback") == "fallback"
