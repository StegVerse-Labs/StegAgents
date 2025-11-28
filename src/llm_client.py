import os
import time
from typing import List, Dict, Any

import requests


API_URL = "https://api.openai.com/v1/chat/completions"


class MissingAPIKey(RuntimeError):
    pass


def _get_api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise MissingAPIKey("OPENAI_API_KEY not set in environment")
    return key


def call_llm(
    messages: List[Dict[str, str]],
    model: str = "gpt-4.1-mini",
    max_tokens: int = 1200,
    temperature: float = 0.4,
    retries: int = 3,
    initial_backoff: float = 2.0,
) -> str:
    """
    Low-level wrapper for OpenAI's chat completions endpoint using `requests`.

    `messages` is a standard OpenAI messages list:
      [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
    """
    api_key = _get_api_key()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    backoff = initial_backoff

    for attempt in range(1, retries + 1):
        resp = requests.post(API_URL, headers=headers, json=payload)
        try:
            resp.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            status = resp.status_code
            # Gentle handling for rate limits
            if status in (429, 500, 502, 503, 504) and attempt < retries:
                print(
                    f"[llm_client] Transient error {status} on attempt "
                    f"{attempt}/{retries}; backing off {backoff:.1f}s..."
                )
                time.sleep(backoff)
                backoff *= 2
                continue

            # Re-raise for non-retryable or final failure
            print(f"[llm_client] HTTP error from OpenAI: {status} {resp.text}")
            raise exc

        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:  # pragma: no cover
            raise RuntimeError(f"Unexpected OpenAI response: {data}") from exc

    raise RuntimeError("Exhausted retries calling OpenAI API")
