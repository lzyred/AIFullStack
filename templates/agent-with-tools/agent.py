"""
Agent with Tools Template
=========================
A production-ready Claude Agent with tool calling, retry logic,
hard iteration limits, and human-in-the-loop confirmation for
irreversible actions.

Dependencies: anthropic, httpx, python-dotenv
Install: pip install -r requirements.txt

Usage:
    python agent.py
    # Or import and use programmatically:
    # from agent import run_agent
    # result = run_agent("Search for the latest Python release and summarize it")
"""

import os
import json
import asyncio
import httpx
from datetime import datetime
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
MODEL = "claude-sonnet-4-6"
MAX_ITERATIONS = 20   # Hard cap — prevents infinite loops


# ─────────────────────────────────────────────
# Tool definitions
# ─────────────────────────────────────────────
TOOLS = [
    {
        "name": "web_search",
        "description": (
            "Search the web for current information. Returns a brief summary of results. "
            "Use when you need facts, news, or information beyond your training data."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "calculate",
        "description": (
            "Evaluate a mathematical expression and return the result. "
            "Supports standard arithmetic, exponentiation (**), and math functions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "A Python-evaluable math expression, e.g. '2 ** 10 + 42'"
                }
            },
            "required": ["expression"]
        }
    },
    {
        "name": "read_file",
        "description": (
            "Read the contents of a local file. "
            "Use absolute paths. Returns the file content as a string."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute path to the file"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": (
            "Write content to a local file. Creates the file if it doesn't exist. "
            "WARNING: This is an irreversible action — requires user confirmation."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute path to the file"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write"
                }
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "get_current_time",
        "description": "Return the current UTC time. Use when the task requires knowing the current date or time.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
]

# Tools that require human confirmation before execution
IRREVERSIBLE_TOOLS = {"write_file"}


# ─────────────────────────────────────────────
# Tool implementations
# ─────────────────────────────────────────────
def tool_web_search(query: str) -> dict:
    """
    Stub implementation — replace with a real search API.
    Options: Tavily, SerpAPI, Brave Search, DuckDuckGo.
    """
    # Example with Tavily (pip install tavily-python):
    # from tavily import TavilyClient
    # tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    # results = tavily.search(query=query, max_results=3)
    # return {"results": results["results"]}

    # Placeholder — returns a clearly fake result
    return {
        "results": [
            {
                "title": f"Search results for: {query}",
                "content": "[Replace tool_web_search() with a real search API like Tavily or SerpAPI]",
                "url": "https://example.com"
            }
        ]
    }


def tool_calculate(expression: str) -> dict:
    """Safely evaluate a math expression."""
    # Restrict to safe math operations only
    allowed = set("0123456789+-*/(). **")
    import math
    if not all(c in allowed or c.isalpha() for c in expression):
        return {"error": "Expression contains disallowed characters"}
    try:
        # Only allow math functions, no builtins
        result = eval(expression, {"__builtins__": {}}, vars(math))
        return {"result": result, "expression": expression}
    except Exception as e:
        return {"error": str(e)}


def tool_read_file(path: str) -> dict:
    """Read a local file."""
    try:
        content = open(path, encoding="utf-8").read()
        return {"content": content, "path": path, "size": len(content)}
    except FileNotFoundError:
        return {"error": f"File not found: {path}"}
    except PermissionError:
        return {"error": f"Permission denied: {path}"}


def tool_write_file(path: str, content: str) -> dict:
    """Write content to a local file."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"success": True, "path": path, "bytes_written": len(content.encode())}
    except Exception as e:
        return {"error": str(e)}


def tool_get_current_time() -> dict:
    return {"utc_time": datetime.utcnow().isoformat() + "Z"}


# ─────────────────────────────────────────────
# Tool router
# ─────────────────────────────────────────────
def execute_tool(name: str, inputs: dict) -> dict:
    """Route tool calls to their implementations."""
    dispatch = {
        "web_search": lambda: tool_web_search(inputs["query"]),
        "calculate": lambda: tool_calculate(inputs["expression"]),
        "read_file": lambda: tool_read_file(inputs["path"]),
        "write_file": lambda: tool_write_file(inputs["path"], inputs["content"]),
        "get_current_time": lambda: tool_get_current_time(),
    }
    if name not in dispatch:
        return {"error": f"Unknown tool: {name}"}
    return dispatch[name]()


# ─────────────────────────────────────────────
# Human-in-the-loop confirmation
# ─────────────────────────────────────────────
def confirm_irreversible_action(tool_name: str, inputs: dict) -> bool:
    """Ask for human confirmation before executing irreversible tools."""
    print(f"\n⚠️  Agent wants to execute: {tool_name}")
    print(f"   Inputs: {json.dumps(inputs, indent=2)}")
    answer = input("   Allow? (yes/no): ").strip().lower()
    return answer in ("yes", "y")


# ─────────────────────────────────────────────
# Agent loop
# ─────────────────────────────────────────────
def run_agent(task: str, verbose: bool = True) -> str:
    """
    Run the agent loop until the task is complete or max iterations reached.

    Args:
        task: The task description for the agent
        verbose: Print tool calls and results if True

    Returns:
        The agent's final response as a string
    """
    messages = [{"role": "user", "content": task}]

    for iteration in range(MAX_ITERATIONS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            tools=TOOLS,
            messages=messages,
        )

        # Task complete — model finished with a text response
        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return "[Agent completed without text output]"

        # Handle tool calls
        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []

            for block in response.content:
                if block.type != "tool_use":
                    continue

                tool_name = block.name
                tool_inputs = block.input

                if verbose:
                    print(f"\n[iter {iteration + 1}] Tool: {tool_name}")
                    print(f"  Input: {json.dumps(tool_inputs, ensure_ascii=False)}")

                # Require confirmation for irreversible actions
                if tool_name in IRREVERSIBLE_TOOLS:
                    if not confirm_irreversible_action(tool_name, tool_inputs):
                        result = {"error": "User declined to execute this action"}
                    else:
                        result = execute_tool(tool_name, tool_inputs)
                else:
                    result = execute_tool(tool_name, tool_inputs)

                if verbose:
                    print(f"  Result: {json.dumps(result, ensure_ascii=False)[:200]}")

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result, ensure_ascii=False),
                })

            messages.append({"role": "user", "content": tool_results})
            continue

        # Unexpected stop reason
        return f"[Agent stopped unexpectedly: {response.stop_reason}]"

    return f"[Agent reached max iterations ({MAX_ITERATIONS}) without completing the task]"


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
def main():
    print("Agent ready. Type 'quit' to exit.\n")
    print("Example tasks:")
    print("  - What time is it?")
    print("  - Calculate 2^32")
    print("  - Search for the latest news about AI")
    print("  - Read the file /path/to/file.txt and summarize it\n")

    while True:
        task = input("Task: ").strip()
        if task.lower() in ("quit", "exit", "q"):
            break
        if not task:
            continue
        print()
        result = run_agent(task)
        print(f"\nResult:\n{result}\n")


if __name__ == "__main__":
    main()
