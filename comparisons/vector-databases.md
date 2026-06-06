# 向量数据库对比：Qdrant / Pinecone / pgvector

> 不是功能列表对比，是生产环境的真实权衡。

---

## 先说结论

| 场景 | 推荐 |
|------|------|
| 快速原型 / 小规模（< 100万向量） | pgvector（已有 PostgreSQL 的话） |
| 生产环境，需要高性能 | Qdrant（开源，自托管，性能好）|
| 不想管基础设施，愿意付费 | Pinecone（托管，简单）|
| 已有 PostgreSQL，不想多一个服务 | pgvector |
| 需要混合检索（向量 + 关键词） | Qdrant 或 Weaviate |
| 企业级，需要 SLA 和合规 | Pinecone 或 Weaviate Cloud |

---

## 核心差异

### Qdrant

**优点**：
- 开源（Apache 2.0），自托管无供应商锁定
- 原生支持混合检索（Dense + Sparse）
- Rust 实现，性能出色，内存效率高
- 支持过滤条件（按元数据过滤后再向量搜索）
- 有托管版（Qdrant Cloud），也可自托管

**缺点**：
- 需要维护独立服务（如果自托管）
- 相比 Pinecone，文档和社区相对少（但在快速增长）

**适用场景**：对性能有要求、需要混合检索、不想被 SaaS 锁定的生产环境。

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

client = QdrantClient(url="http://localhost:6333")

# 创建集合
client.create_collection(
    collection_name="documents",
    vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
)

# 插入向量（带元数据）
client.upsert(
    collection_name="documents",
    points=[
        PointStruct(
            id=1,
            vector=embedding,
            payload={
                "text": "原始文本",
                "source": "doc_001",
                "date": "2026-01-01",
                "category": "technical"
            }
        )
    ]
)

# 带过滤的向量搜索
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

**优点**：
- 全托管，零运维
- 最成熟的 API，文档最好
- 全球部署，低延迟
- 支持 Namespace（多租户隔离）

**缺点**：
- 供应商锁定（专有服务）
- 成本较高（规模大后很贵）
- 不支持原生混合检索（需要额外 BM25 实现）
- 数据在第三方服务器上（某些合规场景不行）

**定价参考**：Starter 免费（100 万向量），生产环境按存储和查询量计费，$70/月起。

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

# 插入
index.upsert(vectors=[
    {"id": "doc_001", "values": embedding, "metadata": {"text": "...", "date": "2026-01"}}
])

# 查询
results = index.query(
    vector=query_embedding,
    top_k=10,
    filter={"date": {"$gte": "2026-01"}},
    include_metadata=True
)
```

### pgvector

**优点**：
- 在已有的 PostgreSQL 里直接用，零额外基础设施
- SQL 语法，开发者熟悉
- 可以和普通 SQL 查询结合（关系数据 + 向量搜索）
- 完全自控，无供应商锁定
- 成本最低（已有数据库的话）

**缺点**：
- 性能不如专门的向量数据库（大规模时）
- 建议上限：< 500 万向量（超过后延迟明显上升）
- 需要额外配置才能支持混合检索（FTS + 向量）

**什么时候用**：已经在用 PostgreSQL，数据量 < 500 万向量，不想多维护一个服务。

```sql
-- 安装扩展
CREATE EXTENSION vector;

-- 创建带向量字段的表
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    content TEXT,
    embedding vector(1536),
    source VARCHAR,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 创建 IVFFlat 索引（加速大规模查询）
CREATE INDEX ON documents USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);  -- lists = sqrt(总行数) 是经验值

-- 向量搜索
SELECT id, content, source,
       1 - (embedding <=> '[0.1, 0.2, ...]'::vector) AS similarity
FROM documents
WHERE source = 'technical'  -- 先过滤，再向量搜索
ORDER BY embedding <=> '[0.1, 0.2, ...]'::vector
LIMIT 10;
```

```python
# Python 使用（推荐 psycopg3）
import psycopg
import numpy as np

conn = psycopg.connect("postgresql://user:pass@localhost/dbname")

# 插入向量
with conn.cursor() as cur:
    cur.execute(
        "INSERT INTO documents (content, embedding, source) VALUES (%s, %s, %s)",
        ("文档内容", embedding.tolist(), "doc_001")
    )
conn.commit()

# 查询
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

## 性能对比

在 100 万向量、1536 维、余弦相似度、top-10 查询的条件下（粗略参考）：

| 数据库 | P50 延迟 | P99 延迟 | QPS（单节点） |
|--------|---------|---------|-------------|
| Qdrant | ~5ms | ~15ms | ~2000 |
| Pinecone | ~10ms | ~30ms | 托管，可扩展 |
| pgvector（HNSW） | ~10ms | ~50ms | ~500 |
| pgvector（IVFFlat） | ~20ms | ~100ms | ~300 |

**注意**：延迟高度依赖硬件、网络、数据规模、索引配置。以上数据仅供量级参考，上线前必须用真实数据自己跑 benchmark。

---

## 选型决策树

```
问：你的 PostgreSQL 里已经有数据，且向量数量 < 500万？
└── 是 → 用 pgvector（最简单，零额外成本）
└── 否 ↓

问：你需要混合检索（向量 + 关键词 BM25）？
└── 是 → 用 Qdrant 或 Weaviate
└── 否 ↓

问：你有 DevOps 能力管理独立服务？
└── 是 → 用 Qdrant（自托管，成本最优）
└── 否 → 用 Pinecone（托管，零运维）
```
