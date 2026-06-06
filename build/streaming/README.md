# 流式输出实现指南

> 流式输出不降低总成本，但把用户体验从"等 5 秒"变成"0.5 秒开始看到内容"。

---

## 为什么流式输出很重要

LLM 生成一段 500 token 的回复需要 3-8 秒。非流式：用户盯着空白屏幕等待。流式：用户 500ms 内看到第一个字，感知延迟下降 80%。

---

## 后端实现

### Anthropic

```python
import anthropic

client = anthropic.Anthropic()

# 方式1：text_stream 迭代器（最简单）
with client.messages.stream(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[{"role": "user", "content": "解释量子纠缠"}]
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)

final = stream.get_final_message()
print(f"\n用量：{final.usage.input_tokens} in, {final.usage.output_tokens} out")


# 方式2：原始事件流（需要细粒度控制时）
with client.messages.stream(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[{"role": "user", "content": "解释量子纠缠"}]
) as stream:
    for event in stream:
        if hasattr(event, 'type'):
            if event.type == 'content_block_delta':
                if hasattr(event.delta, 'text'):
                    print(event.delta.text, end="", flush=True)
            elif event.type == 'message_stop':
                print("\n[完成]")
```

### OpenAI

```python
from openai import OpenAI

client = OpenAI()

stream = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "解释量子纠缠"}],
    stream=True,
    stream_options={"include_usage": True}  # 必须显式开启才能获取 token 用量
)

for chunk in stream:
    if chunk.choices and chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
    if chunk.usage:
        print(f"\n用量：{chunk.usage.total_tokens} tokens")
```

---

## SSE 接口（给前端用）

```python
# FastAPI + SSE 完整示例
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import anthropic
import json

app = FastAPI()
client = anthropic.Anthropic()

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    def generate():
        with client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": request.message}]
        ) as stream:
            for text in stream.text_stream:
                # SSE 格式：data: {json}\n\n
                yield f"data: {json.dumps({'text': text})}\n\n"

            # 流结束信号
            final = stream.get_final_message()
            yield f"data: {json.dumps({'done': True, 'usage': {'input': final.usage.input_tokens, 'output': final.usage.output_tokens}})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",         # 关键：防止缓存
            "X-Accel-Buffering": "no",           # 关键：Nginx 不缓冲
            "Connection": "keep-alive",
        }
    )
```

---

## 前端消费 SSE

```typescript
// React + TypeScript
async function streamChat(message: string, onChunk: (text: string) => void) {
  const response = await fetch('/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n\n').filter(line => line.startsWith('data: '));

    for (const line of lines) {
      const data = JSON.parse(line.slice(6));  // 去掉 "data: " 前缀
      if (data.text) {
        onChunk(data.text);
      }
      if (data.done) {
        console.log('用量:', data.usage);
      }
    }
  }
}

// 使用 Vercel AI SDK（推荐，封装了以上逻辑）
import { useChat } from 'ai/react';

export function Chat() {
  const { messages, input, handleInputChange, handleSubmit, isLoading } = useChat({
    api: '/api/chat',  // 对接 AI SDK 格式的后端
  });

  return (
    <div>
      {messages.map(m => (
        <div key={m.id}>{m.role}: {m.content}</div>
      ))}
      <form onSubmit={handleSubmit}>
        <input value={input} onChange={handleInputChange} disabled={isLoading} />
        <button type="submit">发送</button>
      </form>
    </div>
  );
}
```

---

## 常见踩坑

| 问题 | 症状 | 解法 |
|------|------|------|
| 内容不实时显示 | 流式请求但内容一次性出现 | 加 `flush=True`（Python），设置 Nginx `X-Accel-Buffering: no` |
| 流中断后丢失进度 | 网络抖动后内容消失 | 前端实现断线重连，后端记录生成进度（用 Redis 缓存中间结果） |
| SSE 被 CDN 缓存 | 所有用户看到同一内容 | 设置 `Cache-Control: no-cache`，或配置 CDN 对 `/stream` 路径不缓存 |
| 流式中途错误无法处理 | 用户看到截断的回复 | 用 try/catch 包住整个 stream 迭代，错误时发送 `data: {"error": "..."}` |
| 移动网络频繁断连 | 用户体验差 | 实现进度恢复：给每段内容加序号，断连后从断点续传 |
