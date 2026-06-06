[中文](llm-providers.zh.md) | **English**

# LLM Provider Comparison

> How to choose between OpenAI, Anthropic, and Gemini for the same use case. Engineering decisions, not marketing.

---

## Bottom Line Up Front

There's no "best" model — only the model that best fits your specific use case.

**Quick selection guide**:

| Use case | Recommendation |
|----------|----------------|
| General conversation / Q&A | Claude Sonnet 4.6 or GPT-4o — difference is negligible |
| Long document processing (>100k tokens) | Claude (1M context); Gemini 2.5 Pro as backup |
| Structured data extraction | OpenAI (Structured Outputs is the most mature) |
| Code generation / review | Claude Sonnet 4.6 or GPT-4o |
| Cost-sensitive, high-volume tasks | Claude Haiku 4.5 or GPT-4o-mini |
| Complex reasoning | Claude Opus 4 (latest) or GPT-4o |
| Safety / compliance-sensitive scenarios | Claude (high refusal rate, but also higher false-refusal rate) |

---

## API Differences (These Will Bite You in Code)

Each of these differences can cause real integration pain:

| Difference | OpenAI | Anthropic | Gemini |
|------------|--------|-----------|--------|
| System prompt | `role: "system"` message | Separate `system` field | `system_instruction` |
| `max_tokens` | Optional (has a default) | **Required (no default)** | Optional |
| Message roles | user / assistant / system | user / assistant (only two) | user / model |
| Structured output | Structured Outputs (native, most reliable) | Forced tool use | Similar to OpenAI |
| Streaming event format | `choices[0].delta.content` | `text_stream` iterator | `.text` |
| Prefill (assistant turn pre-fill) | Not supported | **Supported** | Not supported |
| Tool choice | `"required"` / `"auto"` | `{"type": "tool", "name": "xxx"}` | Similar to OpenAI |
| Image input | `image_url` or base64 | base64 / URL (URL must be publicly accessible) | Similar to Anthropic |

---

## Cost Comparison (as of June 2026)

Prices in USD per million tokens (input / output):

| Model | Input | Output | Context | Best for |
|-------|-------|--------|---------|----------|
| Claude Haiku 4.5 | $1 | $5 | 200k | High-volume, classification, simple tasks |
| Claude Sonnet 4.6 | $3 | $15 | 1M | General production workloads |
| Claude Opus 4 (verify model ID at anthropic.com) | $5 | $25 | 1M | Complex reasoning, high-stakes tasks |
| GPT-4o-mini | ~$0.15 | ~$0.6 | 128k | Extremely cost-sensitive scenarios |
| GPT-4o | ~$2.5 | ~$10 | 128k | General use |
| Gemini 2.0 Flash | ~$0.075 | ~$0.3 | 1M | Cost-sensitive + long documents |
| Gemini 2.5 Pro | ~$1.25 | ~$10 | 1M | Multimodal + long documents + complex reasoning |

**Cost control tactics**:
- Anthropic Prompt Caching: repeated prefixes hit the cache at 10% of standard input price
- Anthropic / OpenAI Batch API: async processing at 50% discount
- Model routing: use Haiku / GPT-4o-mini for classification; route complex tasks to Sonnet / GPT-4o

---

## Capability Differences (From Real Testing)

### Instruction Following

Claude handles XML tag semantics and precise instruction adherence best. GPT-4o is also very reliable on system prompt compliance. Gemini occasionally "creatively interprets" instructions.

### Refusal Behavior

Claude is most conservative (safety-first) and may refuse legitimate requests. GPT-4o is more permissive. If your use case touches edge content (marketing copy, creative writing, some healthcare scenarios), test Claude's false-refusal rate explicitly before committing.

### Code Generation

Claude Sonnet 4.6 and GPT-4o are roughly equivalent in code quality — both clearly ahead of the other options. Claude is slightly better at following code style constraints.

### Long Document Processing

Claude's 1M context performs most consistently in production, with fewer "lost in the middle" issues. Gemini 2.5 Pro also supports 1M context, but middle-content recall degradation is more noticeable.

---

## Multi-Provider Strategy

Production systems shouldn't be 100% dependent on a single provider:

```python
import anthropic
import openai
from enum import Enum

class Provider(Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"

def route_by_task(task_type: str) -> Provider:
    routing = {
        "structured_extraction": Provider.OPENAI,    # Structured Outputs most reliable
        "long_document": Provider.ANTHROPIC,          # 1M context more stable
        "code_review": Provider.ANTHROPIC,            # Better instruction following
        "high_volume_simple": Provider.OPENAI,        # GPT-4o-mini lower cost
        "complex_reasoning": Provider.ANTHROPIC,      # Claude Opus
    }
    return routing.get(task_type, Provider.ANTHROPIC)

def llm_call_with_fallback(prompt: str, task_type: str) -> str:
    primary = route_by_task(task_type)
    fallback = Provider.OPENAI if primary == Provider.ANTHROPIC else Provider.ANTHROPIC

    try:
        return call_provider(primary, prompt)
    except Exception as e:
        # Automatically fall back when primary provider fails
        print(f"Primary provider failed: {e}, falling back to {fallback}")
        return call_provider(fallback, prompt)
```

---

## When to Consider Open-Source Models

**Don't consider self-hosting open-source models if**:
- Your team has no ML engineering capability
- You're in the early product stage (premature optimization)
- Your monthly API spend is below $5,000 (self-hosting costs more)

**Open-source models make sense when**:
- Data privacy requirements prohibit sending data to third-party APIs
- Monthly API spend exceeds $50,000 and you have dedicated ML engineers
- You need fine-tuning to adapt to a specific domain
- You have edge deployment requirements

**Recommended open-source models (June 2026)**:
- General: Llama 4 (Meta), Mistral Large
- Code: DeepSeek Coder
- Deployment tooling: vLLM (throughput-optimized), Ollama (local development)
