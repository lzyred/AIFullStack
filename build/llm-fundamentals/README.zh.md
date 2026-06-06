[English](README.md) | **中文**

# LLM 工程基础

> 工程师视角，不是学术解释。理解这些，才能在出问题时知道去哪里修。

---

## Token：成本和限制的根源

### Token 是什么

Token 不等于单词。粗略估算：
- 英文：1 token ≈ 0.75 个单词，100 tokens ≈ 75 个词
- 中文：1 个汉字 ≈ 1-2 tokens（Anthropic 新 tokenizer 效率更高）
- 代码：关键词通常 1 token，变量名可能 2-4 tokens

```python
# 精确计算 token 数（Anthropic）
import anthropic
client = anthropic.Anthropic()
response = client.messages.count_tokens(
    model="claude-sonnet-4-6",
    messages=[{"role": "user", "content": your_text}]
)
print(f"Token 数: {response.input_tokens}")

# 精确计算 token 数（OpenAI）
import tiktoken
enc = tiktoken.encoding_for_model("gpt-4o")
tokens = enc.encode(your_text)
print(f"Token 数: {len(tokens)}")
```

### 成本计算

**主流模型定价（截至 2026 年 6 月，单位：美元/百万 token）**

| 模型 | 输入 | 输出 | 上下文窗口 |
|------|------|------|-----------|
| Claude Sonnet 4.6 | $3 | $15 | 1M tokens |
| Claude Haiku 4.5 | $1 | $5 | 200k tokens |
| GPT-4o-mini | ~$0.15 | ~$0.6 | 128k tokens |
| GPT-4o | ~$2.5 | ~$10 | 128k tokens |

**关键洞见**：
- 输出 token 比输入贵 3-5x，优化成本的重点在于**控制输出长度**
- Batch API（异步处理）有 50% 折扣，适合离线评估和批量任务
- Prompt Caching（Claude）：重复前缀命中缓存后只付 10% 价格

```python
# 单次请求的成本估算
def estimate_cost(input_tokens: int, output_tokens: int, model: str) -> float:
    pricing = {
        "claude-sonnet-4-6": (3.0, 15.0),   # (输入价格, 输出价格) per MTok
        "claude-haiku-4-5": (1.0, 5.0),
    }
    inp_price, out_price = pricing[model]
    return (input_tokens * inp_price + output_tokens * out_price) / 1_000_000
```

---

## 上下文窗口管理

### 核心限制

上下文窗口 = 模型一次能看到的最大 token 数，包含：system prompt + 历史对话 + 当前输入 + 输出空间。

**常见陷阱**：RAG pipeline 没有 token 计数，检索结果 + 对话历史 + system prompt 超出限制，触发 API 报错。

```python
import anthropic

client = anthropic.Anthropic()

MAX_CONTEXT = 180_000  # 留 20k 给输出
SYSTEM_PROMPT = "..."

def safe_messages_create(messages: list, new_message: str) -> str:
    # 1. 计算当前 token 数
    all_messages = messages + [{"role": "user", "content": new_message}]
    token_count = client.messages.count_tokens(
        model="claude-sonnet-4-6",
        system=SYSTEM_PROMPT,
        messages=all_messages
    ).input_tokens

    # 2. 如果超限，截断最旧的对话（保留最新的 N 条）
    while token_count > MAX_CONTEXT and len(messages) > 2:
        messages = messages[2:]  # 移除最旧的一轮对话（user + assistant）
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

## 三大 API 接口差异

实际代码层面的差异，不是营销描述。

```python
# ========== OpenAI ==========
from openai import OpenAI
client = OpenAI()

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "你是助手"},  # system 是一条 message
        {"role": "user", "content": "你好"}
    ],
    temperature=0.7,
    max_tokens=1024       # 可选，有默认值
)
text = response.choices[0].message.content
usage = response.usage   # .prompt_tokens, .completion_tokens


# ========== Anthropic ==========
from anthropic import Anthropic
client = Anthropic()

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,       # 必填！无默认值，忘填直接报错
    system="你是助手",     # system 是顶层字段，不是 message
    messages=[
        {"role": "user", "content": "你好"}
        # 注意：只有 user 和 assistant 两种 role
    ]
)
text = response.content[0].text    # 注意结构与 OpenAI 不同
usage = response.usage   # .input_tokens, .output_tokens


# ========== Gemini（新版 SDK：google-genai >= 1.0）==========
from google import genai as google_genai
client_gemini = google_genai.Client(api_key="...")

response = client_gemini.models.generate_content(
    model="gemini-2.0-flash",
    contents="你好",
    config={"system_instruction": "你是助手"}
)
text = response.text
```

### 关键差异汇总

| 差异点 | OpenAI | Anthropic | Gemini |
|--------|--------|-----------|--------|
| System prompt | `role: "system"` message | 独立 `system` 字段 | `system_instruction` 字段 |
| `max_tokens` | 可选，有默认值 | **必填，无默认值** | 可选 |
| 强制工具调用 | `tool_choice: "required"` | `tool_choice: {"type": "tool", "name": "xxx"}` | 类似 OpenAI |
| Prefill | 不支持 | 支持 assistant 消息预填充 | 不支持 |
| 流式结构 | `choices[0].delta.content` | `text_stream` 迭代器 | `for chunk in stream: chunk.text` |

---

## 流式输出

用户体验的关键：TTFT（Time To First Token）从 5s 降到 0.5s 的感知差异。

```python
# Anthropic 流式（推荐写法）
import anthropic

client = anthropic.Anthropic()

with client.messages.stream(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[{"role": "user", "content": "写一首短诗"}]
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)  # flush=True 关键，否则不实时显示

# 流结束后获取完整用量
final = stream.get_final_message()
print(f"\n输入: {final.usage.input_tokens}, 输出: {final.usage.output_tokens}")
```

```python
# OpenAI 流式
from openai import OpenAI

client = OpenAI()
stream = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "写一首短诗"}],
    stream=True,
    stream_options={"include_usage": True}  # 必须显式开启才能获取 token 用量
)

for chunk in stream:
    if chunk.choices and chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
    if chunk.usage:
        print(f"\nTokens: {chunk.usage.total_tokens}")
```

**流式输出踩坑**：
- 不加 `flush=True`，缓冲区满才输出，用户看不到实时效果
- 做 SSE 接口时必须设置 `Content-Type: text/event-stream` 和 `Cache-Control: no-cache`
- 流式模式下的异常要包住整个迭代过程，不只是创建调用

---

## 成本控制策略（按 ROI 排序）

### 1. 模型路由（最高 ROI）

```python
def route_model(query: str) -> str:
    """用最便宜的模型分类，再路由到合适的模型"""
    classification = client.messages.create(
        model="claude-haiku-4-5",   # 最便宜，用来做分类
        max_tokens=10,
        messages=[{
            "role": "user",
            "content": f"判断以下问题的复杂度：simple/complex\n问题：{query}"
        }]
    ).content[0].text.strip().lower()

    if "simple" in classification:
        return "claude-haiku-4-5"      # $1/$5 per MTok
    else:
        return "claude-sonnet-4-6"     # $3/$15 per MTok
```

### 2. Prompt Caching（Claude 独有，命中后省 90% 输入成本）

```python
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    system=[{
        "type": "text",
        "text": very_long_system_prompt_or_document,  # 长且固定的内容
        "cache_control": {"type": "ephemeral"}        # 标记为可缓存
    }],
    messages=[{"role": "user", "content": user_query}]
)
# 第一次：正常计费（写入缓存）
# 后续命中缓存：输入 token 只收 10% 价格
# 注意：ephemeral 缓存 TTL 为 5 分钟，请求间隔超过 5 分钟缓存失效需重新写入
```

### 3. 输出长度控制

```python
# 在 prompt 里明确限制输出
"用不超过 3 句话回答"
"只返回 JSON，不要解释"

# 用 stop sequences 提前终止
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=500,
    stop_sequences=["</answer>"],  # 找到这个 token 就停止
    ...
)
```

### 4. 语义缓存常见查询

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

## 为什么模型会幻觉

理解原因，才能设计正确的防护：

1. **训练数据截止**：模型不知道近期发生的事情，但会"自信地猜测"
2. **知识边界不清晰**：模型不知道自己不知道什么，缺乏元认知
3. **统计倾向**：倾向于生成"看起来合理"的内容，而非"确认准确"的内容

**工程层面的防护**：
- 提供上下文（RAG），让模型基于文档而非记忆回答
- 明确说明"不知道就说不知道"
- 对关键输出做 programmatic 验证（代码执行、API 调用验证）
- 不要用 AI 回答需要精确数字的问题（价格、日期、统计数据）


---

*[English Version](README.md)*
