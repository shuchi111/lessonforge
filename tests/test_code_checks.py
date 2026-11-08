from __future__ import annotations

import re

import pytest

from lessonforge.evaluator import Evaluator
from lessonforge.inject import inject_errors


def code_eval(md: str, pack):
    return Evaluator(None, pack).evaluate(md, code_only=True)


def failed_ids(ev) -> set[str]:
    return {r.id for r in ev.failed}


def test_reference_lesson_passes_all_code_checks(good_lesson, rag_pack):
    ev = code_eval(good_lesson, rag_pack)
    assert ev.passed, [(r.id, r.reason, r.evidence) for r in ev.failed]
    assert {r.id for r in ev.results} == {"S1", "S2", "L1", "L2", "J1", "G1", "Q1"}


@pytest.mark.parametrize("kind, expected", [
    ("jargon", {"J1"}),
    ("long", {"L2"}),
    ("structure", {"S1"}),
])
def test_injected_errors_are_caught(good_lesson, rag_pack, kind, expected):
    corrupted, applied = inject_errors(good_lesson, [kind])
    assert applied == [kind]
    assert expected <= failed_ids(code_eval(corrupted, rag_pack))


def test_missing_hindi_meaning_fails_g1(good_lesson, rag_pack):
    md = good_lesson.replace("**Chunk** (टुकड़ा)", "**Chunk** (piece)")
    ev = code_eval(md, rag_pack)
    assert failed_ids(ev) == {"G1"}
    assert "Chunk" in next(r.reason for r in ev.failed)


def test_undefined_term_fails_j1_with_specific_fix(good_lesson, rag_pack):
    md = good_lesson.replace(re.search(r"- \*\*Hallucination\*\*.*\n", good_lesson).group(0), "")
    ev = code_eval(md, rag_pack)
    j1 = next(r for r in ev.results if r.id == "J1")
    assert not j1.passed and "hallucination" in j1.fix


def test_missing_quiz_answers_fails_q1(good_lesson, rag_pack):
    md = good_lesson.replace("**Answers:** 1-B, 2-A, 3-C, 4-B", "")
    assert "Q1" in failed_ids(code_eval(md, rag_pack))


def test_hard_words_fail_reading_level(good_lesson, rag_pack):
    dense = ("Contemporary organizational infrastructure fundamentally necessitates sophisticated "
             "computational methodologies, particularly regarding informational accessibility. ")
    md = good_lesson.replace("## Why Does RAG Matter?\n", "## Why Does RAG Matter?\n\n" + dense * 25)
    assert "L1" in failed_ids(code_eval(md, rag_pack))


def test_too_short_lesson_fails_length(rag_pack):
    md = "# Tiny\n\n## Let's Start With a Story\n\nHi.\n"
    assert {"S1", "S2"} <= failed_ids(code_eval(md, rag_pack))
