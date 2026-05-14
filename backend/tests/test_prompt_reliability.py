from app.utils.prompts import (
    audit_citations,
    build_citation_notice,
    build_no_sources_answer,
    build_system_prompt,
    build_user_prompt,
    detect_query_intent,
    extract_citation_numbers,
)


def test_detect_query_intent_routes_common_question_types():
    assert detect_query_intent("React 和 Vue 的区别是什么") == "comparison"
    assert detect_query_intent("如何实现 RAG 检索") == "howto"
    assert detect_query_intent("向量数据库是什么") == "definition"
    assert detect_query_intent("DeepSeek 最新进展") == "news"
    assert detect_query_intent("谁提出了 Transformer？") == "factual"


def test_system_prompt_changes_by_intent():
    prompt = build_system_prompt("comparison")

    assert "当前问题类型：comparison" in prompt
    assert "比较差异" in prompt
    assert "不要引用不存在的来源编号" in prompt


def test_user_prompt_includes_source_quality_and_type():
    sources = [
        {
            "title": "Python Docs",
            "url": "https://docs.python.org/3/",
            "snippet": "Python tutorial",
            "quality_label": "high",
            "quality_score": 0.91,
            "source_type_label": "官方/文档",
        }
    ]

    prompt = build_user_prompt("Python 是什么", sources)

    assert "来源类型: 官方/文档" in prompt
    assert "质量评级: high (0.91)" in prompt
    assert "无法从来源中确认" in prompt


def test_citation_audit_detects_missing_and_invalid_citations():
    sources = [{"title": "A"}, {"title": "B"}]

    assert extract_citation_numbers("结论来自 [1][2]") == [1, 2]
    assert audit_citations("没有引用", sources) == {
        "has_citations": False,
        "invalid_citations": [],
        "valid": False,
        "source_count": 2,
    }
    assert audit_citations("错误引用 [3]", sources)["invalid_citations"] == [3]


def test_citation_notice_is_empty_only_when_audit_is_valid():
    assert build_citation_notice({
        "has_citations": True,
        "invalid_citations": [],
        "valid": True,
        "source_count": 1,
    }) == ""
    assert "缺少明确来源编号" in build_citation_notice({
        "has_citations": False,
        "invalid_citations": [],
        "valid": False,
        "source_count": 1,
    })
    assert "[3]" in build_citation_notice({
        "has_citations": True,
        "invalid_citations": [3],
        "valid": False,
        "source_count": 2,
    })


def test_no_sources_answer_refuses_to_guess():
    answer = build_no_sources_answer("某个冷门问题")

    assert "没有检索到足够可靠的来源" in answer
    assert "不会在缺少来源的情况下给出确定结论" in answer
