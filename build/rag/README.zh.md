[English](README.md) | **中文**

# RAG 生产实现指南

> Karpathy 检验：技术细节基于 Anthropic / OpenAI 官方文档，代码可运行。

---

## 为什么 RAG 会出问题

大多数 RAG 教程能跑通 Demo，但在生产中失效。根本原因：**Demo 的问题和生产的问题不一样。**

Demo 的问题：能不能检索出来。  
生产的问题：检索出来的东西够不够准，够不够稳定，出错了能不能发现。

---

## 分块策略

### 四种分块方式的选择逻辑

| 方式 | 适用场景 | 风险 |
|------|---------|------|
| 固定大小（512 tokens） | 快速原型 | 截断语义单元 |
| 语义分块（按句/段落） | 通用场景首选 | 块大小不均匀 |
| 递归字符分块 | LangChain 默认，均衡选择 | 无法感知文档结构 |
| 文档结构感知分块 | Markdown / HTML / PDF | 实现复杂 |

**推荐起点**：语义分块 + 512 tokens 上限，overlap 64 tokens。

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,
    chunk_overlap=64,
    separators=["\n\n", "\n", "。", " ", ""]
)
chunks = splitter.split_text(document)
```

### 分块的五个高频踩坑

1. **跨代码块/表格切割**：代码被截断后 embedding 语义扭曲，检索根本找不到相关代码。解法：在分隔符列表中加入 ` ``` ` 作为最高优先级分隔符。

2. **不注入元数据**：chunk 里没有文档来源、发布日期信息，模型无法做时效性判断。解法：每个 chunk 存储时附加 `source`、`date`、`section` 元数据。

3. **overlap 过大**：overlap > 20% chunk_size 时，相似 chunk 数量激增，检索噪音增加，reranker 负担加重。

4. **分块粒度与查询粒度不匹配**：用户问"什么是向量数据库"，chunk 是一段对比 5 个向量数据库的表格——语义相似度低于阈值，直接被过滤掉。解法：针对常见查询类型调整分块粒度。

5. **不过滤低质量 chunk**：页眉、页脚、目录页的 embedding 会污染索引。解法：设置最小 chunk 长度（< 50 tokens 直接丢弃）。

---

## Embedding 选型

### 主流模型对比

| 模型 | 维度 | 优势 | 适用场景 |
|------|------|------|---------|
| `text-embedding-3-large` | 3072 | 多语言强，可降维 | 通用生产首选 |
| `text-embedding-3-small` | 1536 | 成本低 10x | 高频、成本敏感 |
| `bge-m3` (BAAI) | 1024 | 开源，中文强，支持稀疏+密集 | 中文场景、私有部署 |
| `jina-embeddings-v3` | 1024 | 长文档（8192 tokens） | 长文档检索 |
| `voyage-3` | 1024 | 代码/技术文档强 | 代码 RAG |

**关键注意**：
- Anthropic 没有独立的 embedding API，中文场景推荐 `bge-m3`
- 迁移 embedding 模型时必须全量重新 embed，新旧向量空间不兼容

---

## 混合检索

纯向量检索的问题：精确关键词（人名、型号、代码函数名）召回率差。

混合检索 = 稀疏检索（BM25）+ 密集检索（向量），用 RRF 融合排名。

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

**推荐做法**：Qdrant、Weaviate、Elasticsearch 都原生支持混合检索，直接用，不要自己实现。

---

## Reranker：最高 ROI 的优化

成本接近 0（本地运行），RAG 质量提升明显。

**"Lost in the middle" 问题**：检索返回 10 个 chunk，相关内容在第 5 个，LLM 会忽略中间内容。Reranker 重排后只取 top-3，直接解决这个问题。

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

## 完整 Pipeline

```python
import anthropic

client = anthropic.Anthropic()

def rag_query(user_query: str, vector_store) -> str:
    # 1. 查询改写（提升召回率）
    rewritten = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=100,
        messages=[{
            "role": "user",
            "content": f"将以下问题改写为更适合语义搜索的形式（一句话）：{user_query}"
        }]
    ).content[0].text

    # 2. 混合检索 top-10
    chunks = vector_store.hybrid_search(rewritten, top_k=10)

    # 3. Rerank，只保留 top-3
    reranked = rerank(rewritten, chunks, top_k=3)

    # 4. Token 预算检查
    context = "\n\n---\n\n".join(reranked)

    # 5. 生成答案（明确禁止幻觉）
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system="""基于以下文档回答用户问题。
规则：
- 只使用文档中的信息作答
- 引用时标注来源
- 如果文档中没有相关信息，明确说"文档中没有这个信息"，不要猜测
- 不要编造任何内容""",
        messages=[{
            "role": "user",
            "content": f"<documents>\n{context}\n</documents>\n\n问题：{user_query}"
        }]
    )
    return response.content[0].text
```

---

## 生产踩坑记录

| 问题 | 症状 | 解法 |
|------|------|------|
| 向量索引不一致 | 旧版和新版文档同时命中，输出矛盾 | 文档级别 upsert，用文档 ID 做前缀删除旧 chunk |
| 查询-文档表达不对齐 | 相似度低于阈值，相关内容被过滤 | HyDE：先让 LLM 生成假设答案，用假设答案做向量检索 |
| 上下文窗口超限 | API 偶发报错，难以复现 | 发请求前用 tokenizer 计算，超限时截断最旧的 chunk |
| 检索质量无监控 | 只能靠用户投诉发现问题 | 记录每次 top-1 相似度分数，设阈值报警 |
| embedding 模型迁移 | 检索质量骤降 | 迁移时必须全量重新 embed，新旧向量空间不兼容 |

---

## 评估：你怎么知道 RAG 够好了

上线前必须做的三个评估：

1. **Retrieval Recall**：给定一批问题，相关 chunk 是否出现在 top-k 结果里。目标：Recall@5 > 80%
2. **Answer Faithfulness**：答案是否只基于检索到的文档，没有幻觉。可用 LLM-as-Judge 自动评估
3. **End-to-End 准确率**：人工标注 50-100 个问答对，定期跑回归

---

*优先级：先做 Reranker（免费），再做混合检索，再做查询改写。按顺序来，不要一次全上。*


---

*[English Version](README.md)*
