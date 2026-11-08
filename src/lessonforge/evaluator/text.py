"""Markdown -> plain prose helpers used by the code checks."""
from __future__ import annotations

import re

from ..lesson_format import DEVANAGARI, split_sections

WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9'\u2019-]*")
_BULLET = re.compile(r"^\s*(?:[-*+>]|\d+[.)]|[A-D][.)])\s+")
_SENT_SPLIT = re.compile(r"(?<=[.!?])[\"'\u201d\u2019)]*\s+")


def strip_markdown(md: str) -> str:
    text = re.sub(r"```.*?```", " ", md, flags=re.DOTALL)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"^#{1,6}\s.*$", " ", text, flags=re.MULTILINE)
    text = re.sub(r"(\*\*|__|\*|_)(?=\S)(.+?)(?<=\S)\1", r"\2", text)
    text = text.replace("|", " ")
    text = re.sub(r"^\s*[-=]{3,}\s*$", " ", text, flags=re.MULTILINE)
    return text


def remove_devanagari(text: str) -> str:
    text = re.sub(r"[\u0900-\u097F]+", " ", text)
    text = re.sub(r"\(\s*[/,\s]*\)", " ", text)
    return text


def body_markdown(lesson_md: str) -> str:
    """Everything except the glossary (the glossary is a reference list, not prose)."""
    sections = split_sections(lesson_md)
    return "\n\n".join(v for k, v in sections.items() if k != "glossary")


def sentences(md: str) -> list[str]:
    plain = remove_devanagari(strip_markdown(md))
    out: list[str] = []
    for line in plain.splitlines():
        line = _BULLET.sub("", line).strip()
        if not line:
            continue
        for s in _SENT_SPLIT.split(line):
            s = s.strip()
            if WORD.search(s):
                out.append(s)
    return out


def words(text: str) -> list[str]:
    return WORD.findall(text)


def has_devanagari(text: str) -> bool:
    return bool(DEVANAGARI.search(text))
