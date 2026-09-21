"""Deterministic RAG evaluation metrics and dataset validation."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


SUPPORTED_CATEGORIES = {"fact", "cross_chunk", "unanswerable", "ocr"}


@dataclass(frozen=True)
class EvalCase:
    id: str
    category: str
    question: str
    relevant_doc_ids: tuple[str, ...]
    answer_keywords: tuple[str, ...]
    unanswerable: bool = False


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc.msg}") from exc
    return rows


def load_cases(path: Path) -> list[EvalCase]:
    return [
        EvalCase(
            id=row["id"],
            category=row["category"],
            question=row["question"],
            relevant_doc_ids=tuple(row.get("relevant_doc_ids", [])),
            answer_keywords=tuple(row.get("answer_keywords", [])),
            unanswerable=bool(row.get("unanswerable", False)),
        )
        for row in load_jsonl(path)
    ]


def validate_dataset(
    cases: list[EvalCase], document_ids: set[str], require_all_categories: bool = True
) -> None:
    errors = []
    counts = Counter(case.category for case in cases)
    duplicate_ids = [case_id for case_id, count in Counter(c.id for c in cases).items() if count > 1]
    if len(cases) < 50:
        errors.append(f"expected at least 50 cases, got {len(cases)}")
    if duplicate_ids:
        errors.append(f"duplicate case ids: {', '.join(duplicate_ids)}")
    unsupported = counts.keys() - SUPPORTED_CATEGORIES
    if unsupported:
        errors.append(f"unsupported categories: {', '.join(sorted(unsupported))}")
    if require_all_categories:
        missing_categories = SUPPORTED_CATEGORIES - counts.keys()
        if missing_categories:
            errors.append(f"missing categories: {', '.join(sorted(missing_categories))}")

    for case in cases:
        if case.category not in SUPPORTED_CATEGORIES:
            errors.append(f"{case.id}: unsupported category {case.category}")
        if case.unanswerable:
            if case.relevant_doc_ids or case.answer_keywords:
                errors.append(f"{case.id}: unanswerable cases cannot define evidence or answer keywords")
        else:
            unknown = set(case.relevant_doc_ids) - document_ids
            if not case.relevant_doc_ids:
                errors.append(f"{case.id}: answerable case has no relevant documents")
            if not case.answer_keywords:
                errors.append(f"{case.id}: answerable case has no answer keywords")
            if unknown:
                errors.append(f"{case.id}: unknown relevant documents: {', '.join(sorted(unknown))}")
    if errors:
        raise ValueError("dataset validation failed:\n- " + "\n- ".join(errors))


def _rank(retrieved_doc_ids: Iterable[str], relevant_doc_ids: tuple[str, ...], k: int) -> int | None:
    relevant = set(relevant_doc_ids)
    return next((rank for rank, doc_id in enumerate(retrieved_doc_ids, 1) if rank <= k and doc_id in relevant), None)


def score_retrieval(cases: list[EvalCase], results: dict[str, list[str]], k: int = 3) -> dict:
    """Score answerable cases; unanswerable questions are measured as rejection precision."""
    groups: dict[str, list[dict]] = defaultdict(list)
    failures = []
    for case in cases:
        retrieved = results.get(case.id, [])[:k]
        if case.unanswerable:
            sample = {"hit": not retrieved, "reciprocal_rank": 0.0}
            if retrieved:
                failures.append({"id": case.id, "category": case.category, "reason": "unexpected_retrieval", "retrieved": retrieved})
        else:
            rank = _rank(retrieved, case.relevant_doc_ids, k)
            sample = {"hit": rank is not None, "reciprocal_rank": 1.0 / rank if rank else 0.0}
            if rank is None:
                failures.append({"id": case.id, "category": case.category, "reason": "relevant_document_not_retrieved", "retrieved": retrieved, "expected": list(case.relevant_doc_ids)})
        groups[case.category].append(sample)

    def summarize(samples: list[dict]) -> dict:
        return {
            "samples": len(samples),
            f"recall@{k}": round(sum(s["hit"] for s in samples) / len(samples), 4),
            "mrr": round(sum(s["reciprocal_rank"] for s in samples) / len(samples), 4),
        }

    answerable = [s for category, samples in groups.items() if category != "unanswerable" for s in samples]
    return {
        "overall": summarize(answerable),
        "by_category": {category: summarize(samples) for category, samples in sorted(groups.items())},
        "failures": failures,
    }


def score_answers(cases: list[EvalCase], answers: dict[str, str]) -> dict:
    """Apply the checked-in human rubric to generated answers using required phrases."""
    refusal_markers = ("无法回答", "无法确认", "未找到", "没有相关", "无相关")
    judged = []
    failures = []
    for case in cases:
        if case.id not in answers:
            continue
        answer = answers[case.id].lower()
        correct = (
            any(marker in answer for marker in refusal_markers)
            if case.unanswerable
            else all(keyword.lower() in answer for keyword in case.answer_keywords)
        )
        judged.append(correct)
        if not correct:
            failures.append({"id": case.id, "category": case.category, "reason": "answer_rubric_failed"})
    return {
        "judged_samples": len(judged),
        "accuracy": round(sum(judged) / len(judged), 4) if judged else None,
        "failures": failures,
    }
