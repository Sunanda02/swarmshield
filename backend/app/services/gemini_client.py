"""
Thin wrapper around the Google Gemini API. Every agent calls `generate()`
with a system instruction + user content and gets back text (optionally
parsed as JSON when `as_json=True`).

Centralizing this here means swapping models/providers later only touches
one file.
"""
import json
from typing import Any, Optional

from google import genai
from google.genai import types

from app.core.config import settings

_client: Optional[genai.Client] = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


def generate(
    system_instruction: str,
    user_content: str,
    as_json: bool = False,
    temperature: float = 0.7,
) -> Any:
    """
    Call Gemini with a system instruction + user turn.

    Returns raw string, or a parsed dict/list if `as_json=True` (the caller
    is responsible for prompting the model to actually return JSON).
    """
    client = _get_client()

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=temperature,
        response_mime_type="application/json" if as_json else "text/plain",
    )

    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=user_content,
        config=config,
    )

    text = response.text or ""

    if as_json:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Model occasionally wraps JSON in markdown fences despite instructions
            cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            return json.loads(cleaned)

    return text
