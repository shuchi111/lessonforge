"""Thin LLM layer.

Everything in the pipeline talks to the `LLM` protocol, so the Groq client can be
swapped for another provider (or a fake in tests) without touching the graph.
"""
from __future__ import annotations

import json
import re
import threading
import time
from collections import deque
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


class LLM(Protocol):
    name: str

    def chat(self, system: str, user: str, *, json_mode: bool = False) -> str: ...


class LLMError(RuntimeError):
    pass


class TokenBudget:
    """Client-side tokens-per-minute limiter.

    Groq counts (prompt tokens + max_tokens) against the per-minute limit, so we wait
    *before* sending instead of burning retries on 429s.
    """

    def __init__(self, tpm: int):
        self.tpm = tpm
        self._events: deque[list] = deque()
        self._lock = threading.Lock()

    def acquire(self, tokens: int) -> list:
        """Reserve tokens; returns a handle so the reservation can be settled to actual usage."""
        tokens = min(tokens, self.tpm)
        while True:
            with self._lock:
                now = time.monotonic()
                while self._events and now - self._events[0][0] > 60:
                    self._events.popleft()
                used = sum(t for _, t in self._events)
                if used + tokens <= self.tpm:
                    event = [now, tokens]
                    self._events.append(event)
                    return event
                wait = 60 - (now - self._events[0][0]) + 0.5
            time.sleep(max(wait, 0.5))

    def settle(self, event: list, actual_tokens: int) -> None:
        with self._lock:
            event[1] = actual_tokens


def estimate_tokens(text: str) -> int:
    return len(text) // 4 + 1


class GroqLLM:
    def __init__(
        self,
        model: str,
        api_key: str,
        *,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        tpm: int = 6000,
        reasoning_effort: str | None = "low",
    ):
        if not api_key:
            raise LLMError("GROQ_API_KEY is not set. Copy .env.example to .env and add your key.")
        from groq import Groq

        self.name = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.reasoning_effort = reasoning_effort
        self.budget = TokenBudget(tpm)
        self._client = Groq(api_key=api_key, max_retries=5)

    def _create_with_backoff(self, kwargs: dict[str, Any], tries: int = 5) -> Any:
        """Groq also enforces limits we can't see client-side (e.g. output tokens per minute)."""
        from groq import RateLimitError

        for attempt in range(1, tries + 1):
            try:
                return self._client.chat.completions.create(**kwargs)
            except RateLimitError as exc:
                if attempt == tries:
                    raise LLMError(f"{self.name} still rate-limited after {tries} tries: {exc}") from exc
                retry_after = exc.response.headers.get("retry-after") if exc.response is not None else None
                try:
                    wait = float(retry_after) + 1
                except (TypeError, ValueError):
                    wait = 20.0 * attempt
                time.sleep(min(max(wait, 5.0), 90.0))

    def _is_reasoning_model(self) -> bool:
        return "gpt-oss" in self.name or "qwen3" in self.name

    def chat(self, system: str, user: str, *, json_mode: bool = False) -> str:
        from groq import BadRequestError

        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        kwargs: dict[str, Any] = dict(
            model=self.name,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        if self._is_reasoning_model() and self.reasoning_effort:
            kwargs["reasoning_effort"] = self.reasoning_effort
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        reservation = self.budget.acquire(estimate_tokens(system + user) + self.max_tokens)
        try:
            resp = self._create_with_backoff(kwargs)
        except BadRequestError as exc:
            # Some models reject json_object mode or reasoning params; retry plainly.
            if "response_format" not in kwargs and "reasoning_effort" not in kwargs:
                raise LLMError(str(exc)) from exc
            kwargs.pop("response_format", None)
            kwargs.pop("reasoning_effort", None)
            resp = self._create_with_backoff(kwargs)
        if resp.usage:
            self.budget.settle(reservation, resp.usage.total_tokens)
        content = re.sub(r"<think>.*?</think>", "", resp.choices[0].message.content or "", flags=re.DOTALL)
        if not content.strip():
            raise LLMError(f"{self.name} returned an empty response")
        return content


_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


def extract_json(text: str) -> Any:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = _JSON_BLOCK.search(text)
        if not match:
            raise
        return json.loads(match.group(0))


def chat_structured(llm: LLM, system: str, user: str, schema: type[T], *, attempts: int = 2) -> T:
    """Ask for JSON, validate it against a Pydantic schema, and repair once on failure."""
    last_error: Exception | None = None
    prompt = user
    for _ in range(attempts):
        raw = llm.chat(system, prompt, json_mode=True)
        try:
            return schema.model_validate(extract_json(raw))
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = exc
            prompt = (
                f"{user}\n\nYour previous reply was not valid JSON for the required schema.\n"
                f"Error: {str(exc)[:500]}\nReply again with ONLY the corrected JSON object."
            )
    raise LLMError(f"Could not get valid JSON from {llm.name}: {last_error}")
