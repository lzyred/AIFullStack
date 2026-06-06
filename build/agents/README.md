[中文](README.zh.md) | **English**

# Agent Design Guide

> Karpathy check: grounded in Anthropic engineering team guidance and Lilian Weng's research; all code is runnable.

---

## The Core Question: Do You Actually Need an Agent?

**Agents are severely overused.** Most "agent applications" should be workflows instead.

```
Decision flow:
│
├── Can a single LLM call + retrieval solve it?
│   └── Yes → Don't use an agent. Just do it directly.
│
├── Can it be broken into a fixed sequence of steps?
│   └── Yes → Use a Workflow (predictable, debuggable, cost-controllable)
│       ├── Fixed step order → Prompt Chaining
│       ├── Needs classification/routing → Routing
│       ├── Subtasks are independent → Parallelization
│       └── Needs iterative refinement → Evaluator-Optimizer
│
└── Number of steps can't be determined upfront; model must plan dynamically?
    └── Only then consider an Agent
```

### Signals That You Need an Agent

- The task requires multiple rounds of tool calls where each step depends on the previous result
- The solution path can't be hardcoded in advance
- There is a clear, verifiable success criterion (tests pass, API returns 200, etc.)

### Signals That You Should Not Use an Agent

- You need low latency (every tool call adds 500ms–2s)
- Budget is a constraint (agent token consumption runs 5–20x higher than sequential calls)
- Actions are irreversible (payments, deletions, sending emails)

---

## Workflow Patterns (Prefer These)

### 1. Prompt Chaining — Sequential Processing

```python
import anthropic

client = anthropic.Anthropic()

def chain(input_text: str) -> str:
    # Step 1: Extract key facts
    extracted = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=500,
        messages=[{"role": "user", "content": f"Extract the key facts from the following text:\n{input_text}"}]
    ).content[0].text

    # Step 2: Synthesize a summary from the extracted facts
    summary = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=200,
        messages=[{"role": "user", "content": f"Write a concise summary from the following key facts:\n{extracted}"}]
    ).content[0].text

    return summary
```

### 2. Parallelization — Independent Subtasks Run Concurrently

```python
import asyncio
import anthropic

client = anthropic.AsyncAnthropic()

async def parallel_analysis(document: str) -> dict:
    tasks = [
        client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=200,
            messages=[{"role": "user", "content": f"Extract all person names from the document:\n{document}"}]
        ),
        client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=200,
            messages=[{"role": "user", "content": f"Extract all dates from the document:\n{document}"}]
        ),
        client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=200,
            messages=[{"role": "user", "content": f"Extract all monetary amounts from the document:\n{document}"}]
        ),
    ]
    results = await asyncio.gather(*tasks)
    return {
        "names": results[0].content[0].text,
        "dates": results[1].content[0].text,
        "amounts": results[2].content[0].text,
    }
```

### 3. Evaluator-Optimizer — Iterative Refinement

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

## Agent Implementation

### Core Structure (with a Hard Stop Condition)

```python
import anthropic
import json

client = anthropic.Anthropic()

tools = [
    {
        "name": "search_web",
        "description": "Search the internet for up-to-date information. Provide a search query; returns a summary of relevant results.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"}
            },
            "required": ["query"]
        }
    }
]

def run_agent(user_task: str, max_iterations: int = 20) -> str:
    messages = [{"role": "user", "content": user_task}]

    for i in range(max_iterations):  # Hard cap to prevent infinite loops
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            tools=tools,
            messages=messages
        )

        # Task complete
        if response.stop_reason == "end_turn":
            return response.content[0].text

        # Situations requiring human intervention
        if response.stop_reason == "max_tokens":
            return "Task exceeded token limit — requires human review"

        # Execute tool calls
        messages.append({"role": "assistant", "content": response.content})
        tool_results = []

        for block in response.content:
            if block.type == "tool_use":
                # Execute the tool and collect the result
                result = execute_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result, ensure_ascii=False)
                })

        messages.append({"role": "user", "content": tool_results})

    return f"Agent reached maximum iterations ({max_iterations}) without completing the task"


def execute_tool(name: str, inputs: dict) -> dict:
    """Tool execution layer — all tool outputs must be schema-validated"""
    if name == "search_web":
        # Actual search logic goes here
        return {"results": f"Results for '{inputs['query']}'..."}
    raise ValueError(f"Unknown tool: {name}")
```

---

## Tool Design Principles

### 1. Absolute Paths, Not Relative Paths

Relative paths break as soon as the agent moves around the filesystem. File tools should require absolute paths.

```python
# Wrong
{"name": "read_file", "input": {"path": "./config.json"}}

# Correct
{"name": "read_file", "input": {"path": "/Users/user/project/config.json"}}
```

### 2. Write Tool Descriptions a Junior Engineer Can Follow

```python
{
    "name": "execute_sql",
    "description": """Execute a SQL query against the PostgreSQL database.

    Supports SELECT statements only — INSERT/UPDATE/DELETE are not permitted (read-only access).
    Query timeout: 30 seconds.
    Return format: {"columns": [...], "rows": [[...], ...], "row_count": N}

    Different from execute_python: this tool is for structured data queries; use execute_python for data processing.
    """,
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The SELECT statement to execute"
            }
        },
        "required": ["query"]
    }
}
```

### 3. Irreversible Operations Must Include a Confirmation Step

```python
def delete_files_tool(file_paths: list[str], confirmed: bool = False) -> dict:
    if not confirmed:
        return {
            "status": "requires_confirmation",
            "message": f"About to delete {len(file_paths)} file(s): {file_paths[:3]}{'...' if len(file_paths) > 3 else ''}. Pass confirmed=True to proceed."
        }
    # Execute deletion
    ...
```

---

## Common Failure Modes

| Failure mode | Symptom | Fix |
|-------------|---------|-----|
| Context amnesia | Agent forgets critical early information on long tasks | Store intermediate results in a vector store; periodically summarize context |
| Hallucinated tool calls | Agent calls nonexistent tools or passes wrong parameters | Schema-validate all tool outputs; return errors to the model for retry |
| Error propagation | A mistake in step 3 corrupts everything downstream | Add programmatic checks after critical steps; only continue if validation passes |
| Rigid planning | Agent repeats the same failing action when it hits an error | Implement Reflexion: have the model explicitly reflect on failure before replanning |
| Unstable output format | JSON missing brackets, malformed markdown | Parsing code must be robust; on failure, return the raw text and ask the model to retry |

---

## Human-in-the-Loop Checkpoints

Anthropic recommends pausing for human confirmation in these situations:

- Irreversible operations (deleting data, sending emails, processing payments)
- Low-confidence decisions (have the model self-assess; pause below a threshold)
- Exceeded token or time budget

```python
def agent_with_human_gate(task: str) -> str:
    plan = generate_plan(task)
    
    # Check for irreversible actions
    if has_irreversible_actions(plan):
        print(f"Agent is planning the following irreversible actions:\n{plan}")
        confirm = input("Proceed? (yes/no): ")
        if confirm.lower() != "yes":
            return "Operation cancelled by user"
    
    return execute_plan(plan)
```

---

*For most problems that seem to call for an agent, the right answer is: use a workflow instead. Agents are the last resort, not the default.*

---

*[中文版 (Chinese)](README.zh.md)*
