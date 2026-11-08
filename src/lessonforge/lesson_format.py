"""The lesson's required shape, shared by the writer prompt and the code checks.

Keeping it in one place guarantees the generator is asked for exactly what the
evaluator verifies.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Section:
    key: str
    heading: str  # may contain {short}
    keywords: tuple[str, ...]


SECTIONS: tuple[Section, ...] = (
    Section("hook", "Let's Start With a Story", ("story", "start")),
    Section("what", "What Is {short}?", ("what is",)),
    Section("why", "Why Does {short} Matter?", ("why",)),
    Section("how", "How Does {short} Work? (Step by Step)", ("how does", "how it works", "step by step")),
    Section("example", "A Complete Example", ("example",)),
    Section("recap", "Quick Recap", ("recap", "summary")),
    Section("quiz", "Check Your Understanding (Quiz)", ("quiz", "check your understanding")),
    Section("glossary", "New Words (Glossary)", ("glossary", "new words")),
)

GLOSSARY_LINE = re.compile(r"^\s*[-*]\s*\*\*(?P<term>.+?)\*\*\s*\((?P<hindi>[^)]*)\)\s*[:\u2014\u2013-]\s*(?P<meaning>.+)$")
DEVANAGARI = re.compile(r"[\u0900-\u097F]")
H2 = re.compile(r"^##\s+(.+?)\s*#*\s*$", re.MULTILINE)


def headings_for(short: str) -> list[str]:
    return [s.heading.format(short=short) for s in SECTIONS]


def classify_heading(heading: str) -> str | None:
    h = heading.lower()
    for section in SECTIONS:
        if any(k in h for k in section.keywords):
            return section.key
    return None


def split_sections(lesson_md: str) -> dict[str, str]:
    """Map section key -> body text. Unknown headings are kept under their raw text."""
    parts: dict[str, str] = {}
    matches = list(H2.finditer(lesson_md))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(lesson_md)
        key = classify_heading(m.group(1)) or m.group(1)
        parts.setdefault(key, lesson_md[m.end():end].strip())
    return parts


def section_order(lesson_md: str) -> list[str]:
    return [classify_heading(m.group(1)) or f"?{m.group(1)}" for m in H2.finditer(lesson_md)]


def format_spec(short: str) -> str:
    heads = "\n".join(f"## {h}" for h in headings_for(short))
    return f"""Use EXACTLY this Markdown structure, with these headings in this order:

# <lesson title>
{heads}

Glossary format - one bullet per term, with the Hindi meaning in Devanagari inside brackets:
- **Term** (हिंदी अर्थ): one short, simple English sentence.
Example:
- **Prompt** (निर्देश / सवाल): The message or question you give to the AI.

Quiz format - at least 3 numbered multiple-choice questions, then an answer key line:
1. Question text?
   A) option  B) option  C) option  D) option
**Answers:** 1-B, 2-A, 3-D"""
