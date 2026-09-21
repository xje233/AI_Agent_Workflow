# RAG evaluation

This checked-in set contains 50 questions across `fact`, `cross_chunk`,
`unanswerable`, and `ocr` categories. The corpus is synthetic and contains no
company or user data. OCR rows are transcriptions of scanned-document fixtures;
they evaluate retrieval after OCR, while loader OCR behavior is tested separately.

From `backend`:

```powershell
python scripts/evaluate_rag.py --validate-only
python scripts/evaluate_rag.py --k 3
python scripts/evaluate_rag.py --k 3 --answers evaluation/rag/answers.jsonl
```

The live run creates a temporary Chroma collection, prints the report, writes
`latest-report.json`, and removes the collection. Generated answers are optional
JSONL rows shaped as `{"id":"fact-001","answer":"..."}`. Accuracy remains
`null` when answers are not supplied, so retrieval support is not mislabeled as
answer correctness.

## 公开测评集（复用方案）

`evaluation/flashrag/` 下的数据集由 `scripts/setup_flashrag_eval.py` 从
FlashRAG 下载并转换而来。对只覆盖部分类别的公开数据集，评测脚本需要：

```powershell
python scripts/evaluate_rag.py --data-dir evaluation/flashrag/domainrag --no-require-all-categories --k 3
```

`--data-dir` 切换语料/题目目录；`--no-require-all-categories` 允许仅覆盖
`fact` 单一类别。详见 `evaluation/flashrag/domainrag/README.md`。

## 已知修复：Embedding 长文本退化

`app/rag/retriever.py` 原先使用 langchain `OpenAIEmbeddings`，其默认
tiktoken 分词会把中文文本拆成 token id 数组再发给硅基流动等 OpenAI 兼容
服务，导致长文档 embedding 语义退化（检索质量随文本长度急剧下降）。
已改为直接调用 OpenAI client 的 `_DirectOpenAIEmbeddings`，修复后
DomainRAG 评测 recall@3 从 0.05 提升到 0.79。
