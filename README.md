# AIFullStack

**What if Karpathy taught you to build, Andrew Chen taught you to grow, and Sam Altman told you why it's worth doing — what would you ship?**

**[中文版](README.zh.md)**

---

Building an AI product solo requires three capabilities firing at once:

**Ship something that works. Get people to keep using it. Know it's worth building.**

Three people in the AI world have each pushed one of these to the extreme. This repository distills their most actionable frameworks into docs, code, and decision tools you can use directly.

---

## The Iron Triangle

### Andrej Karpathy · The Engineer's Lens

Co-founder of OpenAI, Director of Autopilot at Tesla. Originator of "Software 2.0" — neural networks are the new code, prompts are the new programming language.

His core conviction: Most developers building AI apps are just calling APIs. The real gap is understanding model behavior boundaries — why it hallucinates, why RAG retrieval fails, why Agents go off the rails. You can only fix what you understand.

**The question he'd ask you: Does your system actually work reliably?**

---

### Andrew Chen · The Growth Lens

General Partner at a16z, former Head of Growth at Uber, author of *The Cold Start Problem*. His life's work: how does a product go from 0 to millions of users?

His core conviction: AI features are not a moat. Most AI products die because users don't come back after the first session — not because the tech isn't good enough. Retention is the foundation of all growth. Without it, every dollar you spend on acquisition is leaking through the floor.

**The question he'd ask you: Why would users come back to yours instead of switching to something else?**

---

### Sam Altman · The Product Strategy Lens

CEO of OpenAI, former President of Y Combinator. He thinks harder and earlier about AI's impact on building things than anyone, while maintaining a ruthlessly practical filter on what's actually worth doing.

His core conviction: The window to build AI products right now is real. Most people are waiting for the tech to mature. The question was never whether the tech is ready — it's whether the problem you're solving is real enough, and the user's pain is deep enough.

**The question he'd ask you: Will this still matter in 10 years?**

---

## What This Repository Solves

When building AI apps, you've probably run into these:

- The tutorial you found uses an API deprecated six months ago, and the code doesn't run
- You got the tech working, but users can't explain why they'd use yours over ChatGPT
- You spent two months building a feature-complete product and found nobody actually needed it

These three problems map directly to what Karpathy, Andrew Chen, and Sam Altman care most about.

This repository is not about teaching you to call APIs. It's about helping you **ship an AI product that survives**.

---

## Content Structure

```
AIFullStack/
│
├── build/                          # Karpathy layer: How to build
│   ├── llm-fundamentals/           # LLM internals from an engineer's view: tokens, context, cost
│   ├── prompt-engineering/         # System prompts, structured output, anti-patterns
│   ├── rag/                        # Chunking, embeddings, hybrid search, production pitfalls
│   ├── agents/                     # When to use Agents, how to make them reliable
│   ├── streaming/                  # SSE, reconnects, frontend integration
│   └── infrastructure/             # Deployment, cost control, observability, prompt security
│
├── grow/                           # Andrew Chen layer: How to grow
│   ├── retention/                  # AI product retention mechanics: why users don't come back
│   ├── cold-start/                 # Where your first users come from: real paths, not theory
│   ├── growth-loops/               # Growth loop design: viral, content, workflow stickiness
│   └── metrics/                    # What numbers tell you you're on the right track
│
├── vision/                         # Sam Altman layer: Is it worth building?
│   ├── positioning/                # Painkiller vs. vitamin: what users will actually pay for
│   ├── market-timing/              # What to build now vs. what to wait on
│   └── validation/                 # Minimum viable assumptions: test the biggest risk first
│
├── comparisons/                    # Side-by-side: help you decide without guessing
│   ├── llm-providers.md            # OpenAI / Anthropic / Gemini: how to choose for your use case
│   ├── vector-databases.md         # Qdrant / Pinecone / pgvector: cost vs. performance tradeoffs
│   └── frameworks.md               # LangChain / LlamaIndex / raw API: honest real-world experience
│
└── case-studies/                   # Full project walkthroughs: real decisions, including the wrong ones
    ├── rag-chatbot/                 # Enterprise knowledge base Q&A system
    ├── ai-writing-tool/             # AI-assisted writing product
    └── agent-workflow/              # Multi-step automation Agent
```

---

## How to Use This Repository

**Debugging a technical problem** → Start in `build/`, find the relevant module

**Have a product but no users** → Go straight to `grow/retention/` — fix retention first

**Still figuring out what to build** → Start with `vision/positioning/`

**Need to pick a tech stack** → Check `comparisons/` — side-by-side comparisons with real production notes

**Want to see how a full project comes together** → Go to `case-studies/` — decisions from 0 to launch, including the detours

---

## Document Quality Standard

Every document must pass three checks before publishing:

| Check | Standard |
|-------|----------|
| **Karpathy Check** | Technically accurate. Code runs against current API versions. No deprecated patterns. |
| **Andrew Chen Check** | Actionable conclusions. Specific numbers. Not "it depends on your situation." |
| **Sam Altman Check** | Solves a real problem. Not showcasing technical capabilities or stacking tools. |

Outdated content gets flagged or removed. Quality of retrieval matters more than volume of content.

---

## Current Status

Content is being added continuously. Current priorities:

- `build/rag/` — Production-grade RAG, including real failure cases
- `build/agents/` — Reliable Agent design patterns
- `grow/retention/` — AI product retention framework

If you're building an AI product and have production experience or war stories to share, PRs and Issues are welcome.

---

## Language

- **English** (default) — you're reading it
- **[中文版 (Chinese)](README.zh.md)**

---

*Three lenses. One goal: help you ship an AI product that actually lives.*
