import os
import builtins
import types
import pytest
from unittest import mock
import sys

# Ensure the GEMINI_API_KEY env var is controlled per test

def test_gemini_provider_missing_key(monkeypatch):
    # Ensure env var is not set
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    from ai.provider import GeminiProvider
    provider = GeminiProvider()
    assert provider.health_check() is False
    with pytest.raises(RuntimeError) as exc:
        provider.generate_response([{"role": "user", "content": "test"}])
    assert "Gemini client is not initialized" in str(exc.value)

def test_gemini_provider_success(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-key")
    mock_client = mock.Mock()
    mock_models = mock.Mock()
    mock_response = types.SimpleNamespace(
        text="Hello from Gemini",
        function_calls=[],
        candidates=[types.SimpleNamespace(content=types.SimpleNamespace(parts=[]))]
    )
    mock_models.generate_content.return_value = mock_response
    mock_client.models = mock_models

    mock_genai_module = types.SimpleNamespace(
        Client=mock.Mock(return_value=mock_client)
    )
    monkeypatch.setitem(sys.modules, "google.genai", mock_genai_module)

    from ai.provider import GeminiProvider
    provider = GeminiProvider()
    assert provider.health_check() is True
    resp = provider.generate_response([{"role": "user", "content": "Hello"}])
    assert resp["content"] == "Hello from Gemini"
    assert resp["tool_calls"] == []
    assert resp["role"] == "assistant"

def test_gemini_provider_quota_error(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-key")
    mock_client = mock.Mock()
    mock_models = mock.Mock()
    mock_models.generate_content.side_effect = Exception("Quota limits exceeded")
    mock_client.models = mock_models

    mock_genai_module = types.SimpleNamespace(
        Client=mock.Mock(return_value=mock_client)
    )
    monkeypatch.setitem(sys.modules, "google.genai", mock_genai_module)

    from ai.provider import GeminiProvider
    provider = GeminiProvider()
    with pytest.raises(RuntimeError) as exc:
        provider.generate_response([{"role": "user", "content": "test"}])
    assert "quota limits" in str(exc.value).lower()
