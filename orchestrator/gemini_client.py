import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from google import genai


@dataclass
class GeminiConfig:
    api_key: str
    primary_model: str
    fallback_model: str | None


@dataclass
class GeminiResult:
    text: str
    model_used: str
    fallback_used: bool


def load_gemini_config(project_root: Path) -> GeminiConfig:
    load_dotenv(project_root / ".env")

    api_key = os.getenv("GEMINI_API_KEY")
    primary_model = os.getenv("GEMINI_MODEL")
    fallback_model = os.getenv("GEMINI_FALLBACK_MODEL") or None

    if not api_key or not primary_model:
        raise ValueError("Missing GEMINI_API_KEY or GEMINI_MODEL in .env.")

    return GeminiConfig(
        api_key=api_key,
        primary_model=primary_model,
        fallback_model=fallback_model,
    )


def _call_model(api_key: str, model: str, prompt: str) -> str:
    with genai.Client(
        api_key=api_key,
        http_options={"timeout": 60000},
    ) as client:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
        )

    if not response.text:
        raise ValueError(f"Model '{model}' returned no text.")

    return response.text


def generate_with_fallback(config: GeminiConfig, prompt: str) -> GeminiResult:
    """
    Call the primary Gemini model. If it raises any exception and a
    fallback model is configured (GEMINI_FALLBACK_MODEL in .env),
    retry once with the fallback model before giving up.

    This is a genuine fallback -- switching to a different resource --
    which is distinct from a bounded retry (repeating the same call
    against the same model). Bounded retries already exist for test
    execution in executor.py; this covers AI-stage availability.
    """
    try:
        text = _call_model(config.api_key, config.primary_model, prompt)
        return GeminiResult(
            text=text,
            model_used=config.primary_model,
            fallback_used=False,
        )
    except Exception as primary_error:
        if not config.fallback_model:
            raise

        try:
            text = _call_model(
                config.api_key, config.fallback_model, prompt
            )
            return GeminiResult(
                text=text,
                model_used=config.fallback_model,
                fallback_used=True,
            )
        except Exception as fallback_error:
            raise RuntimeError(
                f"Primary model '{config.primary_model}' failed "
                f"({type(primary_error).__name__}: {primary_error}); "
                f"fallback model '{config.fallback_model}' also failed "
                f"({type(fallback_error).__name__}: {fallback_error})"
            ) from fallback_error