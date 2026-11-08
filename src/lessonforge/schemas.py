from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CheckResult(BaseModel):
    id: str
    name: str
    dimension: str
    method: Literal["code", "llm"]
    severity: Literal["critical", "major"] = "major"
    passed: bool
    reason: str = ""
    evidence: str = ""
    fix: str = ""
    evidence_verified: bool | None = None


class Evaluation(BaseModel):
    attempt: int
    results: list[CheckResult]

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results)

    @property
    def failed(self) -> list[CheckResult]:
        return [r for r in self.results if not r.passed]

    @property
    def critical_failures(self) -> int:
        return sum(1 for r in self.failed if r.severity == "critical")


class Attempt(BaseModel):
    number: int
    lesson_md: str
    evaluation: Evaluation
    changes: str = ""
    injected_errors: list[str] = Field(default_factory=list)


class LessonPlan(BaseModel):
    learning_objectives: list[str]
    analogy: str
    worked_example: str
    key_points: list[str] = Field(default_factory=list)


class JudgeVerdict(BaseModel):
    id: str
    passed: bool
    evidence: str = ""
    reason: str = ""
    fix: str = ""


class JudgeResponse(BaseModel):
    verdicts: list[JudgeVerdict]


class LearnedRule(BaseModel):
    source_check: str
    rule: str


class RubricProposal(BaseModel):
    criterion: str
    rationale: str


class ReflectionOutput(BaseModel):
    rules: list[LearnedRule] = Field(default_factory=list)
    rubric_proposals: list[RubricProposal] = Field(default_factory=list)
