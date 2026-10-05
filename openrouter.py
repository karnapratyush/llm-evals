"""
Minimal OpenRouter chat client over plain HTTP (OpenAI-compatible /chat/completions).

Why not a library: langchain-openrouter's ChatOpenRouter hung indefinitely on every call here,
while the same request over plain HTTP returned in ~1s.
"""

import json
import time

import httpx

from config import API_KEY, MAX_RETRIES, MAX_TOKENS, OPENROUTER_URL, REQUEST_TIMEOUT_S

RETRYABLE_STATUS = (429, 500, 502, 503, 504)


class OutOfCredits(Exception):
    """OpenRouter HTTP 402: the account cannot cover the call. Callers should abort the run."""


class OpenRouter:
    """One client shared by all worker threads (httpx.Client is thread-safe)."""

    def __init__(self, api_key=API_KEY):
        self.client = httpx.Client(
            base_url=OPENROUTER_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            # httpx timeouts are per network operation (max gap between bytes), NOT per request;
            # the per-request limit is enforced in post_with_deadline()
            timeout=httpx.Timeout(60, connect=15),
        )

    def post_with_deadline(self, body):
        """
        POST and read the reply, giving up after REQUEST_TIMEOUT_S of wall-clock time.
        Needed because OpenRouter keeps slow requests alive by sending filler bytes, which resets
        httpx's read timeout forever - so a plain client.post() can wait indefinitely.
        """
        deadline = time.monotonic() + REQUEST_TIMEOUT_S
        with self.client.stream("POST", "/chat/completions", json=body) as resp:
            chunks = []
            for chunk in resp.iter_bytes():
                chunks.append(chunk)
                if time.monotonic() > deadline:
                    raise TimeoutError(f"no complete reply within {REQUEST_TIMEOUT_S}s")
        text = b"".join(chunks).decode("utf-8", errors="replace")
        # drop keep-alive lines such as ': OPENROUTER PROCESSING' before parsing the JSON
        text = "\n".join(line for line in text.splitlines() if not line.startswith(":"))
        return resp.status_code, json.loads(text)

    def chat(self, model, system_prompt, user_prompt):
        """Returns (reply text, usage dict). Retries rate limits, server errors and provider failures."""
        body = {
            "model": model,
            "temperature": 0,
            "max_tokens": MAX_TOKENS,
            "messages": [{"role": "system", "content": system_prompt},
                         {"role": "user", "content": user_prompt}],
        }
        for attempt in range(MAX_RETRIES + 1):
            last_try = attempt == MAX_RETRIES
            status, data = self.post_with_deadline(body)
            if status in RETRYABLE_STATUS and not last_try:
                time.sleep(2 ** attempt * 5)
                continue
            if status == 402:   # OpenRouter reserves max_tokens x price up front; balance too low
                raise OutOfCredits(data.get("error", {}).get("message", "insufficient credits"))
            if "error" in data or status != 200:
                err = data.get("error", data)
                raise RuntimeError(f"HTTP {status}: {err.get('message', err) if isinstance(err, dict) else err}")
            choice = data["choices"][0]
            # the provider failed mid-generation (HTTP 200 but finish_reason 'error', not billed)
            if choice.get("finish_reason") == "error" and not last_try:
                time.sleep(2 ** attempt * 5)
                continue
            content = choice["message"].get("content") or ""
            if isinstance(content, list):   # some providers return content blocks
                content = "".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in content)
            usage = data.get("usage", {})
            return content, dict(
                finish_reason=choice.get("finish_reason"),
                prompt_tokens=usage.get("prompt_tokens"),
                completion_tokens=usage.get("completion_tokens"),
                reasoning_tokens=(usage.get("completion_tokens_details") or {}).get("reasoning_tokens"),
                cost_usd=usage.get("cost"),
            )
