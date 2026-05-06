"""
Reusable LLM client for DeepSeek (OpenAI-compatible API).

Usage:
    from src.utils.llm_client import chat_completion

    response = chat_completion([
        {"role": "user", "content": "Hello!"}
    ])
"""
from __future__ import annotations

import json
import logging
import os
import re

from openai import OpenAI, APIError, APIConnectionError, RateLimitError

from config.settings import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL, LLM_TEMPERATURE, LLM_MAX_TOKENS

logger = logging.getLogger(__name__)

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = DEEPSEEK_API_KEY or os.environ.get("DEEPSEEK_API_KEY", "")
        if not api_key:
            raise ValueError(
                "DEEPSEEK_API_KEY is not set. "
                "Copy .env.example to .env and fill in your key."
            )
        _client = OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)
    return _client


def chat_completion(
    messages: list[dict],
    temperature: float = LLM_TEMPERATURE,
    max_tokens: int = LLM_MAX_TOKENS,
    model: str | None = None,
    json_mode: bool = False,
) -> str:
    """
    Send a chat completion request to DeepSeek.

    Parameters
    ----------
    messages : list[dict]
        List of {"role": ..., "content": ...} dicts.
    temperature : float
        Sampling temperature (lower = more deterministic).
    max_tokens : int
        Maximum tokens in the completion.
    model : str | None
        Override the default model.
    json_mode : bool
        If True, asks the model to respond in JSON.

    Returns
    -------
    str  The model's text response.
    """
    effective_model = model or DEEPSEEK_MODEL
    client = _get_client()

    kwargs: dict = {
        "model": effective_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    try:
        logger.debug("LLM request: model=%s, messages=%d", effective_model, len(messages))
        response = client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content or ""
        logger.debug("LLM response length: %d chars", len(content))
        return content
    except RateLimitError as exc:
        logger.error("Rate limit hit: %s", exc)
        raise
    except APIConnectionError as exc:
        logger.error("Connection error: %s", exc)
        raise
    except APIError as exc:
        logger.error("API error: %s", exc)
        raise


def extract_json(text: str) -> dict | list:
    """
    Robustly extract a JSON object or array from model output.

    Handles:
    - Pure JSON strings
    - JSON wrapped in ```json ... ``` code blocks
    - JSON embedded in explanatory prose
    """
    # 1. Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Try extracting from code fence
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence_match:
        try:
            return json.loads(fence_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 3. Try finding first { ... } or [ ... ] block
    brace_match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
    if brace_match:
        try:
            return json.loads(brace_match.group(1))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract JSON from LLM response:\n{text[:500]}")
