# AIFullStack

**构建 AI 应用时，你的文档应该和你的代码一样可靠。**

---

独立开发一个 AI 应用，你大概率遇到过这些情况：

- 搜索"如何实现流式输出"，找到 8 篇文章，有 3 篇用的是已废弃的 API
- 官方文档更新了，但你收藏的教程还是旧版本的写法
- 问 AI 助手一个具体问题，得到一个看起来合理但无法验证来源的答案
- 从 LangChain 切换到别的框架，不知道从哪里找到靠谱的对比资料

这个仓库试图解决一个具体问题：**让 AI 应用全栈开发者能快速找到可信、时效的技术文档，并直接作为上下文注入到开发工作流中。**

---

## 覆盖范围

面向**用 LLM 构建产品**的开发者，不包含模型训练和研究内容。

| 方向 | 包含内容 |
|------|---------|
| Prompt 工程 | 系统提示设计、few-shot、结构化输出 |
| 前端集成 | Streaming UI、Vercel AI SDK、实时交互组件 |
| 后端实现 | LLM API 接入、RAG 搭建、Agent 设计、工作流 |
| 基础设施 | 部署方案、成本控制、日志监控、Prompt 安全 |
| 质量评估 | 测试策略、LLM-as-Judge、回归检测 |

---

## 为什么不直接看官方文档

官方文档能解决"这个 API 怎么用"，但解决不了：

- **跨平台对比**：OpenAI / Anthropic / Gemini 在同一个场景下该怎么选
- **踩坑记录**：某个方案在生产环境的已知问题
- **最佳实践沉淀**：社区验证过的模式，而不是官方示例的 hello world
- **时效性保证**：你需要的是当前版本的写法，不是半年前的

---

## 文档质量标准

入库文档需满足：

- 有明确的发布日期和版本信息
- 来自官方渠道、知名工程师或有实际验证的案例
- 代码示例可以在当前 API 版本下运行
- 不是转载、聚合或营销内容

过时文档会被标记或移除，而不是留在库里降低检索质量。

---

## 文档来源

优先从以下渠道获取，按可信度排序：

1. **`llms.txt`** — 官方文档提供的 LLM 友好索引（Anthropic、FastHTML 等已支持）
2. **官方 GitHub 仓库** — OpenAI Cookbook、Vercel AI SDK docs、LlamaIndex 等
3. **一手工程博客** — 有具名作者、有结论依据的深度文章
4. **高质量 GitHub Issues** — 记录真实问题和解决过程的讨论

---

## 技术架构

```
文档采集
  llms.txt / GitHub repos / Firecrawl（网页）
        ↓
  解析 → 语义分块 → Embedding → 元数据标注
        ↓
  Qdrant（向量检索）+ PostgreSQL（元数据）
        ↓
  混合检索（向量 + 关键词）→ Reranker → 带引用的答案
```

同步机制采用后台 Worker 定时轮询，检测源文档变更后增量入库。

---

## 开发状态

目前处于设计阶段，正在实现文档处理 Pipeline 和连接器。

如果你也在做类似的事情，欢迎一起讨论。

---

## 参考项目

- [Onyx](https://github.com/onyx-dot-app/onyx) — 连接器设计和增量同步机制
- [RAGFlow](https://github.com/infiniflow/ragflow) — 文档存储和处理架构
- [Firecrawl](https://github.com/firecrawl/firecrawl) — 网页内容提取
- [llms.txt](https://llmstxt.org) — 文档的 LLM 友好格式标准
