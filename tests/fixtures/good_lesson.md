# Introduction to RAG: How AI Finds the Right Answer

## Let's Start With a Story

Meet Priya. She is in Class 12 in Pune. Her board exam is next week. She asks an AI chatbot a simple question: "What is the passing mark in my school's new exam rules?"

The chatbot gives a confident answer. But the answer is wrong. The chatbot has never seen her school's rule book. So it guessed.

Now imagine a better chatbot. First, it opens the school rule book. It finds the right page. Then it reads that page and answers. This time the answer is correct.

That better chatbot uses an idea called RAG. In this lesson, you will learn what RAG is, why it matters, and how it works, step by step.

## What Is RAG?

First, let us understand two basic words.

AI means a computer program that can do tasks that need human-like thinking. For example, it can answer questions or write text.

An LLM is a large language model. It is a kind of AI that has read a huge amount of text. Because of this reading, it can understand questions and write answers. ChatGPT and Gemini use LLMs.

An LLM has three big problems.

- **Old knowledge.** An LLM learns from text collected up to a certain date. This date is called the knowledge cutoff. After this date, it knows nothing new.
- **No private knowledge.** It has never read your school rules or your company's files.
- **Made-up answers.** Sometimes it writes an answer that sounds right but is false. This is called a hallucination.

RAG helps with these problems. RAG stands for Retrieval-Augmented Generation. Let us break the name into three parts.

- **Retrieval** means finding and bringing back useful information. The system searches your documents for the right pages.
- **Augmented** means "added to". The found information is added to the question.
- **Generation** means writing. The LLM writes the answer.

So RAG means: first find the right information, then give it to the LLM with the question, then let the LLM write the answer.

Think of an open-book exam. In a closed-book exam, you answer only from memory. In an open-book exam, you first find the right page in your textbook. Then you write your answer using that page. RAG gives the LLM an open-book exam. The LLM is the student. Your documents are the textbook.

## Why Does RAG Matter?

RAG is one of the most useful ideas in AI today. Here is why.

1. **Fresh information.** You can give the LLM new documents at any time. So it can answer about recent things.
2. **Private information.** A company can connect its own files. Then the chatbot can answer questions about that company.
3. **Fewer made-up answers.** The LLM reads real facts before it answers. So it makes fewer mistakes. But it can still make some mistakes.
4. **Answers you can check.** The system can show which document it used. You can open that document and check the answer.
5. **No retraining needed.** RAG does not change the LLM itself. The numbers inside the model, called model weights, stay the same. To update knowledge, you just add or change documents.

Many companies use RAG. Banks use it for customer help chatbots. Companies use it so workers can ask questions about office rules. Students use "chat with your PDF" apps, which also use RAG.

## How Does RAG Work? (Step by Step)

RAG has one preparation step and three question steps.

**Step 0: Prepare the documents.** This happens before anyone asks a question.

First, the system collects documents, like PDFs or web pages. Next, it cuts them into small pieces. Each piece is called a chunk. A chunk may be one short paragraph.

Then each chunk is turned into an embedding. An embedding is a list of numbers that captures the meaning of the text. Texts with similar meaning get similar numbers. For example, "exam result" and "board marks" get close numbers, even though the words are different.

Finally, all chunks and their embeddings are saved in a vector database. A vector database is a special store that can quickly find chunks with similar meaning.

**Step 1: Retrieve.** A user asks a question. The question is also turned into an embedding. Then the system looks for chunks whose numbers are closest to the question's numbers. This is called similarity search. It picks the top few chunks, for example three.

**Step 2: Augment.** The system builds a prompt. A prompt is the message given to the LLM. It puts the chosen chunks and the question together. It also adds an instruction, like "Answer using only this information."

**Step 3: Generate.** The LLM reads the prompt. It writes an answer based on the chunks. It can also say which document the answer came from.

Remember one thing. The LLM does not search the documents itself. A separate search part, called the retriever, finds the chunks. The LLM only reads what it is given.

## A Complete Example

Let us follow Priya's question through every step.

**Step 0: Prepare.** The school's rule book has 40 pages. The system cuts it into 200 chunks. Here are two of them:

- Chunk 57: "From 2026, students need 33 marks out of 100 to pass each subject."
- Chunk 112: "The school canteen is open from 8 AM to 2 PM."

Each chunk is turned into an embedding and saved in the vector database.

**Step 1: Retrieve.** Priya asks: "What is the passing mark in the new exam rules?" Her question becomes an embedding. The system compares it with all 200 chunks. Chunk 57 has the closest meaning, so it is picked. Chunk 112 is about the canteen, so it is not picked.

**Step 2: Augment.** The system builds this prompt:

> Answer the question using only the information below.
> Information: "From 2026, students need 33 marks out of 100 to pass each subject."
> Question: What is the passing mark in the new exam rules?

**Step 3: Generate.** The LLM reads the prompt and writes: "You need 33 marks out of 100 to pass each subject. Source: School rule book, chunk 57."

Priya gets a correct answer, and she can check the source.

But notice one limit. If the system had picked the wrong chunk, the answer could be wrong. RAG is only as good as the information it finds.

## Quick Recap

- An LLM has old knowledge, no private knowledge, and sometimes makes up answers.
- RAG means Retrieval-Augmented Generation: find information, add it to the question, then write the answer.
- Preparation: documents are cut into chunks, turned into embeddings, and saved in a vector database.
- Retrieve: find the chunks with the closest meaning to the question.
- Augment: put the chunks and the question into one prompt.
- Generate: the LLM writes the answer and can show its source.
- RAG does not retrain the model. To update knowledge, update the documents.
- If retrieval finds the wrong chunks, the answer can still be wrong.

## Check Your Understanding (Quiz)

1. What does the "R" in RAG stand for?
   A) Reading  B) Retrieval  C) Robot  D) Repeat
2. What is an embedding?
   A) A list of numbers that captures meaning  B) A type of exam  C) A web page  D) A password
3. How do you update what a RAG system knows?
   A) Retrain the LLM  B) Buy a new computer  C) Add or change the documents  D) Ask more questions
4. Which part finds the chunks?
   A) The LLM  B) The retriever  C) The user  D) The prompt

**Answers:** 1-B, 2-A, 3-C, 4-B

## New Words (Glossary)

- **AI** (कृत्रिम बुद्धि): A computer program that can do tasks that need human-like thinking.
- **LLM (Large Language Model)** (बड़ा भाषा मॉडल): An AI that has read a huge amount of text and can write answers.
- **RAG (Retrieval-Augmented Generation)** (खोजकर जवाब बनाना): First find the right information, then let the LLM write the answer.
- **Retrieval / Retriever** (खोजकर निकालना): Finding and bringing back useful information; the retriever is the part that does it.
- **Prompt** (निर्देश / सवाल): The message or question you give to the AI.
- **Chunk** (टुकड़ा): A small piece of a document.
- **Embedding** (अर्थ को अंकों में बदलना): A list of numbers that captures the meaning of a text.
- **Vector database** (अंकों वाला डेटाबेस): A store that can quickly find chunks with similar meaning.
- **Similarity search** (मिलती-जुलती चीज़ की खोज): Finding the chunks whose meaning is closest to the question.
- **Hallucination** (मनगढ़ंत जवाब): When an AI gives an answer that sounds right but is false.
- **Knowledge cutoff** (ज्ञान की आख़िरी तारीख): The date after which an LLM has no new knowledge.
- **Model weights** (मॉडल के अंदर के अंक): The numbers inside an AI model that it learned during training.
