from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import Message, create_engine, create_sessionmaker
from app.config import settings

router = APIRouter(prefix="/api", tags=["suggest"])

engine = create_engine(settings.database_url)
session_factory = create_sessionmaker(engine)


async def get_db():
    async with session_factory() as session:
        yield session


@router.get("/suggest")
async def suggest(q: str = "", db: AsyncSession = Depends(get_db)):
    if not q or len(q) < 2:
        return {"suggestions": []}

    result = await db.execute(
        select(Message.content)
        .where(Message.role == "user", Message.content.ilike(f"%{q}%"))
        .order_by(Message.created_at.desc())
        .limit(5)
    )
    suggestions = [row[0] for row in result.all()]
    return {"suggestions": suggestions}
