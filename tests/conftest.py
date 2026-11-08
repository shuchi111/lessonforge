from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Callable

import pytest

from lessonforge.knowledge import find_topic_pack

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def good_lesson() -> str:
    return (FIXTURES / "good_lesson.md").read_text(encoding="utf-8")


@pytest.fixture
def rag_pack():
    pack = find_topic_pack("Introduction to RAG")
    assert pack is not None
    return pack


class FakeLLM:
    """Scripted stand-in for a real model. `responder(system, user, json_mode) -> str`."""

    def __init__(self, name: str, responder: Callable[[str, str, bool], str]):
        self.name = name
        self.responder = responder
        self.calls: list[tuple[str, str]] = []

    def chat(self, system: str, user: str, *, json_mode: bool = False) -> str:
        self.calls.append((system, user))
        return self.responder(system, user, json_mode)


def all_pass_judge(fail_ids: set[str] | None = None) -> FakeLLM:
    fail_ids = fail_ids or set()

    def respond(system: str, user: str, json_mode: bool) -> str:
        ids = re.findall(r"^- (\w+) \|", user, re.MULTILINE)
        return json.dumps({"verdicts": [
            {"id": i, "passed": i not in fail_ids,
             "evidence": "" if i not in fail_ids else "MISSING: something",
             "reason": "ok" if i not in fail_ids else "fake failure", "fix": ""}
            for i in ids
        ]})

    return FakeLLM("fake-judge", respond)


PLAN_JSON = json.dumps({
    "learning_objectives": ["Explain what RAG is"],
    "analogy": "Open-book exam",
    "worked_example": "Priya asks about exam rules",
    "key_points": [],
})
