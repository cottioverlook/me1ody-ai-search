from app.services.source_processing import (
    canonicalize_url,
    classify_source,
    clean_text,
    process_sources,
    score_source,
)


def test_clean_text_normalizes_whitespace_and_removes_markdown_images():
    text = "第一段\n\n![alt](https://img.example/a.png)   第二段"

    assert clean_text(text) == "第一段 第二段"


def test_canonicalize_url_removes_tracking_params_and_fragment():
    url = "HTTPS://www.Example.com/path/?utm_source=x&a=1&fbclid=abc#section"

    assert canonicalize_url(url) == "https://example.com/path?a=1"


def test_score_source_rewards_relevance_and_rich_content():
    relevant = {
        "title": "Python AI 检索系统",
        "url": "https://docs.example.org/python",
        "content": "Python AI 检索系统 " * 80,
        "score": 0.8,
    }
    weak = {
        "title": "Unrelated",
        "url": "https://example.com",
        "content": "short unrelated text",
        "score": 0.2,
    }

    assert score_source("Python AI 检索", relevant) > score_source("Python AI 检索", weak)


def test_classify_source_identifies_explainable_source_types():
    assert classify_source("https://docs.python.org/3/tutorial/") == "official"
    assert classify_source("https://arxiv.org/abs/2401.00001") == "academic"
    assert classify_source("https://github.com/langchain-ai/langchain") == "code"
    assert classify_source("https://stackoverflow.com/questions/1") == "community"


def test_process_sources_deduplicates_and_sorts_by_quality():
    sources = [
        {
            "title": "Weak",
            "url": "https://example.com/weak?utm_source=x",
            "snippet": "短内容",
            "content": "短内容",
            "score": 0.1,
        },
        {
            "title": "Python AI 检索系统",
            "url": "https://docs.example.org/python#intro",
            "snippet": "Python AI 检索系统很适合复试项目。",
            "content": "Python AI 检索系统很适合复试项目。" * 40,
            "score": 0.9,
        },
        {
            "title": "Duplicate",
            "url": "https://docs.example.org/python?utm_campaign=copy",
            "snippet": "Python AI 检索系统很适合复试项目。",
            "content": "Python AI 检索系统很适合复试项目。" * 40,
            "score": 0.8,
        },
    ]

    processed = process_sources("Python AI 检索", sources)

    assert len(processed) == 1
    assert processed[0]["title"] == "Python AI 检索系统"
    assert processed[0]["url"] == "https://docs.example.org/python"
    assert processed[0]["quality_label"] == "high"
    assert processed[0]["source_type"] == "official"
    assert processed[0]["source_type_label"] == "官方/文档"


def test_process_sources_limits_single_domain_dominance():
    sources = [
        {
            "title": f"Python AI 检索 {i}",
            "url": f"https://docs.example.org/page-{i}",
            "snippet": f"Python AI 检索系统很适合复试项目，第 {i} 个角度。",
            "content": (f"Python AI 检索系统很适合复试项目，第 {i} 个角度。" * 40),
            "score": 0.9 - i * 0.01,
        }
        for i in range(4)
    ]
    sources.append({
        "title": "Python AI official",
        "url": "https://python.org/about",
        "snippet": "Python AI 检索系统资料。",
        "content": "Python AI 检索系统资料。" * 40,
        "score": 0.7,
    })

    processed = process_sources("Python AI 检索", sources, limit=5)

    assert sum(1 for source in processed if "docs.example.org" in source["url"]) == 2
    assert any("python.org" in source["url"] for source in processed)
