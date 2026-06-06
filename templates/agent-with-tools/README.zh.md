[English](README.md) | **中文**

# 带工具调用的 Agent 模板

生产级 Claude Agent 骨架，包含：
- 5 个示例工具（网络搜索、计算器、文件读写、时间）
- 硬性迭代上限（防止死循环）
- 不可逆操作的人工确认门
- 清晰的工具路由模式——10 行代码即可添加新工具

## 文件结构

```
agent-with-tools/
├── agent.py         # 完整 Agent 循环 + 工具实现
├── requirements.txt
└── .env.example
```

## 快速开始

```bash
pip install -r requirements.txt
cp .env.example .env
# 填入你的 ANTHROPIC_API_KEY

python agent.py
```

## 添加新工具

1. 在 `TOOLS` 列表中添加工具描述：

```python
{
    "name": "my_tool",
    "description": "工具的用途和使用场景（写清楚，模型需要靠这个判断何时调用）。",
    "input_schema": {
        "type": "object",
        "properties": {
            "param": {"type": "string", "description": "参数说明"}
        },
        "required": ["param"]
    }
}
```

2. 在 `execute_tool` 中添加实现：

```python
"my_tool": lambda: my_tool_function(inputs["param"]),
```

3. 如果是不可逆操作（删除、发送、支付），把工具名加到 `IRREVERSIBLE_TOOLS`。

## 什么时候用 Agent，什么时候用 Workflow

**用这个 Agent 模板**：步骤数量无法预先确定，下一步依赖上一步的结果。

**用 Prompt Chaining Workflow**：步骤固定可预测——会比 Agent 可靠 3 倍以上。

完整判断框架见 [`build/agents/README.zh.md`](../../build/agents/README.zh.md)。

## 替换网络搜索 Stub

`tool_web_search` 是一个占位实现。替换为真实 API：

```bash
pip install tavily-python
```

```python
from tavily import TavilyClient
tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

def tool_web_search(query: str) -> dict:
    results = tavily.search(query=query, max_results=3)
    return {"results": results["results"]}
```

---

*[English Version](README.md)*
