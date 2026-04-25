import os
from typing import Optional

from google import genai
from google.genai import types


def _client() -> genai.Client:
    # Prefer env var (never hardcode keys).
    # Google SDK reads GEMINI_API_KEY/GOOGLE_API_KEY automatically if api_key not passed.
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    return genai.Client(api_key=api_key) if api_key else genai.Client()


def gemini_generate_text(
    *,
    model: str,
    user_text: str,
    system_text: Optional[str] = None,
    max_output_tokens: int = 1024,
    temperature: float = 0.4,
) -> str:
    client = _client()
    config = types.GenerateContentConfig(
        system_instruction=system_text,
        max_output_tokens=max_output_tokens,
        temperature=temperature,
    )
    response = client.models.generate_content(model=model, contents=user_text, config=config)
    return (response.text or "").strip()

