[English](llm-providers.md) | **中文**

# LLM 提供商横向对比

> 同一场景下，怎么选 OpenAI / Anthropic / Gemini。不是广告，是工程决策。

---

## 先说结论

没有"最好的"模型，只有"最适合这个场景"的模型。

**快速选择指南**：

| 场景 | 推荐 |
|------|------|
| 通用对话/问答 | Claude Sonnet 4.6 或 GPT-4o，差异不大 |
| 长文档处理（> 100k tokens） | Claude（1M 上下文），Gemini 2.5 Pro 备选 |
| 结构化数据提取 | OpenAI（Structured Outputs 最成熟） |
| 代码生成/审查 | Claude Sonnet 4.6 或 GPT-4o |
| 中文场景 | Claude 或 GPT-4o（Gemini 次之） |
| 成本敏感的高频场景 | Claude Haiku 4.5 或 GPT-4o-mini |
| 复杂推理任务 | Claude Opus 4（最新版）或 GPT-4o |
| 安全/合规敏感场景 | Claude（拒绝率高，但误拒也高） |

---

## 接口层差异（影响开发工作量）

这些差异在代码层面，每一个都可能让你踩坑：

| 差异点 | OpenAI | Anthropic | Gemini |
|--------|--------|-----------|--------|
| System prompt | `role: "system"` message | 独立 `system` 字段 | `system_instruction` |
| `max_tokens` | 可选（有默认值） | **必填（无默认值）** | 可选 |
| 消息角色 | user/assistant/system | user/assistant（只有两种） | user/model |
| 结构化输出 | Structured Outputs（原生，最可靠） | Tool use 强制调用 | 类似 OpenAI |
| 流式事件格式 | `choices[0].delta.content` | `text_stream` 迭代器 | `.text` |
| Prefill（预填充）| 不支持 | **支持 assistant 预填充** | 不支持 |
| Tool choice | `"required"` / `"auto"` | `{"type": "tool", "name": "xxx"}` | 类似 OpenAI |
| 图片输入 | `image_url` 或 base64 | base64 / URL（URL 需要支持） | 类似 Anthropic |

---

## 成本对比（截至 2026 年 6 月）

单位：美元/百万 token（输入/输出）

| 模型 | 输入 | 输出 | 上下文 | 适用场景 |
|------|------|------|--------|---------|
| Claude Haiku 4.5 | $1 | $5 | 200k | 高频、分类、简单任务 |
| Claude Sonnet 4.6 | $3 | $15 | 1M | 通用生产首选 |
| Claude Opus 4（最新版，参考 Anthropic 官网确认 model ID） | $5 | $25 | 1M | 复杂推理、重要任务 |
| GPT-4o-mini | ~$0.15 | ~$0.6 | 128k | 成本极敏感场景 |
| GPT-4o | ~$2.5 | ~$10 | 128k | 通用场景 |
| Gemini 2.0 Flash | ~$0.075 | ~$0.3 | 1M | 成本敏感 + 长文档 |
| Gemini 2.5 Pro | ~$1.25 | ~$10 | 1M | 多模态 + 长文档 + 复杂推理 |

**成本控制技巧**：
- Anthropic Prompt Caching：重复前缀命中缓存后输入只收 10% 价格
- Anthropic / OpenAI Batch API：异步处理享 50% 折扣
- 模型路由：用 Haiku/GPT-4o-mini 分类，复杂任务再走 Sonnet/GPT-4o

---

## 能力差异（真实测试发现）

### 中文能力

Claude ≥ GPT-4o > Gemini（一般场景）。但差距在持续缩小。中文 token 效率：Anthropic 新 tokenizer 效率更高，中文每个字接近 1 token。

### 指令遵从

Claude 在 XML 标签的语义理解和精确指令遵从上表现最好，GPT-4o 在系统消息遵从上也很稳定。Gemini 偶尔会"创造性地解读"指令。

### 拒绝行为

Claude 最保守（安全优先），可能会拒绝合理的请求。GPT-4o 相对宽松。如果应用场景有边界内容（营销文案、创意写作、部分医疗场景），Claude 的误拒率需要测试。

### 代码生成

Claude Sonnet 4.6 和 GPT-4o 在代码质量上基本持平，都明显优于其他模型。Claude 在遵从代码风格约束上稍好。

### 长文档处理

Claude 的 1M 上下文在实际使用中最稳定，"Lost in the middle" 问题较少。Gemini 1.5 Pro 也支持 1M，但中间内容遗忘问题更明显。

---

## 多提供商策略

生产环境不应该 100% 依赖单一提供商：

```python
import anthropic
import openai
from enum import Enum

class Provider(Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"

def route_by_task(task_type: str) -> Provider:
    routing = {
        "structured_extraction": Provider.OPENAI,    # Structured Outputs 最可靠
        "long_document": Provider.ANTHROPIC,          # 1M 上下文更稳定
        "code_review": Provider.ANTHROPIC,            # 指令遵从更好
        "high_volume_simple": Provider.OPENAI,        # GPT-4o-mini 成本更低
        "complex_reasoning": Provider.ANTHROPIC,      # Claude Opus
    }
    return routing.get(task_type, Provider.ANTHROPIC)

def llm_call_with_fallback(prompt: str, task_type: str) -> str:
    primary = route_by_task(task_type)
    fallback = Provider.OPENAI if primary == Provider.ANTHROPIC else Provider.ANTHROPIC

    try:
        return call_provider(primary, prompt)
    except Exception as e:
        # 主提供商失败时自动切换
        print(f"Primary provider failed: {e}, falling back to {fallback}")
        return call_provider(fallback, prompt)
```

---

## 什么时候考虑开源模型

**不要在以下情况考虑自托管开源模型**：
- 团队没有 ML 工程能力
- 项目早期（过早优化）
- 每月 API 成本 < $5000（托管成本更高）

**可以考虑开源模型的情况**：
- 数据隐私要求不允许发送到第三方 API
- 每月 API 成本 > $50000，且有专职 ML 工程师
- 需要微调（fine-tuning）来适应特定领域
- 有需要在边缘设备运行的场景

**推荐开源模型**（2026 年 6 月）：
- 通用：Llama 4（Meta），Mistral Large
- 代码：DeepSeek Coder
- 中文：Qwen 2.x
- 部署工具：vLLM（吞吐量优化），Ollama（本地开发）


---

*[English Version](llm-providers.md)*
