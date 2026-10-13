"""Render a structured :class:`Hint` into a natural-language message.

Two renderers are provided:

* :class:`TemplateRenderer` — deterministic, no network, no API key.  This is
  the default so the prototype is testable out of the box.
* :class:`OpenAIRenderer` — an OpenAI-compatible chat-completion renderer
  (uses only the standard library's ``urllib``).  It is instructed to phrase
  the hint nicely and, crucially, *not* to reveal the answer.

The policy (which rung, what content) is already fixed before rendering, so
the model only ever rewrites an approved hint — never decides to hand over a
solution.
"""

from __future__ import annotations

import json
import os
import urllib.request

from tutor.hints import Hint


class Renderer:
    def render(self, hint: Hint, prompt: str) -> str:
        raise NotImplementedError


class TemplateRenderer(Renderer):
    """Deterministic plain-text rendering.  No dependencies, no API."""

    def render(self, hint: Hint, prompt: str) -> str:
        del prompt  # the hint content is self-contained
        return hint.render_text()


class OpenAIRenderer(Renderer):
    """Phrase hints through an OpenAI-compatible chat completion endpoint."""

    def __init__(self, base_url: str, api_key: str, model: str = "gpt-4o-mini"):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    def render(self, hint: Hint, prompt: str) -> str:
        system = (
            "You are a patient programming tutor. You give hints, never full "
            "answers, because the learner learns by struggling. Use the hint "
            "content you are given and phrase it in a warm, encouraging way. "
            "Do NOT add code beyond what is provided, and do NOT reveal a "
            "complete solution. Keep it short."
        )
        user = (
            f"Learner's prompt: {prompt!r}\n\n"
            f"Hint to phrase (level {int(hint.level)}):\n{hint.render_text()}"
        )
        body = json.dumps(
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.7,
            }
        ).encode("utf-8")

        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return payload["choices"][0]["message"]["content"].strip()


def make_renderer() -> Renderer:
    """Choose a renderer from environment variables.

    Set ``OPENAI_API_KEY`` to enable the LLM renderer; ``OPENAI_BASE_URL`` and
    ``OPENAI_MODEL`` are optional overrides.  Without a key, fall back to the
    deterministic template renderer.
    """
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return TemplateRenderer()
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    return OpenAIRenderer(base_url=base_url, api_key=api_key, model=model)
