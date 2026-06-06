[English](README.md) | **中文**

# 极简 RAG 模板

约 130 行代码实现完整 RAG Pipeline，无需外部向量数据库，使用内存存储。5 分钟内开始查询你的文档。

## 文件结构

```
minimal-rag/
├── main.py          # 完整 RAG Pipeline
├── requirements.txt
├── .env.example
└── docs/
    └── example.md  # 测试用示例文档
```

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 API Key
cp .env.example .env
# 编辑 .env，填入 ANTHROPIC_API_KEY 和 OPENAI_API_KEY

# 3. 把你的文档放到 docs/ 目录（.txt 或 .md 文件）

# 4. 运行
python main.py
```

## 工作原理

```
docs/*.md / *.txt
    → 分块（500 字符，50 字符重叠）
    → Embedding（OpenAI text-embedding-3-small）
    → 内存存储（numpy 余弦相似度）

用户提问
    → 对问题做 Embedding
    → 余弦相似度找 top-3 相关块
    → Claude Haiku 生成带来源引用的答案
```

## 升级路径

当这个模板不够用时：

| 需求 | 下一步 |
|------|--------|
| > 10万个 chunk | 换 Qdrant（`pip install qdrant-client`） |
| 更好的召回率 | 加 BM25 混合检索 |
| 更快的检索速度 | 加 HNSW 索引 |
| 更高的答案质量 | 加 Reranker（`cross-encoder/ms-marco-MiniLM-L-12-v2`） |

生产级版本见 [`build/rag/README.md`](../../build/rag/README.zh.md)。

---

*[English Version](README.md)*
