[中文](README.zh.md) | **English**

# Minimal RAG Template

A complete, runnable RAG pipeline in ~130 lines. No external vector database — uses in-memory storage. Start querying your documents in under 5 minutes.

## What's included

```
minimal-rag/
├── main.py          # Complete RAG pipeline
├── requirements.txt
├── .env.example
└── docs/
    └── example.md  # Sample document to test with
```

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your API keys
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY and OPENAI_API_KEY

# 3. Add your documents to docs/ (.txt or .md files)

# 4. Run
python main.py
```

## How it works

```
docs/*.md / *.txt
    → chunk (500 chars, 50 overlap)
    → embed (OpenAI text-embedding-3-small)
    → store in memory (numpy cosine similarity)

query
    → embed query
    → find top-3 chunks by cosine similarity
    → Claude Haiku generates answer with citations
```

## Upgrade path

When you outgrow this template:

| Need | Next step |
|------|-----------|
| > 100k chunks | Switch to Qdrant (`pip install qdrant-client`) |
| Better recall | Add BM25 hybrid search |
| Faster retrieval | Add HNSW index |
| Better quality | Add a reranker (`cross-encoder/ms-marco-MiniLM-L-12-v2`) |

See [`build/rag/README.md`](../../build/rag/README.md) for the production-grade version.

---

*[中文版 (Chinese)](README.zh.md)*
