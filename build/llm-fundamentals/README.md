[中文](README.zh.md) | **English**

# LLM Engineering Fundamentals

> Written from an engineer's perspective, not an academic one. Understanding this material is what lets you know where to look when things break.

---

## Tokens: The Root of All Costs and Limits

### What Is a Token?

A token is not a word. Rough estimates:
- English: 1 token ≈ 0.75 words; 100 tokens ≈ 75 words
- Chinese/CJK: 1 character ≈ 1–2 tokens (Anthropic's newer tokenizer is more efficient)
- Code: keywords are usually 1 token; variable names can be 2–4 tokens

```python
# Count tokens precisely (Anthropic)
import anthropic
client = anthropic.Anthropic()
response = client.messages.count_tokens(
    model="claude-sonnet-4-6",
    messages=[{"role": "user", "content": your_text}]
)
print(f"Token count: {response.input_tokens}")

# Count tokens precisely (OpenAI)
import tiktoken
enc = tiktoken.encoding_for_model("gpt-4o")
tokens = enc.encode(your_text)
print(f"Token count: {len(tokens)}")
```

### Cost Calculation

**Current model pricing (as of June 2026, USD per million tokens)**

| Model | Input | Output | Context window |
|-------|-------|--------|----------------|
| Claude Sonnet 4.6 | $3 | $15 | 1M tokens |
| Claude Haiku 4.5 | $1 | $5 | 200k tokens |
| GPT-4o-mini | ~$0.15 | ~$0.6 | 128k tokens |
| GPT-4o | ~$2.5 | ~$10 | 128k tokens |

**Key insights**:
- Output tokens cost 3–5x more than input tokens — the highest-leverage cost optimization is **controlling output length**
- The Batch API (async processing) offers a 50% discount, suitable for offline evaluation and bulk jobs
- Prompt Caching (Claude): repeated prefix hits cost only 10% of normal input pricing

```python
# Estimate the cost of a single request
def estimate_cost(input_tokens: int, output_tokens: int, model: str) -> float:
    pricing = {
        "claude-sonnet-4-6": (3.0, 15.0),   # (input price, output price) per MTok
        "claude-haiku-4-5": (1.0, 5.0),
    }
    inp_price, out_price = pricing[model]
    return (input_tokens * inp_price + output_tokens * out_price) / 1_000_000
```

---

## Context Window Management

### The Core Constraint

Context window = the maximum number of tokens the model can see in one request. This includes: system prompt + conversation history + current input + space for the output.

**Common trap**: a RAG pipeline with no token counting — retrieved chunks + conversation history + system prompt quietly exceed the limit and trigger an API error.

```python
import anthropic

client = anthropic.Anthropic()

MAX_CONTEXT = 180_000  # Leave 20k for output
SYSTEM_PROMPT = "..."

def safe_messages_create(messages: list, new_message: str) -> str:
    # 1. Count current tokens
    all_messages = messages + [{"role": "user", "content": new_message}]
    token_count = client.messages.count_tokens(
        model="claude-sonnet-4-6",
        system=SYSTEM_PROMPT,
        messages=all_messages
    ).input_tokens

    # 2. If over the limit, drop the oldest turns (keep the most recent N)
    while token_count > MAX_CONTEXT and len(messages) > 2:
        messages = messages[2:]  # Remove oldest turn (one user + one assistant message)
        all_messages = messages + [{"role": "user", "content": new_message}]
        token_count = client.messages.count_tokens(
            model="claude-sonnet-4-6",
            system=SYSTEM_PROMPT,
            messages=all_messages
        ).input_tokens

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=all_messages
    )
    return response.content[0].text
```

---

## API Differences Across the Three Major Providers

Actual code-level differences — not marketing copy.

```python
# ========== OpenAI ==========
from openai import OpenAI
client = OpenAI()

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are an assistant"},  # system is a message
        {"role": "user", "content": "Hello"}
    ],
    temperature=0.7,
    max_tokens=1024       # Optional, has a default value
)
text = response.choices[0].message.content
usage = response.usage   # .prompt_tokens, .completion_tokens


# ========== Anthropic ==========
from anthropic import Anthropic
client = Anthropic()

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,       # Required! No default — omitting this will error immediately
    system="You are an assistant",     # system is a top-level field, not a message
    messages=[
        {"role": "user", "content": "Hello"}
        # Note: only "user" and "assistant" roles exist
    ]
)
text = response.content[0].text    # Note: different structure from OpenAI
usage = response.usage   # .input_tokens, .output_tokens


# ========== Gemini (new SDK: google-genai >= 1.0) ==========
from google import genai as google_genai
client_gemini = google_genai.Client(api_key="...")

response = client_gemini.models.generate_content(
    model="gemini-2.0-flash",
    contents="Hello",
    config={"system_instruction": "You are an assistant"}
)
text = response.text
```

### Key Differences at a Glance

| Difference | OpenAI | Anthropic | Gemini |
|-----------|--------|-----------|--------|
| System prompt | `role: "system"` message | Separate top-level `system` field | `system_instruction` field |
| `max_tokens` | Optional, has default | **Required, no default** | Optional |
| Force tool call | `tool_choice: "required"` | `tool_choice: {"type": "tool", "name": "xxx"}` | Similar to OpenAI |
| Prefill | Not supported | Supported via assistant message | Not supported |
| Streaming structure | `choices[0].delta.content` | `text_stream` iterator | `for chunk in stream: chunk.text` |

---

## Streaming Output

Critical for perceived performance: the difference between a 5s and 0.5s TTFT (Time To First Token) is dramatic to users.

```python
# Anthropic streaming (recommended pattern)
import anthropic

client = anthropic.Anthropic()

with client.messages.stream(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Write a short poem"}]
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)  # flush=True is critical — without it output buffers and won't appear in real time

# Get full usage stats after the stream finishes
final = stream.get_final_message()
print(f"\nInput: {final.usage.input_tokens}, Output: {final.usage.output_tokens}")
```

```python
# OpenAI streaming
from openai import OpenAI

client = OpenAI()
stream = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Write a short poem"}],
    stream=True,
    stream_options={"include_usage": True}  # Must be explicitly enabled to get token usage
)

for chunk in stream:
    if chunk.choices and chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
    if chunk.usage:
        print(f"\nTokens: {chunk.usage.total_tokens}")
```

**Streaming pitfalls**:
- Omitting `flush=True` causes buffered output — users see nothing until the buffer fills
- SSE endpoints must set `Content-Type: text/event-stream` and `Cache-Control: no-cache`
- In streaming mode, wrap the entire iteration in a try/except — not just the initial create call

---

## Cost Control Strategies (Ordered by ROI)

### 1. Model Routing (Highest ROI)

```python
def route_model(query: str) -> str:
    """Use the cheapest model to classify, then route to the appropriate model"""
    classification = client.messages.create(
        model="claude-haiku-4-5",   # Cheapest — use it for classification only
        max_tokens=10,
        messages=[{
            "role": "user",
            "content": f"Classify the complexity of the following question as simple or complex:\n{query}"
        }]
    ).content[0].text.strip().lower()

    if "simple" in classification:
        return "claude-haiku-4-5"      # $1/$5 per MTok
    else:
        return "claude-sonnet-4-6"     # $3/$15 per MTok
```

### 2. Prompt Caching (Claude-Specific — 90% Input Cost Reduction on Cache Hits)

```python
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    system=[{
        "type": "text",
        "text": very_long_system_prompt_or_document,  # Long, static content
        "cache_control": {"type": "ephemeral"}        # Mark as cacheable
    }],
    messages=[{"role": "user", "content": user_query}]
)
# First request: billed normally (writes to cache)
# Subsequent cache hits: input tokens charged at 10% of normal price
# Note: ephemeral cache TTL is 5 minutes — gaps longer than that require re-writing the cache
```

### 3. Output Length Control

```python
# Constrain output length directly in the prompt
"Answer in no more than 3 sentences"
"Return only JSON — no explanation"

# Use stop sequences to terminate early
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=500,
    stop_sequences=["</answer>"],  # Stop as soon as this token is encountered
    ...
)
```

### 4. Semantic Caching for Common Queries

```python
import hashlib
import redis

cache = redis.Redis()

def cached_llm(prompt: str, model: str = "claude-haiku-4-5") -> str:
    key = hashlib.sha256(f"{model}:{prompt}".encode()).hexdigest()
    if cached := cache.get(key):
        return cached.decode()
    result = llm_call(prompt, model)
    cache.setex(key, 3600, result)
    return result
```

---

## Why Models Hallucinate

Understanding the cause is what lets you design the right defenses:

1. **Training data cutoff**: the model has no knowledge of recent events, but will still answer confidently
2. **Unclear knowledge boundaries**: the model doesn't know what it doesn't know — it lacks reliable metacognition
3. **Statistical tendency**: the model is optimized to generate text that *looks* plausible, not text that is *confirmed* accurate

**Engineering-layer defenses**:
- Provide context (RAG) so the model answers from documents, not memory
- Explicitly tell the model to say "I don't know" when it doesn't know
- Run programmatic validation on critical outputs (execute the code, call the API to verify)
- Do not use AI to answer questions requiring precise figures (prices, dates, statistics)

---

*[中文版 (Chinese)](README.zh.md)*
