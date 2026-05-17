"""Base class for all Helmsman LLM-backed agents."""
from __future__ import annotations

import json
from typing import Any

from openai import APIConnectionError, APITimeoutError, RateLimitError
from openai.types.chat import ChatCompletionMessageParam
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from helmsman.core.llm_client import ModelTier, get_client, get_deployment
from helmsman.core.logging import logger

# LLM の再試行ポリシー (transient 失敗のみ)
_RETRYABLE = (RateLimitError, APITimeoutError, APIConnectionError)


class LLMAgent:
    """Convention-over-configuration LLM agent base.

    Subclass override:
        AGENT_NAME: str
        SYSTEM_PROMPT: str
        TIER: ModelTier (HIGH / MINI)

    Then call ``self._chat(user_text, json_mode=True)`` from your run() method.
    """

    AGENT_NAME: str = "BaseAgent"
    SYSTEM_PROMPT: str = ""
    TIER: ModelTier = ModelTier.MINI

    def __init__(self) -> None:
        self.client = get_client()
        self.deployment = get_deployment(self.TIER)
        self.log = logger.bind(agent=self.AGENT_NAME, deployment=self.deployment)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type(_RETRYABLE),
        reraise=True,
    )
    async def _chat(
        self,
        user_text: str,
        *,
        json_mode: bool = False,
        max_completion_tokens: int = 800,
        temperature: float = 1.0,
    ) -> str:
        """Call the chat completion endpoint and return the assistant content.

        Transient な失敗 (429/Timeout/Connection) は exponential backoff で 3 回まで再試行。
        """
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ]
        kwargs: dict[str, Any] = {
            "model": self.deployment,
            "messages": messages,
            "max_completion_tokens": max_completion_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        r = await self.client.chat.completions.create(**kwargs)
        content = r.choices[0].message.content or ""
        self.log.debug("llm.completed", tokens=r.usage.total_tokens if r.usage else None)
        return content

    async def _chat_json(
        self,
        user_text: str,
        *,
        max_completion_tokens: int = 800,
    ) -> dict[str, Any]:
        """Helper: call chat, expect JSON, return parsed dict."""
        text = await self._chat(
            user_text, json_mode=True, max_completion_tokens=max_completion_tokens
        )
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            self.log.warning("llm.bad_json", raw=text[:200])
            return {}
