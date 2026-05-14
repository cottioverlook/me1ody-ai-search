import json
import re
from pathlib import Path
from statistics import mean
from typing import Any

from app.utils.prompts import audit_citations, detect_query_intent


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as file:
        return json.load(file)


def keyword_recall(answer: str, expected_keywords: list[str]) -> float:
    if not expected_keywords:
        return 1.0

    normalized_answer = normalize_text(answer)
    matched = [
        keyword for keyword in expected_keywords
        if normalize_text(keyword) in normalized_answer
    ]
    return round(len(matched) / len(expected_keywords), 4)


def source_type_coverage(sources: list[dict], expected_types: list[str]) -> float:
    if not expected_types:
        return 1.0

    available_types = {
        source.get("source_type")
        for source in sources
        if source.get("source_type")
    }
    matched = [source_type for source_type in expected_types if source_type in available_types]
    return round(len(matched) / len(expected_types), 4)


def evaluate_answer(case: dict, prediction: dict) -> dict:
    answer = prediction.get("answer", "")
    sources = prediction.get("sources", [])
    expected_keywords = case.get("expected_keywords", [])
    expected_source_types = case.get("expected_source_types", [])
    min_sources = case.get("min_sources", 1)
    expected_intent = case.get("intent")

    citation_audit = audit_citations(answer, sources)
    keyword_score = keyword_recall(answer, expected_keywords)
    source_type_score = source_type_coverage(sources, expected_source_types)
    source_count = len(sources)
    source_count_ok = source_count >= min_sources
    detected_intent = detect_query_intent(case.get("question", ""))
    intent_ok = detected_intent == expected_intent if expected_intent else True

    scores = [
        keyword_score,
        source_type_score,
        1.0 if citation_audit["valid"] else 0.0,
        1.0 if source_count_ok else 0.0,
        1.0 if intent_ok else 0.0,
    ]
    overall_score = round(mean(scores), 4)

    return {
        "id": case["id"],
        "question": case["question"],
        "intent_ok": intent_ok,
        "detected_intent": detected_intent,
        "expected_intent": expected_intent,
        "keyword_recall": keyword_score,
        "source_type_coverage": source_type_score,
        "source_count": source_count,
        "source_count_ok": source_count_ok,
        "citation_valid": citation_audit["valid"],
        "invalid_citations": citation_audit["invalid_citations"],
        "overall_score": overall_score,
        "passed": overall_score >= case.get("pass_score", 0.75),
    }


def evaluate_dataset(cases: list[dict], predictions: list[dict]) -> dict:
    prediction_by_id = {prediction["id"]: prediction for prediction in predictions}
    results = []

    for case in cases:
        prediction = prediction_by_id.get(case["id"], {
            "id": case["id"],
            "answer": "",
            "sources": [],
        })
        results.append(evaluate_answer(case, prediction))

    aggregate_score = round(mean(result["overall_score"] for result in results), 4) if results else 0.0
    pass_count = sum(1 for result in results if result["passed"])

    return {
        "case_count": len(results),
        "pass_count": pass_count,
        "pass_rate": round(pass_count / len(results), 4) if results else 0.0,
        "aggregate_score": aggregate_score,
        "results": results,
    }
