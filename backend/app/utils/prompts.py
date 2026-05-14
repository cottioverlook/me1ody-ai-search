import re
from typing import Literal


QueryIntent = Literal["factual", "comparison", "howto", "definition", "news", "open_ended"]

INTENT_INSTRUCTIONS: dict[QueryIntent, str] = {
    "factual": "回答结构：先给直接结论，再列关键依据。每个事实性判断必须尽量附来源编号。",
    "comparison": "回答结构：先给对比结论，再用表格或分点比较差异、适用场景和取舍。",
    "howto": "回答结构：给出可执行步骤、注意事项和必要前提，避免编造搜索结果中没有的步骤。",
    "definition": "回答结构：先给定义，再解释核心特征、例子和容易混淆的概念。",
    "news": "回答结构：优先说明时间、主体、事件和影响；如果来源时间不足，要明确提示时效性限制。",
    "open_ended": "回答结构：先概括，再按主题组织；明确区分来源支持的信息和合理推断。",
}


def detect_query_intent(query: str) -> QueryIntent:
    normalized = query.lower().strip()
    if any(word in normalized for word in ("对比", "比较", "区别", "差异", "vs", "versus")):
        return "comparison"
    if any(word in normalized for word in ("怎么", "如何", "步骤", "教程", "配置", "实现", "部署")):
        return "howto"
    if any(word in normalized for word in ("是什么", "定义", "概念", "什么意思", "what is")):
        return "definition"
    if any(word in normalized for word in ("最新", "今天", "新闻", "进展", "发布", "recent", "latest")):
        return "news"
    if normalized.endswith("?") or normalized.endswith("？") or any(word in normalized for word in ("谁", "哪里", "多少", "何时", "什么时候")):
        return "factual"
    return "open_ended"


def build_system_prompt(intent: QueryIntent | None = None) -> str:
    intent = intent or "open_ended"
    return (
        "你是一个专业的 AI 搜索助手，类似 Perplexity。根据提供的搜索结果为用户生成高质量的回答。\n\n"
        "通用规则：\n"
        "1. 严格基于提供的搜索结果回答，不要编造信息。\n"
        "2. 在引用信息后使用 [编号] 标注来源，例如：量子计算是一种新型计算方式 [1][3]。\n"
        "3. 如果搜索结果信息不足，诚实说明哪些方面信息不够。\n"
        "4. 使用 Markdown 格式组织回答，适当使用标题、列表、加粗。\n"
        "5. 回答要全面但简洁，先给核心结论，再展开细节。\n"
        "6. 如果搜索结果之间有不同观点，请客观呈现各方观点。\n"
        "7. 不要引用不存在的来源编号，只能使用搜索结果中列出的 [1]、[2] 等编号。\n\n"
        f"当前问题类型：{intent}\n"
        f"{INTENT_INSTRUCTIONS[intent]}"
    )


def _format_source(index: int, source: dict) -> str:
    quality = source.get("quality_label") or "unknown"
    quality_score = source.get("quality_score")
    source_type = source.get("source_type_label") or source.get("source_type") or "未知来源"
    score_text = f"{quality_score:.2f}" if isinstance(quality_score, (int, float)) else "unknown"
    return (
        f"[{index}] {source.get('title', '')}\n"
        f"来源: {source.get('url', '')}\n"
        f"来源类型: {source_type}\n"
        f"质量评级: {quality} ({score_text})\n"
        f"内容片段: {source.get('snippet', '')}"
    )


def build_user_prompt(query: str, sources: list[dict], intent: QueryIntent | None = None) -> str:
    intent = intent or detect_query_intent(query)
    sources_text = "\n\n".join(
        _format_source(i + 1, source)
        for i, source in enumerate(sources)
    )
    return (
        f"搜索结果：\n{sources_text}\n\n"
        f"用户问题：{query}\n\n"
        f"请按“{INTENT_INSTRUCTIONS[intent]}”回答。"
        "在引用具体信息时务必标注 [编号] 来源；如果无法从来源中确认，请明确说明无法确认。"
    )


def build_no_sources_answer(query: str) -> str:
    return (
        f"暂时没有检索到足够可靠的来源来回答“{query}”。\n\n"
        "为了避免编造信息，我不会在缺少来源的情况下给出确定结论。"
        "你可以换一种问法，或补充更具体的关键词后再试。"
    )


def extract_citation_numbers(answer: str) -> list[int]:
    return [int(match) for match in re.findall(r"\[(\d+)]", answer)]


def audit_citations(answer: str, sources: list[dict]) -> dict:
    citations = extract_citation_numbers(answer)
    max_source = len(sources)
    invalid = sorted({citation for citation in citations if citation < 1 or citation > max_source})
    return {
        "has_citations": bool(citations),
        "invalid_citations": invalid,
        "valid": bool(citations) and not invalid,
        "source_count": max_source,
    }


def build_citation_notice(audit: dict) -> str:
    if audit["valid"]:
        return ""
    if audit["invalid_citations"]:
        invalid = ", ".join(f"[{num}]" for num in audit["invalid_citations"])
        return f"\n\n> 引用检查：回答中出现了超出来源范围的引用 {invalid}，请优先核对来源列表。"
    return "\n\n> 引用检查：当前回答缺少明确来源编号，建议结合下方来源列表核对关键信息。"


def build_followup_prompt(query: str, answer: str) -> str:
    return (
        "基于以下问答内容，生成 3-5 个用户可能感兴趣的相关问题。\n"
        "要求：\n"
        "- 每行一个问题，不要加编号或符号\n"
        "- 问题应该能帮助用户更深入地了解主题\n"
        "- 问题要具体且有价值\n\n"
        f"原问题：{query}\n"
        f"回答摘要：{answer[:500]}"
    )
