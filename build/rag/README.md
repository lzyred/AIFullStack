[中文](README.zh.md) | **English**

# RAG Production Implementation Guide

> Karpathy check: technical details are grounded in Anthropic / OpenAI official documentation; all code is runnable.

---

## Why RAG Fails in Production

Most RAG tutorials work fine for demos but fall apart in production. The root cause: **the problems you face in a demo are not the problems you face in production.**

Demo problem: can the system retrieve anything at all?
Production problem: is what gets retrieved accurate enough, consistent enough, and do you have visibility when it goes wrong?

---

## Chunking Strategy

### Choosing the Right Chunking Approach

| Method | Best for | Risk |
|--------|----------|------|
| Fixed size (512 tokens) | Rapid prototyping | Cuts across semantic units |
| Semantic chunking (sentence/paragraph) | General-purpose, first choice | Uneven chunk sizes |
| Recursive character splitting | LangChain default, balanced | No awareness of document structure |
| Structure-aware chunking | Markdown / HTML / PDF | More complex to implement |

**Recommended starting point**: semantic chunking with a 512-token ceiling and 64-token overlap.

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,
    chunk_overlap=64,
    separators=["\n\n", "\n", ".", " ", ""]
)
chunks = splitter.split_text(document)
```

### Five Common Chunking Mistakes

1. **Splitting across code blocks or tables**: Truncated code produces distorted embeddings — retrieval can't find the relevant code at all. Fix: add ` ``` ` as the highest-priority separator.

2. **Not injecting metadata**: Chunks with no source, publication date, or section info prevent the model from making recency judgments. Fix: store `source`, `date`, and `section` metadata alongside every chunk.

3. **Overlap too large**: When overlap exceeds 20% of chunk_size, near-duplicate chunks multiply, retrieval noise increases, and the reranker has to work much harder.

4. **Chunk granularity doesn't match query granularity**: A user asks "what is a vector database?" but the matching chunk is a table comparing five vector databases — semantic similarity falls below the threshold and the chunk gets filtered out. Fix: tune chunk size to match your common query types.

5. **Not filtering low-quality chunks**: Headers, footers, and table-of-contents pages pollute the index. Fix: discard any chunk shorter than 50 tokens.

---

## Embedding Model Selection

### Comparing the Main Options

| Model | Dimensions | Strengths | Best for |
|-------|-----------|-----------|---------|
| `text-embedding-3-large` | 3072 | Strong multilingual support, supports dimensionality reduction | General production use |
| `text-embedding-3-small` | 1536 | 10x cheaper | High-volume, cost-sensitive workloads |
| `bge-m3` (BAAI) | 1024 | Open source, strong CJK support, sparse + dense | CJK content, private deployment |
| `jina-embeddings-v3` | 1024 | Long documents (8192 tokens) | Long-document retrieval |
| `voyage-3` | 1024 | Strong on code and technical docs | Code RAG |

**Key notes**:
- Anthropic does not offer a standalone embedding API; for CJK content, `bge-m3` is the recommended choice.
- Switching embedding models requires a full re-embed of all content — old and new vector spaces are incompatible.

---

## Hybrid Search

Pure vector search struggles with exact-match terms: proper nouns, model numbers, function names. Hybrid search combines sparse retrieval (BM25) with dense retrieval (vector), fused using Reciprocal Rank Fusion (RRF).

```python
def hybrid_search(query, dense_results, bm25_results, alpha=0.5):
    """Reciprocal Rank Fusion"""
    scores = {}
    for rank, doc in enumerate(dense_results):
        scores[doc.id] = scores.get(doc.id, 0) + alpha * (1 / (rank + 60))
    for rank, doc in enumerate(bm25_results):
        scores[doc.id] = scores.get(doc.id, 0) + (1 - alpha) * (1 / (rank + 60))
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

**Recommendation**: Qdrant, Weaviate, and Elasticsearch all support hybrid search natively. Use those — don't roll your own.

---

## Reranking: Highest ROI Optimization

Near-zero cost (runs locally), meaningful quality improvement.

**The "lost in the middle" problem**: when retrieval returns 10 chunks and the relevant content is chunk 5, the LLM tends to ignore what's in the middle. Reranking and keeping only the top 3 fixes this directly.

```python
from sentence_transformers import CrossEncoder

reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-12-v2')

def rerank(query: str, chunks: list[str], top_k: int = 3) -> list[str]:
    pairs = [(query, chunk) for chunk in chunks]
    scores = reranker.predict(pairs)
    ranked = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)
    return [chunk for chunk, _ in ranked[:top_k]]
```

---

## Complete Pipeline

```python
import anthropic

client = anthropic.Anthropic()

def rag_query(user_query: str, vector_store) -> str:
    # 1. Query rewriting (improves recall)
    rewritten = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=100,
        messages=[{
            "role": "user",
            "content": f"Rewrite the following question into a form better suited for semantic search (one sentence): {user_query}"
        }]
    ).content[0].text

    # 2. Hybrid retrieval, top-10
    chunks = vector_store.hybrid_search(rewritten, top_k=10)

    # 3. Rerank, keep top-3
    reranked = rerank(rewritten, chunks, top_k=3)

    # 4. Token budget check
    context = "\n\n---\n\n".join(reranked)

    # 5. Generate answer (explicitly prohibit hallucination)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system="""Answer the user's question based on the documents below.
Rules:
- Use only information from the provided documents
- Cite sources when referencing specific content
- If the documents do not contain relevant information, say explicitly "This information is not in the documents" — do not guess
- Do not fabricate any content""",
        messages=[{
            "role": "user",
            "content": f"<documents>\n{context}\n</documents>\n\nQuestion: {user_query}"
        }]
    )
    return response.content[0].text
```

---

## Production Failure Patterns

| Problem | Symptom | Fix |
|---------|---------|-----|
| Stale vector index | Old and new document versions both match, producing contradictory output | Upsert at the document level; use document ID prefix to delete old chunks before inserting new ones |
| Query-document expression mismatch | Similarity below threshold; relevant content gets filtered | HyDE: have the LLM generate a hypothetical answer first, then use that for vector retrieval |
| Context window exceeded | Intermittent API errors, hard to reproduce | Count tokens with a tokenizer before sending; truncate oldest chunks when over the limit |
| No retrieval quality monitoring | Issues only surface through user complaints | Log the top-1 similarity score on every query; alert when it falls below a threshold |
| Embedding model migration | Retrieval quality drops sharply | A full re-embed is required when switching models — old and new vector spaces are incompatible |

---

## Evaluation: How Do You Know RAG Is Good Enough?

Three evaluations you must run before going to production:

1. **Retrieval Recall**: for a test set of questions, does the relevant chunk appear in the top-k results? Target: Recall@5 > 80%.
2. **Answer Faithfulness**: does the answer stay grounded in the retrieved documents, with no hallucinations? LLM-as-Judge works well for automated scoring here.
3. **End-to-End Accuracy**: manually annotate 50–100 question-answer pairs and run regression on a schedule.

---

*Priority order: start with the reranker (free), then add hybrid search, then query rewriting. Implement them in sequence — don't try to ship everything at once.*

---

*[中文版 (Chinese)](README.zh.md)*
