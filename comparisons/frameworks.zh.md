[English](frameworks.md) | **中文**

# LLM 框架对比：LangChain / LlamaIndex / 裸 API

> 真实使用体验，不是功能列表。

---

## 先说结论

**大多数情况下，优先考虑裸 API + 少量工具函数。**

框架在原型阶段很方便，在生产阶段经常变成障碍。

| 场景 | 推荐 |
|------|------|
| 快速原型（< 1 周） | LangChain 或 LlamaIndex |
| RAG 系统（生产） | LlamaIndex 或裸 API |
| Agent（生产） | 裸 API + 少量工具函数 |
| 需要长期维护的项目 | 裸 API，只引入必要的库 |
| 已有框架的团队 | 继续用，迁移成本高于框架问题 |

---

## LangChain

**适合**：快速搭建原型，探索想法。

**生产问题**：
1. **抽象层太厚**：出错时调用栈 20 层，不知道问题在哪里
2. **版本更新激进**：0.1 → 0.2 → 0.3 每次都有破坏性改变，维护成本高
3. **LCEL 语法学习成本**：`chain = prompt | llm | parser` 看起来优雅，调试困难
4. **性能开销**：相比裸 API，每次调用有额外的对象创建和序列化开销
5. **过度设计**：用 LangChain 实现简单的 RAG，代码量反而比裸 API 更多

**什么时候值得用**：
- 快速原型，证明想法
- 需要 LangSmith 追踪（调试复杂链路时有用）
- 团队已经熟悉 LangChain

```python
# LangChain RAG 示例（原型用）
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

llm = ChatAnthropic(model="claude-sonnet-4-6")
prompt = ChatPromptTemplate.from_messages([
    ("system", "基于以下上下文回答：{context}"),
    ("user", "{question}")
])
chain = prompt | llm
result = chain.invoke({"context": retrieved_docs, "question": user_query})
```

---

## LlamaIndex

**适合**：RAG 和文档处理场景，比 LangChain 在这方面更专注。

**优点**：
- 文档处理和索引功能更完整（PDF、Word、HTML、Notion 等连接器）
- RAG Pipeline 的抽象比 LangChain 更清晰
- Query Engine 概念直观，容易理解

**生产问题**：
1. 抽象层同样存在，出错时不好调试
2. 版本更新也频繁
3. 对于简单 RAG，抽象收益不明显

**什么时候值得用**：
- 需要处理多种文档格式的 RAG 系统
- 需要 LlamaIndex 的连接器生态（Notion、Confluence、Google Drive 等）

```python
# LlamaIndex RAG 示例
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.llms.anthropic import Anthropic

documents = SimpleDirectoryReader("data/").load_data()
index = VectorStoreIndex.from_documents(documents)
query_engine = index.as_query_engine(llm=Anthropic(model="claude-sonnet-4-6"))
response = query_engine.query("你的问题")
```

---

## 裸 API（推荐生产使用）

**优点**：
- 完全可控，出错时清楚知道在哪里
- 没有版本兼容问题
- 性能最好
- 代码可读性更高（对不熟悉框架的团队成员更友好）

**缺点**：
- 需要自己实现工具函数（分块、embedding、检索等）
- 开发速度比框架慢

**实际情况**：自己实现一个生产级 RAG 的核心代码不超过 300 行，框架的价值没有想象中大。

### 裸 API 的生产 RAG 实现骨架

```python
import anthropic
from sentence_transformers import CrossEncoder
from qdrant_client import QdrantClient

# 初始化
client = anthropic.Anthropic()
reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-12-v2')
vector_db = QdrantClient(url="http://localhost:6333")

def embed(text: str) -> list[float]:
    """用 OpenAI 或本地模型生成向量"""
    from openai import OpenAI
    return OpenAI().embeddings.create(
        input=text,
        model="text-embedding-3-small"
    ).data[0].embedding

def retrieve(query: str, top_k: int = 10) -> list[str]:
    """向量检索"""
    query_embedding = embed(query)
    results = vector_db.search(
        collection_name="documents",
        query_vector=query_embedding,
        limit=top_k
    )
    return [r.payload["text"] for r in results]

def rerank(query: str, chunks: list[str], top_k: int = 3) -> list[str]:
    """Reranker 重排"""
    pairs = [(query, chunk) for chunk in chunks]
    scores = reranker.predict(pairs)
    ranked = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)
    return [chunk for chunk, _ in ranked[:top_k]]

def answer(query: str, context: list[str]) -> str:
    """生成答案"""
    context_text = "\n\n---\n\n".join(context)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system="""基于提供的文档回答问题。
        - 只使用文档中的信息
        - 如果文档中没有相关信息，说明"文档中没有这个信息"
        - 不要编造内容""",
        messages=[{
            "role": "user",
            "content": f"<documents>\n{context_text}\n</documents>\n\n问题：{query}"
        }]
    )
    return response.content[0].text

def rag(query: str) -> str:
    """完整 RAG Pipeline"""
    chunks = retrieve(query, top_k=10)
    top_chunks = rerank(query, chunks, top_k=3)
    return answer(query, top_chunks)
```

---

## 框架选择的决策依据

不要问"哪个框架更好"，要问"这个框架解决了我的哪个具体问题"。

| 问题 | 对应工具 |
|------|---------|
| 需要快速搭原型，测想法 | LangChain 或 LlamaIndex |
| 需要处理多种文档格式（PDF/Word/Notion） | LlamaIndex 的 Reader 模块 |
| 需要追踪 LLM 调用链，方便调试 | LangSmith（LangChain 的追踪工具，可单独用） |
| 需要稳定的生产代码，长期维护 | 裸 API + 自定义工具函数 |
| 团队已有框架选型 | 继续用，迁移成本 > 框架问题 |

---

## 一个实用的混合策略

开发阶段用 LangChain/LlamaIndex 快速验证，生产阶段把核心逻辑重写为裸 API：

```
原型（1-2 周）：LangChain，快速验证 RAG 流程
    ↓
验证后（接近上线）：识别生产中最重要的 3-5 个函数
    ↓
生产版本：重写这些函数为裸 API，保持对框架的最小依赖
    ↓
维护期：框架升级不再影响核心逻辑
```


---

*[English Version](frameworks.md)*
