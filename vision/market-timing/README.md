[中文](README.zh.md) | **English**

# Market Timing for AI Products

> The Sam Altman test: timing is part of product strategy, not a matter of luck.

---

## The Current Opportunity Window

**Where we are in 2024–2026**: AI's foundational capabilities have crossed the threshold of practical usefulness, but workflow transformation across most industries is only just beginning.

The analogy: 2008 mobile internet — iPhone shipped, App Store open, but 99% of industry-specific applications hadn't been built yet. That was a massive window. AI is in the same position now.

**Sam Altman's compounding lens**: choose markets with exponential growth characteristics, not linear ones. AI capability itself is growing exponentially — the earlier you establish a foothold in the right vertical, the deeper your moat becomes.

---

## Three Opportunity Categories

```
Technology mature × Market awareness mature  = Red ocean (don't enter)
  → Too many competitors, price wars, no meaningful differentiation

Technology mature × Market awareness lagging = Golden window (enter now)
  → Technical barrier is lower, but no standard solution exists yet

Technology immature × Market awareness mature = Wait (don't enter too early)
  → Demand is clear but technology isn't good enough yet — you'd be burning cash waiting for the tech to catch up
```

### Current Golden Window Areas

Technology has crossed the threshold, but most industries haven't established a standard solution:

**Vertical knowledge work automation**:
- Legal: contract analysis, legal research, document preparation
- Healthcare: clinical notes, patient communication, insurance claims
- Finance: bookkeeping, report generation, compliance review

**"Big company capabilities" for small businesses**:
- Large companies have marketing teams; small ones don't → AI marketing tools
- Large companies have in-house legal; small ones don't → AI legal assistance
- Large companies have data analysts; small ones don't → AI data analysis

**AI as a layer embedded in existing workflows**:
- Don't ask users to change how they work
- Add an AI layer on top of tools they already use (ERP/CRM/document tools)
- Integration beats replacement

---

## Timing Analysis by Horizon

### Build now (2026)

- **Replace repetitive cognitive labor**: format conversion, data extraction, first-draft generation, summarization
- **Give small businesses access to capabilities that previously required specialists**
- **AI embedded in existing workflows** (lowest friction, highest adoption readiness)
- **Vertical applications driven by private data** (internal knowledge bases, industry-specific datasets)

### Wait 12–24 months

- **Fully reliable autonomous agents**: error rates are still too high for high-stakes decision scenarios
- **Applications requiring real-time physical world perception**: video understanding, robotics
- **Deeply personalized AI companions**: need longer data accumulation to be credible

---

## Milestones: 6 Months, 1 Year, 3 Years

### 6 months: PMF validation

**Goal**: find 10–20 real paying users and understand exactly why they're paying.

Key questions:
- Which type of user paid fastest? (That's your core customer profile)
- In what scenarios do they use it, and how often?
- Why did they choose you over other options?

**If you don't have any paying users after 6 months**: it's not time to push harder — it's time to revisit your positioning.

### 1 year: Distribution model validation

**Goal**: find a repeatable acquisition channel that doesn't depend on the founders' personal networks.

Key questions:
- Is there one channel consistently delivering quality users?
- What's your referral rate? (>20% is a healthy signal)
- Have competitors started entering? (Means you've validated a real market)

**If you still don't have a repeatable acquisition channel after 1 year**: positioning is likely the issue — users don't know how to explain your value to someone else.

### 3 years: Moat formation

**Goal**: build real competitive barriers, not just feature differentiation.

Three moat directions:
1. **Proprietary data**: personalized models from user behavior, or exclusive industry data
2. **Workflow lock-in**: deep system integration makes switching extremely costly
3. **Accumulated switching costs**: context, history, and configuration users have built up over time

**If no moat has formed after 3 years**: you face commoditization risk — continued improvements to foundation models will erase whatever differentiation you have.

---

## The "Build Now vs. Wait" Decision

Use this framework to evaluate timing:

```python
def should_build_now(opportunity: dict) -> str:
    checks = {
        "technology_ready": "Can current LLM capability solve 80% of this problem?",
        "market_awareness": "Are target users already looking for a solution?",
        "willingness_to_pay": "Is anyone already paying for something similar (even an inefficient version)?",
        "competitive_window": "Are there no well-funded competitors working on this yet?",
    }

    yes_count = sum(1 for k in checks if opportunity.get(k) == True)

    if yes_count >= 3:
        return "Enter now — timing is right"
    elif yes_count == 2 and opportunity.get("technology_ready"):
        return "Can enter, but move fast — the window may be short"
    else:
        return "Wait — technology or market isn't ready yet"
```

---

## What Not to Do

**Waiting for technology to be "perfect" before starting**:

AI will never be "perfect." 80% capability today is already sufficient for most real-world scenarios. Wait for 99%, and the market will be taken.

**Chasing the latest technology hype**:

Every few months there's a new AI trend (Multimodal, Reasoning, Agents...). Don't change direction every time to chase the latest capability — unless it directly solves your core use case.

**Underestimating the value of execution speed**:

The timing window exists, but it isn't infinite. Wiz's example: Israeli engineers coded during the day and ran US sales calls at night — from $0 to $2.8M in a single quarter, reaching $100M ARR in 18 months. During a golden window, execution speed is itself a moat.

---

*[中文版 (Chinese)](README.zh.md)*
