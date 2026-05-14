import json
import re
import uuid
from collections.abc import Callable
from time import perf_counter
from typing import TYPE_CHECKING, Any

from app.models.db import AsyncSession, Conversation, Message
from app.services.deepseek_client import DeepseekService
from app.services.embeddings import EmbeddingService
from app.services.source_processing import process_sources
from app.services.tavily_client import TavilyService
from app.services.vector_store import VectorStore
from app.utils.prompts import audit_citations, build_citation_notice, build_no_sources_answer

if TYPE_CHECKING:
    from app.services.reranker import RerankerService
else:
    RerankerService = Any


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> list[str]:
    """将长文本按固定大小分块，支持重叠。

    面试话术：
    - 为什么需要分块：Embedding 模型对输入长度有限制（通常 512 token），
      长文本直接编码会丢失细节，分块后每个 chunk 独立编码，检索粒度更细。
    - overlap 的作用：避免在 chunk 边界处切断关键信息，
      比如一个句子被切成两半，overlap 能保证上下文完整性。
    """
    text = text.strip()
    if not text:
        return []
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    overlap = max(0, min(overlap, chunk_size - 1))

    if len(text) <= chunk_size:
        return [text]

    # 按句子边界切分（中文句号、英文句号、换行）
    sentences = re.split(r'(?<=[。！？\.\!\?])\s*', text)

    chunks = []
    current_chunk = ""

    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= chunk_size:
            current_chunk += sentence
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            # 如果单个句子超过 chunk_size，强制切分
            if len(sentence) > chunk_size:
                for i in range(0, len(sentence), chunk_size - overlap):
                    chunks.append(sentence[i : i + chunk_size].strip())
                current_chunk = ""
            else:
                current_chunk = sentence

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    # 添加 overlap：在相邻 chunk 之间保留部分重叠内容
    if overlap > 0 and len(chunks) > 1:
        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_tail = chunks[i - 1][-overlap:]
            overlapped.append(prev_tail + chunks[i])
        chunks = overlapped

    return [c for c in chunks if c]


def build_rag_context(reranked_docs: list[dict]) -> list[dict]:
    """将 rerank 后的文档转为 sources 格式（供 DeepSeek 使用）。

    去重来源 URL，保留最相关的片段。
    """
    source_by_url: dict[str, dict] = {}
    sources = []

    for doc in reranked_docs:
        meta = doc.get("metadata", {})
        url = meta.get("url", "")
        text = doc["text"].strip()
        if not text:
            continue

        if url and url in source_by_url:
            source = source_by_url[url]
            if text not in source["snippet"]:
                source["snippet"] = f"{source['snippet']} ... {text}"[:900]
            source["score"] = max(source.get("score", 0), doc.get("rerank_score", doc.get("score", 0)))
            continue

        source = {
            "citation_index": len(sources) + 1,
            "title": meta.get("title", ""),
            "url": url,
            "snippet": text,
            "score": doc.get("rerank_score", doc.get("score", 0)),
        }
        if "quality_score" in meta:
            source["quality_score"] = meta["quality_score"]
        if "quality_label" in meta:
            source["quality_label"] = meta["quality_label"]
        if "source_score" in meta:
            source["source_score"] = meta["source_score"]
        if "source_type" in meta:
            source["source_type"] = meta["source_type"]
        if "source_type_label" in meta:
            source["source_type_label"] = meta["source_type_label"]

        sources.append(source)
        if url:
            source_by_url[url] = source

    return sources


def resolve_service(service_or_factory):
    if callable(service_or_factory):
        return service_or_factory()
    return service_or_factory


def sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def save_turn(
    db_session: AsyncSession,
    conversation_id: str | None,
    query: str,
    answer: str,
    sources: list[dict],
) -> str:
    if not conversation_id:
        conversation_id = str(uuid.uuid4())
        conv = Conversation(id=conversation_id, title=query[:60])
        db_session.add(conv)

    user_msg = Message(
        conversation_id=conversation_id,
        role="user",
        content=query,
    )
    db_session.add(user_msg)

    assistant_msg = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=answer,
        sources=json.dumps(sources, ensure_ascii=False),
    )
    db_session.add(assistant_msg)
    await db_session.commit()
    return conversation_id


async def run_search_pipeline(
    query: str,
    conversation_id: str | None,
    tavily: TavilyService,
    deepseek: DeepseekService,
    db_session: AsyncSession,
    embedding: EmbeddingService | Callable[[], EmbeddingService | None] | None = None,
    reranker: RerankerService | Callable[[], RerankerService | None] | None = None,
):
    """Orchestrate: search -> chunk -> embed -> rerank -> synthesize -> followup -> save.

    RAG 流程（面试话术）：
    1. Tavily 粗召回：从全网获取 Top-N 搜索结果
    2. 分块：将长文本按语义切分为小 chunk（chunk_size=512, overlap=50）
    3. Embedding 粗排：用 BGE 模型将 chunk 编码为向量，存入 FAISS
    4. 向量检索：用户 query 做 Embedding，余弦相似度找 Top-N 候选
    5. Cross-Encoder 精排：对 Top-N 做精细打分，取 Top-K
    6. 生成：将 Top-K 作为上下文送入 DeepSeek 生成回答
    """
    stage_started: dict[str, float] = {}

    def stage_payload(stage: str, status: str, label: str) -> dict:
        payload: dict[str, Any] = {"stage": stage, "status": status, "label": label}
        if status == "running":
            stage_started[stage] = perf_counter()
        elif status == "done" and stage in stage_started:
            payload["duration_ms"] = round((perf_counter() - stage_started[stage]) * 1000, 1)
        return payload

    # 1. Search via Tavily
    yield sse_event("stage", stage_payload("search", "running", "Tavily 搜索召回"))
    sources = process_sources(query, await tavily.search(query))
    yield sse_event("stage", stage_payload("search", "done", "Tavily 搜索召回"))
    yield sse_event("stage", stage_payload("process", "done", "结果清洗与质量评分"))
    yield sse_event("sources", {"sources": sources})

    if not sources:
        yield sse_event("stage", stage_payload("answer", "done", "无可靠来源兜底"))
        full_answer = build_no_sources_answer(query)
        yield sse_event("token", {"text": full_answer})
        conversation_id = await save_turn(db_session, conversation_id, query, full_answer, sources)
        yield sse_event("done", {"conversation_id": conversation_id})
        return

    # 2-5. RAG pipeline: chunk -> embed -> retrieve -> rerank
    if embedding:
        yield sse_event("stage", stage_payload("rag", "running", "向量检索与重排序"))

        # 2. 分块
        all_chunks: list[str] = []
        all_metadata: list[dict] = []
        for src in sources:
            text = src.get("content") or src.get("snippet", "")
            if not text:
                continue
            chunks = chunk_text(text)
            for chunk in chunks:
                all_chunks.append(chunk)
                all_metadata.append({
                    "title": src.get("title", ""),
                    "url": src.get("url", ""),
                    "source_score": src.get("score", 0),
                    "quality_score": src.get("quality_score", 0),
                    "quality_label": src.get("quality_label", "medium"),
                    "source_type": src.get("source_type", "general"),
                    "source_type_label": src.get("source_type_label", "普通网页"),
                })

        if all_chunks:
            # 3. 构建向量库
            yield sse_event("stage", stage_payload("rag", "running", "加载本地向量模型"))
            embedding_service = resolve_service(embedding)
            reranker_service = None
            store = VectorStore(embedding_service)
            store.add(all_chunks, all_metadata)

            # 4. 向量检索 Top-10 候选
            candidates = store.search(query, top_k=10)

            # 5. Reranker 精排取 Top-5；如果精排模型不可用，保留向量召回结果
            if reranker:
                yield sse_event("stage", stage_payload("rag", "running", "加载精排模型"))
                reranker_service = resolve_service(reranker)
            ranked_docs = (
                reranker_service.rerank(query, candidates, top_k=5)
                if reranker_service
                else candidates[:5]
            )
            sources = build_rag_context(ranked_docs)
            yield sse_event("sources", {"sources": sources})

            # 释放向量库内存
            store.clear()
        yield sse_event("stage", stage_payload("rag", "done", "向量检索与重排序"))

    # 6. Load conversation history if continuing
    conversation_history: list[dict] = []
    if conversation_id:
        from sqlalchemy import select

        result = await db_session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        for msg in result.scalars():
            conversation_history.append({"role": msg.role, "content": msg.content})

    # 7. Stream Deepseek answer via LangChain
    yield sse_event("stage", stage_payload("answer", "running", "DeepSeek 综合生成"))
    full_answer = ""
    async for token in deepseek.stream_answer(query, sources, conversation_history):
        full_answer += token
        yield sse_event("token", {"text": token})
    yield sse_event("stage", stage_payload("answer", "done", "DeepSeek 综合生成"))

    yield sse_event("stage", stage_payload("audit", "running", "引用审计"))
    citation_audit = audit_citations(full_answer, sources)
    citation_notice = build_citation_notice(citation_audit)
    if citation_notice:
        full_answer += citation_notice
        yield sse_event("token", {"text": citation_notice})
    yield sse_event("citation_audit", citation_audit)
    yield sse_event("stage", stage_payload("audit", "done", "引用审计"))

    # 8. Generate follow-ups
    followups = await deepseek.suggest_followups(query, full_answer)
    yield sse_event("followup", {"questions": followups})

    # 9. Save to database
    conversation_id = await save_turn(db_session, conversation_id, query, full_answer, sources)

    yield sse_event("done", {"conversation_id": conversation_id})
