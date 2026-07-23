"""OpenRouter implementation of the classifier's ``Model`` contract.

The only thing above it knows is ``judge(items) -> verdicts``, so swapping the
provider or the model is a change confined to this file.

Named ``DefaultTriageModel`` rather than after the vendor: OpenRouter is today's
route to the model, not a property of the contract.
"""

from __future__ import annotations

import os

from openai import OpenAI

from backend.services.classifier import SYSTEM_PROMPT, parse_model_output

# Beyond this the batch has stalled and the user is staring at rule tiers
# anyway, so waiting longer buys nothing.
REQUEST_TIMEOUT_SECONDS = 20.0


class DefaultTriageModel:
    """Uses the OpenAI client because OpenRouter speaks that wire format."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self._model = model or os.environ.get(
            "OPENROUTER_MODEL", "google/gemini-2.5-flash"
        )
        self._client = OpenAI(
            api_key=api_key or os.environ["OPENROUTER_API_KEY"],
            base_url=base_url
            or os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            timeout=REQUEST_TIMEOUT_SECONDS,
            max_retries=0,  # the classifier owns the retry policy, not the SDK
        )

    def judge(self, items: list[dict]) -> list[dict]:
        response = self._client.chat.completions.create(
            model=self._model,
            temperature=0,  # triage is a judgement, not a draft
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _render(items)},
            ],
        )
        return parse_model_output(response.choices[0].message.content or "")


def _render(items: list[dict]) -> str:
    import json

    return json.dumps(items, ensure_ascii=False, default=str)
