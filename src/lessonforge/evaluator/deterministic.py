"""Deterministic checks: same input, same verdict, zero cost.

Each check returns (passed, reason, evidence, fix). The `fix` is concrete
(the exact sentences/terms to change), which makes the regenerate step targeted.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable

import textstat

from ..knowledge import JargonTerm, TopicPack
from ..lesson_format import GLOSSARY_LINE, SECTIONS, headings_for, section_order, split_sections
from .text import body_markdown, has_devanagari, sentences, strip_markdown, words

Outcome = tuple[bool, str, str, str]


@dataclass
class CheckContext:
    topic: TopicPack
    jargon: list[JargonTerm]
    params: dict[str, Any]


def _clip(items: list[str], n: int = 5) -> str:
    shown = items[:n]
    more = f" (+{len(items) - n} more)" if len(items) > n else ""
    return "; ".join(f'"{s}"' for s in shown) + more


def check_structure(md: str, ctx: CheckContext) -> Outcome:
    expected = [s.key for s in SECTIONS]
    order = [k for k in section_order(md) if k in expected]
    has_title = bool(re.search(r"^#\s+\S", md, re.MULTILINE))
    missing = [s.heading.format(short=ctx.topic.short_name) for s in SECTIONS if s.key not in order]
    duplicates = sorted({k for k in order if order.count(k) > 1})
    in_order = order == sorted(set(order), key=expected.index) and not duplicates
    problems = []
    if not has_title:
        problems.append("no '# Title' line")
    if missing:
        problems.append("missing sections: " + ", ".join(missing))
    if not in_order:
        problems.append(f"sections out of order or repeated: {order}")
    if not problems:
        return True, "All required sections are present, in order.", "", ""
    fix = "Use exactly these headings in this order: " + " | ".join(headings_for(ctx.topic.short_name))
    return False, "; ".join(problems), "", fix


def check_length(md: str, ctx: CheckContext) -> Outcome:
    lo, hi = ctx.params.get("min_words", 800), ctx.params.get("max_words", 1800)
    n = len(words(strip_markdown(body_markdown(md))))
    if lo <= n <= hi:
        return True, f"{n} words (allowed {lo}-{hi}).", "", ""
    if n < lo:
        return False, f"Too short: {n} words (minimum {lo}).", "", (
            f"Add about {lo - n + 100} words: explain each step of 'how it works' more, "
            "and make the worked example more detailed.")
    return False, f"Too long: {n} words (maximum {hi}).", "", (
        f"Cut about {n - hi + 100} words: remove repetition and side topics.")


def check_reading_level(md: str, ctx: CheckContext) -> Outcome:
    max_grade = ctx.params.get("max_grade", 8.0)
    sents = sentences(body_markdown(md))
    text = " ".join(s if s[-1] in ".!?" else s + "." for s in sents)
    grade = round(textstat.flesch_kincaid_grade(text), 1) if text else 0.0
    if grade <= max_grade:
        return True, f"Flesch-Kincaid grade {grade} (max {max_grade}).", "", ""
    jargon_words = {w.lower() for t in ctx.jargon for w in t.term.split()}
    hard = sorted(
        {w for w in words(text) if textstat.syllable_count(w) >= 4 and w.lower() not in jargon_words},
        key=lambda w: -textstat.syllable_count(w),
    )
    worst = sorted(sents, key=lambda s: -textstat.flesch_kincaid_grade(s))[:3]
    fix = "Use shorter, everyday words and split long sentences."
    if hard:
        fix += " Replace or explain these long words: " + ", ".join(hard[:12]) + "."
    return False, f"Flesch-Kincaid grade {grade} is above {max_grade}.", _clip(worst, 3), fix


def check_sentence_length(md: str, ctx: CheckContext) -> Outcome:
    max_avg = ctx.params.get("max_avg_words", 18)
    max_one = ctx.params.get("max_sentence_words", 30)
    sents = sentences(body_markdown(md))
    if not sents:
        return False, "No sentences found.", "", "Write the lesson as normal sentences."
    lengths = [len(words(s)) for s in sents]
    avg = round(sum(lengths) / len(lengths), 1)
    long_ones = [s for s, n in zip(sents, lengths) if n > max_one]
    if avg <= max_avg and not long_ones:
        return True, f"Average {avg} words per sentence; none over {max_one}.", "", ""
    reasons = []
    if avg > max_avg:
        reasons.append(f"average sentence length {avg} > {max_avg}")
    if long_ones:
        reasons.append(f"{len(long_ones)} sentence(s) longer than {max_one} words")
    fix = f"Split every sentence longer than {max_one} words into two or three short ones."
    return False, "; ".join(reasons), _clip(long_ones, 4), fix


def glossary_entries(md: str) -> tuple[list[dict[str, str]], list[str]]:
    """Returns (parsed entries, bullet lines that did not match the required format)."""
    gloss = split_sections(md).get("glossary", "")
    entries, bad = [], []
    for line in gloss.splitlines():
        if not re.match(r"^\s*[-*]\s+", line):
            continue
        m = GLOSSARY_LINE.match(line)
        if m:
            entries.append(m.groupdict())
        else:
            bad.append(line.strip())
    return entries, bad


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def check_jargon_in_glossary(md: str, ctx: CheckContext) -> Outcome:
    body = strip_markdown(body_markdown(md))
    entries, _ = glossary_entries(md)
    gloss_terms = [e["term"] for e in entries]
    used = [t for t in ctx.jargon if t.found_in(body)]
    missing = [
        t.term for t in used
        if not any(t.found_in(g) or _norm(t.term) == _norm(g) for g in gloss_terms)
    ]
    if not missing:
        return True, f"All {len(used)} technical terms used are in the glossary.", "", ""
    return False, f"{len(missing)} technical term(s) used but not in the glossary.", ", ".join(missing), (
        "For each of these terms, either remove it or explain it in simple words where it is "
        "first used AND add a glossary entry: " + ", ".join(missing))


def check_hindi_glossary(md: str, ctx: CheckContext) -> Outcome:
    min_entries = ctx.params.get("min_entries", 5)
    entries, bad = glossary_entries(md)
    no_hindi = [e["term"] for e in entries if not has_devanagari(e["hindi"])]
    problems = []
    if len(entries) < min_entries:
        problems.append(f"only {len(entries)} glossary entries in the required format (minimum {min_entries})")
    if bad:
        problems.append(f"{len(bad)} glossary line(s) not in the format '- **Term** (हिंदी): meaning'")
    if no_hindi:
        problems.append("entries without a Hindi (Devanagari) meaning: " + ", ".join(no_hindi))
    if not problems:
        return True, f"{len(entries)} glossary entries, all with Hindi meanings.", "", ""
    return False, "; ".join(problems), _clip(bad, 3), (
        "Write every glossary line exactly as: - **Term** (हिंदी अर्थ): simple English meaning.")


def check_quiz(md: str, ctx: CheckContext) -> Outcome:
    min_q = ctx.params.get("min_questions", 3)
    quiz = split_sections(md).get("quiz", "")
    questions = re.findall(r"^\s*(?:\*\*)?(?:Q)?\d+[.)]", quiz, re.MULTILINE)
    has_key = bool(re.search(r"answer", quiz, re.IGNORECASE))
    if len(questions) >= min_q and has_key:
        return True, f"{len(questions)} questions with an answer key.", "", ""
    problems = []
    if len(questions) < min_q:
        problems.append(f"{len(questions)} numbered questions (minimum {min_q})")
    if not has_key:
        problems.append("no answer key")
    return False, "; ".join(problems), "", (
        f"Add at least {min_q} numbered multiple-choice questions and a final line '**Answers:** 1-B, 2-A, ...'.")


CODE_CHECKS: dict[str, Callable[[str, CheckContext], Outcome]] = {
    "S1": check_structure,
    "S2": check_length,
    "L1": check_reading_level,
    "L2": check_sentence_length,
    "J1": check_jargon_in_glossary,
    "G1": check_hindi_glossary,
    "Q1": check_quiz,
}
