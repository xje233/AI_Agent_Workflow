"""Download a FlashRAG dataset and convert it to the project's evaluation JSONL format.

DomainRAG is the cheapest option: each sample embeds its own positive_reference
document, so no separate retrieval corpus needs to be downloaded.

Usage (from backend/):
    python scripts/setup_flashrag_eval.py --dataset domainrag --split test
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.evaluation.rag import load_jsonl  # noqa: E402

MODELSCOPE_BASE = "https://modelscope.cn/api/v1/datasets/hhjinjiajie/FlashRAG_Dataset/repo"
DEFAULT_OUTPUT = BACKEND_DIR / "evaluation" / "flashrag"


def download(dataset: str, split: str, dest: Path) -> None:
    """Download the dataset's jsonl from ModelScope."""
    url = f"{MODELSCOPE_BASE}?Revision=master&FilePath={dataset}/{split}.jsonl"
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as resp, dest.open("wb") as handle:
        while chunk := resp.read(1024 * 1024):
            handle.write(chunk)
    print(f"downloaded {dest} ({dest.stat().st_size} bytes)")


def convert(cases_path: Path, output_dir: Path) -> tuple[int, int, int]:
    """Extract corpus + questions from FlashRAG samples with inline references.

    Returns (document count, question count, skipped count).
    """
    rows = load_jsonl(cases_path)
    doc_index: dict[tuple[str, str], str] = {}
    docs: dict[str, dict] = {}
    questions = []
    skipped = 0

    def doc_id(ref: dict) -> str:
        key = (ref.get("title", ""), ref.get("url", ""))
        if key not in doc_index:
            did = f"doc-{len(doc_index) + 1:04d}"
            doc_index[key] = did
            docs[did] = {
                "id": did,
                "text": ref.get("contents", ""),
                "source": ref.get("url", ""),
                "page": None,
            }
        return doc_index[key]

    def collect_refs(value: object) -> list[dict]:
        if not value:
            return []
        if isinstance(value, dict):
            return [value]
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        return []

    for index, row in enumerate(rows, 1):
        meta = row.get("metadata") or {}
        refs = []
        for entry in meta.get("positive_reference") or []:
            refs.extend(collect_refs(entry))
        for item in meta.get("history") or []:
            refs.extend(collect_refs(item.get("positive_reference")))
        if not refs:
            skipped += 1
            continue
        relevant = [doc_id(ref) for ref in refs]
        answers = row.get("golden_answers") or []
        if not answers:
            skipped += 1
            continue
        questions.append(
            {
                "id": f"q-{index:04d}",
                "category": "fact",
                "question": meta.get("query") or row.get("question", ""),
                "relevant_doc_ids": relevant,
                "answer_keywords": [answers[0]],
            }
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "corpus.jsonl").write_text(
        "".join(json.dumps(d, ensure_ascii=False) + "\n" for d in docs.values()),
        encoding="utf-8",
    )
    (output_dir / "questions.jsonl").write_text(
        "".join(json.dumps(q, ensure_ascii=False) + "\n" for q in questions),
        encoding="utf-8",
    )
    return len(docs), len(questions), skipped


def main() -> int:
    parser = argparse.ArgumentParser(description="Download and convert a FlashRAG dataset")
    parser.add_argument("--dataset", default="domainrag", help="Dataset name, e.g. domainrag")
    parser.add_argument("--split", default="test", help="Split to use, e.g. test")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    raw = args.output / args.dataset / f"{args.split}.jsonl"
    if not raw.exists():
        download(args.dataset, args.split, raw)
    else:
        print(f"using cached {raw}")

    target = args.output / args.dataset
    docs, questions, skipped = convert(raw, target)
    print(f"documents: {docs}, questions: {questions}, skipped: {skipped}")
    print(f"wrote {target / 'corpus.jsonl'} and {target / 'questions.jsonl'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
