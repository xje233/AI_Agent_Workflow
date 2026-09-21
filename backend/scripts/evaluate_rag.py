"""Run the checked-in RAG evaluation set against the configured vector store."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from langchain.schema import Document

from app.evaluation.rag import load_cases, load_jsonl, score_answers, score_retrieval, validate_dataset
from app.rag.retriever import add_documents, get_vector_store, similarity_search

DEFAULT_DATA_DIR = BACKEND_DIR / "evaluation" / "rag"


async def run(k: int, answers_path: Path | None, data_dir: Path, require_all_categories: bool = True) -> dict:
    document_rows = load_jsonl(data_dir / "corpus.jsonl")
    cases = load_cases(data_dir / "questions.jsonl")
    validate_dataset(cases, {row["id"] for row in document_rows}, require_all_categories=require_all_categories)

    collection = f"rag_eval_{uuid.uuid4().hex}"
    documents = [
        Document(page_content=row["text"], metadata={"doc_id": row["id"], "source": row["source"], "page": row.get("page")})
        for row in document_rows
    ]
    vector_store = get_vector_store(collection)
    try:
        await add_documents(documents, collection)
        results = {}
        for case in cases:
            hits = await similarity_search(case.question, k=k, collection_name=collection)
            # Chroma always returns nearest neighbors. A no-answer case therefore
            # needs a future relevance threshold; retaining hits exposes that gap.
            results[case.id] = [doc.metadata["doc_id"] for doc in hits]
        report = score_retrieval(cases, results, k=k)
        if answers_path:
            answer_rows = load_jsonl(answers_path)
            report["answer_evaluation"] = score_answers(cases, {row["id"]: row["answer"] for row in answer_rows})
        else:
            report["answer_evaluation"] = {"judged_samples": 0, "accuracy": None, "note": "Pass --answers to score generated answers."}
        return report
    finally:
        vector_store._client.delete_collection(collection)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate the configured RAG retriever")
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--answers", type=Path, help="Optional JSONL rows with id and answer fields")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR, help="Directory with corpus.jsonl and questions.jsonl")
    parser.add_argument("--no-require-all-categories", action="store_true", help="Allow datasets that only cover a subset of categories")
    parser.add_argument("--output", type=Path, default=None, help="Report path (default: <data-dir>/latest-report.json)")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    require_all = not args.no_require_all_categories
    data_dir = args.data_dir
    output = args.output or data_dir / "latest-report.json"

    documents = load_jsonl(data_dir / "corpus.jsonl")
    cases = load_cases(data_dir / "questions.jsonl")
    validate_dataset(cases, {row["id"] for row in documents}, require_all_categories=require_all)
    if args.validate_only:
        print(json.dumps({"status": "ok", "documents": len(documents), "questions": len(cases)}, ensure_ascii=False))
        return 0

    report = asyncio.run(run(args.k, args.answers, data_dir, require_all_categories=require_all))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
