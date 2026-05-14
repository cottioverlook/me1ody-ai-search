from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models.db import Base, create_engine
from app.routers import history, search, suggest
from app.utils.logging import RequestLoggingMiddleware, configure_logging
from app.utils.security import PublicAccessMiddleware


configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = create_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="Me1ody AI Search", lifespan=lifespan)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(PublicAccessMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials="*" not in settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router)
app.include_router(suggest.router)
app.include_router(history.router)


@app.get("/api/ready")
async def ready():
    engine = create_engine(settings.database_url)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(lambda sync_conn: sync_conn.exec_driver_sql("SELECT 1"))
    finally:
        await engine.dispose()
    return {
        "status": "ready",
        "environment": settings.app_env,
        "database": "ok",
    }
