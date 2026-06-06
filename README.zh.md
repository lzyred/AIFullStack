[English](README.md) | **中文**

# AIFullStack

**如果 Karpathy 教你写代码，Andrew Chen 教你找用户，Sam Altman 告诉你为什么值得做——你会做出什么？**

---

独立做一个 AI 产品，你需要三种能力同时在线：

**能建起来。能让人用。知道为什么值得做。**

AI 领域里，有三个人分别把这三种能力做到了极致。这个仓库把他们方法论里最可操作的部分，整理成开发者能直接用的文档、代码和决策框架。

---

## 铁三角

### Andrej Karpathy · 首席工程师视角

OpenAI 联合创始人，Tesla Autopilot 负责人。他提出"Software 2.0"——神经网络是新的代码，提示词是新的编程语言。

他的判断：大多数开发者做 AI 应用时，只是在调用 API。真正的差距在于理解模型的行为边界——为什么它会幻觉，为什么 RAG 检索不准，为什么 Agent 会失控。理解底层，才能在出问题时知道去哪里修。

**他代表的问题：你的系统，真的能稳定工作吗？**

---

### Andrew Chen · 增长负责人视角

a16z 普通合伙人，前 Uber 增长主管，《The Cold Start Problem》作者。他研究的核心命题只有一个：一个新产品，如何从 0 个用户增长到百万？

他的判断：AI 功能本身不是护城河。大多数 AI 产品死于用户用了一次就不再回来，而不是技术不够好。留存率是一切增长的地基——没有留存，你的获客成本是无底洞。

**他代表的问题：用户为什么要反复使用你的产品，而不是换一个？**

---

### Sam Altman · 产品战略视角

OpenAI CEO，前 Y Combinator 主席。他比任何人都更早、更深地思考 AI 对创业的影响，同时保持对"什么值得做"的极度挑剔。

他的判断：现在做 AI 产品的窗口是真实存在的，但大多数人在等技术更成熟。问题从来不是技术准备好了没有——而是你解决的问题够不够真实，用户的痛够不够深。

**他代表的问题：10 年后，这件事还重要吗？**

---

## 这个仓库解决什么问题

做 AI 应用时，你大概遇到过这些：

- 找到的教程用的是半年前的 API，代码跑不通
- 技术上实现了，但不知道用户凭什么用你的而不是直接用 ChatGPT
- 花了两个月做了功能完整的产品，结果发现没有人真正需要它

这三个问题，分别是 Karpathy、Andrew Chen、Sam Altman 最关心的问题。

这个仓库不是教你调 API。是帮你做出**一个能活下来的 AI 产品**。

---

## 内容结构

```
AIFullStack/
│
├── build/                          # Karpathy 层：怎么建
│   ├── llm-fundamentals/           # 工程师视角的 LLM 底层：token、上下文、成本
│   ├── prompt-engineering/         # 系统提示设计、结构化输出、常见 anti-patterns
│   ├── rag/                        # 分块策略、Embedding 选型、混合检索、生产踩坑
│   ├── agents/                     # 什么时候用 Agent，怎么让它可靠而不是失控
│   ├── streaming/                  # SSE 实现、断线重连、前端实时交互
│   └── infrastructure/             # 部署方案、成本控制、日志监控、Prompt 安全
│
├── grow/                           # Andrew Chen 层：怎么长
│   ├── retention/                  # AI 产品的留存机制：为什么用户第二天不回来
│   ├── cold-start/                 # 第一批用户从哪里来，冷启动的几种真实路径
│   ├── growth-loops/               # 增长循环设计：病毒传播、内容循环、工具黏性
│   └── metrics/                    # 什么数据说明你在正确的路上
│
├── vision/                         # Sam Altman 层：值不值得做
│   ├── positioning/                # 止痛药 vs 维生素：用户真正愿意付钱的是什么
│   ├── market-timing/              # 时机判断：现在该做什么，6 个月后该做什么
│   └── validation/                 # 用最小资源验证最大假设的框架
│
├── comparisons/                    # 横向对比：帮你做选型决策，不踩别人踩过的坑
│   ├── llm-providers.md            # OpenAI / Anthropic / Gemini：同一场景下怎么选
│   ├── vector-databases.md         # Qdrant / Pinecone / pgvector：成本与性能权衡
│   └── frameworks.md               # LangChain / LlamaIndex / 裸 API：真实使用体验
│
└── case-studies/                   # 完整项目复盘：从 0 到上线的真实决策过程
    ├── rag-chatbot/                 # 企业知识库问答系统
    ├── ai-writing-tool/             # AI 写作辅助产品
    └── agent-workflow/              # 多步骤自动化 Agent
```

---

## 如何使用这个仓库

**你在解决技术问题** → 从 `build/` 开始，找对应模块

**你有产品但没用户** → 直接去 `grow/retention/`，先弄清楚留存

**你还在找方向，不确定做什么** → 从 `vision/positioning/` 开始

**你需要选技术栈** → 去 `comparisons/`，有横向对比和真实踩坑记录

**你想看完整项目怎么做** → 去 `case-studies/`，有从 0 到上线的决策过程

---

## 文档质量标准

每份文档在发布前需通过三个检验：

| 检验 | 标准 |
|------|------|
| **Karpathy 检验** | 技术细节准确，代码在当前 API 版本下可以运行，不用旧写法 |
| **Andrew Chen 检验** | 有可操作的结论，能直接用，不是"要根据情况判断"的废话 |
| **Sam Altman 检验** | 解决真实问题，不是在展示技术可能性或者堆砌工具 |

过时内容会被标记或移除。检索质量比内容数量重要。

---

## 当前状态

内容持续填充中，优先级：

- `build/rag/` — 生产级 RAG 实现，包含真实踩坑记录
- `build/agents/` — 可靠 Agent 设计模式
- `grow/retention/` — AI 产品留存框架

如果你在做 AI 产品，有踩坑记录或实战经验，欢迎提 PR 或开 Issue 讨论。

---

*三个视角，一个目标：帮你用 AI 做出一个真正活着的产品。*


---

*[English Version](README.md)*
