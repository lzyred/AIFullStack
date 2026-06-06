[English](README.md) | **中文**

# 案例复盘：企业知识库问答系统

> 从 0 到上线的真实决策过程，包含走过的弯路。

---

## 项目背景

**场景**：某 200 人 SaaS 公司，客服团队每天回答重复的产品问题。80% 的问题能在文档中找到答案，但客服需要手动搜索文档，平均每次回答花 5-10 分钟。

**目标**：用 RAG 系统让客服能在 30 秒内找到准确答案，减少重复搜索时间。

**初始数据**：
- 文档量：800 个 Markdown 文件，总计约 300 万字
- 每日问题量：约 200 个
- 客服团队规模：8 人

---

## 阶段1：技术选型（Week 1）

### 向量数据库选择

**决策**：选择 pgvector，而非 Qdrant 或 Pinecone。

**理由**：
- 团队已有 PostgreSQL，零额外基础设施
- 文档量 < 100 万向量，pgvector 性能够用
- 减少运维复杂度优先于性能最优

**后来发现的问题**：pgvector 在 IVFFlat 索引下，过滤 + 向量搜索的组合查询慢。后来迁移到 HNSW 索引，P95 延迟从 200ms 降到 40ms。

```sql
-- 最终使用的索引方式（HNSW 而非 IVFFlat）
CREATE INDEX ON documents USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

### Embedding 模型选择

**决策**：`text-embedding-3-small`（OpenAI），而非 `text-embedding-3-large`。

**理由**：成本差 10x，初期精度差异不足以支撑 10x 成本。后续如果检索质量不满意再升级。

**实际结果**：small 模型对中文文档的检索精度基本够用。只有少数技术术语的召回不理想，用混合检索补上。

---

## 阶段2：第一版上线（Week 2-3）

### 架构决策

```
用户输入
  → 向量检索（pgvector top-10）
  → Claude Haiku 4.5 生成答案
  → 输出（带文档来源链接）
```

**为什么没有上来就做混合检索和 Reranker**：先验证核心价值，再优化细节。上线后根据真实失败案例决定下一步优化。

### 第一版的问题

上线 2 周后收集到的失败案例分析：

| 失败类型 | 案例数 | 原因 |
|---------|--------|------|
| 技术术语召回失败 | 15 | 纯向量检索对精确关键词弱 |
| "Lost in the middle" | 8 | Top-10 里相关内容在第 6 位，模型忽略 |
| 文档版本不一致 | 6 | 旧版文档没有清理，和新版同时命中 |
| 答案过于简短 | 12 | Haiku 模型在复杂问题上输出质量不够 |

---

## 阶段3：针对性优化（Week 4-6）

### 优化1：混合检索（解决技术术语问题）

```python
from qdrant_client import QdrantClient
from rank_bm25 import BM25Okapi

# 迁移到 Qdrant，支持原生混合检索
# pgvector 的混合检索实现太麻烦，这里是迁移后的成本

def hybrid_search(query: str, top_k: int = 10) -> list[str]:
    # 向量检索
    dense_results = vector_db.search(
        collection_name="docs",
        query_vector=embed(query),
        limit=top_k
    )
    # BM25 关键词检索（通过 Qdrant sparse vectors）
    sparse_results = vector_db.search(
        collection_name="docs",
        query_sparse_vector=bm25_encode(query),
        limit=top_k
    )
    # RRF 融合
    return rrf_merge(dense_results, sparse_results)[:top_k]
```

**效果**：技术术语召回失败案例从 15 减少到 3。

### 优化2：Reranker（解决 Lost in the middle 问题）

```python
from sentence_transformers import CrossEncoder

reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-12-v2')

top_3 = rerank(query, retrieved_chunks, top_k=3)
```

**效果**：相关内容进入 top-3 的比例从 72% 提升到 91%。

### 优化3：分级模型路由（解决复杂问题质量问题）

```python
def route_model(query: str) -> str:
    # 先用 Haiku 判断复杂度
    complexity = classify_complexity(query)
    return "claude-sonnet-4-6" if complexity == "complex" else "claude-haiku-4-5"
```

**效果**：复杂问题答案质量提升，成本只增加了 18%（大多数问题还是走 Haiku）。

### 优化4：文档版本管理

```python
def upsert_document(doc_id: str, content: str, metadata: dict):
    """更新文档时，先删除同一 doc_id 的所有旧 chunks，再插入新 chunks"""
    vector_db.delete(
        collection_name="docs",
        points_selector=Filter(
            must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
        )
    )
    # 然后插入新 chunks
    new_chunks = chunk_document(content)
    vector_db.upsert(collection_name="docs", points=[...])
```

---

## 最终结果

| 指标 | 上线前 | 上线后（优化版） |
|------|--------|----------------|
| 平均回答时间 | 5-10 分钟（手动） | 30 秒（AI 辅助） |
| 答案准确率（抽样评估） | N/A | 88% |
| 客服人均处理量 | 25 问题/天 | 40 问题/天 |
| 月 API 成本 | $0 | $380 |

---

## 关键决策复盘

**做对的决策**：
1. 先上线简单版，再根据真实失败案例优化（避免过度设计）
2. 从 pgvector 开始，等有了性能问题再迁移（不过早优化）
3. 按客服角色设计 UI，而非通用聊天界面（降低学习成本）

**走的弯路**：
1. 第一版没有做文档版本管理，导致旧文档污染。应该在设计阶段就考虑
2. 用了 LangChain 的 RetrievalQA chain，出问题时难以调试。后来重写为裸 API，代码更清晰
3. 过早关注 Reranker，实际上更大的问题是文档质量（很多文档写得很差，AI 也无法从差文档里找到好答案）

**最重要的教训**：文档质量是 RAG 质量的上限。在优化 pipeline 之前，先评估文档本身的质量。


---

*[English Version](README.md)*
