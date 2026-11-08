"""Deliberate error injection, used to prove the evaluator catches real problems.

Each corruption targets specific checks:
- factual   -> A1 / A2 (states the #1 RAG misconception: it retrains the model)
- jargon    -> J1 / J2 (dense, undefined technical terms)
- long      -> L2 / L1 (one 50-word sentence)
- structure -> S1 (deletes the "why it matters" section)
"""
from __future__ import annotations

import re

from .lesson_format import H2, classify_heading

CORRUPTIONS: dict[str, tuple[str, str]] = {
    "factual": ("what", (
        "The most important thing to know is that RAG works by retraining the AI model on your "
        "documents, so the new facts are stored permanently inside the model's weights and it "
        "never makes mistakes again."
    )),
    "jargon": ("how", (
        "Internally, the retriever runs approximate nearest-neighbour search over an HNSW graph, "
        "ranking dense embeddings by cosine similarity before BM25 re-ranking."
    )),
    "long": ("why", (
        "Because companies, schools, hospitals and government offices all have huge amounts of "
        "private and constantly changing information that no general model could ever have seen "
        "during its training, connecting a retrieval system to the model allows it to answer "
        "detailed questions about that information in a way that would otherwise be completely "
        "impossible for it."
    )),
}

ALL = [*CORRUPTIONS.keys(), "structure"]
DEFAULT = list(CORRUPTIONS.keys())


def _section_span(md: str, key: str) -> tuple[int, int] | None:
    matches = list(H2.finditer(md))
    for i, m in enumerate(matches):
        if classify_heading(m.group(1)) == key:
            end = matches[i + 1].start() if i + 1 < len(matches) else len(md)
            return m.end(), end
    return None


def _insert_after_first_paragraph(md: str, key: str, sentence: str) -> str:
    span = _section_span(md, key)
    if not span:
        return md + f"\n\n{sentence}\n"
    start, end = span
    body = md[start:end]
    para_end = re.search(r"\S.*?(\n\s*\n|\Z)", body, re.DOTALL)
    cut = start + (para_end.end() if para_end else 0)
    return md[:cut].rstrip() + f" {sentence}\n\n" + md[cut:].lstrip("\n")


def inject_errors(md: str, kinds: list[str] | None = None) -> tuple[str, list[str]]:
    kinds = kinds or DEFAULT
    applied = []
    for kind in kinds:
        if kind == "structure":
            span = _section_span(md, "why")
            if span:
                heading_start = md.rfind("\n##", 0, span[0])
                md = md[: max(heading_start, 0)] + md[span[1]:]
                applied.append(kind)
        elif kind in CORRUPTIONS:
            key, sentence = CORRUPTIONS[kind]
            md = _insert_after_first_paragraph(md, key, sentence)
            applied.append(kind)
        else:
            raise ValueError(f"Unknown error kind '{kind}'. Choose from: {', '.join(ALL)}")
    return md, applied
