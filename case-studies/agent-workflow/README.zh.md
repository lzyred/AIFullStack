[English](README.md) | **中文**

# 案例复盘：AI 驱动的销售外发自动化系统

> 从 0 到上线的真实决策过程，包含那次让项目起死回生的架构转型。

---

## 项目背景

**场景**：某 5 人 B2B SaaS 创业公司，团队只有一名 SDR（销售开发代表）负责所有对外拓客工作。SDR 每天要花 3 个多小时在两件事上：研究潜在客户（公司背景、近期动态、融资情况、痛点），以及根据调研结果撰写个性化冷邮件。时间就这么多，每天最多发出 8 封邮件。

**目标**：自动化潜在客户调研和邮件初稿生成。SDR 负责审核输出内容，按需修改后发送。人在环路中——AI 承担重复性工作。

**初始约束**：
- 团队规模：5 人，无专职 ML 工程师
- 预算：API 成本控制在每月 300 美元以内
- 技术栈：Python 后端，无现有自动化基础设施
- 目标邮件量：每天 35 封以上（从 8 封提升）

---

## 阶段1：架构决策（Week 1）

### 核心问题：用 Agent 还是 Workflow？

团队读了 Anthropic 文档，看了一些演示，进行了内部讨论。第一直觉是用 **Agent**——感觉更强大、更灵活。当时的理由：

- "我们不知道每个潜在客户需要哪些具体的调研步骤，Agent 可以动态决定。"
- "Agent 能处理我们还没想到的边界情况。"
- "感觉更面向未来。"

这个思路可以理解，但是错的。团队后来的推导过程如下：

| 因素 | Agent | Workflow |
|------|-------|---------|
| 步骤是否事先已知？ | 否 | **是** — 调研 → 总结 → 起草 |
| 是否需要动态工具选择？ | 可能 | **否** — 每次相同的工具 |
| 输出必须保持一致？ | 难以保证 | **是，至关重要** |
| 失败模式是否可接受？ | 不可预测 | **确定性，可捕获** |
| 是否需要可审计性？ | 困难 | **容易** |

团队最终决定**先用 Agent 做原型**（Week 1），告诉自己如果出问题再切换。结果出问题了。

---

## 阶段2：Agent 原型（Week 1-2）

### 架构

第一版是一个带三个工具的 ReAct 风格 Agent：

```python
import anthropic

client = anthropic.Anthropic()

tools = [
    {
        "name": "web_search",
        "description": "搜索网络，获取公司或个人的近期新闻、新闻稿或相关信息。",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_company_info",
        "description": "获取公司结构化数据：成立年份、员工规模、融资阶段、所属行业、技术栈。",
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
        "description": "根据调研摘要和潜在客户背景，撰写个性化冷邮件。",
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
    """原始 Agent 方式——让模型自己决定步骤。"""
    messages = [
        {
            "role": "user",
            "content": (
                f"调研这位潜在客户并撰写个性化冷邮件。\n"
                f"潜在客户：{prospect['name']}，就职于 {prospect['company']}（{prospect['domain']}）\n"
                f"我们的产品：{prospect['our_product_context']}"
            )
        }
    ]

    # Agent 循环——模型自己决定什么时候信息已经足够
    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            tools=tools,
            messages=messages
        )

        if response.stop_reason == "end_turn":
            # 提取最终文本
            return next(b.text for b in response.content if hasattr(b, "text"))

        # 执行工具调用并继续
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

### 生产环境中暴露的问题

Agent 在演示中运行良好。在真实使用的第一周就出了问题。

**问题1：捏造公司事实**

Agent 会自信地在邮件中引用一些根本不在任何搜索结果里的"事实"——融资金额、员工规模、产品功能，甚至 CEO 的引言。这些全是编造的。SDR 在发送前发现了两处。有一处没发现，发出去了。

那封漏网之鱼的邮件提到了该公司"最近完成的 B 轮融资"——这轮融资根本没有发生。客户回邮件纠正了这个错误。那次对话在开始之前就结束了。

```
# 真实发生的幻觉邮件开头（已脱敏改写）：
"恭喜贵司完成 B 轮融资——当工程团队扩张到 200 人时，
正是基础设施技术债开始爆发的时候……"

# 现实：这家公司只有 34 名员工，3 年前完成了一轮天使融资。
```

**问题2：非确定性执行路径**

对于完全相同的输入，Agent 有时调用 `web_search` 两次，有时三次，有时完全跳过 `get_company_info`。没有任何一致的逻辑——每次运行全凭模型当时的判断。输出质量的方差大到无法信任。

**问题3：成本不可预测**

每位潜在客户的 token 用量在 4,000 到 18,000 之间浮动，取决于 Agent 决定运行多少轮工具循环。完全无法做预算。

**问题4：不可审计**

当 SDR 问"为什么它会这么说？"时，没有好的答案。Agent 的推理过程埋在不透明的循环里。调试需要重放整个对话。

---

## 阶段3：转型为确定性 Workflow（Week 3-4）

### 决策过程

B 轮融资事故发生后，团队进行了事后复盘。结论令人不舒服，但非常清晰：问题不是 bug，而是架构本身的问题。一个可以自己决定步骤的 Agent，也会决定出错误的步骤。对于一个步骤固定已知的任务，确定性 Workflow 才是正确的工具。

重构花了三天。

### 新架构：Prompt Chaining + 并行化

```
潜在客户输入
  ├── [并行] web_search("公司名 近期新闻")
  ├── [并行] web_search("公司名 融资 招聘")
  └── [并行] get_company_info(company_name, domain)
        ↓
  [Haiku] 汇总所有调研 → 结构化 JSON
        ↓
  [人工审核] SDR 审核调研摘要，批准或修改
        ↓
  [Sonnet] 根据已审核摘要起草个性化邮件
        ↓
  [人工审核] SDR 审核邮件草稿，修改后发送
```

**为什么调研摘要用 Haiku，邮件起草用 Sonnet**：摘要是压缩任务——提取事实并结构化，不需要创意判断，Haiku 能可靠完成，成本约为 Sonnet 的十分之一。邮件起草需要语气、说服力和细致的个性化处理——这里 Sonnet 的质量值得付出更高成本。

### 代码前后对比

**重构前（Agent——非确定性）：**

```python
# Agent 自己决定做什么、何时做。无法保证固定步骤。
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
        # ... Agent 循环任意继续
```

**重构后（Workflow——确定性）：**

```python
import asyncio
import anthropic
import json

client = anthropic.Anthropic()

# 步骤1：并行调研——固定调用这三个接口，不多不少
async def research_prospect(prospect: dict) -> dict:
    """并行执行所有调研。固定输入，固定输出。"""
    loop = asyncio.get_event_loop()

    # 三个调用同时发出
    news_result, funding_result, company_result = await asyncio.gather(
        loop.run_in_executor(None, web_search, f"{prospect['company']} 近期新闻 2024"),
        loop.run_in_executor(None, web_search, f"{prospect['company']} 融资 招聘 扩张"),
        loop.run_in_executor(None, get_company_info, prospect['company'], prospect['domain'])
    )

    return {
        "recent_news": news_result,
        "funding_hiring": funding_result,
        "company_data": company_result
    }

# 步骤2：用 Haiku 做摘要——便宜、快速、确定性
def summarize_research(prospect: dict, raw_research: dict) -> dict:
    """
    Haiku 将原始调研数据压缩为结构化 JSON 摘要。
    关键：提示词要求模型只使用调研数据中明确存在的信息。
    如果某个字段找不到答案，填 null——不允许推断或假设。
    """
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": f"""将以下调研数据整理为结构化 JSON 对象。
只包含调研数据中明确存在的事实。
如果某个字段的答案找不到，使用 null——不要猜测。

调研数据：
{json.dumps(raw_research, indent=2)}

输出以下 JSON 结构：
{{
  "company_name": string,
  "founded_year": number | null,
  "headcount_estimate": string | null,
  "funding_stage": string | null,
  "recent_news_headline": string | null,
  "likely_pain_points": [string],
  "confidence_note": string  // 标记任何不确定的信息
}}"""
        }]
    )
    return json.loads(response.content[0].text)

# 步骤3：人工审核关卡——必须经过，不可跳过
def human_review_research(prospect: dict, summary: dict) -> dict:
    """
    在起草邮件之前，SDR 先看到调研摘要。
    可以纠正事实、补充背景，或跳过这位潜在客户。
    这个关卡存在的原因：邮件质量的上限是调研质量。
    """
    print(f"\n--- {prospect['name']}（{prospect['company']}）的调研摘要 ---")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print("\n选项：[a] 批准 / [e] 编辑 / [s] 跳过此潜在客户")
    choice = input("> ").strip().lower()

    if choice == "s":
        return None  # 跳过，不起草邮件
    elif choice == "e":
        correction = input("输入修正内容（JSON patch 或纯文本备注）：")
        summary["sdr_correction"] = correction
    # choice == "a" 直接通过，不修改摘要

    return summary

# 步骤4：用 Sonnet 起草邮件——只在调研通过审核后执行
def draft_email(prospect: dict, approved_summary: dict) -> str:
    """
    Sonnet 撰写邮件。它只能访问已审核的结构化摘要，
    无法访问原始调研数据。这从根本上阻断了幻觉的渗透。
    """
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{
            "role": "user",
            "content": f"""为 B2B SaaS 销售外发撰写一封简洁、个性化的冷邮件。

潜在客户：{prospect['name']}，职位 {prospect['title']}，就职于 {prospect['company']}
已审核的调研摘要：
{json.dumps(approved_summary, indent=2, ensure_ascii=False)}

我们的产品：{prospect['our_product_context']}

要求：
- 包含主题行和正文（不超过 150 词）
- 引用调研摘要中的一个具体、已核实的事实
- 不得捏造或推断摘要中没有的任何信息
- 语气对话化，不要有推销感
- 明确的行动召唤：邀请进行 15 分钟通话"""
        }]
    )
    return response.content[0].text

# 步骤5：最终人工审核关卡——SDR 批准后才发送
def human_review_email(prospect: dict, draft: str) -> str | None:
    """SDR 看到草稿。批准、就地编辑，或丢弃。"""
    print(f"\n--- {prospect['name']} 的邮件草稿 ---")
    print(draft)
    print("\n选项：[a] 批准并发送 / [e] 编辑 / [d] 丢弃")
    choice = input("> ").strip().lower()

    if choice == "d":
        return None
    elif choice == "e":
        print("粘贴编辑后的版本（以单独一行 'END' 结束）：")
        lines = []
        while True:
            line = input()
            if line == "END":
                break
            lines.append(line)
        return "\n".join(lines)
    return draft  # 直接批准

# 主工作流——固定、可审计、可复现
async def run_outreach_workflow(prospect: dict) -> dict:
    """
    每位潜在客户都按完全相同的步骤、完全相同的顺序处理。
    每个步骤的输出都有日志记录。任何步骤都可以单独重新运行。
    """
    # 1. 调研（并行）
    raw_research = await research_prospect(prospect)

    # 2. 摘要（Haiku）
    summary = summarize_research(prospect, raw_research)

    # 3. 人工审核调研摘要
    approved_summary = human_review_research(prospect, summary)
    if approved_summary is None:
        return {"status": "skipped", "prospect": prospect["name"]}

    # 4. 起草邮件（Sonnet）
    draft = draft_email(prospect, approved_summary)

    # 5. 人工审核邮件草稿
    final_email = human_review_email(prospect, draft)
    if final_email is None:
        return {"status": "discarded", "prospect": prospect["name"]}

    # 6. 发送（或加入发送队列）
    send_email(prospect["email"], final_email)
    return {"status": "sent", "prospect": prospect["name"], "email": final_email}
```

### Workflow 中的关键设计决策

**为什么调研摘要里要有 `confidence_note` 字段**：Haiku 的摘要提示词要求模型主动标记任何不确定的信息。这样在人工审核关卡之前，低置信度的字段就会浮出水面，SDR 知道哪些地方需要重点核查，而不是对所有内容一视同仁地信任。

**为什么 Sonnet 只能看到已审核的摘要，而不是原始调研数据**：原始搜索结果包含噪音、矛盾信息和过时数据。如果 Sonnet 能访问原始数据，它可能会引用未经核实的事实。已审核的摘要是经 SDR 确认的事实来源。Sonnet 从事实出发起草，而不是从噪音出发。

**为什么需要两个人工审核关卡，而不是一个**：调研审核和邮件审核捕获的是不同类型的失败。调研关卡捕获事实错误；邮件关卡捕获只有 SDR 才能判断的语气、框架和背景错误。曾经尝试合并为一个关卡，后来撤回了这个改动——SDR 在阅读邮件时注意力分散，容易忽视调研错误。

---

## 最终结果

| 指标 | 上线前 | 上线后（Workflow 版本） |
|------|--------|----------------------|
| SDR 调研 + 起草时间 | 3 小时/天 | 25 分钟/天 |
| 外发邮件量 | 8 封/天 | 35 封/天 |
| 个性化评分（内部评分标准，1-5 分） | 平均 3.2 | 平均 3.8 |
| 回复率（30 天滚动均值） | 4.1% | 6.7% |
| 在审核关卡捕获的事实错误 | N/A | 每周 2-3 次（发送前拦截） |
| 月 API 成本 | $0 | 约 $180 |

**关于回复率的说明**：归因存在不确定性。更高的发送量和更好的调研质量都有贡献。团队正在进行对照实验，以单独衡量调研质量的影响。

---

## 关键决策复盘

**做对的决策**：
1. 先跑了 Agent 原型，而不是在理论上争论——生产环境的真实失败让转型决策变得显而易见、无需争辩
2. 从一开始就设计了两个人工审核关卡——这个设计在 Workflow 阶段至少避免了三次重大事故
3. 模型分级（Haiku 做摘要，Sonnet 起草邮件）——在不牺牲邮件质量的前提下，让成本保持可预测

**走的弯路**：
1. 不应该把 Agent 直接用于真实潜在客户。原型阶段应该用假的潜在客户数据在内部测试整整一周，再接触真实外发。一封幻觉邮件就足以造成不可挽回的损失。
2. Agent 阶段的工具 schema 设计过于宽松——`draft_email` 接受一个自由格式的 `research_summary` 字符串，意味着模型可以在里面填入任何内容，包括捏造的事实。Workflow 里带有显式 `null` 字段的结构化 JSON 摘要才是正确的设计，应该从第一天就这么做。
3. 低估了 Workflow 稳定后 SDR 审核时间的下降幅度。最初预估每天需要 45 分钟审核，实际稳定在 25 分钟——因为调研质量变得一致且可预测。

**最重要的教训**："Agent"不是"强大"的同义词，而是"让模型来决定"的同义词。对于一个步骤固定已知、顺序确定的任务，确定性 Workflow 更可靠、更可审计、也更便宜。Agent 原型在纸面上"能力更强"；Workflow 在生产中"可靠性更高"。可靠性胜出。

一封包含错误事实的冷邮件，在几秒钟内就能摧毁信任。重建信任需要数周。把这个失败模式放在第一位来设计系统。

---

*[English Version](README.md)*
