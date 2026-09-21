# DomainRAG 公开评测集（FlashRAG）

来自 FlashRAG（RUC-NLPIR）的 DomainRAG 测试集（485 条中文问题，RUC 官方网页域内问答），
作为「复用公开测评集验证评测器」的最小成本方案。每条样本的
`positive_reference` 直接内嵌在 JSON 中，无需下载独立的检索语料库
（完整 wiki 语料约 96 GB，本方案只下载 23 MB 的 test.jsonl）。

## 数据来源

- ModelScope: `hhjinjiajie/FlashRAG_Dataset` 中的 `domainrag/test.jsonl`
- 原始库: https://github.com/RUC-NLPIR/FlashRAG

## 使用方式

从 `backend` 目录执行：

```powershell
# 1. 下载并转换（已缓存则跳过下载）
python scripts/setup_flashrag_eval.py --dataset domainrag --split test

# 2. 校验数据集
python scripts/evaluate_rag.py --data-dir evaluation/flashrag/domainrag --no-require-all-categories --validate-only

# 3. 运行评测（k=3）
python scripts/evaluate_rag.py --data-dir evaluation/flashrag/domainrag --no-require-all-categories --k 3
```

`--no-require-all-categories` 允许只覆盖 `fact` 单一类别的公开数据集通过校验
（项目自带评测集仍默认要求全部类别）。

## 结果

最新一次评测（bge-m3 via 硅基流动）：

- recall@3: 0.7876
- MRR: 0.6787
- samples: 485

## 注意

DomainRAG 的问题带多轮对话历史（`metadata.query` 拼接了上下文），转换脚本使用
`query` 字段作为检索输入。评测器将全部题目映射为 `fact` 类别。
