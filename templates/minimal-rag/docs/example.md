# Example Document

This is a sample document for testing the RAG pipeline.

## About RAG

Retrieval-Augmented Generation (RAG) is a technique that combines document retrieval
with language model generation. Instead of relying solely on the model's training data,
RAG retrieves relevant documents at query time and injects them into the context.

## Key Components

1. **Chunking**: Split documents into smaller pieces that fit in the context window
2. **Embedding**: Convert text chunks into vector representations
3. **Retrieval**: Find the most relevant chunks for a given query
4. **Generation**: Use the retrieved chunks as context for the language model

## When to Use RAG

- You have domain-specific documents that the model hasn't seen
- You need up-to-date information beyond the model's training cutoff
- You need citations and verifiable sources in the output
- You want to reduce hallucinations on factual questions
