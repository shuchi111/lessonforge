# Rejection Log: Introduction to RAG

- **Run ID:** `20261108-093039-761a`
- **Result:** PASSED on attempt 3 of 3
- **Writer model:** `qwen/qwen3.8-27b` | **Judge model:** `openai/gpt-oss-120b`
- **Rubric:** 16 hard pass/fail checks (no partial credit)
- **Learned rules applied from memory:** 0

## Summary

| Attempt | Result | Checks passed | Failed checks |
|---|---|---|---|
| 1 | FAIL | 14/16 | J1, C1 |
| 2 | FAIL | 15/16 | L3 |
| 3 | PASS | 16/16 | - |

## Attempt 1: FAILED

| Check | Method | Why it failed | Evidence | Fix requested |
|---|---|---|---|---|
| **J1** Every technical term used is in the glossary | code | 3 technical term(s) used but not in the glossary. | AI, LLM, RAG | For each of these terms, either remove it or explain it in simple words where it is first used AND add a glossary entry: AI, LLM, RAG |
| **C1** Covers all key points | llm | The lesson does not mention any real‑world use cases like customer‑support chatbots or PDF chat tools, so key point 10 is missing. | MISSING: KP10 real-world uses, e.g. customer-support chatbots or 'chat with your PDF' tools | Add a brief paragraph describing at least one Indian‑relevant real‑world use case, such as a chatbot that answers queries from a school’s handbook or a ‘chat with your PDF’ tool for exam notes. |

## Attempt 2: FAILED

**Check changes vs attempt 1:** fixed: C1, J1; newly broken: L3; still failing: -

**What the writer changed on this retry:**

- Added glossary entries for **AI**, **LLM**, and **RAG** to fix check [J1].
- Ensured every technical term used in the text is now present in the glossary.
- Added a paragraph in "Why Does RAG Matter?" describing real-world uses like customer-support chatbots and "chat with your PDF" tools to fix check [C1].
- Included an Indian context (students preparing for competitive exams) in the new use-case paragraph.
- Verified that all other key points (KP1-KP9) remain covered as in the previous version.
- Maintained the required Markdown structure and word count limits.

| Check | Method | Why it failed | Evidence | Fix requested |
|---|---|---|---|---|
| **L3** Simple, friendly English for a non-native reader | llm | The lesson contains a technical word that a non‑native 12th‑grade reader is unlikely to know. | Uses the term "hallucination" which is an unexplained difficult word for a limited‑vocabulary learner. _(quote not found verbatim)_ | Replace "hallucination" with a simpler phrase like "making up facts" and avoid other technical jargon without simple explanations. |

## Attempt 3: PASSED

**Check changes vs attempt 2:** fixed: L3; newly broken: -; still failing: -

**What the writer changed on this retry:**

- Replaced the term "hallucination" with "making up facts" in the story section to fix L3.
- Replaced "LLMs can hallucinate" with "LLMs can make up facts" in the Why section to fix L3.
- Replaced "They can hallucinate" with "They can make up facts" in the Recap section to fix L3.
- Updated the Glossary entry from "Hallucination" to "Making up facts" to fix L3.
- Corrected the Hindi translation for AI in the Glossary to use proper Devanagari script.
- Ensured all technical terms are explained simply before use to maintain L3 compliance.

All checks passed.

## Final scorecard (attempt 3)

| Check | Dimension | Method | Result | Reason |
|---|---|---|---|---|
| S1 Required sections in teaching order | coherent flow | code | PASS | All required sections are present, in order. |
| S2 Standalone length | covers key points | code | PASS | 1238 words (allowed 800-1800). |
| L1 Reading level at or below grade 8 | beginner-friendly language | code | PASS | Flesch-Kincaid grade 3.8 (max 8.0). |
| L2 Short sentences | beginner-friendly language | code | PASS | Average 6.7 words per sentence; none over 30. |
| J1 Every technical term used is in the glossary | no unexplained jargon | code | PASS | All 10 technical terms used are in the glossary. |
| G1 Glossary entries have a Hindi meaning | beginner-friendly language | code | PASS | 13 glossary entries, all with Hindi meanings. |
| Q1 Quiz has at least 3 questions and an answer key | coherent flow | code | PASS | 4 questions with an answer key. |
| A1 Factually accurate and grounded | accurate & grounded | llm | PASS | All factual statements about RAG, LLM limits, and the workflow align with the provided fact sheet. |
| A2 No misconceptions | accurate & grounded | llm | PASS | No statement or implication from the lesson matches any item in the MISCONCEPTIONS list. |
| J2 Jargon explained in simple words at first use | no unexplained jargon | llm | PASS | All technical terms are introduced with clear, simple definitions before further use. |
| L3 Simple, friendly English for a non-native reader | beginner-friendly language | llm | PASS | Language is simple, direct, and suitable for a non‑native learner with limited vocabulary. |
| C1 Covers all key points | covers key points | llm | PASS | The lesson covers each listed key point with explanations. |
| E1 Teaches by example | teaches by example | llm | PASS | Both an everyday analogy and a complete worked example with concrete data are present. |
| E2 Examples relatable to an Indian learner | teaches by example | llm | PASS | Analogies and examples are familiar to a young Indian learner. |
| F1 Coherent, standalone teaching flow | coherent flow | llm | PASS | The teaching flow is coherent, standalone, and builds concepts sequentially. |
| Q2 Quiz is correct and answerable from the lesson | coherent flow | llm | PASS | All quiz questions are answerable from the lesson and have correct answer keys. |
