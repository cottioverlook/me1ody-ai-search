import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.db import Conversation, Message, create_engine, create_sessionmaker
from app.models.schemas import ConversationListItem, ConversationResponse, HistoryMessage, Source

router = APIRouter(prefix="/api", tags=["history"])

engine = create_engine(settings.database_url)
session_factory = create_sessionmaker(engine)


async def get_db():
    async with session_factory() as session:
        yield session


@router.get("/history", response_model=list[ConversationListItem])
async def list_conversations(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Conversation).order_by(Conversation.created_at.desc()).limit(20)
    )
    return [
        ConversationListItem(
            id=conv.id,
            title=conv.title,
            created_at=conv.created_at.isoformat(),
        )
        for conv in result.scalars()
    ]


@router.get("/history/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: str, db: AsyncSession = Depends(get_db)):
    conv = await db.get(Conversation, conversation_id)
    if not conv:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Conversation not found")

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )

    messages = []
    for msg in result.scalars():
        sources = None
        if msg.sources:
            try:
                sources = [Source(**s) for s in json.loads(msg.sources)]
            except (json.JSONDecodeError, TypeError):
                pass
        messages.append(
            HistoryMessage(role=msg.role, content=msg.content, sources=sources)
        )

    return ConversationResponse(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at.isoformat(),
        messages=messages,
    )
