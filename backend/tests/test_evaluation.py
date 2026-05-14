from pathlib import Path

from app.services.evaluation import (
    evaluate_answer,
    evaluate_dataset,
    keyword_recall,
    load_json,
    source_type_coverage,
)


def test_keyword_recall_matches_expected_terms_case_insensitively():
    answer = "RAG 使用外部知识来减少幻觉，并保留来源。"

    assert keyword_recall(answer, ["外部知识", "减少幻觉", "来源"]) == 1.0
    assert keyword_recall(answer, ["外部知识", "不存在"]) == 0.5


def test_source_type_coverage_scores_expected_types():
    sources = [{"source_type": "official"}, {"source_type": "academic"}]

    assert source_type_coverage(sources, ["official", "academic"]) == 1.0
    assert source_type_coverage(sources, ["official", "news"]) == 0.5


def test_evaluate_answer_combines_intent_keywords_sources_and_citations():
    case = {
        "id": "case-1",
        "question": "RAG 是什么？",
        "intent": "definition",
        "expected_keywords": ["检索增强生成", "外部知识"],
        "expected_source_types": ["official"],
        "min_sources": 1,
        "pass_score": 0.75,
    }
    prediction = {
        "id": "case-1",
        "answer": "RAG 是检索增强生成，会结合外部知识回答问题 [1]。",
        "sources": [{"source_type": "official"}],
    }

    result = evaluate_answer(case, prediction)

    assert result["passed"] is True
    assert result["keyword_recall"] == 1.0
    assert result["citation_valid"] is True
    assert result["intent_ok"] is True


def test_evaluate_dataset_marks_missing_predictions_as_failed():
    cases = [
        {
            "id": "missing",
            "question": "如何实现 RAG？",
            "intent": "howto",
            "expected_keywords": ["Embedding"],
            "expected_source_types": ["official"],
            "min_sources": 1,
            "pass_score": 0.75,
        }
    ]

    report = evaluate_dataset(cases, [])

    assert report["case_count"] == 1
    assert report["pass_count"] == 0
    assert report["results"][0]["passed"] is False


def test_demo_cases_and_sample_predictions_pass():
    backend_dir = Path(__file__).resolve().parents[1]
    cases = load_json(backend_dir / "evals" / "demo_cases.json")
    predictions = load_json(backend_dir / "evals" / "sample_predictions.json")

    report = evaluate_dataset(cases, predictions)

    assert report["case_count"] == 5
    assert report["pass_rate"] == 1.0
