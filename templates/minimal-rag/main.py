"""
Minimal RAG Pipeline
====================
A complete, runnable RAG system in ~130 lines.
No external vector database required — uses in-memory numpy arrays.

Dependencies: anthropic, openai, numpy
Install: pip install anthropic openai numpy

Usage:
    # 1. Add documents to the docs/ directory (any .txt or .md files)
    # 2. Run: python main.py
"""

import os
import json
import math
from pathlib import Path
import anthropic
from openai import OpenAI

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────
DOCS_DIR = Path("docs")
EMBED_MODEL = "text-embedding-3-small"   # $0.02 / 1M tokens
GEN_MODEL = "claude-haiku-4-5"           # fast and cheap for Q&A
CHUNK_SIZE = 500        # characters per chunk
CHUNK_OVERLAP = 50      # overlap between chunks
TOP_K = 3               # chunks to retrieve

openai_client = OpenAI()
anthropic_client = anthropic.Anthropic()


# ─────────────────────────────────────────────
# 1. Load and Chunk Documents
# ─────────────────────────────────────────────
def load_documents(docs_dir: Path) -> list[dict]:
    """Load all .txt and .md files from docs directory."""
    documents = []
    for path in docs_dir.glob("**/*.{txt,md}"):
        text = path.read_text(encoding="utf-8")
        documents.append({"source": str(path), "text": text})
    return documents


def chunk_text(text: str, source: str) -> list[dict]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunk = text[start:end]
        if len(chunk.strip()) > 50:  # skip near-empty chunks
            chunks.append({"text": chunk, "source": source})
        start = end - CHUNK_OVERLAP
    return chunks


# ─────────────────────────────────────────────
# 2. Embed
# ─────────────────────────────────────────────
def embed(texts: list[str]) -> list[list[float]]:
    """Get embeddings for a list of texts using OpenAI."""
    response = openai_client.embeddings.create(
        input=texts,
        model=EMBED_MODEL,
    )
    return [item.embedding for item in response.data]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ─────────────────────────────────────────────
# 3. Index
# ─────────────────────────────────────────────
class InMemoryIndex:
    """Simple in-memory vector index. Good up to ~10k chunks."""

    def __init__(self):
        self.chunks: list[dict] = []          # {"text", "source"}
        self.embeddings: list[list[float]] = []

    def add(self, chunks: list[dict], embeddings: list[list[float]]):
        self.chunks.extend(chunks)
        self.embeddings.extend(embeddings)

    def search(self, query_embedding: list[float], top_k: int) -> list[dict]:
        scores = [
            (cosine_similarity(query_embedding, emb), i)
            for i, emb in enumerate(self.embeddings)
        ]
        scores.sort(reverse=True)
        results = []
        for score, idx in scores[:top_k]:
            results.append({**self.chunks[idx], "score": score})
        return results

    def save(self, path: str):
        data = {"chunks": self.chunks, "embeddings": self.embeddings}
        with open(path, "w") as f:
            json.dump(data, f)
        print(f"Index saved to {path}")

    def load(self, path: str):
        with open(path) as f:
            data = json.load(f)
        self.chunks = data["chunks"]
        self.embeddings = data["embeddings"]
        print(f"Loaded {len(self.chunks)} chunks from {path}")


# ─────────────────────────────────────────────
# 4. Retrieve + Generate
# ─────────────────────────────────────────────
def rag_query(query: str, index: InMemoryIndex) -> str:
    """Run a full RAG query: embed → retrieve → generate."""
    # Embed the query
    query_embedding = embed([query])[0]

    # Retrieve top-k chunks
    results = index.search(query_embedding, top_k=TOP_K)

    if not results or results[0]["score"] < 0.3:
        return "I couldn't find relevant information in the documents to answer this question."

    # Build context
    context_parts = []
    for r in results:
        context_parts.append(
            f"[Source: {r['source']} | Relevance: {r['score']:.2f}]\n{r['text']}"
        )
    context = "\n\n---\n\n".join(context_parts)

    # Generate answer
    response = anthropic_client.messages.create(
        model=GEN_MODEL,
        max_tokens=1024,
        system="""Answer questions based on the provided documents.
Rules:
- Only use information from the documents
- Cite the source when referencing specific information
- If the documents don't contain the answer, say "The documents don't contain information about this"
- Do not fabricate any information""",
        messages=[{
            "role": "user",
            "content": f"<documents>\n{context}\n</documents>\n\nQuestion: {query}"
        }]
    )
    return response.content[0].text


# ─────────────────────────────────────────────
# 5. Main
# ─────────────────────────────────────────────
def build_index() -> InMemoryIndex:
    """Load documents, chunk, embed, and return a populated index."""
    print("Loading documents...")
    documents = load_documents(DOCS_DIR)
    if not documents:
        raise ValueError(f"No .txt or .md files found in {DOCS_DIR}/")

    all_chunks = []
    for doc in documents:
        chunks = chunk_text(doc["text"], doc["source"])
        all_chunks.extend(chunks)
    print(f"Created {len(all_chunks)} chunks from {len(documents)} documents")

    print("Generating embeddings...")
    # Embed in batches of 100 to stay within API limits
    all_embeddings = []
    batch_size = 100
    for i in range(0, len(all_chunks), batch_size):
        batch = [c["text"] for c in all_chunks[i:i + batch_size]]
        all_embeddings.extend(embed(batch))
        print(f"  Embedded {min(i + batch_size, len(all_chunks))}/{len(all_chunks)}")

    index = InMemoryIndex()
    index.add(all_chunks, all_embeddings)
    return index


def main():
    index_path = "index.json"

    # Load existing index or build a new one
    index = InMemoryIndex()
    if Path(index_path).exists():
        index.load(index_path)
    else:
        index = build_index()
        index.save(index_path)

    print("\nRAG system ready. Type 'quit' to exit.\n")
    while True:
        query = input("Question: ").strip()
        if query.lower() in ("quit", "exit", "q"):
            break
        if not query:
            continue
        print("\nAnswer:", rag_query(query, index), "\n")


if __name__ == "__main__":
    main()
