[English](README.md) | **中文**

# 案例复盘：SaaS 营销团队 AI 写作助手

> 一个独立开发者公开构建产品的真实决策过程，包含走过的弯路。

---

## 项目背景

**场景**：一名独立开发者（单人）为小型 B2B SaaS 营销团队构建效率工具。目标用户：1–3 人的营销小团队，每周需要撰写一封产品更新邮件和版本发布说明。使用工具前，每封邮件耗时 4–6 小时——从 GitHub 拉取 changelog、整理成可读文案、调整成符合品牌调性的语气。使用后：全程 45 分钟。

**目标**：让营销团队输入原始 changelog，在两分钟内获得一篇符合品牌声音的可发布初稿。

**初始背景**：
- 开发者：单人，无联创
- 初始用户：0（冷启动）
- 技术熟悉度：Python 后端、基础 React 前端
- 预算：营销费用 $0，API 成本约 $50/月

---

## 阶段1：技术选型（Week 1）

### 流式输出 vs. 等待完整响应

**决策**：选择流式输出（FastAPI + Server-Sent Events），而非等待完整响应后再展示。

**理由**：邮件长度在 600–1200 字之间。在用户测试中，即使输出质量相同，等待 15–25 秒看到任何内容都会让用户觉得产品"坏了"。流式输出带来了可感知的响应性——用户感觉工具在和他们一起工作，而不是在后台默默处理。

**实现**：FastAPI 的 `StreamingResponse` + SSE：

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import anthropic

app = FastAPI()
client = anthropic.Anthropic()

async def stream_draft(changelog: str, brand_voice: dict):
    """通过 SSE 逐 token 流式输出邮件初稿。"""
    system_prompt = build_system_prompt(brand_voice)

    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=system_prompt,
        messages=[{"role": "user", "content": f"Changelog:\n\n{changelog}"}]
    ) as stream:
        for text in stream.text_stream:
            # SSE 格式：data: <内容>\n\n
            yield f"data: {text}\n\n"
        yield "data: [DONE]\n\n"

@app.post("/draft/stream")
async def draft_stream(payload: DraftRequest):
    return StreamingResponse(
        stream_draft(payload.changelog, payload.brand_voice),
        media_type="text/event-stream"
    )
```

### 模型选型

**决策**：分级模型路由——Haiku 生成大纲，Sonnet 生成完整初稿。

**理由**：在带有较长 changelog 上下文的情况下，用单次请求生成完整邮件既贵又慢。关键洞察是：两个任务的质量要求不同——把 changelog 整理成段落结构是分类和排序任务（快速、低成本，Haiku 完全胜任）；把要点转化为精炼文案需要更强的语言能力（Sonnet）。

```python
def route_model(task: str) -> str:
    """根据任务类型路由到对应模型。"""
    if task == "outline":
        return "claude-haiku-4-5"   # 快且便宜，结构生成够用
    elif task == "draft":
        return "claude-sonnet-4-6"  # 最终文案需要更高质量
    else:
        return "claude-haiku-4-5"   # 其他工具类任务默认走便宜模型
```

**实际成本影响**：每封邮件的平均成本从约 $0.08（纯 Sonnet）降至约 $0.031（Haiku 大纲 + Sonnet 初稿）。随用户量增长，这个差距会显著放大。

### 品牌声音系统

**决策**：将品牌声音编码为结构化的 system prompt 块，而非模糊的"用我们的风格写"指令。

**问题**：早期测试发现，"用友好、简洁的语气写"会导致输出不一致。不同运行会产生不同的正式程度、词汇选择和句子节奏。

**解决方案**：带有具体示例的结构化品牌声音 schema。每位新用户填写一份简短的入职表单，答案被序列化进 system prompt。

```python
def build_system_prompt(brand_voice: dict) -> str:
    """
    构建包含品牌声音的 system prompt，用具体示例锚定写作风格。
    brand_voice 键：tone, vocabulary, sentence_length, example_before, example_after
    """
    return f"""你是 {brand_voice['company_name']} 的专业文案撰写人。

## 品牌声音指南

**语气**：{brand_voice['tone']}
（示例："{brand_voice['tone_example']}"）

**推荐词汇**：{', '.join(brand_voice['preferred_words'])}
**禁用词汇**：{', '.join(brand_voice['avoid_words'])}

**句式风格**：{brand_voice['sentence_style']}
目标平均句子长度：{brand_voice['avg_sentence_words']} 字。

## 参考示例

以下是该公司现有写作的样本：

改写前（原始 changelog）：
{brand_voice['example_before']}

改写后（已发布的邮件节选）：
{brand_voice['example_after']}

---

写作时，请匹配"改写后"示例的风格，而非"改写前"。
不要在每句话里都提产品名。开头要多样化。
禁止使用以下表达："我们很高兴地宣布"、"颠覆性的"、"无缝地"。
"""
```

**效果**：多次运行的一致性显著提升。用户反馈输出从第一稿起就有"自己的味道"，而不是通用 AI 文风。

### 上下文长度管理

**问题**：部分工程团队会把几周未经过滤的 git commit 记录全部粘进 changelog 字段。一个活跃仓库的两周 changelog，在加上 system prompt 之前就可能达到 3,000–5,000 个 token。

**决策**：在发送给模型之前预处理并截断 changelog，而不是寄希望于模型能优雅地处理冗长混乱的上下文。

```python
def preprocess_changelog(raw_changelog: str, max_tokens: int = 3000) -> str:
    """
    清理并截断原始 changelog，使其符合上下文预算。
    优先保留高层级条目（功能 > 修复 > 杂项）。
    """
    lines = raw_changelog.strip().split("\n")

    # 按类型排序：功能最优先，依次是修复、性能、重构、杂项
    priority_order = {"feat": 0, "fix": 1, "perf": 2, "refactor": 3, "chore": 4, "deps": 5}

    def line_priority(line: str) -> int:
        for prefix, rank in priority_order.items():
            if line.lower().startswith(prefix) or f"({prefix})" in line.lower():
                return rank
        return 3  # 默认：视为重构级别优先级

    sorted_lines = sorted(lines, key=line_priority)

    # 按 token 预算截断（粗略估算：1 token ≈ 4 字符）
    budget_chars = max_tokens * 4
    result, total = [], 0
    for line in sorted_lines:
        if total + len(line) > budget_chars:
            break
        result.append(line)
        total += len(line)

    return "\n".join(result)
```

**已知取舍**：这种截断是有损的。较长 changelog 末尾的小修复会被丢弃。这是有意为之——邮件应该以功能为主，而不是依赖升级。用户在使用前被明确告知了这一行为。

---

## 阶段2：第一版上线（Week 2-3）

### 架构

```
用户粘贴 changelog + 填写品牌声音表单
  → preprocess_changelog()（Python，服务端）
  → Haiku 生成段落大纲
  → Sonnet 流式输出完整邮件初稿（SSE）
  → 前端实时渲染流式 token
  → 用户内联编辑后复制最终版本
```

**首批用户来源**：开发者在 Twitter 上发了一篇公开构建的帖子——展示了真实截图、实际的 prompt 架构和早期失败案例。这条帖子获得的互动一般，但在 48 小时内带来了 47 个注册用户。这些不是随便点进来的好奇用户，而是立刻认出了这个问题的营销从业者。

**第一天就起效的功能**：
- 流式输出让工具感觉很快，即使生成需要 12–18 秒
- 品牌声音表单只有 6 个字段，用户 3 分钟内就能填完
- Haiku 大纲步骤让用户在完整初稿出现之前就有内容可以预览和反应

**第一天没起效的问题**：
- 没有 diff 视图——用户无法看到自己改了哪里、AI 写了哪里。几个用户反馈刷新后丢失了自己的编辑
- 没有历史记录——每次会话从零开始。第二天回来的用户必须重新填写品牌声音设置
- 对于 changelog 条目很少（2–3 条）的用户，system prompt 太长，模型会用填充内容凑字数

### LangChain 弯路（第 5–8 天）

在从头写流式接口之前，开发者花了三天时间尝试用 LangChain 的 `LLMChain` 和流式回调。

**出了什么问题**：LangChain 的流式抽象在 token 流和 SSE 输出之间添加了两层间接层。当某次运行因限流边界条件静默返回空字符串时，调试需要阅读 LangChain 源码才能搞清楚是哪个内部回调吞掉了错误。折腾三天后，链虽然跑通了，但代码有 340 行，理解它需要掌握 LangChain 特有的心智模型。

**重写过程**：完全去掉 LangChain，直接调用 Anthropic SDK。等效逻辑花了 4 小时写完，85 行代码。SSE 流完全透明，调试友好，每个错误都会立即暴露。

**教训**：LangChain 在复杂多步骤链中是合理的选择——此时它的抽象物有所值。但对于一个直接的单 prompt 流式接口，它只增加了复杂度，没有带来任何价值。评估一下：这个抽象层是否在解决你实际遇到的问题？

---

## 阶段3：针对性优化（Week 4-6）

### 优化1：Diff 视图（解决留存问题）

整个项目影响最大的改动不是 prompt 工程，而是添加了一个 diff 视图——让用户可以看到 AI 写了什么、自己改了什么。

**为什么重要**：diff 视图让用户自己的编辑行为变得可见且有意义。AI 的输出不再是被批改后丢掉的东西，而是带有标注的训练素材——用户可以保存、逐步打磨，最终反哺到自己的品牌声音档案里。它也强化了一个认知：AI 是协作者，不是替代者。

**添加 diff 视图前的 Day-7 留存率**：12%
**添加 diff 视图后的 Day-7 留存率**：31%

```typescript
// 前端：计算并渲染 AI 版本 vs. 用户版本的 diff
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
          // AI 写了这段，用户删掉了
          return <span key={i} className="bg-red-100 line-through text-red-600">{part.value}</span>;
        }
        if (part.added) {
          // 用户加了这段，AI 没有写
          return <span key={i} className="bg-green-100 text-green-700">{part.value}</span>;
        }
        // 未改动
        return <span key={i} className="text-gray-700">{part.value}</span>;
      })}
    </div>
  );
}
```

### 优化2：品牌声音档案持久化

**问题**：用户每次会话都要重新填写 6 个字段的品牌声音表单。两个用户在反馈中直接提到了这个问题。留存数据也印证了这一点——没有保存档案的会话时长短 60%，重新生成次数（参与度的代理指标）也更低。

**解决方案**：在服务端按用户 ID 保存品牌声音档案。实现很简单——一张数据库表、一个 API 接口——但对回访体验的影响立竿见影。

```python
# 品牌声音档案：保存与读取
def save_brand_voice(user_id: str, profile: dict) -> None:
    """持久化品牌声音设置，让回访用户无需重复填写。"""
    db.execute(
        "INSERT INTO brand_voice_profiles (user_id, profile_json, updated_at) "
        "VALUES (?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET "
        "profile_json = excluded.profile_json, updated_at = excluded.updated_at",
        (user_id, json.dumps(profile), datetime.utcnow())
    )

def load_brand_voice(user_id: str) -> dict | None:
    """读取已保存的品牌声音档案，若尚未配置则返回 None。"""
    row = db.execute(
        "SELECT profile_json FROM brand_voice_profiles WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    return json.loads(row["profile_json"]) if row else None
```

### 优化3：自适应输出长度

**问题**：changelog 条目少（2–3 条）时，模型会生成内容填充的通用邮件，因为它隐式地以某个最低字数为目标。changelog 条目多时，初稿试图包含所有内容，读起来像 changelog，而不像邮件。

**解决方案**：根据 changelog 条目数量传入明确的目标长度指令，并为简短输入加上"不要填充"的硬性规则。

```python
def build_length_instruction(item_count: int) -> str:
    """
    根据 changelog 规模返回相应的长度指令。
    防止简短 changelog 被填充，防止长 changelog 面面俱到。
    """
    if item_count <= 3:
        return (
            "这是一次小版本发布。写一封简短的邮件：2 个短段落，"
            "总计 150–200 字。不要用填充内容凑字数。不要凭空添加背景。"
        )
    elif item_count <= 8:
        return (
            "写一封标准邮件：3–4 段，300–450 字。"
            "重点突出 2–3 个最重要的改动。将小修复归并在一起。"
        )
    else:
        return (
            "这是一次大版本发布。写一封结构化邮件：开场段落，"
            "3–4 个带小标题的命名章节，结尾段落。500–700 字。"
            "不要把每个条目都写进去——只筛选影响最大的内容。"
        )
```

### 首位付费用户（第 18 天）

第 18 天，一位用户在 Twitter 上私信："我每周都在用。怎么付钱给你？"当时产品没有任何付款流程。花了两小时设置了一个 Stripe 付款链接，用户当天就支付了 $49/月。

没有转化漏斗，没有定价页面——只是一个觉得工具足够有价值、主动来问的用户。$49 的定价逻辑是：节省的时间折算成月收益的 10%——而非市场调研得出的结论。

---

## 最终结果

| 指标 | 上线前 | 上线后 |
|------|--------|--------|
| 每封邮件耗时 | 4–6 小时 | 45 分钟 |
| 首稿生成时间 | 无 | ~90 秒 |
| Day-7 留存率 | 无基准 | 31%（diff 视图上线后） |
| 首位付费用户 | — | 第 18 天 |
| 活跃用户月均 API 成本 | — | ~$0.93 |
| 定价 | — | $49/月 |

---

## 关键决策复盘

**做对的决策**：
1. 在 Twitter 上公开构建引来了精准的早期用户——他们理解这个问题，而不只是对 AI 感兴趣
2. 两周内上线可用的 v1，由真实使用模式驱动改进路线图——diff 视图是观察用户行为后得出的，不是事先规划的
3. 分级模型路由（Haiku 大纲 + Sonnet 初稿）将每封邮件成本降低了 61%，用户感知不到质量差异

**走的弯路**：
1. 在换成裸 API 调用之前，在 LangChain 上浪费了三天——这个抽象层对当前场景没有解决任何实际问题，还遮蔽了所有报错
2. v1 没有持久化层——用户在不同会话间丢失品牌声音设置是一个安静的、不可见的流失驱动因素，不会出现在反馈中，但会体现在回访率上
3. 低估了输出长度校准的重要性——简短 changelog 产生填充内容，是早期用户访谈中最常见的抱怨，但它完全不在最初的产品路线图里

**最重要的教训**：diff 视图从未出现在最初的产品设计里。它来自于观察用户编辑输出的行为，并意识到*编辑行为本身*具有产品价值——它捕捉了每个团队的声音与模型默认值之间的差距。让用户行为变得可见的功能，往往比提升 AI 输出质量的功能有更高的留存价值。先把核心流程跑通，再观察用户究竟在做什么。

---

*[English Version](README.md)*
