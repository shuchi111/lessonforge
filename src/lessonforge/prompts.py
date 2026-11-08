"""All prompts in one place, so prompt changes are easy to review and diff."""
from __future__ import annotations

from .evaluator.judges import AUDIENCE
from .knowledge import TopicPack
from .lesson_format import format_spec
from .schemas import CheckResult, LessonPlan

CHANGES_MARKER = "<<<CHANGES>>>"

WRITING_RULES = """WRITING RULES (the lesson is checked against these automatically):
1. Short sentences: aim for 8-14 words, never more than 25 words.
2. Everyday English words. Write at a 6th-8th grade reading level. Talk to the learner as "you".
3. No idioms, slang or difficult words (avoid words like leverage, paradigm, robust, utilize, facilitate).
4. Explain every technical term in simple words the FIRST time you use it, before using it again.
   Use as few technical terms as possible. Every technical term you use must also be in the glossary.
5. Teach with examples from Indian daily life: school, board exams, cricket, trains, local shops,
   mobile phones, family. Use one everyday analogy for the big idea.
6. Include one complete worked example that walks through every step with concrete data
   (the actual question, the actual pieces of text found, what the final prompt looks like, the answer).
7. Order: what it is -> why it matters -> how it works -> full example. Never use an idea before explaining it.
8. Standalone: do not say "as discussed earlier" or refer to other lessons.
9. Be accurate. Only state facts that agree with the FACT SHEET. Do not invent statistics, dates or tools.
10. Length: 950-1300 words, not counting the glossary."""


def writer_system(topic: TopicPack) -> str:
    return f"""You are an expert teacher who writes beginner lessons about AI.
{AUDIENCE}

{WRITING_RULES}

{format_spec(topic.short_name)}"""


def learned_rules_block(rules: list[str]) -> str:
    if not rules:
        return ""
    lines = "\n".join(f"- {r}" for r in rules)
    return f"\nLESSONS LEARNED FROM PAST REVIEWS (follow these strictly):\n{lines}\n"


PLANNER_SYSTEM = f"""You are an instructional designer planning a beginner lesson.
{AUDIENCE}
Reply with JSON only."""


def planner_user(topic: TopicPack) -> str:
    kp = topic.key_points_text() or "(none given - propose 6-10 key points a beginner must learn)"
    return f"""Plan a beginner lesson on: {topic.title}

KEY POINTS to cover:
{kp}

Return JSON:
{{
  "learning_objectives": ["3-5 objectives, each starting with a verb, e.g. 'Explain ...'"],
  "analogy": "one everyday analogy from Indian daily life that maps clearly onto how the topic works, with the mapping spelled out",
  "worked_example": "a concrete scenario for the full worked example (who asks what, what documents exist, what gets found, what the answer is)",
  "key_points": ["copy the key points above, or propose them if none were given"]
}}"""


def generate_user(topic: TopicPack, plan: LessonPlan, rules: list[str]) -> str:
    objectives = "\n".join(f"- {o}" for o in plan.learning_objectives)
    facts = topic.fact_sheet or "(no fact sheet - use only well-established facts)"
    return f"""Write the complete lesson: {topic.title}

LEARNING OBJECTIVES:
{objectives}

KEY POINTS (teach every one):
{topic.key_points_text()}

ANALOGY TO USE:
{plan.analogy}

WORKED EXAMPLE SCENARIO:
{plan.worked_example}

FACT SHEET (ground truth - do not contradict it):
{facts}
{learned_rules_block(rules)}
Write only the lesson in Markdown, starting with the '# ' title line."""


def _failure_block(failed: list[CheckResult]) -> str:
    out = []
    for r in failed:
        lines = [f"[{r.id}] {r.name} - FAILED", f"  Why: {r.reason}"]
        if r.evidence:
            lines.append(f"  Evidence: {r.evidence}")
        if r.fix:
            lines.append(f"  How to fix: {r.fix}")
        out.append("\n".join(lines))
    return "\n\n".join(out)


def revise_user(
    topic: TopicPack,
    lesson_md: str,
    failed: list[CheckResult],
    previously_failed: list[str],
    rules: list[str],
) -> str:
    keep = ""
    if previously_failed:
        keep = ("\nThese checks failed in earlier attempts and were fixed - do NOT break them again: "
                + ", ".join(previously_failed) + "\n")
    facts = ""
    if any(r.dimension == "accurate & grounded" for r in failed) and topic.fact_sheet:
        facts = f"\nFACT SHEET (ground truth):\n{topic.fact_sheet}\n"
    return f"""Your lesson on "{topic.title}" was reviewed and FAILED these checks:

{_failure_block(failed)}
{keep}{learned_rules_block(rules)}{facts}
KEY POINTS (teach every one):
{topic.key_points_text()}

PREVIOUS LESSON:
<<<LESSON
{lesson_md}
LESSON>>>

Rewrite the COMPLETE lesson so that every failed check passes. Keep everything that already
works. Follow the required structure exactly.

After the lesson, write a line containing only {CHANGES_MARKER} and then 3-8 bullet points
saying exactly what you changed and which check ID each change fixes."""


REFLECTOR_SYSTEM = """You improve an AI lesson-writing system by learning from its review history.
You write short, concrete, reusable instructions for the lesson writer.
Reply with JSON only."""


def reflector_user(failure_summary: str, existing_rules: list[str], feedback: list[str]) -> str:
    existing = "\n".join(f"- {r}" for r in existing_rules) or "- (none)"
    fb = "\n".join(f"- {f}" for f in feedback) or "- (none)"
    return f"""Below are quality checks that the lesson writer keeps failing across runs, with sample
reasons from the reviewer, plus feedback from human reviewers.

REPEATED FAILURES:
{failure_summary or '(none)'}

HUMAN FEEDBACK:
{fb}

RULES THE WRITER ALREADY FOLLOWS:
{existing}

Tasks:
1. For each repeated failure that existing rules do not already prevent, write ONE new rule:
   an imperative instruction under 30 words, specific enough to act on
   (e.g. "Before using the word 'embedding', explain it as 'a list of numbers that captures meaning'.").
2. If human feedback describes a quality problem the automatic checks would NOT catch, propose a new
   pass/fail rubric criterion for it (a human must approve it before it is used).

Return JSON:
{{"rules": [{{"source_check": "<check ID or 'HUMAN'>", "rule": "..."}}],
  "rubric_proposals": [{{"criterion": "FAIL if ...", "rationale": "..."}}]}}"""
