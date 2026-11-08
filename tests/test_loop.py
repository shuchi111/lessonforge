"""End-to-end tests of the agentic loop and memory, fully offline (scripted fake models)."""
from __future__ import annotations

import json

from conftest import PLAN_JSON, FakeLLM, all_pass_judge

from lessonforge.config import Settings
from lessonforge.graph import Deps, run_pipeline
from lessonforge.memory import Memory
from lessonforge.prompts import CHANGES_MARKER


def settings(tmp_path, retries: int = 2) -> Settings:
    s = Settings()
    s.db_path = tmp_path / "mem.db"
    s.outputs_dir = tmp_path / "out"
    s.max_retries = retries
    return s


def writer_that(first: str, revised: str) -> FakeLLM:
    def respond(system: str, user: str, json_mode: bool) -> str:
        if json_mode:
            return PLAN_JSON
        if "FAILED these checks" in user:
            return f"{revised}\n{CHANGES_MARKER}\n- Split long sentences (L2)\n- Added glossary terms (J1)"
        return first
    return FakeLLM("fake-writer", respond)


def test_fail_then_fix_produces_passing_lesson_and_rejection_log(tmp_path, good_lesson):
    s = settings(tmp_path)
    deps = Deps(settings=s, writer=writer_that(good_lesson, good_lesson), judge=all_pass_judge(),
                memory=Memory(s.db_path), inject=["long", "jargon"])
    state = run_pipeline("Introduction to RAG", deps, "run-1")

    assert state["status"] == "passed"
    assert len(state["attempts"]) == 2
    first = state["attempts"][0]["evaluation"]["results"]
    assert {"L2", "J1"} <= {r["id"] for r in first if not r["passed"]}

    log = (s.outputs_dir / "run-1" / "rejection_log.md").read_text(encoding="utf-8")
    assert "PASSED on attempt 2" in log and "Split long sentences" in log and "fixed: " in log
    assert (s.outputs_dir / "latest" / "lesson.md").exists()

    feedback_prompt = deps.writer.calls[-1][1]
    assert "[L2]" in feedback_prompt and "How to fix" in feedback_prompt


def test_loop_always_terminates_and_flags_for_review(tmp_path, good_lesson):
    s = settings(tmp_path, retries=2)
    judge = all_pass_judge(fail_ids={"A1"})
    deps = Deps(settings=s, writer=writer_that(good_lesson, good_lesson), judge=judge, memory=Memory(s.db_path))
    state = run_pipeline("Introduction to RAG", deps, "run-x")

    assert state["status"] == "needs_human_review"
    assert len(state["attempts"]) == 3
    lesson = (s.outputs_dir / "run-x" / "lesson.md").read_text(encoding="utf-8")
    assert "NEEDS HUMAN REVIEW" in lesson


def test_failed_revision_stops_gracefully_with_best_attempt(tmp_path, good_lesson):
    from lessonforge.llm import LLMError

    def respond(system: str, user: str, json_mode: bool) -> str:
        if json_mode:
            return PLAN_JSON
        if "FAILED these checks" in user:
            raise LLMError("rate-limited")
        return good_lesson

    s = settings(tmp_path)
    deps = Deps(settings=s, writer=FakeLLM("w", respond), judge=all_pass_judge(), memory=Memory(s.db_path),
                inject=["long"])
    state = run_pipeline("Introduction to RAG", deps, "run-err")
    assert state["status"] == "needs_human_review" and len(state["attempts"]) == 1
    assert "Stopped early" in (s.outputs_dir / "run-err" / "rejection_log.md").read_text(encoding="utf-8")


def test_memory_learns_rule_from_repeated_failures_and_uses_it(tmp_path, good_lesson):
    s = settings(tmp_path, retries=1)
    memory = Memory(s.db_path)
    bad = good_lesson.replace("## Why Does RAG Matter?", "## Why Does RAG Matter?\n\nWe use HNSW indexes.")

    reflector = FakeLLM("fake-reflector", lambda *_: json.dumps({
        "rules": [{"source_check": "J1", "rule": "Never mention HNSW or other index algorithms."}],
        "rubric_proposals": [],
    }))

    for i in range(2):
        deps = Deps(settings=s, writer=writer_that(bad, good_lesson), judge=all_pass_judge(),
                    reflector=reflector, memory=memory)
        state = run_pipeline("Introduction to RAG", deps, f"run-{i}")
        assert state["status"] == "passed"

    rules = memory.active_rules()
    assert [r["rule"] for r in rules] == ["Never mention HNSW or other index algorithms."]

    writer = writer_that(good_lesson, good_lesson)
    run_pipeline("Introduction to RAG", Deps(settings=s, writer=writer, judge=all_pass_judge(),
                                             reflector=reflector, memory=memory), "run-3")
    generate_prompt = writer.calls[1][1]
    assert "LESSONS LEARNED FROM PAST REVIEWS" in generate_prompt and "HNSW" in generate_prompt
    assert memory.active_rules()[0]["times_applied"] == 1


def test_human_feedback_creates_rubric_proposal_that_becomes_a_check(tmp_path, good_lesson):
    s = settings(tmp_path)
    memory = Memory(s.db_path)
    memory.add_feedback("run-0", "The example uses too many numbers for a beginner.")
    reflector = FakeLLM("fake-reflector", lambda *_: json.dumps({
        "rules": [{"source_check": "HUMAN", "rule": "Keep numbers in examples small and few."}],
        "rubric_proposals": [{"criterion": "FAIL if the worked example uses more than 5 numbers.",
                              "rationale": "Human reviewer feedback"}],
    }))
    deps = Deps(settings=s, writer=writer_that(good_lesson, good_lesson), judge=all_pass_judge(),
                reflector=reflector, memory=memory)
    run_pipeline("Introduction to RAG", deps, "run-1")

    proposal = memory.proposals("pending")[0]
    memory.set_proposal_status(proposal["id"], "approved")
    judge = all_pass_judge()
    run_pipeline("Introduction to RAG", Deps(settings=s, writer=writer_that(good_lesson, good_lesson),
                                             judge=judge, reflector=reflector, memory=memory), "run-2")
    assert any(f"X{proposal['id']} |" in user for _, user in judge.calls)
