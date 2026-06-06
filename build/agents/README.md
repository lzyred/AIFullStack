# Agent 设计指南

> Karpathy 检验：基于 Anthropic 工程团队和 Lilian Weng 研究，代码可运行。

---

## 核心判断：你真的需要 Agent 吗

**Agent 被严重滥用。** 大多数"Agent 应用"应该是 Workflow。

```
任务判断流程：
│
├── 单次 LLM 调用 + 检索能解决？
│   └── 是 → 不要用 Agent，直接做
│
├── 可以拆成固定步骤的流程？
│   └── 是 → 用 Workflow（可预测、可调试、成本可控）
│       ├── 步骤顺序固定 → Prompt Chaining
│       ├── 需要分类路由 → Routing
│       ├── 子任务独立 → Parallelization
│       └── 需要迭代优化 → Evaluator-Optimizer
│
└── 步骤数量无法预先确定，需要模型动态规划？
    └── 才考虑 Agent
```

### Agent 适用的信号

- 任务需要多轮工具调用，下一步取决于上一步结果
- 解决方案路径无法提前硬编码
- 有明确可验证的成功标准（代码通过测试、API 返回 200 等）

### 不该用 Agent 的信号

- 追求低延迟（每次工具调用增加 500ms-2s）
- 预算敏感（Agent 的 token 消耗是线性调用的 5-20x）
- 操作不可回滚（支付、删除、发送邮件）

---

## Workflow 模式（优先考虑这些）

### 1. Prompt Chaining — 顺序处理

```python
import anthropic

client = anthropic.Anthropic()

def chain(input_text: str) -> str:
    # Step 1: 提取关键信息
    extracted = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=500,
        messages=[{"role": "user", "content": f"从以下文本提取关键事实：\n{input_text}"}]
    ).content[0].text

    # Step 2: 基于提取结果生成摘要
    summary = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=200,
        messages=[{"role": "user", "content": f"将以下关键事实整理成一段摘要：\n{extracted}"}]
    ).content[0].text

    return summary
```

### 2. Parallelization — 独立子任务并行

```python
import asyncio
import anthropic

client = anthropic.AsyncAnthropic()

async def parallel_analysis(document: str) -> dict:
    tasks = [
        client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=200,
            messages=[{"role": "user", "content": f"提取文档中的人名：\n{document}"}]
        ),
        client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=200,
            messages=[{"role": "user", "content": f"提取文档中的日期：\n{document}"}]
        ),
        client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=200,
            messages=[{"role": "user", "content": f"提取文档中的金额：\n{document}"}]
        ),
    ]
    results = await asyncio.gather(*tasks)
    return {
        "names": results[0].content[0].text,
        "dates": results[1].content[0].text,
        "amounts": results[2].content[0].text,
    }
```

### 3. Evaluator-Optimizer — 迭代优化

```python
def iterative_improve(task: str, max_rounds: int = 3) -> str:
    result = generate(task)

    for _ in range(max_rounds):
        evaluation = evaluate(result, task)
        if evaluation["passed"]:
            break
        result = improve(result, evaluation["feedback"])

    return result
```

---

## Agent 实现

### 基础结构（带停止条件）

```python
import anthropic
import json

client = anthropic.Anthropic()

tools = [
    {
        "name": "search_web",
        "description": "搜索互联网获取最新信息。输入搜索关键词，返回相关结果摘要。",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词"}
            },
            "required": ["query"]
        }
    }
]

def run_agent(user_task: str, max_iterations: int = 20) -> str:
    messages = [{"role": "user", "content": user_task}]

    for i in range(max_iterations):  # 硬上限，防止死循环
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            tools=tools,
            messages=messages
        )

        # 任务完成
        if response.stop_reason == "end_turn":
            return response.content[0].text

        # 需要人工介入的情况
        if response.stop_reason == "max_tokens":
            return "任务超出 token 限制，需要人工处理"

        # 执行工具调用
        messages.append({"role": "assistant", "content": response.content})
        tool_results = []

        for block in response.content:
            if block.type == "tool_use":
                # 执行工具，获取结果
                result = execute_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result, ensure_ascii=False)
                })

        messages.append({"role": "user", "content": tool_results})

    return f"Agent 达到最大迭代次数（{max_iterations}），任务未完成"


def execute_tool(name: str, inputs: dict) -> dict:
    """工具执行层——所有工具调用结果必须做 schema validation"""
    if name == "search_web":
        # 实际搜索逻辑
        return {"results": f"搜索 '{inputs['query']}' 的结果..."}
    raise ValueError(f"未知工具: {name}")
```

---

## 工具设计原则

### 1. 绝对路径而非相对路径

Agent 在文件系统中移动后，相对路径会失效。文件工具强制要求绝对路径。

```python
# 错误
{"name": "read_file", "input": {"path": "./config.json"}}

# 正确
{"name": "read_file", "input": {"path": "/Users/user/project/config.json"}}
```

### 2. 工具描述写到初级工程师能理解

```python
{
    "name": "execute_sql",
    "description": """在 PostgreSQL 数据库执行 SQL 查询。
    
    只支持 SELECT 语句，不支持 INSERT/UPDATE/DELETE（只读权限）。
    查询超时 30 秒。
    返回格式：{"columns": [...], "rows": [[...], ...], "row_count": N}
    
    不同于 execute_python：此工具针对结构化数据查询，execute_python 用于数据处理。
    """,
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "要执行的 SELECT 语句"
            }
        },
        "required": ["query"]
    }
}
```

### 3. 不可逆操作必须有确认步骤

```python
def delete_files_tool(file_paths: list[str], confirmed: bool = False) -> dict:
    if not confirmed:
        return {
            "status": "requires_confirmation",
            "message": f"即将删除 {len(file_paths)} 个文件：{file_paths[:3]}{'...' if len(file_paths) > 3 else ''}。确认请传入 confirmed=True"
        }
    # 执行删除
    ...
```

---

## 常见失败模式

| 失败模式 | 症状 | 解法 |
|---------|------|------|
| 有限上下文导致"失忆" | 长任务后期忘记早期关键信息 | 用向量库存中间结果，定期做 context summarization |
| 幻觉工具调用 | 调用不存在的工具或错误参数 | 所有工具调用结果做 schema validation，错误反馈给模型重试 |
| 错误链式传播 | Step 3 错误导致后续全错 | 关键步骤后加 programmatic check，验证通过才继续 |
| 规划僵化 | 面对错误时重复同样失败动作 | 实现 Reflexion：让模型显式反思失败原因后重规划 |
| 输出格式不稳定 | JSON 缺括号、markdown 嵌套错误 | 解析代码必须健壮，失败时返回原文让模型重试 |

---

## Human-in-the-loop 检查点

Anthropic 建议在以下情况暂停等待人工确认：

- 不可逆操作（删除数据、发送邮件、执行支付）
- 置信度低的决策（让模型自评，低于阈值时暂停）
- 超过预设 token 或时间预算

```python
def agent_with_human_gate(task: str) -> str:
    plan = generate_plan(task)
    
    # 检测不可逆操作
    if has_irreversible_actions(plan):
        print(f"Agent 计划执行以下不可逆操作：\n{plan}")
        confirm = input("确认执行？(yes/no): ")
        if confirm.lower() != "yes":
            return "用户取消操作"
    
    return execute_plan(plan)
```

---

*大多数 Agent 问题的正确解法是：换成 Workflow。Agent 是最后手段，不是首选。*
