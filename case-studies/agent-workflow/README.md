[中文](README.zh.md) | **English**

# Case Study: AI-Powered Sales Outreach Automation

> The real decision-making process from zero to production — including the pivot that saved the project.

---

## Background

**Scenario**: a 5-person B2B SaaS startup with a single SDR (Sales Development Representative) responsible for all outbound outreach. The SDR was spending 3+ hours every day on two tasks: researching prospects (company background, recent news, funding rounds, pain points) and writing personalized cold emails based on that research. With only 24 hours in a day, this capped outreach at around 8 emails.

**Goal**: automate prospect research and first-draft email generation. The SDR reviews the output, edits if needed, and hits send. Human stays in the loop; AI handles the grunt work.

**Starting constraints**:
- Team: 5 people, no dedicated ML engineer
- Budget: under $300/month for API costs
- Tooling: Python backend, no existing automation infrastructure
- Volume target: 35+ personalized emails per day (from 8)

---

## Phase 1: Architecture Decision (Week 1)

### The Question: Agent or Workflow?

The team read the Anthropic docs, watched some demos, and had an internal debate. The initial instinct was **Agent** — it seemed more powerful and flexible. The reasoning at the time:

- "We don't know exactly what research steps we'll need for every prospect. An agent can decide dynamically."
- "Agents can handle edge cases we haven't thought of yet."
- "It feels more future-proof."

This reasoning was understandable but wrong. Here is how the team thought through it:

| Factor | Agent | Workflow |
|--------|-------|---------|
| Steps known in advance? | No | **Yes** — research → summarize → draft |
| Needs dynamic tool selection? | Maybe | **No** — same tools every time |
| Output must be consistent? | Hard | **Yes, critical** |
| Failure mode acceptable? | Unpredictable | **Deterministic, catchable** |
| Auditability required? | Difficult | **Easy** |

The team ultimately chose **Agent for the prototype** (Week 1), telling themselves they'd switch if it became a problem. It became a problem.

---

## Phase 2: The Agent Prototype (Weeks 1–2)

### Architecture

The first version was a ReAct-style agent with three tools:

```python
import anthropic

client = anthropic.Anthropic()

tools = [
    {
        "name": "web_search",
        "description": "Search the web for recent news, press releases, or information about a company or person.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_company_info",
        "description": "Retrieve structured company data: founding year, headcount, funding stage, industry, tech stack.",
        "input_schema": {
            "type": "object",
            "properties": {
                "company_name": {"type": "string"},
                "domain": {"type": "string"}
            },
            "required": ["company_name"]
        }
    },
    {
        "name": "draft_email",
        "description": "Write a personalized cold email given a research summary and prospect context.",
        "input_schema": {
            "type": "object",
            "properties": {
                "prospect_name": {"type": "string"},
                "company_name": {"type": "string"},
                "research_summary": {"type": "string"},
                "pain_point": {"type": "string"},
                "our_value_prop": {"type": "string"}
            },
            "required": ["prospect_name", "company_name", "research_summary", "pain_point"]
        }
    }
]

def run_outreach_agent(prospect: dict) -> str:
    """Original agent-based approach — let the model decide the steps."""
    messages = [
        {
            "role": "user",
            "content": (
                f"Research this prospect and write a personalized cold email.\n"
                f"Prospect: {prospect['name']} at {prospect['company']} ({prospect['domain']})\n"
                f"Our product: {prospect['our_product_context']}"
            )
        }
    ]

    # Agentic loop — model decides when it has enough information
    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            tools=tools,
            messages=messages
        )

        if response.stop_reason == "end_turn":
            # Extract final text
            return next(b.text for b in response.content if hasattr(b, "text"))

        # Execute tool calls and continue
        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = execute_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result
                })
        messages.append({"role": "user", "content": tool_results})
```

### What Went Wrong in Production

The agent worked fine in demos. It fell apart in the first week of real use.

**Problem 1: Hallucinated company facts**

The agent would confidently include facts that weren't in any search result — funding amounts, headcount figures, product features, even quotes attributed to the CEO. These were fabricated. The SDR caught two of these before sending. One slipped through.

The email that slipped through referenced a "recent Series B" that the company had not raised. The prospect replied to correct the error. That conversation was over before it started.

```
# Real example of a hallucinated email opening (paraphrased):
"Congrats on your recent Series B — scaling a 200-person engineering team 
is exactly when infrastructure debt starts to compound..."

# Reality: the company had 34 employees and had raised a seed round 3 years prior.
```

**Problem 2: Non-deterministic execution paths**

On identical inputs, the agent sometimes called `web_search` twice, sometimes three times, occasionally skipped `get_company_info` entirely. There was no consistent logic — just the model's judgment each run. This made the output quality variance too high to trust.

**Problem 3: Cost unpredictability**

Token usage per prospect ranged from 4,000 to 18,000 tokens depending on how many tool loops the agent decided to run. Impossible to budget.

**Problem 4: No auditability**

When the SDR asked "why did it say X?", there was no good answer. The agent's reasoning was buried in an opaque loop. Debugging required replaying the entire conversation.

---

## Phase 3: Pivot to Deterministic Workflow (Weeks 3–4)

### The Decision

After the Series B incident, the team held a postmortem. The conclusion was uncomfortable but clear: the problem wasn't a bug — it was the architecture. An agent that can decide its own steps will also decide wrong steps. For a task with a known, fixed sequence of operations, a deterministic workflow is the correct tool.

The refactor took three days.

### New Architecture: Prompt Chaining + Parallelization

```
Prospect input
  ├── [Parallel] web_search("company name recent news")
  ├── [Parallel] web_search("company name funding hiring")
  └── [Parallel] get_company_info(company_name, domain)
        ↓
  [Haiku] Summarize all research → structured JSON
        ↓
  [Human Gate] SDR reviews research summary, approves or edits
        ↓
  [Sonnet] Draft personalized email from approved summary
        ↓
  [Human Gate] SDR reviews draft, edits if needed, sends
```

**Why Haiku for research summarization, Sonnet for email drafting**: summarization is a compression task — extract and structure the facts. It doesn't require creative judgment. Haiku does this reliably at ~10x lower cost. Email drafting requires tone, persuasion, and nuanced personalization — that's where Sonnet's quality justifies the cost.

### Before/After Code Comparison

**Before (Agent — non-deterministic):**

```python
# Agent decides what to do and when. No guaranteed steps.
def run_outreach_agent(prospect: dict) -> str:
    messages = [{"role": "user", "content": build_prompt(prospect)}]
    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            tools=tools,
            messages=messages
        )
        if response.stop_reason == "end_turn":
            return extract_text(response)
        # ... agentic loop continues arbitrarily
```

**After (Workflow — deterministic):**

```python
import asyncio
import anthropic
import json

client = anthropic.Anthropic()

# Step 1: Parallel research — always exactly these three calls, no more, no less
async def research_prospect(prospect: dict) -> dict:
    """Run all research in parallel. Fixed inputs, fixed outputs."""
    loop = asyncio.get_event_loop()

    # All three calls fire simultaneously
    news_result, funding_result, company_result = await asyncio.gather(
        loop.run_in_executor(None, web_search, f"{prospect['company']} recent news 2024"),
        loop.run_in_executor(None, web_search, f"{prospect['company']} funding hiring expansion"),
        loop.run_in_executor(None, get_company_info, prospect['company'], prospect['domain'])
    )

    return {
        "recent_news": news_result,
        "funding_hiring": funding_result,
        "company_data": company_result
    }

# Step 2: Summarize with Haiku — cheap, fast, deterministic
def summarize_research(prospect: dict, raw_research: dict) -> dict:
    """
    Haiku condenses raw research into a structured JSON summary.
    CRITICAL: prompt instructs the model to only use information present in the
    research data. If a fact is not in the data, omit it — never infer or assume.
    """
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": f"""Summarize the following research into a structured JSON object.
Only include facts that are explicitly present in the research data below.
If you cannot find the answer to a field, use null — do not guess.

Research data:
{json.dumps(raw_research, indent=2)}

Output this exact JSON schema:
{{
  "company_name": string,
  "founded_year": number | null,
  "headcount_estimate": string | null,
  "funding_stage": string | null,
  "recent_news_headline": string | null,
  "likely_pain_points": [string],
  "confidence_note": string  // flag anything uncertain
}}"""
        }]
    )
    return json.loads(response.content[0].text)

# Step 3: Human gate — mandatory, non-skippable
def human_review_research(prospect: dict, summary: dict) -> dict:
    """
    SDR sees the research summary before the email is drafted.
    They can correct facts, add context, or abort.
    This gate exists because the email is only as good as the research.
    """
    print(f"\n--- Research Summary for {prospect['name']} at {prospect['company']} ---")
    print(json.dumps(summary, indent=2))
    print("\nOptions: [a]pprove / [e]dit / [s]kip this prospect")
    choice = input("> ").strip().lower()

    if choice == "s":
        return None  # Prospect skipped, no email drafted
    elif choice == "e":
        correction = input("Enter correction (JSON patch or plain text note): ")
        summary["sdr_correction"] = correction
    # choice == "a" falls through with summary unchanged

    return summary

# Step 4: Draft email with Sonnet — only runs on approved research
def draft_email(prospect: dict, approved_summary: dict) -> str:
    """
    Sonnet writes the email. It only has access to the approved, human-verified
    summary — not the raw research. This prevents hallucination leakage.
    """
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{
            "role": "user",
            "content": f"""Write a concise, personalized cold email for a B2B SaaS sales outreach.

Prospect: {prospect['name']}, {prospect['title']} at {prospect['company']}
Verified research summary:
{json.dumps(approved_summary, indent=2)}

Our product: {prospect['our_product_context']}

Requirements:
- Subject line + body (under 150 words)
- Reference ONE specific, verified fact from the research summary
- Do not invent or infer any facts not in the summary
- Conversational, not salesy
- Clear call to action: 15-minute call"""
        }]
    )
    return response.content[0].text

# Step 5: Final human gate — SDR approves before send
def human_review_email(prospect: dict, draft: str) -> str | None:
    """SDR sees the draft. Approve, edit in-place, or discard."""
    print(f"\n--- Email Draft for {prospect['name']} ---")
    print(draft)
    print("\nOptions: [a]pprove and send / [e]dit / [d]iscard")
    choice = input("> ").strip().lower()

    if choice == "d":
        return None
    elif choice == "e":
        print("Paste your edited version (end with a line containing only 'END'):")
        lines = []
        while True:
            line = input()
            if line == "END":
                break
            lines.append(line)
        return "\n".join(lines)
    return draft  # approved as-is

# Main workflow — fixed, auditable, reproducible
async def run_outreach_workflow(prospect: dict) -> dict:
    """
    Every prospect goes through exactly these steps in exactly this order.
    Each step's output is logged. Any step can be re-run independently.
    """
    # 1. Research (parallel)
    raw_research = await research_prospect(prospect)

    # 2. Summarize (Haiku)
    summary = summarize_research(prospect, raw_research)

    # 3. Human reviews research
    approved_summary = human_review_research(prospect, summary)
    if approved_summary is None:
        return {"status": "skipped", "prospect": prospect["name"]}

    # 4. Draft email (Sonnet)
    draft = draft_email(prospect, approved_summary)

    # 5. Human reviews email
    final_email = human_review_email(prospect, draft)
    if final_email is None:
        return {"status": "discarded", "prospect": prospect["name"]}

    # 6. Send (or queue for sending)
    send_email(prospect["email"], final_email)
    return {"status": "sent", "prospect": prospect["name"], "email": final_email}
```

### Key Design Decisions in the Workflow

**Why `confidence_note` in the research summary**: the Haiku summarization prompt asks the model to explicitly flag anything it's uncertain about. This surfaces low-confidence fields before the human review gate, so the SDR knows where to double-check rather than trusting everything equally.

**Why Sonnet only sees the approved summary, not the raw research**: raw search results contain noise, contradictions, and outdated data. If Sonnet has access to raw results, it may pull in unverified facts. The approved summary is the SDR-verified source of truth. Sonnet drafts from truth, not from noise.

**Why two human gates, not one**: the research review and the email review catch different failure modes. The research gate catches factual errors. The email gate catches tone, framing, and context errors that only the SDR can judge. Collapsing them into one gate was tried and reverted — SDRs missed research errors when they were distracted by reading the email.

---

## Final Results

| Metric | Before | After (Workflow) |
|--------|--------|-----------------|
| SDR research + draft time | 3 hours/day | 25 minutes/day |
| Outreach volume | 8 emails/day | 35 emails/day |
| Personalization score (internal rubric, 1–5) | 3.2 avg | 3.8 avg |
| Reply rate (30-day rolling) | 4.1% | 6.7% |
| Factual errors caught at review gate | N/A | 2–3 per week (caught before send) |
| Monthly API cost | $0 | ~$180 |

**Note on reply rate**: attribution is imperfect. Higher volume + better research quality both contributed. The team is running a controlled test to isolate the research quality effect.

---

## Decision Retrospective

**What we got right**:
1. Ran the agent prototype first rather than debating in theory — the production failure made the pivot decision obvious and unanimous
2. Two-gate human review from the start — this design choice prevented at least three near-disasters during the workflow phase
3. Model tiering (Haiku for summarization, Sonnet for drafting) — kept costs predictable without sacrificing email quality

**Where we went wrong**:
1. Should not have shipped the agent to real prospects. The prototype should have been tested internally on fake prospect data for a full week before any real outreach. One hallucinated email was one too many.
2. The agent's tool schemas were too permissive — `draft_email` accepted a freeform `research_summary` string, which meant the model could put anything in it including fabricated facts. The workflow's structured JSON summary with explicit `null` for unknown fields was the correct design from day one.
3. Underestimated how much the SDR's review time would drop after the workflow was stable. The initial estimate was 45 minutes/day for review. It settled at 25 minutes because the research quality became consistent and predictable.

**The most important lesson**: "Agent" is not a synonym for "powerful" — it's a synonym for "the model decides." For a task where you know exactly what steps should happen and in what order, a deterministic workflow is more reliable, more auditable, and cheaper. The agent prototype had more *capability* on paper. The workflow had more *reliability* in production. Reliability won.

A hallucinated fact in a cold email destroys trust in seconds. Trust takes weeks to rebuild. Design for that failure mode first.

---

*[中文版 (Chinese)](README.zh.md)*
