from __future__ import annotations

from typing import Callable

from .config import Settings
from .graph import Deps
from .llm import GroqLLM
from .memory import Memory


def _effort(model: str, thinking: bool) -> str | None:
    """Qwen accepts 'none'/'default'; GPT-OSS accepts 'low'/'medium'/'high'."""
    if "qwen" in model:
        return "default" if thinking else "none"
    if "gpt-oss" in model:
        return "low"
    return None


def make_writer(s: Settings) -> GroqLLM:
    return GroqLLM(s.writer_model, s.groq_api_key, temperature=s.writer_temperature,
                   max_tokens=s.writer_max_tokens, tpm=s.writer_tpm,
                   reasoning_effort=_effort(s.writer_model, thinking=False))


def make_judge(s: Settings) -> GroqLLM:
    return GroqLLM(s.judge_model, s.groq_api_key, temperature=s.judge_temperature,
                   max_tokens=s.judge_max_tokens, tpm=s.judge_tpm,
                   reasoning_effort=_effort(s.judge_model, thinking=True))


def make_reflector(s: Settings) -> GroqLLM:
    return GroqLLM(s.reflector_model, s.groq_api_key, temperature=0.2, max_tokens=1500,
                   tpm=s.writer_tpm, reasoning_effort=_effort(s.reflector_model, thinking=False))


def make_deps(
    s: Settings,
    *,
    inject: list[str] | None = None,
    use_memory: bool = True,
    use_learned_rules: bool = True,
    log: Callable[[str], None] = print,
) -> Deps:
    return Deps(
        settings=s,
        writer=make_writer(s),
        judge=make_judge(s),
        reflector=make_reflector(s),
        memory=Memory(s.db_path) if use_memory else None,
        inject=inject,
        use_learned_rules=use_learned_rules,
        log=log,
    )
