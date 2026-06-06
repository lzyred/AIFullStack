[中文](frameworks.zh.md) | **English**

# LLM Framework Comparison: LangChain / LlamaIndex / Raw API

> Real usage experience, not a feature list.

---

## Bottom Line Up Front

**In most cases, default to raw API calls + a small set of utility functions.**

Frameworks are convenient in the prototyping phase. In production, they often become obstacles.

| Scenario | Recommendation |
|----------|----------------|
| Rapid prototype (<1 week) | LangChain or LlamaIndex |
| RAG system (production) | LlamaIndex or raw API |
| Agent (production) | Raw API + minimal utility functions |
| Long-term maintainable project | Raw API — only add libraries you actually need |
| Team already committed to a framework | Stay with it — migration cost exceeds framework pain |

---

## LangChain

**Good for**: rapid prototyping and idea exploration.

**Production problems**:
1. **Too many abstraction layers**: when something breaks, the call stack is 20 levels deep and you can't tell where the problem is
2. **Aggressive versioning**: 0.1 → 0.2 → 0.3 each brought breaking changes — maintenance overhead is real
3. **LCEL has a learning curve**: `chain = prompt | llm | parser` looks elegant but is painful to debug
4. **Performance overhead**: extra object creation and serialization on every call compared to raw API
5. **Overengineered for simple cases**: implementing a basic RAG with LangChain often produces more code than the raw API equivalent

**When it's worth using**:
- Rapid prototyping to validate an idea
- When you need LangSmith tracing (genuinely useful for debugging complex chains)
- Team is already familiar with LangChain

```python
# LangChain RAG example (prototyping)
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

llm = ChatAnthropic(model="claude-sonnet-4-6")
prompt = ChatPromptTemplate.from_messages([
    ("system", "Answer based on the following context: {context}"),
    ("user", "{question}")
])
chain = prompt | llm
result = chain.invoke({"context": retrieved_docs, "question": user_query})
```

---

## LlamaIndex

**Good for**: RAG and document processing — more focused than LangChain for these use cases.

**Strengths**:
- More complete document processing and indexing (connectors for PDF, Word, HTML, Notion, etc.)
- Cleaner RAG pipeline abstractions than LangChain
- The Query Engine concept is intuitive and easy to reason about

**Production problems**:
1. Same abstraction layer issues — hard to debug when things go wrong
2. Frequent version updates
3. For simple RAG, the abstraction overhead isn't justified

**When it's worth using**:
- RAG systems that need to process multiple document formats
- When you need LlamaIndex's connector ecosystem (Notion, Confluence, Google Drive, etc.)

```python
# LlamaIndex RAG example
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.llms.anthropic import Anthropic

documents = SimpleDirectoryReader("data/").load_data()
index = VectorStoreIndex.from_documents(documents)
query_engine = index.as_query_engine(llm=Anthropic(model="claude-sonnet-4-6"))
response = query_engine.query("your question here")
```

---

## Raw API (Recommended for Production)

**Strengths**:
- Full control — when something breaks, you know exactly where
- No version compatibility issues
- Best performance
- More readable code (friendlier to team members unfamiliar with a specific framework)

**Weaknesses**:
- You implement utility functions yourself (chunking, embedding, retrieval, etc.)
- Slower initial development compared to frameworks

**The reality**: a production-ready RAG core is under 300 lines of code. The value frameworks add isn't as large as it looks.

### Production RAG Skeleton (Raw API)

```python
import anthropic
from sentence_transformers import CrossEncoder
from qdrant_client import QdrantClient

# Initialize clients
client = anthropic.Anthropic()
reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-12-v2')
vector_db = QdrantClient(url="http://localhost:6333")

def embed(text: str) -> list[float]:
    """Generate embeddings using OpenAI or a local model"""
    from openai import OpenAI
    return OpenAI().embeddings.create(
        input=text,
        model="text-embedding-3-small"
    ).data[0].embedding

def retrieve(query: str, top_k: int = 10) -> list[str]:
    """Vector retrieval"""
    query_embedding = embed(query)
    results = vector_db.search(
        collection_name="documents",
        query_vector=query_embedding,
        limit=top_k
    )
    return [r.payload["text"] for r in results]

def rerank(query: str, chunks: list[str], top_k: int = 3) -> list[str]:
    """Reranker cross-encoder reranking"""
    pairs = [(query, chunk) for chunk in chunks]
    scores = reranker.predict(pairs)
    ranked = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)
    return [chunk for chunk, _ in ranked[:top_k]]

def answer(query: str, context: list[str]) -> str:
    """Generate an answer"""
    context_text = "\n\n---\n\n".join(context)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system="""Answer the question based on the provided documents.
        - Only use information from the documents
        - If the documents don't contain relevant information, say so clearly
        - Do not fabricate content""",
        messages=[{
            "role": "user",
            "content": f"<documents>\n{context_text}\n</documents>\n\nQuestion: {query}"
        }]
    )
    return response.content[0].text

def rag(query: str) -> str:
    """Full RAG pipeline"""
    chunks = retrieve(query, top_k=10)
    top_chunks = rerank(query, chunks, top_k=3)
    return answer(query, top_chunks)
```

---

## Framework Selection Criteria

Don't ask "which framework is better?" Ask "what specific problem does this framework solve for me?"

| Problem | Right tool |
|---------|------------|
| Need to prototype fast and test an idea | LangChain or LlamaIndex |
| Need to process multiple document formats (PDF / Word / Notion) | LlamaIndex Reader modules |
| Need to trace LLM call chains for debugging | LangSmith (LangChain's tracing tool — can be used standalone) |
| Need stable production code with long-term maintainability | Raw API + custom utility functions |
| Team already has a framework in place | Stay with it — migration cost exceeds framework problems |

---

## A Practical Hybrid Strategy

Use LangChain or LlamaIndex during development to validate fast. Rewrite core logic as raw API before going to production:

```
Prototype (1–2 weeks): LangChain — quickly validate the RAG flow
    ↓
Post-validation (approaching launch): identify the 3–5 functions that matter most in production
    ↓
Production version: rewrite those functions as raw API calls, minimize framework dependency
    ↓
Maintenance phase: framework upgrades no longer touch core logic
```
