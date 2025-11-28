import os
import time
import json
from typing import Any, Dict

import requests


API_URL = "https://api.openai.com/v1/chat/completions"


def _get_api_key() -> str:
    """
    Fetch the OpenAI API key from the environment.

    We use OPENAI_API_KEY (set in the GitHub Actions workflow) so the
    key name is consistent everywhere.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set in environment")
    return api_key


def call_llm(
    prompt: str,
    model: str = "gpt-4o-mini",
    max_tokens: int = 1200,
    temperature: float = 0.7,
    max_retries: int = 5,
    base_delay_seconds: float = 5.0,
) -> str:
    """
    Call the OpenAI Chat Completions API with robust retry logic.

    - Retries on 429 / 5xx errors with exponential backoff.
    - Logs what it's doing so the Actions log becomes our "black box recorder".
    """

    api_key = _get_api_key()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    body: Dict[str, Any] = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a helpful AI assistant working inside the "
                    "StegVerse StegAgents subsystem. Respond concisely and "
                    "clearly, focusing on actionable output."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    attempt = 0

    while True:
        attempt += 1
        try:
            print(
                f"[LLM] Calling model='{model}' "
                f"(attempt {attempt}/{max_retries})"
            )

            response = requests.post(
                API_URL,
                headers=headers,
                json=body,
                timeout=60,
            )

            # Success path
            if response.status_code == 200:
                data = response.json()
                try:
                    content = data["choices"][0]["message"]["content"]
                except (KeyError, IndexError) as exc:
                    raise RuntimeError(
                        f"Unexpected response structure from OpenAI: {json.dumps(data)[:500]}"
                    ) from exc

                print("[LLM] Call successful.")
                return content

            # Transient / rate-limit errors we should retry
            if response.status_code in (429, 500, 502, 503, 504):
                # Respect Retry-After header when present
                retry_after_header = response.headers.get("Retry-After")
                if retry_after_header:
                    try:
                        delay = float(retry_after_header)
                    except ValueError:
                        delay = base_delay_seconds
                else:
                    delay = base_delay_seconds * (2 ** (attempt - 1))

                print(
                    f"[LLM] Transient error {response.status_code}: "
                    f"{response.text[:200]}..."
                )

                if attempt >= max_retries:
                    raise RuntimeError(
                        f"Exceeded max_retries ({max_retries}) for transient "
                        f"error {response.status_code}"
                    )

                # Cap delay to something sane
                delay = min(delay, 60.0)
                print(f"[LLM] Sleeping {delay:.1f}s before retry...")
                time.sleep(delay)
                continue

            # Non-retryable errors: log and raise
            raise RuntimeError(
                f"OpenAI API returned status {response.status_code}: "
                f"{response.text[:500]}"
            )

        except requests.RequestException as exc:
            # Network-level issues: also retry with backoff
            print(f"[LLM] Network exception: {exc}")

            if attempt >= max_retries:
                raise RuntimeError(
                    f"Exceeded max_retries ({max_retries}) due to network errors"
                ) from exc

            delay = base_delay_seconds * (2 ** (attempt - 1))
            delay = min(delay, 60.0)
            print(f"[LLM] Sleeping {delay:.1f}s before retry after network error...")
            time.sleep(delay)
