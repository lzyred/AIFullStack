[中文](README.zh.md) | **English**

# Lean Validation Framework: Prove the Biggest Assumption with the Least Resources

> The Sam Altman test: before you spend months building a product, prove that someone genuinely needs it.

---

## The Core Insight

**You're not validating a product. You're validating assumptions.**

Every product rests on a stack of assumptions. Find the most fragile one, and disprove or confirm it at the lowest possible cost.

---

## Your Assumption Stack

```
Users have this problem (existence assumption)
    ↓
The problem is severe enough that users will change their current behavior (severity assumption)
    ↓
Users will pay money to solve it (monetization assumption)
    ↓
We can acquire users in a sustainable way (distribution assumption)
    ↓
Our solution actually solves the problem (technical assumption)
```

**Most people start validation at the bottom (build the product first). Start at the top (validate that the problem exists first).**

The most fragile assumption is almost always "users will pay" — and it's where the most self-deception happens.

---

## Three-Step Validation

### Step 1: Problem Validation (no product needed)

**Goal**: find 5 people who are genuinely suffering from this problem.

**Method**: talk to 20 target users for 30 minutes each. Only ask questions — don't explain what you're building.

**Good questions**:
- "When did you last run into [this problem]?" (tests frequency)
- "How did you handle it?" (reveals competitors and effort)
- "How much time did it take?" (quantifies the pain)
- "What tools do you use for this today?" (maps the existing solution landscape)

**Questions to avoid**:
- "What do you think of our product?" (you don't have one)
- "Would you use AI to do this?" (too abstract)
- "If a product like this existed, how much would you pay?" (hypothetical answers are unreliable)

**Pass criteria**: at least 5 of the 20 people describe nearly identical pain, and it happens at least once a week.

---

### Step 2: Value Validation (manual simulation)

**Goal**: prove that your solution actually works and that users will pay for it — without a real product.

**The Wizard of Oz method**:

```
You manually complete the user's task using ChatGPT / Claude
    ↓
Show the user the "product" output (which you produced by hand)
    ↓
Watch their reaction: do they want to use it again? Would they refer it to a colleague?
    ↓
Charge for it (even $50/month) — free feedback is worthless
```

**The Airbnb example**: the founders personally photographed hosts' apartments and rewrote listing descriptions by hand. That manual process exposed every real friction point they never would have anticipated from behind a keyboard.

**Pass criteria**: 3 users are willing to pay before a real product exists, and they ask to continue using it without you following up.

---

### Step 3: Scale Validation (minimal product)

**Goal**: automate the single most-repeated step from manual validation, and check whether scaling is viable.

**Principles**:
- Not a "complete product" — the smallest version that addresses the core pain point
- Convert the 3 users from manual validation into your first product users
- Measure activation rate and D7 retention, not user count

```
Week 1–2:   Problem validation (20 conversations)
Week 3–4:   Value validation (3 users, manual delivery, paid)
Week 5–8:   Minimal product (automate the core step, convert the 3 users)
Month 3:    First user paying through the product itself — no manual help from you
```

---

## The Mom Test: Asking the Right Questions

Rob Fitzpatrick's core insight: anyone who's being polite will give you a positive answer. You learn nothing from politeness.

**The Mom Test**: if your mom can't argue with the question, it's a good question.

```
❌ Bad questions:
"What do you think of our idea?"
"Do you think people would pay for this?"
"Would you use this product?"

✓ Good questions:
"How long did it take you to handle this last time?"
"What's your current approach to solving this?"
"How much do you spend on this per month?"
"Is this the biggest problem you're dealing with right now?"
```

**The rule**: only ask about past behavior, never about future intentions. People are very bad at predicting what they'll actually do.

---

## How to Avoid Fooling Yourself

Sam Altman's observation: he used to hate criticism. Now he assumes all criticism is true by default, then decides whether to act on it. **Self-belief has to coexist with self-awareness.**

### Five Anti-Confirmation-Bias Practices

**1. Run a premortem**:

Before you start, write down: "If this project fails, what's the most likely reason?" This thought experiment forces you to see your blind spots.

**2. Set falsifiable metrics up front**:

Before validation begins, write this down:

```markdown
My core assumption: [target user] will pay [price] for [solution]

Falsification condition: if fewer than [N] out of [sample size] target users
are willing to pay within [timeframe], the assumption is invalid

Today's date: [date]
Decision deadline: [date + 4 weeks]
```

**3. Distinguish signal from noise**:

| Noise (means nothing) | Signal (worth acting on) |
|-----------------------|--------------------------|
| "This feature is interesting" | User pays on the spot |
| "I'll use it when it's finished" | User proactively refers a colleague |
| Investor says "great direction" | User comes back without a nudge |
| Press coverage | User apologizes for the rough edges and keeps using it anyway |

**4. Find your harshest critics**:

Actively seek out the people most likely to invalidate your judgment — competitors, the most experienced practitioners in the field, the most conservative users in your target segment.

**5. Watch behavior, not attitudes**:

"User said they would use it" is worth almost nothing. "User actually used it" is the real signal. When running user tests, only log what people did — not what they said.

---

## Continue vs. Pivot Decision Criteria

| User behavior | Interpretation |
|---------------|----------------|
| Returns unprompted to use it again | Continue — core value is real |
| Pays but is inactive | Danger — you're not solving a high-frequency pain point |
| Won't pay but uses it frequently | Pricing or business model issue — adjustable |
| Neither uses nor pays | Pivot — the value proposition doesn't hold |
| Proactively refers others | Strong signal to continue |
| Founders don't use their own product | Stop and reassess immediately — a critical red flag |

**Paul Graham's "organic growth" test**: if you have to keep pushing to get users to return, the product has no momentum of its own. When you have real PMF, users pull you forward.

---

## Validation Checklist

```
Before validation begins:
□ Write down your 3 most important assumptions
□ Write down a falsification condition for each (specific numbers)
□ Set a decision deadline

During validation:
□ After every user conversation, immediately log: what they said, what they did
□ Record behavior only — not attitudes
□ Once 3 people proactively pay, record the assumption as confirmed

After validation ends:
□ Evaluate against your falsification conditions — don't move the goalposts
□ If an assumption is disproved: find out why, then design a new assumption to test
□ If an assumption holds: advance to validating the next assumption in the stack
```

---

*[中文版 (Chinese)](README.zh.md)*
