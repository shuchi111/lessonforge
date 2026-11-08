from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

from ..config import DATA_DIR
from ..knowledge import TopicPack, load_jargon, load_rubric
from ..llm import LLM
from ..schemas import CheckResult, Evaluation
from .deterministic import CODE_CHECKS, CheckContext
from .judges import run_judge, verify_evidence


class Evaluator:
    """Runs the full rubric: code checks first (cheap), then grouped LLM judges."""

    def __init__(
        self,
        judge: LLM | None,
        topic: TopicPack,
        *,
        data_dir: Path = DATA_DIR,
        extra_checks: list[dict[str, Any]] | None = None,
        log: Callable[[str], None] = lambda _: None,
    ):
        self.judge = judge
        self.topic = topic
        self.jargon = load_jargon(data_dir)
        self.rubric = load_rubric(data_dir) + list(extra_checks or [])
        self.log = log

    def _result(self, meta: dict[str, Any], passed: bool, reason: str, evidence: str, fix: str,
                verified: bool | None = None) -> CheckResult:
        return CheckResult(
            id=meta["id"], name=meta["name"], dimension=meta.get("dimension", "custom"),
            method=meta["method"], severity=meta.get("severity", "major"), passed=passed,
            reason=reason, evidence=evidence, fix="" if passed else fix, evidence_verified=verified,
        )

    def evaluate(self, lesson_md: str, attempt: int = 1, *, code_only: bool = False) -> Evaluation:
        results: list[CheckResult] = []
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)

        for meta in self.rubric:
            if meta["method"] == "code":
                fn = CODE_CHECKS[meta["id"]]
                ctx = CheckContext(self.topic, self.jargon, meta.get("params", {}))
                results.append(self._result(meta, *fn(lesson_md, ctx)))
            else:
                groups[meta.get("judge", "pedagogy")].append(meta)

        if not code_only and self.judge is not None:
            for group, checks in groups.items():
                self.log(f"judge[{group}] reviewing {', '.join(c['id'] for c in checks)}")
                verdicts = run_judge(self.judge, group, checks, lesson_md, self.topic)
                for meta in checks:
                    v = verdicts[meta["id"]]
                    results.append(self._result(
                        meta, v.passed, v.reason, v.evidence, v.fix,
                        verify_evidence(v.evidence, lesson_md),
                    ))

        order = {m["id"]: i for i, m in enumerate(self.rubric)}
        results.sort(key=lambda r: order.get(r.id, 999))
        return Evaluation(attempt=attempt, results=results)
