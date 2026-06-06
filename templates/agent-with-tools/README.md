[中文](README.zh.md) | **English**

# Agent with Tools Template

A production-ready Claude Agent skeleton with:
- 5 example tools (web search, calculator, file read/write, time)
- Hard iteration limit (prevents infinite loops)
- Human-in-the-loop confirmation for irreversible actions
- Clean tool router pattern — add new tools in 10 lines

## Structure

```
agent-with-tools/
├── agent.py         # Complete agent loop + tools
├── requirements.txt
└── .env.example
```

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env
# Add your ANTHROPIC_API_KEY

python agent.py
```

## Adding a New Tool

1. Add the tool schema to `TOOLS`:

```python
{
    "name": "my_tool",
    "description": "What it does and when to use it.",
    "input_schema": {
        "type": "object",
        "properties": {
            "param": {"type": "string", "description": "..."}
        },
        "required": ["param"]
    }
}
```

2. Add the implementation to `execute_tool`:

```python
"my_tool": lambda: my_tool_function(inputs["param"]),
```

3. If it's irreversible (deletes, sends, pays), add its name to `IRREVERSIBLE_TOOLS`.

## When to Use This vs. a Workflow

Use this Agent template when the number of steps can't be determined in advance and depends on intermediate results.

Use a simpler Prompt Chaining workflow when the steps are fixed and predictable — it'll be 3x more reliable.

See [`build/agents/README.md`](../../build/agents/README.md) for the full decision framework.

## Replacing the Web Search Stub

The `tool_web_search` function is a stub. Replace it with a real API:

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

*[中文版 (Chinese)](README.zh.md)*
