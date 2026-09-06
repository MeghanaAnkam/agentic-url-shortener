import pytest

import orchestrator.gemini_client as gemini_client
from orchestrator.gemini_client import (
    GeminiConfig,
    generate_with_fallback,
    load_gemini_config,
)


class FakeResponse:
    def __init__(self, text):
        self.text = text


class FakeModels:
    def __init__(self, behavior):
        # behavior: dict mapping model name -> str (success) or
        # Exception instance (failure)
        self.behavior = behavior
        self.calls = []

    def generate_content(self, model, contents):
        self.calls.append(model)
        outcome = self.behavior[model]

        if isinstance(outcome, Exception):
            raise outcome

        return FakeResponse(outcome)


class FakeClient:
    def __init__(self, behavior):
        self.models = FakeModels(behavior)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


def make_fake_genai_client(behavior, calls_log):
    def factory(api_key, http_options):
        client = FakeClient(behavior)
        client.models.calls = calls_log
        return client

    return factory


def patch_genai(monkeypatch, behavior):
    calls_log = []
    monkeypatch.setattr(
        gemini_client.genai,
        "Client",
        make_fake_genai_client(behavior, calls_log),
    )
    return calls_log


def test_primary_success_does_not_use_fallback(monkeypatch):
    calls = patch_genai(monkeypatch, {"primary-model": "PRIMARY OK"})

    config = GeminiConfig(
        api_key="fake-key",
        primary_model="primary-model",
        fallback_model="fallback-model",
    )

    result = generate_with_fallback(config, "some prompt")

    assert result.text == "PRIMARY OK"
    assert result.model_used == "primary-model"
    assert result.fallback_used is False
    assert calls == ["primary-model"]


def test_fallback_used_when_primary_fails(monkeypatch):
    calls = patch_genai(
        monkeypatch,
        {
            "primary-model": TimeoutError("primary timed out"),
            "fallback-model": "FALLBACK OK",
        },
    )

    config = GeminiConfig(
        api_key="fake-key",
        primary_model="primary-model",
        fallback_model="fallback-model",
    )

    result = generate_with_fallback(config, "some prompt")

    assert result.text == "FALLBACK OK"
    assert result.model_used == "fallback-model"
    assert result.fallback_used is True
    assert calls == ["primary-model", "fallback-model"]


def test_raises_when_primary_fails_and_no_fallback_configured(monkeypatch):
    patch_genai(
        monkeypatch,
        {"primary-model": TimeoutError("primary timed out")},
    )

    config = GeminiConfig(
        api_key="fake-key",
        primary_model="primary-model",
        fallback_model=None,
    )

    with pytest.raises(TimeoutError, match="primary timed out"):
        generate_with_fallback(config, "some prompt")


def test_raises_combined_error_when_both_models_fail(monkeypatch):
    patch_genai(
        monkeypatch,
        {
            "primary-model": TimeoutError("primary timed out"),
            "fallback-model": ValueError("fallback also broke"),
        },
    )

    config = GeminiConfig(
        api_key="fake-key",
        primary_model="primary-model",
        fallback_model="fallback-model",
    )

    with pytest.raises(RuntimeError, match="fallback also broke"):
        generate_with_fallback(config, "some prompt")


def test_load_gemini_config_requires_api_key_and_model(
    tmp_path, monkeypatch
):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.delenv("GEMINI_FALLBACK_MODEL", raising=False)

    with pytest.raises(ValueError, match="Missing GEMINI_API_KEY"):
        load_gemini_config(tmp_path)


def test_load_gemini_config_fallback_is_optional(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("GEMINI_MODEL", "primary-model")
    monkeypatch.delenv("GEMINI_FALLBACK_MODEL", raising=False)

    config = load_gemini_config(tmp_path)

    assert config.api_key == "fake-key"
    assert config.primary_model == "primary-model"
    assert config.fallback_model is None