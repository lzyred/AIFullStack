[English](README.md) | **中文**

# 流式对话模板

FastAPI 后端 + 原生 HTML/JS 前端。通过 SSE（Server-Sent Events）实现完整流式输出。前端无需构建步骤，直接在浏览器打开 `index.html` 或访问 `/` 即可。

## 文件结构

```
streaming-chat/
├── backend.py    # FastAPI + SSE 流式接口
├── index.html    # 前端（无需构建）
├── requirements.txt
└── .env.example
```

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置
cp .env.example .env
# 在 .env 中填入你的 ANTHROPIC_API_KEY

# 3. 启动
uvicorn backend:app --reload --port 8000

# 4. 浏览器打开 http://localhost:8000
```

## API 说明

### POST `/chat/stream`

```json
{
  "messages": [
    {"role": "user", "content": "你好！"}
  ],
  "model": "claude-haiku-4-5",
  "max_tokens": 1024
}
```

返回 SSE 事件流：

```
data: {"type": "text", "text": "你好"}
data: {"type": "text", "text": "！"}
data: {"type": "done", "usage": {"input_tokens": 12, "output_tokens": 5}}
```

## 上线前检查清单

```
□ 限制 CORS origins（把 "*" 改为你的域名）
□ 加速率限制（如 slowapi）
□ 加认证（JWT 或 API Key Header）
□ 换持久化会话存储（Redis）
□ 接入错误监控
□ 换生产级 ASGI 服务器（gunicorn + uvicorn workers）
```

详细流式输出实现指南见 [`build/streaming/README.zh.md`](../../build/streaming/README.zh.md)。

---

*[English Version](README.md)*
