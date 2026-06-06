[中文](README.zh.md) | **English**

# AI Product Cold Start Guide

> Andrew Chen test: grounded in *The Cold Start Problem* framework — specific paths, not generic advice.

---

## The Core Mental Model

The cold start problem in its essence: **every new product begins with zero users, and a product with zero users has no value for new users.** You need a way to break this paradox.

**Why AI products are different**: most single-user AI tools don't face the classic chicken-and-egg problem. Their cold start challenge is primarily about **trust** — users don't trust an unproven AI tool.

**The exception**: AI products whose quality depends on user feedback loops (recommendation algorithms, personalization models, RAG systems with user feedback) face a data cold start problem — no data → poor model performance → no users → no data. These products need to bootstrap with external datasets or manual annotation to fill the early data gap.

---

## Two Fundamental Paths

Based on the YC framework (Michael Siebel / Sam Altman):

### Path A: Hair on Fire

The problem already exists. Users are suffering through it. You offer a better solution.

**Validation signals:**
- Users are already solving this problem with inefficient workarounds (manual Excel, copy-paste, outsourcing)
- Users can immediately calculate how much time or money you save them
- In sales conversations, the customer asks about pricing — you're not chasing them

**Cold start strategy**: go directly to users who are in pain. Speed over polish. You don't need to educate the market, just prove you're better than what they're doing today.

```
Ways to find these users:
- Industry forums and communities: find threads where people are complaining about this problem; reach out directly
- LinkedIn targeted search: filter by job title and industry to find people who likely have this pain
- Slack/Discord communities: join where your target users gather and observe what they're struggling with
```

### Path B: Future Vision (Creating New Demand)

Users don't know they need this yet. The product has to create awareness. Harder, requires more resources.

**Validation signals:**
- First-time users say "I never thought this was possible"
- You need to explain the value before users get it

**Cold start strategy**: find a "stepping stone" market. Don't attack your ultimate market directly — build credibility and case studies in a smaller, more penetrable segment first.

---

## Where to Find Your First Users

Organized by product type:

| Product Type | First User Source | Concrete Action |
|-------------|------------------|-----------------|
| **B2C tools** (writing/coding/design) | Product Hunt + communities | PH launch + targeted Reddit/Twitter exposure |
| **B2B SaaS** | Founder direct sales | Make 50 calls personally; land 3–5 design partners |
| **Vertical AI** | Industry communities + KOLs | Enter the industry circle; work deeply with 5 opinion leaders |
| **Developer tools** | GitHub + tech communities | Open-source a core component; use stars to build trust, then commercialize |
| **Internal enterprise tools** | Start inside your own company | Solve your own company's problem first, then sell outward |

### What Makes a Good Early Adopter

Not all users make good early adopters. The right profile:

- Has a specific, acute pain point (already spending money or significant time trying to solve it)
- Willing to accept an imperfect product in exchange for early access
- Gives detailed feedback, not just "looks good"
- Has influence in the target market (their success becomes a referral to peers)

**How to find them**: look for people already using complex, cobbled-together solutions to solve this problem. They've already proven the problem exists and that they're motivated to fix it.

---

## Cold Start Execution Steps

### Weeks 1–2: Manual Validation

Before you have a product, simulate it manually:

```
Goal: find 5 real users willing to pay for this

Steps:
1. Define the problem you can solve by hand
2. Talk to 10–20 target users for 30 minutes each (ask questions, don't pitch)
3. Offer a manual service, and charge for it (even $50/month)
4. Observe: do they come back unprompted?

Don't:
- Spend 3 months building a product before talking to users
- Offer it for free (free feedback is unreliable)
- Only test with friends and colleagues
```

### Weeks 3–8: First Real Users

```
Goal: 10–50 users genuinely using the product

Channel selection principles:
- Choose channels you can reach directly (not ads)
- Prioritize high-intent channels (users already searching for a solution)
- Focus on one channel at a time; expand only after validating it works

High-intent channels (roughly ordered by difficulty):
① Your existing network (easiest, highest quality)
② Communities and forums where target users gather (medium)
③ SEO / content marketing (slow, but scalable)
④ Paid ads (fast, but only invest once you know LTV)
```

### Months 2–3: Find a Repeatable Acquisition Path

```
Criteria for declaring success:
- Do different users from the same channel have a consistent activation rate?
- Has the user retention curve flattened?
- Are > 20% of new users coming from word of mouth?

If none of these: don't scale acquisition yet — fix the product
If all three are true: start systematically investing in this channel
```

---

## 5 Common Cold Start Failure Modes

### 1. Chasing Virality Too Early

Andrew Chen's explicit warning: **don't pursue viral growth until the retention curve has already flattened.**

The Viddy case: high viral coefficient paired with near-zero retention. User numbers collapsed as soon as the viral effect exhausted itself. Virality can't compensate for a retention problem — it just burns cash faster.

### 2. Platform Dependency

BranchOut rode Facebook Platform to roughly 40M MAU at its peak. Four months later, Facebook changed its rules — user numbers fell over 90%.

Using a platform to bootstrap is fine, but you must quickly build a direct line to users (email list, independent community).

### 3. Conflating Registrations with Activations

A Product Hunt launch can deliver 2,000+ sign-ups, but 80% of those users will never actually use the product.

**Always track activation, not registrations.** Activation = completing the core action in the product (not creating an account).

### 4. Ignoring Channel Quality Differences

User quality varies enormously by channel. Social media ad users and SEO users can differ in retention by a factor of 5.

```python
# Track user quality by acquisition channel
metrics_by_channel = {
    "product_hunt": {"activation_rate": 0.15, "d7_retention": 0.08},
    "google_search": {"activation_rate": 0.45, "d7_retention": 0.25},
    "twitter_organic": {"activation_rate": 0.22, "d7_retention": 0.12},
    "referral": {"activation_rate": 0.60, "d7_retention": 0.35},  # word-of-mouth is highest quality
}
# Conclusion: Google Search and referral are worth investing in; Twitter/PH quality is low
```

### 5. Over-Relying on One-Time Exposure

PR releases, media coverage, and YC batches are one-time events — not loops. Once spent, they're gone.

**The goal of cold start is finding a repeatable acquisition loop, not accumulating exposure events.**

---

## Product–Channel Fit

Andrew Chen's framework: different product types fit different growth channels. A mismatch wastes resources.

| AI Product Type | Right Acquisition Channels | Wrong Channels |
|----------------|---------------------------|----------------|
| Personal productivity tool | SEO/content, Product Hunt, social media | Sales team, enterprise advertising |
| Enterprise B2B tool | Direct sales, industry conferences, referrals | Social media ads, Product Hunt |
| Developer tool | GitHub, technical blogs, open source | TV ads, social media |
| Vertical industry AI | Industry communities, KOLs, trade media | General ad platforms |

---

## Launch Checklist

```
Clarify before starting cold start:
□ What does your early adopter profile look like? (specific role, company size, pain point)
□ How are they currently solving this problem? (validates the problem exists)
□ Where do they gather? (identifies reach channels)
□ Can you deliver value manually within 48 hours? (validates feasibility)
□ What is your activation definition? (not sign-up — completing the core action)
```

---

*[中文版 (Chinese)](README.zh.md)*
