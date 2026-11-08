"""The agentic loop, as a LangGraph state machine.

load_context -> plan -> generate -> evaluate --pass--------------> finalize -> persist -> reflect
                                       |  ^                          ^
                                  fail |  | (max_retries)            | fail, retries used up
                                       v  |                          |
                                     revise ---------------------------
"""
from __future__ import annotations

import json
import re
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, TypedDict

from langgraph.graph import END, START, StateGraph

from .config import Settings
from .evaluator import Evaluator
from .inject import inject_errors
from .knowledge import TopicPack, find_topic_pack
from .llm import LLM, LLMError, chat_structured
from .memory import Memory
from .prompts import (CHANGES_MARKER, PLANNER_SYSTEM, generate_user, planner_user, revise_user,
                      writer_system)
from .reflection import reflect
from .render import rejection_log_md
from .schemas import Attempt, LessonPlan


class LessonState(TypedDict, total=False):
    run_id: str
    topic: str
    topic_pack: dict[str, Any]
    rules: list[str]
    rule_ids: list[int]
    plan: dict[str, Any]
    lesson_md: str
    changes: str
    injected: list[str]
    attempts: list[dict[str, Any]]
    status: str
    final_attempt: int
    output_dir: str
    reflection: dict[str, Any]
    error: str


@dataclass
class Deps:
    settings: Settings
    writer: LLM
    judge: LLM
    reflector: LLM | None = None
    memory: Memory | None = None
    inject: list[str] | None = None
    use_learned_rules: bool = True
    log: Callable[[str], None] = field(default=lambda _: None)


def new_run_id() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4]


def clean_lesson(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:markdown|md)?\s*\n", "", text)
    text = re.sub(r"\n```\s*$", "", text)
    title = re.search(r"^# \S", text, re.MULTILINE)
    return text[title.start():].strip() if title else text


def build_graph(deps: Deps):
    s = deps.settings
    log = deps.log

    def attempts_of(state: LessonState) -> list[Attempt]:
        return [Attempt.model_validate(a) for a in state.get("attempts", [])]

    def topic_of(state: LessonState) -> TopicPack:
        return TopicPack.from_dict(state["topic_pack"])

    # ---------------- nodes ----------------
    def load_context(state: LessonState) -> LessonState:
        pack = find_topic_pack(state["topic"], s.data_dir)
        if pack is None:
            log(f"No topic pack for '{state['topic']}': running UNGROUNDED (judge uses its own knowledge)")
            pack = TopicPack(title=state["topic"], short_name=state["topic"], key_points=[],
                             misconceptions=[], fact_sheet="", grounded=False)
        else:
            log(f"Topic pack loaded: {pack.title} ({len(pack.key_points)} key points, grounded)")
        rules, rule_ids = [], []
        if deps.memory and deps.use_learned_rules:
            active = deps.memory.active_rules()
            rules = [r["rule"] for r in active]
            rule_ids = [r["id"] for r in active]
            log(f"Memory: {len(rules)} learned rule(s) will be added to the writer prompt")
        if deps.memory:
            deps.memory.start_run(state["run_id"], state["topic"], deps.writer.name, deps.judge.name, rules)
        return {"topic_pack": pack.to_dict(), "rules": rules, "rule_ids": rule_ids, "attempts": []}

    def plan(state: LessonState) -> LessonState:
        topic = topic_of(state)
        log("Planning: learning objectives, analogy, worked example")
        p = chat_structured(deps.writer, PLANNER_SYSTEM, planner_user(topic), LessonPlan)
        update: LessonState = {"plan": p.model_dump()}
        if not topic.key_points and p.key_points:
            topic.key_points = [{"id": f"KP{i + 1}", "text": t} for i, t in enumerate(p.key_points)]
            update["topic_pack"] = topic.to_dict()
        return update

    def generate(state: LessonState) -> LessonState:
        topic = topic_of(state)
        log("Generating attempt 1")
        raw = deps.writer.chat(writer_system(topic),
                               generate_user(topic, LessonPlan.model_validate(state["plan"]), state["rules"]))
        lesson = clean_lesson(raw)
        injected: list[str] = []
        if deps.inject is not None:
            lesson, injected = inject_errors(lesson, deps.inject or None)
            log(f"DEMO: injected deliberate errors into attempt 1: {', '.join(injected)}")
        return {"lesson_md": lesson, "changes": "", "injected": injected}

    def evaluate(state: LessonState) -> LessonState:
        attempts = attempts_of(state)
        number = len(attempts) + 1
        extra = deps.memory.approved_checks() if deps.memory else []
        evaluator = Evaluator(deps.judge, topic_of(state), data_dir=s.data_dir, extra_checks=extra, log=log)
        log(f"Evaluating attempt {number}")
        ev = evaluator.evaluate(state["lesson_md"], number)
        attempt = Attempt(number=number, lesson_md=state["lesson_md"], evaluation=ev,
                          changes=state.get("changes", ""), injected_errors=state.get("injected", []))
        if ev.passed:
            log(f"Attempt {number}: PASSED all {len(ev.results)} checks")
        else:
            log(f"Attempt {number}: FAILED {len(ev.failed)}/{len(ev.results)} -> "
                + ", ".join(r.id for r in ev.failed))
        return {"attempts": [a.model_dump() for a in attempts] + [attempt.model_dump()], "injected": []}

    def route(state: LessonState) -> str:
        attempts = attempts_of(state)
        if attempts[-1].evaluation.passed:
            return "finalize"
        if len(attempts) <= s.max_retries:
            return "revise"
        log(f"Retry limit ({s.max_retries}) reached")
        return "finalize"

    def revise(state: LessonState) -> LessonState:
        topic = topic_of(state)
        attempts = attempts_of(state)
        last = attempts[-1]
        failed_now = {r.id for r in last.evaluation.failed}
        fixed_before = sorted({r.id for a in attempts[:-1] for r in a.evaluation.failed} - failed_now)
        log(f"Regenerating attempt {len(attempts) + 1} with feedback on {', '.join(sorted(failed_now))}")
        try:
            raw = deps.writer.chat(
                writer_system(topic),
                revise_user(topic, last.lesson_md, last.evaluation.failed, fixed_before, state["rules"]),
            )
        except LLMError as exc:
            log(f"Revision failed ({exc}); stopping with the best attempt so far")
            return {"error": str(exc)}
        lesson, _, changes = raw.partition(CHANGES_MARKER)
        return {"lesson_md": clean_lesson(lesson), "changes": changes.strip()}

    def finalize(state: LessonState) -> LessonState:
        attempts = attempts_of(state)
        if attempts[-1].evaluation.passed:
            best, status = attempts[-1], "passed"
        else:
            best = min(attempts, key=lambda a: (a.evaluation.critical_failures,
                                                len(a.evaluation.failed), -a.number))
            status = "needs_human_review"
        out_dir = s.outputs_dir / state["run_id"]
        out_dir.mkdir(parents=True, exist_ok=True)
        meta = {"run_id": state["run_id"], "topic": state["topic"], "status": status,
                "writer_model": deps.writer.name, "judge_model": deps.judge.name, "rules": state["rules"],
                "error": state.get("error")}
        lesson_header = "" if status == "passed" else (
            "> **Status: NEEDS HUMAN REVIEW** - this lesson did not pass every quality check. "
            "See rejection_log.md.\n\n")
        (out_dir / "lesson.md").write_text(lesson_header + best.lesson_md + "\n", encoding="utf-8")
        (out_dir / "rejection_log.md").write_text(rejection_log_md(meta, attempts, best.number), encoding="utf-8")
        for a in attempts:
            (out_dir / f"attempt_{a.number}.md").write_text(a.lesson_md + "\n", encoding="utf-8")
        (out_dir / "run.json").write_text(json.dumps(
            {**meta, "final_attempt": best.number, "plan": state.get("plan"),
             "attempts": [a.model_dump() for a in attempts]}, indent=2, ensure_ascii=False), encoding="utf-8")
        latest = s.outputs_dir / "latest"
        shutil.rmtree(latest, ignore_errors=True)
        shutil.copytree(out_dir, latest)
        log(f"Final: {status} (attempt {best.number}) -> {out_dir}")
        return {"status": status, "final_attempt": best.number, "output_dir": str(out_dir)}

    def persist(state: LessonState) -> LessonState:
        if deps.memory:
            deps.memory.finish_run(state["run_id"], state["status"], attempts_of(state))
            deps.memory.mark_rules_applied(state.get("rule_ids", []))
            log("Memory: run, attempts and check results saved")
        return {"status": state["status"]}

    def reflect_node(state: LessonState) -> LessonState:
        if not deps.memory:
            return {"reflection": {"skipped_reason": "memory disabled"}}
        report = reflect(deps.memory, deps.reflector, state["run_id"],
                         min_runs=s.reflection_min_runs, max_active_rules=s.max_active_rules)
        if report.skipped_reason:
            log(f"Reflection: skipped ({report.skipped_reason})")
        for r in report.new_rules:
            log(f"Reflection: learned new rule {r}")
        for p in report.new_proposals:
            log(f"Reflection: rubric proposal awaiting human approval: {p}")
        return {"reflection": report.__dict__}

    g = StateGraph(LessonState)
    for name, fn in [("load_context", load_context), ("plan", plan), ("generate", generate),
                     ("evaluate", evaluate), ("revise", revise), ("finalize", finalize),
                     ("persist", persist), ("reflect", reflect_node)]:
        g.add_node(name, fn)
    g.add_edge(START, "load_context")
    g.add_edge("load_context", "plan")
    g.add_edge("plan", "generate")
    g.add_edge("generate", "evaluate")
    g.add_conditional_edges("evaluate", route, {"revise": "revise", "finalize": "finalize"})
    g.add_conditional_edges("revise", lambda st: "finalize" if st.get("error") else "evaluate",
                            {"evaluate": "evaluate", "finalize": "finalize"})
    g.add_edge("finalize", "persist")
    g.add_edge("persist", "reflect")
    g.add_edge("reflect", END)
    return g.compile()


def run_pipeline(topic: str, deps: Deps, run_id: str | None = None) -> LessonState:
    app = build_graph(deps)
    return app.invoke({"run_id": run_id or new_run_id(), "topic": topic})
