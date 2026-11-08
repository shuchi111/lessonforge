"""Self-evolving step: turn repeated failures and human feedback into prompt rules
and rubric proposals.

Guardrails:
- Rules are only learned from checks that fail in several *distinct* runs (not one bad sample),
  and runs with deliberately injected errors are ignored.
- Rules sharpen the WRITER prompt automatically, but the rubric is never relaxed automatically:
  new rubric criteria are stored as proposals that a human must approve.
- Rules are versioned rows that can be disabled; active rules are capped.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .llm import LLM, chat_structured
from .memory import Memory
from .prompts import REFLECTOR_SYSTEM, reflector_user
from .schemas import ReflectionOutput


@dataclass
class ReflectionReport:
    new_rules: list[str] = field(default_factory=list)
    new_proposals: list[str] = field(default_factory=list)
    skipped_reason: str = ""


def reflect(memory: Memory, llm: LLM | None, run_id: str | None, *, min_runs: int = 2,
            max_active_rules: int = 12) -> ReflectionReport:
    active = memory.active_rules()
    covered = {r["source_check"] for r in active}
    repeated = [f for f in memory.repeated_failures(min_runs) if f["check_id"] not in covered]
    feedback = memory.unprocessed_feedback()

    if not repeated and not feedback:
        return ReflectionReport(skipped_reason="no new repeated failures or human feedback")
    if llm is None:
        return ReflectionReport(skipped_reason="no reflector model configured")

    summary = "\n".join(
        f"- {f['check_id']} ({f['name']}): failed in {f['runs_failed']} runs. Sample reasons: "
        + " | ".join(r for r in f["sample_reasons"] if r)
        for f in repeated
    )
    out = chat_structured(
        llm, REFLECTOR_SYSTEM,
        reflector_user(summary, [r["rule"] for r in active], [f["note"] for f in feedback]),
        ReflectionOutput,
    )

    report = ReflectionReport()
    existing = {r["rule"].strip().lower() for r in memory.all_rules()}
    allowed = {f["check_id"] for f in repeated} | ({"HUMAN"} if feedback else set())
    for rule in out.rules:
        text = rule.rule.strip()
        if not text or text.lower() in existing or rule.source_check not in allowed:
            continue
        memory.add_rule(text, rule.source_check, run_id, max_active_rules)
        existing.add(text.lower())
        report.new_rules.append(f"[{rule.source_check}] {text}")
    if feedback:
        for p in out.rubric_proposals:
            memory.add_proposal(p.criterion, p.rationale)
            report.new_proposals.append(p.criterion)
        memory.mark_feedback_processed([f["id"] for f in feedback])
    return report
