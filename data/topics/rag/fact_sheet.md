# RAG fact sheet (ground truth for the accuracy judge)

## Background: LLMs
- A Large Language Model (LLM) is an AI model trained on a very large amount of text to predict and generate text. Examples: GPT-4, Llama, Gemini, Claude.
- An LLM's knowledge comes from its training data, which stops at a "knowledge cutoff" date. It does not know events after that date.
- An LLM does not know private information it was never trained on (a company's internal documents, a school's rules, your personal notes).
- LLMs can "hallucinate": produce fluent, confident answers that are false or made up.
- An LLM can only read a limited amount of text at one time. This limit is called the context window. This is one reason RAG sends only the most relevant pieces, not the whole library.

## What RAG is
- RAG stands for Retrieval-Augmented Generation.
  - Retrieval: finding relevant information from an external knowledge source.
  - Augmented: adding that information to the prompt (the input given to the LLM).
  - Generation: the LLM writes (generates) the answer.
- The term was introduced in a 2020 research paper by Patrick Lewis and colleagues at Facebook AI Research (now Meta AI): "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks".
- A common analogy: an open-book exam. The student (LLM) is allowed to look up the right pages (retrieval) before writing the answer (generation).

## How RAG works
### Step 0 - Preparation (indexing), done before any question is asked
1. Collect documents (PDFs, web pages, manuals, notes).
2. Split them into small pieces called chunks (for example, a few sentences or a paragraph each).
3. Convert each chunk into an embedding: a list of numbers (a vector) that represents the meaning of the text. Texts with similar meaning get similar numbers. An embedding model does this conversion.
4. Store the chunks and their embeddings in a vector database (also called a vector store or vector index).

### Steps at question time
1. Retrieve: the user's question is converted into an embedding using the same embedding model. The system searches the vector database for the chunks whose embeddings are most similar to the question's embedding (similarity search, often using cosine similarity). It usually returns the top few (top-k) chunks, for example 3 to 5.
2. Augment: the retrieved chunks are inserted into the prompt together with the question and an instruction such as "Answer using only the information below."
3. Generate: the LLM reads the prompt and writes an answer based on the retrieved chunks. The system can also show which documents (sources) were used.

- The search is done by a retriever, which is a separate component, not by the LLM itself.
- Retrieval can also use keyword search (for example BM25) or a mix of keyword and meaning-based (semantic) search, called hybrid search.

## Why RAG matters
- Gives the LLM access to up-to-date and private information without retraining it.
- Reduces (does not eliminate) hallucinations, because the model is given relevant facts.
- Answers can include sources, so people can check them.
- Updating knowledge is cheap and fast: change or add documents and re-index them.
- Usually cheaper and faster than fine-tuning for adding factual knowledge.

## What RAG does NOT do
- RAG does not change the LLM's weights (its internal learned numbers). The model is not retrained or fine-tuned.
- The knowledge is not stored inside the model; it is given to the model fresh for each question.
- RAG does not guarantee correct answers.

## RAG vs fine-tuning
- Fine-tuning further trains the model on new examples, changing its weights. It is better for teaching a style, format or behaviour.
- RAG supplies facts at question time without changing the model. It is better for knowledge that changes often or is private.
- The two can be combined.

## Limitations
- "Garbage in, garbage out": if retrieval finds the wrong or outdated chunks, the answer can be wrong.
- Chunking choices matter: chunks that are too small lose context; too large may include irrelevant text.
- The LLM can still misread the retrieved text or add information that is not there.
- Adds extra steps, so it can be a little slower and costs more than a plain LLM call.

## Real-world uses
- Customer-support chatbots that answer from a company's manuals and policies.
- "Chat with your PDF/notes" tools.
- Company internal search assistants (HR policies, technical documentation).
- Assistants for law, medicine or banking that must answer from approved documents.
