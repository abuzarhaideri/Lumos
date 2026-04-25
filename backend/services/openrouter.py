"""
OpenRouter LLM service.

Uses the openai-compatible API exposed by OpenRouter so every agent can
pick its own model string without any per-vendor SDK.

Environment variable required: OPENROUTER_API_KEY
Optional:  OPENROUTER_BASE_URL  (defaults to https://openrouter.ai/api/v1)
"""

import os
from typing import Optional

from openai import OpenAI

# ── model constants assigned per agent ──────────────────────────────────────
# Agent 1a — RAG Chunker
MODEL_CHUNKER = "meta-llama/llama-3.3-70b-instruct:free"
# Agent 1b — Learner Profiler
MODEL_PROFILER = "meta-llama/llama-3.3-70b-instruct:free"
# Agent 2 — Adaptive Architect
MODEL_ARCHITECT = "nousresearch/hermes-3-llama-3.1-405b:free"
# Agent 3 — Content Writer
MODEL_CONTENT = "nousresearch/hermes-3-llama-3.1-405b:free"
MODEL_CONTENT_FALLBACK = "meta-llama/llama-3.3-70b-instruct:free"
# Agent 4 — Blind Student (smaller, deliberately less capable)
MODEL_STUDENT = "google/gemma-3-12b-it:free"
# Agent 5 — Validator (shared with Architect; runs at a different pipeline step)
MODEL_VALIDATOR = "nousresearch/hermes-3-llama-3.1-405b:free"


def _client() -> OpenAI:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. "
            "Add it to backend/.env or your environment."
        )
    base_url = os.getenv(
        "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
    )
    return OpenAI(api_key=api_key, base_url=base_url)


FREE_FALLBACK_QUEUE = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "google/gemma-3-27b-it:free",
    "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "openai/gpt-oss-120b:free"
]

def generate_text(
    *,
    model: str,
    user_text: str,
    system_text: Optional[str] = None,
    max_tokens: int = 4096,
    temperature: float = 0.4,
    fallback_model: Optional[str] = None,
) -> str:
    """
    Call OpenRouter with the given model and return the text response.

    If the primary model fails, it automatically falls back through a queue of 
    known free models to guarantee a response even if providers are rate-limited.
    """
    client = _client()
    messages = []
    if system_text:
        messages.append({"role": "system", "content": system_text})
    messages.append({"role": "user", "content": user_text})

    def _call(m: str) -> str:
        response = client.chat.completions.create(
            model=m,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return (response.choices[0].message.content or "").strip()

    # Build the queue of models to try
    models_to_try = [model]
    if fallback_model and fallback_model not in models_to_try:
        models_to_try.append(fallback_model)
    for fm in FREE_FALLBACK_QUEUE:
        if fm not in models_to_try:
            models_to_try.append(fm)

    last_error = None
    for current_model in models_to_try:
        try:
            print(f"Attempting inference with model: {current_model}")
            return _call(current_model)
        except Exception as exc:
            print(f"Model {current_model} failed: {exc}. Trying next...")
            last_error = exc

    raise RuntimeError(f"All models in fallback queue failed. Last error: {last_error}")
