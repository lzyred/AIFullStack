[中文](vector-databases.zh.md) | **English**

# Vector Database Comparison: Qdrant / Pinecone / pgvector

> Not a feature checklist — real production trade-offs.

---

## Bottom Line Up Front

| Scenario | Recommendation |
|----------|----------------|
| Quick prototype / small scale (<1M vectors) | pgvector (if you already have PostgreSQL) |
| Production, high-performance required | Qdrant (open-source, self-hosted, excellent performance) |
| No infrastructure to manage, willing to pay | Pinecone (fully managed, simple) |
| Already on PostgreSQL, don't want another service | pgvector |
| Hybrid search needed (vector + keyword) | Qdrant or Weaviate |
| Enterprise, need SLA and compliance | Pinecone or Weaviate Cloud |

---

## Core Differences

### Qdrant

**Strengths**:
- Open-source (Apache 2.0) — self-host with no vendor lock-in
- Native hybrid search (Dense + Sparse vectors)
- Written in Rust — excellent performance and memory efficiency
- Supports filtered vector search (filter by metadata, then search)
- Available both as a managed service (Qdrant Cloud) and self-hosted

**Weaknesses**:
- Requires maintaining a separate service (if self-hosting)
- Smaller community and documentation compared to Pinecone (growing fast though)

**Best for**: production environments where you need performance, hybrid search, and don't want SaaS lock-in.

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

client = QdrantClient(url="http://localhost:6333")

# Create a collection
client.create_collection(
    collection_name="documents",
    vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
)

# Insert vectors with metadata
client.upsert(
    collection_name="documents",
    points=[
        PointStruct(
            id=1,
            vector=embedding,
            payload={
                "text": "original document text",
                "source": "doc_001",
                "date": "2026-01-01",
                "category": "technical"
            }
        )
    ]
)

# Filtered vector search
from qdrant_client.models import Filter, FieldCondition, MatchValue

results = client.search(
    collection_name="documents",
    query_vector=query_embedding,
    query_filter=Filter(
        must=[FieldCondition(key="category", match=MatchValue(value="technical"))]
    ),
    limit=10
)
```

### Pinecone

**Strengths**:
- Fully managed — zero ops
- Most mature API and best documentation
- Global deployment, low latency
- Namespace support for multi-tenant isolation

**Weaknesses**:
- Vendor lock-in (proprietary service)
- Expensive at scale
- No native hybrid search (requires a separate BM25 implementation)
- Data lives on third-party servers (a blocker in some compliance scenarios)

**Pricing reference**: Starter tier is free (up to 1M vectors); production billing is based on storage and query volume, starting at $70/month.

```python
from pinecone import Pinecone, ServerlessSpec

pc = Pinecone(api_key="your-api-key")

pc.create_index(
    name="documents",
    dimension=1536,
    metric="cosine",
    spec=ServerlessSpec(cloud="aws", region="us-east-1")
)

index = pc.Index("documents")

# Upsert
index.upsert(vectors=[
    {"id": "doc_001", "values": embedding, "metadata": {"text": "...", "date": "2026-01"}}
])

# Query
results = index.query(
    vector=query_embedding,
    top_k=10,
    filter={"date": {"$gte": "2026-01"}},
    include_metadata=True
)
```

### pgvector

**Strengths**:
- Runs inside your existing PostgreSQL instance — zero additional infrastructure
- Standard SQL syntax — familiar to any developer
- Combine vector search with regular SQL queries (relational data + vector search together)
- Fully self-controlled, no vendor lock-in
- Lowest cost if you're already running PostgreSQL

**Weaknesses**:
- Lower performance than purpose-built vector databases at scale
- Recommended ceiling: <5M vectors (latency degrades noticeably beyond that)
- Hybrid search requires additional setup (FTS + vector)

**When to use it**: you're already on PostgreSQL, have fewer than 5M vectors, and don't want to operate another service.

```sql
-- Install the extension
CREATE EXTENSION vector;

-- Create a table with a vector column
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    content TEXT,
    embedding vector(1536),
    source VARCHAR,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create an HNSW index (faster for large-scale queries)
CREATE INDEX ON documents USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Or IVFFlat index
-- CREATE INDEX ON documents USING ivfflat (embedding vector_cosine_ops)
-- WITH (lists = 100);  -- lists ≈ sqrt(total rows) is a common rule of thumb

-- Vector search
SELECT id, content, source,
       1 - (embedding <=> '[0.1, 0.2, ...]'::vector) AS similarity
FROM documents
WHERE source = 'technical'  -- filter first, then vector search
ORDER BY embedding <=> '[0.1, 0.2, ...]'::vector
LIMIT 10;
```

```python
# Python usage (psycopg3 recommended)
import psycopg
import numpy as np

conn = psycopg.connect("postgresql://user:pass@localhost/dbname")

# Insert a vector
with conn.cursor() as cur:
    cur.execute(
        "INSERT INTO documents (content, embedding, source) VALUES (%s, %s, %s)",
        ("document text", embedding.tolist(), "doc_001")
    )
conn.commit()

# Query
with conn.cursor() as cur:
    cur.execute("""
        SELECT id, content, 1 - (embedding <=> %s) AS similarity
        FROM documents
        ORDER BY embedding <=> %s
        LIMIT %s
    """, (query_embedding.tolist(), query_embedding.tolist(), 10))
    results = cur.fetchall()
```

---

## Performance Comparison

Rough benchmarks at 1M vectors, 1536 dimensions, cosine similarity, top-10 queries:

| Database | P50 latency | P99 latency | QPS (single node) |
|----------|-------------|-------------|-------------------|
| Qdrant | ~5ms | ~15ms | ~2,000 |
| Pinecone | ~10ms | ~30ms | Managed, scales horizontally |
| pgvector (HNSW) | ~10ms | ~50ms | ~500 |
| pgvector (IVFFlat) | ~20ms | ~100ms | ~300 |

**Important**: latency depends heavily on hardware, network, data scale, and index configuration. These numbers are order-of-magnitude references only. Run your own benchmark with real data before committing to a choice.

---

## Decision Tree

```
Q: Do you already have your data in PostgreSQL, and is your vector count <5M?
└── Yes → Use pgvector (simplest path, no added cost)
└── No  ↓

Q: Do you need hybrid search (vector + keyword BM25)?
└── Yes → Use Qdrant or Weaviate
└── No  ↓

Q: Do you have DevOps capacity to run a separate service?
└── Yes → Use Qdrant (self-hosted, best cost efficiency)
└── No  → Use Pinecone (fully managed, zero ops)
```
