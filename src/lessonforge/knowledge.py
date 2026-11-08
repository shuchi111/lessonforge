"""Loads the topic pack (ground truth), jargon list and rubric from data/."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .config import DATA_DIR


@dataclass
class TopicPack:
    title: str
    short_name: str
    key_points: list[dict[str, str]]
    misconceptions: list[str]
    fact_sheet: str
    grounded: bool = True

    def key_points_text(self) -> str:
        return "\n".join(f"- {kp['id']}: {kp['text']}" for kp in self.key_points)

    def misconceptions_text(self) -> str:
        return "\n".join(f"- {m}" for m in self.misconceptions)

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TopicPack":
        return cls(**d)


@dataclass
class JargonTerm:
    term: str
    patterns: list[re.Pattern]
    raw: list[str] = field(default_factory=list)

    def found_in(self, text: str) -> bool:
        return any(p.search(text) for p in self.patterns)


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", s.lower()).strip()


def find_topic_pack(topic: str, data_dir: Path = DATA_DIR) -> TopicPack | None:
    """Match the requested topic against each pack's title and aliases."""
    wanted = _norm(topic)
    for pack_dir in sorted((data_dir / "topics").glob("*")):
        meta_file = pack_dir / "topic.yaml"
        if not meta_file.exists():
            continue
        meta = yaml.safe_load(meta_file.read_text(encoding="utf-8"))
        names = [meta["title"], meta.get("short_name", ""), *meta.get("aliases", [])]
        if any(_norm(n) and re.search(rf"\b{re.escape(_norm(n))}\b", wanted) for n in names):
            fact = pack_dir / "fact_sheet.md"
            return TopicPack(
                title=meta["title"],
                short_name=meta.get("short_name", meta["title"]),
                key_points=meta.get("key_points", []),
                misconceptions=meta.get("misconceptions", []),
                fact_sheet=fact.read_text(encoding="utf-8") if fact.exists() else "",
            )
    return None


def load_jargon(data_dir: Path = DATA_DIR) -> list[JargonTerm]:
    raw = yaml.safe_load((data_dir / "jargon.yaml").read_text(encoding="utf-8"))
    terms = []
    for t in raw["terms"]:
        flags = 0 if t.get("case_sensitive") else re.IGNORECASE
        terms.append(JargonTerm(t["term"], [re.compile(p, flags) for p in t["patterns"]], t["patterns"]))
    return terms


def load_rubric(data_dir: Path = DATA_DIR) -> list[dict[str, Any]]:
    return yaml.safe_load((data_dir / "rubric.yaml").read_text(encoding="utf-8"))["checks"]
