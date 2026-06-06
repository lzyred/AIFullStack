[中文](README.zh.md) | **English**

# Case Study: Enterprise Knowledge Base Q&A System

> The real decision-making process from zero to production — including the mistakes.

---

## Background

**Scenario**: a 200-person SaaS company whose support team spent most of their day answering the same product questions on repeat. 80% of those questions had answers in the documentation, but agents had to manually search for them — averaging 5–10 minutes per answer.

**Goal**: use a RAG system to let support agents find accurate answers in under 30 seconds, eliminating repetitive search time.

**Starting data**:
- Documentation: 800 Markdown files, approximately 3M words total
- Daily question volume: ~200
- Support team size: 8 agents

---

## Phase 1: Technology Decisions (Week 1)

### Vector Database

**Decision**: pgvector, not Qdrant or Pinecone.

**Reasoning**:
- Team was already running PostgreSQL — zero additional infrastructure
- Document count was well under 1M vectors; pgvector performance was sufficient
- Reducing operational complexity took priority over optimal raw performance

**What we discovered later**: pgvector's IVFFlat index was slow for combined filter + vector search queries. Migrating to HNSW brought P95 latency down from 200ms to 40ms.

```sql
-- Final index configuration (HNSW, not IVFFlat)
CREATE INDEX ON documents USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

### Embedding Model

**Decision**: `text-embedding-3-small` (OpenAI), not `text-embedding-3-large`.

**Reasoning**: 10x cost difference; accuracy gap wasn't large enough to justify it upfront. Upgrade later if retrieval quality falls short.

**Actual result**: `small` retrieval accuracy was adequate for the document corpus. Only a handful of technical terms had poor recall — fixed with hybrid search.

---

## Phase 2: First Launch (Weeks 2–3)

### Architecture

```
User input
  → Vector retrieval (pgvector, top-10)
  → Claude Haiku 4.5 generates answer
  → Output (with source document links)
```

**Why not start with hybrid search and a reranker**: validate the core value first, optimize the details second. Let real failure cases from production drive the next optimization decision.

### First-Version Failure Analysis

Failure cases collected after 2 weeks in production:

| Failure type | Count | Root cause |
|--------------|-------|------------|
| Technical term recall failure | 15 | Pure vector search is weak on exact keyword matching |
| "Lost in the middle" | 8 | Relevant content was ranked 6th in top-10; model overlooked it |
| Outdated document version | 6 | Old docs weren't cleaned up; both old and new versions were hit |
| Answer too brief | 12 | Haiku underperformed on complex questions |

---

## Phase 3: Targeted Optimization (Weeks 4–6)

### Fix 1: Hybrid Search (resolves technical term recall)

```python
from qdrant_client import QdrantClient
from rank_bm25 import BM25Okapi

# Migrated to Qdrant for native hybrid search.
# pgvector hybrid search was too cumbersome to implement well.

def hybrid_search(query: str, top_k: int = 10) -> list[str]:
    # Dense vector retrieval
    dense_results = vector_db.search(
        collection_name="docs",
        query_vector=embed(query),
        limit=top_k
    )
    # BM25 keyword retrieval (via Qdrant sparse vectors)
    sparse_results = vector_db.search(
        collection_name="docs",
        query_sparse_vector=bm25_encode(query),
        limit=top_k
    )
    # Reciprocal Rank Fusion merge
    return rrf_merge(dense_results, sparse_results)[:top_k]
```

**Result**: technical term recall failures dropped from 15 to 3.

### Fix 2: Reranker (resolves "lost in the middle")

```python
from sentence_transformers import CrossEncoder

reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-12-v2')

top_3 = rerank(query, retrieved_chunks, top_k=3)
```

**Result**: relevant content appearing in top-3 improved from 72% to 91%.

### Fix 3: Tiered Model Routing (resolves quality on complex questions)

```python
def route_model(query: str) -> str:
    # Use Haiku first to classify complexity
    complexity = classify_complexity(query)
    return "claude-sonnet-4-6" if complexity == "complex" else "claude-haiku-4-5"
```

**Result**: answer quality improved on complex questions; cost increased only 18% (most questions still routed to Haiku).

### Fix 4: Document Version Management

```python
def upsert_document(doc_id: str, content: str, metadata: dict):
    """When updating a document, delete all existing chunks for that doc_id first, then insert fresh chunks"""
    vector_db.delete(
        collection_name="docs",
        points_selector=Filter(
            must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
        )
    )
    # Insert new chunks
    new_chunks = chunk_document(content)
    vector_db.upsert(collection_name="docs", points=[...])
```

---

## Final Results

| Metric | Before | After (optimized) |
|--------|--------|-------------------|
| Average answer time | 5–10 min (manual) | 30 sec (AI-assisted) |
| Answer accuracy (sampled) | N/A | 88% |
| Questions handled per agent per day | 25 | 40 |
| Monthly API cost | $0 | $380 |

---

## Decision Retrospective

**What we got right**:
1. Launched a simple version first, then optimized based on real production failure cases — avoided over-engineering
2. Started with pgvector and migrated only when we had an actual performance problem — no premature optimization
3. Designed the UI around the support agent workflow rather than a generic chat interface — lower learning curve

**Where we went wrong**:
1. No document version management in v1 — stale documents contaminated results. This should have been designed in from day one
2. Used LangChain's `RetrievalQA` chain — hard to debug when things broke. Rewrote as raw API; code became much clearer
3. Focused too early on the reranker — the bigger issue was document quality. AI can't extract good answers from poorly written source material

**The most important lesson**: document quality is the ceiling for RAG quality. Evaluate your source documents before optimizing the pipeline.

---

*[中文版 (Chinese)](README.zh.md)*
