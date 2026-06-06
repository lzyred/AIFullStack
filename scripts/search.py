#!/usr/bin/env python3
"""
AIFullStack Knowledge Base Search CLI
======================================
Search all docs in this repository from the command line.

Usage:
    python scripts/search.py "RAG chunking"
    python scripts/search.py "retention metrics" --top 5
    python scripts/search.py "streaming" --lang zh

Requirements: No dependencies beyond Python stdlib.

How it works:
    - Reads all .md files in the repository
    - Scores each file by keyword frequency + section heading matches
    - Returns ranked results with a preview snippet
"""

import os
import re
import sys
import argparse
from pathlib import Path
from collections import defaultdict

# Root of the repository (one level up from scripts/)
REPO_ROOT = Path(__file__).parent.parent

# Files/dirs to exclude from search
EXCLUDE_PATTERNS = {".git", "node_modules", "__pycache__", ".env"}


def collect_docs(lang: str = "en") -> list[dict]:
    """
    Collect all markdown files matching the language filter.

    Args:
        lang: "en" (default .md), "zh" (.zh.md), or "all"
    """
    docs = []
    for path in REPO_ROOT.rglob("*.md"):
        # Skip excluded directories
        if any(ex in path.parts for ex in EXCLUDE_PATTERNS):
            continue

        is_zh = path.name.endswith(".zh.md")

        if lang == "en" and is_zh:
            continue
        if lang == "zh" and not is_zh:
            # Keep .zh.md files; also keep files with no .zh.md counterpart
            counterpart = path.with_suffix("").with_suffix(".zh.md")
            if not is_zh and counterpart.exists():
                continue

        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            continue

        relative = path.relative_to(REPO_ROOT)
        docs.append({
            "path": str(relative),
            "content": content,
            "lines": content.splitlines(),
        })

    return docs


def extract_title(content: str, path: str) -> str:
    """Extract the first H1 heading, or fall back to the file path."""
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("# "):
            # Strip language switcher prefix if present
            title = line[2:].strip()
            return title
    return path


def score_doc(doc: dict, terms: list[str]) -> tuple[float, list[str]]:
    """
    Score a document against search terms.
    Returns (score, matching_snippets).
    """
    content_lower = doc["content"].lower()
    lines = doc["lines"]
    score = 0.0
    snippets = []

    for term in terms:
        term_lower = term.lower()
        count = content_lower.count(term_lower)
        if count == 0:
            continue

        # Higher weight for matches in headings
        for line in lines:
            if line.startswith("#") and term_lower in line.lower():
                score += 5
            elif term_lower in line.lower():
                score += 1

        # Collect snippets (lines containing the term, with context)
        for i, line in enumerate(lines):
            if term_lower in line.lower() and line.strip():
                # Skip language switcher lines
                if line.strip().startswith("[") and "](README" in line:
                    continue
                snippet = line.strip()[:120]
                if snippet and snippet not in snippets:
                    snippets.append(snippet)
                if len(snippets) >= 3:
                    break

    return score, snippets


def search(query: str, docs: list[dict], top_k: int = 5) -> list[dict]:
    """Search docs and return ranked results."""
    # Tokenize query
    terms = [t for t in re.split(r"\s+", query.strip()) if t]
    if not terms:
        return []

    results = []
    for doc in docs:
        score, snippets = score_doc(doc, terms)
        if score > 0:
            results.append({
                "path": doc["path"],
                "title": extract_title(doc["content"], doc["path"]),
                "score": score,
                "snippets": snippets,
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


def format_results(results: list[dict], query: str) -> str:
    """Format search results for terminal output."""
    if not results:
        return f'No results found for: "{query}"\n\nTry broader terms or use --lang all'

    lines = [f'\nSearch results for: "{query}"\n{"─" * 50}']

    for i, r in enumerate(results, 1):
        lines.append(f"\n{i}. {r['title']}")
        lines.append(f"   📄 {r['path']}")
        if r["snippets"]:
            for snippet in r["snippets"][:2]:
                # Truncate long lines
                display = snippet if len(snippet) <= 100 else snippet[:97] + "..."
                lines.append(f"   › {display}")

    lines.append(f'\n{"─" * 50}')
    lines.append(f"Found {len(results)} result(s)")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Search the AIFullStack knowledge base",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/search.py "RAG chunking"
  python scripts/search.py "retention metrics" --top 5
  python scripts/search.py "流式输出" --lang zh
  python scripts/search.py "agent" --lang all --top 10
        """
    )
    parser.add_argument("query", help="Search query")
    parser.add_argument("--top", type=int, default=5, metavar="N",
                        help="Number of results to show (default: 5)")
    parser.add_argument("--lang", choices=["en", "zh", "all"], default="en",
                        help="Language filter: en (default), zh, or all")
    args = parser.parse_args()

    docs = collect_docs(lang=args.lang)
    if not docs:
        print(f"No documents found in {REPO_ROOT}")
        sys.exit(1)

    results = search(args.query, docs, top_k=args.top)
    print(format_results(results, args.query))


if __name__ == "__main__":
    main()
