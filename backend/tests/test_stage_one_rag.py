import asyncio
import json

import numpy as np
import pytest

from app.services.embeddings import EmbeddingService
from app.services.demo import DemoDeepseekService, DemoTavilyService
from app.services.synthesis import build_rag_context, chunk_text, run_search_pipeline
from app.services.tavily_client import TavilyService
from app.services.vector_store import VectorStore


class FakeEmbeddingModel:
    def __init__(self):
        self.calls: list[list[str]] = []

    def encode(self, texts, normalize_embeddings=True, show_progress_bar=False, batch_size=32):
        self.calls.append(list(texts))
        return np.array(
            [[len(text), sum(ord(char) for char in text) % 997] for text in texts],
            dtype=np.float32,
        )


def test_embedding_cache_handles_mixed_hits(monkeypatch):
    model = FakeEmbeddingModel()
    monkeypatch.setattr("app.services.embeddings.SentenceTransformer", lambda _: model)

    service = EmbeddingService("fake-model")
    first = service.encode(["alpha", "beta"])
    second = service.encode(["alpha", "gamma"])

    assert model.calls == [["alpha", "beta"], ["gamma"]]
    assert np.array_equal(second[0], first[0])
    assert np.array_equal(second[1], np.array([5, sum(ord(char) for char in "gamma") % 997]))


def test_chunk_text_handles_empty_and_overlap_safely():
    assert chunk_text("   ") == []

    chunks = chunk_text("第一句。第二句。第三句。", chunk_size=6, overlap=2)

    assert len(chunks) > 1
    assert all(len(chunk) <= 8 for chunk in chunks)


class FakeEmbeddingService:
    vectors = {
        "python language": np.array([1.0, 0.0], dtype=np.float32),
        "cooking recipe": np.array([0.0, 1.0], dtype=np.float32),
        "python": np.array([1.0, 0.0], dtype=np.float32),
    }

    def encode(self, texts):
        return np.array([self.vectors[text] for text in texts], dtype=np.float32)

    def encode_single(self, text):
        return self.vectors[text]


def test_vector_store_retrieves_most_relevant_text():
    store = VectorStore(FakeEmbeddingService())
    store.add(
        ["python language", "cooking recipe"],
        [{"url": "https://python.example"}, {"url": "https://cook.example"}],
    )

    results = store.search("python", top_k=1)

    assert results[0]["text"] == "python language"
    assert results[0]["metadata"]["url"] == "https://python.example"


def test_vector_store_rejects_metadata_length_mismatch():
    store = VectorStore(FakeEmbeddingService())

    with pytest.raises(ValueError):
        store.add(["python language", "cooking recipe"], [{"url": "https://python.example"}])


class FakeTavilyTool:
    def __init__(self):
        self.payload = None

    def invoke(self, payload):
        self.payload = payload
        return {
            "results": [
                {
                    "title": "Raw source",
                    "url": "https://example.com/raw",
                    "content": "short",
                    "raw_content": "long raw content for rag",
                    "score": 0.9,
                },
                {
                    "title": "Duplicate source",
                    "url": "https://example.com/raw",
                    "content": "duplicate",
                    "score": 0.1,
                },
            ]
        }


def test_tavily_search_requests_raw_content_and_deduplicates():
    service = TavilyService.__new__(TavilyService)
    service.api_key = "test-key"
    service.tool = FakeTavilyTool()

    sources = asyncio.run(service.search("test query"))

    assert service.tool.payload == {"query": "test query"}
    assert sources == [
        {
            "title": "Raw source",
            "url": "https://example.com/raw",
            "snippet": "long raw content for rag",
            "content": "long raw content for rag",
            "score": 0.9,
        }
    ]


class FakeTavilyErrorTool:
    def invoke(self, payload):
        return {"error": ValueError("bad tavily parameters")}


def test_tavily_search_raises_on_tool_error():
    service = TavilyService.__new__(TavilyService)
    service.api_key = "test-key"
    service.tool = FakeTavilyErrorTool()

    with pytest.raises(RuntimeError, match="Tavily search failed"):
        asyncio.run(service.search("test query"))


def test_build_rag_context_merges_same_url_chunks_and_keeps_citation_stable():
    docs = [
        {
            "text": "best chunk",
            "rerank_score": 0.9,
            "metadata": {
                "title": "A",
                "url": "u",
                "source_type": "official",
                "source_type_label": "官方/文档",
            },
        },
        {"text": "second chunk", "rerank_score": 0.8, "metadata": {"title": "A2", "url": "u"}},
    ]

    sources = build_rag_context(docs)

    assert sources == [
        {
            "citation_index": 1,
            "title": "A",
            "url": "u",
            "snippet": "best chunk ... second chunk",
            "score": 0.9,
            "source_type": "official",
            "source_type_label": "官方/文档",
        }
    ]


class FakeTavilyService:
    async def search(self, query):
        return [
            {
                "title": "Python",
                "url": "https://example.com/python",
                "snippet": "Python snippet",
                "content": "Python is a programming language. It is used for AI.",
                "score": 0.8,
                "source_type": "official",
                "source_type_label": "官方/文档",
            }
        ]


class PipelineEmbedding:
    def encode(self, texts):
        return np.array([[1.0, 0.0] for _ in texts], dtype=np.float32)

    def encode_single(self, text):
        return np.array([1.0, 0.0], dtype=np.float32)


class FakeReranker:
    def rerank(self, query, documents, top_k=5):
        return [{**doc, "rerank_score": 0.99} for doc in documents[:top_k]]


class FakeDeepseek:
    async def stream_answer(self, query, sources, conversation_history=None):
        assert sources[0]["snippet"].startswith("Python is a programming language")
        yield "answer [1]"

    async def suggest_followups(self, query, answer):
        return ["follow up"]


class FakeDbSession:
    def __init__(self):
        self.items = []
        self.committed = False

    def add(self, item):
        self.items.append(item)

    async def commit(self):
        self.committed = True


def parse_sse(event: str):
    lines = event.strip().splitlines()
    event_name = lines[0].replace("event: ", "")
    data = json.loads(lines[1].replace("data: ", ""))
    return event_name, data


def test_search_pipeline_emits_reranked_sources_before_answer():
    async def collect():
        return [
            parse_sse(event)
            async for event in run_search_pipeline(
                query="python",
                conversation_id=None,
                tavily=FakeTavilyService(),
                deepseek=FakeDeepseek(),
                db_session=FakeDbSession(),
                embedding=PipelineEmbedding(),
                reranker=FakeReranker(),
            )
        ]

    events = asyncio.run(collect())
    source_events = [data for name, data in events if name == "sources"]
    done_stages = [
        data["stage"]
        for name, data in events
        if name == "stage" and data["status"] == "done"
    ]

    assert len(source_events) == 2
    assert done_stages == ["search", "process", "rag", "answer", "audit"]
    assert all(
        "duration_ms" in data and data["duration_ms"] >= 0
        for name, data in events
        if name == "stage" and data["stage"] in {"search", "rag", "answer", "audit"} and data["status"] == "done"
    )
    assert source_events[-1]["sources"][0]["score"] == 0.99
    assert ("token", {"text": "answer [1]"}) in events
    assert ("citation_audit", {
        "has_citations": True,
        "invalid_citations": [],
        "valid": True,
        "source_count": 1,
    }) in events


class FakeNoCitationDeepseek:
    async def stream_answer(self, query, sources, conversation_history=None):
        yield "answer without citation"

    async def suggest_followups(self, query, answer):
        return []


def test_search_pipeline_appends_notice_when_answer_lacks_citations():
    async def collect():
        return [
            parse_sse(event)
            async for event in run_search_pipeline(
                query="python",
                conversation_id=None,
                tavily=FakeTavilyService(),
                deepseek=FakeNoCitationDeepseek(),
                db_session=FakeDbSession(),
                embedding=PipelineEmbedding(),
                reranker=FakeReranker(),
            )
        ]

    events = asyncio.run(collect())

    assert any(
        name == "token" and "缺少明确来源编号" in data["text"]
        for name, data in events
    )
    assert ("citation_audit", {
        "has_citations": False,
        "invalid_citations": [],
        "valid": False,
        "source_count": 1,
    }) in events


class EmptyTavilyService:
    async def search(self, query):
        return []


def test_search_pipeline_refuses_to_guess_when_no_sources():
    db = FakeDbSession()

    async def collect():
        return [
            parse_sse(event)
            async for event in run_search_pipeline(
                query="unknown topic",
                conversation_id=None,
                tavily=EmptyTavilyService(),
                deepseek=FakeNoCitationDeepseek(),
                db_session=db,
                embedding=PipelineEmbedding(),
                reranker=FakeReranker(),
            )
        ]

    events = asyncio.run(collect())

    assert any(
        name == "token" and "不会在缺少来源的情况下给出确定结论" in data["text"]
        for name, data in events
    )
    assert db.committed is True
    assert events[-1][0] == "done"


def test_demo_mode_pipeline_runs_without_external_api_clients():
    async def collect():
        return [
            parse_sse(event)
            async for event in run_search_pipeline(
                query="RAG 是什么",
                conversation_id=None,
                tavily=DemoTavilyService(),
                deepseek=DemoDeepseekService(),
                db_session=FakeDbSession(),
                embedding=EmbeddingService(backend="hash"),
                reranker=None,
            )
        ]

    events = asyncio.run(collect())
    answer = "".join(data["text"] for name, data in events if name == "token")

    assert any(name == "sources" and data["sources"] for name, data in events)
    assert "Demo 模式" in answer
    assert any(name == "citation_audit" and data["valid"] is True for name, data in events)
    assert events[-1][0] == "done"
