import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.db import create_engine, create_sessionmaker
from app.models.schemas import SearchRequest
from app.services.deepseek_client import DeepseekService
from app.services.demo import DemoDeepseekService, DemoTavilyService
from app.services.embeddings import EmbeddingService
from app.services.synthesis import run_search_pipeline
from app.services.tavily_client import TavilyService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["search"])

tavily = DemoTavilyService() if settings.demo_mode else None
deepseek = DemoDeepseekService() if settings.demo_mode else None

# RAG 服务：首次请求时延迟加载（模型下载需要时间）
_embedding: EmbeddingService | None = None
_reranker = None  # RerankerService 或 None（加载失败时降级）


def _get_embedding() -> EmbeddingService:
    global _embedding
    if _embedding is None:
        _embedding = EmbeddingService(backend="hash") if settings.demo_mode else EmbeddingService()
    return _embedding


def _get_reranker():
    global _reranker
    if _reranker is None:
        try:
            from app.services.reranker import RerankerService
            _reranker = RerankerService()
            logger.info("RerankerService loaded successfully")
        except Exception as e:
            logger.warning(f"RerankerService failed to load, skipping rerank: {e}")
            _reranker = False  # 标记为已尝试加载
    return _reranker if _reranker is not False else None


def _get_tavily():
    global tavily
    if tavily is None:
        tavily = TavilyService(api_key=settings.tavily_api_key)
    return tavily


def _get_deepseek():
    global deepseek
    if deepseek is None:
        deepseek = DeepseekService(api_key=settings.deepseek_api_key)
    return deepseek

engine = create_engine(settings.database_url)
session_factory = create_sessionmaker(engine)


async def get_db():
    async with session_factory() as session:
        yield session


@router.post("/search")
async def search(request: SearchRequest, db: AsyncSession = Depends(get_db)):
    if not settings.demo_mode and (not settings.tavily_api_key or not settings.deepseek_api_key):
        from fastapi import HTTPException

        raise HTTPException(
            status_code=503,
            detail="Missing TAVILY_API_KEY or DEEPSEEK_API_KEY. Enable DEMO_MODE=true for offline demo.",
        )

    return StreamingResponse(
        run_search_pipeline(
            query=request.query,
            conversation_id=request.conversation_id,
            tavily=_get_tavily(),
            deepseek=_get_deepseek(),
            db_session=db,
            embedding=_get_embedding,
            reranker=_get_reranker,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get("/health")
async def health():
    return {"status": "ok"}
