"""LLM API client wrapper.

One responsibility: send chat messages to an OpenAI-compatible Chat
Completions endpoint and return the assistant text. Retries once on
failure, then raises LLMError so callers can degrade gracefully.

Configuration is via environment variables (never hard-code credentials):
  LLM_API_KEY   - API key (required unless MOCK_LLM=1)
  LLM_BASE_URL  - default https://api.openai.com/v1
  LLM_MODEL     - default gpt-4o-mini
  MOCK_LLM      - set to 1 to use the offline scripted mock
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"
REQUEST_TIMEOUT_SECONDS = 60


class LLMError(Exception):
    """Raised when the LLM API cannot produce a response."""


class LLMClient:
    """Minimal chat-completions client with one retry."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.environ.get("LLM_API_KEY", "")
        self.base_url = (base_url or os.environ.get("LLM_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.model = model or os.environ.get("LLM_MODEL") or DEFAULT_MODEL

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def chat(self, messages: list[dict], temperature: float = 0.4) -> str:
        """Send messages and return the assistant reply text.

        Raises LLMError after one retry on any failure.
        """
        if not self.configured:
            raise LLMError("LLM_API_KEY is not set.")
        last_error: Exception | None = None
        for _attempt in range(2):
            try:
                return self._request(messages, temperature)
            except LLMError as exc:
                last_error = exc
        raise LLMError(f"LLM request failed after retry: {last_error}")

    def _request(self, messages: list[dict], temperature: float) -> str:
        payload = json.dumps(
            {"model": self.model, "messages": messages, "temperature": temperature}
        ).encode("utf-8")
        request = urllib.request.Request(
            url=f"{self.base_url}/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:300]
            raise LLMError(f"HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise LLMError(str(exc)) from exc

        try:
            return body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"Unexpected API response shape: {exc}") from exc


class MockLLMClient:
    """Offline client for development and tests.

    If `script` is provided, replies are popped from it in order.
    Otherwise a deterministic generic Socratic reply is returned.
    Records every call in `self.calls` for assertions.
    """

    def __init__(self, script: list[str] | None = None, fail: bool = False) -> None:
        self.script = list(script or [])
        self.fail = fail
        self.calls: list[list[dict]] = []

    @property
    def configured(self) -> bool:
        return True

    def chat(self, messages: list[dict], temperature: float = 0.4) -> str:
        self.calls.append(messages)
        if self.fail:
            raise LLMError("mock failure")
        if self.script:
            return self.script.pop(0)
        return (
            "That is a useful start. What do you think happens on the first "
            "line of your code, and why?"
        )


def build_default_client() -> LLMClient | MockLLMClient:
    """Return the mock client when MOCK_LLM=1, else the real client."""
    if os.environ.get("MOCK_LLM") == "1":
        return MockLLMClient()
    return LLMClient()
