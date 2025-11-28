import os
import time
import random
import requests

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not set in environment")

API_URL = "https://api.openai.com/v1/chat/completions"


def call_llm(prompt, model="gpt-4o-mini", max_retries=7):
    """Calls OpenAI API with built-in rate-limit handling."""

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(API_URL, json=payload, headers=headers)

            # Success
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]

            # Rate limit
            if response.status_code == 429:
                wait = min(2 ** attempt, 30) + random.uniform(0, 1.5)
                print(f"[RateLimit] 429 received. Retrying in {wait:.2f}s (attempt {attempt}/{max_retries})")
                time.sleep(wait)
                continue

            # Other errors — raise normally
            response.raise_for_status()

        except requests.exceptions.RequestException as e:
            wait = min(2 ** attempt, 30) + random.uniform(0, 1.5)
            print(f"[NetworkError] {e} — retrying in {wait:.2f}s (attempt {attempt}/{max_retries})")
            time.sleep(wait)

    raise RuntimeError("OpenAI request failed after maximum retry attempts.")
