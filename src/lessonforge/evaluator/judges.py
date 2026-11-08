"""LLM-as-judge checks.

Design choices:
- Checks are grouped by what context they need (accuracy needs the fact sheet,
  pedagogy needs the key points). 3 calls instead of 9 keeps us inside Groq's
  free-tier tokens-per-minute limit, while each check still gets its own verdict.
- Binary verdicts only, temperature 0, "when in doubt, FAIL".
- Every verdict must quote evidence; we verify the quote exists in the lesson so a
  hallucinated failure is flagged instead of silently driving a rewrite.
"""
from __future__ import annotations

import re
from typing import Any

from ..knowledge import TopicPack
from ..llm import LLM, chat_structured
from ..schemas import JudgeResponse, JudgeVerdict

AUDIENCE = (
    "The learner is a 12th-grade graduate from India who studied in a non-English-medium "
    "school, has limited English vocabulary, has zero background in AI or programming, "
    "and wants to start a career in AI."
)

JUDGE_SYSTEM = f"""You are a strict quality reviewer for beginner learning content.
{AUDIENCE}

You judge a lesson against hard pass/fail checkpoints. Rules:
- Each checkpoint is PASS or FAIL. No partial credit. When in doubt, FAIL.
- Judge only what is written in the lesson. Do not assume intent.
- "evidence" must be an EXACT short quote copied from the lesson (max 30 words) that
  supports your verdict. For a FAIL, quote the problem text. If something is missing
  entirely, write "MISSING: <what is missing>".
- "reason" explains the verdict in one or two sentences.
- "fix" is a specific instruction the writer can follow to make the check pass
  (empty string if passed).
Reply with JSON only."""

OUTPUT_FORMAT = """Return a JSON object exactly like this, with one verdict per checkpoint ID:
{"verdicts": [{"id": "<ID>", "passed": true|false, "evidence": "...", "reason": "...", "fix": "..."}]}"""


def _context_for(group: str, topic: TopicPack) -> str:
    if group == "accuracy":
        if topic.grounded and topic.fact_sheet:
            facts = f"FACT SHEET (ground truth):\n{topic.fact_sheet}"
        else:
            facts = ("FACT SHEET: none available for this topic. Use well-established knowledge, "
                     "and FAIL any claim you are not confident is true.")
        return f"{facts}\n\nMISCONCEPTIONS (must not appear):\n{topic.misconceptions_text() or '- (none listed)'}"
    if group == "pedagogy":
        return f"KEY POINTS the lesson must teach:\n{topic.key_points_text()}"
    return ""


def _norm(s: str) -> str:
    s = re.sub(r"[\u2010-\u2015\u2212]", "-", s)
    s = re.sub(r"[\u2018\u2019]", "'", s)
    return re.sub(r"\s+", " ", re.sub(r"[*_`#>\"\u201c\u201d]", "", s)).strip().lower()


def verify_evidence(evidence: str, lesson_md: str) -> bool | None:
    if not evidence or evidence.upper().startswith("MISSING"):
        return None
    lesson = _norm(lesson_md)
    pieces = [p for p in re.split(r"\.\.\.|\u2026|\"\s*;\s*\"", evidence) if len(_norm(p)) >= 12]
    if not pieces:
        return _norm(evidence) in lesson
    return any(_norm(p) in lesson for p in pieces)


def run_judge(
    llm: LLM,
    group: str,
    checks: list[dict[str, Any]],
    lesson_md: str,
    topic: TopicPack,
) -> dict[str, JudgeVerdict]:
    def ask(subset: list[dict[str, Any]]) -> dict[str, JudgeVerdict]:
        checklist = "\n".join(f"- {c['id']} | {c['name']}: {c['criterion']}" for c in subset)
        user = (
            f"TOPIC: {topic.title}\n\n{_context_for(group, topic)}\n\n"
            f"CHECKPOINTS:\n{checklist}\n\n"
            f"LESSON TO REVIEW:\n<<<LESSON\n{lesson_md}\nLESSON>>>\n\n{OUTPUT_FORMAT}"
        )
        resp = chat_structured(llm, JUDGE_SYSTEM, user, JudgeResponse)
        return {v.id.strip().upper(): v for v in resp.verdicts}

    verdicts = ask(checks)
    missing = [c for c in checks if c["id"] not in verdicts]
    if missing:
        verdicts.update(ask(missing))
    for c in checks:
        verdicts.setdefault(c["id"], JudgeVerdict(
            id=c["id"], passed=False, reason="Judge returned no verdict for this check.",
        ))
    return verdicts
