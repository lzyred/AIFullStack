[中文](README.zh.md) | **English**

# Streaming Chat Template

FastAPI backend + vanilla HTML/JS frontend. Full streaming via Server-Sent Events (SSE). No build step, no framework dependencies on the frontend — open `index.html` or hit `/` in your browser.

## Structure

```
streaming-chat/
├── backend.py    # FastAPI + SSE streaming endpoint
├── index.html    # Frontend (no build step required)
├── requirements.txt
└── .env.example
```

## Quick Start

```bash
# 1. Install
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env

# 3. Run
uvicorn backend:app --reload --port 8000

# 4. Open http://localhost:8000 in your browser
```

## API

### POST `/chat/stream`

```json
{
  "messages": [
    {"role": "user", "content": "Hello!"}
  ],
  "model": "claude-haiku-4-5",
  "max_tokens": 1024
}
```

Returns an SSE stream with events:

```
data: {"type": "text", "text": "Hello"}
data: {"type": "text", "text": "!"}
data: {"type": "done", "usage": {"input_tokens": 12, "output_tokens": 5}}
```

## Production Checklist

```
□ Restrict CORS origins (replace "*" with your domain)
□ Add rate limiting (e.g., slowapi)
□ Add authentication (JWT or API key header)
□ Switch to a persistent conversation store (Redis)
□ Set up proper error monitoring
□ Move to a production ASGI server (gunicorn + uvicorn workers)
```

See [`build/streaming/README.md`](../../build/streaming/README.md) for in-depth streaming guidance.

---

*[中文版 (Chinese)](README.zh.md)*
