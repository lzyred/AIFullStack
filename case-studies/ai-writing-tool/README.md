[中文](README.zh.md) | **English**

# Case Study: AI Writing Assistant for SaaS Marketing Teams

> The real decisions, dead ends, and eventual traction — from a solo dev building in public.

---

## Background

**Scenario**: a solo indie developer building a productivity tool for small B2B SaaS marketing teams. The target user: a 1–3-person marketing team responsible for writing a weekly product update newsletter and versioned release notes. Before the tool, each newsletter took 4–6 hours — pulling changelog notes from GitHub, massaging them into readable prose, and aligning the tone with the company brand. After: 45 minutes end-to-end.

**Goal**: let marketing teams feed in a raw product changelog and get a publication-ready first draft, already written in their brand voice, in under two minutes.

**Starting context**:
- Developer: solo, no co-founder
- Initial target users: 0 (cold start)
- Stack familiarity: Python backend, basic React frontend
- Budget: $0 marketing, $50/month for API costs

---

## Phase 1: Technology Decisions (Week 1)

### Streaming vs. Batch Response

**Decision**: streaming (Server-Sent Events via FastAPI), not waiting for the full response.

**Reasoning**: newsletters are 600–1200 words. Waiting 15–25 seconds for a complete response before showing anything felt broken in user testing, even when the output quality was identical. Streaming gave perceived responsiveness. Users felt the tool was working alongside them rather than processing in the background.

**Implementation**: FastAPI's `StreamingResponse` with SSE:

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import anthropic

app = FastAPI()
client = anthropic.Anthropic()

async def stream_draft(changelog: str, brand_voice: dict):
    """Stream a newsletter draft token by token via SSE."""
    system_prompt = build_system_prompt(brand_voice)

    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=system_prompt,
        messages=[{"role": "user", "content": f"Changelog:\n\n{changelog}"}]
    ) as stream:
        for text in stream.text_stream:
            # SSE format: data: <chunk>\n\n
            yield f"data: {text}\n\n"
        yield "data: [DONE]\n\n"

@app.post("/draft/stream")
async def draft_stream(payload: DraftRequest):
    return StreamingResponse(
        stream_draft(payload.changelog, payload.brand_voice),
        media_type="text/event-stream"
    )
```

### Model Selection

**Decision**: model routing — Haiku for outline generation, Sonnet for full draft.

**Reasoning**: generating a complete newsletter draft in one shot with a long changelog context was expensive and slow. The insight was that the two tasks have different quality requirements: structuring the changelog into sections is a classification and ordering task (fast, cheap, Haiku handles it fine); transforming bullet points into polished prose requires more capability (Sonnet).

```python
def route_model(task: str) -> str:
    """Route to the appropriate model based on task type."""
    if task == "outline":
        return "claude-haiku-4-5"   # Fast, cheap — good enough for structure
    elif task == "draft":
        return "claude-sonnet-4-6"  # Higher quality for final prose
    else:
        return "claude-haiku-4-5"   # Default to cheaper for utilities
```

**Actual cost impact**: average cost per newsletter dropped from ~$0.08 (Sonnet-only) to ~$0.031 (outline with Haiku + draft with Sonnet). At scale across many newsletters per day, this compounds significantly.

### Brand Voice System

**Decision**: encode brand voice as a structured system prompt block, not a freeform "write like us" instruction.

**Problem**: early testing showed that "write in a friendly, concise tone" produced inconsistent results. Different runs would produce different levels of formality, vocabulary, and sentence rhythm.

**Solution**: a structured brand voice schema with concrete examples. Each customer fills in a short onboarding form; the answers are serialized into the system prompt.

```python
def build_system_prompt(brand_voice: dict) -> str:
    """
    Build a system prompt that encodes brand voice with concrete examples.
    brand_voice keys: tone, vocabulary, sentence_length, example_before, example_after
    """
    return f"""You are a professional copywriter for {brand_voice['company_name']}.

## Brand Voice Guidelines

**Tone**: {brand_voice['tone']}
(e.g. "{brand_voice['tone_example']}")

**Vocabulary to use**: {', '.join(brand_voice['preferred_words'])}
**Vocabulary to avoid**: {', '.join(brand_voice['avoid_words'])}

**Sentence style**: {brand_voice['sentence_style']}
Target sentence length: {brand_voice['avg_sentence_words']} words on average.

## Reference Examples

Here is a sample of the company's existing writing:

BEFORE (raw changelog):
{brand_voice['example_before']}

AFTER (published newsletter excerpt):
{brand_voice['example_after']}

---

When writing, match the voice of the AFTER example, not the BEFORE.
Do not mention the product name in every sentence. Vary your openings.
Never use the phrases: "we're excited to announce", "game-changing", "seamlessly".
"""
```

**What this fixed**: consistency across runs improved dramatically. Users reported the output felt recognizably "theirs" from the first draft rather than generic AI prose.

### Context Length Management

**Problem**: some engineering teams dump weeks of unfiltered git commit messages into the changelog field. A two-week changelog from an active repo can be 3,000–5,000 tokens before the system prompt is even added.

**Decision**: pre-process and truncate changelogs before sending to the model, rather than hoping the model handles a long messy context gracefully.

```python
def preprocess_changelog(raw_changelog: str, max_tokens: int = 3000) -> str:
    """
    Clean and truncate a raw changelog to fit within context budget.
    Prioritizes keeping higher-level items (features > fixes > chores).
    """
    lines = raw_changelog.strip().split("\n")

    # Rank lines by type: features first, then fixes, then chores/deps
    priority_order = {"feat": 0, "fix": 1, "perf": 2, "refactor": 3, "chore": 4, "deps": 5}

    def line_priority(line: str) -> int:
        for prefix, rank in priority_order.items():
            if line.lower().startswith(prefix) or f"({prefix})" in line.lower():
                return rank
        return 3  # Default: treat as refactor-level priority

    sorted_lines = sorted(lines, key=line_priority)

    # Trim to token budget (rough approximation: 1 token ≈ 4 chars)
    budget_chars = max_tokens * 4
    result, total = [], 0
    for line in sorted_lines:
        if total + len(line) > budget_chars:
            break
        result.append(line)
        total += len(line)

    return "\n".join(result)
```

**Tradeoff acknowledged**: this truncation is lossy. Minor fixes at the bottom of a long changelog get dropped. This is intentional — a newsletter should lead with features, not dependency bumps. Users were told about this behavior upfront.

---

## Phase 2: First Version Shipped (Weeks 2–3)

### Architecture

```
User pastes changelog + brand voice form
  → preprocess_changelog() (Python, server-side)
  → Haiku generates section outline
  → Sonnet streams full newsletter draft (SSE)
  → Frontend renders streamed tokens in real time
  → User edits inline and copies final version
```

**First users**: the developer posted a Twitter thread about building the tool in public — showing raw screenshots, the actual prompt architecture, and early failure cases. The thread got modest engagement but drove 47 signups in 48 hours. These were not random curiosity signups: they were marketers who recognized the problem immediately.

**What worked on day one**:
- Streaming made the tool feel fast even though generation took 12–18 seconds
- The brand voice form had 6 fields — short enough that users completed it in under 3 minutes
- Haiku outline step gave users something to react to before the full draft appeared

**What didn't work on day one**:
- No diff view — users had no way to see what they changed vs. what the AI wrote. Several users reported losing their edits after refreshing
- No history — each session started from scratch. Users who came back the next day had to re-enter their brand voice settings every time
- The system prompt was too long for users with very short changelogs (2–3 items). The model would pad the output with filler to hit an implied length target

### LangChain Detour (Days 5–8)

Before writing the streaming endpoint from scratch, the developer spent three days attempting to use LangChain's `LLMChain` and streaming callbacks.

**What broke**: LangChain's streaming abstraction added two layers of indirection between the token stream and the SSE output. When a run silently returned an empty string (a rate-limit edge case), debugging required reading LangChain source code to understand which internal callback was swallowing the error. After three days, the chain was working but the code was 340 lines and required LangChain-specific mental models to understand.

**The rewrite**: stripped out LangChain entirely and called the Anthropic SDK directly. The equivalent logic took 4 hours and 85 lines. The SSE stream was transparent and debuggable. Every error surfaced immediately.

**Lesson**: LangChain is a reasonable choice for complex multi-step chains where its abstractions earn their cost. For a straightforward single-prompt streaming endpoint, it adds complexity without adding value. Evaluate whether the abstraction layer is solving a problem you actually have.

---

## Phase 3: Targeted Improvements (Weeks 4–6)

### Fix 1: Diff View (resolves the retention problem)

The highest-impact change in the entire project wasn't prompt engineering — it was adding a diff view that showed what the AI had written versus what the user had edited.

**Why it mattered**: the diff view made users' own editing visible and meaningful. Instead of AI output that got corrected and discarded, the edited diff became a training artifact — something users could save, refine over time, and eventually feed back into their brand voice profile. It also reinforced that the AI was a collaborator, not a replacement.

**Day-7 retention before diff view**: 12%
**Day-7 retention after diff view**: 31%

```typescript
// Frontend: compute and render the AI-vs-user diff
import { diffWords } from "diff";

interface DiffViewProps {
  aiDraft: string;
  userDraft: string;
}

export function DiffView({ aiDraft, userDraft }: DiffViewProps) {
  const parts = diffWords(aiDraft, userDraft);

  return (
    <div className="diff-view font-mono text-sm leading-relaxed">
      {parts.map((part, i) => {
        if (part.removed) {
          // AI wrote this; user deleted it
          return <span key={i} className="bg-red-100 line-through text-red-600">{part.value}</span>;
        }
        if (part.added) {
          // User added this; AI didn't write it
          return <span key={i} className="bg-green-100 text-green-700">{part.value}</span>;
        }
        // Unchanged
        return <span key={i} className="text-gray-700">{part.value}</span>;
      })}
    </div>
  );
}
```

### Fix 2: Brand Voice Profile Persistence

**Problem**: users had to re-enter their 6-field brand voice form every session. Two users mentioned this directly in feedback. Retention data confirmed it — sessions without a saved profile were 60% shorter and had lower regeneration rates (a proxy for engagement).

**Fix**: store brand voice profiles server-side, keyed by user ID. Simple — one database table, one API endpoint — but the impact on return-visit experience was significant.

```python
# Brand voice profile: save and load
def save_brand_voice(user_id: str, profile: dict) -> None:
    """Persist brand voice settings so returning users don't re-enter them."""
    db.execute(
        "INSERT INTO brand_voice_profiles (user_id, profile_json, updated_at) "
        "VALUES (?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET "
        "profile_json = excluded.profile_json, updated_at = excluded.updated_at",
        (user_id, json.dumps(profile), datetime.utcnow())
    )

def load_brand_voice(user_id: str) -> dict | None:
    """Load saved brand voice profile, or None if not yet configured."""
    row = db.execute(
        "SELECT profile_json FROM brand_voice_profiles WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    return json.loads(row["profile_json"]) if row else None
```

### Fix 3: Adaptive Output Length

**Problem**: short changelogs (2–3 items) produced padded, generic newsletters because the model was implicitly targeting a minimum length. Long changelogs produced drafts that tried to include everything and read like a changelog, not a newsletter.

**Fix**: pass an explicit target length instruction based on changelog item count, and add a hard "do not pad" rule for short inputs.

```python
def build_length_instruction(item_count: int) -> str:
    """
    Return a length instruction calibrated to the changelog size.
    Prevents padding on short changelogs and over-inclusion on long ones.
    """
    if item_count <= 3:
        return (
            "This is a short release. Write a concise newsletter: 2 short paragraphs, "
            "150–200 words total. Do not pad with filler. Do not invent context."
        )
    elif item_count <= 8:
        return (
            "Write a standard newsletter: 3–4 paragraphs, 300–450 words. "
            "Highlight the 2–3 most significant changes. Group minor fixes together."
        )
    else:
        return (
            "This is a major release. Write a structured newsletter: intro paragraph, "
            "3–4 named sections with subheadings, closing paragraph. 500–700 words. "
            "Do not include every item — curate the most impactful ones."
        )
```

### First Paying Customer (Day 18)

On Day 18, a user direct-messaged on Twitter: "I've been using it every week. How do I pay you?" The product had no payment flow. A Stripe link was set up in two hours and the user paid $49/month within the same day.

No conversion funnel, no pricing page — just a user who found the tool valuable enough to ask unprompted. The $49 price point was chosen by asking: "what's 10% of the hourly rate saved per month?" — not by market research.

---

## Final Results

| Metric | Before | After |
|--------|--------|-------|
| Time per newsletter | 4–6 hours | 45 minutes |
| Time-to-first-draft | N/A | ~90 seconds |
| Day-7 retention | N/A (no baseline) | 31% (post-diff view) |
| First paying customer | — | Day 18 |
| Monthly API cost per active user | — | ~$0.93 |
| Price | — | $49/month |

---

## Decision Retrospective

**What we got right**:
1. Building in public on Twitter generated qualified early users — people who understood the problem, not just people who thought AI was cool
2. Shipping a working v1 in two weeks and letting real usage patterns drive the improvement roadmap — the diff view came from watching users, not from planning
3. Model routing (Haiku for outline, Sonnet for draft) cut per-newsletter cost by 61% with no perceptible quality loss for users

**Where we went wrong**:
1. Three days lost to LangChain before switching to raw API calls — the abstraction solved no real problem for this use case and obscured every error
2. No persistence layer in v1 — users losing their brand voice settings between sessions was a quiet, invisible churn driver that didn't show up in feedback but showed up in return-visit rates
3. Underestimated how much output length calibration mattered — padded output on short changelogs was the most common complaint in early user interviews, but it wasn't on the original roadmap at all

**The most important lesson**: the diff view was never in the original spec. It emerged from watching users edit the output and realizing that *the editing behavior itself* was product-valuable — it captured how each team's voice differed from the model's defaults. Features that make user behavior visible often have higher retention impact than features that improve AI output quality. Ship the core loop, then watch what people actually do.

---

*[中文版 (Chinese)](README.zh.md)*
