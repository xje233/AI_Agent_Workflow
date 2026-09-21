from pathlib import Path

import pytest

from app.evaluation.rag import EvalCase, load_cases, load_jsonl, score_answers, score_retrieval, validate_dataset


DATA_DIR = Path(__file__).resolve().parents[1] / "evaluation" / "rag"


def test_checked_in_dataset_meets_minimum_contract():
    documents = load_jsonl(DATA_DIR / "corpus.jsonl")
    cases = load_cases(DATA_DIR / "questions.jsonl")

    validate_dataset(cases, {row["id"] for row in documents})

    assert len(cases) == 50
    assert {case.category for case in cases} == {"fact", "cross_chunk", "unanswerable", "ocr"}


def test_retrieval_metrics_include_rank_categories_and_failures():
    cases = [
        EvalCase("q1", "fact", "q", ("d1",), ("answer",)),
        EvalCase("q2", "fact", "q", ("d2",), ("answer",)),
        EvalCase("q3", "unanswerable", "q", (), (), True),
    ]

    report = score_retrieval(cases, {"q1": ["x", "d1"], "q2": ["x"], "q3": []}, k=3)

    assert report["overall"] == {"samples": 2, "recall@3": 0.5, "mrr": 0.25}
    assert report["by_category"]["unanswerable"]["recall@3"] == 1.0
    assert report["failures"][0]["id"] == "q2"


def test_answer_accuracy_uses_answerable_and_refusal_rubrics():
    cases = [
        EvalCase("q1", "fact", "q", ("d1",), ("200元", "不需要")),
        EvalCase("q2", "unanswerable", "q", (), (), True),
    ]

    result = score_answers(cases, {"q1": "补贴为200元，不需要发票", "q2": "根据资料无法确认"})

    assert result["judged_samples"] == 2
    assert result["accuracy"] == 1.0


def test_dataset_validation_rejects_unknown_relevant_document():
    case = EvalCase("q1", "fact", "q", ("missing",), ("answer",))

    with pytest.raises(ValueError, match="unknown relevant documents"):
        validate_dataset([case] * 50, {"known"})
