"""
Streaming Chat Backend
======================
FastAPI backend with Server-Sent Events (SSE) streaming.
Connects to Anthropic Claude with full streaming support.

Dependencies: fastapi, uvicorn, anthropic, python-dotenv
Install: pip install -r requirements.txt

Run: uvicorn backend:app --reload --port 8000
"""

import os
import json
from typing import AsyncGenerator
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import anthropic
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Streaming Chat API")

# Allow all origins in development — restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

SYSTEM_PROMPT = """You are a helpful AI assistant. Be concise and direct.
If you don't know something, say so — don't make things up."""


# ─────────────────────────────────────────────
# Request / Response models
# ─────────────────────────────────────────────
class Message(BaseModel):
    role: str   # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    model: str = "claude-haiku-4-5"
    max_tokens: int = 1024


# ─────────────────────────────────────────────
# SSE Generator
# ─────────────────────────────────────────────
async def stream_response(request: ChatRequest) -> AsyncGenerator[str, None]:
    """Yield SSE events from Claude's streaming API."""
    messages = [{"role": m.role, "content": m.content} for m in request.messages]

    try:
        with client.messages.stream(
            model=request.model,
            max_tokens=request.max_tokens,
            system=SYSTEM_PROMPT,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                # SSE format: data: <json>\n\n
                yield f"data: {json.dumps({'type': 'text', 'text': text})}\n\n"

            # Send usage stats at the end
            final = stream.get_final_message()
            yield f"data: {json.dumps({'type': 'done', 'usage': {'input_tokens': final.usage.input_tokens, 'output_tokens': final.usage.output_tokens}})}\n\n"

    except anthropic.APIError as e:
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"


# ─────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────
@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    return StreamingResponse(
        stream_response(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # Disable Nginx buffering
            "Connection": "keep-alive",
        },
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


# ─────────────────────────────────────────────
# Serve the frontend (development convenience)
# ─────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the bundled frontend for development."""
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(html_path) as f:
        return f.read()
