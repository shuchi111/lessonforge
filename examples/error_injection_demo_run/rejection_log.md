# Rejection Log: Introduction to RAG

- **Run ID:** `20261108-095813-680d`
- **Result:** DID NOT PASS after 3 attempts - best attempt (2) sent for human review
- **Writer model:** `qwen/qwen3.8-27b` | **Judge model:** `openai/gpt-oss-120b`
- **Rubric:** 16 hard pass/fail checks (no partial credit)
- **Learned rules applied from memory:** 1

## Summary

| Attempt | Result | Checks passed | Failed checks |
|---|---|---|---|
| 1 | FAIL | 9/16 | L2, J1, A1, A2, J2, L3, C1 |
| 2 | FAIL | 14/16 | J1, E1 |
| 3 | FAIL | 15/16 | J2 |

## Learned rules used in this run (from memory)

- Before using any technical term, ensure it is explicitly defined in the glossary section of the lesson.

## Attempt 1: FAILED

> Deliberately injected errors (demo): **factual, jargon, long**

| Check | Method | Why it failed | Evidence | Fix requested |
|---|---|---|---|---|
| **L2** Short sentences | code | 2 sentence(s) longer than 30 words | "The most important thing to know is that RAG works by retraining the AI model on your documents, so the new facts are stored permanently inside the model's weights and it never makes mistakes again."; "Because companie… | Split every sentence longer than 30 words into two or three short ones. |
| **J1** Every technical term used is in the glossary | code | 11 technical term(s) used but not in the glossary. | AI, LLM, RAG, model weights, embedding model, cosine similarity, nearest neighbour, HNSW, BM25, dense retrieval, index | For each of these terms, either remove it or explain it in simple words where it is first used AND add a glossary entry: AI, LLM, RAG, model weights, embedding model, cosine similarity, nearest neighbour, HNSW, BM25, de… |
| **A1** Factually accurate and grounded | llm | The lesson claims RAG retrains the model and stores facts permanently, which contradicts the fact sheet that states RAG does not change the LLM's weights. | RAG works by retraining the AI model on your documents, so the new facts are stored permanently inside the model's weights and it never makes mistakes again. | Remove or correct the statement about retraining and permanent storage; explain that RAG only retrieves external information at query time without altering the model. |
| **A2** No misconceptions | llm | This directly introduces a misconception that RAG retrains or fine‑tunes the model, which is listed in the prohibited misconceptions. | RAG works by retraining the AI model on your documents, so the new facts are stored permanently inside the model's weights and it never makes mistakes again. | Delete the misconception and replace it with the correct description that RAG adds retrieved chunks to the prompt without modifying the model. |
| **J2** Jargon explained in simple words at first use | llm | Technical terms (HNSW graph, cosine similarity, BM25) are used without a simple explanation at first use. | ...approximate nearest‑neighbour search over an HNSW graph, ranking dense embeddings by cosine similarity before BM25 re‑ranking... | Add a brief plain‑English explanation for each term the first time it appears, e.g., "HNSW graph: a way computers organize data for fast searching". |
| **L3** Simple, friendly English for a non-native reader | llm | The lesson includes advanced technical phrases that a learner with limited English vocabulary would not understand and are not simplified. | ...approximate nearest‑neighbour search over an HNSW graph, ranking dense embeddings by cosine similarity before BM25 re‑ranking... | Replace or explain such phrases in simple everyday language, e.g., "a quick search that finds the most similar pieces of text". |
| **C1** Covers all key points | llm | The lesson incorrectly states that RAG retrains the model, missing the correct explanation that RAG does not change or retrain the model. | RAG works by retraining the AI model on your documents, so the new facts are stored permanently inside the model's weights and it never makes mistakes again. | Replace the retraining claim with a correct description: RAG keeps the model unchanged and simply retrieves relevant chunks to augment the prompt. |

## Attempt 2: FAILED

**Check changes vs attempt 1:** fixed: A1, A2, C1, J2, L2, L3; newly broken: E1; still failing: J1

**What the writer changed on this retry:**

- Removed the false claim that RAG retrains the model or changes weights, fixing [A1], [A2], and [C1].
- Replaced the long, complex sentence about companies and private info with short, simple sentences, fixing [L2].
- Removed unexplained technical terms like HNSW, BM25, and cosine similarity, fixing [L3] and [J2].
- Added missing technical terms (AI, LLM, RAG, Embedding Model) to the glossary, fixing [J1].
- Ensured all sentences are under 25 words to strictly meet the short sentence requirement, fixing [L2].
- Clarified that RAG adds chunks to the prompt without modifying the model, ensuring factual accuracy.

| Check | Method | Why it failed | Evidence | Fix requested |
|---|---|---|---|---|
| **J1** Every technical term used is in the glossary | code | 2 technical term(s) used but not in the glossary. | model weights, index | For each of these terms, either remove it or explain it in simple words where it is first used AND add a glossary entry: model weights, index |
| **E1** Teaches by example | llm | The worked example is incomplete; it lacks a concrete full prompt and detailed retrieval output. | The example describes the question and chunk but does not show the exact final prompt text or list all retrieved chunks explicitly. _(quote not found verbatim)_ | Provide a complete worked example showing the exact prompt sent to the LLM (question + retrieved chunk(s)) and list the retrieved chunks with their content. |

## Attempt 3: FAILED

**Check changes vs attempt 2:** fixed: E1, J1; newly broken: J2; still failing: -

**What the writer changed on this retry:**

*   Removed the phrase "model's internal weights" from the "What Is RAG?" section and replaced it with "model's internal settings" to avoid introducing a technical term not in the glossary, fixing check J1.
*   Changed "preparation or indexing" to "preparation or the indexing process" in the "How Does RAG Work?" section to ensure the term "indexing" is treated as a process rather than a standalone technical noun requiring definition, or alternatively, I added "Index" to the glossary to satisfy the requirement for any technical term used. I chose to add "Index" to the glossary to be safe.
*   Added the glossary entry for **Index** (सूची) to ensure all technical terms used in the text are defined, fixing check J1.
*   Expanded the "A Complete Example" section to explicitly list the "Retrieved Chunk" and show the exact text of the "Final Prompt" sent to the LLM, fixing check E1.
*   Ensured the final prompt includes the context and the question clearly, providing the concrete data required by the review.

| Check | Method | Why it failed | Evidence | Fix requested |
|---|---|---|---|---|
| **J2** Jargon explained in simple words at first use | llm | The acronym RAG is used in the title before any explanation, violating the rule that jargon must be explained at first use in the lesson body. | # Introduction to RAG: How AI Finds the Right Answer | Introduce and define RAG before it appears in the title or move the definition to the very first sentence of the lesson. |

## Final scorecard (attempt 2)

| Check | Dimension | Method | Result | Reason |
|---|---|---|---|---|
| S1 Required sections in teaching order | coherent flow | code | PASS | All required sections are present, in order. |
| S2 Standalone length | covers key points | code | PASS | 1223 words (allowed 800-1800). |
| L1 Reading level at or below grade 8 | beginner-friendly language | code | PASS | Flesch-Kincaid grade 4.2 (max 8.0). |
| L2 Short sentences | beginner-friendly language | code | PASS | Average 7.0 words per sentence; none over 30. |
| J1 Every technical term used is in the glossary | no unexplained jargon | code | FAIL | 2 technical term(s) used but not in the glossary. |
| G1 Glossary entries have a Hindi meaning | beginner-friendly language | code | PASS | 14 glossary entries, all with Hindi meanings. |
| Q1 Quiz has at least 3 questions and an answer key | coherent flow | code | PASS | 3 questions with an answer key. |
| A1 Factually accurate and grounded | accurate & grounded | llm | PASS | All factual statements match the provided fact sheet and no invented facts are present. |
| A2 No misconceptions | accurate & grounded | llm | PASS | The lesson avoids all listed misconceptions and does not imply permanent storage or guaranteed correctness. |
| J2 Jargon explained in simple words at first use | no unexplained jargon | llm | PASS | All technical terms (RAG, Retrieval, Augmented, Generation, embedding, vector database, similarity search, prompt) are defined in simple language at their firs… |
| L3 Simple, friendly English for a non-native reader | beginner-friendly language | llm | PASS | The lesson avoids complex vocabulary, idioms, and culturally specific references, using simple, friendly English suitable for a non‑native reader. |
| C1 Covers all key points | covers key points | llm | PASS | The lesson covers each listed key point with explanations. |
| E1 Teaches by example | teaches by example | llm | FAIL | The worked example is incomplete; it lacks a concrete full prompt and detailed retrieval output. |
| E2 Examples relatable to an Indian learner | teaches by example | llm | PASS | Examples are based on school exams and common service interactions, which are relatable to Indian learners. |
| F1 Coherent, standalone teaching flow | coherent flow | llm | PASS | The teaching flow is coherent, standalone, and builds concepts in order. |
| Q2 Quiz is correct and answerable from the lesson | coherent flow | llm | PASS | All quiz items have a single correct answer and are covered by the lesson content. |
